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
