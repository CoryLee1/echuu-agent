"""StoryCore — 故事内核：这个人在这个话题上「凭什么值得讲」。

由 PersonaAnalyst 产出，交给 ScriptWriter 作为创作起点。它给的是「讲什么、
为什么有意思」，不是「第几段放什么」——叙事编排由 ScriptWriter 通盘负责。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StoryCore:
    spine: str                       # 一句话主线：就讲【一件】具体的事
    core_struggle: str = ""          # 主角围绕这件事的核心纠结/矛盾点（故事的心脏）
    twist: str = ""                  # 翻转/转折（重头戏，必须精彩）
    central_contrast: str = ""       # 核心反差/悬念
    emotional_undercurrent: str = "" # 情绪暗线（从哪走到哪）
    # 【同一件事】的 4 个阶段（起承转合），围绕核心纠结推进、有跌宕起伏。
    # 不是 4 件不同的事，也不是同一个点绕 4 遍；第 3 拍(转)是重头戏。
    story_beats: tuple[str, ...] = field(default_factory=tuple)
    punchline_seeds: tuple[str, ...] = field(default_factory=tuple)  # 金句种子（粗胚）
    hook_angle: str = ""             # 开场钩子角度（前 30-60s 怎么抓人）
