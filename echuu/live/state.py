"""
运行时状态与数据结构定义。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Danmaku:
    """弹幕（带优先级计算字段）。"""

    text: str
    user: str = "观众"
    is_sc: bool = False
    amount: int = 0

    relevance: float = 0.0
    priority: float = 0.0

    @classmethod
    def from_text(cls, text: str, user: str = "观众") -> "Danmaku":
        """解析弹幕。"""
        is_sc = False
        amount = 0

        if "SC" in text or "¥" in text or "$" in text:
            is_sc = True
            import re

            match = re.search(r"[¥$]?\s*(\d+)", text)
            if match:
                amount = int(match.group(1))

        return cls(text=text, user=user, is_sc=is_sc, amount=amount)

    def is_question(self) -> bool:
        """判断是否是问题。"""
        return "?" in self.text or "？" in self.text


@dataclass
class PerformerMemory:
    """记忆系统 - 可视化展示AI记住了什么。"""

    script_progress: Dict = field(
        default_factory=lambda: {
            "current_line": 0,
            "total_lines": 0,
            "completed_stages": [],
            "current_stage": "Hook",
        }
    )

    danmaku_memory: Dict = field(
        default_factory=lambda: {
            "received": [],
            "responded": [],
            "ignored": [],
            "pending_questions": [],
        }
    )

    promises: List[Dict] = field(default_factory=list)
    story_points: Dict = field(
        default_factory=lambda: {
            "mentioned": [],
            "upcoming": [],
            "revealed": [],
        }
    )
    emotion_track: List[Dict] = field(default_factory=list)

    def to_display(self) -> str:
        """生成用户可见的记忆状态。"""
        lines = []
        lines.append("+-------------------------------------------+")
        lines.append("| AI 记忆状态                               |")
        lines.append("+-------------------------------------------+")

        prog = self.script_progress
        current = prog.get("current_line", 0)
        total = prog.get("total_lines", 0)
        if total > 0:
            percent = int(current / total * 10)
            bar = "#" * percent + "-" * (10 - percent)
            lines.append(f"| 剧本: [{bar}] {current}/{total} ({prog.get('current_stage', '?')}) |")

        dm = self.danmaku_memory
        responded = len(dm.get("responded", []))
        pending = len(dm.get("pending_questions", []))
        lines.append(f"| 弹幕: 已回应{responded}条, 待回答{pending}个问题           |")

        unfulfilled = [p for p in self.promises if not p.get("fulfilled", False)]
        if unfulfilled:
            lines.append("| 待兑现承诺:                               |")
            for p in unfulfilled[:2]:
                content = p.get("content", "")[:20]
                lines.append(f"|   - {content}...                          |")

        if self.emotion_track:
            lines.append("| 情绪轨迹:                                 |")
            for emo in self.emotion_track[-2:]:
                level_name = {1: "微破防", 2: "明显破防", 3: "完全破防"}.get(
                    emo.get("level", 0), "?"
                )
                trigger = emo.get("trigger", "")[:12]
                lines.append(f"|   {level_name}: {trigger}...               |")

        mentioned = self.story_points.get("mentioned", [])
        if mentioned:
            lines.append("| 已提到:                                   |")
            for point in mentioned[-3:]:
                lines.append(f"|   * {point[:20]}...                        |")

        lines.append("+-------------------------------------------+")
        return "\n".join(lines)

    def to_context(self) -> str:
        """生成给 LLM 的上下文摘要。"""
        parts = []
        prog = self.script_progress
        parts.append(
            f"剧本进度: {prog.get('current_line')}/{prog.get('total_lines')} "
            f"({prog.get('current_stage')})"
        )

        mentioned = self.story_points.get("mentioned", [])
        if mentioned:
            parts.append(f"已提到: {', '.join(mentioned[-5:])}")

        pending = self.danmaku_memory.get("pending_questions", [])
        if pending:
            parts.append(f"待回答: {', '.join(q[:20] for q in pending[:3])}")

        unfulfilled = [p for p in self.promises if not p.get("fulfilled", False)]
        if unfulfilled:
            parts.append(f"待兑现承诺: {', '.join(p['content'][:15] for p in unfulfilled[:2])}")

        return " | ".join(parts)


@dataclass
class PerformanceState:
    """表演状态。"""

    name: str
    persona: str
    background: str
    topic: str

    script_lines: List = field(default_factory=list)
    current_line_idx: int = 0
    current_step: int = 0

    memory: PerformerMemory = field(default_factory=PerformerMemory)
    danmaku_queue: List[Danmaku] = field(default_factory=list)
    catchphrases: List[str] = field(default_factory=list)
