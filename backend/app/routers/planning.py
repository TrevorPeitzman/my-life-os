from fastapi import APIRouter, HTTPException

from app.models import GoalBreakdown, PlanningNote, PlanningUpdateRequest
from app.services import vault

router = APIRouter(prefix="/planning", tags=["planning"])

VALID_HORIZONS = ("weekly", "monthly", "quarterly", "yearly")


def _check_horizon(horizon: str) -> None:
    if horizon not in VALID_HORIZONS:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid horizon '{horizon}'. Must be one of: {', '.join(VALID_HORIZONS)}",
        )


@router.get("/{horizon}/{key}", response_model=PlanningNote)
def get_planning_note(horizon: str, key: str) -> PlanningNote:
    _check_horizon(horizon)
    try:
        content = vault.read_note(horizon, key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fm, _ = vault.parse_frontmatter(content)
    return PlanningNote(horizon=horizon, key=key, content=content, frontmatter=fm)


@router.put("/{horizon}/{key}", response_model=PlanningNote)
def put_planning_note(horizon: str, key: str, body: PlanningUpdateRequest) -> PlanningNote:
    _check_horizon(horizon)
    try:
        vault.write_note(horizon, key, body.content)
        content = vault.read_note(horizon, key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    fm, _ = vault.parse_frontmatter(content)
    return PlanningNote(horizon=horizon, key=key, content=content, frontmatter=fm)


@router.get("/goals/breakdown/{horizon}/{key}", response_model=GoalBreakdown)
def goal_breakdown(horizon: str, key: str) -> GoalBreakdown:
    _check_horizon(horizon)
    try:
        data = vault.get_goal_breakdown(horizon, key)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return GoalBreakdown(**data)
