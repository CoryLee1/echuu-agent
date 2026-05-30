"""Tests for ScriptWriter (agent②) — story-core authoring + degradation."""
from __future__ import annotations

import json

import pytest

from echuu.core.persona_model import RichPersona
from echuu.core.story_core import StoryCore
from echuu.core.unit_planner import UnitPlanner
from echuu.generators.script_writer import ScriptWriter


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


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
        spine="转行 6 个月，热爱被生计磨出真相",
        central_contrast="做喜欢的事反而更累",
        emotional_undercurrent="兴奋→怀疑→坦白",
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
    assert core.hook_angle in p
    assert "热爱是有 KPI 的" in p        # 金句种子
    assert "真实案例" in p              # few-shot 注入
    assert "碎碎念" in p                # 硬要求出现在 prompt


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


def test_write_first_line_hook_last_line_turn(persona, core, units):
    """软 stage 标注：首行 hook、末行 turn（仅供节奏，不驱动 rupture）。"""
    out = ScriptWriter(FakeLLM(_resp())).write(persona, core, units, topic="转行")
    for u in out:
        assert u.lines[0].stage == "hook"
        assert u.lines[-1].stage == "turn"
