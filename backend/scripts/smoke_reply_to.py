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


def register(nick: str) -> tuple[str, str]:
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
    return reg["access_token"], nick


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def unread(token: str) -> int:
    status, body = req("GET", "/api/notifications/unread-count", headers=auth(token))
    assert status == 200, body
    return int(body["count"])


def main() -> None:
    ts = int(time.time())
    token_a, nick_a = register(f"rta_{ts}")
    token_b, nick_b = register(f"rtb_{ts}")
    token_c, _nick_c = register(f"rtc_{ts}")

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
            "title": (None, f"rtpage_{ts}", None),
            "page_no": (None, "1", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, page
    page_id = page["id"]

    # 1) A top -> B reply A -> A gets reply notif
    status, top = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_a),
        data={"content": "top by a"},
    )
    assert status == 201, top
    top_id = top["id"]
    unread_a0 = unread(token_a)

    status, reply_b = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_b),
        data={"content": "reply by b", "parent_id": top_id},
    )
    assert status == 201, reply_b
    assert reply_b["parent_id"] == top_id
    assert reply_b.get("reply_to_nickname") in (None, "")
    b_id = reply_b["id"]
    assert unread(token_a) == unread_a0 + 1
    print("B reply A -> A notified ok")

    unread_b0 = unread(token_b)
    unread_a1 = unread(token_a)

    # 2) C reply B's nested -> flatten under A; notify B not A
    status, reply_c = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_c),
        data={"content": "reply to b", "parent_id": b_id},
    )
    assert status == 201, reply_c
    assert reply_c["parent_id"] == top_id
    assert reply_c["reply_to_id"] == b_id
    assert reply_c["reply_to_nickname"] == nick_b
    assert unread(token_b) == unread_b0 + 1
    assert unread(token_a) == unread_a1
    print("C reply B nested -> B notified, A unchanged ok")

    # 3) list shows reply_to_nickname for C
    status, tree = req(
        "GET",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_a),
    )
    assert status == 200, tree
    replies = tree["items"][0]["replies"]
    c_item = next(r for r in replies if r["id"] == reply_c["id"])
    assert c_item["reply_to_nickname"] == nick_b
    b_item = next(r for r in replies if r["id"] == b_id)
    assert b_item.get("reply_to_nickname") in (None, "")
    print("list reply_to_nickname ok")
    print("ALL_OK")


if __name__ == "__main__":
    main()
