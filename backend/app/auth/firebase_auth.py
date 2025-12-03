from typing import Any

import firebase_admin
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.database.db import SessionLocal
from app.database.models import ThreadMembership, User

# Initialize Firebase Admin once
if not firebase_admin._apps:
    cred = credentials.Certificate(settings.GOOGLE_APPLICATION_CREDENTIALS)
    firebase_admin.initialize_app(cred)

# Swagger login tokenUrl is required (even if unused)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


async def get_db() -> AsyncSession:
    async with SessionLocal() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
) -> Any:
    try:
        decoded = firebase_auth.verify_id_token(token)
    except Exception:
        # firebase_admin may raise different exceptions; map to 401 for clients
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    email = decoded.get("email")
    uid = decoded.get("uid")
    name = decoded.get("name")
    picture = decoded.get("picture")

    result = await db.execute(
        select(User)
        .options(
            selectinload(User.thread_memberships).selectinload(ThreadMembership.thread)
        )
        .where(User.email == email)
    )

    user = result.scalar_one_or_none()

    # create user if not exists
    if not user:
        user = User(email=email, firebase_uid=uid, full_name=name, avatar_url=picture)
        db.add(user)
        try:
            await db.commit()
            await db.refresh(user)
        except Exception:
            # Handle race where user was created concurrently
            await db.rollback()
            result = await db.execute(select(User).where(User.email == email))
            user = result.scalar_one_or_none()
            if not user:
                # if still not found, raise a server error
                raise HTTPException(status_code=500, detail="Could not create user")

    # return the SQLAlchemy user instance (routes expect model attributes)
    return user
