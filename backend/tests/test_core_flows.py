import pytest
from httpx import ASGITransport, AsyncClient

from app.database import models
from app.main import app


@pytest.mark.asyncio
async def test_thread_and_post_flow(db_session):
    # create a dummy user
    user = models.User(email="test@example.com", firebase_uid="uid", full_name="Test")
    db_session.add(user)
    await db_session.flush()

    # override get_current_user to return our test user
    async def _get_user():
        return user

    app.dependency_overrides.clear()
    from app.auth.firebase_auth import get_current_user as real_get_current_user
    from app.auth.firebase_auth import get_db as auth_get_db

    app.dependency_overrides[real_get_current_user] = _get_user

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        # create thread
        resp = await ac.post(
            "/threads/",
            json={"title": "Test Thread", "description": "Test Description"},
        )
        assert resp.status_code == 200
        tid = resp.json()["thread"]["id"]

        # create post
        resp = await ac.post("/posts/", json={"thread_id": tid, "content": "hello"})
        assert resp.status_code == 200
        post_id = resp.json()["post"]["id"]

        # reply
        resp = await ac.post(f"/posts/{post_id}/reply", json={"content": "reply"})
        assert resp.status_code == 200

        # list posts
        resp = await ac.get(f"/posts/thread/{tid}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["thread_id"] == tid
        assert len(data["posts"]) >= 1
