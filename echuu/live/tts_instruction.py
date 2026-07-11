"""CLS 认知负荷状态 → Qwen3-TTS-Instruct 自然语言情绪指令。

CLS（Cognitive Load State）是设计层概念（见 3modes 设计文档），代码里没有
显式字段，由剧本已有信号推导：
  - line.stage: hook / pad / turn
  - line.is_rupture: 结构断裂点（卡壳、自我修正）
  - unit.density: high / medium / low（能量提示）
  - line.cue.emotion: PerformerCue 的情绪键（可选，优先级最高）

映射仅在 TTS_MODEL 为 instruct 系列时生效（非 instruct 模型忽略指令）。
"""
from __future__ import annotations

# CLS 四态的基础指令
CLS_INSTRUCTIONS = {
    "NATURAL_CASUAL": "随意放松的日常聊天语气，语速自然，像跟熟人闲聊",
    "THEATRICAL": "夸张有戏剧张力的演绎语气，情绪起伏明显，抑扬顿挫",
    "HIGH_LOAD": "犹豫磕绊，像在边想边说，语速偏慢，带思考停顿和不确定感",
    "HYPER_FLUENT": "想通了一口气流畅推进，语速略快，情绪投入兴奋",
}

# PerformerCue 情绪键 → 指令补充（叠加在 CLS 基础指令后）
_EMOTION_HINTS = {
    "joy": "带着藏不住的开心",
    "excited": "非常兴奋，音调上扬",
    "sad": "低落，声音发闷",
    "angry": "带着一点火气",
    "surprised": "惊讶，语气突然拔高",
    "frustrated": "不甘心又有点烦躁",
    "shy": "有点不好意思，声音变小",
    "smug": "得意洋洋",
}


def infer_cls(unit, line) -> str:
    """由剧本信号推导 CLS 状态。"""
    if getattr(line, "is_rupture", False):
        return "HIGH_LOAD"
    stage = getattr(line, "stage", "pad")
    if stage == "hook":
        return "NATURAL_CASUAL"
    if stage == "turn":
        return "HYPER_FLUENT"
    # pad: 按单元能量分
    density = getattr(unit, "density", "medium")
    return "THEATRICAL" if density == "high" else "NATURAL_CASUAL"


def build_instruction(unit, line) -> str:
    """组合 CLS 基础指令 + cue 情绪补充，返回给 TTS 的自然语言指令。"""
    cls_state = infer_cls(unit, line)
    parts = [CLS_INSTRUCTIONS[cls_state]]

    cue = getattr(line, "cue", None)
    emotion = getattr(getattr(cue, "emotion", None), "key", None) if cue else None
    emotion_key = getattr(emotion, "value", emotion)  # Enum → str
    if emotion_key and str(emotion_key) in _EMOTION_HINTS:
        parts.append(_EMOTION_HINTS[str(emotion_key)])

    return "，".join(parts)
