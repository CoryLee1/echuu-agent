# prepare_sdk_release.ps1 - 准备 SDK 发布

param(
    [string]$RepoUrl = "https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git"
)

$SDK_DIR = "echuu-sdk-release"

Write-Host "🚀 准备 ECHUU SDK 发布..." -ForegroundColor Cyan

# 清理旧目录
if (Test-Path $SDK_DIR) {
    Write-Host "清理旧目录..." -ForegroundColor Yellow
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
"@ | Out-File -FilePath "$SDK_DIR\requirements.txt" -Encoding utf8

# 创建 .gitignore
Write-Host "📝 创建 .gitignore..." -ForegroundColor Yellow
@"
# Python
__pycache__/
*.py[cod]
*`$py.class
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
"@ | Out-File -FilePath "$SDK_DIR\.gitignore" -Encoding utf8

# 更新 pyproject.toml 中的 URL
if ($RepoUrl) {
    Write-Host "🔧 更新 pyproject.toml..." -ForegroundColor Yellow
    $content = Get-Content "$SDK_DIR\pyproject.toml" -Raw
    $content = $content -replace "https://github.com/your-username/echuu-python-sdk", $RepoUrl
    $content = $content -replace "https://github.com/your-repo/echuu-agent", $RepoUrl
    $content | Out-File -FilePath "$SDK_DIR\pyproject.toml" -Encoding utf8 -NoNewline
}

Write-Host ""
Write-Host "✅ SDK 发布准备完成！" -ForegroundColor Green
Write-Host "📁 目录: $SDK_DIR" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步：" -ForegroundColor Yellow
Write-Host "1. cd $SDK_DIR"
Write-Host "2. git init"
Write-Host "3. git add ."
Write-Host "4. git commit -m 'Initial commit: ECHUU Python SDK v0.1.0'"
Write-Host "5. git remote add origin $RepoUrl"
Write-Host "6. git branch -M main"
Write-Host "7. git push -u origin main"
Write-Host ""
Write-Host "💡 提示: 如果要发布到 PyPI，运行:" -ForegroundColor Cyan
Write-Host "   cd $SDK_DIR"
Write-Host "   python -m build"
Write-Host "   python -m twine upload dist/*"
