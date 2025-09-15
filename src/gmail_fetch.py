import base64
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service(client_id: str, client_secret: str, refresh_token: str):
    """Builds an authenticated Gmail API service using OAuth refresh token."""
    creds = Credentials(
        None,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=client_id,
        client_secret=client_secret,
        scopes=SCOPES,
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def list_messages(svc, label: str, since_days: int = 1) -> List[Dict]:
    """
    Return a list of message metadata IDs for a given label within the last `since_days`.
    """
    q_time = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y/%m/%d")
    query = f"label:{label} after:{q_time}"
    msgs = []
    resp = svc.users().messages().list(userId="me", q=query, maxResults=50).execute()
    msgs.extend(resp.get("messages", []))
    while resp.get("nextPageToken"):
        resp = svc.users().messages().list(
            userId="me",
            q=query,
            pageToken=resp["nextPageToken"],
            maxResults=50
        ).execute()
        msgs.extend(resp.get("messages", []))
    return msgs


def get_message(svc, msg_id: str) -> Dict:
    """Fetch full message content by ID."""
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()


def extract_email_html(msg: Dict) -> str:
    """
    Extract HTML (or plain text as fallback) from a Gmail message payload.
    """
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])

    # Check top-level HTML
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Look through multipart sections
    for p in parts:
        if p.get("mimeType") == "text/html" and p.get("body", {}).get("data"):
            data = p["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    # Fallback: plain text
    if payload.get("mimeType") == "text/plain" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    for p in parts:
        if p.get("mimeType") == "text/plain" and p.get("body", {}).get("data"):
            data = p["body"]["data"]
            return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")

    return ""


def guess_source(headers: List[Dict]) -> str:
    """Try to return the From header for attribution."""
    return next((h["value"] for h in headers if h.get("name", "").lower() == "from"), "")
