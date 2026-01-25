#!/usr/bin/env python3
"""
echuu-agent 集成测试脚本

测试 Claude LLM + 通义千问 TTS 的集成

使用方法:
    python workflow/backend/test_integration.py
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def test_llm():
    """测试 Claude LLM"""
    print("\n" + "="*50)
    print("🧠 测试 Claude LLM")
    print("="*50)
    
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        print("❌ 未设置 ANTHROPIC_API_KEY")
        return False
    
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        
        response = client.messages.create(
            model=os.getenv("DEFAULT_MODEL", "claude-3-haiku-20240307"),
            max_tokens=100,
            messages=[{"role": "user", "content": "用一句话介绍你自己"}]
        )
        
        print(f"✅ LLM 响应: {response.content[0].text[:100]}...")
        return True
        
    except Exception as e:
        print(f"❌ LLM 测试失败: {e}")
        return False


def test_tts():
    """测试通义千问 TTS"""
    print("\n" + "="*50)
    print("🔊 测试通义千问 TTS")
    print("="*50)
    
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        print("⚠️ 未设置 DASHSCOPE_API_KEY，跳过 TTS 测试")
        print("   如需使用 TTS，请在 .env 文件中配置:")
        print("   DASHSCOPE_API_KEY=your-api-key")
        print("   获取地址: https://bailian.console.aliyun.com/?tab=model#/api-key")
        return None
    
    try:
        from workflow.backend.tts_client import CosyVoiceTTS
        
        tts = CosyVoiceTTS()
        
        output_path = PROJECT_ROOT / "output" / "test_tts.mp3"
        output_path.parent.mkdir(exist_ok=True)
        
        audio = tts.synthesize(
            "你好，我是echuu AI主播，很高兴认识你！",
            str(output_path)
        )
        
        print(f"✅ TTS 成功! 音频大小: {len(audio)} bytes")
        print(f"   保存路径: {output_path}")
        return True
        
    except Exception as e:
        print(f"❌ TTS 测试失败: {e}")
        return False


def test_engine():
    """测试完整引擎"""
    print("\n" + "="*50)
    print("🎭 测试 echuu Live Engine")
    print("="*50)
    
    try:
        from workflow.backend.echuu_live_engine import EchuuLiveEngine
        
        engine = EchuuLiveEngine()
        
        # 禁用 TTS 如果没有配置
        if not os.getenv("DASHSCOPE_API_KEY"):
            engine.enable_tts = False
        
        engine.setup(
            name="六螺",
            persona="25岁主播，活泼自嘲",
            topic="留学时偷吃室友腰果的故事"
        )
        
        # 模拟弹幕
        danmaku = [
            {"step": 1, "text": "哈哈哈"},
            {"step": 2, "text": "[SC ¥50] 室友后来知道了吗"},
        ]
        
        # 只运行3步
        print("\n🎬 开始表演 (3步测试)...\n")
        for i, output in enumerate(engine.run(max_steps=3, danmaku_sim=danmaku)):
            if i >= 3:
                break
        
        print("✅ 引擎测试完成!")
        return True
        
    except Exception as e:
        print(f"❌ 引擎测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("\n" + "="*60)
    print("   echuu-agent 集成测试")
    print("="*60)
    
    results = {}
    
    # 测试 LLM
    results["LLM"] = test_llm()
    
    # 测试 TTS
    results["TTS"] = test_tts()
    
    # 测试完整引擎
    results["Engine"] = test_engine()
    
    # 汇总
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    for name, result in results.items():
        if result is True:
            status = "✅ 通过"
        elif result is False:
            status = "❌ 失败"
        else:
            status = "⚠️ 跳过"
        print(f"  {name}: {status}")
    
    print("\n" + "="*60)
    
    # 配置提示
    if not os.getenv("DASHSCOPE_API_KEY"):
        print("\n💡 提示: 如需启用 TTS 功能，请配置 DASHSCOPE_API_KEY")
        print("   1. 访问 https://bailian.console.aliyun.com/?tab=model#/api-key")
        print("   2. 创建 API Key")
        print("   3. 在 .env 文件中添加: DASHSCOPE_API_KEY=your-key")


if __name__ == "__main__":
    main()
