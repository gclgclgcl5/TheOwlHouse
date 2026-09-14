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


def main() -> None:
    status, admin = req(
        "POST", "/api/admin/login", data={"username": "admin", "password": "admin123"}
    )
    assert status == 200, admin
    token = admin["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    ts = int(time.time())
    status, p1 = req(
        "POST",
        "/api/admin/pages",
        headers=h,
        files={
            "title": (None, f"auto1_{ts}", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, p1
    assert p1["page_no"] == 1, p1

    status, p2 = req(
        "POST",
        "/api/admin/pages",
        headers=h,
        files={
            "title": (None, f"auto2_{ts}", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, p2
    assert p2["page_no"] == 2, p2

    # register user to list by page_no
    status, reg = req(
        "POST",
        "/api/auth/register",
        files={
            "nickname": (None, f"pn_{ts}", None),
            "password": (None, "pass1234", None),
            "avatar": ("a.png", PNG, "image/png"),
        },
    )
    assert status == 200, reg
    uh = {"Authorization": f"Bearer {reg['access_token']}"}
    status, lst = req("GET", "/api/pages?order=page_no&limit=100", headers=uh)
    assert status == 200, lst
    nos = [i["page_no"] for i in lst["items"]]
    assert nos == sorted(nos), nos
    assert p1["id"] in [i["id"] for i in lst["items"]]
    print("page_no auto-increment + order ok")
    print("ALL_OK")


if __name__ == "__main__":
    main()
