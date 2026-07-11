#!/usr/bin/env python3
"""
Run 3 Example Cases - Multilingual Support Test
测试3个案例：中文、日文、英文
"""

import os
import sys
import json
import datetime
from pathlib import Path

# Add SDK to path
SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"
sys.path.insert(0, str(SDK_ROOT))

# Load environment variables
from dotenv import load_dotenv
load_dotenv()


def run_example(example_file: str, output_dir: Path):
    """Run a single example case."""
    from echuu.live.engine import EchuuLiveEngine

    # Load example
    with open(example_file, "r", encoding="utf-8") as f:
        example = json.load(f)

    # Extract character info from example
    character = example.get("character", {})
    name = character.get("name", "主播")
    persona = character.get("persona", "VTuber主播")
    background = character.get("background", "")
    topic = example.get("topic", "分享有趣的故事")
    language = example.get("language", "zh")
    script = example.get("script", [])

    # Store metadata for results
    metadata_info = {
        "name": name,
        "persona": persona,
        "background": background,
        "topic": topic,
        "language": language
    }

    print("\n" + "="*70)
    print(f"   Example: {name}")
    print(f"   Topic: {topic}")
    print(f"   Language: {language}")
    print("="*70 + "\n")

    # Create engine and run
    engine = EchuuLiveEngine()

    # Setup with the character info
    engine.setup(
        name=name,
        persona=persona,
        topic=topic,
        background=background,
        language=language,
    )

    # Run without danmaku, just to see script generation in target language
    print("\n" + "="*70)
    print("   Running performance...")
    print("="*70 + "\n")

    results = []
    for i, step in enumerate(engine.run(
        max_steps=10,
        danmaku_sim=None,
        play_audio=False,
        save_audio=True,  # Enable audio saving
    )):
        results.append(step)
        if i >= 9:
            break

    return results, metadata_info


def main():
    examples_dir = Path("echuu-sdk-release/output/examples")

    examples = [
        "example_chinese_canteen.json",
        "example_japanese_akihabara.json",
        "example_english_dance_video.json",
    ]

    output_dir = Path("output/example_runs")
    output_dir.mkdir(parents=True, exist_ok=True)

    all_results = {}

    for example_name in examples:
        example_file = examples_dir / example_name
        if not example_file.exists():
            print(f"⚠️ Example file not found: {example_file}")
            continue

        try:
            results, metadata = run_example(str(example_file), output_dir)
            all_results[example_name] = {
                "metadata": metadata,
                "results": results
            }
        except Exception as e:
            print(f"❌ Error running {example_name}: {e}")
            import traceback
            traceback.print_exc()

    # Save results
    summary_file = output_dir / "summary.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": str(datetime.datetime.now()),
            "results": {
                name: {
                    "metadata": data["metadata"],
                    "first_speech": data["results"][0].get('speech', '')[:200] if data["results"] else ""
                }
                for name, data in all_results.items()
            }
        }, f, ensure_ascii=False, indent=2)

    # Summary
    print("\n" + "="*70)
    print("   SUMMARY - Multilingual Test Results")
    print("="*70 + "\n")

    for example_name, data in all_results.items():
        metadata = data["metadata"]
        results = data["results"]

        print(f"\n📺 {metadata.get('name', 'Unknown')} - {metadata.get('topic', 'Unknown')}")
        print(f"   Language: {metadata.get('language', 'Unknown')}")
        print(f"   Steps generated: {len(results)}")

        if results:
            first_speech = results[0].get('speech', '')[:200]
            print(f"   First speech preview: {first_speech}...")

            # Check if language matches
            lang = metadata.get('language', 'zh')
            first_speech_full = results[0].get('speech', '')

            if lang == 'zh':
                has_chinese = any('\u4e00' <= c <= '\u9fff' for c in first_speech_full)
                print(f"   ✓ Contains Chinese: {has_chinese}")
            elif lang == 'ja':
                has_japanese = any('\u3040' <= c <= '\u309f' or '\u30a0' <= c <= '\u30ff' for c in first_speech_full)
                print(f"   ✓ Contains Japanese: {has_japanese}")
            elif lang == 'en':
                has_english = any(c.isalpha() and ord(c) < 128 for c in first_speech_full)
                print(f"   ✓ Contains English: {has_english}")

    print("\n" + "="*70)
    print("✅ Test complete!")
    print("="*70 + "\n")
    print("Audio files saved in: output/scripts/")
    print("Check if generated content matches the target language!\n")


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
