from echuu.core.persona_model import RichPersona
from echuu.core.unit import AcousticHint, ScriptLine, Show, Unit
from echuu.live.engine import EchuuLiveEngine
from echuu.live.state import Danmaku
from echuu.live.story_tokens import TokenHunt, compose_tangent_text, extract_tokens_from_line


def test_extract_tokens_uses_key_info_and_skips_stopwords():
    tokens = extract_tokens_from_line(
        "那天晚上我把伞忘在前任那儿了",
        ["伞", "的", "那天晚上", "前任", "然后"],
        "u0l1",
    )
    labels = [item["label"] for item in tokens]
    assert labels[:3] == ["伞", "那天晚上", "前任"]
    assert tokens[0]["kind"] == "item"
    assert tokens[1]["kind"] == "time"
    assert tokens[2]["kind"] == "person"
    assert len(tokens) <= 4


def test_extract_tokens_falls_back_to_speech_when_key_info_empty():
    tokens = extract_tokens_from_line("那天晚上我把伞忘在前任那儿了", [], "u0l1")
    labels = [item["label"] for item in tokens]
    assert "那天晚上" in labels
    assert "前任" in labels
    assert 1 <= len(tokens) <= 4


def test_extract_tokens_classifies_place():
    tokens = extract_tokens_from_line("是那天晚上我蹲在便利店冷", [], "u0l2")
    labels = [item["label"] for item in tokens]
    assert "那天晚上" in labels
    assert "便利店" in labels
    assert any(item["kind"] == "place" for item in tokens if item["label"] == "便利店")


def test_collect_three_crafts_when_ready():
    hunt = TokenHunt()
    hunt.collect({"id": "a", "label": "伞", "kind": "item"})
    hunt.collect({"id": "b", "label": "那天晚上", "kind": "time"})
    hunt.collect({"id": "c", "label": "前任", "kind": "person"})
    result = hunt.maybe_craft(True)
    assert result["crafted"] is not None
    assert [item["label"] for item in result["crafted"]] == ["伞", "那天晚上", "前任"]
    assert result["slots"] == []
    assert result["pending"] == result["crafted"]


def test_collect_holds_until_cooldown():
    hunt = TokenHunt()
    hunt.collect({"id": "a", "label": "伞", "kind": "item"})
    hunt.collect({"id": "b", "label": "那天晚上", "kind": "time"})
    hunt.collect({"id": "c", "label": "前任", "kind": "person"})
    held = hunt.maybe_craft(False)
    assert held["crafted"] is None
    assert len(held["slots"]) == 3
    released = hunt.maybe_craft(True)
    assert released["crafted"] is not None


def test_collect_accepts_label_only_and_crafts_on_third():
    hunt = TokenHunt()
    hunt.collect({"label": "伞"})
    hunt.collect("那天晚上")
    result = hunt.collect({"id": "", "label": "前任"})
    crafted = hunt.maybe_craft(True)
    assert len(result["slots"]) + (3 if crafted["crafted"] else 0) >= 3
    assert crafted["crafted"] is not None
    assert [item["label"] for item in crafted["crafted"]] == ["伞", "那天晚上", "前任"]


def test_compose_tangent_text_joins_labels():
    text = compose_tangent_text([
        {"label": "伞"},
        {"label": "那天晚上"},
        {"label": "前任"},
    ])
    assert "伞" in text and "那天晚上" in text and "前任" in text


def _engine_with(queue):
    persona = RichPersona(identity="前HR现插画师", belief="b", flaw="f", verbal_tics=("我跟你讲",))
    show = Show(
        persona=persona,
        topic="商稿稿费",
        units=[Unit(index=0, time_window=(0, 75), acoustic=AcousticHint(), lines=[
            ScriptLine(id="u0l0", text="第一句", stage="hook"),
        ])],
    )
    engine = EchuuLiveEngine.__new__(EchuuLiveEngine)
    engine.on_steering = None
    state = type("S", (), {})()
    state.show = show
    state.topic = show.topic
    state.danmaku_queue = list(queue)
    engine.state = state
    return engine


def test_pick_danmaku_prefers_tangent():
    engine = _engine_with([
        Danmaku.from_text("普通弹幕", user="a"),
        Danmaku.from_text("¥100 加油", user="c"),
        Danmaku.from_input("沿着线索", user="host", kind="tangent"),
    ])
    picked = engine._pick_danmaku()
    assert picked.kind == "tangent"
    assert picked.user == "host"


if __name__ == "__main__":
    test_extract_tokens_uses_key_info_and_skips_stopwords()
    test_extract_tokens_falls_back_to_speech_when_key_info_empty()
    test_extract_tokens_classifies_place()
    test_collect_three_crafts_when_ready()
    test_collect_holds_until_cooldown()
    test_collect_accepts_label_only_and_crafts_on_third()
    test_compose_tangent_text_joins_labels()
    test_pick_danmaku_prefers_tangent()
    print("ok")
