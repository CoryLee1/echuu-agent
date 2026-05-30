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


def test_planner_time_windows_partition_300s():
    units = UnitPlanner().plan()
    assert units[0].time_window == (0, 90)
    assert units[1].time_window == (90, 180)
    assert units[2].time_window == (180, 240)
    assert units[3].time_window == (240, 300)


def test_planner_signature_back_compat():
    """旧签名 plan(persona, topic) 仍可调（参数被忽略）。"""
    units = UnitPlanner().plan(persona=object(), topic="随便")
    assert len(units) == 4
