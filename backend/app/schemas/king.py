from datetime import datetime

from pydantic import BaseModel

from app.schemas.comment import CommentOut


class KingVersionOut(BaseModel):
    id: int
    name: str
    cover_url: str
    description: str = ""
    is_default: bool
    uploaded_count: int
    created_at: datetime


class KingVersionListOut(BaseModel):
    items: list[KingVersionOut]


class KingPageOut(BaseModel):
    slot_id: int
    page_no: int
    title: str
    image_url: str
    comment_count: int


class KingPageListOut(BaseModel):
    version_id: int
    version_name: str
    description: str = ""
    items: list[KingPageOut]


class KingResolveOut(BaseModel):
    version_id: int
    version_name: str
    switched: bool
    slot_id: int
    page_no: int
    title: str
    image_url: str
    comment_count: int


class KingCommentListOut(BaseModel):
    items: list[CommentOut]
