#!/usr/bin/env python3
"""
清理和重构 echuu_with_tts_cleaned.ipynb
"""

import json
from pathlib import Path

def load_notebook(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_notebook(nb, path):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(nb, f, ensure_ascii=False, indent=1)

def get_cell_source(cell):
    """获取 cell 的源代码"""
    source = cell.get('source', [])
    if isinstance(source, list):
        return ''.join(source)
    return source

def set_cell_source(cell, source):
    """设置 cell 的源代码"""
    cell['source'] = source.split('\n')
    # 添加换行符
    cell['source'] = [line + '\n' for line in cell['source'][:-1]] + [cell['source'][-1]]

def main():
    nb_path = Path('echuu_with_tts_cleaned.ipynb')
    nb = load_notebook(nb_path)
    
    cells = nb['cells']
    print(f"原始 Cell 数量: {len(cells)}")
    
    # ========== 1. 标记要删除的 Cell ==========
    cells_to_delete = set()
    
    # Cell 1, 2: 重复的 save_script_to_file 代码
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if '# 💾 保存剧本（可选）' in source and 'save_script_to_file' in source:
            if i in [1, 2]:
                cells_to_delete.add(i)
                print(f"标记删除 Cell {i}: 重复的保存剧本代码")
    
    # 找到 Cell 36 (另一个重复的保存剧本)
    save_script_cells = []
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if '# 💾 保存剧本（可选）' in source and 'save_script_to_file' in source:
            save_script_cells.append(i)
    
    # 保留最后一个测试用例后的那个，删除其他
    if len(save_script_cells) > 1:
        for idx in save_script_cells[:-1]:
            if idx not in cells_to_delete:
                cells_to_delete.add(idx)
                print(f"标记删除 Cell {idx}: 重复的保存剧本代码")
    
    # 找到空的 Part 12 cell
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if '## Part 12: 📊 V2 版本核心改进' in source and cell['cell_type'] == 'markdown':
            # 检查是否只有标题
            if source.strip() == '## Part 12: 📊 V2 版本核心改进':
                cells_to_delete.add(i)
                print(f"标记删除 Cell {i}: 空的 Part 12")
    
    # ========== 2. 找到 SC优化代码 和 DanmakuEvaluator 定义 ==========
    sc_optimize_idx = None
    danmaku_evaluator_idx = None
    
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if '# 🔥 SC响应优化' in source and 'original_evaluate = DanmakuEvaluator.evaluate' in source:
            sc_optimize_idx = i
            print(f"找到 SC优化代码: Cell {i}")
        if 'class DanmakuEvaluator:' in source and 'def evaluate' in source:
            danmaku_evaluator_idx = i
            print(f"找到 DanmakuEvaluator 定义: Cell {i}")
    
    # ========== 3. 修复 TTSClient ==========
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if 'class TTSClient:' in source:
            # 修复 synthesize 方法中的 sample_rate
            if 'sample_rate=22050' in source:
                source = source.replace(
                    '''            # 注意：阿里云 TTS API 的参数名可能有所不同，需要查看最新文档
            audio_data = synthesizer.call(
                text,
                sample_rate=22050,
                # rate=dynamic_rate,    # 如果API支持，取消注释
                # pitch=dynamic_pitch,  # 如果API支持，取消注释
                # volume=self.volume,   # 如果API支持，取消注释
            )''',
                    '''            # 阿里云 TTS API: call() 只接受 text 参数
            audio_data = synthesizer.call(text)'''
                )
                set_cell_source(cell, source)
                print(f"修复 Cell {i}: TTSClient.synthesize() 移除 sample_rate")
    
    # ========== 4. 添加 _save_script 方法到 EchuuEngineV2 ==========
    for i, cell in enumerate(cells):
        source = get_cell_source(cell)
        if 'class EchuuEngineV2:' in source and 'def create_performance' in source:
            # 检查是否已有 _save_script
            if '_save_script' not in source:
                # 在 create_performance 方法之前添加 _save_script
                insert_point = source.find('    def create_performance')
                if insert_point > 0:
                    save_script_method = '''    def _save_script(self, script_lines, name: str, topic: str):
        """保存剧本到 JSON 文件"""
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        safe_topic = topic[:30].replace(' ', '_').replace('/', '_')
        filename = f"{timestamp}_{name}_{safe_topic}.json"
        filepath = self.scripts_dir / filename
        
        script_data = {
            "metadata": {
                "timestamp": timestamp,
                "name": name,
                "topic": topic,
                "total_lines": len(script_lines),
            },
            "script": [
                {
                    "id": line.id,
                    "text": line.text,
                    "stage": line.stage,
                    "cost": line.interruption_cost,
                    "key_info": line.key_info
                }
                for line in script_lines
            ]
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(script_data, f, ensure_ascii=False, indent=2)
        print(f"💾 剧本已保存: {filepath}")
    
'''
                    source = source[:insert_point] + save_script_method + source[insert_point:]
                    set_cell_source(cell, source)
                    print(f"添加 Cell {i}: EchuuEngineV2._save_script() 方法")
    
    # ========== 5. 重建 Cell 列表 ==========
    new_cells = []
    sc_optimize_cell = None
    
    for i, cell in enumerate(cells):
        if i in cells_to_delete:
            continue
        
        # 暂存 SC 优化代码
        if i == sc_optimize_idx:
            sc_optimize_cell = cell
            continue
        
        new_cells.append(cell)
        
        # 在 DanmakuEvaluator 定义后插入 SC 优化代码
        if sc_optimize_cell and i == danmaku_evaluator_idx:
            new_cells.append(sc_optimize_cell)
            sc_optimize_cell = None
            print(f"移动 SC优化代码 到 DanmakuEvaluator 定义之后")
    
    # ========== 6. 重新编号 Part 标题 ==========
    part_num = 0
    part_mapping = {}
    
    for i, cell in enumerate(new_cells):
        if cell['cell_type'] == 'markdown':
            source = get_cell_source(cell)
            # 匹配 ## Part X: 格式
            import re
            match = re.search(r'## Part \d+:', source)
            if match:
                part_num += 1
                old_part = match.group(0)
                new_part = f'## Part {part_num}:'
                if old_part != new_part:
                    source = source.replace(old_part, new_part, 1)
                    set_cell_source(cell, source)
                    part_mapping[old_part] = new_part
    
    if part_mapping:
        print(f"重新编号 Part 标题: {part_mapping}")
    
    # ========== 7. 整合导入 - 将 script_manager_patch 导入移到 Part 1 ==========
    script_manager_import_idx = None
    imports_cell_idx = None
    
    for i, cell in enumerate(new_cells):
        source = get_cell_source(cell)
        if 'from script_manager_patch import' in source:
            script_manager_import_idx = i
        if 'from IPython.display import' in source and 'from dotenv import' in source:
            imports_cell_idx = i
    
    if script_manager_import_idx and imports_cell_idx:
        # 将导入添加到主导入 cell
        import_cell = new_cells[imports_cell_idx]
        import_source = get_cell_source(import_cell)
        
        # 添加 script_manager 导入和目录创建
        additional_imports = '''
# 剧本管理工具
try:
    from script_manager_patch import save_script_to_file, show_script_progress
    scripts_dir = PROJECT_ROOT / "output" / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    print("✅ 剧本管理工具已加载")
except ImportError:
    print("⚠️ script_manager_patch 未找到，部分功能不可用")
    save_script_to_file = None
    show_script_progress = None
'''
        
        if 'script_manager_patch' not in import_source:
            import_source = import_source.rstrip() + '\n' + additional_imports
            set_cell_source(import_cell, import_source)
            print(f"整合导入: script_manager_patch 移到 Cell {imports_cell_idx}")
        
        # 删除原来的 script_manager 导入 cell
        # 但先确认它不是同一个 cell
        if script_manager_import_idx != imports_cell_idx:
            new_cells[script_manager_import_idx] = None
            print(f"标记删除原 script_manager 导入 Cell {script_manager_import_idx}")
    
    # 过滤掉 None
    new_cells = [c for c in new_cells if c is not None]
    
    # ========== 8. 清理元数据 ==========
    for cell in new_cells:
        # 清除执行计数
        if 'execution_count' in cell:
            cell['execution_count'] = None
        # 清除输出
        if 'outputs' in cell:
            cell['outputs'] = []
    
    # ========== 9. 保存 ==========
    nb['cells'] = new_cells
    save_notebook(nb, nb_path)
    
    print(f"\n✅ 清理完成！")
    print(f"原始 Cell 数量: {len(cells)}")
    print(f"清理后 Cell 数量: {len(new_cells)}")
    print(f"删除了 {len(cells) - len(new_cells)} 个 Cell")

if __name__ == '__main__':
    main()

