import { createApp } from "./vue.esm-browser.js";
import { App } from "./App.mjs?v=20260424e";

const root = document.querySelector("#app");

function renderError(title, detail) {
  if (!root) return;
  root.innerHTML = `
    <div style="max-width:960px;margin:40px auto;padding:24px;border-radius:20px;background:rgba(255,255,255,.88);border:1px solid rgba(176,67,47,.18);box-shadow:0 20px 40px rgba(59,35,14,.12);font-family:'Microsoft YaHei',sans-serif;color:#231811;">
      <h2 style="margin:0 0 12px;color:#a02c1e;">${title}</h2>
      <pre style="white-space:pre-wrap;line-height:1.7;background:#151311;color:#f8f0e8;padding:16px;border-radius:14px;overflow:auto;">${String(detail || "未知错误")}</pre>
    </div>
  `;
}

window.addEventListener("error", (event) => {
  renderError("前端运行出错", event.error?.stack || event.message);
});

window.addEventListener("unhandledrejection", (event) => {
  renderError("前端异步错误", event.reason?.stack || event.reason);
});

try {
  createApp(App).mount("#app");
} catch (error) {
  renderError("前端启动失败", error?.stack || error);
}
