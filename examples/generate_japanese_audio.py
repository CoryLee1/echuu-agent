#!/usr/bin/env python3
"""
Generate Japanese audio example for the hackathon repository
"""

import sys
import os
from pathlib import Path

# Add echuu to path
sys.path.insert(0, str(Path(__file__).parent))

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from echuu.live.engine import EchuuLiveEngine

def main():
    print("Generating Japanese audio example...")

    engine = EchuuLiveEngine()

    # Japanese streaming - Akihabara story
    print("\n📡 Generating Japanese streaming content (Akihabara story)...\n")

    engine.setup(
        name="さくら",
        persona="オタク系VTuber、アニメとゲームが大好き",
        topic="秋葉原でグッズを買いに行ったら同好の士に出会った話",
        language="ja"
    )

    # Generate with TTS and save as MP3
    results = list(engine.run_streaming(
        max_steps=5,  # Shorter for demo
        save_audio=True,
        convert_to_mp3=True
    ))

    print(f"\n✅ Generated {len(results)} steps")
    print("\nAudio saved to output/scripts/")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
