from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPORAL_MEMORY_PATH = REPO_ROOT / "tmp" / "weekly-report-memory.json"
TEMPORAL_MEMORY_SCHEMA_VERSION = 1


def load_temporal_memory(memory_path: Path = DEFAULT_TEMPORAL_MEMORY_PATH) -> Dict[str, Any]:
    payload = _default_memory_payload()
    try:
        raw = memory_path.read_text(encoding="utf-8")
    except OSError:
        return payload

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        payload["load_error"] = "invalid_json"
        return payload

    if not isinstance(parsed, dict):
        payload["load_error"] = "invalid_shape"
        return payload

    payload["schema_version"] = int(parsed.get("schema_version") or TEMPORAL_MEMORY_SCHEMA_VERSION)
    payload["last_updated_utc"] = str(parsed.get("last_updated_utc") or "")
    payload["latest_report"] = _normalize_report_snapshot(parsed.get("latest_report"))
    payload["previous_report"] = _normalize_report_snapshot(parsed.get("previous_report"))
    return payload


def build_temporal_snapshot(
    headline: str,
    kpi_status: str,
    key_changes: List[str],
    explanations: List[str],
    actions: List[str],
    core_results: List[Dict[str, Any]],
    generated_at_utc: Optional[str] = None,
) -> Dict[str, Any]:
    timestamp = generated_at_utc or _format_utc(datetime.now(timezone.utc))
    return {
        "generated_at_utc": timestamp,
        "headline": str(headline).strip(),
        "kpi_status": str(kpi_status).strip(),
        "key_changes": _string_list(key_changes, limit=5),
        "possible_explanations": _string_list(explanations, limit=5),
        "suggested_actions": _string_list(actions, limit=5),
        "core_metrics_snapshot": [_metric_snapshot(result) for result in core_results],
    }


def save_temporal_memory(
    snapshot: Dict[str, Any],
    memory_path: Path = DEFAULT_TEMPORAL_MEMORY_PATH,
) -> Dict[str, Any]:
    existing = load_temporal_memory(memory_path)
    latest = _normalize_report_snapshot(existing.get("latest_report"))

    if latest == snapshot:
        return {
            "status": "unchanged",
            "memory_path": str(memory_path),
            "memory": existing,
        }

    updated = _default_memory_payload()
    updated["schema_version"] = TEMPORAL_MEMORY_SCHEMA_VERSION
    updated["last_updated_utc"] = str(snapshot.get("generated_at_utc") or _format_utc(datetime.now(timezone.utc)))
    updated["latest_report"] = snapshot
    updated["previous_report"] = latest

    memory_path.parent.mkdir(parents=True, exist_ok=True)
    _atomic_write_json(memory_path, updated)
    return {
        "status": "updated",
        "memory_path": str(memory_path),
        "memory": updated,
    }


def _metric_snapshot(result: Dict[str, Any]) -> Dict[str, Any]:
    summary = result.get("summary") if isinstance(result.get("summary"), dict) else {}
    return {
        "metric_key": str(result.get("metric_key") or ""),
        "chart_title": str(result.get("chart_title") or ""),
        "chart_link": str(result.get("chart_link") or ""),
        "status": str(result.get("status") or "unknown"),
        "current_conversion_pct": _number_or_none(summary.get("current_conversion_pct")),
        "current_start_count": _number_or_none(summary.get("current_start_count")),
        "current_end_count": _number_or_none(summary.get("current_end_count")),
        "latest_value": _number_or_none(summary.get("latest_value")),
        "previous_value": _number_or_none(summary.get("previous_value")),
        "pct_change_vs_previous": _number_or_none(summary.get("pct_change_vs_previous")),
    }


def _normalize_report_snapshot(value: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(value, dict):
        return None
    snapshot = {
        "generated_at_utc": str(value.get("generated_at_utc") or ""),
        "headline": str(value.get("headline") or ""),
        "kpi_status": str(value.get("kpi_status") or ""),
        "key_changes": _string_list(value.get("key_changes") or [], limit=5),
        "possible_explanations": _string_list(value.get("possible_explanations") or [], limit=5),
        "suggested_actions": _string_list(value.get("suggested_actions") or [], limit=5),
        "core_metrics_snapshot": [],
    }
    metrics = value.get("core_metrics_snapshot")
    if isinstance(metrics, list):
        for item in metrics:
            if not isinstance(item, dict):
                continue
            snapshot["core_metrics_snapshot"].append(
                {
                    "metric_key": str(item.get("metric_key") or ""),
                    "chart_title": str(item.get("chart_title") or ""),
                    "chart_link": str(item.get("chart_link") or ""),
                    "status": str(item.get("status") or "unknown"),
                    "current_conversion_pct": _number_or_none(item.get("current_conversion_pct")),
                    "current_start_count": _number_or_none(item.get("current_start_count")),
                    "current_end_count": _number_or_none(item.get("current_end_count")),
                    "latest_value": _number_or_none(item.get("latest_value")),
                    "previous_value": _number_or_none(item.get("previous_value")),
                    "pct_change_vs_previous": _number_or_none(item.get("pct_change_vs_previous")),
                }
            )
    return snapshot


def _default_memory_payload() -> Dict[str, Any]:
    return {
        "schema_version": TEMPORAL_MEMORY_SCHEMA_VERSION,
        "last_updated_utc": "",
        "latest_report": None,
        "previous_report": None,
    }


def _string_list(value: Any, limit: int) -> List[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()][:limit]


def _number_or_none(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def _atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    temp_path.replace(path)


def _format_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
