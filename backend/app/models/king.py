from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class KingVersion(Base):
    __tablename__ = "king_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    cover_path: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str] = mapped_column(
        Text, default="", server_default="", nullable=False
    )
    is_default: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    images: Mapped[list["KingVersionImage"]] = relationship(
        back_populates="version",
        cascade="all, delete-orphan",
    )


class KingSlot(Base):
    __tablename__ = "king_slots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    page_no: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    images: Mapped[list["KingVersionImage"]] = relationship(back_populates="slot")


class KingVersionImage(Base):
    __tablename__ = "king_version_images"
    __table_args__ = (UniqueConstraint("version_id", "slot_id", name="uq_king_version_slot"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("king_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    slot_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("king_slots.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    image_path: Mapped[str] = mapped_column(String(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    version: Mapped[KingVersion] = relationship(back_populates="images")
    slot: Mapped[KingSlot] = relationship(back_populates="images")
