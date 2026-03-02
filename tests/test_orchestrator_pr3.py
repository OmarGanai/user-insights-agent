import unittest
from unittest.mock import patch

from config import Settings
from services.orchestrator import run_weekly_report


def _settings() -> Settings:
    return Settings(
        amplitude_api_key="amp-key",
        amplitude_secret_key="amp-secret",
        amplitude_base_url="https://amplitude.com/api/3",
        chart_ids=["oys29da5"],
        typeform_token=None,
        typeform_form_id=None,
        gemini_api_key="gem-key",
        gemini_model="gemini-3-flash-preview",
        slack_webhook_url="",
        slack_channel="#user-insights",
        lookback_days=7,
        report_chart_set="legacy",
        report_app_id=639837,
    )


def _funnel_period_payload(current_end: int, previous_end: int, start_count: int = 100) -> dict:
    return {
        "data": [
            {
                "cumulativeRaw": [start_count, current_end],
                "cumulative": [1.0, current_end / float(start_count)],
            },
            {
                "cumulativeRaw": [start_count, previous_end],
                "cumulative": [1.0, previous_end / float(start_count)],
            },
        ]
    }


class OrchestratorPR3ReliabilityTest(unittest.TestCase):
    @patch("services.orchestrator.save_temporal_memory")
    @patch("services.orchestrator.load_temporal_memory")
    @patch("services.orchestrator.build_ios_release_context")
    @patch("services.orchestrator.InsightAnalyzer.generate")
    @patch("services.orchestrator.TypeformClient.fetch_recent_responses")
    @patch("services.orchestrator.AmplitudeClient.query_chart")
    def test_adds_low_confidence_note_and_passes_themes_and_reliability(
        self,
        mock_query_chart,
        mock_fetch_feedback,
        mock_generate,
        mock_ios_release_context,
        mock_load_temporal_memory,
        mock_save_temporal_memory,
    ) -> None:
        chart_payloads = {
            "oys29da5": _funnel_period_payload(current_end=5, previous_end=40, start_count=20),
            "rviqohkp": _funnel_period_payload(current_end=30, previous_end=20),
            "hc4183lh": _funnel_period_payload(current_end=18, previous_end=20),
            "p9fsuwzc": _funnel_period_payload(current_end=12, previous_end=8),
            "w2p98xci": _funnel_period_payload(current_end=25, previous_end=22),
            "gfhad295": _funnel_period_payload(current_end=9, previous_end=10),
            "sb8w2oof": _funnel_period_payload(current_end=14, previous_end=11),
        }
        mock_query_chart.side_effect = lambda chart_id: chart_payloads[chart_id]
        mock_fetch_feedback.return_value = [
            {"submitted_at": "2026-02-20T00:00:00Z", "answers": [f"Calendar sync issue {idx}"]}
            for idx in range(30)
        ]
        mock_ios_release_context.return_value = {
            "ingestion_status": "updated",
            "ingestion_error": "",
            "recent_releases": [],
        }
        mock_load_temporal_memory.return_value = {
            "schema_version": 1,
            "last_updated_utc": "",
            "latest_report": None,
            "previous_report": None,
        }
        mock_save_temporal_memory.return_value = {
            "status": "updated",
            "memory_path": "tmp/weekly-report-memory.json",
        }
        mock_generate.return_value = {
            "headline": "Activation trend is mixed this week.",
            "key_changes": ["Placeholder key change"],
            "possible_explanations": ["Recent onboarding changes may have shifted behavior."],
            "suggested_actions": ["Validate onboarding instrumentation for new users."],
            "analysis_meta": {
                "requested_model": "gemini-3-flash-preview",
                "used_model": "gemini-3-flash-preview",
                "fallback_used": False,
            },
        }

        result = run_weekly_report(settings=_settings(), dry_run=True)

        explanations = result["analysis"]["possible_explanations"]
        self.assertTrue(explanations)
        self.assertTrue(explanations[0].startswith("*Claim:* Low confidence:"))
        self.assertIn("*Evidence:*", explanations[0])
        self.assertIn("Signup Completed -> Life Tab Viewed", explanations[0])
        self.assertGreaterEqual(result["core_low_confidence_count"], 1)

        analyzer_kwargs = mock_generate.call_args.kwargs
        self.assertEqual(len(analyzer_kwargs["feedback_items"]), 30)
        self.assertIn("feedback_themes", analyzer_kwargs)
        self.assertGreaterEqual(analyzer_kwargs["feedback_themes"]["theme_count"], 1)
        self.assertIn("chart_reliability", analyzer_kwargs)
        self.assertGreaterEqual(analyzer_kwargs["chart_reliability"]["core_low_confidence_count"], 1)


if __name__ == "__main__":
    unittest.main()
