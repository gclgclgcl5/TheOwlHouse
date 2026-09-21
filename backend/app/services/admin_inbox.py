from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.admin_inbox import AdminInbox
from app.models.comic import ComicPage
from app.models.comment import Comment
from app.models.king import KingSlot
from app.models.user import User

PAGE_SIZE = 50
PREVIEW_LEN = 80


@dataclass
class InboxItem:
    id: int
    is_read: bool
    author_nickname: str
    preview: str
    created_at: datetime
    page_no: int | None
    page_title: str
    page_id: int | None
    king_slot_id: int | None


def _preview(content: str) -> str:
    text = content.strip().replace("\n", " ")
    if len(text) <= PREVIEW_LEN:
        return text
    return text[: PREVIEW_LEN - 1] + "…"


def _nickname(db: Session, user_id: int) -> str:
    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        return "已注销用户"
    return user.nickname


def record_for_comment(db: Session, comment: Comment) -> AdminInbox | None:
    """为一条评论写入收件行。已存在则跳过。不 commit。"""
    if comment.page_id is None and comment.king_slot_id is None:
        return None
    existing = db.scalar(select(AdminInbox).where(AdminInbox.comment_id == comment.id))
    if existing is not None:
        return existing
    row = AdminInbox(
        comment_id=comment.id,
        page_id=comment.page_id,
        king_slot_id=comment.king_slot_id,
        author_nickname=_nickname(db, comment.user_id),
        preview=_preview(comment.content),
        is_read=False,
        created_at=comment.created_at,
    )
    db.add(row)
    return row


def backfill_missing(db: Session) -> int:
    """把尚无收件行的评论补成未读。"""
    missing = list(
        db.scalars(
            select(Comment)
            .outerjoin(AdminInbox, AdminInbox.comment_id == Comment.id)
            .where(AdminInbox.id.is_(None))
        ).all()
    )
    added = 0
    for comment in missing:
        if record_for_comment(db, comment) is not None:
            added += 1
    if added:
        db.commit()
    return added


def _section_filter(section: str):
    if section == "doujin":
        return AdminInbox.page_id.is_not(None)
    if section == "king":
        return AdminInbox.king_slot_id.is_not(None)
    raise ValueError(section)


def unread_count(db: Session, section: str) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(AdminInbox)
            .where(_section_filter(section), AdminInbox.is_read.is_(False))
        )
        or 0
    )


def list_section(
    db: Session, section: str, *, page: int = 1
) -> tuple[list[InboxItem], int]:
    filt = _section_filter(section)
    total = int(
        db.scalar(select(func.count()).select_from(AdminInbox).where(filt)) or 0
    )
    page = max(1, page)
    offset = (page - 1) * PAGE_SIZE
    rows = list(
        db.scalars(
            select(AdminInbox)
            .where(filt)
            .order_by(AdminInbox.created_at.desc(), AdminInbox.id.desc())
            .offset(offset)
            .limit(PAGE_SIZE)
        ).all()
    )
    page_ids = [r.page_id for r in rows if r.page_id is not None]
    slot_ids = [r.king_slot_id for r in rows if r.king_slot_id is not None]
    pages = {}
    if page_ids:
        pages = {
            p.id: p
            for p in db.scalars(select(ComicPage).where(ComicPage.id.in_(page_ids))).all()
        }
    slots = {}
    if slot_ids:
        slots = {
            s.id: s
            for s in db.scalars(select(KingSlot).where(KingSlot.id.in_(slot_ids))).all()
        }
    items: list[InboxItem] = []
    for row in rows:
        page_no = None
        title = ""
        if row.page_id is not None and row.page_id in pages:
            page_no = pages[row.page_id].page_no
            title = pages[row.page_id].title
        elif row.king_slot_id is not None and row.king_slot_id in slots:
            page_no = slots[row.king_slot_id].page_no
            title = slots[row.king_slot_id].title
        items.append(
            InboxItem(
                id=row.id,
                is_read=row.is_read,
                author_nickname=row.author_nickname,
                preview=row.preview,
                created_at=row.created_at,
                page_no=page_no,
                page_title=title,
                page_id=row.page_id,
                king_slot_id=row.king_slot_id,
            )
        )
    return items, total


def get_item(db: Session, item_id: int) -> AdminInbox | None:
    return db.get(AdminInbox, item_id)


def mark_read(db: Session, item: AdminInbox) -> None:
    if not item.is_read:
        item.is_read = True
        db.add(item)
        db.commit()


def mark_section_read(db: Session, section: str) -> None:
    rows = list(db.scalars(select(AdminInbox).where(_section_filter(section), AdminInbox.is_read.is_(False))).all())
    for row in rows:
        row.is_read = True
        db.add(row)
    if rows:
        db.commit()


def _expunge_inbox(db: Session, comment_ids: set[int] | None = None, page_id: int | None = None) -> None:
    for obj in list(db.identity_map.values()):
        if not isinstance(obj, AdminInbox):
            continue
        if comment_ids is not None and obj.comment_id in comment_ids:
            db.expunge(obj)
        elif page_id is not None and obj.page_id == page_id:
            db.expunge(obj)


def delete_for_comments(db: Session, comment_ids: list[int]) -> None:
    if not comment_ids:
        return
    _expunge_inbox(db, comment_ids=set(comment_ids))
    db.execute(delete(AdminInbox).where(AdminInbox.comment_id.in_(comment_ids)))


def delete_for_page(db: Session, page_id: int) -> None:
    _expunge_inbox(db, page_id=page_id)
    db.execute(delete(AdminInbox).where(AdminInbox.page_id == page_id))
