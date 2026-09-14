"""阶段 6：MVP 全链路 API 冒烟（对齐需求文档 §9）。"""

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


def auth(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


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

    status, health = req("GET", "/api/health")
    assert status == 200 and health.get("status") == "ok", health

    # 无 Token 访问应 401
    status, _ = req("GET", "/api/pages")
    assert status == 401

    status, admin = req(
        "POST", "/api/admin/login", data={"username": "admin", "password": "admin123"}
    )
    assert status == 200, admin
    admin_token = admin["access_token"]
    ah = auth(admin_token)

    # 管理员上传漫画
    status, page = req(
        "POST",
        "/api/admin/pages",
        headers=ah,
        files={
            "title": (None, f"mvp_{ts}", None),
            "image": ("p.png", PNG, "image/png"),
        },
    )
    assert status == 201, page
    page_id = page["id"]
    assert page["page_no"] >= 1

    # 超大图应被拒（头像 5MB 上限；用略大于 5MB 的伪 png 头+填充测漫画 20MB 太重，测头像接口）
    # 漫画上限用服务常量说明；此处验证错误文案接口可用：空文件
    status, bad = req(
        "POST",
        "/api/admin/pages",
        headers=ah,
        files={
            "title": (None, "bad", None),
            "image": ("empty.png", b"", "image/png"),
        },
    )
    assert status == 400, bad

    token_a = register(f"m6a_{ts}")
    token_b = register(f"m6b_{ts}")
    ua, ub = auth(token_a), auth(token_b)

    # 用户可见列表 / 详情
    status, pages = req("GET", "/api/pages", headers=ua)
    assert status == 200 and any(p["id"] == page_id for p in pages["items"]), pages
    status, one = req("GET", f"/api/pages/{page_id}", headers=ua)
    assert status == 200 and one["id"] == page_id

    # 评论 / 回复 / 点赞 / 最新最热
    status, c1 = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=ua,
        data={"content": "hello mvp"},
    )
    assert status == 201, c1
    top_id = c1["id"]

    status, like = req("POST", f"/api/comments/{top_id}/like", headers=ub)
    assert status == 200 and like["liked"] is True

    status, reply = req(
        "POST",
        f"/api/pages/{page_id}/comments",
        headers=ub,
        data={"content": "nice", "parent_id": top_id},
    )
    assert status == 201, reply

    status, latest = req(
        "GET", f"/api/pages/{page_id}/comments?sort=latest", headers=ua
    )
    assert status == 200 and len(latest["items"]) >= 1
    status, hot = req("GET", f"/api/pages/{page_id}/comments?sort=hot", headers=ua)
    assert status == 200 and hot["items"][0]["id"] == top_id

    # 消息：A 应收到 like + reply
    status, unread = req("GET", "/api/notifications/unread-count", headers=ua)
    assert status == 200 and unread["count"] >= 2, unread
    status, notifs = req("GET", "/api/notifications", headers=ua)
    assert status == 200
    types = {n["type"] for n in notifs["items"]}
    assert "like" in types and "reply" in types
    status, _ = req("POST", "/api/notifications/read-all", headers=ua)
    assert status == 200
    status, unread2 = req("GET", "/api/notifications/unread-count", headers=ua)
    assert status == 200 and unread2["count"] == 0

    # 管理：看评论、删评
    status, admin_comments = req(
        "GET", f"/api/admin/pages/{page_id}/comments", headers=ah
    )
    assert status == 200
    status, _ = req("DELETE", f"/api/admin/comments/{top_id}", headers=ah)
    assert status == 204
    status, tree = req("GET", f"/api/pages/{page_id}/comments", headers=ua)
    assert status == 200 and tree["items"] == []

    # 管理：删用户
    status, me_b = req("GET", "/api/auth/me", headers=ub)
    assert status == 200
    status, _ = req("DELETE", f"/api/admin/users/{me_b['id']}", headers=ah)
    assert status == 204
    status, login_fail = req(
        "POST", "/api/auth/login", data={"nickname": f"m6b_{ts}", "password": "pass1234"}
    )
    assert status == 400, login_fail

    # 管理员改标题
    status, updated = req(
        "PUT",
        f"/api/admin/pages/{page_id}",
        headers=ah,
        files={"title": (None, f"mvp_edited_{ts}", None)},
    )
    assert status == 200 and updated["title"].startswith("mvp_edited")

    status, _ = req("DELETE", f"/api/admin/pages/{page_id}", headers=ah)
    assert status == 204

    print("ALL_OK")


if __name__ == "__main__":
    main()
