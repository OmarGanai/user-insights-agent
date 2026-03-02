from datetime import datetime, timedelta, timezone
import re
from typing import Any, Dict, List, Optional

import requests

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,2}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)\d{3}[-.\s]?\d{4}\b")


class TypeformClient:
    def __init__(self, token: Optional[str], form_id: Optional[str]) -> None:
        self.token = token
        self.form_id = form_id
        self.session = requests.Session()
        if token:
            self.session.headers.update({"Authorization": f"Bearer {token}"})

    def fetch_recent_responses(self, days: int = 7) -> List[Dict[str, Any]]:
        if not self.token or not self.form_id:
            return []

        since = datetime.now(timezone.utc) - timedelta(days=days)
        since_iso = _format_utc_timestamp(since)
        url = f"https://api.typeform.com/forms/{self.form_id}/responses"
        page_size = 200

        def fetch_page(after_token: Optional[str], include_since: bool) -> requests.Response:
            params: Dict[str, Any] = {
                "page_size": page_size,
                "response_type": "completed",
            }
            if include_since:
                params["since"] = since_iso
            if after_token:
                params["after"] = after_token
            return self.session.get(url, params=params, timeout=30)

        try:
            first = fetch_page(after_token=None, include_since=True)
            use_since = True
            if first.status_code == 400:
                # Some forms/tokens reject the since filter. Retry without it,
                # then enforce lookback client-side.
                print(
                    "Warning: Typeform returned 400 for since filter. "
                    f"Body excerpt: {_truncate(first.text)}. Retrying without since."
                )
                first = fetch_page(after_token=None, include_since=False)
                use_since = False
            first.raise_for_status()
        except requests.RequestException as exc:
            # Typeform context is optional; do not fail the full report.
            print(f"Warning: failed to fetch Typeform responses ({exc}). Continuing without feedback context.")
            return []

        all_items = _paginate_items(
            first_page=first.json().get("items", []),
            fetch_page_fn=lambda after: fetch_page(after_token=after, include_since=use_since),
            page_size=page_size,
        )
        field_lookup: Dict[str, Dict[str, str]] = {}
        try:
            field_lookup = self._fetch_form_field_lookup()
        except requests.RequestException as exc:
            # Form metadata helps context but should not block feedback ingestion.
            print(f"Warning: failed to fetch Typeform form fields ({exc}). Continuing without question metadata.")

        results: List[Dict[str, Any]] = []
        for item in all_items:
            submitted_at = item.get("submitted_at")
            submitted_dt = _parse_typeform_datetime(submitted_at)
            if submitted_dt and submitted_dt < since:
                continue

            answers = item.get("answers", [])
            answer_details = _extract_text_answer_details(answers, field_lookup)
            text_answers = [str(detail["text"]) for detail in answer_details if detail.get("text")]
            if not text_answers:
                continue
            results.append(
                {
                    "submitted_at": submitted_at,
                    "answers": text_answers,
                    "answer_details": answer_details,
                }
            )

        return results

    def _fetch_form_field_lookup(self) -> Dict[str, Dict[str, str]]:
        if not self.form_id:
            return {}
        url = f"https://api.typeform.com/forms/{self.form_id}"
        resp = self.session.get(url, timeout=30)
        resp.raise_for_status()
        payload = resp.json()
        fields = payload.get("fields") or []
        return _build_field_lookup(fields)


def _extract_text_answers(answers: List[Dict[str, Any]]) -> List[str]:
    return [str(detail["text"]) for detail in _extract_text_answer_details(answers, {}) if detail.get("text")]


def _extract_text_answer_details(
    answers: List[Dict[str, Any]],
    field_lookup: Dict[str, Dict[str, str]],
) -> List[Dict[str, str]]:
    details: List[Dict[str, str]] = []
    for answer in answers:
        if not isinstance(answer, dict):
            continue
        # Typeform answer object can contain one of several fields.
        candidates: List[str] = []
        if "text" in answer and isinstance(answer["text"], str):
            candidates.append(answer["text"])
        elif "choice" in answer and isinstance(answer["choice"], dict):
            label = answer["choice"].get("label")
            if label:
                candidates.append(str(label))
            other = answer["choice"].get("other")
            if other:
                candidates.append(str(other))
        elif "choices" in answer and isinstance(answer["choices"], dict):
            labels = answer["choices"].get("labels") or []
            candidates.extend([str(label) for label in labels if label])
            other_values = answer["choices"].get("other")
            if isinstance(other_values, list):
                candidates.extend([str(value) for value in other_values if value])
            elif other_values:
                candidates.append(str(other_values))

        field = answer.get("field") if isinstance(answer.get("field"), dict) else {}
        field_ref = str(field.get("ref") or "").strip()
        field_id = str(field.get("id") or "").strip()
        field_type = str(field.get("type") or "").strip()
        answer_type = str(answer.get("type") or "").strip()
        metadata = _resolve_field_metadata(field_ref, field_id, field_lookup)
        question = str(metadata.get("question") or "").strip()
        resolved_field_type = str(metadata.get("field_type") or field_type or "").strip()

        for candidate in candidates:
            sanitized = _sanitize_text_answer(candidate)
            if sanitized:
                detail: Dict[str, str] = {"text": sanitized}
                if question:
                    detail["question"] = question
                if field_ref:
                    detail["field_ref"] = field_ref
                if resolved_field_type:
                    detail["field_type"] = resolved_field_type
                if answer_type:
                    detail["answer_type"] = answer_type
                details.append(detail)
    return details


def _sanitize_text_answer(value: str) -> str:
    text = " ".join(value.split()).strip()
    if not text:
        return ""
    text = EMAIL_PATTERN.sub("[redacted-email]", text)
    text = PHONE_PATTERN.sub("[redacted-phone]", text)
    return text


def _format_utc_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_typeform_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _truncate(value: str, limit: int = 300) -> str:
    compact = " ".join(value.split())
    if len(compact) <= limit:
        return compact
    return compact[:limit] + "..."


def _paginate_items(
    first_page: List[Dict[str, Any]],
    fetch_page_fn,
    page_size: int,
) -> List[Dict[str, Any]]:
    items = list(first_page)
    current_page_items = list(first_page)
    seen_after_tokens = set()

    while True:
        if not current_page_items:
            break
        last_token = current_page_items[-1].get("token")
        if not last_token:
            break
        if last_token in seen_after_tokens:
            break
        if len(current_page_items) < page_size:
            break
        seen_after_tokens.add(last_token)

        resp = fetch_page_fn(last_token)
        if resp.status_code >= 400:
            print(f"Warning: failed to fetch Typeform page after token ({resp.status_code}). Stopping pagination.")
            break
        page_items = resp.json().get("items", [])
        if not page_items:
            break
        items.extend(page_items)
        current_page_items = page_items

    return items


def _resolve_field_metadata(
    field_ref: str,
    field_id: str,
    field_lookup: Dict[str, Dict[str, str]],
) -> Dict[str, str]:
    if field_ref:
        meta = field_lookup.get(f"ref:{field_ref}")
        if meta:
            return meta
    if field_id:
        meta = field_lookup.get(f"id:{field_id}")
        if meta:
            return meta
    return {}


def _build_field_lookup(fields: List[Dict[str, Any]]) -> Dict[str, Dict[str, str]]:
    lookup: Dict[str, Dict[str, str]] = {}
    for field in _iter_form_fields(fields):
        if not isinstance(field, dict):
            continue
        title = str(field.get("title") or "").strip()
        field_type = str(field.get("type") or "").strip()
        metadata = {
            "question": title,
            "field_type": field_type,
        }
        field_ref = str(field.get("ref") or "").strip()
        field_id = str(field.get("id") or "").strip()
        if field_ref:
            lookup[f"ref:{field_ref}"] = metadata
        if field_id:
            lookup[f"id:{field_id}"] = metadata
    return lookup


def _iter_form_fields(fields: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    flattened: List[Dict[str, Any]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        flattened.append(field)
        properties = field.get("properties") if isinstance(field.get("properties"), dict) else {}
        nested = properties.get("fields") if isinstance(properties.get("fields"), list) else []
        if nested:
            flattened.extend(_iter_form_fields(nested))
    return flattened
