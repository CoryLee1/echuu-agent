"""
VRM 表情映射器

提供 VRM0/VRM1 格式兼容的表情映射。
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Any

from ..core.performer_cue import EmotionKey


class VRMVersion(str, Enum):
    """VRM 版本"""
    VRM0 = "vrm0"
    VRM1 = "vrm1"


@dataclass
class BlendShapeMapping:
    """BlendShape 映射定义"""
    vrm0_name: str              # VRM0 BlendShape 名称
    vrm1_name: str              # VRM1 Expression 名称
    blendshape_keys: List[str]  # 实际 BlendShape 键名列表
    default_weight: float = 1.0


# VRM 标准表情映射表
VRM_EXPRESSION_MAP: Dict[EmotionKey, BlendShapeMapping] = {
    EmotionKey.NEUTRAL: BlendShapeMapping(
        vrm0_name="Neutral",
        vrm1_name="neutral",
        blendshape_keys=["Neutral", "neutral", "NEUTRAL"],
    ),
    EmotionKey.HAPPY: BlendShapeMapping(
        vrm0_name="Joy",
        vrm1_name="happy",
        blendshape_keys=["Joy", "Happy", "happy", "joy", "Smile", "smile"],
    ),
    EmotionKey.ANGRY: BlendShapeMapping(
        vrm0_name="Angry",
        vrm1_name="angry",
        blendshape_keys=["Angry", "angry", "ANGRY", "Mad", "mad"],
    ),
    EmotionKey.SAD: BlendShapeMapping(
        vrm0_name="Sorrow",
        vrm1_name="sad",
        blendshape_keys=["Sorrow", "Sad", "sad", "sorrow", "Cry", "cry"],
    ),
    EmotionKey.RELAXED: BlendShapeMapping(
        vrm0_name="Fun",
        vrm1_name="relaxed",
        blendshape_keys=["Fun", "Relaxed", "relaxed", "fun", "Calm", "calm"],
    ),
    EmotionKey.SURPRISED: BlendShapeMapping(
        vrm0_name="Surprised",
        vrm1_name="surprised",
        blendshape_keys=["Surprised", "surprised", "SURPRISED", "Shock", "shock"],
    ),
    EmotionKey.FUN: BlendShapeMapping(
        vrm0_name="Fun",
        vrm1_name="relaxed",
        blendshape_keys=["Fun", "fun", "Relaxed"],
    ),
    EmotionKey.SORROW: BlendShapeMapping(
        vrm0_name="Sorrow",
        vrm1_name="sad",
        blendshape_keys=["Sorrow", "sorrow", "Sad"],
    ),
}


# 口型映射（用于 Lipsync）
VRM_VISEME_MAP: Dict[str, BlendShapeMapping] = {
    "aa": BlendShapeMapping(
        vrm0_name="A",
        vrm1_name="aa",
        blendshape_keys=["A", "a", "Fcl_MTH_A", "vrc.v_aa"],
    ),
    "ih": BlendShapeMapping(
        vrm0_name="I",
        vrm1_name="ih",
        blendshape_keys=["I", "i", "Fcl_MTH_I", "vrc.v_ih"],
    ),
    "ou": BlendShapeMapping(
        vrm0_name="U",
        vrm1_name="ou",
        blendshape_keys=["U", "u", "Fcl_MTH_U", "vrc.v_ou"],
    ),
    "ee": BlendShapeMapping(
        vrm0_name="E",
        vrm1_name="ee",
        blendshape_keys=["E", "e", "Fcl_MTH_E", "vrc.v_ee"],
    ),
    "oh": BlendShapeMapping(
        vrm0_name="O",
        vrm1_name="oh",
        blendshape_keys=["O", "o", "Fcl_MTH_O", "vrc.v_oh"],
    ),
}


class VRMExpressionMapper:
    """
    VRM 表情映射器

    负责将 canonical 表情枚举转换为具体 VRM 模型的 BlendShape 名称。
    支持 VRM0 和 VRM1 两种格式。
    """

    def __init__(
        self,
        version: VRMVersion = VRMVersion.VRM1,
        custom_mappings: Optional[Dict[str, str]] = None,
    ):
        """
        初始化映射器

        Args:
            version: VRM 版本
            custom_mappings: 自定义 BlendShape 名称映射
        """
        self.version = version
        self.custom_mappings = custom_mappings or {}
        self._available_expressions: Optional[List[str]] = None

    def set_available_expressions(self, expressions: List[str]) -> None:
        """
        设置模型可用的表情列表（用于自动匹配）

        Args:
            expressions: 模型支持的表情名称列表
        """
        self._available_expressions = expressions

    def map_emotion(self, emotion: EmotionKey, intensity: float = 1.0) -> Dict[str, Any]:
        """
        将情绪枚举映射为 VRM BlendShape 指令

        Args:
            emotion: 情绪枚举
            intensity: 强度 0.0~1.0

        Returns:
            包含 BlendShape 名称和权重的字典
        """
        # 检查自定义映射
        if emotion.value in self.custom_mappings:
            return {
                "blendShape": self.custom_mappings[emotion.value],
                "weight": intensity,
            }

        # 使用标准映射
        mapping = VRM_EXPRESSION_MAP.get(emotion)
        if mapping is None:
            # 降级到 neutral
            mapping = VRM_EXPRESSION_MAP[EmotionKey.NEUTRAL]

        # 根据版本选择名称
        if self.version == VRMVersion.VRM0:
            blend_name = mapping.vrm0_name
        else:
            blend_name = mapping.vrm1_name

        # 如果有可用表情列表，尝试找到匹配的
        if self._available_expressions:
            for key in mapping.blendshape_keys:
                if key in self._available_expressions:
                    blend_name = key
                    break

        return {
            "blendShape": blend_name,
            "weight": intensity * mapping.default_weight,
        }

    def map_viseme(self, viseme: str, intensity: float = 1.0) -> Dict[str, Any]:
        """
        将口型映射为 VRM BlendShape 指令

        Args:
            viseme: 口型标识 (aa, ih, ou, ee, oh)
            intensity: 强度 0.0~1.0

        Returns:
            包含 BlendShape 名称和权重的字典
        """
        mapping = VRM_VISEME_MAP.get(viseme)
        if mapping is None:
            return {"blendShape": "A", "weight": 0.0}

        if self.version == VRMVersion.VRM0:
            blend_name = mapping.vrm0_name
        else:
            blend_name = mapping.vrm1_name

        if self._available_expressions:
            for key in mapping.blendshape_keys:
                if key in self._available_expressions:
                    blend_name = key
                    break

        return {
            "blendShape": blend_name,
            "weight": intensity * mapping.default_weight,
        }

    def get_blink_shapes(self) -> Dict[str, str]:
        """
        获取眨眼 BlendShape 名称

        Returns:
            包含 left 和 right 眨眼形状名称的字典
        """
        if self.version == VRMVersion.VRM0:
            return {
                "left": "Blink_L",
                "right": "Blink_R",
                "both": "Blink",
            }
        else:
            return {
                "left": "blinkLeft",
                "right": "blinkRight",
                "both": "blink",
            }

    def get_lookat_bone(self) -> str:
        """
        获取视线骨骼名称

        Returns:
            视线控制骨骼的名称
        """
        if self.version == VRMVersion.VRM0:
            return "lookAt"
        else:
            return "lookAt"

    def to_vrm_command(
        self,
        emotion: EmotionKey,
        intensity: float = 1.0,
        attack: float = 0.2,
        release: float = 0.3,
    ) -> Dict[str, Any]:
        """
        生成完整的 VRM 表情控制指令

        Args:
            emotion: 情绪枚举
            intensity: 强度
            attack: 淡入时间（秒）
            release: 淡出时间（秒）

        Returns:
            可发送给 VRM 渲染器的完整指令
        """
        blend_info = self.map_emotion(emotion, intensity)

        return {
            "type": "expression",
            "blendShape": blend_info["blendShape"],
            "weight": blend_info["weight"],
            "fadeIn": attack,
            "fadeOut": release,
            "version": self.version.value,
        }

    def create_batch_command(
        self,
        expressions: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        创建批量表情控制指令

        Args:
            expressions: 表情指令列表

        Returns:
            批量控制指令
        """
        return {
            "type": "expression_batch",
            "expressions": expressions,
            "version": self.version.value,
        }
