"""PersonaCard：解析、空卡判定、prompt 渲染、analyst 口癖钉死。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echuu.core.persona_card import PersonaCard

CATHY = {
    "name": "Cathy",
    "tagline": "温柔敏锐的猫娘观察者",
    "speech_tics": ["喵", "诶嘿"],
    "audience_nickname": "猫粮供应商们",
    "metaphor_domain": "一切都用猫的世界观解释",
    "stances": ["坚决反对早起"],
    "fears": ["被说其实是狗派"],
    "prides": ["耳朵是全直播圈最灵的"],
    "running_gags": ["本喵的迷惑人类行为大赏"],
}


def test_from_dict_roundtrip():
    card = PersonaCard.from_dict(CATHY)
    assert card is not None
    assert card.speech_tics == ("喵", "诶嘿")
    assert card.audience_nickname == "猫粮供应商们"
    assert not card.is_empty()


def test_from_dict_rejects_empty():
    assert PersonaCard.from_dict(None) is None
    assert PersonaCard.from_dict({}) is None
    assert PersonaCard.from_dict({"name": "X", "tagline": "只有一句话"}) is None  # 无任何结构字段


def test_render_lists_only_nonempty_fields():
    card = PersonaCard.from_dict({"speech_tics": ["喵"], "fears": ["打雷"]})
    text = card.render_for_prompt()
    assert "口癖" in text and "喵" in text
    assert "雷点" in text and "打雷" in text
    assert "骄傲点" not in text  # 空字段不渲染


def test_analyst_pins_card_tics():
    """卡片口癖必须钉死 RichPersona（不许 analyst 自己发明）。"""
    from echuu.core.persona_analyst import PersonaAnalyst

    class FakeLLM:
        def generate(self, prompt):
            assert "猫粮供应商们" in prompt  # 卡片进了 prompt
            return (
                '{"persona": {"identity": "猫娘观察者", "belief": "人类都需要猫", '
                '"flaw": "一被夸就竖尾巴", "verbal_tics": ["analyst自编的口癖"], '
                '"situational_weaknesses": [], "contrast_hook": "", "life_anchors": [], '
                '"title_hook": "", "visual_anchor": ""}, '
                '"story": {"spine": "一件事", "core_struggle": "纠结", "twist": "翻转", '
                '"central_contrast": "", "emotional_undercurrent": "", '
                '"story_beats": ["起", "转", "合"], "punchline_seeds": [], "hook_angle": ""}}'
            )

    card = PersonaCard.from_dict(CATHY)
    rp, _ = PersonaAnalyst().analyze(
        name="Cathy", persona="猫娘", topic="云养猫", background="", llm=FakeLLM(), card=card,
    )
    assert rp.verbal_tics == ("喵", "诶嘿")  # 卡片钉死，不采纳 analyst 自编
