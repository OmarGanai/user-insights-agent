import json
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import requests


SYSTEM_PROMPT = """
You are a product analyst for tenant.
You are given:
1) Weekly Amplitude chart summaries
2) User feedback snippets + extracted feedback themes
3) Structured app context (base app context + activation-weekly context)
4) iOS release context (latest lookup + recent release log rows)
5) Temporal memory from prior weekly reports
6) Chart reliability annotations

Task:
- Identify the 2-3 most important metric movements.
- Focus on the core activation charts provided in chart_summaries.
- Prioritize findings that remove the need for stakeholders to manually inspect charts.
- Keep headline and key changes factual and metric-grounded.
- In key changes, include concrete values/deltas whenever available.
- For possible explanations, you may propose cautious hypotheses only when grounded in provided chart metrics, feedback text/themes, and app context.
- If evidence is weak or reliability notes show thin evidence, explicitly say "Low confidence".
- Never invent product features or events not present in input data.
- When mentioning a chart, use this exact format: "<chart_title> (<chart_link>)". Never mention chart IDs.
- Use user journey/company context to make interpretations easier to understand for non-technical readers.
- Follow the report style contract exactly: evidence first, confidence explicit, and action items decision-oriented.
- Keep possible_explanations and suggested_actions positionally aligned (item 1 explains key movement 1, etc.).

Output must be strict JSON:
{
  "headline": "single factual sentence",
  "key_changes": ["factual observation with metric values and chart title/link", "..."],
  "possible_explanations": ["grounded hypothesis with confidence level and supporting evidence from input", "..."],
  "suggested_actions": ["verification/investigation action grounded in observed facts", "..."]
}
"""

REPORT_STYLE_CONTRACT = {
    "headline": (
        "One sentence that states North Star direction and major risk/context. "
        "Avoid repeating exact metric numbers that are already covered in key changes."
    ),
    "key_changes": [
        "Each item includes chart title/link and concrete evidence (percentages and absolute counts).",
        "Order by decision importance, not by metric novelty.",
    ],
    "possible_explanations": [
        "Every explanation is grounded in chart evidence + feedback/release/context signals.",
        "When evidence is weak, prefix explicitly with 'Low confidence:'.",
    ],
    "suggested_actions": [
        "Actions are concrete and immediately executable.",
        "Each action should include owner and a specific next step.",
        "Avoid explicit priority labels such as P0/P1/P2 unless requested.",
    ],
}


class InsightAnalyzer:
    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model

    def generate(
        self,
        chart_summaries: List[Dict[str, Any]],
        feedback_items: List[Dict[str, Any]],
        app_context: str = "",
        feedback_themes: Optional[Dict[str, Any]] = None,
        chart_reliability: Optional[Dict[str, Any]] = None,
        context_sections: Optional[Dict[str, Any]] = None,
        ios_release_context: Optional[Dict[str, Any]] = None,
        temporal_memory: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        normalized_context_sections = _normalize_context_sections(
            app_context=app_context,
            context_sections=context_sections,
        )
        context_section = _context_section_for_prompt(normalized_context_sections)
        payload = {
            "report_generated_at": datetime.utcnow().isoformat() + "Z",
            "chart_summaries": chart_summaries,
            "feedback_items": feedback_items,
            "feedback_themes": _normalize_json_block(
                feedback_themes,
                fallback={
                    "feedback_items_count": len(feedback_items),
                    "feedback_snippets_count": 0,
                    "theme_count": 0,
                    "themes": [],
                },
                max_chars=12000,
            ),
            "chart_reliability": _normalize_json_block(
                chart_reliability,
                fallback={
                    "core_low_confidence_count": 0,
                    "supplemental_low_confidence_count": 0,
                    "charts": [],
                },
                max_chars=15000,
            ),
            "report_style_contract": REPORT_STYLE_CONTRACT,
            "context_sections": normalized_context_sections,
            "ios_release_context": _normalize_json_block(
                ios_release_context,
                fallback={
                    "ingestion_status": "unknown",
                    "ingestion_error": "",
                    "recent_releases": [],
                    "release_notes_ingestion_status": "unknown",
                    "release_notes_ingestion_error": "",
                    "recent_release_notes": [],
                    "recent_releases_with_notes": [],
                },
                max_chars=7000,
            ),
            "temporal_memory": _normalize_json_block(
                temporal_memory,
                fallback={
                    "schema_version": 1,
                    "last_updated_utc": "",
                    "latest_report": None,
                    "previous_report": None,
                },
                max_chars=10000,
            ),
        }
        user_prompt = (
            "Analyze this weekly data.\n"
            "Use plain language for product and engineering stakeholders.\n"
            "Avoid chart IDs and always use chart titles with links.\n\n"
            f"Structured Prompt Payload:\n{json.dumps(payload, indent=2)}\n\n"
            "Report Style Contract:\n"
            f"{json.dumps(REPORT_STYLE_CONTRACT, indent=2)}\n\n"
            f"User Journey Context:\n{context_section}\n\n"
            "iOS Release Context:\n"
            f"{json.dumps(payload['ios_release_context'], indent=2)}\n\n"
            "Temporal Memory:\n"
            f"{json.dumps(payload['temporal_memory'], indent=2)}"
        )

        gemini_result = self._call_gemini(user_prompt)
        if isinstance(gemini_result, tuple):
            content, model_meta = gemini_result
        else:
            content = gemini_result
            model_meta = {
                "requested_model": self.model,
                "used_model": self.model,
                "fallback_used": False,
            }

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError:
            parsed = {
                "headline": "Weekly metrics analysis generated.",
                "key_changes": [content[:400]],
                "possible_explanations": [],
                "suggested_actions": [],
            }
        analysis = {
            "headline": str(parsed.get("headline", "Weekly metrics analysis generated.")),
            "key_changes": _ensure_string_list(parsed.get("key_changes")),
            "possible_explanations": _ensure_string_list(parsed.get("possible_explanations")),
            "suggested_actions": _ensure_string_list(parsed.get("suggested_actions")),
            "analysis_meta": model_meta,
        }
        _apply_quality_guards(analysis, chart_summaries)
        return analysis

    def _call_gemini(self, user_prompt: str) -> Tuple[str, Dict[str, Any]]:
        """
        Call Gemini REST API and return the raw model text response.
        """
        combined_prompt = f"{SYSTEM_PROMPT.strip()}\n\n{user_prompt}"
        models_to_try = [self.model]
        if self.model != "gemini-3-flash-preview":
            models_to_try.append("gemini-3-flash-preview")

        last_error = "unknown error"
        failure_by_model: Dict[str, str] = {}
        for model_name in models_to_try:
            model_last_error = "unknown error"
            for attempt in range(3):
                try:
                    response = self._post_gemini_request(model_name, combined_prompt)
                except requests.RequestException as exc:
                    model_last_error = f"request error: {exc}"
                    last_error = model_last_error
                    wait_seconds = _retry_wait_seconds(None, attempt)
                    print(
                        f"Warning: Gemini request failed on model '{model_name}' "
                        f"({exc}). Retrying in {wait_seconds}s (attempt {attempt + 1}/3)."
                    )
                    time.sleep(wait_seconds)
                    continue

                if response.status_code in (429, 500, 502, 503, 504):
                    api_message = _extract_response_error_message(response)
                    if api_message:
                        model_last_error = f"http {response.status_code}: {api_message}"
                    else:
                        model_last_error = f"http {response.status_code}"
                    last_error = model_last_error
                    wait_seconds = _retry_wait_seconds(response, attempt)
                    print(
                        f"Warning: Gemini returned {response.status_code} on model '{model_name}'. "
                        f"Retrying in {wait_seconds}s (attempt {attempt + 1}/3)."
                    )
                    time.sleep(wait_seconds)
                    continue

                try:
                    response.raise_for_status()
                except requests.HTTPError as exc:
                    api_message = _extract_response_error_message(response)
                    if api_message:
                        model_last_error = f"http {response.status_code}: {api_message}"
                    else:
                        model_last_error = f"http {response.status_code}: {exc}"
                    last_error = model_last_error
                    print(
                        f"Warning: Gemini request failed on model '{model_name}' "
                        f"({model_last_error})."
                    )
                    # Non-retryable status for this model (for example, model not found).
                    break
                payload = response.json()
                candidates = payload.get("candidates") or []
                if not candidates:
                    return "{}", _model_meta(
                        requested=self.model,
                        used=model_name,
                        fallback_reason=failure_by_model.get(self.model),
                    )
                parts = ((candidates[0].get("content") or {}).get("parts")) or []
                if not parts:
                    return "{}", _model_meta(
                        requested=self.model,
                        used=model_name,
                        fallback_reason=failure_by_model.get(self.model),
                    )
                text = parts[0].get("text")
                return (text or "{}"), _model_meta(
                    requested=self.model,
                    used=model_name,
                    fallback_reason=failure_by_model.get(self.model),
                )

            failure_by_model[model_name] = model_last_error
            print(f"Warning: exhausted retries for model '{model_name}'.")

        raise RuntimeError(f"Gemini request failed after retries across available models ({last_error}).")

    def _post_gemini_request(self, model_name: str, prompt_text: str) -> requests.Response:
        endpoint = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent?key={self.api_key}"
        )
        body = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt_text}],
                }
            ],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        return requests.post(endpoint, json=body, timeout=60)


def _ensure_string_list(value: Any) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _retry_wait_seconds(response: Optional[requests.Response], attempt_index: int) -> int:
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        if retry_after and retry_after.isdigit():
            return min(int(retry_after), 20)
    # Fast exponential backoff with bounded wait.
    return min(2 ** attempt_index, 8)


def _extract_response_error_message(response: requests.Response) -> str:
    try:
        payload = response.json()
    except ValueError:
        return ""
    error = payload.get("error")
    if isinstance(error, dict):
        message = error.get("message")
        if isinstance(message, str):
            return message.strip()
    if isinstance(error, str):
        return error.strip()
    return ""


def _normalize_context(context: str, max_chars: int = 12000) -> str:
    trimmed = (context or "").strip()
    if not trimmed:
        return ""
    if len(trimmed) <= max_chars:
        return trimmed
    return trimmed[:max_chars] + "\n\n[Context truncated]"


def _normalize_context_sections(
    app_context: str,
    context_sections: Optional[Dict[str, Any]],
) -> Dict[str, str]:
    base_context = ""
    activation_context = ""
    context_source = "none"

    if isinstance(context_sections, dict):
        base_context = _normalize_context(str(context_sections.get("base_app_context") or ""))
        activation_context = _normalize_context(str(context_sections.get("activation_weekly_context") or ""))
        context_source = str(context_sections.get("context_source") or "").strip() or "split"

    if not base_context and not activation_context:
        legacy_context = _normalize_context(app_context)
        if legacy_context:
            base_context = legacy_context
            context_source = "legacy_fallback"
        else:
            context_source = "none"

    return {
        "context_source": context_source,
        "base_app_context": base_context,
        "activation_weekly_context": activation_context,
    }


def _context_section_for_prompt(context_sections: Dict[str, str]) -> str:
    base_context = str(context_sections.get("base_app_context") or "")
    activation_context = str(context_sections.get("activation_weekly_context") or "")
    source = str(context_sections.get("context_source") or "none")

    if not base_context and not activation_context:
        return "No user journey context provided."

    return (
        f"Context source: {source}\n\n"
        f"Base App Context:\n{base_context or 'Not provided.'}\n\n"
        f"Activation Weekly Context:\n{activation_context or 'Not provided.'}"
    )


def _normalize_json_block(value: Any, fallback: Dict[str, Any], max_chars: int) -> Dict[str, Any]:
    if value is None:
        return fallback
    if not isinstance(value, dict):
        return fallback | {"note": "Invalid section payload; expected object."}
    serialized = json.dumps(value, ensure_ascii=True)
    if len(serialized) <= max_chars:
        return value

    return fallback | {
        "note": "Section truncated due to size.",
        "truncated_preview": serialized[:max_chars],
    }


def _model_meta(requested: str, used: str, fallback_reason: Optional[str] = None) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "requested_model": requested,
        "used_model": used,
        "fallback_used": used != requested,
    }
    if used != requested and fallback_reason:
        meta["fallback_reason"] = fallback_reason
    return meta


def _apply_quality_guards(analysis: Dict[str, Any], chart_summaries: List[Dict[str, Any]]) -> None:
    if not analysis.get("key_changes"):
        analysis["key_changes"] = _fallback_key_changes(chart_summaries)

    if not analysis.get("possible_explanations"):
        analysis["possible_explanations"] = [
            (
                "Low confidence: this week does not include enough linked feedback "
                "evidence to confidently explain the metric movements."
            )
        ]

    if not analysis.get("suggested_actions"):
        analysis["suggested_actions"] = [
            "Validate the top metric changes against recent user feedback before taking action."
        ]


def _fallback_key_changes(chart_summaries: List[Dict[str, Any]]) -> List[str]:
    ranked: List[Tuple[float, str]] = []
    for chart in chart_summaries:
        latest = _to_float(chart.get("latest_value"))
        previous = _to_float(chart.get("previous_value"))
        if latest is None or previous is None:
            continue

        pct_change = _to_float(chart.get("pct_change_vs_previous"))
        magnitude = abs(pct_change) if pct_change is not None else abs(latest - previous)
        chart_title = str(chart.get("chart_title") or "Unknown chart")
        chart_link = str(chart.get("chart_link") or "")
        chart_ref = f"{chart_title} ({chart_link})" if chart_link else chart_title

        if pct_change is not None:
            description = (
                f"{chart_ref}: {previous:.2f} -> {latest:.2f} "
                f"({pct_change:+.2f}% vs previous period)."
            )
        else:
            delta = latest - previous
            description = f"{chart_ref}: {previous:.2f} -> {latest:.2f} ({delta:+.2f} absolute change)."
        ranked.append((magnitude, description))

    ranked.sort(key=lambda item: item[0], reverse=True)
    if ranked:
        return [description for _magnitude, description in ranked[:3]]
    return ["No measurable chart deltas were available in this run."]


def _to_float(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None
