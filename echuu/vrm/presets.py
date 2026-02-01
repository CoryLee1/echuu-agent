"""
动作预设库

提供常用手势/动作的预设，供剧本生成时使用。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional
import random


class GestureCategory(str, Enum):
    """动作分类"""
    IDLE = "idle"           # 待机动作
    TALK = "talk"           # 说话动作
    EMOTE = "emote"         # 表情动作
    REACT = "react"         # 反应动作
    POSE = "pose"           # 姿势动作


@dataclass
class GesturePreset:
    """动作预设定义"""
    name: str                           # 动作名称
    category: GestureCategory           # 分类
    duration: float                     # 建议时长（秒）
    loop: bool                          # 是否循环
    compatible_emotions: List[str]      # 兼容的情绪
    description: str                    # 中文描述
    weight: float = 1.0                 # 默认权重


# 动作预设库 - 18个常用动作
GESTURE_PRESETS: Dict[str, GesturePreset] = {
    # === 待机动作 ===
    "idle_breathe": GesturePreset(
        name="idle_breathe",
        category=GestureCategory.IDLE,
        duration=3.0,
        loop=True,
        compatible_emotions=["neutral", "relaxed", "happy", "sad"],
        description="平静呼吸",
    ),
    "idle_sway": GesturePreset(
        name="idle_sway",
        category=GestureCategory.IDLE,
        duration=4.0,
        loop=True,
        compatible_emotions=["neutral", "relaxed", "happy"],
        description="轻微摇晃",
    ),
    "idle_look_around": GesturePreset(
        name="idle_look_around",
        category=GestureCategory.IDLE,
        duration=2.5,
        loop=False,
        compatible_emotions=["neutral", "surprised"],
        description="环顾四周",
    ),

    # === 说话动作 ===
    "talk_gesture_small": GesturePreset(
        name="talk_gesture_small",
        category=GestureCategory.TALK,
        duration=1.5,
        loop=False,
        compatible_emotions=["neutral", "relaxed"],
        description="小幅度手势",
    ),
    "talk_gesture_medium": GesturePreset(
        name="talk_gesture_medium",
        category=GestureCategory.TALK,
        duration=2.0,
        loop=False,
        compatible_emotions=["neutral", "happy", "surprised"],
        description="中等手势",
    ),
    "talk_gesture_big": GesturePreset(
        name="talk_gesture_big",
        category=GestureCategory.TALK,
        duration=2.5,
        loop=False,
        compatible_emotions=["happy", "angry", "surprised"],
        description="大幅度手势",
    ),
    "talk_point": GesturePreset(
        name="talk_point",
        category=GestureCategory.TALK,
        duration=1.0,
        loop=False,
        compatible_emotions=["neutral", "angry", "surprised"],
        description="指点手势",
    ),

    # === 表情动作 ===
    "emote_nod": GesturePreset(
        name="emote_nod",
        category=GestureCategory.EMOTE,
        duration=0.8,
        loop=False,
        compatible_emotions=["neutral", "happy", "relaxed"],
        description="点头",
    ),
    "emote_shake_head": GesturePreset(
        name="emote_shake_head",
        category=GestureCategory.EMOTE,
        duration=1.0,
        loop=False,
        compatible_emotions=["sad", "angry", "neutral"],
        description="摇头",
    ),
    "emote_tilt_head": GesturePreset(
        name="emote_tilt_head",
        category=GestureCategory.EMOTE,
        duration=0.6,
        loop=False,
        compatible_emotions=["surprised", "neutral", "happy"],
        description="歪头",
    ),
    "emote_shrug": GesturePreset(
        name="emote_shrug",
        category=GestureCategory.EMOTE,
        duration=1.2,
        loop=False,
        compatible_emotions=["neutral", "sad", "relaxed"],
        description="耸肩",
    ),

    # === 反应动作 ===
    "react_surprised": GesturePreset(
        name="react_surprised",
        category=GestureCategory.REACT,
        duration=0.8,
        loop=False,
        compatible_emotions=["surprised"],
        description="惊讶反应",
    ),
    "react_laugh": GesturePreset(
        name="react_laugh",
        category=GestureCategory.REACT,
        duration=1.5,
        loop=False,
        compatible_emotions=["happy"],
        description="大笑",
    ),
    "react_think": GesturePreset(
        name="react_think",
        category=GestureCategory.REACT,
        duration=2.0,
        loop=False,
        compatible_emotions=["neutral", "sad"],
        description="思考",
    ),
    "react_facepalm": GesturePreset(
        name="react_facepalm",
        category=GestureCategory.REACT,
        duration=1.5,
        loop=False,
        compatible_emotions=["sad", "angry"],
        description="捂脸",
    ),

    # === 姿势动作 ===
    "pose_confident": GesturePreset(
        name="pose_confident",
        category=GestureCategory.POSE,
        duration=2.0,
        loop=True,
        compatible_emotions=["happy", "neutral"],
        description="自信姿势",
    ),
    "pose_shy": GesturePreset(
        name="pose_shy",
        category=GestureCategory.POSE,
        duration=1.5,
        loop=True,
        compatible_emotions=["happy", "sad"],
        description="害羞姿势",
    ),
    "pose_angry": GesturePreset(
        name="pose_angry",
        category=GestureCategory.POSE,
        duration=1.5,
        loop=True,
        compatible_emotions=["angry"],
        description="生气姿势",
    ),
}


def get_gesture_by_emotion(emotion: str, category: Optional[GestureCategory] = None) -> Optional[GesturePreset]:
    """
    根据情绪获取匹配的动作预设

    Args:
        emotion: 情绪关键词 (neutral, happy, angry, sad, relaxed, surprised)
        category: 可选的动作分类过滤

    Returns:
        匹配的动作预设，如果没有匹配则返回 None
    """
    compatible_gestures = []
    for preset in GESTURE_PRESETS.values():
        if emotion in preset.compatible_emotions:
            if category is None or preset.category == category:
                compatible_gestures.append(preset)

    if not compatible_gestures:
        return None

    return random.choice(compatible_gestures)


def get_random_idle_gesture() -> GesturePreset:
    """获取随机待机动作"""
    idle_gestures = [
        p for p in GESTURE_PRESETS.values()
        if p.category == GestureCategory.IDLE
    ]
    return random.choice(idle_gestures)


def get_gesture_for_stage(stage: str, emotion: str) -> Optional[GesturePreset]:
    """
    根据叙事阶段和情绪获取推荐动作

    Args:
        stage: 叙事阶段 (Hook, Build-up, Climax, Resolution)
        emotion: 情绪关键词

    Returns:
        推荐的动作预设
    """
    stage_category_map = {
        "Hook": GestureCategory.REACT,
        "Build-up": GestureCategory.TALK,
        "Climax": GestureCategory.EMOTE,
        "Resolution": GestureCategory.IDLE,
    }

    category = stage_category_map.get(stage, GestureCategory.TALK)
    gesture = get_gesture_by_emotion(emotion, category)

    # 如果找不到匹配的，尝试不限分类
    if gesture is None:
        gesture = get_gesture_by_emotion(emotion)

    return gesture
