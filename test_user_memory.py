#!/usr/bin/env python3
"""
Test User Memory & Bonding System
测试用户记忆和情感连接系统
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
    from echuu.live.state import Danmaku

    print("\n" + "="*70)
    print("   Echuu SDK - User Memory & Bonding System Test")
    print("   测试用户记忆和情感连接系统")
    print("="*70 + "\n")

    # Create engine
    engine = EchuuLiveEngine()

    # Setup
    engine.setup(
        name="六螺",
        persona="25岁主播，活泼自嘲，喜欢分享生活经历",
        topic="第一次直播的紧张经历",
        background="刚开始做全职主播，以前是上班族",
    )

    # Simulate multiple danmaku from same users to build bonding
    # 模拟同一用户多次发弹幕来建立情感连接
    danmaku_scenarios = [
        # Step 1: New user "小明" laughs
        [
            Danmaku(text="哈哈哈哈", user="小明"),
        ],
        # Step 2: "小明" asks question, new user "小红" supports
        [
            Danmaku(text="然后呢然后呢", user="小明"),
            Danmaku(text="六螺加油！", user="小红"),
        ],
        # Step 3: "小明" again (3rd time - should be "眼熟")
        [
            Danmaku(text="我第一次直播也紧张", user="小明"),
        ],
        # Step 4-10: More interactions from "小明" to reach "老观众" status
        # We'll simulate repeated interactions
    ]

    print("📊 Scenario 1: Building relationship with viewer '小明'\n")
    print("Let's see how the VTuber responds as the bonding level increases...\n")

    # Simulate "小明" sending multiple danmaku
    ming_danmakus = [
        "哈哈哈哈",
        "然后呢",
        "我第一次直播也紧张",
        "真的假的",
        "太搞笑了",
        "支持支持",
        "哈哈哈哈",  # 7th
        "催更催更",
        "六螺加油",  # 9th
        "期待下次",  # 10th - should be "老观众"
    ]

    for i, dm_text in enumerate(ming_danmakus, 1):
        danmaku = Danmaku(text=dm_text, user="小明")

        # Update user profile
        user = engine.state.memory.update_user_from_danmaku(danmaku)

        bonding = user.get_bonding_description()
        print(f"[Interaction {i:2d}] '{dm_text}'")
        print(f"  └─ Bonding Level: {bonding}")
        print(f"  └─ User Profile: {user.get_context_summary()}")
        print()

    print("\n" + "="*70)
    print("📊 Memory Display:")
    print("="*70)
    print(engine.state.memory.to_display())

    print("\n" + "="*70)
    print("📊 Active Users Context (for LLM):")
    print("="*70)
    print(engine.state.memory.get_active_users_context(limit=5))

    # Now let's test a full workflow with named users
    print("\n" + "="*70)
    print("🎭 Running Live Stream with Named Users")
    print("="*70 + "\n")

    # Create danmaku simulation with named users
    named_danmaku_sim = [
        {"step": 0, "text": "开播了开播了", "user": "小明"},
        {"step": 1, "text": "哈哈哈哈", "user": "小红"},
        {"step": 2, "text": "我第一次直播也紧张", "user": "小明"},  # 3rd interaction
        {"step": 3, "text": "六螺加油！", "user": "小刚"},
        {"step": 4, "text": "然后呢然后呢", "user": "小明"},  # 4th interaction
    ]

    # Run 5 steps
    print("Starting live stream (5 steps)...\n")

    for i, step in enumerate(engine.run(max_steps=5, danmaku_sim=named_danmaku_sim, play_audio=False, save_audio=False)):
        if i >= 5:
            break

        print(f"\n[Step {step['step']}] {step.get('stage', 'Unknown')}")

        # Show danmaku response if any
        if step.get('danmaku'):
            danmaku_text = step['danmaku']
            # Extract username from speech to show who was responded to
            speech = step.get('speech', '')

            # Find which user this was from
            for dm in named_danmaku_sim:
                if dm['step'] == i-1 and dm['text'] == danmaku_text:
                    user_name = dm['user']
                    user = engine.state.memory.get_or_create_user(user_name)
                    bonding = user.get_bonding_description()
                    print(f"💬 Danmaku from {user_name} ({bonding})")
                    print(f"   Content: {danmaku_text}")
                    break

        # Show speech preview
        speech = step.get('speech', '')
        if speech:
            preview = speech[:80] + "..." if len(speech) > 80 else speech
            print(f"🗣️  Speech: {preview}")

        # Show memory state
        if step.get('memory_display'):
            print(step['memory_display'])

    print("\n" + "="*70)
    print("📊 Final User Profiles:")
    print("="*70)

    for username, user in engine.state.memory.user_profiles.items():
        print(f"\n{username}:")
        print(f"  Interactions: {user.interaction_count}")
        print(f"  Bonding: {user.get_bonding_description()}")
        if user.reaction_style:
            print(f"  Style: {user.reaction_style}")
        if user.total_sc_amount > 0:
            print(f"  Total SC: ¥{user.total_sc_amount}")

    print("\n" + "="*70)
    print("✅ User Memory & Bonding System Test Complete!")
    print("="*70 + "\n")
    print("Key Features Demonstrated:")
    print("  ✓ Tracks individual users by name")
    print("  ✓ Remembers interaction count")
    print("  ✓ Classifies bonding level (新观众→眼熟→老观众→核心粉丝)")
    print("  ✓ Provides user context to LLM for personalized responses")
    print("  ✓ Shows familiar viewers in memory display")
    print("\nNext Steps:")
    print("  • User profiles persist across sessions")
    print("  • LLM generates persona-driven responses based on relationship")
    print("  • SC history and special moments are tracked")
    print("  • Natural bonding builds over multiple interactions\n")


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
