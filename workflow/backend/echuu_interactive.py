"""
echuu 交互式直播入口
支持用户输入人物信息并运行多个直播案例
"""

from pathlib import Path
import sys

# 确保项目根目录可导入
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from echuu.live.engine import EchuuLiveEngine


def get_user_input(prompt: str, default: str = "") -> str:
    """获取用户输入，支持默认值"""
    if default:
        user_input = input(f"{prompt} (默认: {default}): ").strip()
        return user_input if user_input else default
    else:
        while True:
            user_input = input(f"{prompt}: ").strip()
            if user_input:
                return user_input
            print("  输入不能为空，请重新输入")


def run_live_session(engine: EchuuLiveEngine, name: str, persona: str, background: str, topic: str):
    """运行一场直播会话"""
    print(f"\n{'='*70}")
    print(f"开始直播: {name} - {topic}")
    print(f"{'='*70}\n")
    
    # 生成模拟弹幕（根据话题动态生成）
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
    print(f"直播结束: {name} - {topic}")
    print(f"{'='*70}\n")


def main():
    print("\n" + "="*70)
    print("echuu 交互式直播系统")
    print("="*70 + "\n")
    
    # 获取基础人物信息
    print("【第一步】设置人物信息\n")
    name = get_user_input("人物名称")
    persona = get_user_input("人设描述", "25岁主播，活泼自嘲，喜欢分享生活经历")
    background = get_user_input("背景设定", "目前在一家外企市场部工作")
    
    print("\n【第二步】选择运行模式\n")
    print("1. 自定义主题（手动输入）")
    print("2. 运行预设案例（3个有趣话题）")
    print("3. 混合模式（先跑预设，再自定义）")
    
    mode = input("\n请选择模式 (1/2/3，默认2): ").strip() or "2"
    
    engine = EchuuLiveEngine()
    
    if mode == "1":
        # 仅自定义
        topic = get_user_input("\n请输入直播主题")
        run_live_session(engine, name, persona, background, topic)
        
    elif mode == "2":
        # 仅预设案例
        preset_topics = [
            "关于上司的超劲爆八卦",
            "大学时全班开卷考，但只有自己以为闭卷考结果没过",
            "第一次养猫时把猫粮当零食吃了",
        ]
        
        print("\n【预设案例】")
        for i, topic in enumerate(preset_topics, 1):
            print(f"{i}. {topic}")
        
        print("\n开始运行预设案例...\n")
        
        for i, topic in enumerate(preset_topics, 1):
            print(f"\n>>> 案例 {i}/{len(preset_topics)} <<<")
            run_live_session(engine, name, persona, background, topic)
            
            if i < len(preset_topics):
                input("\n按 Enter 继续下一个案例...")
        
    elif mode == "3":
        # 先预设，后自定义
        preset_topics = [
            "关于上司的超劲爆八卦",
            "大学时全班开卷考，但只有自己以为闭卷考结果没过",
            "第一次养猫时把猫粮当零食吃了",
        ]
        
        print("\n【第一步：运行预设案例】")
        for i, topic in enumerate(preset_topics, 1):
            print(f"{i}. {topic}")
        
        print("\n开始运行预设案例...\n")
        
        for i, topic in enumerate(preset_topics, 1):
            print(f"\n>>> 预设案例 {i}/{len(preset_topics)} <<<")
            run_live_session(engine, name, persona, background, topic)
            
            if i < len(preset_topics):
                input("\n按 Enter 继续下一个案例...")
        
        # 自定义部分
        print("\n【第二步：自定义主题】")
        while True:
            topic = get_user_input("\n请输入自定义直播主题（留空结束）", "")
            if not topic:
                break
            run_live_session(engine, name, persona, background, topic)
            
            continue_custom = input("\n继续添加自定义主题？(y/n，默认n): ").strip().lower()
            if continue_custom != "y":
                break
    
    print("\n" + "="*70)
    print("所有直播会话已完成！")
    print("="*70 + "\n")
    print(f"生成的剧本和音频文件保存在: {engine.scripts_dir}")


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
