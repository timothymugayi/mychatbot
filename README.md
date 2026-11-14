# mychatbot

## WhatsApp Cloud API

The chatbot can receive WhatsApp text messages through a Meta WhatsApp Cloud API
webhook and reply using the existing Google Docs index. It continues to support
the interactive command-line mode.

1. Create a Meta app with the WhatsApp product, configure a public HTTPS webhook
   URL ending in `/webhook`, and subscribe it to the `messages` field.
2. Set the following environment variables. Use a current Graph API version
   enabled for your Meta app.

   ```powershell
   $env:OPENAI_API_KEY = "<OpenAI API key>"
   $env:WHATSAPP_ACCESS_TOKEN = "<Meta access token>"
   $env:WHATSAPP_PHONE_NUMBER_ID = "<WhatsApp phone number ID>"
   $env:WHATSAPP_APP_SECRET = "<Meta app secret>"
   $env:WHATSAPP_VERIFY_TOKEN = "<webhook verification token you choose>"
   $env:WHATSAPP_GRAPH_API_VERSION = "<Graph API version, for example vXX.0>"
   ```

3. Start the webhook server:

   ```powershell
   python main.py --whatsapp
   ```

   The server listens on port `8000` by default; set `PORT` to change it. Enter
   the same verification token in the Meta webhook configuration. The app secret
   is used to verify Meta's `X-Hub-Signature-256` header. Keep all tokens and
   secrets out of source control, and expose the webhook through HTTPS (for
   example, with a reverse proxy terminating TLS).