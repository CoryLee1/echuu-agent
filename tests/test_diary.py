import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

BACKEND = Path(__file__).resolve().parents[1] / "echuu-web" / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from services.diary import compose_diary, diary_title, is_public_diary, tags_from_topic


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


def load_tests(loader, tests, pattern):
    return tests


if __name__ == "__main__":
    unittest.main()
