from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.auth.firebase_auth import get_current_user
from app.database.db import SessionLocal
from app.database.models import Post, Thread, ThreadMembership, ThreadRole, User
from app.schemas.post_schemas import PostCreate, ReplyCreate
from app.schemas.responses import PostRead, PostsResponse
from app.utils.redis_notifications import publish_notification
from app.utils.websocket_manager import manager

router = APIRouter(tags=["Posts"])


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


# -------------------------
# CREATE POST
# -------------------------
@router.post("/", response_model=dict)
async def create_post(
    data: PostCreate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # thread exists?
    thread_res = await db.execute(select(Thread).where(Thread.id == data.thread_id))
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    # membership required
    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == data.thread_id,
                ThreadMembership.user_id == current_user.id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Only thread members can post"
        )

    post = Post(
        content=data.content,
        user_id=current_user.id,
        thread_id=data.thread_id,
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
            "parent_id": post.parent_id,
            "user": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url,
            },
            "created_at": str(post.created_at),
        },
    }

    await manager.broadcast_thread(post.thread_id, payload)
    return {"status": "ok", "post": payload["post"]}


# -------------------------
# REPLY TO A POST
# -------------------------
@router.post("/{post_id}/reply", response_model=dict)
async def reply_to_post(
    post_id: int,
    data: ReplyCreate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    parent_res = await db.execute(select(Post).where(Post.id == post_id))
    parent = parent_res.scalar_one_or_none()
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

    reply = Post(
        content=data.content,
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
            "parent_id": reply.parent_id,
            "user": {
                "id": current_user.id,
                "full_name": current_user.full_name,
                "avatar_url": current_user.avatar_url,
            },
            "created_at": str(reply.created_at),
        },
    }

    await manager.broadcast_thread(reply.thread_id, payload)

    # notify parent owner (via Redis pub/sub) if different user
    if getattr(parent, "user_id", None) and parent.user_id != current_user.id:
        notif = {
            "type": "reply_notification",
            "message": f"{current_user.full_name} replied to your post",
            "post": payload["post"],
            "thread_id": reply.thread_id,
        }
        await publish_notification(parent.user_id, notif)

    return {"status": "ok", "reply": payload["post"]}


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
        await db.delete(post)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete post",
        )

    payload = {"type": "post_deleted", "thread_id": post.thread_id, "post_id": post_id}
    await manager.broadcast_thread(post.thread_id, payload)
    return {"status": "ok", "deleted_post_id": post_id}


# -------------------------
# GET ALL POSTS FOR A THREAD (TREE)
# -------------------------
@router.get("/thread/{thread_id}", response_model=PostsResponse)
async def get_posts(thread_id: int, db: AsyncSession = Depends(get_db)):
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
