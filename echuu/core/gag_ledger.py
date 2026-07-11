"""GagLedger — call-back 埋梗账本（Phase 2-①）。

综艺感 = 前面随口埋的意象在结尾"啪"地接上。ScriptWriter 在前 1/3 埋 1-2 个
可回收意象登记进账本；末段与 closing 生成时注入未回收的梗要求自然回收；
弹幕回应能顺手挂上也优先挂。

See docs/superpowers/specs/2026-07-11-phase2-entertainment-persona-card.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PlantedGag:
    text: str
    unit_index: int = 0
    recalled: bool = False


class GagLedger:
    def __init__(self) -> None:
        self._gags: list[PlantedGag] = []

    def register(self, texts, unit_index: int = 0) -> None:
        for text in texts or []:
            cleaned = str(text).strip()
            if cleaned and all(g.text != cleaned for g in self._gags):
                self._gags.append(PlantedGag(text=cleaned, unit_index=unit_index))

    def unrecalled(self) -> list[str]:
        return [g.text for g in self._gags if not g.recalled]

    def mark_recalled(self, text: str) -> None:
        for g in self._gags:
            if g.text == text:
                g.recalled = True

    def __len__(self) -> int:
        return len(self._gags)
