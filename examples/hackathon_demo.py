#!/usr/bin/env python3
"""
Echuu - AI VTuber Auto-Live System
Demo for Gemini 3 Dev Hackathon

This demo showcases:
1. Gemini 3 Thinking Mode integration
2. Multi-language content generation
3. User memory and bonding system
4. Natural danmaku interaction
5. VRM avatar control signals
"""

import os
import sys
from pathlib import Path

# Add echuu to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Installing python-dotenv...")
    os.system("pip install python-dotenv")
    from dotenv import load_dotenv
    load_dotenv()


def demo_basic():
    """Basic demo - Generate streaming content"""
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*60)
    print("🎭 Echuu AI VTuber Demo - Gemini 3 Edition")
    print("="*60 + "\n")

    engine = EchuuLiveEngine()

    # Example: Chinese streaming
    print("📡 Generating Chinese streaming content...\n")
    engine.setup(
        name="小梅",
        persona="活泼可爱的VTuber主播，喜欢分享生活中的趣事",
        topic="食堂打饭遇到的有趣故事",
        language="zh"
    )

    for i, result in enumerate(engine.run(max_steps=5)):
        stage = result.get("stage", "")
        speech = result.get("speech", "")
        print(f"[{i+1}] {stage}")
        print(f"    {speech[:80]}...")
        print()

    print("✅ Demo complete!")


def demo_multilingual():
    """Multi-language demo"""
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*60)
    print("🌍 Multi-Language Demo")
    print("="*60 + "\n")

    engine = EchuuLiveEngine()

    # Test different languages
    test_cases = [
        ("zh", "小梅", "今天天气真好", "Chinese"),
        ("en", "Luna", "Complaining about algorithms", "English"),
        ("ja", "さくら", "秋葉原でグッズ購入", "Japanese"),
    ]

    for lang, name, topic, lang_name in test_cases:
        print(f"\n🌐 Testing {lang_name}...")
        engine.setup(
            name=name,
            persona=f"VTuber主播",
            topic=topic,
            language=lang
        )

        for result in engine.run(max_steps=2):
            speech = result.get("speech", "")
            # Check if language matches
            has_target_char = False
            if lang == "zh":
                has_target_char = any('\u4e00' <= c <= '\u9fff' for c in speech)
            elif lang == "ja":
                has_target_char = any('\u3040' <= c <= '\u30ff' for c in speech)
            elif lang == "en":
                has_target_char = any(c.isalpha() and ord(c) < 128 for c in speech)

            status = "✅" if has_target_char else "❌"
            print(f"  {status} {speech[:60]}...")
            break


def demo_user_memory():
    """User memory system demo"""
    from echuu.live.engine import EchuuLiveEngine
    from echuu.live.state import Danmaku

    print("\n" + "="*60)
    print("💾 User Memory & Bonding System Demo")
    print("="*60 + "\n")

    engine = EchuuLiveEngine()
    engine.setup(
        name="小梅",
        persona="活泼可爱的VTuber",
        topic="欢迎来到直播间",
        language="zh"
    )

    # Simulate multiple interactions from same user
    print("👤 Simulating user '小明' interacting multiple times...\n")

    danmaku_list = [
        Danmaku.from_text("主播你好！", "小明"),
        Danmaku.from_text("今天讲什么？", "小明"),
        Danmaku.from_text("哈哈哈哈太好笑了", "小明"),
        Danmaku.from_text("支持支持！", "小明"),
        Danmaku.from_text("我是老观众了", "小明"),
    ]

    for i, dm in enumerate(danmaku_list):
        # Update user memory
        engine.state.memory.update_user_from_danmaku(dm)

        # Get user profile
        user = engine.state.memory.get_or_create_user("小明")

        print(f"互动 {i+1}: {dm.text}")
        print(f"  用户等级: {user.get_bonding_description()}")
        print(f"  互动次数: {user.interaction_count}")

        # Generate response
        result = engine.performer.step(engine.state, new_danmaku=[dm])
        response = result.get("response", "")
        if response:
            print(f"  AI 回复: {response[:60]}...")
        print()

    print("✅ User bonding: 新观众 → 眼熟 → 老观众 → 核心粉丝")


def demo_vrm_cues():
    """VRM control signals demo"""
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*60)
    print("🎭 VRM Avatar Control Demo")
    print("="*60 + "\n")

    engine = EchuuLiveEngine()
    engine.setup(
        name="小梅",
        persona="活泼可爱的VTuber",
        topic="今天遇到的趣事",
        language="zh"
    )

    print("Generating VRM control signals:\n")

    for result in engine.run(max_steps=3):
        cue = result.get("cue")
        if cue:
            print(f"Stage: {result.get('stage')}")
            print(f"  Emotion: {cue.get('emotion', {})}")
            print(f"  Gesture: {cue.get('gesture', {})}")
            print(f"  Look: {cue.get('look', {})}")
            print()


def main():
    """Run all demos"""
    import argparse

    parser = argparse.ArgumentParser(description="Echuu AI VTuber Demo")
    parser.add_argument("--mode", choices=["basic", "multi", "memory", "vrm", "all"],
                        default="basic", help="Demo mode")

    args = parser.parse_args()

    try:
        if args.mode == "basic":
            demo_basic()
        elif args.mode == "multi":
            demo_multilingual()
        elif args.mode == "memory":
            demo_user_memory()
        elif args.mode == "vrm":
            demo_vrm_cues()
        elif args.mode == "all":
            demo_basic()
            demo_multilingual()
            demo_user_memory()
            demo_vrm_cues()

        print("\n" + "="*60)
        print("🎉 All demos completed!")
        print("="*60)
        print("\nFor more information:")
        print("  - README.md: Project overview")
        print("  - QUICKSTART.md: 5-minute setup guide")
        print("  - GEMINI3_FEATURES.md: Gemini 3 features")
        print("  - HACKATHON.md: Hackathon submission")
        print()

    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
