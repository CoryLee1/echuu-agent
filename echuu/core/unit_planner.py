"""UnitPlanner (V2, degraded) — 只产出时间/音色/能量护栏，不再硬编排叙事。

V1 曾硬绑 axis=[身份,信念,信念,弱点] + rupture 槽，造成机械感。V2 把叙事编排交给
ScriptWriter（从 StoryCore 创作），UnitPlanner 退化为纯节奏骨架：4 个时间窗 + 音色
曲线（能量从高走到低）+ 能量提示。确定性、无 LLM。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §5.
"""
from __future__ import annotations

from typing import Literal, Optional

from echuu.core.unit import AcousticHint, Unit


_DENSITY: list[Literal["high", "medium", "low"]] = ["high", "high", "medium", "low"]
_TIME_WINDOWS: list[tuple[float, float]] = [(0, 90), (90, 180), (180, 240), (240, 300)]
_ACOUSTIC: list[AcousticHint] = [
    AcousticHint(pitch_rate=1.10, speech_rate=1.10, volume=60),   # U1 兴奋/钩
    AcousticHint(pitch_rate=1.05, speech_rate=1.05, volume=55),   # U2 递进
    AcousticHint(pitch_rate=0.92, speech_rate=0.92, volume=45),   # U3 缠结/认真
    AcousticHint(pitch_rate=0.88, speech_rate=0.88, volume=50),   # U4 收束/弱点浮现
]


class UnitPlanner:
    """节奏/音色护栏。确定性，无 LLM。叙事由 ScriptWriter 负责。"""

    def plan(self, persona=None, topic: str = "") -> list[Unit]:
        # persona/topic 仅为向后兼容签名，V2 不再使用
        units = [
            Unit(
                index=i,
                time_window=_TIME_WINDOWS[i],
                acoustic=_ACOUSTIC[i],
                axis=None,                 # deprecated soft label
                density=_DENSITY[i],       # energy hint
                rupture_slots=[],
                lines=[],
            )
            for i in range(4)
        ]
        assert len(units) == 4, "I1 violated"  # I1: 恰好 4 个时间桶
        return units
