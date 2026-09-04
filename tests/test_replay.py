import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

BACKEND = Path(__file__).resolve().parents[1] / "echuu-web" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.replay import load_replay_timeline, normalize_timeline, s3_public_url  # noqa: E402


def _session(tmp: Path, session_id: str = "s1", **extra):
    return SimpleNamespace(session_id=session_id, script_path=str(tmp / session_id / "full_script.json"), s3_prefix=None, **extra)


class NormalizeTimeline(unittest.TestCase):
    def test_keeps_only_playable_steps_sorted_by_anchor(self):
        raw = {
            "version": 1,
            "mode": "storytelling",
            "meta": {"name": "Cathy"},
            "total_duration": 5,
            "events": [
                {"type": "step", "speech": "第二句", "audio_url": "/audio/s1/step_1.wav", "t": 4.4, "duration": 2.0},
                {"type": "reasoning", "content": "thinking"},
                {"type": "step", "speech": "   ", "t": 9.0},
                {"type": "step", "speech": "第一句", "audio_url": "/audio/s1/step_0.wav", "t": 0, "duration": 3.84},
            ],
        }
        timeline = normalize_timeline(raw)
        self.assertEqual([e["speech"] for e in timeline["events"]], ["第一句", "第二句"])
        self.assertEqual(timeline["total_duration"], 6.4)
        self.assertEqual(timeline["meta"], {"name": "Cathy"})

    def test_missing_numbers_default_to_zero(self):
        timeline = normalize_timeline({"events": [{"speech": "x"}]})
        self.assertEqual(timeline["events"][0]["t"], 0.0)
        self.assertEqual(timeline["events"][0]["duration"], 0.0)
        self.assertEqual(timeline["mode"], "storytelling")


class LoadReplayTimeline(unittest.TestCase):
    def test_reads_local_timeline_next_to_script(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "s1").mkdir()
            (root / "s1" / "timeline.json").write_text(json.dumps({
                "events": [{"type": "step", "speech": "hi", "audio_url": "/audio/s1/step_0.wav", "t": 0, "duration": 1}]
            }), encoding="utf-8")
            timeline = load_replay_timeline(_session(root))
            self.assertIsNotNone(timeline)
            self.assertEqual(timeline["events"][0]["audio_url"], "/audio/s1/step_0.wav")

    def test_returns_none_without_timeline_or_prefix(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNone(load_replay_timeline(_session(Path(tmp))))

    def test_falls_back_to_s3_and_rewrites_audio_urls(self):
        payload = {"events": [{"type": "step", "speech": "hi", "audio_url": "/audio/s1/step_0.wav", "t": 0, "duration": 1}]}

        class FakeBody:
            def read(self):
                return json.dumps(payload).encode("utf-8")

        class FakeClient:
            def get_object(self, Bucket, Key):
                assert Key == "streaming_content/s1/timeline.json"
                return {"Body": FakeBody()}

        fake_boto3 = SimpleNamespace(client=lambda *_args, **_kwargs: FakeClient())
        with tempfile.TemporaryDirectory() as tmp, patch.dict(sys.modules, {"boto3": fake_boto3}), patch.dict(
            "os.environ", {"S3_BUCKET": "echuu-storage", "S3_REGION": "us-east-2"}
        ):
            session = _session(Path(tmp))
            session.s3_prefix = "streaming_content/s1/"
            timeline = load_replay_timeline(session)
            self.assertIsNotNone(timeline)
            self.assertEqual(
                timeline["events"][0]["audio_url"],
                "https://echuu-storage.s3.us-east-2.amazonaws.com/streaming_content/s1/step_0.wav",
            )

    def test_s3_public_url_uses_env_bucket(self):
        with patch.dict("os.environ", {"S3_BUCKET": "b", "S3_REGION": "r"}):
            self.assertEqual(s3_public_url("k/x.wav"), "https://b.s3.r.amazonaws.com/k/x.wav")


if __name__ == "__main__":
    unittest.main()
