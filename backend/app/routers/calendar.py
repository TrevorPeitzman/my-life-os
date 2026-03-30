from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import RedirectResponse

from app.models import CalendarEvent, FreeBusySlot
from app.services import gcal_service, vault

router = APIRouter(prefix="/calendar", tags=["calendar"])


@router.get("/auth")
def gcal_auth() -> RedirectResponse:
    if not gcal_service.is_configured():
        raise HTTPException(
            status_code=503,
            detail="Google Calendar is not configured. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI.",
        )
    auth_url = gcal_service.get_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/callback")
def gcal_callback(code: str = Query(...), state: str | None = Query(None)) -> dict:
    if not gcal_service.is_configured():
        raise HTTPException(status_code=503, detail="Google Calendar not configured")
    try:
        gcal_service.handle_callback(code)
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"OAuth callback failed: {exc}")
    return {"connected": True, "message": "Google Calendar connected successfully"}


@router.get("/status")
def gcal_status() -> dict:
    return {
        "configured": gcal_service.is_configured(),
        "connected": gcal_service.is_connected(),
    }


@router.get("/freebusy/{day}", response_model=list[FreeBusySlot])
def get_freebusy(day: str) -> list[FreeBusySlot]:
    if not gcal_service.is_connected():
        raise HTTPException(
            status_code=503,
            detail="Google Calendar not connected. Visit /api/calendar/auth",
        )
    try:
        slots = gcal_service.get_free_slots(day)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return [FreeBusySlot(**s) for s in slots]


@router.post("/fill/{day}")
async def fill_day(day: str) -> dict:
    """
    Combines open tasks + free slots → AI suggestions informed by calendar.
    Returns time block suggestions ready to paste into the daily note.
    """
    if not gcal_service.is_connected():
        raise HTTPException(status_code=503, detail="Google Calendar not connected")

    try:
        content = vault.read_note("daily", day)
        free_slots = gcal_service.get_free_slots(day)
    except Exception as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    open_tasks = [t["text"] for t in vault.get_open_tasks(horizon="daily", days_back=7)]

    from app.services import ai_service
    suggestion = await ai_service.suggest(day, content, open_tasks, free_slots)
    return {
        "free_slots": free_slots,
        "suggested_blocks": [b.model_dump() for b in suggestion.blocks],
        "rationale": suggestion.rationale,
    }


@router.post("/create-event")
def create_event(event: CalendarEvent) -> dict:
    if not gcal_service.is_connected():
        raise HTTPException(status_code=503, detail="Google Calendar not connected")
    try:
        created = gcal_service.create_event(
            title=event.title,
            start=event.start,
            end=event.end,
            description=event.description or "",
            calendar_id=event.calendar_id,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    return {
        "created": True,
        "event_id": created.get("id"),
        "html_link": created.get("htmlLink"),
    }
