# The Owl House

汉化连载漫画阅读 + 按页评论的 Android App，配合本地后端与管理网站。

一期 **MVP 已完成**（阶段 0–6）：注册登录、漫画发布/阅读、评论回复点赞、站内消息、管理站治理。

## 目录

```
TheOwlHouse/
├── docs/       # 需求、选型、实现计划
├── backend/    # FastAPI：用户/管理 API + Jinja 管理站
├── web/        # 读者网页（Vite + 原生 JS）
└── app/        # Android（Kotlin + Compose）用户端
```

仓库：[github.com/gclgclgcl5/TheOwlHouse](https://github.com/gclgclgcl5/TheOwlHouse.git)

- 需求：[docs/需求文档.md](docs/需求文档.md)
- 选型：[docs/技术选型与目录约定.md](docs/技术选型与目录约定.md)
- 计划：[docs/实现计划-阶段012.md](docs/实现计划-阶段012.md) · [docs/实现计划-阶段345.md](docs/实现计划-阶段345.md)

## 功能一览（MVP）

| 角色 | 能力 |
|------|------|
| 管理员 | 登录后台；漫画增删改（页序自动递增）；按页看/删评论；软删用户 |
| 用户 App | 注册（昵称+头像）/登录；下拉刷新漫画列表；沉浸阅读+左右滑翻页；底部评论面板（最新/最热）；回复楼中楼；点赞；消息中心与未读角标 |

明确不做（二期）：系统推送、消息定位到楼层、改资料、举报禁言等。

## 启动后端

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python run.py
```

也可参考仓库根目录 `docs/后端开启命令.txt`。

- 健康检查：http://127.0.0.1:8000/api/health  
- 管理站：http://127.0.0.1:8000/admin/（默认账号见 `.env`，示例 `admin` / `admin123`）  
- API 文档：http://127.0.0.1:8000/docs  

上传限制：漫画图 **20MB**，头像 **5MB**；格式 jpg/png/webp/gif。

## Android 联调

1. 电脑与手机同一 Wi‑Fi；后端监听 `0.0.0.0:8000`。
2. 用 Android Studio 打开 **`app/`** 目录（见 [app/README.md](app/README.md)）。
3. 将 `app/reader/build.gradle.kts` 中 `API_BASE_URL` 改为 `http://<电脑IPv4>:8000/`（当前示例 `192.168.1.120`）。
4. 打包：`cd app` → `.\gradlew.bat :reader:assembleDebug`  
   APK：`app/reader/build/outputs/apk/debug/reader-debug.apk`

自定义图标：把 PNG 放到 `app/reader/branding/app_icon.png`，执行 `python apply_icon.py` 后重装。

## 冒烟脚本（backend）

在 `backend` 且服务已启动时：

```powershell
.\.venv\Scripts\python.exe scripts\smoke_phase6.py
```

另有 `smoke_phase012.py` … `smoke_phase5.py`、`smoke_reply_to.py`、`smoke_page_no.py` 等分阶段脚本。

## 技术栈

| 端 | 技术 |
|----|------|
| 后端 + 管理站 | Python 3.12 · FastAPI · SQLAlchemy · SQLite · Jinja2 · JWT/Session |
| Android | Kotlin · Compose · Retrofit · Coil · AGP 8.4 / Gradle 8.6 |
