from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.home_announcement import HomeAnnouncementOut
from app.services import home_announcement as home_announcement_service

router = APIRouter(prefix="/home-announcement", tags=["home-announcement"])


@router.get("", response_model=HomeAnnouncementOut)
def get_home_announcement(db: Session = Depends(get_db)) -> HomeAnnouncementOut:
    """公开接口：首页标题/小公告，客户端刷新时拉取。"""
    return home_announcement_service.get_out(db)
