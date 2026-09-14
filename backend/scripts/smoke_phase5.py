import json
import time
import urllib.request
from urllib.error import HTTPError

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
        with urllib.request.urlopen(request, timeout=15) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except Exception:
            payload = raw.decode(errors="replace")
        return exc.code, payload


def register(nick: str) -> str:
    status, reg = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, nick, None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    assert status == 200, reg
    return reg["access_token"]


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    ts = int(time.time())
    token_a = register(f"p5a_{ts}")
    token_b = register(f"p5b_{ts}")

    status, admin = req(
        "POST", "/api/admin/login", data={"username": "admin", "password": "admin123"}
    )
    assert status == 200, admin
    admin_token = admin["access_token"]

    status, page = req(
        "POST",
        "/api/admin/pages",
        headers=auth(admin_token),
        files={
            "title": (None, f"p5page_{ts}", None),
            "page_no": (None, "1", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, page
    page_id = page["id"]

    status, c1 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_a),
        data={"content": "comment by a"},
    )
    assert status == 201, c1
    top_id = c1["id"]

    # 1) B likes A -> A unread=1, list has like
    status, like = req(
        "POST",
        f"/api/comments/{top_id}/like",
        headers=auth(token_b),
    )
    assert status == 200 and like["liked"] is True, like

    status, unread = req("GET", "/api/notifications/unread-count", headers=auth(token_a))
    print("unread after like", status, unread)
    assert status == 200 and unread["count"] == 1

    status, lst = req("GET", "/api/notifications", headers=auth(token_a))
    assert status == 200
    assert lst["total"] == 1
    assert lst["items"][0]["type"] == "like"
    assert "赞了你的评论" in lst["items"][0]["summary"]
    like_notif_id = lst["items"][0]["id"]

    # 2) B likes again -> notification count unchanged
    status, _ = req(
        "POST",
        f"/api/comments/{top_id}/like",
        headers=auth(token_b),
    )
    assert status == 200
    status, lst2 = req("GET", "/api/notifications", headers=auth(token_a))
    assert status == 200 and lst2["total"] == 1
    print("repeat like ok, total still", lst2["total"])

    # 3) B replies -> A unread increases with reply
    status, reply = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_b),
        data={"content": "reply by b", "parent_id": top_id},
    )
    assert status == 201, reply

    status, unread2 = req("GET", "/api/notifications/unread-count", headers=auth(token_a))
    print("unread after reply", status, unread2)
    assert status == 200 and unread2["count"] == 2

    status, lst3 = req("GET", "/api/notifications", headers=auth(token_a))
    types = {n["type"] for n in lst3["items"]}
    assert types == {"like", "reply"}
    reply_notif = next(n for n in lst3["items"] if n["type"] == "reply")
    assert reply_notif["comment_id"] == reply["id"]
    assert reply_notif["comment_preview"] == "reply by b"

    # 4) A marks one read, then all read
    status, one = req(
        "POST",
        f"/api/notifications/{like_notif_id}/read",
        headers=auth(token_a),
    )
    assert status == 200 and one["is_read"] is True
    status, unread3 = req("GET", "/api/notifications/unread-count", headers=auth(token_a))
    assert status == 200 and unread3["count"] == 1

    status, all_read = req("POST", "/api/notifications/read-all", headers=auth(token_a))
    assert status == 200 and all_read["updated"] >= 1
    status, unread4 = req("GET", "/api/notifications/unread-count", headers=auth(token_a))
    assert status == 200 and unread4["count"] == 0
    print("read / read-all ok")

    # 5) delete parent comment -> notification remains, comment_id may be null
    status, _ = req(
        "DELETE",
        f"/api/admin/comments/{top_id}",
        headers=auth(admin_token),
    )
    assert status == 204

    status, lst4 = req("GET", "/api/notifications", headers=auth(token_a))
    assert status == 200 and lst4["total"] == 2
    for n in lst4["items"]:
        assert n["comment_preview"]
        # like/reply refs cleared after cascade delete
        assert n["comment_id"] is None
    print("nullify after delete ok")
    print("ALL_OK")


if __name__ == "__main__":
    main()
