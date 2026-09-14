from datetime import datetime

from pydantic import BaseModel


class HomeAnnouncementOut(BaseModel):
    title: str
    updated_at: datetime | None = None
