import { isLoggedIn } from "./store.js";
import { go, onRoute, parseHash } from "./router.js";
import { renderLogin } from "./views/login.js";
import { renderRegister } from "./views/register.js";
import { renderHome } from "./views/home.js";
import { renderReader } from "./views/reader.js";
import { createDoujinSource, createKingSource } from "./reader-source.js";
import { renderNotifications } from "./views/notifications.js";
import { renderKingPages } from "./views/king-pages.js";

const app = document.getElementById("app");

function render(route) {
  const authed = isLoggedIn();
  if (!authed && route.name !== "login" && route.name !== "register") {
    go("/login");
    return;
  }
  if (authed && (route.name === "login" || route.name === "register")) {
    go("/home");
    return;
  }
  switch (route.name) {
    case "register":
      renderRegister(app);
      break;
    case "home":
      renderHome(app);
      break;
    case "page":
      renderReader(app, createDoujinSource(route.pageId));
      break;
    case "king-pages":
      renderKingPages(app, route.versionId);
      break;
    case "king":
      renderReader(app, createKingSource(route.versionId, route.slotId || 0));
      break;
    case "notifications":
      renderNotifications(app);
      break;
    default:
      renderLogin(app);
  }
}

onRoute(render);

if (!location.hash) {
  go(isLoggedIn() ? "/home" : "/login");
} else {
  render(parseHash());
}
