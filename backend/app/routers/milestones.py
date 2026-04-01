from fastapi import APIRouter, Query

from app.models import Milestone
from app.services import vault
from app.services.vault import MILESTONE_CATEGORIES, HORIZONS

router = APIRouter(prefix="/milestones", tags=["milestones"])


@router.get("", response_model=list[Milestone])
def get_milestones(
    category: str | None = Query(
        None,
        description=f"Filter by category. One of: {', '.join(MILESTONE_CATEGORIES)}",
    ),
    horizon: str | None = Query(
        None,
        description=f"Filter by horizon. One of: {', '.join(HORIZONS)}",
    ),
    days_back: int = Query(
        3650,
        ge=1,
        le=36500,
        description="How many notes to scan per horizon (sorted newest-first).",
    ),
) -> list[Milestone]:
    horizons = [horizon] if horizon else None
    raw = vault.get_milestones(horizons=horizons, days_back=days_back)
    if category:
        raw = [m for m in raw if m["category"] == category.lower()]
    return [Milestone(**m) for m in raw]
