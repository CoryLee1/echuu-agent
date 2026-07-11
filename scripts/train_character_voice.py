"""一次性工具：用 Qwen TTS 预置音色合成训练数据，在 Replicate 云端训练角色 RVC 音色模型。

不需要真人录音——说话声（TTS）和唱歌声（RVC 转换）出自同一声源，声线天然统一。

用法：
  1. .env 配好 DASHSCOPE_API_KEY 和 REPLICATE_API_TOKEN
  2. python scripts/train_character_voice.py --voice Chelsie --name xiaoyu
  3. 训练完成后把输出的模型 URL 填进 .env 的 RVC_MODEL_URL

成本：训练一次约 $1-3（Replicate GPU 按秒计费），每个角色只需一次。
"""
from __future__ import annotations

import argparse
import io
import os
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv

# 训练语料：覆盖不同情绪/语速/音域的句子，凑约 8-10 分钟语音
_CORPUS = [
    "大家好呀，今天也是元气满满的一天！我们今天聊点特别的话题好不好？",
    "啊……这个嘛，其实我一直没有想清楚，让我再想想，再想想哦。",
    "不会吧不会吧！居然真的有人这样做吗？我不信，我真的不信！",
    "夜深了，今天就到这里吧。谢谢每一个陪我到现在的人，晚安，好梦。",
    "哈哈哈哈哈这个太好笑了，等一下，让我笑完，笑完再继续讲。",
    "其实那天我挺难过的，但是我没有说出来，因为我觉得说出来也没有用。",
    "三、二、一！开始！哇，这个速度也太快了吧，完全跟不上啊！",
    "如果你也有这样的经历，把它打在弹幕里，让我看到你们的故事。",
    "嗯——让我唱一句试试看哦：啦啦啦，啦——啦啦，咦，好像还不错？",
    "有时候我在想，我们为什么要这么努力呢？大概是因为，想成为更好的自己吧。",
    "什么？！你再说一遍？！我没听错吧！这也太离谱了！",
    "轻轻地告诉你一个秘密，你可不要告诉别人哦，拉钩上吊一百年不许变。",
]


def synthesize_corpus(voice: str, out_dir: Path, repeats: int) -> list[Path]:
    os.environ["TTS_MODEL"] = os.getenv("TTS_MODEL", "qwen3-tts-flash-realtime")
    os.environ["TTS_VOICE"] = voice
    from echuu.live.tts_client import TTSClient

    tts = TTSClient()
    if not tts.enabled:
        raise RuntimeError("TTS 初始化失败，检查 DASHSCOPE_API_KEY")

    out_dir.mkdir(parents=True, exist_ok=True)
    files = []
    total = len(_CORPUS) * repeats
    for r in range(repeats):
        for i, text in enumerate(_CORPUS):
            idx = r * len(_CORPUS) + i
            path = out_dir / f"corpus_{idx:03d}.wav"
            if path.exists():
                files.append(path)
                continue
            audio = tts.synthesize(text)
            if audio:
                path.write_bytes(audio)
                files.append(path)
            print(f"  [{idx + 1}/{total}] {'ok' if audio else 'FAIL'} {text[:18]}...")
    return files


def train_on_replicate(dataset_zip: Path, name: str) -> str:
    import replicate

    print("上传数据集并启动 Replicate 训练（约 10-30 分钟）...")
    model = os.getenv(
        "RVC_TRAIN_MODEL",
        "replicate/train-rvc-model:0397d5e28c9b54665e1e5d29c0cbca8b95ab40261e9584d3922b7b436b0b8060",
    )
    with open(dataset_zip, "rb") as f:
        output = replicate.run(model, input={
            "dataset_zip": f,
            "sample_rate": "48k",
            "version": "v2",
            "f0method": "rmvpe_gpu",
            "epoch": 80,
            "batch_size": "7",
        })
    url = output.get("url") if isinstance(output, dict) else str(output)
    return url


def main():
    parser = argparse.ArgumentParser(description="训练角色 RVC 音色模型（全云端）")
    parser.add_argument("--voice", default="Chelsie", help="Qwen TTS 预置音色（角色说话用的同一个）")
    parser.add_argument("--name", default="character", help="角色名（用于输出文件命名）")
    parser.add_argument("--repeats", type=int, default=4, help="语料重复轮数（4 轮约 8-10 分钟语音）")
    parser.add_argument("--skip-train", action="store_true", help="只合成语料打包，不启动训练")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    load_dotenv(root / ".env")

    work = root / "output" / f"voice_training_{args.name}"
    print(f"1/3 合成训练语料（音色={args.voice}，{args.repeats} 轮）...")
    files = synthesize_corpus(args.voice, work / "wavs", args.repeats)
    if len(files) < len(_CORPUS):
        raise RuntimeError("语料合成不完整，重跑一次（已合成的会跳过）")

    print("2/3 打包数据集...")
    dataset_zip = work / f"{args.name}_dataset.zip"
    with zipfile.ZipFile(dataset_zip, "w", zipfile.ZIP_STORED) as zf:
        for p in files:
            zf.write(p, f"dataset/{p.name}")
    print(f"  {dataset_zip} ({dataset_zip.stat().st_size / 1e6:.1f} MB)")

    if args.skip_train:
        print("--skip-train：到此为止。")
        return

    if not os.getenv("REPLICATE_API_TOKEN"):
        raise RuntimeError("未配置 REPLICATE_API_TOKEN，无法启动云端训练")

    print("3/3 云端训练...")
    url = train_on_replicate(dataset_zip, args.name)
    print("\n========== 训练完成 ==========")
    print(f"模型 URL: {url}")
    print("把它填进 .env：")
    print(f"  RVC_MODEL_URL={url}")


if __name__ == "__main__":
    main()
