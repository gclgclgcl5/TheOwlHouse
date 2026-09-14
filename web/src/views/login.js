import { api } from "../api.js";
import { setToken } from "../store.js";
import { go } from "../router.js";
import { escapeHtml } from "../util.js";

export function renderLogin(root) {
  root.innerHTML = `
    <div class="auth-screen">
      <form class="auth-box" id="login-form">
        <h1>登录</h1>
        <input class="field" name="nickname" placeholder="昵称" autocomplete="username" required />
        <input class="field" name="password" type="password" placeholder="密码" autocomplete="current-password" required />
        <p class="error hidden" id="err"></p>
        <button class="btn" type="submit" id="submit">登录</button>
        <button class="btn-ghost" type="button" id="to-reg">没有账号？去注册</button>
      </form>
    </div>
  `;
  root.querySelector("#to-reg").onclick = () => go("/register");
  root.querySelector("#login-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = root.querySelector("#err");
    const btn = root.querySelector("#submit");
    err.classList.add("hidden");
    btn.disabled = true;
    try {
      const res = await api.login(String(fd.get("nickname") || "").trim(), String(fd.get("password") || ""));
      setToken(res.access_token);
      go("/home");
    } catch (ex) {
      err.textContent = ex.message || "登录失败";
      err.classList.remove("hidden");
    } finally {
      btn.disabled = false;
    }
  };
  void escapeHtml;
}
