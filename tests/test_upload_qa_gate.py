
import importlib.util
import os
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
UPLOAD_PATH = ROOT / "src" / "upload_video.py"


def load_upload_module():
    """Load upload script without requiring Google API packages."""
    names = [
        "google",
        "google.oauth2",
        "google.oauth2.credentials",
        "google.auth",
        "google.auth.transport",
        "google.auth.transport.requests",
        "googleapiclient",
        "googleapiclient.discovery",
        "googleapiclient.http",
    ]

    fake_modules = {
        name: types.ModuleType(name)
        for name in names
    }

    fake_modules["google.oauth2.credentials"].Credentials = type(
        "Credentials", (), {}
    )
    fake_modules["google.auth.transport.requests"].Request = type(
        "Request", (), {}
    )
    fake_modules["googleapiclient.discovery"].build = (
        lambda *args, **kwargs: None
    )
    fake_modules["googleapiclient.http"].MediaFileUpload = (
        lambda *args, **kwargs: None
    )

    spec = importlib.util.spec_from_file_location(
        "_upload_video_test_module",
        UPLOAD_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load src/upload_video.py")

    module = importlib.util.module_from_spec(spec)

    with patch.dict(sys.modules, fake_modules):
        spec.loader.exec_module(module)

    return module


upload_video = load_upload_module()


class UploadQAGateTests(unittest.TestCase):

    def test_unapproved_path_is_rejected(self):
        with self.assertRaisesRegex(
            SystemExit,
            "path is invalid|only the approved",
        ):
            upload_video.validate_approved_video(
                "unused-test.mp4"
            )

    def test_missing_approved_video_is_rejected(self):
        approved = (
            ROOT / "output" / "youtube_landscape_final.mp4"
        )

        with patch.object(
            Path,
            "resolve",
            side_effect=FileNotFoundError,
        ):
            with self.assertRaisesRegex(
                SystemExit,
                "does not exist",
            ):
                upload_video.validate_approved_video(
                    str(approved)
                )

    def test_approved_landscape_path_is_accepted(self):
        approved = (
            ROOT / "output" / "youtube_landscape_final.mp4"
        )

        with patch.object(
            Path,
            "resolve",
            return_value=approved,
        ):
            with patch.object(
                Path,
                "is_file",
                return_value=True,
            ):
                result = upload_video.validate_approved_video(
                    str(approved)
                )

        self.assertEqual(result, approved)

    def test_approved_vertical_path_is_accepted(self):
        approved = (
            ROOT / "output" / "short_vertical_final.mp4"
        )

        with patch.object(
            Path,
            "resolve",
            return_value=approved,
        ):
            with patch.object(
                Path,
                "is_file",
                return_value=True,
            ):
                result = upload_video.validate_approved_video(
                    str(approved)
                )

        self.assertEqual(result, approved)

    def test_qa_failure_blocks_upload(self):
        failed = types.SimpleNamespace(returncode=1)

        with patch.object(
            upload_video.subprocess,
            "run",
            return_value=failed,
        ):
            with self.assertRaisesRegex(
                SystemExit,
                "QA Gate HOLD: upload blocked",
            ):
                upload_video.require_qa_pass()

    def test_qa_pass_allows_gate_to_return(self):
        passed = types.SimpleNamespace(returncode=0)

        with patch.object(
            upload_video.subprocess,
            "run",
            return_value=passed,
        ) as run_mock:
            upload_video.require_qa_pass()

        self.assertEqual(run_mock.call_count, 1)
        self.assertEqual(
            run_mock.call_args.args[0],
            [sys.executable, "-m", "src.qa_gate"],
        )
        self.assertEqual(
            run_mock.call_args.kwargs["check"],
            False,
        )
        self.assertEqual(
            run_mock.call_args.kwargs["cwd"],
            str(ROOT),
        )

    def test_main_rejects_unapproved_path_before_token_access(self):
        with (
            patch.dict(
                os.environ,
                {"ENABLE_YOUTUBE_UPLOAD": "true"},
            ),
            patch.object(
                sys,
                "argv",
                [
                    "upload_video.py",
                    "--video",
                    "unused-test.mp4",
                    "--title",
                    "QA safety test",
                    "--privacy",
                    "private",
                ],
            ),
            patch.object(
                upload_video.Path,
                "exists",
            ) as exists_mock,
            patch.object(
                upload_video,
                "require_qa_pass",
            ) as qa_mock,
        ):
            with self.assertRaisesRegex(
                SystemExit,
                "path is invalid|only the approved",
            ):
                upload_video.main()

            exists_mock.assert_not_called()
            qa_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main(verbosity=2)
