"""
ExampleSampler - Few-shot 随机采样器。
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Dict, List


class ExampleSampler:
    """
    从真实 VTuber 片段中随机采样 few-shot examples。
    """

    def __init__(self, clips_path: str):
        self.clips: List[Dict] = []
        clips_file = Path(clips_path)

        if clips_file.exists():
            with clips_file.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        self.clips.append(json.loads(line))
            print(f"ExampleSampler: 加载了 {len(self.clips)} 个 clips")
        else:
            print(f"clips 文件不存在: {clips_path}")

        self.categorize_clips()

    def categorize_clips(self):
        """将 clips 按特征分类。"""
        self.by_emotion = {
            "high_emotion": [],
            "casual": [],
            "storytelling": [],
        }

        self.by_structure = {
            "linear": [],
            "digressive": [],
            "interactive": [],
        }

        zh_high_emotion = ["爆发", "紧张", "释然", "感动", "破防", "愤怒", "震惊", "激动"]
        zh_casual = ["轻松", "调侃", "自嘲", "搞笑", "宠溺"]

        en_high_emotion = ["angry", "rage", "crying", "emotional", "sad", "vulnerable", "break"]
        en_casual = ["funny", "chill", "relax", "joking", "sarcastic"]

        for clip in self.clips:
            notes = clip.get("notes", {})
            lang = clip.get("language", "zh")

            emotion = notes.get("emotion", "").lower()
            feature = notes.get("feature", "").lower()

            high_markers = zh_high_emotion if lang == "zh" else en_high_emotion
            casual_markers = zh_casual if lang == "zh" else en_casual

            is_high = any(word in emotion or word in feature for word in high_markers)
            is_casual = any(word in emotion or word in feature for word in casual_markers)

            if "**" in feature:
                is_high = True

            if is_high:
                self.by_emotion["high_emotion"].append(clip)
            elif is_casual:
                self.by_emotion["casual"].append(clip)
            else:
                self.by_emotion["storytelling"].append(clip)

            structure = notes.get("structure", "")
            if "跑题" in structure or "插入" in structure or "digress" in structure.lower():
                self.by_structure["digressive"].append(clip)
            elif "互动" in structure or "弹幕" in structure or "interactive" in structure.lower():
                self.by_structure["interactive"].append(clip)
            else:
                self.by_structure["linear"].append(clip)

        print(
            "   情绪分类: 高情绪={}, 日常={}, 叙事={}".format(
                len(self.by_emotion["high_emotion"]),
                len(self.by_emotion["casual"]),
                len(self.by_emotion["storytelling"]),
            )
        )
        print(
            "   结构分类: 跑题={}, 互动={}, 线性={}".format(
                len(self.by_structure["digressive"]),
                len(self.by_structure["interactive"]),
                len(self.by_structure["linear"]),
            )
        )

    def sample_diverse(self, n: int = 3, language: str = None) -> List[Dict]:
        """采样 n 个多样化的 examples。"""
        if language:
            available = [c for c in self.clips if c.get("language") == language]
            high_emotion = [
                c for c in self.by_emotion["high_emotion"] if c.get("language") == language
            ]
            digressive = [
                c for c in self.by_structure["digressive"] if c.get("language") == language
            ]
        else:
            available = self.clips
            high_emotion = self.by_emotion["high_emotion"]
            digressive = self.by_structure["digressive"]

        if not available:
            print(f"没有可用的 clips (language={language})")
            return []

        samples: List[Dict] = []

        if high_emotion:
            samples.append(random.choice(high_emotion))

        digressive_available = [c for c in digressive if c not in samples]
        if digressive_available:
            samples.append(random.choice(digressive_available))

        remaining = [c for c in available if c not in samples]
        while len(samples) < n and remaining:
            choice = random.choice(remaining)
            samples.append(choice)
            remaining.remove(choice)

        random.shuffle(samples)
        return samples

    def extract_transcript_segments(self, clip: Dict, max_segments: int = 3) -> str:
        """从一个 clip 中提取有代表性的 transcript 片段。"""
        transcript = clip.get("transcript", [])
        if not transcript:
            return ""

        lang = clip.get("language", "zh")

        zh_self_correct = ["不对", "还是", "来着", "我的意思是", "不是那个", "应该是", "好像是"]
        zh_emotion = ["救命", "天哪", "我的天", "哎呀", "卧槽", "太", "真的", "可怕"]
        zh_digress = ["对了", "说起这个", "诶", "话说", "等等", "不是"]

        en_self_correct = ["wait", "no", "actually", "i mean", "not that", "well"]
        en_emotion = ["oh my god", "holy", "what the", "damn", "crazy", "insane"]
        en_digress = ["anyway", "by the way", "speaking of", "oh", "wait"]

        self_correct = zh_self_correct if lang == "zh" else en_self_correct
        emotion_words = zh_emotion if lang == "zh" else en_emotion
        digress_words = zh_digress if lang == "zh" else en_digress

        scored_segments = []
        for seg in transcript:
            text = seg.get("text", "").lower()
            score = 0

            if any(marker.lower() in text for marker in self_correct):
                score += 3
            if any(marker.lower() in text for marker in emotion_words):
                score += 2
            if any(marker.lower() in text for marker in digress_words):
                score += 2

            if lang == "zh" and "，" in seg.get("text", ""):
                parts = seg.get("text", "").split("，")
                for i in range(len(parts) - 1):
                    if len(parts[i]) >= 2 and len(parts[i + 1]) >= 2:
                        if parts[i][-2:] == parts[i + 1][:2]:
                            score += 1

            text_len = len(seg.get("text", ""))
            if 50 < text_len < 300:
                score += 1

            scored_segments.append((score, seg))

        scored_segments.sort(key=lambda x: x[0], reverse=True)
        selected = scored_segments[:max_segments]

        selected.sort(key=lambda x: x[1].get("t", 0) or 0)

        result = []
        for _, seg in selected:
            result.append(seg.get("text", ""))

        return "\n".join(result)

    def format_as_fewshot(self, clips: List[Dict]) -> str:
        """将采样的 clips 格式化为 few-shot prompt。"""
        output = []

        for i, clip in enumerate(clips, 1):
            title = clip.get("title", "未知")
            notes = clip.get("notes", {})
            lang = clip.get("language", "zh")

            features = []
            if notes.get("habit"):
                features.append(f"口癖: {notes['habit']}")
            if notes.get("emotion"):
                features.append(f"情绪: {notes['emotion']}")
            if notes.get("feature"):
                feat = notes["feature"].replace("**", "")
                features.append(f"特点: {feat}")

            segments = self.extract_transcript_segments(clip)
            lang_label = "中文" if lang == "zh" else "英文"

            output.append(
                f"""
### 真实案例 {i}: {title} ({lang_label})
{' | '.join(features)}

**原文片段（注意口语特征）：**
```
{segments}
```
"""
            )

        return "\n".join(output)

    def get_random_examples(self, n: int = 3, language: str = "zh") -> str:
        """一键获取格式化的 few-shot examples。"""
        samples = self.sample_diverse(n=n, language=language)
        if not samples:
            return "（无可用的 few-shot examples）"
        return self.format_as_fewshot(samples)
