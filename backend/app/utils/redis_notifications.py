import asyncio
import json
from typing import Optional

import redis.asyncio as redis

from app.core.config import settings
from app.utils.websocket_manager import manager

_redis: Optional[redis.Redis] = None
_listener_task: Optional[asyncio.Task] = None


async def init_redis(url: str):
    global _redis
    _redis = redis.from_url(url, decode_responses=True)


async def publish_notification(user_id: int, payload: dict):
    if not _redis:
        await init_redis(getattr(settings, "REDIS_URL", "redis://localhost:6379"))
    channel = f"notifications:user:{user_id}"
    await _redis.publish(channel, json.dumps(payload))


async def _listener_loop(url: str):
    global _redis
    if not _redis:
        await init_redis(url)
    pubsub = _redis.pubsub()
    await pubsub.psubscribe("notifications:user:*")
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
            try:
                uid = int(str(channel).rsplit(":", 1)[-1])
            except Exception:
                continue
            await manager.send_user(uid, payload)
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
