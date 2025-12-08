from pydantic import BaseModel
from typing import Optional


class ThreadCreate(BaseModel):
    title: str
    description: Optional[str] = None
