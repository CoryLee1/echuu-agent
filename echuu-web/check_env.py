#!/usr/bin/env python3
"""
环境检查脚本 - 检查运行 ECHUU Web 所需的环境和依赖
"""
import sys
import os
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print("❌ Python 版本过低，需要 Python 3.8+")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_node():
    """检查 Node.js"""
    import subprocess
    try:
        result = subprocess.run(['node', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ Node.js {version}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print("❌ 未找到 Node.js，请安装 Node.js 16+")
    return False

def check_npm():
    """检查 npm"""
    import subprocess
    try:
        result = subprocess.run(['npm', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            version = result.stdout.strip()
            print(f"✅ npm {version}")
            return True
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    print("❌ 未找到 npm")
    return False

def check_python_packages():
    """检查 Python 依赖"""
    required = ['fastapi', 'uvicorn', 'websockets']
    missing = []
    for pkg in required:
        try:
            __import__(pkg)
            print(f"✅ {pkg}")
        except ImportError:
            print(f"❌ {pkg} 未安装")
            missing.append(pkg)
    return len(missing) == 0, missing

def check_env_file():
    """检查 .env 文件"""
    project_root = Path(__file__).resolve().parents[1]
    env_file = project_root / ".env"
    if not env_file.exists():
        print("⚠️  .env 文件不存在，请从 .env.example 复制并配置")
        return False
    
    print("✅ .env 文件存在")
    
    # 检查关键配置
    with open(env_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    has_llm_key = 'ANTHROPIC_API_KEY' in content or 'OPENAI_API_KEY' in content
    has_tts_key = 'DASHSCOPE_API_KEY' in content
    
    if not has_llm_key:
        print("⚠️  未找到 LLM API Key (ANTHROPIC_API_KEY 或 OPENAI_API_KEY)")
    else:
        print("✅ LLM API Key 已配置")
    
    if not has_tts_key:
        print("⚠️  未找到 TTS API Key (DASHSCOPE_API_KEY)")
    else:
        print("✅ TTS API Key 已配置")
    
    return has_llm_key and has_tts_key

def check_frontend_deps():
    """检查前端依赖"""
    frontend_dir = Path(__file__).resolve().parent / "frontend"
    node_modules = frontend_dir / "node_modules"
    if node_modules.exists():
        print("✅ 前端依赖已安装")
        return True
    else:
        print("⚠️  前端依赖未安装，运行 'cd frontend && npm install'")
        return False

def main():
    print("=" * 50)
    print("ECHUU Web 环境检查")
    print("=" * 50)
    print()
    
    all_ok = True
    
    print("[1] Python 环境")
    if not check_python_version():
        all_ok = False
    print()
    
    print("[2] Node.js 环境")
    node_ok = check_node()
    npm_ok = check_npm()
    if not (node_ok and npm_ok):
        all_ok = False
    print()
    
    print("[3] Python 依赖")
    deps_ok, missing = check_python_packages()
    if not deps_ok:
        all_ok = False
        print(f"\n   安装缺失依赖: pip install {' '.join(missing)}")
    print()
    
    print("[4] 环境变量配置")
    if not check_env_file():
        all_ok = False
    print()
    
    print("[5] 前端依赖")
    check_frontend_deps()
    print()
    
    print("=" * 50)
    if all_ok:
        print("✅ 环境检查通过！可以运行 start.bat/start.sh 启动服务")
    else:
        print("❌ 环境检查未通过，请根据上述提示修复问题")
    print("=" * 50)

if __name__ == "__main__":
    main()
