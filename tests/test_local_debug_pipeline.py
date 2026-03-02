import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from config import Settings
from scripts.local_debug_pipeline import run_local_debug_pipeline


def _settings() -> Settings:
    return Settings(
        amplitude_api_key="amp-key",
        amplitude_secret_key="amp-secret",
        amplitude_base_url="https://amplitude.com/api/3",
        chart_ids=["chart-1"],
        typeform_token=None,
        typeform_form_id=None,
        gemini_api_key="gemini-key",
        gemini_model="gemini-3-flash-preview",
        slack_webhook_url="",
        slack_channel="#user-insights",
        lookback_days=7,
    )


class LocalDebugPipelineTest(unittest.TestCase):
    def test_config_validation_allows_missing_slack_for_dry_run(self) -> None:
        settings = _settings()
        settings.slack_webhook_url = ""
        settings.validate_required(require_slack=False)

    @patch("scripts.local_debug_pipeline.TypeformClient.fetch_recent_responses")
    @patch("scripts.local_debug_pipeline.AmplitudeClient.query_charts")
    def test_writes_all_step_files_with_skip_ai(
        self,
        mock_query_charts,
        mock_fetch_recent_responses,
    ) -> None:
        mock_query_charts.return_value = [
            {
                "chart_id": "chart-1",
                "summary": {
                    "latest_value": 120.0,
                    "previous_value": 100.0,
                    "pct_change_vs_previous": 20.0,
                    "series_points": 2,
                    "response_type": "json",
                },
                "raw": {"jsonResponse": {}},
            }
        ]
        mock_fetch_recent_responses.return_value = [
            {"submitted_at": "2025-01-01T00:00:00Z", "answers": ["Loving it"]}
        ]
        mocked_orchestration = {
            "analysis": {
                "headline": "AI analysis skipped; report generated from deterministic chart evidence.",
                "key_changes": ["AI stage disabled for this run."],
                "possible_explanations": [],
                "suggested_actions": [],
                "analysis_meta": {"ai_skipped": True},
            },
            "slack_preview": {
                "text": "User Insights Digest",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "*Executive Summary*"}}],
            },
            "analysis_meta": {"ai_skipped": True},
            "chart_count": 1,
            "feedback_count": 1,
            "feedback_theme_count": 0,
            "ios_release_ingestion_status": "unchanged",
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scripts.local_debug_pipeline.load_context_sections") as mock_context_sections, patch(
                "scripts.local_debug_pipeline.build_ios_release_context"
            ) as mock_ios_release_context, patch(
                "scripts.local_debug_pipeline.run_weekly_report"
            ) as mock_run_weekly_report:
                mock_context_sections.return_value = {
                    "base_app_context": "base",
                    "activation_weekly_context": "activation",
                    "context_source": "split",
                }
                mock_ios_release_context.return_value = {
                    "app_id": "6480279827",
                    "lookup_url": "https://itunes.apple.com/lookup?id=6480279827",
                    "release_log_path": "docs/ios-releases.md",
                    "ingestion_status": "unchanged",
                    "ingestion_error": "",
                    "recent_releases": [],
                }
                mock_run_weekly_report.return_value = mocked_orchestration
                result = run_local_debug_pipeline(
                    settings=_settings(),
                    output_dir=tmp_dir,
                    skip_ai=True,
                )

            output_dir = Path(result["output_dir"])
            expected_files = [
                "01_amplitude_query_charts.json",
                "02_typeform_feedback.json",
                "02b_typeform_feedback_themes.json",
                "02c_app_context_sections.json",
                "02d_ios_release_context.json",
                "03_ai_analysis.json",
                "04_slack_payload_preview.json",
            ]
            for filename in expected_files:
                self.assertTrue((output_dir / filename).exists(), msg=f"Missing {filename}")

            analysis = json.loads((output_dir / "03_ai_analysis.json").read_text(encoding="utf-8"))
            self.assertEqual(
                analysis["headline"],
                "AI analysis skipped; report generated from deterministic chart evidence.",
            )

            slack_preview = json.loads(
                (output_dir / "04_slack_payload_preview.json").read_text(encoding="utf-8")
            )
            self.assertIn("User Insights Digest", slack_preview["text"])
            self.assertIn("blocks", slack_preview)
            self.assertEqual(slack_preview.get("channel"), "#user-insights")
            self.assertTrue(result.get("production_parity_mode"))

            mock_run_weekly_report.assert_called_once()
            run_kwargs = mock_run_weekly_report.call_args.kwargs
            self.assertTrue(run_kwargs["dry_run"])
            self.assertTrue(run_kwargs["skip_ai"])
            self.assertIsNone(run_kwargs["chart_ids"])
            self.assertEqual(run_kwargs["settings"].lookback_days, 7)

    @patch("scripts.local_debug_pipeline.TypeformClient.fetch_recent_responses")
    @patch("scripts.local_debug_pipeline.AmplitudeClient.query_charts")
    def test_uses_lookback_window_from_override(
        self,
        mock_query_charts,
        mock_fetch_recent_responses,
    ) -> None:
        mock_query_charts.return_value = [{"chart_id": "chart-1", "summary": {}, "raw": {}}]
        mock_fetch_recent_responses.return_value = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scripts.local_debug_pipeline.load_context_sections") as mock_context_sections, patch(
                "scripts.local_debug_pipeline.build_ios_release_context"
            ) as mock_ios_release_context, patch(
                "scripts.local_debug_pipeline.run_weekly_report"
            ) as mock_run_weekly_report:
                mock_context_sections.return_value = {
                    "base_app_context": "",
                    "activation_weekly_context": "",
                    "context_source": "none",
                }
                mock_ios_release_context.return_value = {
                    "app_id": "6480279827",
                    "lookup_url": "https://itunes.apple.com/lookup?id=6480279827",
                    "release_log_path": "docs/ios-releases.md",
                    "ingestion_status": "error",
                    "ingestion_error": "network unavailable",
                    "recent_releases": [],
                }
                mock_run_weekly_report.return_value = {
                    "analysis": {
                        "headline": "AI analysis skipped; report generated from deterministic chart evidence.",
                        "key_changes": [],
                        "possible_explanations": [],
                        "suggested_actions": [],
                        "analysis_meta": {"ai_skipped": True},
                    },
                    "slack_preview": {"text": "User Insights Digest", "blocks": []},
                    "analysis_meta": {"ai_skipped": True},
                }
                run_local_debug_pipeline(
                    settings=_settings(),
                    output_dir=tmp_dir,
                    lookback_days=21,
                    skip_ai=True,
                )

        mock_fetch_recent_responses.assert_called_once_with(days=21)
        mock_run_weekly_report.assert_called_once()
        run_kwargs = mock_run_weekly_report.call_args.kwargs
        self.assertIsNone(run_kwargs["chart_ids"])
        self.assertEqual(run_kwargs["settings"].lookback_days, 21)

    @patch("scripts.local_debug_pipeline.TypeformClient.fetch_recent_responses")
    @patch("scripts.local_debug_pipeline.AmplitudeClient.query_charts")
    def test_adds_fallback_note_to_actions_when_model_falls_back(
        self,
        mock_query_charts,
        mock_fetch_recent_responses,
    ) -> None:
        mock_query_charts.return_value = [
            {"chart_id": "chart-1", "summary": {}, "raw": {}}
        ]
        mock_fetch_recent_responses.return_value = []

        with tempfile.TemporaryDirectory() as tmp_dir:
            with patch("scripts.local_debug_pipeline.load_context_sections") as mock_context_sections, patch(
                "scripts.local_debug_pipeline.build_ios_release_context"
            ) as mock_ios_release_context, patch(
                "scripts.local_debug_pipeline.run_weekly_report"
            ) as mock_run_weekly_report:
                mock_context_sections.return_value = {
                    "base_app_context": "base",
                    "activation_weekly_context": "activation",
                    "context_source": "split",
                }
                mock_ios_release_context.return_value = {
                    "app_id": "6480279827",
                    "lookup_url": "https://itunes.apple.com/lookup?id=6480279827",
                    "release_log_path": "docs/ios-releases.md",
                    "ingestion_status": "unchanged",
                    "ingestion_error": "",
                    "recent_releases": [],
                }
                mock_run_weekly_report.return_value = {
                    "analysis": {
                        "headline": "Headline",
                        "key_changes": [],
                        "possible_explanations": [],
                        "suggested_actions": [
                            (
                                "Pipeline note: requested Gemini model `gemini-3-pro-preview` failed "
                                "(http 404: model not found); used `gemini-3-flash-preview` instead."
                            ),
                            "Original action",
                        ],
                        "analysis_meta": {
                            "requested_model": "gemini-3-pro-preview",
                            "used_model": "gemini-3-flash-preview",
                            "fallback_used": True,
                            "fallback_reason": "http 404: model not found",
                        },
                    },
                    "slack_preview": {"text": "User Insights Digest", "blocks": []},
                    "analysis_meta": {
                        "requested_model": "gemini-3-pro-preview",
                        "used_model": "gemini-3-flash-preview",
                        "fallback_used": True,
                        "fallback_reason": "http 404: model not found",
                    },
                }
                run_local_debug_pipeline(
                    settings=_settings(),
                    output_dir=tmp_dir,
                    skip_ai=False,
                )
            analysis = json.loads(Path(tmp_dir, "03_ai_analysis.json").read_text(encoding="utf-8"))

        self.assertTrue(analysis["suggested_actions"])
        self.assertIn("requested Gemini model", analysis["suggested_actions"][0])
        self.assertIn("http 404: model not found", analysis["suggested_actions"][0])
        self.assertIn("Original action", analysis["suggested_actions"])


if __name__ == "__main__":
    unittest.main()
