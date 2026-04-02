"""quote.py — Daily quote / weekly challenge endpoint."""
from datetime import date

from fastapi import APIRouter, HTTPException

from app.services.quotes import get_quote

router = APIRouter(prefix="/quote", tags=["quote"])


@router.get("/{day}")
def daily_quote(day: str) -> dict:
    try:
        d = date.fromisoformat(day)
    except ValueError:
        raise HTTPException(status_code=422, detail="day must be YYYY-MM-DD")
    return get_quote(d)
