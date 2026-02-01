# ECHUU Web 后端

## 目录结构

```
backend/
├── main.py              # 应用入口，FastAPI 应用初始化
├── config.py            # 配置管理（路径、CORS、服务器配置等）
├── models.py            # 数据模型定义（Pydantic 模型）
├── state.py             # 全局状态管理（WebSocket 连接、引擎状态等）
├── routers/             # 路由模块
│   ├── __init__.py
│   ├── api.py          # REST API 路由
│   └── websocket.py    # WebSocket 路由
└── services/            # 业务逻辑服务层
    ├── __init__.py
    └── live_service.py # 直播引擎服务
```

## 模块说明

### `main.py`
- FastAPI 应用入口
- 配置中间件（CORS）
- 挂载静态资源
- 注册路由

### `config.py`
- 项目路径配置
- CORS 配置
- 服务器配置（host、port）

### `models.py`
- `CharacterConfig`: 角色配置模型
- `LiveConfig`: 直播配置模型
- `SessionInfo`: Session 信息模型
- `StatusResponse`: 状态响应模型

### `state.py`
- `GlobalStateManager`: 全局状态管理器
  - WebSocket 连接管理
  - 引擎状态管理
  - 消息广播

### `routers/api.py`
REST API 端点：
- `GET /api/history`: 获取历史 Session 列表
- `GET /api/status`: 获取当前直播状态
- `GET /api/download/{session_id}`: 下载 Session 打包文件
- `POST /api/danmaku`: 发送实时弹幕
- `POST /api/start`: 启动直播

### `routers/websocket.py`
WebSocket 端点：
- `WS /ws`: WebSocket 连接端点

### `services/live_service.py`
业务逻辑服务：
- `LiveService.run_live_engine()`: 运行直播引擎任务
- `LiveService.inject_danmaku()`: 注入实时弹幕

## 运行

```bash
# 方式1: 直接运行（从 backend 目录）
cd echuu-web/backend
python main.py

# 方式2: 使用 uvicorn（从 backend 目录）
cd echuu-web/backend
uvicorn main:app --host 0.0.0.0 --port 8000

# 方式3: 作为模块运行（从项目根目录）
python -m echuu-web.backend.main
```

## 重构说明

### 重构前
- 所有代码都在一个 `main.py` 文件中（229行）
- 配置、模型、状态、路由、业务逻辑混在一起
- 难以维护和扩展

### 重构后
- **模块化设计**：按功能拆分为独立模块
- **关注点分离**：配置、模型、状态、路由、服务各司其职
- **易于扩展**：新增功能只需在对应模块添加代码
- **兼容性**：支持相对导入和绝对导入，可灵活运行

## 设计原则

1. **关注点分离**: 配置、模型、状态、路由、服务各司其职
2. **可维护性**: 代码模块化，易于理解和修改
3. **可扩展性**: 新增功能只需在对应模块添加代码
4. **类型安全**: 使用 Pydantic 模型进行数据验证
