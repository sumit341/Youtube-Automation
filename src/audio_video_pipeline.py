import asyncio
import math
import os
import subprocess
import wave
from pathlib import Path

import edge_tts
from dotenv import load_dotenv

# Sarvam is the preferred voice provider. Edge TTS remains the fallback.
try:
    from sarvamai import SarvamAI
    from sarvamai.play import save as save_sarvam_audio
except ImportError:
    SarvamAI = None
    save_sarvam_audio = None


# --------------------------------------------------
# CONFIGURATION
# --------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "output"
OUT.mkdir(parents=True, exist_ok=True)

VOICE = "hi-IN-MadhurNeural"
VOICE_RATE = "-8%"
VOICE_PITCH = "-3Hz"

SCRIPT = (
    "Power ka sabse bada secret kya hai? "
    "Har baat ka jawab dena zaroori nahi hota. "
    "Psychology kehti hai ki jo insaan apne emotions ko control karta hai, "
    "woh pressure mein behtar decisions le sakta hai. "
    "Paise aur success ki race mein sirf hard work nahi, "
    "clear thinking bhi zaroori hai. "
    "React karne se pehle rukna seekho. "
    "Observe karo. Phir strategy ke saath action lo. "
    "Yaad rakho, asli power shor machane mein nahi, "
    "apne upar control rakhne mein hai."
)

SUBTITLE_LINES = [
    "Power ka sabse bada secret kya hai?",
    "Har baat ka jawab dena zaroori nahi hota.",
    "Psychology kehti hai: emotions ko control karo.",
    "Pressure mein behtar decisions lo.",
    "Paise aur success ke liye clear thinking zaroori hai.",
    "React karne se pehle rukna seekho.",
    "Observe karo. Phir strategy ke saath action lo.",
    "Asli power hai apne upar control."
]


# --------------------------------------------------
# UTILITIES
# --------------------------------------------------

def run(cmd):
    """Run a command and show errors if it fails."""
    subprocess.run(cmd, check=True)


def check_programs():
    """Check that FFmpeg and FFprobe are installed."""
    for program in ("ffmpeg", "ffprobe"):
        try:
            subprocess.run(
                [program, "-version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )
        except (FileNotFoundError, subprocess.CalledProcessError):
            raise RuntimeError(
                f"{program} nahi mila. FFmpeg install karo "
                "aur ensure karo ki woh Windows PATH mein hai."
            )


def ffmpeg_subtitle_path(path):
    """Escape a Windows path for FFmpeg's subtitles filter."""
    p = path.resolve().as_posix()
    p = p.replace("\\", "/")
    p = p.replace(":", r"\:")
    p = p.replace("'", r"\'")
    p = p.replace(" ", r"\ ")
    return p


def get_duration(path):
    """Read media duration using FFprobe."""
    result = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        text=True,
    )
    return float(result.strip())


# --------------------------------------------------
# VOICE GENERATION
# --------------------------------------------------

async def make_voice():
    """
    Prefer Sarvam Bulbul v3 / Shubh voice when an API key exists.
    If the SDK/API call fails, use Edge TTS as a fallback.
    """
    print("\n[1/5] Hindi voice-over generate ho raha hai...")
    load_dotenv(ROOT / ".env")

    voice_path = OUT / "voice.mp3"
    sarvam_temp = OUT / "voice_sarvam_temp.wav"
    api_key = os.getenv("SARVAM_API_KEY", "").strip()

    if api_key and SarvamAI is not None and save_sarvam_audio is not None:
        try:
            print("Preferred voice: Sarvam Shubh Male")
            client = SarvamAI(api_subscription_key=api_key)

            audio = client.text_to_speech.convert(
                text=SCRIPT,
                model="bulbul:v3",
                speaker="shubh",
                language_code="hi-IN",
            )

            save_sarvam_audio(audio, str(sarvam_temp))

            if not sarvam_temp.exists() or sarvam_temp.stat().st_size == 0:
                raise RuntimeError("Sarvam ne audio file nahi banayi.")

            subprocess.run(
                [
                    "ffmpeg", "-hide_banner", "-y",
                    "-i", str(sarvam_temp),
                    "-codec:a", "libmp3lame",
                    "-b:a", "192k",
                    str(voice_path),
                ],
                check=True,
            )

            if not voice_path.exists() or voice_path.stat().st_size == 0:
                raise RuntimeError("Sarvam audio ko MP3 mein convert nahi kar paaye.")

            print("Sarvam Shubh voice ready:", voice_path)
            return

        except Exception as exc:
            print(f"WARNING: Sarvam voice failed ({type(exc).__name__}): {exc}")
            print("Fallback: Edge TTS use hoga.")
        finally:
            if sarvam_temp.exists():
                try:
                    sarvam_temp.unlink()
                except OSError:
                    pass

    elif not api_key:
        print("SARVAM_API_KEY nahi mili; Edge TTS fallback use hoga.")
    else:
        print("Sarvam SDK import nahi hua; Edge TTS fallback use hoga.")

    audio = edge_tts.Communicate(
        SCRIPT,
        VOICE,
        rate=VOICE_RATE,
        pitch=VOICE_PITCH,
    )
    await audio.save(str(voice_path))

    if not voice_path.exists() or voice_path.stat().st_size == 0:
        raise RuntimeError("Voice-over file create nahi hui.")

    print("Edge TTS fallback ready:", voice_path)


# --------------------------------------------------
# ORIGINAL AMBIENT BACKGROUND MUSIC
# NOTE: This is generated ambient tone, not licensed music.
# --------------------------------------------------

def make_music(path, seconds, sample_rate=22050):
    print("\n[2/5] Ambient background music generate ho raha hai...")

    chunk_size = 4096
    total_samples = int(seconds * sample_rate)

    with wave.open(str(path), "wb") as audio_file:
        audio_file.setnchannels(1)
        audio_file.setsampwidth(2)
        audio_file.setframerate(sample_rate)

        for start in range(0, total_samples, chunk_size):
            count = min(chunk_size, total_samples - start)
            frames = bytearray()

            for i in range(count):
                t = (start + i) / sample_rate
                fade_in = min(1.0, t / 2.0)
                fade_out = min(1.0, max(0.0, (seconds - t) / 2.0))
                fade = min(fade_in, fade_out)

                tone = (
                    0.55 * math.sin(2 * math.pi * 55.0 * t)
                    + 0.25 * math.sin(2 * math.pi * 82.4 * t)
                    + 0.12 * math.sin(2 * math.pi * 110.0 * t)
                )

                sample = int(
                    max(-1.0, min(1.0, tone * fade * 0.13)) * 32767
                )
                frames.extend(sample.to_bytes(2, "little", signed=True))

            audio_file.writeframes(frames)

    print("Background music ready:", path)


# --------------------------------------------------
# SUBTITLES
# --------------------------------------------------

def make_subtitles(path, duration, width, height):
    """Create ASS subtitles; timing is distributed, not word-aligned."""
    vertical = height > width
    font_size = 42 if not vertical else 46
    margin_lr = 70 if not vertical else 42
    margin_v = 48 if not vertical else 180

    with open(path, "w", encoding="utf-8-sig") as f:
        f.write(
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"PlayResX: {width}\n"
            f"PlayResY: {height}\n"
            "WrapStyle: 2\n"
            "ScaledBorderAndShadow: yes\n\n"
        )
        f.write(
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, "
            "SecondaryColour, OutlineColour, BackColour, Bold, "
            "Italic, BorderStyle, Outline, Shadow, Alignment, "
            "MarginL, MarginR, MarginV, Encoding\n"
        )
        f.write(
            f"Style: Default,Arial,{font_size},"
            "&H00FFFFFF,&H0000FFFF,&H00101010,&H80000000,"
            "-1,0,1,3,1,2,"
            f"{margin_lr},{margin_lr},{margin_v},1\n\n"
        )
        f.write(
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, "
            "MarginR, MarginV, Effect, Text\n"
        )

        count = len(SUBTITLE_LINES)

        def stamp(seconds):
            hours = int(seconds // 3600)
            minutes = int((seconds % 3600) // 60)
            secs = seconds % 60
            return f"{hours}:{minutes:02}:{secs:05.2f}"

        for index, line in enumerate(SUBTITLE_LINES):
            start = duration * index / count
            end = duration * (index + 1) / count
            safe_line = (
                line.replace("\\", r"\\")
                .replace("{", r"\{")
                .replace("}", r"\}")
            )
            f.write(
                f"Dialogue: 0,{stamp(start)},{stamp(end)},"
                f"Default,,0,0,0,,{safe_line}\n"
            )

    print("Subtitles ready:", path)


# --------------------------------------------------
# VIDEO RENDERING
# --------------------------------------------------

def render_video(
    voice_path,
    music_path,
    subtitle_path,
    output_path,
    width,
    height,
    duration,
):
    print(
        f"\nRendering {output_path.name} "
        f"({width}x{height})..."
    )

    subtitle_filter_path = ffmpeg_subtitle_path(subtitle_path)
    video_filter = (
        f"subtitles=filename='{subtitle_filter_path}':"
        f"original_size={width}x{height}"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x080B16:s={width}x{height}:r=30:d={duration}",
        "-i", str(voice_path),
        "-stream_loop", "-1",
        "-i", str(music_path),
        "-filter_complex",
        (
            "[1:a]volume=1.0[voice];"
            "[2:a]volume=0.10[music];"
            "[voice][music]"
            "amix=inputs=2:duration=first:dropout_transition=2,"
            "alimiter=limit=0.95[audio]"
        ),
        "-vf", video_filter,
        "-map", "0:v:0",
        "-map", "[audio]",
        "-t", f"{duration:.3f}",
        "-r", "30",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        "-shortest",
        str(output_path),
    ]

    run(command)

    if not output_path.exists() or output_path.stat().st_size < 20_000:
        raise RuntimeError(
            f"Video render fail hua ya file bahut chhoti hai: {output_path}"
        )

    print("Render complete:", output_path)


# --------------------------------------------------
# OUTPUT VALIDATION
# --------------------------------------------------

def verify_video(path, expected_width, expected_height):
    print("\nChecking:", path.name)
    result = subprocess.check_output(
        [
            "ffprobe",
            "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(path),
        ],
        text=True,
    ).strip()

    expected = f"{expected_width}x{expected_height}"
    if result != expected:
        raise RuntimeError(
            f"Resolution mismatch: {path.name}: expected {expected}, got {result}"
        )

    duration = get_duration(path)
    print("Resolution:", result)
    print(f"Duration: {duration:.2f} seconds")
    print(f"File size: {path.stat().st_size / 1024 / 1024:.2f} MB")


# --------------------------------------------------
# MAIN PIPELINE
# --------------------------------------------------

async def main():
    check_programs()

    voice_path = OUT / "voice.mp3"
    music_path = OUT / "ambient.wav"
    subtitle_path = OUT / "captions.ass"
    landscape_path = OUT / "youtube_landscape.mp4"
    vertical_path = OUT / "short_vertical.mp4"

    print("=" * 55)
    print("FACELESS VIDEO PIPELINE")
    print("=" * 55)

    await make_voice()

    voice_duration = get_duration(voice_path)
    duration = voice_duration + 1.5

    make_music(music_path, seconds=duration + 2.0)

    make_subtitles(
        subtitle_path, duration, width=1280, height=720
    )
    render_video(
        voice_path, music_path, subtitle_path, landscape_path,
        width=1280, height=720, duration=duration,
    )
    verify_video(landscape_path, expected_width=1280, expected_height=720)

    vertical_subtitle_path = OUT / "captions_vertical.ass"
    make_subtitles(
        vertical_subtitle_path, duration, width=720, height=1280
    )
    render_video(
        voice_path, music_path, vertical_subtitle_path, vertical_path,
        width=720, height=1280, duration=duration,
    )
    verify_video(vertical_path, expected_width=720, expected_height=1280)

    print("\n" + "=" * 55)
    print("SUCCESS: BOTH VIDEOS CREATED")
    print("=" * 55)
    print("Landscape:", landscape_path)
    print("Vertical: ", vertical_path)
    print("\nNote: This base pipeline uses a dark background, not stock footage.")
    print("For stock footage, run the separate stock pipeline.")


if __name__ == "__main__":
    asyncio.run(main())
