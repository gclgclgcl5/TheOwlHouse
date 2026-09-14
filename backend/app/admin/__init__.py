from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER

from app.config import BASE_DIR, settings
from app.database import get_db
from app.services import app_update as app_update_service
from app.services import comments as comments_service
from app.services import home_announcement as home_announcement_service
from app.services import pages as pages_service
from app.services import users as users_service
from app.services.storage import save_comic_image

router = APIRouter(prefix="/admin", tags=["admin-web"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

SESSION_KEY = "admin_logged_in"
ADMIN_PAGES_PAGE_SIZE = 100


def _page_numbers(current: int, total_pages: int, *, radius: int = 2) -> list[int]:
    start = max(1, current - radius)
    end = min(total_pages, current + radius)
    return list(range(start, end + 1))


def is_admin(request: Request) -> bool:
    return bool(request.session.get(SESSION_KEY))


def require_admin(request: Request) -> None:
    if not is_admin(request):
        raise HTTPException(status_code=status.HTTP_303_SEE_OTHER, headers={"Location": "/admin/login"})


def login_required(view: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(view)
    def wrapper(request: Request, *args: Any, **kwargs: Any) -> Any:
        if not is_admin(request):
            return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
        return view(request, *args, **kwargs)

    return wrapper


@router.get("/login", response_class=HTMLResponse, response_model=None)
def login_page(request: Request):
    if is_admin(request):
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={"app_name": settings.app_name, "title": "管理员登录", "error": None},
    )


@router.post("/login", response_model=None)
async def login_submit(request: Request):
    form = await request.form()
    username = str(form.get("username", "")).strip()
    password = str(form.get("password", ""))
    if username == settings.admin_username and password == settings.admin_password:
        request.session[SESSION_KEY] = True
        request.session["admin_username"] = username
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_login.html",
        context={
            "app_name": settings.app_name,
            "title": "管理员登录",
            "error": "账号或密码错误",
        },
        status_code=400,
    )


@router.post("/logout")
def logout(request: Request) -> RedirectResponse:
    request.session.clear()
    return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)


@router.get("/", response_class=HTMLResponse, response_model=None)
def admin_home(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_home.html",
        context={
            "app_name": settings.app_name,
            "title": "管理后台",
            "admin_username": request.session.get("admin_username", "admin"),
        },
    )


@router.get("/pages", response_class=HTMLResponse, response_model=None)
def pages_list(
    request: Request,
    db: Session = Depends(get_db),
    order: str = "page_no_desc",
    page: int = 1,
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    if order not in ("page_no", "page_no_desc"):
        order = "page_no_desc"
    page_size = ADMIN_PAGES_PAGE_SIZE
    page = max(1, page)
    offset = (page - 1) * page_size
    items, total = pages_service.list_pages(db, limit=page_size, offset=offset, order=order)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * page_size
        items, total = pages_service.list_pages(
            db, limit=page_size, offset=offset, order=order
        )
    counts = pages_service.comment_counts_by_page_ids(db, [p.id for p in items])
    return templates.TemplateResponse(
        request=request,
        name="admin_pages.html",
        context={
            "app_name": settings.app_name,
            "title": "漫画管理",
            "pages": [
                pages_service.page_to_out(p, comment_count=counts.get(p.id, 0))
                for p in items
            ],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "page_numbers": _page_numbers(page, total_pages),
            "message": request.query_params.get("message"),
            "order": order,
        },
    )


@router.get("/pages/new", response_class=HTMLResponse, response_model=None)
def pages_new(request: Request):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_page_form.html",
        context={
            "app_name": settings.app_name,
            "title": "新增漫画页",
            "page": None,
            "error": None,
            "action": "/admin/pages/new",
            "auto_page_no": True,
        },
    )


@router.post("/pages/new", response_model=None)
async def pages_create(
    request: Request,
    title: str = Form(...),
    image: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    try:
        image_path = await save_comic_image(image)
        pages_service.create_page(db, title=title, image_path=image_path)
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_page_form.html",
            context={
                "app_name": settings.app_name,
                "title": "新增漫画页",
                "page": {"title": title},
                "error": exc.detail,
                "action": "/admin/pages/new",
                "auto_page_no": True,
            },
            status_code=400,
        )
    return RedirectResponse(
        url="/admin/pages?message=created&order=page_no_desc",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/pages/{page_id}/edit", response_class=HTMLResponse, response_model=None)
def pages_edit(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = pages_service.get_page(db, page_id)
    if page is None:
        return RedirectResponse(url="/admin/pages?message=missing&order=page_no_desc", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_page_form.html",
        context={
            "app_name": settings.app_name,
            "title": "编辑漫画页",
            "page": pages_service.page_to_out(page),
            "error": None,
            "action": f"/admin/pages/{page_id}/edit",
        },
    )


@router.post("/pages/{page_id}/edit", response_model=None)
async def pages_update(
    request: Request,
    page_id: int,
    title: str = Form(...),
    page_no: int = Form(1),
    image: UploadFile | None = File(None),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = pages_service.get_page(db, page_id)
    if page is None:
        return RedirectResponse(url="/admin/pages?message=missing&order=page_no_desc", status_code=HTTP_303_SEE_OTHER)
    try:
        image_path = None
        if image is not None and image.filename:
            image_path = await save_comic_image(image)
        pages_service.update_page(
            db, page, title=title, page_no=page_no, image_path=image_path
        )
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_page_form.html",
            context={
                "app_name": settings.app_name,
                "title": "编辑漫画页",
                "page": pages_service.page_to_out(page),
                "error": exc.detail,
                "action": f"/admin/pages/{page_id}/edit",
            },
            status_code=400,
        )
    return RedirectResponse(
        url="/admin/pages?message=updated&order=page_no_desc",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.post("/pages/{page_id}/delete", response_model=None)
def pages_delete(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = pages_service.get_page(db, page_id)
    if page is not None:
        pages_service.delete_page(db, page)
    return RedirectResponse(
        url="/admin/pages?message=deleted&order=page_no_desc",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/pages/{page_id}/comments", response_class=HTMLResponse, response_model=None)
def page_comments(
    request: Request,
    page_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = pages_service.get_page(db, page_id)
    if page is None:
        return RedirectResponse(url="/admin/pages?message=missing", status_code=HTTP_303_SEE_OTHER)
    try:
        items = comments_service.list_page_comments(db, page_id, current_user_id=None)
    except HTTPException:
        return RedirectResponse(url="/admin/pages?message=missing", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_page_comments.html",
        context={
            "app_name": settings.app_name,
            "title": f"评论 · {page.title}",
            "page": pages_service.page_to_out(page),
            "comments": items,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/comments/{comment_id}/delete", response_model=None)
def comment_delete(
    request: Request,
    comment_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    comment = comments_service.get_comment(db, comment_id)
    page_id = comment.page_id if comment is not None else None
    if comment is not None:
        comments_service.delete_comment_cascade(db, comment_id)
    if page_id is None:
        return RedirectResponse(url="/admin/pages", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse(
        url=f"/admin/pages/{page_id}/comments?message=deleted",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/users", response_class=HTMLResponse, response_model=None)
def users_list(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    items, total = users_service.list_active_users(db, limit=100, offset=0)
    return templates.TemplateResponse(
        request=request,
        name="admin_users.html",
        context={
            "app_name": settings.app_name,
            "title": "用户管理",
            "users": [users_service.user_to_admin_out(u) for u in items],
            "total": total,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/users/{user_id}/delete", response_model=None)
def users_delete(
    request: Request,
    user_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    deleted = users_service.soft_delete_user(db, user_id)
    message = "deleted" if deleted is not None else "missing"
    return RedirectResponse(
        url=f"/admin/users?message={message}",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/app-update", response_class=HTMLResponse, response_model=None)
def app_update_page(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    config = app_update_service.get_config_out(db)
    return templates.TemplateResponse(
        request=request,
        name="admin_app_update.html",
        context={
            "app_name": settings.app_name,
            "title": "App 版本更新",
            "config": config,
            "error": None,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/app-update", response_model=None)
async def app_update_save(
    request: Request,
    version_code: int = Form(...),
    version_name: str = Form(""),
    download_url: str = Form(""),
    message: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    version_name = version_name.strip()
    download_url = download_url.strip()
    message = message.strip()
    error: str | None = None
    if version_code < 0:
        error = "versionCode 不能为负数"
    elif version_code > 0 and not download_url:
        error = "填写了版本号时，下载链接不能为空"
    elif download_url and not (
        download_url.startswith("http://") or download_url.startswith("https://")
    ):
        error = "下载链接需以 http:// 或 https:// 开头"
    if error:
        config = app_update_service.get_config_out(db)
        return templates.TemplateResponse(
            request=request,
            name="admin_app_update.html",
            context={
                "app_name": settings.app_name,
                "title": "App 版本更新",
                "config": {
                    "version_code": version_code,
                    "version_name": version_name,
                    "download_url": download_url,
                    "message": message,
                    "available": False,
                },
                "error": error,
                "message": None,
            },
            status_code=400,
        )
    app_update_service.save_config(
        db,
        version_code=version_code,
        version_name=version_name,
        download_url=download_url,
        message=message,
    )
    return RedirectResponse(
        url="/admin/app-update?message=saved",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/home-announcement", response_class=HTMLResponse, response_model=None)
def home_announcement_page(
    request: Request,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    config = home_announcement_service.get_out(db)
    return templates.TemplateResponse(
        request=request,
        name="admin_home_announcement.html",
        context={
            "app_name": settings.app_name,
            "title": "首页公告标题",
            "config": config,
            "error": None,
            "message": request.query_params.get("message"),
        },
    )


@router.post("/home-announcement", response_model=None)
async def home_announcement_save(
    request: Request,
    title: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    title = title.strip()
    if not title:
        config = home_announcement_service.get_out(db)
        return templates.TemplateResponse(
            request=request,
            name="admin_home_announcement.html",
            context={
                "app_name": settings.app_name,
                "title": "首页公告标题",
                "config": {"title": title},
                "error": "标题不能为空",
                "message": None,
            },
            status_code=400,
        )
    home_announcement_service.save(db, title=title)
    return RedirectResponse(
        url="/admin/home-announcement?message=saved",
        status_code=HTTP_303_SEE_OTHER,
    )
