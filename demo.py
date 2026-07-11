#!/usr/bin/env python3
"""
简单演示 - 实时流式播放 + MP3 转换

使用方法:
    python demo.py --streaming    # 流式播放模式（播放音频+自然停顿）
    python demo.py --mp3          # 仅生成 MP3（不播放）
    python demo.py --both         # 两者都测试
"""

import os
import sys
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


def demo_acceptance():
    """
    Rupture 引擎 V1 验收 (PR 8)。

    - setup() 后导出 Show 结构为 JSON + 跑结构性断言 (I1 / 轴序 / I3)
    - run() 实时渲染 4 units × ~3 lines，按 unit 切换 acoustic 并录制 MP3
    - 产物写到 output/example_runs/
    """
    import json
    from dataclasses import asdict

    print("\n" + "="*70)
    print("  🎬 Rupture 引擎 V1 验收演示 (PR 8)")
    print("  - 导出 Show JSON + 结构断言")
    print("  - 实时渲染 4 单元，per-unit acoustic 切换 + MP3 录制")
    print("="*70 + "\n")

    # Provider override: default auto-select picks Gemini, which is geo-blocked
    # in some regions. Allow ECHUU_LLM_PROVIDER to choose (e.g. "claude").
    provider = os.getenv("ECHUU_LLM_PROVIDER", "claude")
    engine = EchuuLiveEngine(llm_provider=provider)
    print(f"🤖 LLM provider: {provider}")

    # 身份/信念/弱点三轴都清晰的 persona，让弱点轴 (Unit[3]) 有料可演
    engine.setup(
        name="小梅",
        persona=(
            "我是 25 岁前 HR，现在是自由插画师。我一直觉得做喜欢的事比薪水重要，"
            "但说实话，决定辞职那天我还是哭了一整夜。手腕上贴满便签是我的怪癖。"
        ),
        topic="转行 6 个月的真实体感",
        language="zh",
    )

    # --- Show JSON dump + acceptance asserts (V2 内容质感) ---
    show = engine.state.show
    show_json = {
        "rich_persona": asdict(show.persona),
        "story_core": asdict(show.story_core) if show.story_core else None,
        "topic": show.topic,
        "units": [
            {
                "index": u.index,
                "time_window": list(u.time_window),
                "density": u.density,
                "acoustic": asdict(u.acoustic),
                "lines": [
                    {"id": l.id, "text": l.text, "stage": l.stage}
                    for l in u.lines
                ],
            }
            for u in show.units
        ],
    }
    out_dir = Path("output/example_runs")
    out_dir.mkdir(parents=True, exist_ok=True)
    show_path = out_dir / "demo_show.json"
    with open(show_path, "w", encoding="utf-8") as f:
        json.dump(show_json, f, ensure_ascii=False, indent=2)
    print(f"📄 Show JSON: {show_path}")

    assert 2 <= len(show.units) <= 4, "节目段数应在 2~4（长度自适应）"
    assert all(len(u.lines) >= 2 for u in show.units), "每个 unit 至少 2 行台词"
    assert show.persona.flaw, "I4: persona.flaw 必须非空"
    print("✅ 结构校验通过 (I1 / 每段有台词 / I4 flaw 非空)。")
    print(f"   故事主线: {show.story_core.spine if show.story_core else '-'}")
    print(f"   语癖: {'、'.join(show.persona.verbal_tics) or '-'}\n")

    # --- Live render + MP3 recording (run() records & saves internally) ---
    # 注入几条模拟弹幕，演示 Cursor 式排队 + 弹幕穿插
    danmaku_sim = [
        {"text": "主播你后悔转行吗？", "user": "阿强"},
        {"text": "改17次也太惨了哈哈哈", "user": "momo"},
        {"text": "¥66 加油画手！", "user": "老粉丝"},
        {"text": "甲方都是魔鬼", "user": "打工人"},
    ]
    # 段间插 1.5s 静音让 MP3 有喘气感（实时直播由前端 gap 控制，更长）
    for ev in engine.run(max_steps=20, danmaku_sim=danmaku_sim, play_audio=False,
                         save_audio=True, convert_to_mp3=True, segment_gap_ms=1500):
        pass  # progress is printed inside run()

    print("\n✅ 验收演示完成。MP3 已保存到 output/scripts/（见上方录制路径）。")
    print(f"   结构产物: {show_path}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="演示流式播放和 MP3 转换")
    parser.add_argument("--streaming", action="store_true", help="流式播放模式（播放音频+停顿）")
    parser.add_argument("--mp3", action="store_true", help="仅生成 MP3（不播放）")
    parser.add_argument("--both", action="store_true", help="两者都测试")
    parser.add_argument("--acceptance", action="store_true", help="Rupture 引擎 V1 验收 (Show JSON + MP3)")

    args = parser.parse_args()

    try:
        if args.acceptance:
            demo_acceptance()

        if args.streaming or args.both:
            demo_streaming()

        if args.mp3 or args.both:
            demo_mp3_only()

        if not any([args.streaming, args.mp3, args.both, args.acceptance]):
            print("\n请选择一个模式:")
            print("  python demo.py --acceptance  # Rupture 引擎 V1 验收 (推荐)")
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
