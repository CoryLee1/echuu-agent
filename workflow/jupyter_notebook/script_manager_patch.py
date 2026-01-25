# 剧本管理工具补丁
# 这个文件包含了剧本保存和进度管理的功能

from pathlib import Path
import json
from datetime import datetime
from typing import List, Dict

def save_script_to_file(script_lines, name: str, topic: str, scripts_dir: Path) -> str:
    """保存剧本到JSON文件"""
    # 生成文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_safe = topic[:20].replace(" ", "_").replace("/", "_")
    filename = f"{timestamp}_{name}_{topic_safe}.json"
    filepath = scripts_dir / filename
    
    # 转换为可序列化的格式
    script_data = {
        "metadata": {
            "name": name,
            "topic": topic,
            "generated_at": datetime.now().isoformat(),
            "total_lines": len(script_lines),
            "total_chars": sum(len(line.text) for line in script_lines)
        },
        "script": [
            {
                "id": line.id,
                "text": line.text,
                "stage": line.stage,
                "interruption_cost": line.interruption_cost,
                "key_info": line.key_info,
                "char_count": len(line.text)
            }
            for line in script_lines
        ]
    }
    
    # 保存
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(script_data, f, ensure_ascii=False, indent=2)
    
    print(f"💾 剧本已保存: {filename}")
    print(f"   路径: {filepath}")
    print(f"   总字数: {script_data['metadata']['total_chars']} 字\n")
    
    return str(filepath)


def show_script_progress(state):
    """显示剧本进度"""
    total = len(state.script_lines)
    current = state.current_line_idx
    
    print("\n" + "="*60)
    print("📊 剧本进度")
    print("="*60)
    
    # 进度条
    progress = current / total if total > 0 else 0
    bar_length = 40
    filled = int(progress * bar_length)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"\n进度: [{bar}] {current}/{total} ({progress*100:.1f}%)")
    print(f"当前阶段: {state.memory.script_progress.get('current_stage', 'Unknown')}")
    
    # 已说内容（最近3句）
    if current > 0:
        print(f"\n📖 已说内容（最近{min(3, current)}句）:")
        for i in range(max(0, current-3), current):
            line = state.script_lines[i]
            print(f"  [{i}] {line.text[:60]}{'...' if len(line.text) > 60 else ''}")
    
    # 当前句
    if current < total:
        print(f"\n▶️ 当前句:")
        line = state.script_lines[current]
        print(f"  [{current}] {line.text}")
        print(f"  🔑 key_info: {', '.join(line.key_info)}")
    
    # 未说内容（接下来3句）
    if current < total - 1:
        print(f"\n⏭️ 接下来{min(3, total-current-1)}句:")
        for i in range(current+1, min(current+4, total)):
            line = state.script_lines[i]
            print(f"  [{i}] ({line.stage}) {line.text[:50]}...")
    
    print("\n" + "="*60 + "\n")


