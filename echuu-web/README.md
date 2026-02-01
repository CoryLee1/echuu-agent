# ECHUU Web 控制台

这是一个为 ECHUU Agent 设计的 Web 实时监控与控制台。采用前后端分离架构，支持实时剧本生成监控、AI 推理过程展示、语音自动播放以及实时弹幕互动，并提供角色管理与历史归档。

## 📋 目录结构

```
echuu-web/
├── backend/          # FastAPI 后端服务
│   ├── main.py       # 入口文件
│   ├── database/     # 数据库模型和配置
│   ├── routers/      # API 路由
│   ├── services/     # 业务逻辑
│   └── migrations/   # 数据库迁移脚本
├── frontend/         # React + Vite 前端
│   ├── src/
│   │   ├── pages/    # 页面组件
│   │   ├── api/      # API 客户端
│   │   └── hooks/     # React Hooks
│   └── package.json
├── start.bat         # Windows 启动脚本
├── start.ps1         # PowerShell 启动脚本
└── start.sh          # Linux/Mac 启动脚本
```

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

#### Windows
```bash
# 方式1: 双击 start.bat 文件（在文件资源管理器中）

# 方式2: 在 CMD 中执行
start.bat

# 方式3: 在 PowerShell 中执行（注意需要加 .\）
.\start.bat

# 方式4: 使用 PowerShell 脚本
.\start.ps1
```

#### Linux/Mac
```bash
chmod +x start.sh
./start.sh
```

启动脚本会自动：
1. 检查并安装后端 Python 依赖（如果不存在）
2. 启动后端服务（http://localhost:8000）
3. 检查并安装前端依赖（如果不存在）
4. 启动前端服务（http://localhost:5173）

### 方式二：手动启动

#### 1. 安装后端依赖

```bash
# 方式1: 使用安装脚本（推荐）
cd echuu-web
.\install-deps.ps1  # PowerShell
# 或
install-deps.bat    # CMD

# 方式2: 手动安装
cd echuu-web/..
pip install -r requirements.txt
```

#### 2. 启动后端

```bash
cd echuu-web/backend
python main.py
```

后端将在 `http://localhost:8000` 启动。

#### 3. 启动前端

```bash
cd echuu-web/frontend

# 安装依赖（首次运行）
npm install

# 启动开发服务器
npm run dev
```

前端将在 `http://localhost:5173` 启动。

### 方式三：单独启动前端（如果启动脚本有问题）

如果使用启动脚本时前端没有启动，可以单独启动：

**Windows:**
```bash
# 方式1: 使用单独的前端启动脚本
cd echuu-web
.\start-frontend.bat

# 方式2: 手动启动
cd echuu-web/frontend
npm run dev
```

**PowerShell:**
```powershell
cd echuu-web
.\start-frontend.ps1
```

## 🔐 首次登录

系统会自动创建默认管理员账户：

- **用户名**: `admin`
- **密码**: `admin123`

首次启动时，系统会自动：
1. 创建数据库表
2. 创建默认管理员用户
3. 创建默认 LLM 模型
4. 创建默认角色（六螺、小梅）

## 📱 功能页面

- **`/`** - Overview：总览与快捷统计
- **`/characters`** - 角色管理：创建/编辑角色，配置声音列表
- **`/live`** - 直播控制与监控：启动直播，查看推理过程和实时台词
- **`/history`** - 历史记录：查看和下载历史直播 Session
- **`/settings`** - 系统设置（管理员）：管理 LLM 模型、3D 模型和系统配置

## 🔧 环境配置

### 后端环境变量

在 `echuu-web/backend` 目录创建 `.env` 文件（或使用项目根目录的 `.env`）：

```env
# 数据库配置
DATABASE_URL=sqlite:///./echuu.db
DB_ECHO=False

# JWT 配置
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=1440

# LLM API Keys（根据使用的模型配置）
ANTHROPIC_API_KEY=your-anthropic-api-key
OPENAI_API_KEY=your-openai-api-key

# TTS 配置（Qwen TTS）
QWEN_TTS_API_KEY=your-qwen-tts-api-key
QWEN_TTS_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

### 前端配置

前端 API 基础 URL 在 `frontend/src/api/echuuApi.ts` 中配置：

```typescript
const API_BASE = "http://localhost:8000";
```

如需修改，请更新所有 API 客户端文件中的 `API_BASE`。

## 📊 数据库

系统使用 SQLite 数据库（默认），数据文件位于 `echuu-web/backend/echuu.db`。

### 数据库初始化

首次启动时自动初始化：
- 创建所有表
- 创建默认管理员用户
- 创建默认 LLM 模型
- 创建默认角色（六螺、小梅）

### 手动迁移数据

如果之前使用 localStorage 存储角色数据，可以使用迁移脚本：

```bash
cd echuu-web/backend
python migrations/migrate_localstorage.py
```

## 🎯 核心功能

### 1. 角色管理
- ✅ 创建/编辑/删除角色
- ✅ 为每个角色配置多个声音（TTS）
- ✅ 关联默认 LLM 模型和 3D 模型
- ✅ 用户隔离（每个用户只能看到自己的角色）

### 2. 直播监控
- ✅ 实时显示 AI 推理过程
- ✅ 展示实时生成的台词
- ✅ 自动播放语音（可选）
- ✅ 实时弹幕注入
- ✅ 记忆系统可视化

### 3. 历史归档
- ✅ 查看所有历史直播 Session
- ✅ 下载 Session 数据（JSON + 音频文件）
- ✅ 显示会话状态（进行中/已完成/失败）

### 4. 系统设置（管理员）
- ✅ 管理 LLM 模型（添加/编辑/设置默认）
- ✅ 管理 3D 模型（上传/设置默认）
- ✅ 系统配置管理

## 🔌 API 文档

启动后端后，访问以下地址查看自动生成的 API 文档：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🐛 常见问题

### 1. 端口被占用

如果 8000 或 5173 端口被占用，可以修改：

**后端端口**：修改 `backend/main.py` 中的 `SERVER_PORT`

**前端端口**：修改 `frontend/vite.config.ts` 中的 `server.port`

### 2. 数据库初始化失败

确保：
- Python 依赖已安装（`pip install -r requirements.txt`）
- 数据库目录有写权限
- 没有其他进程占用数据库文件

### 3. 前端无法连接后端

检查：
- 后端是否正常启动（访问 http://localhost:8000/docs 测试）
- CORS 配置是否正确（`backend/config.py`）
- 浏览器控制台是否有错误信息

### 4. 登录后看不到角色

首次登录后，系统会自动创建两个默认角色（六螺、小梅）。如果看不到：
- 检查浏览器控制台是否有错误
- 检查后端日志是否有错误
- 尝试刷新页面

## 📝 开发说明

### 后端技术栈
- FastAPI - Web 框架
- SQLAlchemy - ORM
- Pydantic - 数据验证
- JWT - 身份认证
- WebSocket - 实时通信

### 前端技术栈
- React 18 - UI 框架
- TypeScript - 类型安全
- Tailwind CSS - 样式
- Vite - 构建工具
- Lucide React - 图标库

## 📄 许可证

与主项目保持一致。
