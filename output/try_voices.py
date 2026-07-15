#!/usr/bin/env python3
"""一次性：换新男声重跑 #1/#3 + 看自适应段数。用完即删。"""
import os, json
from dataclasses import asdict
from pathlib import Path
from importlib import reload

os.environ.setdefault("ECHUU_LLM_PROVIDER", "claude")

CONFIGS = [
    {"voice": "Moon", "name": "雷神教练",
     "persona": ("健身房热血私教，天天喊'兄弟练起来'，朋友圈全是肌肉打卡；"
                 "结果疫情居家偷偷胖了20斤，靠宽卫衣和滤镜瞒着学员。"),
     "topic": "作为私教，我是怎么瞒着学员偷偷胖20斤的",
     "background": "硬拉200kg奖牌还挂墙上，现在裤子扣不上",
     "danmaku": [{"text": "教练你自己还练吗哈哈", "user": "铁子"},
                 {"text": "¥58 减脂食谱发我!", "user": "卷王"}]},
    {"voice": "Andre", "name": "老代码",
     "persona": ("35岁被大厂裁员的后端程序员，理性到有点轴，凡事讲最优解；"
                 "失业后摆摊卖煎饼，忍不住用写代码那套去优化排队和出餐。"),
     "topic": "35岁被裁后我用算法优化了我的煎饼摊",
     "background": "煎饼车上贴着手写的'吞吐量/延迟'看板",
     "danmaku": [{"text": "35岁危机太真实了", "user": "同行"},
                 {"text": "用算法摊煎饼笑死", "user": "吃瓜"}]},
]


def run_one(cfg):
    os.environ["TTS_VOICE"] = cfg["voice"]
    import echuu.live.engine as eng_mod
    reload(eng_mod)
    engine = eng_mod.EchuuLiveEngine(llm_provider=os.environ["ECHUU_LLM_PROVIDER"])
    engine.setup(name=cfg["name"], persona=cfg["persona"], topic=cfg["topic"],
                 background=cfg["background"], language="zh")
    show = engine.state.show
    mins = round(len(show.units) * 75 / 60, 1)
    print("\n" + "=" * 74)
    print(f"🎤 voice={cfg['voice']}  {cfg['name']} — 段数={len(show.units)} (~{mins}min)")
    print(f"   主线: {show.story_core.spine}")
    print(f"   翻转: {show.story_core.twist}")
    print("-" * 74)
    Path("output/example_runs").mkdir(parents=True, exist_ok=True)
    Path(f"output/example_runs/voice_{cfg['name']}.json").write_text(json.dumps({
        "voice": cfg["voice"], "n_units": len(show.units),
        "story_core": asdict(show.story_core),
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    for _ in engine.run(max_steps=20, danmaku_sim=cfg["danmaku"], play_audio=False,
                        save_audio=True, convert_to_mp3=True, segment_gap_ms=1500):
        pass


if __name__ == "__main__":
    for cfg in CONFIGS:
        try:
            run_one(cfg)
        except Exception as e:
            import traceback
            print(f"❌ {cfg['name']} 失败: {e}"); traceback.print_exc()
