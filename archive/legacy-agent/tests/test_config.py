import os
import unittest
from unittest.mock import patch

from config import Settings


class SettingsLoadTest(unittest.TestCase):
    @patch("config.load_dotenv", return_value=None)
    def test_defaults_to_gemini_flash_model(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "GEMINI_API_KEY": "gem",
            },
            clear=True,
        ):
            settings = Settings.load()

        self.assertEqual(settings.gemini_model, "gemini-3-flash-preview")
        self.assertEqual(settings.lookback_days, 7)
        self.assertEqual(settings.report_chart_set, "activation_v1")
        self.assertEqual(
            settings.chart_ids,
            ["0pl4jd50", "i3i58uut", "ectuc1bm", "w2p98xci", "p8g2bhzg", "9wo48n2l", "i2cqwsyx", "0zug54x7"],
        )

    @patch("config.load_dotenv", return_value=None)
    def test_honors_lookback_days_override(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "GEMINI_API_KEY": "gem",
                "LOOKBACK_DAYS": "21",
            },
            clear=True,
        ):
            settings = Settings.load()

        self.assertEqual(settings.lookback_days, 21)

    @patch("config.load_dotenv", return_value=None)
    def test_honors_custom_gemini_model(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "GEMINI_API_KEY": "gem",
                "GEMINI_MODEL": "gemini-3.1-pro-preview",
            },
            clear=True,
        ):
            settings = Settings.load()

        self.assertEqual(settings.gemini_model, "gemini-3.1-pro-preview")

    @patch("config.load_dotenv", return_value=None)
    def test_honors_report_chart_set_override(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "GEMINI_API_KEY": "gem",
                "REPORT_CHART_SET": "activation_v1",
            },
            clear=True,
        ):
            settings = Settings.load()

        self.assertEqual(settings.report_chart_set, "activation_v1")
        self.assertEqual(
            settings.chart_ids,
            [
                "0pl4jd50",
                "i3i58uut",
                "ectuc1bm",
                "w2p98xci",
                "p8g2bhzg",
                "9wo48n2l",
                "i2cqwsyx",
                "0zug54x7",
            ],
        )

    @patch("config.load_dotenv", return_value=None)
    def test_rejects_invalid_report_chart_set(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "GEMINI_API_KEY": "gem",
                "REPORT_CHART_SET": "bad_set",
            },
            clear=True,
        ):
            with self.assertRaises(ValueError):
                Settings.load()

    @patch("config.load_dotenv", return_value=None)
    def test_honors_skip_ai_analysis_flag(self, _mock_dotenv) -> None:
        with patch.dict(
            os.environ,
            {
                "AMPLITUDE_API_KEY": "amp",
                "AMPLITUDE_SECRET_KEY": "secret",
                "SKIP_AI_ANALYSIS": "true",
            },
            clear=True,
        ):
            settings = Settings.load()

        self.assertTrue(settings.skip_ai_analysis)


if __name__ == "__main__":
    unittest.main()
