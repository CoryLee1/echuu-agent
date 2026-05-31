"""DanmakuInterleaver — 在讲故事的间隙穿插一句人设化的弹幕回应。

Cursor 式交付：故事行是队列，主播讲完一行后在断点回应一条弹幕，再回到故事。
约束（spec 反馈）：弹幕只穿插【反应】，不改主播讲故事的方式与关注的重点；
故事队列本身不被改写。回应简短、带语癖、点名观众、最后拉回正在讲的事。

See docs/superpowers/specs/2026-05-31-rupture-engine-content-quality-design.md.
"""
from __future__ import annotations

from typing import Protocol


class _LLM(Protocol):
    def generate(self, prompt: str) -> str: ...


_PROMPT = """\
你在演一个正在直播讲故事的主播，此刻有条弹幕飘过，你要【插一句话】回应观众，然后马上回到你的故事。

你是谁：{identity}
你的语癖（用一个）：{verbal_tics}
你正在讲的事（重点，别跑偏）：{topic}
你刚说到：{last_line}

弹幕来自【{user}】：{danmaku}

要求：
- 只回 1-2 句，像真主播随口接一下，自然口语，带一点你的语癖。
- 点一下这位观众（用名字或"这位"），简短反应，然后一句话拉回你正在讲的事。
- 绝不改变你故事的重点和走向，别开新话题、别长篇大论。
- 只输出你要说的话，不要任何解释、不要引号、不要括号说明。
"""


class DanmakuInterleaver:
    def __init__(self, llm: _LLM) -> None:
        self.llm = llm

    def respond(self, *, identity: str, verbal_tics, topic: str,
                last_line: str, danmaku_text: str, user: str) -> str | None:
        tics = "、".join(verbal_tics) if verbal_tics else "（自然口语）"
        prompt = _PROMPT.format(
            identity=identity or "一个主播",
            verbal_tics=tics,
            topic=topic or "（正在讲的事）",
            last_line=last_line or "",
            user=user or "观众",
            danmaku=danmaku_text or "",
        )
        try:
            reply = self.llm.generate(prompt)
        except Exception as exc:
            print(f"[DanmakuInterleaver] LLM 调用失败，跳过本次穿插: {exc}")
            return None
        reply = (reply or "").strip().strip('"“”')
        return reply or None
