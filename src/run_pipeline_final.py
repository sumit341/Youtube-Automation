
import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "output"

LANDSCAPE_SOURCE = OUTPUT / "youtube_landscape_stock.mp4"
VERTICAL_SOURCE = OUTPUT / "short_vertical_stock.mp4"
VOICE = OUTPUT / "voice.mp3"
MUSIC = ROOT / "assets" / "music" / "dark_cinematic.mp3"

LANDSCAPE_FINAL = OUTPUT / "youtube_landscape_final.mp4"
VERTICAL_FINAL = OUTPUT / "short_vertical_final.mp4"


def run(command):
    print("\nRunning:", subprocess.list2cmdline([str(x) for x in command]))
    subprocess.run(command, cwd=ROOT, check=True)


def probe(path):
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries",
            "format=duration:stream=codec_type,width,height",
            "-of", "json", str(path),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return json.loads(result.stdout)


def check_file(path):
    if not path.is_file():
        raise FileNotFoundError(f"Missing file: {path}")
    if path.stat().st_size == 0:
        raise RuntimeError(f"Empty file: {path}")
    info = probe(path)
    if not info.get("streams"):
        raise RuntimeError(f"Unreadable media: {path.name}")
    return info


def render(source, destination, vertical, duration):
    temp = destination.with_name(destination.stem + ".rendering.mp4")
    if temp.exists():
        temp.unlink()

    if vertical:
        # Preserve the existing vertical source, including its captions.
        video_filter = (
            "[0:v]split=2[bg][fg];"
            "[bg]scale=720:1280:force_original_aspect_ratio=increase,"
            "crop=720:1280,boxblur=20:10[blur];"
            "[fg]scale=720:1280:force_original_aspect_ratio=decrease[fit];"
            "[blur][fit]overlay=(W-w)/2:(H-h)/2,"
            "fps=30,setsar=1[vout]"
        )
    else:
        # No subtitles filter: landscape captions are not added.
        video_filter = (
            "[0:v]scale=1280:720:force_original_aspect_ratio=increase,"
            "crop=1280:720,fps=30,setsar=1[vout]"
        )

    audio_filter = (
        "[1:a]aresample=48000,volume=1.0[voice];"
        f"[2:a]aresample=48000,volume=0.35,"
        f"atrim=duration={duration:.6f},asetpts=PTS-STARTPTS[bgm];"
        "[voice][bgm]amix=inputs=2:duration=first:"
        "dropout_transition=2,alimiter=limit=0.95[aout]"
    )

    try:
        run([
            "ffmpeg", "-hide_banner", "-y",
            "-i", str(source),
            "-i", str(VOICE),
            "-i", str(MUSIC),
            "-filter_complex", video_filter + ";" + audio_filter,
            "-map", "[vout]",
            "-map", "[aout]",
            "-t", f"{duration:.6f}",
            "-c:v", "libx264",
            "-preset", "medium",
            "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "48000",
            "-movflags", "+faststart",
            str(temp),
        ])

        if not temp.is_file() or temp.stat().st_size == 0:
            raise RuntimeError(f"Empty output: {temp.name}")

        info = check_file(temp)
        streams = info["streams"]
        videos = [s for s in streams if s.get("codec_type") == "video"]
        audios = [s for s in streams if s.get("codec_type") == "audio"]
        expected = (720, 1280) if vertical else (1280, 720)

        if not videos or not audios:
            raise RuntimeError(f"Missing audio/video stream: {temp.name}")

        actual = (videos[0].get("width"), videos[0].get("height"))
        if actual != expected:
            raise RuntimeError(f"Wrong resolution {actual}; expected {expected}")

        run([
            "ffmpeg", "-v", "error", "-i", str(temp),
            "-f", "null", "NUL",
        ])

        os.replace(temp, destination)

        print(f"\nVALIDATED: {destination.name}")
        print(f"Resolution: {actual[0]}x{actual[1]}")
        print(f"Duration: {float(info['format']['duration']):.2f}s")
        print(f"Size: {destination.stat().st_size:,} bytes")
        print("Full-file decode check: passed")

    finally:
        if temp.exists():
            temp.unlink()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)

    for path in (LANDSCAPE_SOURCE, VERTICAL_SOURCE, VOICE, MUSIC):
        check_file(path)

    duration = float(check_file(VOICE)["format"]["duration"])
    if duration <= 0:
        raise RuntimeError("Invalid voice duration")

    print(f"Voice duration: {duration:.3f}s")

    print("\n[1/2] Rendering landscape WITHOUT added captions...")
    render(LANDSCAPE_SOURCE, LANDSCAPE_FINAL, False, duration)

    print("\n[2/2] Rendering vertical, preserving source captions...")
    render(VERTICAL_SOURCE, VERTICAL_FINAL, True, duration)

    print("\nTechnical render checks passed.")
    print("Please play both final files to confirm their appearance.")


if __name__ == "__main__":
    try:
        main()
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        RuntimeError,
        ValueError,
        KeyError,
        OSError,
    ) as exc:
        print(f"\nERROR: {exc}", file=sys.stderr)
        sys.exit(1)
