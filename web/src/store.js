const TOKEN_KEY = "owlhouse_access_token";
const PROG_KEY = "owlhouse_reading";

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

export function isLoggedIn() {
  return !!getToken();
}

export function logout() {
  setToken("");
}

export function loadProgress() {
  try {
    const raw = localStorage.getItem(PROG_KEY);
    if (!raw) return { lastPageId: 0, lastPageNo: 0, lastTitle: "" };
    const o = JSON.parse(raw);
    return {
      lastPageId: Number(o.lastPageId) || 0,
      lastPageNo: Number(o.lastPageNo) || 0,
      lastTitle: String(o.lastTitle || ""),
    };
  } catch {
    return { lastPageId: 0, lastPageNo: 0, lastTitle: "" };
  }
}

export function markRead(page) {
  const cur = loadProgress();
  const next = {
    lastPageId: page.id,
    lastTitle: page.title || "",
    lastPageNo: page.page_no >= cur.lastPageNo ? page.page_no : cur.lastPageNo,
  };
  localStorage.setItem(PROG_KEY, JSON.stringify(next));
  return next;
}

export function isRead(page) {
  const { lastPageNo } = loadProgress();
  return lastPageNo > 0 && page.page_no <= lastPageNo;
}

const COLL_KEY = "owlhouse_collection_mode";

/** 合集模式（默认开）。 */
export function loadCollectionMode() {
  const raw = localStorage.getItem(COLL_KEY);
  if (raw === null) return true;
  return raw === "1" || raw === "true";
}

export function saveCollectionMode(on) {
  localStorage.setItem(COLL_KEY, on ? "1" : "0");
}

const COMMENTS_LAYOUT_KEY = "owlhouse_comments_layout";

/** 阅读布局：docked（评论区常驻底部，默认开）| immersive。 */
export function loadCommentsLayoutMode() {
  const raw = localStorage.getItem(COMMENTS_LAYOUT_KEY);
  if (raw === null) return "docked";
  return raw === "immersive" ? "immersive" : "docked";
}

export function saveCommentsLayoutMode(mode) {
  localStorage.setItem(COMMENTS_LAYOUT_KEY, mode === "docked" ? "docked" : "immersive");
}

const HOME_TAB_KEY = "owlhouse_home_tab";

/** 首页 Tab：doujin | king */
export function loadHomeTab() {
  const raw = localStorage.getItem(HOME_TAB_KEY);
  return raw === "king" ? "king" : "doujin";
}

export function saveHomeTab(tab) {
  localStorage.setItem(HOME_TAB_KEY, tab === "king" ? "king" : "doujin");
}

const KING_PROG_KEY = "owlhouse_king_progress";

export function loadKingProgress() {
  try {
    const raw = localStorage.getItem(KING_PROG_KEY);
    if (!raw) {
      return { lastSlotId: 0, lastPageNo: 0, lastVersionId: 0, lastTitle: "" };
    }
    const o = JSON.parse(raw);
    return {
      lastSlotId: Number(o.lastSlotId) || 0,
      lastPageNo: Number(o.lastPageNo) || 0,
      lastVersionId: Number(o.lastVersionId) || 0,
      lastTitle: String(o.lastTitle || ""),
    };
  } catch {
    return { lastSlotId: 0, lastPageNo: 0, lastVersionId: 0, lastTitle: "" };
  }
}

export function markKingRead({ slotId, page_no, title, versionId }) {
  const cur = loadKingProgress();
  const next = {
    lastSlotId: slotId,
    lastTitle: title || "",
    lastVersionId: versionId || cur.lastVersionId || 0,
    lastPageNo: page_no >= cur.lastPageNo ? page_no : cur.lastPageNo,
  };
  localStorage.setItem(KING_PROG_KEY, JSON.stringify(next));
  return next;
}

export function isKingRead(page_no) {
  const { lastPageNo } = loadKingProgress();
  return lastPageNo > 0 && page_no <= lastPageNo;
}

const STRIP_ASPECT_THRESHOLD = 2.0;

/** 高宽比（height/width）达到阈值时走条漫。 */
export function effectiveStripMode(heightOverWidth) {
  return (heightOverWidth || 0) >= STRIP_ASPECT_THRESHOLD;
}
