import re
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


class OrchestratorPR1DryRunTest(unittest.TestCase):
    @patch("services.orchestrator.save_temporal_memory")
    @patch("services.orchestrator.load_temporal_memory")
    @patch("services.orchestrator.build_ios_release_context")
    @patch("services.orchestrator.InsightAnalyzer.generate")
    @patch("services.orchestrator.TypeformClient.fetch_recent_responses")
    @patch("services.orchestrator.AmplitudeClient.query_chart")
    def test_pr1_structure_and_evidence_rules(
        self,
        mock_query_chart,
        mock_fetch_feedback,
        mock_generate,
        mock_ios_release_context,
        mock_load_temporal_memory,
        mock_save_temporal_memory,
    ) -> None:
        chart_payloads = {
            "oys29da5": _funnel_period_payload(46, 40),
            "rviqohkp": _funnel_period_payload(30, 20),
            "hc4183lh": _funnel_period_payload(18, 20),
            "p9fsuwzc": _funnel_period_payload(12, 8),
            "w2p98xci": _funnel_period_payload(25, 22),
            "gfhad295": _funnel_period_payload(9, 10),
            "sb8w2oof": _funnel_period_payload(14, 11),
        }

        def _fake_query(chart_id: str) -> dict:
            return chart_payloads[chart_id]

        mock_query_chart.side_effect = _fake_query
        mock_fetch_feedback.return_value = [{"submitted_at": "2026-02-20T00:00:00Z", "answers": ["Great app"]}]
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
            "headline": "Activation improved this week with stronger creation behavior.",
            "key_changes": ["Placeholder"],
            "possible_explanations": ["Recent onboarding changes likely reduced early friction."],
            "suggested_actions": ["Validate onboarding copy and event instrumentation for new users."],
            "analysis_meta": {"requested_model": "gemini-3-flash-preview", "used_model": "gemini-3-flash-preview", "fallback_used": False},
        }

        result = run_weekly_report(settings=_settings(), dry_run=True)

        self.assertEqual(result["report_chart_set"], "legacy")
        self.assertEqual(result["core_metric_count"], 5)
        self.assertEqual(result["supplemental_metric_count"], 3)

        analysis = result["analysis"]
        self.assertEqual(len(analysis["key_changes"]), 3)
        for claim in analysis["key_changes"]:
            self.assertIn("%", claim)
            self.assertTrue("absolute" in claim or "/" in claim)

        slack_preview = result["slack_preview"]
        blocks = slack_preview["blocks"]
        headers = [block["text"]["text"] for block in blocks if block.get("type") == "header"]
        context_texts = [
            element["text"]
            for block in blocks
            if block.get("type") == "context"
            for element in block.get("elements", [])
            if element.get("type") == "mrkdwn"
        ]
        section_texts = [block["text"]["text"] for block in blocks if block.get("type") == "section"]
        rendered_text = "\n".join(section_texts + context_texts)

        self.assertTrue(headers[0].startswith("User Insights Digest -"))
        self.assertIn("Executive Summary", headers)
        self.assertIn("Top Movers", headers)
        self.assertIn("Insights & Actions", headers)
        self.assertIn("All Charts", headers)
        self.assertIn(
            "_Cohort: Users excluding tenant team | Trailing 4 weeks vs previous 4 weeks | Report release: Mondays_",
            context_texts,
        )
        self.assertNotIn("North Star Snapshot", rendered_text)
        self.assertNotIn("North Star Metric", rendered_text)
        self.assertNotIn("Supplemental Diagnostics Appendix", rendered_text)

        links = re.findall(r"https://app\.amplitude\.com/analytics/tenant/chart/([a-z0-9]+)", rendered_text)
        self.assertTrue(links)
        expected_ids = {"oys29da5", "rviqohkp", "hc4183lh", "p9fsuwzc", "w2p98xci", "gfhad295", "sb8w2oof"}
        self.assertTrue(set(links).issubset(expected_ids))

        self.assertIsNone(re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", rendered_text))

        self.assertEqual(result["ios_release_ingestion_status"], "updated")
        self.assertEqual(result["temporal_memory_status"], "updated")

        analyzer_kwargs = mock_generate.call_args.kwargs
        self.assertIn("context_sections", analyzer_kwargs)
        self.assertIn("ios_release_context", analyzer_kwargs)
        self.assertIn("temporal_memory", analyzer_kwargs)
        self.assertIn("feedback_themes", analyzer_kwargs)
        self.assertIn("chart_reliability", analyzer_kwargs)

    @patch("services.orchestrator.save_temporal_memory")
    @patch("services.orchestrator.load_temporal_memory")
    @patch("services.orchestrator.build_ios_release_context")
    @patch("services.orchestrator.InsightAnalyzer.generate")
    @patch("services.orchestrator.TypeformClient.fetch_recent_responses")
    @patch("services.orchestrator.AmplitudeClient.query_chart")
    def test_can_skip_ai_analysis(
        self,
        mock_query_chart,
        mock_fetch_feedback,
        mock_generate,
        mock_ios_release_context,
        mock_load_temporal_memory,
        mock_save_temporal_memory,
    ) -> None:
        mock_query_chart.return_value = _funnel_period_payload(46, 40)
        mock_fetch_feedback.return_value = [{"submitted_at": "2026-02-20T00:00:00Z", "answers": ["Great app"]}]
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

        result = run_weekly_report(
            settings=_settings(),
            dry_run=True,
            chart_ids=["oys29da5"],
            skip_ai=True,
        )

        mock_generate.assert_not_called()
        self.assertTrue(result["analysis_meta"].get("ai_skipped"))
        self.assertIn("Pipeline note", " ".join(result["analysis"]["suggested_actions"]))

    @patch("services.orchestrator.save_temporal_memory")
    @patch("services.orchestrator.load_temporal_memory")
    @patch("services.orchestrator.build_ios_release_context")
    @patch("services.orchestrator.InsightAnalyzer.generate")
    @patch("services.orchestrator.TypeformClient.fetch_recent_responses")
    @patch("services.orchestrator.AmplitudeClient.query_chart")
    def test_preserves_concise_ai_explanations_and_actions(
        self,
        mock_query_chart,
        mock_fetch_feedback,
        mock_generate,
        mock_ios_release_context,
        mock_load_temporal_memory,
        mock_save_temporal_memory,
    ) -> None:
        chart_payloads = {
            "oys29da5": _funnel_period_payload(46, 40),
            "rviqohkp": _funnel_period_payload(30, 20),
            "hc4183lh": _funnel_period_payload(18, 20),
            "p9fsuwzc": _funnel_period_payload(12, 8),
            "w2p98xci": _funnel_period_payload(25, 22),
            "gfhad295": _funnel_period_payload(9, 10),
            "sb8w2oof": _funnel_period_payload(14, 11),
        }
        mock_query_chart.side_effect = lambda chart_id: chart_payloads[chart_id]
        mock_fetch_feedback.return_value = []
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
            "headline": "Activation moved this week.",
            "key_changes": [],
            "possible_explanations": ["Activation dropped by 12% after onboarding edits."],
            "suggested_actions": ["Recover 10% conversion next week."],
            "analysis_meta": {
                "requested_model": "gemini-3-flash-preview",
                "used_model": "gemini-3-flash-preview",
                "fallback_used": False,
            },
        }

        result = run_weekly_report(settings=_settings(), dry_run=True)
        explanation = result["analysis"]["possible_explanations"][0]
        action = result["analysis"]["suggested_actions"][0]

        self.assertNotIn("Absolute context (deterministic)", explanation)
        self.assertNotIn("Absolute context (deterministic)", action)
        self.assertEqual(explanation, "Activation dropped by 12% after onboarding edits.")
        self.assertEqual(action, "Recover 10% conversion next week.")


if __name__ == "__main__":
    unittest.main()
