from pathlib import Path
from google_auth_oauthlib.flow import InstalledAppFlow

ROOT = Path(__file__).resolve().parents[1]
CLIENT_FILE = ROOT / "client_secret.json"
TOKEN_FILE = ROOT / "token.json"
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

def main():
    if not CLIENT_FILE.exists():
        raise SystemExit("Place your downloaded Desktop OAuth JSON at client_secret.json (never commit it).")
    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_FILE), SCOPES)
    creds = flow.run_local_server(port=0, access_type="offline", prompt="consent")
    TOKEN_FILE.write_text(creds.to_json(), encoding="utf-8")
    print("Saved token.json. Keep it private; do not commit or share it.")

if __name__ == "__main__":
    main()
