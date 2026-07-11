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
{card_rules}"""

_QUIP_PROMPT = """\
你在演一个正在直播的主播。你刚向观众抛了一个问题，结果弹幕没人理你。
自嘲一句（1 句，带你的语癖，别卖惨），然后半句话接回你正在讲的事。

你是谁：{identity}
你的语癖（用一个）：{verbal_tics}
你刚问的：{question}
你正在讲的事：{topic}

只输出你要说的话，不要任何解释、不要引号、不要括号说明。
"""


class DanmakuInterleaver:
    def __init__(self, llm: _LLM) -> None:
        self.llm = llm

    def respond(self, *, identity: str, verbal_tics, topic: str,
                last_line: str, danmaku_text: str, user: str,
                card=None, gags=None) -> str | None:
        tics = "、".join(verbal_tics) if verbal_tics else "（自然口语）"
        # 人设卡加成：固定称呼；雷点被戳 → 破防加倍；骄傲点被夸/被质疑 → 反应加倍；顺手挂已埋的梗
        card_rules = ""
        if card is not None:
            rules = []
            if getattr(card, "audience_nickname", ""):
                rules.append(f"- 提到观众整体时用固定称呼「{card.audience_nickname}」。")
            if getattr(card, "fears", ()):
                rules.append(f"- 若弹幕戳中你的雷点（{'；'.join(card.fears)}），反应要明显破防/炸毛，加倍！")
            if getattr(card, "prides", ()):
                rules.append(f"- 若弹幕夸到/质疑你的骄傲点（{'；'.join(card.prides)}），要明显得意/不服，加倍！")
            if rules:
                card_rules += "\n".join(rules) + "\n"
        if gags:
            card_rules += f"- 如果能自然接上你前面埋的梗（{'；'.join(gags)}），优先顺手接一下。\n"
        prompt = _PROMPT.format(
            identity=identity or "一个主播",
            verbal_tics=tics,
            topic=topic or "（正在讲的事）",
            last_line=last_line or "",
            user=user or "观众",
            danmaku=danmaku_text or "",
            card_rules=card_rules,
        )
        try:
            reply = self.llm.generate(prompt)
        except Exception as exc:
            print(f"[DanmakuInterleaver] LLM 调用失败，跳过本次穿插: {exc}")
            return None
        reply = (reply or "").strip().strip('"“”')
        return reply or None

    def no_reaction_quip(self, *, identity: str, verbal_tics, topic: str,
                         question: str) -> str | None:
        """互动点没人理时的自嘲兜底（不写死台词，人设化生成）。"""
        tics = "、".join(verbal_tics) if verbal_tics else "（自然口语）"
        prompt = _QUIP_PROMPT.format(
            identity=identity or "一个主播",
            verbal_tics=tics,
            question=question or "",
            topic=topic or "（正在讲的事）",
        )
        try:
            reply = self.llm.generate(prompt)
        except Exception as exc:
            print(f"[DanmakuInterleaver] 自嘲兜底生成失败，跳过: {exc}")
            return None
        reply = (reply or "").strip().strip('"“”')
        return reply or None
