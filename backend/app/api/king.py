from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.comment import CommentCreate, CommentOut
from app.schemas.king import (
    KingCommentListOut,
    KingPageListOut,
    KingPageOut,
    KingResolveOut,
    KingVersionListOut,
    KingVersionOut,
)
from app.services import comments as comments_service
from app.services import king as king_service

router = APIRouter(prefix="/king", tags=["king"])


@router.get("/versions", response_model=KingVersionListOut)
def list_king_versions(
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KingVersionListOut:
    versions = king_service.list_versions(db)
    return KingVersionListOut(
        items=[KingVersionOut(**king_service.version_to_out(db, v)) for v in versions]
    )


@router.get("/versions/{version_id}/pages", response_model=KingPageListOut)
def list_king_version_pages(
    version_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KingPageListOut:
    version = king_service.get_version(db, version_id)
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="版本不存在")
    rows = king_service.list_version_uploaded_pages(db, version_id)
    return KingPageListOut(
        version_id=version.id,
        version_name=version.name,
        description=version.description or "",
        items=[
            KingPageOut(
                slot_id=r.slot_id,
                page_no=r.page_no,
                title=r.title,
                image_url=r.image_url or "",
                comment_count=r.comment_count,
            )
            for r in rows
        ],
    )


@router.get("/resolve", response_model=KingResolveOut)
def resolve_king_page(
    page_no: int | None = Query(None),
    slot_id: int | None = Query(None),
    preferred_version_id: int | None = Query(None),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KingResolveOut:
    data = king_service.resolve_page(
        db,
        page_no=page_no,
        slot_id=slot_id,
        preferred_version_id=preferred_version_id,
    )
    return KingResolveOut(**data)


@router.get("/slots/{slot_id}/comments", response_model=KingCommentListOut)
def list_king_slot_comments(
    slot_id: int,
    sort: str = Query("latest", pattern="^(latest|hot)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> KingCommentListOut:
    items = comments_service.list_slot_comments(
        db, slot_id, current_user.id, sort=sort
    )
    return KingCommentListOut(items=items)


@router.post(
    "/slots/{slot_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_king_slot_comment(
    slot_id: int,
    body: CommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> CommentOut:
    return comments_service.create_slot_comment(
        db,
        slot_id=slot_id,
        user_id=current_user.id,
        content=body.content,
        parent_id=body.parent_id,
    )
