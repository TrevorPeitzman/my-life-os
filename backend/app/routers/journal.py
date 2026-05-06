import calendar as cal_module
import re as _re

from fastapi import APIRouter, HTTPException

from app.models import EveningEntry, MorningEntry
from app.services import vault

router = APIRouter(prefix="/journal", tags=["journal"])


@router.post("/{day}/morning")
def journal_morning(day: str, entry: MorningEntry) -> dict:
    try:
        content = vault.read_note("daily", day)
        fm, body = vault.parse_frontmatter(content)

        fm["morning_done"] = True
        if entry.mood_score is not None:
            fm["mood_morning"] = entry.mood_score
        if entry.sleep_hours is not None:
            fm["sleep_hours"] = entry.sleep_hours

        morning_md = (
            f"**Grateful 1**: {entry.gratitude_1}\n"
            f"**Grateful 2**: {entry.gratitude_2}\n"
            f"**Grateful 3**: {entry.gratitude_3}\n"
            f"**Great today 1**: {entry.great_1}\n"
            f"**Great today 2**: {entry.great_2}\n"
            f"**Great today 3**: {entry.great_3}\n"
            f"**Realistic work**: {entry.realistic_work}\n"
            f"**Affirmation**: {entry.affirmation}\n"
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

        fm["evening_done"] = True
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


@router.get("/consistency")
def get_consistency(month: str) -> dict:
    """
    Return morning/evening completion for every day in a month.
    month: "YYYY-MM"
    Completion is inferred from mood_morning / mood_evening frontmatter fields.
    """
    if not _re.match(r"^\d{4}-(0[1-9]|1[0-2])$", month):
        raise HTTPException(status_code=422, detail="month must be YYYY-MM")

    year_str, month_str = month.split("-")
    year, mon = int(year_str), int(month_str)
    _, days_in_month = cal_module.monthrange(year, mon)

    days = []
    for day_num in range(1, days_in_month + 1):
        day_str = f"{year:04d}-{mon:02d}-{day_num:02d}"
        morning_done = False
        evening_done = False
        if vault.note_exists("daily", day_str):
            try:
                content = vault.read_note("daily", day_str)
                fm, _ = vault.parse_frontmatter(content)
                morning_done = bool(fm.get("morning_done")) or (fm.get("mood_morning") is not None)
                evening_done = bool(fm.get("evening_done")) or (fm.get("mood_evening") is not None)
            except ValueError:
                pass  # oversized or malformed file — treat as incomplete
        days.append({
            "date": day_str,
            "day": day_num,
            "morning": morning_done,
            "evening": evening_done,
        })

    return {"month": month, "days": days}
