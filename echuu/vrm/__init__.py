"""
VRM 表情与动作映射模块

提供 VRM0/VRM1 兼容的表情映射和动作预设库。
"""

from .presets import (
    GESTURE_PRESETS,
    GestureCategory,
    get_gesture_by_emotion,
    get_random_idle_gesture,
)
from .mapper import (
    VRMExpressionMapper,
    VRMVersion,
)

__all__ = [
    # Presets
    "GESTURE_PRESETS",
    "GestureCategory",
    "get_gesture_by_emotion",
    "get_random_idle_gesture",
    # Mapper
    "VRMExpressionMapper",
    "VRMVersion",
]
