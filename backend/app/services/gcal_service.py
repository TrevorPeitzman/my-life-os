"""gcal_service.py — Google Calendar OAuth 2.0 + read/write integration.

OAuth flow:
  GET /calendar/auth       → redirect user to Google consent screen
  GET /calendar/callback   → receive code, exchange for tokens, store in config/google_tokens.json

Tokens are stored as JSON and auto-refreshed before each API call.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timezone
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    _GCAL_AVAILABLE = True
except ImportError:
    _GCAL_AVAILABLE = False
    logger.warning("google-api-python-client not installed; Google Calendar disabled")


SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

_TOKEN_FILE = None  # set lazily


def _token_path() -> Path:
    return settings.CONFIG_DIR / "google_tokens.json"


# ---------------------------------------------------------------------------
# OAuth flow helpers
# ---------------------------------------------------------------------------

def is_configured() -> bool:
    return bool(
        _GCAL_AVAILABLE
        and settings.GOOGLE_CLIENT_ID
        and settings.GOOGLE_CLIENT_SECRET
        and settings.GOOGLE_REDIRECT_URI
    )


def is_connected() -> bool:
    return is_configured() and _token_path().exists()


def get_auth_url() -> str:
    """Return the Google OAuth consent URL."""
    if not is_configured():
        raise RuntimeError("Google Calendar is not configured (missing CLIENT_ID/SECRET/REDIRECT_URI)")
    flow = _make_flow()
    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    return auth_url


def handle_callback(code: str) -> None:
    """Exchange authorization code for tokens and persist them."""
    flow = _make_flow()
    flow.fetch_token(code=code)
    creds = flow.credentials
    _save_credentials(creds)
    logger.info("Google Calendar tokens saved to %s", _token_path())


def _make_flow() -> "Flow":
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = settings.GOOGLE_REDIRECT_URI
    return flow


def _load_credentials() -> "Credentials | None":
    p = _token_path()
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        creds = Credentials(
            token=data.get("token"),
            refresh_token=data.get("refresh_token"),
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.GOOGLE_CLIENT_ID,
            client_secret=settings.GOOGLE_CLIENT_SECRET,
            scopes=SCOPES,
        )
        # Auto-refresh if expired
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            _save_credentials(creds)
        return creds
    except Exception as exc:
        logger.error("Failed to load Google credentials: %s", exc)
        return None


def _save_credentials(creds: "Credentials") -> None:
    data = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes or []),
    }
    _token_path().write_text(json.dumps(data, indent=2), encoding="utf-8")


def _get_service():
    creds = _load_credentials()
    if not creds:
        raise RuntimeError("Google Calendar not connected. Visit /api/calendar/auth to authorise.")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


# ---------------------------------------------------------------------------
# Free/busy
# ---------------------------------------------------------------------------

def get_free_slots(day: str) -> list[dict]:
    """
    Return free time slots for the given date (YYYY-MM-DD).
    Slots are gaps between existing events during waking hours (07:00–22:00).
    """
    if not is_connected():
        return []

    service = _get_service()
    tz = settings.TZ

    # Build start/end in UTC for the API query
    day_start = f"{day}T07:00:00"
    day_end = f"{day}T22:00:00"

    try:
        body = {
            "timeMin": f"{day}T00:00:00Z",
            "timeMax": f"{day}T23:59:59Z",
            "timeZone": tz,
            "items": [{"id": cal_id} for cal_id in settings.GOOGLE_CALENDAR_IDS],
        }
        result = service.freebusy().query(body=body).execute()
    except Exception as exc:
        logger.error("freebusy query failed: %s", exc)
        return []

    # Collect all busy intervals across all calendars
    busy_raw: list[tuple[datetime, datetime]] = []
    for cal_data in result.get("calendars", {}).values():
        for interval in cal_data.get("busy", []):
            start = datetime.fromisoformat(interval["start"].replace("Z", "+00:00"))
            end = datetime.fromisoformat(interval["end"].replace("Z", "+00:00"))
            busy_raw.append((start, end))

    # Sort and merge overlapping busy intervals
    busy_raw.sort(key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in busy_raw:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))

    # Build free slots between 07:00 and 22:00 in user's TZ
    from zoneinfo import ZoneInfo
    tz_obj = ZoneInfo(tz)
    window_start = datetime.fromisoformat(f"{day}T07:00:00").replace(tzinfo=tz_obj)
    window_end = datetime.fromisoformat(f"{day}T22:00:00").replace(tzinfo=tz_obj)

    # Convert busy to local TZ
    busy_local = [(s.astimezone(tz_obj), e.astimezone(tz_obj)) for s, e in merged]

    free_slots: list[dict] = []
    cursor = window_start
    for busy_start, busy_end in busy_local:
        if busy_start > cursor and (busy_start - cursor).seconds >= 900:  # ≥ 15 min
            free_slots.append({
                "start": cursor.strftime("%H:%M"),
                "end": busy_start.strftime("%H:%M"),
                "duration_minutes": int((busy_start - cursor).seconds / 60),
            })
        cursor = max(cursor, busy_end)

    if cursor < window_end and (window_end - cursor).seconds >= 900:
        free_slots.append({
            "start": cursor.strftime("%H:%M"),
            "end": window_end.strftime("%H:%M"),
            "duration_minutes": int((window_end - cursor).seconds / 60),
        })

    return free_slots


# ---------------------------------------------------------------------------
# Event creation
# ---------------------------------------------------------------------------

def create_event(title: str, start: str, end: str, description: str = "", calendar_id: str | None = None) -> dict:
    """
    Create a calendar event. start/end are ISO datetime strings (YYYY-MMDDTHH:MM:SS).
    Returns the created event resource dict.
    """
    if not is_connected():
        raise RuntimeError("Google Calendar not connected.")

    cal_id = calendar_id or settings.GOOGLE_CALENDAR_WRITE_ID
    service = _get_service()

    event = {
        "summary": title,
        "description": description,
        "start": {"dateTime": _ensure_tz(start), "timeZone": settings.TZ},
        "end": {"dateTime": _ensure_tz(end), "timeZone": settings.TZ},
    }

    try:
        created = service.events().insert(calendarId=cal_id, body=event).execute()
        logger.info("Created event '%s' on %s", title, cal_id)
        return created
    except Exception as exc:
        logger.error("Event creation failed: %s", exc)
        raise RuntimeError(f"Google Calendar event creation failed: {exc}") from exc


def _ensure_tz(dt_str: str) -> str:
    """Append local timezone offset if not already present."""
    if "T" not in dt_str:
        raise ValueError(f"Expected ISO datetime string, got: {dt_str!r}")
    if "+" not in dt_str and dt_str[-1] != "Z":
        # Append timezone from settings
        from zoneinfo import ZoneInfo
        tz_obj = ZoneInfo(settings.TZ)
        naive = datetime.fromisoformat(dt_str)
        aware = naive.replace(tzinfo=tz_obj)
        return aware.isoformat()
    return dt_str
