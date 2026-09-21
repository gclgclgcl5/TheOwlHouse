from collections.abc import Callable
from functools import wraps
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from starlette.status import HTTP_303_SEE_OTHER

from app.admin.auth import SESSION_KEY, is_admin
from app.config import BASE_DIR, settings
from app.database import get_db
from app.services import admin_inbox as admin_inbox_service
from app.services import app_update as app_update_service
from app.services import comments as comments_service
from app.services import home_announcement as home_announcement_service
from app.services import pages as pages_service
from app.services import users as users_service
from app.services.storage import save_comic_image

router = APIRouter(prefix="/admin", tags=["admin-web"])
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

ADMIN_PAGES_PAGE_SIZE = 100
ADMIN_USERS_PAGE_SIZE = 50


def _page_numbers(current: int, total_pages: int, *, radius: int = 2) -> list[int]:
    start = max(1, current - radius)
    end = min(total_pages, current + radius)
    return list(range(start, end + 1))


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
def admin_home(request: Request, db: Session = Depends(get_db)):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    return templates.TemplateResponse(
        request=request,
        name="admin_home.html",
        context={
            "app_name": settings.app_name,
            "title": "管理后台",
            "admin_username": request.session.get("admin_username", "admin"),
            "doujin_unread": admin_inbox_service.unread_count(db, "doujin"),
            "king_unread": admin_inbox_service.unread_count(db, "king"),
        },
    )


def _inbox_title(section: str) -> str:
    return "同人消息" if section == "doujin" else "长寿之王消息"


@router.get("/inbox/{section}", response_class=HTMLResponse, response_model=None)
def inbox_list(
    request: Request,
    section: str,
    db: Session = Depends(get_db),
    page: int = 1,
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    if section not in ("doujin", "king"):
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    page_size = admin_inbox_service.PAGE_SIZE
    page = max(1, page)
    items, total = admin_inbox_service.list_section(db, section, page=page)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page > total_pages:
        page = total_pages
        items, total = admin_inbox_service.list_section(db, section, page=page)
    return templates.TemplateResponse(
        request=request,
        name="admin_inbox.html",
        context={
            "app_name": settings.app_name,
            "title": _inbox_title(section),
            "section": section,
            "items": items,
            "total": total,
            "unread": admin_inbox_service.unread_count(db, section),
            "page": page,
            "total_pages": total_pages,
            "page_numbers": _page_numbers(page, total_pages),
            "message": request.query_params.get("message"),
        },
    )


@router.post("/inbox/{section}/read-all", response_model=None)
def inbox_read_all(
    request: Request,
    section: str,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    if section not in ("doujin", "king"):
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    admin_inbox_service.mark_section_read(db, section)
    return RedirectResponse(
        url=f"/admin/inbox/{section}?message=read-all",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/inbox/items/{item_id}/open", response_model=None)
def inbox_open(
    request: Request,
    item_id: int,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    item = admin_inbox_service.get_item(db, item_id)
    if item is None:
        return RedirectResponse(url="/admin/", status_code=HTTP_303_SEE_OTHER)
    section = "doujin" if item.page_id is not None else "king"
    admin_inbox_service.mark_read(db, item)
    if item.page_id is not None:
        return RedirectResponse(
            url=f"/admin/pages/{item.page_id}/comments",
            status_code=HTTP_303_SEE_OTHER,
        )
    if item.king_slot_id is not None:
        return RedirectResponse(
            url=f"/admin/king/slots/{item.king_slot_id}/comments",
            status_code=HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=f"/admin/inbox/{section}",
        status_code=HTTP_303_SEE_OTHER,
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
            "title": "同人漫画",
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
            "title": "新增同人页",
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
                "title": "新增同人页",
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


def _insert_form_context(
    *,
    before_page,
    title_value: str = "",
    error=None,
    db: Session,
):
    insert_no = int(before_page.page_no)
    prev_title, next_title = pages_service.neighbor_titles_for_insert_before(
        db, before_page=before_page
    )
    return {
        "app_name": settings.app_name,
        "title": "插入同人页",
        "page": {"title": title_value} if title_value else None,
        "error": error,
        "action": "/admin/pages/insert",
        "auto_page_no": False,
        "insert_mode": True,
        "insert_no": insert_no,
        "before_id": before_page.id,
        "insert_prev_title": prev_title,
        "insert_next_title": next_title,
    }


@router.get("/pages/insert", response_class=HTMLResponse, response_model=None)
def pages_insert_form(
    request: Request,
    db: Session = Depends(get_db),
    before: int | None = None,
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    if before is None or before <= 0:
        return RedirectResponse(
            url="/admin/pages?message=missing&order=page_no_desc",
            status_code=HTTP_303_SEE_OTHER,
        )
    before_page = pages_service.get_page(db, before)
    if before_page is None:
        return RedirectResponse(
            url="/admin/pages?message=missing&order=page_no_desc",
            status_code=HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="admin_page_form.html",
        context=_insert_form_context(before_page=before_page, db=db),
    )


@router.post("/pages/insert", response_model=None)
async def pages_insert(
    request: Request,
    title: str = Form(...),
    image: UploadFile = File(...),
    before_id: str = Form(""),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    try:
        bid = int(before_id.strip()) if before_id.strip() else 0
    except ValueError:
        bid = 0
    before_page = pages_service.get_page(db, bid) if bid > 0 else None
    if before_page is None:
        return RedirectResponse(
            url="/admin/pages?message=missing&order=page_no_desc",
            status_code=HTTP_303_SEE_OTHER,
        )
    try:
        image_path = await save_comic_image(image)
        pages_service.insert_page_before(
            db, before_page=before_page, title=title, image_path=image_path
        )
    except HTTPException as exc:
        return templates.TemplateResponse(
            request=request,
            name="admin_page_form.html",
            context=_insert_form_context(
                before_page=before_page, title_value=title, error=exc.detail, db=db
            ),
            status_code=400,
        )
    return RedirectResponse(
        url="/admin/pages?message=inserted&order=page_no_desc",
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
            "title": "编辑同人页",
            "page": pages_service.page_to_out(page),
            "error": None,
            "action": f"/admin/pages/{page_id}/edit",
            "edit_page_no_hint": True,
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
                "title": "编辑同人页",
                "page": pages_service.page_to_out(page),
                "error": exc.detail,
                "action": f"/admin/pages/{page_id}/edit",
                "edit_page_no_hint": True,
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
            "back_href": "/admin/pages",
            "back_label": "← 返回同人列表",
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
    slot_id = comment.king_slot_id if comment is not None else None
    if comment is not None:
        comments_service.delete_comment_cascade(db, comment_id)
    if slot_id is not None:
        return RedirectResponse(
            url=f"/admin/king/slots/{slot_id}/comments?message=deleted",
            status_code=HTTP_303_SEE_OTHER,
        )
    if page_id is None:
        return RedirectResponse(url="/admin/pages", status_code=HTTP_303_SEE_OTHER)
    return RedirectResponse(
        url=f"/admin/pages/{page_id}/comments?message=deleted",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.get("/users", response_class=HTMLResponse, response_model=None)
def users_list(
    request: Request,
    page: int = 1,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page_size = ADMIN_USERS_PAGE_SIZE
    page = max(1, page)
    offset = (page - 1) * page_size
    items, total = users_service.list_active_users(db, limit=page_size, offset=offset)
    total_pages = max(1, (total + page_size - 1) // page_size) if total else 1
    if page > total_pages:
        page = total_pages
        offset = (page - 1) * page_size
        items, total = users_service.list_active_users(db, limit=page_size, offset=offset)
    return templates.TemplateResponse(
        request=request,
        name="admin_users.html",
        context={
            "app_name": settings.app_name,
            "title": "用户管理",
            "users": [users_service.user_to_admin_out(u) for u in items],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "page_numbers": _page_numbers(page, total_pages),
            "message": request.query_params.get("message"),
        },
    )


@router.get("/users/{user_id}/password", response_class=HTMLResponse, response_model=None)
def users_password_form(
    request: Request,
    user_id: int,
    page: int = 1,
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    user = users_service.get_active_user(db, user_id)
    if user is None:
        return RedirectResponse(
            url=f"/admin/users?message=missing&page={max(1, page)}",
            status_code=HTTP_303_SEE_OTHER,
        )
    return templates.TemplateResponse(
        request=request,
        name="admin_user_password.html",
        context={
            "app_name": settings.app_name,
            "title": "修改密码",
            "user": users_service.user_to_admin_out(user),
            "page": max(1, page),
            "error": None,
            "action": f"/admin/users/{user_id}/password",
        },
    )


@router.post("/users/{user_id}/password", response_model=None)
def users_password_update(
    request: Request,
    user_id: int,
    password: str = Form(...),
    password_confirm: str = Form(...),
    page: int = Form(1),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = max(1, page)
    user = users_service.get_active_user(db, user_id)
    if user is None:
        return RedirectResponse(
            url=f"/admin/users?message=missing&page={page}",
            status_code=HTTP_303_SEE_OTHER,
        )

    def render_error(message: str):
        return templates.TemplateResponse(
            request=request,
            name="admin_user_password.html",
            context={
                "app_name": settings.app_name,
                "title": "修改密码",
                "user": users_service.user_to_admin_out(user),
                "page": page,
                "error": message,
                "action": f"/admin/users/{user_id}/password",
            },
            status_code=400,
        )

    password = password.strip()
    password_confirm = password_confirm.strip()
    if len(password) < 4 or len(password) > 128:
        return render_error("密码长度需为 4～128 个字符")
    if password != password_confirm:
        return render_error("两次输入的密码不一致")

    updated = users_service.set_password(db, user_id, password)
    if updated is None:
        return RedirectResponse(
            url=f"/admin/users?message=missing&page={page}",
            status_code=HTTP_303_SEE_OTHER,
        )
    return RedirectResponse(
        url=f"/admin/users?message=password_updated&page={page}",
        status_code=HTTP_303_SEE_OTHER,
    )


@router.post("/users/{user_id}/delete", response_model=None)
def users_delete(
    request: Request,
    user_id: int,
    page: int = Form(1),
    db: Session = Depends(get_db),
):
    if not is_admin(request):
        return RedirectResponse(url="/admin/login", status_code=HTTP_303_SEE_OTHER)
    page = max(1, page)
    deleted = users_service.soft_delete_user(db, user_id)
    message = "deleted" if deleted is not None else "missing"
    return RedirectResponse(
        url=f"/admin/users?message={message}&page={page}",
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


from app.admin.king import router as king_router

router.include_router(king_router)
