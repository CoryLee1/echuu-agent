"""
表演执行器（实时弹幕互动 + 记忆系统 + 多语言支持）。
"""

from __future__ import annotations

import random
from typing import Dict, List, Optional

from .danmaku import DanmakuHandler
from .llm_client import LLMClient
from .response_generator import DanmakuResponseGenerator
from .state import Danmaku, PerformanceState
from .tts_client import TTSClient
from .language import StreamLanguageContext


class PerformerV3:
    """
    表演引擎 V3 - 带记忆系统、统一弹幕处理和多语言支持。
    """

    def __init__(
        self,
        llm: LLMClient,
        tts: TTSClient,
        danmaku_handler: DanmakuHandler,
        stream_lang_context: Optional[StreamLanguageContext] = None
    ):
        self.llm = llm
        self.tts = tts
        self.danmaku_handler = danmaku_handler
        self.response_generator = DanmakuResponseGenerator(llm, stream_lang_context)

    def step(self, state: PerformanceState, new_danmaku: Optional[List[Danmaku]] = None) -> Dict:
        """
        执行一步表演。
        """
        if new_danmaku:
            state.danmaku_queue.extend(new_danmaku)
            for dm in new_danmaku:
                state.memory.danmaku_memory["received"].append(dm.text)
                # 更新用户档案（自动记录互动）
                state.memory.update_user_from_danmaku(dm)

        if state.current_line_idx >= len(state.script_lines):
            return self._generate_ending(state)

        current_line = state.script_lines[state.current_line_idx]

        best_danmaku = None
        handle_result = None

        if state.danmaku_queue:
            for danmaku in state.danmaku_queue:
                result = self.danmaku_handler.handle(danmaku, state)
                if result.get("should_interrupt"):
                    if best_danmaku is None or result.get("priority", 0) > handle_result.get(
                        "priority", 0
                    ):
                        best_danmaku = danmaku
                        handle_result = result

        if best_danmaku and handle_result:
            output = self._handle_danmaku_response(best_danmaku, handle_result, current_line, state)
            state.danmaku_queue = [d for d in state.danmaku_queue if d != best_danmaku]
            state.memory.danmaku_memory["responded"].append(best_danmaku.text)

            if best_danmaku.is_question() and handle_result.get("action") == "tease":
                answer_loc = handle_result.get("answer_loc", {})
                if answer_loc.get("found"):
                    state.memory.promises.append(
                        {
                            "content": best_danmaku.text,
                            "made_at_step": state.current_step,
                            "fulfilled": False,
                            "answer_at_line": answer_loc.get("line_idx"),
                        }
                    )
        else:
            output = {
                "speech": current_line.text,
                "action": "continue",
                "priority": 0.0,
                "cost": current_line.interruption_cost,
            }

        state.current_line_idx += 1
        state.current_step += 1

        for info in current_line.key_info:
            if info not in state.memory.story_points["mentioned"]:
                state.memory.story_points["mentioned"].append(info)

        state.memory.script_progress["current_line"] = state.current_line_idx
        state.memory.script_progress["total_lines"] = len(state.script_lines)
        state.memory.script_progress["current_stage"] = current_line.stage

        self._check_promises(current_line, state)

        speech = output.get("speech", "")
        audio = None
        if speech and self.tts.enabled:
            emotion_boost = {
                "Hook": 0.3,
                "Build-up": 0.2,
                "Climax": 0.8,
                "Resolution": 0.4,
            }.get(current_line.stage, 0.0)

            if isinstance(current_line.emotion_break, dict):
                level = current_line.emotion_break.get("level", 0)
                emotion_boost += level * 0.15

            if output.get("action") in ["tease", "improvise", "jump"]:
                emotion_boost += 0.2

            emotion_boost = min(1.0, emotion_boost)
            audio = self.tts.synthesize(speech, emotion_boost=emotion_boost)

        output["audio"] = audio
        output["line_idx"] = state.current_line_idx - 1
        output["stage"] = current_line.stage
        output["step"] = state.current_step
        output["disfluencies"] = current_line.disfluencies
        output["emotion_break"] = current_line.emotion_break
        # 添加表演标注
        output["cue"] = current_line.cue.to_dict() if hasattr(current_line, 'cue') and current_line.cue else None

        if isinstance(current_line.emotion_break, dict):
            state.memory.emotion_track.append(
                {
                    "step": state.current_step,
                    "line_idx": state.current_line_idx - 1,
                    "level": current_line.emotion_break.get("level", 0),
                    "trigger": current_line.emotion_break.get("trigger", ""),
                    "stage": current_line.stage,
                }
            )

        output["memory_display"] = state.memory.to_display()
        return output

    def _handle_danmaku_response(
        self,
        danmaku: Danmaku,
        handle_result: Dict,
        current_line,
        state: PerformanceState,
    ) -> Dict:
        """处理弹幕回应 - 使用 LLM 基于用户档案生成自然回应。"""
        next_line = None
        if state.current_line_idx < len(state.script_lines) - 1:
            next_line = state.script_lines[state.current_line_idx + 1]

        llm_result = self.response_generator.generate_response(
            danmaku=danmaku,
            current_line=current_line,
            next_line=next_line,
            memory=state.memory,
            name=state.name,
            persona=state.persona,
            background=state.background,
        )

        response = llm_result.get("response", "")
        llm_action = llm_result.get("action", "continue")
        next_content = llm_result.get("next_content", "")

        if llm_action == "continue":
            speech = f"{response} {current_line.text}"
        elif llm_action == "adapt":
            speech = f"{response} {next_content or current_line.text}"
        elif llm_action == "digress":
            if next_content:
                speech = f"{response} {next_content}"
            else:
                transition = self._generate_transition()
                speech = f"{response} {transition}{current_line.text}"
        else:
            speech = f"{response} {current_line.text}"

        return {
            "speech": speech,
            "action": handle_result.get("action", "improvise"),
            "llm_action": llm_action,
            "danmaku": danmaku.text,
            "priority": handle_result.get("priority", 0),
            "cost": handle_result.get("cost", 0),
            "relevance": handle_result.get("relevance", 0),
        }

    def _generate_transition(self) -> str:
        """生成承接语。"""
        transitions = ["好，那刚才说到，", "回到我们的故事，", "继续说，", "对了，", ""]
        return random.choice(transitions)

    def _check_promises(self, current_line, state: PerformanceState):
        """检查当前台词是否兑现了承诺。"""
        for promise in state.memory.promises:
            if promise.get("fulfilled", False):
                continue
            if promise.get("answer_at_line") == state.current_line_idx - 1:
                promise["fulfilled"] = True

    def _generate_ending(self, state: PerformanceState) -> Dict:
        """生成结尾。"""
        speech = f"好啦，今天关于{state.topic}就聊到这里，谢谢大家！"
        audio = self.tts.synthesize(speech) if self.tts.enabled else None
        return {
            "speech": speech,
            "action": "end",
            "step": state.current_step,
            "audio": audio,
            "disfluencies": [],
            "emotion_break": None,
            "memory_display": state.memory.to_display(),
        }
