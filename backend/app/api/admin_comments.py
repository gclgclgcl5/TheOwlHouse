from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.schemas.comment import CommentListOut
from app.services import comments as comments_service

router = APIRouter(tags=["admin-comments"])


@router.get("/admin/pages/{page_id}/comments", response_model=CommentListOut)
def admin_list_comments(
    page_id: int,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> CommentListOut:
    items = comments_service.list_page_comments(db, page_id, current_user_id=None)
    return CommentListOut(items=items)


@router.delete(
    "/admin/comments/{comment_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def admin_delete_comment(
    comment_id: int,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    ok = comments_service.delete_comment_cascade(db, comment_id)
    if not ok:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="评论不存在")
