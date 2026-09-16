import { getToken, logout } from "./store.js";

function parseDetail(body) {
  if (!body) return "";
  try {
    const data = JSON.parse(body);
    const d = data.detail;
    if (typeof d === "string") return d;
    if (Array.isArray(d)) {
      return d
        .map((el) => (typeof el === "string" ? el : el?.msg))
        .filter(Boolean)
        .join("；");
    }
  } catch {
    return "";
  }
  return "";
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

async function request(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;
  if (options.body && !(options.body instanceof FormData) && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }
  let res;
  try {
    res = await fetch(path, { ...options, headers });
  } catch {
    throw new ApiError("网络异常，请检查网络后重试", 0);
  }
  if (res.status === 401) {
    logout();
    throw new ApiError("登录已失效，请重新登录", 401);
  }
  if (!res.ok) {
    const raw = await res.text();
    const detail = parseDetail(raw);
    const fallback =
      res.status === 400
        ? "请求无效，请检查输入"
        : res.status === 403
          ? "没有权限"
          : res.status === 404
            ? "内容不存在"
            : res.status === 413
              ? "文件过大"
              : res.status >= 500
                ? "服务器繁忙，请稍后再试"
                : "请求失败";
    throw new ApiError(detail || fallback, res.status);
  }
  if (res.status === 204) return null;
  const text = await res.text();
  if (!text) return null;
  return JSON.parse(text);
}

export const api = {
  login(nickname, password) {
    return request("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ nickname, password }),
    });
  },
  register(nickname, password, avatarFile) {
    const fd = new FormData();
    fd.append("nickname", nickname);
    fd.append("password", password);
    fd.append("avatar", avatarFile, avatarFile.name || "avatar.jpg");
    return request("/api/auth/register", { method: "POST", body: fd });
  },
  listPages({ limit = 20, offset = 0, order = "page_no" } = {}) {
    const q = new URLSearchParams({ limit, offset, order });
    return request(`/api/pages?${q}`);
  },
  getPage(id) {
    return request(`/api/pages/${id}`);
  },
  listComments(pageId, sort = "latest") {
    return request(`/api/pages/${pageId}/comments?sort=${encodeURIComponent(sort)}`);
  },
  createComment(pageId, content, parentId = null) {
    return request(`/api/pages/${pageId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content, parent_id: parentId }),
    });
  },
  likeComment(id) {
    return request(`/api/comments/${id}/like`, { method: "POST" });
  },
  unlikeComment(id) {
    return request(`/api/comments/${id}/like`, { method: "DELETE" });
  },
  listNotifications({ limit = 50, offset = 0 } = {}) {
    const q = new URLSearchParams({ limit, offset });
    return request(`/api/notifications?${q}`);
  },
  unreadCount() {
    return request("/api/notifications/unread-count");
  },
  markNotificationRead(id) {
    return request(`/api/notifications/${id}/read`, { method: "POST" });
  },
  markAllNotificationsRead() {
    return request("/api/notifications/read-all", { method: "POST" });
  },
  homeAnnouncement() {
    return request("/api/home-announcement");
  },
  listKingVersions() {
    return request("/api/king/versions");
  },
  listKingVersionPages(versionId) {
    return request(`/api/king/versions/${versionId}/pages`);
  },
  resolveKingPage({ page_no, slot_id, preferred_version_id } = {}) {
    const q = new URLSearchParams();
    if (page_no != null) q.set("page_no", String(page_no));
    if (slot_id != null) q.set("slot_id", String(slot_id));
    if (preferred_version_id != null) q.set("preferred_version_id", String(preferred_version_id));
    return request(`/api/king/resolve?${q}`);
  },
  listKingComments(slotId, sort = "latest") {
    return request(`/api/king/slots/${slotId}/comments?sort=${encodeURIComponent(sort)}`);
  },
  createKingComment(slotId, content, parentId = null) {
    return request(`/api/king/slots/${slotId}/comments`, {
      method: "POST",
      body: JSON.stringify({ content, parent_id: parentId }),
    });
  },
};

export function mediaUrl(path) {
  if (!path) return "";
  if (path.startsWith("http://") || path.startsWith("https://")) return path;
  return path.startsWith("/") ? path : `/${path}`;
}
