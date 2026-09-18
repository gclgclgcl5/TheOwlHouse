from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.comic import ComicPage
from app.models.comment import Comment
from app.schemas.comic import ComicPageOut
from app.services.storage import delete_upload, media_url


def page_to_out(page: ComicPage, *, comment_count: int = 0) -> ComicPageOut:
    return ComicPageOut(
        id=page.id,
        title=page.title,
        page_no=page.page_no,
        image_url=media_url(page.image_path),
        created_at=page.created_at,
        updated_at=page.updated_at,
        comment_count=comment_count,
    )


def comment_counts_by_page_ids(db: Session, page_ids: list[int]) -> dict[int, int]:
    if not page_ids:
        return {}
    rows = db.execute(
        select(Comment.page_id, func.count(Comment.id))
        .where(Comment.page_id.in_(page_ids))
        .group_by(Comment.page_id)
    ).all()
    return {int(page_id): int(n) for page_id, n in rows}


def next_page_no(db: Session) -> int:
    current = db.scalar(select(func.max(ComicPage.page_no)))
    return int(current or 0) + 1


def list_pages(
    db: Session,
    *,
    limit: int = 20,
    offset: int = 0,
    order: str = "created_at",
) -> tuple[list[ComicPage], int]:
    total = db.scalar(select(func.count()).select_from(ComicPage)) or 0
    q = select(ComicPage)
    if order == "page_no":
        q = q.order_by(ComicPage.page_no.asc(), ComicPage.id.asc())
    elif order == "page_no_desc":
        q = q.order_by(ComicPage.page_no.desc(), ComicPage.id.desc())
    else:
        q = q.order_by(ComicPage.created_at.desc())
    items = list(db.scalars(q.offset(offset).limit(limit)).all())
    return items, total


def get_page(db: Session, page_id: int) -> ComicPage | None:
    return db.get(ComicPage, page_id)


def create_page(
    db: Session,
    *,
    title: str,
    image_path: str,
    page_no: int | None = None,
) -> ComicPage:
    assigned = next_page_no(db) if page_no is None else page_no
    page = ComicPage(title=title.strip(), page_no=assigned, image_path=image_path)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def update_page(
    db: Session,
    page: ComicPage,
    *,
    title: str | None = None,
    page_no: int | None = None,
    image_path: str | None = None,
) -> ComicPage:
    if title is not None:
        page.title = title.strip()
    if page_no is not None:
        page.page_no = page_no
    if image_path is not None:
        old = page.image_path
        page.image_path = image_path
        if old and old != image_path:
            delete_upload(old)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def shift_page_nos_from(db: Session, from_no: int) -> None:
    """Bump page_no for all pages at/after from_no (high → low to avoid collisions)."""
    rows = list(
        db.scalars(
            select(ComicPage)
            .where(ComicPage.page_no >= from_no)
            .order_by(ComicPage.page_no.desc(), ComicPage.id.desc())
        ).all()
    )
    for row in rows:
        row.page_no = row.page_no + 1
        db.add(row)
    if rows:
        db.flush()


def insert_page_before(
    db: Session,
    *,
    before_page: ComicPage,
    title: str,
    image_path: str,
) -> ComicPage:
    """Insert a page immediately before before_page. Shifts that page and following."""
    text = title.strip()
    n = int(before_page.page_no)
    shift_page_nos_from(db, n)
    page = ComicPage(title=text, page_no=n, image_path=image_path)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


def renumber_pages_contiguous(db: Session, *, commit: bool = True) -> None:
    rows = list(
        db.scalars(
            select(ComicPage).order_by(ComicPage.page_no.asc(), ComicPage.id.asc())
        ).all()
    )
    for i, row in enumerate(rows, start=1):
        if row.page_no != i:
            row.page_no = i
            db.add(row)
    if commit:
        db.commit()
    else:
        db.flush()


def delete_page(db: Session, page: ComicPage) -> None:
    delete_upload(page.image_path)
    db.delete(page)
    db.flush()
    renumber_pages_contiguous(db, commit=True)


def neighbor_titles_for_insert_before(
    db: Session, *, before_page: ComicPage
) -> tuple[str | None, str]:
    """Return (prev_title, before_page title that will shift)."""
    nxt_title = before_page.title
    prev = db.scalar(
        select(ComicPage)
        .where(ComicPage.page_no < before_page.page_no)
        .order_by(ComicPage.page_no.desc(), ComicPage.id.desc())
        .limit(1)
    )
    prev_title = prev.title if prev is not None else None
    return prev_title, nxt_title
