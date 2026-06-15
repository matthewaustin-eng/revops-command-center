"""
Extract signals from Gmail, Calendar, and Slack for the daily sync.

Supports two credential modes:
  - Local:  reads refresh token from .env (set by auth_setup.py)
  - GitHub Actions: reads GOOGLE_OAUTH_CREDENTIALS env var (JSON string)

Usage:
    from signal_extractor import GmailExtractor, CalendarExtractor, SlackExtractor
    creds = get_google_credentials()
    gmail = GmailExtractor(creds)
    signals = gmail.get_signals(days=2)
"""

import os
import json
import base64
import re
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from dotenv import load_dotenv
load_dotenv()


# ---------------------------------------------------------------------------
# Google credential helper
# ---------------------------------------------------------------------------

def get_google_credentials():
    """
    Return google.oauth2.credentials.Credentials ready for Gmail + Calendar.
    Priority:
      1. GOOGLE_OAUTH_CREDENTIALS env var (JSON blob — used in GitHub Actions)
      2. GOOGLE_OAUTH_REFRESH_TOKEN + GOOGLE_OAUTH_CLIENT_ID + GOOGLE_OAUTH_CLIENT_SECRET in .env
    """
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.send",
        "https://www.googleapis.com/auth/calendar.readonly",
    ]

    raw_json = os.getenv("GOOGLE_OAUTH_CREDENTIALS")
    if raw_json:
        data = json.loads(raw_json)
    else:
        data = {
            "client_id": os.getenv("GOOGLE_OAUTH_CLIENT_ID", ""),
            "client_secret": os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", ""),
            "refresh_token": os.getenv("GOOGLE_OAUTH_REFRESH_TOKEN", ""),
            "token_uri": os.getenv("GOOGLE_OAUTH_TOKEN_URI", "https://oauth2.googleapis.com/token"),
        }

    if not data.get("refresh_token"):
        raise RuntimeError(
            "No Google OAuth credentials found. "
            "Run `python3 scripts/auth_setup.py` locally first."
        )

    creds = Credentials(
        token=None,
        refresh_token=data["refresh_token"],
        token_uri=data["token_uri"],
        client_id=data["client_id"],
        client_secret=data["client_secret"],
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


# ---------------------------------------------------------------------------
# Gmail
# ---------------------------------------------------------------------------

_NOISE_SENDERS = re.compile(
    r'(noreply|no-reply|notifications?@|mailer@|donotreply|'
    r'calendar-notification|monday\.com|jira|confluence|'
    r'slack\.com|zoom\.us|dropbox\.com|atlassian)',
    re.IGNORECASE,
)


class GmailExtractor:
    def __init__(self, credentials):
        from googleapiclient.discovery import build
        self.service = build("gmail", "v1", credentials=credentials, cache_discovery=False)

    def get_signals(self, days=2, max_results=100):
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        after_ts = int(cutoff.timestamp())

        query = (
            f"after:{after_ts} "
            "-from:noreply@* -from:no-reply@* "
            "-label:promotions -label:spam "
            "in:inbox"
        )

        results = self.service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()

        messages = results.get("messages", [])
        signals = []

        for msg_ref in messages:
            try:
                msg = self.service.users().messages().get(
                    userId="me", id=msg_ref["id"], format="full"
                ).execute()
                signal = self._parse_message(msg)
                if signal:
                    signals.append(signal)
            except Exception:
                continue

        return signals

    def _parse_message(self, msg):
        headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
        sender = headers.get("from", "")

        if _NOISE_SENDERS.search(sender):
            return None

        subject = headers.get("subject", "(no subject)")
        date_str = headers.get("date", "")
        try:
            date = parsedate_to_datetime(date_str).strftime("%Y-%m-%d")
        except Exception:
            date = ""

        snippet = msg.get("snippet", "")
        body = self._extract_body(msg.get("payload", {}))

        return {
            "source": "gmail",
            "id": msg["id"],
            "date": date,
            "subject": subject,
            "sender": self._clean_sender(sender),
            "content": (body or snippet)[:800],
        }

    def _clean_sender(self, sender):
        m = re.search(r'<([^>]+)>', sender)
        if m:
            return m.group(1).lower()
        return sender.strip().lower()

    def _extract_body(self, payload):
        parts = payload.get("parts", [])
        if not parts:
            data = payload.get("body", {}).get("data", "")
            return self._decode_b64(data)

        for part in parts:
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                return self._decode_b64(data)

        for part in parts:
            text = self._extract_body(part)
            if text:
                return text

        return ""

    def _decode_b64(self, data):
        if not data:
            return ""
        try:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        except Exception:
            return ""


# ---------------------------------------------------------------------------
# Calendar
# ---------------------------------------------------------------------------

class CalendarExtractor:
    def __init__(self, credentials):
        from googleapiclient.discovery import build
        self.service = build("calendar", "v3", credentials=credentials, cache_discovery=False)

    def get_signals(self, days_ahead=7):
        now = datetime.now(timezone.utc)
        time_max = now + timedelta(days=days_ahead)

        events_result = self.service.events().list(
            calendarId="primary",
            timeMin=now.isoformat(),
            timeMax=time_max.isoformat(),
            maxResults=50,
            singleEvents=True,
            orderBy="startTime",
        ).execute()

        signals = []
        for event in events_result.get("items", []):
            signal = self._parse_event(event)
            if signal:
                signals.append(signal)

        return signals

    def _parse_event(self, event):
        title = event.get("summary", "")
        if not title:
            return None

        start = event.get("start", {})
        date = start.get("date") or start.get("dateTime", "")[:10]

        attendees = [
            a["email"].lower()
            for a in event.get("attendees", [])
            if not a.get("self") and a.get("responseStatus") != "declined"
        ]

        description = event.get("description", "")[:400]

        return {
            "source": "calendar",
            "id": event["id"],
            "date": date,
            "title": title,
            "attendees": attendees,
            "content": description,
        }


# ---------------------------------------------------------------------------
# Slack
# ---------------------------------------------------------------------------

class SlackExtractor:
    def __init__(self, token=None):
        from slack_sdk import WebClient
        self.client = WebClient(token=token or os.getenv("SLACK_TOKEN", ""))

    def get_signals(self, days=2, channel_limit=20, message_limit=50):
        if not os.getenv("SLACK_TOKEN") and not self.client.token:
            return []

        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        cutoff_ts = str(cutoff.timestamp())

        try:
            channels_resp = self.client.conversations_list(
                types="public_channel,private_channel",
                limit=channel_limit,
            )
        except Exception:
            return []

        channels = channels_resp.get("channels", [])
        signals = []

        for ch in channels:
            cid = ch["id"]
            cname = ch.get("name", cid)
            try:
                hist = self.client.conversations_history(
                    channel=cid,
                    oldest=cutoff_ts,
                    limit=message_limit,
                )
            except Exception:
                continue

            for msg in hist.get("messages", []):
                if msg.get("subtype"):
                    continue
                text = msg.get("text", "")
                if len(text) < 20:
                    continue
                ts = msg.get("ts", "")
                try:
                    date = datetime.fromtimestamp(float(ts), tz=timezone.utc).strftime("%Y-%m-%d")
                except Exception:
                    date = ""
                signals.append({
                    "source": "slack",
                    "id": f"{cid}-{ts}",
                    "date": date,
                    "channel": cname,
                    "sender": msg.get("user", ""),
                    "content": text[:800],
                })

        return signals
