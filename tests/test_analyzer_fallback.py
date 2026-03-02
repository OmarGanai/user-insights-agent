import json
import unittest
from unittest.mock import patch

import requests

from services.analyzer import InsightAnalyzer


class _FakeResponse:
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def json(self):
        return self._payload

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)


class AnalyzerFallbackTest(unittest.TestCase):
    @patch("services.analyzer.time.sleep", return_value=None)
    def test_falls_back_to_flash_when_requested_model_unavailable(self, _mock_sleep) -> None:
        analyzer = InsightAnalyzer(api_key="test-key", model="gemini-3-pro-preview")

        calls = []

        def fake_post(model_name: str, _prompt: str):
            calls.append(model_name)
            if model_name == "gemini-3-pro-preview":
                return _FakeResponse(status_code=404, payload={"error": {"message": "not found"}})
            return _FakeResponse(
                status_code=200,
                payload={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "headline": "Fallback headline",
                                                "key_changes": [],
                                                "possible_explanations": [],
                                                "suggested_actions": [],
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
            )

        with patch.object(analyzer, "_post_gemini_request", side_effect=fake_post):
            result = analyzer.generate(chart_summaries=[], feedback_items=[])

        self.assertEqual(result["headline"], "Fallback headline")
        self.assertTrue(result["analysis_meta"]["fallback_used"])
        self.assertEqual(result["analysis_meta"]["requested_model"], "gemini-3-pro-preview")
        self.assertEqual(result["analysis_meta"]["used_model"], "gemini-3-flash-preview")
        self.assertIn("http 404", result["analysis_meta"]["fallback_reason"])
        self.assertIn("not found", result["analysis_meta"]["fallback_reason"])
        self.assertIn("gemini-3-pro-preview", calls)
        self.assertIn("gemini-3-flash-preview", calls)


if __name__ == "__main__":
    unittest.main()
