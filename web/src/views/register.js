import { api } from "../api.js";
import { setToken } from "../store.js";
import { go } from "../router.js";

export function renderRegister(root) {
  root.innerHTML = `
    <div class="auth-screen">
      <form class="auth-box" id="reg-form">
        <h1>注册</h1>
        <label class="avatar-pick" id="avatar-box">头像</label>
        <input type="file" id="avatar" accept="image/*" hidden />
        <button class="btn-ghost" type="button" id="pick">选择头像</button>
        <input class="field" name="nickname" placeholder="昵称" required maxlength="64" />
        <input class="field" name="password" type="password" placeholder="密码（至少4位）" required minlength="4" />
        <p class="error hidden" id="err"></p>
        <button class="btn" type="submit" id="submit">注册</button>
        <button class="btn-ghost" type="button" id="to-login">已有账号？去登录</button>
      </form>
    </div>
  `;
  const fileInput = root.querySelector("#avatar");
  const box = root.querySelector("#avatar-box");
  let file = null;
  const pick = () => fileInput.click();
  box.onclick = pick;
  root.querySelector("#pick").onclick = pick;
  fileInput.onchange = () => {
    file = fileInput.files?.[0] || null;
    if (!file) return;
    const url = URL.createObjectURL(file);
    box.innerHTML = `<img src="${url}" alt="头像预览" />`;
    root.querySelector("#pick").textContent = "已选择头像（点击重选）";
  };
  root.querySelector("#to-login").onclick = () => go("/login");
  root.querySelector("#reg-form").onsubmit = async (e) => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const err = root.querySelector("#err");
    const btn = root.querySelector("#submit");
    err.classList.add("hidden");
    if (!file) {
      err.textContent = "请选择头像";
      err.classList.remove("hidden");
      return;
    }
    const nick = String(fd.get("nickname") || "").trim();
    const pass = String(fd.get("password") || "");
    if (pass.length < 4) {
      err.textContent = "密码至少 4 位";
      err.classList.remove("hidden");
      return;
    }
    btn.disabled = true;
    try {
      const res = await api.register(nick, pass, file);
      setToken(res.access_token);
      go("/home");
    } catch (ex) {
      err.textContent = ex.message || "注册失败";
      err.classList.remove("hidden");
    } finally {
      btn.disabled = false;
    }
  };
}
