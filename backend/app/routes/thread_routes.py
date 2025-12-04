from typing import Any, List

from sqlalchemy import or_

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.auth.firebase_auth import get_current_user
from app.database.db import SessionLocal
from app.database.models import Thread, ThreadMembership, ThreadRole, User
from app.schemas.responses import ThreadRead
from app.schemas.thread_schemas import ThreadCreate

router = APIRouter(tags=["Threads"])


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


@router.get("/search", response_model=List[ThreadRead])
async def search_threads(q: str, db: AsyncSession = Depends(get_db)):
    # simple search across title and description (case-insensitive)
    if not q or not q.strip():
        return []
    pattern = f"%{q}%"
    res = await db.execute(
        select(Thread).where(
            or_(Thread.title.ilike(pattern), Thread.description.ilike(pattern))
        )
    )
    threads = res.scalars().all()
    out = []
    for t in threads:
        creator_name = None
        try:
            creator = await db.get(User, getattr(t, "created_by", None))
            creator_name = getattr(creator, "full_name", None)
        except Exception:
            creator_name = None
        created_by_val = getattr(t, "created_by", None)
        try:
            created_by_val = int(created_by_val) if created_by_val is not None else 0
        except Exception:
            created_by_val = 0
        out.append(
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "created_by": created_by_val,
                "created_by_name": creator_name,
                "members": [],
            }
        )
    return out


@router.post("/", response_model=dict)
async def create_thread(
    data: ThreadCreate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    thread = Thread(
        title=data.title,
        description=getattr(data, "description", None),
        created_by=current_user.id,
    )
    db.add(thread)
    await db.flush()
    membership = ThreadMembership(
        thread_id=thread.id, user_id=current_user.id, role=ThreadRole.admin
    )
    db.add(membership)
    try:
        await db.commit()
        await db.refresh(thread)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not create thread",
        )
    return {
        "status": "ok",
        "thread": {
            "id": thread.id,
            "title": thread.title,
            "description": thread.description,
        },
    }


@router.get("/{thread_id}", response_model=ThreadRead)
async def get_thread(thread_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )
    members_res = await db.execute(
        select(ThreadMembership).where(ThreadMembership.thread_id == thread_id)
    )
    members = members_res.scalars().all()
    # resolve creator name
    creator_name = None
    try:
        creator = await db.get(User, getattr(thread, "created_by", None))
        creator_name = getattr(creator, "full_name", None)
    except Exception:
        creator_name = None

    members_out = []
    for m in members:
        user_full = None
        try:
            u = await db.get(User, getattr(m, "user_id", None))
            user_full = getattr(u, "full_name", None)
        except Exception:
            user_full = None
        members_out.append(
            {
                "user_id": m.user_id,
                "role": m.role.value,
                "joined_at": m.joined_at,
                "user_full_name": user_full,
            }
        )

    return {
        "id": thread.id,
        "title": thread.title,
        "description": thread.description,
        "created_by": thread.created_by,
        "created_by_name": creator_name,
        "members": members_out,
    }


@router.get("/", response_model=List[ThreadRead])
async def list_threads(db: AsyncSession = Depends(get_db)):
    # join with users to include creator name
    res = await db.execute(
        select(Thread).join(User, Thread.created_by == User.id).options()
    )
    threads = res.scalars().all()
    # build a simple payload including creator name
    out = []
    for t in threads:
        # try to fetch the user if relationship not loaded
        creator_name = None
        try:
            # attempt attribute access -- may not be present
            creator = await db.get(User, getattr(t, "created_by", None))
            creator_name = getattr(creator, "full_name", None)
        except Exception:
            creator_name = None
        created_by_val = getattr(t, "created_by", None)
        try:
            created_by_val = int(created_by_val) if created_by_val is not None else 0
        except Exception:
            created_by_val = 0
        out.append(
            {
                "id": t.id,
                "title": t.title,
                "description": t.description,
                "created_by": created_by_val,
                "created_by_name": creator_name,
                "members": [],
            }
        )
    return out


@router.put("/{thread_id}")
async def update_thread(
    thread_id: int,
    data: ThreadCreate,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not mem or mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can update the thread",
        )

    thread.title = data.title
    thread.description = getattr(data, "description", thread.description)
    try:
        db.add(thread)
        await db.commit()
        await db.refresh(thread)
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not update thread",
        )
    return {
        "status": "ok",
        "thread": {
            "id": thread.id,
            "title": thread.title,
            "description": thread.description,
        },
    }


@router.delete("/{thread_id}")
async def delete_thread(
    thread_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = result.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not mem or mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can delete the thread",
        )

    try:
        await db.delete(thread)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not delete thread",
        )
    return {"status": "ok", "deleted_thread_id": thread_id}


@router.post("/{thread_id}/add-moderator/{user_id}")
async def add_moderator(
    thread_id: int,
    user_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requester_mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not requester_mem or requester_mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can add moderators",
        )

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user_id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if membership:
        membership.role = ThreadRole.moderator
    else:
        membership = ThreadMembership(
            thread_id=thread_id, user_id=user_id, role=ThreadRole.moderator
        )
        db.add(membership)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not add moderator",
        )
    return {"status": "ok", "user_id": user_id, "role": ThreadRole.moderator.value}


@router.post("/{thread_id}/make-admin/{user_id}")
async def make_admin(
    thread_id: int,
    user_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requester_mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not requester_mem or requester_mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can set admins",
        )

    user_res = await db.execute(select(User).where(User.id == user_id))
    user = user_res.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
        )

    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user_id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if membership:
        membership.role = ThreadRole.admin
    else:
        membership = ThreadMembership(
            thread_id=thread_id, user_id=user_id, role=ThreadRole.admin
        )
        db.add(membership)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not set admin",
        )
    return {"status": "ok", "user_id": user_id, "role": ThreadRole.admin.value}


@router.post("/{thread_id}/promote/{user_id}")
async def promote_member(
    thread_id: int,
    user_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requester_mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not requester_mem or requester_mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can promote members",
        )

    # fetch existing membership if any
    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user_id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()

    # if no membership, create as moderator
    if not membership:
        membership = ThreadMembership(
            thread_id=thread_id, user_id=user_id, role=ThreadRole.moderator
        )
        db.add(membership)
        try:
            await db.commit()
        except Exception:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not promote member",
            )
        return {"status": "ok", "user_id": user_id, "role": ThreadRole.moderator.value}

    # member -> moderator
    if membership.role == ThreadRole.member:
        membership.role = ThreadRole.moderator
    # moderator -> admin
    elif membership.role == ThreadRole.moderator:
        membership.role = ThreadRole.admin
    # already admin -> noop
    else:
        return {"status": "ok", "user_id": user_id, "role": membership.role.value}

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not promote member",
        )
    return {"status": "ok", "user_id": user_id, "role": membership.role.value}


@router.post("/{thread_id}/demote/{user_id}")
async def demote_member(
    thread_id: int,
    user_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requester_mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not requester_mem or requester_mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can demote members",
        )

    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user_id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )

    # moderator -> member
    if membership.role == ThreadRole.moderator:
        membership.role = ThreadRole.member
    # admin -> moderator (ensure at least one admin remains)
    elif membership.role == ThreadRole.admin:
        admins_res = await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.role == ThreadRole.admin,
                )
            )
        )
        admins = admins_res.scalars().all()
        if len(admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote the only admin",
            )
        membership.role = ThreadRole.moderator
    # member -> noop
    else:
        return {"status": "ok", "user_id": user_id, "role": membership.role.value}

    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not demote member",
        )
    return {"status": "ok", "user_id": user_id, "role": membership.role.value}


@router.post("/{thread_id}/remove-moderator/{user_id}")
async def remove_moderator(
    thread_id: int,
    user_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    requester_mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not requester_mem or requester_mem.role != ThreadRole.admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only thread admins can remove moderators",
        )

    mem_res = await db.execute(
        select(ThreadMembership).where(
            and_(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user_id,
            )
        )
    )
    membership = mem_res.scalar_one_or_none()
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Membership not found"
        )

    membership.role = ThreadRole.member
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not demote moderator",
        )
    return {"status": "ok", "user_id": user_id, "role": membership.role.value}


@router.post("/{thread_id}/join")
async def join_thread(
    thread_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    thread_res = await db.execute(select(Thread).where(Thread.id == thread_id))
    thread = thread_res.scalar_one_or_none()
    if not thread:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Thread not found"
        )

    existing = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if existing:
        return {"status": "ok", "message": "Already a member"}

    mem = ThreadMembership(
        thread_id=thread_id, user_id=current_user.id, role=ThreadRole.member
    )
    db.add(mem)
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not join thread",
        )
    return {"status": "ok", "thread_id": thread_id}


@router.post("/{thread_id}/leave")
async def leave_thread(
    thread_id: int,
    current_user: Any = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    mem = (
        await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.user_id == current_user.id,
                )
            )
        )
    ).scalar_one_or_none()
    if not mem:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Not a member"
        )

    if mem.role == ThreadRole.admin:
        admins_res = await db.execute(
            select(ThreadMembership).where(
                and_(
                    ThreadMembership.thread_id == thread_id,
                    ThreadMembership.role == ThreadRole.admin,
                )
            )
        )
        admins = admins_res.scalars().all()
        if len(admins) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot leave thread as the only admin",
            )

    try:
        await db.delete(mem)
        await db.commit()
    except Exception:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Could not leave thread",
        )
    return {"status": "ok", "thread_id": thread_id}
