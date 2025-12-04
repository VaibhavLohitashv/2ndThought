from typing import Any

import firebase_admin.auth as firebase_auth
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.database.db import SessionLocal
from app.database.models import ThreadMembership, User
from app.utils.websocket_manager import manager

router = APIRouter(tags=["WebSockets"])


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def _get_user_from_token(token: str, db: AsyncSession) -> Any:
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token"
        )

    email = decoded.get("email")
    if not email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload"
        )

    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user:
        # minimal fallback creation
        user = User(
            email=email,
            firebase_uid=decoded.get("uid"),
            full_name=decoded.get("name"),
            avatar_url=decoded.get("picture"),
        )
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception:
            await db.rollback()
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                raise HTTPException(status_code=500, detail="Could not create user")
    return user


@router.websocket("/ws/thread/{thread_id}")
async def ws_thread(websocket: WebSocket, thread_id: int):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    # ensure DB context will be created via SessionLocal below
    async with SessionLocal() as session:
        try:
            user = await _get_user_from_token(token, session)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        mem_res = await session.execute(
            select(ThreadMembership).where(
                ThreadMembership.thread_id == thread_id,
                ThreadMembership.user_id == user.id,
            )
        )
        mem = mem_res.scalar_one_or_none()
        if not mem:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        await manager.connect_thread(thread_id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect_thread(thread_id, websocket)


@router.websocket("/ws/notifications")
async def ws_notifications(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
        return

    async with SessionLocal() as session:
        try:
            user = await _get_user_from_token(token, session)
        except HTTPException:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        await websocket.accept()
        await manager.connect_user(user.id, websocket)
        try:
            while True:
                await websocket.receive_text()
        except WebSocketDisconnect:
            await manager.disconnect_user(user.id, websocket)
