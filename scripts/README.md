# 发布脚本说明

## prepare_sdk_release.ps1 / prepare_sdk_release.sh

准备 ECHUU SDK 独立发布的脚本。

### 使用方法

**PowerShell (Windows)**:
```powershell
.\scripts\prepare_sdk_release.ps1 -RepoUrl "https://github.com/your-username/echuu-python-sdk.git"
```

**Bash (Linux/Mac)**:
```bash
chmod +x scripts/prepare_sdk_release.sh
./scripts/prepare_sdk_release.sh https://github.com/your-username/echuu-python-sdk.git
```

### 功能

1. 创建独立的 SDK 目录 `echuu-sdk-release/`
2. 复制必要的文件（echuu 模块、pyproject.toml、LICENSE、README.md）
3. 创建独立的 `requirements.txt`（仅包含 SDK 核心依赖）
4. 创建独立的 `.gitignore`
5. 更新 `pyproject.toml` 中的仓库 URL

### 输出

脚本会在项目根目录创建 `echuu-sdk-release/` 目录，包含所有发布所需的文件。

### 后续步骤

1. 进入 SDK 目录: `cd echuu-sdk-release`
2. 初始化 Git: `git init`
3. 添加文件: `git add .`
4. 提交: `git commit -m 'Initial commit: ECHUU Python SDK v0.1.0'`
5. 添加远程仓库: `git remote add origin <your-repo-url>`
6. 推送: `git push -u origin main`

### 发布到 PyPI（可选）

```bash
cd echuu-sdk-release
pip install build twine
python -m build
python -m twine upload dist/*
```
