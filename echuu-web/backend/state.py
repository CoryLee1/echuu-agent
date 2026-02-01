"""全局状态管理"""
import json
import asyncio
import uuid
from typing import Optional, Dict
from fastapi import WebSocket

from echuu.live.engine import EchuuLiveEngine


class GlobalStateManager:
    """全局状态管理器"""
    
    def __init__(self):
        self.is_running = False
        self.active_session_id: Optional[str] = None
        self.active_connections: Dict[str, WebSocket] = {}
        self.realtime_danmaku_queue = asyncio.Queue()
        self.current_engine: Optional[EchuuLiveEngine] = None

    async def broadcast(self, data: dict):
        """向所有连接的 WebSocket 客户端广播消息"""
        clean_data = json.loads(json.dumps(data, default=str))
        for ws in list(self.active_connections.values()):
            try:
                await ws.send_json(clean_data)
            except:
                continue

    def add_connection(self, websocket: WebSocket) -> str:
        """添加 WebSocket 连接"""
        ws_id = str(uuid.uuid4())
        self.active_connections[ws_id] = websocket
        return ws_id

    def remove_connection(self, ws_id: str):
        """移除 WebSocket 连接"""
        if ws_id in self.active_connections:
            del self.active_connections[ws_id]

    def set_engine(self, engine: EchuuLiveEngine):
        """设置当前运行的引擎"""
        self.current_engine = engine

    def clear_engine(self):
        """清除当前引擎"""
        self.current_engine = None


# 全局状态实例
state = GlobalStateManager()
