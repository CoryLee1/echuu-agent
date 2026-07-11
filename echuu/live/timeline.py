"""Timeline 落盘 — 三模式共享的事件流记录器。

一场 session 的产物 = timeline.json + 音频资产，前端可确定性重放。
事件形状 = WS 广播的 step 事件（去掉原始音频字节，保留 audio_url）
再补上回放所需的时间轴字段（t / duration / mode / event）。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Optional


def estimate_wav_duration(audio_bytes: Optional[bytes], sample_rate: int = 24000) -> float:
    """按 16bit mono PCM WAV 估算时长（秒）。非 WAV/空数据返回 0。"""
    if not audio_bytes:
        return 0.0
    data_len = len(audio_bytes) - 44 if audio_bytes[:4] == b"RIFF" else len(audio_bytes)
    return max(0.0, data_len / (sample_rate * 2))


class TimelineWriter:
    """把 step 事件追加进 session 目录的 timeline.json（每次 append 全量落盘）。"""

    # talk 事件之间的自然停顿（秒），与前端播放节奏对齐
    DEFAULT_GAP = 0.6

    def __init__(self, session_dir: Path, mode: str, meta: Optional[dict] = None):
        self.path = Path(session_dir) / "timeline.json"
        self.mode = mode
        self.meta = meta or {}
        self.events: list[dict] = []
        self.cursor = 0.0  # 顺序播报模式下的时间游标

    def append(self, event: dict, duration: float = 0.0, t: Optional[float] = None) -> dict:
        """追加事件并落盘。

        Args:
            event: WS step 事件（不含原始音频字节）。
            duration: 该事件音频时长（秒）。
            t: 显式时间锚点（reaction 的 video_t 对齐等）；None 时用顺序游标。
        """
        ev = dict(event)
        ev.pop("audio", None)  # 保险：原始字节永不落盘
        ev.setdefault("mode", self.mode)
        ev.setdefault("event", "talk")
        if t is None:
            t = self.cursor
            self.cursor = t + duration + self.DEFAULT_GAP
        else:
            self.cursor = max(self.cursor, t + duration + self.DEFAULT_GAP)
        ev["t"] = round(t, 3)
        ev["duration"] = round(duration, 3)
        self.events.append(ev)
        self._flush()
        return ev

    def _flush(self) -> None:
        payload = {
            "version": 1,
            "mode": self.mode,
            "meta": self.meta,
            "total_duration": round(self.cursor, 3),
            "events": self.events,
        }
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
