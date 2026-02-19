import os
import sys
import json
import base64
import asyncio
import traceback
import uuid
import secrets
from typing import List, Optional, Dict
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

# 将项目根目录添加到路径
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from echuu.live.engine import EchuuLiveEngine

app = FastAPI(title="ECHUU Agent Control Panel")

# 允许跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
SCRIPTS_DIR = PROJECT_ROOT / "output" / "scripts"
SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(SCRIPTS_DIR)), name="audio")

# 数据模型
class LiveRequest(BaseModel):
    character_name: str = "六螺"
    persona: str = "一个性格古怪、喜欢碎碎念的虚拟主播"
    background: str = "正在直播，和观众聊天"
    topic: str = "关于上司的超劲爆八卦"
    danmaku: List[str] = ["主播快说！", "真的假的？", "这也太离谱了"]
    voice: str = "Cherry"  # TTS 音色，与前端侧栏「声音」一致
    language: str = ""  # 留空则从 topic/persona 检测；"en"/"zh"/"ja" 则强制该语言

class DanmakuRequest(BaseModel):
    text: str
    user: str = "观众"


class RoomState:
    """单个直播间的状态，按 room_id 隔离。"""
    def __init__(self, room_id: str, owner_token: str):
        self.room_id = room_id
        self.owner_token = owner_token
        self.is_running = False
        self.current_step = 0
        self.total_steps = 0
        self.current_stage = ""
        self.stream_state = "idle"
        self.info_message = ""
        self.error_message = ""
        self.active_connections: List[WebSocket] = []
        self.connection_ids: dict = {}  # WebSocket -> viewer_id (用于 cursor 广播)
        self.live_danmaku: List[dict] = []

    async def broadcast(self, data: dict):
        clean_data = json.loads(json.dumps(data, default=str))
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(clean_data)
            except Exception:
                dead.append(connection)
        for c in dead:
            if c in self.active_connections:
                self.active_connections.remove(c)
            self.connection_ids.pop(c, None)

    async def broadcast_to_others(self, exclude: WebSocket, data: dict):
        """向房间内除 exclude 外的所有连接广播（用于 cursor，避免发给自己）。"""
        clean_data = json.loads(json.dumps(data, default=str))
        dead = []
        for connection in self.active_connections:
            if connection is exclude:
                continue
            try:
                await connection.send_json(clean_data)
            except Exception:
                dead.append(connection)
        for c in dead:
            if c in self.active_connections:
                self.active_connections.remove(c)
            self.connection_ids.pop(c, None)

    async def broadcast_user_count(self):
        await self.broadcast({"type": "user_count", "count": len(self.active_connections)})


# 所有直播间：room_id -> RoomState
rooms: Dict[str, RoomState] = {}
LOBBY_ROOM_ID = "lobby"


def get_room(room_id: str) -> Optional[RoomState]:
    return rooms.get(room_id)


def get_or_create_room(room_id: str) -> RoomState:
    """获取房间，若为 lobby 则不存在时自动创建（用于全站在线人数）。"""
    if room_id == LOBBY_ROOM_ID and room_id not in rooms:
        rooms[LOBBY_ROOM_ID] = RoomState(room_id=LOBBY_ROOM_ID, owner_token="")
    return rooms[room_id]

@app.post("/api/room")
async def create_room():
    """创建直播间，仅房主调用。返回 room_id 与 owner_token，房主需妥善保存 owner_token。"""
    room_id = str(uuid.uuid4())
    owner_token = secrets.token_urlsafe(16)
    rooms[room_id] = RoomState(room_id=room_id, owner_token=owner_token)
    return {"room_id": room_id, "owner_token": owner_token}


@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: Optional[str] = Query(None),
):
    if not room_id:
        await websocket.close(code=4000)
        return
    room = get_or_create_room(room_id) if room_id == LOBBY_ROOM_ID else get_room(room_id)
    if not room:
        await websocket.close(code=4004)
        return
    await websocket.accept()
    room.active_connections.append(websocket)
    viewer_id = f"v_{id(websocket)}"
    room.connection_ids[websocket] = viewer_id
    await websocket.send_json({"type": "system", "message": "Connected", "room_id": room_id})
    await room.broadcast_user_count()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "danmaku":
                    room.live_danmaku.append({
                        "text": msg.get("text", ""),
                        "user": msg.get("user", "观众"),
                        "timestamp": datetime.now().isoformat(),
                    })
                    await room.broadcast({
                        "type": "danmaku",
                        "text": msg.get("text", ""),
                        "user": msg.get("user", "观众"),
                    })
                elif msg.get("type") == "cursor":
                    x = msg.get("x", 0)
                    y = msg.get("y", 0)
                    await room.broadcast_to_others(websocket, {
                        "type": "cursor",
                        "viewer_id": viewer_id,
                        "x": x,
                        "y": y,
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in room.active_connections:
            room.active_connections.remove(websocket)
        room.connection_ids.pop(websocket, None)
        await room.broadcast_user_count()


@app.get("/api/online-count")
async def get_online_count(room_id: Optional[str] = Query(None)):
    if not room_id:
        return {"count": 0}
    room = get_room(room_id)
    if not room:
        return {"count": 0}
    return {"count": len(room.active_connections)}


@app.get("/api/status")
async def get_status(room_id: Optional[str] = Query(None)):
    if not room_id:
        raise HTTPException(status_code=400, detail="room_id required")
    room = get_room(room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    return {
        "is_running": room.is_running,
        "stream_state": room.stream_state,
        "current_step": room.current_step,
        "total_steps": room.total_steps,
        "current_stage": room.current_stage,
        "info_message": room.info_message,
        "error_message": room.error_message,
        "online_count": len(room.active_connections),
    }


class DanmakuRequestWithRoom(DanmakuRequest):
    room_id: str = ""


@app.post("/api/danmaku")
async def post_danmaku(req: DanmakuRequestWithRoom):
    if not req.room_id:
        raise HTTPException(status_code=400, detail="room_id required")
    room = get_room(req.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    room.live_danmaku.append({
        "text": req.text,
        "user": req.user,
        "timestamp": datetime.now().isoformat(),
    })
    await room.broadcast({"type": "danmaku", "text": req.text, "user": req.user})
    return {"ok": True}

@app.get("/api/history")
async def get_history():
    files = sorted(SCRIPTS_DIR.glob("*.json"), key=os.path.getmtime, reverse=True)
    history = []
    for f in files:
        try:
            with open(f, "r", encoding="utf-8") as jf:
                data = json.load(jf)
                meta = data.get("metadata", {})
                history.append({
                    "filename": f.name,
                    "title": meta.get("topic", "未命名"),
                    "name": meta.get("name", "未知"),
                    "timestamp": meta.get("timestamp", "")
                })
        except:
            continue
    return history

class StartLiveRequest(LiveRequest):
    """开播请求：必须带 room_id 与 owner_token，仅房主可调用。"""
    room_id: str = ""
    owner_token: str = ""


@app.post("/api/start")
async def start_live(req: StartLiveRequest, background_tasks: BackgroundTasks):
    if not req.room_id or not req.owner_token:
        raise HTTPException(status_code=400, detail="room_id and owner_token required")
    room = get_room(req.room_id)
    if not room:
        raise HTTPException(status_code=404, detail="Room not found")
    if room.owner_token != req.owner_token:
        raise HTTPException(status_code=403, detail="Only room owner can start live")
    if room.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")

    room.live_danmaku.clear()
    room.error_message = ""
    room.info_message = ""
    room.stream_state = "initializing"
    background_tasks.add_task(run_engine_task, room, req)
    return {"message": "直播任务已启动", "topic": req.topic, "room_id": req.room_id}


async def run_engine_task(room: RoomState, req: StartLiveRequest):
    room.is_running = True
    room.current_step = 0
    room.current_stage = "initializing"
    try:
        voice = getattr(req, "voice", None) or "Cherry"
        os.environ["TTS_VOICE"] = voice
        print(f"[start] room={room.room_id} TTS_VOICE={voice}")

        room.stream_state = "initializing"
        room.info_message = "正在初始化直播引擎..."
        await room.broadcast({"type": "info", "content": room.info_message})

        engine = EchuuLiveEngine()

        # 语言：请求里指定 > 从 topic/persona 检测，否则默认 zh
        from echuu.live.language import detect_language
        if getattr(req, "language", None) and req.language.strip():
            lang = req.language.strip().lower()
            if lang in ("en", "english"):
                stream_lang = "en"
            elif lang in ("ja", "japanese", "jp"):
                stream_lang = "ja"
            else:
                stream_lang = "zh"
        else:
            profile = detect_language((req.topic or "") + " " + (req.persona or ""))
            stream_lang = profile.primary.value
        print(f"[start] stream_lang={stream_lang} (topic/persona used for detection)")

        room.info_message = f"正在为【{req.character_name}】生成关于【{req.topic}】的剧本..."
        await room.broadcast({"type": "info", "content": room.info_message})
        room.current_stage = "generating_script"
        room.stream_state = "generating_script"

        state = engine.setup(
            name=req.character_name,
            persona=req.persona,
            background=req.background,
            topic=req.topic,
            language=stream_lang,
        )

        room.total_steps = len(state.script_lines)

        await room.broadcast({
            "type": "script_ready",
            "content": f"剧本生成完毕，共 {len(state.script_lines)} 个节点",
            "total_steps": len(state.script_lines),
            "script_preview": [line.text[:50] for line in state.script_lines[:3]]
        })

        room.info_message = "开始表演..."
        await room.broadcast({"type": "info", "content": room.info_message})
        room.current_stage = "performing"
        room.stream_state = "performing"

        simulated_danmaku = []
        for i, text in enumerate(req.danmaku):
            simulated_danmaku.append({"step": i * 2, "text": text, "user": f"用户_{i}"})

        def live_danmaku_getter(step: int):
            """每步取出并清空当前房间的实时弹幕，注入引擎供 AI 回应。"""
            items = room.live_danmaku.copy()
            room.live_danmaku.clear()
            return [{"text": x.get("text", ""), "user": x.get("user", "观众")} for x in items]

        for step_result in engine.run(
            danmaku_sim=simulated_danmaku,
            play_audio=False,
            save_audio=True,
            live_danmaku_getter=live_danmaku_getter,
        ):
            step_num = step_result.get("step", 0)
            room.current_step = step_num
            room.current_stage = step_result.get("stage", "")

            audio_data = step_result.get("audio")
            audio_b64 = None
            if audio_data and isinstance(audio_data, bytes):
                audio_b64 = base64.b64encode(audio_data).decode("ascii")
            elif step_result.get("speech") and not audio_data:
                print(f"[warn] Step {step_num} has speech but no audio (TTS may have failed)")

            cue = step_result.get("cue")
            cue_dict = None
            if cue is not None:
                if hasattr(cue, "to_dict"):
                    cue_dict = cue.to_dict()
                elif isinstance(cue, dict):
                    cue_dict = cue

            broadcast_data = {
                "type": "step",
                "step": step_num,
                "stage": step_result.get("stage", ""),
                "speech": step_result.get("speech", ""),
                "action": step_result.get("action", "continue"),
                "cue": cue_dict,
                "audio_b64": audio_b64,
                "danmaku": step_result.get("danmaku"),
                "emotion_break": step_result.get("emotion_break"),
            }

            await room.broadcast(broadcast_data)
            try:
                if engine.state and hasattr(engine.state, "memory") and hasattr(engine.state.memory, "to_dict"):
                    await room.broadcast({"type": "memory", "memory": engine.state.memory.to_dict()})
            except Exception as e:
                print(f"[memory] broadcast error: {e}")
            await asyncio.sleep(0.1)

        room.current_stage = "finished"
        room.stream_state = "finished"
        try:
            if engine.state and hasattr(engine.state, "memory") and hasattr(engine.state.memory, "to_dict"):
                await room.broadcast({"type": "memory", "memory": engine.state.memory.to_dict()})
        except Exception as e:
            print(f"[memory] final broadcast error: {e}")
        await room.broadcast({"type": "success", "content": "直播表演圆满结束！"})

    except Exception as e:
        error_msg = f"引擎运行出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        room.stream_state = "error"
        room.error_message = str(e)
        await room.broadcast({"type": "error", "content": error_msg})
    finally:
        room.is_running = False
        room.current_stage = ""
        if room.stream_state not in ["finished", "error"]:
            room.stream_state = "idle"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
