"""
PerformerCue - 表演标注协议

用于在剧本生成阶段为每行台词打上可执行的表情与动作标注，
供 Unity/three-vrm 等前端消费。

设计原则：
- 使用 canonical 枚举，不依赖具体模型的自定义 blendshape 名字
- 每行最多一个主 emotion + 一个 gesture，避免冲突
- 可序列化为 JSON，保持 ensure_ascii=False
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, List, Dict, Any, Literal, Union
import json


class EmotionKey(str, Enum):
    """Canonical 表情枚举，兼容 VRM0/VRM1"""
    NEUTRAL = "neutral"
    HAPPY = "happy"
    ANGRY = "angry"
    SAD = "sad"
    RELAXED = "relaxed"
    SURPRISED = "surprised"
    # 扩展表情（部分 VRM 可能不支持，会自动降级）
    FUN = "fun"
    SORROW = "sorrow"


class LookTarget(str, Enum):
    """视线目标枚举"""
    CAMERA = "camera"
    CHAT = "chat"
    OFFSCREEN = "offscreen"
    DOWN = "down"
    UP = "up"
    LEFT = "left"
    RIGHT = "right"


class BlinkMode(str, Enum):
    """眨眼模式"""
    AUTO = "auto"      # 自动随机眨眼
    HOLD = "hold"      # 保持当前状态
    NONE = "none"      # 完全不眨眼
    WINK_LEFT = "wink_left"
    WINK_RIGHT = "wink_right"


@dataclass
class EmotionCue:
    """表情标注"""
    key: EmotionKey
    intensity: float = 0.7          # 0.0 ~ 1.0
    attack: float = 0.2             # 淡入时间（秒）
    release: float = 0.3            # 淡出时间（秒）

    def __post_init__(self):
        if isinstance(self.key, str):
            self.key = EmotionKey(self.key)
        self.intensity = max(0.0, min(1.0, self.intensity))
        self.attack = max(0.0, self.attack)
        self.release = max(0.0, self.release)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key.value,
            "intensity": self.intensity,
            "attack": self.attack,
            "release": self.release,
        }


@dataclass
class GestureCue:
    """动作/手势标注"""
    clip: str                       # 动作名称（来自预置库）
    weight: float = 1.0             # 0.0 ~ 1.0
    duration: float = 1.0           # 持续时间（秒）
    loop: bool = False              # 是否循环

    def __post_init__(self):
        self.weight = max(0.0, min(1.0, self.weight))
        self.duration = max(0.0, self.duration)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "clip": self.clip,
            "weight": self.weight,
            "duration": self.duration,
            "loop": self.loop,
        }


@dataclass
class LookCue:
    """视线标注"""
    target: Union[LookTarget, tuple]  # 枚举或 (x, y) 坐标
    strength: float = 0.8             # 0.0 ~ 1.0

    def __post_init__(self):
        if isinstance(self.target, str):
            self.target = LookTarget(self.target)
        self.strength = max(0.0, min(1.0, self.strength))

    def to_dict(self) -> Dict[str, Any]:
        target_value = self.target.value if isinstance(self.target, LookTarget) else list(self.target)
        return {
            "target": target_value,
            "strength": self.strength,
        }


@dataclass
class BlinkCue:
    """眨眼标注"""
    mode: BlinkMode = BlinkMode.AUTO
    extra: float = 0.0                # 额外眨眼频率调整

    def __post_init__(self):
        if isinstance(self.mode, str):
            self.mode = BlinkMode(self.mode)
        self.extra = max(0.0, min(1.0, self.extra))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "extra": self.extra,
        }


@dataclass
class LipsyncCue:
    """口型标注 - 预留字段，实际由音频驱动"""
    enabled: bool = True
    # 以下字段由实时音频分析填充
    aa: float = 0.0
    ih: float = 0.0
    ou: float = 0.0
    ee: float = 0.0
    oh: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "enabled": self.enabled,
            "aa": self.aa,
            "ih": self.ih,
            "ou": self.ou,
            "ee": self.ee,
            "oh": self.oh,
        }


@dataclass
class CameraCue:
    """镜头标注 - 可选"""
    preset: Optional[str] = None     # 镜头预设名
    zoom: Optional[float] = None     # 缩放比例

    def to_dict(self) -> Dict[str, Any]:
        return {
            "preset": self.preset,
            "zoom": self.zoom,
        }


@dataclass
class PerformerCue:
    """
    完整的表演标注协议

    包含：表情、手势、视线、眨眼、口型（预留）、镜头（可选）
    """
    emotion: Optional[EmotionCue] = None
    gesture: Optional[GestureCue] = None
    look: Optional[LookCue] = None
    blink: Optional[BlinkCue] = None
    lipsync: Optional[LipsyncCue] = None
    camera: Optional[CameraCue] = None
    # 节拍/暂停提示
    beat: Optional[float] = None     # 节拍点（秒）
    pause: Optional[float] = None    # 暂停时长（秒）

    def to_dict(self) -> Dict[str, Any]:
        """转换为可序列化的字典"""
        result = {}
        if self.emotion:
            result["emotion"] = self.emotion.to_dict()
        if self.gesture:
            result["gesture"] = self.gesture.to_dict()
        if self.look:
            result["look"] = self.look.to_dict()
        if self.blink:
            result["blink"] = self.blink.to_dict()
        if self.lipsync:
            result["lipsync"] = self.lipsync.to_dict()
        if self.camera:
            result["camera"] = self.camera.to_dict()
        if self.beat is not None:
            result["beat"] = self.beat
        if self.pause is not None:
            result["pause"] = self.pause
        return result

    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PerformerCue":
        """从字典创建 PerformerCue"""
        cue = cls()
        if "emotion" in data and data["emotion"]:
            cue.emotion = EmotionCue(**data["emotion"])
        if "gesture" in data and data["gesture"]:
            cue.gesture = GestureCue(**data["gesture"])
        if "look" in data and data["look"]:
            cue.look = LookCue(**data["look"])
        if "blink" in data and data["blink"]:
            cue.blink = BlinkCue(**data["blink"])
        if "lipsync" in data and data["lipsync"]:
            cue.lipsync = LipsyncCue(**data["lipsync"])
        if "camera" in data and data["camera"]:
            cue.camera = CameraCue(**data["camera"])
        cue.beat = data.get("beat")
        cue.pause = data.get("pause")
        return cue

    @classmethod
    def neutral(cls) -> "PerformerCue":
        """创建中性表情的默认 Cue"""
        return cls(
            emotion=EmotionCue(key=EmotionKey.NEUTRAL, intensity=0.5),
            look=LookCue(target=LookTarget.CAMERA),
            blink=BlinkCue(mode=BlinkMode.AUTO),
            lipsync=LipsyncCue(enabled=True),
        )


# 情绪关键词到 EmotionKey 的映射
EMOTION_KEYWORD_MAP: Dict[str, EmotionKey] = {
    # 中文关键词
    "开心": EmotionKey.HAPPY,
    "高兴": EmotionKey.HAPPY,
    "快乐": EmotionKey.HAPPY,
    "兴奋": EmotionKey.HAPPY,
    "愤怒": EmotionKey.ANGRY,
    "生气": EmotionKey.ANGRY,
    "恼火": EmotionKey.ANGRY,
    "悲伤": EmotionKey.SAD,
    "难过": EmotionKey.SAD,
    "伤心": EmotionKey.SAD,
    "委屈": EmotionKey.SAD,
    "放松": EmotionKey.RELAXED,
    "轻松": EmotionKey.RELAXED,
    "平静": EmotionKey.NEUTRAL,
    "惊讶": EmotionKey.SURPRISED,
    "震惊": EmotionKey.SURPRISED,
    "吃惊": EmotionKey.SURPRISED,
    "尴尬": EmotionKey.SURPRISED,
    "害羞": EmotionKey.HAPPY,
    "得意": EmotionKey.HAPPY,
    "无奈": EmotionKey.SAD,
    "焦虑": EmotionKey.SAD,
    # 英文关键词
    "happy": EmotionKey.HAPPY,
    "joy": EmotionKey.HAPPY,
    "excited": EmotionKey.HAPPY,
    "angry": EmotionKey.ANGRY,
    "mad": EmotionKey.ANGRY,
    "sad": EmotionKey.SAD,
    "upset": EmotionKey.SAD,
    "relaxed": EmotionKey.RELAXED,
    "calm": EmotionKey.NEUTRAL,
    "surprised": EmotionKey.SURPRISED,
    "shocked": EmotionKey.SURPRISED,
}


def infer_emotion_from_text(text: str, stage: str = "Build-up") -> EmotionCue:
    """
    从文本内容推断表情

    Args:
        text: 台词文本
        stage: 叙事阶段

    Returns:
        推断出的 EmotionCue
    """
    # 基于关键词检测
    detected_key = EmotionKey.NEUTRAL
    for keyword, emotion_key in EMOTION_KEYWORD_MAP.items():
        if keyword in text:
            detected_key = emotion_key
            break

    # 基于标点符号调整强度
    intensity = 0.6
    if "！" in text or "!" in text:
        intensity = 0.85
    if "..." in text or "…" in text:
        intensity = 0.5
    if "？" in text or "?" in text:
        intensity = 0.7

    # 基于阶段调整
    stage_intensity_mod = {
        "Hook": 0.0,
        "Build-up": 0.1,
        "Climax": 0.3,
        "Resolution": -0.1,
    }
    intensity += stage_intensity_mod.get(stage, 0.0)
    intensity = max(0.3, min(1.0, intensity))

    return EmotionCue(
        key=detected_key,
        intensity=intensity,
        attack=0.15,
        release=0.25,
    )
