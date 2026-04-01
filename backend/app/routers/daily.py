from fastapi import APIRouter, HTTPException

from app.models import DailyNote, DailyUpdateRequest
from app.services import vault

router = APIRouter(prefix="/daily", tags=["daily"])


@router.get("/{day}", response_model=DailyNote)
def get_daily(day: str) -> DailyNote:
    try:
        content = vault.read_note("daily", day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fm, _ = vault.parse_frontmatter(content)
    return DailyNote(date=day, content=content, frontmatter=fm)


@router.put("/{day}", response_model=DailyNote)
def put_daily(day: str, body: DailyUpdateRequest) -> DailyNote:
    try:
        vault.write_note("daily", day, body.content)
        content = vault.read_note("daily", day)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fm, _ = vault.parse_frontmatter(content)
    return DailyNote(date=day, content=content, frontmatter=fm)
