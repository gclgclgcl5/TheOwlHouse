from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.notification import NotificationListOut, NotificationOut, UnreadCountOut
from app.services import notifications as notifications_service

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListOut)
def list_notifications(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationListOut:
    items, total = notifications_service.list_notifications(
        db, user.id, limit=limit, offset=offset
    )
    return NotificationListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/unread-count", response_model=UnreadCountOut)
def get_unread_count(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> UnreadCountOut:
    return UnreadCountOut(count=notifications_service.unread_count(db, user.id))


@router.post("/read-all")
def read_all(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict[str, int]:
    updated = notifications_service.mark_all_read(db, user.id)
    return {"updated": updated}


@router.post("/{notif_id}/read", response_model=NotificationOut)
def read_one(
    notif_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> NotificationOut:
    return notifications_service.mark_read(db, user.id, notif_id)
