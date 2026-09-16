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


def _table_cols(conn, table: str) -> set[str]:
    rows = conn.execute(text(f"PRAGMA table_info({table})")).fetchall()
    return {row[1] for row in rows}


def _rebuild_comments(conn) -> None:
    cols = _table_cols(conn, "comments")
    if not cols:
        return
    if "king_slot_id" in cols:
        return
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        text(
            """
            CREATE TABLE comments_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                page_id INTEGER,
                king_slot_id INTEGER,
                user_id INTEGER NOT NULL,
                parent_id INTEGER,
                reply_to_id INTEGER,
                content VARCHAR(500) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(page_id) REFERENCES comic_pages(id) ON DELETE CASCADE,
                FOREIGN KEY(king_slot_id) REFERENCES king_slots(id) ON DELETE CASCADE,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(parent_id) REFERENCES comments(id) ON DELETE CASCADE,
                FOREIGN KEY(reply_to_id) REFERENCES comments(id) ON DELETE SET NULL
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO comments_new (
                id, page_id, king_slot_id, user_id, parent_id, reply_to_id, content, created_at
            )
            SELECT id, page_id, NULL, user_id, parent_id, reply_to_id, content, created_at
            FROM comments
            """
        )
    )
    conn.execute(text("DROP TABLE comments"))
    conn.execute(text("ALTER TABLE comments_new RENAME TO comments"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_page_id ON comments (page_id)"))
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_comments_king_slot_id ON comments (king_slot_id)")
    )
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_user_id ON comments (user_id)"))
    conn.execute(text("CREATE INDEX IF NOT EXISTS ix_comments_parent_id ON comments (parent_id)"))
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_comments_reply_to_id ON comments (reply_to_id)")
    )


def _rebuild_notifications(conn) -> None:
    cols = _table_cols(conn, "notifications")
    if not cols:
        return
    if "king_slot_id" in cols:
        return
    conn.execute(text("PRAGMA foreign_keys=OFF"))
    conn.execute(
        text(
            """
            CREATE TABLE notifications_new (
                id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                recipient_id INTEGER NOT NULL,
                actor_id INTEGER NOT NULL,
                type VARCHAR(16) NOT NULL,
                comment_id INTEGER,
                page_id INTEGER,
                king_slot_id INTEGER,
                comment_preview VARCHAR(80) NOT NULL DEFAULT '',
                is_read BOOLEAN NOT NULL DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP NOT NULL,
                FOREIGN KEY(recipient_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(actor_id) REFERENCES users(id) ON DELETE CASCADE,
                FOREIGN KEY(comment_id) REFERENCES comments(id) ON DELETE SET NULL,
                FOREIGN KEY(page_id) REFERENCES comic_pages(id) ON DELETE CASCADE,
                FOREIGN KEY(king_slot_id) REFERENCES king_slots(id) ON DELETE CASCADE
            )
            """
        )
    )
    conn.execute(
        text(
            """
            INSERT INTO notifications_new (
                id, recipient_id, actor_id, type, comment_id, page_id, king_slot_id,
                comment_preview, is_read, created_at
            )
            SELECT id, recipient_id, actor_id, type, comment_id, page_id, NULL,
                   comment_preview, is_read, created_at
            FROM notifications
            """
        )
    )
    conn.execute(text("DROP TABLE notifications"))
    conn.execute(text("ALTER TABLE notifications_new RENAME TO notifications"))
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_recipient_id ON notifications (recipient_id)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_notifications_actor_id ON notifications (actor_id)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_comment_id ON notifications (comment_id)"
        )
    )
    conn.execute(
        text("CREATE INDEX IF NOT EXISTS ix_notifications_page_id ON notifications (page_id)")
    )
    conn.execute(
        text(
            "CREATE INDEX IF NOT EXISTS ix_notifications_king_slot_id ON notifications (king_slot_id)"
        )
    )


def _ensure_schema() -> None:
    """为已有 SQLite 补列 / 重建约束（create_all 不会改旧表）。"""
    with engine.begin() as conn:
        rows = conn.execute(text("PRAGMA table_info(comments)")).fetchall()
        if rows:
            cols = {row[1] for row in rows}
            if "reply_to_id" not in cols and "king_slot_id" not in cols:
                conn.execute(text("ALTER TABLE comments ADD COLUMN reply_to_id INTEGER"))
        _rebuild_comments(conn)
        _rebuild_notifications(conn)
        king_rows = conn.execute(text("PRAGMA table_info(king_versions)")).fetchall()
        if king_rows:
            king_cols = {row[1] for row in king_rows}
            if "description" not in king_cols:
                conn.execute(
                    text(
                        "ALTER TABLE king_versions ADD COLUMN description TEXT NOT NULL DEFAULT ''"
                    )
                )


def init_db() -> None:
    # 模型完善后在此 import，再 create_all
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_schema()
