#!/usr/bin/env python3
"""
Echuu SDK + Gemini 3 Integration Test
测试完整的直播工作流，使用 Gemini 3 模型

Usage:
    python test_gemini3_streaming.py
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Add SDK to path
SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"
sys.path.insert(0, str(SDK_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def test_gemini3_basic():
    """Test basic Gemini 3 API connection"""
    print("\n" + "="*60)
    print("🧠 Test 1: Gemini 3 Basic API")
    print("="*60)

    try:
        from echuu.live.llm_factory import create_llm_client

        client = create_llm_client(
            provider="gemini",
            model="gemini-3-flash-preview",
            thinking_level="high"
        )

        response = client.call(
            prompt="用一句话介绍 Gemini 3 的主要特点",
            max_tokens=100
        )

        print(f"✅ Gemini 3 Response:\n{response}\n")
        return True

    except Exception as e:
        print(f"❌ Gemini 3 Test Failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_echuu_sdk_workflow():
    """Test complete Echuu SDK workflow with streaming topic"""
    print("\n" + "="*60)
    print("🎭 Test 2: Echuu SDK Workflow - Streaming Topic")
    print("="*60)

    try:
        from echuu.live.engine import EchuuLiveEngine

        # Create engine
        engine = EchuuLiveEngine()

        # Setup for streaming topic
        print("\n📝 Character Setup:")
        print("  Name: 六螺")
        print("  Persona: 25岁主播，活泼自嘲，喜欢分享生活经历")
        print("  Topic: 第一次直播的紧张经历")
        print("  Background: 刚开始做全职主播，以前是上班族\n")

        engine.setup(
            name="六螺",
            persona="25岁主播，活泼自嘲，喜欢分享生活经历",
            topic="第一次直播的紧张经历",
            background="刚开始做全职主播，以前是上班族",
        )

        # Simulate danmaku
        danmaku_sim = [
            {"step": 1, "text": "哈哈哈哈"},
            {"step": 2, "text": "我第一次直播也紧张"},
            {"step": 3, "text": "六螺加油！"},
        ]

        print("🎬 Starting Live Stream (5 steps)...\n")

        results = []
        for i, step in enumerate(engine.run(
            max_steps=5,
            danmaku_sim=danmaku_sim,
            play_audio=False,  # Don't play audio during test
            save_audio=True,   # But save it
        )):
            if i >= 5:
                break

            print(f"\n[Step {step['step']}] {step.get('stage', 'Unknown')}")
            print(f"Speech: {step.get('speech', '')[:100]}...")

            if step.get('danmaku'):
                print(f"💬 Danmaku: {step['danmaku']}")

            if step.get('inner_monologue'):
                print(f"💭 Inner Thought: {step['inner_monologue'][:80]}...")

            if step.get('cue'):
                cue = step['cue']
                if cue.get('emotion'):
                    print(f"🎭 Emotion: {cue['emotion']['key']} ({cue['emotion']['intensity']*100:.0f}%)")
                if cue.get('gesture'):
                    print(f"✋ Gesture: {cue['gesture']['clip']}")

            if step.get('audio_url'):
                print(f"🎵 Audio: {step['audio_url']}")

            results.append(step)

        print(f"\n✅ Workflow Test Complete!")
        print(f"   Generated {len(results)} steps")
        print(f"   Scripts saved to: {engine.scripts_dir}")
        return True

    except Exception as e:
        print(f"\n❌ Workflow Test Failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def test_echuu_with_thinking_levels():
    """Test Echuu SDK with different thinking levels"""
    print("\n" + "="*60)
    print("🧪 Test 3: Different Thinking Levels")
    print("="*60)

    thinking_levels = ["low", "high"]

    for level in thinking_levels:
        print(f"\n--- Testing with thinking_level={level} ---")

        try:
            from echuu.live.llm_factory import create_llm_client

            client = create_llm_client(
                provider="gemini",
                model="gemini-3-flash-preview",
                thinking_level=level
            )

            response = client.call(
                prompt="简单介绍一下你自己",
                max_tokens=50
            )

            print(f"Response ({level}): {response[:100]}...")

        except Exception as e:
            print(f"❌ Failed for level '{level}': {e}")
            return False

    print(f"\n✅ Thinking Levels Test Complete!")
    return True


def test_vrm_output():
    """Test VRM expression output"""
    print("\n" + "="*60)
    print("🎨 Test 4: VRM Expression Output")
    print("="*60)

    try:
        from echuu.vrm.mapper import VRMExpressionMapper, VRMVersion, EmotionKey

        mapper = VRMExpressionMapper(version=VRMVersion.VRM1)

        test_emotions = [
            (EmotionKey.HAPPY, 0.9),
            (EmotionKey.SURPRISED, 0.7),
            (EmotionKey.ANGRY, 1.0),
        ]

        print("\nVRM Commands:")
        for emotion, intensity in test_emotions:
            cmd = mapper.to_vrm_command(emotion, intensity)
            print(f"  {emotion.value} ({intensity}): {cmd}")

        print(f"\n✅ VRM Output Test Complete!")
        return True

    except Exception as e:
        print(f"\n❌ VRM Test Failed: {e}\n")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*70)
    print("   Echuu SDK + Gemini 3 Integration Test")
    print("="*70)
    print(f"\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Check environment
    gemini_key = os.getenv("GEMINI_API_KEY")
    if not gemini_key:
        print("\n⚠️  WARNING: GEMINI_API_KEY not set!")
        print("   Please set it in your .env file")
        return

    tts_key = os.getenv("DASHSCOPE_API_KEY")
    if not tts_key:
        print("\n⚠️  WARNING: DASHSCOPE_API_KEY not set!")
        print("   TTS will be disabled\n")

    # Run tests
    results = {}

    results["Gemini 3 Basic"] = test_gemini3_basic()
    results["Thinking Levels"] = test_echuu_with_thinking_levels()
    results["VRM Output"] = test_vrm_output()
    results["Full Workflow"] = test_echuu_sdk_workflow()

    # Summary
    print("\n" + "="*70)
    print("📊 Test Results Summary")
    print("="*70)

    for name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {name:.<40} {status}")

    print("\n" + "="*70)

    # Final message
    all_passed = all(results.values())
    if all_passed:
        print("\n🎉 All tests passed! Echuu SDK + Gemini 3 is working correctly!\n")
    else:
        print("\n⚠️  Some tests failed. Please check the errors above.\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
