/**
 * utils.js — Shared UI helpers.
 */

/**
 * Show a toast notification.
 * @param {string} message
 * @param {"ok"|"error"|"warn"} type
 * @param {number} duration ms
 */
export function showToast(message, type = "ok", duration = 3000) {
  let toast = document.getElementById("toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.id = "toast";
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.className = type === "error" ? "error" : type === "warn" ? "" : "success";
  toast.classList.add("show");
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove("show"), duration);
}

/**
 * Check for a stored API key and validate it against /health.
 * Calls onMissing() if key is absent or invalid.
 */
export async function requireAuth(onMissing) {
  const key = localStorage.getItem("life_os_api_key");
  if (!key) { onMissing(); return false; }

  try {
    const resp = await fetch("/api/health");
    if (!resp.ok) throw new Error("health check failed");
    // Now try an authenticated endpoint
    const testResp = await fetch(`/api/daily/${getToday()}`, {
      headers: { Authorization: `Bearer ${key}` },
    });
    if (testResp.status === 401) { onMissing(); return false; }
    return true;
  } catch {
    // Network error — let it through, will fail at next real call
    return true;
  }
}

export function getToday() {
  const d = new Date();
  return [
    d.getFullYear(),
    String(d.getMonth() + 1).padStart(2, "0"),
    String(d.getDate()).padStart(2, "0"),
  ].join("-");
}

export function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/**
 * Show/hide the setup modal.
 */
export function showSetupModal() {
  document.getElementById("setup-modal")?.classList.remove("hidden");
}

export function hideSetupModal() {
  document.getElementById("setup-modal")?.classList.add("hidden");
}
