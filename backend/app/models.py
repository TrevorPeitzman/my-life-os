from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Journal
# ---------------------------------------------------------------------------

class MorningEntry(BaseModel):
    gratitude_1: str
    gratitude_2: str
    gratitude_3: str
    great_1: str
    great_2: str
    great_3: str
    realistic_work: str
    affirmation: str
    mood_score: int | None = None
    sleep_hours: float | None = None

    @field_validator("mood_score")
    @classmethod
    def validate_mood(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 10):
            raise ValueError("mood_score must be between 1 and 10")
        return v

    @field_validator("sleep_hours")
    @classmethod
    def validate_sleep(cls, v: float | None) -> float | None:
        if v is not None and not (0 < v <= 24):
            raise ValueError("sleep_hours must be between 0 and 24")
        return v


class EveningEntry(BaseModel):
    wins: list[str]
    change: str
    feeling: str
    mood_score: int | None = None

    @field_validator("wins")
    @classmethod
    def validate_wins(cls, v: list[str]) -> list[str]:
        if len(v) != 3:
            raise ValueError("wins must contain exactly 3 items")
        return v

    @field_validator("mood_score")
    @classmethod
    def validate_mood(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 10):
            raise ValueError("mood_score must be between 1 and 10")
        return v


class AppleHealthData(BaseModel):
    date: str          # YYYY-MM-DD
    sleep_hours: float | None = None
    sleep_score: int | None = None  # 0-100

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not _DATE_RE.match(v):
            raise ValueError("date must be in YYYY-MM-DD format")
        return v

    @field_validator("sleep_score")
    @classmethod
    def validate_score(cls, v: int | None) -> int | None:
        if v is not None and not (0 <= v <= 100):
            raise ValueError("sleep_score must be between 0 and 100")
        return v

    @field_validator("sleep_hours")
    @classmethod
    def validate_sleep(cls, v: float | None) -> float | None:
        if v is not None and not (0 < v <= 24):
            raise ValueError("sleep_hours must be between 0 and 24")
        return v


# ---------------------------------------------------------------------------
# Planning
# ---------------------------------------------------------------------------

class DailyUpdateRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def check_size(cls, v: str) -> str:
        if len(v.encode()) > 524288:
            raise ValueError("Content exceeds 512 KB limit")
        return v


class PlanningUpdateRequest(BaseModel):
    content: str

    @field_validator("content")
    @classmethod
    def check_size(cls, v: str) -> str:
        if len(v.encode()) > 524288:
            raise ValueError("Content exceeds 512 KB limit")
        return v


# ---------------------------------------------------------------------------
# Time blocks & AI
# ---------------------------------------------------------------------------

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_TIME_RE = re.compile(r"^\d{2}:\d{2}$")


class TimeBlock(BaseModel):
    start: str
    end: str
    label: str
    type: str

    @field_validator("start", "end")
    @classmethod
    def validate_time(cls, v: str) -> str:
        if not _TIME_RE.match(v):
            raise ValueError("Time must be in HH:MM format")
        return v

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        if v not in {"focus", "admin", "break", "personal", "health"}:
            raise ValueError("type must be one of: focus, admin, break, personal, health")
        return v


class AISuggestionResponse(BaseModel):
    blocks: list[TimeBlock]
    rationale: str


# ---------------------------------------------------------------------------
# Milestones
# ---------------------------------------------------------------------------

class Milestone(BaseModel):
    text: str
    date: str
    category: str   # career | health | business | learning | finance | personal
    horizon: str
    checked: bool   # True if the source line was a completed task (- [x])


# ---------------------------------------------------------------------------
# Push notifications
# ---------------------------------------------------------------------------

class PushSubscription(BaseModel):
    endpoint: str
    keys: dict[str, str]


# ---------------------------------------------------------------------------
# Google Calendar
# ---------------------------------------------------------------------------

class CalendarEvent(BaseModel):
    title: str
    start: str   # ISO datetime string
    end: str     # ISO datetime string
    calendar_id: str | None = None
    description: str | None = None


class FreeBusySlot(BaseModel):
    start: str
    end: str
    duration_minutes: int


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------

class OpenTask(BaseModel):
    text: str
    date: str
    line: int
    horizon: str  # "daily" | "weekly" | "monthly" etc.


# ---------------------------------------------------------------------------
# Responses
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: str
    vault_dir: str
    tz: str
    ai_provider: str
    gcal_connected: bool


class DailyNote(BaseModel):
    date: str
    content: str
    frontmatter: dict[str, Any]


class PlanningNote(BaseModel):
    horizon: str
    key: str
    content: str
    frontmatter: dict[str, Any]


class GoalBreakdown(BaseModel):
    horizon: str
    key: str
    title: str
    parent: "GoalBreakdown | None" = None
    children: list["GoalBreakdown"] = []
    open_tasks: list[str] = []


# Resolve forward references for the recursive GoalBreakdown model
GoalBreakdown.model_rebuild()
