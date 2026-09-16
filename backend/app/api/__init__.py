from fastapi import APIRouter

from app.api.admin_auth import router as admin_auth_router
from app.api.admin_comments import router as admin_comments_router
from app.api.admin_pages import router as admin_pages_router
from app.api.admin_users import router as admin_users_router
from app.api.app_update import router as app_update_router
from app.api.auth import router as auth_router
from app.api.comments import router as comments_router
from app.api.home_announcement import router as home_announcement_router
from app.api.king import router as king_router
from app.api.notifications import router as notifications_router
from app.api.pages import router as pages_router

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "the-owl-house"}


router.include_router(auth_router)
router.include_router(admin_auth_router)
router.include_router(admin_pages_router)
router.include_router(admin_users_router)
router.include_router(admin_comments_router)
router.include_router(pages_router)
router.include_router(comments_router)
router.include_router(king_router)
router.include_router(notifications_router)
router.include_router(app_update_router)
router.include_router(home_announcement_router)
