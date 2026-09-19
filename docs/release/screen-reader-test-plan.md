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

## PARITY-001 — The file changed on disk, and QUILL asks

Fix: QUILL used to reload a tab silently whenever the buffer was clean. Nothing
announced it, so a document could be replaced under the caret between one key and
the next. It now always asks, and can be told to stop asking per file format.

- TC-PARITY-001a — The question itself
  - Steps: open a `.txt` in QUILL, then save the same file from Notepad. Return to
    QUILL.
  - Expected: a dialog titled "File Changed on Disk". Focus is on **Reload from
    Disk**; the message names the file and says what each of the three answers
    would do. Nothing has changed in the document until you answer.
- TC-PARITY-001b — With unsaved edits, the wording changes
  - Steps: as above, but type in QUILL first so the buffer is dirty.
  - Expected: the message says the edits would be replaced by the version on disk;
    the three answers are the same three.
- TC-PARITY-001c — The third answer
  - Steps: press **Open Disk Version in a New Tab**.
  - Expected: a second tab opens with the disk version, announced as a new
    document; the first tab is untouched and still dirty.
- TC-PARITY-001d — Remembering, per format
  - Steps: raise the question again, tick **Do not ask me again for .txt files**,
    and choose **Keep Mine**. Raise it again on a `.txt`, then on a `.md`.
  - Expected: the `.txt` is kept with no dialog and a spoken status line saying so;
    the `.md` still asks. The checkbox is reachable by Tab and announced with its
    own name, not as an unnamed check box.
- TC-PARITY-001e — The way back
  - Steps: press `Ctrl+Shift+F11` (File > Forget Remembered File-Change Answers).
  - Expected: it says how many formats were forgotten. Pressing it again says that
    no formats are being answered for you — not silence. A question that can be
    switched off and not on is a trap, and this is the only way back.

## PARITY-002 — Three sentences about the document you are in

Fix: the three "magical tier" commands, each answering a question a listener
otherwise cannot ask. All three are announcements, so over-announcing is the risk
to watch as much as under-announcing.

- TC-PARITY-002a — What Is This Document? (`Alt+Shift+F1`)
  - Steps: open a Markdown file with several headings and a list; press the key.
  - Expected: one sentence, in this order: kind and size ("Markdown: 412 words, 38
    lines"), then shape ("6 headings and 14 list items"), then anything that will
    stop you ("Read-only"). A document with no headings says **"No headings"** —
    that is why Alt+Down will not move, and a listener who is not told spends the
    next few presses finding out.
  - Expected: an empty document says **"Empty document"**. An empty document and a
    document that failed to load sound identical otherwise, and the difference is
    whether to start typing.
- TC-PARITY-002b — What Changed? (`Alt+Shift+F2`)
  - Steps: with a fresh document, press the key. Then type a sentence, press it
    again. Then paste a paragraph and press it again.
  - Expected: first **"Nothing has changed this document yet."**, then a sentence
    naming the action, where it happened, and how much it was. Never the text
    itself: the journal records sizes, so a password typed into a document cannot
    be read back out of it.
- TC-PARITY-002c — Undo and Say What Changed (`Alt+Shift+F3`)
  - Steps: type a word, press the key.
  - Expected: the edit is undone **and** the announcement says what was undone and
    how the document changed size. Pressing it with nothing to undo says so rather
    than going silent.

## PARITY-003 — A formatting key that cannot mean anything

Fix: the native Rich Edit control answers `Ctrl+U`, `Ctrl+E`/`L`/`R`/`J`, `Ctrl+=`
and `Ctrl+Shift+=` whether the document can hold formatting or not. In a Markdown
or plain document the run was really applied — on screen and on the undo stack —
and never marked dirty, never announced and never saved.

- TC-PARITY-003a — Plain text
  - Steps: in a plain document, press `Ctrl+U` and type a word.
  - Expected: the word is not underlined, and the status line says **"Underline has
    no meaning in a plain text document."**
- TC-PARITY-003b — Once per effect, not once per press
  - Steps: press `Ctrl+U` twice more, then `Ctrl+R` twice.
  - Expected: silence for the repeated `Ctrl+U`; one sentence for the first
    `Ctrl+R`, naming right alignment; silence for the second.
- TC-PARITY-003c — The article is chosen by sound
  - Steps: do the same in an HTML document.
  - Expected: **"an HTML document"**, not "a HTML document". The sentence is going
    to be spoken, and an initialism is read letter by letter. QuillLite says the
    same sentence from the same shared table.
- TC-PARITY-003d — Rich text is left alone
  - Steps: in a `.rtf`, press `Ctrl+U` and type.
  - Expected: the text underlines and nothing is said. The guard is for documents
    that cannot hold formatting.

## PARITY-004 — Suggestions are spelled, not just spoken

Fix: QUILL's spelling review never spelled the suggestion you arrowed onto, while
QuillLite always had.

- TC-PARITY-004 — The F7 review list
  - Steps: type `recieve`, open the review with `F7`, arrow down the suggestions.
  - Expected: each suggestion is spoken and then, after a pause, spelled out as a
    separate utterance — so pressing the next key cancels the spelling unheard.
    "receive" and "recieve" are the same sound; the letters are the answer.

## PARITY-005 — Bringing a QuillLite setup across

Fix: QuillLite could already read QUILL's abbreviations and dictionary; QUILL had
no way to take QuillLite's. Now it does, and the two stores become one.

- TC-PARITY-005a — The plan is described before it is applied
  - Steps: with QuillLite installed and used on the same machine, press
    `Alt+Shift+F11` (Tools > Customize and Support > Bring My QuillLite
    Settings...).
  - Expected: a Yes/No question whose text says how many settings and rebound keys
    would be copied, which stores would be merged **and shared from then on**, and
    what is being **left behind**. An import that says nothing about its own limits
    reads as having brought everything.
- TC-PARITY-005b — No
  - Steps: answer No.
  - Expected: **"Left QUILL's own settings as they are."** Nothing is written.
- TC-PARITY-005c — Yes
  - Steps: answer Yes.
  - Expected: an announcement counting the settings, the keys, the entries added
    and the stores they went into; that QuillLite now reads those stores from
    QUILL; and that a restart shows every change. Afterwards, an abbreviation you
    had only in QuillLite expands in QUILL, and one you had only in QUILL is still
    there with its own expansion.
- TC-PARITY-005d — Nothing to bring
  - Steps: run it on a machine where QuillLite has never run.
  - Expected: it says so in one sentence rather than opening an empty dialog or
    doing nothing.
- TC-PARITY-005e — The profile offers it once
  - Steps: `Alt+Shift+P`, choose the **QuillLite** profile.
  - Expected: the same question is offered once, and never again after it has been
    answered either way; the profile also applies the document model its name
    promises rather than only renaming the menus.

## PARITY-006 — The status bar in a document that has no encoding

Fix: the Encoding and Line Endings segments read "UTF-8" and "CRLF" for a rich
text document, which has neither.

- TC-PARITY-006 — Rich text
  - Steps: open a `.rtf`, press `F6`, read the Encoding and Line Endings segments.
  - Expected: **"RTF (rich text)"** and **"Not applicable (rich text)"**. A segment
    stating a fact the document does not have is worse than a segment that is not
    there. The `Ctrl+Alt+E` window agrees: a file in a format its lists cannot
    offer shows a **keep as is** row and stays in it.

## PARITY-007 — An export keeps the document's own encoding, and says when it cannot

Fix: Save As Plain Text and Save As HTML hard-coded UTF-8 and wrote
non-atomically, so an exported copy of a Windows-1252 document came back in a
different encoding than the document it came from, and a failure mid-write left a
truncated file where the old one had been.

- TC-PARITY-007a — The encoding survives the export
  - Steps: open a Windows-1252 `.txt` (the Encoding segment says so), then
    File > Export > Plain Text.
  - Expected: the exported file is Windows-1252, not UTF-8.
- TC-PARITY-007b — When a character will not fit, it is widened out loud
  - Steps: type an em dash into that document and export again.
  - Expected: the file is written as UTF-8 **and** a save warning says so, naming
    the encoding that could not hold the text. Silence here would mean a file
    whose encoding changed without anybody being told.
- TC-PARITY-007c — The HTML charset matches the bytes
  - Steps: File > Export > HTML from the same document; read the `<meta charset>`
    of the result.
  - Expected: it names the encoding actually written. A declaration that disagrees
    with the bytes is worse than none: the browser believes the declaration.

## Sign-off

- Tester:
- Screen reader(s) and version(s):
- Build / commit tested:
- Date:
- Overall result: Pass / Pass-with-notes / Fail
- Notes:
