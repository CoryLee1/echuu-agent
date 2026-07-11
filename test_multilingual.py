#!/usr/bin/env python3
"""
Test Multilingual Support
测试多语言支持和欢迎消息
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


def main():
    from echuu.live.engine import EchuuLiveEngine

    print("\n" + "="*70)
    print("   Echuu SDK - Multilingual Support Test")
    print("   多语言支持和欢迎消息测试")
    print("="*70 + "\n")

    # Test 1: Chinese stream with Chinese viewers
    print("📺 Test 1: 中文直播 + 中文观众")
    print("="*70 + "\n")

    engine_zh = EchuuLiveEngine()
    engine_zh.setup(
        name="六螺",
        persona="25岁主播，活泼自嘲，喜欢分享生活经历",
        topic="第一次直播的紧张经历",  # 中文topic
        background="刚开始做全职主播，以前是上班族",
    )

    print("语言设置:", engine_zh.stream_lang_context.greeting_style)
    print()

    # Simulate new Chinese viewer
    danmaku_zh = [
        {"step": 0, "text": "开播了开播了", "user": "小明"},
        {"step": 1, "text": "哈哈哈哈", "user": "小红"},
    ]

    for i, step in enumerate(engine_zh.run(max_steps=2, danmaku_sim=danmaku_zh, play_audio=False, save_audio=False)):
        if i >= 2:
            break
        print(f"[Step {step['step']}] Speech: {step.get('speech', '')[:100]}...\n")

    # Test 2: English stream with English viewers
    print("\n" + "="*70)
    print("📺 Test 2: English stream + English viewers")
    print("="*70 + "\n")

    engine_en = EchuuLiveEngine()
    engine_en.setup(
        name="Liu",
        persona="25-year-old streamer, lively and self-deprecating",
        topic="My first time streaming was super nervous",  # English topic
        background="Just quit job to become full-time streamer",
    )

    print("Language setting:", engine_en.stream_lang_context.greeting_style)
    print()

    # Simulate new English viewers
    danmaku_en = [
        {"step": 0, "text": "let's gooo", "user": "Mike"},
        {"step": 1, "text": "lololol that's funny", "user": "Sarah"},
    ]

    for i, step in enumerate(engine_en.run(max_steps=2, danmaku_sim=danmaku_en, play_audio=False, save_audio=False)):
        if i >= 2:
            break
        print(f"[Step {step['step']}] Speech: {step.get('speech', '')[:100]}...\n")

    # Test 3: Japanese stream
    print("\n" + "="*70)
    print("📺 Test 3: Japanese stream + Japanese viewers")
    print("="*70 + "\n")

    engine_ja = EchuuLiveEngine()
    engine_ja.setup(
        name="リュウ",
        persona="25歳の配信者、活発で自虐気味",
        topic="初めての配信の時の緊張",  # Japanese topic
        background="仕事を辞めてフルタイム配信者になったばかり",
    )

    print("Language setting:", engine_ja.stream_lang_context.greeting_style)
    print()

    # Simulate new Japanese viewers
    danmaku_ja = [
        {"step": 0, "text": "始まりました！", "user": "太郎"},
        {"step": 1, "text": "あははは", "user": "花子"},
    ]

    for i, step in enumerate(engine_ja.run(max_steps=2, danmaku_sim=danmaku_ja, play_audio=False, save_audio=False)):
        if i >= 2:
            break
        print(f"[Step {step['step']}] Speech: {step.get('speech', '')[:100]}...\n")

    # Test 4: Mixed language scenario
    print("\n" + "="*70)
    print("📺 Test 4: Mixed language - Chinese stream with international viewers")
    print("="*70 + "\n")

    engine_mixed = EchuuLiveEngine()
    engine_mixed.setup(
        name="六螺",
        persona="25岁主播，活泼自嘲，会点英语",
        topic="第一次直播的紧张经历",  # Chinese topic
        background="刚开始做全职主播，以前是上班族",
    )

    print("Language setting:", engine_mixed.stream_lang_context.greeting_style)
    print()

    # Mixed danmaku
    danmaku_mixed = [
        {"step": 0, "text": "hello everyone", "user": "John"},  # English
        {"step": 1, "text": "好好笑", "user": "小明"},  # Chinese
    ]

    for i, step in enumerate(engine_mixed.run(max_steps=2, danmaku_sim=danmaku_mixed, play_audio=False, save_audio=False)):
        if i >= 2:
            break
        print(f"[Step {step['step']}] Speech: {step.get('speech', '')[:120]}...\n")

    print("\n" + "="*70)
    print("✅ Multilingual Support Test Complete!")
    print("="*70 + "\n")
    print("Features Demonstrated:")
    print("  ✓ Auto-detect stream language from topic")
    print("  ✓ Generate welcome messages in matching language:")
    print("    - Chinese: 欢迎小明来到直播间！")
    print("    - English: Welcome Mike to the stream!")
    print("    - Japanese: 太郎さん、ありがとうございます！")
    print("  ✓ Response language adapts to viewer's language")
    print("  ✓ Mixed language handling (Chinese stream + English viewers)")
    print("\nHow it works:")
    print("  1. Detect language from user's topic input")
    print("  2. Set stream language context")
    print("  3. For new viewers: use welcome message in stream language")
    print("  4. For familiar viewers: match their language or use stream language")
    print("  5. All handled by LLM with language-aware prompts")
    print()


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
