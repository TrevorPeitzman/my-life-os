from fastapi import APIRouter, Query

from app.models import OpenTask
from app.services import vault

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/open", response_model=list[OpenTask])
def get_open_tasks(
    horizon: str = Query("daily", description="Vault horizon to scan: daily, weekly, monthly, etc."),
    days_back: int = Query(90, ge=1, le=365, description="How many notes to scan (sorted newest-first)"),
) -> list[OpenTask]:
    raw = vault.get_open_tasks(horizon=horizon, days_back=days_back)
    return [OpenTask(**t) for t in raw]
