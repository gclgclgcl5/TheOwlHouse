from sqlalchemy.orm import Session

from app.models.app_update import AppUpdateConfig
from app.schemas.app_update import AppUpdateOut

CONFIG_ID = 1


def get_or_create(db: Session) -> AppUpdateConfig:
    row = db.get(AppUpdateConfig, CONFIG_ID)
    if row is None:
        row = AppUpdateConfig(
            id=CONFIG_ID,
            version_code=0,
            version_name="",
            download_url="",
            message="",
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def to_out(row: AppUpdateConfig) -> AppUpdateOut:
    url = (row.download_url or "").strip()
    available = row.version_code > 0 and bool(url)
    return AppUpdateOut(
        version_code=row.version_code,
        version_name=row.version_name or "",
        download_url=url,
        message=row.message or "",
        updated_at=row.updated_at,
        available=available,
    )


def get_config_out(db: Session) -> AppUpdateOut:
    return to_out(get_or_create(db))


def save_config(
    db: Session,
    *,
    version_code: int,
    version_name: str,
    download_url: str,
    message: str,
) -> AppUpdateConfig:
    row = get_or_create(db)
    row.version_code = max(0, version_code)
    row.version_name = version_name.strip()[:32]
    row.download_url = download_url.strip()[:1024]
    row.message = message.strip()
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
