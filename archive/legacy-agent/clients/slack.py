from datetime import datetime
import re
from typing import Any, Dict, List, Optional

import requests

MAX_SECTION_TEXT_CHARS = 2900
MAX_BULLET_ITEM_CHARS = 500
MAX_TOP_MOVERS = 3
MAX_ACTIONS = 3
MAX_EXPLANATIONS = 3
BULLET_GLYPH = "\u2022"
REPORT_TITLE = "User Insights Digest"
METADATA_SUBTITLE = (
    "_Cohort: Users excluding tenant team | Trailing 4 weeks vs previous 4 weeks | Report release: Mondays_"
)
CHANGE_UP_GLYPH = ":large_green_circle:"
CHANGE_DOWN_GLYPH = ":red_circle:"
CHANGE_NEUTRAL_GLYPH = ":white_circle:"
TRAILING_REFERENCE_PATTERN = re.compile(
    r"^(?P<prefix>.+?)\s*\((?P<url>https?://[^\s)]+)\)(?P<suffix>[.!,;:]?)$"
)
INLINE_REFERENCE_PATTERN = re.compile(r"(?P<label>[^()<>]+?)\s*\((?P<url>https?://[^\s)]+)\)")
SLACK_LINK_PATTERN = re.compile(r"<(?P<url>https?://[^|>]+)\|(?P<label>[^>]*)>")
PAREN_URL_PATTERN = re.compile(r"\(\s*(?P<url>https?://[^\s)]+)\s*\)")
BARE_URL_PATTERN = re.compile(r"(?P<url>https?://[^\s)>]+)")
CLAIM_PATTERN = re.compile(r"\*?Claim:\*?\s*", re.IGNORECASE)
EVIDENCE_PATTERN = re.compile(r"\*?Evidence:\*?\s*", re.IGNORECASE)
PRIORITY_PIPE_PATTERN = re.compile(r"\s*\|\s*Priority:\s*[^|]+", re.IGNORECASE)
PRIORITY_SENTENCE_PATTERN = re.compile(r"\s*Priority:\s*[^.]+\.?", re.IGNORECASE)
EXPECTED_IMPACT_PIPE_PATTERN = re.compile(r"\s*\|\s*Expected impact:\s*[^|]+", re.IGNORECASE)
EXPECTED_IMPACT_SENTENCE_PATTERN = re.compile(r"\s*Expected impact:\s*[^.]+\.?", re.IGNORECASE)
ABSOLUTE_CONTEXT_PATTERN = re.compile(
    r"\s*\|\s*Absolute context \(deterministic\):\s*[^|]+",
    re.IGNORECASE,
)
ADDITIONAL_CONTEXT_PATTERN = re.compile(
    r"\s*\|\s*Additional model context:\s*",
    re.IGNORECASE,
)
LOW_CONFIDENCE_PREFIX_PATTERN = re.compile(r"^\s*Low confidence:\s*", re.IGNORECASE)
CONFIDENCE_PREFIX_PATTERN = re.compile(
    r"^\s*[*_]*(?:low|medium|high)\s+confidence[*_]*\s*:\s*",
    re.IGNORECASE,
)
GROUNDED_PREFIX_PATTERN = re.compile(
    r"^\s*[*_]*grounded(?:\s+observation)?[*_]*\s*:\s*",
    re.IGNORECASE,
)
INSIGHT_PREFIX_PATTERN = re.compile(r"^\s*[*_]*insight[*_]*\s*:\s*", re.IGNORECASE)
SUMMARY_NUMERIC_HINT_PATTERN = re.compile(r"(?:\d+(?:\.\d+)?%|\d+(?:\.\d+)?\s*pp|\b\d+/\d+\b)")
PERCENT_VALUE_PATTERN = re.compile(r"([-+]?\d+(?:\.\d+)?)\s*%")
SLACK_LINK_LABEL_PATTERN = re.compile(r"<https?://[^|>]+\|([^>]+)>")
WORD_TOKEN_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9'/-]*")
NORTH_STAR_PREFIX_PATTERN = re.compile(
    r"^North Star target\s+\d+(?:\.\d+)?-\d+(?:\.\d+)?%\s*:\s*",
    re.IGNORECASE,
)
CONVERSION_SNIPPET_PATTERN = re.compile(
    r"^(?P<label>.+?):\s*"
    r"(?P<current>\d+(?:\.\d+)?)%\s*\((?P<current_end>\d+)/(?P<current_start>\d+)\)\s*"
    r"vs\s*(?P<previous>\d+(?:\.\d+)?)%\s*\((?P<previous_end>\d+)/(?P<previous_start>\d+)\)\s*"
    r"\((?P<delta>[+-]?\d+(?:\.\d+)?)\s*(?:pp|%)\)\.?$",
    re.IGNORECASE,
)
CONVERSION_WITHOUT_DELTA_PATTERN = re.compile(
    r"^(?P<label>.+?):\s*"
    r"(?P<current>\d+(?:\.\d+)?)%\s*\((?P<current_end>\d+)/(?P<current_start>\d+)\)\s*"
    r"vs\s*(?P<previous>\d+(?:\.\d+)?)%\s*\((?P<previous_end>\d+)/(?P<previous_start>\d+)\)\.?$",
    re.IGNORECASE,
)
VALUE_DELTA_PATTERN = re.compile(
    r"^(?P<label>.+?):\s*"
    r"(?P<latest>[-+]?\d+(?:\.\d+)?)\s*vs\s*(?P<previous>[-+]?\d+(?:\.\d+)?)\s*"
    r"\((?P<delta>[+-]?\d+(?:\.\d+)?)%\s*WoW\)\.?$",
    re.IGNORECASE,
)
ALL_CHART_METADATA_PATTERN = re.compile(
    r"_Change:_\s*(?P<change>[^|]+)\s*\|\s*"
    r"_Latest:_\s*(?P<latest>[^|]+)\s*\|\s*"
    r"_Previous:_\s*(?P<previous>[^|]+)\s*\|\s*"
    r"_Type:_\s*(?P<chart_type>[^|]+)",
    re.IGNORECASE,
)
RELEASE_VERSION_PATTERN = re.compile(r"\bv?(?P<version>\d+\.\d+\.\d+)\b")
TEAM_COLON_PREFIX_PATTERN = re.compile(
    r"^\s*(?:product(?: analyst| analytics| design)?|product/support|support/product|data(?: team| analyst)?|"
    r"data/analyst|engineering|"
    r"growth|support|pm|design|marketing|ops|research)\s*:\s*",
    re.IGNORECASE,
)
TEAM_TO_PREFIX_PATTERN = re.compile(
    r"^\s*(?:product(?: analyst| analytics| design)?|product/support|support/product|data(?: team| analyst)?|"
    r"data/analyst|engineering|"
    r"growth|support|pm|design|marketing|ops|research)\s+to\s+",
    re.IGNORECASE,
)
OWNER_SEGMENT_PATTERN = re.compile(r"\s*\|?\s*\(?\bOwner:\s*[^|).;]+[).;]?\s*", re.IGNORECASE)
ACTION_PREFIX_PATTERN = re.compile(r"^\s*[*_]*(?:next step|action)[*_]*\s*:\s*", re.IGNORECASE)
THEME_STOPWORDS = {
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
    "insight",
    "into",
    "is",
    "it",
    "its",
    "may",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "was",
    "we",
    "with",
    "action",
    "evidence",
}


class SlackWebhookClient:
    def __init__(self, webhook_url: str, channel: Optional[str] = None) -> None:
        self.webhook_url = webhook_url
        self.channel = channel

    def post_payload(self, payload: Dict[str, Any]) -> None:
        body = dict(payload or {})
        if self.channel and not body.get("channel"):
            body["channel"] = self.channel
        response = requests.post(self.webhook_url, json=body, timeout=20)
        response.raise_for_status()

    def post_report(self, text: str, blocks: List[Dict[str, Any]]) -> None:
        payload: Dict[str, Any] = {"text": text, "blocks": blocks}
        self.post_payload(payload)


def build_weekly_blocks(
    headline: str,
    kpi_status: str,
    top_movers: List[str],
    explanations: List[str],
    actions: List[str],
    supplemental_diagnostics: Optional[List[str]] = None,
    ios_release_context: Optional[Dict[str, Any]] = None,
    all_charts: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    date_str = datetime.utcnow().strftime("%b %d, %Y")
    release_dates = _build_release_date_lookup(ios_release_context)
    key_metrics = _build_key_metrics(kpi_status, top_movers)
    summary_candidates = [kpi_status] + key_metrics
    executive_summary_bullets = _build_executive_summary_bullets(
        headline=headline,
        summary_candidates=summary_candidates,
        release_dates=release_dates,
    )
    key_metrics = [_annotate_release_mentions(item, release_dates) for item in key_metrics]
    insights_and_actions = _merge_insights_with_actions(
        explanations=explanations,
        actions=actions,
        release_dates=release_dates,
    )
    top_mover_blocks = _build_top_mover_blocks(key_metrics)
    all_chart_items = [str(item).strip() for item in (all_charts or []) if str(item).strip()]
    all_chart_blocks = _build_all_chart_blocks(all_chart_items)
    blocks: List[Dict[str, Any]] = [
        _header_block(f"{REPORT_TITLE} - {date_str}"),
        _context_block(METADATA_SUBTITLE),
        _header_block("Executive Summary"),
    ]
    summary_lines = executive_summary_bullets[:3] or ["No executive summary generated this week."]
    for summary_line in summary_lines:
        blocks.append(_section_block(f"{BULLET_GLYPH} {summary_line}"))

    blocks.extend(
        [
            {"type": "divider"},
            _header_block("Top Movers"),
        ]
    )
    if top_mover_blocks:
        blocks.extend(top_mover_blocks[:MAX_TOP_MOVERS])
    else:
        blocks.append(_section_block("No core chart movers available."))

    blocks.append(_header_block("Insights & Actions"))
    if insights_and_actions:
        for item in insights_and_actions[:MAX_ACTIONS]:
            blocks.append(_section_block(item))
    else:
        blocks.append(_section_block("No grounded insights or actions were generated this week."))

    blocks.extend(
        [
            {"type": "divider"},
            _header_block("All Charts"),
        ]
    )
    if all_chart_blocks:
        blocks.extend(all_chart_blocks)
    else:
        blocks.append(_section_block("No chart query results available this run."))
    return blocks


def _header_block(text: str) -> Dict[str, Any]:
    title = str(text or "").strip() or "Report Section"
    return {
        "type": "header",
        "text": {
            "type": "plain_text",
            "text": _truncate_text(title, 150),
            "emoji": True,
        },
    }


def _context_block(text: str) -> Dict[str, Any]:
    return {
        "type": "context",
        "elements": [{"type": "mrkdwn", "text": _truncate_text(str(text or "").strip(), MAX_SECTION_TEXT_CHARS)}],
    }


def _section_block(text: str) -> Dict[str, Any]:
    return {
        "type": "section",
        "text": {"type": "mrkdwn", "text": _truncate_text(str(text or "").strip(), MAX_SECTION_TEXT_CHARS)},
    }


def _build_top_mover_blocks(top_movers: List[str]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for line in top_movers:
        parsed = _parse_top_mover(str(line).strip())
        text_lines = [
            f"*{parsed['title']}*",
            f"*Change:* {parsed['change']}",
            f"*Latest:* {parsed['latest']}",
            f"*Previous:* {parsed['previous']}",
        ]
        if parsed["chart_url"]:
            text_lines.append(f"<{parsed['chart_url']}|chart>")
        blocks.append(_section_block("\n".join(text_lines)))
    return blocks


def _build_all_chart_blocks(all_chart_items: List[str]) -> List[Dict[str, Any]]:
    blocks: List[Dict[str, Any]] = []
    for item in all_chart_items:
        parsed = _parse_all_chart_line(item)
        text_lines = [f"*{parsed['title']}*"]
        meta_line = (
            f"_Change:_ {parsed['change']} | "
            f"_Latest:_ {parsed['latest']} | "
            f"_Previous:_ {parsed['previous']} | "
            f"_Type:_ {parsed['chart_type']}"
        )
        if parsed["chart_url"]:
            meta_line = f"{meta_line} | <{parsed['chart_url']}|chart>"
        text_lines.append(meta_line)
        blocks.append(_section_block("\n".join(text_lines)))
    return blocks


def _parse_top_mover(line: str) -> Dict[str, str]:
    raw = str(line or "").strip()
    chart_url = _extract_first_chart_url(raw)
    normalized = SLACK_LINK_PATTERN.sub("", raw)
    normalized = INLINE_REFERENCE_PATTERN.sub(lambda match: match.group("label").strip(), normalized)
    normalized = PAREN_URL_PATTERN.sub("", normalized)
    normalized = BARE_URL_PATTERN.sub("", normalized)
    normalized = re.sub(r"\(\s*\)", "", normalized)
    normalized = normalized.rstrip(".").strip()
    normalized = re.sub(r"\s{2,}", " ", normalized)

    conversion_match = CONVERSION_SNIPPET_PATTERN.match(normalized)
    if conversion_match:
        delta = _normalize_change_token(conversion_match.group("delta"), suffix="%")
        return {
            "title": conversion_match.group("label").strip(),
            "change": _change_with_glyph(delta),
            "latest": (
                f"{conversion_match.group('current')}% "
                f"({conversion_match.group('current_end')}/{conversion_match.group('current_start')})"
            ),
            "previous": (
                f"{conversion_match.group('previous')}% "
                f"({conversion_match.group('previous_end')}/{conversion_match.group('previous_start')})"
            ),
            "chart_url": chart_url,
        }

    conversion_no_delta_match = CONVERSION_WITHOUT_DELTA_PATTERN.match(normalized)
    if conversion_no_delta_match:
        current = float(conversion_no_delta_match.group("current"))
        previous = float(conversion_no_delta_match.group("previous"))
        change = "N/A" if previous == 0 else f"{((current - previous) / previous) * 100.0:+.2f}%"
        return {
            "title": conversion_no_delta_match.group("label").strip(),
            "change": _change_with_glyph(change),
            "latest": (
                f"{conversion_no_delta_match.group('current')}% "
                f"({conversion_no_delta_match.group('current_end')}/{conversion_no_delta_match.group('current_start')})"
            ),
            "previous": (
                f"{conversion_no_delta_match.group('previous')}% "
                f"({conversion_no_delta_match.group('previous_end')}/{conversion_no_delta_match.group('previous_start')})"
            ),
            "chart_url": chart_url,
        }

    value_delta_match = VALUE_DELTA_PATTERN.match(normalized)
    if value_delta_match:
        delta = _normalize_change_token(value_delta_match.group("delta"), suffix="%")
        return {
            "title": value_delta_match.group("label").strip(),
            "change": _change_with_glyph(delta),
            "latest": value_delta_match.group("latest"),
            "previous": value_delta_match.group("previous"),
            "chart_url": chart_url,
        }

    fallback_title = normalized or "Metric update"
    return {
        "title": fallback_title,
        "change": _change_with_glyph("N/A"),
        "latest": "N/A",
        "previous": "N/A",
        "chart_url": chart_url,
    }


def _parse_all_chart_line(line: str) -> Dict[str, str]:
    text = str(line or "").strip()
    rows = [row.strip() for row in text.splitlines() if row.strip()]
    title_line = rows[0] if rows else "Unknown chart"
    metadata_line = rows[1] if len(rows) >= 2 else ""

    title, chart_url = _extract_title_and_link(title_line)
    if not title:
        title = "Unknown chart"

    metadata_match = ALL_CHART_METADATA_PATTERN.search(metadata_line)
    if metadata_match:
        return {
            "title": title,
            "change": _change_with_glyph(metadata_match.group("change").strip()),
            "latest": metadata_match.group("latest").strip(),
            "previous": metadata_match.group("previous").strip(),
            "chart_type": metadata_match.group("chart_type").strip(),
            "chart_url": chart_url,
        }

    return {
        "title": title,
        "change": _change_with_glyph("N/A"),
        "latest": "N/A",
        "previous": "N/A",
        "chart_type": "unknown",
        "chart_url": chart_url,
    }


def _extract_title_and_link(text: str) -> tuple[str, str]:
    raw = str(text or "").strip()
    link_match = SLACK_LINK_PATTERN.search(raw)
    if link_match:
        title = (link_match.group("label") or "").strip() or "Chart"
        return title, link_match.group("url").strip()

    url = _extract_first_chart_url(raw)
    stripped = _strip_chart_links(raw)
    stripped = stripped.strip("* ").strip()
    return stripped, url


def _extract_first_chart_url(text: str) -> str:
    content = str(text or "")
    slack_match = SLACK_LINK_PATTERN.search(content)
    if slack_match:
        return slack_match.group("url").strip()

    trailing_match = TRAILING_REFERENCE_PATTERN.match(content.strip())
    if trailing_match:
        return trailing_match.group("url").strip()

    inline_match = INLINE_REFERENCE_PATTERN.search(content)
    if inline_match:
        return inline_match.group("url").strip()

    bare_match = BARE_URL_PATTERN.search(content)
    if bare_match:
        return bare_match.group("url").strip().rstrip(").,;:!?")
    return ""


def _strip_chart_links(text: str) -> str:
    content = str(text or "")
    without_slack_links = SLACK_LINK_PATTERN.sub(lambda match: (match.group("label") or "").strip(), content)
    without_inline = INLINE_REFERENCE_PATTERN.sub(lambda match: match.group("label").strip(), without_slack_links)
    without_paren_urls = PAREN_URL_PATTERN.sub("", without_inline)
    without_bare_urls = BARE_URL_PATTERN.sub("", without_paren_urls)
    without_empty_parens = re.sub(r"\(\s*\)", "", without_bare_urls)
    return re.sub(r"\s{2,}", " ", without_empty_parens).strip()


def _normalize_change_token(value: str, suffix: str = "") -> str:
    token = str(value or "").strip()
    if not token:
        return "N/A"
    if token.lower() == "n/a":
        return "N/A"
    try:
        number = float(token.replace("%", ""))
    except ValueError:
        return token
    rendered = f"{number:+.2f}"
    if suffix and not rendered.endswith(suffix):
        return f"{rendered}{suffix}"
    return rendered


def _change_with_glyph(change_value: str) -> str:
    token = str(change_value or "").strip()
    if not token or token.lower() == "n/a":
        return f"{CHANGE_NEUTRAL_GLYPH} N/A"
    normalized = _normalize_change_token(token, suffix="%" if "%" in token or re.match(r"^[+-]?\d+(\.\d+)?$", token) else "")
    try:
        numeric = float(normalized.replace("%", ""))
    except ValueError:
        return f"{CHANGE_NEUTRAL_GLYPH} {normalized}"
    if abs(numeric) < 1e-9:
        return f"{CHANGE_NEUTRAL_GLYPH} {normalized}"
    if numeric > 0:
        return f"{CHANGE_UP_GLYPH} {normalized}"
    return f"{CHANGE_DOWN_GLYPH} {normalized}"


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    safe_limit = max(limit - 3, 1)
    return text[:safe_limit].rstrip() + "..."


def _format_slack_line(text: str, chart_tag_links: bool = False) -> str:
    line = str(text).strip()
    if not line:
        return line

    if chart_tag_links:
        if "\n" in line:
            formatted_lines: List[str] = []
            for raw_line in line.splitlines():
                if not raw_line.strip():
                    continue
                indent_match = re.match(r"^\s*", raw_line)
                indent = indent_match.group(0) if indent_match else ""
                formatted_line = _format_line_with_chart_tags(raw_line.strip())
                if formatted_line:
                    formatted_lines.append(f"{indent}{formatted_line}")
            return "\n".join(formatted_lines)
        return _format_line_with_chart_tags(line)

    if "<http" in line:
        return line

    trailing_match = TRAILING_REFERENCE_PATTERN.match(line)
    if trailing_match:
        prefix = trailing_match.group("prefix").strip().rstrip(".")
        url = trailing_match.group("url").strip()
        suffix = trailing_match.group("suffix") or ""
        if prefix:
            chart_label = prefix
            statement = prefix
            sentence_parts = re.split(r"(?<=[.!?])\s+", prefix)
            if len(sentence_parts) >= 2:
                potential_label = sentence_parts[-1].strip()
                if len(WORD_TOKEN_PATTERN.findall(potential_label)) >= 2:
                    chart_label = potential_label
                    statement = " ".join(sentence_parts[:-1]).strip()
            elif ":" in prefix:
                head, tail = prefix.rsplit(":", 1)
                if len(WORD_TOKEN_PATTERN.findall(tail)) >= 2:
                    chart_label = tail.strip()
                    statement = f"{head.strip()}:"

            short_label = _short_link_label(chart_label)
            if statement:
                return f"{statement} <{url}|{short_label}>{suffix}"
            return f"<{url}|{short_label}>{suffix}"

    def _replace_inline(match: re.Match[str]) -> str:
        label = match.group("label").strip().strip("'\"").rstrip(".")
        url = match.group("url").strip()
        if not label:
            return f"<{url}|chart>"
        return f"<{url}|{_short_link_label(label)}>"

    return INLINE_REFERENCE_PATTERN.sub(_replace_inline, line)


def _format_line_with_chart_tags(text: str) -> str:
    if "http://" not in text and "https://" not in text and "<http" not in text:
        return text

    links: List[str] = []

    def _capture_link(url: str) -> str:
        candidate = str(url).strip().rstrip(").,;:!?")
        if candidate and candidate not in links:
            links.append(candidate)
        return candidate

    segments: List[str] = []
    last_index = 0
    for match in SLACK_LINK_PATTERN.finditer(text):
        segments.append(text[last_index : match.start()])
        _capture_link(match.group("url"))
        label = (match.group("label") or "").strip()
        tail = text[match.end() :]
        is_trailing_token = not re.search(r"[A-Za-z0-9]", tail)
        segments.append("" if is_trailing_token else label)
        last_index = match.end()
    line = "".join(segments) + text[last_index:]

    trailing_match = TRAILING_REFERENCE_PATTERN.match(line)
    if trailing_match:
        prefix = trailing_match.group("prefix").strip().rstrip(".")
        suffix = trailing_match.group("suffix") or ""
        _capture_link(trailing_match.group("url"))
        statement = prefix
        sentence_parts = re.split(r"(?<=[.!?])\s+", prefix)
        if len(sentence_parts) >= 2:
            potential_label = sentence_parts[-1].strip()
            label_words = WORD_TOKEN_PATTERN.findall(potential_label)
            if 0 < len(label_words) <= 4 and not SUMMARY_NUMERIC_HINT_PATTERN.search(potential_label):
                statement = " ".join(sentence_parts[:-1]).strip()
        line = f"{statement}{suffix}".strip()

    source_line = line

    def _replace_inline(match: re.Match[str]) -> str:
        _capture_link(match.group("url"))
        label = match.group("label").strip()
        tail = source_line[match.end() :]
        is_trailing_token = not re.search(r"[A-Za-z0-9]", tail)
        label_words = WORD_TOKEN_PATTERN.findall(label)
        looks_like_chart_label = 0 < len(label_words) <= 4 and not SUMMARY_NUMERIC_HINT_PATTERN.search(label)
        return "" if is_trailing_token and looks_like_chart_label else label

    line = INLINE_REFERENCE_PATTERN.sub(_replace_inline, line)

    def _remove_paren_url(match: re.Match[str]) -> str:
        _capture_link(match.group("url"))
        return ""

    line = PAREN_URL_PATTERN.sub(_remove_paren_url, line)

    def _remove_bare_url(match: re.Match[str]) -> str:
        _capture_link(match.group("url"))
        return ""

    line = BARE_URL_PATTERN.sub(_remove_bare_url, line)
    line = re.sub(r"\(\s*\)", "", line)
    line = re.sub(r"\s+([.,;:!?])", r"\1", line)
    line = re.sub(r"\s{2,}", " ", line).strip()

    if not links:
        return line

    chart_tags = " ".join(f"(<{url}|chart>)" for url in links)
    if not line:
        return chart_tags
    return f"{line} {chart_tags}"


def _clean_explanation(explanation: str, release_dates: Optional[Dict[str, str]] = None) -> str:
    text = str(explanation).strip()
    if not text:
        return ""

    parts = [part.strip() for part in text.splitlines() if part.strip()]
    claim = ""
    evidence = ""
    for part in parts:
        if part.lower().startswith("*claim:*") or part.lower().startswith("claim:"):
            claim = CLAIM_PATTERN.sub("", part).strip()
            continue
        if part.lower().startswith("*evidence:*") or part.lower().startswith("evidence:"):
            evidence = EVIDENCE_PATTERN.sub("", part).strip()
            continue

    if not claim:
        claim = CLAIM_PATTERN.sub("", text)
        claim = EVIDENCE_PATTERN.sub("", claim)
        claim = claim.replace("\n", " ").strip()

    claim = LOW_CONFIDENCE_PREFIX_PATTERN.sub("", claim)
    claim = CONFIDENCE_PREFIX_PATTERN.sub("", claim)
    claim = GROUNDED_PREFIX_PATTERN.sub("", claim)
    claim = INSIGHT_PREFIX_PATTERN.sub("", claim)
    claim = ABSOLUTE_CONTEXT_PATTERN.sub("", claim)
    claim = ADDITIONAL_CONTEXT_PATTERN.sub(" Additional context: ", claim)
    claim = re.sub(r"\s{2,}", " ", claim).strip()

    if evidence:
        evidence = CONFIDENCE_PREFIX_PATTERN.sub("", evidence)
        evidence = GROUNDED_PREFIX_PATTERN.sub("", evidence)
        evidence = INSIGHT_PREFIX_PATTERN.sub("", evidence)
        evidence = ABSOLUTE_CONTEXT_PATTERN.sub("", evidence)
        evidence = re.sub(r"\s{2,}", " ", evidence).strip()
        if evidence:
            claim = f"{claim} Evidence: {evidence}"

    claim = _annotate_release_mentions(claim, release_dates)
    return _format_slack_line(claim)


def _clean_action(action: str, release_dates: Optional[Dict[str, str]] = None) -> str:
    text = str(action).strip()
    if not text:
        return ""

    text = PRIORITY_PIPE_PATTERN.sub("", text)
    text = PRIORITY_SENTENCE_PATTERN.sub("", text)
    text = EXPECTED_IMPACT_PIPE_PATTERN.sub("", text)
    text = EXPECTED_IMPACT_SENTENCE_PATTERN.sub("", text)
    text = ABSOLUTE_CONTEXT_PATTERN.sub("", text)
    text = ADDITIONAL_CONTEXT_PATTERN.sub(" Additional context: ", text)
    text = OWNER_SEGMENT_PATTERN.sub(" ", text)
    text = re.sub(r"^\s*[*•-]\s*", "", text)
    text = ACTION_PREFIX_PATTERN.sub("", text)
    text = TEAM_COLON_PREFIX_PATTERN.sub("", text)
    text = TEAM_TO_PREFIX_PATTERN.sub("", text)
    text = text.rstrip("| ").strip()
    text = re.sub(r"\s{2,}", " ", text).strip()

    segments = [segment.strip() for segment in re.split(r"\s+\|\s+", text) if segment.strip()]
    if not segments:
        return ""
    primary = ACTION_PREFIX_PATTERN.sub("", segments[0]).strip()
    primary = TEAM_COLON_PREFIX_PATTERN.sub("", primary).strip()
    primary = TEAM_TO_PREFIX_PATTERN.sub("", primary).strip()
    primary = re.sub(r"\s{2,}", " ", primary).strip(" -")
    if primary and primary[0].islower():
        primary = primary[0].upper() + primary[1:]
    primary = _annotate_release_mentions(primary, release_dates)
    return _format_slack_line(primary)


def _merge_insights_with_actions(
    explanations: List[str],
    actions: List[str],
    release_dates: Optional[Dict[str, str]] = None,
) -> List[str]:
    cleaned_explanations = [
        _clean_explanation(item, release_dates=release_dates)
        for item in explanations
        if str(item).strip()
    ]
    cleaned_explanations = [item for item in cleaned_explanations if item][:MAX_EXPLANATIONS]
    cleaned_actions = [
        _clean_action(item, release_dates=release_dates)
        for item in actions
        if str(item).strip()
    ]
    cleaned_actions = [item for item in cleaned_actions if item][:MAX_ACTIONS]

    if not cleaned_explanations and not cleaned_actions:
        return []

    if cleaned_explanations and cleaned_actions:
        limit = min(len(cleaned_explanations), len(cleaned_actions), MAX_ACTIONS)
    else:
        limit = min(max(len(cleaned_explanations), len(cleaned_actions)), MAX_ACTIONS)
    merged: List[str] = []
    for index in range(limit):
        explanation = (
            cleaned_explanations[index]
            if index < len(cleaned_explanations)
            else "No additional explanation context was generated."
        )
        action = (
            cleaned_actions[index]
            if index < len(cleaned_actions)
            else "Define a verification step for this metric movement."
        )
        theme = _infer_insight_theme(explanation, action)
        merged.append(f"*{theme}*\n{BULLET_GLYPH} _Insight:_ {explanation}\n{BULLET_GLYPH} _Action:_ {action}")
    return merged


def _build_key_metrics(kpi_status: str, top_movers: List[str]) -> List[str]:
    candidates = list(top_movers or [])
    if not candidates:
        candidates = [kpi_status]
    selected: List[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        raw = str(candidate).strip()
        if not raw:
            continue
        marker = _strip_slack_link_markup(raw).lower()
        if marker in seen:
            continue
        seen.add(marker)
        selected.append(raw)
        if len(selected) >= MAX_TOP_MOVERS:
            break
    return selected or [kpi_status]


def _build_executive_summary_bullets(
    headline: str,
    summary_candidates: List[str],
    release_dates: Optional[Dict[str, str]] = None,
) -> List[str]:
    summary = _ensure_numeric_executive_summary(headline, summary_candidates)
    summary = _annotate_release_mentions(summary, release_dates)
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", summary) if part.strip()]
    bullets = parts[:3]
    if bullets:
        return bullets
    fallback = summary.strip()
    return [fallback] if fallback else ["No executive summary generated this week."]


def _strip_slack_link_markup(text: str) -> str:
    return SLACK_LINK_LABEL_PATTERN.sub(lambda match: match.group(1), text)


def _metric_snippet_for_summary(metric_line: str) -> str:
    cleaned = _strip_slack_link_markup(str(metric_line).strip())
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip()
    cleaned = NORTH_STAR_PREFIX_PATTERN.sub("", cleaned)
    trailing_label_match = re.search(
        r"\.\s+([A-Za-z][A-Za-z0-9'/-]*(?:\s+[A-Za-z0-9'/-]+){0,3})$",
        cleaned,
    )
    if trailing_label_match:
        tail = trailing_label_match.group(1).strip()
        # Strip trailing link labels left behind after removing Slack link markup.
        if len(WORD_TOKEN_PATTERN.findall(tail)) <= 4 and not SUMMARY_NUMERIC_HINT_PATTERN.search(tail):
            cleaned = cleaned[: trailing_label_match.start()].rstrip()
    return cleaned.rstrip(".")


def _summary_metric_label(label: str) -> str:
    candidate = str(label).strip()
    if ":" in candidate:
        candidate = candidate.split(":", 1)[0].strip()
    elif "->" in candidate:
        candidate = candidate.split("->")[-1].strip()

    words = WORD_TOKEN_PATTERN.findall(candidate)
    if not words:
        return "Key metric"
    if len(words) <= 4:
        return " ".join(words)
    return " ".join(words[-4:])


def _to_concise_signal(snippet: str) -> str:
    compact = str(snippet).strip().rstrip(".")
    match = CONVERSION_SNIPPET_PATTERN.match(compact)
    if not match:
        return f"{compact}."

    label = _summary_metric_label(match.group("label"))
    current = match.group("current")
    previous = match.group("previous")
    current_end = match.group("current_end")
    current_start = match.group("current_start")
    current_float = float(current)
    previous_float = float(previous)
    raw_delta = current_float - previous_float
    relative_delta = (
        ((current_float - previous_float) / previous_float) * 100.0
        if previous_float != 0
        else None
    )
    verb = "rose" if raw_delta >= 0 else "fell"
    delta_text = f"{relative_delta:+.2f}%" if relative_delta is not None else "N/A"
    return (
        f"{label} {verb} from {previous}% to {current}% "
        f"({delta_text}, {current_end}/{current_start})."
    )


def _ensure_numeric_executive_summary(headline: str, key_metrics: List[str]) -> str:
    base = str(headline).strip()
    if not base:
        base = "No executive summary generated this week."
    numeric_hits = len(SUMMARY_NUMERIC_HINT_PATTERN.findall(base))

    snippets: List[str] = []
    metric_candidates = key_metrics if numeric_hits == 0 else (key_metrics[1:] + key_metrics[:1])
    candidate_snippets: List[str] = []
    for metric in metric_candidates:
        snippet = _metric_snippet_for_summary(metric)
        if not snippet:
            continue
        if not SUMMARY_NUMERIC_HINT_PATTERN.search(snippet):
            continue
        if snippet.lower() in base.lower():
            continue
        candidate_snippets.append(snippet)

    if numeric_hits == 0:
        snippets = candidate_snippets[:2]
    else:
        snippets = sorted(
            candidate_snippets,
            key=_max_percent_magnitude,
            reverse=True,
        )[:1]

    if not snippets:
        return base

    base = base.rstrip(". ")
    concise_signals = [_to_concise_signal(snippet) for snippet in snippets if snippet]
    if not concise_signals:
        return f"{base}."
    return f"{base}. {' '.join(concise_signals)}"


def _max_percent_magnitude(text: str) -> float:
    values = [abs(float(match.group(1))) for match in PERCENT_VALUE_PATTERN.finditer(text)]
    return max(values) if values else 0.0


def _short_link_label(label: str, max_words: int = 3) -> str:
    candidate = str(label).strip().strip("'\"")
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


def _build_release_date_lookup(ios_release_context: Optional[Dict[str, Any]]) -> Dict[str, str]:
    if not isinstance(ios_release_context, dict):
        return {}

    lookup: Dict[str, str] = {}
    sources = [
        ios_release_context.get("recent_releases_with_notes"),
        ios_release_context.get("recent_release_notes"),
        ios_release_context.get("recent_releases"),
    ]
    for source in sources:
        if not isinstance(source, list):
            continue
        for entry in source:
            if not isinstance(entry, dict):
                continue
            version = str(entry.get("version") or "").strip()
            if not version:
                continue
            release_date = (
                str(entry.get("curated_release_date") or "").strip()
                or str(entry.get("release_date") or "").strip()
            )
            formatted = _format_release_date_for_text(release_date)
            if not formatted:
                continue
            normalized = version.lower().lstrip("v")
            lookup[normalized] = formatted
    return lookup


def _format_release_date_for_text(value: str) -> str:
    raw = str(value).strip()
    if not raw:
        return ""
    if re.match(r"^\d{4}-\d{2}-\d{2}$", raw):
        try:
            parsed = datetime.strptime(raw, "%Y-%m-%d")
            return f"{parsed:%b} {parsed.day}, {parsed.year}"
        except ValueError:
            return raw
    if re.match(r"^\d{4}-\d{2}-\d{2}T", raw):
        try:
            normalized = raw.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return f"{parsed:%b} {parsed.day}, {parsed.year}"
        except ValueError:
            return raw
    return raw


def _annotate_release_mentions(text: str, release_dates: Optional[Dict[str, str]] = None) -> str:
    content = str(text or "").strip()
    if not content:
        return content
    dates = release_dates or {}
    if not dates:
        return content

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0)
        version = str(match.group("version") or "").lower().lstrip("v")
        release_date = dates.get(version)
        if not release_date:
            return token
        tail = content[match.end() : match.end() + 40].lower()
        if "(released " in tail:
            return token
        return f"{token} (released {release_date})"

    return RELEASE_VERSION_PATTERN.sub(_replace, content)


def _infer_insight_theme(explanation: str, action: str) -> str:
    insight_text = str(explanation or "").lower()
    action_text = str(action or "").lower()
    text = f"{insight_text} {action_text}".lower()
    rules = [
        (r"\bincomplete|bucket|reliability|confidence\b", "Data Reliability"),
        (r"\bcancel|subscription|trial\b", "Cancellation Friction"),
        (r"\brepeat\b|\bafter activation\b", "Repeat Behavior"),
        (r"\bactivation\b|\bnorth star\b|\bkpi\b", "Activation Shift"),
        (r"\bdent\b", "DENT Conversion"),
        (r"\bonboarding\b", "Onboarding Friction"),
        (r"\bcalendar\b", "Calendar Connect"),
        (r"\bhouse appliance\b|\bappliance\b", "Appliance Setup"),
        (r"\bfeedback\b", "User Feedback"),
    ]
    for pattern, theme in rules:
        if re.search(pattern, insight_text):
            return theme
    for pattern, theme in rules:
        if re.search(pattern, action_text):
            return theme
    for pattern, theme in rules:
        if re.search(pattern, text):
            return theme

    words: List[str] = []
    seen = set()
    for token in WORD_TOKEN_PATTERN.findall(text):
        lowered = token.lower()
        if lowered in THEME_STOPWORDS or lowered.isdigit():
            continue
        if lowered in seen:
            continue
        seen.add(lowered)
        words.append("DENT" if lowered == "dent" else lowered.capitalize())
        if len(words) >= 3:
            break
    if len(words) >= 2:
        return " ".join(words[:3])
    return "Metric Follow-up"
