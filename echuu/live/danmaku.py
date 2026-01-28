"""
弹幕处理逻辑。
"""

from __future__ import annotations

import random
import re
from typing import Dict, List

from .state import Danmaku, PerformanceState


def extract_keywords(text: str) -> List[str]:
    """提取关键词（简单版）。"""
    text = re.sub(r"[，。！？、：；\"\"''（）【】《》…~]", " ", text)
    words = text.split()
    stopwords = {
        "的",
        "了",
        "在",
        "是",
        "我",
        "你",
        "他",
        "她",
        "它",
        "们",
        "这",
        "那",
        "有",
        "和",
        "就",
        "不",
        "也",
        "都",
        "说",
        "很",
        "吗",
        "吧",
        "呢",
        "啊",
        "哦",
        "嗯",
        "哈",
        "呀",
    }
    keywords = [w for w in words if len(w) >= 2 and w not in stopwords]
    return keywords[:5]


class DanmakuEvaluator:
    """
    弹幕评估器 - 计算优先级。

    priority = base_score + relevance_bonus + sc_bonus
    """

    def evaluate(self, danmaku: Danmaku, state: PerformanceState) -> Danmaku:
        """评估单条弹幕。"""
        if danmaku.is_question():
            base = 0.5
        elif any(
            kw in danmaku.text for kw in ["哈哈", "笑死", "真的假的", "！", "牛", "woc", "啊这", "离谱", "绝了"]
        ):
            base = 0.35
        else:
            base = 0.25

        if random.random() < 0.2:
            base += 0.3

        relevance = self._calc_relevance(danmaku.text, state)
        danmaku.relevance = relevance

        if relevance > 0.7:
            relevance_bonus = 0.4
        elif relevance > 0.4:
            relevance_bonus = 0.2
        else:
            relevance_bonus = 0.0

        if danmaku.is_sc:
            if danmaku.amount >= 200:
                sc_bonus = 0.7
            elif danmaku.amount >= 100:
                sc_bonus = 0.5
            elif danmaku.amount >= 50:
                sc_bonus = 0.3
            else:
                sc_bonus = 0.2
        else:
            sc_bonus = 0.0

        danmaku.priority = base + relevance_bonus + sc_bonus
        return danmaku

    def _calc_relevance(self, text: str, state: PerformanceState) -> float:
        """计算弹幕与当前上下文的相关性。"""
        story_keywords = set()
        for info in state.memory.story_points.get("mentioned", []):
            story_keywords.update(extract_keywords(info))
        for info in state.memory.story_points.get("upcoming", []):
            story_keywords.update(extract_keywords(info))

        if not story_keywords:
            story_keywords.update(extract_keywords(state.topic))

        danmaku_keywords = set(extract_keywords(text))
        if not story_keywords:
            return 0.0

        overlap = len(danmaku_keywords & story_keywords)
        return min(overlap / 2, 1.0)


class DanmakuHandler:
    """
    统一弹幕处理器。

    根据优先级决定是否打断以及行动策略。
    """

    def __init__(self, evaluator: DanmakuEvaluator):
        self.evaluator = evaluator

    def handle(self, danmaku: Danmaku, state: PerformanceState) -> Dict:
        """处理弹幕。"""
        danmaku = self.evaluator.evaluate(danmaku, state)

        if state.current_line_idx >= len(state.script_lines):
            current_cost = 0.2
        else:
            current_line = state.script_lines[state.current_line_idx]
            current_cost = current_line.interruption_cost

        effective_cost = current_cost * 0.7
        random_interrupt = random.random() < 0.15
        should_interrupt = danmaku.priority > effective_cost or (
            danmaku.priority > 0.3 and random_interrupt
        )

        if not should_interrupt:
            return {
                "should_interrupt": False,
                "action": "ignore",
                "priority": danmaku.priority,
                "cost": current_cost,
            }

        echo = self._maybe_echo(danmaku)
        answer_loc = self._find_answer(danmaku.text, state)
        action = self._decide_action(danmaku, answer_loc)

        return {
            "should_interrupt": True,
            "echo": echo,
            "action": action,
            "answer_loc": answer_loc,
            "priority": danmaku.priority,
            "cost": current_cost,
            "relevance": danmaku.relevance,
        }

    def _maybe_echo(self, danmaku: Danmaku) -> str:
        """决定是否复读弹幕。"""
        if danmaku.is_sc:
            return f"诶有SC！有人说：{danmaku.text}"
        if danmaku.priority > 0.5:
            return f"有人说{danmaku.text}，"
        if danmaku.is_question():
            return f"有人问{danmaku.text}，"
        return ""

    def _find_answer(self, question: str, state: PerformanceState) -> Dict:
        """在剧本中查找问题的答案位置。"""
        keywords = extract_keywords(question)
        current_idx = state.current_line_idx

        for i, line in enumerate(state.script_lines):
            if i < current_idx:
                continue
            for info in line.key_info:
                if any(kw in info for kw in keywords):
                    return {
                        "found": True,
                        "line_idx": i,
                        "distance": i - current_idx,
                        "answer_hint": info,
                    }

        return {"found": False}

    def _decide_action(self, danmaku: Danmaku, answer_loc: Dict) -> str:
        """决定叙事动作。"""
        if not answer_loc.get("found", False):
            return "improvise"

        distance = answer_loc.get("distance", 0)

        if danmaku.priority > 0.8:
            if distance <= 3:
                return "jump"
            return "tease"
        if danmaku.priority > 0.5:
            if distance <= 2:
                return "continue"
            return "tease"
        return "continue"
