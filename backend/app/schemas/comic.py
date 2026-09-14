from datetime import datetime

from pydantic import BaseModel, Field


class ComicPageOut(BaseModel):
    id: int
    title: str
    page_no: int
    image_url: str
    created_at: datetime
    updated_at: datetime
    comment_count: int = 0

    model_config = {"from_attributes": True}


class ComicPageListOut(BaseModel):
    items: list[ComicPageOut]
    total: int
    limit: int
    offset: int


class ComicPageUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    page_no: int | None = Field(default=None, ge=1)
