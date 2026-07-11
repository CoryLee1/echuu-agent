"""Smoke test: an event built by EchuuLiveEngine._build_step_event matches the v2 WS schema."""
from __future__ import annotations

from echuu.core.persona_model import PersonaModel
from echuu.core.unit import AcousticHint, Rupture, ScriptLine, Show, Unit
from echuu.live.engine import EchuuLiveEngine
from echuu.live.motion import DANMAKU_CLIPS, RUPTURE_CLIPS
from echuu.live.state import Danmaku


def _show():
    persona = PersonaModel(identity="i", belief="b", flaw="f", visual_anchor="v", title_hook="t")
    units = [Unit(
        index=i, time_window=(i*75, (i+1)*75),
        axis="identity", density="high",
        acoustic=AcousticHint(),
        rupture_slots=[Rupture(kind="meme", nucleus_mode="tiny_shame", intensity=0.5)],
        lines=[ScriptLine(id="x", text="t", stage="turn", is_rupture=True)],
    ) for i in range(4)]
    return Show(persona=persona, topic="t", units=units)


def test_step_event_v2_shape():
    engine = EchuuLiveEngine.__new__(EchuuLiveEngine)
    engine.tts = None
    engine.state = type("S", (), {"show": _show()})()
    unit = engine.state.show.units[0]
    line = unit.lines[0]
    ev = engine._build_step_event(unit, 0, line, audio=None)

    assert ev["type"] == "step"
    assert ev["show"]["total_units"] == 4
    assert "total_lines" in ev["show"]
    assert ev["unit"]["index"] == 0
    assert ev["unit"]["axis"] in ("identity", "belief", "flaw")
    assert ev["unit"]["acoustic"]["pitch_rate"] == 1.0
    assert ev["line"]["stage"] in ("hook", "pad", "turn")
    assert ev["line"]["is_rupture"] is True
    assert ev["speech"] == "t"  # compat alias
    assert ev["motion"]["state"] == "reacting"
    assert ev["motion"]["clip"] in RUPTURE_CLIPS
    assert ev["motion"]["loop"] is False


def test_step_event_audio_field_present_for_broadcast_pop():
    """live_service.py does `result.pop('audio', None)` — must not KeyError on missing key.
    But for v2 events, audio key is always present (None if synthesize failed)."""
    engine = EchuuLiveEngine.__new__(EchuuLiveEngine)
    engine.tts = None
    engine.state = type("S", (), {"show": _show()})()
    unit = engine.state.show.units[0]
    line = unit.lines[0]
    ev = engine._build_step_event(unit, 0, line, audio=None)
    assert "audio" in ev
    assert ev["audio"] is None
    assert "motion" in ev


def test_step_event_rupture_kind_only_on_rupture_lines():
    """rupture_kind should only be set when line.is_rupture=True."""
    engine = EchuuLiveEngine.__new__(EchuuLiveEngine)
    engine.tts = None
    engine.state = type("S", (), {"show": _show()})()
    unit = engine.state.show.units[0]
    # Non-rupture line
    non_rupture = ScriptLine(id="nr", text="ordinary", stage="hook", is_rupture=False)
    ev_nr = engine._build_step_event(unit, 0, non_rupture, audio=None)
    assert ev_nr["unit"]["rupture_kind"] is None
    # Rupture line
    rupture = ScriptLine(id="r", text="critical", stage="turn", is_rupture=True)
    ev_r = engine._build_step_event(unit, 0, rupture, audio=None)
    assert ev_r["unit"]["rupture_kind"] == "meme"  # matches unit[0]'s rupture slot


def test_danmaku_event_has_motion_hint():
    engine = EchuuLiveEngine.__new__(EchuuLiveEngine)
    engine.tts = None
    engine.state = type("S", (), {"show": _show()})()
    unit = engine.state.show.units[0]
    ev = engine._build_danmaku_event(unit, Danmaku.from_text("你好", user="u"), "hello", audio=None)

    assert ev["line"]["stage"] == "danmaku"
    assert ev["motion"]["state"] == "danmaku"
    assert ev["motion"]["clip"] in DANMAKU_CLIPS
