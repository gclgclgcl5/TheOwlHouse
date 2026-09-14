from datetime import datetime

from pydantic import BaseModel


class AdminUserOut(BaseModel):
    id: int
    nickname: str
    avatar_url: str
    created_at: datetime
    is_deleted: bool

    model_config = {"from_attributes": True}


class AdminUserListOut(BaseModel):
    items: list[AdminUserOut]
    total: int
    limit: int
    offset: int
