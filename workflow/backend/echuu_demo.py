"""
echuu 演示脚本 - 运行预设案例
无需交互，直接运行3个有趣的直播案例
"""

from pathlib import Path

from echuu.live.engine import EchuuLiveEngine


def run_live_session(engine: EchuuLiveEngine, name: str, persona: str, background: str, topic: str, session_num: int = 1):
    """运行一场直播会话"""
    print(f"\n{'='*70}")
    print(f"【案例 {session_num}】{name} - {topic}")
    print(f"{'='*70}\n")
    
    # 根据话题生成动态弹幕
    danmaku_templates = [
        {"step": 1, "text": "哈哈哈"},
        {"step": 2, "text": "真的假的"},
        {"step": 3, "text": "展开讲讲"},
        {"step": 4, "text": "这也太刺激了"},
        {"step": 5, "text": "[SC ¥50] 然后呢然后呢"},
    ]
    
    engine.setup(
        name=name,
        persona=persona,
        topic=topic,
        background=background,
    )
    
    for _ in engine.run(danmaku_sim=danmaku_templates, save_audio=True, play_audio=True):
        pass
    
    print(f"\n{'='*70}")
    print(f"✅ 案例 {session_num} 完成")
    print(f"{'='*70}\n")


def main():
    print("\n" + "="*70)
    print("echuu 演示模式 - 运行3个预设案例")
    print("="*70 + "\n")
    
    # 默认人物信息（可通过环境变量或命令行参数覆盖）
    import os
    name = os.getenv("ECHUU_NAME", "六螺")
    persona = os.getenv("ECHUU_PERSONA", "25岁主播，活泼自嘲，喜欢分享生活经历")
    background = os.getenv("ECHUU_BACKGROUND", "目前在一家外企市场部工作")
    
    print(f"人物名称: {name}")
    print(f"人设: {persona}")
    print(f"背景: {background}\n")
    
    # 3个有趣的预设案例
    preset_topics = [
        "关于上司的超劲爆八卦",
        "大学时全班开卷考，但只有自己以为闭卷考结果没过",
        "第一次养猫时把猫粮当零食吃了",
    ]
    
    engine = EchuuLiveEngine()
    
    for i, topic in enumerate(preset_topics, 1):
        run_live_session(engine, name, persona, background, topic, session_num=i)
        
        if i < len(preset_topics):
            print(f"等待3秒后继续下一个案例...\n")
            import time
            time.sleep(3)
    
    print("\n" + "="*70)
    print("🎉 所有演示案例已完成！")
    print("="*70 + "\n")
    print(f"📁 生成的剧本和音频文件保存在: {engine.scripts_dir}")
    print("\n💡 提示：")
    print("   - 可以通过环境变量自定义人物信息：")
    print("     ECHUU_NAME=你的名字")
    print("     ECHUU_PERSONA=你的人设")
    print("     ECHUU_BACKGROUND=你的背景")
    print("   - 或运行交互式模式：python workflow/backend/echuu_interactive.py")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，退出程序")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
