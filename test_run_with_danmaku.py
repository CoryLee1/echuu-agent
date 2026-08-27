#!/usr/bin/env python3
"""
带假弹幕的完整流程测试：query + 弹幕 + 跑通并可选上传 S3
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
SDK_ROOT = PROJECT_ROOT / "echuu-sdk-release"
sys.path.insert(0, str(SDK_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv()

# 测试用 query：人设 + 话题
QUERY = {
    "name": "小梅",
    "persona": "活泼可爱的VTuber，喜欢碎碎念和分享日常糗事",
    "topic": "早上起床发现睡过头，狂奔去公司差点摔跤的倒霉经历",
    "language": "zh",
}

# 假弹幕：按 step 注入（step 0/1/2/3... 时出现）
FAKE_DANMAKU = [
    {"step": 0, "text": "主播早啊！", "user": "路人A"},
    {"step": 1, "text": "哈哈哈哈睡过头太真实了", "user": "吃瓜群众"},
    {"step": 2, "text": "后来迟到了吗？", "user": "好奇宝宝"},
    {"step": 3, "text": "SC ¥5 支持一下，主播别慌", "user": "热心观众"},
]


def main():
    print("=" * 60)
    print("  测试：query + 假弹幕 跑通")
    print("=" * 60)
    print("\nQuery:")
    for k, v in QUERY.items():
        print(f"  {k}: {v}")
    print("\n假弹幕:")
    for d in FAKE_DANMAKU:
        print(f"  step {d['step']}: [{d['user']}] {d['text']}")
    print()

    from echuu.live.engine import EchuuLiveEngine

    engine = EchuuLiveEngine()
    engine.setup(
        name=QUERY["name"],
        persona=QUERY["persona"],
        topic=QUERY["topic"],
        language=QUERY.get("language", "zh"),
    )

    count = 0
    for r in engine.run(
        max_steps=4,
        danmaku_sim=FAKE_DANMAKU,
        play_audio=False,
        save_audio=True,
        convert_to_mp3=True,
    ):
        count += 1
        step = r.get("step", 0)
        stage = r.get("stage", "?")
        speech = (r.get("speech") or "")[:70]
        print(f"[Step {step}] {stage}: {speech}...")
        if r.get("danmaku"):
            print(f"  -> 回应弹幕: {r['danmaku']}")

    print("\n表演结束，共 %d 步。" % count)
    print("剧本与音频已保存到 output/scripts/")

    # 可选上传 S3
    try:
        from services.s3_upload import upload_after_run, is_s3_configured
        if is_s3_configured():
            result = upload_after_run(engine.scripts_dir, memory=engine.state.memory)
            if not result.get("skipped"):
                print("\nS3 上传完成:")
                print("  streaming_content:", result.get("streaming_content"))
                print("  memory:", result.get("memory"))
            else:
                print("\nS3 已配置但本次未上传（或未找到新文件）")
        else:
            print("\nS3 未配置，跳过上传")
    except Exception as e:
        print("\nS3 上传跳过:", e)

    print("\n" + "=" * 60)
    print("  跑通完成")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
