"""管理员评论收件箱冒烟（独立内存库）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.admin_inbox import AdminInbox
from app.models.comic import ComicPage
from app.models.comment import Comment
from app.models.king import KingSlot
from app.models.user import User
from app.services import admin_inbox as inbox
from app.services import comments as comments_service
from app.services.auth import hash_password


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _unread(db, section: str) -> int:
    return inbox.unread_count(db, section)


def main() -> None:
    db = _session()
    user = User(
        nickname="inbox_user",
        password_hash=hash_password("x"),
        avatar_path="avatars/x.png",
        is_deleted=False,
    )
    db.add(user)
    page = ComicPage(title="同人页", page_no=3, image_path="comics/a.png")
    slot = KingSlot(page_no=2, title="国王页")
    db.add(page)
    db.add(slot)
    db.commit()
    db.refresh(user)
    db.refresh(page)
    db.refresh(slot)

    historical = Comment(page_id=page.id, user_id=user.id, content="历史评论")
    db.add(historical)
    db.commit()
    added = inbox.backfill_missing(db)
    assert added == 1, added
    assert _unread(db, "doujin") == 1

    fresh = comments_service.create_comment(
        db, page_id=page.id, user_id=user.id, content="新评论", parent_id=None
    )
    reply = comments_service.create_comment(
        db, page_id=page.id, user_id=user.id, content="一条回复", parent_id=fresh.id
    )
    assert _unread(db, "doujin") == 3

    items, total = inbox.list_section(db, "doujin", page=1)
    assert total == 3
    target = next(i for i in items if i.preview == "新评论")
    row = inbox.get_item(db, target.id)
    assert row is not None
    inbox.mark_read(db, row)
    assert _unread(db, "doujin") == 2

    inbox.mark_section_read(db, "doujin")
    assert _unread(db, "doujin") == 0

    comments_service.delete_comment_cascade(db, fresh.id)
    left = db.scalar(select(func.count()).select_from(AdminInbox).where(AdminInbox.page_id == page.id))
    assert left == 1, left
    assert db.scalar(select(AdminInbox).where(AdminInbox.comment_id == reply.id)) is None
    assert db.scalar(select(AdminInbox).where(AdminInbox.comment_id == historical.id)) is not None

    king_hist = Comment(king_slot_id=slot.id, user_id=user.id, content="国王历史")
    db.add(king_hist)
    db.commit()
    assert inbox.backfill_missing(db) == 1
    comments_service.create_slot_comment(
        db, slot_id=slot.id, user_id=user.id, content="国王新评", parent_id=None
    )
    assert _unread(db, "king") == 2
    assert _unread(db, "doujin") == 0
    inbox.mark_section_read(db, "king")
    assert _unread(db, "king") == 0

    print("smoke_admin_inbox: ok")


if __name__ == "__main__":
    main()
