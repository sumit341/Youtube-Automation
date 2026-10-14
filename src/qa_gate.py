
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "output" / "qa_reports"

# These are the currently verified export targets.
TARGETS = [
    {
        "name": "youtube_landscape_final",
        "path": ROOT / "output" / "youtube_landscape_final.mp4",
        "width": 1280,
        "height": 720,
    },
    {
        "name": "short_vertical_final",
        "path": ROOT / "output" / "short_vertical_final.mp4",
        "width": 720,
        "height": 1280,
    },
]


def run_command(args):
    result = subprocess.run(
        args, capture_output=True, text=True, timeout=600
    )
    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or result.stdout or "Command failed")[-3000:]
        )
    return result.stdout


def check_video(target):
    path = target["path"]
    checks = {}
    details = {}
    errors = []

    if not path.is_file():
        return {
            "name": target["name"],
            "path": str(path),
            "status": "HOLD",
            "checks": {"file_exists": False},
            "errors": ["Video file is missing."],
        }

    checks["file_exists"] = path.stat().st_size > 0
    details["file_size_bytes"] = path.stat().st_size

    ffprobe = shutil.which("ffprobe")
    ffmpeg = shutil.which("ffmpeg")

    if not ffprobe or not ffmpeg:
        return {
            "name": target["name"],
            "path": str(path),
            "status": "HOLD",
            "checks": checks,
            "errors": ["ffmpeg and ffprobe must both be available."],
        }

    try:
        raw = run_command([
            ffprobe, "-v", "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of", "json", str(path),
        ])
        info = json.loads(raw)
        streams = info.get("streams", [])
        video_streams = [s for s in streams if s.get("codec_type") == "video"]
        audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

        checks["video_stream"] = bool(video_streams)
        checks["audio_stream"] = bool(audio_streams)

        if video_streams:
            video = video_streams[0]
            details["width"] = video.get("width")
            details["height"] = video.get("height")
            checks["resolution"] = (
                video.get("width") == target["width"]
                and video.get("height") == target["height"]
            )
        else:
            checks["resolution"] = False

        duration = float(info.get("format", {}).get("duration", 0))
        details["duration_seconds"] = round(duration, 3)
        checks["duration_valid"] = duration >= 5

        # Full decode check: reads the entire file without creating an output video.
        run_command([
            ffmpeg, "-v", "error", "-i", str(path),
            "-f", "null", "-"
        ])
        checks["full_decode"] = True

    except Exception as exc:
        checks["full_decode"] = False
        errors.append(str(exc))

    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        errors.append("Failed checks: " + ", ".join(failed))

    return {
        "name": target["name"],
        "path": str(path),
        "status": "PASS" if not failed else "HOLD",
        "checks": checks,
        "details": details,
        "errors": errors,
    }


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    results = [check_video(target) for target in TARGETS]

    report = {
        "created_at": datetime.now().astimezone().isoformat(),
        "purpose": "Local QA only; this script does not upload or schedule.",
        "overall_status": (
            "PASS" if all(r["status"] == "PASS" for r in results)
            else "HOLD"
        ),
        "videos": results,
    }

    report_path = REPORT_DIR / "latest_qa_report.json"
    report_path.write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("Overall QA:", report["overall_status"])
    for item in results:
        print(f"\n{item['name']}: {item['status']}")
        for key, passed in item["checks"].items():
            print(f"  {key}: {'PASS' if passed else 'FAIL'}")
        for error in item["errors"]:
            print("  NOTE:", error)

    print("\nReport:", report_path)
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
