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
    token_a = register(f"sa_{ts}")
    token_b = register(f"sb_{ts}")

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
            "title": (None, f"sortpage_{ts}", None),
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
        data={"content": "older low likes"},
    )
    assert status == 201, c1
    time.sleep(1.1)
    status, c2 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=auth(token_a),
        data={"content": "newer will be hot"},
    )
    assert status == 201, c2

    status, _ = req(
        "POST",
        f"/api/comments/{c2['id']}/like",
        headers=auth(token_b),
    )
    assert status == 200

    status, latest = req(
        "GET",
        f"/api/pages/{page_id}/comments?sort=latest",
        headers=auth(token_a),
    )
    assert status == 200, latest
    ours = [i for i in latest["items"] if i["id"] in (c1["id"], c2["id"])]
    assert len(ours) == 2, latest["items"]
    assert ours[0]["id"] == c2["id"], ours
    assert latest["items"][0]["id"] == c2["id"], latest["items"]

    status, hot = req(
        "GET",
        f"/api/pages/{page_id}/comments?sort=hot",
        headers=auth(token_a),
    )
    assert status == 200, hot
    assert hot["items"][0]["id"] == c2["id"]
    assert hot["items"][0]["like_count"] >= 1
    print("sort latest/hot ok")
    print("ALL_OK")


if __name__ == "__main__":
    main()
