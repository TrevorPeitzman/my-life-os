# Calendar Day Editor Modal — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clicking a past or present day cell on the calendar opens a modal with a raw markdown editor for that day's vault file; saving refreshes the calendar grid.

**Architecture:** All changes are confined to two files — `calendar.html` (modal markup + scoped styles) and `calendar.js` (modal state, open/close/save functions, click handlers on day cells). No new files, no backend changes. The modal reuses the existing `api.getDaily` / `api.putDaily` calls already used by `daily.js`.

**Tech Stack:** Vanilla JS ES modules, FastAPI backend, Markdown vault files.

---

### Task 1: Modal markup and styles in `calendar.html`

**Files:**
- Modify: `frontend/calendar.html`

- [ ] **Step 1: Add modal CSS to the existing `<style>` block**

Open `frontend/calendar.html`. Inside the `<style>` tag (after the last existing rule, before `</style>`), append:

```css
    /* ── Day editor modal ── */
    #day-modal {
      position: fixed;
      inset: 0;
      z-index: 100;
      align-items: center;
      justify-content: center;
    }
    #modal-backdrop {
      position: absolute;
      inset: 0;
      background: rgba(0, 0, 0, 0.6);
    }
    .day-modal-box {
      position: relative;
      z-index: 1;
      width: 100%;
      max-width: 640px;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      background: var(--surface);
      border: 1px solid var(--border);
      border-radius: var(--radius);
      overflow: hidden;
      margin: 16px;
    }
    .modal-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 16px;
      border-bottom: 1px solid var(--border);
      flex-shrink: 0;
    }
    .modal-header h3 { margin: 0; font-size: 1rem; font-weight: 600; }
    #modal-body {
      flex: 1;
      display: flex;
      flex-direction: column;
      min-height: 0;
    }
    #modal-spinner { padding: 24px; }
    #modal-editor {
      flex: 1;
      width: 100%;
      min-height: 300px;
      resize: none;
      background: var(--surface);
      border: none;
      color: var(--text);
      padding: 16px;
      font-family: monospace;
      font-size: 0.875rem;
      line-height: 1.6;
      box-sizing: border-box;
    }
    .modal-footer {
      padding: 12px 16px;
      border-top: 1px solid var(--border);
      display: flex;
      justify-content: flex-end;
      flex-shrink: 0;
    }
    .cal-day:not(.empty):not(.future) { cursor: pointer; }
    .cal-day:not(.empty):not(.future):hover { border-color: var(--accent); }
```

- [ ] **Step 2: Add modal HTML before `</body>`**

In `frontend/calendar.html`, immediately before the closing `</body>` tag, add:

```html
<div id="day-modal" style="display:none">
  <div id="modal-backdrop"></div>
  <div class="day-modal-box">
    <div class="modal-header">
      <h3 id="modal-date-label"></h3>
      <button id="modal-close" class="btn btn-secondary" style="padding:6px 12px">&#x2715;</button>
    </div>
    <div id="modal-body">
      <div id="modal-spinner" class="loading"><div class="spinner"></div>Loading&hellip;</div>
      <textarea id="modal-editor" style="display:none" spellcheck="true"></textarea>
    </div>
    <div class="modal-footer">
      <button id="modal-save" class="btn btn-primary">Save</button>
    </div>
  </div>
</div>
```

- [ ] **Step 3: Verify markup is hidden at page load**

Open the calendar page in a browser. Confirm no modal is visible. Open DevTools → Elements and confirm `#day-modal` is present with `display: none`.

- [ ] **Step 4: Commit**

```bash
git add frontend/calendar.html
git commit -m "feat(calendar): add day editor modal markup and styles"
```

---

### Task 2: Modal state, open/close/save functions in `calendar.js`

**Files:**
- Modify: `frontend/js/calendar.js`

- [ ] **Step 1: Add module-level state variables**

In `frontend/js/calendar.js`, after the `let viewMonth` declaration (line 18), add:

```js
let modalDate     = null;  // YYYY-MM-DD of the currently open day
let modalOriginal = null;  // content as loaded, for dirty-check on close
```

- [ ] **Step 2: Add `openModal` function**

After the closing brace of `renderMonth` (end of file), append:

```js
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

  api.getDaily(date).then(note => {
    editor.value  = note.content;
    modalOriginal = note.content;
    spinner.style.display = "none";
    editor.style.display  = "block";
    editor.focus();
  }).catch(err => {
    modal.style.display = "none";
    modalDate = modalOriginal = null;
    showToast(`Could not load ${date}: ${err.message}`, "error");
  });
}
```

- [ ] **Step 3: Add `closeModal` function**

Append after `openModal`:

```js
function closeModal(force = false) {
  const editor = document.getElementById("modal-editor");
  if (!force && modalOriginal !== null && editor.value !== modalOriginal) {
    if (!confirm("You have unsaved changes. Close anyway?")) return;
  }
  document.getElementById("day-modal").style.display = "none";
  modalDate = modalOriginal = null;
}
```

- [ ] **Step 4: Add `saveModal` function**

Append after `closeModal`:

```js
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
```

- [ ] **Step 5: Wire modal events inside `DOMContentLoaded`**

In the existing `DOMContentLoaded` listener (currently ends with `renderMonth();`), append these lines before the closing `}`):

```js
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
```

- [ ] **Step 6: Verify events are wired (DevTools)**

Start the dev server (`uvicorn app.main:app --reload` from `backend/`). Open the calendar page. Open DevTools → Elements and confirm `#day-modal` is present and `style="display:none"`. In DevTools → Console, confirm no JS errors on page load.

Note: `openModal` is an ES module function and is not callable from the console. Full interaction testing happens in Task 3 once click handlers are wired.

- [ ] **Step 7: Commit**

```bash
git add frontend/js/calendar.js
git commit -m "feat(calendar): add modal open/close/save logic"
```

---

### Task 3: Wire click handlers on day cells in `renderMonth`

**Files:**
- Modify: `frontend/js/calendar.js`

- [ ] **Step 1: Attach click handler to each non-future day cell**

In `renderMonth`, inside the `days.forEach` block, the current code appends the element and then moves on. Find this line (currently the last line inside `days.forEach`):

```js
    grid.appendChild(el);
```

Replace it with:

```js
    grid.appendChild(el);
    if (date <= todayStr) {
      el.addEventListener("click", () => openModal(date));
    }
```

- [ ] **Step 2: Manual end-to-end test**

With the dev server running, open the calendar page:

1. Click a past day cell → modal opens with correct date label and raw markdown.
2. Edit a line, click Save → "Saved" toast appears, modal closes, calendar re-renders.
3. Click the same day again → edits are reflected in the textarea.
4. Edit text, press ESC → confirm prompt appears; click Cancel → modal stays open; press ESC again → click OK → modal closes.
5. Edit text, click backdrop → same dirty-check behaviour.
6. Click a future day (dimmed) → nothing happens.
7. Press Ctrl+S (or Cmd+S on Mac) while editing → saves and closes.

- [ ] **Step 3: Commit**

```bash
git add frontend/js/calendar.js
git commit -m "feat(calendar): open day editor modal on cell click"
```
