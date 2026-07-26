"""Tests for PersonaAnalyst (agent①) — RichPersona + StoryCore + degradation."""
from __future__ import annotations

import json

from echuu.core.persona_analyst import PersonaAnalyst, is_placeholder_persona
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
            "discourse_mode": "narrative",
            "mode_rationale": "主播在讲一段有明确时间线的亲身经历",
            "spine": "上周接了个甲方稿子，改到第八版崩溃的那一晚",
            "core_struggle": "到底是坚持自己的画风，还是为了恰饭妥协",
            "supporting_points": ["八轮修改磨掉了最初的表达", "甲方最终选择第一版"],
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
    assert sc.discourse_mode == "narrative"
    assert sc.mode_rationale
    assert len(sc.supporting_points) == 2
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
    assert "commentary" in prompt and "banter" in prompt
    assert "最多 2 条" in prompt
    assert "每段换一个隐喻" in prompt


def test_explicit_playful_direction_is_hard_constraint():
    payload = json.loads(_good_response())
    payload["story"].update({
        "discourse_mode": "commentary",
        "tone_mode": "serious",
        "depth_budget": "deep",
        "spine": "称呼意味着关系权限与解释权的静默移交",
        "supporting_points": ["默认签约", "责任外包"],
    })
    llm = FakeLLM(json.dumps(payload, ensure_ascii=False))
    _, core = PersonaAnalyst().analyze(
        "主播",
        "擅长调笑",
        "称呼玩笑",
        "故作认真后抖包袱",
        llm,
        tone_intent="playful_teasing",
        depth_budget="light",
        entertainment_mechanism="故作认真 + 吊胃口 + 反转",
    )
    assert len(llm.calls) == 2
    assert core.tone_mode == "playful_teasing"
    assert core.depth_budget == "light"
    assert core.discourse_mode == "banter"
    assert "权限" not in core.spine
    assert "反转" in core.entertainment_mechanism
    assert "用户指定语气：playful_teasing" in llm.calls[0]


def test_analyst_applies_tuning_guidance_without_changing_output_schema():
    llm = FakeLLM(_good_response())
    _, core = PersonaAnalyst().analyze(
        "n", "p", "t", "b", llm,
        tuning_guidance=[{
            "id": "n1",
            "category": "logic",
            "rule": "转折句必须补全结果。",
        }],
    )
    assert "clause_completeness" in llm.calls[0]
    assert "转折句必须补全结果" not in llm.calls[0]
    assert core.spine


def test_factuality_guidance_removes_unsupported_skeleton_details():
    payload = json.loads(_good_response())
    payload["story"]["discourse_mode"] = "advice"
    payload["story"]["spine"] = "我三年前靠没签合同的经历劝你换导师"
    payload["story"]["supporting_points"] = ["两篇论文", "左耳垂伤疤"]
    payload["story"]["story_beats"] = ["三年前开场", "摸左耳垂", "给出判断"]
    payload["persona"]["life_anchors"] = ["左耳垂伤疤", "屏保合影"]
    _, core = PersonaAnalyst().analyze(
        "主播", "有读博经历", "读博换导师", "擅长分析利弊",
        FakeLLM(json.dumps(payload, ensure_ascii=False)),
        tuning_guidance=[{
            "id": "n1",
            "category": "fabricated_detail",
            "rule": "不得补造日期、数字或身体特征。",
        }],
    )
    assert "三年前" not in core.spine
    assert "合同" not in core.spine
    assert core.supporting_points == (
        "确认当前是否仍能获得实现目标所需的有效支持",
        "比较继续与改变各自可确认的代价、流程和边界",
    )
    assert len(core.story_beats) == 3


def test_non_narrative_plan_is_trimmed_to_three_beats_and_two_anchors():
    payload = json.loads(_good_response())
    payload["story"]["discourse_mode"] = "advice"
    payload["story"]["story_beats"] = ["建立问题", "依据一", "依据二", "额外收尾"]
    payload["story"]["supporting_points"] = ["一", "二", "不应保留"]
    payload["persona"]["life_anchors"] = ["一", "二", "不应保留"]
    _, sc = PersonaAnalyst().analyze("n", "p", "t", "b", FakeLLM(json.dumps(payload)))
    assert sc.story_beats == ("建立问题", "依据一", "依据二")
    assert sc.supporting_points == ("一", "二")


def test_invalid_mode_uses_deterministic_topic_fallback():
    payload = json.loads(_good_response())
    payload["story"]["discourse_mode"] = "everything"
    _, sc = PersonaAnalyst().analyze(
        "主持人", "反应快、擅长接梗", "嘉宾联动破防挑战", "", FakeLLM(json.dumps(payload)),
    )
    assert sc.discourse_mode == "banter"


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


def test_model_chosen_playful_rejection_keeps_persona_on_auto_tone():
    """tone_intent=auto（默认）时语气门连拒两次，不该把人设一起丢掉。

    语气守门拒的是 story 的抽象化，不是 persona 本身。抢救分支原先只看
    requested_tone，而 auto 时它是空串 → 抢救永不成立 → 整场退化成
    _placeholder() 的硬编码占位符（verbal_tics=('那个','就是说')），实跑中已复现。
    """
    payload = json.loads(_good_response())
    payload["persona"]["identity"] = "传媒大二在读，爱把纠结讲成段子"
    payload["story"].update({
        "discourse_mode": "commentary",
        "tone_mode": "playful_teasing",   # 模型自己选的，用户没指定
        "depth_budget": "light",
        "spine": "称呼这件事其实是关系权限的静默移交",
        "supporting_points": ["责任外包", "默认签约"],
    })
    llm = FakeLLM(json.dumps(payload, ensure_ascii=False))

    rp, sc = PersonaAnalyst().analyze("小满", "大二女生主播", "暑假躺平还是实习", "", llm)

    assert len(llm.calls) == 2               # 拒了两次
    assert rp.identity == "传媒大二在读，爱把纠结讲成段子"
    assert not is_placeholder_persona(rp)    # 没有退化成占位符
    assert rp.verbal_tics != ("那个", "就是说")
    # story 仍然要被换成安全版本——被拒的是它
    assert "权限" not in sc.spine
    assert sc.depth_budget == "light"


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
