import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import json
from fastapi import HTTPException, WebSocket, WebSocketDisconnect
from app.routes.ws_routes import _get_user_from_token, ws_thread, ws_notifications


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket."""
    ws = AsyncMock(spec=WebSocket)
    ws.query_params = MagicMock()
    return ws


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.full_name = "Test User"
    return user


@pytest.mark.asyncio
async def test_get_user_from_token_success_existing_user(mock_db, mock_user):
    """Test successful user retrieval with existing user."""
    mock_token = "valid_token"
    mock_decoded = {
        "email": "test@example.com",
        "uid": "firebase_uid",
        "name": "Test User",
        "picture": "avatar_url",
    }

    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_user)

    mock_db.execute = AsyncMock(return_value=mock_result)

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_decoded):
        result = await _get_user_from_token(mock_token, mock_db)

    assert result == mock_user
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_from_token_success_create_user(mock_db):
    """Test successful user creation when user doesn't exist."""
    mock_token = "valid_token"
    mock_decoded = {
        "email": "new@example.com",
        "uid": "firebase_uid",
        "name": "New User",
        "picture": "avatar_url",
    }

    # First query returns None, second returns the created user
    mock_empty_result = MagicMock()
    mock_empty_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_user_result = MagicMock()
    new_user = MagicMock()
    new_user.id = 2
    new_user.email = "new@example.com"
    new_user.firebase_uid = "firebase_uid"
    new_user.full_name = "New User"
    new_user.avatar_url = "avatar_url"
    mock_user_result.scalar_one_or_none = MagicMock(return_value=new_user)

    mock_db.execute = AsyncMock(side_effect=[mock_empty_result, mock_user_result])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_decoded):
        result = await _get_user_from_token(mock_token, mock_db)

    assert result.email == "new@example.com"
    assert result.firebase_uid == "firebase_uid"
    assert result.full_name == "New User"
    assert result.avatar_url == "avatar_url"
    assert mock_db.add.called
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_from_token_invalid_token(mock_db):
    """Test handling of invalid Firebase token."""
    mock_token = "invalid_token"

    with patch(
        "firebase_admin.auth.verify_id_token", side_effect=Exception("Invalid token")
    ):
        with pytest.raises(HTTPException) as exc_info:
            await _get_user_from_token(mock_token, mock_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token"


@pytest.mark.asyncio
async def test_get_user_from_token_missing_email(mock_db):
    """Test handling of token without email."""
    mock_token = "token_without_email"
    mock_decoded = {"uid": "firebase_uid"}  # No email

    with patch("firebase_admin.auth.verify_id_token", return_value=mock_decoded):
        with pytest.raises(HTTPException) as exc_info:
            await _get_user_from_token(mock_token, mock_db)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid token payload"


@pytest.mark.asyncio
async def test_ws_thread_missing_token(mock_websocket):
    """Test WebSocket thread connection with missing token."""
    mock_websocket.query_params.get.return_value = None

    with patch("app.routes.ws_routes.SessionLocal"):
        await ws_thread(mock_websocket, 1)

    mock_websocket.close.assert_called_once_with(code=1008)


@pytest.mark.asyncio
async def test_ws_thread_invalid_token(mock_websocket):
    """Test WebSocket thread connection with invalid token."""
    mock_websocket.query_params.get.return_value = "invalid_token"

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        with patch(
            "app.routes.ws_routes._get_user_from_token",
            side_effect=HTTPException(status_code=401, detail="Invalid token"),
        ):
            await ws_thread(mock_websocket, 1)

    mock_websocket.close.assert_called_once_with(code=1008)


@pytest.mark.asyncio
async def test_ws_thread_not_thread_member(mock_websocket, mock_user):
    """Test WebSocket thread connection when user is not a thread member."""
    mock_websocket.query_params.get.return_value = "valid_token"

    # Mock membership check returns None (not a member)
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=None)

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock(return_value=mock_membership_result)

        with patch("app.routes.ws_routes._get_user_from_token", return_value=mock_user):
            await ws_thread(mock_websocket, 1)

    mock_websocket.close.assert_called_once_with(code=1008)


@pytest.mark.asyncio
async def test_ws_thread_success_connection(mock_websocket, mock_user):
    """Test successful WebSocket thread connection."""
    mock_websocket.query_params.get.return_value = "valid_token"

    # Mock membership exists
    mock_membership = MagicMock()
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local, patch(
        "app.routes.ws_routes.manager.connect_thread", new_callable=AsyncMock
    ) as mock_connect_thread:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock(return_value=mock_membership_result)

        with patch("app.routes.ws_routes._get_user_from_token", return_value=mock_user):
            # Mock WebSocket to disconnect immediately after accept
            mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

            await ws_thread(mock_websocket, 1)

    mock_websocket.accept.assert_called_once()
    mock_connect_thread.assert_called_once_with(1, mock_websocket)


@pytest.mark.asyncio
async def test_ws_thread_typing_message(mock_websocket, mock_user):
    """Test handling of typing message in thread WebSocket."""
    mock_websocket.query_params.get.return_value = "valid_token"

    # Mock membership exists
    mock_membership = MagicMock()
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    typing_message = {"type": "typing"}

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local, patch(
        "app.routes.ws_routes.manager.broadcast_thread", new_callable=AsyncMock
    ) as mock_broadcast:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock(return_value=mock_membership_result)

        with patch("app.routes.ws_routes._get_user_from_token", return_value=mock_user):
            # Send typing message then disconnect
            mock_websocket.receive_text = AsyncMock(
                side_effect=[json.dumps(typing_message), WebSocketDisconnect()]
            )

            await ws_thread(mock_websocket, 1)

    # Verify broadcast was called
    expected_payload = {
        "type": "typing",
        "thread_id": 1,
        "user": {"id": 1, "full_name": mock_user.full_name},
    }
    mock_broadcast.assert_called_with(1, expected_payload)


@pytest.mark.asyncio
async def test_ws_thread_typing_stop_message(mock_websocket, mock_user):
    """Test handling of typing_stop message in thread WebSocket."""
    mock_websocket.query_params.get.return_value = "valid_token"

    # Mock membership exists
    mock_membership = MagicMock()
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    typing_stop_message = {"type": "typing_stop"}

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local, patch(
        "app.routes.ws_routes.manager.broadcast_thread", new_callable=AsyncMock
    ) as mock_broadcast:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock(return_value=mock_membership_result)

        with patch("app.routes.ws_routes._get_user_from_token", return_value=mock_user):
            # Send typing_stop message then disconnect
            mock_websocket.receive_text = AsyncMock(
                side_effect=[json.dumps(typing_stop_message), WebSocketDisconnect()]
            )

            await ws_thread(mock_websocket, 1)

    # Verify broadcast was called
    expected_payload = {"type": "typing_stop", "thread_id": 1, "user": {"id": 1}}
    mock_broadcast.assert_called_with(1, expected_payload)


@pytest.mark.asyncio
async def test_ws_notifications_missing_token(mock_websocket):
    """Test WebSocket notifications connection with missing token."""
    mock_websocket.query_params.get.return_value = None

    await ws_notifications(mock_websocket)

    mock_websocket.close.assert_called_once_with(code=1008)


@pytest.mark.asyncio
async def test_ws_notifications_invalid_token(mock_websocket):
    """Test WebSocket notifications connection with invalid token."""
    mock_websocket.query_params.get.return_value = "invalid_token"

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        with patch(
            "app.routes.ws_routes._get_user_from_token",
            side_effect=HTTPException(status_code=401, detail="Invalid token"),
        ):
            await ws_notifications(mock_websocket)

    mock_websocket.close.assert_called_once_with(code=1008)


@pytest.mark.asyncio
async def test_ws_notifications_success_connection(mock_websocket, mock_user):
    """Test successful WebSocket notifications connection."""
    mock_websocket.query_params.get.return_value = "valid_token"

    with patch("app.routes.ws_routes.SessionLocal") as mock_session_local, patch(
        "app.routes.ws_routes.manager.connect_user", new_callable=AsyncMock
    ) as mock_connect_user:
        mock_session = AsyncMock()
        mock_session_local.return_value.__aenter__.return_value = mock_session

        with patch("app.routes.ws_routes._get_user_from_token", return_value=mock_user):
            # Mock WebSocket to disconnect immediately after accept
            mock_websocket.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

            await ws_notifications(mock_websocket)

    mock_websocket.accept.assert_called_once()
    mock_connect_user.assert_called_once_with(mock_user.id, mock_websocket)
