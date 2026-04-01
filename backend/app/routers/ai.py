from fastapi import APIRouter, HTTPException

from app.models import AISuggestionResponse
from app.services import ai_service, gcal_service, vault

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/suggest/{day}", response_model=AISuggestionResponse)
async def suggest(day: str) -> AISuggestionResponse:
    try:
        content = vault.read_note("daily", day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    open_tasks = [t["text"] for t in vault.get_open_tasks(horizon="daily", days_back=7)]

    # Optionally enrich with Google Calendar free/busy
    free_slots: list[dict] = []
    if gcal_service.is_connected():
        try:
            free_slots = gcal_service.get_free_slots(day)
        except Exception:
            pass  # Non-fatal; proceed without calendar data

    return await ai_service.suggest(day, content, open_tasks, free_slots)
