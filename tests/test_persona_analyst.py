"""Tests for PersonaAnalyst (agent①) — RichPersona + StoryCore + degradation."""
from __future__ import annotations

import json

from echuu.core.persona_analyst import PersonaAnalyst
from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


class RaisingLLM:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("provider down")


def _good_response() -> str:
    return json.dumps({
        "persona": {
            "identity": "25 岁前 HR，现自由插画师",
            "belief": "做喜欢的事比薪水重要",
            "flaw": "一被夸就慌到转移话题",
            "verbal_tics": ["我跟你讲", "对吧"],
            "situational_weaknesses": ["一谈钱就回避"],
            "contrast_hook": "嘴上洒脱，手腕上全是焦虑便签",
            "life_anchors": ["腕上贴满便签", "凌晨三点改稿"],
            "title_hook": "从 HR 辞职那天我把便签全贴手上了",
            "visual_anchor": "腕上便签",
        },
        "story": {
            "spine": "上周接了个甲方稿子，改到第八版崩溃的那一晚",
            "core_struggle": "到底是坚持自己的画风，还是为了恰饭妥协",
            "twist": "甲方最后说还是用第一版，那版我画了十分钟",
            "central_contrast": "做喜欢的事反而更累",
            "emotional_undercurrent": "兴奋 → 自我怀疑 → 脆弱坦白",
            "story_beats": ["起：接到稿子很兴奋", "承：改到第八版", "转：甲方要第一版", "合：对着屏幕笑出声"],
            "punchline_seeds": ["热爱是有 KPI 的", "我把热爱过成了加班"],
            "hook_angle": "辞职那天我哭了一整夜，但没人知道",
        },
    })


def test_analyze_happy_path():
    llm = FakeLLM(_good_response())
    rp, sc = PersonaAnalyst().analyze("小梅", "前 HR 转插画师", "转行体感", "", llm)
    assert isinstance(rp, RichPersona) and isinstance(sc, StoryCore)
    assert rp.identity.startswith("25 岁")
    assert "我跟你讲" in rp.verbal_tics
    assert rp.situational_weaknesses
    assert rp.contrast_hook
    assert rp.life_anchors
    assert sc.spine and sc.hook_angle
    assert sc.punchline_seeds
    assert sc.core_struggle           # 核心纠结点
    assert sc.twist                   # 翻转
    assert 2 <= len(sc.story_beats) <= 4  # 一件事的若干阶段（自适应 2~4）
    assert rp.flaw  # I4


def test_analyze_single_call_on_success():
    llm = FakeLLM(_good_response())
    PersonaAnalyst().analyze("n", "p", "t", "b", llm)
    assert len(llm.calls) == 1


def test_prompt_asks_for_grounded_variety_twist():
    llm = FakeLLM(_good_response())
    PersonaAnalyst().analyze("n", "p", "t", "b", llm)
    prompt = llm.calls[0]
    assert "接地气" in prompt
    assert "生活化" in prompt
    assert "禁止" in prompt and "实体化协议" in prompt


def test_analyze_strips_code_fence():
    llm = FakeLLM(f"```json\n{_good_response()}\n```")
    rp, sc = PersonaAnalyst().analyze("n", "p", "t", "b", llm)
    assert rp.identity.startswith("25 岁")


def test_analyze_invalid_json_degrades():
    llm = FakeLLM("not json at all {{{")
    rp, sc = PersonaAnalyst().analyze("小梅", "前 HR", "转行", "", llm)
    assert rp.flaw            # I4: 永不为空
    assert rp.verbal_tics     # 占位也给语癖
    assert sc.spine
    assert len(llm.calls) == 2  # retried once


def test_analyze_llm_exception_degrades_not_crash():
    rp, sc = PersonaAnalyst().analyze("小梅", "前 HR", "转行 6 个月", "", RaisingLLM())
    assert rp.flaw
    assert isinstance(sc, StoryCore)
    assert "转行 6 个月" in sc.spine or sc.spine


def test_analyze_missing_axis_degrades():
    """合法 JSON 但三轴缺 flaw → 退化（flaw 仍非空）。"""
    payload = json.dumps({
        "persona": {"identity": "A", "belief": "B"},  # flaw 缺
        "story": {"spine": "S"},
    })
    rp, _ = PersonaAnalyst().analyze("n", "p", "t", "b", FakeLLM(payload))
    assert rp.flaw


def test_placeholder_survives_whitespace():
    """persona 为纯空白字符串时不应在 _placeholder 里抛 IndexError（I4: flaw 永不为空）。"""
    rp, sc = PersonaAnalyst().analyze("n", "   ", "t", "b", RaisingLLM())
    assert rp.flaw
    assert isinstance(sc, StoryCore)


from echuu.core.persona_dossier import CharacterDossier, Conflict, BehaviorRules


class _CapturingLLM:
    def __init__(self, payload): self._p, self.prompts = payload, []
    def generate(self, prompt):
        self.prompts.append(prompt); return self._p


def test_analyze_injects_dossier_into_prompt():
    import json
    payload = json.dumps({
        "persona": {"identity": "i", "belief": "b", "flaw": "f",
                    "verbal_tics": ["诶"], "situational_weaknesses": ["一紧张就绕"],
                    "contrast_hook": "h", "life_anchors": ["便利贴"],
                    "title_hook": "t", "visual_anchor": "v"},
        "story": {"spine": "s", "core_struggle": "cs", "twist": "tw",
                  "central_contrast": "cc", "emotional_undercurrent": "eu",
                  "story_beats": ["起", "转", "合"], "punchline_seeds": ["p"],
                  "hook_angle": "ha"},
    }, ensure_ascii=False)
    from echuu.core.persona_analyst import PersonaAnalyst
    llm = _CapturingLLM(payload)
    dossier = CharacterDossier(
        expanded_bio="", conflict=Conflict(statement="她从不拒绝别人，但心里在记账"),
        behavior_rules=BehaviorRules(contradiction="嘴上没事，行为拖延"))
    PersonaAnalyst().analyze("n", "温柔女孩", "帮朋友做决定", "", llm=llm, dossier=dossier)
    assert "她从不拒绝别人，但心里在记账" in llm.prompts[0]


def test_analyze_without_dossier_unchanged():
    import json
    payload = json.dumps({"persona": {"identity": "i", "belief": "b", "flaw": "f"},
                          "story": {"spine": "s"}}, ensure_ascii=False)
    from echuu.core.persona_analyst import PersonaAnalyst
    llm = _CapturingLLM(payload)
    PersonaAnalyst().analyze("n", "p", "t", "", llm=llm)  # 不传 dossier
    assert "核心冲突" not in llm.prompts[0]
