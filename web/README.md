# The Owl House · 读者网页

手机优先的读者站（Vite + 原生 JS），对标 App：登录/注册、列表、阅读、评论、消息。  
不做 App 版本更新。与 FastAPI **同域**部署后，浏览器打开 `http://<公网IP>/` 即可。

## 本地开发

需 Node.js 18+。默认把 `/api`、`/media` 代理到生产机 `http://101.132.75.57`。若本机已跑后端：

```powershell
cd web
$env:VITE_PROXY_TARGET="http://127.0.0.1:8000"
npm install
npm run dev
```

电脑打开终端里的 `http://127.0.0.1:5173`。

手机请用电脑的 **局域网 IP**，不要用 `localhost`（那是手机自己）。例如：

```text
http://192.168.1.120:5173
```

`npm run dev` 已设置 `host: true`，会监听 `0.0.0.0:5173`。电脑防火墙若拦截，需放行 5173。

电脑阅读：单击显示顶栏和评论；按住左右拖动翻页（拖过约一指宽即可）；也可用方向键。

## 打包

```powershell
cd web
npm install
npm run build
```

产物在 `web/dist/`（`index.html` + `assets/`）。

## 部署到云服务器

把 [`docs/AI服务器部署手册.md`](docs/AI服务器部署手册.md) 交给 AI，按「填写区」填好后逐步执行。已填密码的手册不要提交 Git。

## 部署到现有 Nginx（给服务器 AI）

目标：

- `http://公网IP/` → 本目录静态文件（读者站）
- `/api/` `/admin` `/media/` `/static/` → `http://127.0.0.1:8000`（FastAPI）

步骤：

1. 把本地 `web/dist/` 全部拷到服务器 `/www/wwwroot/owlhouse-web/`（需含 `index.html`）。
2. **备份**现有站点 conf（常见 `/www/server/nginx/conf/vhost/owlhouse.conf`）。
3. 用下面配置替换 `location /` 整段（保留 `listen 80`、`server_name`、`client_max_body_size 32m`）。
4. `nginx -t` 通过后 `nginx -s reload`。
5. 手机流量打开 `http://公网IP/` 应为登录页，不是 JSON。  
   `http://公网IP/api/health` 仍返回 JSON。  
   `http://公网IP/admin/` 管理后台仍可用。

配置示例见同目录 [`deploy-nginx.conf`](deploy-nginx.conf)。

更新网页：重新 `npm run build`，覆盖服务器 `owlhouse-web/`，一般不用 reload Nginx。
