# 数据库设置说明

## 数据库初始化

首次启动后端时，会自动：
1. 创建数据库文件：`echuu-web/backend/data/echuu.db`
2. 创建所有表结构
3. 初始化默认数据：
   - 默认管理员用户：`admin` / `admin123`
   - 默认 LLM 模型（Claude Sonnet 4）
   - OpenAI 模型（GPT-4）

## 手动初始化

如果需要手动初始化数据库：

```bash
cd echuu-web/backend
python migrations/init_data.py
```

## 数据迁移

从 localStorage 迁移角色数据：

```bash
cd echuu-web/backend
python migrations/migrate_localstorage.py
```

然后按照提示提供 localStorage 中的角色数据（JSON格式）。

## 数据库文件位置

- SQLite 数据库：`echuu-web/backend/data/echuu.db`
- 3D 模型文件：`echuu-web/backend/storage/models/`

## 默认账户

- 用户名：`admin`
- 密码：`admin123`
- 角色：管理员

**⚠️ 生产环境请务必修改默认密码！**
