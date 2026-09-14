from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentListOut, CommentOut, LikeStateOut
from app.services import comments as comments_service

router = APIRouter(tags=["comments"])


@router.get("/pages/{page_id}/comments", response_model=CommentListOut)
def list_comments(
    page_id: int,
    sort: str = Query("latest", pattern="^(latest|hot)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentListOut:
    items = comments_service.list_page_comments(
        db, page_id, current_user.id, sort=sort
    )
    return CommentListOut(items=items)


@router.post(
    "/pages/{page_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(
    page_id: int,
    body: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentOut:
    return comments_service.create_comment(
        db,
        page_id=page_id,
        user_id=current_user.id,
        content=body.content,
        parent_id=body.parent_id,
    )


@router.post("/comments/{comment_id}/like", response_model=LikeStateOut)
def like_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> LikeStateOut:
    liked, count = comments_service.like_comment(
        db, user_id=current_user.id, comment_id=comment_id
    )
    return LikeStateOut(liked=liked, like_count=count)


@router.delete(
    "/comments/{comment_id}/like",
    status_code=status.HTTP_204_NO_CONTENT,
)
def unlike_comment(
    comment_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    comments_service.unlike_comment(
        db, user_id=current_user.id, comment_id=comment_id
    )
