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

let modalDate     = null;  // YYYY-MM-DD of the currently open day
let modalOriginal = null;  // content as loaded, for dirty-check on close

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
  document.getElementById("modal-close").addEventListener("click", () => closeModal());
  document.getElementById("modal-backdrop").addEventListener("click", () => closeModal());
  document.getElementById("modal-save").addEventListener("click", saveModal);

  document.addEventListener("keydown", e => {
    const modalOpen = document.getElementById("day-modal").style.display !== "none";
    if (e.key === "Escape" && modalOpen) {
      closeModal();
    }
    if ((e.ctrlKey || e.metaKey) && e.key === "s" && modalOpen) {
      e.preventDefault();
      saveModal();
    }
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
  let apiError = false;
  let errMessage = "";

  const apiKey = localStorage.getItem("life_os_api_key");
  console.log("[Calendar] life_os_api_key in localStorage:",
    apiKey ? `present (${apiKey.length} chars)` : "MISSING");

  if (!apiKey) {
    apiError = true;
    errMessage = "API key not set in this browser";
  } else {
    const url = `/api/journal/consistency?month=${monthStr}`;
    console.log("[Calendar] requesting", url);
    try {
      const data = await api.getConsistency(monthStr);
      console.log("[Calendar] response:", data);
      if (Array.isArray(data.days)) days = data.days;
    } catch (err) {
      apiError = true;
      errMessage = err.message || String(err);
      console.error("[Calendar] consistency error:", err);
      showToast(`Could not load ${monthStr}: ${errMessage}`, "error");
    }
  }

  // Always generate blank day cells for the month as fallback
  if (days.length === 0) {
    const daysInMonth = new Date(viewYear, viewMonth, 0).getDate();
    for (let d = 1; d <= daysInMonth; d++) {
      const dateStr = `${viewYear}-${String(viewMonth).padStart(2, "0")}-${String(d).padStart(2, "0")}`;
      days.push({ date: dateStr, day: d, morning: false, evening: false });
    }
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
    if (date <= todayStr) {
      el.addEventListener("click", () => openModal(date));
    }
  });

  const pastDays = days.filter(d => d.date <= todayStr).length;
  const missed   = pastDays - bothCount - morningOnly - eveningOnly;
  if (apiError) {
    const isMissingKey = errMessage === "API key not set in this browser";
    summary.innerHTML = isMissingKey
      ? `<strong>API key not set in this browser.</strong> ` +
        `Go to the <a href="/" style="color:var(--accent)">home page</a> and enter your key. ` +
        `(Saving entries from another tab/device does not share localStorage.)`
      : `<strong>Could not load check-in data:</strong> <code>${errMessage}</code>. ` +
        `<a href="#" onclick="location.reload();return false;" style="color:var(--accent)">Reload</a> ` +
        `or check <strong>DevTools \u2192 Network</strong> for the <code>/api/journal/consistency</code> request.`;
  } else if (pastDays > 0) {
    summary.textContent =
      `${bothCount} full \u00b7 ${morningOnly} morning only \u00b7 ${eveningOnly} evening only \u00b7 ${missed} missed`;
  } else {
    summary.textContent = "No days yet this month.";
  }
}

function openModal(date) {
  if (document.getElementById("day-modal").style.display !== "none") return;

  const modal   = document.getElementById("day-modal");
  const spinner = document.getElementById("modal-spinner");
  const editor  = document.getElementById("modal-editor");

  modalDate     = date;
  modalOriginal = null;

  document.getElementById("modal-date-label").textContent =
    new Date(date + "T12:00:00").toLocaleDateString(undefined, {
      weekday: "long", month: "long", day: "numeric",
    });

  spinner.style.display = "";
  editor.style.display  = "none";
  editor.value          = "";
  modal.style.display   = "flex";

  const targetDate = date;
  api.getDaily(date).then(note => {
    if (modalDate !== targetDate) return;
    editor.value  = note.content;
    modalOriginal = note.content;
    spinner.style.display = "none";
    editor.style.display  = "block";
    editor.focus();
  }).catch(err => {
    closeModal(true);
    showToast(`Could not load ${date}: ${err.message}`, "error");
  });
}

function closeModal(force = false) {
  const editor = document.getElementById("modal-editor");
  if (!force && modalOriginal !== null && editor.value !== modalOriginal) {
    if (!confirm("You have unsaved changes. Close anyway?")) return;
  }
  document.getElementById("day-modal").style.display = "none";
  modalDate = modalOriginal = null;
}

async function saveModal() {
  if (!modalDate) return;
  const editor  = document.getElementById("modal-editor");
  const saveBtn = document.getElementById("modal-save");
  saveBtn.disabled    = true;
  saveBtn.textContent = "Saving…";
  try {
    await api.putDaily(modalDate, editor.value);
    showToast("Saved", "ok");
    modalOriginal = editor.value;
    closeModal(true);
    renderMonth();
  } catch (err) {
    showToast(`Save failed: ${err.message}`, "error");
  } finally {
    saveBtn.disabled    = false;
    saveBtn.textContent = "Save";
  }
}
