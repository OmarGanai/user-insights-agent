import json
import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from dotenv import load_dotenv

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - optional dependency fallback
    yaml = None


REPORT_APP_ID = 639837
DEFAULT_REPORT_CHART_SET = "activation_v1"
ALLOWED_REPORT_CHART_SETS = {"legacy", "activation_v1"}
METRIC_DICTIONARY_PATH = Path(__file__).resolve().parent / "docs" / "metric-dictionary.yaml"
CHART_LINK_TEMPLATE = "https://app.amplitude.com/analytics/tenant/chart/{chart_id}"


@dataclass(frozen=True)
class ChartMetric:
    metric_key: str
    chart_id: str
    chart_name: str
    intent: str
    chart_type: str
    status: str
    group: str
    chart_set: str
    app_id: int

    @property
    def has_chart_id(self) -> bool:
        return bool(self.chart_id.strip())

    @property
    def chart_link(self) -> str:
        if not self.has_chart_id:
            return ""
        return CHART_LINK_TEMPLATE.format(chart_id=self.chart_id)


@lru_cache(maxsize=1)
def _load_metric_dictionary() -> Dict[str, Any]:
    raw = METRIC_DICTIONARY_PATH.read_text(encoding="utf-8")
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        if yaml is None:
            raise ValueError(
                "Metric dictionary is not valid JSON and PyYAML is not installed. "
                "Install PyYAML or keep docs/metric-dictionary.yaml JSON-compatible."
            )
        payload = yaml.safe_load(raw)

    if not isinstance(payload, dict):
        raise ValueError("Metric dictionary must parse to an object.")

    app_id = int(payload.get("app_id", -1))
    if app_id != REPORT_APP_ID:
        raise ValueError(
            f"Metric dictionary app_id must be {REPORT_APP_ID}, found {app_id}."
        )

    chart_sets = payload.get("chart_sets")
    if not isinstance(chart_sets, dict) or not chart_sets:
        raise ValueError("Metric dictionary is missing chart_sets.")

    return payload


def load_metric_dictionary() -> Dict[str, Any]:
    return _load_metric_dictionary()


def _raw_chart_entries(chart_set: str) -> Dict[str, List[Dict[str, Any]]]:
    if chart_set not in ALLOWED_REPORT_CHART_SETS:
        allowed = ", ".join(sorted(ALLOWED_REPORT_CHART_SETS))
        raise ValueError(f"Unsupported REPORT_CHART_SET '{chart_set}'. Allowed values: {allowed}.")

    metric_dictionary = load_metric_dictionary()
    chart_sets = metric_dictionary["chart_sets"]
    if chart_set not in chart_sets:
        raise ValueError(f"Metric dictionary is missing chart set '{chart_set}'.")

    chart_set_payload = chart_sets[chart_set]
    core = chart_set_payload.get("core")
    supplemental = chart_set_payload.get("supplemental")

    if not isinstance(core, list) or not isinstance(supplemental, list):
        raise ValueError(f"Chart set '{chart_set}' must define core and supplemental arrays.")

    if len(core) < 5 or len(supplemental) < 3:
        raise ValueError(
            f"Chart set '{chart_set}' must include at least 5 core and 3 supplemental entries "
            f"(found core={len(core)}, supplemental={len(supplemental)})."
        )

    return {"core": core, "supplemental": supplemental}


def get_chart_metrics(chart_set: str) -> List[ChartMetric]:
    grouped = get_chart_metrics_by_group(chart_set)
    return grouped["core"] + grouped["supplemental"]


def get_chart_metrics_by_group(chart_set: str) -> Dict[str, List[ChartMetric]]:
    entries = _raw_chart_entries(chart_set)
    grouped: Dict[str, List[ChartMetric]] = {"core": [], "supplemental": []}
    for group_name in ("core", "supplemental"):
        for entry in entries[group_name]:
            grouped[group_name].append(
                ChartMetric(
                    metric_key=str(entry.get("metric_key") or "").strip(),
                    chart_id=str(entry.get("chart_id") or "").strip(),
                    chart_name=str(entry.get("chart_name") or "").strip(),
                    intent=str(entry.get("intent") or "").strip(),
                    chart_type=str(entry.get("chart_type") or "unknown").strip(),
                    status=str(entry.get("status") or "planned").strip(),
                    group=group_name,
                    chart_set=chart_set,
                    app_id=REPORT_APP_ID,
                )
            )

    missing_required_fields = [
        metric.metric_key
        for metric in grouped["core"] + grouped["supplemental"]
        if not metric.metric_key or not metric.chart_name or not metric.intent
    ]
    if missing_required_fields:
        raise ValueError(
            "Metric dictionary entries are missing required fields for metric keys: "
            + ", ".join(missing_required_fields)
        )

    return grouped


def get_default_chart_ids(chart_set: str) -> List[str]:
    unique_ids: List[str] = []
    seen = set()
    for metric in get_chart_metrics(chart_set):
        if not metric.has_chart_id:
            continue
        if metric.chart_id in seen:
            continue
        seen.add(metric.chart_id)
        unique_ids.append(metric.chart_id)
    return unique_ids


def get_known_chart_ids() -> Set[str]:
    known_ids: Set[str] = set()
    metric_dictionary = load_metric_dictionary()
    chart_sets = metric_dictionary.get("chart_sets", {})
    for chart_set_name in chart_sets.keys():
        grouped = _raw_chart_entries(chart_set_name)
        for group_name in ("core", "supplemental"):
            for entry in grouped[group_name]:
                chart_id = str(entry.get("chart_id") or "").strip()
                if chart_id:
                    known_ids.add(chart_id)
    return known_ids


@lru_cache(maxsize=1)
def _metric_contract_rows() -> List[Dict[str, str]]:
    metric_dictionary = load_metric_dictionary()
    chart_sets = metric_dictionary.get("chart_sets", {})
    rows: List[Dict[str, str]] = []

    for chart_set_name in sorted(chart_sets.keys()):
        grouped = _raw_chart_entries(chart_set_name)
        for group_name in ("core", "supplemental"):
            for entry in grouped[group_name]:
                rows.append(
                    {
                        "chart_set": chart_set_name,
                        "group": group_name,
                        "metric_key": str(entry.get("metric_key") or "").strip(),
                        "chart_id": str(entry.get("chart_id") or "").strip(),
                        "chart_name": str(entry.get("chart_name") or "").strip(),
                        "chart_type": str(entry.get("chart_type") or "unknown").strip(),
                        "status": str(entry.get("status") or "planned").strip(),
                        "intent": str(entry.get("intent") or "").strip(),
                        "alias_of_metric_key": str(entry.get("alias_of_metric_key") or "").strip(),
                        "chart_reuse_note": str(entry.get("chart_reuse_note") or "").strip(),
                    }
                )

    return rows


@lru_cache(maxsize=1)
def get_chart_reference_catalog() -> Dict[str, Dict[str, Any]]:
    catalog: Dict[str, Dict[str, Any]] = {}

    for row in _metric_contract_rows():
        chart_id = row["chart_id"]
        if not chart_id:
            continue

        ref = catalog.setdefault(
            chart_id,
            {
                "chart_id": chart_id,
                "chart_title": row["chart_name"] or f"Amplitude chart {chart_id}",
                "chart_link": CHART_LINK_TEMPLATE.format(chart_id=chart_id),
                "chart_types": [],
                "metric_keys": [],
                "chart_sets": [],
                "groups": [],
                "statuses": [],
                "contracts": [],
            },
        )

        if row["chart_name"] and ref["chart_title"].startswith("Amplitude chart "):
            ref["chart_title"] = row["chart_name"]

        for key, value in (
            ("chart_types", row["chart_type"]),
            ("metric_keys", row["metric_key"]),
            ("chart_sets", row["chart_set"]),
            ("groups", row["group"]),
            ("statuses", row["status"]),
        ):
            if value and value not in ref[key]:
                ref[key].append(value)

        ref["contracts"].append(
            {
                "chart_set": row["chart_set"],
                "group": row["group"],
                "metric_key": row["metric_key"],
                "chart_type": row["chart_type"],
                "status": row["status"],
                "intent": row["intent"],
                "alias_of_metric_key": row["alias_of_metric_key"],
                "chart_reuse_note": row["chart_reuse_note"],
            }
        )

    for ref in catalog.values():
        for key in ("chart_types", "metric_keys", "chart_sets", "groups", "statuses"):
            ref[key].sort()
        ref["contracts"].sort(
            key=lambda contract: (
                contract["chart_set"],
                contract["group"],
                contract["metric_key"],
            )
        )

    return catalog


@lru_cache(maxsize=1)
def _chart_title_lookup() -> Dict[str, str]:
    return {
        chart_id: str(ref.get("chart_title") or f"Amplitude chart {chart_id}")
        for chart_id, ref in get_chart_reference_catalog().items()
    }


def get_chart_reference(chart_id: str, chart_title: Optional[str] = None) -> Dict[str, str]:
    title = chart_title or _chart_title_lookup().get(chart_id, f"Amplitude chart {chart_id}")
    return {
        "chart_id": chart_id,
        "chart_title": title,
        "chart_link": CHART_LINK_TEMPLATE.format(chart_id=chart_id),
    }


def _split_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    amplitude_api_key: str
    amplitude_secret_key: str
    amplitude_base_url: str
    chart_ids: List[str]
    typeform_token: Optional[str]
    typeform_form_id: Optional[str]
    gemini_api_key: str
    gemini_model: str
    slack_webhook_url: str
    slack_channel: Optional[str]
    lookback_days: int
    skip_ai_analysis: bool = False
    report_chart_set: str = DEFAULT_REPORT_CHART_SET
    report_app_id: int = REPORT_APP_ID

    @classmethod
    def load(cls) -> "Settings":
        load_dotenv()

        report_chart_set = (os.getenv("REPORT_CHART_SET", DEFAULT_REPORT_CHART_SET).strip() or DEFAULT_REPORT_CHART_SET)
        if report_chart_set not in ALLOWED_REPORT_CHART_SETS:
            allowed = ", ".join(sorted(ALLOWED_REPORT_CHART_SETS))
            raise ValueError(
                f"Unsupported REPORT_CHART_SET '{report_chart_set}'. Allowed values: {allowed}."
            )

        override_chart_ids = _split_csv(os.getenv("AMPLITUDE_CHART_IDS"))
        chart_ids = override_chart_ids or get_default_chart_ids(report_chart_set)
        lookback_days = int(os.getenv("LOOKBACK_DAYS", "7"))

        return cls(
            amplitude_api_key=os.getenv("AMPLITUDE_API_KEY", "").strip(),
            amplitude_secret_key=os.getenv("AMPLITUDE_SECRET_KEY", "").strip(),
            amplitude_base_url=os.getenv("AMPLITUDE_BASE_URL", "https://amplitude.com/api/3").rstrip("/"),
            chart_ids=chart_ids,
            typeform_token=os.getenv("TYPEFORM_TOKEN", "").strip() or None,
            typeform_form_id=os.getenv("TYPEFORM_FORM_ID", "").strip() or None,
            gemini_api_key=os.getenv("GEMINI_API_KEY", "").strip(),
            # Keep Pro opt-in via GEMINI_MODEL once paid quota is available.
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),
            slack_webhook_url=os.getenv("SLACK_WEBHOOK_URL", "").strip(),
            slack_channel=os.getenv("SLACK_CHANNEL", "").strip() or None,
            lookback_days=lookback_days,
            skip_ai_analysis=_env_bool("SKIP_AI_ANALYSIS", default=False),
            report_chart_set=report_chart_set,
            report_app_id=REPORT_APP_ID,
        )

    def validate_required(self, require_slack: bool = True, require_ai: Optional[bool] = None) -> None:
        if require_ai is None:
            require_ai = not self.skip_ai_analysis
        required = {
            "AMPLITUDE_API_KEY": self.amplitude_api_key,
            "AMPLITUDE_SECRET_KEY": self.amplitude_secret_key,
        }
        if require_ai:
            required["GEMINI_API_KEY"] = self.gemini_api_key
        if require_slack:
            required["SLACK_WEBHOOK_URL"] = self.slack_webhook_url
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
