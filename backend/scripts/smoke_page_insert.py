"""同人页插入顺延与删除重排冒烟（独立内存库）。"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.comic import ComicPage
from app.services import pages as pages_service


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine)()


def _nos(db) -> list[int]:
    rows = list(
        db.scalars(select(ComicPage).order_by(ComicPage.page_no.asc(), ComicPage.id.asc())).all()
    )
    return [r.page_no for r in rows]


def _titles(db) -> list[str]:
    rows = list(
        db.scalars(select(ComicPage).order_by(ComicPage.page_no.asc(), ComicPage.id.asc())).all()
    )
    return [r.title for r in rows]


def main() -> None:
    db = _session()
    p1 = pages_service.create_page(db, title="一", image_path="comics/1.png")
    p2 = pages_service.create_page(db, title="二", image_path="comics/2.png")
    p3 = pages_service.create_page(db, title="三", image_path="comics/3.png")
    assert _nos(db) == [1, 2, 3], _nos(db)

    # insert before p2 (= after p1): new is 2, old 2→3, 3→4
    mid = pages_service.insert_page_before(
        db, before_page=p2, title="一后", image_path="comics/1b.png"
    )
    assert mid.page_no == 2, mid.page_no
    assert _titles(db) == ["一", "一后", "二", "三"], _titles(db)
    assert _nos(db) == [1, 2, 3, 4], _nos(db)

    # insert before first page
    p1 = db.scalar(select(ComicPage).where(ComicPage.title == "一"))
    assert p1 is not None
    front = pages_service.insert_page_before(
        db, before_page=p1, title="最前", image_path="comics/0.png"
    )
    assert front.page_no == 1, front.page_no
    assert _titles(db) == ["最前", "一", "一后", "二", "三"], _titles(db)
    assert _nos(db) == [1, 2, 3, 4, 5], _nos(db)

    victim = db.scalar(select(ComicPage).where(ComicPage.title == "一后"))
    assert victim is not None
    pages_service.delete_page(db, victim)
    assert _titles(db) == ["最前", "一", "二", "三"], _titles(db)
    assert _nos(db) == [1, 2, 3, 4], _nos(db)

    print("smoke_page_insert: ok")


if __name__ == "__main__":
    main()
