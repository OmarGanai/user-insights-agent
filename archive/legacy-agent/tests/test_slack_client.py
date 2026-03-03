import unittest
from unittest.mock import Mock, patch

from clients.slack import SlackWebhookClient


class SlackWebhookClientTest(unittest.TestCase):
    @patch("clients.slack.requests.post")
    def test_post_payload_uses_payload_as_given_when_no_default_channel(self, mock_post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        client = SlackWebhookClient(webhook_url="https://example.com/webhook", channel=None)
        payload = {"text": "Digest", "blocks": [{"type": "divider"}], "channel": "#custom"}
        client.post_payload(payload)

        self.assertTrue(mock_post.called)
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], "https://example.com/webhook")
        self.assertEqual(kwargs["json"], payload)

    @patch("clients.slack.requests.post")
    def test_post_report_applies_default_channel(self, mock_post: Mock) -> None:
        response = Mock()
        response.raise_for_status.return_value = None
        mock_post.return_value = response

        client = SlackWebhookClient(webhook_url="https://example.com/webhook", channel="#defaults")
        client.post_report(text="Digest", blocks=[{"type": "divider"}])

        payload = mock_post.call_args.kwargs["json"]
        self.assertEqual(payload["channel"], "#defaults")
        self.assertEqual(payload["text"], "Digest")
        self.assertEqual(payload["blocks"], [{"type": "divider"}])


if __name__ == "__main__":
    unittest.main()
