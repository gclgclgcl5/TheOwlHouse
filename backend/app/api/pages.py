from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.comic import ComicPageListOut, ComicPageOut
from app.services import pages as pages_service

router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("", response_model=ComicPageListOut)
def list_pages(
    limit: int = 20,
    offset: int = 0,
    order: str = Query("created_at", pattern="^(created_at|page_no)$"),
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComicPageListOut:
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    items, total = pages_service.list_pages(
        db, limit=limit, offset=offset, order=order
    )
    return ComicPageListOut(
        items=[pages_service.page_to_out(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/{page_id}", response_model=ComicPageOut)
def get_page(
    page_id: int,
    _: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ComicPageOut:
    page = pages_service.get_page(db, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    return pages_service.page_to_out(page)
