from collections.abc import Generator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import ensure_data_dirs, settings

ensure_data_dirs()

engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_schema() -> None:
    """为已有 SQLite 补列（create_all 不会改旧表）。"""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(comments)")).fetchall()
        if not rows:
            return
        cols = {row[1] for row in rows}
        if "reply_to_id" not in cols:
            conn.execute(text("ALTER TABLE comments ADD COLUMN reply_to_id INTEGER"))


def init_db() -> None:
    # 模型完善后在此 import，再 create_all
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema()
