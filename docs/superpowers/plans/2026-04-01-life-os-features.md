# Life OS Feature Additions — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add four prioritised features to Life OS: redesigned morning prompts, daily quote/weekly challenge, a calendar consistency view, and optional Apple Health sleep seeding.

**Architecture:** Each feature is self-contained and can be deployed independently. Backend changes follow the existing FastAPI + Pydantic + Markdown-vault pattern. Frontend changes are vanilla JS/HTML with no build step. All new API routes are registered in `main.py` and require Bearer auth.

**Tech Stack:** FastAPI, Pydantic v2, PyYAML, filelock, Vanilla JS ES modules, CSS custom properties

**Progress:** 0 / 14 tasks complete

---

## Clarification Notes (read before implementing)

**Morning prompts — removed field:** The existing `success` field ("What would make today feel successful?") is removed. Old vault entries simply will not display that line — no migration needed since vault files are updated in-place per section.

**Sleep score to mood math:** The user spec says "94 sleep score gives 8 morning mood (divide by ten and round down)." `floor(94/10) = 9`, not 8. The plan implements `math.floor(score / 10)` clamped to 1-10, which gives **9** for a score of 94. If the intent is 8, the formula becomes `math.floor(score / 10) - 1`, which breaks for scores below 10 (produces 0). Confirm with the user before shipping Task 9.

---

## File Map

| File | Action | Purpose |
|------|--------|---------|
| `backend/app/models.py` | Modify | Update `MorningEntry`; add `AppleHealthData` |
| `backend/app/routers/journal.py` | Modify | Update morning writer; add `GET /journal/consistency` |
| `backend/app/routers/quote.py` | Create | `GET /api/quote/{day}` |
| `backend/app/routers/health_data.py` | Create | `POST /api/health/apple`, `GET /api/health/apple/{day}` |
| `backend/app/services/quotes.py` | Create | Curated quote + challenge lists, date-seeded selection |
| `backend/app/services/vault.py` | Modify | Update `_daily_template` for new fields |
| `backend/app/main.py` | Modify | Register new routers |
| `frontend/journal-morning.html` | Modify | 3+3+energy+affirmation layout; quote banner |
| `frontend/journal-evening.html` | Modify | Quote banner at top |
| `frontend/js/api.js` | Modify | Add `getQuote` method |
| `frontend/js/journal.js` | Modify | New prefill logic; Apple Health seed; affirmation ghost placeholder |
| `frontend/calendar.html` | Create | Monthly consistency grid page |
| `frontend/js/calendar.js` | Create | Month nav, day grid render, completion colouring |
| `frontend/index.html` | Modify | Add "Calendar" to nav |
| `frontend/sw.js` | Modify | Add `calendar.html` to `APP_SHELL`, bump cache to `v3` |
| `docs/todos.md` | Create | Deferred items documented |

---

## Task 1: Update `MorningEntry` model + add `AppleHealthData`

**Files:**
- Modify: `backend/app/models.py:13-32`

- [ ] **Step 1: Replace the `MorningEntry` class (lines 13-32)**

```python
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
```

- [ ] **Step 2: Add `AppleHealthData` model after `EveningEntry`**

```python
class AppleHealthData(BaseModel):
    date: str          # YYYY-MM-DD
    sleep_hours: float | None = None
    sleep_score: int | None = None  # 0-100

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
```

- [ ] **Step 3: Verify syntax**

```bash
cd /home/backend/projects/my-life-os
python -c "
import sys; sys.path.insert(0, 'backend')
from app.models import MorningEntry, AppleHealthData
print('ok')
"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat(models): update MorningEntry (3x gratitude, 3x great-today, affirmation); add AppleHealthData"
```

---

## Task 2: Update `journal.py` morning route + add consistency endpoint

**Files:**
- Modify: `backend/app/routers/journal.py`

- [ ] **Step 1: Update the morning writer**

Replace the `journal_morning` function completely:

```python
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
```

- [ ] **Step 2: Add consistency endpoint**

Add these imports at the top of `journal.py` (after the existing imports):

```python
import calendar as cal_module
import re as _re
from datetime import date as _date
```

Append to the end of `journal.py`:

```python
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
                morning_done = fm.get("mood_morning") is not None
                evening_done = fm.get("mood_evening") is not None
            except Exception:
                pass
        days.append({
            "date": day_str,
            "day": day_num,
            "morning": morning_done,
            "evening": evening_done,
        })

    return {"month": month, "days": days}
```

- [ ] **Step 3: Smoke test (requires running server)**

```bash
curl -s "http://localhost:8000/journal/consistency?month=2026-04" \
  -H "Authorization: Bearer $API_KEY" | python -m json.tool | head -20
```

Expected: JSON `{"month": "2026-04", "days": [...]}` with 30 entries.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/journal.py
git commit -m "feat(journal): update morning section format; add GET /journal/consistency endpoint"
```

---

## Task 3: Update daily note template in `vault.py`

**Files:**
- Modify: `backend/app/services/vault.py:264-295`

- [ ] **Step 1: Replace `_daily_template` return string**

Find `_daily_template` (around line 264) and replace the triple-quoted return string:

```python
def _daily_template(key: str, created: str) -> str:
    return f"""---
date: {key}
created: {created}
sleep_hours: null
mood_morning: null
mood_evening: null
apple_sleep_hours: null
apple_sleep_score: null
tags: []
---

## Morning

**Grateful 1**:
**Grateful 2**:
**Grateful 3**:
**Great today 1**:
**Great today 2**:
**Great today 3**:
**Realistic work**:
**Affirmation**:

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
```

- [ ] **Step 2: Verify**

```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from app.services.vault import _daily_template
t = _daily_template('2026-04-01', '2026-04-01T00:00:00Z')
assert 'Grateful 1' in t
assert 'Great today 1' in t
assert 'Affirmation' in t
assert 'apple_sleep_hours' in t
print('ok')
"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/vault.py
git commit -m "feat(vault): update daily template with new morning fields and Apple Health frontmatter keys"
```

---

## Task 4: Create `quotes.py` service

**Files:**
- Create: `backend/app/services/quotes.py`

- [ ] **Step 1: Write the file**

```python
"""quotes.py — Deterministic daily quote and Monday weekly challenge selection."""
from __future__ import annotations

from datetime import date

QUOTES: list[dict[str, str]] = [
    {"text": "The secret of getting ahead is getting started.", "author": "Mark Twain"},
    {"text": "Do what you can, with what you have, where you are.", "author": "Theodore Roosevelt"},
    {"text": "It always seems impossible until it's done.", "author": "Nelson Mandela"},
    {"text": "Don't watch the clock; do what it does. Keep going.", "author": "Sam Levenson"},
    {"text": "The only way to do great work is to love what you do.", "author": "Steve Jobs"},
    {"text": "In the middle of every difficulty lies opportunity.", "author": "Albert Einstein"},
    {"text": "Success is not final, failure is not fatal: it is the courage to continue that counts.", "author": "Winston Churchill"},
    {"text": "Believe you can and you're halfway there.", "author": "Theodore Roosevelt"},
    {"text": "You miss 100% of the shots you don't take.", "author": "Wayne Gretzky"},
    {"text": "The future belongs to those who believe in the beauty of their dreams.", "author": "Eleanor Roosevelt"},
    {"text": "What you get by achieving your goals is not as important as what you become.", "author": "Zig Ziglar"},
    {"text": "Hardships often prepare ordinary people for an extraordinary destiny.", "author": "C.S. Lewis"},
    {"text": "It is during our darkest moments that we must focus to see the light.", "author": "Aristotle"},
    {"text": "The best time to plant a tree was 20 years ago. The second best time is now.", "author": "Chinese Proverb"},
    {"text": "An unexamined life is not worth living.", "author": "Socrates"},
    {"text": "Spread love everywhere you go. Let no one ever come to you without leaving happier.", "author": "Mother Teresa"},
    {"text": "Always remember that you are absolutely unique. Just like everyone else.", "author": "Margaret Mead"},
    {"text": "Don't judge each day by the harvest you reap but by the seeds that you plant.", "author": "Robert Louis Stevenson"},
    {"text": "The only impossible journey is the one you never begin.", "author": "Tony Robbins"},
    {"text": "In three words I can sum up everything I've learned about life: it goes on.", "author": "Robert Frost"},
    {"text": "Too many of us are not living our dreams because we are living our fears.", "author": "Les Brown"},
    {"text": "A person who never made a mistake never tried anything new.", "author": "Albert Einstein"},
    {"text": "You become what you believe.", "author": "Oprah Winfrey"},
    {"text": "I would rather die of passion than of boredom.", "author": "Vincent van Gogh"},
    {"text": "Do one thing every day that scares you.", "author": "Eleanor Roosevelt"},
    {"text": "Nothing is impossible; the word itself says 'I'm possible!'", "author": "Audrey Hepburn"},
    {"text": "The question isn't who is going to let me; it's who is going to stop me.", "author": "Ayn Rand"},
    {"text": "It's not whether you get knocked down, it's whether you get up.", "author": "Vince Lombardi"},
    {"text": "We generate fears while we sit. We overcome them by action.", "author": "Dr. Henry Link"},
    {"text": "Whether you think you can or think you can't, you're right.", "author": "Henry Ford"},
    {"text": "Security is mostly a superstition. Life is either a daring adventure or nothing.", "author": "Helen Keller"},
    {"text": "The only real mistake is the one from which we learn nothing.", "author": "Henry Ford"},
    {"text": "Never let the fear of striking out keep you from playing the game.", "author": "Babe Ruth"},
    {"text": "When you have a dream, you've got to grab it and never let go.", "author": "Carol Burnett"},
    {"text": "Darkness cannot drive out darkness; only light can do that.", "author": "Martin Luther King Jr."},
    {"text": "We must accept finite disappointment, but never lose infinite hope.", "author": "Martin Luther King Jr."},
    {"text": "The most common way people give up their power is by thinking they don't have any.", "author": "Alice Walker"},
    {"text": "You may be disappointed if you fail, but you are doomed if you don't try.", "author": "Beverly Sills"},
    {"text": "Remember that not getting what you want is sometimes a wonderful stroke of luck.", "author": "Dalai Lama"},
    {"text": "You can't use up creativity. The more you use, the more you have.", "author": "Maya Angelou"},
    {"text": "I have learned over the years that when one's mind is made up, this diminishes fear.", "author": "Rosa Parks"},
    {"text": "I alone cannot change the world, but I can cast a stone across the water to create many ripples.", "author": "Mother Teresa"},
    {"text": "When everything seems to be going against you, remember that the airplane takes off against the wind.", "author": "Henry Ford"},
    {"text": "Education is the most powerful weapon which you can use to change the world.", "author": "Nelson Mandela"},
    {"text": "Life is not measured by the number of breaths we take, but by the moments that take our breath away.", "author": "Maya Angelou"},
    {"text": "If you're offered a seat on a rocket ship, don't ask what seat! Just get on.", "author": "Sheryl Sandberg"},
    {"text": "How wonderful it is that nobody need wait a single moment before starting to improve the world.", "author": "Anne Frank"},
    {"text": "You can never plan the future by the past.", "author": "Edmund Burke"},
    {"text": "Live in the sunshine, swim the sea, drink the wild air.", "author": "Ralph Waldo Emerson"},
    {"text": "It is not what you do for your children, but what you have taught them to do for themselves.", "author": "Ann Landers"},
    {"text": "To handle yourself, use your head; to handle others, use your heart.", "author": "Eleanor Roosevelt"},
    {"text": "If you want to lift yourself up, lift up someone else.", "author": "Booker T. Washington"},
    {"text": "Limitations live only in our minds. But if we use our imaginations, our possibilities become limitless.", "author": "Jamie Paolinetti"},
    {"text": "First, have a definite, clear practical ideal — a goal, an objective.", "author": "Aristotle"},
    {"text": "A truly rich man is one whose children run into his arms when his hands are empty.", "author": "Unknown"},
    {"text": "The most wasted of all days is one without laughter.", "author": "E.E. Cummings"},
    {"text": "We must be the change we wish to see in the world.", "author": "Mahatma Gandhi"},
    {"text": "Strive not to be a success, but rather to be of value.", "author": "Albert Einstein"},
    {"text": "Two roads diverged in a wood, and I took the one less traveled by.", "author": "Robert Frost"},
    {"text": "I am not a product of my circumstances. I am a product of my decisions.", "author": "Stephen Covey"},
    {"text": "Every child is an artist. The problem is how to remain an artist once we grow up.", "author": "Pablo Picasso"},
]

WEEKLY_CHALLENGES: list[str] = [
    "Take a 10-minute walk outside every day this week.",
    "Put your phone away for the first hour after waking.",
    "Read for at least 15 minutes before bed each night.",
    "Say one genuine compliment out loud to someone each day.",
    "Take a complete break from social media for the whole week.",
    "Write down three things you are grateful for before bed each night.",
    "Drink 8 glasses of water every day this week.",
    "Say 'I love you' in the mirror every morning this week.",
    "Cook at least one meal from scratch every day.",
    "Spend 10 minutes tidying one area of your home each day.",
    "Reach out to one person you haven't spoken to in a while.",
    "Go to bed 30 minutes earlier than usual every night.",
    "Do 5 minutes of deep breathing or meditation each morning.",
    "Write a handwritten note to someone who matters to you.",
    "No caffeine after 2 PM this week — see how your sleep changes.",
    "Listen to a new album, podcast, or audiobook you have never tried.",
    "Take a photo of something beautiful each day this week.",
    "Eat at least one piece of fruit or vegetable at every meal.",
    "Journal for 5 minutes each evening about what went well.",
    "Set a specific 'stop work' time and honour it every day.",
    "Spend 20 minutes in nature every day, no phone allowed.",
    "Practice one random act of kindness per day.",
    "Unsubscribe from 5 email newsletters you never read.",
    "Go for a run or brisk walk before breakfast at least 3 times.",
    "Write down one goal for the next day the night before — every night.",
    "Have at least one full meal without any screens.",
]


def get_quote(day: date) -> dict:
    """
    Return the quote or challenge for a given date.
    Monday (weekday == 0) returns a weekly challenge.
    All other days return a rotating inspirational quote.
    Both are deterministic: same date always returns the same entry.
    """
    if day.weekday() == 0:  # Monday
        idx = (day.toordinal() // 7) % len(WEEKLY_CHALLENGES)
        return {"type": "challenge", "text": WEEKLY_CHALLENGES[idx], "author": ""}
    idx = day.toordinal() % len(QUOTES)
    q = QUOTES[idx]
    return {"type": "quote", "text": q["text"], "author": q.get("author", "")}
```

- [ ] **Step 2: Verify**

```bash
python -c "
import sys; sys.path.insert(0, 'backend')
from datetime import date
from app.services.quotes import get_quote
q = get_quote(date(2026, 4, 7))   # Tuesday
assert q['type'] == 'quote', q
c = get_quote(date(2026, 4, 6))   # Monday
assert c['type'] == 'challenge', c
print('ok')
"
```

Expected: `ok`

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/quotes.py
git commit -m "feat(quotes): add curated daily quote and weekly challenge service with date-seeded selection"
```

---

## Task 5: Create quote router and register it

**Files:**
- Create: `backend/app/routers/quote.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create the router**

```python
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
```

- [ ] **Step 2: Register in `main.py`**

Update the router import line (near line 8) to include `quote`:

```python
from app.routers import ai, calendar, daily, journal, milestones, planning, push, quote, tasks
```

Add to the authenticated routers block (after the existing `include_router` calls):

```python
app.include_router(quote.router, dependencies=_auth)
```

- [ ] **Step 3: Smoke test**

```bash
# Monday — should return challenge
curl -s "http://localhost:8000/quote/2026-04-06" \
  -H "Authorization: Bearer $API_KEY" | python -m json.tool

# Tuesday — should return quote
curl -s "http://localhost:8000/quote/2026-04-07" \
  -H "Authorization: Bearer $API_KEY" | python -m json.tool
```

Expected: JSON with `"type": "challenge"` and `"type": "quote"` respectively.

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/quote.py backend/app/main.py
git commit -m "feat(quote): add GET /quote/{day} endpoint returning daily quote or Monday weekly challenge"
```

---

## Task 6: Add `getQuote` to `api.js`

**Files:**
- Modify: `frontend/js/api.js`

- [ ] **Step 1: Add method to the api object**

Inside the exported `api` object (before the closing `}`), add:

```javascript
getQuote(day) {
  return this.request("GET", `/quote/${day}`);
},
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/api.js
git commit -m "feat(api): add getQuote(day) method"
```

---

## Task 7: Add quote banner to morning and evening pages

**Files:**
- Modify: `frontend/journal-morning.html`
- Modify: `frontend/journal-evening.html`

The quote banner is a card with a left accent border, hidden by default (`display:none`), shown by `journal.js` once the API responds.

- [ ] **Step 1: Replace `journal-morning.html` entirely**

The new file completely replaces the old form structure with: quote banner, Sleep & Energy card, Grateful x3 card, Great Today x3 card, Energy/Realistic-work card, Affirmation card (last).

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#1a1a2e">
  <link rel="manifest" href="/manifest.json">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="apple-touch-icon" href="/icon-192.png">
  <title>Life OS — Morning</title>
  <link rel="stylesheet" href="/css/style.css">
</head>
<body>

<header>
  <a href="/" class="btn btn-secondary" style="padding:8px 14px;font-size:0.875rem">Back</a>
  <h1>Morning Check-in</h1>
  <span class="journal-date" style="font-size:0.8rem;color:var(--text-dim)"></span>
</header>

<div class="container">

  <div class="card">
    <p style="font-size:0.875rem;color:var(--text-dim);margin-bottom:4px">
      Take 5 minutes to set your intentions for the day.
    </p>
    <p class="journal-date" style="font-size:0.875rem;color:var(--accent2)"></p>
  </div>

  <div class="card" id="quote-banner" style="border-left:3px solid var(--accent);display:none">
    <p id="quote-type" style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;color:var(--text-dim);margin-bottom:6px"></p>
    <p id="quote-text" style="font-size:0.95rem;line-height:1.5;font-style:italic"></p>
    <p id="quote-author" style="font-size:0.8rem;color:var(--text-dim);margin-top:6px"></p>
  </div>

  <form id="journal-form" data-type="morning">

    <div class="card">
      <h2>Sleep &amp; Energy</h2>
      <div class="field-row">
        <div class="field">
          <label for="sleep-hours">Hours of sleep</label>
          <input type="number" id="sleep-hours" inputmode="decimal" min="0" max="24" step="0.5" placeholder="7.5">
        </div>
        <div class="field">
          <label for="mood-score">Morning mood: <strong id="mood-label">5</strong>/10</label>
          <input type="range" id="mood-score" min="1" max="10" value="5" step="1">
          <div class="range-labels"><span>1 — rough</span><span>10 — great</span></div>
        </div>
      </div>
    </div>

    <div class="card">
      <h2>I am grateful for&hellip;</h2>
      <div class="field">
        <input type="text" id="gratitude-1" placeholder="1." required>
      </div>
      <div class="field">
        <input type="text" id="gratitude-2" placeholder="2." required>
      </div>
      <div class="field">
        <input type="text" id="gratitude-3" placeholder="3." required>
      </div>
    </div>

    <div class="card">
      <h2>What would make today great?</h2>
      <div class="field">
        <input type="text" id="great-1" placeholder="1." required>
      </div>
      <div class="field">
        <input type="text" id="great-2" placeholder="2." required>
      </div>
      <div class="field">
        <input type="text" id="great-3" placeholder="3." required>
      </div>
    </div>

    <div class="card">
      <h2>Given my energy&hellip;</h2>
      <div class="field">
        <label for="realistic-work">What kind of work is realistic today?</label>
        <textarea id="realistic-work" rows="3" placeholder="Deep focus for 90 min then lighter tasks, or mostly admin today..." required></textarea>
      </div>
    </div>

    <div class="card">
      <h2>Daily Affirmations</h2>
      <div class="field">
        <textarea id="affirmation" rows="5" placeholder="Type your affirmations for today..." required></textarea>
        <p style="font-size:0.75rem;color:var(--text-dim);margin-top:4px">
          Placeholder shows yesterday's affirmations. Type yours fresh each day.
        </p>
      </div>
    </div>

    <button type="submit" class="btn btn-primary btn-full" style="margin-bottom:24px">
      Save morning entry
    </button>

  </form>
</div>

<div id="toast"></div>

<script type="module">
  import "/js/journal.js";
  import { showSetupModal } from "/js/utils.js";
  if (!localStorage.getItem("life_os_api_key")) showSetupModal();
</script>

<div id="setup-modal" class="hidden">
  <div class="modal-box">
    <h2>API key required</h2>
    <p>Go back to the <a href="/" style="color:var(--accent)">home page</a> to set up your API key.</p>
  </div>
</div>

</body>
</html>
```

- [ ] **Step 2: Insert quote banner into `journal-evening.html`**

Read the current `journal-evening.html`. After the introductory card (the card containing "Reflect on your day...") and before the `<form>` tag, insert:

```html
  <div class="card" id="quote-banner" style="border-left:3px solid var(--accent);display:none">
    <p id="quote-type" style="font-size:0.7rem;text-transform:uppercase;letter-spacing:1px;color:var(--text-dim);margin-bottom:6px"></p>
    <p id="quote-text" style="font-size:0.95rem;line-height:1.5;font-style:italic"></p>
    <p id="quote-author" style="font-size:0.8rem;color:var(--text-dim);margin-top:6px"></p>
  </div>
```

- [ ] **Step 3: Commit**

```bash
git add frontend/journal-morning.html frontend/journal-evening.html
git commit -m "feat(ui): redesign morning prompts; add quote banner to morning and evening pages"
```

---

## Task 8: Update `journal.js` — new morning logic, ghost placeholder, Apple Health seed, quote

**Files:**
- Modify: `frontend/js/journal.js`

- [ ] **Step 1: Replace the entire file**

```javascript
/**
 * journal.js — Morning and evening journal form logic.
 *
 * Reads ?date= query param (falls back to today).
 * Submits to /api/journal/{date}/morning or /api/journal/{date}/evening.
 */

import { api } from "./api.js";
import { showToast, getToday } from "./utils.js";

const params = new URLSearchParams(location.search);
const targetDate = params.get("date") || getToday();

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".journal-date").forEach(el => {
    el.textContent = new Date(targetDate + "T12:00:00").toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric",
    });
  });

  const form = document.getElementById("journal-form");
  if (!form) return;

  const type = form.dataset.type;

  loadQuote(targetDate);

  if (type === "morning") initMorning(form);
  else if (type === "evening") initEvening(form);
});

// ---------------------------------------------------------------------------
// Quote banner — shared by morning and evening
// ---------------------------------------------------------------------------

function loadQuote(day) {
  api.getQuote(day).then(q => {
    const banner = document.getElementById("quote-banner");
    if (!banner) return;
    const typeEl = document.getElementById("quote-type");
    const textEl = document.getElementById("quote-text");
    const authorEl = document.getElementById("quote-author");
    typeEl.textContent = q.type === "challenge" ? "Weekly Challenge" : "Today's Quote";
    textEl.textContent = q.text;
    authorEl.textContent = q.author ? `\u2014 ${q.author}` : "";
    banner.style.display = "";
  }).catch(() => {});
}

// ---------------------------------------------------------------------------
// Morning
// ---------------------------------------------------------------------------

function initMorning(form) {
  const moodInput = document.getElementById("mood-score");
  const moodLabel = document.getElementById("mood-label");
  if (moodInput && moodLabel) {
    moodInput.addEventListener("input", () => { moodLabel.textContent = moodInput.value; });
  }

  // Prefill from today's saved note
  api.getDaily(targetDate).then(note => {
    const fm = note.frontmatter;

    // Sleep hours: prefer manual entry, fall back to Apple Health
    if (fm.sleep_hours != null) {
      document.getElementById("sleep-hours").value = fm.sleep_hours;
    } else if (fm.apple_sleep_hours != null) {
      document.getElementById("sleep-hours").value = fm.apple_sleep_hours;
    }

    // Mood: prefer saved mood, seed from Apple Health sleep score if not yet set
    if (fm.mood_morning != null) {
      if (moodInput) moodInput.value = fm.mood_morning;
      if (moodLabel) moodLabel.textContent = fm.mood_morning;
    } else if (fm.apple_sleep_score != null) {
      const seeded = Math.min(10, Math.max(1, Math.floor(fm.apple_sleep_score / 10)));
      if (moodInput) moodInput.value = seeded;
      if (moodLabel) moodLabel.textContent = seeded;
    }

    // Text field prefill from saved Morning section
    const body = note.content;
    const g1 = body.match(/\*\*Grateful 1\*\*:\s*(.+)/);
    const g2 = body.match(/\*\*Grateful 2\*\*:\s*(.+)/);
    const g3 = body.match(/\*\*Grateful 3\*\*:\s*(.+)/);
    const gr1 = body.match(/\*\*Great today 1\*\*:\s*(.+)/);
    const gr2 = body.match(/\*\*Great today 2\*\*:\s*(.+)/);
    const gr3 = body.match(/\*\*Great today 3\*\*:\s*(.+)/);
    const work = body.match(/\*\*Realistic work\*\*:\s*(.+)/);
    const aff = body.match(/\*\*Affirmation\*\*:\s*([\s\S]+?)(?=\n\*\*|\n##|$)/);

    if (g1) document.getElementById("gratitude-1").value = g1[1].trim();
    if (g2) document.getElementById("gratitude-2").value = g2[1].trim();
    if (g3) document.getElementById("gratitude-3").value = g3[1].trim();
    if (gr1) document.getElementById("great-1").value = gr1[1].trim();
    if (gr2) document.getElementById("great-2").value = gr2[1].trim();
    if (gr3) document.getElementById("great-3").value = gr3[1].trim();
    if (work) document.getElementById("realistic-work").value = work[1].trim();
    if (aff) document.getElementById("affirmation").value = aff[1].trim();
  }).catch(() => {});

  // Ghost placeholder: previous day's affirmation
  const prev = new Date(targetDate + "T12:00:00");
  prev.setDate(prev.getDate() - 1);
  const prevStr = prev.toISOString().slice(0, 10);
  api.getDaily(prevStr).then(prevNote => {
    const prevAff = prevNote.content.match(/\*\*Affirmation\*\*:\s*([\s\S]+?)(?=\n\*\*|\n##|$)/);
    if (prevAff) {
      const el = document.getElementById("affirmation");
      if (el && !el.value) el.placeholder = prevAff[1].trim();
    }
  }).catch(() => {});

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving\u2026";

    const entry = {
      gratitude_1: document.getElementById("gratitude-1").value.trim(),
      gratitude_2: document.getElementById("gratitude-2").value.trim(),
      gratitude_3: document.getElementById("gratitude-3").value.trim(),
      great_1: document.getElementById("great-1").value.trim(),
      great_2: document.getElementById("great-2").value.trim(),
      great_3: document.getElementById("great-3").value.trim(),
      realistic_work: document.getElementById("realistic-work").value.trim(),
      affirmation: document.getElementById("affirmation").value.trim(),
      mood_score: parseInt(moodInput?.value) || null,
      sleep_hours: parseFloat(document.getElementById("sleep-hours")?.value) || null,
    };

    const required = ["gratitude_1","gratitude_2","gratitude_3","great_1","great_2","great_3","realistic_work","affirmation"];
    if (required.some(k => !entry[k])) {
      showToast("Please fill in all fields", "error");
      btn.disabled = false;
      btn.textContent = "Save morning entry";
      return;
    }

    try {
      await api.journalMorning(targetDate, entry);
      showToast("Morning entry saved!", "ok");
      setTimeout(() => { location.href = "/"; }, 1200);
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
      btn.disabled = false;
      btn.textContent = "Save morning entry";
    }
  });
}

// ---------------------------------------------------------------------------
// Evening
// ---------------------------------------------------------------------------

function initEvening(form) {
  const moodInput = document.getElementById("mood-score");
  const moodLabel = document.getElementById("mood-label");
  if (moodInput && moodLabel) {
    moodInput.addEventListener("input", () => { moodLabel.textContent = moodInput.value; });
  }

  api.getDaily(targetDate).then(note => {
    const fm = note.frontmatter;
    if (fm.mood_evening != null) {
      if (moodInput) moodInput.value = fm.mood_evening;
      if (moodLabel) moodLabel.textContent = fm.mood_evening;
    }
    const body = note.content;
    const changeMatch = body.match(/\*\*What I'd change\*\*:\s*(.+)/);
    const feelingMatch = body.match(/\*\*Feeling\*\*:\s*(.+)/);
    if (changeMatch) document.getElementById("change").value = changeMatch[1].trim();
    if (feelingMatch) document.getElementById("feeling").value = feelingMatch[1].trim();
    const winsSection = body.match(/\*\*Wins\*\*:\n((?:-.+\n?){0,3})/);
    if (winsSection) {
      const lines = winsSection[1].trim().split("\n").map(l => l.replace(/^-\s*/, "").trim());
      lines.forEach((text, i) => {
        const el = document.getElementById(`win-${i + 1}`);
        if (el && text) el.value = text;
      });
    }
  }).catch(() => {});

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving\u2026";

    const wins = [
      document.getElementById("win-1")?.value.trim() || "",
      document.getElementById("win-2")?.value.trim() || "",
      document.getElementById("win-3")?.value.trim() || "",
    ];

    if (wins.some(w => !w)) {
      showToast("Please enter all three wins (even small ones!)", "error");
      btn.disabled = false;
      btn.textContent = "Save evening entry";
      return;
    }

    const entry = {
      wins,
      change: document.getElementById("change").value.trim(),
      feeling: document.getElementById("feeling").value.trim(),
      mood_score: parseInt(moodInput?.value) || null,
    };

    if (!entry.change || !entry.feeling) {
      showToast("Please fill in all fields", "error");
      btn.disabled = false;
      btn.textContent = "Save evening entry";
      return;
    }

    try {
      await api.journalEvening(targetDate, entry);
      showToast("Evening entry saved! Great work today.", "ok");
      setTimeout(() => { location.href = "/"; }, 1200);
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
      btn.disabled = false;
      btn.textContent = "Save evening entry";
    }
  });
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/journal.js
git commit -m "feat(journal): new morning form fields, affirmation ghost placeholder, Apple Health seed, quote loading"
```

---

## Task 9: Create Apple Health router

**Files:**
- Create: `backend/app/routers/health_data.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Create `health_data.py`**

```python
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
    Confirm formula with user if 8 was expected (use floor(score/10) - 1 instead).
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
```

- [ ] **Step 2: Register in `main.py`**

Update the router import line to include `health_data`:

```python
from app.routers import ai, calendar, daily, health_data, journal, milestones, planning, push, quote, tasks
```

Add to the authenticated routers block:

```python
app.include_router(health_data.router, dependencies=_auth)
```

- [ ] **Step 3: Smoke test**

```bash
curl -s -X POST "http://localhost:8000/health/apple" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"date":"2026-04-01","sleep_hours":7.5,"sleep_score":94}' | python -m json.tool
```

Expected: `{"stored": true, "date": "2026-04-01", "seeded_mood": 9}`

```bash
curl -s "http://localhost:8000/health/apple/2026-04-01" \
  -H "Authorization: Bearer $API_KEY" | python -m json.tool
```

Expected: `{"date": "2026-04-01", "apple_sleep_hours": 7.5, "apple_sleep_score": 94}`

- [ ] **Step 4: Commit**

```bash
git add backend/app/routers/health_data.py backend/app/main.py
git commit -m "feat(health): POST /health/apple stores Apple Health sleep data; includes iOS Shortcut setup docs"
```

---

## Task 10: Create `calendar.html`

**Files:**
- Create: `frontend/calendar.html`

- [ ] **Step 1: Write the page**

The CSS uses `::before` / `::after` pseudo-elements for half-fill effects. No JS manipulates styles directly — completion state is encoded as CSS classes (`morning`, `evening`, `both`) set by `calendar.js`.

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#1a1a2e">
  <link rel="manifest" href="/manifest.json">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <link rel="apple-touch-icon" href="/icon-192.png">
  <title>Life OS &mdash; Calendar</title>
  <link rel="stylesheet" href="/css/style.css">
  <style>
    .cal-nav {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 16px;
    }
    .cal-nav h2 { font-size: 1.1rem; font-weight: 600; }
    .cal-grid {
      display: grid;
      grid-template-columns: repeat(7, 1fr);
      gap: 4px;
      margin-bottom: 20px;
    }
    .cal-day-label {
      text-align: center;
      font-size: 0.7rem;
      color: var(--text-dim);
      padding: 4px 0;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
    .cal-day {
      position: relative;
      aspect-ratio: 1;
      border-radius: var(--radius-sm);
      background: var(--surface);
      border: 1px solid var(--border);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 0.8rem;
      font-weight: 500;
      overflow: hidden;
    }
    .cal-day.empty { background: transparent; border-color: transparent; }
    .cal-day.future { opacity: 0.35; }
    /* Morning done: bottom half filled with accent */
    .cal-day.morning::after {
      content: "";
      position: absolute;
      bottom: 0; left: 0; right: 0;
      height: 50%;
      background: var(--accent);
      opacity: 0.6;
      border-radius: 0 0 var(--radius-sm) var(--radius-sm);
    }
    /* Evening done: top half filled with accent2 */
    .cal-day.evening::before {
      content: "";
      position: absolute;
      top: 0; left: 0; right: 0;
      height: 50%;
      background: var(--accent2);
      opacity: 0.6;
      border-radius: var(--radius-sm) var(--radius-sm) 0 0;
    }
    /* Both done: full solid fill */
    .cal-day.both { background: var(--accent); border-color: var(--accent); color: #fff; }
    .cal-day.both::before, .cal-day.both::after { display: none; }
    /* Keep day number above the pseudo-element fills */
    .cal-day span { position: relative; z-index: 1; }
    .cal-legend {
      display: flex; gap: 16px; flex-wrap: wrap;
      font-size: 0.8rem; color: var(--text-dim); margin-bottom: 16px;
    }
    .cal-legend-item { display: flex; align-items: center; gap: 6px; }
    .cal-legend-swatch { width: 16px; height: 16px; border-radius: 4px; border: 1px solid var(--border); }
    .swatch-morning { background: linear-gradient(to top, var(--accent) 50%, var(--surface) 50%); }
    .swatch-evening { background: linear-gradient(to bottom, var(--accent2) 50%, var(--surface) 50%); }
    .swatch-both    { background: var(--accent); }
    .swatch-none    { background: var(--surface); }
  </style>
</head>
<body>

<header>
  <a href="/" class="btn btn-secondary" style="padding:8px 14px;font-size:0.875rem">Back</a>
  <h1>Check-in Calendar</h1>
  <span></span>
</header>

<div class="container">

  <div class="cal-nav">
    <button id="prev-month" class="btn btn-secondary">&lsaquo;</button>
    <h2 id="month-label"></h2>
    <button id="next-month" class="btn btn-secondary">&rsaquo;</button>
  </div>

  <div class="cal-legend">
    <div class="cal-legend-item">
      <div class="cal-legend-swatch swatch-morning"></div><span>Morning</span>
    </div>
    <div class="cal-legend-item">
      <div class="cal-legend-swatch swatch-evening"></div><span>Evening</span>
    </div>
    <div class="cal-legend-item">
      <div class="cal-legend-swatch swatch-both"></div><span>Both</span>
    </div>
    <div class="cal-legend-item">
      <div class="cal-legend-swatch swatch-none"></div><span>Incomplete</span>
    </div>
  </div>

  <div class="cal-grid" id="cal-grid"></div>

  <p id="cal-summary" style="font-size:0.875rem;color:var(--text-dim);text-align:center"></p>

</div>

<div id="toast"></div>

<script type="module">
  import "/js/calendar.js";
  import { showSetupModal } from "/js/utils.js";
  if (!localStorage.getItem("life_os_api_key")) showSetupModal();
</script>

<div id="setup-modal" class="hidden">
  <div class="modal-box">
    <h2>API key required</h2>
    <p>Go back to the <a href="/" style="color:var(--accent)">home page</a> to set up your API key.</p>
  </div>
</div>

</body>
</html>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/calendar.html
git commit -m "feat(calendar): add calendar.html consistency grid page with CSS half-fill day cells"
```

---

## Task 11: Create `calendar.js`

**Files:**
- Create: `frontend/js/calendar.js`

- [ ] **Step 1: Write the script**

Note: uses `replaceChildren()` to clear the grid (safe DOM method, no `innerHTML` manipulation of user content).

```javascript
/**
 * calendar.js — Monthly check-in consistency grid.
 *
 * Each day cell gets a CSS class based on completion:
 *   .morning  — bottom half filled (purple)
 *   .evening  — top half filled (teal)
 *   .both     — full fill (purple)
 *   (none)    — incomplete
 */

import { api } from "./api.js";
import { showToast } from "./utils.js";

const DAY_LABELS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];

const now = new Date();
let viewYear  = now.getFullYear();
let viewMonth = now.getMonth() + 1; // 1-12

document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("prev-month").addEventListener("click", () => {
    viewMonth--;
    if (viewMonth < 1) { viewMonth = 12; viewYear--; }
    renderMonth();
  });
  document.getElementById("next-month").addEventListener("click", () => {
    viewMonth++;
    if (viewMonth > 12) { viewMonth = 1; viewYear++; }
    renderMonth();
  });
  renderMonth();
});

async function renderMonth() {
  const grid    = document.getElementById("cal-grid");
  const label   = document.getElementById("month-label");
  const summary = document.getElementById("cal-summary");

  const monthStr = `${viewYear}-${String(viewMonth).padStart(2, "0")}`;
  label.textContent = new Date(viewYear, viewMonth - 1, 1).toLocaleDateString(undefined, {
    month: "long", year: "numeric",
  });

  // Clear grid using safe DOM method
  grid.replaceChildren();

  // Day-of-week header row
  DAY_LABELS.forEach(d => {
    const el = document.createElement("div");
    el.className = "cal-day-label";
    el.textContent = d;
    grid.appendChild(el);
  });

  let days = [];
  try {
    const data = await api.request("GET", `/journal/consistency?month=${monthStr}`);
    days = data.days;
  } catch (_err) {
    showToast(`Could not load ${monthStr}`, "error");
    return;
  }

  // Blank padding cells before the 1st of the month
  const firstDow = new Date(viewYear, viewMonth - 1, 1).getDay(); // 0=Sun
  for (let i = 0; i < firstDow; i++) {
    const el = document.createElement("div");
    el.className = "cal-day empty";
    grid.appendChild(el);
  }

  const todayStr = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}-${String(now.getDate()).padStart(2,"0")}`;

  let morningOnly = 0, eveningOnly = 0, bothCount = 0;

  days.forEach(({ date, day, morning, evening }) => {
    const el   = document.createElement("div");
    const span = document.createElement("span");
    span.textContent = String(day);
    el.appendChild(span);
    el.className = "cal-day";

    if (date > todayStr) {
      el.classList.add("future");
    } else if (morning && evening) {
      el.classList.add("both");
      bothCount++;
    } else if (morning) {
      el.classList.add("morning");
      morningOnly++;
    } else if (evening) {
      el.classList.add("evening");
      eveningOnly++;
    }

    grid.appendChild(el);
  });

  const pastDays = days.filter(d => d.date <= todayStr).length;
  const missed   = pastDays - bothCount - morningOnly - eveningOnly;
  if (pastDays > 0) {
    summary.textContent =
      `${bothCount} full \u00b7 ${morningOnly} morning only \u00b7 ${eveningOnly} evening only \u00b7 ${missed} missed`;
  } else {
    summary.textContent = "No days yet this month.";
  }
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/js/calendar.js
git commit -m "feat(calendar): add calendar.js month grid with morning/evening completion colouring"
```

---

## Task 12: Add Calendar to nav + update service worker

**Files:**
- Modify: `frontend/index.html`
- Modify: `frontend/sw.js`

- [ ] **Step 1: Add Calendar link in `index.html` nav**

Find the `<nav>` block and add the Calendar link second (after Today):

```html
<nav>
  <a href="/" class="active">Today</a>
  <a href="/calendar.html">Calendar</a>
  <a href="/milestones.html">Milestones</a>
  <a href="/daily.html">Editor</a>
  <a href="/planning.html?horizon=weekly">Weekly</a>
  <a href="/planning.html?horizon=monthly">Monthly</a>
  <a href="/planning.html?horizon=quarterly">Quarterly</a>
  <a href="/planning.html?horizon=yearly">Yearly</a>
</nav>
```

- [ ] **Step 2: Update `sw.js`**

1. Find the `CACHE_VERSION` or cache name string. It is currently `'life-os-v2'` or similar. Change to `'life-os-v3'`.
2. Find the `APP_SHELL` array and add two entries:
   - `"/calendar.html"`
   - `"/js/calendar.js"`

- [ ] **Step 3: Commit**

```bash
git add frontend/index.html frontend/sw.js
git commit -m "feat(nav): add Calendar tab; bump SW cache to v3 with calendar.html and calendar.js"
```

---

## Task 13: Document deferred TODOs

**Files:**
- Create: `docs/todos.md`

- [ ] **Step 1: Write the file**

```markdown
# Life OS — Deferred TODOs

Items identified but not yet implemented.

---

## iOS Push Notifications Not Working

**Status:** Known issue, investigation pending.

Push notifications may not fire on iOS. Things to check:
- The PWA must be installed to the Home Screen (not just open in Safari) for Web Push to work on iOS.
- iOS 16.4+ is required for Web Push support in installed PWAs.
- Check `config/push_subscriptions.json` — confirm a subscription exists after subscribing on iOS.
- Safari on iOS may silently deny `Notification.requestPermission()`. Open Safari Web Inspector (Settings > Safari > Advanced > Web Inspector) and check the console on device.
- Add a `console.log` inside the `push` event listener in `frontend/sw.js` and verify it fires when a push is triggered manually from the backend.

Files to investigate:
- `frontend/sw.js` — push event handler
- `frontend/js/push.js` — subscription flow
- `backend/app/services/push_service.py` — push delivery and 410 cleanup

---

## Claude Code CLI Through Container

**Status:** Deferred. Use Mistral API instead (`AI_PROVIDER=mistral`).

The `claude-code` AI provider spawns the host's `claude` CLI as a subprocess. Inside Docker this requires mounting the binary, matching user credentials, and dealing with auth token paths — all fragile. No value over the Mistral API path for daily use.

---

## OpenAI-Compatible AI Provider

**Status:** Not yet implemented.

A generic `openai-compat` provider would allow any model with an OpenAI-format chat completions endpoint (Ollama, OpenRouter, self-hosted Llama, etc.).

Planned env vars:
- `AI_PROVIDER=openai-compat`
- `OPENAI_COMPAT_BASE_URL=http://localhost:11434/v1`
- `OPENAI_COMPAT_API_KEY=ollama`
- `OPENAI_COMPAT_MODEL=llama3.2`

Files to modify:
- `backend/app/config.py` — add the three new vars
- `backend/app/services/ai_service.py` — add `openai-compat` branch using `httpx` to POST to `{base_url}/chat/completions`
- `backend/.env.example` — document the vars
- `README.md` — update the AI Suggestions section
```

- [ ] **Step 2: Commit**

```bash
git add docs/todos.md
git commit -m "docs: add deferred TODOs (iOS push, Claude CLI in container, OpenAI-compat provider)"
```

---

## Task 14: Update README

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Add new bullet points to the Features section**

Add after the existing feature bullets:

```markdown
- **Redesigned morning journal** — three gratitude entries, three "what would make today great?" entries, an energy/realistic-work assessment, and a daily affirmations block; yesterday's affirmations appear as a ghost placeholder so you rewrite them fresh each day
- **Daily quote and weekly challenge** — an inspiring quote is shown at the top of both morning and evening check-ins, changing daily; Mondays show a short weekly challenge instead; same content appears on both pages since the quote is date-seeded
- **Calendar consistency view** — month grid where each day square fills based on check-in completion: bottom half for morning, top half for evening, full fill when both are done; navigable by month from the Calendar nav tab
- **Apple Health sleep seeding** — optional iOS Shortcut posts overnight sleep data to the app; the morning journal pre-fills the sleep hours field and seeds the mood slider from the sleep score
```

- [ ] **Step 2: Add Apple Health section**

After the Google Calendar Setup section, add:

```markdown
## Apple Health Integration (Optional)

Create an iOS Shortcut to automatically send last night's sleep data to Life OS:

1. Open the **Shortcuts** app.
2. Create a new Shortcut with:
   - **Get Health Samples** (Sleep Analysis, sum, last night)
   - **Get Health Samples** (Sleep Score, average, last night — if available on your device)
   - **Get Contents of URL**
     - URL: `https://lifeos.yourdomain.com/api/health/apple`
     - Method: POST
     - Headers: `Authorization: Bearer <your-api-key>`
     - Body (JSON): `{"date":"<current-date>","sleep_hours":<hours>,"sleep_score":<score>}`
3. Add the shortcut to a **Personal Automation** set to run at your usual wake time.

The morning journal reads the stored values and pre-fills sleep hours and mood (sleep score divided by 10, rounded down, clamped 1–10). You can still override both before saving.
```

- [ ] **Step 3: Commit and push**

```bash
git add README.md
git commit -m "docs: update README with new features and Apple Health setup instructions"
git push origin main
```

---

## Running Progress

| # | Task | Status |
|---|------|--------|
| 1 | Update MorningEntry model + add AppleHealthData | ☐ |
| 2 | Update journal.py morning writer + consistency endpoint | ☐ |
| 3 | Update daily note template in vault.py | ☐ |
| 4 | Create quotes.py service | ☐ |
| 5 | Create quote router + register in main.py | ☐ |
| 6 | Add getQuote to api.js | ☐ |
| 7 | Add quote banner to morning + evening pages | ☐ |
| 8 | Update journal.js (new fields, ghost placeholder, Apple seed, quote) | ☐ |
| 9 | Create Apple Health router + register in main.py | ☐ |
| 10 | Create calendar.html | ☐ |
| 11 | Create calendar.js | ☐ |
| 12 | Add Calendar to nav + update sw.js | ☐ |
| 13 | Document deferred TODO items | ☐ |
| 14 | Update README | ☐ |
