from fastapi import APIRouter, HTTPException

from app.models import EveningEntry, MorningEntry
from app.services import vault

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("/{day}/morning")
def journal_morning(day: str, entry: MorningEntry) -> dict:
    try:
        content = vault.read_note("daily", day)
        fm, body = vault.parse_frontmatter(content)

        if entry.mood_score is not None:
            fm["mood_morning"] = entry.mood_score
        if entry.sleep_hours is not None:
            fm["sleep_hours"] = entry.sleep_hours

        morning_md = (
            f"**Success metric**: {entry.success}\n"
            f"**Gratitude**: {entry.gratitude}\n"
            f"**Realistic work**: {entry.realistic_work}\n"
        )
        body = vault.update_section(body, "## Morning", morning_md)
        vault.write_note("daily", day, vault.dump_frontmatter(fm, body))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"updated": True, "date": day, "section": "morning"}


@router.post("/{day}/evening")
def journal_evening(day: str, entry: EveningEntry) -> dict:
    try:
        content = vault.read_note("daily", day)
        fm, body = vault.parse_frontmatter(content)

        if entry.mood_score is not None:
            fm["mood_evening"] = entry.mood_score

        wins_lines = "\n".join(f"- {w}" for w in entry.wins)
        evening_md = (
            f"**Wins**:\n{wins_lines}\n\n"
            f"**What I'd change**: {entry.change}\n"
            f"**Feeling**: {entry.feeling}\n"
        )
        body = vault.update_section(body, "## Evening", evening_md)
        vault.write_note("daily", day, vault.dump_frontmatter(fm, body))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"updated": True, "date": day, "section": "evening"}
