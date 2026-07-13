"""生成 Qwen 音色试听 WAV 并上传 S3 — 前端 qwenVoices.ts 音色面板用。

输出: output/voice_previews/{voice}.wav → s3://nextjs-vtuber-assets/voice/{voice}.wav
运行: python scripts/build_voice_previews.py [--voices "Maia,Kai"] [--force] [--no-upload]
默认跳过 S3 上已存在的音色（--force 重新生成并覆盖）。
音色全集与 docs/qwen_tts_voices.md、前端 src/data/qwenVoices.ts 对齐（49 个）。
AWS 凭证从仓库根 .env 读取（AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY）。
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv

_AGENT_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = _AGENT_ROOT.parent
load_dotenv(_AGENT_ROOT / ".env")           # DASHSCOPE_API_KEY / TTS_*
load_dotenv(_REPO_ROOT / ".env")            # AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY

BUCKET = "nextjs-vtuber-assets"
REGION = "us-east-2"
S3_PREFIX = "voice/"
OUT_DIR = _AGENT_ROOT / "output" / "voice_previews"

# voice id → 试听台词里的自称（短名）。与 docs/qwen_tts_voices.md 全量对齐。
VOICES: dict[str, str] = {
    "Cherry": "芊悦", "Serena": "苏瑶", "Ethan": "晨煦", "Chelsie": "千雪",
    "Momo": "茉兔", "Vivian": "十三", "Moon": "月白", "Maia": "四月",
    "Kai": "凯", "Nofish": "不吃鱼", "Bella": "萌宝", "Jennifer": "詹妮弗",
    "Ryan": "甜茶", "Katerina": "卡捷琳娜", "Aiden": "艾登", "Eldric Sage": "沧明子",
    "Mia": "乖小妹", "Mochi": "沙小弥", "Bellona": "燕铮莺", "Vincent": "田叔",
    "Bunny": "萌小姬", "Neil": "阿闻", "Elias": "墨讲师", "Arthur": "徐大爷",
    "Nini": "邻家妹妹", "Ebona": "诡婆婆", "Seren": "小婉", "Pip": "顽屁小孩",
    "Stella": "少女阿月", "Bodega": "博德加", "Sonrisa": "索尼莎", "Alek": "阿列克",
    "Dolce": "多尔切", "Sohee": "素熙", "Ono Anna": "小野杏", "Lenn": "莱恩",
    "Emilien": "埃米尔安", "Andre": "安德雷", "Radio Gol": "拉迪奥·戈尔",
    "Jada": "阿珍", "Dylan": "晓东", "Li": "老李", "Marcus": "秦川",
    "Roy": "阿杰", "Peter": "李彼得", "Sunny": "晴儿", "Eric": "程川",
    "Rocky": "阿强", "Kiki": "阿清",
}

PREVIEW_TEXT = "嗨，你好呀！我是{name}，很高兴认识你。今天也一起开开心心直播吧！"


def _s3_client():
    import boto3

    return boto3.client("s3", region_name=REGION)


def _s3_exists(s3, key: str) -> bool:
    try:
        s3.head_object(Bucket=BUCKET, Key=key)
        return True
    except Exception:
        return False


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--voices", default=",".join(VOICES))
    parser.add_argument("--force", action="store_true", help="覆盖 S3 已有的试听")
    parser.add_argument("--no-upload", action="store_true", help="只生成本地 WAV")
    args = parser.parse_args()
    voices = [v.strip() for v in args.voices.split(",") if v.strip()]
    unknown = [v for v in voices if v not in VOICES]
    if unknown:
        print(f"[preview] 未知音色（不在 docs 全集里）: {unknown}")
        return

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    s3 = None if args.no_upload else _s3_client()

    made = skipped = failed = uploaded = 0
    for voice in voices:
        key = f"{S3_PREFIX}{voice}.wav"
        if s3 is not None and not args.force and _s3_exists(s3, key):
            skipped += 1
            continue

        path = OUT_DIR / f"{voice}.wav"
        if args.force or not (path.exists() and path.stat().st_size > 1000):
            os.environ["TTS_VOICE"] = voice
            from echuu.live.tts_client import TTSClient  # noqa: PLC0415 — 每音色重建 client

            client = TTSClient()
            if not client.enabled:
                print("[preview] TTS 不可用，中止（检查 DASHSCOPE_API_KEY）")
                return
            audio = client.synthesize(PREVIEW_TEXT.format(name=VOICES[voice]))
            if not audio:
                failed += 1
                print(f"[preview] 合成失败: {voice}")
                continue
            path.write_bytes(audio)
            made += 1
            print(f"[preview] {voice}.wav 已生成 ({len(audio)} bytes)")

        if s3 is not None:
            s3.upload_file(str(path), BUCKET, key, ExtraArgs={"ContentType": "audio/wav"})
            uploaded += 1
            print(f"[preview] ↑ s3://{BUCKET}/{key}")

    print(f"[preview] 完成: 生成={made} 上传={uploaded} 跳过(S3已有)={skipped} 失败={failed}")


if __name__ == "__main__":
    main()
