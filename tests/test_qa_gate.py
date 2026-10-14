
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from src.qa_gate import check_video


class QAGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ffmpeg = shutil.which("ffmpeg")
        if not cls.ffmpeg:
            raise RuntimeError("ffmpeg is required for QA tests.")

        cls.temp_dir = tempfile.TemporaryDirectory()
        cls.temp_path = Path(cls.temp_dir.name)
        cls.valid_video = cls.temp_path / "valid_test.mp4"

        subprocess.run(
            [
                cls.ffmpeg, "-y",
                "-f", "lavfi", "-i",
                "testsrc=size=1280x720:rate=24",
                "-f", "lavfi", "-i",
                "sine=frequency=1000:sample_rate=44100",
                "-t", "5", "-shortest",
                "-c:v", "libx264", "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                str(cls.valid_video),
            ],
            check=True,
            capture_output=True,
            text=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.temp_dir.cleanup()

    def test_valid_video_passes(self):
        result = check_video({
            "name": "valid_test",
            "path": self.valid_video,
            "width": 1280,
            "height": 720,
        })
        self.assertEqual(result["status"], "PASS", result)

    def test_missing_video_is_held(self):
        result = check_video({
            "name": "missing_test",
            "path": self.temp_path / "does_not_exist.mp4",
            "width": 1280,
            "height": 720,
        })
        self.assertEqual(result["status"], "HOLD", result)

    def test_wrong_resolution_is_held(self):
        result = check_video({
            "name": "wrong_resolution_test",
            "path": self.valid_video,
            "width": 720,
            "height": 1280,
        })
        self.assertEqual(result["status"], "HOLD", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
