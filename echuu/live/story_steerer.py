"""把观众弹幕 / 投喂写进尚未播出的故事走向。

穿插回应只是当场接一句；steerer 改后面还没讲的台词和剩余 beats，
这样下一段会真的往观众推的方向走，而不是讲完原剧本再当没发生。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Protocol

from echuu.live.untrusted import sanitize_untrusted


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_REWRITE_PROMPT = """\
你在给一场正在直播的故事改「下一句还没播出的台词」。
观众刚刚用{kind}推了一把方向，后面必须接住，但不能丢掉主轴。

主轴（必须还是这件事）：{spine}
正在讲的话题：{topic}
观众是谁：{user}
观众刚说/刚做：{trigger}

原定下一句：
{line}

要求：
- 只输出改写后的一句口语台词，不要解释、不要引号、不要括号说明。
- 仍然服务主轴，但明显接住观众刚推的方向（提问就回应关切，投喂就带上这份心意再往下讲）。
- 不要另开一个新故事，不要复述设定表。
"""


class StorySteerer:
    def __init__(self, llm: _LLM) -> None:
        self.llm = llm

    def rewrite_line(self, *, spine: str, topic: str, user: str, trigger: str,
                     kind: str, line: str) -> str | None:
        prompt = _REWRITE_PROMPT.format(
            kind="投喂" if kind == "gift" else "弹幕",
            spine=spine or topic or "正在讲的事",
            topic=topic or "（正在讲的事）",
            user=sanitize_untrusted(user or "观众", max_chars=24),
            trigger=sanitize_untrusted(trigger or "", max_chars=120),
            line=line or "",
        )
        try:
            text = self.llm.generate(prompt)
        except Exception as exc:  # noqa: BLE001 — 转向失败不挡当场回应
            print(f"[StorySteerer] 改写下一句失败（跳过）: {exc}")
            return None
        text = (text or "").strip().strip('"“”')
        return text or None


def annotate_remaining_beats(story_core, trigger: str):
    """给还没走完的 beats 挂上观众方向（frozen StoryCore 用 replace）。"""
    if story_core is None:
        return story_core
    beats = list(getattr(story_core, "story_beats", ()) or ())
    if not beats:
        return story_core
    note = sanitize_untrusted(trigger, max_chars=24)
    if not note:
        return story_core
    beats[-1] = f"{beats[-1]}（接住观众：{note}）"
    return replace(story_core, story_beats=tuple(beats))
