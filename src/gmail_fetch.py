import base64
from datetime import datetime, timedelta, timezone
from typing import List, Dict
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from bs4 import BeautifulSoup

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def gmail_service(client_id, client_secret, refresh_token):
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
    q_time = (datetime.now(timezone.utc) - timedelta(days=since_days)).strftime("%Y/%m/%d")
    query = f"label:{label} after:{q_time}"
    msgs = []
    resp = svc.users().messages().list(userId="me", q=query, maxResults=50).execute()
    msgs.extend(resp.get("messages", []))
    while resp.get("nextPageToken"):
        resp = svc.users().messages().list(userId="me", q=query, pageToken=resp["nextPageToken"]).execute()
        msgs.extend(resp.get("messages", []))
    return msgs


def get_message(svc, msg_id: str) -> Dict:
    return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()


def extract_email_html(msg) -> str:
    payload = msg.get("payload", {})
    parts = payload.get("parts", [])
    if payload.get("mimeType") == "text/html" and payload.get("body", {}).get("data"):
        data = payload["body"]["data"]
        return base64.urlsafe_b64decode(data).decode("utf-8", errors="ignore")
    for p in parts:
        if p.get("mimeType") == "text/html" and p.get("body", {}).get("data"):
 
