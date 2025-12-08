import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException
from app.main import app
from app.database.models import Thread, ThreadMembership, ThreadRole, User

client = TestClient(app)


def test_create_thread_unauthorized():
    response = client.post(
        "/threads/", json={"title": "Test Thread", "description": "Test Description"}
    )
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_get_threads():
    response = client.get("/threads/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_search_threads_empty_query():
    """Test search_threads with empty query."""
    from app.routes.thread_routes import search_threads

    mock_db = AsyncMock()
    result = await search_threads(q="", db=mock_db)

    assert result == []
    mock_db.execute.assert_not_called()


@pytest.mark.asyncio
async def test_search_threads_with_results():
    """Test search_threads with valid query that returns results."""
    from app.routes.thread_routes import search_threads

    mock_db = AsyncMock()
    mock_thread = MagicMock()
    mock_thread.id = 1
    mock_thread.title = "Test Thread"
    mock_thread.description = "Test Description"

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_thread]
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await search_threads(q="test", db=mock_db)

    assert len(result) == 1
    mock_db.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_thread_success():
    """Test successful thread creation."""
    from app.routes.thread_routes import create_thread

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Test User"

    mock_thread = MagicMock()
    mock_thread.id = 1
    mock_thread.title = "Test Thread"
    mock_thread.description = "Test Description"
    mock_thread.created_at = "2023-01-01T00:00:00"

    # Setup mocks
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    with patch("app.routes.thread_routes.Thread", return_value=mock_thread):
        with patch(
            "app.routes.thread_routes.ThreadMembership"
        ) as mock_membership_class:
            with patch(
                "app.routes.thread_routes.manager.broadcast_thread",
                new_callable=AsyncMock,
            ) as mock_broadcast:
                result = await create_thread(
                    data=MagicMock(title="Test Thread", description="Test Description"),
                    current_user=mock_user,
                    db=mock_db,
                )

    assert "thread" in result
    assert result["thread"]["id"] == 1


@pytest.mark.asyncio
async def test_get_thread_not_found():
    """Test getting a non-existent thread."""
    from app.routes.thread_routes import get_thread

    mock_db = AsyncMock()

    # Mock thread query result - thread not found
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=None)
    mock_db.execute = AsyncMock(return_value=mock_thread_result)

    with pytest.raises(HTTPException) as exc:
        await get_thread(thread_id=999, db=mock_db)

    assert exc.value.status_code == 404
    assert "Thread not found" in exc.value.detail


@pytest.mark.asyncio
async def test_get_thread_success():
    """Test successful thread retrieval."""
    from app.routes.thread_routes import get_thread

    mock_db = AsyncMock()
    mock_thread = MagicMock()
    mock_thread.id = 1
    mock_thread.title = "Test Thread"

    # Mock thread query result
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    # Mock members query result
    mock_members_result = MagicMock()
    mock_members_result.scalars.return_value.all.return_value = []

    mock_db.execute = AsyncMock(side_effect=[mock_thread_result, mock_members_result])

    result = await get_thread(thread_id=1, db=mock_db)

    assert result["id"] == 1
    assert result["title"] == "Test Thread"


@pytest.mark.asyncio
async def test_join_thread_success():
    """Test successful thread join."""
    from app.routes.thread_routes import join_thread

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1

    # Setup mocks - thread exists, user not member
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_check_result = MagicMock()
    mock_membership_check_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_check_result]
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch(
        "app.routes.thread_routes.ThreadMembership.__new__",
        return_value=MagicMock(),
    ):
        result = await join_thread(thread_id=1, current_user=mock_user, db=mock_db)

    assert result["thread_id"] == 1


@pytest.mark.asyncio
async def test_join_thread_already_member():
    """Test joining a thread when already a member."""
    from app.routes.thread_routes import join_thread

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()

    # Setup mocks - thread exists, user already member
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )

    result = await join_thread(thread_id=1, current_user=mock_user, db=mock_db)

    assert result["message"] == "Already a member"


@pytest.mark.asyncio
async def test_update_thread_success():
    """Test successful thread update by admin."""
    from app.routes.thread_routes import update_thread
    from app.schemas.thread_schemas import ThreadCreate
    from app.database.models import ThreadRole

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1
    mock_thread.title = "Old Title"
    mock_thread.description = "Old Description"

    mock_membership = MagicMock()
    mock_membership.role = ThreadRole.admin

    # Setup mocks - thread exists, user is admin
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    update_data = ThreadCreate(title="New Title", description="New Description")

    result = await update_thread(
        thread_id=1, data=update_data, current_user=mock_user, db=mock_db
    )

    assert result["status"] == "ok"
    assert result["thread"]["id"] == 1
    assert result["thread"]["title"] == "New Title"
    assert result["thread"]["description"] == "New Description"
    mock_db.add.assert_called_once_with(mock_thread)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(mock_thread)


@pytest.mark.asyncio
async def test_update_thread_not_found():
    """Test updating non-existent thread."""
    from app.routes.thread_routes import update_thread
    from app.schemas.thread_schemas import ThreadCreate
    from fastapi import HTTPException

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Setup mocks - thread not found
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(return_value=mock_thread_result)

    update_data = ThreadCreate(title="New Title", description="New Description")

    with pytest.raises(HTTPException) as exc_info:
        await update_thread(
            thread_id=999, data=update_data, current_user=mock_user, db=mock_db
        )

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Thread not found"


@pytest.mark.asyncio
async def test_update_thread_forbidden():
    """Test updating thread by non-admin user."""
    from app.routes.thread_routes import update_thread
    from app.schemas.thread_schemas import ThreadCreate
    from app.database.models import ThreadRole
    from fastapi import HTTPException

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()
    mock_membership.role = ThreadRole.member  # Not admin

    # Setup mocks - thread exists, user is not admin
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )

    update_data = ThreadCreate(title="New Title", description="New Description")

    with pytest.raises(HTTPException) as exc_info:
        await update_thread(
            thread_id=1, data=update_data, current_user=mock_user, db=mock_db
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only thread admins can update the thread"


@pytest.mark.asyncio
async def test_delete_thread_success():
    """Test successful thread deletion by admin."""
    from app.routes.thread_routes import delete_thread
    from app.database.models import ThreadRole

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()
    mock_membership.role = ThreadRole.admin

    # Setup mocks - thread exists, user is admin
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result, None, None]
    )
    mock_db.delete = AsyncMock()
    mock_db.commit = AsyncMock()

    result = await delete_thread(thread_id=1, current_user=mock_user, db=mock_db)

    assert result["status"] == "ok"
    assert result["deleted_thread_id"] == 1
    mock_db.delete.assert_called_once_with(mock_thread)
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_thread_not_found():
    """Test deleting non-existent thread."""
    from app.routes.thread_routes import delete_thread
    from fastapi import HTTPException

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Setup mocks - thread not found
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(return_value=mock_thread_result)

    with pytest.raises(HTTPException) as exc_info:
        await delete_thread(thread_id=999, current_user=mock_user, db=mock_db)

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Thread not found"


@pytest.mark.asyncio
async def test_delete_thread_forbidden():
    """Test deleting thread by non-admin user."""
    from app.routes.thread_routes import delete_thread
    from app.database.models import ThreadRole
    from fastapi import HTTPException

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()
    mock_membership.role = ThreadRole.member  # Not admin

    # Setup mocks - thread exists, user is not admin
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )

    with pytest.raises(HTTPException) as exc_info:
        await delete_thread(thread_id=1, current_user=mock_user, db=mock_db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only thread admins can delete the thread"


@pytest.mark.asyncio
async def test_promote_member_success_member_to_moderator():
    """Test promoting a member to moderator."""
    from app.routes.thread_routes import promote_member
    from app.database.models import ThreadRole

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Requester is admin
    mock_requester_mem = MagicMock()
    mock_requester_mem.role = ThreadRole.admin

    # Target user is member
    mock_target_mem = MagicMock()
    mock_target_mem.role = ThreadRole.member
    mock_target_mem.user_id = 2

    # Setup mocks
    mock_requester_result = MagicMock()
    mock_requester_result.scalar_one_or_none = MagicMock(
        return_value=mock_requester_mem
    )

    mock_target_result = MagicMock()
    mock_target_result.scalar_one_or_none = MagicMock(return_value=mock_target_mem)

    mock_db.execute = AsyncMock(side_effect=[mock_requester_result, mock_target_result])
    mock_db.commit = AsyncMock()

    with patch(
        "app.routes.thread_routes.manager.broadcast_thread", AsyncMock()
    ) as mock_broadcast:
        result = await promote_member(
            thread_id=1, user_id=2, current_user=mock_user, db=mock_db
        )

    assert result["status"] == "ok"
    assert result["user_id"] == 2
    assert result["role"] == "moderator"
    assert mock_target_mem.role == ThreadRole.moderator
    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_promote_member_success_create_new_membership():
    """Test promoting a user who has no membership (creates as moderator)."""
    from app.routes.thread_routes import promote_member
    from app.database.models import ThreadRole

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Requester is admin
    mock_requester_mem = MagicMock()
    mock_requester_mem.role = ThreadRole.admin

    # Setup mocks - target has no membership
    mock_requester_result = MagicMock()
    mock_requester_result.scalar_one_or_none = MagicMock(
        return_value=mock_requester_mem
    )

    mock_target_result = MagicMock()
    mock_target_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(side_effect=[mock_requester_result, mock_target_result])
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()

    with patch(
        "app.routes.thread_routes.manager.broadcast_thread", AsyncMock()
    ) as mock_broadcast, patch(
        "app.routes.thread_routes.ThreadMembership.__new__", return_value=MagicMock()
    ) as mock_membership:
        result = await promote_member(
            thread_id=1, user_id=2, current_user=mock_user, db=mock_db
        )

    assert result["status"] == "ok"
    assert result["user_id"] == 2
    assert result["role"] == "moderator"
    mock_db.add.assert_called_once()
    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_promote_member_already_admin():
    """Test promoting a user who is already admin (no-op)."""
    from app.routes.thread_routes import promote_member
    from app.database.models import ThreadRole

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Requester is admin
    mock_requester_mem = MagicMock()
    mock_requester_mem.role = ThreadRole.admin

    # Target user is already admin
    mock_target_mem = MagicMock()
    mock_target_mem.role = ThreadRole.admin
    mock_target_mem.user_id = 2

    # Setup mocks
    mock_requester_result = MagicMock()
    mock_requester_result.scalar_one_or_none = MagicMock(
        return_value=mock_requester_mem
    )

    mock_target_result = MagicMock()
    mock_target_result.scalar_one_or_none = MagicMock(return_value=mock_target_mem)

    mock_db.execute = AsyncMock(side_effect=[mock_requester_result, mock_target_result])

    result = await promote_member(
        thread_id=1, user_id=2, current_user=mock_user, db=mock_db
    )

    assert result["status"] == "ok"
    assert result["user_id"] == 2
    assert result["role"] == "admin"


@pytest.mark.asyncio
async def test_promote_member_forbidden():
    """Test promoting member by non-admin user."""
    from app.routes.thread_routes import promote_member
    from app.database.models import ThreadRole
    from fastapi import HTTPException

    # Mock dependencies
    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Requester is not admin
    mock_requester_mem = MagicMock()
    mock_requester_mem.role = ThreadRole.member

    # Setup mocks
    mock_requester_result = MagicMock()
    mock_requester_result.scalar_one_or_none = MagicMock(
        return_value=mock_requester_mem
    )

    mock_db.execute = AsyncMock(return_value=mock_requester_result)

    with pytest.raises(HTTPException) as exc_info:
        await promote_member(thread_id=1, user_id=2, current_user=mock_user, db=mock_db)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Only thread admins can promote members"
