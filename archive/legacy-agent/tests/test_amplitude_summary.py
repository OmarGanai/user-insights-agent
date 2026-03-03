import unittest
from datetime import datetime, timedelta, timezone

from clients.amplitude import summarize_chart_payload


class AmplitudeSummaryTest(unittest.TestCase):
    def test_summarizes_time_series_payload(self) -> None:
        payload = {
            "timeSeries": [
                [
                    {"value": 10},
                    {"value": 15},
                ]
            ]
        }

        summary = summarize_chart_payload(payload)

        self.assertEqual(summary["latest_value"], 15.0)
        self.assertEqual(summary["previous_value"], 10.0)
        self.assertEqual(summary["pct_change_vs_previous"], 50.0)
        self.assertEqual(summary["series_points"], 2)
        self.assertEqual(summary["response_type"], "json")

    def test_summarizes_segmentation_series_values(self) -> None:
        payload = {
            "data": {
                "series": [
                    {
                        "values": {
                            "Feb 16, 2026": [{"count": 3}],
                            "Feb 09, 2026": [{"count": 4}],
                        }
                    },
                    {
                        "values": {
                            "Feb 16, 2026": [{"count": 2}],
                            "Feb 09, 2026": [{"count": 1}],
                        }
                    },
                ]
            }
        }

        summary = summarize_chart_payload(payload)

        self.assertEqual(summary["series_points"], 2)
        self.assertEqual(summary["previous_value"], 5.0)
        self.assertEqual(summary["latest_value"], 5.0)
        self.assertEqual(summary["pct_change_vs_previous"], 0.0)

    def test_funnel_falls_back_to_cumulative_when_day_funnel_zero(self) -> None:
        payload = {
            "data": [
                {
                    "dayFunnels": {
                        "series": [
                            [0, 0],
                            [0, 0],
                        ],
                        "isComplete": [True, True],
                    },
                    "cumulativeRaw": [97, 54],
                    "stepByStep": [1.0, 0.5567010309],
                }
            ]
        }

        summary = summarize_chart_payload(payload)

        self.assertEqual(summary["series_points"], 2)
        self.assertEqual(summary["previous_value"], 97.0)
        self.assertEqual(summary["latest_value"], 54.0)
        self.assertEqual(summary["pct_change_vs_previous"], -44.33)

    def test_funnel_period_comparison_uses_conversion_rates(self) -> None:
        payload = {
            "data": [
                {
                    "cumulativeRaw": [97, 54],
                    "cumulative": [1.0, 0.5567010309],
                },
                {
                    "cumulativeRaw": [105, 65],
                    "cumulative": [1.0, 0.6190476190],
                },
            ]
        }

        summary = summarize_chart_payload(payload)

        self.assertEqual(summary["metric_kind"], "funnel_conversion_period_compare")
        self.assertEqual(summary["series_points"], 2)
        self.assertAlmostEqual(summary["latest_value"], 55.67, places=2)
        self.assertAlmostEqual(summary["previous_value"], 61.9, places=2)
        self.assertAlmostEqual(summary["pct_change_vs_previous"], -10.06, places=2)
        self.assertAlmostEqual(summary["conversion_delta_percentage_points"], -6.23, places=2)
        self.assertAlmostEqual(summary["conversion_delta_relative_pct"], -10.07, places=2)
        self.assertEqual(summary["current_start_count"], 97.0)
        self.assertEqual(summary["current_end_count"], 54.0)
        self.assertEqual(summary["previous_start_count"], 105.0)
        self.assertEqual(summary["previous_end_count"], 65.0)
        self.assertEqual(summary["reliability"]["confidence"], "high")
        self.assertFalse(summary["reliability"]["low_volume_caution"])
        self.assertFalse(summary["reliability"]["incomplete_bucket_detected"])

    def test_reliability_flags_low_volume(self) -> None:
        payload = {
            "data": [
                {
                    "cumulativeRaw": [12, 3],
                    "cumulative": [1.0, 0.25],
                },
                {
                    "cumulativeRaw": [20, 8],
                    "cumulative": [1.0, 0.40],
                },
            ]
        }

        summary = summarize_chart_payload(payload)

        self.assertEqual(summary["reliability"]["base_count"], 12.0)
        self.assertEqual(summary["reliability"]["converted_count"], 3.0)
        self.assertTrue(summary["reliability"]["low_volume_caution"])
        self.assertEqual(summary["reliability"]["confidence"], "low")

    def test_reliability_detects_incomplete_bucket(self) -> None:
        now = datetime.now(timezone.utc)
        week_ago = (now - timedelta(days=7)).date().isoformat()
        today = now.date().isoformat()
        payload = {
            "data": [
                {
                    "cumulativeRaw": [80, 40],
                    "cumulative": [1.0, 0.5],
                    "dayFunnels": {
                        "series": [[40, 20], [40, 20]],
                        "isComplete": [True, False],
                        "xValues": [week_ago, today],
                    },
                },
                {
                    "cumulativeRaw": [85, 45],
                    "cumulative": [1.0, 0.5294],
                },
            ]
        }

        summary = summarize_chart_payload(payload)

        self.assertTrue(summary["reliability"]["incomplete_bucket_detected"])
        self.assertEqual(summary["reliability"]["confidence"], "low")


if __name__ == "__main__":
    unittest.main()
