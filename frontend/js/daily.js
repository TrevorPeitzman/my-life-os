/**
 * daily.js — Raw markdown note editor.
 * ?date=YYYY-MM-DD for daily notes.
 * ?horizon=weekly&key=2026-W13 for planning notes.
 */

import { api } from "./api.js";
import { showToast, getToday } from "./utils.js";

const params = new URLSearchParams(location.search);
const horizon = params.get("horizon") || "daily";
const key = params.get("key") || (horizon === "daily" ? params.get("date") || getToday() : null);

document.addEventListener("DOMContentLoaded", async () => {
  if (!key) {
    showToast("No date/key specified", "error");
    return;
  }

  document.getElementById("note-title").textContent = `${horizon} / ${key}`;

  const textarea = document.getElementById("md-editor");
  const saveBtn = document.getElementById("save-btn");
  const loadingEl = document.getElementById("loading");

  try {
    let note;
    if (horizon === "daily") {
      note = await api.getDaily(key);
    } else {
      note = await api.getPlanning(horizon, key);
    }
    textarea.value = note.content;
    loadingEl?.remove();
    textarea.style.display = "block";
  } catch (err) {
    showToast(`Could not load note: ${err.message}`, "error");
    return;
  }

  // Auto-save on Ctrl+S / Cmd+S
  document.addEventListener("keydown", async e => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      await save(horizon, key, textarea.value, saveBtn);
    }
  });

  saveBtn.addEventListener("click", () => save(horizon, key, textarea.value, saveBtn));
});

async function save(horizon, key, content, btn) {
  btn.disabled = true;
  btn.textContent = "Saving…";
  try {
    if (horizon === "daily") {
      await api.putDaily(key, content);
    } else {
      await api.putPlanning(horizon, key, content);
    }
    showToast("Saved", "ok");
  } catch (err) {
    showToast(`Save failed: ${err.message}`, "error");
  } finally {
    btn.disabled = false;
    btn.textContent = "Save";
  }
}
