"""WebSocket 路由"""
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

try:
    from ..state import state
except ImportError:
    from state import state

router = APIRouter()


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 连接端点"""
    ws_id = state.add_connection(websocket)
    await websocket.accept()
    
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        state.remove_connection(ws_id)
