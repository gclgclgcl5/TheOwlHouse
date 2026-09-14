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


def main() -> None:
    ts = int(time.time())
    token_a = register(f"p4a_{ts}")
    token_b = register(f"p4b_{ts}")

    status, admin = req(
        "POST", "/api/admin/login", data={"username": "admin", "password": "admin123"}
    )
    assert status == 200, admin
    admin_token = admin["access_token"]

    status, page = req(
        "POST",
        "/api/admin/pages",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "title": (None, f"p4page_{ts}", None),
            "page_no": (None, "1", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, page
    page_id = page["id"]

    status, c1 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_a}"},
        data={"content": "hello top"},
    )
    print("create top", status, c1)
    assert status == 201
    top_id = c1["id"]

    status, c2 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_b}"},
        data={"content": "reply one", "parent_id": top_id},
    )
    print("create reply", status, c2)
    assert status == 201
    assert c2["parent_id"] == top_id

    status, like = req(
        "POST",
        f"/api/comments/{top_id}/like",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    print("like", status, like)
    assert status == 200 and like["liked"] is True and like["like_count"] == 1

    status, tree = req(
        "GET",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    print("tree", status, len(tree["items"]), tree["items"][0]["like_count"])
    assert status == 200
    assert len(tree["items"]) == 1
    assert len(tree["items"][0]["replies"]) == 1
    assert tree["items"][0]["liked_by_me"] is True

    status, _ = req(
        "DELETE",
        f"/api/comments/{top_id}/like",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    print("unlike", status)
    assert status == 204

    status, me_b = req("GET", "/api/auth/me", headers={"Authorization": f"Bearer {token_b}"})
    assert status == 200
    user_b_id = me_b["id"]

    # B likes again then soft-delete B -> like gone
    req(
        "POST",
        f"/api/comments/{top_id}/like",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    status, _ = req(
        "DELETE",
        f"/api/admin/users/{user_b_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status == 204
    status, tree2 = req(
        "GET",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert status == 200
    assert tree2["items"][0]["like_count"] == 0
    reply = tree2["items"][0]["replies"][0]
    assert reply["author_deleted"] is True
    assert reply["author_nickname"] == "已注销用户"
    print("deleted author display ok")

    # recreate reply for cascade test
    token_c = register(f"p4c_{ts}")
    status, c3 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_c}"},
        data={"content": "reply two", "parent_id": top_id},
    )
    assert status == 201

    status, _ = req(
        "DELETE",
        f"/api/admin/comments/{top_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print("admin delete parent", status)
    assert status == 204
    status, tree3 = req(
        "GET",
        f"/api/pages/{page_id}/comments",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    assert status == 200 and tree3["items"] == []
    print("ALL_OK")


if __name__ == "__main__":
    main()
