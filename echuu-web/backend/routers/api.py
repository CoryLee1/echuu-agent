"""REST API 路由"""
import os
import json
import zipfile
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

try:
    from ..config import SCRIPTS_DIR
    from ..models import LiveConfig, StatusResponse
    from ..state import state
    from ..services.live_service import LiveService
    from ..auth.auth import get_current_active_user
    from ..database.database import get_db
    from ..database.models import User, LiveSession
except ImportError:
    from config import SCRIPTS_DIR
    from models import LiveConfig, StatusResponse
    from state import state
    from services.live_service import LiveService
    from auth.auth import get_current_active_user
    from database.database import get_db
    from database.models import User, LiveSession

router = APIRouter()


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


@router.get("/status", response_model=StatusResponse)
async def get_status():
    """获取当前直播状态"""
    return StatusResponse(
        is_running=state.is_running,
        session_id=state.active_session_id
    )


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


@router.post("/danmaku")
async def send_realtime_danmaku(text: str, user: str = "观众"):
    """发送实时弹幕"""
    if not state.is_running or not state.current_engine:
        raise HTTPException(status_code=400, detail="直播未运行")
    
    try:
        LiveService.inject_danmaku(text, user)
        await state.broadcast({
            "type": "info",
            "content": f"实时弹幕注入: {user} - {text}"
        })
        return {"message": "弹幕已注入队列"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/start")
async def start_live(
    config: LiveConfig,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """启动直播（使用数据库中的角色）"""
    if state.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")
    
    # 验证角色ID
    if not config.character_id:
        raise HTTPException(status_code=400, detail="请指定角色ID")
    
    # 验证角色所有权
    from ..database.models import Character
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
    
    return {
        "session_id": session_id,
        "message": "直播已启动"
    }
