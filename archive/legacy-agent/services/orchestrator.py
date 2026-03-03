import re
from typing import Any, Dict, List, Optional, Set, Tuple

from clients.amplitude import AmplitudeClient, summarize_chart_payload
from clients.feedback import TypeformClient
from clients.slack import SlackWebhookClient, build_weekly_blocks
from config import (
    ChartMetric,
    Settings,
    get_chart_metrics_by_group,
    get_chart_reference,
    get_known_chart_ids,
)
from services.analyzer import InsightAnalyzer
from services.feedback_themes import build_feedback_theme_summary
from services.report_context import build_ios_release_context, load_context_sections
from services.temporal_memory import build_temporal_snapshot, load_temporal_memory, save_temporal_memory

ACTIVATION_TARGET_MIN_PCT = 40.0
ACTIVATION_TARGET_MAX_PCT = 50.0
PERCENT_PATTERN = re.compile(r"[-+]?\d+(?:\.\d+)?\s*(?:%|pp)(?=\s|$|[),.;:])", re.IGNORECASE)
RATIO_PATTERN = re.compile(r"\b\d+(?:\.\d+)?/\d+(?:\.\d+)?\b")
ABSOLUTE_PATTERN = re.compile(r"\b[-+]?\d+(?:\.\d+)?\s+absolute\b", re.IGNORECASE)
VS_NUMERIC_PATTERN = re.compile(r"\b\d+(?:\.\d+)?\s+vs\s+\d+(?:\.\d+)?\b", re.IGNORECASE)
PRIORITY_PIPE_PATTERN = re.compile(r"\s*\|\s*Priority:\s*[^|]+", re.IGNORECASE)
PRIORITY_SENTENCE_PATTERN = re.compile(r"\s*Priority:\s*[^.]+\.?", re.IGNORECASE)
WORD_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'/-]*")
MAX_INSIGHT_ACTION_ITEMS = 3
ALIGNMENT_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
    "user",
    "users",
    "metric",
    "metrics",
    "chart",
    "kpi",
}

def _manual_grouped_metrics(
    chart_ids: List[str],
    chart_set: str,
    app_id: int,
) -> Dict[str, List[ChartMetric]]:
    grouped: Dict[str, List[ChartMetric]] = {"core": [], "supplemental": []}
    for index, chart_id in enumerate(chart_ids):
        group_name = "core" if index < 5 else "supplemental"
        ref = get_chart_reference(chart_id)
        grouped[group_name].append(
            ChartMetric(
                metric_key=f"manual_{group_name}_{index + 1}",
                chart_id=chart_id,
                chart_name=ref["chart_title"],
                intent="Manual chart override.",
                chart_type="unknown",
                status="manual",
                group=group_name,
                chart_set=chart_set,
                app_id=app_id,
            )
        )
    return grouped


def _resolve_grouped_metrics(settings: Settings, chart_ids: Optional[List[str]]) -> Dict[str, List[ChartMetric]]:
    if chart_ids:
        unknown_chart_ids = [chart_id for chart_id in chart_ids if chart_id not in get_known_chart_ids()]
        if unknown_chart_ids:
            raise ValueError(
                "Chart overrides must be known tenant-prod chart IDs from the metric dictionary. "
                f"Unknown chart ID(s): {', '.join(unknown_chart_ids)}"
            )
        return _manual_grouped_metrics(chart_ids, settings.report_chart_set, settings.report_app_id)
    return get_chart_metrics_by_group(settings.report_chart_set)


def _as_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _fmt_number(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def _truncate_error(value: str, limit: int = 160) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[: limit - 3] + "..."


def _chart_ref_text(chart_title: str, chart_link: str) -> str:
    if chart_link:
        return f"<{chart_link}|{chart_title}>"
    return chart_title


def _slack_link_text(url: str, label: str) -> str:
    safe_label = str(label).replace("|", "¦").replace("<", "").replace(">", "")
    return f"<{url}|{safe_label}>"


def _short_chart_label(chart_title: str, max_words: int = 3) -> str:
    candidate = str(chart_title).strip()
    if "->" in candidate:
        candidate = candidate.split("->")[-1].strip()
    if ":" in candidate and len(WORD_TOKEN_PATTERN.findall(candidate)) > max_words:
        candidate = candidate.split(":")[-1].strip()

    words = WORD_TOKEN_PATTERN.findall(candidate)
    if not words:
        return "chart"
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[-max_words:])


def _build_chart_evidence_line(
    chart_title: str,
    chart_link: str,
    statement: str,
    suffix: str = "",
) -> str:
    full_statement = f"{chart_title}: {statement}"
    if chart_link:
        short_label = _short_chart_label(chart_title)
        return f"{full_statement} {_slack_link_text(chart_link, short_label)}{suffix}"
    return f"{full_statement}{suffix}"


def _summary_reliability(summary: Dict[str, Any]) -> Dict[str, Any]:
    reliability = summary.get("reliability")
    if not isinstance(reliability, dict):
        return {
            "confidence": "medium",
            "low_volume_caution": False,
            "incomplete_bucket_detected": False,
            "notes": [],
            "base_count": None,
            "converted_count": None,
        }
    return {
        "confidence": str(reliability.get("confidence") or "medium"),
        "low_volume_caution": bool(reliability.get("low_volume_caution")),
        "incomplete_bucket_detected": bool(reliability.get("incomplete_bucket_detected")),
        "notes": list(reliability.get("notes") or []),
        "base_count": _as_float(reliability.get("base_count")),
        "converted_count": _as_float(reliability.get("converted_count")),
    }


def _reliability_suffix(summary: Dict[str, Any]) -> str:
    # Keep metric lines concise; reliability caveats are handled in explanation text.
    _ = summary
    return ""


def _chart_reliability_context(
    core_results: List[Dict[str, Any]],
    supplemental_results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    charts: List[Dict[str, Any]] = []
    core_low = 0
    supplemental_low = 0

    for result in core_results + supplemental_results:
        if result.get("status") != "ok":
            continue
        summary = result.get("summary") or {}
        reliability = _summary_reliability(summary)
        row = {
            "metric_key": result.get("metric_key", ""),
            "group": result.get("group", ""),
            "chart_title": result.get("chart_title", ""),
            "chart_link": result.get("chart_link", ""),
            "confidence": reliability["confidence"],
            "base_count": reliability["base_count"],
            "converted_count": reliability["converted_count"],
            "low_volume_caution": reliability["low_volume_caution"],
            "incomplete_bucket_detected": reliability["incomplete_bucket_detected"],
            "notes": reliability["notes"],
        }
        charts.append(row)
        if reliability["confidence"] == "low":
            if row["group"] == "core":
                core_low += 1
            else:
                supplemental_low += 1

    return {
        "core_low_confidence_count": core_low,
        "supplemental_low_confidence_count": supplemental_low,
        "charts": charts,
    }


def _low_confidence_notes(core_results: List[Dict[str, Any]], limit: int = 3) -> List[str]:
    notes: List[str] = []
    for result in core_results:
        if result.get("status") != "ok":
            continue
        summary = result.get("summary") or {}
        reliability = _summary_reliability(summary)
        if reliability["confidence"] != "low":
            continue
        chart_ref = _chart_ref_text(result["chart_title"], result["chart_link"])
        base = reliability["base_count"]
        converted = reliability["converted_count"]
        if reliability["notes"]:
            reason = reliability["notes"][0]
        elif base is not None and converted is not None:
            reason = (
                f"low sample size ({_fmt_number(converted)}/{_fmt_number(base)}) "
                "limits week-over-week confidence."
            )
        else:
            reason = "available evidence is thin for confident interpretation."
        notes.append(f"*Claim:* Low confidence: {chart_ref}\n*Evidence:* {reason}")
        if len(notes) >= limit:
            break
    return notes


def _query_metrics(
    amplitude_client: AmplitudeClient,
    grouped_metrics: Dict[str, List[ChartMetric]],
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], int]:
    all_metrics = grouped_metrics["core"] + grouped_metrics["supplemental"]
    unique_chart_ids: List[str] = []
    seen_chart_ids = set()
    for metric in all_metrics:
        if not metric.has_chart_id:
            continue
        if metric.chart_id in seen_chart_ids:
            continue
        seen_chart_ids.add(metric.chart_id)
        unique_chart_ids.append(metric.chart_id)

    chart_success: Dict[str, Dict[str, Any]] = {}
    chart_failures: Dict[str, str] = {}

    for chart_id in unique_chart_ids:
        try:
            raw_payload = amplitude_client.query_chart(chart_id)
        except Exception as exc:  # pylint: disable=broad-except
            chart_failures[chart_id] = _truncate_error(str(exc) or "query failed")
            continue
        chart_success[chart_id] = {
            "summary": summarize_chart_payload(raw_payload),
            "raw": raw_payload,
        }

    def build_result(metric: ChartMetric) -> Dict[str, Any]:
        chart_ref = get_chart_reference(metric.chart_id, metric.chart_name) if metric.has_chart_id else {
            "chart_id": "",
            "chart_title": metric.chart_name,
            "chart_link": "",
        }
        result: Dict[str, Any] = {
            "metric_key": metric.metric_key,
            "chart_id": metric.chart_id,
            "chart_title": chart_ref["chart_title"],
            "chart_link": chart_ref["chart_link"],
            "intent": metric.intent,
            "chart_type": metric.chart_type,
            "group": metric.group,
            "status": "ok",
            "summary": {},
        }

        if not metric.has_chart_id:
            result["status"] = "missing_chart_id"
            result["error"] = "chart_id is empty"
            return result

        if metric.chart_id in chart_failures:
            result["status"] = "query_failed"
            result["error"] = chart_failures[metric.chart_id]
            return result

        success = chart_success.get(metric.chart_id)
        if not success:
            result["status"] = "query_failed"
            result["error"] = "chart query did not return a payload"
            return result

        result["summary"] = success["summary"]
        return result

    core_results = [build_result(metric) for metric in grouped_metrics["core"]]
    supplemental_results = [build_result(metric) for metric in grouped_metrics["supplemental"]]
    return core_results, supplemental_results, len(unique_chart_ids)


def _format_evidence_line(metric_result: Dict[str, Any]) -> str:
    chart_title = metric_result["chart_title"]
    chart_link = metric_result["chart_link"]
    status = metric_result.get("status")
    if status != "ok":
        reason = str(metric_result.get("error") or "unavailable")
        return _build_chart_evidence_line(chart_title, chart_link, f"unavailable ({reason}).")

    summary = metric_result.get("summary") or {}
    reliability_suffix = _reliability_suffix(summary)

    current_pct = _as_float(summary.get("current_conversion_pct"))
    current_start = _as_float(summary.get("current_start_count"))
    current_end = _as_float(summary.get("current_end_count"))
    previous_pct = _as_float(summary.get("previous_conversion_pct"))
    previous_start = _as_float(summary.get("previous_start_count"))
    previous_end = _as_float(summary.get("previous_end_count"))
    delta_relative_pct = _as_float(summary.get("conversion_delta_relative_pct"))

    if current_pct is not None and current_start is not None and current_end is not None:
        current_text = (
            f"{current_pct:.2f}% ({_fmt_number(current_end)}/{_fmt_number(current_start)})"
        )
        if previous_pct is not None and previous_start is not None and previous_end is not None:
            previous_text = (
                f"{previous_pct:.2f}% ({_fmt_number(previous_end)}/{_fmt_number(previous_start)})"
            )
            if delta_relative_pct is None and previous_pct != 0:
                delta_relative_pct = ((current_pct - previous_pct) / previous_pct) * 100.0
            if delta_relative_pct is not None:
                return _build_chart_evidence_line(
                    chart_title,
                    chart_link,
                    f"{current_text} vs {previous_text} ({delta_relative_pct:+.2f}%).",
                    reliability_suffix,
                )
            return _build_chart_evidence_line(
                chart_title,
                chart_link,
                f"{current_text} vs {previous_text}.",
                reliability_suffix,
            )
        return _build_chart_evidence_line(chart_title, chart_link, f"{current_text}.", reliability_suffix)

    latest = _as_float(summary.get("latest_value"))
    previous = _as_float(summary.get("previous_value"))
    pct_change = _as_float(summary.get("pct_change_vs_previous"))

    if latest is not None and previous is not None:
        if pct_change is None and previous != 0:
            pct_change = ((latest - previous) / previous) * 100.0
        pct_text = f"{pct_change:+.2f}%" if pct_change is not None else "n/a%"
        return _build_chart_evidence_line(
            chart_title,
            chart_link,
            (
                f"{_fmt_number(latest)} vs {_fmt_number(previous)} "
                f"({pct_text} WoW)."
            ),
            reliability_suffix,
        )

    if latest is not None:
        return _build_chart_evidence_line(
            chart_title,
            chart_link,
            f"latest {_fmt_number(latest)} (WoW % unavailable; previous period missing).",
            reliability_suffix,
        )

    return _build_chart_evidence_line(
        chart_title,
        chart_link,
        "no numeric values returned.",
        reliability_suffix,
    )


def _kpi_status_line(core_results: List[Dict[str, Any]]) -> str:
    if not core_results:
        return "North Star target 40-50%: unavailable (no core chart configured)."
    return (
        f"North Star target {ACTIVATION_TARGET_MIN_PCT:.0f}-{ACTIVATION_TARGET_MAX_PCT:.0f}%: "
        f"{_format_evidence_line(core_results[0])}"
    )


def _top_movers(
    core_results: List[Dict[str, Any]],
    limit: int = 3,
    exclude_chart_ids: Optional[Set[str]] = None,
) -> Tuple[List[str], List[str]]:
    excluded = set(exclude_chart_ids or set())
    ranked: List[Tuple[float, str, str]] = []
    seen_chart_ids: Set[str] = set()
    for result in core_results:
        if result.get("status") != "ok":
            continue
        chart_id = str(result.get("chart_id") or "")
        if chart_id and (chart_id in excluded or chart_id in seen_chart_ids):
            continue
        summary = result.get("summary") or {}
        reliability = _summary_reliability(summary)
        if reliability["confidence"] == "low":
            # De-prioritize low-confidence movers to reduce noise in the main metric section.
            continue
        latest = _as_float(summary.get("latest_value"))
        previous = _as_float(summary.get("previous_value"))
        pct_change = _as_float(summary.get("pct_change_vs_previous"))
        if latest is None or previous is None:
            continue
        if pct_change is None and previous != 0:
            pct_change = ((latest - previous) / previous) * 100.0
        if pct_change is None:
            continue
        ranked.append((abs(pct_change), chart_id, _format_evidence_line(result)))
        if chart_id:
            seen_chart_ids.add(chart_id)

    ranked.sort(key=lambda item: item[0], reverse=True)
    if ranked:
        selected = ranked[:limit]
        return [line for _score, _chart_id, line in selected], [
            chart_id for _score, chart_id, _line in selected if chart_id
        ]

    fallback: List[Tuple[str, str]] = []
    for result in core_results:
        if result.get("status") != "ok":
            continue
        chart_id = str(result.get("chart_id") or "")
        if chart_id and (chart_id in excluded or chart_id in seen_chart_ids):
            continue
        fallback.append((chart_id, _format_evidence_line(result)))
        if chart_id:
            seen_chart_ids.add(chart_id)

    if fallback:
        selected = fallback[:limit]
        return [line for _chart_id, line in selected], [chart_id for chart_id, _line in selected if chart_id]

    return ["No core chart evidence available this run."], []


def _supplemental_lines(
    supplemental_results: List[Dict[str, Any]],
    limit: int = 3,
    exclude_chart_ids: Optional[Set[str]] = None,
) -> List[str]:
    excluded = set(exclude_chart_ids or set())
    seen_chart_ids: Set[str] = set()
    lines: List[str] = []
    for result in supplemental_results:
        chart_id = str(result.get("chart_id") or "")
        if chart_id and (chart_id in excluded or chart_id in seen_chart_ids):
            continue
        lines.append(_format_evidence_line(result))
        if chart_id:
            seen_chart_ids.add(chart_id)
        if len(lines) >= limit:
            break
    while len(lines) < limit:
        lines.append("Supplemental diagnostic slot unavailable (missing chart contract entry).")
    return lines


def _format_all_chart_value(value: Optional[float], chart_type: str) -> str:
    if value is None:
        return "N/A"
    if str(chart_type).lower() == "funnel":
        return f"{value:.2f}%"
    return f"{value:.2f}"


def _format_all_chart_change(pct_change: Optional[float]) -> str:
    if pct_change is None:
        return "N/A"
    if abs(pct_change) < 1e-9:
        return "0.00%"
    sign = "+" if pct_change > 0 else ""
    return f"{sign}{pct_change:.2f}%"


def _all_charts_lines(
    core_results: List[Dict[str, Any]],
    supplemental_results: List[Dict[str, Any]],
) -> List[str]:
    lines: List[str] = []
    for result in core_results + supplemental_results:
        chart_title = str(result.get("chart_title") or "Unknown chart")
        chart_link = str(result.get("chart_link") or "")
        chart_type = str(result.get("chart_type") or "unknown")
        summary = result.get("summary") or {}
        latest = _as_float(summary.get("latest_value"))
        previous = _as_float(summary.get("previous_value"))
        pct_change = _as_float(summary.get("pct_change_vs_previous"))

        title_line = f"*<{chart_link}|{chart_title}>*" if chart_link else f"*{chart_title}*"
        metadata_line = (
            f"  _Change:_ {_format_all_chart_change(pct_change)} | "
            f"_Latest:_ {_format_all_chart_value(latest, chart_type)} | "
            f"_Previous:_ {_format_all_chart_value(previous, chart_type)} | "
            f"_Type:_ {chart_type}"
        )
        lines.append(f"{title_line}\n{metadata_line}")
    return lines


def _append_evidence_to_explanations(explanations: List[str], evidence_lines: List[str]) -> List[str]:
    if not evidence_lines:
        evidence_lines = ["No chart evidence available."]
    normalized: List[str] = []
    for item in explanations[:5]:
        text = str(item).strip()
        if not text:
            continue
        normalized.append(text)

    if normalized:
        return normalized

    return [
        (
            "Low confidence: there is not enough linked evidence to explain the observed movement. "
            f"Evidence: {evidence_lines[0]}"
        )
    ]


def _tokenize_alignment(text: str) -> Set[str]:
    tokens: Set[str] = set()
    for token in WORD_TOKEN_PATTERN.findall(str(text).lower()):
        if len(token) <= 2 or token in ALIGNMENT_STOPWORDS or token.isdigit():
            continue
        tokens.add(token)
    return tokens


def _alignment_score(text: str, metric_result: Dict[str, Any]) -> int:
    candidate = str(text or "")
    if not candidate.strip():
        return 0
    lowered = candidate.lower()
    chart_title = str(metric_result.get("chart_title") or "")
    score = 0
    if chart_title and chart_title.lower() in lowered:
        score += 8

    title_tokens = _tokenize_alignment(chart_title)
    if title_tokens:
        score += len(title_tokens.intersection(_tokenize_alignment(candidate)))

    reliability = _summary_reliability(metric_result.get("summary") or {})
    if reliability.get("incomplete_bucket_detected") and "incomplete" in lowered:
        score += 2
    if reliability.get("low_volume_caution") and ("sample" in lowered or "volume" in lowered):
        score += 2
    return score


def _action_pair_score(action: str, explanation: str, metric_result: Dict[str, Any]) -> int:
    explanation_tokens = _tokenize_alignment(explanation)
    action_tokens = _tokenize_alignment(action)
    overlap = len(explanation_tokens.intersection(action_tokens))
    return overlap + _alignment_score(action, metric_result)


def _fallback_explanation_for_metric(metric_result: Dict[str, Any]) -> str:
    chart_title = str(metric_result.get("chart_title") or "Core activation metric")
    evidence = _format_evidence_line(metric_result)
    return f"{chart_title} changed this week. Evidence: {evidence}"


def _fallback_action_for_metric(metric_result: Dict[str, Any]) -> str:
    chart_title = str(metric_result.get("chart_title") or "this core metric")
    reliability = _summary_reliability(metric_result.get("summary") or {})
    if reliability.get("incomplete_bucket_detected"):
        return (
            f"Re-check {chart_title} after the current weekly bucket closes to confirm the movement persists."
        )
    return f"Investigate the event-level drivers behind the movement in {chart_title} and validate persistence next week."


def _prioritized_core_results(
    core_results: List[Dict[str, Any]],
    prioritized_chart_ids: List[str],
    limit: int = MAX_INSIGHT_ACTION_ITEMS,
) -> List[Dict[str, Any]]:
    ordered: List[Dict[str, Any]] = []
    seen: Set[str] = set()
    by_chart_id: Dict[str, Dict[str, Any]] = {
        str(result.get("chart_id") or ""): result
        for result in core_results
        if result.get("status") == "ok" and str(result.get("chart_id") or "")
    }

    for chart_id in prioritized_chart_ids:
        result = by_chart_id.get(str(chart_id))
        if not result:
            continue
        cid = str(result.get("chart_id") or "")
        if cid in seen:
            continue
        seen.add(cid)
        ordered.append(result)
        if len(ordered) >= limit:
            return ordered

    for result in core_results:
        if result.get("status") != "ok":
            continue
        cid = str(result.get("chart_id") or "")
        if cid and cid in seen:
            continue
        if cid:
            seen.add(cid)
        ordered.append(result)
        if len(ordered) >= limit:
            break
    return ordered


def _align_core_insights_and_actions(
    explanations: List[str],
    actions: List[str],
    core_priority_results: List[Dict[str, Any]],
) -> Tuple[List[str], List[str]]:
    explanation_pool = [str(item).strip() for item in explanations if str(item).strip()]
    action_pool = [str(item).strip() for item in actions if str(item).strip()]
    if not core_priority_results:
        return explanation_pool[:MAX_INSIGHT_ACTION_ITEMS], action_pool[:MAX_INSIGHT_ACTION_ITEMS]

    requested_pairs = max(len(explanation_pool), len(action_pool), 1)
    limit = min(MAX_INSIGHT_ACTION_ITEMS, len(core_priority_results), requested_pairs)

    aligned_explanations: List[str] = []
    aligned_actions: List[str] = []

    for metric_result in core_priority_results[:limit]:
        if explanation_pool:
            scored_explanations = [
                (_alignment_score(candidate, metric_result), index, candidate)
                for index, candidate in enumerate(explanation_pool)
            ]
            scored_explanations.sort(key=lambda row: row[0], reverse=True)
            best_expl_score, best_expl_index, best_explanation = scored_explanations[0]
            if best_expl_score > 0:
                explanation = best_explanation
                explanation_pool.pop(best_expl_index)
            else:
                explanation = explanation_pool.pop(0)
        else:
            explanation = _fallback_explanation_for_metric(metric_result)

        if action_pool:
            scored_actions = [
                (_action_pair_score(candidate, explanation, metric_result), index, candidate)
                for index, candidate in enumerate(action_pool)
            ]
            scored_actions.sort(key=lambda row: row[0], reverse=True)
            best_action_score, best_action_index, best_action = scored_actions[0]
            if best_action_score > 0:
                action = best_action
                action_pool.pop(best_action_index)
            else:
                action = action_pool.pop(0)
        else:
            action = _fallback_action_for_metric(metric_result)

        aligned_explanations.append(explanation)
        aligned_actions.append(action)

    return aligned_explanations, aligned_actions


def _infer_owner_team(action_text: str) -> str:
    lowered = action_text.lower()
    team_keywords = {
        "Product": [
            "onboarding",
            "signup",
            "activation",
            "funnel",
            "copy",
            "flow",
            "ux",
        ],
        "Data": [
            "instrumentation",
            "tracking",
            "event",
            "schema",
            "pipeline",
            "query",
            "chart",
        ],
        "Growth": [
            "experiment",
            "a/b",
            "ab test",
            "campaign",
            "retention",
            "email",
            "re-engagement",
        ],
        "Engineering": [
            "release",
            "ios",
            "android",
            "bug",
            "crash",
            "performance",
            "latency",
        ],
    }
    scores = {team: 0 for team in team_keywords}
    for team, keywords in team_keywords.items():
        for keyword in keywords:
            if keyword in lowered:
                scores[team] += 1
    best_team = max(scores.items(), key=lambda item: item[1])
    if best_team[1] <= 0:
        return "Product"
    return best_team[0]


def _normalize_actions(actions: List[str]) -> List[str]:
    normalized: List[str] = []
    for item in actions[:5]:
        text = _strip_priority_label(str(item).strip())
        if not text:
            continue
        normalized.append(text)

    if normalized:
        return normalized

    return [
        "Review top mover evidence and define one follow-up step this week."
    ]


def _strip_priority_label(text: str) -> str:
    without_pipe = PRIORITY_PIPE_PATTERN.sub("", text)
    without_sentence = PRIORITY_SENTENCE_PATTERN.sub("", without_pipe)
    return re.sub(r"\s{2,}", " ", without_sentence).strip()


def _has_percentage(text: str) -> bool:
    return bool(PERCENT_PATTERN.search(text))


def _has_absolute_context(text: str) -> bool:
    return bool(
        RATIO_PATTERN.search(text)
        or ABSOLUTE_PATTERN.search(text)
        or VS_NUMERIC_PATTERN.search(text)
    )


def _ensure_deterministic_absolute_context(text: str, deterministic_evidence: str) -> str:
    content = str(text).strip()
    if not content:
        return content
    if not _has_percentage(content):
        return content
    if _has_absolute_context(content):
        return content
    return f"{content} | Absolute context (deterministic): {deterministic_evidence}"


def _enforce_percentage_absolute_contract(
    items: List[str],
    deterministic_evidence_lines: List[str],
) -> List[str]:
    if not deterministic_evidence_lines:
        return items
    enforced: List[str] = []
    for index, item in enumerate(items):
        evidence = deterministic_evidence_lines[index % len(deterministic_evidence_lines)]
        enforced.append(_ensure_deterministic_absolute_context(item, evidence))
    return enforced


def _core_failure_note(core_results: List[Dict[str, Any]], report_chart_set: str) -> Optional[str]:
    failed = [result for result in core_results if result.get("status") != "ok"]
    if not failed:
        return None

    failed_keys = ", ".join(result.get("metric_key", "unknown_metric") for result in failed)
    rollback_hint = (
        " Toggle REPORT_CHART_SET=legacy for immediate rollback."
        if report_chart_set == "activation_v1"
        else ""
    )
    return (
        f"Pipeline note: {len(failed)}/{len(core_results)} core chart(s) unavailable "
        f"({failed_keys}). Reporting continues with available evidence and reduced confidence.{rollback_hint}"
    )


def _skip_ai_analysis_payload(reason: str, model_name: str) -> Dict[str, Any]:
    return {
        "headline": "AI analysis skipped; report generated from deterministic chart evidence.",
        "key_changes": ["AI stage disabled for this run."],
        "possible_explanations": [f"Low confidence: {reason}"],
        "suggested_actions": [f"Pipeline note: {reason}"],
        "analysis_meta": {
            "requested_model": model_name,
            "used_model": "skipped",
            "fallback_used": False,
            "ai_skipped": True,
            "skip_reason": reason,
        },
    }


def run_weekly_report(
    settings: Settings,
    dry_run: bool = False,
    chart_ids: Optional[List[str]] = None,
    skip_ai: bool = False,
) -> Dict[str, Any]:
    grouped_metrics = _resolve_grouped_metrics(settings=settings, chart_ids=chart_ids)

    amplitude_client = AmplitudeClient(
        base_url=settings.amplitude_base_url,
        api_key=settings.amplitude_api_key,
        secret_key=settings.amplitude_secret_key,
    )
    feedback_client = TypeformClient(token=settings.typeform_token, form_id=settings.typeform_form_id)
    analyzer = None if skip_ai else InsightAnalyzer(api_key=settings.gemini_api_key, model=settings.gemini_model)
    slack_client = SlackWebhookClient(
        webhook_url=settings.slack_webhook_url,
        channel=settings.slack_channel,
    )

    configured_metric_count = len(grouped_metrics["core"]) + len(grouped_metrics["supplemental"])
    print(
        f"Fetching Amplitude charts for {configured_metric_count} metric contracts "
        f"(chart_set={settings.report_chart_set})..."
    )
    core_results, supplemental_results, queried_chart_count = _query_metrics(
        amplitude_client=amplitude_client,
        grouped_metrics=grouped_metrics,
    )

    print("Fetching Typeform feedback context...")
    feedback_items = feedback_client.fetch_recent_responses(days=settings.lookback_days)
    feedback_themes = build_feedback_theme_summary(feedback_items)

    chart_summaries_for_ai: List[Dict[str, Any]] = []
    for result in core_results:
        if result.get("status") != "ok":
            continue
        chart_summaries_for_ai.append(
            (result.get("summary") or {})
            | {
                "metric_key": result["metric_key"],
                "chart_title": result["chart_title"],
                "chart_link": result["chart_link"],
            }
        )

    context_sections = load_context_sections()

    print("Refreshing iOS release context...")
    ios_release_context = build_ios_release_context()
    if ios_release_context.get("ingestion_status") == "error":
        error = str(ios_release_context.get("ingestion_error") or "unknown error")
        print(f"Warning: iOS release ingestion failed ({error}). Continuing with cached release log context.")

    temporal_memory = load_temporal_memory()
    chart_reliability = _chart_reliability_context(core_results, supplemental_results)

    if analyzer is None:
        skip_reason = "AI stage skipped via --skip-ai or SKIP_AI_ANALYSIS=true."
        print(f"Skipping AI analysis ({skip_reason})")
        analysis = _skip_ai_analysis_payload(skip_reason, settings.gemini_model)
    else:
        print("Generating AI analysis...")
        analysis = analyzer.generate(
            chart_summaries=chart_summaries_for_ai,
            feedback_items=feedback_items,
            feedback_themes=feedback_themes,
            chart_reliability=chart_reliability,
            context_sections=context_sections,
            ios_release_context=ios_release_context,
            temporal_memory=temporal_memory,
        )

    analysis_meta = analysis.get("analysis_meta") or {}
    if analysis_meta.get("fallback_used"):
        requested_model = analysis_meta.get("requested_model", settings.gemini_model)
        used_model = analysis_meta.get("used_model", "unknown")
        fallback_reason = str(analysis_meta.get("fallback_reason") or "").strip()
        if fallback_reason:
            fallback_note = (
                f"Pipeline note: requested Gemini model `{requested_model}` failed "
                f"({fallback_reason}); used `{used_model}` instead."
            )
        else:
            fallback_note = (
                f"Pipeline note: requested Gemini model `{requested_model}` was unavailable; "
                f"used `{used_model}` instead."
            )
        analysis["suggested_actions"] = [fallback_note] + list(analysis.get("suggested_actions") or [])

    kpi_status = _kpi_status_line(core_results)
    top_movers, top_mover_chart_ids = _top_movers(core_results)
    used_chart_ids = set(top_mover_chart_ids)
    supplemental_diagnostics = _supplemental_lines(
        supplemental_results,
        exclude_chart_ids=used_chart_ids,
    )

    core_priority_results = _prioritized_core_results(core_results, top_mover_chart_ids)
    aligned_explanations, aligned_actions = _align_core_insights_and_actions(
        explanations=_as_string_list(analysis.get("possible_explanations")),
        actions=_as_string_list(analysis.get("suggested_actions")),
        core_priority_results=core_priority_results,
    )

    evidence_for_claims = top_movers if top_movers else [kpi_status]
    explanations = _append_evidence_to_explanations(
        aligned_explanations,
        evidence_for_claims,
    )
    low_confidence_notes = _low_confidence_notes(core_results)
    if low_confidence_notes:
        explanations = low_confidence_notes + explanations

    actions = _normalize_actions(aligned_actions)

    core_failure_note = _core_failure_note(core_results, settings.report_chart_set)
    if core_failure_note:
        explanations = [
            "*Claim:* Low confidence: pipeline coverage is reduced this week.\n"
            f"*Evidence:* {core_failure_note}"
        ] + explanations
        actions = [
            core_failure_note
        ] + actions

    analysis["key_changes"] = top_movers
    analysis["possible_explanations"] = explanations
    analysis["suggested_actions"] = actions

    memory_write_result: Dict[str, Any] = {"status": "not_attempted", "memory_path": ""}
    memory_snapshot = build_temporal_snapshot(
        headline=analysis["headline"],
        kpi_status=kpi_status,
        key_changes=analysis["key_changes"],
        explanations=analysis["possible_explanations"],
        actions=analysis["suggested_actions"],
        core_results=core_results,
    )
    try:
        memory_write_result = save_temporal_memory(memory_snapshot)
    except OSError as exc:
        memory_write_result = {
            "status": "error",
            "memory_path": "",
            "error": _truncate_error(str(exc) or "failed to write temporal memory"),
        }
        print(
            "Warning: failed to update temporal memory file "
            f"({memory_write_result['error']}). Continuing without memory write."
        )

    blocks = build_weekly_blocks(
        headline=analysis["headline"],
        kpi_status=kpi_status,
        top_movers=analysis["key_changes"],
        explanations=analysis["possible_explanations"],
        actions=analysis["suggested_actions"],
        supplemental_diagnostics=supplemental_diagnostics,
        ios_release_context=ios_release_context,
        all_charts=_all_charts_lines(core_results, supplemental_results),
    )

    fallback_text = "User Insights Digest"
    result = {
        "analysis": analysis,
        "feedback_count": len(feedback_items),
        "feedback_theme_count": int(feedback_themes.get("theme_count", 0)),
        "chart_count": queried_chart_count,
        "core_metric_count": len(core_results),
        "supplemental_metric_count": len(supplemental_results),
        "report_chart_set": settings.report_chart_set,
        "analysis_meta": analysis_meta,
        "core_low_confidence_count": int(chart_reliability.get("core_low_confidence_count", 0)),
        "ios_release_ingestion_status": ios_release_context.get("ingestion_status", "unknown"),
        "temporal_memory_status": memory_write_result.get("status", "unknown"),
        "temporal_memory_path": memory_write_result.get("memory_path", ""),
    }

    if dry_run:
        print("Dry run enabled. Not posting to Slack.")
        print(fallback_text)
        result["slack_preview"] = {
            "text": fallback_text,
            "blocks": blocks,
        }
        return result

    print("Posting report to Slack...")
    slack_client.post_report(text=fallback_text, blocks=blocks)
    print("Report posted.")
    return result


def _as_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]
