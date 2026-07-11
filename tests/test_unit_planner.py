"""Tests for UnitPlanner (V2, degraded) — time/acoustic/energy rails only.

V2 moved narrative authoring to ScriptWriter; the planner no longer hard-maps
axis or pre-allocates rupture slots. See
docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §5.
"""
from __future__ import annotations

import pytest

from echuu.core.unit import AcousticHint, Unit
from echuu.core.unit_planner import UnitPlanner


def test_acoustic_hint_defaults():
    h = AcousticHint()
    assert h.pitch_rate == 1.0
    assert h.speech_rate == 1.0
    assert h.volume == 50


def test_planner_outputs_exactly_four_units():
    """I1: 恰好 4 个时间桶。"""
    units = UnitPlanner().plan()
    assert len(units) == 4
    assert all(isinstance(u, Unit) for u in units)


def test_planner_no_hard_axis_mapping():
    """V2: 不再硬绑 axis（叙事交给 ScriptWriter）。"""
    units = UnitPlanner().plan()
    assert all(u.axis is None for u in units)


def test_planner_no_preallocated_ruptures():
    """V2: 不再预分配 rupture 槽。"""
    units = UnitPlanner().plan()
    assert all(u.rupture_slots == [] for u in units)


def test_planner_energy_curve_descends():
    """能量提示从高走到低（节奏护栏）。"""
    units = UnitPlanner().plan()
    assert [u.density for u in units] == ["high", "high", "medium", "low"]


def test_planner_acoustic_in_legal_range():
    """I5: acoustic 在合法区间。"""
    units = UnitPlanner().plan()
    for u in units:
        assert 0.7 <= u.acoustic.pitch_rate <= 1.3
        assert 0.7 <= u.acoustic.speech_rate <= 1.3
        assert 0 <= u.acoustic.volume <= 100


def test_planner_acoustic_descends():
    """音色从兴奋(高pitch)走到收束(低pitch)，配合情绪暗线。"""
    units = UnitPlanner().plan()
    pitches = [u.acoustic.pitch_rate for u in units]
    assert pitches[0] > pitches[-1]


def test_planner_time_windows_75s_each():
    units = UnitPlanner().plan()  # default 4
    assert units[0].time_window == (0, 75)
    assert units[1].time_window == (75, 150)
    assert units[2].time_window == (150, 225)
    assert units[3].time_window == (225, 300)


def test_planner_variable_length():
    """节目长度自适应：2~4 段 ≈ 2.5~5 分钟。"""
    assert len(UnitPlanner().plan(2)) == 2
    assert len(UnitPlanner().plan(3)) == 3
    assert len(UnitPlanner().plan(4)) == 4
    # 2 段 ≈ 150s = 2.5min
    u2 = UnitPlanner().plan(2)
    assert u2[-1].time_window[1] == 150
    # 末段总是 low 能量，首段 high
    assert u2[0].density == "high" and u2[-1].density == "low"


def test_planner_clamps_to_2_4():
    assert len(UnitPlanner().plan(1)) == 2    # 下限
    assert len(UnitPlanner().plan(9)) == 4    # 上限


def test_planner_acoustic_descends_any_length():
    for n in (2, 3, 4):
        units = UnitPlanner().plan(n)
        assert units[0].acoustic.pitch_rate > units[-1].acoustic.pitch_rate


def test_planner_signature_back_compat():
    """旧签名（含 persona/topic kwargs）仍可调（参数被忽略）。"""
    units = UnitPlanner().plan(4, persona=object(), topic="随便")
    assert len(units) == 4
