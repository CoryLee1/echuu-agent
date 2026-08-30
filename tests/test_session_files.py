import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "echuu-web" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.s3_archive import _s3_credentials
from services.session_files import resolve_session_dir, stage_compat_audio


class SessionFileResolve(unittest.TestCase):
    def test_rejects_path_escape(self):
        with self.assertRaises(FileNotFoundError):
            resolve_session_dir("../secret")

    def test_stages_compat_audio_into_scripts_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            audio_dir = root / "compat-audio"
            scripts_dir = root / "scripts"
            audio_dir.mkdir()
            scripts_dir.mkdir()
            (audio_dir / "v4-testhunt01-0.wav").write_bytes(b"RIFF")
            (audio_dir / "v4-testhunt01-2.wav").write_bytes(b"RIFF")
            (audio_dir / "v4-testhunt01-script.json").write_text('{"units":[{"lines":[{"text":"我有点没胃口"}]}]}', encoding="utf-8")
            (audio_dir / "v4-testhunt01-memory.json").write_text('{"story_points":["便利店"]}', encoding="utf-8")
            with patch.dict("os.environ", {"ECHUU_COMPAT_AUDIO_DIR": str(audio_dir)}), \
                    patch("services.session_files.SCRIPTS_DIR", scripts_dir):
                dest = stage_compat_audio("v4-testhunt01")
            self.assertEqual(dest, scripts_dir / "v4-testhunt01")
            self.assertTrue((dest / "v4-testhunt01-0.wav").exists())
            self.assertTrue((dest / "v4-testhunt01-2.wav").exists())
            self.assertTrue((dest / "full_script.json").exists())
            self.assertTrue((dest / "memory.json").exists())


class S3CredentialNames(unittest.TestCase):
    def test_accepts_project_s3_key_names(self):
        with patch.dict("os.environ", {
            "S3_ACCESS_KEY": "ak-test",
            "S3_SECRET_KEY": "sk-test",
        }, clear=False):
            os.environ.pop("AWS_ACCESS_KEY_ID", None)
            os.environ.pop("AWS_SECRET_ACCESS_KEY", None)
            self.assertEqual(_s3_credentials(), ("ak-test", "sk-test"))


if __name__ == "__main__":
    unittest.main()
