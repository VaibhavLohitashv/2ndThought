from pydantic import BaseModel


class ThreadCreate(BaseModel):
    title: str
    description: str
