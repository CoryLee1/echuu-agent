# 修复发布问题指南

## 遇到的问题

1. ✅ **LICENSE 文件不存在** - 已修复脚本
2. ✅ **嵌入的 git 仓库警告** - 已移除
3. ⚠️ **推送被拒绝** - 需要处理远程仓库冲突

## 解决方案

### 问题 1: LICENSE 文件不存在

脚本已更新，现在会检查 LICENSE 文件是否存在，如果不存在会跳过。

### 问题 2: 嵌入的 git 仓库

已从缓存中移除，现在需要重新添加文件：

```powershell
cd echuu-sdk-release
git add echuu/Echuu-AI-Vtuber-SDK
git commit -m "Add Echuu-AI-Vtuber-SDK files"
```

### 问题 3: 推送被拒绝（远程仓库有内容）

远程仓库已经有 LICENSE 文件（Apache-2.0），需要合并或覆盖。

#### 方案 A: 合并远程内容（推荐）

```powershell
cd echuu-sdk-release

# 拉取远程内容
git pull origin main --allow-unrelated-histories

# 如果有冲突，解决冲突后：
git add .
git commit -m "Merge remote LICENSE"
git push -u origin main
```

#### 方案 B: 强制推送（会覆盖远程 LICENSE）

⚠️ **注意**: 这会覆盖远程仓库的 Apache-2.0 LICENSE

```powershell
cd echuu-sdk-release

# 强制推送（如果确定要覆盖）
git push -u origin main --force
```

#### 方案 C: 保留 Apache-2.0 LICENSE

如果你想保留远程仓库的 Apache-2.0 许可证：

```powershell
cd echuu-sdk-release

# 拉取远程内容
git pull origin main --allow-unrelated-histories

# 如果有 LICENSE 冲突，选择保留远程的 Apache-2.0
# 或者手动删除本地的 LICENSE（如果存在）
if (Test-Path LICENSE) {
    git rm LICENSE
}

git add .
git commit -m "Keep Apache-2.0 license from remote"
git push -u origin main
```

## 完整修复步骤

```powershell
cd echuu-sdk-release

# 1. 添加被移除的文件
git add echuu/Echuu-AI-Vtuber-SDK
git commit -m "Add Echuu-AI-Vtuber-SDK files"

# 2. 拉取远程内容
git pull origin main --allow-unrelated-histories

# 3. 如果有 LICENSE 冲突：
#    - 如果想保留 Apache-2.0: 删除本地 LICENSE，保留远程的
#    - 如果想使用 MIT: 保留本地的，覆盖远程的

# 4. 解决冲突后提交
git add .
git commit -m "Merge with remote repository"

# 5. 推送
git push -u origin main
```

## 许可证选择建议

### Apache-2.0 vs MIT

- **Apache-2.0**: 更严格，包含专利授权条款
- **MIT**: 更简单，更宽松

**建议**: 如果你的仓库已经使用 Apache-2.0，建议保持一致，保留 Apache-2.0。

## 如果网络连接失败

如果 `git pull` 失败（网络问题），可以：

1. **手动下载 LICENSE**:
   - 访问 https://github.com/CoryLee1/Echuu-AIVtuber-SDK/blob/main/LICENSE
   - 复制内容到本地 `LICENSE` 文件

2. **或者直接强制推送**（如果确定要覆盖）:
   ```powershell
   git push -u origin main --force
   ```

## 验证发布

推送成功后，访问：
https://github.com/CoryLee1/Echuu-AIVtuber-SDK

检查：
- [ ] 所有文件都已上传
- [ ] README.md 显示正确
- [ ] LICENSE 文件存在
- [ ] 没有嵌入的 git 仓库警告
