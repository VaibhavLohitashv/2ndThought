import asyncio
from collections import defaultdict
from typing import Dict, Optional, Set

from starlette.websockets import WebSocket


class WebSocketManager:
    """
    Tracks connections per-thread and per-user.
    - thread_conns: thread_id -> set(WebSocket)
    - user_conns: user_id -> set(WebSocket)
    Safe for concurrent access using an asyncio.Lock.
    """

    def __init__(self) -> None:
        self.thread_conns: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.user_conns: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_thread(self, thread_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self.thread_conns[thread_id].add(ws)

    async def disconnect_thread(self, thread_id: int, ws: WebSocket) -> None:
        async with self._lock:
            conns = self.thread_conns.get(thread_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self.thread_conns[thread_id]

    async def connect_user(self, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            self.user_conns[user_id].add(ws)

    async def disconnect_user(self, user_id: int, ws: WebSocket) -> None:
        async with self._lock:
            conns = self.user_conns.get(user_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self.user_conns[user_id]

    async def broadcast_thread(self, thread_id: int, payload: dict) -> None:
        conns = []
        async with self._lock:
            conns = list(self.thread_conns.get(thread_id, set()))
        await asyncio.gather(*(self._safe_send(ws, payload) for ws in conns))

    async def send_user(self, user_id: int, payload: dict) -> None:
        conns = []
        async with self._lock:
            conns = list(self.user_conns.get(user_id, set()))
        await asyncio.gather(*(self._safe_send(ws, payload) for ws in conns))

    async def _safe_send(self, ws: WebSocket, payload: dict) -> None:
        try:
            await ws.send_json(payload)
        except Exception:
            # on error remove the websocket from any lists
            await self._remove_ws(ws)

    async def _remove_ws(self, ws: WebSocket) -> None:
        async with self._lock:
            # remove from threads
            for tid in list(self.thread_conns.keys()):
                conns = self.thread_conns.get(tid)
                if conns and ws in conns:
                    conns.discard(ws)
                    if not conns:
                        del self.thread_conns[tid]
            # remove from users
            for uid in list(self.user_conns.keys()):
                conns = self.user_conns.get(uid)
                if conns and ws in conns:
                    conns.discard(ws)
                    if not conns:
                        del self.user_conns[uid]


# module-level singleton to import from routes/background tasks
manager = WebSocketManager()
