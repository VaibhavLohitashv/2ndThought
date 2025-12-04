import asyncio
import json
import uuid
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.utils.websocket_manager import manager

# unique id for this process to avoid re-broadcasting our own redis-published messages
_PROCESS_ID = str(uuid.uuid4())

_redis: Optional[redis.Redis] = None
_listener_task: Optional[asyncio.Task] = None


async def init_redis(url: str):
    global _redis
    _redis = redis.from_url(url, decode_responses=True)


async def publish_notification(user_id: int, payload: dict):
    if not _redis:
        await init_redis(getattr(settings, "REDIS_URL", "redis://localhost:6379"))
    channel = f"notifications:user:{user_id}"
    # attach origin so listeners can ignore messages from this process
    msg = dict(payload)
    msg["origin"] = _PROCESS_ID
    # First, try to deliver to any local websocket connections so notifications
    # work even when Redis is not available or this is a single-process setup.
    try:
        # manager.send_user is async; call it but don't fail the publisher on errors
        await manager.send_user(user_id, dict(payload))
    except Exception:
        pass

    # Then publish to Redis so other processes can receive it.
    await _redis.publish(channel, json.dumps(msg))


async def publish_thread_event(thread_id: int, payload: dict):
    if not _redis:
        await init_redis(getattr(settings, "REDIS_URL", "redis://localhost:6379"))
    channel = f"thread:events:{thread_id}"
    msg = dict(payload)
    msg["origin"] = _PROCESS_ID
    await _redis.publish(channel, json.dumps(msg))


async def _listener_loop(url: str):
    global _redis
    if not _redis:
        await init_redis(url)
    pubsub = _redis.pubsub()
    await pubsub.psubscribe("notifications:user:*")
    await pubsub.psubscribe("thread:events:*")
    try:
        # listen loop using get_message with a small timeout to allow cancellation
        while True:
            msg = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1.0)
            if not msg:
                await asyncio.sleep(0)  # yield
                continue
            # msg example: {'type': 'pmessage', 'pattern': 'notifications:user:*', 'channel': 'notifications:user:123', 'data': '{"..."}'}
            data = msg.get("data")
            channel = msg.get("channel") or msg.get("pattern")
            try:
                payload = json.loads(data)
            except Exception:
                continue
            # ignore messages originating from this process
            if isinstance(payload, dict) and payload.get("origin") == _PROCESS_ID:
                continue
            # channel examples: 'notifications:user:123' or 'thread:events:10'
            try:
                parts = str(channel).rsplit(":", 1)
                prefix = parts[0]
                ident = parts[1]
            except Exception:
                continue
            if prefix == "notifications:user":
                try:
                    uid = int(ident)
                except Exception:
                    continue
                await manager.send_user(uid, payload)
            elif prefix == "thread:events":
                try:
                    tid = int(ident)
                except Exception:
                    continue
                # forward the event to all websockets connected to this thread
                await manager.broadcast_thread(tid, payload)
    finally:
        try:
            await pubsub.close()
        except Exception:
            pass


async def start_redis_listener(url: str):
    global _listener_task
    if _listener_task and not _listener_task.done():
        return
    _listener_task = asyncio.create_task(_listener_loop(url))


async def stop_redis_listener():
    global _listener_task
    if _listener_task:
        _listener_task.cancel()
        try:
            await _listener_task
        except asyncio.CancelledError:
            pass
        _listener_task = None
