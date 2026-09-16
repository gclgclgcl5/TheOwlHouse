from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.models.like import Like
from app.models.user import User
from app.schemas.user_admin import AdminUserOut
from app.services import auth as auth_service
from app.services.storage import media_url


def user_to_admin_out(user: User) -> AdminUserOut:
    return AdminUserOut(
        id=user.id,
        nickname=user.nickname,
        avatar_url=media_url(user.avatar_path),
        created_at=user.created_at,
        is_deleted=user.is_deleted,
    )


def list_active_users(
    db: Session,
    *,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[User], int]:
    total = (
        db.scalar(
            select(func.count()).select_from(User).where(User.is_deleted.is_(False))
        )
        or 0
    )
    items = list(
        db.scalars(
            select(User)
            .where(User.is_deleted.is_(False))
            .order_by(User.created_at.desc())
            .offset(offset)
            .limit(limit)
        ).all()
    )
    return items, total


def get_active_user(db: Session, user_id: int) -> User | None:
    user = db.get(User, user_id)
    if user is None or user.is_deleted:
        return None
    return user


def set_password(db: Session, user_id: int, new_password: str) -> User | None:
    user = get_active_user(db, user_id)
    if user is None:
        return None
    user.password_hash = auth_service.hash_password(new_password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def soft_delete_user(db: Session, user_id: int) -> User | None:
    user = get_active_user(db, user_id)
    if user is None:
        return None
    # 回滚该用户点赞
    db.execute(delete(Like).where(Like.user_id == user_id))
    # 释放昵称唯一约束，便于同名重新注册；旧账号仍以 is_deleted 标记失效
    user.nickname = _freed_nickname(user.nickname, user.id)
    user.is_deleted = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _freed_nickname(nickname: str, user_id: int) -> str:
    suffix = f"__del_{user_id}"
    base_max = max(1, 64 - len(suffix))
    return f"{nickname[:base_max]}{suffix}"


def release_deleted_nickname(db: Session, nickname: str) -> None:
    """兼容：此前软删未改昵称的记录，注册前强制释放。"""
    stale_users = list(
        db.scalars(
            select(User).where(
                User.nickname == nickname,
                User.is_deleted.is_(True),
            )
        ).all()
    )
    for stale in stale_users:
        stale.nickname = _freed_nickname(nickname, stale.id)
        db.add(stale)
    if stale_users:
        db.commit()
