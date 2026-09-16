import { api, mediaUrl } from "../api.js";
import { isLoggedIn, effectiveStripMode, loadCommentsLayoutMode, saveCommentsLayoutMode } from "../store.js";
import { go } from "../router.js";
import { escapeHtml, formatMmDd, avatarHtml } from "../util.js";
import { createDoujinSource } from "../reader-source.js";

function sortReplies(replies) {
  return [...(replies || [])].sort((a, b) => {
    if (b.like_count !== a.like_count) return b.like_count - a.like_count;
    return String(b.created_at).localeCompare(String(a.created_at));
  });
}

/** @param {HTMLElement} root @param {number} pageId */
export function renderReaderByPageId(root, pageId) {
  return renderReader(root, createDoujinSource(pageId));
}

/** @param {HTMLElement} root @param {*} source */
export function renderReader(root, source) {
  if (!isLoggedIn()) {
    go("/login");
    return;
  }

  let pages = [];
  let index = 0;
  let chromeOn = false;
  let chromeTimer = 0;
  let commentsOpen = false;
  let layoutMode = loadCommentsLayoutMode();
  let sortTab = 0;
  let comments = [];
  let commentCount = 0;
  let expanded = new Set();
  let expandedBodies = new Set();
  let replyTo = null;
  const PAGE_PREFETCH_REMAINING = 5;
  let totalPages = 0;
  let nextOffset = 0;
  let hasMorePages = false;
  let loadingMorePages = false;
  let versionDescription = "";
  const PREVIEW_BATCH = 8;
  let previewVisibleCount = PREVIEW_BATCH;
  /** @type {Map<number, number>} pageId -> height/width */
  const aspectById = new Map();

  let dragStartX = null;
  let dragStartY = null;
  let dragDx = 0;
  /** @type {null|"h"|"v"} */
  let axisLock = null;
  let scrollStartTop = 0;
  /** @type {HTMLElement|null} */
  let scrollPageEl = null;
  let didSwipe = false;
  let didScroll = false;

  const ZOOM_MIN = 1;
  const ZOOM_MAX = 4;
  const ZOOM_EPS = 1.01;
  let zoom = { scale: 1, tx: 0, ty: 0 };
  /** @type {null|{dist:number,scale:number,tx:number,ty:number,midX:number,midY:number,originX:number,originY:number}} */
  let pinch = null;
  /** @type {null|{x:number,y:number,tx:number,ty:number}} */
  let zoomPan = null;
  let touchGesture = false;

  root.innerHTML = `
    <div class="reader" id="reader">
      <div class="reader-stage" id="stage">
        <div class="reader-track" id="track"></div>
        <div class="chrome top hidden" id="chrome">
          <button class="icon-btn" id="back" type="button">←</button>
          <div class="title" id="rtitle"></div>
          <button class="icon-btn${layoutMode === "docked" ? " on" : ""}" id="layout-toggle" type="button" title="${layoutMode === "docked" ? "沉浸式模式" : "评论区模式"}" aria-pressed="${layoutMode === "docked" ? "true" : "false"}">💬</button>
          ${source.kind === "king" ? `<button class="icon-btn" id="version-info" type="button" title="版本介绍" aria-label="版本介绍">ℹ</button>` : ""}
          <button class="save-btn" id="save" type="button">保存</button>
        </div>
        <div class="king-switch-banner hidden" id="switch-banner"></div>
        <button class="fab hidden" id="fab" type="button">💬<span class="fab-badge hidden" id="cc"></span></button>
      </div>
      <div class="comment-preview hidden" id="comment-preview"></div>
      <button class="entry-bar hidden" id="entry-bar" type="button"><span>写留言...</span><span class="entry-action">留言</span></button>
      <div class="composer-bar hidden" id="composer-bar">
        <div class="hint hidden" id="composer-hint"></div>
        <p class="error hidden" id="composer-err"></p>
        <div class="row">
          <textarea id="composer-draft" maxlength="500" placeholder="写评论"></textarea>
          <button class="btn" type="button" id="composer-send">发送</button>
        </div>
      </div>
      <div class="sheet hidden" id="sheet">
        <div class="sheet-panel" id="sheet-panel">
          <div class="sheet-head">
            <button class="icon-btn" id="sheet-close" type="button">←</button>
            <strong>评论</strong>
          </div>
          <div class="comments-body" id="comments-body">
            <div class="tabs">
              <button type="button" class="on" data-sort="0">最新</button>
              <button type="button" data-sort="1">最热</button>
            </div>
            <p class="error hidden" id="cerr" style="padding:4px 16px"></p>
            <div class="comments" id="comments"></div>
            <div class="composer">
              <div class="hint hidden" id="reply-bar"></div>
              <textarea id="draft" maxlength="500" placeholder="写评论"></textarea>
              <div class="row"><button class="btn" type="button" id="send">发送</button></div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <div class="version-info-overlay hidden" id="version-info-overlay">
      <div class="version-info-panel" role="dialog" aria-labelledby="version-info-title">
        <div class="version-info-head">
          <strong id="version-info-title">版本介绍</strong>
          <button class="icon-btn" id="version-info-close" type="button" aria-label="关闭">×</button>
        </div>
        <div class="version-info-body" id="version-info-body"></div>
      </div>
    </div>
  `;

  const track = root.querySelector("#track");
  const reader = root.querySelector("#reader");
  const chrome = root.querySelector("#chrome");
  const switchBanner = root.querySelector("#switch-banner");
  const layoutToggle = root.querySelector("#layout-toggle");
  const saveBtn = root.querySelector("#save");
  const fab = root.querySelector("#fab");
  const cc = root.querySelector("#cc");
  const sheet = root.querySelector("#sheet");
  const commentPreview = root.querySelector("#comment-preview");
  const commentsEl = root.querySelector("#comments");
  const cerr = root.querySelector("#cerr");
  const draft = root.querySelector("#draft");
  const replyBar = root.querySelector("#reply-bar");
  const composerBar = root.querySelector("#composer-bar");
  const composerHint = root.querySelector("#composer-hint");
  const composerDraft = root.querySelector("#composer-draft");
  const composerErr = root.querySelector("#composer-err");
  const composerSend = root.querySelector("#composer-send");
  const entryBar = root.querySelector("#entry-bar");
  const versionInfoBtn = root.querySelector("#version-info");
  const versionInfoOverlay = root.querySelector("#version-info-overlay");
  const versionInfoTitle = root.querySelector("#version-info-title");
  const versionInfoBody = root.querySelector("#version-info-body");
  const versionInfoClose = root.querySelector("#version-info-close");

  const current = () => pages[index];

  function gesturesBlocked() {
    return layoutMode === "immersive" && commentsOpen;
  }

  function updateLayoutToggleUi() {
    const docked = layoutMode === "docked";
    layoutToggle.classList.toggle("on", docked);
    layoutToggle.setAttribute("aria-pressed", docked ? "true" : "false");
    layoutToggle.title = docked ? "沉浸式模式" : "评论区模式";
  }

  function closeComposer() {
    composerBar.classList.add("hidden");
    entryBar.classList.toggle("hidden", layoutMode !== "docked");
    composerHint.classList.add("hidden");
    composerHint.innerHTML = "";
    composerDraft.value = "";
    composerErr.classList.add("hidden");
    replyTo = null;
  }

  function openComposer(target) {
    replyTo = target || null;
    if (layoutMode === "docked") entryBar.classList.add("hidden");
    composerBar.classList.remove("hidden");
    composerErr.classList.add("hidden");
    if (replyTo) {
      composerHint.classList.remove("hidden");
      composerHint.innerHTML = `回复 ${escapeHtml(replyTo.author_nickname)} <a href="javascript:void(0)" id="composer-cancel">取消</a>`;
      composerHint.querySelector("#composer-cancel").onclick = (e) => {
        e.stopPropagation();
        closeComposer();
      };
      composerDraft.placeholder = "写回复";
    } else {
      composerHint.classList.add("hidden");
      composerHint.innerHTML = "";
      composerDraft.placeholder = "写评论";
    }
    composerDraft.focus();
  }

  function setLayoutMode(mode) {
    layoutMode = mode === "docked" ? "docked" : "immersive";
    saveCommentsLayoutMode(layoutMode);
    reader.classList.toggle("docked", layoutMode === "docked");
    commentPreview.classList.toggle("hidden", layoutMode !== "docked");
    entryBar.classList.toggle("hidden", layoutMode !== "docked");
    updateLayoutToggleUi();
    closeComposer();
    if (layoutMode === "docked") {
      commentsOpen = false;
      sheet.classList.add("hidden");
      refreshComments();
    }
    setChrome(chromeOn);
    setCount(commentCount);
    // 等 flex 高度落地后再按新舞台重算 fit/strip，避免普通页仍按整屏裁切
    requestAnimationFrame(() => {
      paintPages();
      const pageEl = currentPageEl();
      if (pageEl) pageEl.scrollTop = 0;
    });
  }

  function windowIndices() {
    const out = [];
    if (!pages.length) return out;
    const lo = Math.max(0, index - 1);
    const hi = Math.min(pages.length - 1, index + 1);
    for (let i = lo; i <= hi; i++) out.push(i);
    return out;
  }

  function currentPageEl() {
    const p = current();
    if (!p) return null;
    return track.querySelector(`.reader-page[data-page-id="${p.id}"]`);
  }

  /** 评论区舞台更矮：若按宽缩放后高度仍装得下，则用 fit 整页展示，避免被当成条漫裁切。 */
  function pageIsStrip(page) {
    if (!page) return false;
    const aspect = aspectById.get(page.id);
    if (!effectiveStripMode(aspect)) return false;
    if (layoutMode === "docked") {
      const stage = root.querySelector("#stage");
      if (stage && aspect > 0) {
        const scaledH = stage.clientWidth * aspect;
        if (scaledH <= stage.clientHeight * 1.02) return false;
      }
    }
    return true;
  }

  function applyPageClasses() {
    track.querySelectorAll(".reader-page").forEach((el) => {
      const id = Number(el.dataset.pageId);
      const page = pages.find((p) => p.id === id);
      const strip = pageIsStrip(page || { id });
      el.classList.toggle("strip", strip);
      el.classList.toggle("fit", !strip);
      if (!strip) el.scrollTop = 0;
    });
    applyZoomToDom();
  }

  function unloadPageEl(el) {
    if (!el) return;
    const img = el.querySelector("img");
    if (img) {
      img.removeAttribute("src");
      img.src = "";
    }
    el.remove();
  }

  function bindImageAspect(img, pageId) {
    const applyAspect = () => {
      if (!img.naturalWidth) return;
      aspectById.set(pageId, img.naturalHeight / img.naturalWidth);
      applyPageClasses();
    };
    if (img.complete && img.naturalWidth) applyAspect();
    else img.addEventListener("load", applyAspect, { once: true });
  }

  function syncWindow() {
    const idxs = windowIndices();
    const keep = new Set(idxs.map((i) => pages[i].id));

    [...track.querySelectorAll(".reader-page")].forEach((el) => {
      const id = Number(el.dataset.pageId);
      if (!keep.has(id)) unloadPageEl(el);
    });

    idxs.forEach((i) => {
      const p = pages[i];
      let el = track.querySelector(`.reader-page[data-page-id="${p.id}"]`);
      if (!el) {
        el = document.createElement("div");
        el.className = "reader-page fit";
        el.dataset.pageId = String(p.id);
        el.innerHTML = `<div class="zoom-layer"><img alt="" draggable="false" /></div>`;
        const img = el.querySelector("img");
        img.alt = p.title || "";
        img.src = mediaUrl(p.image_url);
        bindImageAspect(img, p.id);
      } else {
        const img = el.querySelector("img");
        const want = mediaUrl(p.image_url);
        if (img && img.getAttribute("src") !== want) {
          img.src = want;
          bindImageAspect(img, p.id);
        }
      }
      track.appendChild(el); // 保证窗口顺序
    });

    applyPageClasses();
  }

  function currentZoomLayer() {
    return currentPageEl()?.querySelector(".zoom-layer") || null;
  }

  function applyZoomToDom() {
    const pageEl = currentPageEl();
    if (!pageEl) return;
    const layer = pageEl.querySelector(".zoom-layer");
    if (!layer) return;
    const zoomed = zoom.scale > ZOOM_EPS;
    pageEl.classList.toggle("is-zoomed", zoomed);
    layer.style.transform = zoomed
      ? `translate(${zoom.tx}px, ${zoom.ty}px) scale(${zoom.scale})`
      : "";
  }

  function resetZoom() {
    zoom = { scale: 1, tx: 0, ty: 0 };
    pinch = null;
    zoomPan = null;
    applyZoomToDom();
  }

  function isZoomed() {
    return zoom.scale > ZOOM_EPS;
  }

  function touchDist(a, b) {
    return Math.hypot(a.clientX - b.clientX, a.clientY - b.clientY);
  }

  function touchMid(a, b) {
    return { x: (a.clientX + b.clientX) / 2, y: (a.clientY + b.clientY) / 2 };
  }

  function layerOrigin() {
    const page = currentPageEl();
    if (!page) return { x: 0, y: 0 };
    const pr = page.getBoundingClientRect();
    return { x: pr.left, y: pr.top };
  }

  function guessExt(url, mime) {
    if (mime && mime.includes("png")) return "png";
    if (mime && mime.includes("webp")) return "webp";
    if (mime && mime.includes("gif")) return "gif";
    const path = String(url || "").split("?")[0].toLowerCase();
    if (path.endsWith(".png")) return "png";
    if (path.endsWith(".webp")) return "webp";
    if (path.endsWith(".gif")) return "gif";
    return "jpg";
  }

  function safeFilename(page, ext) {
    const raw = `p${page.page_no}_${page.title || "comic"}`
      .replace(/[\\/:*?"<>|]/g, "_")
      .trim()
      .slice(0, 80);
    return raw.includes(".") ? raw : `${raw}.${ext}`;
  }

  async function saveCurrentPage() {
    const page = current();
    if (!page || saveBtn.disabled) return;
    const url = mediaUrl(page.image_url);
    saveBtn.disabled = true;
    saveBtn.textContent = "…";
    setChrome(true);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`下载失败（${res.status}）`);
      const blob = await res.blob();
      const ext = guessExt(url, blob.type);
      const name = safeFilename(page, ext);
      const objectUrl = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = objectUrl;
      a.download = name;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(objectUrl), 2000);
    } catch (e) {
      try {
        window.open(url, "_blank", "noopener");
      } catch {
        alert(e.message || "保存失败");
      }
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = "保存";
    }
  }

  function applyTransform(animate) {
    track.classList.toggle("dragging", !animate);
    const indices = windowIndices();
    const local = Math.max(0, indices.indexOf(index));
    const x = -local * 100 + (dragDx / (track.clientWidth || 1)) * 100;
    track.style.transform = `translateX(${x}%)`;
  }

  function paintPages() {
    syncWindow();
    resetZoom();
    applyTransform(false);
  }

  function setChrome(on) {
    chromeOn = on;
    chrome.classList.toggle("hidden", !on || gesturesBlocked());
    const hideFab = layoutMode === "docked" || !on || gesturesBlocked() || !current();
    fab.classList.toggle("hidden", hideFab);
    if (on) {
      const p = current();
      const title = p?.title || "阅读";
      root.querySelector("#rtitle").textContent = p?.subtitle
        ? `${title} · ${p.subtitle}`
        : title;
      clearTimeout(chromeTimer);
      chromeTimer = setTimeout(() => {
        if (!gesturesBlocked()) setChrome(false);
      }, 3000);
    }
  }

  function setCount(n) {
    commentCount = n;
    if (layoutMode === "docked" || n <= 0) {
      cc.classList.add("hidden");
      return;
    }
    cc.textContent = String(n);
    cc.classList.remove("hidden");
  }

  function commentBlock(c, indented) {
    const av = avatarHtml(mediaUrl(c.author_avatar_url), c.author_nickname);
    const reply = c.reply_to_nickname
      ? `<div class="sub">回复 ${escapeHtml(c.reply_to_nickname)}</div>`
      : "";
    const heart = c.liked_by_me ? "♥" : "♡";
    return `
      <div class="comment${indented ? " indent" : ""}">
        ${av}
        <div style="flex:1">
          <div class="nick">${escapeHtml(c.author_nickname)}</div>
          ${reply}
          <div>${escapeHtml(c.content)}</div>
          <div class="meta">
            <span>${escapeHtml(formatMmDd(c.created_at))}</span>
            <span>·</span>
            <span data-reply="${c.id}" style="color:var(--accent);cursor:pointer">回复</span>
            <button class="like${c.liked_by_me ? " on" : ""}" data-like="${c.id}" type="button">${heart} ${c.like_count}</button>
          </div>
        </div>
      </div>`;
  }

  function paintComments() {
    if (!comments.length) {
      commentsEl.innerHTML = `<div class="center">还没有评论，来抢沙发吧。</div>`;
      return;
    }
    const html = [];
    for (const c of comments) {
      html.push(commentBlock(c, false));
      const sorted = sortReplies(c.replies);
      const open = expanded.has(c.id);
      const visible = open ? c.replies : sorted.slice(0, 1);
      for (const r of visible) html.push(commentBlock(r, true));
      if (sorted.length > 1) {
        html.push(
          `<div class="fold" data-fold="${c.id}">${
            open ? "收起" : `展开 ${sorted.length - 1} 条回复`
          }</div>`,
        );
      }
    }
    commentsEl.innerHTML = html.join("");
    commentsEl.querySelectorAll("[data-fold]").forEach((el) => {
      el.onclick = () => {
        const id = Number(el.dataset.fold);
        if (expanded.has(id)) expanded.delete(id);
        else expanded.add(id);
        paintComments();
      };
    });
    commentsEl.querySelectorAll("[data-reply]").forEach((el) => {
      el.onclick = () => {
        const id = Number(el.dataset.reply);
        replyTo = findComment(id);
        updateReplyBar();
      };
    });
    commentsEl.querySelectorAll("[data-like]").forEach((el) => {
      el.onclick = () => toggleLike(Number(el.dataset.like));
    });
  }

  function previewRow(c, indented) {
    const av = avatarHtml(mediaUrl(c.author_avatar_url), c.author_nickname);
    const reply = c.reply_to_nickname
      ? `<div class="preview-reply">回复 ${escapeHtml(c.reply_to_nickname)}</div>`
      : "";
    const heart = c.liked_by_me ? "♥" : "♡";
    const bodyOpen = expandedBodies.has(c.id);
    return `
      <div class="preview-row${indented ? " indent" : ""}" data-open-reply="${c.id}">
        <div class="preview-body">
        ${av}
        <div class="preview-main">
          <div class="preview-head">
            <div class="preview-nick">${escapeHtml(c.author_nickname)}</div>
            <div class="preview-time">${escapeHtml(formatMmDd(c.created_at))}</div>
          </div>
          ${reply}
          <div class="preview-text${bodyOpen ? " open" : ""}">${escapeHtml(c.content)}</div>
        </div>
        <button class="like preview-like${c.liked_by_me ? " on" : ""}" data-like="${c.id}" type="button">${heart} ${c.like_count}</button>
      </div>
      <button class="preview-expand hidden" data-expand-body="${c.id}" type="button">${bodyOpen ? "收起" : "展开全文"}</button>
    </div>`;
  }

  function paintPreviewComments() {
    if (!comments.length) {
      commentPreview.innerHTML = `
        <div class="preview-top">
          <strong>热评</strong>
          <button class="preview-collapse hidden" type="button" disabled>收起评论</button>
        </div>
        <div class="preview-empty">还没有评论</div>`;
      return;
    }
    const html = [];
    html.push(`
      <div class="preview-top">
        <strong>热评</strong>
        <button class="preview-collapse${expanded.size || expandedBodies.size ? "" : " hidden"}" data-collapse-all type="button">收起评论</button>
      </div>
    `);
    const visible = comments.slice(0, previewVisibleCount);
    for (const c of visible) {
      html.push(previewRow(c, false));
      const sorted = sortReplies(c.replies);
      const open = expanded.has(c.id);
      if (open) {
        for (const r of c.replies || []) html.push(previewRow(r, true));
      }
      if (sorted.length) {
        html.push(
          `<div class="preview-fold" data-fold="${c.id}">${
            open ? "收起" : `展开 ${sorted.length} 条回复`
          }</div>`,
        );
      }
    }
    commentPreview.innerHTML = html.join("");
    commentPreview.querySelectorAll("[data-fold]").forEach((el) => {
      el.onclick = (e) => {
        e.stopPropagation();
        const id = Number(el.dataset.fold);
        if (expanded.has(id)) expanded.delete(id);
        else expanded.add(id);
        paintPreviewComments();
      };
    });
    commentPreview.querySelectorAll("[data-open-reply]").forEach((el) => {
      el.onclick = () => {
        const id = Number(el.dataset.openReply);
        openComposer(findComment(id));
      };
    });
    commentPreview.querySelectorAll("[data-expand-body]").forEach((el) => {
      el.onclick = (e) => {
        e.stopPropagation();
        const id = Number(el.dataset.expandBody);
        if (expandedBodies.has(id)) expandedBodies.delete(id);
        else expandedBodies.add(id);
        paintPreviewComments();
      };
    });
    commentPreview.querySelectorAll("[data-like]").forEach((el) => {
      el.onclick = (e) => {
        e.stopPropagation();
        toggleLike(Number(el.dataset.like));
      };
    });
    commentPreview.querySelectorAll("[data-collapse-all]").forEach((el) => {
      el.onclick = (e) => {
        e.stopPropagation();
        expanded = new Set();
        expandedBodies = new Set();
        paintPreviewComments();
      };
    });
    requestAnimationFrame(() => {
      commentPreview.querySelectorAll(".preview-row").forEach((row) => {
        const text = row.querySelector(".preview-text");
        const btn = row.querySelector("[data-expand-body]");
        if (!text || !btn) return;
        if (text.classList.contains("open") || text.scrollHeight > text.clientHeight + 1) {
          btn.classList.remove("hidden");
        }
      });
      if (layoutMode !== "docked") return;
      if (previewVisibleCount >= comments.length) return;
      if (commentPreview.clientHeight === 0) return;
      if (commentPreview.scrollHeight <= commentPreview.clientHeight + 8) {
        previewVisibleCount = Math.min(comments.length, previewVisibleCount + PREVIEW_BATCH);
        paintPreviewComments();
      }
    });
  }

  function paintCommentViews() {
    if (layoutMode === "docked") paintPreviewComments();
    else paintComments();
  }

  function findComment(id) {
    for (const c of comments) {
      if (c.id === id) return c;
      const r = (c.replies || []).find((x) => x.id === id);
      if (r) return r;
    }
    return null;
  }

  function patchLike(id, liked, count) {
    const mapOne = (c) => {
      let self = c.id === id ? { ...c, liked_by_me: liked, like_count: count } : c;
      self = {
        ...self,
        replies: (self.replies || []).map((r) =>
          r.id === id ? { ...r, liked_by_me: liked, like_count: count } : r,
        ),
      };
      return self;
    };
    comments = comments.map(mapOne);
    paintCommentViews();
  }

  async function toggleLike(id) {
    const c = findComment(id);
    if (!c) return;
    try {
      if (c.liked_by_me) {
        await api.unlikeComment(id);
        patchLike(id, false, Math.max(0, c.like_count - 1));
      } else {
        const state = await api.likeComment(id);
        patchLike(id, state.liked, state.like_count);
      }
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
      else {
        const errEl = layoutMode === "docked" ? composerErr : cerr;
        errEl.textContent = e.message || "点赞失败";
        errEl.classList.remove("hidden");
      }
    }
  }

  function updateReplyBar() {
    if (!replyTo) {
      replyBar.classList.add("hidden");
      replyBar.innerHTML = "";
      return;
    }
    replyBar.classList.remove("hidden");
    replyBar.innerHTML = `回复 ${escapeHtml(replyTo.author_nickname)} <a href="javascript:void(0)" id="cancel-reply">取消</a>`;
    replyBar.querySelector("#cancel-reply").onclick = () => {
      replyTo = null;
      updateReplyBar();
    };
  }

  async function loadCatalogUntilContains(_targetPageId) {
    const boot = await source.bootstrap();
    pages = boot.pages || [];
    totalPages = Number(boot.total || pages.length);
    nextOffset = Number(boot.nextOffset || pages.length);
    hasMorePages = Boolean(boot.hasMore);
    loadingMorePages = false;
    if (boot.switchMessage) {
      switchBanner.textContent = boot.switchMessage;
      switchBanner.classList.remove("hidden");
      window.setTimeout(() => switchBanner.classList.add("hidden"), 3200);
    }
    versionDescription = boot.versionDescription || "";
    return boot.initialId;
  }

  async function loadMorePagesIfNeeded() {
    if (loadingMorePages || !hasMorePages) return;
    const remain = pages.length - 1 - index;
    if (remain > PAGE_PREFETCH_REMAINING) return;
    loadingMorePages = true;
    try {
      const chunk = await source.loadMore(pages, nextOffset);
      pages = chunk.pages || pages;
      totalPages = Number(chunk.total || totalPages);
      nextOffset = Number(chunk.nextOffset || nextOffset);
      hasMorePages = Boolean(chunk.hasMore);
      syncWindow();
      applyTransform(false);
    } finally {
      loadingMorePages = false;
    }
  }

  async function refreshComments() {
    const p = current();
    if (!p) return;
    const sort = layoutMode === "docked" || sortTab === 1 ? "hot" : "latest";
    try {
      const res = await source.listComments(p.id, sort);
      comments = res.items || [];
      previewVisibleCount = PREVIEW_BATCH;
      setCount(comments.length);
      paintCommentViews();
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
      else {
        const errEl = layoutMode === "docked" ? composerErr : cerr;
        errEl.textContent = e.message || "评论加载失败";
        errEl.classList.remove("hidden");
      }
    }
  }

  async function onSettled() {
    const p = current();
    if (!p) return;
    source.markRead(p);
    setChrome(false);
    closeComposer();
    void loadMorePagesIfNeeded();
    if (layoutMode === "docked") {
      await refreshComments();
      return;
    }
    try {
      const res = await source.listComments(p.id, "latest");
      setCount((res.items || []).length);
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
    }
  }

  let pageTurning = false;
  const TURN_MS = 280;

  function settleIndex(next) {
    index = Math.max(0, Math.min(pages.length - 1, next));
    dragDx = 0;
    resetZoom();
    syncWindow();
    applyTransform(false);
    pageTurning = false;
    onSettled();
  }

  /** 先滑到邻页再 syncWindow，避免瞬切；非邻页则直接换窗。 */
  function animateToIndex(target) {
    if (!pages.length || pageTurning) return;
    const next = Math.max(0, Math.min(pages.length - 1, target));
    if (next === index) {
      dragDx = 0;
      applyTransform(true);
      return;
    }

    const indices = windowIndices();
    const local = indices.indexOf(index);
    const targetLocal = indices.indexOf(next);
    const w = track.clientWidth || 1;
    const adjacent = Math.abs(next - index) === 1 && targetLocal >= 0 && local >= 0;

    if (!adjacent) {
      settleIndex(next);
      return;
    }

    pageTurning = true;
    didSwipe = true;
    dragStartX = null;
    dragStartY = null;
    axisLock = null;
    scrollPageEl = null;
    scrollStartTop = 0;

    let fallbackTimer = 0;
    let finished = false;
    const finish = () => {
      if (finished) return;
      finished = true;
      track.removeEventListener("transitionend", onEnd);
      clearTimeout(fallbackTimer);
      settleIndex(next);
    };
    const onEnd = (e) => {
      if (e.target !== track) return;
      if (e.propertyName && e.propertyName !== "transform") return;
      finish();
    };

    // 先固定当前 peek 帧，再在下一帧用 transition 滑满一屏
    applyTransform(false);
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        if (finished) return;
        dragDx = (local - targetLocal) * w;
        track.addEventListener("transitionend", onEnd);
        fallbackTimer = setTimeout(finish, TURN_MS + 100);
        applyTransform(true);
      });
    });
  }

  function goIndex(i) {
    animateToIndex(i);
  }

  root.querySelector("#back").onclick = () => go("/home");
  layoutToggle.onclick = (e) => {
    e.stopPropagation();
    setLayoutMode(layoutMode === "docked" ? "immersive" : "docked");
  };
  saveBtn.onclick = (e) => {
    e.stopPropagation();
    saveCurrentPage();
  };
  function openVersionInfo() {
    if (!versionInfoOverlay) return;
    const p = current();
    versionInfoTitle.textContent = p?.subtitle || "版本介绍";
    versionInfoBody.textContent = versionDescription.trim() || "暂无介绍";
    versionInfoOverlay.classList.remove("hidden");
  }
  function closeVersionInfo() {
    versionInfoOverlay?.classList.add("hidden");
  }
  if (versionInfoBtn) {
    versionInfoBtn.onclick = (e) => {
      e.stopPropagation();
      openVersionInfo();
    };
  }
  versionInfoClose.onclick = (e) => {
    e.stopPropagation();
    closeVersionInfo();
  };
  versionInfoOverlay.onclick = (e) => {
    if (e.target === versionInfoOverlay) closeVersionInfo();
  };
  root.querySelector("#fab").onclick = () => {
    if (layoutMode === "docked") {
      openComposer(null);
      return;
    }
    commentsOpen = true;
    setChrome(false);
    sheet.classList.remove("hidden");
    refreshComments();
  };
  entryBar.onclick = (e) => {
    e.stopPropagation();
    openComposer(null);
  };
  root.querySelector("#sheet-close").onclick = () => {
    commentsOpen = false;
    sheet.classList.add("hidden");
    replyTo = null;
    updateReplyBar();
  };
  sheet.onclick = (e) => {
    if (e.target === sheet) {
      commentsOpen = false;
      sheet.classList.add("hidden");
    }
  };
  root.querySelectorAll(".tabs button").forEach((btn) => {
    btn.onclick = () => {
      sortTab = Number(btn.dataset.sort);
      root.querySelectorAll(".tabs button").forEach((b) => b.classList.toggle("on", b === btn));
      refreshComments();
    };
  });
  root.querySelector("#send").onclick = async () => {
    const text = draft.value.trim();
    const p = current();
    if (!text || !p) return;
    const btn = root.querySelector("#send");
    btn.disabled = true;
    cerr.classList.add("hidden");
    try {
      await source.createComment(p.id, text, replyTo?.id ?? null);
      draft.value = "";
      replyTo = null;
      updateReplyBar();
      await refreshComments();
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
      else {
        cerr.textContent = e.message || "发送失败";
        cerr.classList.remove("hidden");
      }
    } finally {
      btn.disabled = false;
    }
  };

  composerSend.onclick = async (e) => {
    e.stopPropagation();
    const text = composerDraft.value.trim();
    const p = current();
    if (!text || !p) return;
    composerSend.disabled = true;
    composerErr.classList.add("hidden");
    try {
      await source.createComment(p.id, text, replyTo?.id ?? null);
      closeComposer();
      await refreshComments();
    } catch (err) {
      if (err.status === 401 || !isLoggedIn()) go("/login");
      else {
        composerErr.textContent = err.message || "发送失败";
        composerErr.classList.remove("hidden");
      }
    } finally {
      composerSend.disabled = false;
    }
  };

  commentPreview.addEventListener("scroll", () => {
    if (previewVisibleCount >= comments.length) return;
    if (
      commentPreview.scrollTop + commentPreview.clientHeight >=
      commentPreview.scrollHeight - 24
    ) {
      previewVisibleCount = Math.min(comments.length, previewVisibleCount + PREVIEW_BATCH);
      paintPreviewComments();
    }
  });

  const AXIS_THRESHOLD = 10;

  function resetDrag() {
    dragStartX = null;
    dragStartY = null;
    dragDx = 0;
    axisLock = null;
    scrollPageEl = null;
    scrollStartTop = 0;
  }

  function finishSwipe() {
    if (pageTurning) return;
    if (dragStartX == null || gesturesBlocked() || isZoomed() || touchGesture) {
      const shouldSnap = dragStartX != null && !gesturesBlocked();
      resetDrag();
      if (shouldSnap) applyTransform(true);
      return;
    }
    const w = track.clientWidth || 1;
    // 条漫略降阈值，横滑更容易翻页
    const ratio = pageIsStrip(current()) ? 0.08 : 0.12;
    const threshold = Math.max(40, w * ratio);
    const canTurn = Math.abs(dragDx) >= threshold;
    if (axisLock === "v" && !canTurn) {
      resetDrag();
      applyTransform(true);
      return;
    }
    if (canTurn) didSwipe = true;
    if (dragDx <= -threshold) {
      const fromDx = dragDx;
      resetDrag();
      dragDx = fromDx; // 保留 peek，交给 animateToIndex 续滑
      animateToIndex(index + 1);
      return;
    }
    if (dragDx >= threshold) {
      const fromDx = dragDx;
      resetDrag();
      dragDx = fromDx;
      animateToIndex(index - 1);
      return;
    }
    dragDx = 0;
    applyTransform(true);
    resetDrag();
  }

  function stillHere() {
    return document.body.contains(reader);
  }

  function beginPinch(t0, t1) {
    const mid = touchMid(t0, t1);
    const origin = layerOrigin();
    pinch = {
      dist: Math.max(1, touchDist(t0, t1)),
      scale: zoom.scale,
      tx: zoom.tx,
      ty: zoom.ty,
      midX: mid.x,
      midY: mid.y,
      originX: origin.x,
      originY: origin.y,
    };
    zoomPan = null;
    resetDrag();
    touchGesture = true;
    didScroll = true;
  }

  function updatePinch(t0, t1) {
    if (!pinch) return;
    const mid = touchMid(t0, t1);
    const dist = Math.max(1, touchDist(t0, t1));
    let nextScale = (pinch.scale * dist) / pinch.dist;
    nextScale = Math.min(ZOOM_MAX, Math.max(ZOOM_MIN, nextScale));
    const ox = pinch.originX;
    const oy = pinch.originY;
    const focalX = pinch.midX - ox;
    const focalY = pinch.midY - oy;
    const ratio = nextScale / pinch.scale;
    let tx = focalX - (focalX - pinch.tx) * ratio;
    let ty = focalY - (focalY - pinch.ty) * ratio;
    tx += mid.x - pinch.midX;
    ty += mid.y - pinch.midY;
    if (nextScale <= ZOOM_EPS) {
      zoom = { scale: 1, tx: 0, ty: 0 };
    } else {
      zoom = { scale: nextScale, tx, ty };
    }
    applyZoomToDom();
  }

  reader.addEventListener("click", (e) => {
    if (gesturesBlocked() || didSwipe || didScroll) {
      didSwipe = false;
      didScroll = false;
      return;
    }
    if (
      e.target.closest(".chrome") ||
      e.target.closest(".fab") ||
      e.target.closest(".sheet") ||
      e.target.closest(".comment-preview") ||
      e.target.closest(".composer-bar")
    ) return;
    setChrome(!chromeOn);
  });

  reader.addEventListener("dragstart", (e) => e.preventDefault());

  reader.addEventListener(
    "touchstart",
    (e) => {
      if (gesturesBlocked() || pageTurning) return;
      if (
        e.target.closest(".chrome") ||
        e.target.closest(".fab") ||
        e.target.closest(".sheet") ||
        e.target.closest(".comment-preview") ||
        e.target.closest(".composer-bar")
      ) return;
      if (e.touches.length >= 2) {
        e.preventDefault();
        beginPinch(e.touches[0], e.touches[1]);
        return;
      }
      if (e.touches.length === 1 && isZoomed()) {
        e.preventDefault();
        const t = e.touches[0];
        zoomPan = { x: t.clientX, y: t.clientY, tx: zoom.tx, ty: zoom.ty };
        pinch = null;
        resetDrag();
        touchGesture = true;
        didScroll = true;
      }
    },
    { passive: false },
  );

  reader.addEventListener(
    "touchmove",
    (e) => {
      if (gesturesBlocked()) return;
      if (e.touches.length >= 2) {
        e.preventDefault();
        if (!pinch) beginPinch(e.touches[0], e.touches[1]);
        else updatePinch(e.touches[0], e.touches[1]);
        return;
      }
      if (zoomPan && e.touches.length === 1 && isZoomed()) {
        e.preventDefault();
        const t = e.touches[0];
        zoom = {
          scale: zoom.scale,
          tx: zoomPan.tx + (t.clientX - zoomPan.x),
          ty: zoomPan.ty + (t.clientY - zoomPan.y),
        };
        applyZoomToDom();
        return;
      }
      // 单指阅读手势：阻止浏览器默认滚动，避免 pointercancel 打断翻页
      if (dragStartX != null && e.touches.length === 1) {
        e.preventDefault();
      }
    },
    { passive: false },
  );

  function endTouchZoom(e) {
    if (e.touches.length >= 2) {
      beginPinch(e.touches[0], e.touches[1]);
      return;
    }
    if (e.touches.length === 1 && isZoomed()) {
      const t = e.touches[0];
      zoomPan = { x: t.clientX, y: t.clientY, tx: zoom.tx, ty: zoom.ty };
      pinch = null;
      return;
    }
    pinch = null;
    zoomPan = null;
    if (zoom.scale <= ZOOM_EPS) resetZoom();
    setTimeout(() => {
      touchGesture = false;
    }, 0);
  }

  reader.addEventListener("touchend", endTouchZoom, { passive: true });
  reader.addEventListener("touchcancel", endTouchZoom, { passive: true });

  reader.addEventListener("pointerdown", (e) => {
    if (gesturesBlocked() || isZoomed() || pinch || touchGesture || pageTurning) return;
    if (e.pointerType === "mouse" && e.button !== 0) return;
    if (
      e.target.closest(".chrome") ||
      e.target.closest(".fab") ||
      e.target.closest(".sheet") ||
      e.target.closest(".comment-preview") ||
      e.target.closest(".composer-bar")
    ) return;
    dragStartX = e.clientX;
    dragStartY = e.clientY;
    dragDx = 0;
    axisLock = null;
    didSwipe = false;
    didScroll = false;
    scrollPageEl = currentPageEl();
    scrollStartTop = scrollPageEl ? scrollPageEl.scrollTop : 0;
    try {
      reader.setPointerCapture(e.pointerId);
    } catch {
      /* ignore */
    }
  });

  reader.addEventListener("pointermove", (e) => {
    if (dragStartX == null || gesturesBlocked() || isZoomed() || pinch || touchGesture || pageTurning) return;
    const dx = e.clientX - dragStartX;
    const dy = e.clientY - dragStartY;

    if (!axisLock) {
      if (Math.abs(dx) < AXIS_THRESHOLD && Math.abs(dy) < AXIS_THRESHOLD) return;
      // 条漫：纵滑需明显大于横滑才锁 v（1.5 倍），避免轻微抖动抢走翻页
      const preferV =
        pageIsStrip(current()) && Math.abs(dy) > Math.abs(dx) * 1.5;
      axisLock = preferV ? "v" : "h";
    }

    // 纵滚时仍跟踪 dx，便于松手时按阈值翻页（方案 2）
    dragDx = dx;

    if (axisLock === "v") {
      if (scrollPageEl) {
        scrollPageEl.scrollTop = scrollStartTop - dy;
      }
      if (Math.abs(dy) >= AXIS_THRESHOLD) didScroll = true;
      // 不拖 track，避免纵滚时整页跟着横移
      return;
    }

    applyTransform(false);
  });

  reader.addEventListener("pointerup", finishSwipe);
  reader.addEventListener("pointercancel", finishSwipe);

  window.addEventListener("keydown", (e) => {
    if (!stillHere() || gesturesBlocked() || pageTurning) return;
    if (isZoomed()) return;
    if (e.key === "ArrowLeft") {
      goIndex(index - 1);
      return;
    }
    if (e.key === "ArrowRight") {
      goIndex(index + 1);
      return;
    }
    if (e.key === "ArrowUp" || e.key === "ArrowDown") {
      if (pageIsStrip(current())) {
        const el = currentPageEl();
        if (el) {
          e.preventDefault();
          el.scrollTop += e.key === "ArrowDown" ? 120 : -120;
        }
      } else if (e.key === "ArrowDown") {
        goIndex(index + 1);
      } else {
        goIndex(index - 1);
      }
    }
  });

  setLayoutMode(layoutMode);

  (async () => {
    try {
      const initialId = await loadCatalogUntilContains();
      if (!pages.length) {
        root.innerHTML = `<div class="center">${
          source.kind === "king" ? "该版本还没有已上传的页" : "还没有漫画"
        }</div>`;
        return;
      }
      const idx = pages.findIndex((p) => p.id === initialId);
      index = Math.max(0, idx);
      paintPages();
      onSettled();
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) go("/login");
      else root.innerHTML = `<div class="center error">${escapeHtml(e.message || "加载失败")}</div>`;
    }
  })();
}
