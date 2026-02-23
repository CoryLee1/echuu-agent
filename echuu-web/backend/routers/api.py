"""REST API 路由"""
import os
import json
import zipfile
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel

try:
    from ..config import SCRIPTS_DIR
    from ..models import LiveConfig, StatusResponse
    from ..state import state
    from ..services.live_service import LiveService
    from ..auth.auth import get_current_active_user
    from ..database.database import get_db
    from ..database.models import User, LiveSession, Character
except ImportError:
    from config import SCRIPTS_DIR
    from models import LiveConfig, StatusResponse
    from state import state
    from services.live_service import LiveService
    from auth.auth import get_current_active_user
    from database.database import get_db
    from database.models import User, LiveSession, Character

router = APIRouter()


# ============================================================
# Room management
# ============================================================

@router.post("/room")
async def create_room():
    """创建直播间，返回 room_id 与 owner_token"""
    room_id, owner_token = state.create_room()
    return {"room_id": room_id, "owner_token": owner_token}


@router.get("/online-count")
async def get_online_count(room_id: str):
    """获取指定房间的在线人数"""
    if not state.room_exists(room_id):
        return {"count": 0}
    count = state.get_online_count(room_id)
    return {"count": count}


# ============================================================
# Danmaku
# ============================================================

class DanmakuRequest(BaseModel):
    room_id: Optional[str] = None
    text: str
    user: str = "观众"


@router.post("/danmaku")
async def send_realtime_danmaku(request: DanmakuRequest):
    """发送实时弹幕（接受 JSON body）"""
    if not state.is_running or not state.current_engine:
        raise HTTPException(status_code=400, detail="直播未运行")

    try:
        LiveService.inject_danmaku(request.text, request.user)
        await state.broadcast_to_room({
            "type": "danmaku",
            "text": request.text,
            "user": request.user,
        })
        return {"message": "弹幕已注入队列"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Start live — DB mode (existing) + inline mode (new)
# ============================================================

class InlineStartRequest(BaseModel):
    """前端无 DB 模式：直接传人设数据"""
    character_name: str
    persona: str
    background: str = ""
    topic: str
    voice: Optional[str] = None
    language: Optional[str] = None
    danmaku: Optional[List[str]] = []
    room_id: str
    owner_token: str
    max_steps: int = 15


@router.post("/start")
async def start_live(
    config: LiveConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """启动直播（数据库模式，使用数据库中的角色）"""
    if state.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")

    if not config.character_id:
        raise HTTPException(status_code=400, detail="请指定角色ID")

    character = db.query(Character).filter(
        Character.id == config.character_id,
        Character.user_id == current_user.id,
        Character.is_active == True
    ).first()

    if not character:
        raise HTTPException(status_code=404, detail="角色不存在或无权限")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    state.active_session_id = session_id

    background_tasks.add_task(
        LiveService.run_live_engine,
        config.character_id,
        config,
        session_id,
        current_user.id
    )

    return {"session_id": session_id, "message": "直播已启动"}


class StopRequest(BaseModel):
    room_id: str
    owner_token: str


@router.post("/stop")
async def stop_live(request: StopRequest):
    """房主提前终止直播（广播 success 事件后结束）"""
    if not state.room_exists(request.room_id):
        raise HTTPException(status_code=404, detail="房间不存在")
    if not state.verify_owner(request.room_id, request.owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")
    if not state.is_running:
        return {"message": "直播未运行"}

    state.stop_requested = True
    return {"message": "停止信号已发送"}


@router.post("/start-inline")
async def start_live_inline(
    request: InlineStartRequest,
    background_tasks: BackgroundTasks,
):
    """启动直播（内联模式）：无需数据库角色，用 owner_token 验证房主身份"""
    if state.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")

    if not state.room_exists(request.room_id):
        raise HTTPException(status_code=404, detail="房间不存在，请先调用 /api/room")

    if not state.verify_owner(request.room_id, request.owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    state.active_session_id = session_id
    state.current_room_id = request.room_id

    background_tasks.add_task(
        LiveService.run_live_engine_inline,
        request.character_name,
        request.persona,
        request.background,
        request.topic,
        request.voice or "Cherry",
        request.danmaku or [],
        session_id,
        request.room_id,
        request.max_steps,
    )

    return {"session_id": session_id, "message": "直播已启动"}


# ============================================================
# Status / history / download
# ============================================================

@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取当前直播状态"""
    return StatusResponse(
        is_running=state.is_running,
        session_id=state.active_session_id
    )


@router.get("/history", response_model=list)
async def get_history(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的历史 Session（从数据库）"""
    sessions = db.query(LiveSession).filter(
        LiveSession.user_id == current_user.id
    ).order_by(LiveSession.created_at.desc()).limit(100).all()

    result = []
    for session in sessions:
        result.append({
            "session_id": session.session_id,
            "topic": session.topic,
            "name": session.character.name if session.character else "未知",
            "timestamp": session.created_at.isoformat() if session.created_at else session.session_id,
            "status": session.status.value,
            "started_at": session.started_at.isoformat() if session.started_at else None,
            "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        })

    return result


@router.get("/download/{session_id}")
async def download_session(session_id: str):
    """打包下载整个 Session"""
    session_dir = SCRIPTS_DIR / session_id
    if not session_dir.exists():
        raise HTTPException(status_code=404, detail="Session 不存在")

    zip_path = SCRIPTS_DIR / f"{session_id}.zip"
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(session_dir):
            for file in files:
                zipf.write(
                    os.path.join(root, file),
                    arcname=file
                )

    return FileResponse(
        zip_path,
        filename=f"echuu_session_{session_id}.zip"
    )


# ============================================================
# AI suggest
# ============================================================

class AiSuggestRequest(BaseModel):
    field: str  # "persona" | "background" | "topic"
    context: dict = {}


@router.post("/ai-suggest")
async def ai_suggest(request: AiSuggestRequest):
    """Use LLM to generate a creative suggestion for character setup fields."""
    field = request.field
    ctx = request.context
    character_name = ctx.get("characterName", "")
    model_name = ctx.get("modelName", "")
    language = ctx.get("language", "zh")

    prompts = {
        "persona": {
            "zh": f"为一个名叫「{character_name}」的虚拟主播写一段简短有趣的人设描述（2-3句话），要有个性和特色。模型名: {model_name}",
            "en": f"Write a short, fun personality description (2-3 sentences) for a VTuber named '{character_name}'. Model: {model_name}",
            "ja": f"「{character_name}」というVTuberの個性的で面白いキャラクター設定を2-3文で書いてください。モデル: {model_name}",
        },
        "background": {
            "zh": f"为虚拟主播「{character_name}」写一段简短的背景故事（2-3句话），要有画面感和故事性。",
            "en": f"Write a short backstory (2-3 sentences) for VTuber '{character_name}'. Make it vivid and story-like.",
            "ja": f"VTuber「{character_name}」の短い背景ストーリーを2-3文で書いてください。",
        },
        "topic": {
            "zh": f"为虚拟主播「{character_name}」建议一个有趣的直播主题（一句话），要能吸引观众、引发互动。",
            "en": f"Suggest an engaging stream topic (one sentence) for VTuber '{character_name}' that attracts viewers.",
            "ja": f"VTuber「{character_name}」の面白い配信テーマを1文で提案してください。",
        },
    }

    if field not in prompts:
        raise HTTPException(status_code=400, detail=f"Unknown field: {field}")

    lang = language if language in prompts[field] else "zh"
    prompt_text = prompts[field][lang]

    try:
        from echuu.live.gemini_client import GeminiClient
        client = GeminiClient(thinking_level="low")
        suggestion = client.call(
            prompt=prompt_text,
            system="You are a creative VTuber character designer. Respond ONLY with the requested content, no explanations or formatting.",
            max_tokens=200,
            thinking_level="low",
        )
        return {"suggestion": suggestion.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")
