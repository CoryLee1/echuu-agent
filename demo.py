#!/usr/bin/env python3
"""
简单演示 - 实时流式播放 + MP3 转换

使用方法:
    python demo.py --streaming    # 流式播放模式（播放音频+自然停顿）
    python demo.py --mp3          # 仅生成 MP3（不播放）
    python demo.py --both         # 两者都测试
"""

import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from echuu.live.engine import EchuuLiveEngine


def demo_streaming():
    """
    流式直播模式 - 实时播放每段音频，段落间有1-5秒自然停顿
    模拟真实直播体验
    """
    print("\n" + "="*70)
    print("  🎙️  流式直播模式演示")
    print("  - 串行播放每段音频")
    print("  - 段落间有1-5秒的自然停顿（根据剧本阶段智能调整）")
    print("  - 自动转换为 MP3 保存")
    print("="*70 + "\n")

    engine = EchuuLiveEngine()

    engine.setup(
        name="小梅",
        persona="活泼可爱的VTuber，喜欢分享生活中的趣事",
        topic="食堂打饭遇到的有趣故事",
        language="zh",
    )

    # 使用 run_streaming 方法
    engine.run_streaming(
        max_steps=8,
        save_audio=True,
        convert_to_mp3=True,
    )


def demo_mp3_only():
    """
    仅生成 MP3 - 不播放音频，快速生成压缩音频文件
    """
    print("\n" + "="*70)
    print("  💾 MP3 生成模式演示")
    print("  - 快速生成音频")
    print("  - 自动转换为 MP3 (压缩率 ~95%)")
    print("  - 不播放音频，仅保存")
    print("="*70 + "\n")

    engine = EchuuLiveEngine()

    engine.setup(
        name="Luna",
        persona="Energetic VTuber who loves dancing and sharing stories",
        topic="Complaining about platform algorithm",
        language="en",
    )

    # 使用 run 方法，不播放
    for i, result in enumerate(engine.run(
        max_steps=8,
        play_audio=False,
        save_audio=True,
        convert_to_mp3=True,  # 自动转换为 MP3
    )):
        speech = result.get("speech", "")
        stage = result.get("stage", "")
        print(f"[{i+1}] {stage}: {speech[:60]}...")

    print("\n✅ MP3 文件已保存到 output/scripts/")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="演示流式播放和 MP3 转换")
    parser.add_argument("--streaming", action="store_true", help="流式播放模式（播放音频+停顿）")
    parser.add_argument("--mp3", action="store_true", help="仅生成 MP3（不播放）")
    parser.add_argument("--both", action="store_true", help="两者都测试")

    args = parser.parse_args()

    try:
        if args.streaming or args.both:
            demo_streaming()

        if args.mp3 or args.both:
            demo_mp3_only()

        if not any([args.streaming, args.mp3, args.both]):
            print("\n请选择一个模式:")
            print("  python demo.py --streaming   # 流式播放模式")
            print("  python demo.py --mp3         # 仅生成 MP3")
            print("  python demo.py --both        # 两者都测试")

    except KeyboardInterrupt:
        print("\n\n演示被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
