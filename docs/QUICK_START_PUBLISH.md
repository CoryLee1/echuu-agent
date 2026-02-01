# 🚀 快速发布 ECHUU SDK 到 GitHub

## 一键发布（推荐）

### Windows PowerShell

```powershell
# 1. 运行准备脚本（替换为你的 GitHub 仓库 URL）
.\scripts\prepare_sdk_release.ps1 -RepoUrl "https://github.com/your-username/echuu-python-sdk.git"

# 2. 进入 SDK 目录
cd echuu-sdk-release

# 3. 初始化 Git 并推送
git init
git add .
git commit -m "Initial commit: ECHUU Python SDK v0.1.0"
git remote add origin https://github.com/your-username/echuu-python-sdk.git
git branch -M main
git push -u origin main
```

### Linux/Mac

```bash
# 1. 运行准备脚本（替换为你的 GitHub 仓库 URL）
chmod +x scripts/prepare_sdk_release.sh
./scripts/prepare_sdk_release.sh https://github.com/your-username/echuu-python-sdk.git

# 2. 进入 SDK 目录
cd echuu-sdk-release

# 3. 初始化 Git 并推送
git init
git add .
git commit -m "Initial commit: ECHUU Python SDK v0.1.0"
git remote add origin https://github.com/your-username/echuu-python-sdk.git
git branch -M main
git push -u origin main
```

## 📋 发布前检查清单

- [ ] 在 GitHub 上创建新仓库（例如：`echuu-python-sdk`）
- [ ] 更新脚本中的仓库 URL
- [ ] 检查 `echuu/__init__.py` 中的版本号
- [ ] 检查 `pyproject.toml` 中的版本号和描述
- [ ] 确保 `LICENSE` 文件存在
- [ ] 确保 `echuu/README.md` 完整

## 🔧 修复代码中的路径依赖

在发布前，建议修改 `echuu/live/engine.py` 中的 `_find_project_root()` 函数：

```python
def _find_project_root() -> Path:
    """查找项目根目录（支持独立安装）"""
    import os
    from pathlib import Path
    
    # 尝试查找 echuu-agent 项目根目录（开发环境）
    root = Path.cwd()
    original_root = root
    while root.name != "echuu-agent" and root.parent != root:
        root = root.parent
    
    # 如果找不到，使用用户数据目录（独立安装）
    if root.name != "echuu-agent":
        root = Path.home() / ".echuu"
        root.mkdir(exist_ok=True)
        # 创建必要的子目录
        (root / "data").mkdir(exist_ok=True)
        (root / "output" / "scripts").mkdir(parents=True, exist_ok=True)
    
    return root
```

## 📦 发布到 PyPI（可选）

如果你想发布到 PyPI，让用户可以通过 `pip install echuu` 安装：

```bash
cd echuu-sdk-release

# 安装构建工具
pip install build twine

# 构建分发包
python -m build

# 上传到测试 PyPI（推荐先测试）
python -m twine upload --repository testpypi dist/*

# 测试安装
pip install --index-url https://test.pypi.org/simple/ echuu

# 如果测试通过，上传到正式 PyPI
python -m twine upload dist/*
```

**注意**: 需要先注册 PyPI 账户并配置 API token。

## 🎯 用户安装方式

发布后，用户可以通过以下方式安装：

### 从 GitHub 安装

```bash
pip install git+https://github.com/your-username/echuu-python-sdk.git
```

### 从 PyPI 安装（如果已发布）

```bash
pip install echuu
```

## 📝 更新版本

每次发布新版本时：

1. 更新 `echuu/__init__.py` 中的 `__version__`
2. 更新 `pyproject.toml` 中的 `version`
3. 创建 Git tag: `git tag v0.1.0`
4. 推送 tag: `git push origin v0.1.0`
5. 在 GitHub 上创建 Release

## ✅ 完成！

发布完成后，你的 SDK 就可以被其他人使用了！

查看完整文档: [PUBLISH_SDK.md](./PUBLISH_SDK.md)
