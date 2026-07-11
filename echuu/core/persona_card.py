"""PersonaCard — 用户可控的结构化人设卡（Phase 2-①）。

与 PersonaAnalyst 推导的 RichPersona 的分工：
- RichPersona = 每场即席推导（身份/信念/弱点/故事内核），场与场之间会漂；
- PersonaCard = 用户钉死的稳定输入（口癖/观众称呼/雷点/骄傲点/固定bit），
  跨场一致，是"角色认得出来"的根基。卡缺省时行为与之前完全一致（analyst 自由发挥）。

See docs/superpowers/specs/2026-07-11-phase2-entertainment-persona-card.md §1.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


def _as_tuple(value: Any) -> tuple[str, ...]:
    if isinstance(value, (list, tuple)):
        return tuple(str(v).strip() for v in value if str(v).strip())
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


@dataclass(frozen=True)
class PersonaCard:
    name: str = ""
    tagline: str = ""                          # 一句话人设（兼容现有 persona 字段）
    speech_tics: tuple[str, ...] = ()          # 口癖/语尾，硬约束进台词
    audience_nickname: str = ""                # 对观众的固定称呼
    metaphor_domain: str = ""                  # 惯用比喻域
    stances: tuple[str, ...] = ()              # 立场与偏见
    fears: tuple[str, ...] = ()                # 雷点（弹幕戳中 → 反应加倍）
    prides: tuple[str, ...] = ()               # 骄傲点（被夸会飘，被质疑会炸毛）
    running_gags: tuple[str, ...] = ()         # 固定 bit
    backstory: str = ""                        # 背景故事（兼容现有 background）

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> Optional["PersonaCard"]:
        if not isinstance(data, dict):
            return None
        card = cls(
            name=str(data.get("name", "")).strip(),
            tagline=str(data.get("tagline", "")).strip(),
            speech_tics=_as_tuple(data.get("speech_tics")),
            audience_nickname=str(data.get("audience_nickname", "")).strip(),
            metaphor_domain=str(data.get("metaphor_domain", "")).strip(),
            stances=_as_tuple(data.get("stances")),
            fears=_as_tuple(data.get("fears")),
            prides=_as_tuple(data.get("prides")),
            running_gags=_as_tuple(data.get("running_gags")),
            backstory=str(data.get("backstory", "")).strip(),
        )
        return None if card.is_empty() else card

    def is_empty(self) -> bool:
        return not (
            self.speech_tics or self.audience_nickname or self.metaphor_domain
            or self.stances or self.fears or self.prides or self.running_gags
        )

    def render_for_prompt(self) -> str:
        """结构化渲染进 prompt 的人设卡段落（只列非空字段）。"""
        lines: list[str] = []
        if self.tagline:
            lines.append(f"- 一句话人设：{self.tagline}")
        if self.speech_tics:
            lines.append(f"- 口癖（必须自然织进台词，不许发明新口癖）：{'、'.join(self.speech_tics)}")
        if self.audience_nickname:
            lines.append(f"- 对观众的固定称呼（提到观众必须用它）：{self.audience_nickname}")
        if self.metaphor_domain:
            lines.append(f"- 惯用比喻域（打比方优先从这里取）：{self.metaphor_domain}")
        if self.stances:
            lines.append(f"- 立场与偏见（敢说、态度一致）：{'；'.join(self.stances)}")
        if self.fears:
            lines.append(f"- 雷点/害怕（被戳中会明显破防）：{'；'.join(self.fears)}")
        if self.prides:
            lines.append(f"- 骄傲点（被夸会飘、被质疑会炸毛）：{'；'.join(self.prides)}")
        if self.running_gags:
            lines.append(f"- 固定 bit/常驻梗（可自然复用）：{'；'.join(self.running_gags)}")
        return "\n".join(lines)
