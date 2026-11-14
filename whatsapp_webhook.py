import hashlib
import hmac
import json
import logging
import os

import requests
from flask import Flask, request


logger = logging.getLogger(__name__)


def create_app(query_fn, config=None):
    app = Flask(__name__)
    app.config.from_mapping(
        WHATSAPP_ACCESS_TOKEN=os.environ.get("WHATSAPP_ACCESS_TOKEN"),
        WHATSAPP_PHONE_NUMBER_ID=os.environ.get("WHATSAPP_PHONE_NUMBER_ID"),
        WHATSAPP_APP_SECRET=os.environ.get("WHATSAPP_APP_SECRET"),
        WHATSAPP_VERIFY_TOKEN=os.environ.get("WHATSAPP_VERIFY_TOKEN"),
        WHATSAPP_GRAPH_API_VERSION=os.environ.get("WHATSAPP_GRAPH_API_VERSION"),
    )
    if config:
        app.config.update(config)

    required_settings = (
        "WHATSAPP_ACCESS_TOKEN",
        "WHATSAPP_PHONE_NUMBER_ID",
        "WHATSAPP_APP_SECRET",
        "WHATSAPP_VERIFY_TOKEN",
        "WHATSAPP_GRAPH_API_VERSION",
    )
    missing_settings = [
        setting for setting in required_settings if not app.config.get(setting)
    ]
    if missing_settings:
        raise RuntimeError(
            "Missing WhatsApp configuration: " + ", ".join(missing_settings)
        )

    @app.get("/webhook")
    def verify_webhook():
        mode = request.args.get("hub.mode", "")
        token = request.args.get("hub.verify_token", "")
        challenge = request.args.get("hub.challenge", "")
        if (
            mode == "subscribe"
            and hmac.compare_digest(token, app.config["WHATSAPP_VERIFY_TOKEN"])
        ):
            return challenge, 200
        return "Webhook verification failed", 403

    @app.post("/webhook")
    def receive_webhook():
        raw_body = request.get_data()
        signature = request.headers.get("X-Hub-Signature-256", "")
        expected_signature = "sha256=" + hmac.new(
            app.config["WHATSAPP_APP_SECRET"].encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            return "Invalid webhook signature", 403

        try:
            payload = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return "Invalid JSON", 400
        if not isinstance(payload, dict):
            return "Invalid webhook payload", 400

        for entry in payload.get("entry", []):
            if not isinstance(entry, dict):
                continue
            for change in entry.get("changes", []):
                if not isinstance(change, dict):
                    continue
                value = change.get("value", {})
                if not isinstance(value, dict):
                    continue
                for message in value.get("messages", []):
                    if not isinstance(message, dict) or message.get("type") != "text":
                        continue
                    sender = message.get("from")
                    text_message = message.get("text")
                    if not isinstance(text_message, dict):
                        continue
                    text = text_message.get("body")
                    if not isinstance(sender, str) or not isinstance(text, str):
                        continue
                    if not text.strip():
                        continue

                    answer = str(query_fn(text))
                    if not answer.strip():
                        raise ValueError("The chatbot returned an empty response.")
                    send_text_message(app.config, sender, answer)

        return "EVENT_RECEIVED", 200

    @app.errorhandler(requests.RequestException)
    def handle_whatsapp_api_error(error):
        logger.error("WhatsApp Cloud API request failed: %s", error)
        return "WhatsApp message delivery failed", 502

    return app


def send_text_message(config, recipient, message):
    version = config["WHATSAPP_GRAPH_API_VERSION"]
    phone_number_id = config["WHATSAPP_PHONE_NUMBER_ID"]
    url = "https://graph.facebook.com/{}/{}/messages".format(
        version, phone_number_id
    )
    response = requests.post(
        url,
        headers={"Authorization": "Bearer " + config["WHATSAPP_ACCESS_TOKEN"]},
        json={
            "messaging_product": "whatsapp",
            "to": recipient,
            "type": "text",
            "text": {"body": message},
        },
        timeout=15,
    )
    response.raise_for_status()
