"""push_service.py — VAPID web push notification management."""
from __future__ import annotations

import json
import logging
from pathlib import Path

from filelock import FileLock

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from pywebpush import WebPushException, webpush as _webpush
    _PUSH_AVAILABLE = True
except ImportError:
    _PUSH_AVAILABLE = False
    logger.warning("pywebpush not installed; push notifications disabled")


# ---------------------------------------------------------------------------
# Subscription storage
# ---------------------------------------------------------------------------

def _subs_path() -> Path:
    return settings.CONFIG_DIR / "push_subscriptions.json"


def _lock() -> FileLock:
    return FileLock(str(_subs_path()) + ".lock", timeout=5)


def _load_subscriptions() -> list[dict]:
    p = _subs_path()
    if not p.exists():
        return []
    try:
        with _lock():
            return json.loads(p.read_text(encoding="utf-8")).get("subscriptions", [])
    except (json.JSONDecodeError, OSError):
        return []


def _save_subscriptions(subs: list[dict]) -> None:
    p = _subs_path()
    with _lock():
        p.write_text(
            json.dumps({"subscriptions": subs}, indent=2),
            encoding="utf-8",
        )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def subscribe(endpoint: str, keys: dict[str, str]) -> None:
    subs = _load_subscriptions()
    # De-duplicate by endpoint
    if any(s["endpoint"] == endpoint for s in subs):
        return
    subs.append({"endpoint": endpoint, "keys": keys})
    _save_subscriptions(subs)
    logger.info("Push subscription added (total: %d)", len(subs))


def unsubscribe(endpoint: str) -> None:
    subs = _load_subscriptions()
    new_subs = [s for s in subs if s["endpoint"] != endpoint]
    _save_subscriptions(new_subs)
    logger.info("Push subscription removed (total: %d)", len(new_subs))


def send_push_to_all(payload: dict) -> dict[str, int]:
    """
    Send a push notification to all subscribers.
    Returns {"sent": N, "failed": M, "removed": K}.
    """
    if not _PUSH_AVAILABLE:
        logger.warning("Push skipped: pywebpush unavailable")
        return {"sent": 0, "failed": 0, "removed": 0}

    if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_PUBLIC_KEY:
        logger.warning("Push skipped: VAPID keys not configured")
        return {"sent": 0, "failed": 0, "removed": 0}

    subs = _load_subscriptions()
    sent, failed, to_remove = 0, 0, []

    for sub in subs:
        success, gone = _send_one(sub, payload)
        if success:
            sent += 1
        elif gone:
            to_remove.append(sub["endpoint"])
            failed += 1
        else:
            failed += 1

    if to_remove:
        remaining = [s for s in subs if s["endpoint"] not in to_remove]
        _save_subscriptions(remaining)

    logger.info("Push results: sent=%d failed=%d removed=%d", sent, failed, len(to_remove))
    return {"sent": sent, "failed": failed, "removed": len(to_remove)}


def _send_one(sub: dict, payload: dict) -> tuple[bool, bool]:
    """
    Send to one subscriber.
    Returns (success, gone_410).
    """
    try:
        _webpush(
            subscription_info=sub,
            data=json.dumps(payload),
            vapid_private_key=settings.VAPID_PRIVATE_KEY,
            vapid_claims={
                "sub": settings.VAPID_EMAIL or "mailto:noreply@example.com",
            },
        )
        return True, False
    except Exception as exc:  # pywebpush raises WebPushException
        status = getattr(getattr(exc, "response", None), "status_code", None)
        if status == 410:
            logger.info("Push endpoint gone (410), removing: %s…", sub["endpoint"][:40])
            return False, True
        logger.warning("Push failed for %s…: %s", sub["endpoint"][:40], exc)
        return False, False
