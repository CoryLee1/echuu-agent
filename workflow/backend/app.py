import os
import sys
import json
import base64
import asyncio
import traceback
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from pathlib import Path

# 将项目根目录添加到路径并加载 .env
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

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

class DanmakuRequest(BaseModel):
    text: str
    user: str = "观众"

class StatusManager:
    def __init__(self):
        self.is_running = False
        self.current_step = 0
        self.total_steps = 0
        self.current_stage = ""
        self.stream_state = "idle"
        self.info_message = ""
        self.error_message = ""
        self.active_connections: List[WebSocket] = []
        self.live_danmaku: List[dict] = []

    async def broadcast(self, data: dict):
        clean_data = json.loads(json.dumps(data, default=str))
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(clean_data)
            except:
                dead.append(connection)
        for c in dead:
            if c in self.active_connections:
                self.active_connections.remove(c)

    async def broadcast_user_count(self):
        count = len(self.active_connections)
        await self.broadcast({"type": "user_count", "count": count})

status_manager = StatusManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    status_manager.active_connections.append(websocket)
    await websocket.send_json({"type": "system", "message": "Connected to ECHUU WebSocket"})
    await status_manager.broadcast_user_count()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                if msg.get("type") == "danmaku":
                    status_manager.live_danmaku.append({
                        "text": msg.get("text", ""),
                        "user": msg.get("user", "观众"),
                        "timestamp": datetime.now().isoformat(),
                    })
                    await status_manager.broadcast({
                        "type": "danmaku",
                        "text": msg.get("text", ""),
                        "user": msg.get("user", "观众"),
                    })
            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        if websocket in status_manager.active_connections:
            status_manager.active_connections.remove(websocket)
        await status_manager.broadcast_user_count()

@app.get("/api/online-count")
async def get_online_count():
    return {"count": len(status_manager.active_connections)}

@app.get("/api/status")
async def get_status():
    return {
        "is_running": status_manager.is_running,
        "stream_state": status_manager.stream_state,
        "current_step": status_manager.current_step,
        "total_steps": status_manager.total_steps,
        "current_stage": status_manager.current_stage,
        "info_message": status_manager.info_message,
        "error_message": status_manager.error_message,
        "online_count": len(status_manager.active_connections),
    }

@app.post("/api/danmaku")
async def post_danmaku(req: DanmakuRequest):
    status_manager.live_danmaku.append({
        "text": req.text,
        "user": req.user,
        "timestamp": datetime.now().isoformat(),
    })
    await status_manager.broadcast({
        "type": "danmaku",
        "text": req.text,
        "user": req.user,
    })
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

@app.post("/api/start")
async def start_live(req: LiveRequest, background_tasks: BackgroundTasks):
    if status_manager.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")

    status_manager.live_danmaku.clear()
    status_manager.error_message = ""
    status_manager.info_message = ""
    status_manager.stream_state = "initializing"
    background_tasks.add_task(run_engine_task, req)
    return {"message": "直播任务已启动", "topic": req.topic}

async def run_engine_task(req: LiveRequest):
    status_manager.is_running = True
    status_manager.current_step = 0
    status_manager.current_stage = "initializing"
    try:
        status_manager.stream_state = "initializing"
        status_manager.info_message = "正在初始化直播引擎..."
        await status_manager.broadcast({"type": "info", "content": status_manager.info_message})

        engine = EchuuLiveEngine()

        status_manager.info_message = f"正在为【{req.character_name}】生成关于【{req.topic}】的剧本..."
        await status_manager.broadcast({"type": "info", "content": status_manager.info_message})
        status_manager.current_stage = "generating_script"
        status_manager.stream_state = "generating_script"

        state = engine.setup(
            name=req.character_name,
            persona=req.persona,
            background=req.background,
            topic=req.topic
        )

        status_manager.total_steps = len(state.script_lines)

        await status_manager.broadcast({
            "type": "script_ready",
            "content": f"剧本生成完毕，共 {len(state.script_lines)} 个节点",
            "total_steps": len(state.script_lines),
            "script_preview": [line.text[:50] for line in state.script_lines[:3]]
        })

        status_manager.info_message = "开始表演..."
        await status_manager.broadcast({"type": "info", "content": status_manager.info_message})
        status_manager.current_stage = "performing"
        status_manager.stream_state = "performing"

        simulated_danmaku = []
        for i, text in enumerate(req.danmaku):
            simulated_danmaku.append({"step": i * 2, "text": text, "user": f"用户_{i}"})

        for step_result in engine.run(
            danmaku_sim=simulated_danmaku,
            play_audio=False,
            save_audio=True
        ):
            step_num = step_result.get("step", 0)
            status_manager.current_step = step_num
            status_manager.current_stage = step_result.get("stage", "")

            # Base64 encode audio bytes if present
            audio_data = step_result.get("audio")
            audio_b64 = None
            if audio_data and isinstance(audio_data, bytes):
                audio_b64 = base64.b64encode(audio_data).decode("ascii")

            # Build cue dict from step result
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

            await status_manager.broadcast(broadcast_data)
            await asyncio.sleep(0.1)

        status_manager.current_stage = "finished"
        status_manager.stream_state = "finished"
        await status_manager.broadcast({"type": "success", "content": "直播表演圆满结束！"})

        # 上传到 S3：streaming_content（文+声音）、memory（收藏/日记）
        try:
            from services.s3_upload import upload_after_run, is_s3_configured
            if is_s3_configured():
                r = upload_after_run(engine.scripts_dir, memory=engine.state.memory)
                if not r.get("skipped"):
                    await status_manager.broadcast({
                        "type": "s3_upload",
                        "streaming_content": r.get("streaming_content", {}),
                        "memory": r.get("memory"),
                    })
        except Exception as s3_err:
            print("S3 上传跳过:", s3_err)

    except Exception as e:
        error_msg = f"引擎运行出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        status_manager.stream_state = "error"
        status_manager.error_message = str(e)
        await status_manager.broadcast({"type": "error", "content": error_msg})
    finally:
        status_manager.is_running = False
        status_manager.current_stage = ""
        if status_manager.stream_state not in ["finished", "error"]:
            status_manager.stream_state = "idle"

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
