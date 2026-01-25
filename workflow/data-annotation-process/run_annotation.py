#!/usr/bin/env python3
"""
echuu-agent 数据标注入口脚本

使用方法:
    # 快速标注（不调用LLM，使用启发式规则）
    python run_annotation.py --quick
    
    # LLM精细标注
    python run_annotation.py
    
    # 标注指定数量（用于测试）
    python run_annotation.py --max-clips 5
    
    # 指定输出路径
    python run_annotation.py -o custom_output.json
"""

import os
import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# 加载环境变量
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    print("⚠️ python-dotenv 未安装，请运行: pip install python-dotenv")
    print("   将使用系统环境变量")

# 导入标注pipeline
# 由于目录名包含连字符，需要特殊处理
import importlib.util
pipeline_path = Path(__file__).parent / "data_annotation_pipeline.py"
spec = importlib.util.spec_from_file_location("data_annotation_pipeline", pipeline_path)
pipeline_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pipeline_module)

load_raw_clips = pipeline_module.load_raw_clips
quick_convert_without_llm = pipeline_module.quick_convert_without_llm
run_annotation_pipeline = pipeline_module.run_annotation_pipeline


def get_config():
    """从环境变量获取配置"""
    return {
        "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
        "default_model": os.getenv("DEFAULT_MODEL", "claude-sonnet-4-20250514"),
        "raw_data_path": os.getenv("RAW_DATA_PATH", "data/vtuber_raw_clips_for_notebook_full_30_cleaned.jsonl"),
        "annotated_data_path": os.getenv("ANNOTATED_DATA_PATH", "data/annotated_clips.json"),
        "max_concurrent": int(os.getenv("MAX_CONCURRENT_REQUESTS", "3")),
        "request_delay": float(os.getenv("REQUEST_DELAY", "1.0")),
        "verbose": os.getenv("VERBOSE", "true").lower() == "true"
    }


def setup_llm_client(config: dict):
    """根据配置创建LLM客户端"""
    # 优先使用 Anthropic
    if config["anthropic_api_key"]:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=config["anthropic_api_key"])
            print("✅ 使用 Anthropic Claude API")
            return client, config["default_model"]
        except ImportError:
            print("⚠️ anthropic 未安装，请运行: pip install anthropic")
    
    # 其次使用 OpenAI
    if config["openai_api_key"]:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=config["openai_api_key"])
            print("✅ 使用 OpenAI API")
            return client, config["default_model"]
        except ImportError:
            print("⚠️ openai 未安装，请运行: pip install openai")
    
    return None, None


def print_banner():
    """打印欢迎banner"""
    print()
    print("=" * 60)
    print("  echuu-agent 数据标注工具")
    print("=" * 60)
    print()


def print_summary(annotated_clips: list, output_path: str, duration: float):
    """打印标注结果摘要"""
    total_segments = sum(len(c.get("segments", [])) for c in annotated_clips)
    zh_clips = sum(1 for c in annotated_clips if c.get("language") == "zh")
    en_clips = len(annotated_clips) - zh_clips
    
    print()
    print("=" * 60)
    print("  标注完成!")
    print("=" * 60)
    print(f"  总clip数: {len(annotated_clips)}")
    print(f"    - 中文: {zh_clips}")
    print(f"    - 英文: {en_clips}")
    print(f"  总segment数: {total_segments}")
    print(f"  平均segments/clip: {total_segments/len(annotated_clips):.1f}")
    print(f"  耗时: {duration:.1f}秒")
    print(f"  输出文件: {output_path}")
    print("=" * 60)
    print()


def main():
    parser = argparse.ArgumentParser(
        description="echuu-agent 数据标注工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python run_annotation.py --quick          # 快速模式
  python run_annotation.py --max-clips 5    # 只标注5个clip
  python run_annotation.py -v               # 详细输出
        """
    )
    
    parser.add_argument(
        "-i", "--input",
        help="输入JSONL文件路径（默认从.env读取）"
    )
    parser.add_argument(
        "-o", "--output",
        help="输出JSON文件路径（默认从.env读取）"
    )
    parser.add_argument(
        "--quick", action="store_true",
        help="快速模式：使用启发式规则，不调用LLM"
    )
    parser.add_argument(
        "--max-clips", type=int,
        help="最大处理clip数量（用于测试）"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true",
        help="显示详细输出"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="只检查配置，不执行标注"
    )
    
    args = parser.parse_args()
    
    # 打印banner
    print_banner()
    
    # 获取配置
    config = get_config()
    
    # 处理路径
    input_path = args.input or str(PROJECT_ROOT / config["raw_data_path"])
    output_path = args.output or str(PROJECT_ROOT / config["annotated_data_path"])
    verbose = args.verbose or config["verbose"]
    
    # 检查输入文件
    if not Path(input_path).exists():
        print(f"❌ 输入文件不存在: {input_path}")
        sys.exit(1)
    
    # 加载原始数据
    print(f"📂 加载数据: {input_path}")
    raw_clips = load_raw_clips(input_path)
    print(f"   找到 {len(raw_clips)} 个clips")
    
    # 限制数量
    if args.max_clips:
        raw_clips = raw_clips[:args.max_clips]
        print(f"   限制处理: {len(raw_clips)} 个clips")
    
    # Dry run 模式
    if args.dry_run:
        print("\n🔍 Dry Run 模式 - 配置检查")
        print(f"   输入: {input_path}")
        print(f"   输出: {output_path}")
        print(f"   模式: {'快速' if args.quick else 'LLM标注'}")
        if not args.quick:
            if config["anthropic_api_key"]:
                print(f"   API: Anthropic (key: ...{config['anthropic_api_key'][-8:]})")
            elif config["openai_api_key"]:
                print(f"   API: OpenAI (key: ...{config['openai_api_key'][-8:]})")
            else:
                print("   ⚠️ 未配置API Key")
        return
    
    # 开始计时
    start_time = datetime.now()
    
    # 执行标注
    if args.quick:
        print("\n🚀 快速模式（启发式规则）")
        annotated = quick_convert_without_llm(
            input_path, 
            output_path,
            verbose=verbose
        )
    else:
        # 设置LLM客户端
        client, model = setup_llm_client(config)
        
        if client is None:
            print("\n⚠️ 未配置有效的API Key")
            print("   请在 .env 文件中配置 ANTHROPIC_API_KEY 或 OPENAI_API_KEY")
            print("   或使用 --quick 模式（不需要API）")
            sys.exit(1)
        
        print(f"\n🤖 LLM标注模式 (模型: {model})")
        annotated = run_annotation_pipeline(
            input_path,
            output_path,
            client=client,
            model=model,
            max_clips=args.max_clips,
            verbose=verbose
        )
    
    # 计算耗时
    duration = (datetime.now() - start_time).total_seconds()
    
    # 打印摘要
    print_summary(annotated, output_path, duration)
    
    print("✨ 下一步: 在 echuu notebook 中加载 annotated_clips.json")


if __name__ == "__main__":
    main()
