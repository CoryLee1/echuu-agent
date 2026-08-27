# 客户端对接自检说明（弹幕回复 + 开播）

用本文逐项检查你的**前端/客户端**是否具备与后端对应的设施，确保：  
① 能正确开播并收到剧本/步骤/音频；② **用户发弹幕后 AI 会回复**。

---

## 一、先确认你接的是哪个后端

| 后端 | 典型地址 | 说明 |
|------|----------|------|
| **Workflow 控制台** | `http://localhost:8000`（workflow/backend/app.py） | 多房间、room_id、WebSocket 带 `room_id` 查询参数 |
| **echuu-web** | `http://localhost:8xxx`（echuu-web/backend） | 需登录、角色/配置来自数据库，弹幕用 POST 注入 |

下面分别给出两套自检项。

---

## 二、Workflow 后端（多房间）— 客户端自检

### 2.1 房间与开播

- [ ] **创建房间**  
  - 调用 `POST /api/room`  
  - 响应中保存 `room_id` 和 `owner_token`（仅房主持有，用于开播）

- [ ] **WebSocket 连接必须带 room_id**  
  - 连接 URL：`/ws?room_id=<room_id>`  
  - 未传 `room_id` 会 4000 关闭；`room_id` 不存在会 4004

- [ ] **开播请求**  
  - 调用 `POST /api/start`，Body 为 JSON，**必须包含**：  
    - `room_id`、`owner_token`（与创建房间拿到的一致）  
    - 以及 `character_name`、`persona`、`background`、`topic`、`danmaku`（初始弹幕列表，可选）  
    - 可选：`voice`（如 `"Cherry"`）、`language`（如 `"zh"`/`"en"`/`"ja"`）

- [ ] **状态与在线人数**  
  - `GET /api/status?room_id=<room_id>` 获取当前直播状态（is_running、current_step、stream_state 等）  
  - `GET /api/online-count?room_id=<room_id>` 获取当前房间在线人数  

### 2.2 弹幕（用户发弹幕 → AI 会回复）

- [ ] **通过 WebSocket 发弹幕**  
  - 连接同一房间的 WebSocket 后，向服务端发送一条 JSON 文本消息：  
    ```json
    { "type": "danmaku", "text": "用户输入的弹幕内容", "user": "用户名或昵称" }
    ```  
  - 服务端会把这条弹幕加入该房间的 `live_danmaku`，并在**下一表演步**被引擎消费，AI 会据此生成回复并合进当句台词/语音。

- [ ] **通过 HTTP 发弹幕（可选）**  
  - 调用 `POST /api/danmaku`，Body 为 JSON：  
    ```json
    { "text": "弹幕内容", "user": "用户名", "room_id": "<当前房间的 room_id>" }
    ```  
  - 同样会进入该房间的实时弹幕队列，下一步会被回复。

- [ ] **前端是否展示「弹幕」并发送到上述其一**  
  - 例如：输入框 + 发送按钮 → 要么通过已连接的 WebSocket 发 `{ "type": "danmaku", "text", "user" }`，要么调 `POST /api/danmaku`（带 `room_id`）。  
  - 二者至少实现其一，AI 才能收到并回复。

### 2.3 收流与展示

- [ ] **订阅 WebSocket 消息**  
  - 连接 `/ws?room_id=xxx` 后，能收到服务端推送的 JSON，例如：  
    - `type: "system"` — 连接成功  
    - `type: "user_count"` — 在线人数  
    - `type: "danmaku"` — 有人发弹幕（可用来刷新弹幕列表）  
    - `type: "info"` / `type: "script_ready"` / `type: "step"` / `type: "success"` / `type: "error"` 等 — 开播与表演进度  

- [ ] **step 消息中的 speech / audio**  
  - `type: "step"` 的 payload 中包含 `speech`（文本）和 `audio_b64`（Base64 音频），客户端需能播放/展示，才能听到「带弹幕回复」的整句内容。

- [ ] **可选：cursor**  
  - 若有多人光标需求，可发 `{ "type": "cursor", "x": number, "y": number }`，服务端会向同房间其他人广播。

---

## 三、echuu-web 后端 — 客户端自检

### 3.1 直播与弹幕

- [ ] **开播**  
  - 按 echuu-web 现有流程调用开播接口（如 `POST /start` 等，带角色、配置），并建立其 WebSocket/SSE 等收流方式。

- [ ] **发送实时弹幕**  
  - 调用 `POST /danmaku?text=<内容>&user=<用户名>`（或按实际路由的 query/body 传参）。  
  - 仅在**直播已运行**时有效；弹幕会被注入到当前引擎的 `danmaku_queue`，**下一步**表演时会参与决策并生成回复。

- [ ] **前端是否有「发弹幕」入口**  
  - 例如输入框 + 发送 → 请求上述 `POST /danmaku`，确保直播进行中时能成功调用。

---

## 四、快速核对表（仅关心「弹幕会不会被回复」）

| 后端 | 客户端必须具备 | 否则 |
|------|----------------|------|
| **Workflow** | 1）WebSocket 连接带 `room_id`<br>2）能发 `{ "type": "danmaku", "text", "user" }` 或调 `POST /api/danmaku` 且带 `room_id` | 弹幕进不了房间队列，AI 不会回复 |
| **echuu-web** | 直播进行中能调 `POST /danmaku`（带 text、user） | 弹幕进不了引擎队列，AI 不会回复 |

---

## 五、自检通过标准

- **Workflow**：在已开播的房间内，用 WebSocket 或 POST 发一条弹幕，在**下一个** step 的 `speech`/语音里能听到或看到 AI 对这条弹幕的回应（如欢迎、接话等）。  
- **echuu-web**：直播中调用 `POST /danmaku` 发一条弹幕，在接下来的表演步中能听到/看到 AI 的回复内容。

若你愿意，我可以再根据你当前前端技术栈（例如 React + 某 WebSocket 库）写一段「最小可用的发弹幕示例代码」方便你贴到项目里做一次联调。
