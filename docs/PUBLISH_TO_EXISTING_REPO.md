# 发布到现有仓库：Echuu-AIVtuber-SDK

你的 GitHub 仓库已经创建：**https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git**

## 🚀 快速发布步骤

### Windows PowerShell

```powershell
# 1. 运行准备脚本（使用你的仓库 URL）
.\scripts\prepare_sdk_release.ps1

# 2. 进入 SDK 目录
cd echuu-sdk-release

# 3. 初始化 Git 并推送到现有仓库
git init
git add .
git commit -m "Initial commit: ECHUU Python SDK v0.1.0"
git remote add origin https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git
git branch -M main
git push -u origin main
```

### Linux/Mac

```bash
# 1. 运行准备脚本
chmod +x scripts/prepare_sdk_release.sh
./scripts/prepare_sdk_release.sh

# 2. 进入 SDK 目录
cd echuu-sdk-release

# 3. 初始化 Git 并推送
git init
git add .
git commit -m "Initial commit: ECHUU Python SDK v0.1.0"
git remote add origin https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git
git branch -M main
git push -u origin main
```

## ⚠️ 注意事项

### 1. 许可证问题

你的仓库使用的是 **Apache-2.0** 许可证，但当前项目使用的是 **MIT** 许可证。

**选项 A**: 保持 Apache-2.0（推荐，如果仓库已设置）
- 脚本会复制项目根目录的 LICENSE 文件
- 如果仓库已有 Apache-2.0 LICENSE，GitHub 会提示冲突
- 可以选择保留 Apache-2.0 或替换为 MIT

**选项 B**: 切换到 MIT
- 在推送前，确保 `echuu-sdk-release/LICENSE` 是 MIT 许可证
- 或者手动替换仓库中的 LICENSE 文件

### 2. 仓库已有 LICENSE 文件

如果仓库已经有 LICENSE 文件，推送时可能会遇到冲突。解决方法：

```bash
# 方法 1: 强制推送（会覆盖现有 LICENSE）
git push -u origin main --force

# 方法 2: 先拉取，合并后再推送
git pull origin main --allow-unrelated-histories
# 解决冲突后
git push -u origin main
```

### 3. 更新仓库描述和主题

发布后，建议在 GitHub 仓库设置中添加：

- **Description**: "AI VTuber Auto-Live System - Generate natural, spontaneous-feeling live broadcast content"
- **Topics**: `vtuber`, `ai`, `streaming`, `tts`, `llm`, `python`, `live-streaming`

## 📝 发布后建议

### 1. 添加 README.md

确保 `echuu-sdk-release/README.md` 包含：
- 项目简介
- 安装说明
- 快速开始示例
- API 文档链接
- 贡献指南

### 2. 创建第一个 Release

```bash
# 创建 tag
git tag v0.1.0
git push origin v0.1.0

# 然后在 GitHub 上创建 Release
# https://github.com/CoryLee1/Echuu-AIVtuber-SDK/releases/new
```

### 3. 添加 GitHub Actions（可选）

创建 `.github/workflows/publish.yml` 用于自动发布到 PyPI：

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: |
          pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
```

## 🔧 如果遇到问题

### 问题：推送被拒绝

```bash
# 如果仓库已有内容，先拉取
git pull origin main --allow-unrelated-histories
# 解决冲突后
git push -u origin main
```

### 问题：LICENSE 冲突

```bash
# 查看仓库中的 LICENSE
# 决定保留哪个许可证
# 然后手动解决冲突或强制推送
```

### 问题：需要更新现有仓库

如果仓库已有内容，可以：

```bash
# 方法 1: 清空仓库后推送（谨慎使用）
git push -u origin main --force

# 方法 2: 合并现有内容
git pull origin main --allow-unrelated-histories
# 手动合并后
git push -u origin main
```

## ✅ 完成检查清单

- [ ] 运行准备脚本
- [ ] 检查 LICENSE 文件（Apache-2.0 vs MIT）
- [ ] 初始化 Git 仓库
- [ ] 推送到 GitHub
- [ ] 添加仓库描述和主题
- [ ] 创建第一个 Release
- [ ] （可选）设置 GitHub Actions

## 📦 用户安装方式

发布后，用户可以通过以下方式安装：

```bash
# 从 GitHub 安装
pip install git+https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git

# 或指定版本
pip install git+https://github.com/CoryLee1/Echuu-AIVtuber-SDK.git@v0.1.0
```

---

**仓库地址**: https://github.com/CoryLee1/Echuu-AIVtuber-SDK
