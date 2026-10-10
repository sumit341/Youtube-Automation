"""
Creates a simple text-card video from a plain-text narration file using FFmpeg.
This is a technical smoke test, not a complete production-grade editor.
Requires ffmpeg and ffprobe installed on the machine.
"""
import argparse
import subprocess
from pathlib import Path

def run(cmd):
    subprocess.run(cmd, check=True)

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--text", default="AI ko samajhne ka simple tareeqa")
    p.add_argument("--audio", help="Optional narration audio file (wav/mp3)")
    p.add_argument("--output", default="work/demo.mp4")
    p.add_argument("--duration", type=int, default=8)
    args = p.parse_args()
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Drawtext font support varies by FFmpeg build; this smoke test uses a plain background.
    duration = max(3, args.duration)
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"color=c=0x111827:s=1280x720:d={duration}:r=30",
    ]
    if args.audio:
        cmd += ["-i", args.audio]
    # Escape drawtext special characters conservatively.
    safe = args.text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'").replace("%", "\\%")
    cmd += ["-vf", f"drawtext=text='{safe}':fontcolor=white:fontsize=48:x=(w-text_w)/2:y=(h-text_h)/2",
            "-c:v", "libx264", "-pix_fmt", "yuv420p"]
    if args.audio:
        cmd += ["-c:a", "aac", "-shortest"]
    else:
        cmd += ["-an", "-t", str(duration)]
    cmd += [str(out)]
    run(cmd)
    print(f"Created {out}")

if __name__ == "__main__":
    main()
