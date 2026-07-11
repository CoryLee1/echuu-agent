"""规则化喘气停顿：舞台指示剥离、呼吸组切分、PCM 静音拼接。"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from echuu.live.breath import (
    strip_stage_directions,
    split_breath_groups,
    chunk_text,
    pause_ms_after,
    wrap_pcm_as_wav,
    stitch_wavs_with_pauses,
    synthesize_with_breath,
)


def test_chunk_text_short_passthrough():
    assert chunk_text("短句而已。") == ["短句而已。"]


def test_chunk_text_splits_long_line_losslessly():
    text = "就刚才，我在游戏里送走了一只猫。它死的时候，我正握着现实里另一只猫主人的手机壳！屏幕上还是那只猫生前最后一条视频…你们说巧不巧？"
    chunks = chunk_text(text, max_chars=42)
    assert len(chunks) >= 2
    assert "".join(chunks) == text
    assert all(len(c) <= 42 + 8 for c in chunks)  # 单呼吸组略超限时允许（不硬拆句中）


def test_strip_stage_directions():
    assert strip_stage_directions("喵…（轻轻抖耳朵）这个信号") == "喵…这个信号"
    assert strip_stage_directions("你好(挥手)呀") == "你好呀"
    # 只剥离括号段，不动正文
    assert strip_stage_directions("没有括号") == "没有括号"


def test_split_breath_groups_at_major_punctuation():
    text = "哎哟——刚刷到弹幕了？其实呢，不是害羞。它在等你…但不是等你喂！"
    groups = split_breath_groups(text)
    assert len(groups) >= 3
    assert "".join(groups) == text  # 无损：拼回原文
    for g in groups[:-1]:
        assert g[-1] in "。！？…—；"


def test_split_merges_tiny_segments():
    # "好。" 只有 2 字，应并入相邻组而不是独立成组
    groups = split_breath_groups("好。那我们今天聊聊这个话题吧。")
    assert all(len(g) >= 4 for g in groups)


def test_split_short_text_is_single_group():
    assert split_breath_groups("短句而已") == ["短句而已"]


def test_pause_rules():
    assert pause_ms_after("想想看…", jitter=0) > pause_ms_after("好的。", jitter=0)
    assert pause_ms_after("好的。", jitter=0) >= 200


def _fake_wav(n_samples: int) -> bytes:
    return wrap_pcm_as_wav(b"\x01\x00" * n_samples, sample_rate=24000)


def test_stitch_inserts_silence():
    a, b = _fake_wav(2400), _fake_wav(2400)  # 各 0.1s
    out = stitch_wavs_with_pauses([a, b], [300], sample_rate=24000)
    assert out[:4] == b"RIFF"
    pcm_len = len(out) - 44
    silence_samples = int(24000 * 0.3)
    assert pcm_len == (2400 + 2400 + silence_samples) * 2
    # RIFF data 段长度字段与实际一致
    assert struct.unpack("<I", out[40:44])[0] == pcm_len


def test_synthesize_with_breath_multi_segment():
    calls = []

    def fake_synth(text):
        calls.append(text)
        return _fake_wav(1200)

    out = synthesize_with_breath(fake_synth, "第一句话说完了。然后是第二句话哦！", rng_jitter=0)
    assert len(calls) == 2
    assert out[:4] == b"RIFF"
    # 总 PCM > 两段之和（有静音插入）
    assert len(out) - 44 > 2 * 1200 * 2


def test_synthesize_with_breath_strips_stage_directions():
    calls = []

    def fake_synth(text):
        calls.append(text)
        return _fake_wav(1200)

    synthesize_with_breath(fake_synth, "喵（抖耳朵）今天聊聊这个吧。", rng_jitter=0)
    assert all("抖耳朵" not in c for c in calls)


def test_synthesize_with_breath_segment_failure_degrades():
    def flaky(text):
        return None if "坏" in text else _fake_wav(1200)

    out = synthesize_with_breath(flaky, "这一段是坏的。这一段是好的呢！", rng_jitter=0)
    assert out is not None  # 跳过失败段，剩余仍拼出音频
    assert out[:4] == b"RIFF"


def test_synthesize_with_breath_all_failed_returns_none():
    assert synthesize_with_breath(lambda t: None, "随便说点什么吧。再来一句呢！") is None
