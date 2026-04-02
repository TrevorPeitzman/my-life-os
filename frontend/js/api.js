/**
 * api.js — Authenticated fetch wrapper for Life OS backend.
 *
 * All requests include Authorization: Bearer <key> from localStorage.
 * The API key is read fresh on every call (supports key rotation without reload).
 */

const API_BASE = "/api";

class ApiError extends Error {
  constructor(status, detail) {
    super(detail || `HTTP ${status}`);
    this.status = status;
    this.detail = detail;
  }
}

function getKey() {
  const key = localStorage.getItem("life_os_api_key");
  if (!key) throw new Error("NO_API_KEY");
  return key;
}

/**
 * Returns today's date as YYYY-MM-DD in the user's LOCAL timezone.
 * This is correct for "what day is it for me" — the server uses its own TZ for cron.
 */
function getToday() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

async function request(method, path, body = null) {
  const key = getKey();
  const opts = {
    method,
    headers: {
      Authorization: `Bearer ${key}`,
      "Content-Type": "application/json",
    },
  };
  if (body !== null) {
    opts.body = JSON.stringify(body);
  }

  let resp;
  try {
    resp = await fetch(API_BASE + path, opts);
  } catch (err) {
    throw new ApiError(0, "Network error — is the server reachable?");
  }

  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      detail = data.detail || detail;
    } catch (_) {}
    throw new ApiError(resp.status, detail);
  }

  const ct = resp.headers.get("content-type") || "";
  if (ct.includes("application/json")) return resp.json();
  return resp.text();
}

const api = {
  getToday,

  // --- Meta ---
  health: ()           => fetch(API_BASE + "/health").then(r => r.json()),
  publicConfig: ()     => fetch(API_BASE + "/config/public").then(r => r.json()),

  // --- Daily notes ---
  getDaily: (day)      => request("GET",  `/daily/${day}`),
  putDaily: (day, content) => request("PUT", `/daily/${day}`, { content }),

  // --- Journal ---
  journalMorning: (day, entry) => request("POST", `/journal/${day}/morning`, entry),
  journalEvening: (day, entry) => request("POST", `/journal/${day}/evening`, entry),

  // --- Tasks ---
  getOpenTasks: (horizon = "daily", daysBack = 90) =>
    request("GET", `/tasks/open?horizon=${horizon}&days_back=${daysBack}`),

  // --- Push ---
  subscribePush: (sub)   => request("POST", "/push/subscribe", sub),
  unsubscribePush: (sub) => request("POST", "/push/unsubscribe", sub),

  // --- AI ---
  aiSuggest: (day)       => request("POST", `/ai/suggest/${day}`),

  // --- Google Calendar ---
  gcalStatus: ()         => request("GET",  "/calendar/status"),
  gcalFreebusy: (day)    => request("GET",  `/calendar/freebusy/${day}`),
  gcalFill: (day)        => request("POST", `/calendar/fill/${day}`),
  gcalCreateEvent: (ev)  => request("POST", "/calendar/create-event", ev),

  // --- Planning ---
  getPlanning: (horizon, key) => request("GET",  `/planning/${horizon}/${key}`),
  putPlanning: (horizon, key, content) => request("PUT", `/planning/${horizon}/${key}`, { content }),
  goalBreakdown: (horizon, key) => request("GET", `/planning/goals/breakdown/${horizon}/${key}`),

  // --- Milestones ---
  getMilestones: (category = null, horizon = null) => {
    const p = new URLSearchParams();
    if (category) p.set("category", category);
    if (horizon) p.set("horizon", horizon);
    const qs = p.toString() ? `?${p}` : "";
    return request("GET", `/milestones${qs}`);
  },

  // --- Quote ---
  getQuote: (day) => request("GET", `/quote/${day}`),
};

export { api, ApiError };
