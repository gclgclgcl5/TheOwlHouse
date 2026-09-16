from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    content: str = Field(min_length=1, max_length=500)
    parent_id: int | None = None


class CommentOut(BaseModel):
    id: int
    page_id: int | None = None
    king_slot_id: int | None = None
    content: str
    created_at: datetime
    like_count: int
    liked_by_me: bool
    author_id: int
    author_nickname: str
    author_avatar_url: str
    author_deleted: bool
    parent_id: int | None = None
    reply_to_id: int | None = None
    reply_to_nickname: str | None = None
    reply_to_author_deleted: bool = False
    replies: list["CommentOut"] = []

    model_config = {"from_attributes": True}


class CommentListOut(BaseModel):
    items: list[CommentOut]


class LikeStateOut(BaseModel):
    liked: bool
    like_count: int
