import math
import subprocess
from pathlib import Path

import audio_video_pipeline as base

ROOT = Path(__file__).resolve().parent.parent
STOCK = ROOT / "assets" / "stock"
SOURCE = ROOT / "output" / "voice_pipeline_test"
OUT = ROOT / "output" / "cinematic_test"
FPS = 30
TRANSITION = 0.35


def run(cmd):
    print("\n>", subprocess.list2cmdline([str(x) for x in cmd]))
    subprocess.run([str(x) for x in cmd], check=True)


def render_segment(clip, destination, width, height, duration, index):
    # Each clip is looped if needed, cropped to fill, then given gentle camera motion.
    zoom_expr = "min(zoom+0.0007,1.07)" if index % 2 == 0 else "if(eq(on,0),1.07,max(zoom-0.0007,1.0))"
    vf = (
        f"scale={width}:{height}:force_original_aspect_ratio=increase,"
        f"crop={width}:{height},setsar=1,"
        f"zoompan=z='{zoom_expr}':d=1:s={width}x{height}:fps={FPS},"
        "eq=contrast=1.08:saturation=0.82:brightness=-0.025,"
        "vignette=PI/5,"
        "fade=t=in:st=0:d=0.18,"
        f"fade=t=out:st={max(0.0, duration-0.22):.3f}:d=0.22,"
        "format=yuv420p"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-stream_loop", "-1", "-i", clip,
        "-vf", vf, "-an", "-t", f"{duration:.4f}",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p",
        destination
    ])
    if not destination.exists() or destination.stat().st_size < 20_000:
        raise RuntimeError(f"Scene render failed: {destination}")


def build_reel(clips, destination, width, height, total_duration, tag):
    if not clips:
        raise RuntimeError("No valid stock clips found in assets/stock.")
    transition = TRANSITION if len(clips) > 1 else 0.0
    segment_duration = (total_duration + transition * (len(clips) - 1)) / len(clips)
    segment_paths = []

    for i, clip in enumerate(clips):
        segment_path = OUT / f"{tag}_scene_{i+1:02d}.mp4"
        render_segment(
            clip, segment_path, width, height, segment_duration, i
        )
        segment_paths.append(segment_path)

    if len(segment_paths) == 1:
        segment_paths[0].replace(destination)
        return

    inputs = []
    for path in segment_paths:
        inputs += ["-i", str(path)]

    filters = []
    last_label = "v0"
    current_duration = segment_duration
    for i in range(1, len(segment_paths)):
        out_label = f"x{i}"
        offset = current_duration - transition
        filters.append(
            f"[{last_label}][{i}:v]xfade=transition=fade:"
            f"duration={transition}:offset={offset:.4f}[{out_label}]"
        )
        last_label = out_label
        current_duration = current_duration + segment_duration - transition

    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        *inputs,
        "-filter_complex", ";".join(filters),
        "-map", f"[{last_label}]",
        "-t", f"{total_duration:.3f}",
        "-r", str(FPS), "-c:v", "libx264", "-preset", "veryfast",
        "-crf", "22", "-pix_fmt", "yuv420p",
        destination
    ])
    if not destination.exists() or destination.stat().st_size < 20_000:
        raise RuntimeError(f"Reel render failed: {destination}")


def add_audio_and_subtitles(reel, voice, music, subtitles, destination,
                            width, height, duration):
    subtitle_path = base.ffmpeg_subtitle_path(Path(subtitles))
    # Voice is authoritative; music is kept low under narration.
    filter_complex = (
        "[1:a]volume=1.0[voice];"
        "[2:a]loudnorm=I=-18:TP=-2:LRA=7,volume=0.60[music];"
        "[voice][music]amix=inputs=2:duration=first:"
        "dropout_transition=2:normalize=0[audio]"
    )
    vf = (
        f"subtitles=filename='{subtitle_path}':"
        f"original_size={width}x{height},"
        "fade=t=in:st=0:d=0.35"
    )
    run([
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-i", reel, "-i", voice, "-stream_loop", "-1", "-i", music,
        "-filter_complex", filter_complex,
        "-vf", vf, "-map", "0:v:0", "-map", "[audio]",
        "-t", f"{duration:.3f}", "-r", str(FPS),
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "22",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k",
        "-movflags", "+faststart", destination
    ])
    base.verify_video(Path(destination), width, height)


def main():
    base.check_programs()
    OUT.mkdir(parents=True, exist_ok=True)

    voice = SOURCE / "voice.mp3"
    music = SOURCE / "ambient.wav"
    landscape_subs = SOURCE / "captions.ass"
    vertical_subs = SOURCE / "captions_vertical.ass"

    for path in (voice, music, landscape_subs, vertical_subs):
        if not path.exists():
            raise FileNotFoundError(f"Required test asset not found: {path}")

    clips = sorted(p for p in STOCK.glob("*.mp4") if p.stat().st_size > 50_000)
    if not clips:
        raise RuntimeError(f"No MP4 stock clips found in {STOCK}")

    voice_duration = base.get_duration(voice)
    duration = voice_duration + 1.0
    print(f"Using {len(clips)} clips; voice duration={voice_duration:.2f}s")
    print(f"All generated files will go to: {OUT}")

    landscape_reel = OUT / "cinematic_reel_landscape.mp4"
    vertical_reel = OUT / "cinematic_reel_vertical.mp4"
    landscape_out = OUT / "youtube_landscape_cinematic.mp4"
    vertical_out = OUT / "short_vertical_cinematic.mp4"

    build_reel(clips, landscape_reel, 1280, 720, duration, "landscape")
    build_reel(clips, vertical_reel, 720, 1280, duration, "vertical")

    add_audio_and_subtitles(
        str(landscape_reel), str(voice), str(music), str(landscape_subs),
        str(landscape_out), 1280, 720, duration
    )
    add_audio_and_subtitles(
        str(vertical_reel), str(voice), str(music), str(vertical_subs),
        str(vertical_out), 720, 1280, duration
    )

    print("\nCINEMATIC TEST RENDER COMPLETE")
    print("Landscape:", landscape_out)
    print("Vertical: ", vertical_out)
    print("Review both files before using them. No approved final exports were touched.")


if __name__ == "__main__":
    main()


