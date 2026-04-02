"""health_data.py — Apple Health webhook for sleep data."""
from __future__ import annotations

import math

from fastapi import APIRouter, HTTPException

from app.models import AppleHealthData
from app.services import vault

router = APIRouter(prefix="/health", tags=["health"])


@router.post("/apple")
def submit_apple_health(data: AppleHealthData) -> dict:
    """
    Receive sleep data posted by an iOS Shortcut and store it in the daily note frontmatter.
    Only sets apple_sleep_hours / apple_sleep_score; does not overwrite manual entries.

    iOS Shortcut setup (run at wake time via Personal Automation):
      1. Get Sleep Analysis (sum) from Health for last night.
      2. Get Sleep Score (if available) from Health for last night.
      3. Get Contents of URL:
           URL: https://<your-domain>/api/health/apple
           Method: POST
           Header: Authorization: Bearer <api-key>
           Body JSON: {"date":"<date>","sleep_hours":<hours>,"sleep_score":<score>}

    Sleep score to mood mapping: floor(score / 10) clamped 1-10.
    A score of 94 produces seeded_mood = 9.
    """
    try:
        content = vault.read_note("daily", data.date)
        fm, body = vault.parse_frontmatter(content)
        if data.sleep_hours is not None:
            fm["apple_sleep_hours"] = data.sleep_hours
        if data.sleep_score is not None:
            fm["apple_sleep_score"] = data.sleep_score
        vault.write_note("daily", data.date, vault.dump_frontmatter(fm, body))
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    seeded_mood: int | None = None
    if data.sleep_score is not None:
        seeded_mood = min(10, max(1, math.floor(data.sleep_score / 10)))

    return {"stored": True, "date": data.date, "seeded_mood": seeded_mood}


@router.get("/apple/{day}")
def get_apple_health(day: str) -> dict:
    """Return stored Apple Health data for a given day (used by frontend prefill)."""
    try:
        content = vault.read_note("daily", day)
        fm, _ = vault.parse_frontmatter(content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {
        "date": day,
        "apple_sleep_hours": fm.get("apple_sleep_hours"),
        "apple_sleep_score": fm.get("apple_sleep_score"),
    }
