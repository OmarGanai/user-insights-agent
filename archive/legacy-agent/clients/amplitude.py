import base64
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests

LOW_VOLUME_BASE_THRESHOLD = 50.0
LOW_VOLUME_CONVERTED_THRESHOLD = 5.0
LOW_VOLUME_SERIES_THRESHOLD = 30.0


class AmplitudeClient:
    def __init__(self, base_url: str, api_key: str, secret_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.secret_key = secret_key
        self.session = requests.Session()
        token = base64.b64encode(f"{api_key}:{secret_key}".encode("utf-8")).decode("utf-8")
        self.session.headers.update({"Authorization": f"Basic {token}"})

    def query_chart(self, chart_id: str) -> Dict[str, Any]:
        url = f"{self.base_url}/chart/{chart_id}/query"
        response = self.session.get(url, timeout=45)
        response.raise_for_status()
        return response.json()

    def query_charts(self, chart_ids: List[str]) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        for chart_id in chart_ids:
            raw = self.query_chart(chart_id)
            results.append(
                {
                    "chart_id": chart_id,
                    "summary": summarize_chart_payload(raw),
                    "raw": raw,
                }
            )
        return results


def summarize_chart_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a compact summary that is useful to the LLM and Slack output.
    Handles both CSV-style and JSON-style chart query responses.
    """
    summary: Dict[str, Any] = {
        "latest_value": None,
        "previous_value": None,
        "pct_change_vs_previous": None,
        "series_points": 0,
        "reliability": {
            "base_count": None,
            "converted_count": None,
            "incomplete_bucket_detected": False,
            "low_volume_caution": False,
            "confidence": "medium",
            "notes": [],
        },
    }

    try:
        if payload.get("isCsvResponse"):
            lines = payload.get("csvResponse") or []
            if isinstance(lines, str):
                lines = [line for line in lines.splitlines() if line.strip()]
            numeric_values = _extract_numeric_values_from_csv_lines(lines)
            _fill_summary_from_values(summary, numeric_values)
            _apply_reliability_fields(summary, payload)
            summary["response_type"] = "csv"
            return summary

        json_resp = payload.get("jsonResponse", payload)
        values = _extract_numeric_values_from_json_response(json_resp)
        _fill_summary_from_values(summary, values)
        funnel_period_fields = _extract_funnel_period_fields(json_resp.get("data"))
        if funnel_period_fields:
            summary.update(funnel_period_fields)
            summary["latest_value"] = funnel_period_fields["current_conversion_pct"]
            summary["previous_value"] = funnel_period_fields["previous_conversion_pct"]
            summary["series_points"] = 2
            prev = summary["previous_value"]
            if prev != 0:
                summary["pct_change_vs_previous"] = round(
                    ((summary["latest_value"] - prev) / prev) * 100.0,
                    2,
                )
            else:
                summary["pct_change_vs_previous"] = None
        _apply_reliability_fields(summary, payload)
        summary["response_type"] = "json"
        return summary
    except Exception:
        # Fall back to a truncated raw preview if we cannot parse known shapes.
        _apply_reliability_fields(summary, payload)
        summary["raw_preview"] = json.dumps(payload)[:800]
        summary["response_type"] = "unknown"
        return summary


def _fill_summary_from_values(summary: Dict[str, Any], values: List[float]) -> None:
    if not values:
        return
    summary["series_points"] = len(values)
    summary["latest_value"] = values[-1]
    if len(values) > 1:
        summary["previous_value"] = values[-2]
        prev = values[-2]
        if prev != 0:
            summary["pct_change_vs_previous"] = round(((values[-1] - prev) / prev) * 100.0, 2)


def _extract_numeric_values_from_csv_lines(lines: List[str]) -> List[float]:
    values: List[float] = []
    for line in lines:
        # The payload often prefixes cells with tabs and quotes.
        cleaned = line.replace('"', "").replace("\t", "").strip()
        parts = [part.strip() for part in cleaned.split(",") if part.strip()]
        if len(parts) < 2:
            continue
        for cell in parts[1:]:
            try:
                values.append(float(cell))
            except ValueError:
                continue
    return values


def _extract_numeric_values_from_json_response(json_resp: Dict[str, Any]) -> List[float]:
    time_series_values = _extract_time_series_values(json_resp.get("timeSeries"))
    if time_series_values:
        return time_series_values

    data = json_resp.get("data")

    # Segmentation charts often return date keyed maps under data.series[].values.
    segmentation_values = _extract_segmentation_series_values(data)
    if segmentation_values:
        return segmentation_values

    # Funnel charts commonly return dayFunnels/cumulative arrays under data[].
    funnel_values = _extract_funnel_values(data)
    if funnel_values:
        return funnel_values

    return []


def _extract_time_series_values(time_series: Any) -> List[float]:
    values: List[float] = []
    for series in time_series or []:
        for point in series or []:
            value = point.get("value") if isinstance(point, dict) else None
            if _is_number(value):
                values.append(float(value))
    return values


def _extract_segmentation_series_values(data: Any) -> List[float]:
    if not isinstance(data, dict):
        return []
    series = data.get("series")
    if not isinstance(series, list):
        return []

    date_totals: Dict[str, float] = {}
    for segment in series:
        if not isinstance(segment, dict):
            continue
        values_by_date = segment.get("values")
        if not isinstance(values_by_date, dict):
            continue
        for date_label, bucket in values_by_date.items():
            count = _extract_bucket_count(bucket)
            if count is None:
                continue
            date_totals[date_label] = date_totals.get(date_label, 0.0) + count

    if not date_totals:
        return []

    ordered_dates = sorted(date_totals.keys(), key=_date_sort_key)
    return [date_totals[date] for date in ordered_dates]


def _extract_bucket_count(bucket: Any) -> Optional[float]:
    if _is_number(bucket):
        return float(bucket)
    if isinstance(bucket, dict):
        for key in ("count", "value", "outof"):
            value = bucket.get(key)
            if _is_number(value):
                return float(value)
        return None
    if not isinstance(bucket, list):
        return None

    total = 0.0
    found = False
    for item in bucket:
        if _is_number(item):
            total += float(item)
            found = True
            continue
        if not isinstance(item, dict):
            continue
        for key in ("count", "value", "outof"):
            value = item.get(key)
            if _is_number(value):
                total += float(value)
                found = True
                break
    return total if found else None


def _extract_funnel_values(data: Any) -> List[float]:
    if not isinstance(data, list):
        return []

    period_comparison_values = _extract_funnel_period_comparison_values(data)
    if period_comparison_values:
        return period_comparison_values

    fallback_values: List[float] = []
    for item in data:
        if not isinstance(item, dict):
            continue

        day_funnels = item.get("dayFunnels")
        day_funnel_values = _extract_day_funnel_values(day_funnels)
        if day_funnel_values:
            if _has_non_zero(day_funnel_values):
                return day_funnel_values
            if not fallback_values:
                fallback_values = day_funnel_values

        for key in ("cumulativeRaw", "stepByStep", "cumulative"):
            values = _extract_numeric_list(item.get(key))
            if not values:
                continue
            if _has_non_zero(values):
                return values
            if not fallback_values:
                fallback_values = values

    return fallback_values


def _extract_funnel_period_comparison_values(data: List[Any]) -> List[float]:
    if len(data) < 2:
        return []
    if not isinstance(data[0], dict) or not isinstance(data[1], dict):
        return []

    current_conversion = _extract_funnel_conversion_pct(data[0])
    previous_conversion = _extract_funnel_conversion_pct(data[1])
    if current_conversion is None or previous_conversion is None:
        return []

    # Maintain chronological order for _fill_summary_from_values:
    # previous period first, current period second.
    return [previous_conversion, current_conversion]


def _extract_funnel_period_fields(data: Any) -> Dict[str, Any]:
    if not isinstance(data, list) or len(data) < 2:
        return {}
    current = data[0] if isinstance(data[0], dict) else None
    previous = data[1] if isinstance(data[1], dict) else None
    if not current or not previous:
        return {}

    current_conversion = _extract_funnel_conversion_pct(current)
    previous_conversion = _extract_funnel_conversion_pct(previous)
    if current_conversion is None or previous_conversion is None:
        return {}

    current_counts = _extract_funnel_counts(current)
    previous_counts = _extract_funnel_counts(previous)

    fields: Dict[str, Any] = {
        "metric_kind": "funnel_conversion_period_compare",
        "current_conversion_pct": round(current_conversion, 2),
        "previous_conversion_pct": round(previous_conversion, 2),
        "conversion_delta_percentage_points": round(current_conversion - previous_conversion, 2),
    }
    if previous_conversion != 0:
        fields["conversion_delta_relative_pct"] = round(
            ((current_conversion - previous_conversion) / previous_conversion) * 100.0,
            2,
        )
    else:
        fields["conversion_delta_relative_pct"] = None

    if current_counts:
        fields["current_start_count"] = current_counts[0]
        fields["current_end_count"] = current_counts[1]
    if previous_counts:
        fields["previous_start_count"] = previous_counts[0]
        fields["previous_end_count"] = previous_counts[1]
    return fields


def _extract_funnel_conversion_pct(item: Dict[str, Any]) -> Optional[float]:
    counts = _extract_funnel_counts(item)
    if counts:
        start_count, end_count = counts
        if start_count != 0:
            return (end_count / start_count) * 100.0

    cumulative = _extract_numeric_list(item.get("cumulative"))
    if len(cumulative) >= 2:
        return cumulative[-1] * 100.0
    return None


def _extract_funnel_counts(item: Dict[str, Any]) -> Optional[List[float]]:
    cumulative_raw = _extract_numeric_list(item.get("cumulativeRaw"))
    if len(cumulative_raw) >= 2:
        return [cumulative_raw[0], cumulative_raw[-1]]
    return None


def _extract_day_funnel_values(day_funnels: Any) -> List[float]:
    if not isinstance(day_funnels, dict):
        return []
    rows = day_funnels.get("series")
    if not isinstance(rows, list):
        return []

    is_complete = day_funnels.get("isComplete")
    values: List[float] = []
    for idx, row in enumerate(rows):
        if isinstance(is_complete, list) and idx < len(is_complete) and not bool(is_complete[idx]):
            continue
        row_values = _extract_numeric_list(row)
        if not row_values:
            continue
        denominator = row_values[0]
        latest_step = row_values[-1]
        if len(row_values) > 1 and denominator != 0:
            values.append(latest_step / denominator)
        else:
            values.append(latest_step)
    return values


def _apply_reliability_fields(summary: Dict[str, Any], payload: Dict[str, Any]) -> None:
    base_count = _to_float(summary.get("current_start_count"))
    converted_count = _to_float(summary.get("current_end_count"))

    incomplete_bucket_detected = _detect_incomplete_bucket(payload)
    low_volume_caution = _detect_low_volume(
        base_count=base_count,
        converted_count=converted_count,
        latest_value=_to_float(summary.get("latest_value")),
    )

    notes: List[str] = []
    if base_count is None or converted_count is None:
        notes.append("base/converted counts unavailable from chart payload.")
    if low_volume_caution:
        if base_count is not None and converted_count is not None:
            notes.append(
                "low sample size in current period "
                f"({_format_intish(converted_count)}/{_format_intish(base_count)})."
            )
        else:
            notes.append("latest volume is low; treat movement as directional.")
    if incomplete_bucket_detected:
        notes.append("latest bucket may be incomplete.")

    if low_volume_caution or incomplete_bucket_detected:
        confidence = "low"
    elif base_count is None or converted_count is None:
        confidence = "medium"
    else:
        confidence = "high"

    summary["reliability"] = {
        "base_count": base_count,
        "converted_count": converted_count,
        "incomplete_bucket_detected": incomplete_bucket_detected,
        "low_volume_caution": low_volume_caution,
        "confidence": confidence,
        "notes": notes,
    }


def _detect_low_volume(
    base_count: Optional[float],
    converted_count: Optional[float],
    latest_value: Optional[float],
) -> bool:
    if base_count is not None and converted_count is not None:
        return base_count < LOW_VOLUME_BASE_THRESHOLD or converted_count < LOW_VOLUME_CONVERTED_THRESHOLD
    if latest_value is not None:
        return latest_value < LOW_VOLUME_SERIES_THRESHOLD
    return False


def _detect_incomplete_bucket(payload: Dict[str, Any]) -> bool:
    json_resp = payload.get("jsonResponse", payload)
    data = json_resp.get("data")

    # Retention payloads can include an explicit incomplete flag per value row.
    if _contains_incomplete_flag(data):
        return True

    # Some funnel payloads include per-day completion flags.
    if _contains_day_funnel_incomplete_flag(data):
        return True

    # For payloads with xValues only, infer whether the latest bucket is still open.
    x_values = _extract_x_values(json_resp)
    return _infer_incomplete_from_x_values(x_values)


def _contains_incomplete_flag(value: Any) -> bool:
    if isinstance(value, dict):
        if value.get("incomplete") is True:
            return True
        for nested in value.values():
            if _contains_incomplete_flag(nested):
                return True
        return False
    if isinstance(value, list):
        return any(_contains_incomplete_flag(item) for item in value)
    return False


def _contains_day_funnel_incomplete_flag(data: Any) -> bool:
    if not isinstance(data, list):
        return False
    for item in data:
        if not isinstance(item, dict):
            continue
        day_funnels = item.get("dayFunnels")
        if not isinstance(day_funnels, dict):
            continue
        is_complete = day_funnels.get("isComplete")
        if isinstance(is_complete, list) and any(flag is False for flag in is_complete):
            return True
    return False


def _extract_x_values(json_resp: Dict[str, Any]) -> List[str]:
    labels: List[str] = []

    series_labels = json_resp.get("xValuesForTimeSeries")
    if isinstance(series_labels, list):
        labels.extend([str(label) for label in series_labels if str(label).strip()])

    data = json_resp.get("data")
    if isinstance(data, dict):
        x_values = data.get("xValues")
        if isinstance(x_values, list):
            labels.extend([str(label) for label in x_values if str(label).strip()])
    elif isinstance(data, list):
        for item in data:
            if not isinstance(item, dict):
                continue
            day_funnels = item.get("dayFunnels")
            if isinstance(day_funnels, dict):
                x_values = day_funnels.get("xValues")
                if isinstance(x_values, list):
                    labels.extend([str(label) for label in x_values if str(label).strip()])

    return labels


def _infer_incomplete_from_x_values(labels: List[str]) -> bool:
    if not labels:
        return False

    parsed: List[datetime] = []
    for label in labels:
        parsed_label = _parse_datetime_label(label)
        if parsed_label is not None:
            parsed.append(parsed_label)
    if not parsed:
        return False

    latest = parsed[-1]
    now_utc = datetime.now(timezone.utc)
    if latest > now_utc:
        return True

    interval_days = 1
    if len(parsed) >= 2:
        delta = parsed[-1] - parsed[-2]
        interval_days = max(int(round(delta.total_seconds() / 86400.0)), 1)
    bucket_end = latest + timedelta(days=interval_days)
    return now_utc < bucket_end


def _parse_datetime_label(label: str) -> Optional[datetime]:
    raw = str(label).strip()
    if not raw:
        return None

    if raw.isdigit():
        try:
            timestamp = int(raw)
            # Amplitude can emit epoch seconds in some payload shapes.
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        except (OverflowError, ValueError):
            return None

    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _to_float(value: Any) -> Optional[float]:
    if _is_number(value):
        return float(value)
    return None


def _format_intish(value: float) -> str:
    if abs(value - round(value)) < 1e-9:
        return str(int(round(value)))
    return f"{value:.2f}"


def _extract_numeric_list(raw_values: Any) -> List[float]:
    if not isinstance(raw_values, list):
        return []
    values: List[float] = []
    for value in raw_values:
        if _is_number(value):
            values.append(float(value))
    return values


def _date_sort_key(label: str) -> Any:
    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            return (0, datetime.strptime(label, fmt).timestamp())
        except ValueError:
            continue
    return (1, label)


def _has_non_zero(values: List[float]) -> bool:
    return any(value != 0 for value in values)


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)
