"""WebSocket 路由"""
import asyncio
import json
import os
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

try:
    from ..state import state
except ImportError:
    from state import state

router = APIRouter()


@router.websocket("/ws/onboarding-asr")
async def onboarding_asr_endpoint(
    websocket: WebSocket,
    language: str = Query(default="zh"),
):
    """Proxy browser PCM16/16k microphone frames to Qwen streaming ASR.

    Keeping this proxy server-side prevents the DashScope API key from ever
    reaching the browser. Sending {"type":"stop"} commits the push-to-talk turn.
    """
    await websocket.accept()
    if not os.getenv("DASHSCOPE_API_KEY"):
        await websocket.send_json({"type": "error", "message": "DASHSCOPE_API_KEY is not configured"})
        await websocket.close(code=1011)
        return

    try:
        from dashscope.audio.asr import Recognition, RecognitionCallback, RecognitionResult
    except ImportError:
        await websocket.send_json({"type": "error", "message": "dashscope streaming ASR is unavailable"})
        await websocket.close(code=1011)
        return

    loop = asyncio.get_running_loop()
    events: asyncio.Queue = asyncio.Queue()

    class Callback(RecognitionCallback):
        def _emit(self, payload: dict) -> None:
            loop.call_soon_threadsafe(events.put_nowait, payload)

        def on_open(self) -> None:
            self._emit({"type": "ready", "language": language})

        def on_event(self, result: RecognitionResult) -> None:
            sentence = result.get_sentence()
            sentences = sentence if isinstance(sentence, list) else [sentence]
            for item in sentences:
                if not isinstance(item, dict):
                    continue
                text = str(item.get("text") or "").strip()
                if text:
                    self._emit({
                        "type": "final" if RecognitionResult.is_sentence_end(item) else "partial",
                        "text": text,
                    })

        def on_error(self, result: RecognitionResult) -> None:
            self._emit({"type": "error", "message": str(getattr(result, "message", result))})

        def on_complete(self) -> None:
            self._emit({"type": "complete"})

        def on_close(self) -> None:
            self._emit({"type": "closed"})

    recognition = Recognition(
        model=os.getenv("QWEN_ASR_MODEL", "qwen-audio-3.0-asr-flash-streaming"),
        callback=Callback(),
        format="pcm",
        sample_rate=16000,
        # VAD segmentation is the low-latency mode recommended for interactive
        # captions. Semantic segmentation waits for more linguistic context and
        # is better suited to meeting transcription than live VTuber subtitles.
        semantic_punctuation_enabled=False,
        max_sentence_silence=max(
            200,
            min(6000, int(os.getenv("QWEN_ASR_MAX_SENTENCE_SILENCE_MS", "500"))),
        ),
    )

    async def forward_events() -> None:
        while True:
            event = await events.get()
            await websocket.send_json(event)
            if event.get("type") in ("complete", "closed"):
                return

    sender = asyncio.create_task(forward_events())
    started = False
    try:
        await asyncio.to_thread(recognition.start)
        started = True
        while True:
            packet = await websocket.receive()
            if packet.get("type") == "websocket.disconnect":
                break
            audio = packet.get("bytes")
            if audio:
                await asyncio.to_thread(recognition.send_audio_frame, audio)
                continue
            raw_text = packet.get("text")
            if raw_text:
                try:
                    command = json.loads(raw_text)
                except json.JSONDecodeError:
                    command = {}
                if command.get("type") == "stop":
                    await asyncio.to_thread(recognition.stop)
                    started = False
                    await asyncio.wait_for(sender, timeout=10)
                    break
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        try:
            await websocket.send_json({"type": "error", "message": str(exc)})
        except Exception:
            pass
    finally:
        if started:
            await asyncio.to_thread(recognition.stop)
        if not sender.done():
            sender.cancel()


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    room_id: Optional[str] = Query(default=None),
):
    """WebSocket 连接端点；room_id 必须对应已创建的房间"""
    if not room_id or not state.room_exists(room_id):
        await websocket.accept()
        await websocket.close(code=4004)
        return

    ws_id = state.add_connection(websocket, room_id)
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            # Echo cursor/danmaku messages back to room (future: handle client-to-server msgs)
            try:
                import json
                msg = json.loads(data)
                msg_type = msg.get("type")
                if msg_type == "danmaku":
                    await state.broadcast(
                        {"type": "danmaku", "text": msg.get("text", ""), "user": msg.get("user", "观众")},
                        room_id=room_id,
                    )
                elif msg_type == "cursor":
                    await state.broadcast(
                        {"type": "cursor", "viewer_id": ws_id, "x": msg.get("x", 0), "y": msg.get("y", 0)},
                        room_id=room_id,
                    )
            except Exception:
                pass
    except WebSocketDisconnect:
        state.remove_connection(ws_id)
        # Broadcast updated viewer count to the room
        count = state.get_online_count(room_id)
        await state.broadcast({"type": "user_count", "count": count}, room_id=room_id)
