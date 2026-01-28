"""
echuu Live Engine - 解耦后的统一入口。
"""

from pathlib import Path
import sys

# 确保项目根目录可导入
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from echuu.live.engine import EchuuLiveEngine


if __name__ == "__main__":
    print("\n=== echuu Live Engine 测试 ===\n")

    engine = EchuuLiveEngine()

    engine.setup(
        name="六螺",
        persona="25岁主播，活泼自嘲，喜欢分享生活经历",
        topic="关于上司的超劲爆八卦",
        background="目前在一家外企市场部工作",
    )

    danmaku = [
        {"step": 1, "text": "真的假的，展开讲讲"},
        {"step": 3, "text": "这也太刺激了"},
        {"step": 5, "text": "[SC ¥50] 你们上司平时看起来很正经吗"},
    ]

    for _ in engine.run(danmaku_sim=danmaku, save_audio=True, play_audio=True):
        pass

    print("\n测试完成！")
