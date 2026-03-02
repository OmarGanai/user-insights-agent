import base64
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import unittest

import requests
from dotenv import load_dotenv

from config import load_metric_dictionary


class LiveAmplitudeChartContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        load_dotenv()

        api_key = os.getenv("AMPLITUDE_API_KEY", "").strip()
        secret_key = os.getenv("AMPLITUDE_SECRET_KEY", "").strip()
        if not api_key or not secret_key:
            raise AssertionError(
                "AMPLITUDE_API_KEY and AMPLITUDE_SECRET_KEY are required for live chart contract tests."
            )

        base_url = os.getenv("AMPLITUDE_BASE_URL", "https://amplitude.com/api/3").rstrip("/")
        token = base64.b64encode(f"{api_key}:{secret_key}".encode("utf-8")).decode("utf-8")
        session = requests.Session()
        session.headers.update({"Authorization": f"Basic {token}"})

        payload = load_metric_dictionary()
        cls.time_standard = payload.get("time_standard", {})
        cls.comparison_standard = str(cls.time_standard.get("comparison") or "").strip().lower()
        cls.session = session
        cls.base_url = base_url
        cls.chart_contracts = _unique_chart_contracts(payload)

    def test_chart_types_match_query_payload_shape(self) -> None:
        mismatches: List[str] = []
        for chart_id, chart_type, metric_keys in self.chart_contracts:
            if chart_type not in {"funnel", "retention"}:
                continue
            payload = _query_chart(self.session, self.base_url, chart_id)
            actual = _infer_chart_type(payload)
            if actual != chart_type:
                mismatches.append(
                    f"{chart_id} ({', '.join(metric_keys)}): expected {chart_type}, got {actual or 'unknown'}"
                )
        self.assertFalse(
            mismatches,
            msg="Chart type mismatches found:\n- " + "\n- ".join(mismatches),
        )

    def test_weekly_buckets_present_for_funnel_and_retention(self) -> None:
        issues: List[str] = []
        for chart_id, chart_type, metric_keys in self.chart_contracts:
            if chart_type not in {"funnel", "retention"}:
                continue
            payload = _query_chart(self.session, self.base_url, chart_id)
            dates = _extract_bucket_dates(payload, chart_type)
            if len(dates) < 4:
                issues.append(
                    f"{chart_id} ({', '.join(metric_keys)}): expected >=4 weekly buckets, got {len(dates)}"
                )
                continue
            if not _is_weekly_spacing(dates):
                rendered = ", ".join(value.strftime("%Y-%m-%d") for value in sorted(dates))
                issues.append(f"{chart_id} ({', '.join(metric_keys)}): non-weekly bucket spacing ({rendered})")
        self.assertFalse(
            issues,
            msg="Weekly bucket issues found:\n- " + "\n- ".join(issues),
        )

    def test_funnel_previous_period_comparison_when_configured(self) -> None:
        if "previous period" not in self.comparison_standard:
            self.skipTest("Metric dictionary comparison standard does not require previous period checks.")

        issues: List[str] = []
        for chart_id, chart_type, metric_keys in self.chart_contracts:
            if chart_type != "funnel":
                continue
            payload = _query_chart(self.session, self.base_url, chart_id)
            period_count = _funnel_period_count(payload)
            if period_count < 2:
                issues.append(
                    f"{chart_id} ({', '.join(metric_keys)}): expected previous-period comparison "
                    f"(period_count>=2), got {period_count}"
                )

        self.assertFalse(
            issues,
            msg="Funnel comparison issues found:\n- " + "\n- ".join(issues),
        )


def _unique_chart_contracts(payload: Dict[str, Any]) -> List[Tuple[str, str, List[str]]]:
    per_chart: Dict[str, Dict[str, Any]] = {}
    chart_sets = payload.get("chart_sets", {})
    for chart_set_payload in chart_sets.values():
        if not isinstance(chart_set_payload, dict):
            continue
        for group_name in ("core", "supplemental"):
            entries = chart_set_payload.get(group_name, [])
            if not isinstance(entries, list):
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                chart_id = str(entry.get("chart_id") or "").strip()
                chart_type = str(entry.get("chart_type") or "").strip()
                metric_key = str(entry.get("metric_key") or "").strip()
                if not chart_id:
                    continue

                row = per_chart.setdefault(
                    chart_id,
                    {
                        "chart_type": chart_type,
                        "metric_keys": [],
                    },
                )
                if chart_type and row["chart_type"] and chart_type != row["chart_type"]:
                    raise ValueError(
                        f"Chart {chart_id} has conflicting chart_type values: "
                        f"{row['chart_type']} vs {chart_type}"
                    )
                if metric_key and metric_key not in row["metric_keys"]:
                    row["metric_keys"].append(metric_key)

    result: List[Tuple[str, str, List[str]]] = []
    for chart_id, row in sorted(per_chart.items()):
        result.append((chart_id, str(row["chart_type"]), list(row["metric_keys"])))
    return result


def _query_chart(session: requests.Session, base_url: str, chart_id: str) -> Dict[str, Any]:
    response = session.get(f"{base_url}/chart/{chart_id}/query", timeout=60)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        snippet = response.text[:240]
        raise AssertionError(f"Chart {chart_id} query failed ({exc}): {snippet}") from exc
    payload = response.json()
    if not isinstance(payload, dict):
        raise AssertionError(f"Chart {chart_id} query payload is not an object.")
    return payload


def _infer_chart_type(payload: Dict[str, Any]) -> str:
    data = payload.get("data")
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict) and (
                "dayFunnels" in item or "cumulativeRaw" in item or "convertedByDay" in item
            ):
                return "funnel"
    if isinstance(data, dict):
        series = data.get("series")
        if isinstance(series, list) and series and isinstance(series[0], dict) and "values" in series[0]:
            return "retention"
    return ""


def _extract_bucket_dates(payload: Dict[str, Any], chart_type: str) -> List[datetime]:
    if chart_type == "funnel":
        return _extract_funnel_bucket_dates(payload)
    if chart_type == "retention":
        return _extract_retention_bucket_dates(payload)
    return []


def _extract_funnel_bucket_dates(payload: Dict[str, Any]) -> List[datetime]:
    data = payload.get("data")
    if not isinstance(data, list) or not data or not isinstance(data[0], dict):
        return []
    day_funnels = data[0].get("dayFunnels")
    if not isinstance(day_funnels, dict):
        return []
    x_values = day_funnels.get("xValues")
    if not isinstance(x_values, list):
        return []
    parsed: List[datetime] = []
    for value in x_values:
        if not isinstance(value, str):
            continue
        parsed_date = _parse_date(value)
        if parsed_date:
            parsed.append(parsed_date)
    return parsed


def _extract_retention_bucket_dates(payload: Dict[str, Any]) -> List[datetime]:
    data = payload.get("data")
    if not isinstance(data, dict):
        return []
    series = data.get("series")
    if not isinstance(series, list) or not series or not isinstance(series[0], dict):
        return []
    dates = series[0].get("dates")
    if not isinstance(dates, list):
        return []
    parsed: List[datetime] = []
    for value in dates:
        if not isinstance(value, str):
            continue
        parsed_date = _parse_date(value)
        if parsed_date:
            parsed.append(parsed_date)
    return parsed


def _parse_date(value: str) -> Optional[datetime]:
    value = value.strip()
    for fmt in ("%Y-%m-%d", "%b %d, %Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def _is_weekly_spacing(dates: List[datetime]) -> bool:
    if len(dates) < 2:
        return True
    ordered = sorted(dates)
    for previous, current in zip(ordered, ordered[1:]):
        delta_days = (current - previous).days
        if delta_days not in (6, 7, 8):
            return False
    return True


def _funnel_period_count(payload: Dict[str, Any]) -> int:
    data = payload.get("data")
    if not isinstance(data, list):
        return 0
    return len(data)
