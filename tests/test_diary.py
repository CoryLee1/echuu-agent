import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1] / "echuu-web" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.diary import compose_diary, diary_title, is_public_diary, parse_diary_llm, tags_from_topic


class DiaryRules(unittest.TestCase):
    def test_default_visibility_is_public(self):
        self.assertTrue(is_public_diary({}))
        self.assertTrue(is_public_diary({"diary": {"visibility": "public"}}))
        self.assertFalse(is_public_diary({"diary": {"visibility": "private"}}))

    def test_title_never_recites_full_topic(self):
        topic = "搬家时把电饭锅落在旧房，半夜回去取却发现它还在保温"
        title = diary_title(topic, ["锅还亮着保温灯"], "小梅")
        self.assertNotEqual(title, topic)
        self.assertNotIn(topic, title)
        self.assertIn("保温", title)

    def test_short_topic_can_be_title(self):
        title = diary_title("午饭没胃口", [], "Echuu")
        self.assertIn("午饭没胃口", title)

    def test_title_falls_back_without_story_points(self):
        topic = "下雨天把伞借给陌生人，第二天在门口收到一张手写纸条"
        title = diary_title(topic, [], "小梅")
        self.assertNotEqual(title, topic)
        self.assertTrue(title.startswith("今晚"))

    def test_tags_stay_short(self):
        tags = tags_from_topic("出去送外卖送错了，最后和收错餐的人一起想办法补救", ["保温袋勒手"])
        self.assertTrue(tags)
        self.assertTrue(all(len(tag) <= 6 for tag in tags))


class DiaryCompose(unittest.TestCase):
    def test_compose_uses_script_lede_not_topic(self):
        topic = "下雨天把伞借给陌生人，第二天在门口收到一张手写纸条"
        session = SimpleNamespace(
            session_id="s1",
            topic=topic,
            character=SimpleNamespace(name="小梅"),
            voice_config=SimpleNamespace(voice_name="Cherry"),
            started_at=None,
            ended_at=None,
            status=SimpleNamespace(value="completed"),
            archive_status="completed",
            script_path="",
            session_metadata={
                "character_name": "小梅",
                "voice": "Cherry",
                "diary": {"visibility": "public"},
            },
        )
        diary = compose_diary(session)
        self.assertEqual(diary["visibility"], "public")
        self.assertNotEqual(diary["title"], topic)
        self.assertNotIn(topic, diary["lede"])

    def test_compose_uses_v4_speech_when_generic_lede_cached(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "full_script.json"
            script.write_text(
                '{"units":[{"lines":[{"text":"我对着便当发了好一会儿呆，一口都没动。"}]}]}',
                encoding="utf-8",
            )
            session = SimpleNamespace(
                session_id="v4-demo",
                topic="午饭没胃口",
                character=SimpleNamespace(name="Echuu"),
                voice_config=SimpleNamespace(voice_name="Cherry"),
                started_at=None,
                ended_at=None,
                status=SimpleNamespace(value="completed"),
                archive_status="completed",
                script_path=str(script),
                session_metadata={
                    "character_name": "Echuu",
                    "voice": "Cherry",
                    "diary": {
                        "visibility": "public",
                        "lede": "今晚聊了一件很小、但想起来还是会停一下的事。",
                    },
                },
            )
            diary = compose_diary(session)
            self.assertIn("便当", diary["lede"])


class DiaryLlmParse(unittest.TestCase):
    def test_parse_json_fence_and_reject_full_topic_title(self):
        topic = "搬家时把电饭锅落在旧房，半夜回去取却发现它还在保温"
        raw = """```json
{"title":"%s","lede":"我半夜摸回去，灯还亮着。","scene":"锅还温着。","voice_note":"嗓子停在门口。","tags":["保温灯","旧房"]}
```""" % topic
        parsed = parse_diary_llm(raw, topic=topic)
        self.assertEqual(parsed["title"], "")
        self.assertIn("灯还亮着", parsed["lede"])
        self.assertEqual(parsed["tags"], [])

    def test_parse_keeps_social_tags(self):
        parsed = parse_diary_llm(
            '{"title":"今晚，便当还热着","lede":"我对着盒子发呆，一口都没动。","scene":"筷子搁在盖上。","voice_note":"下午的嗓子还有点黏。","tags":["#今日份没胃口","胃比人诚实","便当"]}',
            topic="午饭没胃口",
        )
        self.assertIn("便当", parsed["title"])
        self.assertIn("发呆", parsed["lede"])
        self.assertEqual(parsed["tags"], ["今日份没胃口", "胃比人诚实"])


def load_tests(loader, tests, pattern):
    return tests


if __name__ == "__main__":
    unittest.main()
