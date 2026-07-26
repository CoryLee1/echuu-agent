"""Tests for ScriptWriter (agent②) — story-core authoring + degradation."""
from __future__ import annotations

import json

import pytest

from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore
from echuu.core.unit import Unit
from echuu.core.unit_planner import UnitPlanner
from echuu.generators.script_writer import ScriptWriter


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


class FakeLLMSequence:
    def __init__(self, responses: list[str]):
        self.responses = responses
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        index = min(len(self.calls) - 1, len(self.responses) - 1)
        return self.responses[index]


@pytest.fixture
def persona() -> RichPersona:
    return RichPersona(
        identity="25 岁前 HR，现自由插画师",
        belief="做喜欢的事比薪水重要",
        flaw="一被夸就慌",
        verbal_tics=("我跟你讲", "对吧"),
        situational_weaknesses=("一谈钱就回避",),
        contrast_hook="嘴上洒脱手腕全是焦虑便签",
        life_anchors=("腕上便签",),
        title_hook="辞职那天我把便签贴手上了",
        visual_anchor="腕上便签",
    )


@pytest.fixture
def core() -> StoryCore:
    return StoryCore(
        spine="改到第八版崩溃的那一晚",
        core_struggle="坚持画风还是恰饭妥协",
        supporting_points=("八轮修改磨掉最初表达", "甲方最终仍选择第一版"),
        twist="甲方最后要的是我十分钟画的第一版",
        central_contrast="做喜欢的事反而更累",
        emotional_undercurrent="兴奋→怀疑→坦白",
        story_beats=("起：接稿很兴奋", "承：改到第八版", "转：甲方要第一版", "合：笑出声"),
        punchline_seeds=("热爱是有 KPI 的",),
        hook_angle="辞职那天我哭了一整夜",
    )


@pytest.fixture
def units():
    return UnitPlanner().plan()


def _resp(lines_per_unit=3) -> str:
    units = []
    for i in range(4):
        lines = [{"text": f"unit{i} 第{j}句 嗯…那个——", "interruption_cost": 0.5}
                 for j in range(lines_per_unit)]
        units.append({
            "index": i,
            "purpose": "建立主轴" if i == 0 else "推进主轴",
            "spine_link": f"第{i + 1}步推进同一件事",
            "lines": lines,
        })
    return json.dumps({"units": units})


def test_write_happy_path(persona, core, units):
    llm = FakeLLM(_resp())
    out = ScriptWriter(llm).write(persona, core, units, examples="", topic="转行")
    assert len(out) == 4
    for u in out:
        assert len(u.lines) == 3
    # 不再硬塞 rupture
    assert all(not l.is_rupture for u in out for l in u.lines)


def test_write_single_call(persona, core, units):
    llm = FakeLLM(_resp())
    ScriptWriter(llm).write(persona, core, units, topic="转行")
    assert len(llm.calls) == 1


def test_prompt_contains_persona_and_core(persona, core, units):
    llm = FakeLLM(_resp())
    ScriptWriter(llm).write(persona, core, units, examples="【真实案例】xxx", topic="转行")
    p = llm.calls[0]
    assert persona.identity in p
    assert "我跟你讲" in p              # 语癖注入
    assert core.spine in p              # 故事内核
    assert core.core_struggle in p      # 核心纠结点
    assert "八轮修改磨掉最初表达" in p  # 支撑点
    assert core.twist in p              # 翻转
    assert "起：接稿很兴奋" in p         # story_beats 进了 rails
    assert core.hook_angle in p
    assert "热爱是有 KPI 的" in p        # 金句种子
    assert "真实案例" in p              # few-shot 注入
    assert "碎碎念" in p                # 硬要求出现在 prompt
    assert "求共鸣" in p or "提问" in p  # 提问式互动开场
    assert "单核心写作契约" in p
    assert "spine_link" in p


def test_writer_distinguishes_source_facts_from_model_hypotheses(persona, core, units):
    llm = FakeLLM(_resp())
    ScriptWriter(llm).write(
        persona, core, units, topic="转行",
        source_material={"persona": "用户只说自己是插画师", "background": "", "topic": "转行"},
        tuning_guidance=[{
            "id": "n1",
            "category": "fabricated_detail",
            "rule": "不得补造人物履历。",
        }],
    )
    prompt = llm.calls[0]
    assert "可当作事实的原始输入" in prompt
    assert "用户只说自己是插画师" in prompt
    assert "fact_grounding" in prompt
    assert "不得补造人物履历" not in prompt


def test_write_invalid_json_degrades(persona, core, units):
    llm = FakeLLM("totally not json")
    out = ScriptWriter(llm).write(persona, core, units, topic="转行")
    assert len(out) == 4
    assert all(len(u.lines) >= 2 for u in out)
    assert len(llm.calls) == 2  # retried once


def test_write_short_units_degrades(persona, core, units):
    short = json.dumps({"units": [{"index": 0, "lines": [{"text": "x"}]}]})
    llm = FakeLLM(short)
    out = ScriptWriter(llm).write(persona, core, units, topic="转行")
    assert len(out) == 4
    assert all(len(u.lines) >= 2 for u in out)


def test_write_rejects_ungrounded_high_concept_turns(persona, core, units):
    """没被 topic/persona/core 铺垫的病历/协议式硬转弯应重试。"""
    bad = json.dumps({
        "units": [
            {"index": 0, "purpose": "建立主轴", "spine_link": "建立普通约稿场景", "lines": [
                {"text": "我在便利店门口等甲方，手里攥着热豆浆。"},
                {"text": "他迟到十分钟，我已经把杯套抠成纸屑。"},
            ]},
            {"index": 1, "purpose": "提供依据", "spine_link": "错误地引入无依据设定", "lines": [
                {"text": "然后平台弹出实体化过渡协议，右下角是我三年前住院病历号。"},
                {"text": "我突然明白这不是约稿，是命运系统在结算。"},
            ]},
            {"index": 2, "purpose": "提供依据", "spine_link": "错误地继续设定", "lines": [
                {"text": "协议开始扫描我的灵魂 KPI，我连豆浆都不敢喝。"},
                {"text": "这时候甲方说第一版像人画的，后面像服务器加班。"},
            ]},
            {"index": 3, "purpose": "收束主轴", "spine_link": "错误地收束设定", "lines": [
                {"text": "最后我把协议锁进抽屉，继续画第一版。"},
                {"text": "热豆浆凉透了，但命运系统说可以报销。"},
            ]},
        ]
    })
    good = json.dumps({
        "units": [
            {"index": 0, "purpose": "建立主轴", "spine_link": "建立修改场景", "lines": [
                {"text": "我在便利店门口等甲方，热豆浆烫得我换了三次手。"},
                {"text": "他迟到十分钟，我已经把杯套抠成纸屑。"},
            ]},
            {"index": 1, "purpose": "提供依据", "spine_link": "说明修改磨掉原始表达", "lines": [
                {"text": "他一开口说第八版很好，就是少了第一版那股傻劲。"},
                {"text": "我说那股傻劲已经被您七轮意见腌入味了。"},
            ]},
            {"index": 2, "purpose": "给出判断", "spine_link": "揭示核心反差", "lines": [
                {"text": "我当场笑出声：原来我熬夜修掉的，全是他要买的。"},
                {"text": "更离谱的是，他还夸我第一版有松弛感。"},
            ]},
            {"index": 3, "purpose": "收束主轴", "spine_link": "回收约稿经历", "lines": [
                {"text": "最后我把第一版文件名改成热豆浆，不然太像工伤证明。"},
                {"text": "下次谁再说松弛感，我先给他递杯凉的。"},
            ]},
        ]
    })
    llm = FakeLLMSequence([bad, good])

    out = ScriptWriter(llm).write(persona, core, units, topic="转行")

    assert len(llm.calls) == 2
    joined = "\n".join(line.text for unit in out for line in unit.lines)
    assert "实体化过渡协议" not in joined
    assert "住院病历号" not in joined
    assert "热豆浆" in joined
    assert out[1].spine_link == "说明修改磨掉原始表达"


def test_write_rejects_missing_spine_link(persona, core, units):
    payload = json.loads(_resp())
    payload["units"][1]["spine_link"] = ""
    llm = FakeLLM(json.dumps(payload))
    out = ScriptWriter(llm).write(persona, core, units, topic="转行")
    assert len(llm.calls) == 2
    assert all(unit.purpose == "生成失败占位" for unit in out)


def test_feedback_gate_rewrites_unsupported_numbers_body_and_contract(persona, core, units):
    def payload(first_line: str) -> str:
        return json.dumps({
            "units": [{
                "index": i,
                "purpose": "建立主轴" if i == 0 else "推进主轴",
                "spine_link": "始终回答是否应该换导师",
                "lines": [
                    {"text": first_line if i == 0 else "这段只解释原始问题。"},
                    {"text": "判断依据只使用用户已经提供的信息。"},
                ],
            } for i in range(4)],
            "planted_gags": [],
        }, ensure_ascii=False)

    llm = FakeLLMSequence([
        payload("我三年前左耳垂留了疤，错的是当初没签合同。"),
        payload("先确认目前是否还能得到有效的学术指导。"),
    ])
    writer = ScriptWriter(llm)
    out = writer.write(
        persona, core, units, topic="读博换导师",
        source_material={
            "persona": "有读博经历的学术区主播",
            "background": "会分析利弊",
            "topic": "读博换导师",
        },
        tuning_guidance=[
            {"category": "fabricated_detail", "rule": "禁止补造细节"},
            {"category": "world_knowledge", "rule": "增加领域常识校验"},
        ],
    )

    assert len(llm.calls) == 2
    assert "CONTRACT=" in llm.calls[1]
    assert len(llm.calls[1]) < len(llm.calls[0])
    assert writer.last_quality_gate == {
        "retried": True,
        "sanitized": False,
        "passed": True,
        "first_issues": ["unsupported_specific_detail"],
        "retry_issues": [],
        "first_issue_details": [
            "number:三年",
            "detail:耳垂",
            "domain:没签合同",
        ],
        "retry_issue_details": [],
        "post_sanitize_issues": [],
        "post_sanitize_issue_details": [],
    }
    joined = "\n".join(line.text for unit in out for line in unit.lines)
    assert "三年前" not in joined
    assert "耳垂" not in joined
    assert "没签合同" not in joined


def test_light_playful_gate_rejects_abstract_reframes_and_stage_directions(persona, units):
    playful_core = StoryCore(
        spine="把答案吊到最后一句再抖包袱",
        discourse_mode="banter",
        tone_mode="playful_teasing",
        depth_budget="light",
        entertainment_mechanism="故作认真 + 吊胃口 + 截断反转",
        story_beats=("接住玩笑", "继续吊胃口", "轻巧收尾", "道别"),
    )

    def payload(first_line: str) -> str:
        return json.dumps({
            "units": [{
                "index": i,
                "purpose": "接住玩笑" if i == 0 else "推进同一玩笑",
                "spine_link": "继续吊住同一个答案",
                "lines": [
                    {"text": first_line if i == 0 else "我就再多停一会儿，不急着回答。"},
                    {"text": "好啦，答案已经到嘴边了——下次再说。"},
                ],
            } for i in range(4)],
        }, ensure_ascii=False)

    llm = FakeLLMSequence([
        payload(
            "这是临时许可证，0.3 seconds 后开始倒计时。"
            "*ASMR mic brush, then 0.8s silence* consent certificate required。（转笔停半拍）"
        ),
        payload("你们越催，我越想故作认真地把答案多停片刻。"),
    ])
    writer = ScriptWriter(llm)
    out = writer.write(
        persona,
        playful_core,
        units,
        topic="称呼玩笑",
        source_material={
            "topic": "称呼玩笑",
            "tone_intent": "playful_teasing",
            "depth_budget": "light",
            "entertainment_mechanism": "故作认真 + 吊胃口 + 截断反转",
        },
        tuning_guidance=[{"category": "fabricated_detail", "rule": "禁止补造数字"}],
    )

    assert len(llm.calls) == 2
    joined = "\n".join(line.text for unit in out for line in unit.lines)
    assert "许可证" not in joined
    assert "0.3 seconds" not in joined
    assert "转笔" not in joined
    assert "ASMR mic brush" not in joined
    assert "consent" not in joined
    assert "certificate" not in joined
    assert "故作认真" in joined


def test_feedback_gate_rejects_invented_object_and_audience_reaction(persona, units):
    playful_core = StoryCore(
        spine="接住称呼玩笑并把答案吊到最后",
        discourse_mode="banter",
        tone_mode="playful_teasing",
        depth_budget="light",
        story_beats=("接住玩笑", "继续吊胃口", "轻巧收尾", "道别"),
    )

    def payload(first_line: str) -> str:
        return json.dumps({
            "units": [{
                "index": i,
                "purpose": "接住玩笑",
                "spine_link": "继续吊住同一个答案",
                "lines": [
                    {"text": first_line if i == 0 else "Okay，我再吊你们一下胃口。"},
                    {"text": "答案到了嘴边——先不说。"},
                ],
            } for i in range(4)],
        }, ensure_ascii=False)

    writer = ScriptWriter(FakeLLMSequence([
        payload("Not while I'm holding this tea cup—chat just dropped a hundred messages."),
        payload("Okay，这个称呼我听见了，但答案先留到最后。"),
    ]))
    out = writer.write(
        persona,
        playful_core,
        units,
        topic="Daddy称呼玩笑",
        source_material={"topic": "Daddy称呼玩笑"},
        tuning_guidance=[{"category": "fabricated_detail", "rule": "禁止补造细节"}],
    )

    assert writer.last_quality_gate["passed"] is True
    assert "detail:tea cup" in writer.last_quality_gate["first_issue_details"]
    assert any(
        detail.startswith("fabricated_audience:")
        for detail in writer.last_quality_gate["first_issue_details"]
    )
    joined = "\n".join(line.text for unit in out for line in unit.lines)
    assert "tea cup" not in joined
    assert "hundred messages" not in joined


def test_safe_surface_sanitizer_removes_stage_notes_and_blurs_counts(persona, units):
    playful_core = StoryCore(
        spine="把称呼玩笑的答案吊到最后",
        discourse_mode="banter",
        tone_mode="playful_teasing",
        depth_budget="light",
        story_beats=("接住玩笑", "继续吊胃口", "轻巧收尾", "道别"),
    )

    payload = json.dumps({
        "units": [{
            "index": i,
            "purpose": "继续吊胃口",
            "spine_link": "靠近同一个答案",
            "lines": [
                {"text": "（停顿半秒，轻笑）Okay，我把答案再说三遍。"},
                {"text": "最后半句先留着，you know。"},
            ],
        } for i in range(4)],
    }, ensure_ascii=False)
    writer = ScriptWriter(FakeLLM(payload))
    out = writer.write(
        persona,
        playful_core,
        units,
        topic="Daddy称呼玩笑",
        source_material={"topic": "Daddy称呼玩笑"},
        tuning_guidance=[{"category": "fabricated_detail", "rule": "禁止补造细节"}],
    )

    assert writer.last_quality_gate["passed"] is True
    assert writer.last_quality_gate["sanitized"] is True
    assert writer.last_quality_gate["post_sanitize_issues"] == []
    joined = "\n".join(line.text for unit in out for line in unit.lines)
    assert "停顿半秒" not in joined
    assert "三遍" not in joined
    assert "半句" not in joined
    assert "几遍" in joined


def test_feedback_gate_fails_closed_after_failed_compact_retry(persona, core, units):
    bad_units = [{
        "index": i,
        "purpose": "建立主轴" if i == 0 else "推进主轴",
        "spine_link": "围绕同一判断推进",
        "lines": [
            {"text": "这句只说明判断边界。"},
            {"text": "我三年前摸了左耳垂，才发现没签合同。"},
        ],
    } for i in range(4)]
    writer = ScriptWriter(FakeLLM(json.dumps({"units": bad_units}, ensure_ascii=False)))
    out = writer.write(
        persona, core, units, topic="读博换导师",
        source_material={"persona": "学术区主播", "topic": "读博换导师"},
        tuning_guidance=[
            {"category": "fabricated_detail", "rule": "禁止补造细节"},
            {"category": "world_knowledge", "rule": "增加领域常识校验"},
        ],
    )

    assert writer.last_quality_gate == {
        "retried": True,
        "sanitized": False,
        "passed": False,
        "first_issues": ["unsupported_specific_detail"],
        "retry_issues": ["unsupported_specific_detail"],
        "first_issue_details": [
            "number:三年",
            "detail:耳垂",
            "domain:没签合同",
        ],
        "retry_issue_details": [
            "number:三年",
            "detail:耳垂",
            "domain:没签合同",
        ],
        "post_sanitize_issues": [],
        "post_sanitize_issue_details": [],
    }
    texts = [line.text for unit in out for line in unit.lines]
    assert all("占位" in text for text in texts)
    assert all("耳垂" not in text and "合同" not in text for text in texts)


def test_write_first_line_hook_last_line_turn(persona, core, units):
    """软 stage 标注：首行 hook、末行 turn（仅供节奏，不驱动 rupture）。"""
    out = ScriptWriter(FakeLLM(_resp())).write(persona, core, units, topic="转行")
    for u in out:
        assert u.lines[0].stage == "hook"
        assert u.lines[-1].stage == "turn"


from echuu.core.persona_dossier import CharacterDossier, Conflict, BehaviorRules
from echuu.core.unit import AcousticHint


class _RecLLM:
    def __init__(self): self.prompts = []
    def generate(self, prompt): self.prompts.append(prompt); return "{ bad json }"


def _units(n=3):
    return [Unit(index=i, time_window=(i * 60, (i + 1) * 60), acoustic=AcousticHint())
            for i in range(n)]


def _persona():
    return RichPersona(identity="i", belief="b", flaw="f")


def _core():
    return StoryCore(spine="s", story_beats=("起", "转", "合"))


def test_writer_prompt_carries_dossier_and_breaking_point_on_turn():
    llm = _RecLLM()
    dossier = CharacterDossier(
        expanded_bio="",
        conflict=Conflict(statement="她从不拒绝别人，但心里在记账"),
        behavior_rules=BehaviorRules(
            contradiction="嘴上没事，行为拖延",
            breaking_point="被第三次索取会突然强硬"))
    ScriptWriter(llm).write(_persona(), _core(), _units(3),
                            topic="帮朋友做决定", dossier=dossier)
    p = llm.prompts[0]
    assert "她从不拒绝别人，但心里在记账" in p
    # breaking_point 出现在"转"拍附近（n=3 时转是 index=1）
    assert "被第三次索取会突然强硬" in p
    turn_pos = p.index("被第三次索取会突然强硬")
    unit1_pos = p.index("Unit1")
    unit2_pos = p.index("Unit2")
    assert unit1_pos < turn_pos < unit2_pos


def test_writer_prompt_without_dossier_unchanged():
    llm = _RecLLM()
    ScriptWriter(llm).write(_persona(), _core(), _units(3), topic="t")
    assert "内在冲突" not in llm.prompts[0]


def test_commentary_mode_uses_mode_specific_rails_without_forced_twist():
    llm = _RecLLM()
    core = StoryCore(
        spine="讨论把主播当精神寄托是否健康",
        discourse_mode="commentary",
        mode_rationale="这是一个需要边界条件的观点讨论",
        core_struggle="陪伴和依赖的边界在哪里",
        story_beats=("先说立场", "给出个人依据", "说明边界", "落回观众"),
    )
    ScriptWriter(llm).write(_persona(), core, _units(4), topic="精神寄托")
    prompt = llm.prompts[0]
    assert "观点评论（commentary）" in prompt
    assert "明确主张" in prompt
    assert "不要强造认知翻转" in prompt
    assert "转·认知翻转" not in prompt
