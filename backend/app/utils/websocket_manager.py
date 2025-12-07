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
        """
        Initialize the WebSocketManager with empty connection dictionaries and a lock.
        """
        self.thread_conns: Dict[int, Set[WebSocket]] = defaultdict(set)
        self.user_conns: Dict[int, Set[WebSocket]] = defaultdict(set)
        self._lock = asyncio.Lock()

    async def connect_thread(self, thread_id: int, ws: WebSocket) -> None:
        """
        Connect a WebSocket to a thread.

        Args:
            thread_id (int): The ID of the thread.
            ws (WebSocket): The WebSocket connection to add.
        """
        async with self._lock:
            self.thread_conns[thread_id].add(ws)

    async def disconnect_thread(self, thread_id: int, ws: WebSocket) -> None:
        """
        Disconnect a WebSocket from a thread.

        Args:
            thread_id (int): The ID of the thread.
            ws (WebSocket): The WebSocket connection to remove.
        """
        async with self._lock:
            conns = self.thread_conns.get(thread_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self.thread_conns[thread_id]

    async def connect_user(self, user_id: int, ws: WebSocket) -> None:
        """
        Connect a WebSocket to a user.

        Args:
            user_id (int): The ID of the user.
            ws (WebSocket): The WebSocket connection to add.
        """
        async with self._lock:
            self.user_conns[user_id].add(ws)

    async def disconnect_user(self, user_id: int, ws: WebSocket) -> None:
        """
        Disconnect a WebSocket from a user.

        Args:
            user_id (int): The ID of the user.
            ws (WebSocket): The WebSocket connection to remove.
        """
        async with self._lock:
            conns = self.user_conns.get(user_id)
            if conns:
                conns.discard(ws)
                if not conns:
                    del self.user_conns[user_id]

    async def broadcast_thread(self, thread_id: int, payload: dict) -> None:
        """
        Broadcast a payload to all WebSockets connected to a thread.

        Args:
            thread_id (int): The ID of the thread.
            payload (dict): The data to send.
        """
        conns = []
        async with self._lock:
            conns = list(self.thread_conns.get(thread_id, set()))
        await asyncio.gather(*(self._safe_send(ws, payload) for ws in conns))

    async def send_user(self, user_id: int, payload: dict) -> None:
        """
        Send a payload to all WebSockets connected to a user.

        Args:
            user_id (int): The ID of the user.
            payload (dict): The data to send.
        """
        conns = []
        async with self._lock:
            conns = list(self.user_conns.get(user_id, set()))
        await asyncio.gather(*(self._safe_send(ws, payload) for ws in conns))

    async def _safe_send(self, ws: WebSocket, payload: dict) -> None:
        """
        Safely send a payload to a WebSocket, removing it on error.

        Args:
            ws (WebSocket): The WebSocket to send to.
            payload (dict): The data to send.
        """
        try:
            await ws.send_json(payload)
        except Exception:
            # on error remove the websocket from any lists
            await self._remove_ws(ws)

    async def _remove_ws(self, ws: WebSocket) -> None:
        """
        Remove a WebSocket from all connection lists.

        Args:
            ws (WebSocket): The WebSocket to remove.
        """
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
