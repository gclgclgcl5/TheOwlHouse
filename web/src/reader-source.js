import { api } from "./api.js";
import { markRead, markKingRead, loadKingProgress } from "./store.js";

const PAGE_BATCH = 40;

function mapDoujinPage(p) {
  return {
    id: p.id,
    title: p.title,
    page_no: p.page_no,
    image_url: p.image_url,
  };
}

function mapKingPage(p, versionName) {
  return {
    id: p.slot_id,
    title: p.title,
    page_no: p.page_no,
    image_url: p.image_url,
    subtitle: versionName || undefined,
  };
}

/**
 * @param {number} startPageId
 */
export function createDoujinSource(startPageId) {
  return {
    kind: "doujin",
    pageKey(page) {
      return page.id;
    },
    async bootstrap() {
      let pages = [];
      let total = 0;
      let nextOffset = 0;
      let hasMore = false;

      while (true) {
        const res = await api.listPages({
          limit: PAGE_BATCH,
          offset: nextOffset,
          order: "page_no",
        });
        const items = res.items || [];
        if (!items.length) break;
        pages = [...pages, ...items.map(mapDoujinPage)]
          .filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i)
          .sort((a, b) => a.page_no - b.page_no);
        total = Number(res.total || 0);
        nextOffset += items.length;
        hasMore = nextOffset < total;
        if (pages.some((p) => p.id === startPageId)) break;
        if (!hasMore) break;
      }

      if (pages.length && !pages.some((p) => p.id === startPageId)) {
        const one = await api.getPage(startPageId);
        pages = [...pages, mapDoujinPage(one)]
          .filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i)
          .sort((a, b) => a.page_no - b.page_no);
      }

      return {
        pages,
        initialId: startPageId,
        total: Math.max(total, pages.length),
        hasMore,
        nextOffset,
      };
    },
    async loadMore(pages, nextOffset) {
      const res = await api.listPages({
        limit: PAGE_BATCH,
        offset: nextOffset,
        order: "page_no",
      });
      const items = res.items || [];
      const total = Number(res.total || pages.length);
      if (!items.length) {
        return {
          pages,
          total,
          nextOffset,
          hasMore: false,
        };
      }
      const merged = [...pages, ...items.map(mapDoujinPage)]
        .filter((p, i, arr) => arr.findIndex((x) => x.id === p.id) === i)
        .sort((a, b) => a.page_no - b.page_no);
      const newOffset = nextOffset + items.length;
      return {
        pages: merged,
        total: Math.max(total, merged.length),
        nextOffset: newOffset,
        hasMore: newOffset < Math.max(total, merged.length),
      };
    },
    listComments(id, sort) {
      return api.listComments(id, sort);
    },
    createComment(id, content, parentId) {
      return api.createComment(id, content, parentId);
    },
    markRead(page) {
      markRead(page);
    },
  };
}

/**
 * @param {number} preferredVersionId
 * @param {number} deepSlotId
 */
export function createKingSource(preferredVersionId, deepSlotId = 0) {
  let activeVersionId = preferredVersionId;
  let versionName = "";

  return {
    kind: "king",
    pageKey(page) {
      return page.id;
    },
    async bootstrap() {
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
      activeVersionId = resolved.version_id;
      versionName = resolved.version_name;
      markKingRead({
        slotId: resolved.slot_id,
        page_no: resolved.page_no,
        title: resolved.title,
        versionId: activeVersionId,
      });
      const list = await api.listKingVersionPages(activeVersionId);
      versionName = list.version_name || versionName;
      const pages = (list.items || []).map((p) => mapKingPage(p, versionName));
      const switchMessage = resolved.switched
        ? `已切换到「${resolved.version_name}」`
        : null;
      return {
        pages,
        initialId: resolved.slot_id,
        total: pages.length,
        hasMore: false,
        nextOffset: pages.length,
        switchMessage,
        showVersionInfo: true,
        versionDescription: list.description || "",
      };
    },
    async loadMore(pages, nextOffset) {
      return {
        pages,
        total: pages.length,
        nextOffset,
        hasMore: false,
      };
    },
    listComments(id, sort) {
      return api.listKingComments(id, sort);
    },
    createComment(id, content, parentId) {
      return api.createKingComment(id, content, parentId);
    },
    markRead(page) {
      markKingRead({
        slotId: page.id,
        page_no: page.page_no,
        title: page.title,
        versionId: activeVersionId,
      });
    },
  };
}
