from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.admin import router as admin_router
from app.api import router as api_router
from app.config import UPLOAD_DIR, ensure_data_dirs, settings
from app.database import init_db

ensure_data_dirs()
init_db()

app = FastAPI(title=settings.app_name, debug=settings.debug)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.secret_key,
    session_cookie="owlhouse_admin_session",
    same_site="lax",
    https_only=False,
)
app.include_router(api_router)
app.include_router(admin_router)

static_dir = Path(__file__).resolve().parent.parent / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.mount("/media", StaticFiles(directory=str(UPLOAD_DIR)), name="media")


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "admin": "/admin/",
        "health": "/api/health",
    }
