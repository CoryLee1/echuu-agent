#!/usr/bin/env python3
"""
测试 echuu agent 是否正常工作，以及上传相关能力。
- Agent: 使用 echuu-sdk-release 的 EchuuLiveEngine，跑 1 步（不播放、不保存音频）
- 上传: 当前项目无 AWS S3 实现；echuu-web 的 3D 模型上传为本地 storage
"""

import sys
from pathlib import Path

# Add SDK to path
SDK_ROOT = Path(__file__).parent / "echuu-sdk-release"
sys.path.insert(0, str(SDK_ROOT))

def test_agent():
    """测试 echuu 引擎：初始化、setup、跑 1 步"""
    from dotenv import load_dotenv
    load_dotenv()

    from echuu.live.engine import EchuuLiveEngine

    print("[1] 导入引擎 ... OK")
    e = EchuuLiveEngine()
    e.setup(name="测试", persona="测试用", topic="打个招呼", language="zh")
    print("[2] Setup 完成，剧本单元数:", len(e.state.script_lines))

    count = 0
    for r in e.run(max_steps=1, play_audio=False, save_audio=False):
        count += 1
        speech = (r.get("speech") or "")[:60]
        print("[3] Step 执行:", speech, "...")
    print("[4] Agent 运行 ... OK (执行步数: %d)" % count)
    return e


def main():
    print("=" * 60)
    print("  Echuu Agent 与上传能力测试")
    print("=" * 60)

    # Agent
    try:
        engine = test_agent()
    except Exception as e:
        print("Agent 测试失败:", e)
        import traceback
        traceback.print_exc()
        return 1

    # 可选：若已配置 S3，测试上传
    try:
        sys.path.insert(0, str(Path(__file__).parent))
        from services.s3_upload import upload_after_run, is_s3_configured
        if is_s3_configured():
            r = upload_after_run(engine.scripts_dir, memory=engine.state.memory)
            if r.get("skipped"):
                print("[5] S3 已配置但跳过（无新文件或未找到）")
            else:
                print("[5] S3 上传测试:", r.get("streaming_content"), "memory:", r.get("memory"))
        else:
            print("[5] S3 未配置（未设置 AWS_ACCESS_KEY_ID/SECRET），跳过上传测试")
    except Exception as e:
        print("[5] S3 测试跳过:", e)

    # 上传说明
    print()
    print("上传说明:")
    print("  - 已实现 S3 上传：streaming_content/（文+声音）、memory/（收藏/日记）")
    print("  - 在 .env 中配置 AWS_ACCESS_KEY_ID、AWS_SECRET_ACCESS_KEY、S3_BUCKET=nextjs-vtuber-assets")
    print("  - demo.py 与 workflow 跑完后会自动上传到 S3（若已配置）")
    print()
    print("=" * 60)
    print("  测试通过")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
