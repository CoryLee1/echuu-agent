#!/usr/bin/env python3
"""
项目清理脚本 - 清理临时文件和归档旧文件
"""

import os
import shutil
from pathlib import Path


def cleanup_project():
    """清理项目中的临时文件和归档旧文件"""

    project_root = Path.cwd()

    print("="*60)
    print("  项目清理工具")
    print("="*60)
    print()

    # 1. 清理 Python 缓存
    print("1. 清理 Python 缓存...")
    pycache_dirs = list(project_root.rglob("__pycache__"))
    for d in pycache_dirs:
        if d.is_dir():
            shutil.rmtree(d)
            print(f"   ✓ 删除: {d.relative_to(project_root)}")

    # 2. 清理 Jupyter checkpoints
    print("\n2. 清理 Jupyter checkpoints...")
    checkpoint_dirs = list(project_root.rglob(".ipynb_checkpoints"))
    for d in checkpoint_dirs:
        if d.is_dir():
            shutil.rmtree(d)
            print(f"   ✓ 删除: {d.relative_to(project_root)}")

    # 3. 清理 .cursor 临时文件
    print("\n3. 清理编辑器临时文件...")
    cursor_log = project_root / ".cursor" / "debug.log"
    if cursor_log.exists():
        cursor_log.unlink()
        print(f"   ✓ 删除: {cursor_log.relative_to(project_root)}")

    # 4. 归档 output 目录中的旧音频文件
    print("\n4. 归档旧输出文件...")
    archive_dir = project_root / "output" / "archive"
    archive_dir.mkdir(exist_ok=True)

    output_dir = project_root / "output"

    # 要归档的文件模式
    patterns_to_archive = [
        "*.mp3",
        "*.wav",
        "test_*.json",
        "voice_cache.json",
        "step_*.mp3"
    ]

    archived_count = 0
    for pattern in patterns_to_archive:
        for file in output_dir.glob(pattern):
            if file.is_file() and file.name != ".gitkeep":
                dest = archive_dir / file.name
                shutil.move(str(file), str(dest))
                print(f"   ✓ 归档: {file.name}")
                archived_count += 1

    if archived_count == 0:
        print("   (没有需要归档的文件)")

    # 5. 清理空的 example_runs 目录
    print("\n5. 清理空的临时目录...")
    example_runs = project_root / "output" / "example_runs"
    if example_runs.exists() and example_runs.is_dir():
        if not list(example_runs.iterdir()):
            shutil.rmtree(example_runs)
            print(f"   ✓ 删除空目录: example_runs")

    print("\n" + "="*60)
    print("  清理完成！")
    print("="*60)
    print()
    print("已清理:")
    print(f"  - {len(pycache_dirs)} 个 __pycache__ 目录")
    print(f"  - {len(checkpoint_dirs)} 个 .ipynb_checkpoints 目录")
    print(f"  - {archived_count} 个旧输出文件")
    print()


if __name__ == "__main__":
    try:
        cleanup_project()
    except Exception as e:
        print(f"\n❌ 清理失败: {e}")
        import traceback
        traceback.print_exc()
