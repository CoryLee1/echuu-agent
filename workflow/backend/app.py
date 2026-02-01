import os
import sys
import json
import asyncio
import traceback
from typing import List, Optional
from datetime import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks, WebSocket, WebSocketDisconnect
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

class StatusManager:
    def __init__(self):
        self.is_running = False
        self.active_connections: List[WebSocket] = []

    async def broadcast(self, data: dict):
        # 转换字典中的非 JSON 序列化对象（如果有）
        clean_data = json.loads(json.dumps(data, default=str))
        for connection in self.active_connections:
            try:
                await connection.send_json(clean_data)
            except:
                continue

status_manager = StatusManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    status_manager.active_connections.append(websocket)
    try:
        # 发送当前状态
        await websocket.send_json({"type": "system", "message": "Connected to ECHUU WebSocket"})
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        status_manager.active_connections.remove(websocket)

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
    
    background_tasks.add_task(run_engine_task, req)
    return {"message": "直播任务已启动", "topic": req.topic}

async def run_engine_task(req: LiveRequest):
    status_manager.is_running = True
    try:
        await status_manager.broadcast({"type": "info", "content": "正在初始化直播引擎..."})
        
        # 初始化引擎
        engine = EchuuLiveEngine()
        
        # Phase 1: 生成剧本
        await status_manager.broadcast({"type": "info", "content": f"正在为【{req.character_name}】生成关于【{req.topic}】的剧本..."})
        state = engine.setup(
            name=req.character_name,
            persona=req.persona,
            background=req.background,
            topic=req.topic
        )
        
        await status_manager.broadcast({
            "type": "script_ready", 
            "content": f"剧本生成完毕，共 {len(state.script_lines)} 个节点",
            "script_preview": [line.text[:50] for line in state.script_lines[:3]]
        })

        # Phase 2: 开始执行（迭代生成器）
        await status_manager.broadcast({"type": "info", "content": "开始表演..."})
        
        # 模拟弹幕数据格式
        simulated_danmaku = []
        for i, text in enumerate(req.danmaku):
            simulated_danmaku.append({"step": i * 2, "text": text, "user": f"用户_{i}"})

        # 运行引擎
        # play_audio=False (Web端播放), save_audio=True (保存音频供Web端调用)
        for step_result in engine.run(
            danmaku_sim=simulated_danmaku,
            play_audio=False, 
            save_audio=True
        ):
            # 将每一步的结果实时推送到前端
            await status_manager.broadcast({
                "type": "step",
                "data": step_result
            })
            # 模拟念白间隔（如果需要的话，engine.run里其实已经有TTS的耗时了）
            # await asyncio.sleep(0.5) 

        await status_manager.broadcast({"type": "success", "content": "直播表演圆满结束！"})

    except Exception as e:
        error_msg = f"引擎运行出错: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        await status_manager.broadcast({"type": "error", "content": error_msg})
    finally:
        status_manager.is_running = False

if __name__ == "__main__":
    import uvicorn
    # 启动命令: python workflow/backend/app.py
    uvicorn.run(app, host="0.0.0.0", port=8000)
