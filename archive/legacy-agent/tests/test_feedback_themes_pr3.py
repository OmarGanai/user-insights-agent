import json
import unittest
from pathlib import Path

from services.feedback_themes import build_feedback_theme_summary


FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "pr3_feedback_theme_summary.json"


class FeedbackThemesPR3Test(unittest.TestCase):
    def test_builds_theme_counts_and_representative_snippets(self) -> None:
        feedback_items = [
            {
                "submitted_at": "2026-02-18T00:00:00Z",
                "answers": [
                    "Calendar sync keeps failing when I connect Google Calendar.",
                    "Please add better calendar error messages.",
                ],
            },
            {
                "submitted_at": "2026-02-18T01:00:00Z",
                "answers": ["The app is slow on startup and loading my tasks."],
            },
            {
                "submitted_at": "2026-02-18T02:00:00Z",
                "answers": ["The app crashes when I open detail view. Reach me at test@example.com"],
            },
            {
                "submitted_at": "2026-02-18T03:00:00Z",
                "answers": ["I wish notifications were more reliable. Call me 555-123-4567"],
            },
            {
                "submitted_at": "2026-02-18T04:00:00Z",
                "answers": ["Calendar connection is confusing during onboarding."],
            },
        ]

        summary = build_feedback_theme_summary(feedback_items)
        expected = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

        self.assertEqual(summary, expected)


if __name__ == "__main__":
    unittest.main()
