import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi import HTTPException, UploadFile
from io import BytesIO
from app.main import app
from app.database.models import Post, Thread, ThreadMembership, User

client = TestClient(app)


def test_create_post_unauthorized():
    response = client.post("/posts/", json={"thread_id": 1, "content": "Test post"})
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


def test_get_posts_unauthorized():
    response = client.get("/posts/thread/1")
    assert response.status_code == 401
    assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio
async def test_create_post_thread_not_found():
    """Test creating a post in a non-existent thread."""
    from app.routes.post_routes import create_post

    # Mock dependencies
    mock_db = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=None)  # Thread not found
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await create_post(
            thread_id=999,
            content="Test content",
            image=None,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 404
    assert "Thread not found" in exc.value.detail


@pytest.mark.asyncio
async def test_create_post_user_not_member():
    """Test creating a post when user is not a thread member."""
    from app.routes.post_routes import create_post

    # Mock dependencies
    mock_db = AsyncMock()

    # First call: thread exists
    mock_thread_result = MagicMock()
    mock_thread = MagicMock()
    mock_thread.id = 1
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    # Second call: membership not found
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await create_post(
            thread_id=1,
            content="Test content",
            image=None,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 403
    assert "Only thread members can post" in exc.value.detail


@pytest.mark.asyncio
async def test_create_post_success():
    """Test successful post creation."""
    from app.routes.post_routes import create_post

    # Mock dependencies
    mock_db = AsyncMock()
    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Test User"
    mock_user.avatar_url = None

    mock_post = MagicMock()
    mock_post.id = 1
    mock_post.content = "Test content"
    mock_post.thread_id = 1
    mock_post.parent_id = None
    mock_post.created_at = "2023-01-01T00:00:00"
    mock_post.image_data = None

    # Setup mocks
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Mock the post creation
    with patch("app.routes.post_routes.Post", return_value=mock_post):
        with patch(
            "app.routes.post_routes.manager.broadcast_thread", new_callable=AsyncMock
        ) as mock_broadcast:
            with patch(
                "app.routes.post_routes.publish_notification", new_callable=AsyncMock
            ):
                result = await create_post(
                    thread_id=1,
                    content="Test content",
                    image=None,
                    current_user=mock_user,
                    db=mock_db,
                )

    assert "post" in result
    assert result["post"]["id"] == 1
    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_create_post_with_image():
    """Test post creation with image upload."""
    from app.routes.post_routes import create_post

    # Mock dependencies
    mock_db = AsyncMock()
    mock_thread = MagicMock()
    mock_thread.id = 1

    mock_membership = MagicMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Test User"
    mock_user.avatar_url = None

    mock_post = MagicMock()
    mock_post.id = 1
    mock_post.content = "Test content"
    mock_post.thread_id = 1
    mock_post.parent_id = None
    mock_post.created_at = "2023-01-01T00:00:00"
    mock_post.image_data = b"fake_image_data"

    # Mock image
    mock_image = AsyncMock()
    mock_image.read = AsyncMock(return_value=b"fake_image_data")
    mock_image.filename = "test.jpg"

    # Setup mocks
    mock_thread_result = MagicMock()
    mock_thread_result.scalar_one_or_none = MagicMock(return_value=mock_thread)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(
        side_effect=[mock_thread_result, mock_membership_result]
    )
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Mock the post creation
    with patch("app.routes.post_routes.Post", return_value=mock_post):
        with patch(
            "app.routes.post_routes.manager.broadcast_thread", new_callable=AsyncMock
        ):
            with patch(
                "app.routes.post_routes.publish_notification", new_callable=AsyncMock
            ):
                result = await create_post(
                    thread_id=1,
                    content="Test content",
                    image=mock_image,
                    current_user=mock_user,
                    db=mock_db,
                )

    assert "post" in result
    assert result["post"]["image_url"] is not None


@pytest.mark.asyncio
async def test_reply_to_post_parent_not_found():
    """Test replying to a non-existent post."""
    from app.routes.post_routes import reply_to_post

    # Mock dependencies
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)  # Parent post not found

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await reply_to_post(
            post_id=999,
            content="Test reply",
            image=None,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 404
    assert "Parent post not found" in exc.value.detail


@pytest.mark.asyncio
async def test_reply_to_post_user_not_member():
    """Test replying when user is not a thread member."""
    from app.routes.post_routes import reply_to_post

    # Mock dependencies
    mock_db = AsyncMock()

    mock_parent = MagicMock()
    mock_parent.id = 1
    mock_parent.thread_id = 1

    mock_db.get = AsyncMock(return_value=mock_parent)

    # Membership not found
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=None)

    mock_db.execute = AsyncMock(return_value=mock_membership_result)

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await reply_to_post(
            post_id=1,
            content="Test reply",
            image=None,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 403
    assert "Only thread members can reply" in exc.value.detail


@pytest.mark.asyncio
async def test_reply_to_post_success():
    """Test successful reply creation."""
    from app.routes.post_routes import reply_to_post

    # Mock dependencies
    mock_db = AsyncMock()
    mock_parent = MagicMock()
    mock_parent.id = 1
    mock_parent.thread_id = 1
    mock_parent.user_id = 2  # Different user

    mock_membership = MagicMock()

    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.full_name = "Test User"
    mock_user.avatar_url = None

    mock_reply = MagicMock()
    mock_reply.id = 2
    mock_reply.content = "Test reply"
    mock_reply.thread_id = 1
    mock_reply.parent_id = 1
    mock_reply.created_at = "2023-01-01T00:00:00"
    mock_reply.image_data = None

    # Setup mocks
    mock_db.get = AsyncMock(return_value=mock_parent)

    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(return_value=mock_membership)

    mock_db.execute = AsyncMock(return_value=mock_membership_result)
    mock_db.add = MagicMock()
    mock_db.flush = AsyncMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    # Mock the reply creation - patch Post constructor
    def mock_post_constructor(*args, **kwargs):
        return mock_reply

    with patch("app.routes.post_routes.Post", side_effect=mock_post_constructor):
        with patch(
            "app.routes.post_routes.manager.broadcast_thread", new_callable=AsyncMock
        ) as mock_broadcast:
            with patch(
                "app.routes.post_routes.publish_notification", new_callable=AsyncMock
            ):
                result = await reply_to_post(
                    post_id=1,
                    content="Test reply",
                    image=None,
                    current_user=mock_user,
                    db=mock_db,
                )

    assert "reply" in result
    assert result["reply"]["id"] == 2
    assert result["reply"]["parent_id"] == 1
    mock_broadcast.assert_called_once()


@pytest.mark.asyncio
async def test_get_post_image_not_found():
    """Test getting image for non-existent post."""
    from app.routes.post_routes import get_post_image

    mock_db = AsyncMock()
    mock_db.get.return_value = None  # Post not found

    with pytest.raises(HTTPException) as exc:
        await get_post_image(post_id=999, db=mock_db)

    assert exc.value.status_code == 404
    assert "Post not found" in exc.value.detail


@pytest.mark.asyncio
async def test_get_post_image_no_image():
    """Test getting image when post has no image."""
    from app.routes.post_routes import get_post_image

    mock_db = AsyncMock()
    mock_post = MagicMock()
    mock_post.image_data = None

    mock_db.get.return_value = mock_post

    with pytest.raises(HTTPException) as exc:
        await get_post_image(post_id=1, db=mock_db)

    assert exc.value.status_code == 404
    assert "No image found" in exc.value.detail


@pytest.mark.asyncio
async def test_get_post_image_success():
    """Test successful image retrieval."""
    from app.routes.post_routes import get_post_image
    from fastapi.responses import StreamingResponse

    mock_db = AsyncMock()
    mock_post = MagicMock()
    mock_post.image_data = b"fake_image_data"
    mock_post.image_filename = "test.jpg"

    mock_db.get.return_value = mock_post

    result = await get_post_image(post_id=1, db=mock_db)

    assert isinstance(result, StreamingResponse)
    assert result.media_type == "image/jpeg"


@pytest.mark.asyncio
async def test_delete_post_not_found():
    """Test deleting a non-existent post."""
    from app.routes.post_routes import delete_post

    mock_db = AsyncMock()
    mock_db.get.return_value = None  # Post not found

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await delete_post(
            post_id=999,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 404
    assert "Post not found" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_post_not_authorized():
    """Test deleting a post when user is not authorized."""
    from app.routes.post_routes import delete_post

    mock_db = AsyncMock()
    mock_post = MagicMock()
    mock_post.user_id = 2  # Different user
    mock_post.thread_id = 1

    mock_db.get.return_value = mock_post

    # Mock membership query result
    mock_membership_result = MagicMock()
    mock_membership_result.scalar_one_or_none = MagicMock(
        return_value=None
    )  # No membership
    mock_db.execute = AsyncMock(return_value=mock_membership_result)

    mock_user = MagicMock()
    mock_user.id = 1

    with pytest.raises(HTTPException) as exc:
        await delete_post(
            post_id=1,
            current_user=mock_user,
            db=mock_db,
        )

    assert exc.value.status_code == 403
    assert "Not authorized to delete this post" in exc.value.detail


@pytest.mark.asyncio
async def test_delete_post_success():
    """Test successful post deletion."""
    from app.routes.post_routes import delete_post

    mock_db = AsyncMock()
    mock_post = MagicMock()
    mock_post.id = 1
    mock_post.user_id = 1  # Same user
    mock_post.thread_id = 1

    # Mock empty posts list for the thread
    mock_db.get.return_value = mock_post

    # Mock the query result for getting all posts in thread
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db.execute = AsyncMock(return_value=mock_result)

    mock_user = MagicMock()
    mock_user.id = 1

    with patch(
        "app.routes.post_routes.manager.broadcast_thread", new_callable=AsyncMock
    ):
        result = await delete_post(
            post_id=1,
            current_user=mock_user,
            db=mock_db,
        )

    assert "deleted_post_ids" in result
    assert result["deleted_post_ids"] == [1]


@pytest.mark.asyncio
async def test_get_posts_success():
    """Test successful posts retrieval."""
    from app.routes.post_routes import get_posts

    mock_db = AsyncMock()
    mock_user = MagicMock()
    mock_user.id = 1

    # Mock posts
    mock_post = MagicMock()
    mock_post.id = 1
    mock_post.content = "Test post"
    mock_post.parent_id = None
    mock_post.created_at = "2023-01-01T00:00:00"
    mock_post.image_data = None
    mock_post.user_id = 1

    mock_post_user = MagicMock()
    mock_post_user.id = 1
    mock_post_user.email = "test@example.com"
    mock_post_user.full_name = "Test User"
    mock_post_user.avatar_url = None

    mock_post.user = mock_post_user

    # Mock the query result
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [mock_post]
    mock_db.execute = AsyncMock(return_value=mock_result)

    result = await get_posts(
        thread_id=1,
        db=mock_db,
        current_user=mock_user,
    )

    assert "thread_id" in result
    assert "posts" in result
    assert len(result["posts"]) == 1
    assert result["posts"][0]["id"] == 1
