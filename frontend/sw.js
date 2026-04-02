/**
 * sw.js — Life OS Service Worker
 *
 * Responsibilities:
 *   1. Cache app shell on install (cache-first for static assets)
 *   2. Network-first for /api/ (never cache API responses)
 *   3. Handle push notifications
 *   4. Handle notification click → open PWA URL
 */

const CACHE_VERSION = "v3";
const CACHE_NAME = `life-os-${CACHE_VERSION}`;

const APP_SHELL = [
  "/",
  "/index.html",
  "/journal-morning.html",
  "/journal-evening.html",
  "/daily.html",
  "/planning.html",
  "/milestones.html",
  "/css/style.css",
  "/js/api.js",
  "/js/push.js",
  "/js/utils.js",
  "/js/today.js",
  "/js/journal.js",
  "/js/daily.js",
  "/calendar.html",
  "/js/calendar.js",
  "/manifest.json",
  "/icon-192.png",
  "/icon-512.png",
];

// ---------------------------------------------------------------------------
// Install — cache the app shell
// ---------------------------------------------------------------------------
self.addEventListener("install", event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL))
  );
  self.skipWaiting();
});

// ---------------------------------------------------------------------------
// Activate — delete old caches
// ---------------------------------------------------------------------------
self.addEventListener("activate", event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(k => k.startsWith("life-os-") && k !== CACHE_NAME)
          .map(k => caches.delete(k))
      )
    )
  );
  self.clients.claim();
});

// ---------------------------------------------------------------------------
// Fetch — cache-first for static, network-first for /api/
// ---------------------------------------------------------------------------
self.addEventListener("fetch", event => {
  const url = new URL(event.request.url);

  if (url.pathname.startsWith("/api/")) {
    // Network-first: never serve stale API data
    event.respondWith(
      fetch(event.request).catch(() =>
        new Response(JSON.stringify({ detail: "Offline" }), {
          status: 503,
          headers: { "Content-Type": "application/json" },
        })
      )
    );
    return;
  }

  // Cache-first for everything else
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(event.request, clone));
        }
        return resp;
      });
    })
  );
});

// ---------------------------------------------------------------------------
// Push — show notification
// ---------------------------------------------------------------------------
self.addEventListener("push", event => {
  let data = { title: "Life OS", body: "Tap to open", url: "/" };
  try {
    data = event.data.json();
  } catch (_) {}

  event.waitUntil(
    self.registration.showNotification(data.title, {
      body: data.body,
      icon: data.icon || "/icon-192.png",
      badge: "/icon-192.png",
      data: { url: data.url || "/" },
    })
  );
});

// ---------------------------------------------------------------------------
// Notification click — focus or open the PWA
// ---------------------------------------------------------------------------
self.addEventListener("notificationclick", event => {
  event.notification.close();
  const targetUrl = event.notification.data?.url || "/";

  event.waitUntil(
    clients.matchAll({ type: "window", includeUncontrolled: true }).then(clientList => {
      for (const client of clientList) {
        if ("focus" in client) {
          client.navigate(targetUrl);
          return client.focus();
        }
      }
      if (clients.openWindow) return clients.openWindow(targetUrl);
    })
  );
});
