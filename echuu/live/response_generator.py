"""
LLM 驱动的弹幕响应生成器。
"""

from __future__ import annotations

import json
import random
from typing import Dict, Optional

from .llm_client import LLMClient
from .state import Danmaku, PerformerMemory


class DanmakuResponseGenerator:
    """
    使用 LLM 生成自然的弹幕响应。
    """

    RESPONSE_PROMPT = """你是一个正在直播的VTuber主播，名叫{name}。
你正在讲一个故事，突然看到了一条弹幕。请自然地回应它。

## 当前状态
- 正在讲的阶段: {stage}
- 刚才说的: {current_text_preview}
- 接下来本来要说: {next_text_preview}
- 已经提到过: {mentioned}

## 弹幕信息
- 用户: {danmaku_user}
- 内容: {danmaku_text}
- 类型: {danmaku_type}

## 回应要求
1. 口语化: 像真人直播一样说话，可以“诶”“哈哈”开头
2. 自然承接: 回应弹幕后要自然过渡回故事
3. 长度适中: 回应部分 20-50 字，然后继续故事
4. 根据类型调整:
   - SC打赏: 要感谢，可以稍微跑题聊聊
   - 问题: 如果答案马上要说就吊胃口，如果答案在后面就提前透露一点
   - 反应(哈哈/绝了): 简短回应，继续故事
   - 闲聊: 可以忽略或简单回应

## 输出格式（JSON）
{{
    "response": "你对弹幕的回应（口语化）",
    "action": "continue 或 adapt 或 digress",
    "next_content": "如果 action 是 adapt/digress，写融入弹幕后的下一段话；continue 留空"
}}

只输出 JSON，不要其他内容。"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def generate_response(
        self,
        danmaku: Danmaku,
        current_line,
        next_line: Optional,
        memory: PerformerMemory,
        name: str,
    ) -> Dict:
        """生成对弹幕的响应。"""
        if danmaku.is_sc:
            danmaku_type = f"SC打赏 (¥{danmaku.amount})"
        elif danmaku.is_question():
            danmaku_type = "问题"
        elif any(kw in danmaku.text for kw in ["哈哈", "笑", "绝", "离谱", "woc", "草"]):
            danmaku_type = "情绪反应"
        else:
            danmaku_type = "闲聊评论"

        mentioned = memory.story_points.get("mentioned", [])[-5:]

        prompt = self.RESPONSE_PROMPT.format(
            name=name,
            stage=current_line.stage,
            current_text_preview=current_line.text[:80] + "...",
            next_text_preview=next_line.text[:80] + "..." if next_line else "（故事即将结束）",
            mentioned=", ".join(mentioned) if mentioned else "还没开始讲",
            danmaku_user=danmaku.user,
            danmaku_text=danmaku.text,
            danmaku_type=danmaku_type,
        )

        try:
            response_text = self.llm.call(
                system="你是一个VTuber主播，正在直播。用JSON格式回复。",
                prompt=prompt,
                max_tokens=500,
            )

            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0]
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0]

            result = json.loads(response_text.strip())
            result.setdefault("response", f"哈哈{danmaku.text}！")
            result.setdefault("action", "continue")
            result.setdefault("next_content", "")
            return result
        except Exception as exc:
            print(f"[DanmakuResponse] LLM 调用失败: {exc}")
            return {
                "response": f"哈哈有人说'{danmaku.text}'！",
                "action": "continue",
                "next_content": "",
            }

    def generate_quick_response(self, danmaku: Danmaku) -> str:
        """快速生成简单回应（不调用 LLM）。"""
        if danmaku.is_sc:
            return f"感谢{danmaku.user}的SC！"
        if danmaku.is_question():
            return f"有人问'{danmaku.text}'，等下会说到的~"
        quick_responses = [
            f"哈哈'{danmaku.text}'！",
            f"对对对{danmaku.text}！",
            "弹幕说得对！",
        ]
        return random.choice(quick_responses)
