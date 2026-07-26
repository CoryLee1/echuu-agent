"""Discourse-mode routing for generalized live-content planning.

The router intentionally lives outside the prompt strings so the accepted
mode vocabulary and deterministic fallback stay versionable and testable.
"""
from __future__ import annotations

from typing import Final


DISCOURSE_MODES: Final[tuple[str, ...]] = (
    "narrative",
    "commentary",
    "advice",
    "banter",
    "emotional",
    "explainer",
    "reaction",
)

MODE_LABELS: Final[dict[str, str]] = {
    "narrative": "故事叙述",
    "commentary": "观点评论",
    "advice": "问答建议",
    "banter": "联动接梗",
    "emotional": "情绪分享",
    "explainer": "解释科普",
    "reaction": "即时反应",
}

MODE_GUIDES: Final[dict[str, str]] = {
    "narrative": "具体场景 → 事情发展 → 关键变化/发现 → 回到当下；允许转折，但不必硬造金句。",
    "commentary": "明确主张 → 个人依据 → 反方或边界 → 更精确的立场；重点是观点推进，不强编故事。",
    "advice": "复述真实问题 → 拆解条件与代价 → 给出可执行判断 → 说明适用边界；不替观众做绝对决定。",
    "banter": "接住对方/观众的话 → 抓矛盾或包袱 → 追击并留回应空间 → callback；不替对方编台词。",
    "emotional": "说清当下感受 → 给出具体体验 → 承认矛盾或尚未解决之处 → 自然停住；不强行治愈或升华。",
    "explainer": "提出问题 → 用生活化例子解释机制 → 处理常见误解 → 给出可复述结论。",
    "reaction": "即时反应 → 说出触发细节 → 联想到个人经验/判断 → 回到现场；保留 spontanity，不过度规划。",
}


def normalize_discourse_mode(value: str | None, *context: str) -> str:
    """Return a supported mode, using a deterministic lexical fallback."""
    mode = (value or "").strip().lower()
    if mode in DISCOURSE_MODES:
        return mode

    text = " ".join(part or "" for part in context).lower()
    keyword_groups = (
        ("banter", ("联动", "嘉宾", "采访", "接梗", "挑战", "安全词", "collab", "banter")),
        ("advice", ("怎么办", "建议", "该不该", "选择", "求助", "劝", "advice")),
        ("explainer", ("科普", "解释", "原理", "机制", "经济学", "为什么会", "explain")),
        ("reaction", ("反应", "初见", "试玩", "看完", "现场", "reaction")),
        ("emotional", ("脆弱", "悲伤", "难过", "焦虑", "痛苦", "感悟", "sad", "vulnerable")),
        ("commentary", ("观点", "辩护", "哲学", "意义", "讨论", "论", "看法", "opinion")),
    )
    for candidate, keywords in keyword_groups:
        if any(keyword in text for keyword in keywords):
            return candidate
    return "narrative"
