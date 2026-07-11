"""UnitPlanner (V2, degraded) — 只产出时间/音色/能量护栏，不再硬编排叙事。

V1 曾硬绑 axis=[身份,信念,信念,弱点] + rupture 槽，造成机械感。V2 把叙事编排交给
ScriptWriter（从 StoryCore 创作），UnitPlanner 退化为纯节奏骨架：4 个时间窗 + 音色
曲线（能量从高走到低）+ 能量提示。确定性、无 LLM。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §5.
"""
from __future__ import annotations

from typing import Literal, Optional

from echuu.core.unit import AcousticHint, Unit


# 每个 beat 约 75 秒 → 2 段≈2.5min，4 段≈5min（节目长度自适应）
_SECONDS_PER_BEAT = 75
_MIN_UNITS, _MAX_UNITS = 2, 4


def _acoustic_for(i: int, n: int) -> AcousticHint:
    """音色随位置从兴奋(高)走到收束(低)，按段数插值。"""
    frac = 0.0 if n <= 1 else i / (n - 1)
    pitch = round(1.10 - 0.22 * frac, 3)   # 1.10 → 0.88
    volume = int(round(60 - 12 * frac))    # 60 → 48
    return AcousticHint(pitch_rate=pitch, speech_rate=pitch, volume=volume)


def _density_for(i: int, n: int) -> str:
    """能量：首段 high，末段 low，倒数第二 medium，其余 high。"""
    if i == 0:
        return "high"
    if i == n - 1:
        return "low"
    if i == n - 2:
        return "medium"
    return "high"


class UnitPlanner:
    """节奏/音色护栏。确定性，无 LLM。叙事由 ScriptWriter 负责。

    plan(n_units) 产出 n 个时间/音色桶（n∈[2,4]）；时长随段数自适应——
    短故事少几段、不注水（2.5~5 分钟）。"""

    def plan(self, n_units: int = 4, persona=None, topic: str = "") -> list[Unit]:
        n = max(_MIN_UNITS, min(_MAX_UNITS, int(n_units)))
        units = [
            Unit(
                index=i,
                time_window=(i * _SECONDS_PER_BEAT, (i + 1) * _SECONDS_PER_BEAT),
                acoustic=_acoustic_for(i, n),
                axis=None,                 # deprecated soft label
                density=_density_for(i, n),
                rupture_slots=[],
                lines=[],
            )
            for i in range(n)
        ]
        assert _MIN_UNITS <= len(units) <= _MAX_UNITS, "unit count out of range"
        return units
