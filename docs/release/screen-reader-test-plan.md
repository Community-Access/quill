# QUILL Screen-Reader and Keyboard Test Plan

Manual validation steps for every accessibility/focus/keyboard fix in the public
beta quality pass. Each fix in the quality ledger has a matching case here.

How to use this plan:
- Test with NVDA and JAWS (and Narrator where noted) on a real Windows build.
- For each case: follow the steps with the mouse unplugged (keyboard only), then
  again reading with the screen reader's virtual/focus cursor.
- Record Pass/Fail and the actual spoken text. "Expected" describes the intended
  announcement; exact wording varies by screen reader, but the field name, role,
  and state must be present and correct.
- A case fails if focus is lost, a control is unnamed/misnamed, Tab cannot leave a
  field, or an error is not announced and focus is not placed to fix it.

General keyboard contract to confirm in every dialog: Tab / Shift+Tab move
predictably, Escape cancels, Enter activates the default, and focus returns to a
sensible place when the dialog closes.

---

## A11Y-001 — Notebook tab groups have accessible names

Fix: six `wx.Notebook` tab groups were unnamed and announced generically; each now
has a name.

- TC-A11Y-001a — Application Status dialog
  - Steps: Help > Application Status. Tab to the tab control; arrow Left/Right
    across tabs.
  - Expected: the tab control is announced as "System status sections" (tab list /
    page tab list role); tabs read "Status", "Tasks & Downloads", "Features",
    "Actions"; each page's list is reachable and named (see A11Y-002).
- TC-A11Y-001b — About dialogs
  - Steps: Help > About (and the "About" tabbed dialog). Move to the tab control.
  - Expected: the tab group is announced as "About sections", not an unnamed tab
    control.
- TC-A11Y-001c — Word view / Rich text view / CSV view surfaces
  - Steps: open a document that offers the Word/Rich-text/CSV view; move to its
    view switcher tab control.
  - Expected: announced as "Word view" / "Rich text view" / "CSV view" respectively.
- TC-A11Y-001d — Document tab bar
  - Steps: open two or more documents; move focus to the document tab control.
  - Expected: announced as "Open documents" (not a bare/unnamed notebook).

## A11Y-002 — Controls use human-readable names (not snake_case)

Fix: controls previously named like "status_overview" (spoken letter-for-letter)
now use readable names.

- TC-A11Y-002a — Application Status lists
  - Steps: Help > Application Status; Tab through each tab's list/control.
  - Expected: the lists/fields are announced as "Status overview", "Tasks and
    downloads", "Features", "Recent actions", and the button as "Refresh" — never
    "status underscore overview" or similar.
- TC-A11Y-002b — Verbosity preferences status line
  - Steps: open Verbosity preferences; navigate to the status line.
  - Expected: announced as "Verbosity status".

## FOCUS-001 — HTML preview fallback opens on its content

Fix: the `wx.html` fallback dialog opened with focus on the Close button; it now
focuses the readable content.

- TC-FOCUS-001 — HTML message/preview fallback
  - Precondition: the `wx-accessible-webview` backend is absent (so the wx.html
    fallback is used). If your build has the WebView backend, this path is not
    exercised; note that and skip.
  - Steps: open a dialog that renders HTML content (e.g. an About/preview surface)
    in the fallback path.
  - Expected: on open, the screen reader begins reading the content (the HTML view
    has focus), not "Close button". Tab still reaches Close; Escape closes.

## A11Y-003 — Input fields have accessible names

Fix: input controls that had only an adjacent visual label now carry an explicit
accessible name.

- TC-A11Y-003a — Skill Library dialog
  - Steps: open the Skill Library; Tab through the Skills list, the Description
    field, and (when running a skill with parameters) each parameter control.
  - Expected: "Skills" (list), "Description" (text), and each parameter field
    announced by its parameter label; no unnamed edit/combo/spin controls.
- TC-A11Y-003b — Assistant authoring / model-search dialogs
  - Steps: open the prompt-authoring dialog and the model-search dialog; Tab
    through the fields.
  - Expected: fields announced as "Title", "Tone", "Audience", "Goal", "Template",
    "Prompt", and "Search models" respectively.
- TC-A11Y-003c — Web form dialog
  - Steps: open any Quillin/web-form dialog with multiple fields.
  - Expected: every field is announced by its label; no unnamed text areas or
    selects.
- TC-A11Y-003d — Sticky note editor
  - Steps: create/edit a sticky note (native fallback path).
  - Expected: the two editors are announced as "Title" and "Note".

## KEY-001 — Tab is not trapped in prose multiline fields

Fix: `wx.TE_PROCESS_TAB` was removed from prose fields so Tab moves focus instead
of inserting a tab character.

- TC-KEY-001a — Assistant prompt field
  - Steps: focus the Prompt field; type a few words; press Tab.
  - Expected: focus LEAVES the field to the next control; Tab does NOT insert a tab
    character. Shift+Tab returns. (Keyboard-only: confirm you can reach the action
    buttons without the mouse.)
- TC-KEY-001b — Sticky note body
  - Steps: focus the Note body; press Tab.
  - Expected: focus moves to the Save/Cancel buttons; no tab character inserted.
- TC-KEY-001c — Web form textarea
  - Steps: focus a multiline textarea field; press Tab.
  - Expected: focus moves to the next field/button; no tab character inserted.
- TC-KEY-001d — Code editor is intentionally different (control case)
  - Steps: open the restricted-Python code tool; focus the code field; press Tab.
  - Expected: Tab inserts indentation here on purpose (this field keeps
    `TE_PROCESS_TAB`). Known limitation: there is not yet a keyboard focus-exit
    from this field — recorded as a follow-up. Confirm the behavior and note it.

## A11Y-004 — Validation errors move focus to the offending field

Fix: the GitHub "open repository" form announced an error but left focus on the
button; it now moves focus to the field.

- TC-A11Y-004 — GitHub open-repository validation
  - Steps: open File > Open from Remote > GitHub (open-repository form). Leave the
    repository box empty (or enter a value without a "/") and activate Load.
  - Expected: the status message is announced ("Enter a repository name..." or
    "Repository must be in owner/repo format."), AND focus moves to the repository
    edit field so you can correct it without hunting for it.

## Editor surface (wave 6 — confirm existing behavior; no code changed)

These confirm the core editing surface is announced correctly. No fix was made
here (the audit found it already correct), but verify on a real build.

- TC-EDIT-001 — Editor control
  - Steps: open a document; move focus into the text area.
  - Expected: announced as "Document", edit/text-area role, multi-line; typed text
    reads back; the selection is announced and stays visible when focus leaves.
- TC-EDIT-002 — Leaving the editor with the keyboard
  - Steps: with focus in the editor, press Tab.
  - Expected: focus moves out of the editor to the next control (Tab is not
    trapped; it does not insert a tab character).
- TC-EDIT-003 — Document tabs and side preview
  - Steps: open two+ documents; arrow across the document tab control; press
    Enter on one; toggle/focus the side preview (View > Focus Preview).
  - Expected: the tab control is "Open documents"; each tab announces its document
    name; Enter announces "Focused document <name>" and lands in the editor; the
    preview pane is announced as "Preview".
- TC-EDIT-004 — Status bar segments
  - Steps: invoke the focus-status-bar command; Tab across the cells; press Escape.
  - Expected: each cell announces "Status bar, <label>, <value>" (e.g. language,
    position); Tab moves between cells; Escape announces "Returned to editor" and
    returns focus to the document.

---

## Regression context (not user-visible, no SR step needed)

These fixes are verified by automated tests and need no manual SR check, listed so
the plan is complete:
- TEST-002: watchdog re-dump test made deterministic (unit test).
- CALL-1 gate: undefined-private-method audit (CI gate).

## SAVE-001 — Save As conversion, window title, and export fidelity (0.9.0)

Run with JAWS or NVDA on a real build. This is the manual verification (Task 9) carried
over from the retired `save-as-conversion-fix` plan; converter bake-off verdicts are in
`docs/qa/converter-bakeoff.md`.

- [ ] **Original repro:** new document, 8 lines, Ctrl-S, switch type to Word, name it,
  Enter. Verify: title bar reads "name.docx - QUILL for All ..." (no [modified]); second
  Ctrl-S saves silently with no dialog; the save announcement speaks; the file opens in
  Word with 8 paragraphs.
- [ ] **Save As each type:** .txt, .md, .html, .rtf, .docx — title updates, status speaks
  the format label, file opens in Notepad/browser/WordPad/Word respectively.
- [ ] **Typed rogue extension:** Save As, type `notes.pdf` — the Export routing prompt
  appears; accepting lands in Export as PDF; declining returns safely.
- [ ] **Binary protection:** open any .pdf and any .xlsx, edit, Ctrl-S — the explanation
  speaks, Save As opens, the original file on disk is byte-identical.
- [ ] **Export each Tier-1 format** (with Pandoc installed) from an 8-line doc — line
  breaks survive in docx/odt/html/rtf outputs; PDF either produces a file or speaks the
  missing-PDF-engine error clearly.
- [ ] **DAISY export** of the same doc — 8 phrases in the book (line breaks and headings
  map to phrases; it was built line-oriented).
- [ ] **First-line title:** untitled doc starting `# Trip Report`, Ctrl-S — name box
  pre-filled "Trip Report".
- [ ] **Engine preference:** flip `docx_write_engine` to pandoc, Save As .docx, open in
  Word — structure present, fonts absent, matching the documented outcome.

## Sign-off

- Tester:
- Screen reader(s) and version(s):
- Build / commit tested:
- Date:
- Overall result: Pass / Pass-with-notes / Fail
- Notes:
