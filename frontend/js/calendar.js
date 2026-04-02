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
