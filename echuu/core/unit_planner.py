"""UnitPlanner — V1 hardcoded structural template. NO LLM (spec §2.3).

Outputs exactly 4 Units with fixed axis/density/acoustic/rupture-slot schedule.
"""
from __future__ import annotations

from typing import Literal

from echuu.core.unit import AcousticHint, Rupture, Unit


_AXIS: list[Literal["identity", "belief", "flaw"]] = ["identity", "belief", "belief", "flaw"]
_DENSITY: list[Literal["high", "medium", "low"]] = ["high", "high", "medium", "low"]
_TIME_WINDOWS: list[tuple[float, float]] = [(0, 90), (90, 180), (180, 240), (240, 300)]
_ACOUSTIC: list[AcousticHint] = [
    AcousticHint(pitch_rate=1.10, speech_rate=1.10, volume=60),   # U1 兴奋
    AcousticHint(pitch_rate=1.05, speech_rate=1.05, volume=55),   # U2 递进
    AcousticHint(pitch_rate=0.92, speech_rate=0.92, volume=45),   # U3 认真
    AcousticHint(pitch_rate=0.88, speech_rate=0.88, volume=50),   # U4 弱点闪现
]
# Default nucleus mode per unit — StructureBreaker may refine later
_NUCLEUS: list[str] = ["slippery_slope", "kindness_trap", "contradiction_reveal", "tiny_shame"]
_INTENSITY: list[float] = [0.55, 0.65, 0.7, 0.95]  # Unit[3] highest

_KINDS: list[str] = ["meme", "meme", "meme", "flaw"]


class UnitPlanner:
    """Pure structural planner. Deterministic. No LLM."""

    def plan(self, persona, topic: str) -> list[Unit]:
        units: list[Unit] = []
        for i in range(4):
            rupture = Rupture(
                kind=_KINDS[i],
                nucleus_mode=_NUCLEUS[i],
                intensity=_INTENSITY[i],
            )
            units.append(Unit(
                index=i,
                time_window=_TIME_WINDOWS[i],
                axis=_AXIS[i],
                density=_DENSITY[i],
                acoustic=_ACOUSTIC[i],
                rupture_slots=[rupture],
                lines=[],
            ))
        assert len(units) == 4, "I1 violated"  # I1 assertion (spec §5)
        return units
