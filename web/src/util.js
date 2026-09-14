export function escapeHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

export function formatMmDd(raw) {
  const s = String(raw || "");
  try {
    const d = new Date(s);
    if (!Number.isNaN(d.getTime())) {
      const m = String(d.getMonth() + 1).padStart(2, "0");
      const day = String(d.getDate()).padStart(2, "0");
      return `${m}-${day}`;
    }
  } catch {
    /* fallthrough */
  }
  if (s.length >= 10 && s[4] === "-") return `${s.slice(5, 7)}-${s.slice(8, 10)}`;
  return s.slice(0, 10);
}

export function avatarHtml(url, name, cls = "") {
  const letter = escapeHtml((name || "?").slice(0, 1));
  if (url) {
    return `<img class="${cls}" src="${escapeHtml(url)}" alt="" />`;
  }
  return `<div class="av ${cls}">${letter}</div>`;
}
