"""Tests for UnitPlanner — V1 structural invariants I1/I2/I3/I5."""
from __future__ import annotations

import pytest

from echuu.core.persona_model import PersonaModel
from echuu.core.unit import AcousticHint, Rupture, ScriptLine, Show, Unit
from echuu.core.unit_planner import UnitPlanner


@pytest.fixture
def persona() -> PersonaModel:
    return PersonaModel(
        identity="25 岁前 HR，现自由插画师",
        belief="做喜欢的事比薪水重要",
        flaw="决定辞职那天哭了一整夜",
        visual_anchor="腕上便签",
        title_hook="我跟你讲，从 HR 转行插画师那天——",
    )


def test_acoustic_hint_defaults():
    h = AcousticHint()
    assert h.pitch_rate == 1.0
    assert h.speech_rate == 1.0
    assert h.volume == 50


def test_planner_outputs_exactly_four_units(persona):
    """I1: 恰好 4 个 Unit."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="转行 6 个月的体感")
    assert len(units) == 4
    assert all(isinstance(u, Unit) for u in units)


def test_planner_axis_sequence_fixed(persona):
    """V1 axis 顺序固定 [identity, belief, belief, flaw]."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    assert [u.axis for u in units] == ["identity", "belief", "belief", "flaw"]


def test_planner_density_curve_fixed(persona):
    """V1 density 曲线 [high, high, medium, low]."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    assert [u.density for u in units] == ["high", "high", "medium", "low"]


def test_planner_unit3_has_flaw_rupture(persona):
    """I3: Unit[3].rupture_slots 必须含 kind='flaw'."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    flaw_kinds = [r.kind for r in units[3].rupture_slots]
    assert "flaw" in flaw_kinds
    # And Unit[3] flaw must have the highest intensity overall
    all_intensities = [(u.index, r.intensity) for u in units for r in u.rupture_slots]
    max_unit_idx, _ = max(all_intensities, key=lambda x: x[1])
    assert max_unit_idx == 3


def test_planner_each_unit_has_at_least_one_rupture(persona):
    """I2: every Unit has ≥1 rupture_slot."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    for u in units:
        assert len(u.rupture_slots) >= 1, f"Unit[{u.index}] has no rupture slots"


def test_planner_units_0_to_2_are_meme(persona):
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    for i in range(3):
        kinds = [r.kind for r in units[i].rupture_slots]
        assert kinds, f"Unit[{i}] empty rupture_slots"
        assert "meme" in kinds


def test_planner_acoustic_in_legal_range(persona):
    """I5: acoustic 在合法区间 (pitch/speech_rate 0.7-1.3, volume 0-100)."""
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    for u in units:
        assert 0.7 <= u.acoustic.pitch_rate <= 1.3
        assert 0.7 <= u.acoustic.speech_rate <= 1.3
        assert 0 <= u.acoustic.volume <= 100


def test_planner_time_windows_partition_300s(persona):
    planner = UnitPlanner()
    units = planner.plan(persona, topic="t")
    assert units[0].time_window == (0, 90)
    assert units[1].time_window == (90, 180)
    assert units[2].time_window == (180, 240)
    assert units[3].time_window == (240, 300)
