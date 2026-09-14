from datetime import datetime

from pydantic import BaseModel


class NotificationOut(BaseModel):
    id: int
    type: str
    is_read: bool
    created_at: datetime
    actor_nickname: str
    actor_avatar_url: str
    actor_deleted: bool
    page_id: int
    comment_id: int | None
    comment_preview: str
    summary: str


class NotificationListOut(BaseModel):
    items: list[NotificationOut]
    total: int
    limit: int
    offset: int


class UnreadCountOut(BaseModel):
    count: int
