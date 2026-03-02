import json
import unittest
from unittest.mock import patch

from services.analyzer import InsightAnalyzer


class AnalyzerPromptTest(unittest.TestCase):
    @patch.object(InsightAnalyzer, "_call_gemini")
    def test_includes_user_journey_context_in_prompt(self, mock_call_gemini) -> None:
        mock_call_gemini.return_value = json.dumps(
            {
                "headline": "Factual headline",
                "key_changes": [],
                "possible_explanations": [],
                "suggested_actions": [],
            }
        )
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-flash-preview")

        analyzer.generate(
            chart_summaries=[{"chart_id": "c1", "latest_value": 1}],
            feedback_items=[],
            app_context="User journey: signup -> invite -> create task",
        )

        sent_prompt = mock_call_gemini.call_args.args[0]
        self.assertIn("Avoid chart IDs and always use chart titles with links.", sent_prompt)
        self.assertIn("User Journey Context:", sent_prompt)
        self.assertIn("signup -> invite -> create task", sent_prompt)

    @patch.object(InsightAnalyzer, "_call_gemini")
    def test_marks_missing_context_when_not_provided(self, mock_call_gemini) -> None:
        mock_call_gemini.return_value = "{}"
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-flash-preview")

        analyzer.generate(chart_summaries=[], feedback_items=[])

        sent_prompt = mock_call_gemini.call_args.args[0]
        self.assertIn("No user journey context provided.", sent_prompt)

    @patch.object(InsightAnalyzer, "_call_gemini")
    def test_fills_key_changes_when_model_returns_empty(self, mock_call_gemini) -> None:
        mock_call_gemini.return_value = "{}"
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-flash-preview")

        result = analyzer.generate(
            chart_summaries=[
                {
                    "chart_title": "Signup Conversion",
                    "chart_link": "https://example.com/chart",
                    "latest_value": 40.0,
                    "previous_value": 20.0,
                    "pct_change_vs_previous": 100.0,
                }
            ],
            feedback_items=[],
        )

        self.assertTrue(result["key_changes"])
        self.assertIn("Signup Conversion", result["key_changes"][0])

    @patch.object(InsightAnalyzer, "_call_gemini")
    def test_includes_structured_release_and_memory_sections(self, mock_call_gemini) -> None:
        mock_call_gemini.return_value = "{}"
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-flash-preview")

        analyzer.generate(
            chart_summaries=[],
            feedback_items=[],
            context_sections={
                "base_app_context": "Base context line",
                "activation_weekly_context": "Weekly focus line",
                "context_source": "split",
            },
            ios_release_context={
                "ingestion_status": "updated",
                "recent_releases": [{"version": "1.0.1", "build": "88"}],
            },
            temporal_memory={
                "schema_version": 1,
                "latest_report": {"headline": "Previous headline"},
                "previous_report": None,
            },
        )

        sent_prompt = mock_call_gemini.call_args.args[0]
        self.assertIn("Structured Prompt Payload:", sent_prompt)
        self.assertIn("iOS Release Context:", sent_prompt)
        self.assertIn("\"ingestion_status\": \"updated\"", sent_prompt)
        self.assertIn("Temporal Memory:", sent_prompt)
        self.assertIn("\"schema_version\": 1", sent_prompt)

    @patch.object(InsightAnalyzer, "_call_gemini")
    def test_does_not_truncate_feedback_items_by_count(self, mock_call_gemini) -> None:
        mock_call_gemini.return_value = "{}"
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-flash-preview")
        feedback_items = [
            {
                "submitted_at": f"2026-02-20T{idx:02d}:00:00Z",
                "answers": [f"feedback-{idx}"],
            }
            for idx in range(25)
        ]

        analyzer.generate(
            chart_summaries=[],
            feedback_items=feedback_items,
            feedback_themes={"feedback_items_count": 25, "feedback_snippets_count": 25, "theme_count": 1, "themes": []},
            chart_reliability={"core_low_confidence_count": 0, "supplemental_low_confidence_count": 0, "charts": []},
        )

        sent_prompt = mock_call_gemini.call_args.args[0]
        self.assertIn("feedback-24", sent_prompt)
        self.assertIn("\"feedback_items_count\": 25", sent_prompt)
        self.assertIn("\"chart_reliability\"", sent_prompt)


if __name__ == "__main__":
    unittest.main()
