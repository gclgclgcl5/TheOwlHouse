const listeners = [];

export function parseHash() {
  const raw = (location.hash || "#/login").replace(/^#/, "") || "/login";
  const path = raw.split("?")[0];
  const parts = path.split("/").filter(Boolean);
  if (parts[0] === "page" && parts[1]) {
    return { name: "page", pageId: Number(parts[1]) };
  }
  if (parts[0] === "king" && parts[1]) {
    const versionId = Number(parts[1]);
    if (parts[2] === "pages") {
      return { name: "king-pages", versionId };
    }
    if (parts[2] === "slot" && parts[3]) {
      return { name: "king", versionId, slotId: Number(parts[3]) };
    }
    return { name: "king", versionId, slotId: 0 };
  }
  const name = parts[0] || "login";
  return { name };
}

export function go(hash) {
  const path = hash.startsWith("#") ? hash.slice(1) : hash;
  const next = path.startsWith("/") ? `#${path}` : `#/${path}`;
  if (location.hash === next) {
    window.dispatchEvent(new HashChangeEvent("hashchange"));
    return;
  }
  location.hash = next;
}

export function onRoute(fn) {
  listeners.push(fn);
}

window.addEventListener("hashchange", () => {
  const route = parseHash();
  listeners.forEach((fn) => fn(route));
});
