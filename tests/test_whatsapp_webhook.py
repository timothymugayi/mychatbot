import hashlib
import hmac
import json
import unittest
from unittest.mock import patch

from whatsapp_webhook import create_app


TEST_CONFIG = {
    "WHATSAPP_ACCESS_TOKEN": "test-access-token",
    "WHATSAPP_PHONE_NUMBER_ID": "123456",
    "WHATSAPP_APP_SECRET": "test-app-secret",
    "WHATSAPP_VERIFY_TOKEN": "test-verify-token",
    "WHATSAPP_GRAPH_API_VERSION": "v99.0",
}


class WhatsAppWebhookTests(unittest.TestCase):
    def setUp(self):
        self.queries = []
        self.app = create_app(
            lambda text: self.queries.append(text) or "Answer: " + text,
            TEST_CONFIG,
        )
        self.client = self.app.test_client()

    def test_verifies_meta_webhook_subscription(self):
        response = self.client.get(
            "/webhook",
            query_string={
                "hub.mode": "subscribe",
                "hub.verify_token": "test-verify-token",
                "hub.challenge": "challenge-value",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_data(as_text=True), "challenge-value")

    def test_rejects_invalid_webhook_signature(self):
        response = self.client.post(
            "/webhook",
            data=b'{"entry":[]}',
            headers={"X-Hub-Signature-256": "sha256=invalid"},
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.queries, [])

    @patch("whatsapp_webhook.requests.post")
    def test_queries_and_replies_to_incoming_text(self, post):
        body = json.dumps(
            {
                "entry": [
                    {
                        "changes": [
                            {
                                "value": {
                                    "messages": [
                                        {
                                            "from": "15551234567",
                                            "type": "text",
                                            "text": {"body": "Hello"},
                                        }
                                    ]
                                }
                            }
                        ]
                    }
                ]
            }
        ).encode("utf-8")
        signature = hmac.new(
            TEST_CONFIG["WHATSAPP_APP_SECRET"].encode("utf-8"),
            body,
            hashlib.sha256,
        ).hexdigest()

        response = self.client.post(
            "/webhook",
            data=body,
            headers={"X-Hub-Signature-256": "sha256=" + signature},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.queries, ["Hello"])
        post.assert_called_once_with(
            "https://graph.facebook.com/v99.0/123456/messages",
            headers={"Authorization": "Bearer test-access-token"},
            json={
                "messaging_product": "whatsapp",
                "to": "15551234567",
                "type": "text",
                "text": {"body": "Answer: Hello"},
            },
            timeout=15,
        )

    def test_requires_all_whatsapp_settings(self):
        config = dict(TEST_CONFIG)
        del config["WHATSAPP_ACCESS_TOKEN"]

        with self.assertRaisesRegex(RuntimeError, "WHATSAPP_ACCESS_TOKEN"):
            create_app(lambda text: text, config)


if __name__ == "__main__":
    unittest.main()
