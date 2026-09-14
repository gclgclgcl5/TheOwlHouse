from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_admin
from app.database import get_db
from app.schemas.comic import ComicPageListOut, ComicPageOut
from app.services import pages as pages_service
from app.services.storage import save_comic_image

router = APIRouter(prefix="/admin/pages", tags=["admin-pages"])


@router.get("", response_model=ComicPageListOut)
def admin_list_pages(
    limit: int = 50,
    offset: int = 0,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ComicPageListOut:
    limit = max(1, min(limit, 100))
    offset = max(0, offset)
    items, total = pages_service.list_pages(db, limit=limit, offset=offset)
    return ComicPageListOut(
        items=[pages_service.page_to_out(p) for p in items],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.post("", response_model=ComicPageOut, status_code=status.HTTP_201_CREATED)
async def admin_create_page(
    title: str = Form(..., min_length=1, max_length=200),
    image: UploadFile = File(...),
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ComicPageOut:
    image_path = await save_comic_image(image)
    page = pages_service.create_page(db, title=title, image_path=image_path)
    return pages_service.page_to_out(page)


@router.put("/{page_id}", response_model=ComicPageOut)
async def admin_update_page(
    page_id: int,
    title: str | None = Form(None),
    page_no: int | None = Form(None),
    image: UploadFile | None = File(None),
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> ComicPageOut:
    page = pages_service.get_page(db, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    image_path = None
    if image is not None and image.filename:
        image_path = await save_comic_image(image)
    if title is None and page_no is None and image_path is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="无更新内容")
    page = pages_service.update_page(
        db, page, title=title, page_no=page_no, image_path=image_path
    )
    return pages_service.page_to_out(page)


@router.delete("/{page_id}", status_code=status.HTTP_204_NO_CONTENT)
def admin_delete_page(
    page_id: int,
    _: str = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> None:
    page = pages_service.get_page(db, page_id)
    if page is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    pages_service.delete_page(db, page)
