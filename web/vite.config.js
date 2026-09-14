import { defineConfig } from "vite";

/** 本地 npm run dev 时把 /api /media 转到这台后端。本机跑后端则改为 http://127.0.0.1:8000 */
const backend = process.env.VITE_PROXY_TARGET || "http://101.132.75.57";

export default defineConfig({
  server: {
    host: true,
    port: 5173,
    proxy: {
      "/api": backend,
      "/media": backend,
    },
  },
});
