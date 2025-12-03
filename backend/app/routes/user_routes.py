from typing import Any

from fastapi import APIRouter, Depends

from app.auth.firebase_auth import get_current_user
from app.database.models import User
from app.schemas.responses import UserWithThreads

router = APIRouter()


@router.get("/me", response_model=UserWithThreads)
async def get_me(current_user: Any = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "avatar_url": current_user.avatar_url,
        "firebase_uid": current_user.firebase_uid,
        "created_at": (
            current_user.created_at.isoformat()
            if getattr(current_user, "created_at", None) is not None
            else None
        ),
        "threads": [
            {
                "thread_id": m.thread_id,
                "thread_title": m.thread.title,
                "role": m.role.value,
                "joined_at": (
                    m.joined_at.isoformat()
                    if getattr(m, "joined_at", None) is not None
                    else None
                ),
            }
            for m in current_user.thread_memberships
        ],
    }
