"""Tests for StructureBreaker.inject_flaw_rupture — Unit[3] flaw injection."""
from __future__ import annotations

import pytest

from echuu.core.persona_model import PersonaModel
from echuu.core.structure_breaker import StructureBreaker
from echuu.core.unit import AcousticHint, Rupture, ScriptLine, Unit


VALID_MODES = {"slippery_slope", "kindness_trap", "anger_armor",
               "choice_cost", "tiny_shame", "contradiction_reveal"}


@pytest.fixture
def persona() -> PersonaModel:
    return PersonaModel(
        identity="i", belief="b",
        flaw="决定辞职那天哭了一整夜",
        visual_anchor="v", title_hook="t",
    )


def _make_unit_3() -> Unit:
    return Unit(
        index=3,
        time_window=(240, 300),
        axis="flaw",
        density="low",
        acoustic=AcousticHint(pitch_rate=0.88, speech_rate=0.88, volume=50),
        rupture_slots=[Rupture(kind="flaw", nucleus_mode="tiny_shame", intensity=0.95)],
        lines=[
            ScriptLine(id="l0", text="钩子开场", stage="hook"),
            ScriptLine(id="l1", text="铺垫", stage="pad"),
            ScriptLine(id="l2", text="结尾翻转", stage="turn"),
        ],
    )


def test_inject_flaw_rupture_marks_last_line(persona):
    sb = StructureBreaker()
    unit = sb.inject_flaw_rupture(_make_unit_3(), persona)
    assert unit.lines[-1].is_rupture is True
    assert unit.lines[-1].stage == "turn"


def test_inject_flaw_rupture_selects_valid_nucleus_mode(persona):
    sb = StructureBreaker()
    unit = sb.inject_flaw_rupture(_make_unit_3(), persona)
    modes = [r.nucleus_mode for r in unit.rupture_slots]
    assert any(m in VALID_MODES for m in modes)


def test_inject_flaw_rupture_falls_back_to_tiny_shame(persona):
    """spec §5: nucleus_mode 找不到时降级到 tiny_shame."""
    # persona.flaw 设成一段不容易匹配任何 nucleus pattern 的文本
    weird = PersonaModel(identity="i", belief="b", flaw="zzz",
                         visual_anchor="v", title_hook="t")
    sb = StructureBreaker()
    unit = sb.inject_flaw_rupture(_make_unit_3(), weird)
    modes = [r.nucleus_mode for r in unit.rupture_slots]
    assert "tiny_shame" in modes


def test_inject_flaw_rupture_works_with_placeholder_flaw(persona):
    """spec §5: PersonaModel.flaw 为占位时仍能注入 (don't crash)."""
    placeholder = PersonaModel(identity="i", belief="b", flaw="[待补充弱点]",
                               visual_anchor="v", title_hook="t")
    sb = StructureBreaker()
    unit = sb.inject_flaw_rupture(_make_unit_3(), placeholder)
    # Doesn't crash. Last line still marked rupture.
    assert unit.lines[-1].is_rupture is True


class _FakeDigression:
    def inject_digression(self, script_line, topic, language="zh", force=False):
        return f"{script_line}…邻居半夜很奇怪", {"chain_type": "location_tangent"}


def test_break_structure_does_not_inject_engine_tangent():
    sb = StructureBreaker(_FakeDigression())
    lines = [{"text": f"第{i}句正经主线", "language": "zh"} for i in range(5)]
    out = sb.break_structure(lines, topic="云养猫", language="zh")
    assert all(not line.get("has_digression") for line in out)
    assert all("邻居半夜" not in line["text"] for line in out)


def test_delete_sublimation_keeps_rupture_lines(persona):
    """spec §6: delete_sublimation 不删 rupture line."""
    sb = StructureBreaker()
    unit = _make_unit_3()
    # Mark last line as rupture before scrubbing
    unit.lines[-1].is_rupture = True
    unit.lines[-1].text = "所以说这件事让我明白人生的意义"  # sublimation pattern
    # Use the new unit-aware scrub method (added in implementation)
    result = sb.delete_sublimation_in_unit(unit)
    # The rupture line must still be present
    assert any(l.is_rupture for l in result.lines)
