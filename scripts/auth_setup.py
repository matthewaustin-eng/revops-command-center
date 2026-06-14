#!/usr/bin/env python3
"""
One-time OAuth2 setup for Gmail + Calendar access.
Run this locally to generate a refresh token, then store it as a GitHub Secret.

Prerequisites:
  1. Go to Google Cloud Console → APIs & Services → Credentials
     (project: revops-command-center-499414)
  2. Create an OAuth 2.0 Client ID → Desktop app
  3. Download the JSON and note client_id and client_secret
  4. Add your email to Test Users under OAuth consent screen
     (until the app is published)
  5. Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in .env
  6. Run: python3 scripts/auth_setup.py

The script will open your browser, ask you to sign in as matthew.austin@hicleo.com,
and save the refresh token to .oauth_creds.json and print it for GitHub Secrets.

Usage:
    python3 scripts/auth_setup.py
"""

import os
import json
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv, set_key
load_dotenv()

SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.readonly",
]

CREDS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".oauth_creds.json")
ENV_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")


def main():
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
    except ImportError:
        print("Missing dependencies. Run: pip install -r requirements.txt")
        sys.exit(1)

    client_id = os.getenv("GOOGLE_OAUTH_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")

    if not client_id or not client_secret:
        print("Error: GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET must be set in .env")
        print("\nGet these from Google Cloud Console:")
        print("  https://console.cloud.google.com/apis/credentials")
        print("  Project: revops-command-center-499414")
        print("  Create OAuth 2.0 Client ID → Desktop app")
        sys.exit(1)

    # Check for existing valid credentials
    if os.path.exists(CREDS_FILE):
        with open(CREDS_FILE) as f:
            cred_data = json.load(f)
        creds = Credentials.from_authorized_user_info(cred_data, SCOPES)
        if creds.valid:
            print("Existing credentials are still valid. No action needed.")
            _print_secret(cred_data)
            return
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_creds(creds)
            print("Credentials refreshed.")
            _print_secret(json.loads(creds.to_json()))
            return

    # Run full OAuth2 flow
    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "redirect_uris": ["urn:ietf:wg:oauth:2.0:oob", "http://localhost"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    _save_creds(creds)
    cred_data = json.loads(creds.to_json())

    print("\nOAuth2 setup complete.")
    _print_secret(cred_data)


def _save_creds(creds):
    data = json.loads(creds.to_json())
    with open(CREDS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"Credentials saved to {CREDS_FILE}")

    # Also write to .env for local use
    set_key(ENV_FILE, "GOOGLE_OAUTH_REFRESH_TOKEN", data.get("refresh_token", ""))
    set_key(ENV_FILE, "GOOGLE_OAUTH_TOKEN_URI", data.get("token_uri", "https://oauth2.googleapis.com/token"))


def _print_secret(data):
    secret_value = json.dumps({
        "client_id": data.get("client_id", os.getenv("GOOGLE_OAUTH_CLIENT_ID")),
        "client_secret": data.get("client_secret", os.getenv("GOOGLE_OAUTH_CLIENT_SECRET")),
        "refresh_token": data.get("refresh_token", ""),
        "token_uri": data.get("token_uri", "https://oauth2.googleapis.com/token"),
    })
    print("\n" + "=" * 60)
    print("Add this as GitHub Secret: GOOGLE_OAUTH_CREDENTIALS")
    print("=" * 60)
    print(secret_value)
    print("=" * 60)


if __name__ == "__main__":
    main()
