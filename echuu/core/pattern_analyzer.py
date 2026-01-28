"""
PatternAnalyzer - 从标注数据中提取叙事/弹幕相关模式。
"""

from __future__ import annotations

from collections import Counter, defaultdict
from typing import Dict, List, Tuple


class PatternAnalyzer:
    """从标注数据中提取模式。"""

    def __init__(self, annotated_clips: List[dict]):
        self.clips = annotated_clips
        self.all_segments = []
        for clip in annotated_clips:
            self.all_segments.extend(clip.get("segments", []))

    def _normalize_field(self, value, default: str = "self") -> str:
        """处理字段值，如果是列表则取第一个元素。"""
        if isinstance(value, list):
            return value[0] if value else default
        return value if value else default

    def compute_attention_transitions(self) -> Dict[str, Dict[str, float]]:
        """计算 attention 转移概率。"""
        trans = defaultdict(lambda: defaultdict(int))
        for clip in self.clips:
            segs = clip.get("segments", [])
            for i in range(len(segs) - 1):
                frm = self._normalize_field(segs[i].get("attention_focus"), "self")
                to = self._normalize_field(segs[i + 1].get("attention_focus"), "self")
                trans[frm][to] += 1

        prob = {}
        for frm, tos in trans.items():
            total = sum(tos.values())
            prob[frm] = {to: c / total for to, c in tos.items()}
        return prob

    def infer_baseline_costs(self) -> Dict[str, float]:
        """推断不同 attention 下的打断代价。"""
        focus_stats = defaultdict(lambda: {"total": 0, "ignored": 0})

        for seg in self.all_segments:
            focus = self._normalize_field(seg.get("attention_focus"), "self")
            trigger = self._normalize_field(seg.get("trigger"), "self")
            act = self._normalize_field(seg.get("speech_act"), "narrate")

            if trigger == "danmaku":
                focus_stats[focus]["total"] += 1
                if act != "respond":
                    focus_stats[focus]["ignored"] += 1

        costs = {}
        for focus, stats in focus_stats.items():
            if stats["total"] > 0:
                costs[focus] = stats["ignored"] / stats["total"]
            else:
                costs[focus] = 0.5
        return costs

    def extract_skeletons(self) -> List[Tuple[str, int]]:
        """提取叙事骨架。"""
        skeletons = [c.get("skeleton", "") for c in self.clips if c.get("skeleton")]
        return Counter(skeletons).most_common(10)

    def extract_catchphrases(self, language: str = None) -> List[Tuple[str, int]]:
        """提取口癖。"""
        cps = []
        for clip in self.clips:
            if language and clip.get("language") != language:
                continue
            cps.extend(clip.get("catchphrases", []))
        return Counter(cps).most_common(20)

    def extract_hooks(self, language: str = None) -> List[str]:
        """提取开场示例。"""
        hooks = []
        for clip in self.clips:
            if language and clip.get("language") != language:
                continue
            segs = clip.get("segments", [])
            if segs:
                hooks.append(segs[0].get("text", "")[:100])
        return hooks[:10]

    def extract_punchlines(self, language: str = None) -> List[str]:
        """提取收尾示例。"""
        punches = []
        for clip in self.clips:
            if language and clip.get("language") != language:
                continue
            segs = clip.get("segments", [])
            if segs:
                punches.append(segs[-1].get("text", "")[:100])
        return punches[:10]

    def get_report(self) -> str:
        """输出简要分析报告。"""
        lines = [
            "=" * 50,
            "Pattern Analysis Report",
            "=" * 50,
            f"Total clips: {len(self.clips)}, Total segments: {len(self.all_segments)}",
        ]

        lines.append("\n--- Attention Transitions ---")
        for frm, tos in self.compute_attention_transitions().items():
            top = sorted(tos.items(), key=lambda x: -x[1])[:3]
            lines.append(f"  {frm} -> " + ", ".join(f"{t}:{p:.0%}" for t, p in top))

        lines.append("\n--- Inferred Interruption Costs ---")
        for focus, cost in self.infer_baseline_costs().items():
            lines.append(f"  {focus}: {cost:.2f}")

        lines.append("\n--- Top Catchphrases ---")
        cps = self.extract_catchphrases()[:10]
        lines.append("  " + ", ".join(f"\"{c}\"({n})" for c, n in cps))

        return "\n".join(lines)
