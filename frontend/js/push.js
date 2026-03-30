/**
 * push.js — Service worker registration + VAPID push subscription.
 *
 * Push on iOS requires:
 *   1. PWA added to Home Screen (Safari → Share → Add to Home Screen)
 *   2. iOS 16.4+
 *   3. Notification.requestPermission() called from a user gesture
 */

import { api } from "./api.js";

function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map(c => c.charCodeAt(0)));
}

let _swReg = null;

export async function registerServiceWorker() {
  if (!("serviceWorker" in navigator)) return null;
  try {
    _swReg = await navigator.serviceWorker.register("/sw.js");
    console.log("[push] Service worker registered");
    return _swReg;
  } catch (err) {
    console.error("[push] SW registration failed:", err);
    return null;
  }
}

export async function requestPushPermission() {
  if (!("Notification" in window)) {
    console.warn("[push] Notifications not supported");
    return false;
  }
  if (Notification.permission === "granted") return true;
  if (Notification.permission === "denied") return false;

  const result = await Notification.requestPermission();
  return result === "granted";
}

export async function subscribeToPush() {
  if (!_swReg) {
    console.warn("[push] No service worker registration");
    return false;
  }

  // Fetch VAPID public key
  let vapidKey;
  try {
    const config = await api.publicConfig();
    vapidKey = config.vapid_public_key;
  } catch (err) {
    console.warn("[push] Could not fetch VAPID key:", err);
    return false;
  }

  if (!vapidKey) {
    console.warn("[push] VAPID public key not configured on server");
    return false;
  }

  try {
    const existing = await _swReg.pushManager.getSubscription();
    if (existing) {
      // Already subscribed — ensure server knows about it
      await api.subscribePush({
        endpoint: existing.endpoint,
        keys: {
          p256dh: btoa(String.fromCharCode(...new Uint8Array(existing.getKey("p256dh")))),
          auth: btoa(String.fromCharCode(...new Uint8Array(existing.getKey("auth")))),
        },
      });
      return true;
    }

    const sub = await _swReg.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToUint8Array(vapidKey),
    });

    await api.subscribePush({
      endpoint: sub.endpoint,
      keys: {
        p256dh: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("p256dh")))),
        auth: btoa(String.fromCharCode(...new Uint8Array(sub.getKey("auth")))),
      },
    });

    console.log("[push] Subscribed successfully");
    return true;
  } catch (err) {
    console.error("[push] Subscribe failed:", err);
    return false;
  }
}

/**
 * Show the iOS "Add to Home Screen" banner if:
 *   - Running on iOS Safari
 *   - Not already in standalone mode
 */
export function showIOSInstallBanner() {
  const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
  const isStandalone = window.navigator.standalone;
  const dismissed = sessionStorage.getItem("ios_banner_dismissed");

  if (!isIOS || isStandalone || dismissed) return;

  const banner = document.getElementById("ios-install-banner");
  if (banner) {
    banner.classList.remove("hidden");
    banner.querySelector(".dismiss")?.addEventListener("click", () => {
      banner.classList.add("hidden");
      sessionStorage.setItem("ios_banner_dismissed", "1");
    });
  }
}
