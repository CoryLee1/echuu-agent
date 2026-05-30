"""StoryCore — 故事内核：这个人在这个话题上「凭什么值得讲」。

由 PersonaAnalyst 产出，交给 ScriptWriter 作为创作起点。它给的是「讲什么、
为什么有意思」，不是「第几段放什么」——叙事编排由 ScriptWriter 通盘负责。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StoryCore:
    spine: str                       # 一句话主线：这人在这话题上要讲的核心故事
    central_contrast: str            # 核心反差/悬念
    emotional_undercurrent: str      # 情绪暗线（从哪走到哪）
    punchline_seeds: tuple[str, ...] = field(default_factory=tuple)  # 金句种子（粗胚）
    hook_angle: str = ""             # 开场钩子角度（前 30-60s 怎么抓人）
