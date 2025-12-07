from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class UserRead(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    avatar_url: Optional[str] = None
    firebase_uid: Optional[str] = None
    created_at: Optional[str] = None

    class Config:
        model_config = {"from_attributes": True}


class UserThreadInfo(BaseModel):
    thread_id: int
    thread_title: str
    role: str
    joined_at: str


class UserWithThreads(UserRead):
    threads: List[UserThreadInfo] = []


class PostRead(BaseModel):
    id: int
    content: str
    image_url: Optional[str] = None
    parent_id: Optional[int] = None
    user: UserRead
    created_at: datetime
    children: List["PostRead"] = []

    class Config:
        model_config = {"from_attributes": True}


class ThreadMember(BaseModel):
    user_id: int
    role: str
    joined_at: datetime
    user_full_name: Optional[str] = None


class ThreadRead(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    created_by: int
    created_by_name: Optional[str] = None
    members: List[ThreadMember] = []

    class Config:
        model_config = {"from_attributes": True}


class PostsResponse(BaseModel):
    thread_id: int
    posts: List[PostRead]


# fix forward refs for recursive PostRead
PostRead.update_forward_refs()
