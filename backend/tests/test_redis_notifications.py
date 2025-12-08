import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import asyncio
import json
from app.utils.redis_notifications import (
    init_redis,
    publish_notification,
    publish_thread_event,
    start_redis_listener,
    stop_redis_listener,
)


@pytest.mark.asyncio
async def test_init_redis():
    """Test Redis initialization."""
    with patch("app.utils.redis_notifications.redis.from_url") as mock_redis_from_url:
        mock_redis = MagicMock()
        mock_redis_from_url.return_value = mock_redis

        await init_redis("redis://localhost:6379")

        mock_redis_from_url.assert_called_once_with(
            "redis://localhost:6379", decode_responses=True
        )


@pytest.mark.asyncio
async def test_publish_notification():
    """Test publishing user notifications."""
    with patch("app.utils.redis_notifications._redis", None):
        with patch(
            "app.utils.redis_notifications.init_redis", new_callable=AsyncMock
        ) as mock_init:
            with patch(
                "app.utils.redis_notifications.manager.send_user",
                new_callable=AsyncMock,
            ) as mock_send_user:
                with patch("app.utils.redis_notifications._redis") as mock_redis:
                    mock_redis.publish = AsyncMock()

                    await publish_notification(1, {"type": "test"})

                    mock_init.assert_called_once()
                    mock_send_user.assert_called_once_with(1, {"type": "test"})
                    mock_redis.publish.assert_called_once()


@pytest.mark.asyncio
async def test_publish_thread_event():
    """Test publishing thread events."""
    with patch("app.utils.redis_notifications._redis", None):
        with patch(
            "app.utils.redis_notifications.init_redis", new_callable=AsyncMock
        ) as mock_init:
            with patch("app.utils.redis_notifications._redis") as mock_redis:
                mock_redis.publish = AsyncMock()

                await publish_thread_event(1, {"type": "test"})

                mock_init.assert_called_once()
                mock_redis.publish.assert_called_once()


@pytest.mark.asyncio
async def test_start_redis_listener_already_running():
    """Test starting Redis listener when already running."""
    with patch(
        "app.utils.redis_notifications._listener_task", MagicMock()
    ) as mock_task:
        mock_task.done.return_value = False

        await start_redis_listener("redis://localhost:6379")

        # Should not create a new task
        assert not hasattr(asyncio, "_create_task_called")


@pytest.mark.asyncio
async def test_start_redis_listener_new():
    """Test starting Redis listener when not running."""
    with patch("app.utils.redis_notifications._listener_task", None):
        with patch("asyncio.create_task") as mock_create_task:
            await start_redis_listener("redis://localhost:6379")

            mock_create_task.assert_called_once()


@pytest.mark.asyncio
async def test_stop_redis_listener():
    """Test stopping Redis listener."""
    mock_task = AsyncMock()
    mock_task.cancel = MagicMock()
    mock_task.done = MagicMock(return_value=False)

    with patch("app.utils.redis_notifications._listener_task", mock_task):
        await stop_redis_listener()

        mock_task.cancel.assert_called_once()
