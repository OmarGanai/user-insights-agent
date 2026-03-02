import tempfile
import unittest
from pathlib import Path

from services.temporal_memory import (
    build_temporal_snapshot,
    load_temporal_memory,
    save_temporal_memory,
)


class TemporalMemoryPR2Test(unittest.TestCase):
    def test_saves_snapshot_and_rotates_previous_report(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "weekly-memory.json"
            core_results = [
                {
                    "metric_key": "core_metric",
                    "chart_title": "Core Metric",
                    "chart_link": "https://app.amplitude.com/chart/core",
                    "status": "ok",
                    "summary": {
                        "current_conversion_pct": 42.0,
                        "current_start_count": 100,
                        "current_end_count": 42,
                        "latest_value": 42.0,
                        "previous_value": 35.0,
                        "pct_change_vs_previous": 20.0,
                    },
                }
            ]

            first_snapshot = build_temporal_snapshot(
                headline="Week 1 headline",
                kpi_status="Activation KPI target 40-50%: 42.00% (42/100).",
                key_changes=["Week 1 change"],
                explanations=["Week 1 explanation"],
                actions=["Week 1 action"],
                core_results=core_results,
                generated_at_utc="2026-02-20T00:00:00Z",
            )
            second_snapshot = build_temporal_snapshot(
                headline="Week 2 headline",
                kpi_status="Activation KPI target 40-50%: 44.00% (44/100).",
                key_changes=["Week 2 change"],
                explanations=["Week 2 explanation"],
                actions=["Week 2 action"],
                core_results=core_results,
                generated_at_utc="2026-02-27T00:00:00Z",
            )

            first_write = save_temporal_memory(first_snapshot, memory_path=memory_path)
            same_write = save_temporal_memory(first_snapshot, memory_path=memory_path)
            second_write = save_temporal_memory(second_snapshot, memory_path=memory_path)
            loaded = load_temporal_memory(memory_path=memory_path)

            self.assertEqual(first_write["status"], "updated")
            self.assertEqual(same_write["status"], "unchanged")
            self.assertEqual(second_write["status"], "updated")
            self.assertEqual(loaded["latest_report"]["headline"], "Week 2 headline")
            self.assertEqual(loaded["previous_report"]["headline"], "Week 1 headline")

    def test_load_temporal_memory_handles_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            memory_path = Path(tmp_dir) / "weekly-memory.json"
            memory_path.write_text("{invalid json", encoding="utf-8")

            loaded = load_temporal_memory(memory_path=memory_path)

            self.assertEqual(loaded["schema_version"], 1)
            self.assertEqual(loaded.get("load_error"), "invalid_json")
            self.assertIsNone(loaded["latest_report"])


if __name__ == "__main__":
    unittest.main()
