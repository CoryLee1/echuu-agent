"""Unit / Show skeleton — Show → Unit × 4 → Rupture / Line.

See docs/superpowers/specs/2026-05-30-echuu-rupture-engine-design.md §2.1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Optional


@dataclass
class AcousticHint:
    """Segment-level Qwen TTS knobs (passed to update_session)."""
    pitch_rate: float = 1.0   # 0.7-1.3
    speech_rate: float = 1.0  # 0.7-1.3
    volume: int = 50          # 0-100


@dataclass
class Rupture:
    """A scheduled break-point slot. The 'how' is filled by StructureBreaker."""
    kind: Literal["meme", "flaw"]
    nucleus_mode: str  # one of: slippery_slope / kindness_trap / anger_armor / choice_cost / tiny_shame / contradiction_reveal
    intensity: float   # 0-1; Unit[3] flaw must be highest


@dataclass
class ScriptLine:
    """A single line within a Unit."""
    id: str
    text: str
    stage: Literal["hook", "pad", "turn"]
    is_rupture: bool = False
    interruption_cost: float = 0.5
    cue: object | None = None  # echuu.core.performer_cue.PerformerCue — late import to avoid cycle
    key_info: list[str] = field(default_factory=list)


@dataclass
class Unit:
    """A 60-90s self-contained time/acoustic slice.

    V2: `axis` is a deprecated soft label (no longer drives generation); the
    narrative is authored by ScriptWriter from the StoryCore. `density` is now
    just an energy hint (high/medium/low) for pacing. `rupture_slots` are no
    longer pre-allocated (kept for backward compat)."""
    index: int                              # 0..3
    time_window: tuple[float, float]        # seconds
    acoustic: AcousticHint
    axis: Optional[str] = None              # deprecated soft label (V1: identity/belief/flaw)
    density: Literal["high", "medium", "low"] = "medium"  # energy hint
    rupture_slots: list[Rupture] = field(default_factory=list)
    lines: list[ScriptLine] = field(default_factory=list)
    purpose: str = ""                       # 本段在唯一主轴中的功能
    spine_link: str = ""                    # 本段如何推进 StoryCore.spine


@dataclass
class Show:
    """A complete 5-min show. Unit count is always 4 (I1)."""
    persona: object                          # RichPersona / PersonaModel — avoid cycle
    topic: str
    units: list[Unit] = field(default_factory=list)
    story_core: object | None = None         # StoryCore — avoid cycle
