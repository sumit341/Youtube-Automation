import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import cinematic_test_renderer as renderer

STAGING = ROOT / "output" / "cinematic_staging"


def main():
    # Never overwrite an existing staging directory or its contents.
    if STAGING.exists():
        raise FileExistsError(
            f"Refusing to overwrite existing staging directory: {STAGING}"
        )

    STAGING.mkdir(parents=True)

    # Redirect all renderer-generated scenes and videos to staging.
    renderer.OUT = STAGING

    print("=" * 60)
    print("ISOLATED CINEMATIC STAGING RUN")
    print(f"Input voice/assets: {renderer.SOURCE}")
    print(f"Stock clips:        {renderer.STOCK}")
    print(f"Output directory:   {STAGING}")
    print("Approved production exports will not be targeted.")
    print("=" * 60)

    renderer.main()

    expected = [
        STAGING / "youtube_landscape_cinematic.mp4",
        STAGING / "short_vertical_cinematic.mp4",
    ]

    for path in expected:
        if not path.is_file() or path.stat().st_size < 20_000:
            raise RuntimeError(f"Expected output missing or too small: {path}")
        print(f"CREATED: {path.name} ({path.stat().st_size:,} bytes)")

    print("\nSTAGING RENDER COMPLETE")
    print("Review and QA these files before any production integration.")


if __name__ == "__main__":
    main()
