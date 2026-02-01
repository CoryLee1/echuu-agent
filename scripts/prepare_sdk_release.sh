#!/bin/bash
# prepare_sdk_release.sh - 准备 SDK 发布

set -e

REPO_URL="${1:-https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git}"
SDK_DIR="echuu-sdk-release"

echo "🚀 准备 ECHUU SDK 发布..."

# 清理旧目录
if [ -d "$SDK_DIR" ]; then
    echo "清理旧目录..."
    rm -rf "$SDK_DIR"
fi
mkdir -p "$SDK_DIR"

# 复制文件
echo "📦 复制文件..."
cp -r echuu "$SDK_DIR/"
cp pyproject.toml "$SDK_DIR/"
cp LICENSE "$SDK_DIR/"
cp echuu/README.md "$SDK_DIR/README.md"

# 创建 requirements.txt
echo "📝 创建 requirements.txt..."
cat > "$SDK_DIR/requirements.txt" << 'EOF'
# ECHUU SDK 核心依赖
python-dotenv>=1.0.0
anthropic>=0.18.0
openai>=1.12.0
dashscope>=1.25.2
pandas>=2.0.0
numpy>=1.24.0
aiohttp>=3.9.0
asyncio-throttle>=1.0.0
rich>=13.0.0
tqdm>=4.65.0
EOF

# 创建 .gitignore
echo "📝 创建 .gitignore..."
cat > "$SDK_DIR/.gitignore" << 'EOF'
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
.venv/
venv/
ENV/
env/

# IDE
.vscode/
.idea/
*.swp
*.swo

# Testing
.pytest_cache/
.coverage
htmlcov/

# Environment
.env
.env.local

# Output
output/
*.mp3
*.wav
*.zip
EOF

# 更新 pyproject.toml 中的 URL
if [ -n "$REPO_URL" ]; then
    echo "🔧 更新 pyproject.toml..."
    if [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        sed -i '' "s|https://github.com/your-username/echuu-python-sdk|$REPO_URL|g" "$SDK_DIR/pyproject.toml"
        sed -i '' "s|https://github.com/your-repo/echuu-agent|$REPO_URL|g" "$SDK_DIR/pyproject.toml"
    else
        # Linux
        sed -i "s|https://github.com/your-username/echuu-python-sdk|$REPO_URL|g" "$SDK_DIR/pyproject.toml"
        sed -i "s|https://github.com/your-repo/echuu-agent|$REPO_URL|g" "$SDK_DIR/pyproject.toml"
    fi
fi

echo ""
echo "✅ SDK 发布准备完成！"
echo "📁 目录: $SDK_DIR"
echo ""
echo "下一步："
echo "1. cd $SDK_DIR"
echo "2. git init"
echo "3. git add ."
echo "4. git commit -m 'Initial commit: ECHUU Python SDK v0.1.0'"
echo "5. git remote add origin $REPO_URL"
echo "6. git branch -M main"
echo "7. git push -u origin main"
echo ""
echo "💡 提示: 如果要发布到 PyPI，运行:"
echo "   cd $SDK_DIR"
echo "   python -m build"
echo "   python -m twine upload dist/*"
