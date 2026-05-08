# Calendar Day Editor Modal — Design Spec

**Date:** 2026-05-08
**Status:** Approved

## Summary

When a user clicks a day cell on the calendar page, a modal opens with a raw markdown editor for that day's vault file. Saving refreshes the calendar grid so completion status stays current.

## Scope

- `frontend/calendar.html` — add modal markup and styles
- `frontend/js/calendar.js` — add click handlers, load/save logic, modal lifecycle

No new files. No changes to the backend, `daily.html`, `daily.js`, or any other page.

## Behaviour

### Clickable cells

All `.cal-day` cells that are neither `.empty` nor `.future` are clickable. They get `cursor: pointer` and a subtle hover highlight (lightened border/background). The `date` string already attached to each day during render is used to key the API call.

### Opening the modal

1. User clicks a day cell.
2. Modal overlay fades in; content area shows a spinner.
3. `api.getDaily(date)` is called; on success, the raw markdown string is placed into the textarea and the spinner is removed.
4. Modal header shows the formatted date: `new Date(date + "T12:00:00").toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })`.
5. On API error, show a toast and close the modal.

### Saving

- **Save button** or **Ctrl+S / Cmd+S** (while modal is focused) → `api.putDaily(date, textarea.value)`.
- On success: show toast "Saved", close modal, call `renderMonth()` to refresh the grid.
- On error: show toast with error message; modal stays open so the user doesn't lose their edits.

### Closing without saving

- **ESC key** or **clicking the backdrop** closes the modal.
- If the textarea content differs from what was loaded (dirty check), a `confirm()` prompt warns "You have unsaved changes. Close anyway?" before discarding.

### Future days

Cells with the `.future` class remain non-interactive (no cursor change, no click handler). They are already visually dimmed at 35% opacity.

## UI / Markup

Single `<div id="day-modal">` appended inside `<body>` in `calendar.html`. Structure:

```
#day-modal (fixed overlay, full viewport, semi-transparent backdrop)
  .modal-box (centered card, max-width 640px, ~90vh tall on mobile)
    .modal-header
      h3#modal-date-label
      button#modal-close (×)
    #modal-body
      .spinner (shown while loading)
      textarea#modal-editor (hidden until loaded; fills remaining height)
    .modal-footer
      button#modal-save ("Save")
```

Styles are scoped inline in `calendar.html`'s `<style>` block (consistent with existing pattern on that page).

## State Management

`calendar.js` tracks two module-level variables when the modal is open:
- `modalDate` — the YYYY-MM-DD string for the open day
- `modalOriginal` — the content string as loaded, used for dirty checking

Both are set to `null` when the modal closes.

## Error Handling

| Scenario | Behaviour |
|---|---|
| API key missing | Existing `apiError` guard already prevents calendar render; modal can't open |
| Load fails | Toast error, modal closes |
| Save fails | Toast error, modal stays open |
| Concurrent clicks | Second click while modal is open is ignored (modal already visible) |

## Testing

Manual acceptance criteria:
1. Click a past day → modal opens with correct date label and raw markdown content.
2. Edit content, press Save → toast appears, modal closes, calendar cell updates if frontmatter changed (e.g. `morning_done` toggled).
3. Edit content, press ESC → confirm prompt appears; cancel keeps modal open; confirm closes without saving.
4. Click backdrop → same dirty-check behaviour as ESC.
5. Click a future day → nothing happens.
6. Save fails (kill server mid-edit) → toast shown, modal stays open with edits intact.
