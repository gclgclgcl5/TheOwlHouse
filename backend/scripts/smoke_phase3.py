import json
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
        with urllib.request.urlopen(request, timeout=10) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw) if raw else None
    except HTTPError as exc:
        raw = exc.read()
        try:
            payload = json.loads(raw) if raw else None
        except Exception:
            payload = raw.decode(errors="replace")
        return exc.code, payload


def main() -> None:
    nick = "phase3_user"
    status, reg = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, nick, None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    # allow re-run: if nickname taken, login instead then we need a fresh user
    if status != 200:
        import time

        nick = f"phase3_user_{int(time.time())}"
        status, reg = req(
            "POST",
            "/api/auth/register",
            files={
                "nickname": (None, nick, None),
                "password": (None, "pass1234", None),
                "avatar": ("a.png", PNG, "image/png"),
            },
        )
    print("register", status)
    assert status == 200, reg
    user_token = reg["access_token"]

    status, me = req("GET", "/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    print("me", status, me["id"] if status == 200 else me)
    assert status == 200
    user_id = me["id"]

    status, admin = req(
        "POST",
        "/api/admin/login",
        data={"username": "admin", "password": "admin123"},
    )
    assert status == 200, admin
    admin_token = admin["access_token"]

    status, users = req(
        "GET",
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print("list users", status, users["total"] if status == 200 else users)
    assert status == 200
    assert any(u["id"] == user_id for u in users["items"])

    status, _ = req(
        "DELETE",
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print("delete", status)
    assert status == 204

    status, users2 = req(
        "GET",
        "/api/admin/users",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert status == 200
    assert all(u["id"] != user_id for u in users2["items"])
    print("list after delete ok, total", users2["total"])

    status, login = req(
        "POST",
        "/api/auth/login",
        data={"nickname": nick, "password": "pass1234"},
    )
    print("login deleted", status, login)
    assert status == 400

    status, pages = req(
        "GET",
        "/api/pages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print("old token pages", status)
    assert status == 401

    status, again = req(
        "DELETE",
        f"/api/admin/users/{user_id}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    print("delete again", status)
    assert status == 404

    print("admin users html", urllib.request.urlopen(BASE + "/admin/login").status)
    print("ALL_OK")


if __name__ == "__main__":
    main()
