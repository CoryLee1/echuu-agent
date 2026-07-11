"""演唱做旧 — 把"好版本"人声受控地变差。

核心思路（见三模式方案 §5.2）：不让模型自然失败（不可控），
而是先拿到好版本，再用信号处理做出"跑调"效果，失败度是参数。

quality 档位：
  good: 原样（或仅微瑕疵：尾音轻微飘）
  mid:  轻度音准漂移，听感"还行但不稳"
  bad:  重度漂移 + 局部走音 + 尾音崩，听感"认真在唱但唱不好"

实现约束：漂移必须是缓变曲线（真人跑调是连续的），绝不能逐帧随机
（那是"机器坏了"的听感）。
"""
from __future__ import annotations

import io
from typing import Literal

import numpy as np

Quality = Literal["good", "mid", "bad"]

# 每档的漂移参数：(最大漂移 cents, 漂移段数/10s, 尾音崩概率)
_PROFILES = {
    "good": (12, 1, 0.0),
    "mid": (35, 2, 0.2),
    "bad": (80, 4, 0.9),
}


def _drift_curve(n_samples: int, sr: int, max_cents: float, segments_per_10s: int,
                 rng: np.random.Generator) -> np.ndarray:
    """生成缓变音准漂移曲线（cents），用平滑随机折线插值。"""
    duration = n_samples / sr
    n_knots = max(3, int(duration / 10 * segments_per_10s) + 2)
    knot_t = np.linspace(0, n_samples, n_knots)
    # 漂移偏向单方向（真人跑调通常整体偏低或偏高），叠加局部波动
    bias = rng.uniform(-0.5, 0.5) * max_cents
    knots = bias + rng.uniform(-max_cents, max_cents, n_knots) * 0.6
    knots[0] *= 0.3  # 起音相对准
    return np.interp(np.arange(n_samples), knot_t, knots)


def degrade_vocal(wav_bytes: bytes, quality: Quality, seed: int = 0) -> bytes:
    """输入 WAV 字节，输出做旧后的 WAV 字节。good 档基本原样返回。"""
    import librosa
    import soundfile as sf

    if quality == "good" and seed % 3 != 0:
        return wav_bytes  # 大多数 good 保持原样，少数带微瑕疵

    y, sr = librosa.load(io.BytesIO(wav_bytes), sr=None, mono=True)
    if len(y) < sr // 4:
        return wav_bytes

    max_cents, seg_rate, tail_break_p = _PROFILES[quality]
    rng = np.random.default_rng(seed or None)

    # 1) 缓变音准漂移：分块 pitch shift（块间线性过渡由曲线平滑保证）
    curve = _drift_curve(len(y), sr, max_cents, seg_rate, rng)
    block = sr // 2  # 0.5s 块
    out = np.copy(y)
    for start in range(0, len(y), block):
        end = min(start + block, len(y))
        cents = float(np.mean(curve[start:end]))
        if abs(cents) > 5:
            out[start:end] = librosa.effects.pitch_shift(
                y[start:end], sr=sr, n_steps=cents / 100.0,
            )

    # 2) bad 档：随机挑 1-2 处整句走音（突然偏离半音级别再回来）
    if quality == "bad":
        for _ in range(rng.integers(1, 3)):
            pos = rng.integers(0, max(1, len(out) - sr))
            span = min(int(sr * rng.uniform(0.6, 1.5)), len(out) - pos)
            n_steps = float(rng.choice([-1.2, -0.8, 0.9, 1.3]))
            out[pos:pos + span] = librosa.effects.pitch_shift(
                out[pos:pos + span], sr=sr, n_steps=n_steps,
            )

    # 3) 尾音崩：末尾 0.4-0.8s 音量收不干净 + 音高下坠
    if rng.random() < tail_break_p:
        tail = int(sr * rng.uniform(0.4, 0.8))
        if tail < len(out):
            seg = out[-tail:]
            seg = librosa.effects.pitch_shift(seg, sr=sr, n_steps=-0.7)
            fade = np.linspace(1.0, 0.35, tail)
            out[-tail:] = seg * fade

    buf = io.BytesIO()
    sf.write(buf, out, sr, format="WAV", subtype="PCM_16")
    return buf.getvalue()
