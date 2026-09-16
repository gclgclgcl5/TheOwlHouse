from collections import defaultdict

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.orm import Session

from app.models.comic import ComicPage
from app.models.comment import Comment
from app.models.like import Like
from app.models.user import User
from app.schemas.comment import CommentOut
from app.services import notifications as notifications_service
from app.services.storage import media_url


def author_display(user: User) -> tuple[str, str, bool]:
    if user.is_deleted:
        return "已注销用户", "", True
    return user.nickname, media_url(user.avatar_path), False


def _like_counts(db: Session, comment_ids: list[int]) -> dict[int, int]:
    if not comment_ids:
        return {}
    rows = db.execute(
        select(Like.comment_id, func.count())
        .where(Like.comment_id.in_(comment_ids))
        .group_by(Like.comment_id)
    ).all()
    return {cid: int(cnt) for cid, cnt in rows}


def _liked_set(db: Session, user_id: int | None, comment_ids: list[int]) -> set[int]:
    if user_id is None or not comment_ids:
        return set()
    rows = db.scalars(
        select(Like.comment_id).where(
            Like.user_id == user_id,
            Like.comment_id.in_(comment_ids),
        )
    ).all()
    return set(rows)


def _reply_to_display(
    comment: Comment,
    comments_by_id: dict[int, Comment],
    users: dict[int, User],
) -> tuple[int | None, str | None, bool]:
    """仅当 reply_to 目标本身是楼中楼时填充昵称。"""
    reply_to_id = comment.reply_to_id
    if reply_to_id is None:
        return None, None, False
    target = comments_by_id.get(reply_to_id)
    if target is None or target.parent_id is None:
        return reply_to_id, None, False
    author = users.get(target.user_id)
    if author is None:
        return reply_to_id, None, False
    nick, _, deleted = author_display(author)
    return reply_to_id, nick, deleted


def _to_out(
    comment: Comment,
    user: User,
    *,
    like_count: int,
    liked_by_me: bool,
    replies: list[CommentOut] | None = None,
    reply_to_id: int | None = None,
    reply_to_nickname: str | None = None,
    reply_to_author_deleted: bool = False,
) -> CommentOut:
    nick, avatar, deleted = author_display(user)
    return CommentOut(
        id=comment.id,
        page_id=comment.page_id,
        king_slot_id=comment.king_slot_id,
        content=comment.content,
        created_at=comment.created_at,
        like_count=like_count,
        liked_by_me=liked_by_me,
        author_id=user.id,
        author_nickname=nick,
        author_avatar_url=avatar,
        author_deleted=deleted,
        parent_id=comment.parent_id,
        reply_to_id=reply_to_id if reply_to_id is not None else comment.reply_to_id,
        reply_to_nickname=reply_to_nickname,
        reply_to_author_deleted=reply_to_author_deleted,
        replies=replies or [],
    )


def _assemble_comments(
    db: Session,
    comments: list[Comment],
    current_user_id: int | None,
    *,
    sort: str,
) -> list[CommentOut]:
    if not comments:
        return []

    comments_by_id = {c.id: c for c in comments}
    user_ids = {c.user_id for c in comments}
    for c in comments:
        if c.reply_to_id is not None:
            target = comments_by_id.get(c.reply_to_id)
            if target is not None:
                user_ids.add(target.user_id)
    users = {
        u.id: u
        for u in db.scalars(select(User).where(User.id.in_(user_ids))).all()
    }
    ids = [c.id for c in comments]
    counts = _like_counts(db, ids)
    liked = _liked_set(db, current_user_id, ids)

    children: dict[int | None, list[Comment]] = defaultdict(list)
    for c in comments:
        children[c.parent_id].append(c)

    tops = children.get(None, [])
    result: list[CommentOut] = []
    for top in tops:
        author = users[top.user_id]
        reply_outs: list[CommentOut] = []
        for reply in children.get(top.id, []):
            r_author = users[reply.user_id]
            rtid, rtnick, rtdel = _reply_to_display(reply, comments_by_id, users)
            reply_outs.append(
                _to_out(
                    reply,
                    r_author,
                    like_count=counts.get(reply.id, 0),
                    liked_by_me=reply.id in liked,
                    replies=[],
                    reply_to_id=rtid,
                    reply_to_nickname=rtnick,
                    reply_to_author_deleted=rtdel,
                )
            )
        tid, tnick, tdel = _reply_to_display(top, comments_by_id, users)
        result.append(
            _to_out(
                top,
                author,
                like_count=counts.get(top.id, 0),
                liked_by_me=top.id in liked,
                replies=reply_outs,
                reply_to_id=tid,
                reply_to_nickname=tnick,
                reply_to_author_deleted=tdel,
            )
        )

    if sort == "hot":
        result.sort(key=lambda c: (c.like_count, c.created_at, c.id), reverse=True)
    else:
        result.sort(key=lambda c: (c.created_at, c.id), reverse=True)
    return result


def list_page_comments(
    db: Session,
    page_id: int,
    current_user_id: int | None,
    *,
    sort: str = "latest",
) -> list[CommentOut]:
    page = db.get(ComicPage, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    if sort not in ("latest", "hot"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="排序参数无效")

    comments = list(
        db.scalars(
            select(Comment)
            .where(Comment.page_id == page_id)
            .order_by(Comment.created_at.asc())
        ).all()
    )
    return _assemble_comments(db, comments, current_user_id, sort=sort)


def list_slot_comments(
    db: Session,
    slot_id: int,
    current_user_id: int | None,
    *,
    sort: str = "latest",
) -> list[CommentOut]:
    from app.models.king import KingSlot

    slot = db.get(KingSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    if sort not in ("latest", "hot"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="排序参数无效")

    comments = list(
        db.scalars(
            select(Comment)
            .where(Comment.king_slot_id == slot_id)
            .order_by(Comment.created_at.asc())
        ).all()
    )
    return _assemble_comments(db, comments, current_user_id, sort=sort)


def _resolve_parent_id(db: Session, page_id: int, parent_id: int | None) -> int | None:
    if parent_id is None:
        return None
    parent = db.get(Comment, parent_id)
    if parent is None or parent.page_id != page_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回复目标不存在")
    # 拍平：若回复的是回复，挂到顶层
    if parent.parent_id is not None:
        return parent.parent_id
    return parent.id


def create_comment(
    db: Session,
    *,
    page_id: int,
    user_id: int,
    content: str,
    parent_id: int | None,
) -> CommentOut:
    page = db.get(ComicPage, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    text = content.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论不能为空")
    if len(text) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论过长")

    target: Comment | None = None
    if parent_id is not None:
        target = db.get(Comment, parent_id)
        if target is None or target.page_id != page_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回复目标不存在")

    resolved_parent = _resolve_parent_id(db, page_id, parent_id)
    reply_to_id = target.id if target is not None else None

    comment = Comment(
        page_id=page_id,
        user_id=user_id,
        parent_id=resolved_parent,
        reply_to_id=reply_to_id,
        content=text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    if target is not None:
        notifications_service.create_notification(
            db,
            recipient_id=target.user_id,
            actor_id=user_id,
            notif_type="reply",
            page_id=page_id,
            comment_id=comment.id,
            preview=text,
        )

    user = db.get(User, user_id)
    assert user is not None

    rtid, rtnick, rtdel = None, None, False
    if target is not None and target.parent_id is not None:
        t_author = db.get(User, target.user_id)
        if t_author is not None:
            rtnick, _, rtdel = author_display(t_author)
            rtid = target.id

    return _to_out(
        comment,
        user,
        like_count=0,
        liked_by_me=False,
        replies=[],
        reply_to_id=rtid if rtid is not None else comment.reply_to_id,
        reply_to_nickname=rtnick,
        reply_to_author_deleted=rtdel,
    )


def _resolve_slot_parent_id(
    db: Session, slot_id: int, parent_id: int | None
) -> int | None:
    if parent_id is None:
        return None
    parent = db.get(Comment, parent_id)
    if parent is None or parent.king_slot_id != slot_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回复目标不存在")
    if parent.parent_id is not None:
        return parent.parent_id
    return parent.id


def create_slot_comment(
    db: Session,
    *,
    slot_id: int,
    user_id: int,
    content: str,
    parent_id: int | None,
) -> CommentOut:
    from app.models.king import KingSlot

    slot = db.get(KingSlot, slot_id)
    if slot is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    text = content.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论不能为空")
    if len(text) > 500:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="评论过长")

    target: Comment | None = None
    if parent_id is not None:
        target = db.get(Comment, parent_id)
        if target is None or target.king_slot_id != slot_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回复目标不存在")

    resolved_parent = _resolve_slot_parent_id(db, slot_id, parent_id)
    reply_to_id = target.id if target is not None else None

    comment = Comment(
        page_id=None,
        king_slot_id=slot_id,
        user_id=user_id,
        parent_id=resolved_parent,
        reply_to_id=reply_to_id,
        content=text,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)

    if target is not None:
        notifications_service.create_notification(
            db,
            recipient_id=target.user_id,
            actor_id=user_id,
            notif_type="reply",
            page_id=None,
            king_slot_id=slot_id,
            comment_id=comment.id,
            preview=text,
        )

    user = db.get(User, user_id)
    assert user is not None

    rtid, rtnick, rtdel = None, None, False
    if target is not None and target.parent_id is not None:
        t_author = db.get(User, target.user_id)
        if t_author is not None:
            rtnick, _, rtdel = author_display(t_author)
            rtid = target.id

    return _to_out(
        comment,
        user,
        like_count=0,
        liked_by_me=False,
        replies=[],
        reply_to_id=rtid if rtid is not None else comment.reply_to_id,
        reply_to_nickname=rtnick,
        reply_to_author_deleted=rtdel,
    )


def delete_comment_cascade(db: Session, comment_id: int) -> bool:
    comment = db.get(Comment, comment_id)
    if comment is None:
        return False
    # 子回复
    child_ids = list(
        db.scalars(select(Comment.id).where(Comment.parent_id == comment_id)).all()
    )
    all_ids = child_ids + [comment_id]
    notifications_service.nullify_comment_refs(db, all_ids)
    # 先清其他评论对本条的 reply_to 引用，避免 FK 阻碍删除
    db.execute(
        update(Comment)
        .where(Comment.reply_to_id.in_(all_ids))
        .values(reply_to_id=None)
    )
    db.execute(delete(Like).where(Like.comment_id.in_(all_ids)))
    if child_ids:
        db.execute(delete(Comment).where(Comment.id.in_(child_ids)))
    db.execute(delete(Comment).where(Comment.id == comment_id))
    db.commit()
    return True


def like_comment(db: Session, *, user_id: int, comment_id: int) -> tuple[bool, int]:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    existing = db.scalar(
        select(Like).where(Like.user_id == user_id, Like.comment_id == comment_id)
    )
    if existing is None:
        db.add(Like(user_id=user_id, comment_id=comment_id))
        db.commit()
        if comment.user_id != user_id:
            notifications_service.create_notification(
                db,
                recipient_id=comment.user_id,
                actor_id=user_id,
                notif_type="like",
                page_id=comment.page_id,
                king_slot_id=comment.king_slot_id,
                comment_id=comment.id,
                preview=comment.content,
            )
    count = db.scalar(
        select(func.count()).select_from(Like).where(Like.comment_id == comment_id)
    ) or 0
    return True, int(count)


def unlike_comment(db: Session, *, user_id: int, comment_id: int) -> None:
    comment = db.get(Comment, comment_id)
    if comment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
    db.execute(
        delete(Like).where(Like.user_id == user_id, Like.comment_id == comment_id)
    )
    db.commit()


def get_comment(db: Session, comment_id: int) -> Comment | None:
    return db.get(Comment, comment_id)
