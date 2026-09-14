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
    print("health", req("GET", "/api/health"))

    status, reg = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, "tester01", None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    print("register", status, reg)
    assert status == 200, reg
    user_token = reg["access_token"]

    status, dup = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, "tester01", None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    print("dup", status, dup)
    assert status == 400

    status, me = req("GET", "/api/auth/me", headers={"Authorization": f"Bearer {user_token}"})
    print("me", status, me)
    assert status == 200

    status, _ = req("GET", "/api/pages")
    print("pages unauth", status)
    assert status == 401

    status, admin = req(
        "POST",
        "/api/admin/login",
        data={"username": "admin", "password": "admin123"},
    )
    print("admin login", status, admin)
    assert status == 200
    admin_token = admin["access_token"]

    status, page = req(
        "POST",
        "/api/admin/pages",
        headers={"Authorization": f"Bearer {admin_token}"},
        files={
            "title": (None, "测试第一页", None),
            "page_no": (None, "1", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    print("create page", status, page)
    assert status == 201, page
    page_id = page["id"]

    status, pages = req(
        "GET",
        "/api/pages",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print("pages", status, pages["total"] if status == 200 else pages)
    assert status == 200 and pages["total"] >= 1

    status, detail = req(
        "GET",
        f"/api/pages/{page_id}",
        headers={"Authorization": f"Bearer {user_token}"},
    )
    print("detail", status, detail["title"] if status == 200 else detail)
    assert status == 200

    print("admin login html", urllib.request.urlopen(BASE + "/admin/login").status)
    print("ALL_OK")


if __name__ == "__main__":
    main()
