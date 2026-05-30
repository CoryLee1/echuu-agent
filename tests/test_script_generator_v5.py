"""Tests for ScriptGeneratorV5 — unit-based, single LLM call."""
from __future__ import annotations

import json
import pytest

from echuu.core.persona_model import PersonaModel
from echuu.core.unit import AcousticHint, Rupture, Unit
from echuu.core.unit_planner import UnitPlanner
from echuu.generators.script_generator_v5 import ScriptGeneratorV5


class FakeLLM:
    def __init__(self, response: str):
        self.response = response
        self.calls: list[str] = []

    def generate(self, prompt: str) -> str:
        self.calls.append(prompt)
        return self.response


@pytest.fixture
def persona() -> PersonaModel:
    return PersonaModel(
        identity="25 岁前 HR，现自由插画师",
        belief="做喜欢的事比薪水重要",
        flaw="决定辞职那天哭了一整夜",
        visual_anchor="腕上便签",
        title_hook="我跟你讲——",
    )


@pytest.fixture
def planned_units(persona) -> list[Unit]:
    return UnitPlanner().plan(persona, topic="转行 6 个月的体感")


def _make_complete_llm_response() -> str:
    """Build a JSON response with 4 units × 3 lines each."""
    units = []
    for i in range(4):
        lines = []
        for j, stage in enumerate(("hook", "pad", "turn")):
            lines.append({
                "id": f"u{i}l{j}",
                "text": f"unit{i} line{j} 嗯…那个 ——",
                "stage": stage,
                "interruption_cost": 0.5,
            })
        units.append({"index": i, "lines": lines})
    return json.dumps({"units": units})


def test_generate_happy_path_returns_4_units_with_lines(persona, planned_units):
    llm = FakeLLM(_make_complete_llm_response())
    gen = ScriptGeneratorV5(llm=llm)
    units = gen.generate(persona, planned_units)
    assert len(units) == 4
    for u in units:
        assert len(u.lines) == 3
        assert {l.stage for l in u.lines} == {"hook", "pad", "turn"}


def test_generate_calls_llm_exactly_once(persona, planned_units):
    """spec §2.3: single LLM call to preserve unit-to-unit progression."""
    llm = FakeLLM(_make_complete_llm_response())
    gen = ScriptGeneratorV5(llm=llm)
    gen.generate(persona, planned_units)
    assert len(llm.calls) == 1


def test_generate_prompt_contains_persona_and_unit_metadata(persona, planned_units):
    llm = FakeLLM(_make_complete_llm_response())
    gen = ScriptGeneratorV5(llm=llm)
    gen.generate(persona, planned_units)
    prompt = llm.calls[0]
    # Persona axes present
    assert persona.identity in prompt
    assert persona.belief in prompt
    assert persona.flaw in prompt
    # Per-unit metadata present
    assert "identity" in prompt  # U0 axis
    assert "flaw" in prompt       # U3 axis
    # Acoustic hints visible to LLM
    assert "pitch_rate" in prompt or "1.10" in prompt
    # Density curve visible
    assert "high" in prompt


def test_generate_forces_last_line_to_turn(persona, planned_units):
    """spec §5 degradation: 强制每单元最后一行 stage='turn' + is_rupture=true."""
    # Response missing the 'turn' line in unit 0
    units_payload = []
    for i in range(4):
        lines = []
        stages = ("hook", "pad", "pad") if i == 0 else ("hook", "pad", "turn")  # u0 missing turn
        for j, st in enumerate(stages):
            lines.append({"id": f"u{i}l{j}", "text": "x", "stage": st, "interruption_cost": 0.5})
        units_payload.append({"index": i, "lines": lines})
    llm = FakeLLM(json.dumps({"units": units_payload}))
    gen = ScriptGeneratorV5(llm=llm)
    units = gen.generate(persona, planned_units)
    # u0's last line must now be turn + is_rupture
    assert units[0].lines[-1].stage == "turn"
    assert units[0].lines[-1].is_rupture is True


def test_generate_invalid_json_falls_back_to_placeholder(persona, planned_units):
    llm = FakeLLM("totally not json")
    gen = ScriptGeneratorV5(llm=llm)
    units = gen.generate(persona, planned_units)
    assert len(units) == 4
    for u in units:
        assert len(u.lines) == 3
        # Last line forced to turn + rupture even on full fallback
        assert u.lines[-1].stage == "turn"
        assert u.lines[-1].is_rupture is True


def test_generate_retries_once_then_falls_back(persona, planned_units):
    """LLM 第一次返回非法 JSON，第二次返回合法 → 用第二次结果。"""
    class FlakyLLM:
        def __init__(self):
            self.calls = 0
        def generate(self, prompt: str) -> str:
            self.calls += 1
            if self.calls == 1:
                return "broken"
            return _make_complete_llm_response()
    flaky = FlakyLLM()
    gen = ScriptGeneratorV5(llm=flaky)
    units = gen.generate(persona, planned_units)
    assert flaky.calls == 2
    assert len(units) == 4
    assert all(len(u.lines) == 3 for u in units)


def test_generate_short_units_triggers_retry(persona, planned_units):
    """LLM 第一次返回少于 4 unit → 重试 1 次 → 仍失败则占位。"""
    short = json.dumps({"units": [{"index": 0, "lines": [
        {"id": "x", "text": "y", "stage": "turn", "interruption_cost": 0.5}
    ]}]})
    class ShortLLM:
        def __init__(self):
            self.calls = 0
        def generate(self, prompt):
            self.calls += 1
            return short
    s = ShortLLM()
    gen = ScriptGeneratorV5(llm=s)
    units = gen.generate(persona, planned_units)
    assert s.calls == 2  # one retry
    # Fallback to placeholder for all 4
    for u in units:
        assert len(u.lines) == 3
        assert u.lines[-1].is_rupture is True
