from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.app_update import AppUpdateOut
from app.services import app_update as app_update_service

router = APIRouter(prefix="/app-update", tags=["app-update"])


@router.get("", response_model=AppUpdateOut)
def get_app_update(db: Session = Depends(get_db)) -> AppUpdateOut:
    """公开接口：客户端启动时拉取最新版本与下载链接。"""
    return app_update_service.get_config_out(db)
