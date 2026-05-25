"""
Post routes for the Realtime Discussion Forum.

This module handles API endpoints related to posts, including creation,
retrieval, and real-time updates via WebSockets.
"""

from typing import Any, List, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth.firebase_auth import get_current_user
from app.core.config import settings
from app.database.db import SessionLocal
from app.database.models import Post, Thread, ThreadMembership, ThreadRole, User
from app.schemas.post_schemas import PostCreate, ReplyCreate
from app.schemas.responses import PostRead, PostsResponse
from app.utils.redis_notifications import publish_notification
from app.utils.websocket_manager import manager

router = APIRouter(tags=["Posts"])


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get an async database session.

    Yields:
        AsyncSession: A database session.
    """
    async with SessionLocal() as session:
        yield session


# -------------------------
# CREATE POST
# -------------------------
@router.post("/", response_model=dict)
async def create_post(
    thread_id: int = Form(...),
    content: str = Form(...),
    image: UploadFile = File(None),
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new post in a thread.

    Allows users to create top-level posts with optional image attachments.
    Validates thread existence and user membership before creating the post.
    Broadcasts the new post via WebSocket and sends notifications.

    Args:
        thread_id (int): The ID of the thread to post in.
        content (str): The text content of the post.
        image (UploadFile, optional): An optional image file to attach.
        current_user (Any): The authenticated user.
        db (AsyncSession): The database session.

    Returns:
        dict: Status and post data.

    Raises:
        HTTPException: If thread not found, user not a member, or creation fails.
    """
    # thread exists?
    thread_res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    # membership required
    # Fetch the thread associated with the parent post

    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == current_user.id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only thread members can post"
        )

    image_data = None
    image_filename = None
    if image:
        # Store image data in database
        image_data = await image.read()
        image_filename = image.filename

    post = Post(
        content=content,
        image_data=image_data,
        image_filename=image_filename,
        user_id=current_user.id,
        thread_id=thread_id,
        parent_id=None,
    )
    db.add(post)
    try:
        await db.flush()
        await db.commit()
        await db.refresh(post)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create post",
        )

    payload = {
        "type": "post_created",
        "thread_id": post.thread_id,
        "post": {
            "id": post.id,
            "content": post.content,
            "image_url": post.image_data
            and f"{settings.BASE_URL}/posts/images/{post.id}"
            or None,
            "parent_id": post.parent_id,
            "user": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url,
            },
            "created_at": str(post.created_at),
        },
    }

    # broadcast locally
    await manager.broadcast_thread(post.thread_id, payload)
    # publish to redis so other processes can forward
    try:
        await publish_notification(
            post.user_id, {"type": "post_created", "post": payload["post"]}
        )
    except Exception:
        pass
    try:
        from app.utils.redis_notifications import publish_thread_event

        await publish_thread_event(post.thread_id, payload)
    except Exception as e:
        # Log the exception or handle it appropriately
        print(f"Error publishing thread event: {e}")
    # notify all thread members (except author)
    try:
        members_res = await db.execute(
            select(ThreadMembership).where(ThreadMembership.thread_id == post.thread_id)
        )
        members = members_res.scalars().all()
        notif = {
            "type": "thread_post",
            "message": f"{current_user.full_name} posted in {getattr(thread, 'title', 'a thread')}",
            "post": payload["post"],
            "thread_id": post.thread_id,
        }
        for m in members:
            try:
                if getattr(m, "user_id", None) == current_user.id:
                    continue
                await publish_notification(m.user_id, notif)
            except Exception:
                continue
    except Exception:
        pass
    return {"status": "ok", "post": payload["post"]}


# -------------------------
# REPLY TO A POST
# -------------------------
@router.post("/{post_id}/reply", response_model=dict)
async def reply_to_post(
    post_id: int,
    content: str = Form(...),
    image: UploadFile = File(None),
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent = await db.get(Post, post_id)
    if not parent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Parent post not found"
        )

    # membership required on parent thread
    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == parent.thread_id,
                ThreadMembership.user_id == current_user.id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread members can reply",
        )

    image_data = None
    image_filename = None
    if image:
        # Store image data in database
        image_data = await image.read()
        image_filename = image.filename

    reply = Post(
        content=content,
        image_data=image_data,
        image_filename=image_filename,
        user_id=current_user.id,
        thread_id=parent.thread_id,
        parent_id=parent.id,
    )
    db.add(reply)
    try:
        await db.flush()
        await db.commit()
        await db.refresh(reply)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create reply",
        )

    payload = {
        "type": "reply_created",
        "thread_id": reply.thread_id,
        "post": {
            "id": reply.id,
            "content": reply.content,
            "image_url": reply.image_data
            and f"{settings.BASE_URL}/posts/images/{reply.id}"
            or None,
            "parent_id": reply.parent_id,
            "user": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url,
            },
            "created_at": str(reply.created_at),
        },
    }

    # broadcast locally
    await manager.broadcast_thread(reply.thread_id, payload)
    # publish to redis for other processes
    try:
        await publish_notification(
            reply.user_id, {"type": "reply_created", "post": payload["post"]}
        )
    except Exception:
        pass
    try:
        from app.utils.redis_notifications import publish_thread_event

        await publish_thread_event(reply.thread_id, payload)
    except Exception:
        pass

    # notify all thread members (except author and parent owner) about the reply
    try:
        members_res = await db.execute(
            select(ThreadMembership).where(
                ThreadMembership.thread_id == reply.thread_id
            )
        )
        members = members_res.scalars().all()
        notif = {
            "type": "thread_reply",
            "message": f"{current_user.full_name} replied in {getattr(parent.thread, 'title', 'a thread')}",
            "post": payload["post"],
            "thread_id": reply.thread_id,
        }
        for m in members:
            try:
                if getattr(m, "user_id", None) == current_user.id:
                    continue
                # skip parent-specific notify here to avoid duplicate
                if getattr(parent, "user_id", None) and m.user_id == parent.user_id:
                    continue
                await publish_notification(m.user_id, notif)
            except Exception:
                continue
    except Exception:
        pass

    # notify parent owner (via Redis pub/sub) if different user
    if getattr(parent, "user_id", None) and parent.user_id != current_user.id:
        notif_parent = {
            "type": "reply_notification",
            "message": f"{current_user.full_name} replied to your post",
            "post": payload["post"],
            "thread_id": reply.thread_id,
        }
        try:
            await publish_notification(parent.user_id, notif_parent)
        except Exception:
            pass

    return {"status": "ok", "reply": payload["post"]}


# -------------------------
# GET POST IMAGE
# -------------------------
@router.get("/images/{post_id}")
async def get_post_image(post_id: int, db: AsyncSession = Depends(get_db)):
    """
    Serve image for a post from database.

    Args:
        post_id (int): The ID of the post.
        db (AsyncSession): The database session.

    Returns:
        StreamingResponse: The image file.

    Raises:
        HTTPException: If post not found or no image.
    """
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    if not post.image_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="No image found"
        )

    # Determine content type based on filename
    content_type = "image/jpeg"  # default
    if post.image_filename:
        ext = post.image_filename.lower().split(".")[-1]
        if ext == "png":
            content_type = "image/png"
        elif ext == "gif":
            content_type = "image/gif"
        elif ext == "webp":
            content_type = "image/webp"

    return StreamingResponse(
        BytesIO(post.image_data),
        media_type=content_type,
        headers={
            "Content-Disposition": f"inline; filename={post.image_filename or 'image.jpg'}"
        },
    )


# -------------------------
# DELETE POST
# -------------------------
@router.delete("/{post_id}")
async def delete_post(
    post_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    post = await db.get(Post, post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Post not found"
        )

    owner_id = getattr(post, "user_id", getattr(post, "created_by", None))
    if current_user.id != owner_id:
        mem_res = await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == post.thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
        membership = mem_res.scalar_one_or_none()
        if not membership or membership.role not in (
            ThreadRole.admin,
            ThreadRole.moderator,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to delete this post",
            )

    try:
        # collect all posts in the same thread to find descendants
        res = await db.execute(select(Post).where(Post.thread_id == post.thread_id))
        all_posts = res.scalars().all()

        # build parent->children map
        children_map = {}
        for p in all_posts:
            pid = getattr(p, "parent_id", None)
            children_map.setdefault(pid, []).append(p.id)

        # collect ids to delete via BFS/DFS starting from post_id
        to_delete = []
        stack = [post_id]
        while stack:
            cur = stack.pop()
            to_delete.append(cur)
            for child_id in children_map.get(cur, []):
                stack.append(child_id)

        # delete all posts by id
        for pid in to_delete:
            p = await db.get(Post, pid)
            if p:
                await db.delete(p)

        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete post",
        )

    # Broadcast deletion events for each deleted post id
    try:
        for pid in to_delete:
            payload = {
                "type": "post_deleted",
                "thread_id": post.thread_id,
                "post_id": pid,
            }
            await manager.broadcast_thread(post.thread_id, payload)
        # also publish to redis so other processes can forward
        try:
            from app.utils.redis_notifications import publish_thread_event

            await publish_thread_event(
                post.thread_id, {"type": "posts_deleted", "post_ids": to_delete}
            )
        except Exception:
            pass
    except Exception:
        # Log but don't raise — deletion already committed
        pass

    return {"status": "ok", "deleted_post_ids": to_delete}


# -------------------------
# GET ALL POSTS FOR A THREAD (TREE)
# -------------------------
@router.get("/thread/{thread_id}", response_model=PostsResponse)
async def get_posts(
    thread_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Any = Depends(get_current_user),
):
    res = await db.execute(
        select(Post)
        .where(Post.thread_id == thread_id)
        .options(selectinload(Post.user))
        .order_by(Post.created_at)
    )
    posts = res.scalars().all()

    # build nested tree
    nodes = {}
    roots = []
    for p in posts:
        # build user payload; prefer loaded relationship, fallback to DB lookup
        user_payload = None
        if hasattr(p, "user") and getattr(p, "user") is not None:
            u = p.user
            user_payload = {
                "id": u.id,
                "email": u.email,
                "full_name": u.full_name,
                "avatar_url": u.avatar_url,
            }
        else:
            # fetch minimal user info if not loaded
            try:
                u = await db.get(User, getattr(p, "user_id", None))
            except Exception:
                u = None
            user_payload = {
                "id": getattr(u, "id", getattr(p, "user_id", None)),
                "email": getattr(u, "email", None),
                "full_name": getattr(u, "full_name", None),
                "avatar_url": getattr(u, "avatar_url", None),
            }

        node = {
            "id": p.id,
            "content": p.content,
            "image_url": p.image_data
            and f"{settings.BASE_URL}/posts/images/{p.id}"
            or None,
            "parent_id": p.parent_id,
            "user": user_payload,
            "created_at": str(p.created_at),
            "children": [],
        }
        nodes[p.id] = node

    for p in posts:
        node = nodes[p.id]
        if p.parent_id and p.parent_id in nodes:
            nodes[p.parent_id]["children"].append(node)
        else:
            roots.append(node)

    return {"thread_id": thread_id, "posts": roots}