from sqlalchemy.orm import Session

from app.models.home_announcement import DEFAULT_HOME_TITLE, HomeAnnouncement
from app.schemas.home_announcement import HomeAnnouncementOut

CONFIG_ID = 1


def get_or_create(db: Session) -> HomeAnnouncement:
    row = db.get(HomeAnnouncement, CONFIG_ID)
    if row is None:
        row = HomeAnnouncement(id=CONFIG_ID, title=DEFAULT_HOME_TITLE)
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def to_out(row: HomeAnnouncement) -> HomeAnnouncementOut:
    title = (row.title or "").strip() or DEFAULT_HOME_TITLE
    return HomeAnnouncementOut(title=title, updated_at=row.updated_at)


def get_out(db: Session) -> HomeAnnouncementOut:
    return to_out(get_or_create(db))


def save(db: Session, *, title: str) -> HomeAnnouncement:
    row = get_or_create(db)
    cleaned = title.strip()[:80]
    row.title = cleaned or DEFAULT_HOME_TITLE
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
