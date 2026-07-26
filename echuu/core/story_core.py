"""StoryCore — 故事内核：这个人在这个话题上「凭什么值得讲」。

由 PersonaAnalyst 产出，交给 ScriptWriter 作为创作起点。它给的是「讲什么、
为什么有意思」，不是「第几段放什么」——叙事编排由 ScriptWriter 通盘负责。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md §2.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class StoryCore:
    spine: str                       # 一句话中心结论/回答：全篇只能服务这一件事
    discourse_mode: str = "narrative"  # narrative/commentary/advice/banter/...
    mode_rationale: str = ""         # 为什么这个话题适合该话语结构
    tone_mode: str = "conversational"  # playful_teasing/light_banter/warm/serious/...
    depth_budget: str = "medium"      # light/medium/deep：允许把话题解释到多深
    entertainment_mechanism: str = "" # 这轮靠什么好看：吊胃口/误会/回收/反差等
    core_struggle: str = ""          # 主角围绕这件事的核心纠结/矛盾点（故事的心脏）
    supporting_points: tuple[str, ...] = field(default_factory=tuple)
    # 最多 2 个支撑点：它们是主轴的证据/判断依据，不是新的话题或支线故事。
    twist: str = ""                  # 翻转/转折（重头戏，必须精彩）
    central_contrast: str = ""       # 核心反差/悬念
    emotional_undercurrent: str = "" # 情绪暗线（从哪走到哪）
    # 【同一主轴】的 2-3 个推进阶段；只有确有时间线的厚叙事才允许 4 个。
    # 不是几个话题拼盘，也不是换隐喻重复同一点。
    story_beats: tuple[str, ...] = field(default_factory=tuple)
    punchline_seeds: tuple[str, ...] = field(default_factory=tuple)  # 金句种子（粗胚）
    hook_angle: str = ""             # 开场钩子角度（前 30-60s 怎么抓人）
