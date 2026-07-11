#!/usr/bin/env python3
"""
测试实时流式播放 + MP3 转换
"""

import os
import sys
from pathlib import Path

# Add SDK to path
SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"
sys.path.insert(0, str(SDK_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def test_streaming_mode():
    """测试实时流式直播模式"""
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*60)
    print("  测试实时流式直播模式（带自然停顿 + MP3 转换）")
    print("="*60 + "\n")

    # Create engine
    engine = EchuuLiveEngine()

    # Simple test case
    name = "小梅"
    persona = "活泼可爱的VTuber主播，喜欢分享生活中的趣事"
    topic = "今天遇到的搞笑事情"
    language = "zh"

    # Setup
    engine.setup(
        name=name,
        persona=persona,
        topic=topic,
        language=language,
    )

    # Run streaming mode (plays audio with natural pauses)
    # 串行播放每段音频，段落间有1-5秒的自然停顿
    engine.run_streaming(
        max_steps=6,  # 测试6步
        danmaku_sim=None,  # 无弹幕
        save_audio=True,   # 保存音频
        convert_to_mp3=True,  # 自动转换为 MP3
    )


def test_mp3_conversion():
    """测试 MP3 转换功能"""
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*60)
    print("  测试 MP3 自动转换功能")
    print("="*60 + "\n")

    # Create engine
    engine = EchuuLiveEngine()

    # Test case - English
    name = "Luna"
    persona = "Energetic VTuber who loves dancing and sharing stories"
    topic = "My experience with platform algorithms"
    language = "en"

    # Setup
    engine.setup(
        name=name,
        persona=persona,
        topic=topic,
        language=language,
    )

    # Run with MP3 conversion (no streaming playback)
    print("\n生成内容并自动转换为 MP3...\n")

    for i, result in enumerate(engine.run(
        max_steps=5,
        save_audio=True,
        convert_to_mp3=True,  # 自动转换为 MP3
    )):
        speech = result.get("speech", "")
        print(f"  [{i+1}] {speech[:60]}...")
        if i >= 4:
            break

    print("\n✅ 测试完成！检查 output/scripts/ 目录中的 MP3 文件\n")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="测试流式播放和 MP3 转换")
    parser.add_argument("--mode", choices=["streaming", "mp3", "both"], default="streaming",
                        help="测试模式: streaming=流式播放, mp3=仅转换, both=两者都测试")

    args = parser.parse_args()

    try:
        if args.mode in ["streaming", "both"]:
            test_streaming_mode()

        if args.mode in ["mp3", "both"]:
            test_mp3_conversion()

    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
