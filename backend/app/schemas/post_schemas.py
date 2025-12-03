from pydantic import BaseModel


class PostCreate(BaseModel):
    thread_id: int
    content: str


class ReplyCreate(BaseModel):
    content: str
