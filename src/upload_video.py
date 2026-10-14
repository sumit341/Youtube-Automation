
"""
YouTube upload helper with approved-export and local-QA safety gates.
Uploads remain disabled unless explicitly enabled.
"""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

ROOT = Path(__file__).resolve().parents[1]

APPROVED_EXPORTS = {
    (ROOT / "output" / "youtube_landscape_final.mp4").resolve(),
    (ROOT / "output" / "short_vertical_final.mp4").resolve(),
}

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.readonly",
    "https://www.googleapis.com/auth/yt-analytics.readonly",
]


def validate_approved_video(video_arg):
    """Accept only the two approved export files inside this project."""
    candidate = Path(video_arg)

    if not candidate.is_absolute():
        candidate = ROOT / candidate

    try:
        candidate = candidate.resolve(strict=True)
    except (OSError, RuntimeError):
        raise SystemExit(
            "Upload blocked: video file does not exist or its path is invalid."
        )

    if candidate not in APPROVED_EXPORTS:
        raise SystemExit(
            "Upload blocked: only the approved landscape or vertical "
            "export may be uploaded."
        )

    if not candidate.is_file():
        raise SystemExit("Upload blocked: approved video is not a regular file.")

    return candidate


def require_qa_pass():
    """Run local QA immediately before upload."""
    result = subprocess.run(
        [sys.executable, "-m", "src.qa_gate"],
        cwd=str(ROOT),
        check=False,
    )

    if result.returncode != 0:
        raise SystemExit(
            "QA Gate HOLD: upload blocked. "
            "Review output/qa_reports/latest_qa_report.json"
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video", required=True)
    parser.add_argument("--title", required=True)
    parser.add_argument(
        "--description",
        default="Original Hindi/Hinglish educational content.",
    )
    parser.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        default="private",
    )
    parser.add_argument("--confirm-public", action="store_true")
    args = parser.parse_args()

    # Validate the selected file before checking credentials or running QA.
    video_file = validate_approved_video(args.video)

    if args.privacy == "public" and not args.confirm_public:
        raise SystemExit(
            "Public upload blocked. Add --confirm-public only after "
            "reviewing the video and policy checks."
        )

    if os.environ.get("ENABLE_YOUTUBE_UPLOAD", "false").lower() != "true":
        raise SystemExit(
            "Upload disabled. Keep disabled until the safety checks "
            "and upload process have been deliberately tested."
        )

    require_qa_pass()

    # Recheck the approved file after QA, immediately before credential access.
    video_file = validate_approved_video(str(video_file))

    token_file = ROOT / "token.json"
    if not token_file.is_file():
        raise SystemExit(
            "Missing token.json. Run python -m src.oauth_bootstrap first."
        )

    creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)

    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token_file.write_text(creds.to_json(), encoding="utf-8")

    youtube = build(
        "youtube",
        "v3",
        credentials=creds,
        cache_discovery=False,
    )

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

    media = MediaFileUpload(
        str(video_file),
        chunksize=-1,
        resumable=True,
        mimetype="video/mp4",
    )

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"Upload progress: {int(status.progress() * 100)}%")

    print(
        json.dumps(
            {
                "video_id": response.get("id"),
                "privacy": args.privacy,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
