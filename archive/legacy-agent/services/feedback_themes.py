from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple


MAX_REPRESENTATIVE_SNIPPETS = 3
MAX_SNIPPET_CHARS = 240
MAX_THEMES = 8

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")
WHITESPACE_PATTERN = re.compile(r"\s+")

THEME_RULES: List[Dict[str, Any]] = [
    {
        "theme_key": "calendar_connection_friction",
        "theme_label": "Calendar connection friction",
        "keywords": [
            "calendar",
            "sync",
            "connect",
            "connection",
            "google calendar",
            "apple calendar",
            "outlook",
        ],
    },
    {
        "theme_key": "signup_onboarding_friction",
        "theme_label": "Signup/onboarding friction",
        "keywords": [
            "signup",
            "sign up",
            "onboarding",
            "getting started",
            "first time",
            "setup",
            "confusing",
            "confused",
            "friction",
        ],
    },
    {
        "theme_key": "dent_creation_friction",
        "theme_label": "DENT creation friction",
        "keywords": [
            "task",
            "event",
            "note",
            "document",
            "create",
            "created",
            "creation",
            "add item",
        ],
    },
    {
        "theme_key": "hive_collaboration",
        "theme_label": "Hive/collaboration experience",
        "keywords": [
            "hive",
            "invite",
            "member",
            "family",
            "share",
            "collabor",
        ],
    },
    {
        "theme_key": "bugs_and_reliability",
        "theme_label": "Bugs and reliability issues",
        "keywords": [
            "bug",
            "crash",
            "error",
            "broken",
            "issue",
            "stuck",
            "freeze",
            "doesn't work",
            "doesnt work",
        ],
    },
    {
        "theme_key": "performance_speed",
        "theme_label": "Performance and speed",
        "keywords": [
            "slow",
            "lag",
            "loading",
            "takes forever",
            "performance",
            "speed",
        ],
    },
    {
        "theme_key": "notifications_reminders",
        "theme_label": "Notifications/reminders",
        "keywords": [
            "notification",
            "notify",
            "reminder",
            "alert",
        ],
    },
    {
        "theme_key": "feature_requests",
        "theme_label": "Feature requests",
        "keywords": [
            "feature",
            "would like",
            "wish",
            "please add",
            "request",
            "missing",
            "need",
        ],
    },
]

OTHER_THEME_KEY = "other_feedback"
OTHER_THEME_LABEL = "Other feedback"


def build_feedback_theme_summary(
    feedback_items: List[Dict[str, Any]],
    max_themes: int = MAX_THEMES,
) -> Dict[str, Any]:
    snippets = _flatten_feedback_snippets(feedback_items)
    if not snippets:
        return {
            "feedback_items_count": len(feedback_items),
            "feedback_snippets_count": 0,
            "theme_count": 0,
            "themes": [],
        }

    aggregates: Dict[str, Dict[str, Any]] = {}
    theme_lookup = {rule["theme_key"]: rule for rule in THEME_RULES}
    for snippet in snippets:
        theme_key, theme_label = _match_theme(snippet)
        bucket = aggregates.setdefault(
            theme_key,
            {
                "theme_key": theme_key,
                "theme_label": theme_label,
                "mention_count": 0,
                "representative_snippets": [],
            },
        )
        bucket["mention_count"] += 1
        representatives = bucket["representative_snippets"]
        if snippet not in representatives and len(representatives) < MAX_REPRESENTATIVE_SNIPPETS:
            representatives.append(snippet)

    ordered = sorted(
        aggregates.values(),
        key=lambda item: (-int(item["mention_count"]), str(item["theme_label"]).lower()),
    )
    selected = ordered[: max(1, max_themes)]

    # Keep theme labels aligned with static rule labels when available.
    normalized_themes: List[Dict[str, Any]] = []
    for item in selected:
        theme_key = str(item["theme_key"])
        fallback = {
            "theme_label": OTHER_THEME_LABEL,
        }
        metadata = theme_lookup.get(theme_key, fallback)
        normalized_themes.append(
            {
                "theme_key": theme_key,
                "theme_label": str(metadata.get("theme_label") or item["theme_label"]),
                "mention_count": int(item["mention_count"]),
                "representative_snippets": list(item["representative_snippets"]),
            }
        )

    return {
        "feedback_items_count": len(feedback_items),
        "feedback_snippets_count": len(snippets),
        "theme_count": len(normalized_themes),
        "themes": normalized_themes,
    }


def _flatten_feedback_snippets(feedback_items: List[Dict[str, Any]]) -> List[str]:
    snippets: List[str] = []
    for item in feedback_items:
        if not isinstance(item, dict):
            continue
        answers = item.get("answers")
        if not isinstance(answers, list):
            continue
        for answer in answers:
            normalized = _sanitize_snippet(str(answer or ""))
            if normalized:
                snippets.append(normalized)
    return snippets


def _sanitize_snippet(value: str) -> str:
    if not value:
        return ""
    text = EMAIL_PATTERN.sub("[redacted-email]", value)
    text = PHONE_PATTERN.sub("[redacted-phone]", text)
    text = WHITESPACE_PATTERN.sub(" ", text).strip()
    if not text:
        return ""
    if len(text) <= MAX_SNIPPET_CHARS:
        return text
    return text[: MAX_SNIPPET_CHARS - 3].rstrip() + "..."


def _match_theme(snippet: str) -> Tuple[str, str]:
    lowered = snippet.lower()
    best_match_key: Optional[str] = None
    best_match_label: Optional[str] = None
    best_score = 0
    for rule in THEME_RULES:
        score = 0
        for keyword in rule["keywords"]:
            if keyword in lowered:
                score += 1
        if score > best_score:
            best_score = score
            best_match_key = str(rule["theme_key"])
            best_match_label = str(rule["theme_label"])

    if best_match_key and best_match_label:
        return best_match_key, best_match_label
    return OTHER_THEME_KEY, OTHER_THEME_LABEL
