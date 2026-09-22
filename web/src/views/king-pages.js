import { api, mediaUrl } from "../api.js";
import { isLoggedIn, loadKingProgress, isKingRead } from "../store.js";
import { go } from "../router.js";
import { escapeHtml } from "../util.js";

function showTip(root, message) {
  let tip = root.querySelector(".toast-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "toast-tip";
    tip.setAttribute("role", "status");
    root.appendChild(tip);
  }
  tip.textContent = message;
  tip.classList.add("show");
  clearTimeout(tip._hideTimer);
  tip._hideTimer = setTimeout(() => tip.classList.remove("show"), 1800);
}

export function renderKingPages(root, versionId) {
  if (!isLoggedIn()) {
    go("/login");
    return;
  }

  const id = Number(versionId) || 0;
  root.innerHTML = `
    <div class="screen">
      <header class="topbar">
        <button class="icon-btn" id="back" type="button" title="返回" aria-label="返回">←</button>
        <h1 id="title">加载中…</h1>
      </header>
      <div class="list" id="list">
        <div class="center">加载中…</div>
      </div>
    </div>
  `;

  const listEl = root.querySelector("#list");
  const titleEl = root.querySelector("#title");
  root.querySelector("#back").onclick = () => go("/home");

  function openSlot(item) {
    if (!item) return;
    if (!item.image_url) {
      showTip(root, "本版本该页尚未更新");
      return;
    }
    go(`/king/${id}/slot/${item.slot_id}`);
  }

  function renderList(versionName, items) {
    titleEl.textContent = versionName || "长寿之王";
    const prog = loadKingProgress();
    const parts = [];

    if (prog.lastPageNo > 0) {
      const cont = items.find((p) => p.page_no === prog.lastPageNo);
      if (cont) {
        parts.push(`
          <div class="card continue" data-slot="${cont.slot_id}">
            <div class="label">继续阅读</div>
            <div class="title">${escapeHtml(cont.title || prog.lastTitle || `第 ${cont.page_no} 页`)}</div>
          </div>`);
      }
    }

    for (const p of items) {
      const missing = !p.image_url;
      const read = isKingRead(p.page_no);
      const current = prog.lastPageNo > 0 && p.page_no === prog.lastPageNo;
      const cls = `card page-row${read ? " read" : ""}${current ? " current" : ""}${missing ? " missing" : ""}`;
      const sub = current ? "上次读到这里" : read ? "已读" : missing ? "未更新" : "";
      const thumb = missing
        ? `<div class="page-thumb-missing" aria-hidden="true">未更新</div>`
        : `<img src="${escapeHtml(mediaUrl(p.image_url))}" alt="" />`;
      parts.push(`
        <div class="${cls}" data-slot="${p.slot_id}">
          ${thumb}
          <div class="page-row-main">
            <div class="title">${escapeHtml(p.title || `第 ${p.page_no} 页`)}</div>
            ${sub ? `<div class="sub">${escapeHtml(sub)}</div>` : ""}
          </div>
        </div>`);
    }

    listEl.innerHTML =
      parts.join("") || `<div class="center">该版本还没有页。</div>`;

    const bySlot = new Map(items.map((p) => [String(p.slot_id), p]));
    listEl.querySelectorAll("[data-slot]").forEach((el) => {
      el.onclick = () => openSlot(bySlot.get(el.dataset.slot));
    });
  }

  (async () => {
    try {
      const res = await api.listKingVersionPages(id, { includeMissing: true });
      renderList(res.version_name, res.items || []);
    } catch (e) {
      if (!isLoggedIn() || e.status === 401) {
        go("/login");
        return;
      }
      titleEl.textContent = "长寿之王";
      listEl.innerHTML = `<div class="center error">${escapeHtml(e.message || "加载失败")}</div>`;
    }
  })();
}
