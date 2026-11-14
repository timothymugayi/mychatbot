import argparse
import os
import pickle

from google.auth.transport.requests import Request

from google_auth_oauthlib.flow import InstalledAppFlow
from llama_index import GPTSimpleVectorIndex, download_loader


def authorize_gdocs():
    google_oauth2_scopes = [
        "https://www.googleapis.com/auth/documents.readonly"
    ]
    cred = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", 'rb') as token:
            cred = pickle.load(token)
    if not cred or not cred.valid:
        if cred and cred.expired and cred.refresh_token:
            cred.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", google_oauth2_scopes)
            cred = flow.run_local_server(port=0)
        with open("token.pickle", 'wb') as token:
            pickle.dump(cred, token)


def load_index():
    authorize_gdocs()
    GoogleDocsReader = download_loader('GoogleDocsReader')
    gdoc_ids = ['1UuCLbWjE9nB0MQDd1Gk9DjN74Pny6Zwjp1W83q-CLiw']
    loader = GoogleDocsReader()
    documents = loader.load_data(document_ids=gdoc_ids)
    return GPTSimpleVectorIndex(documents)


def run_cli(index):
    while True:
        prompt = input("Type prompt...")
        response = index.query(prompt)
        print(response)

        # Get the last token usage
        last_token_usage = index.llm_predictor.last_token_usage
        print(f"last_token_usage={last_token_usage}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--whatsapp",
        action="store_true",
        help="Run the WhatsApp Cloud API webhook instead of the interactive CLI.",
    )
    args = parser.parse_args()

    index = load_index()
    if args.whatsapp:
        from whatsapp_webhook import create_app
        from waitress import serve

        app = create_app(index.query)
        serve(app, host="0.0.0.0", port=int(os.environ.get("PORT", "8000")))
    else:
        run_cli(index)
