import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import asyncio
from app.utils.websocket_manager import WebSocketManager


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocketManager for each test."""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    return AsyncMock()


@pytest.mark.asyncio
async def test_connect_thread(ws_manager, mock_websocket):
    """Test connecting a WebSocket to a thread."""
    await ws_manager.connect_thread(1, mock_websocket)

    assert 1 in ws_manager.thread_conns
    assert mock_websocket in ws_manager.thread_conns[1]


@pytest.mark.asyncio
async def test_disconnect_thread(ws_manager, mock_websocket):
    """Test disconnecting a WebSocket from a thread."""
    await ws_manager.connect_thread(1, mock_websocket)
    assert mock_websocket in ws_manager.thread_conns[1]

    await ws_manager.disconnect_thread(1, mock_websocket)

    assert 1 not in ws_manager.thread_conns


@pytest.mark.asyncio
async def test_disconnect_thread_empty_set(ws_manager, mock_websocket):
    """Test disconnecting from a thread that becomes empty."""
    ws2 = AsyncMock()
    await ws_manager.connect_thread(1, mock_websocket)
    await ws_manager.connect_thread(1, ws2)

    await ws_manager.disconnect_thread(1, mock_websocket)

    assert 1 in ws_manager.thread_conns
    assert mock_websocket not in ws_manager.thread_conns[1]
    assert ws2 in ws_manager.thread_conns[1]


@pytest.mark.asyncio
async def test_connect_user(ws_manager, mock_websocket):
    """Test connecting a WebSocket to a user."""
    await ws_manager.connect_user(1, mock_websocket)

    assert 1 in ws_manager.user_conns
    assert mock_websocket in ws_manager.user_conns[1]


@pytest.mark.asyncio
async def test_disconnect_user(ws_manager, mock_websocket):
    """Test disconnecting a WebSocket from a user."""
    await ws_manager.connect_user(1, mock_websocket)
    assert mock_websocket in ws_manager.user_conns[1]

    await ws_manager.disconnect_user(1, mock_websocket)

    assert 1 not in ws_manager.user_conns


@pytest.mark.asyncio
async def test_broadcast_thread(ws_manager, mock_websocket):
    """Test broadcasting to all WebSockets in a thread."""
    ws2 = AsyncMock()
    await ws_manager.connect_thread(1, mock_websocket)
    await ws_manager.connect_thread(1, ws2)

    payload = {"type": "test"}

    await ws_manager.broadcast_thread(1, payload)

    mock_websocket.send_json.assert_called_once_with(payload)
    ws2.send_json.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_broadcast_thread_no_connections(ws_manager):
    """Test broadcasting to a thread with no connections."""
    payload = {"type": "test"}

    # Should not raise an exception
    await ws_manager.broadcast_thread(1, payload)


@pytest.mark.asyncio
async def test_send_user(ws_manager, mock_websocket):
    """Test sending to all WebSockets for a user."""
    ws2 = AsyncMock()
    await ws_manager.connect_user(1, mock_websocket)
    await ws_manager.connect_user(1, ws2)

    payload = {"type": "test"}

    await ws_manager.send_user(1, payload)

    mock_websocket.send_json.assert_called_once_with(payload)
    ws2.send_json.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_send_user_no_connections(ws_manager):
    """Test sending to a user with no connections."""
    payload = {"type": "test"}

    # Should not raise an exception
    await ws_manager.send_user(1, payload)


@pytest.mark.asyncio
async def test_safe_send_success(ws_manager, mock_websocket):
    """Test _safe_send with successful send."""
    payload = {"type": "test"}

    await ws_manager._safe_send(mock_websocket, payload)

    mock_websocket.send_json.assert_called_once_with(payload)


@pytest.mark.asyncio
async def test_safe_send_failure(ws_manager, mock_websocket):
    """Test _safe_send with failed send."""
    mock_websocket.send_json.side_effect = Exception("Connection lost")
    payload = {"type": "test"}

    await ws_manager._safe_send(mock_websocket, payload)

    mock_websocket.send_json.assert_called_once_with(payload)
    # WebSocket should be removed from all connections


@pytest.mark.asyncio
async def test_remove_ws_from_threads(ws_manager, mock_websocket):
    """Test _remove_ws removes WebSocket from thread connections."""
    ws2 = AsyncMock()
    await ws_manager.connect_thread(1, mock_websocket)
    await ws_manager.connect_thread(2, mock_websocket)
    await ws_manager.connect_thread(1, ws2)  # Another WS in thread 1

    await ws_manager._remove_ws(mock_websocket)

    assert mock_websocket not in ws_manager.thread_conns[1]
    assert 2 not in ws_manager.thread_conns  # Thread 2 should be removed
    assert ws2 in ws_manager.thread_conns[1]  # ws2 should remain


@pytest.mark.asyncio
async def test_remove_ws_from_users(ws_manager, mock_websocket):
    """Test _remove_ws removes WebSocket from user connections."""
    ws2 = AsyncMock()
    await ws_manager.connect_user(1, mock_websocket)
    await ws_manager.connect_user(2, mock_websocket)
    await ws_manager.connect_user(1, ws2)  # Another WS for user 1

    await ws_manager._remove_ws(mock_websocket)

    assert mock_websocket not in ws_manager.user_conns[1]
    assert 2 not in ws_manager.user_conns  # User 2 should be removed
    assert ws2 in ws_manager.user_conns[1]  # ws2 should remain


@pytest.mark.asyncio
async def test_remove_ws_empty_thread_cleanup(ws_manager, mock_websocket):
    """Test _remove_ws cleans up empty thread connections."""
    await ws_manager.connect_thread(1, mock_websocket)

    await ws_manager._remove_ws(mock_websocket)

    assert 1 not in ws_manager.thread_conns


@pytest.mark.asyncio
async def test_remove_ws_empty_user_cleanup(ws_manager, mock_websocket):
    """Test _remove_ws cleans up empty user connections."""
    await ws_manager.connect_user(1, mock_websocket)

    await ws_manager._remove_ws(mock_websocket)

    assert 1 not in ws_manager.user_conns
