"""WebSocket 路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional

try:
    from ..state import state
except ImportError:
    from state import state

router = APIRouter()


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
