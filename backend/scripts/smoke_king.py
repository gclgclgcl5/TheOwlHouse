"""长寿之王服务规则冒烟（独立内存库，不碰线上 data/app.db）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi import HTTPException
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.comment import Comment
from app.models.king import KingSlot, KingVersion
from app.models.user import User
from app.services import king as king_service
from app.services.auth import hash_password


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def main() -> None:
    db = _session()
    a = king_service.create_default_version(db, name="默认", cover_path="king_covers/a.png")
    try:
        king_service.delete_version(db, a)
        raise SystemExit("default version should not be deletable")
    except HTTPException as exc:
        assert exc.status_code == 400

    s1 = king_service.append_global_page(db, a, title="第一页", image_path="comics/a1.png")
    king_service.append_global_page(db, a, title="第二页", image_path="comics/a2.png")
    assert king_service.slot_count(db) == 2
    assert s1.page_no == 1

    b = king_service.create_version(db, name="汉化组B", cover_path="king_covers/b.png")
    assert king_service.pending_count(db, b.id) == 2

    try:
        king_service.append_global_page(db, b, title="第三页", image_path="comics/b3.png")
        raise SystemExit("B should not append while pending")
    except HTTPException as exc:
        assert king_service.PENDING_APPEND_HINT in str(exc.detail)

    slots = list(db.scalars(select(KingSlot).order_by(KingSlot.page_no.asc())).all())
    king_service.upsert_version_slot(
        db, b, slots[0], title="第一页改", image_path="comics/b1.png"
    )
    assert slots[0].title == "第一页改"
    a_rows = king_service.list_version_slots(db, a.id)
    assert a_rows[0].title == "第一页改"
    assert king_service.pending_count(db, b.id) == 1

    king_service.upsert_version_slot(db, b, slots[1], image_path="comics/b2.png")
    assert king_service.pending_count(db, b.id) == 0

    s3 = king_service.append_global_page(db, b, title="第三页", image_path="comics/b3.png")
    assert s3.page_no == 3
    assert king_service.pending_count(db, a.id) == 1

    user = User(
        nickname="smoke_king",
        password_hash=hash_password("x"),
        avatar_path="avatars/x.png",
        is_deleted=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.add(
        Comment(
            page_id=None,
            king_slot_id=slots[0].id,
            user_id=user.id,
            content="共享评论",
        )
    )
    db.commit()

    king_service.delete_version(db, b)
    assert db.get(KingVersion, b.id) is None
    assert king_service.slot_count(db) == 3
    leftover = db.scalar(
        select(func.count()).select_from(Comment).where(Comment.king_slot_id == slots[0].id)
    )
    assert leftover == 1
    assert king_service.default_version(db).id == a.id
    print("smoke_king: ok")


if __name__ == "__main__":
    main()
