import unittest
from unittest.mock import Mock

from clients.feedback import (
    TypeformClient,
    _build_field_lookup,
    _extract_text_answer_details,
    _extract_text_answers,
    _paginate_items,
)


class FeedbackClientTextExtractionTest(unittest.TestCase):
    def test_excludes_email_answers(self) -> None:
        answers = [
            {"email": "user@example.com"},
            {"text": "Great app"},
            {"choice": {"label": "Very likely"}},
        ]

        extracted = _extract_text_answers(answers)

        self.assertEqual(extracted, ["Great app", "Very likely"])

    def test_extracts_multi_choice_labels(self) -> None:
        answers = [
            {"choices": {"labels": ["Fast", "Easy"]}},
        ]

        extracted = _extract_text_answers(answers)

        self.assertEqual(extracted, ["Fast", "Easy"])

    def test_extracts_other_write_ins_and_redacts_pii(self) -> None:
        answers = [
            {"choice": {"label": "Something else", "other": "Please email me at user@example.com"}},
            {"choices": {"labels": ["Cancel"], "other": ["Call me 555-123-4567"]}},
        ]

        extracted = _extract_text_answers(answers)

        self.assertEqual(
            extracted,
            [
                "Something else",
                "Please email me at [redacted-email]",
                "Cancel",
                "Call me [redacted-phone]",
            ],
        )

    def test_extracts_answer_details_with_question_context(self) -> None:
        answers = [
            {
                "type": "choice",
                "field": {"id": "f1", "ref": "how_can_we_help", "type": "multiple_choice"},
                "choice": {"label": "I have a question"},
            },
            {
                "type": "text",
                "field": {"id": "f2", "ref": "tell_us_more", "type": "long_text"},
                "text": "I expected X but got Y",
            },
        ]
        field_lookup = {
            "ref:how_can_we_help": {"question": "How can we help?", "field_type": "multiple_choice"},
            "ref:tell_us_more": {"question": "Tell us more", "field_type": "long_text"},
        }

        details = _extract_text_answer_details(answers, field_lookup)

        self.assertEqual(
            details,
            [
                {
                    "text": "I have a question",
                    "question": "How can we help?",
                    "field_ref": "how_can_we_help",
                    "field_type": "multiple_choice",
                    "answer_type": "choice",
                },
                {
                    "text": "I expected X but got Y",
                    "question": "Tell us more",
                    "field_ref": "tell_us_more",
                    "field_type": "long_text",
                    "answer_type": "text",
                },
            ],
        )

    def test_build_field_lookup_includes_nested_fields(self) -> None:
        fields = [
            {
                "id": "parent_1",
                "ref": "parent_ref",
                "title": "Parent question",
                "type": "group",
                "properties": {
                    "fields": [
                        {
                            "id": "child_1",
                            "ref": "child_ref",
                            "title": "Child question",
                            "type": "short_text",
                        }
                    ]
                },
            }
        ]

        lookup = _build_field_lookup(fields)

        self.assertEqual(lookup["ref:parent_ref"]["question"], "Parent question")
        self.assertEqual(lookup["id:child_1"]["question"], "Child question")


class FeedbackClientFetchTest(unittest.TestCase):
    def test_does_not_cap_answers_per_response(self) -> None:
        client = TypeformClient(token="token", form_id="form")
        responses_payload = Mock()
        responses_payload.status_code = 200
        responses_payload.raise_for_status.return_value = None
        responses_payload.json.return_value = {
            "items": [
                {
                    "token": "tok-1",
                    "submitted_at": "2026-02-20T00:00:00Z",
                    "answers": [{
                        "type": "choice",
                        "field": {"id": "f1", "ref": "how_can_we_help", "type": "multiple_choice"},
                        "choice": {"label": "I have a question"},
                    }] + [
                        {
                            "type": "text",
                            "field": {"id": "f2", "ref": "tell_us_more", "type": "long_text"},
                            "text": f"answer-{idx}",
                        }
                        for idx in range(7)
                    ],
                }
            ]
        }
        form_payload = Mock()
        form_payload.status_code = 200
        form_payload.raise_for_status.return_value = None
        form_payload.json.return_value = {
            "fields": [
                {"id": "f1", "ref": "how_can_we_help", "title": "How can we help?", "type": "multiple_choice"},
                {"id": "f2", "ref": "tell_us_more", "title": "Tell us more", "type": "long_text"},
            ]
        }
        client.session.get = Mock(side_effect=[responses_payload, form_payload])

        items = client.fetch_recent_responses(days=30)

        self.assertEqual(len(items), 1)
        self.assertEqual(len(items[0]["answers"]), 8)
        self.assertEqual(items[0]["answers"][0], "I have a question")
        self.assertEqual(items[0]["answers"][-1], "answer-6")
        self.assertIn("answer_details", items[0])
        self.assertEqual(items[0]["answer_details"][0]["question"], "How can we help?")
        self.assertEqual(items[0]["answer_details"][0]["field_type"], "multiple_choice")


class FeedbackPaginationTest(unittest.TestCase):
    def test_paginates_until_short_page(self) -> None:
        first_page = [
            {"token": "a"},
            {"token": "b"},
        ]
        second_page = [
            {"token": "c"},
            {"token": "d"},
        ]
        third_page = [
            {"token": "e"},
        ]
        pages = {"b": second_page, "d": third_page}

        class _Resp:
            def __init__(self, items):
                self.status_code = 200
                self._items = items

            def json(self):
                return {"items": self._items}

        fetched = _paginate_items(
            first_page=first_page,
            fetch_page_fn=lambda after: _Resp(pages.get(after, [])),
            page_size=2,
        )

        self.assertEqual(len(fetched), 5)
        self.assertEqual([item["token"] for item in fetched], ["a", "b", "c", "d", "e"])


if __name__ == "__main__":
    unittest.main()
