import sys
import json
import google_auth_oauthlib.flow

# Usage: python get_refresh_token.py <CLIENT_ID> <CLIENT_SECRET>
CLIENT_ID = sys.argv[1]
CLIENT_SECRET = sys.argv[2]

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_config(
    {
        "installed": {
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    },
    SCOPES,
)

creds = flow.run_local_server(port=0)

print("\n=== Paste these into your GitHub Secrets ===\n")
print(f"GMAIL_CLIENT_ID: {CLIENT_ID}")
print(f"GMAIL_CLIENT_SECRET: {CLIENT_SECRET}")
print(f"GMAIL_REFRESH_TOKEN: {creds.refresh_token}")
