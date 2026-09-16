import { api, mediaUrl } from "../api.js";
import { isLoggedIn, loadKingProgress } from "../store.js";
import { go } from "../router.js";
import { escapeHtml, avatarHtml } from "../util.js";

export function renderNotifications(root) {
  if (!isLoggedIn()) {
    go("/login");
    return;
  }

  root.innerHTML = `
    <div class="screen">
      <header class="topbar">
        <button class="icon-btn" id="back" type="button">←</button>
        <h1>消息</h1>
        <button class="btn-ghost" id="all" type="button" style="width:auto;padding:8px 12px">全部已读</button>
      </header>
      <div class="list" id="list"><div class="center">加载中…</div></div>
    </div>
  `;
  const listEl = root.querySelector("#list");
  root.querySelector("#back").onclick = () => go("/home");

  async function openNotification(n) {
    if (n.king_slot_id) {
      const preferred = loadKingProgress().lastVersionId || undefined;
      try {
        const resolved = await api.resolveKingPage({
          slot_id: n.king_slot_id,
          preferred_version_id: preferred || null,
        });
        go(`/king/${resolved.version_id}/slot/${resolved.slot_id}`);
      } catch {
        go("/home");
      }
      return;
    }
    if (n.page_id) go(`/page/${n.page_id}`);
    else go("/home");
  }

  async function load() {
    try {
      const res = await api.listNotifications();
      const items = res.items || [];
      root.querySelector("#all").disabled = !items.some((n) => !n.is_read);
      if (!items.length) {
        listEl.innerHTML = `<div class="center">暂无消息</div>`;
        return;
      }
      listEl.innerHTML = items
        .map((n) => {
          const av = avatarHtml(mediaUrl(n.actor_avatar_url), n.actor_nickname);
          const preview = n.comment_preview
            ? `<div class="sub">${escapeHtml(n.comment_preview)}</div>`
            : "";
          return `
            <div class="notif${n.is_read ? " read" : ""}" data-id="${n.id}" data-page="${n.page_id || ""}" data-slot="${n.king_slot_id || ""}">
              ${av}
              <div style="flex:1">
                <div>${escapeHtml(n.summary)}</div>
                ${preview}
              </div>
              ${n.is_read ? "" : `<span class="dot"></span>`}
            </div>`;
        })
        .join("");
      listEl.querySelectorAll(".notif").forEach((el) => {
        el.onclick = async () => {
          const id = Number(el.dataset.id);
          const page = el.dataset.page ? Number(el.dataset.page) : 0;
          const slot = el.dataset.slot ? Number(el.dataset.slot) : 0;
          try {
            if (!el.classList.contains("read")) await api.markNotificationRead(id);
          } catch {
            /* still open */
          }
          await openNotification({ page_id: page || null, king_slot_id: slot || null });
        };
      });
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
      else listEl.innerHTML = `<div class="center error">${escapeHtml(e.message || "加载失败")}</div>`;
    }
  }

  root.querySelector("#all").onclick = async () => {
    try {
      await api.markAllNotificationsRead();
      load();
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
    }
  };

  load();
}
