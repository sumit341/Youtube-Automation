"""
Minimal YouTube upload helper. Public publishing is intentionally gated.
This script expects a rendered video and OAuth token file.
"""
import argparse
import json
import os
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]
SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="Original Hindi/Hinglish educational content.")
    parser.add_argument("--privacy", choices=["private", "unlisted", "public"], default="private")
    parser.add_argument("--confirm-public", action="store_true")
    args = parser.parse_args()

    if args.privacy == "public" and not args.confirm_public:
        raise SystemExit("Public upload blocked. Add --confirm-public only after reviewing the video and policy checks.")
    if os.environ.get("ENABLE_YOUTUBE_UPLOAD", "false").lower() != "true":
        raise SystemExit("Upload disabled. Set ENABLE_YOUTUBE_UPLOAD=true only after testing.")
    token_file = ROOT / "token.json"
    if not token_file.exists():
        raise SystemExit("Missing token.json. Run python -m src.oauth_bootstrap first.")
    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")
    youtube = build("youtube", "v3", credentials=creds, cache_discovery=False)
    body = {
        "snippet": {
            "title": args.title[:100],
            "description": args.description[:5000],
            "categoryId": "28",
        },
        "status": {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": False,
        },
    }
    media = MediaFileUpload(args.video, chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")
    print(json.dumps({"video_id": response.get("id"), "privacy": args.privacy}, indent=2))
    # Note: token refresh persistence is local only; cloud workflow must securely persist updated token if needed.

if __name__ == "__main__":
    main()
