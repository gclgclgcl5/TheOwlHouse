from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AdminInbox(Base):
    """管理员评论收件箱。与读者 notifications 分开，不挂用户账号。"""

    __tablename__ = "admin_inbox"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    comment_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("comments.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    page_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    king_slot_id: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    author_nickname: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    preview: Mapped[str] = mapped_column(String(80), nullable=False, default="")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
