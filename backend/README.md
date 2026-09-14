# The Owl House · Backend

FastAPI 后端：REST API + 管理网站。当前为骨架，可供局域网联调。

## 快速启动

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python run.py
```

> 必须先激活 `.venv`。直接用系统 `python run.py` 会报 `No module named 'uvicorn'`。

浏览器访问：

- 根信息：http://127.0.0.1:8000/
- 管理后台骨架：http://127.0.0.1:8000/admin/
- API 文档：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/api/health

## 手机局域网访问

1. 确认 `HOST=0.0.0.0`（默认如此）。
2. 在电脑上查局域网 IP（如 `ipconfig` 中的 IPv4）。
3. 手机与电脑同一 Wi‑Fi，访问 `http://<电脑IP>:8000/api/health`。
4. Android App 的 Base URL 填同一地址（不要用 `localhost`）。

## 目录说明

见仓库 `docs/技术选型与目录约定.md`。

## 部署到云服务器（公网 IP，不备案）

把 `docs/AI服务器部署手册.md` 交给 AI，按文中「填写区」填好密码与 Token 后逐步执行。已填密码的手册不要提交到 Git。

读者网页见仓库旁 `web/`（`npm run build`，Nginx 配置见 `web/deploy-nginx.conf`）。
