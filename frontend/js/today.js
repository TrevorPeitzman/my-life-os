/**
 * today.js — Today view logic.
 * Fetches today's daily note, renders tasks and time blocks,
 * shows quick-links to morning/evening journal based on time of day.
 */

import { api, ApiError } from "./api.js";
import { showToast } from "./utils.js";

const today = api.getToday();

document.addEventListener("DOMContentLoaded", async () => {
  document.getElementById("date-display").textContent = formatDate(today);
  document.getElementById("morning-link").href = `/journal-morning.html?date=${today}`;
  document.getElementById("evening-link").href = `/journal-evening.html?date=${today}`;

  // Highlight the contextually relevant journal link based on hour
  const hour = new Date().getHours();
  if (hour < 12) {
    document.getElementById("morning-link").classList.add("btn-primary");
  } else {
    document.getElementById("evening-link").classList.add("btn-primary");
  }

  await loadDailyNote();
  await loadOpenTasks();
});

async function loadDailyNote() {
  const container = document.getElementById("daily-content");
  try {
    const note = await api.getDaily(today);
    renderFrontmatter(note.frontmatter);
    renderTimeBlocks(note.content);
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return; // handled by auth guard
    container.innerHTML = `<p class="text-dim">Could not load today's note: ${err.message}</p>`;
  }
}

async function loadOpenTasks() {
  const container = document.getElementById("task-list");
  try {
    const tasks = await api.getOpenTasks("daily", 14);
    if (tasks.length === 0) {
      container.innerHTML = `<p style="color:var(--text-dim);font-size:0.875rem">No open tasks. Add some in today's note.</p>`;
      return;
    }
    container.innerHTML = tasks
      .map(t => `
        <li class="task-item">
          <input type="checkbox" disabled>
          <div>
            <div>${escHtml(t.text)}</div>
            <div class="task-meta">${t.date}</div>
          </div>
        </li>`)
      .join("");
  } catch (err) {
    container.innerHTML = `<p style="color:var(--text-dim);font-size:0.875rem">Could not load tasks.</p>`;
  }
}

function renderFrontmatter(fm) {
  const moodM = fm.mood_morning;
  const moodE = fm.mood_evening;
  const sleep = fm.sleep_hours;

  if (moodM != null) {
    document.getElementById("mood-morning-val").textContent = moodM;
    renderMoodPips("mood-morning-pips", moodM);
  }
  if (moodE != null) {
    document.getElementById("mood-evening-val").textContent = moodE;
    renderMoodPips("mood-evening-pips", moodE);
  }
  if (sleep != null) {
    document.getElementById("sleep-val").textContent = `${sleep}h`;
  }
}

function renderMoodPips(id, value) {
  const el = document.getElementById(id);
  if (!el) return;
  el.innerHTML = Array.from({ length: 10 }, (_, i) =>
    `<div class="mood-pip${i < value ? " filled" : ""}"></div>`
  ).join("");
}

function renderTimeBlocks(content) {
  const container = document.getElementById("time-blocks");
  // Extract lines that look like time blocks: "- HH:MM–HH:MM Label"
  const blockRe = /^[-*]\s+(\d{2}:\d{2})[–\-–](\d{2}:\d{2})\s+(.+)$/gm;
  const blocks = [];
  let m;
  while ((m = blockRe.exec(content)) !== null) {
    blocks.push({ start: m[1], end: m[2], label: m[3] });
  }
  if (blocks.length === 0) {
    container.innerHTML = `<p style="color:var(--text-dim);font-size:0.875rem">No time blocks yet. Use AI Suggest or add them manually.</p>`;
    return;
  }
  container.innerHTML = blocks
    .map(b => `
      <div class="time-block">
        <span class="time">${escHtml(b.start)} – ${escHtml(b.end)}</span>
        <span class="label">${escHtml(b.label)}</span>
      </div>`)
    .join("");
}

// AI Suggest button
document.getElementById("ai-suggest-btn")?.addEventListener("click", async () => {
  const btn = document.getElementById("ai-suggest-btn");
  btn.disabled = true;
  btn.textContent = "Thinking…";
  try {
    const result = await api.aiSuggest(today);
    if (result.blocks.length === 0) {
      showToast(result.rationale || "No suggestions returned", "warn");
    } else {
      renderAISuggestions(result);
    }
  } catch (err) {
    showToast(`AI error: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "AI Suggest";
  }
});

function renderAISuggestions(result) {
  const container = document.getElementById("ai-suggestions");
  container.innerHTML = `
    <div class="card">
      <h2>AI Suggestions</h2>
      <p style="color:var(--text-dim);font-size:0.875rem;margin-bottom:12px">${escHtml(result.rationale)}</p>
      <div class="block-list">
        ${result.blocks.map(b => `
          <div class="time-block ${b.type}">
            <span class="time">${b.start} – ${b.end}</span>
            <span class="label">${escHtml(b.label)}</span>
          </div>`).join("")}
      </div>
    </div>`;
  container.scrollIntoView({ behavior: "smooth" });
}

// Helpers
function formatDate(iso) {
  return new Date(iso + "T12:00:00").toLocaleDateString(undefined, {
    weekday: "long", month: "long", day: "numeric",
  });
}

function escHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
