# 启动后端服务指南

## 🚀 快速启动

### 方式一：使用启动脚本（推荐）

```powershell
# 在 echuu-web 目录下
cd d:\vtuberclip\echuu-agent\echuu-web
.\start.ps1
```

这会自动：
1. 检查并安装依赖
2. 启动后端服务（新窗口）
3. 启动前端服务（新窗口）

### 方式二：手动启动后端

```powershell
# 1. 进入后端目录
cd d:\vtuberclip\echuu-agent\echuu-web\backend

# 2. 确保依赖已安装
pip install -r ../../requirements.txt

# 3. 启动服务
python main.py
```

### 方式三：使用 uvicorn

```powershell
cd d:\vtuberclip\echuu-agent\echuu-web\backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

## ⚠️ 常见问题

### 问题 1: bcrypt 版本错误

**错误信息**:
```
AttributeError: module 'bcrypt' has no attribute '__about__'
```

**解决方法**:
```powershell
pip uninstall bcrypt -y
pip install "bcrypt>=4.0.0,<5.0.0"
```

### 问题 2: 依赖未安装

**错误信息**:
```
ModuleNotFoundError: No module named 'fastapi'
```

**解决方法**:
```powershell
cd d:\vtuberclip\echuu-agent
pip install -r requirements.txt
```

### 问题 3: 端口被占用

**错误信息**:
```
ERROR: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000): only one usage of each socket address (protocol/network address/port) is normally permitted
```

**解决方法**:

**方法一：停止占用端口的进程（推荐）**

```powershell
# 1. 查找占用 8000 端口的进程 PID
netstat -ano | findstr ":8000" | findstr "LISTENING"

# 输出示例：
# TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       40896
# 最后的数字就是进程 ID (PID)

# 2. 停止该进程（替换 40896 为实际的 PID）
taskkill /PID 40896 /F

# 3. 验证端口已释放
netstat -ano | findstr ":8000" | findstr "LISTENING"
# 如果没有输出，说明端口已释放

# 4. 重新启动后端
python main.py
```

**方法二：使用不同的端口**

如果不想停止现有进程，可以修改后端配置使用其他端口：

```powershell
# 使用 uvicorn 指定不同端口
uvicorn main:app --host 0.0.0.0 --port 8001 --reload
```

然后记得更新前端配置中的 API 地址。

### 问题 4: 数据库初始化失败

**错误信息**:
```
数据库初始化警告: ...
```

**解决方法**:
- 检查 `backend/data/` 目录权限
- 删除旧的数据库文件重新初始化（如果数据不重要）
- 检查 SQLAlchemy 版本兼容性

## ✅ 验证后端是否启动成功

### 方法 1: 访问 API 文档

打开浏览器访问：
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

如果能看到 API 文档页面，说明后端已成功启动。

### 方法 2: 测试 API 端点

```powershell
# 测试状态端点
Invoke-WebRequest -Uri "http://localhost:8000/api/status" -UseBasicParsing

# 应该返回 JSON 响应
```

### 方法 3: 检查端口监听

```powershell
netstat -ano | findstr ":8000"
```

应该看到类似：
```
TCP    0.0.0.0:8000           0.0.0.0:0              LISTENING       12345
```

## 📝 启动后的日志

正常启动后，你应该看到：

```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ 创建默认管理员用户: admin / admin123
✅ 创建默认LLM模型
✅ 创建默认角色: 六螺
✅ 创建默认角色: 小梅
✅ 数据库初始化完成
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## 🔧 环境变量配置

确保在项目根目录或 `backend` 目录有 `.env` 文件：

```env
# LLM API Key
ANTHROPIC_API_KEY=your_key_here
# 或
OPENAI_API_KEY=your_key_here

# TTS API Key
DASHSCOPE_API_KEY=your_key_here

# 数据库配置（可选）
DATABASE_URL=sqlite:///./data/echuu.db

# JWT 配置（可选）
SECRET_KEY=your-secret-key-change-in-production
```

## 🎯 下一步

后端启动成功后：

1. **访问前端**: http://localhost:5173
2. **登录**: 使用默认账户 `admin` / `admin123`
3. **开始使用**: 创建角色、启动直播等

## 📞 需要帮助？

如果遇到其他问题：
1. 查看后端窗口的错误信息
2. 检查 `backend/data/` 目录的日志文件
3. 查看 FastAPI 的自动文档: http://localhost:8000/docs
