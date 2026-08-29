"""REST API 路由"""
import os
import json
import asyncio
import base64
import io
import wave
import zipfile
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

try:
    from ..config import SCRIPTS_DIR
    from ..models import LiveConfig, StatusResponse
    from ..state import state
    from ..services.live_service import LiveService
    from ..auth.auth import get_current_active_user
    from ..database.database import get_db
    from ..database.models import User, LiveSession, Character, VoiceConfig, LLMModel, SessionStatus
except ImportError:
    from config import SCRIPTS_DIR
    from models import LiveConfig, StatusResponse
    from state import state
    from services.live_service import LiveService
    from auth.auth import get_current_active_user
    from database.database import get_db
    from database.models import User, LiveSession, Character, VoiceConfig, LLMModel, SessionStatus

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
    kind: str = "chat"
    gift_id: str = ""
    client_id: str = ""
    amount: int = 0
    entities: List = Field(default_factory=list)


@router.post("/danmaku")
async def send_realtime_danmaku(request: DanmakuRequest):
    """发送实时弹幕、投喂、线索收集或跑毛卡。"""
    if not state.is_running or not state.current_engine:
        raise HTTPException(status_code=400, detail="直播未运行")

    try:
        dm = LiveService.inject_danmaku(
            request.text,
            request.user,
            kind=request.kind,
            gift_id=request.gift_id,
            client_id=request.client_id,
            amount=request.amount,
            entities=request.entities,
        )
        if request.kind == "collect":
            return {"message": "已记下线索", "item": dm.to_public()}
        return {"message": "已进入处理队列", "item": dm.to_public()}
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
    # 三模式：storytelling（默认）/ reaction / singing_learn
    mode: str = "storytelling"
    # 模式专属输入（尽量简单）：
    #   reaction:      {"video_url": "..."}  公网可访问的视频 URL
    #   singing_learn: {"song_path": "...", "song_title": "...", "lyrics": "...(可选)"}
    source: Optional[dict] = None
    # 结构化人设卡（Phase 2-①，可选）：speech_tics/audience_nickname/stances/fears/
    # prides/running_gags/metaphor_domain 等，见 echuu/core/persona_card.py
    persona_card: Optional[dict] = None
    # 主平台用户 ID（可选），只用于归档归属元数据。
    owner_id: Optional[str] = None


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

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
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


class ArchiveRetryRequest(BaseModel):
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


@router.post("/archive/{session_id}/retry")
async def retry_archive(session_id: str, request: ArchiveRetryRequest):
    """房主重试一次已落盘 Session 的 S3 归档。"""
    if not state.room_exists(request.room_id):
        raise HTTPException(status_code=404, detail="房间不存在")
    if not state.verify_owner(request.room_id, request.owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")
    try:
        return await LiveService.archive_existing_session(session_id, room_id=request.room_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@router.post("/start-inline")
async def start_live_inline(
    request: InlineStartRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """启动直播（内联模式）：无需数据库角色，用 owner_token 验证房主身份"""
    if state.is_running:
        raise HTTPException(status_code=400, detail="直播已经在运行中")

    if not state.room_exists(request.room_id):
        raise HTTPException(status_code=404, detail="房间不存在，请先调用 /api/room")

    if not state.verify_owner(request.room_id, request.owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")

    session_id = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    state.active_session_id = session_id
    state.current_room_id = request.room_id

    # Inline 也写标准 LiveSession。它没有 Agent JWT，所以使用受控的
    # 内置用户作为外键 owner，真实主平台 owner_id 放在 metadata 中。
    inline_user = db.query(User).filter(User.username == "admin").first()
    llm_model = db.query(LLMModel).filter(LLMModel.is_default == True).first()
    if not inline_user or not llm_model:
        raise HTTPException(status_code=503, detail="Agent inline persistence is not initialized")
    character = db.query(Character).filter(
        Character.user_id == inline_user.id,
        Character.name == request.character_name,
    ).first()
    if not character:
        character = Character(
            user_id=inline_user.id,
            name=request.character_name,
            persona=request.persona,
            background=request.background,
            default_llm_model_id=llm_model.id,
        )
        db.add(character)
        db.flush()
    voice_name = request.voice or "Cherry"
    voice_config = db.query(VoiceConfig).filter(
        VoiceConfig.character_id == character.id,
        VoiceConfig.voice_name == voice_name,
    ).first()
    if not voice_config:
        voice_config = VoiceConfig(
            character_id=character.id,
            voice_name=voice_name,
            tts_model=os.getenv("TTS_MODEL", "qwen3-tts-flash-realtime"),
            is_default=False,
        )
        db.add(voice_config)
        db.flush()
    session_dir = SCRIPTS_DIR / session_id
    db.add(LiveSession(
        session_id=session_id,
        user_id=inline_user.id,
        character_id=character.id,
        topic=request.topic,
        llm_model_id=llm_model.id,
        voice_config_id=voice_config.id,
        status=SessionStatus.RUNNING,
        script_path=str(session_dir / "full_script.json"),
        audio_dir=str(session_dir),
        archive_status="pending",
        started_at=datetime.utcnow(),
        session_metadata={
            "source": "start-inline",
            "owner_id": request.owner_id,
            "room_id": request.room_id,
            "mode": request.mode,
            "character_name": request.character_name,
            "persona": request.persona,
            "background": request.background,
            "voice": voice_name,
            "diary": {"visibility": "public"},
        },
    ))
    db.commit()

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
        request.mode,
        request.source,
        request.persona_card,
    )

    return {"session_id": session_id, "mode": request.mode, "message": "直播已启动"}


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


@router.get("/diaries")
async def list_public_diaries(db: Session = Depends(get_db)):
    """公开直播日记：默认公开，日历和社媒分发共用。"""
    try:
        from ..services.diary import compose_diary, is_public_diary
    except ImportError:
        from services.diary import compose_diary, is_public_diary

    sessions = (
        db.query(LiveSession)
        .order_by(LiveSession.created_at.desc())
        .limit(120)
        .all()
    )
    diaries = []
    for session in sessions:
        if session.status not in {SessionStatus.COMPLETED, SessionStatus.RUNNING}:
            continue
        if not is_public_diary(session.session_metadata):
            continue
        diaries.append(compose_diary(session))
    return {"diaries": diaries}


@router.get("/diaries/{session_id}")
async def get_public_diary(session_id: str, db: Session = Depends(get_db)):
    try:
        from ..services.diary import compose_diary, is_public_diary
    except ImportError:
        from services.diary import compose_diary, is_public_diary

    session = db.query(LiveSession).filter(LiveSession.session_id == session_id).first()
    if not session or not is_public_diary(session.session_metadata):
        raise HTTPException(status_code=404, detail="日记不存在或未公开")
    return compose_diary(session)


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
            "s3_prefix": session.s3_prefix,
            "uploaded_count": session.uploaded_count,
            "archive_status": session.archive_status,
            "archive_error": session.archive_error,
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
    current_value = str(ctx.get("currentValue", "")).strip()

    prompts = {
        "persona": {
            "zh": f"为一个名叫「{character_name}」的虚拟主播写一段简短有趣的人设描述（2-3句话），要有个性和特色。模型名: {model_name}",
            "en": f"Write a short, fun personality description (2-3 sentences) for a VTuber named '{character_name}'. Model: {model_name}",
            "ja": f"「{character_name}」というVTuberの個性的で面白いキャラクター設定を2-3文で書いてください。モデル: {model_name}",
            "ko": f"'{character_name}'라는 VTuber의 개성 있고 재미있는 페르소나를 2~3문장으로 작성하세요. 모델: {model_name}",
        },
        "background": {
            "zh": f"为虚拟主播「{character_name}」写一段简短的背景故事（2-3句话），要有画面感和故事性。",
            "en": f"Write a short backstory (2-3 sentences) for VTuber '{character_name}'. Make it vivid and story-like.",
            "ja": f"VTuber「{character_name}」の短い背景ストーリーを2-3文で書いてください。",
            "ko": f"VTuber '{character_name}'의 생생하고 짧은 배경 이야기를 2~3문장으로 작성하세요.",
        },
        "topic": {
            "zh": f"为虚拟主播「{character_name}」建议一个有趣的直播主题（一句话），要能吸引观众、引发互动。",
            "en": f"Suggest an engaging stream topic (one sentence) for VTuber '{character_name}' that attracts viewers.",
            "ja": f"VTuber「{character_name}」の面白い配信テーマを1文で提案してください。",
            "ko": f"VTuber '{character_name}'의 흥미롭고 상호작용을 유도하는 방송 주제를 한 문장으로 제안하세요.",
        },
    }

    if field not in prompts:
        raise HTTPException(status_code=400, detail=f"Unknown field: {field}")

    lang = language if language in prompts[field] else "zh"
    prompt_text = prompts[field][lang]
    if current_value:
        prompt_text += (
            "\nContinue and improve the existing text below without repeating it. Return the complete revised text, "
            "in the same language and within 600 characters:\n" + current_value
        )

    try:
        from echuu.live.llm_factory import create_llm_client
        client = create_llm_client(thinking_level="low")
        suggestion = await asyncio.to_thread(
            client.call,
            prompt=prompt_text,
            system="You are a creative VTuber character designer. Respond ONLY with the requested content, no explanations or formatting.",
            max_tokens=200,
        )
        return {"suggestion": suggestion.strip()}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI generation failed: {str(e)}")


class OnboardingChatTurn(BaseModel):
    role: str
    content: str


class OnboardingChatRequest(BaseModel):
    message: str
    name: str
    persona: str
    background: str = ""
    voice: str = "Cherry"
    language: str = "zh"
    history: List[OnboardingChatTurn] = []


def _synthesize_onboarding_reply(text: str, voice_id: str) -> Optional[str]:
    """Synthesize short preview speech and return a browser-playable WAV data payload."""
    from echuu.live.tts_client import TTSClient
    from echuu.live.breath import strip_stage_directions

    tts = TTSClient()
    if not tts.enabled or not tts.tts:
        return None
    tts.tts.voice = voice_id
    tts.tts.language_type = "auto"
    # Step 2 is a short preview turn: synthesize it in one committed request.
    # The live engine's server_commit + breath grouping is designed for a
    # timeline, but can leave an HTTP preview waiting on multiple WS sessions.
    tts.tts.mode = "commit"
    tts.tts.timeout = min(float(getattr(tts.tts, "timeout", 30)), 30.0)
    audio = tts.tts.synthesize(strip_stage_directions(text))
    if not audio:
        return None
    if audio[:4] == b"RIFF":
        return base64.b64encode(audio).decode("ascii")
    sample_rate = int(os.getenv("TTS_SAMPLE_RATE", "24000"))
    wav_buffer = io.BytesIO()
    with wave.open(wav_buffer, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        output.writeframes(audio)
    return base64.b64encode(wav_buffer.getvalue()).decode("ascii")


@router.post("/onboarding-chat")
async def onboarding_chat(request: OnboardingChatRequest):
    """Role-play one short turn using the exact persona/background/voice selected in Step 2."""
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="message is required")

    language_names = {"zh": "Simplified Chinese", "en": "English", "ja": "Japanese", "ko": "Korean"}
    history = "\n".join(
        f"{turn.role}: {turn.content[:400]}" for turn in request.history[-6:]
    )
    system = f"""You are {request.name}, a VTuber speaking directly with the user.
Persona: {request.persona}
Background: {request.background}
Reply in {language_names.get(request.language, 'Simplified Chinese')}.
Stay fully in character, naturally reflect the persona and background, and answer in 1-3 spoken sentences.
Never mention prompts, system messages, policies, or that you are testing a configuration."""
    prompt = f"Conversation so far:\n{history or '(new conversation)'}\nuser: {message}\nassistant:"

    try:
        from echuu.live.llm_factory import create_llm_client
        from echuu.core.output_safety import sanitize_audience_text

        client = create_llm_client(thinking_level="low")
        raw_reply = await asyncio.to_thread(client.call, prompt=prompt, system=system, max_tokens=180)
        safe = sanitize_audience_text(
            raw_reply,
            source_material={"persona": request.persona, "background": request.background, "message": message},
            tuning_guidance=system,
        )
        reply = safe.text.strip()
        audio_base64 = await asyncio.wait_for(
            asyncio.to_thread(_synthesize_onboarding_reply, reply, request.voice),
            timeout=40,
        )
        return {
            "reply": reply,
            "audio_base64": audio_base64,
            "audio_mime": "audio/wav" if audio_base64 else None,
            "safety_issues": list(safe.issues),
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Onboarding chat failed: {exc}")
