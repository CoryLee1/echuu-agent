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
        units.append({"index": i, "lines": lines})
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
    assert core.twist in p              # 翻转
    assert "起：接稿很兴奋" in p         # story_beats 进了 rails
    assert core.hook_angle in p
    assert "热爱是有 KPI 的" in p        # 金句种子
    assert "真实案例" in p              # few-shot 注入
    assert "碎碎念" in p                # 硬要求出现在 prompt
    assert "求共鸣" in p or "提问" in p  # 提问式互动开场


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
            {"index": 0, "lines": [
                {"text": "我在便利店门口等甲方，手里攥着热豆浆。"},
                {"text": "他迟到十分钟，我已经把杯套抠成纸屑。"},
            ]},
            {"index": 1, "lines": [
                {"text": "然后平台弹出实体化过渡协议，右下角是我三年前住院病历号。"},
                {"text": "我突然明白这不是约稿，是命运系统在结算。"},
            ]},
            {"index": 2, "lines": [
                {"text": "协议开始扫描我的灵魂 KPI，我连豆浆都不敢喝。"},
                {"text": "这时候甲方说第一版像人画的，后面像服务器加班。"},
            ]},
            {"index": 3, "lines": [
                {"text": "最后我把协议锁进抽屉，继续画第一版。"},
                {"text": "热豆浆凉透了，但命运系统说可以报销。"},
            ]},
        ]
    })
    good = json.dumps({
        "units": [
            {"index": 0, "lines": [
                {"text": "我在便利店门口等甲方，热豆浆烫得我换了三次手。"},
                {"text": "他迟到十分钟，我已经把杯套抠成纸屑。"},
            ]},
            {"index": 1, "lines": [
                {"text": "他一开口说第八版很好，就是少了第一版那股傻劲。"},
                {"text": "我说那股傻劲已经被您七轮意见腌入味了。"},
            ]},
            {"index": 2, "lines": [
                {"text": "我当场笑出声：原来我熬夜修掉的，全是他要买的。"},
                {"text": "更离谱的是，他还夸我第一版有松弛感。"},
            ]},
            {"index": 3, "lines": [
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
