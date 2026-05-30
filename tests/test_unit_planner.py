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
