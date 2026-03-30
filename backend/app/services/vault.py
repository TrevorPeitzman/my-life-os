"""
vault.py — all file I/O for the Life OS vault.

All paths go through _safe_path() which enforces:
1. Strict format validation (ISO date, week key, etc.)
2. Path reconstruction from parsed value (strips any injected components)
3. resolve() + prefix check (prevents symlink-based escapes)
"""
from __future__ import annotations

import re
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from filelock import FileLock

from app.config import settings

# ---------------------------------------------------------------------------
# Horizon definitions
# ---------------------------------------------------------------------------

HORIZONS = ("daily", "weekly", "monthly", "quarterly", "yearly")

_WEEKLY_RE = re.compile(r"^\d{4}-W(?:0[1-9]|[1-4]\d|5[0-3])$")
_MONTHLY_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")
_QUARTERLY_RE = re.compile(r"^\d{4}-Q[1-4]$")
_YEARLY_RE = re.compile(r"^\d{4}$")

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _vault_subdir(horizon: str) -> Path:
    if horizon not in HORIZONS:
        raise ValueError(f"Unknown horizon: {horizon}")
    return settings.VAULT_DIR / horizon


def _safe_path(horizon: str, key: str) -> Path:
    """
    Validate key format for the given horizon and return a safe Path.
    Raises ValueError on invalid input.
    """
    subdir = _vault_subdir(horizon)

    if horizon == "daily":
        parsed = date.fromisoformat(key)
        safe_key = parsed.isoformat()
    elif horizon == "weekly":
        if not _WEEKLY_RE.match(key):
            raise ValueError(f"Invalid week key: {key!r}. Expected YYYY-WNN")
        safe_key = key
    elif horizon == "monthly":
        if not _MONTHLY_RE.match(key):
            raise ValueError(f"Invalid month key: {key!r}. Expected YYYY-MM")
        safe_key = key
    elif horizon == "quarterly":
        if not _QUARTERLY_RE.match(key):
            raise ValueError(f"Invalid quarter key: {key!r}. Expected YYYY-QN")
        safe_key = key
    elif horizon == "yearly":
        if not _YEARLY_RE.match(key):
            raise ValueError(f"Invalid year key: {key!r}. Expected YYYY")
        safe_key = key
    else:
        raise ValueError(f"Unknown horizon: {horizon}")

    target = (subdir / f"{safe_key}.md").resolve()
    subdir_resolved = subdir.resolve()
    if not str(target).startswith(str(subdir_resolved) + "/"):
        raise ValueError("Path traversal detected")
    return target


# ---------------------------------------------------------------------------
# Frontmatter helpers
# ---------------------------------------------------------------------------

def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a markdown file into (frontmatter_dict, body)."""
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(parts[1]) or {}
    except yaml.YAMLError:
        fm = {}
    return fm, parts[2].lstrip("\n")


def dump_frontmatter(fm: dict[str, Any], body: str) -> str:
    """Reassemble frontmatter + body into a markdown string."""
    fm_str = yaml.dump(fm, default_flow_style=False, allow_unicode=True).rstrip()
    return f"---\n{fm_str}\n---\n\n{body}"


def update_section(content: str, header: str, new_body: str) -> str:
    """
    Replace the content of a section (identified by its ## header) with new_body.
    The section ends at the next ## header or EOF.
    Raises ValueError if the header is not found.
    """
    if header not in content:
        raise ValueError(f"Section '{header}' not found in document")

    before, _, rest = content.partition(header)

    # Find where the next ## section starts (but not ### or deeper)
    next_section = re.search(r"\n## ", rest)
    if next_section:
        after = rest[next_section.start():]
    else:
        after = ""

    return before + header + "\n\n" + new_body.strip() + "\n" + after


# ---------------------------------------------------------------------------
# Read / write
# ---------------------------------------------------------------------------

def read_note(horizon: str, key: str) -> str:
    path = _safe_path(horizon, key)
    if not path.exists():
        content = _make_template(horizon, key)
        _write_locked(path, content)
        return content
    if path.stat().st_size > settings.MAX_DAILY_FILE_BYTES:
        raise ValueError(f"File exceeds size limit ({settings.MAX_DAILY_FILE_BYTES} bytes)")
    return path.read_text(encoding="utf-8")


def write_note(horizon: str, key: str, content: str) -> None:
    if len(content.encode()) > settings.MAX_DAILY_FILE_BYTES:
        raise ValueError(f"Content exceeds size limit ({settings.MAX_DAILY_FILE_BYTES} bytes)")
    path = _safe_path(horizon, key)
    _write_locked(path, content)


def _write_locked(path: Path, content: str) -> None:
    lock = FileLock(str(path) + ".lock", timeout=5)
    with lock:
        path.write_text(content, encoding="utf-8")


def note_exists(horizon: str, key: str) -> bool:
    try:
        path = _safe_path(horizon, key)
        return path.exists()
    except ValueError:
        return False


# ---------------------------------------------------------------------------
# Open task scanner
# ---------------------------------------------------------------------------

def get_open_tasks(horizon: str = "daily", days_back: int = 90) -> list[dict]:
    """
    Scan vault notes for unchecked GFM tasks (- [ ] ...).
    Returns list of {text, date, line, horizon}.
    """
    subdir = _vault_subdir(horizon)
    files = sorted(subdir.glob("*.md"), reverse=True)[:days_back]
    tasks: list[dict] = []
    for f in files:
        if f.stat().st_size > settings.MAX_DAILY_FILE_BYTES:
            continue
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        key = f.stem
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("- [ ]"):
                tasks.append({
                    "text": stripped[5:].strip(),
                    "date": key,
                    "line": i,
                    "horizon": horizon,
                })
    return tasks


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _make_template(horizon: str, key: str) -> str:
    now_iso = datetime.utcnow().isoformat(timespec="seconds") + "Z"
    if horizon == "daily":
        return _daily_template(key, now_iso)
    elif horizon == "weekly":
        return _weekly_template(key, now_iso)
    elif horizon == "monthly":
        return _monthly_template(key, now_iso)
    elif horizon == "quarterly":
        return _quarterly_template(key, now_iso)
    elif horizon == "yearly":
        return _yearly_template(key, now_iso)
    raise ValueError(f"Unknown horizon: {horizon}")


def _daily_template(key: str, created: str) -> str:
    return f"""---
date: {key}
created: {created}
sleep_hours: null
mood_morning: null
mood_evening: null
tags: []
---

## Morning

**Success metric**:
**Gratitude**:
**Realistic work**:

## Tasks

<!-- Add tasks as: - [ ] Task description @project:name @estimate:30m -->

## Notes

## Evening

**Wins**:
-
-
-

**What I'd change**:
**Feeling**:
"""


def _weekly_template(key: str, created: str) -> str:
    # Infer parent month from week key e.g. 2026-W13 → 2026-03 (approximate)
    year, week = key.split("-W")
    # ISO week to approximate month
    d = datetime.strptime(f"{year}-W{week}-1", "%G-W%V-%u").date()
    parent_month = d.strftime("%Y-%m")
    return f"""---
horizon: weekly
key: {key}
created: {created}
parent: ../monthly/{parent_month}.md
theme: null
tags: []
---

## Focus this week

What's the single most important outcome for this week?

## Key outcomes

-
-
-

## Tasks

<!-- - [ ] Task description @project:name -->

## Daily notes

<!-- Links to each day's note will appear here -->

## Reflection

**What went well**:
**What I'd change**:
**Carry-forward**:
"""


def _monthly_template(key: str, created: str) -> str:
    year, month = key.split("-")
    quarter = (int(month) - 1) // 3 + 1
    parent_quarter = f"{year}-Q{quarter}"
    return f"""---
horizon: monthly
key: {key}
created: {created}
parent: ../quarterly/{parent_quarter}.md
theme: null
tags: []
---

## Theme

One word or phrase that captures this month's focus.

## Goals this month

<!-- Link to quarterly goals and break them into monthly actions -->

-
-
-

## Projects

<!-- Active projects this month and their key milestones -->

## Weekly breakdown

- Week 1:
- Week 2:
- Week 3:
- Week 4:

## Reflection

**Wins**:
**Misses**:
**Lessons**:
"""


def _quarterly_template(key: str, created: str) -> str:
    year = key.split("-")[0]
    return f"""---
horizon: quarterly
key: {key}
created: {created}
parent: ../yearly/{year}.md
theme: null
tags: []
---

## Theme

What does success look like this quarter in one sentence?

## OKRs / Big goals

### Objective 1

- KR:
- KR:

### Objective 2

- KR:
- KR:

## Monthly breakdown

- {key[:4]}-XX (Month 1):
- {key[:4]}-XX (Month 2):
- {key[:4]}-XX (Month 3):

## Projects

## Reflection

**What moved the needle**:
**What stalled**:
**Adjustments for next quarter**:
"""


def _yearly_template(key: str, created: str) -> str:
    return f"""---
horizon: yearly
key: {key}
created: {created}
theme: null
tags: []
---

## Vision

What does a great {key} look like? Write it as if you're looking back from Dec 31.

## Big goals

1.
2.
3.

## Quarterly breakdown

- Q1 ({key}):
- Q2 ({key}):
- Q3 ({key}):
- Q4 ({key}):

## Areas of life

### Health

### Work / Business

### Relationships

### Learning

### Finance

## Year in review

*(Fill in at year end)*

**Top wins**:
**Top lessons**:
**One word for the year**:
"""


# ---------------------------------------------------------------------------
# Goal hierarchy traversal
# ---------------------------------------------------------------------------

def get_goal_breakdown(horizon: str, key: str, depth: int = 0) -> dict:
    """
    Return a dict representing the note at (horizon, key), with:
    - parent: traversed upward via frontmatter 'parent' field
    - children: all notes in child horizon that reference this key
    - open_tasks: unchecked tasks in this note
    """
    max_depth = 5
    content = read_note(horizon, key)
    fm, body = parse_frontmatter(content)

    open_tasks = [
        line.strip()[5:].strip()
        for line in body.splitlines()
        if line.strip().startswith("- [ ]")
    ]

    result: dict = {
        "horizon": horizon,
        "key": key,
        "title": fm.get("theme") or key,
        "open_tasks": open_tasks,
        "parent": None,
        "children": [],
    }

    if depth < max_depth:
        result["children"] = _find_children(horizon, key, depth)

    return result


def _find_children(parent_horizon: str, parent_key: str, depth: int) -> list[dict]:
    """Find notes in the child horizon whose frontmatter 'parent' references this key."""
    child_horizon_map = {
        "yearly": "quarterly",
        "quarterly": "monthly",
        "monthly": "weekly",
        "weekly": "daily",
    }
    child_horizon = child_horizon_map.get(parent_horizon)
    if not child_horizon:
        return []

    subdir = _vault_subdir(child_horizon)
    children = []
    for f in sorted(subdir.glob("*.md")):
        try:
            text = f.read_text(encoding="utf-8")
            fm, _ = parse_frontmatter(text)
            parent_ref = str(fm.get("parent", ""))
            if parent_key in parent_ref:
                children.append(get_goal_breakdown(child_horizon, f.stem, depth + 1))
        except (OSError, ValueError):
            continue
    return children
