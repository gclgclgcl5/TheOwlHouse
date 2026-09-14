from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AppUpdateConfig(Base):
    """全局 App 更新配置（仅保留一行，id 固定为 1）。"""

    __tablename__ = "app_update_config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    version_code: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    version_name: Mapped[str] = mapped_column(String(32), nullable=False, default="")
    download_url: Mapped[str] = mapped_column(String(1024), nullable=False, default="")
    message: Mapped[str] = mapped_column(Text, nullable=False, default="")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
