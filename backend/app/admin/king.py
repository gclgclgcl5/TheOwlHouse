from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER

from app.admin.auth import is_admin
from app.admin.timefmt import format_cn_time
from app.config import BASE_DIR, settings
from app.database import get_db
from app.services import admin_inbox as admin_inbox_service
from app.services import comments as comments_service
from app.services import king as king_service
from app.services.storage import media_url, save_comic_image, save_king_cover

router = APIRouter(prefix="/king", tags=["admin-king"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
templates.env.filters["cn_time"] = format_cn_time


def _login_redirect() -> RedirectResponse:
    return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)


def _ctx(**extra: object) -> dict:
    base = {"app_name": settings.app_name}
    base.update(extra)
    return base


@router.get("", response_class=HTMLResponse, response_model=None)
def king_index(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return _login_redirect()
    versions = king_service.list_versions(db)
    if not versions:
        return templates.TemplateResponse(
            request=request,
            name="admin_king_bootstrap.html",
            context=_ctx(title="创建默认版本", error=None, name="默认"),
        )
    default = king_service.default_version(db) or versions[0]
    return RedirectResponse(
        url=f"/admin/king/versions/{default.id}",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.post("", response_model=None)
async def king_bootstrap(
    request: Request,
    name: str = Form("默认"),
    cover: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    if king_service.list_versions(db):
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    try:
        cover_path = await save_king_cover(cover)
        version = king_service.create_default_version(db, name=name, cover_path=cover_path)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_king_bootstrap.html",
            context=_ctx(title="创建默认版本", error=exc.detail, name=name),
            status_code=400,
        )
    return RedirectResponse(
        url=f"/admin/king/versions/{version.id}?message=created",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/versions/{version_id}", response_class=HTMLResponse, response_model=None)
def king_version_pages(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    versions = king_service.list_versions(db)
    rows = king_service.list_version_slots(db, version.id)
    pending = king_service.pending_count(db, version.id)
    uploaded = king_service.uploaded_count(db, version.id)
    return templates.TemplateResponse(
        request=request,
        name="admin_king_pages.html",
        context=_ctx(
            title=f"长寿之王 · {version.name}",
            version=version,
            versions=versions,
            rows=rows,
            pending=pending,
            uploaded=uploaded,
            slot_total=king_service.slot_count(db),
            king_unread=admin_inbox_service.unread_count(db, "king"),
            message=request.query_params.get("message"),
            error=request.query_params.get("error"),
        ),
    )


@router.get("/versions/{version_id}/settings", response_class=HTMLResponse, response_model=None)
def king_version_settings(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_king_version_settings.html",
        context=_ctx(
            title="版本设置",
            version=version,
            cover_url=media_url(version.cover_path),
            message=request.query_params.get("message"),
            error=request.query_params.get("error"),
        ),
    )


@router.post("/versions", response_model=None)
async def king_create_version(
    request: Request,
    name: str = Form(...),
    cover: UploadFile = File(...),
    from_version_id: int = Form(0),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()

    def settings_fallback() -> str:
        if from_version_id > 0 and king_service.get_version(db, from_version_id) is not None:
            return f"/admin/king/versions/{from_version_id}/settings"
        default = king_service.default_version(db)
        if default is not None:
            return f"/admin/king/versions/{default.id}/settings"
        return "/admin/king"

    try:
        cover_path = await save_king_cover(cover)
        version = king_service.create_version(db, name=name, cover_path=cover_path)
    except HTTPException as exc:
        return RedirectResponse(
            url=f"{settings_fallback()}?error={quote(str(exc.detail))}",
            status_code=HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=f"/admin/king/versions/{version.id}?message=created",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.post("/versions/{version_id}/meta", response_model=None)
async def king_update_meta(
    request: Request,
    version_id: int,
    name: str = Form(...),
    description: str = Form(""),
    cover: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    try:
        cover_path = None
        if cover is not None and cover.filename:
            cover_path = await save_king_cover(cover)
        king_service.update_version(
            db, version, name=name, cover_path=cover_path, description=description
        )
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/admin/king/versions/{version_id}/settings?error={quote(str(exc.detail))}",
            status_code=HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=f"/admin/king/versions/{version_id}/settings?message=updated",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.post("/versions/{version_id}/delete", response_model=None)
def king_delete_version(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    try:
        king_service.delete_version(db, version)
    except HTTPException as exc:
        return RedirectResponse(
            url=f"/admin/king/versions/{version_id}/settings?error={quote(str(exc.detail))}",
            status_code=HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(url="/admin/king?message=deleted", status_code=HTTP_303_SEE_OTHER)


@router.get("/versions/{version_id}/pages/new", response_class=HTMLResponse, response_model=None)
def king_page_new(
    request: Request,
    version_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    pending = king_service.pending_count(db, version.id)
    if pending > 0:
        return RedirectResponse(
            url=f"/admin/king/versions/{version_id}?error={quote(king_service.PENDING_APPEND_HINT)}",
            status_code=HTTP_303_SEE_OTHER,
        )
    next_no = king_service.slot_count(db) + 1
    return templates.TemplateResponse(
        request=request,
        name="admin_king_page_new.html",
        context=_ctx(
            title="追加新页",
            version=version,
            next_no=next_no,
            error=None,
            title_value="",
        ),
    )


@router.post("/versions/{version_id}/pages/new", response_model=None)
async def king_page_create(
    request: Request,
    version_id: int,
    title: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    if version is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    try:
        image_path = await save_comic_image(image)
        king_service.append_global_page(db, version, title=title, image_path=image_path)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_king_page_new.html",
            context=_ctx(
                title="追加新页",
                version=version,
                next_no=king_service.slot_count(db) + 1,
                error=exc.detail,
                title_value=title,
            ),
            status_code=400,
        )
    return RedirectResponse(
        url=f"/admin/king/versions/{version_id}?message=created",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get(
    "/versions/{version_id}/slots/{slot_id}",
    response_class=HTMLResponse,
    response_model=None,
)
def king_slot_edit(
    request: Request,
    version_id: int,
    slot_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    slot = king_service.get_slot(db, slot_id)
    if version is None or slot is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    image = king_service.get_version_image(db, version.id, slot.id)
    return templates.TemplateResponse(
        request=request,
        name="admin_king_slot_form.html",
        context=_ctx(
            title=f"第 {slot.page_no} 页",
            version=version,
            slot=slot,
            image_url=media_url(image.image_path) if image is not None else None,
            error=None,
        ),
    )


@router.post("/versions/{version_id}/slots/{slot_id}", response_model=None)
async def king_slot_save(
    request: Request,
    version_id: int,
    slot_id: int,
    title: str = Form(...),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    version = king_service.get_version(db, version_id)
    slot = king_service.get_slot(db, slot_id)
    if version is None or slot is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    try:
        image_path = None
        if image is not None and image.filename:
            image_path = await save_comic_image(image)
        king_service.upsert_version_slot(
            db, version, slot, title=title, image_path=image_path
        )
    except HTTPException as exc:
        img = king_service.get_version_image(db, version.id, slot.id)
        return templates.TemplateResponse(
            request=request,
            name="admin_king_slot_form.html",
            context=_ctx(
                title=f"第 {slot.page_no} 页",
                version=version,
                slot=slot,
                image_url=media_url(img.image_path) if img is not None else None,
                error=exc.detail,
            ),
            status_code=400,
        )
    return RedirectResponse(
        url=f"/admin/king/versions/{version_id}?message=updated",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/slots/{slot_id}/comments", response_class=HTMLResponse, response_model=None)
def king_slot_comments(
    request: Request,
    slot_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return _login_redirect()
    slot = king_service.get_slot(db, slot_id)
    if slot is None:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    version = king_service.default_version(db)
    back = f"/admin/king/versions/{version.id}" if version is not None else "/admin/king"
    try:
        items = comments_service.list_slot_comments(db, slot_id, current_user_id=None)
    except HTTPException:
        return RedirectResponse(url="/admin/king", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_page_comments.html",
        context=_ctx(
            title=f"评论 · {slot.title}",
            page=slot,
            comments=items,
            message=request.query_params.get("message"),
            back_href=back,
            back_label="← 返回长寿之王",
        ),
    )
