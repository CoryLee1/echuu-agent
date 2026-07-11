"""预生成礼物受击语音库 — 每个面板音色一套短叫声，前端命中时零延迟播放。

输出: echuu-ux-r3f-vite/public/assets/gift-voices/{voice}/{flavor}_{i}.wav
运行: 注入 .env 后 python scripts/build_gift_voice_bank.py [--voices Cherry,Chelsie]
已存在的文件跳过（增量生成）。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# 与前端 src/data/qwenVoices.ts 的 16 音色对齐
PANEL_VOICES = [
    "Cherry", "Serena", "Chelsie", "Momo", "Vivian", "Bella", "Bunny", "Nini",
    "Stella", "Mia", "Katerina", "Sunny", "Kiki", "Ethan", "Ryan", "Moon",
]

# flavor 与前端 expressionDictionary 的爆发脸对齐；instruction 仅 instruct 模型生效
PHRASES: dict[str, tuple[str, list[str]]] = {
    "pain": ("被东西砸到，痛得短促大叫", ["啊！", "哎哟！", "痛痛痛！", "呜哇！", "干嘛砸我呀！"]),
    "yum": ("收到好吃的，惊喜开心", ["哇！", "好耶！", "是吃的！", "谢谢投喂～"]),
    "startled": ("被吓一跳，疑惑惊讶", ["诶？", "咦？", "给我的吗？"]),
}

OUT_ROOT = Path(__file__).resolve().parents[2] / "echuu-ux-r3f-vite" / "public" / "assets" / "gift-voices"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voices", default=",".join(PANEL_VOICES))
    args = parser.parse_args()
    voices = [v.strip() for v in args.voices.split(",") if v.strip()]

    total = skipped = failed = 0
    for voice in voices:
        os.environ["TTS_VOICE"] = voice
        from echuu.live.tts_client import TTSClient  # noqa: PLC0415 — 每音色重建 client

        client = TTSClient()
        if not client.enabled:
            print(f"[bank] TTS 不可用，中止（检查 DASHSCOPE_API_KEY）")
            return
        out_dir = OUT_ROOT / voice
        out_dir.mkdir(parents=True, exist_ok=True)
        for flavor, (instruction, phrases) in PHRASES.items():
            client.set_instruction(instruction)
            for i, phrase in enumerate(phrases):
                total += 1
                path = out_dir / f"{flavor}_{i}.wav"
                if path.exists() and path.stat().st_size > 1000:
                    skipped += 1
                    continue
                audio = client.synthesize(phrase)
                if not audio:
                    failed += 1
                    print(f"[bank] 合成失败: {voice}/{flavor}_{i} ({phrase})")
                    continue
                path.write_bytes(audio)
                print(f"[bank] {voice}/{flavor}_{i}.wav  ({phrase})  {len(audio)} bytes")
    print(f"[bank] 完成: total={total} skipped={skipped} failed={failed} → {OUT_ROOT}")


if __name__ == "__main__":
    main()
