"""公开 king API 冒烟（需本机后端已启动）。"""

import json
import time
import urllib.request
from urllib.error import HTTPError

from sqlalchemy.orm import Session

from app.config import UPLOAD_DIR
from app.database import SessionLocal, init_db
from app.models.king import KingSlot
from app.services import king as king_service

BASE = "http://127.0.0.1:8000"
PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
    "0000000a49444154789a63000100000500010d0a2db40000000049454e44ae426082"
)


def req(method, path, data=None, headers=None, files=None):
    headers = dict(headers or {})
    if files:
        boundary = "----owlboundary"
        body = bytearray()
        for name, (fname, content, ctype) in files.items():
            body.extend(f"--{boundary}\r\n".encode())
            if fname:
                body.extend(
                    f'Content-Disposition: form-data; name="{name}"; filename="{fname}"\r\n'.encode()
                )
                body.extend(f"Content-Type: {ctype}\r\n\r\n".encode())
                body.extend(content)
                body.extend(b"\r\n")
            else:
                body.extend(f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode())
                body.extend(str(content).encode())
                body.extend(b"\r\n")
        body.extend(f"--{boundary}--\r\n".encode())
        headers["Content-Type"] = f"multipart/form-data; boundary={boundary}"
        data = bytes(body)
    elif isinstance(data, dict):
        data = json.dumps(data).encode()
        headers.setdefault("Content-Type", "application/json")
    request = urllib.request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except Exception:
            payload = raw.decode(errors="replace")
        return exc.code, payload


def seed() -> tuple[int, int, int, int]:
    init_db()
    db: Session = SessionLocal()
    try:
        (UPLOAD_DIR / "king_covers").mkdir(parents=True, exist_ok=True)
        (UPLOAD_DIR / "comics").mkdir(parents=True, exist_ok=True)
        cover_a = "king_covers/smoke_a.png"
        cover_b = "king_covers/smoke_b.png"
        img = "comics/smoke_k.png"
        (UPLOAD_DIR / cover_a).write_bytes(PNG)
        (UPLOAD_DIR / cover_b).write_bytes(PNG)
        (UPLOAD_DIR / img).write_bytes(PNG)

        a = king_service.default_version(db)
        if a is None:
            a = king_service.create_default_version(db, name="Smoke默认", cover_path=cover_a)
        else:
            king_service.update_version(db, a, name="Smoke默认")

        while king_service.pending_count(db, a.id) > 0:
            for row in king_service.list_version_slots(db, a.id):
                if row.image_url is None:
                    slot = db.get(KingSlot, row.slot_id)
                    king_service.upsert_version_slot(db, a, slot, image_path=img)

        s1 = king_service.append_global_page(
            db, a, title=f"smoke1_{time.time()}", image_path=img
        )
        king_service.append_global_page(db, a, title=f"smoke2_{time.time()}", image_path=img)

        b = king_service.create_version(
            db, name=f"SmokeB_{int(time.time())}", cover_path=cover_b
        )
        assert king_service.pending_count(db, b.id) >= 2
        return a.id, b.id, s1.id, s1.page_no
    finally:
        db.close()


def main() -> None:
    a_id, b_id, slot1_id, page_no = seed()
    ts = int(time.time())
    status, reg = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, f"kingapi_{ts}", None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    assert status == 200, reg
    uh = {"Authorization": f"Bearer {reg['access_token']}"}

    status, vers = req("GET", "/api/king/versions", headers=uh)
    assert status == 200, vers
    ids = {v["id"] for v in vers["items"]}
    assert a_id in ids and b_id in ids, vers

    status, pages_a = req("GET", f"/api/king/versions/{a_id}/pages", headers=uh)
    assert status == 200, pages_a
    assert any(p["slot_id"] == slot1_id for p in pages_a["items"]), pages_a

    status, resolved = req(
        "GET",
        f"/api/king/resolve?page_no={page_no}&preferred_version_id={b_id}",
        headers=uh,
    )
    assert status == 200, resolved
    assert resolved["switched"] is True
    assert resolved["version_id"] == a_id

    status, resolved2 = req(
        "GET",
        f"/api/king/resolve?slot_id={slot1_id}&preferred_version_id={a_id}",
        headers=uh,
    )
    assert status == 200 and resolved2["switched"] is False, resolved2

    status, c = req(
        "POST",
        f"/api/king/slots/{slot1_id}/comments",
        headers=uh,
        data={"content": "king shared comment", "parent_id": None},
    )
    assert status == 201 and c["king_slot_id"] == slot1_id, c

    status, lst = req(
        "GET", f"/api/king/slots/{slot1_id}/comments?sort=latest", headers=uh
    )
    assert status == 200 and any(i["id"] == c["id"] for i in lst["items"]), lst
    print("smoke_king_api: ok")


if __name__ == "__main__":
    main()
