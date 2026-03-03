import unittest
from collections import defaultdict
from typing import Any, Dict, Iterable

from config import load_metric_dictionary


def _iter_entries(payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
    chart_sets = payload.get("chart_sets", {})
    for chart_set_payload in chart_sets.values():
        for group_name in ("core", "supplemental"):
            entries = chart_set_payload.get(group_name, [])
            for entry in entries:
                yield entry


class MetricDictionaryContractTest(unittest.TestCase):
    def test_chart_type_values_match_declared_standard(self) -> None:
        payload = load_metric_dictionary()
        chart_type_standard = payload.get("chart_type_standard")
        self.assertIsInstance(chart_type_standard, list)
        self.assertTrue(chart_type_standard, "chart_type_standard must not be empty")

        allowed_chart_types = {str(item).strip() for item in chart_type_standard if str(item).strip()}
        self.assertTrue(allowed_chart_types, "chart_type_standard must contain non-empty values")

        for entry in _iter_entries(payload):
            metric_key = str(entry.get("metric_key") or "").strip()
            chart_type = str(entry.get("chart_type") or "").strip()
            self.assertIn(
                chart_type,
                allowed_chart_types,
                msg=f"metric_key={metric_key} has unsupported chart_type={chart_type}",
            )

    def test_reused_chart_ids_require_alias_metadata(self) -> None:
        payload = load_metric_dictionary()
        seen_primary_metric_by_chart_id: Dict[str, str] = {}

        for entry in _iter_entries(payload):
            metric_key = str(entry.get("metric_key") or "").strip()
            chart_id = str(entry.get("chart_id") or "").strip()
            if not chart_id:
                continue

            if chart_id not in seen_primary_metric_by_chart_id:
                seen_primary_metric_by_chart_id[chart_id] = metric_key
                continue

            alias_of_metric_key = str(entry.get("alias_of_metric_key") or "").strip()
            chart_reuse_note = str(entry.get("chart_reuse_note") or "").strip()
            self.assertTrue(
                alias_of_metric_key,
                msg=f"metric_key={metric_key} reuses chart_id={chart_id} but is missing alias_of_metric_key",
            )
            self.assertTrue(
                chart_reuse_note,
                msg=f"metric_key={metric_key} reuses chart_id={chart_id} but is missing chart_reuse_note",
            )
            self.assertEqual(
                alias_of_metric_key,
                seen_primary_metric_by_chart_id[chart_id],
                msg=(
                    f"metric_key={metric_key} must alias the primary metric_key "
                    f"for chart_id={chart_id} ({seen_primary_metric_by_chart_id[chart_id]})"
                ),
            )

    def test_aliases_point_to_existing_metric_keys(self) -> None:
        payload = load_metric_dictionary()
        all_metric_keys = {
            str(entry.get("metric_key") or "").strip()
            for entry in _iter_entries(payload)
            if str(entry.get("metric_key") or "").strip()
        }
        self.assertTrue(all_metric_keys, "Metric dictionary must contain at least one metric_key")

        aliases_by_metric = defaultdict(str)
        for entry in _iter_entries(payload):
            metric_key = str(entry.get("metric_key") or "").strip()
            alias_of_metric_key = str(entry.get("alias_of_metric_key") or "").strip()
            if alias_of_metric_key:
                aliases_by_metric[metric_key] = alias_of_metric_key

        for metric_key, alias_of_metric_key in aliases_by_metric.items():
            self.assertNotEqual(metric_key, alias_of_metric_key)
            self.assertIn(
                alias_of_metric_key,
                all_metric_keys,
                msg=f"metric_key={metric_key} aliases unknown metric_key={alias_of_metric_key}",
            )


if __name__ == "__main__":
    unittest.main()
