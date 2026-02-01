# 发布 ECHUU SDK 到 GitHub 指南

本指南将帮助你将 `echuu` 模块作为独立的 Python SDK 发布到 GitHub。

## 📋 准备工作

### 1. 创建独立的 GitHub 仓库

1. 在 GitHub 上创建新仓库（例如：`echuu-python-sdk`）
2. 设置仓库为 Public（如果要发布到 PyPI）或 Private（仅内部使用）
3. 记录仓库 URL（例如：`https://github.com/your-username/echuu-python-sdk`）

### 2. 准备发布文件

确保以下文件已准备好：
- ✅ `pyproject.toml` - 包配置（已存在）
- ✅ `LICENSE` - MIT 许可证（已存在）
- ✅ `echuu/README.md` - SDK 文档（已存在）
- ✅ `echuu/py.typed` - 类型提示标记（已存在）

---

## 🚀 发布步骤

### 步骤 1: 创建独立的 SDK 目录结构

```bash
# 在项目根目录执行
mkdir -p echuu-sdk-release
cd echuu-sdk-release

# 复制 echuu 模块
cp -r ../echuu .

# 复制必要文件
cp ../pyproject.toml .
cp ../LICENSE .
cp ../echuu/README.md ./README.md

# 创建独立的 requirements.txt（仅 SDK 依赖）
cat > requirements.txt << EOF
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

# 创建独立的 .gitignore
cat > .gitignore << EOF
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
```

### 步骤 2: 更新 pyproject.toml

更新 `pyproject.toml` 中的仓库 URL：

```toml
[project.urls]
Homepage = "https://github.com/your-username/echuu-python-sdk"
Documentation = "https://github.com/your-username/echuu-python-sdk#readme"
Repository = "https://github.com/your-username/echuu-python-sdk"
Issues = "https://github.com/your-username/echuu-python-sdk/issues"
```

### 步骤 3: 修复代码中的路径依赖

`echuu/live/engine.py` 中的 `_find_project_root()` 函数需要修改，使其在独立安装时也能正常工作：

```python
def _find_project_root() -> Path:
    """查找项目根目录（支持独立安装）"""
    # 如果作为包安装，使用用户数据目录
    import os
    from pathlib import Path
    
    # 尝试查找 echuu-agent 项目根目录
    root = Path.cwd()
    while root.name != "echuu-agent" and root.parent != root:
        root = root.parent
    
    # 如果找不到，使用用户数据目录
    if root.name != "echuu-agent":
        root = Path.home() / ".echuu"
        root.mkdir(exist_ok=True)
    
    return root
```

### 步骤 4: 初始化 Git 仓库

```bash
cd echuu-sdk-release

# 初始化 Git
git init
git add .
git commit -m "Initial commit: ECHUU Python SDK v0.1.0"

# 添加远程仓库
git remote add origin https://github.com/your-username/echuu-python-sdk.git
git branch -M main
git push -u origin main
```

### 步骤 5: 创建 GitHub Release

1. 在 GitHub 仓库页面，点击 "Releases" → "Create a new release"
2. 填写版本号（例如：`v0.1.0`）
3. 填写 Release 标题和描述
4. 点击 "Publish release"

---

## 📦 发布到 PyPI（可选）

如果你想让用户可以通过 `pip install echuu` 安装：

### 1. 安装构建工具

```bash
pip install build twine
```

### 2. 构建分发包

```bash
cd echuu-sdk-release
python -m build
```

这会生成 `dist/` 目录，包含：
- `echuu-0.1.0.tar.gz` (源码包)
- `echuu-0.1.0-py3-none-any.whl` (wheel 包)

### 3. 上传到 PyPI

#### 测试 PyPI（推荐先测试）

```bash
# 上传到测试 PyPI
python -m twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ echuu
```

#### 正式 PyPI

```bash
# 上传到正式 PyPI
python -m twine upload dist/*
```

**注意**: 需要先注册 PyPI 账户并配置 API token。

---

## 🔧 自动化脚本

创建一个自动化发布脚本 `scripts/prepare_sdk_release.sh`：

```bash
#!/bin/bash
# prepare_sdk_release.sh - 准备 SDK 发布

set -e

SDK_DIR="echuu-sdk-release"
REPO_URL="${1:-https://github.com/your-username/echuu-python-sdk.git}"

echo "🚀 准备 ECHUU SDK 发布..."

# 清理旧目录
rm -rf "$SDK_DIR"
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
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env
EOF

# 更新 pyproject.toml 中的 URL（如果需要）
if [ -n "$REPO_URL" ]; then
    echo "🔧 更新 pyproject.toml..."
    sed -i.bak "s|https://github.com/your-repo/echuu-agent|$REPO_URL|g" "$SDK_DIR/pyproject.toml"
    rm "$SDK_DIR/pyproject.toml.bak"
fi

echo "✅ SDK 发布准备完成！"
echo "📁 目录: $SDK_DIR"
echo ""
echo "下一步："
echo "1. cd $SDK_DIR"
echo "2. git init"
echo "3. git add ."
echo "4. git commit -m 'Initial commit'"
echo "5. git remote add origin $REPO_URL"
echo "6. git push -u origin main"
```

Windows PowerShell 版本 `scripts/prepare_sdk_release.ps1`：

```powershell
# prepare_sdk_release.ps1 - 准备 SDK 发布

param(
    [string]$RepoUrl = "https://github.com/your-username/echuu-python-sdk.git"
)

$SDK_DIR = "echuu-sdk-release"

Write-Host "🚀 准备 ECHUU SDK 发布..." -ForegroundColor Cyan

# 清理旧目录
if (Test-Path $SDK_DIR) {
    Remove-Item -Recurse -Force $SDK_DIR
}
New-Item -ItemType Directory -Path $SDK_DIR | Out-Null

# 复制文件
Write-Host "📦 复制文件..." -ForegroundColor Yellow
Copy-Item -Recurse echuu "$SDK_DIR\echuu"
Copy-Item pyproject.toml "$SDK_DIR\"
Copy-Item LICENSE "$SDK_DIR\"
Copy-Item echuu\README.md "$SDK_DIR\README.md"

# 创建 requirements.txt
Write-Host "📝 创建 requirements.txt..." -ForegroundColor Yellow
@"
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
"@ | Out-File -FilePath "$SDK_DIR\requirements.txt" -Encoding utf8

# 创建 .gitignore
Write-Host "📝 创建 .gitignore..." -ForegroundColor Yellow
@"
__pycache__/
*.py[cod]
*.egg-info/
dist/
build/
.venv/
venv/
.env
"@ | Out-File -FilePath "$SDK_DIR\.gitignore" -Encoding utf8

# 更新 pyproject.toml 中的 URL
if ($RepoUrl) {
    Write-Host "🔧 更新 pyproject.toml..." -ForegroundColor Yellow
    $content = Get-Content "$SDK_DIR\pyproject.toml" -Raw
    $content = $content -replace "https://github.com/your-repo/echuu-agent", $RepoUrl
    $content | Out-File -FilePath "$SDK_DIR\pyproject.toml" -Encoding utf8 -NoNewline
}

Write-Host "✅ SDK 发布准备完成！" -ForegroundColor Green
Write-Host "📁 目录: $SDK_DIR" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. cd $SDK_DIR"
Write-Host "2. git init"
Write-Host "3. git add ."
Write-Host "4. git commit -m 'Initial commit'"
Write-Host "5. git remote add origin $RepoUrl"
Write-Host "6. git push -u origin main"
```

---

## 📝 更新 README.md

确保 `README.md` 包含：

1. **安装说明**:
   ```bash
   # 从 GitHub 安装
   pip install git+https://github.com/your-username/echuu-python-sdk.git
   
   # 或从 PyPI 安装（如果已发布）
   pip install echuu
   ```

2. **快速开始示例**
3. **API 文档链接**
4. **贡献指南**
5. **许可证信息**

---

## 🔄 版本更新流程

每次发布新版本时：

1. 更新 `echuu/__init__.py` 中的 `__version__`
2. 更新 `pyproject.toml` 中的 `version`
3. 更新 `CHANGELOG.md`（如果存在）
4. 创建 Git tag: `git tag v0.1.0`
5. 推送到 GitHub: `git push origin v0.1.0`
6. 创建 GitHub Release
7. （可选）构建并上传到 PyPI

---

## ✅ 检查清单

发布前检查：

- [ ] 所有代码已测试
- [ ] `__version__` 已更新
- [ ] `pyproject.toml` 中的 URL 已更新
- [ ] `README.md` 完整且准确
- [ ] `LICENSE` 文件存在
- [ ] `.gitignore` 配置正确
- [ ] 没有硬编码的路径依赖
- [ ] 所有依赖都在 `requirements.txt` 和 `pyproject.toml` 中

---

## 🆘 常见问题

### Q: 如何让 SDK 不依赖项目根目录的数据文件？

A: 修改 `EchuuLiveEngine.__init__()` 中的路径查找逻辑，使用可选的数据路径参数，或者使用用户数据目录。

### Q: 如何让 SDK 支持可选的示例数据？

A: 将示例数据作为可选依赖或单独的数据包发布，用户可以选择性安装。

### Q: 如何添加 CI/CD 自动发布？

A: 使用 GitHub Actions，在创建 tag 时自动构建并发布到 PyPI。

---

## 📚 参考资源

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Upload Guide](https://packaging.python.org/guides/distributing-packages-using-setuptools/)
- [GitHub Releases](https://docs.github.com/en/repositories/releasing-projects-on-github)

---

*最后更新: 2026-01-30*
