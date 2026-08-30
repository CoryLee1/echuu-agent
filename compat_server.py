"""Local-only API adapter for the January 2026 Echuu V4.1 pipeline."""

from __future__ import annotations

import asyncio
import json
import os
import secrets
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
from pydantic import BaseModel

from echuu.live.engine import EchuuLiveEngine


def _load_agent_env() -> None:
    here = Path(__file__).resolve().parent
    candidates = [here / ".env"]
    for parent in here.parents:
        candidates.append(parent / "echuu-agent" / ".env")
        candidates.append(parent / ".env")
    for path in candidates:
        if path.is_file():
            load_dotenv(path, override=False)
            return


_load_agent_env()

# V4 对照服自己不装 boto3；归档交给本机 echuu-web（默认 :8000）。
ECHUU_WEB_URL = os.getenv("ECHUU_WEB_URL", "http://127.0.0.1:8000").rstrip("/")


app = FastAPI(title="Echuu V4.1 local compatibility server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDIO_DIR = Path(__file__).resolve().parent / "output" / "compat-audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/audio", StaticFiles(directory=str(AUDIO_DIR)), name="audio")


@dataclass
class Room:
    owner_token: str
    sockets: list[WebSocket] = field(default_factory=list)
    task: asyncio.Task | None = None
    stop_requested: bool = False


rooms: dict[str, Room] = {}


class StartRequest(BaseModel):
    room_id: str
    owner_token: str
    character_name: str = "Echuu"
    persona: str = "自然、真诚的虚拟主播"
    background: str = ""
    topic: str
    voice: str | None = None
    danmaku: list[str] = []
    max_steps: int | None = None
    mode: str = "storytelling"
    source: dict[str, Any] | None = None
    persona_card: dict[str, Any] | None = None


class StopRequest(BaseModel):
    room_id: str
    owner_token: str


class ArchiveRetryRequest(BaseModel):
    room_id: str = ""
    owner_token: str = ""


def _safe_session_id(session_id: str) -> str:
    name = (session_id or "").strip()
    if not name or "/" in name or "\\" in name or ".." in name:
        raise HTTPException(status_code=400, detail="invalid session_id")
    return name


def session_audio_files(session_id: str) -> list[Path]:
    name = _safe_session_id(session_id)
    return sorted(path for path in AUDIO_DIR.glob(f"{name}*") if path.is_file())


def _proxy_archive_sync(
    session_id: str,
    room_id: str = "",
    owner_token: str = "",
) -> dict[str, Any]:
    payload = json.dumps({"room_id": room_id, "owner_token": owner_token}).encode("utf-8")
    request = urllib.request.Request(
        f"{ECHUU_WEB_URL}/api/archive/{session_id}/retry",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        return {
            "bucket": "",
            "prefix": f"streaming_content/{session_id}/",
            "uploaded_count": 0,
            "status": "failed",
            "error": f"echuu-web archive {exc.code}: {detail[:500]}",
        }
    except Exception as exc:  # noqa: BLE001 — 归档失败仍要回传结构化结果
        return {
            "bucket": "",
            "prefix": f"streaming_content/{session_id}/",
            "uploaded_count": 0,
            "status": "failed",
            "error": str(exc)[:500],
        }


async def archive_session(session_id: str, room_id: str = "", owner_token: str = "") -> dict[str, Any]:
    if not session_audio_files(session_id):
        return {
            "bucket": "",
            "prefix": f"streaming_content/{session_id}/",
            "uploaded_count": 0,
            "status": "failed",
            "error": "session directory was empty",
        }
    return await asyncio.to_thread(_proxy_archive_sync, session_id, room_id, owner_token)


def write_session_meta(session_id: str, request: StartRequest) -> None:
    payload = {
        "topic": request.topic,
        "character_name": request.character_name,
        "persona": request.persona,
        "background": request.background,
        "voice": request.voice,
        "room_id": request.room_id,
    }
    (AUDIO_DIR / f"{session_id}.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def write_session_script(
    session_id: str,
    request: StartRequest,
    speeches: list[str],
    engine: EchuuLiveEngine,
) -> None:
    script = {
        "units": [{"lines": [{"text": text} for text in speeches]}],
    }
    (AUDIO_DIR / f"{session_id}-script.json").write_text(
        json.dumps(script, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    story_points: list[str] = []
    promises: list[Any] = []
    memory = getattr(getattr(engine, "state", None), "memory", None)
    if memory is not None:
        mentioned = getattr(memory, "story_points", None)
        if isinstance(mentioned, dict):
            story_points = [str(item) for item in (mentioned.get("mentioned") or []) if str(item).strip()]
        promises = [item for item in (getattr(memory, "promises", None) or []) if isinstance(item, dict)]
    (AUDIO_DIR / f"{session_id}-memory.json").write_text(
        json.dumps(
            {"name": request.character_name, "story_points": story_points, "promises": promises},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def _proxy_get_sync(path: str) -> Any:
    return _proxy_request_sync("GET", path)


def _proxy_request_sync(method: str, path: str, body: bytes | None = None) -> Any:
    headers = {"Accept": "application/json"}
    if body:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        f"{ECHUU_WEB_URL}{path}",
        data=body,
        headers=headers,
        method=method,
    )
    timeout = 90 if method != "GET" else 60
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as exc:
        raise HTTPException(status_code=exc.code, detail=exc.read().decode("utf-8", errors="replace")[:500]) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=502, detail=f"echuu-web unreachable: {exc}") from exc


async def broadcast(room: Room, payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for socket in room.sockets:
        try:
            await socket.send_json(payload)
        except Exception:
            dead.append(socket)
    for socket in dead:
        if socket in room.sockets:
            room.sockets.remove(socket)


def verify_room(room_id: str, owner_token: str) -> Room:
    room = rooms.get(room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")
    if not secrets.compare_digest(room.owner_token, owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")
    return room


@app.post("/api/room")
async def create_room() -> dict[str, str]:
    room_id = str(uuid.uuid4())
    owner_token = secrets.token_urlsafe(16)
    rooms[room_id] = Room(owner_token=owner_token)
    return {"room_id": room_id, "owner_token": owner_token}


@app.websocket("/ws")
async def room_socket(websocket: WebSocket, room_id: str) -> None:
    room = rooms.get(room_id)
    if room is None:
        await websocket.close(code=4004)
        return
    await websocket.accept()
    room.sockets.append(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        if websocket in room.sockets:
            room.sockets.remove(websocket)


async def run_v4(request: StartRequest, room: Room, session_id: str) -> None:
    try:
        write_session_meta(session_id, request)
        await broadcast(room, {"type": "reasoning", "content": "V4 · 正在确定故事内核…"})
        engine = EchuuLiveEngine()
        await broadcast(room, {"type": "reasoning", "content": "V4 · 正在建立第一人称沉浸状态…"})
        await asyncio.to_thread(
            engine.setup,
            name=request.character_name,
            persona=request.persona,
            background=request.background,
            topic=request.topic,
            language="zh",
        )
        await broadcast(room, {"type": "reasoning", "content": "V4 · 正在进行结构破坏与口语化处理…"})

        danmaku_sim = [
            {"step": index + 1, "text": text, "user": "观众"}
            for index, text in enumerate(request.danmaku)
        ]
        max_steps = request.max_steps or 12
        await broadcast(room, {"type": "reasoning", "content": "V4 · 正在合成台词语音…"})
        results = await asyncio.to_thread(
            lambda: list(engine.run(max_steps=max_steps, danmaku_sim=danmaku_sim)),
        )
        await broadcast(
            room,
            {
                "type": "ready",
                "content": f"V4.1 剧本已生成，Session: {session_id}",
                "session_id": session_id,
                "mode": "storytelling",
            },
        )

        speeches: list[str] = []
        for index, result in enumerate(results):
            if room.stop_requested:
                break
            audio = result.pop("audio", None)
            clean = json.loads(json.dumps(result, ensure_ascii=False, default=str))
            speech = str(clean.get("speech") or clean.get("text") or "").strip()
            if speech:
                speeches.append(speech)
            if audio:
                filename = f"{session_id}-{index}.wav"
                with wave.open(str(AUDIO_DIR / filename), "wb") as output:
                    output.setnchannels(1)
                    output.setsampwidth(2)
                    output.setframerate(24000)
                    output.writeframes(audio)
                clean["audio_url"] = f"/audio/{filename}"
            await broadcast(room, {"type": "step", "mode": "storytelling", **clean})
            await asyncio.sleep(0.05)

        write_session_script(session_id, request, speeches, engine)
        archive_task = asyncio.create_task(archive_session(session_id))
        await broadcast(
            room,
            {"type": "success", "session_id": session_id, "content": "V4.1 表演结束"},
        )
        result = await archive_task
        await broadcast(room, {"type": "archived", "session_id": session_id, **result})
    except Exception as exc:
        await broadcast(room, {"type": "error", "content": f"V4.1: {exc}"})
    finally:
        room.task = None


@app.post("/api/start-inline")
async def start_inline(request: StartRequest) -> dict[str, str]:
    if request.mode != "storytelling":
        raise HTTPException(status_code=400, detail="V4.1 对照服务只支持 storytelling")
    room = verify_room(request.room_id, request.owner_token)
    if room.task and not room.task.done():
        raise HTTPException(status_code=400, detail="该房间的 V4.1 直播已经在运行中")
    room.stop_requested = False
    session_id = f"v4-{uuid.uuid4().hex[:10]}"
    room.task = asyncio.create_task(run_v4(request, room, session_id))
    return {"session_id": session_id, "mode": "storytelling", "message": "V4.1 已启动"}


@app.post("/api/stop")
async def stop(request: StopRequest) -> dict[str, str]:
    room = verify_room(request.room_id, request.owner_token)
    room.stop_requested = True
    return {"message": "V4.1 停止信号已发送"}


@app.post("/api/archive/{session_id}/retry")
async def retry_archive(session_id: str, request: ArchiveRetryRequest) -> dict[str, Any]:
    """房间关了也能按落盘 wav 重试；有房间则校验 owner_token。"""
    room = rooms.get(request.room_id) if request.room_id else None
    if room is not None and not secrets.compare_digest(room.owner_token, request.owner_token):
        raise HTTPException(status_code=403, detail="owner_token 验证失败")
    if not session_audio_files(session_id):
        raise HTTPException(status_code=404, detail=f"Session does not exist: {session_id}")
    return await archive_session(session_id, request.room_id, request.owner_token)


@app.get("/api/diaries")
async def list_diaries() -> Any:
    return await asyncio.to_thread(_proxy_get_sync, "/api/diaries")


@app.get("/api/diaries/{session_id}")
async def get_diary(session_id: str) -> Any:
    return await asyncio.to_thread(_proxy_get_sync, f"/api/diaries/{session_id}")


@app.api_route("/api/analytics/{rest:path}", methods=["GET", "POST"])
async def proxy_analytics(rest: str, request: Request) -> Any:
    """对照服不写 S3，看板和上报都转给 echuu-web。"""
    path = f"/api/analytics/{rest}"
    if request.url.query:
        path = f"{path}?{request.url.query}"
    body = await request.body() if request.method != "GET" else None
    return await asyncio.to_thread(_proxy_request_sync, request.method, path, body or None)


@app.post("/api/danmaku")
async def danmaku(payload: dict[str, Any]) -> dict[str, str]:
    room = rooms.get(str(payload.get("room_id", "")))
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")
    await broadcast(
        room,
        {"type": "danmaku", "text": str(payload.get("text", "")), "user": str(payload.get("user", "观众"))},
    )
    return {"message": "弹幕已广播（V4 对照模式不做实时重排）"}


@app.get("/api/status")
async def status() -> dict[str, Any]:
    active = sum(1 for room in rooms.values() if room.task and not room.task.done())
    return {
        "pipeline": "v4.1-f0d4260",
        "active_rooms": active,
        "llm_ready": bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("DASHSCOPE_API_KEY")),
    }
