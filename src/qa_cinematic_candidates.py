import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "output" / "cinematic_staging"
REPORT_PATH = STAGING / "qa_report.json"

TARGETS = [
    {
        "name": "cinematic_landscape_staging",
        "path": STAGING / "youtube_landscape_cinematic_candidate.mp4",
        "width": 1280,
        "height": 720,
    },
    {
        "name": "cinematic_vertical_staging",
        "path": STAGING / "short_vertical_cinematic_candidate.mp4",
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


def find_media_tools():
    tool_dir = (
        ROOT / "tools" / "ffmpeg"
        / "ffmpeg-9.0.2-essentials_build" / "bin"
    )
    ffmpeg = (
        str(tool_dir / "ffmpeg.exe")
        if (tool_dir / "ffmpeg.exe").is_file()
        else shutil.which("ffmpeg")
    )
    ffprobe = (
        str(tool_dir / "ffprobe.exe")
        if (tool_dir / "ffprobe.exe").is_file()
        else shutil.which("ffprobe")
    )
    return ffmpeg, ffprobe


def check_video(target, ffmpeg, ffprobe):
    path = target["path"]
    checks = {
        "file_exists": path.is_file() and path.stat().st_size > 0
    }
    details = {"path": str(path)}
    errors = []

    if not checks["file_exists"]:
        return {
            "name": target["name"],
            "status": "HOLD",
            "checks": checks,
            "details": details,
            "errors": ["File missing or empty."],
        }

    details["file_size_bytes"] = path.stat().st_size

    if not ffmpeg or not ffprobe:
        return {
            "name": target["name"],
            "status": "HOLD",
            "checks": checks,
            "details": details,
            "errors": ["ffmpeg and ffprobe must be available."],
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
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]

        checks["video_stream"] = bool(videos)
        checks["audio_stream"] = bool(audios)
        checks["resolution"] = (
            bool(videos)
            and videos[0].get("width") == target["width"]
            and videos[0].get("height") == target["height"]
        )

        duration = float(info.get("format", {}).get("duration", 0))
        details["duration_seconds"] = round(duration, 3)
        details["width"] = videos[0].get("width") if videos else None
        details["height"] = videos[0].get("height") if videos else None
        checks["duration_valid"] = duration >= 5

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
        "status": "PASS" if not failed else "HOLD",
        "checks": checks,
        "details": details,
        "errors": errors,
    }


def main():
    if not STAGING.is_dir():
        print("HOLD: staging directory does not exist:", STAGING)
        return 1

    ffmpeg, ffprobe = find_media_tools()
    results = [
        check_video(target, ffmpeg, ffprobe)
        for target in TARGETS
    ]

    report = {
        "created_at": datetime.now().astimezone().isoformat(),
        "purpose": (
            "Isolated cinematic staging QA only. "
            "No uploads or production exports modified."
        ),
        "overall_status": (
            "PASS"
            if all(item["status"] == "PASS" for item in results)
            else "HOLD"
        ),
        "videos": results,
    }

    REPORT_PATH.write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )

    print("Cinematic staging QA:", report["overall_status"])
    for item in results:
        print(f"\n{item['name']}: {item['status']}")
        for key, passed in item["checks"].items():
            print(f"  {key}: {'PASS' if passed else 'FAIL'}")
        for error in item["errors"]:
            print("  NOTE:", error)

    print("\nReport:", REPORT_PATH)
    return 0 if report["overall_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
