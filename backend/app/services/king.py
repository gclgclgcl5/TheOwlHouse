from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comment import Comment
from app.models.king import KingSlot, KingVersion, KingVersionImage
from app.services.storage import delete_upload, media_url

PENDING_APPEND_HINT = "请先补全该版本的待上传页，再追加新页。"
DESCRIPTION_MAX_LEN = 5000


@dataclass
class KingSlotRow:
    slot_id: int
    page_no: int
    title: str
    image_url: str | None
    comment_count: int


def get_version(db: Session, version_id: int) -> KingVersion | None:
    return db.get(KingVersion, version_id)


def get_slot(db: Session, slot_id: int) -> KingSlot | None:
    return db.get(KingSlot, slot_id)


def list_versions(db: Session) -> list[KingVersion]:
    return list(
        db.scalars(
            select(KingVersion).order_by(
                KingVersion.is_default.desc(),
                KingVersion.created_at.asc(),
                KingVersion.id.asc(),
            )
        ).all()
    )


def default_version(db: Session) -> KingVersion | None:
    return db.scalar(
        select(KingVersion).where(KingVersion.is_default.is_(True)).limit(1)
    )


def uploaded_count(db: Session, version_id: int) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(KingVersionImage)
            .where(KingVersionImage.version_id == version_id)
        )
        or 0
    )


def slot_count(db: Session) -> int:
    return int(db.scalar(select(func.count()).select_from(KingSlot)) or 0)


def pending_count(db: Session, version_id: int) -> int:
    return max(0, slot_count(db) - uploaded_count(db, version_id))


def comment_counts_by_slot_ids(db: Session, slot_ids: list[int]) -> dict[int, int]:
    if not slot_ids:
        return {}
    rows = db.execute(
        select(Comment.king_slot_id, func.count(Comment.id))
        .where(Comment.king_slot_id.in_(slot_ids))
        .group_by(Comment.king_slot_id)
    ).all()
    return {int(slot_id): int(n) for slot_id, n in rows if slot_id is not None}


def list_version_slots(db: Session, version_id: int) -> list[KingSlotRow]:
    slots = list(db.scalars(select(KingSlot).order_by(KingSlot.page_no.asc())).all())
    images = {
        img.slot_id: img
        for img in db.scalars(
            select(KingVersionImage).where(KingVersionImage.version_id == version_id)
        ).all()
    }
    counts = comment_counts_by_slot_ids(db, [s.id for s in slots])
    rows: list[KingSlotRow] = []
    for slot in slots:
        img = images.get(slot.id)
        rows.append(
            KingSlotRow(
                slot_id=slot.id,
                page_no=slot.page_no,
                title=slot.title,
                image_url=media_url(img.image_path) if img is not None else None,
                comment_count=counts.get(slot.id, 0),
            )
        )
    return rows


def create_default_version(db: Session, *, name: str, cover_path: str) -> KingVersion:
    if default_version(db) is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="默认版本已存在")
    title = name.strip() or "默认"
    version = KingVersion(name=title, cover_path=cover_path, is_default=True)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def create_version(db: Session, *, name: str, cover_path: str) -> KingVersion:
    if default_version(db) is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="请先创建默认版本"
        )
    title = name.strip()
    if not title:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="版本名称不能为空")
    version = KingVersion(name=title, cover_path=cover_path, is_default=False)
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def update_version(
    db: Session,
    version: KingVersion,
    *,
    name: str | None = None,
    cover_path: str | None = None,
    description: str | None = None,
) -> KingVersion:
    if name is not None:
        title = name.strip()
        if not title:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="版本名称不能为空")
        version.name = title
    if cover_path is not None:
        old = version.cover_path
        version.cover_path = cover_path
        if old and old != cover_path:
            delete_upload(old)
    if description is not None:
        text = description.strip()
        if len(text) > DESCRIPTION_MAX_LEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"版本介绍不能超过{DESCRIPTION_MAX_LEN}字",
            )
        version.description = text
    db.add(version)
    db.commit()
    db.refresh(version)
    return version


def delete_version(db: Session, version: KingVersion) -> None:
    if version.is_default:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="默认版本不可删除")
    delete_upload(version.cover_path)
    for img in list(version.images):
        delete_upload(img.image_path)
    db.delete(version)
    db.commit()


def append_global_page(
    db: Session,
    version: KingVersion,
    *,
    title: str,
    image_path: str,
) -> KingSlot:
    if pending_count(db, version.id) > 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=PENDING_APPEND_HINT)
    text = title.strip()
    if not text:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标题不能为空")
    next_no = slot_count(db) + 1
    slot = KingSlot(page_no=next_no, title=text)
    db.add(slot)
    db.flush()
    db.add(
        KingVersionImage(
            version_id=version.id,
            slot_id=slot.id,
            image_path=image_path,
        )
    )
    db.commit()
    db.refresh(slot)
    return slot


def upsert_version_slot(
    db: Session,
    version: KingVersion,
    slot: KingSlot,
    *,
    title: str | None = None,
    image_path: str | None = None,
) -> KingVersionImage:
    if title is not None:
        text = title.strip()
        if not text:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="标题不能为空")
        slot.title = text
        db.add(slot)
    image = db.scalar(
        select(KingVersionImage).where(
            KingVersionImage.version_id == version.id,
            KingVersionImage.slot_id == slot.id,
        )
    )
    if image_path:
        if image is None:
            image = KingVersionImage(
                version_id=version.id,
                slot_id=slot.id,
                image_path=image_path,
            )
            db.add(image)
        else:
            old = image.image_path
            image.image_path = image_path
            db.add(image)
            if old and old != image_path:
                delete_upload(old)
    elif image is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请上传图片")
    db.commit()
    db.refresh(image)
    return image


def get_version_image(
    db: Session, version_id: int, slot_id: int
) -> KingVersionImage | None:
    return db.scalar(
        select(KingVersionImage).where(
            KingVersionImage.version_id == version_id,
            KingVersionImage.slot_id == slot_id,
        )
    )


def version_to_out(db: Session, version: KingVersion) -> dict:
    return {
        "id": version.id,
        "name": version.name,
        "cover_url": media_url(version.cover_path),
        "description": version.description or "",
        "is_default": version.is_default,
        "uploaded_count": uploaded_count(db, version.id),
        "created_at": version.created_at,
    }


def list_version_uploaded_pages(db: Session, version_id: int) -> list[KingSlotRow]:
    return [row for row in list_version_slots(db, version_id) if row.image_url]


def _versions_with_slot_image(db: Session, slot_id: int) -> list[KingVersion]:
    version_ids = list(
        db.scalars(
            select(KingVersionImage.version_id).where(KingVersionImage.slot_id == slot_id)
        ).all()
    )
    if not version_ids:
        return []
    return list(
        db.scalars(
            select(KingVersion)
            .where(KingVersion.id.in_(version_ids))
            .order_by(
                KingVersion.is_default.desc(),
                KingVersion.created_at.asc(),
                KingVersion.id.asc(),
            )
        ).all()
    )


def resolve_page(
    db: Session,
    *,
    page_no: int | None = None,
    slot_id: int | None = None,
    preferred_version_id: int | None = None,
) -> dict:
    slot: KingSlot | None = None
    if slot_id is not None:
        slot = get_slot(db, slot_id)
        if slot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    elif page_no is not None:
        slot = db.scalar(select(KingSlot).where(KingSlot.page_no == page_no))
        if slot is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="页面不存在")
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="需要 page_no 或 slot_id",
        )

    candidates = _versions_with_slot_image(db, slot.id)
    if not candidates:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该页暂无可用版本")

    chosen: KingVersion | None = None
    if preferred_version_id is not None:
        for v in candidates:
            if v.id == preferred_version_id:
                chosen = v
                break
    if chosen is None:
        chosen = candidates[0]

    switched = preferred_version_id is not None and preferred_version_id != chosen.id

    image = get_version_image(db, chosen.id, slot.id)
    assert image is not None
    counts = comment_counts_by_slot_ids(db, [slot.id])
    return {
        "version_id": chosen.id,
        "version_name": chosen.name,
        "switched": switched,
        "slot_id": slot.id,
        "page_no": slot.page_no,
        "title": slot.title,
        "image_url": media_url(image.image_path),
        "comment_count": counts.get(slot.id, 0),
    }
