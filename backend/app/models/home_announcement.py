from datetime import datetime

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base

DEFAULT_HOME_TITLE = "欢迎来到沸腾群岛！"


class HomeAnnouncement(Base):
    """首页顶栏公告标题（仅一行，id 固定为 1）。"""

    __tablename__ = "home_announcement"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(80), nullable=False, default=DEFAULT_HOME_TITLE)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
