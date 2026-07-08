"""三模式共享的开场/收尾段（rundown segments）。

治「观众进来一头雾水」：开场 = 打招呼 + 说今天要干嘛 + 过渡；
收尾 = 随口感想 + 道别。自然感硬约束（Cory 确认）：
- 生成走 persona prompt + StructureBreaker（开场 insert_thread_loss，收尾 break_structure 去升华/非闭合）
- CLS 固定 NATURAL_CASUAL，TTS 走现有 CLS→情绪指令映射
- 禁止"大家好我是AI主播"式播报腔（prompt 里写死）
"""
from __future__ import annotations

from typing import Callable, List, Optional

from .reaction import _cls_instruction, _parse_json_array

_MODE_INTENT = {
    "storytelling": "今天要聊的话题是「{topic}」",
    "reaction": "今天要和观众一起看一个视频（主题：{topic}），你自己也是第一次看",
    "singing_learn": "今天要现场挑战学唱一首歌（{topic}），大概率会翻车",
}

_OPENING_PROMPT = """你是虚拟主播「{name}」。人设：{persona}
你刚打开直播间，观众陆续进来。{intent}。
写 2-3 句开场白。要求：
- 像溜达进直播间随口打招呼，禁止「大家好我是AI主播」「欢迎来到直播间」式播报腔
- 第 1 句打招呼（带你的口癖），第 2 句说今天要干嘛，最后半句自然过渡到正式开始
- 每句 10-25 字，口语，可以带「诶/嗯/那个」这类碎语
输出 JSON 数组（不要 markdown 代码块）：[{{"text": "...", "emotion": "joy|excited|surprised|shy 之一"}}]"""

_CLOSING_PROMPT = """你是虚拟主播「{name}」。人设：{persona}
{intent}，现在直播到尾声了。写 1-2 句收尾。要求：
- 一句对今天内容的随口感想（具体一点，不要「今天很开心」这种空话），一句道别
- 禁止升华、禁止「感谢大家的陪伴」式套话；可以留一个没说完的小尾巴
- 每句 10-25 字，口语
输出 JSON 数组（不要 markdown 代码块）：[{{"text": "...", "emotion": "joy|relaxed|shy 之一"}}]"""


def _generate_lines(engine, prompt: str) -> List[dict]:
    raw = engine.llm.call(prompt, max_tokens=400)
    items = _parse_json_array(raw)
    lines = []
    for item in items:
        text = str(item.get("text", "")).strip()
        if not text:
            continue
        lines.append({
            "text": text,
            "emotion": str(item.get("emotion", "joy")).lower(),
            "language": "zh",
        })
    return lines


def _to_events(lines: List[dict], mode: str, stage: str, tts_client,
               on_phase: Optional[Callable[[str], None]] = None) -> List[dict]:
    motion_state = "greet" if stage == "opening" else "farewell"
    events: List[dict] = []
    for line in lines:
        tts_client.set_instruction(_cls_instruction("NATURAL_CASUAL", line["emotion"]))
        audio = None
        for attempt in range(2):
            try:
                audio = tts_client.synthesize(line["text"])
                if audio:
                    break
            except Exception as exc:  # noqa: BLE001 — TTS 失败降级为纯字幕
                print(f"[rundown] TTS 失败（第{attempt + 1}次）: {exc}")
        events.append({
            "type": "step",
            "mode": mode,
            "event": stage,
            "stage": stage,
            "speech": line["text"],
            "emotion": line["emotion"],
            "cls": "NATURAL_CASUAL",
            "motion": {"state": motion_state},
            "audio": audio,
        })
    if on_phase:
        on_phase(f"{stage} 段就绪：{len(events)} 句")
    return events


def produce_opening_events(engine, name: str, persona: str, topic: str, mode: str,
                           on_phase: Optional[Callable[[str], None]] = None,
                           tts=None) -> List[dict]:
    intent = _MODE_INTENT.get(mode, _MODE_INTENT["storytelling"]).format(topic=topic)
    lines = _generate_lines(engine, _OPENING_PROMPT.format(name=name, persona=persona, intent=intent))[:3]
    lines = engine.structure_breaker.insert_thread_loss(lines, probability=0.2)
    return _to_events(lines, mode, "opening", tts or engine.tts, on_phase)


def produce_closing_events(engine, name: str, persona: str, topic: str, mode: str,
                           on_phase: Optional[Callable[[str], None]] = None,
                           tts=None) -> List[dict]:
    intent = _MODE_INTENT.get(mode, _MODE_INTENT["storytelling"]).format(topic=topic)
    lines = _generate_lines(engine, _CLOSING_PROMPT.format(name=name, persona=persona, intent=intent))[:2]
    lines = engine.structure_breaker.break_structure(lines, topic=topic, language="zh")
    return _to_events(lines, mode, "closing", tts or engine.tts, on_phase)
