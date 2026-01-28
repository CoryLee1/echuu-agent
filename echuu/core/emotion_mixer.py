"""
情绪混合器 - 真实情绪不是单一的

功能：
1. 情绪复合：主情绪 + 副情绪
2. 情绪包装：用情绪A表达情绪B
3. 情绪轨迹：情绪的变化路径
"""

import random
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class EmotionConfig:
    primary: str
    secondary: Optional[str] = None
    mask: Optional[str] = None  # 用什么情绪包装
    trajectory: List[str] = None  # 情绪变化轨迹
    markers: Dict[str, List[str]] = None  # 各情绪的语言标记


class EmotionMixer:

    COMPOUNDS = {
        "angry": ["self_deprecating", "affectionate", "helpless", "amused"],
        "sad": ["accepting", "self_mocking", "grateful", "peaceful"],
        "happy": ["embarrassed", "nostalgic", "proud", "anxious"],
        "anxious": ["self_deprecating", "hopeful", "resigned", "excited"],
        "touched": ["embarrassed", "guilty", "overwhelmed", "awkward"],
        "embarrassed": ["amused", "defensive", "self_mocking"],
        "nostalgic": ["bittersweet", "grateful", "melancholic", "warm"],
    }

    MASKS = {
        "vulnerability_as_anger": {
            "surface": "angry",
            "underlying": "vulnerable",
            "markers_zh": {
                "surface": ["闭嘴", "你们懂什么", "别说了", "烦死了"],
                "crack": ["...算了", "反正...", "我只是..."],
            },
            "markers_en": {
                "surface": ["shut up", "you don't understand", "whatever"],
                "crack": ["...anyway", "I just...", "it's fine"],
            },
        },
        "gratitude_as_complaint": {
            "surface": "complaining",
            "underlying": "grateful",
            "markers_zh": {
                "surface": ["烦死了", "又来了", "你们够了", "每次都这样"],
                "crack": ["...谢谢啊", "你们真的...", "我..."],
            },
            "markers_en": {
                "surface": ["ugh", "here we go again", "you guys"],
                "crack": ["...thanks though", "you guys really...", "I..."],
            },
        },
        "anxiety_as_humor": {
            "surface": "joking",
            "underlying": "anxious",
            "markers_zh": {
                "surface": ["哈哈哈", "笑死", "太好笑了", "绝了"],
                "crack": ["...其实", "不是，真的", "我当时真的..."],
            },
            "markers_en": {
                "surface": ["lmao", "that's hilarious", "I'm dead"],
                "crack": ["...actually though", "no but really", "I was actually..."],
            },
        },
        "love_as_annoyance": {
            "surface": "annoyed",
            "underlying": "affectionate",
            "markers_zh": {
                "surface": ["臭{target}", "你怎么这样", "烦人"],
                "crack": ["...好吧", "行行行", "随你"],
            },
            "markers_en": {
                "surface": ["stupid {target}", "why are you like this", "so annoying"],
                "crack": ["...fine", "okay okay", "whatever you want"],
            },
        },
    }

    TRAJECTORIES = [
        ["light", "serious", "self_deprecating"],
        ["calm", "escalating", "peak", "deflate"],
        ["vulnerable", "rational", "hopeful"],
        ["joking", "accidentally_serious", "retreat"],
        ["nostalgic", "bittersweet", "accepting"],
        ["excited", "tangent", "confused", "back"],
    ]

    EMOTION_MARKERS = {
        "zh": {
            "angry": ["靠", "气死了", "什么玩意", "闭嘴"],
            "sad": ["唉", "好难过", "心累", "算了"],
            "happy": ["哈哈哈", "太好了", "开心", "耶"],
            "anxious": ["完了", "怎么办", "慌了", "救命"],
            "touched": ["呜呜", "好感动", "我的天", "太好了"],
            "embarrassed": ["啊这", "尴尬", "社死", "不说了"],
            "nostalgic": ["那时候", "想起来", "以前", "好久了"],
            "self_deprecating": ["我真是", "太蠢了", "笑死我自己", "傻逼"],
        },
        "en": {
            "angry": ["what the", "ugh", "I swear", "shut up"],
            "sad": ["man", "sigh", "it sucks", "whatever"],
            "happy": ["yay", "nice", "let's go", "awesome"],
            "anxious": ["oh no", "what do I do", "I'm scared", "help"],
            "touched": ["aww", "I'm gonna cry", "that's so sweet"],
            "embarrassed": ["oh god", "kill me", "I can't", "anyway"],
            "nostalgic": ["back then", "I remember", "those days"],
            "self_deprecating": ["I'm such an idiot", "why am I like this", "classic me"],
        },
    }

    def mix(self, primary: str, context: dict = None, language: str = "zh") -> EmotionConfig:
        """
        生成复合情绪配置

        Args:
            primary: 主要情绪
            context: 上下文（可能影响情绪混合）
            language: 语言

        Returns:
            EmotionConfig
        """
        config = EmotionConfig(primary=primary)

        if primary in self.COMPOUNDS and random.random() < 0.5:
            config.secondary = random.choice(self.COMPOUNDS[primary])

        for mask_name, mask_config in self.MASKS.items():
            if mask_config["underlying"] == primary and random.random() < 0.3:
                config.mask = mask_name
                config.primary = mask_config["surface"]
                break

        if random.random() < 0.4:
            config.trajectory = random.choice(self.TRAJECTORIES)

        markers = {}
        markers_dict = self.EMOTION_MARKERS.get(language, self.EMOTION_MARKERS["zh"])

        if config.primary in markers_dict:
            markers[config.primary] = markers_dict[config.primary]
        if config.secondary and config.secondary in markers_dict:
            markers[config.secondary] = markers_dict[config.secondary]

        config.markers = markers

        return config

    def get_markers_for_stage(self, config: EmotionConfig, stage: str, language: str = "zh") -> List[str]:
        """
        根据当前阶段获取合适的情绪标记

        Args:
            config: 情绪配置
            stage: 当前阶段 (Hook/Build-up/Climax/Resolution)
            language: 语言

        Returns:
            可用的情绪标记列表
        """
        markers = []

        if config.mask and stage in ["Climax", "Resolution"]:
            mask_config = self.MASKS.get(config.mask)
            if mask_config:
                marker_key = f"markers_{language}"
                if marker_key in mask_config:
                    if random.random() < 0.7:
                        markers.extend(mask_config[marker_key]["surface"])
                    else:
                        markers.extend(mask_config[marker_key]["crack"])

        if config.markers and config.primary in config.markers:
            markers.extend(config.markers[config.primary])

        if config.secondary and config.markers and config.secondary in config.markers:
            if random.random() < 0.3:
                markers.extend(config.markers[config.secondary])

        return markers
