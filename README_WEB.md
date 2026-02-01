# ECHUU Agent - Web 控制台

这是一个为 ECHUU Agent 设计的 Web 实时监控与控制台。采用前后端分离架构，支持实时剧本生成监控、AI 推理过程展示、语音自动播放以及实时弹幕互动，并提供角色管理与历史归档。

## 目录结构

- `echuu-web/backend/`: 基于 FastAPI 的后端服务，负责调用引擎并提供 WebSocket 通讯。
- `echuu-web/frontend/`: 基于 React + Tailwind + Lucide 图标的前端展示层。

## 后端接口说明 (FastAPI)

### REST API

- **`POST /api/start`**: 启动一场直播表演。
  - **输入**: `CharacterConfig` (姓名, 人设, 背景) 和 `LiveConfig` (话题, 初始弹幕, TTS配置)。
- **`GET /api/status`**: 获取当前引擎运行状态。
- **`POST /api/danmaku`**: 在直播过程中实时注入弹幕，引导 Agent 表演。
- **`GET /api/history`**: 获取历史直播 Session 列表。
- **`GET /api/download/{session_id}`**: 一键打包下载指定 Session 的剧本 JSON 和所有音频文件。

### WebSocket (`ws://localhost:8000/ws`)

后端通过 WebSocket 实时推送以下类型的数据：

- `reasoning`: AI 的创作推理过程（Phase -1 到 Phase 3）。
- `step`: 每一轮表演的具体内容，包括：
  - `speech`: 台词
  - `stage`: 当前叙事阶段 (Hook/Climax 等)
  - `inner_monologue`: 内心独白
  - `audio_url`: 该句语音的静态访问路径
  - `memory_snapshot`: 此时此刻的 AI 记忆状态（剧情点、承诺、情绪趋势）
- `info/ready/finish`: 系统状态通知。

## 前端功能介绍 (React)

- **推理引擎监视器**: 实时展示 AI 是如何确定故事内核、反常点以及规划情节的。
- **记忆系统可视化**: 实时同步展示 Agent 脑海中已经提到的关键剧情点和待兑现的承诺。
- **自动语音流**: 开启语音开关后，前端将按顺序自动播放每一句生成的语音。
- **互动控制面板**: 底部输入框支持实时注入弹幕，模拟观众互动。
- **角色管理**: 创建/编辑 VTuber 角色，便于复用人设。
- **历史归档**: 记录每次直播 Session，并支持打包下载。

## 启动指南

### 后端
```bash
cd echuu-web/backend
pip install fastapi uvicorn python-multipart websockets
python main.py
```

### 前端
```bash
cd echuu-web/frontend
npm install
npm run dev
```

访问 [http://localhost:5173](http://localhost:5173) 开启调试。

## 前端页面导航

- `/` Overview：总览与快捷统计
- `/characters` 角色管理
- `/live` 直播控制与监控
- `/history` 历史记录与下载
