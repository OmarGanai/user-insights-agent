import unittest
from typing import List

from config import CHART_LINK_TEMPLATE, Settings
from scripts.debug_pipeline_ui import BLOCK_KIT_BUILDER_URL, _build_defaults_payload, _normalize_slack_payload


def _settings(chart_ids: List[str]) -> Settings:
    return Settings(
        amplitude_api_key="amp-key",
        amplitude_secret_key="amp-secret",
        amplitude_base_url="https://amplitude.com/api/3",
        chart_ids=chart_ids,
        typeform_token=None,
        typeform_form_id=None,
        gemini_api_key="gemini-key",
        gemini_model="gemini-3-flash-preview",
        slack_webhook_url="",
        slack_channel="#user-insights",
        lookback_days=7,
        report_chart_set="legacy",
    )


class DebugPipelineUiDefaultsTest(unittest.TestCase):
    def test_build_defaults_payload_includes_dictionary_contract_metadata(self) -> None:
        payload = _build_defaults_payload(_settings(["rviqohkp"]))
        chart_reference = payload["chart_references"][0]

        self.assertEqual(chart_reference["chart_id"], "rviqohkp")
        self.assertTrue(chart_reference["chart_title"])
        self.assertEqual(chart_reference["chart_link"], CHART_LINK_TEMPLATE.format(chart_id="rviqohkp"))
        self.assertIn("funnel", chart_reference["chart_types"])
        self.assertIn("legacy_signup_to_task_created", chart_reference["metric_keys"])
        self.assertIn("legacy_signup_to_task_created_diagnostic", chart_reference["metric_keys"])
        self.assertGreaterEqual(len(chart_reference["contracts"]), 2)
        alias_contracts = [
            contract for contract in chart_reference["contracts"] if contract.get("alias_of_metric_key")
        ]
        self.assertTrue(alias_contracts)

    def test_build_defaults_payload_provides_fallback_shape_for_unknown_chart(self) -> None:
        payload = _build_defaults_payload(_settings(["unknown-chart-id"]))
        chart_reference = payload["chart_references"][0]

        self.assertEqual(chart_reference["chart_id"], "unknown-chart-id")
        self.assertEqual(chart_reference["chart_title"], "Amplitude chart unknown-chart-id")
        self.assertEqual(
            chart_reference["chart_link"],
            CHART_LINK_TEMPLATE.format(chart_id="unknown-chart-id"),
        )
        self.assertEqual(chart_reference["chart_types"], [])
        self.assertEqual(chart_reference["metric_keys"], [])
        self.assertEqual(chart_reference["contracts"], [])
        self.assertEqual(payload["block_kit_builder_url"], BLOCK_KIT_BUILDER_URL)


class DebugPipelineUiSlackPayloadValidationTest(unittest.TestCase):
    def test_normalize_slack_payload_accepts_valid_payload(self) -> None:
        payload = _normalize_slack_payload(
            {
                "text": " User Insights Digest ",
                "blocks": [{"type": "section", "text": {"type": "mrkdwn", "text": "hi"}}],
                "channel": " #user-insights ",
            }
        )
        self.assertEqual(payload["text"], "User Insights Digest")
        self.assertEqual(payload["channel"], "#user-insights")
        self.assertEqual(len(payload["blocks"]), 1)

    def test_normalize_slack_payload_rejects_invalid_shape(self) -> None:
        with self.assertRaises(ValueError):
            _normalize_slack_payload({"text": "", "blocks": []})
        with self.assertRaises(ValueError):
            _normalize_slack_payload({"text": "ok", "blocks": "not-a-list"})
        with self.assertRaises(ValueError):
            _normalize_slack_payload({"text": "ok", "blocks": ["not-an-object"]})
        with self.assertRaises(ValueError):
            _normalize_slack_payload({"text": "ok", "blocks": [], "channel": ""})


if __name__ == "__main__":
    unittest.main()
