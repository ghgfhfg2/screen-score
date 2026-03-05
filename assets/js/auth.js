---
---

(() => {
  const enabled = {{ site.auth.enabled | default: false | jsonify }};
  if (!enabled) return;

  const loginPath = {{ site.auth.login_path | default: '/login/' | jsonify }};
  const expectedHash = {{ site.auth.password_hash_sha256 | default: '' | jsonify }};

  const path = window.location.pathname;
  const isLoginPage = path === loginPath || path === loginPath.replace(/\/$/, "");

  const isStaticAsset = /\.(css|js|png|jpg|jpeg|gif|svg|webp|ico|xml|txt)$/i.test(path);
  if (isStaticAsset) return;

  const ok = sessionStorage.getItem("screen_score_auth_ok") === "1";

  if (!ok && !isLoginPage) {
    const next = encodeURIComponent(window.location.pathname + window.location.search + window.location.hash);
    window.location.replace(`${loginPath}?next=${next}`);
    return;
  }

  if (!isLoginPage) return;

  const form = document.getElementById("login-form");
  const input = document.getElementById("login-password");
  const error = document.getElementById("login-error");
  if (!form || !input) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value || "";
    const hash = await sha256(text);

    if (hash === expectedHash) {
      sessionStorage.setItem("screen_score_auth_ok", "1");
      const next = new URLSearchParams(window.location.search).get("next") || "/";
      window.location.replace(next);
      return;
    }

    if (error) error.style.display = "block";
    input.value = "";
    input.focus();
  });

  async function sha256(str) {
    const buf = new TextEncoder().encode(str);
    const digest = await crypto.subtle.digest("SHA-256", buf);
    return Array.from(new Uint8Array(digest)).map((b) => b.toString(16).padStart(2, "0")).join("");
  }
})();
