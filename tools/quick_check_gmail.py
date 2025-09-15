# quick_check_gmail.py
import os
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

creds = Credentials(
    None,
    refresh_token=os.getenv("GMAIL_REFRESH_TOKEN"),
    token_uri="https://oauth2.googleapis.com/token",
    client_id=os.getenv("GMAIL_CLIENT_ID"),
    client_secret=os.getenv("GMAIL_CLIENT_SECRET"),
    scopes=["https://www.googleapis.com/auth/gmail.readonly"],
)
svc = build("gmail","v1",credentials=creds, cache_discovery=False)
q = f'label:{os.getenv("GMAIL_LABEL","Fintech")} newer_than:14d'
resp = svc.users().messages().list(userId="me", q=q, maxResults=10).execute()
msgs = resp.get("messages", [])
print(f"Found {len(msgs)} messages for query: {q}")
