from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user import User
from app.schemas.notification import NotificationOut
from app.services.storage import media_url


def _preview(text: str, limit: int = 80) -> str:
    text = (text or "").strip().replace("\n", " ")
    if len(text) <= limit:
        return text
    return text[: limit - 1] + "…"


def _actor_display(user: User) -> tuple[str, str, bool]:
    if user.is_deleted:
        return "已注销用户", "", True
    return user.nickname, media_url(user.avatar_path), False


def _summary(notif_type: str, actor_nickname: str) -> str:
    if notif_type == "like":
        return f"{actor_nickname} 赞了你的评论"
    if notif_type == "reply":
        return f"{actor_nickname} 回复了你"
    return f"{actor_nickname} 与你互动"


def create_notification(
    db: Session,
    *,
    recipient_id: int,
    actor_id: int,
    notif_type: str,
    page_id: int | None = None,
    king_slot_id: int | None = None,
    comment_id: int | None,
    preview: str,
) -> Notification | None:
    if recipient_id == actor_id:
        return None
    notif = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        type=notif_type,
        page_id=page_id,
        king_slot_id=king_slot_id,
        comment_id=comment_id,
        comment_preview=_preview(preview),
        is_read=False,
    )
    db.add(notif)
    db.commit()
    db.refresh(notif)
    return notif


def _to_out(notif: Notification, actor: User) -> NotificationOut:
    nick, avatar, deleted = _actor_display(actor)
    return NotificationOut(
        id=notif.id,
        type=notif.type,
        is_read=notif.is_read,
        created_at=notif.created_at,
        actor_nickname=nick,
        actor_avatar_url=avatar,
        actor_deleted=deleted,
        page_id=notif.page_id,
        king_slot_id=notif.king_slot_id,
        comment_id=notif.comment_id,
        comment_preview=notif.comment_preview,
        summary=_summary(notif.type, nick),
    )


def list_notifications(
    db: Session,
    user_id: int,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[NotificationOut], int]:
    total = (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.recipient_id == user_id)
        )
        or 0
    )
    rows = list(
        db.scalars(
            select(Notification)
            .where(Notification.recipient_id == user_id)
            .order_by(Notification.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    if not rows:
        return [], int(total)
    actor_ids = {n.actor_id for n in rows}
    actors = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(actor_ids))).all()
    }
    items = [_to_out(n, actors[n.actor_id]) for n in rows if n.actor_id in actors]
    return items, int(total)


def unread_count(db: Session, user_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(
                Notification.recipient_id == user_id,
                Notification.is_read.is_(False),
            )
        )
        or 0
    )


def mark_read(db: Session, user_id: int, notif_id: int) -> NotificationOut:
    notif = db.get(Notification, notif_id)
    if notif is None or notif.recipient_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    if not notif.is_read:
        notif.is_read = True
        db.add(notif)
        db.commit()
        db.refresh(notif)
    actor = db.get(User, notif.actor_id)
    assert actor is not None
    return _to_out(notif, actor)


def mark_all_read(db: Session, user_id: int) -> int:
    result = db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == user_id,
            Notification.is_read.is_(False),
        )
        .values(is_read=True)
    )
    db.commit()
    return int(result.rowcount or 0)


def nullify_comment_refs(db: Session, comment_ids: list[int]) -> None:
    if not comment_ids:
        return
    db.execute(
        update(Notification)
        .where(Notification.comment_id.in_(comment_ids))
        .values(comment_id=None)
    )
    db.commit()
