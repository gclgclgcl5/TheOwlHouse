import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile, status

from app.config import UPLOAD_DIR

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
    "image/gif": ".gif",
}
MAX_AVATAR_BYTES = 5 * 1024 * 1024
MAX_COMIC_BYTES = 20 * 1024 * 1024


def _ext_for(upload: UploadFile) -> str:
    content_type = (upload.content_type or "").lower()
    if content_type in ALLOWED_IMAGE_TYPES:
        return ALLOWED_IMAGE_TYPES[content_type]
    name = upload.filename or ""
    suffix = Path(name).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="仅支持 jpg/png/webp/gif 图片",
    )


async def save_upload(upload: UploadFile, *, folder: str, max_bytes: int) -> str:
    """保存上传文件，返回相对 uploads 的路径，如 avatars/xxx.jpg"""
    ext = _ext_for(upload)
    data = await upload.read()
    if not data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="空文件")
    if len(data) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件过大，上限 {max_bytes // (1024 * 1024)}MB",
        )
    target_dir = UPLOAD_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{uuid.uuid4().hex}{ext}"
    path = target_dir / filename
    path.write_bytes(data)
    return f"{folder}/{filename}"


async def save_avatar(upload: UploadFile) -> str:
    return await save_upload(upload, folder="avatars", max_bytes=MAX_AVATAR_BYTES)


async def save_comic_image(upload: UploadFile) -> str:
    return await save_upload(upload, folder="comics", max_bytes=MAX_COMIC_BYTES)


def media_url(relative_path: str) -> str:
    normalized = relative_path.replace("\\", "/")
    return f"/media/{normalized}"


def delete_upload(relative_path: str | None) -> None:
    if not relative_path:
        return
    path = UPLOAD_DIR / relative_path
    if path.is_file():
        path.unlink(missing_ok=True)
