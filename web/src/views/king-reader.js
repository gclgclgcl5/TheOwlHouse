import { api, mediaUrl } from "../api.js";
import {
  isLoggedIn,
  markKingRead,
  loadKingProgress,
  loadCommentsLayoutMode,
  saveCommentsLayoutMode,
  effectiveStripMode,
} from "../store.js";
import { go } from "../router.js";
import { escapeHtml, formatMmDd, avatarHtml } from "../util.js";

function sortReplies(replies) {
  return [...(replies || [])].sort((a, b) => {
    if (b.like_count !== a.like_count) return b.like_count - a.like_count;
    return String(b.created_at).localeCompare(String(a.created_at));
  });
}

/**
 * @param {HTMLElement} root
 * @param {number} preferredVersionId
 * @param {number} deepSlotId 0 = use work progress
 */
export function renderKingReader(root, preferredVersionId, deepSlotId = 0) {
  if (!isLoggedIn()) {
    go("/login");
    return;
  }

  let versionId = preferredVersionId;
  let versionName = "";
  /** @type {{slot_id:number,page_no:number,title:string,image_url:string,comment_count:number}[]} */
  let pages = [];
  let index = 0;
  let chromeOn = false;
  let chromeTimer = 0;
  let commentsOpen = false;
  let layoutMode = loadCommentsLayoutMode();
  let sortTab = 0;
  let comments = [];
  let expanded = new Set();
  let replyTo = null;
  /** @type {Map<number, number>} */
  const aspectById = new Map();
  let dragStartX = null;
  let dragDx = 0;
  let didSwipe = false;
  let switchHint = "";

  root.innerHTML = `
    <div class="reader" id="reader">
      <div class="reader-stage" id="stage">
        <div class="reader-track" id="track"></div>
        <div class="chrome top hidden" id="chrome">
          <button class="icon-btn" id="back" type="button">←</button>
          <div class="title" id="rtitle"></div>
          <button class="icon-btn${layoutMode === "docked" ? " on" : ""}" id="layout-toggle" type="button" title="评论布局">💬</button>
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
        <div class="sheet-panel">
          <div class="sheet-head">
            <button class="icon-btn" id="sheet-close" type="button">←</button>
            <strong>评论</strong>
          </div>
          <div class="comments-body">
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
  `;

  const track = root.querySelector("#track");
  const chrome = root.querySelector("#chrome");
  const layoutToggle = root.querySelector("#layout-toggle");
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
  const entryBar = root.querySelector("#entry-bar");
  const switchBanner = root.querySelector("#switch-banner");
  const rtitle = root.querySelector("#rtitle");

  const current = () => pages[index];

  function showChromeBriefly() {
    chromeOn = true;
    chrome.classList.remove("hidden");
    clearTimeout(chromeTimer);
    chromeTimer = window.setTimeout(() => {
      chromeOn = false;
      chrome.classList.add("hidden");
    }, 2800);
  }

  function updateLayoutUi() {
    const docked = layoutMode === "docked";
    layoutToggle.classList.toggle("on", docked);
    layoutToggle.title = docked ? "沉浸式模式" : "评论区模式";
    fab.classList.toggle("hidden", docked || !pages.length);
    entryBar.classList.toggle("hidden", !docked || !pages.length);
    commentPreview.classList.toggle("hidden", !docked || !pages.length);
    if (docked) sheet.classList.add("hidden");
  }

  function paintTrack(instant) {
    const stage = root.querySelector("#stage");
    const w = stage?.clientWidth || 1;
    track.style.transition = instant ? "none" : "transform 0.28s ease";
    track.style.transform = `translateX(${-index * w}px)`;
    const p = current();
    if (!p) return;
    rtitle.textContent = `${p.title} · ${versionName}`;
    const strip = effectiveStripMode(aspectById.get(p.slot_id) || 1);
    root.querySelectorAll(".reader-page").forEach((el, i) => {
      el.classList.toggle("strip", i === index && strip);
      el.classList.toggle("fit", !(i === index && strip));
    });
  }

  function rebuildTrack() {
    const stage = root.querySelector("#stage");
    const w = stage?.clientWidth || window.innerWidth;
    track.innerHTML = pages
      .map((p) => {
        const src = mediaUrl(p.image_url);
        return `<div class="reader-page fit" data-slot="${p.slot_id}" style="flex:0 0 ${w}px;width:${w}px;min-width:${w}px"><div class="zoom-layer"><img src="${escapeHtml(src)}" alt="" draggable="false" /></div></div>`;
      })
      .join("");
    track.querySelectorAll("img").forEach((img) => {
      const pageEl = img.closest(".reader-page");
      const slotId = Number(pageEl?.dataset.slot);
      const apply = () => {
        if (img.naturalWidth > 0) {
          aspectById.set(slotId, img.naturalHeight / img.naturalWidth);
          paintTrack(true);
        }
      };
      if (img.complete) apply();
      else img.onload = apply;
    });
  }

  function onSettled() {
    const p = current();
    if (!p) return;
    markKingRead({
      slotId: p.slot_id,
      page_no: p.page_no,
      title: p.title,
      versionId,
    });
    refreshComments();
  }

  function goIndex(next, instant) {
    if (!pages.length) return;
    index = Math.max(0, Math.min(pages.length - 1, next));
    paintTrack(instant);
    onSettled();
    showChromeBriefly();
  }

  function findComment(id) {
    for (const c of comments) {
      if (c.id === id) return c;
      const r = (c.replies || []).find((x) => x.id === id);
      if (r) return r;
    }
    return null;
  }

  function updateReplyBar() {
    if (!replyTo) {
      replyBar.classList.add("hidden");
      replyBar.innerHTML = "";
      composerHint.classList.add("hidden");
      return;
    }
    const html = `回复 ${escapeHtml(replyTo.author_nickname)} <button type="button" id="cancel-reply">取消</button>`;
    replyBar.innerHTML = html;
    replyBar.classList.remove("hidden");
    composerHint.innerHTML = html;
    composerHint.classList.remove("hidden");
    replyBar.querySelector("#cancel-reply")?.addEventListener("click", () => {
      replyTo = null;
      updateReplyBar();
    });
    composerHint.querySelector("#cancel-reply")?.addEventListener("click", () => {
      replyTo = null;
      updateReplyBar();
    });
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
      commentPreview.innerHTML = `<div class="preview-empty">还没有评论</div>`;
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
    commentPreview.innerHTML = `
      <div class="preview-top"><strong>热评</strong></div>
      ${comments
        .slice(0, 6)
        .map((c) => commentBlock(c, false))
        .join("")}`;
    const bind = (el) => {
      el.querySelectorAll("[data-fold]").forEach((node) => {
        node.onclick = () => {
          const id = Number(node.dataset.fold);
          if (expanded.has(id)) expanded.delete(id);
          else expanded.add(id);
          paintComments();
        };
      });
      el.querySelectorAll("[data-reply]").forEach((node) => {
        node.onclick = () => {
          replyTo = findComment(Number(node.dataset.reply));
          updateReplyBar();
          if (layoutMode === "docked") {
            composerBar.classList.remove("hidden");
            entryBar.classList.add("hidden");
          }
        };
      });
      el.querySelectorAll("[data-like]").forEach((node) => {
        node.onclick = () => toggleLike(Number(node.dataset.like));
      });
    };
    bind(commentsEl);
    bind(commentPreview);
  }

  async function refreshComments() {
    const p = current();
    if (!p) return;
    try {
      const res = await api.listKingComments(p.slot_id, sortTab === 0 ? "latest" : "hot");
      comments = res.items || [];
      const n = comments.length;
      if (n > 0 && layoutMode !== "docked") {
        cc.textContent = String(n);
        cc.classList.remove("hidden");
      } else {
        cc.classList.add("hidden");
      }
      paintComments();
    } catch (e) {
      cerr.textContent = e.message || "评论加载失败";
      cerr.classList.remove("hidden");
    }
  }

  async function toggleLike(id) {
    const c = findComment(id);
    if (!c) return;
    try {
      if (c.liked_by_me) {
        await api.unlikeComment(id);
        c.liked_by_me = false;
        c.like_count = Math.max(0, (c.like_count || 1) - 1);
      } else {
        const res = await api.likeComment(id);
        c.liked_by_me = true;
        c.like_count = res.like_count ?? c.like_count + 1;
      }
      paintComments();
    } catch {
      /* ignore */
    }
  }

  async function sendComment(text, fromComposer) {
    const p = current();
    if (!p || !text.trim()) return;
    try {
      await api.createKingComment(p.slot_id, text.trim(), replyTo?.id || null);
      replyTo = null;
      updateReplyBar();
      if (fromComposer) {
        composerDraft.value = "";
        composerBar.classList.add("hidden");
        entryBar.classList.toggle("hidden", layoutMode !== "docked");
      } else {
        draft.value = "";
      }
      await refreshComments();
    } catch (e) {
      const msg = e.message || "发送失败";
      if (fromComposer) {
        composerErr.textContent = msg;
        composerErr.classList.remove("hidden");
      } else {
        cerr.textContent = msg;
        cerr.classList.remove("hidden");
      }
    }
  }

  async function bootstrap() {
    track.innerHTML = `<div class="center" style="padding:40px">加载中…</div>`;
    try {
      const prog = loadKingProgress();
      let resolved;
      if (deepSlotId > 0) {
        resolved = await api.resolveKingPage({
          slot_id: deepSlotId,
          preferred_version_id: preferredVersionId,
        });
      } else {
        const pageNo = prog.lastPageNo > 0 ? prog.lastPageNo : 1;
        resolved = await api.resolveKingPage({
          page_no: pageNo,
          preferred_version_id: preferredVersionId,
        });
      }
      versionId = resolved.version_id;
      versionName = resolved.version_name;
      if (resolved.switched) {
        switchHint = `已切换到「${resolved.version_name}」`;
        switchBanner.textContent = switchHint;
        switchBanner.classList.remove("hidden");
        window.setTimeout(() => switchBanner.classList.add("hidden"), 3200);
      }
      markKingRead({
        slotId: resolved.slot_id,
        page_no: resolved.page_no,
        title: resolved.title,
        versionId,
      });
      const list = await api.listKingVersionPages(versionId);
      pages = list.items || [];
      if (!pages.length) {
        track.innerHTML = `<div class="center" style="padding:40px">该版本还没有已上传的页</div>`;
        return;
      }
      index = Math.max(
        0,
        pages.findIndex((p) => p.slot_id === resolved.slot_id),
      );
      if (index < 0) index = 0;
      rebuildTrack();
      paintTrack(true);
      updateLayoutUi();
      onSettled();
      showChromeBriefly();
      if (location.hash !== `#/king/${versionId}/slot/${pages[index].slot_id}`) {
        history.replaceState(null, "", `#/king/${versionId}/slot/${pages[index].slot_id}`);
      }
    } catch (e) {
      if (e.status === 401 || !isLoggedIn()) {
        go("/login");
        return;
      }
      track.innerHTML = `<div class="center error" style="padding:40px">${escapeHtml(e.message || "加载失败")}</div>`;
    }
  }

  root.querySelector("#back").onclick = () => go("/home");
  layoutToggle.onclick = () => {
    layoutMode = layoutMode === "docked" ? "immersive" : "docked";
    saveCommentsLayoutMode(layoutMode);
    commentsOpen = false;
    sheet.classList.add("hidden");
    updateLayoutUi();
    paintComments();
  };
  fab.onclick = () => {
    commentsOpen = true;
    sheet.classList.remove("hidden");
    refreshComments();
  };
  root.querySelector("#sheet-close").onclick = () => {
    commentsOpen = false;
    sheet.classList.add("hidden");
  };
  entryBar.onclick = () => {
    composerBar.classList.remove("hidden");
    entryBar.classList.add("hidden");
  };
  root.querySelector("#composer-send").onclick = () => sendComment(composerDraft.value, true);
  root.querySelector("#send").onclick = () => sendComment(draft.value, false);
  root.querySelectorAll("[data-sort]").forEach((btn) => {
    btn.onclick = () => {
      sortTab = Number(btn.dataset.sort);
      root.querySelectorAll("[data-sort]").forEach((b) => b.classList.toggle("on", Number(b.dataset.sort) === sortTab));
      refreshComments();
    };
  });

  const stage = root.querySelector("#stage");
  stage.addEventListener("click", () => {
    if (didSwipe) {
      didSwipe = false;
      return;
    }
    if (chromeOn) {
      chromeOn = false;
      chrome.classList.add("hidden");
    } else showChromeBriefly();
  });

  stage.addEventListener(
    "touchstart",
    (e) => {
      if (e.touches.length !== 1) return;
      dragStartX = e.touches[0].clientX;
      dragDx = 0;
    },
    { passive: true },
  );
  stage.addEventListener(
    "touchmove",
    (e) => {
      if (dragStartX == null || e.touches.length !== 1) return;
      dragDx = e.touches[0].clientX - dragStartX;
    },
    { passive: true },
  );
  stage.addEventListener(
    "touchend",
    () => {
      if (dragStartX == null) return;
      if (Math.abs(dragDx) > 48) {
        didSwipe = true;
        goIndex(index + (dragDx < 0 ? 1 : -1), false);
      }
      dragStartX = null;
      dragDx = 0;
    },
    { passive: true },
  );

  window.addEventListener("keydown", onKey);
  function onKey(e) {
    if (e.key === "ArrowLeft") goIndex(index - 1, false);
    if (e.key === "ArrowRight") goIndex(index + 1, false);
  }

  const prevCleanup = root._kingCleanup;
  if (typeof prevCleanup === "function") prevCleanup();
  root._kingCleanup = () => window.removeEventListener("keydown", onKey);

  bootstrap();
}
