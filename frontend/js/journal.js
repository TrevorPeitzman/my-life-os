/**
 * journal.js — Morning and evening journal form logic.
 *
 * Reads ?date= query param (falls back to today).
 * Submits to /api/journal/{date}/morning or /api/journal/{date}/evening.
 */

import { api } from "./api.js";
import { showToast, getToday, escHtml } from "./utils.js";

const params = new URLSearchParams(location.search);
const targetDate = params.get("date") || getToday();

document.addEventListener("DOMContentLoaded", () => {
  // Display the target date
  document.querySelectorAll(".journal-date").forEach(el => {
    el.textContent = new Date(targetDate + "T12:00:00").toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric",
    });
  });

  const form = document.getElementById("journal-form");
  if (!form) return;

  const type = form.dataset.type; // "morning" or "evening"

  if (type === "morning") initMorning(form);
  else if (type === "evening") initEvening(form);
});

// ---------------------------------------------------------------------------
// Morning
// ---------------------------------------------------------------------------

function initMorning(form) {
  // Wire up mood slider label
  const moodInput = document.getElementById("mood-score");
  const moodLabel = document.getElementById("mood-label");
  if (moodInput && moodLabel) {
    moodInput.addEventListener("input", () => {
      moodLabel.textContent = moodInput.value;
    });
  }

  // Prefill from existing note if present
  api.getDaily(targetDate).then(note => {
    const fm = note.frontmatter;
    if (fm.sleep_hours) document.getElementById("sleep-hours").value = fm.sleep_hours;
    if (fm.mood_morning) {
      if (moodInput) moodInput.value = fm.mood_morning;
      if (moodLabel) moodLabel.textContent = fm.mood_morning;
    }
    // Try to prefill text fields from note content
    const body = note.content;
    const successMatch = body.match(/\*\*Success metric\*\*:\s*(.+)/);
    const gratitudeMatch = body.match(/\*\*Gratitude\*\*:\s*(.+)/);
    const workMatch = body.match(/\*\*Realistic work\*\*:\s*(.+)/);
    if (successMatch) document.getElementById("success").value = successMatch[1].trim();
    if (gratitudeMatch) document.getElementById("gratitude").value = gratitudeMatch[1].trim();
    if (workMatch) document.getElementById("realistic-work").value = workMatch[1].trim();
  }).catch(() => {}); // Non-fatal

  form.addEventListener("submit", async e => {
    e.preventDefault();
    const btn = form.querySelector("button[type=submit]");
    btn.disabled = true;
    btn.textContent = "Saving…";

    const entry = {
      success: document.getElementById("success").value.trim(),
      gratitude: document.getElementById("gratitude").value.trim(),
      realistic_work: document.getElementById("realistic-work").value.trim(),
      mood_score: parseInt(document.getElementById("mood-score")?.value) || null,
      sleep_hours: parseFloat(document.getElementById("sleep-hours")?.value) || null,
    };

    if (!entry.success || !entry.gratitude || !entry.realistic_work) {
      showToast("Please fill in all three prompts", "error");
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
    moodInput.addEventListener("input", () => {
      moodLabel.textContent = moodInput.value;
    });
  }

  // Prefill from existing note
  api.getDaily(targetDate).then(note => {
    const fm = note.frontmatter;
    if (fm.mood_evening) {
      if (moodInput) moodInput.value = fm.mood_evening;
      if (moodLabel) moodLabel.textContent = fm.mood_evening;
    }
    const body = note.content;
    const changeMatch = body.match(/\*\*What I'd change\*\*:\s*(.+)/);
    const feelingMatch = body.match(/\*\*Feeling\*\*:\s*(.+)/);
    if (changeMatch) document.getElementById("change").value = changeMatch[1].trim();
    if (feelingMatch) document.getElementById("feeling").value = feelingMatch[1].trim();
    // Try to prefill wins
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
    btn.textContent = "Saving…";

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
      mood_score: parseInt(document.getElementById("mood-score")?.value) || null,
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
