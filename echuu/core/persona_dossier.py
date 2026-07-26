"""CharacterDossier — 机器扩充、用户可认领的人物小传 + 一条冲突 + 行为规则。

与 PersonaCard 的分工：
- PersonaCard = 用户钉死的硬约束（机器不许改）；
- CharacterDossier = PersonaExpander 从用户输入扩充出来的（用户可一键换），
  给单薄输入补上"过不去的坎"。两者都通过 render_for_prompt() 注入 analyst/writer。

See docs/superpowers/specs/2026-07-25-persona-dossier-content-quality-design.md §1.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional


def _as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


@dataclass(frozen=True)
class Conflict:
    angle: str = ""        # 代价 | 反面 | 谎言 | 未了
    premise: str = ""      # 从用户最强特质推：如"她很温柔"
    statement: str = ""    # 冲突一句话：如"她从不拒绝别人，但心里在记账"


@dataclass(frozen=True)
class BehaviorRules:
    avoid_topics: tuple[str, ...] = ()
    trigger: str = ""
    contradiction: str = ""     # 言行不一（最有用）
    breaking_point: str = ""    # 天然高潮位，挂"转"拍


@dataclass(frozen=True)
class CharacterDossier:
    expanded_bio: str = ""
    conflict: Conflict = Conflict()
    behavior_rules: BehaviorRules = BehaviorRules()

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["CharacterDossier"]:
        if not isinstance(data, dict):
            return None
        c = data.get("conflict"); c = c if isinstance(c, dict) else {}
        b = data.get("behavior_rules"); b = b if isinstance(b, dict) else {}
        dossier = cls(
            expanded_bio=str(data.get("expanded_bio", "")).strip(),
            conflict=Conflict(
                angle=str(c.get("angle", "")).strip(),
                premise=str(c.get("premise", "")).strip(),
                statement=str(c.get("statement", "")).strip(),
            ),
            behavior_rules=BehaviorRules(
                avoid_topics=_as_tuple(b.get("avoid_topics")),
                trigger=str(b.get("trigger", "")).strip(),
                contradiction=str(b.get("contradiction", "")).strip(),
                breaking_point=str(b.get("breaking_point", "")).strip(),
            ),
        )
        return None if dossier.is_empty() else dossier

    def is_empty(self) -> bool:
        c, b = self.conflict, self.behavior_rules
        return not (
            self.expanded_bio or c.premise or c.statement
            or b.avoid_topics or b.trigger or b.contradiction or b.breaking_point
        )

    def render_for_prompt(self) -> str:
        """结构化渲染进 prompt（只列非空字段）。"""
        lines: list[str] = []
        if self.expanded_bio:
            lines.append(f"- 人物小传假设（不是已证实履历）：{self.expanded_bio}")
        c = self.conflict
        if c.statement:
            angle = f"（{c.angle}）" if c.angle else ""
            lines.append(f"- 核心冲突假设{angle}：{c.statement}")
        b = self.behavior_rules
        if b.contradiction:
            lines.append(f"- 言行不一（贯穿全场，别点破）：{b.contradiction}")
        if b.trigger:
            lines.append(f"- 触发反应：{b.trigger}")
        if b.breaking_point:
            lines.append(f"- 临界反应（仅在内容自然触及时使用）：{b.breaking_point}")
        if b.avoid_topics:
            lines.append(f"- 会回避的话题（越回避越真实）：{'、'.join(b.avoid_topics)}")
        return "\n".join(lines)
