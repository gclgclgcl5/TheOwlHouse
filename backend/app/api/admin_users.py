from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.schemas.user_admin import AdminUserListOut
from app.services import users as users_service

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


@router.get("", response_model=AdminUserListOut)
def admin_list_users(
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> AdminUserListOut:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    items, total = users_service.list_active_users(db, limit=limit, offset=offset)
    return AdminUserListOut(
        items=[users_service.user_to_admin_out(u) for u in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_user(
    user_id: int,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    deleted = users_service.soft_delete_user(db, user_id)
    if deleted is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在或已删除")
