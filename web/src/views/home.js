import { api, mediaUrl } from "../api.js";
import {
  isLoggedIn,
  loadProgress,
  logout,
  isRead,
  loadCollectionMode,
  saveCollectionMode,
  loadHomeTab,
  saveHomeTab,
  loadKingProgress,
} from "../store.js";
import { go } from "../router.js";
import { escapeHtml } from "../util.js";

const PAGE_SIZE = 20;

function groupPagesByExactTitle(pages) {
  const map = new Map();
  for (const p of pages) {
    const key = p.title;
    if (!map.has(key)) map.set(key, []);
    map.get(key).push(p);
  }
  const collections = [];
  for (const [title, list] of map) {
    const sorted = list.slice().sort((a, b) => {
      if (a.page_no !== b.page_no) return a.page_no - b.page_no;
      return a.id - b.id;
    });
    collections.push({ title, cover: sorted[0], pages: sorted, count: sorted.length });
  }
  collections.sort((a, b) => {
    if (a.cover.page_no !== b.cover.page_no) return a.cover.page_no - b.cover.page_no;
    return a.cover.id - b.cover.id;
  });
  return collections;
}

export function renderHome(root) {
  if (!isLoggedIn()) {
    go("/login");
    return;
  }

  let pages = [];
  let total = 0;
  let loadingMore = false;
  let title = "欢迎来到沸腾群岛！";
  let collectionMode = loadCollectionMode();
  let homeTab = loadHomeTab();
  let kingVersions = [];

  root.innerHTML = `
    <div class="screen">
      <header class="topbar">
        <div class="marquee" id="announce"><span id="announce-text"></span></div>
        <button class="icon-btn${collectionMode ? " on" : ""}" id="collection" type="button" title="合集模式" aria-pressed="${collectionMode ? "true" : "false"}">
          <svg class="icon-layers" viewBox="0 0 24 24" width="22" height="22" aria-hidden="true">
            <path fill="currentColor" d="M12 2 2 7l10 5 10-5-10-5zm0 9L2 6v2l10 5 10-5V6l-10 5zm0 4L2 10v2l10 5 10-5v-2l-10 5z"/>
          </svg>
        </button>
        <button class="icon-btn" id="msg" type="button" title="消息">🔔<span class="badge hidden" id="badge"></span></button>
        <button class="icon-btn" id="logout" type="button" title="退出">⎋</button>
      </header>
      <nav class="home-tabs" aria-label="分区">
        <button type="button" class="home-tab${homeTab === "doujin" ? " on" : ""}" data-tab="doujin">同人漫画</button>
        <button type="button" class="home-tab${homeTab === "king" ? " on" : ""}" data-tab="king">长寿之王</button>
      </nav>
      <div class="list" id="list"></div>
    </div>
    <div class="dialog-mask hidden" id="dlg">
      <div class="dialog">
        <h2>退出登录</h2>
        <p>确定要退出当前账号吗？</p>
        <div class="dialog-actions">
          <button type="button" id="dlg-no">取消</button>
          <button type="button" id="dlg-yes">退出</button>
        </div>
      </div>
    </div>
  `;

  const listEl = root.querySelector("#list");
  const announceText = root.querySelector("#announce-text");
  const badge = root.querySelector("#badge");
  const dlg = root.querySelector("#dlg");
  const collectionBtn = root.querySelector("#collection");

  function setAnnounce(text) {
    title = text || title;
    const show = title.length > 12 ? `${title}\u00a0\u00a0\u00a0${title}` : title;
    announceText.textContent = show;
    announceText.style.animation = title.length > 12 ? "" : "none";
    if (title.length <= 12) announceText.style.transform = "none";
  }
  setAnnounce(title);

  function syncCollectionBtn() {
    const show = homeTab === "doujin";
    collectionBtn.classList.toggle("hidden", !show);
    collectionBtn.classList.toggle("on", collectionMode);
    collectionBtn.setAttribute("aria-pressed", collectionMode ? "true" : "false");
    collectionBtn.title = collectionMode ? "合集模式已开" : "合集模式";
  }

  function syncTabs() {
    root.querySelectorAll(".home-tab").forEach((btn) => {
      btn.classList.toggle("on", btn.dataset.tab === homeTab);
    });
    syncCollectionBtn();
  }

  function openCollection(col) {
    const prog = loadProgress();
    const hit = col.pages.find((p) => p.id === prog.lastPageId);
    go(`/page/${hit ? hit.id : col.cover.id}`);
  }

  function renderDoujinList(footer) {
    const prog = loadProgress();
    const parts = [];
    if (prog.lastPageId > 0) {
      parts.push(`
        <div class="card continue" data-open="${prog.lastPageId}">
          <div class="label">继续阅读</div>
          <div class="title">${escapeHtml(prog.lastTitle || "上次阅读")}</div>
        </div>`);
    }
    if (collectionMode) {
      const collections = groupPagesByExactTitle(pages);
      collections.forEach((col, i) => {
        const current = col.pages.some((p) => p.id === prog.lastPageId);
        const allRead =
          prog.lastPageNo > 0 && col.pages.every((p) => p.page_no <= prog.lastPageNo);
        const cls = `card page-row${allRead ? " read" : ""}${current ? " current" : ""}`;
        const src = mediaUrl(col.cover.image_url);
        const subParts = [`${col.count} 页`];
        if (current) subParts.push("上次读到这里");
        else if (allRead) subParts.push("已读");
        parts.push(`
          <div class="${cls}" data-collection-i="${i}">
            <img src="${escapeHtml(src)}" alt="" />
            <div>
              <div class="title">${escapeHtml(col.title)}</div>
              <div class="sub">${subParts.map(escapeHtml).join(" · ")}</div>
            </div>
          </div>`);
      });
    } else {
      for (const p of pages) {
        const read = isRead(p);
        const current = p.id === prog.lastPageId;
        const cls = `card page-row${read ? " read" : ""}${current ? " current" : ""}`;
        const src = mediaUrl(p.image_url);
        const sub = current ? "上次读到这里" : read ? "已读" : "";
        parts.push(`
          <div class="${cls}" data-open="${p.id}">
            <img src="${escapeHtml(src)}" alt="" />
            <div>
              <div class="title">${escapeHtml(p.title)}</div>
              ${sub ? `<div class="sub">${sub}</div>` : ""}
            </div>
          </div>`);
      }
    }
    if (footer) parts.push(footer);
    listEl.innerHTML = parts.join("") || `<div class="center">还没有漫画，请先在管理后台上传。</div>`;
    listEl.querySelectorAll("[data-open]").forEach((el) => {
      el.onclick = () => go(`/page/${el.dataset.open}`);
    });
    if (collectionMode) {
      const collections = groupPagesByExactTitle(pages);
      listEl.querySelectorAll("[data-collection-i]").forEach((el) => {
        el.onclick = () => {
          const col = collections[Number(el.dataset.collectionI)];
          if (col) openCollection(col);
        };
      });
    }
  }

  function renderKingList() {
    const prog = loadKingProgress();
    if (!kingVersions.length) {
      listEl.innerHTML = `<div class="center">暂无内容，请先在管理后台创建长寿之王版本。</div>`;
      return;
    }
    const parts = kingVersions.map((v) => {
      const current = prog.lastVersionId > 0 && v.id === prog.lastVersionId;
      const cls = `card page-row${current ? " current" : ""}`;
      const src = mediaUrl(v.cover_url);
      const subParts = [`已上传 ${v.uploaded_count} 页`];
      if (current) subParts.push("上次阅读");
      return `
        <div class="${cls}" data-version="${v.id}">
          <img src="${escapeHtml(src)}" alt="" />
          <div>
            <div class="title">${escapeHtml(v.name)}${v.is_default ? " · 默认" : ""}</div>
            <div class="sub">${subParts.map(escapeHtml).join(" · ")}</div>
          </div>
        </div>`;
    });
    listEl.innerHTML = parts.join("");
    listEl.querySelectorAll("[data-version]").forEach((el) => {
      el.onclick = () => go(`/king/${el.dataset.version}`);
    });
  }

  async function ensureAllPagesLoaded() {
    while (pages.length < total) {
      const res = await api.listPages({
        limit: PAGE_SIZE,
        offset: pages.length,
        order: "page_no",
      });
      const items = res.items || [];
      if (!items.length) break;
      pages = pages.concat(items);
      total = res.total || total;
    }
  }

  async function refreshUnreadAndAnnounce() {
    const [unread, ann] = await Promise.all([
      api.unreadCount().catch(() => ({ count: 0 })),
      api.homeAnnouncement().catch(() => null),
    ]);
    if (ann?.title) setAnnounce(ann.title.trim());
    const n = unread.count || 0;
    if (n > 0) {
      badge.textContent = n > 99 ? "99+" : String(n);
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  async function refreshDoujin() {
    const res = await api.listPages({ limit: PAGE_SIZE, offset: 0, order: "page_no" });
    pages = res.items || [];
    total = res.total || 0;
    if (collectionMode) await ensureAllPagesLoaded();
    const end = pages.length >= total && total > 0;
    renderDoujinList(end ? `<p class="hint" style="text-align:center">没有更多了</p>` : "");
  }

  async function refreshKing() {
    const res = await api.listKingVersions();
    kingVersions = res.items || [];
    renderKingList();
  }

  async function refresh() {
    try {
      await refreshUnreadAndAnnounce();
      if (homeTab === "king") await refreshKing();
      else await refreshDoujin();
    } catch (e) {
      if (!isLoggedIn() || e.status === 401) {
        go("/login");
        return;
      }
      listEl.innerHTML = `<div class="center error">${escapeHtml(e.message || "加载失败")}</div>`;
    }
  }

  async function loadMore() {
    if (homeTab !== "doujin" || collectionMode || loadingMore || pages.length >= total) return;
    loadingMore = true;
    try {
      const res = await api.listPages({ limit: PAGE_SIZE, offset: pages.length, order: "page_no" });
      pages = pages.concat(res.items || []);
      total = res.total || total;
      const end = pages.length >= total && total > 0;
      renderDoujinList(end ? `<p class="hint" style="text-align:center">没有更多了</p>` : "");
    } catch (e) {
      if (!isLoggedIn() || e.status === 401) go("/login");
    } finally {
      loadingMore = false;
    }
  }

  async function setCollectionMode(on) {
    if (homeTab !== "doujin") return;
    collectionMode = on;
    saveCollectionMode(on);
    syncCollectionBtn();
    if (on) {
      try {
        await ensureAllPagesLoaded();
      } catch (e) {
        if (!isLoggedIn() || e.status === 401) {
          go("/login");
          return;
        }
      }
    }
    const end = pages.length >= total && total > 0;
    renderDoujinList(end ? `<p class="hint" style="text-align:center">没有更多了</p>` : "");
  }

  async function setHomeTab(tab) {
    homeTab = tab === "king" ? "king" : "doujin";
    saveHomeTab(homeTab);
    syncTabs();
    listEl.innerHTML = `<div class="center">加载中…</div>`;
    await refresh();
  }

  listEl.addEventListener("scroll", () => {
    if (homeTab !== "doujin" || collectionMode) return;
    if (listEl.scrollTop + listEl.clientHeight >= listEl.scrollHeight - 80) {
      loadMore();
    }
  });

  let pullY = 0;
  listEl.addEventListener(
    "touchstart",
    (e) => {
      if (listEl.scrollTop <= 0) pullY = e.touches[0].clientY;
    },
    { passive: true },
  );
  listEl.addEventListener(
    "touchend",
    (e) => {
      if (listEl.scrollTop > 0 || !pullY) {
        pullY = 0;
        return;
      }
      const dy = e.changedTouches[0].clientY - pullY;
      pullY = 0;
      if (dy > 56) refresh();
    },
    { passive: true },
  );

  root.querySelectorAll(".home-tab").forEach((btn) => {
    btn.onclick = () => setHomeTab(btn.dataset.tab);
  });
  collectionBtn.onclick = () => setCollectionMode(!collectionMode);
  root.querySelector("#msg").onclick = () => go("/notifications");
  root.querySelector("#logout").onclick = () => dlg.classList.remove("hidden");
  root.querySelector("#dlg-no").onclick = () => dlg.classList.add("hidden");
  root.querySelector("#dlg-yes").onclick = () => {
    logout();
    go("/login");
  };

  syncTabs();
  refresh();
}
