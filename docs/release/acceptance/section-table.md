# Section — Tables, Reveal Codes, Notes & misc (`table.*` `reveal.*` `notes.*` + `document/sync/ai/media`, 22 commands)

Four small worlds in one section: moving around a **table** cell by cell and
hearing where you are (`table.*`); inspecting the hidden formatting **codes**
WordPerfect-style (`reveal.*`); leaving and finding your own **inline notes**
(`notes.*`); and a handful of one-off commands — a spoken **document summary**,
**folder sync** with GitHub, AI **metadata** suggestions, and the media **sleep
timer** (`document/sync/ai/media`). Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → the `table.*`, `reveal.*`, `notes.*`,
`document.*`, `sync.*`, `ai.*`, and `media.*` sections. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
**`table.md`** — a one-line caption then a **3-column** table (`Region`,
`Device`, `Notes`) with a header row and **3 body rows** (North / South / East),
i.e. **4 navigable rows** once the `| --- |` separator is set aside. The South
row's Device cell holds `Phone \| Watch` — an **escaped pipe** that must stay
inside one cell. The table-navigation scenarios reuse the wording established in
the core-journey plan, `../qa-core-journeys.md` → **JOURNEY-002**.

The `table.*` chords all follow the same rule: they move only when the caret is
**inside** a table, they **speak position first then content** ("Row 2 of 4,
column 3 of 3: Ships Q1"), an empty cell is spoken as **"blank"**, and hitting an
edge announces the edge and leaves the caret put. Outside a table every chord
says **"Not in a table"** and does nothing.

---

## TBL-01 — Table: Next Cell (`table.next_cell`, Ctrl+Alt+Right)

*What & why.* Step one cell to the right along a row — the everyday "read across
the table" move, spoken so you always know which cell you landed on.

**Before you start**
- Open **`table.md`**. Put the caret on the header row (the line with `Region`).

**Do this**
1. Press **Ctrl+Alt+Right**. (No menu path — this is a keyboard command; you can
   also run **Table: Next Cell** from the Command Palette, **Ctrl+Shift+P**.)
2. Keep pressing **Ctrl+Alt+Right** to the end of the row, then once more.

**You should see and hear**
- The caret jumps into the next cell and QUILL speaks **position then content**,
  e.g. "Row 1 of 4, column 2 of 3: Device", then "…column 3 of 3: Notes". The
  count is **4 rows** (header + 3 body) and **3 columns**.
- At the **last cell of a non-final row** it says **"No more cells"** and the
  caret stays put. At the **final cell of the final row** (East / Backordered) it
  says **"No more cells, end of table"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-02 — Table: Previous Cell (`table.previous_cell`, Ctrl+Alt+Left)

*What & why.* Step one cell to the **left** along a row — the mirror of TBL-01.

**Before you start**
- **`table.md`** open. Caret in the **Notes** column of any body row (e.g. after
  a couple of Ctrl+Alt+Right presses).

**Do this**
1. Press **Ctrl+Alt+Left** repeatedly back toward the first column.

**You should see and hear**
- Each press moves one column left and speaks "Row R of 4, column C of 3: …".
- From the **first cell of a row**, another Ctrl+Alt+Left says **"No more cells"**
  and the caret does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-03 — Table: Cell Below (`table.cell_below`, Ctrl+Alt+Down)

*What & why.* Drop straight down one row, staying in the same column — reading a
column top to bottom.

**Before you start**
- **`table.md`** open. Caret on the **Region** cell of the header row.

**Do this**
1. Press **Ctrl+Alt+Down** to walk down column 1: Region → North → South → East.
2. At East, press **Ctrl+Alt+Down** once more.

**You should see and hear**
- Each press moves down one row in the **same column** and speaks position +
  content, e.g. "Row 2 of 4, column 1 of 3: North".
- Below the last row it says **"No more rows"** (or **"No more rows, end of
  table"** if you are on the final cell of the final row); the caret stays put.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-04 — Table: Cell Above (`table.cell_above`, Ctrl+Alt+Up)

*What & why.* Move up one row in the same column — the mirror of TBL-03.

**Before you start**
- **`table.md`** open. Caret on the **East** row's Region cell (bottom of column 1).

**Do this**
1. Press **Ctrl+Alt+Up** to climb: East → South → North → Region.
2. On the header row, press **Ctrl+Alt+Up** once more.

**You should see and hear**
- Each press moves up one row and speaks position + content.
- Above the top row it says **"No more rows"** and the caret does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-05 — Table: First Cell (`table.first_cell`, Ctrl+Alt+Home)

*What & why.* Jump straight to the very first cell of the whole table (row 1,
column 1) from anywhere inside it.

**Before you start**
- **`table.md`** open. Caret somewhere in the middle of the table (e.g. the South
  row's Notes cell).

**Do this**
1. Press **Ctrl+Alt+Home**.

**You should see and hear**
- The caret lands on the top-left cell and QUILL says "Row 1 of 4, column 1 of 3:
  Region".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-06 — Table: Last Cell (`table.last_cell`, Ctrl+Alt+End)

*What & why.* Jump to the very last cell of the table (final row, final column).

**Before you start**
- **`table.md`** open. Caret anywhere inside the table.

**Do this**
1. Press **Ctrl+Alt+End**.

**You should see and hear**
- The caret lands on the bottom-right cell and QUILL says "Row 4 of 4, column 3
  of 3: Backordered".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-07 — Table: First Cell in Row (`table.row_start`, Alt+Home)

*What & why.* Jump to the start of the **current** row without leaving it.

**Before you start**
- **`table.md`** open. Caret in the **Notes** cell of the South row (column 3).

**Do this**
1. Press **Alt+Home**.

**You should see and hear**
- The caret jumps to column 1 of the **same** row and QUILL says "Row 3 of 4,
  column 1 of 3: South". The row does not change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TBL-08 — Table: Last Cell in Row (`table.row_end`, Alt+End)

*What & why.* Jump to the end of the **current** row. Use this scenario to also
prove the **escaped-pipe** cell stays whole.

**Before you start**
- **`table.md`** open. Caret in the **Region** cell of the **South** row (column 1).

**Do this**
1. Press **Alt+End** to reach the last cell of that row (the Notes column).
2. Then press **Ctrl+Alt+Left** once to land on the **Device** cell of the South
   row — the one holding `Phone \| Watch`.

**You should see and hear**
- Step 1: the caret jumps to column 3 of the same row: "Row 3 of 4, column 3 of
  3: Bundle SKU".
- Step 2: the Device cell is announced as **one cell** — "…column 2 of 3: Phone |
  Watch" — the escaped pipe `\|` is read as a literal pipe **inside** the cell and
  does **not** split it into an extra column. Position stays "column 2 of 3".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## REV-01 — Reveal Codes: Next Code (`reveal.next_code`)

*What & why.* With the Reveal Codes pane open, jump to the **next** hidden
formatting code (a bold-on, heading, link, list marker, …) and hear it named —
WordPerfect's "show me the codes" for a screen-reader user.

**Before you start**
- Open **`formatting.md`** (it is full of headings, bold/italic, a link and lists).
- Turn the pane on: press **Alt+F3** (**View menu ▸ Reveal Codes**). You should
  hear "Reveal Codes shown." A status hint mentions **F6** to move into the pane.
- Note: `reveal.next_code` has **no default shortcut**. Run it from the **Command
  Palette** (**Ctrl+Shift+P** → "Reveal Codes: Next Code"), or move into the pane
  with **F6** and arrow through the flowed codes directly.

**Do this**
1. Run **Reveal Codes: Next Code** (Command Palette), or press **Down/Right** in
   the pane after **F6**.

**You should see and hear**
- The pane selection advances to the next **code** token and QUILL **speaks the
  code phrase** (e.g. "Heading 1", "Bold on"); the editor caret follows to the
  matching spot. When there is nothing further it says **"Reveal Codes: no
  further code."** and stays put.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## REV-02 — Reveal Codes: Previous Code (`reveal.previous_code`)

*What & why.* The mirror of REV-01 — step to the **previous** code.

**Before you start**
- Same as REV-01: **`formatting.md`** open, Reveal Codes shown (**Alt+F3**), with
  the pane caret somewhere past the first code.

**Do this**
1. Run **Reveal Codes: Previous Code** (Command Palette), or press **Up/Left** in
   the pane.

**You should see and hear**
- Selection moves to the previous code and its phrase is spoken; the editor caret
  follows. Before the first code it says **"Reveal Codes: no earlier code."** and
  the caret stays put.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## REV-03 — Reveal Codes: Go to Matching Code (`reveal.go_to_pair`)

*What & why.* Formatting codes come in pairs (bold-on ↔ bold-off, list-start ↔
list-end). This jumps from one half of the pair to its partner, so you can see
exactly what a code encloses.

**Before you start**
- **`formatting.md`** open, Reveal Codes shown (**Alt+F3**). Put the pane
  selection on a **paired** code — e.g. a **Bold on** marker on a bold word.

**Do this**
1. Run **Reveal Codes: Go to Matching Code** from the **Command Palette**
   (**Ctrl+Shift+P**).

**You should see and hear**
- Selection jumps to the **partner** code (the matching "off") and QUILL speaks
  the landing code; the editor caret follows. On a code that has no partner the
  command does nothing rather than jumping somewhere wrong. **Note:** if nothing
  is spoken on an unpaired code, that is expected — confirm it did not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## REV-04 — Reveal Codes: Speak Codes Aloud (`reveal.toggle_speak`)

*What & why.* A verbosity switch. **Off** (the default) keeps your screen reader
as the single voice while you arrow through the flowed view — QUILL mirrors the
code phrase silently to the status bar so NVDA/JAWS don't double-speak. **On**
restores QUILL's own spoken narration of each code for people who prefer it.

**Before you start**
- **`formatting.md`** open, Reveal Codes shown (**Alt+F3**).

**Do this**
1. Run **Reveal Codes: Speak Codes Aloud** from the **Command Palette**
   (**Ctrl+Shift+P**). Then run it again to toggle back.

**You should see and hear**
- Turning it **on**: QUILL says **"Reveal Codes will speak codes aloud."** — now
  arrowing the flowed view speaks each code phrase in QUILL's voice as well.
- Turning it **off**: QUILL says **"Reveal Codes codes are now silent; your
  screen reader reads the line."** The setting persists across restarts.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NOTE-01 — Add Inline Note (`notes.add_inline_note`, Alt+Shift+I)

*What & why.* Attach a private note to the current line or selection — a margin
comment that is **anchored to the text** (it follows edits) and **saved per
document**, so it comes back when you reopen the file.

**Before you start**
- Open **`plain.txt`**. Put the caret on a line (or select a phrase) to anchor to.
- The note text you will type: **`Check this figure`**.

**Do this**
1. Press **Alt+Shift+I**, or **Navigate menu ▸ Sticky Notes ▸** the inline-note
   command.
2. In the note dialog, type **`Check this figure`**; activate **Save**.

**You should see and hear**
- The dialog is labelled and keyboard-complete. On Save, QUILL announces
  **"Inline note added."** and the status line shows the anchor text in quotes
  (e.g. `Inline note added on "…"`). Choosing **Cancel** (or saving an empty note)
  announces the add was cancelled and writes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NOTE-02 — Next Inline Note (`notes.next_inline_note`, Alt+Shift+J)

*What & why.* Jump the caret forward to the next inline note in the document and
hear it — walking your notes in order.

**Before you start**
- **`plain.txt`** open with **at least two** inline notes added (repeat NOTE-01 on
  two different lines). Put the caret above the first note.

**Do this**
1. Press **Alt+Shift+J** to advance to the next note; press again to continue.

**You should see and hear**
- The caret moves to the next note's anchored text and QUILL announces its
  position and summary, e.g. **"Inline note 1 of 2: Check this figure"**. Past the
  last note it **wraps** to the first. With no notes at all it says **"No inline
  notes in this document"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NOTE-03 — Previous Inline Note (`notes.previous_inline_note`, Alt+Shift+G)

*What & why.* The mirror of NOTE-02 — step to the previous note.

**Before you start**
- Same as NOTE-02: **`plain.txt`** with two or more inline notes; caret below the
  last note.

**Do this**
1. Press **Alt+Shift+G** to move back to the previous note; press again to continue.

**You should see and hear**
- The caret moves to the previous note and QUILL announces "Inline note N of M: …".
  Before the first note it **wraps** to the last. With no notes it says "No inline
  notes in this document".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NOTE-04 — Speak Inline Note / double-press to edit (`notes.speak_inline_note`, Alt+Shift+H)

*What & why.* Read the full text of the note **at the caret** aloud; press the key
**twice quickly** to open that note to view, edit, or delete it.

**Before you start**
- **`plain.txt`** open with an inline note; caret on the note's anchored line
  (use NOTE-02 to land on it first).

**Do this**
1. Press **Alt+Shift+H** once — listen.
2. Press **Alt+Shift+H twice in quick succession** (within about half a second).
3. In the editor dialog, change the text and **Save** — or use **Delete** — then
   run NOTE-04 again to confirm.

**You should see and hear**
- Single press: QUILL speaks **"Inline note: "** followed by the note's full text.
  With the caret **not** on a note it says "No inline notes in this document".
- Double press: the note opens in an edit dialog with **Delete** available.
  Saving announces **"Inline note updated"**; deleting announces **"Inline note
  deleted"**; Cancel changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NOTE-05 — Sticky Notes Browser… (`notes.sticky_browser`)

*What & why.* A searchable list of your **sticky notes** (the free-standing
notes, distinct from the inline notes above) that you can arrow, preview, and
open to edit — reachable even when QUILL is minimized to the tray.

**Before you start**
- Create at least one sticky note first via **New Sticky Note…**
  (`tools.sticky_note_capture`, **Ctrl+Shift+Grave** then **Shift+N**) so the
  browser has something to show.

**Do this**
1. Open **Navigate menu ▸ Sticky Notes ▸ Sticky Notes Browser…**, or run it from
   the Command Palette.
2. Type in the search box; arrow the results; open one to edit; **Escape** to close.

**You should see and hear**
- The dialog is keyboard-navigable and announced: a search field, a results list
  you can arrow with a spoken preview, and an edit path. Opening a note whose
  underlying note no longer exists is reported ("That note no longer exists.")
  rather than erroring. Escape returns focus to where you were.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## MISC-01 — Document Summary (`document.summary`, Alt+I)

*What & why.* A one-key spoken snapshot of where you are: file name, word and
line counts, headings, and whether there are unsaved changes.

**Before you start**
- Open **`formatting.md`** (it has headings). Optionally type one word so it shows
  as modified.

**Do this**
1. Press **Alt+I**.

**You should see and hear**
- QUILL speaks a single sentence in substance: the file name, then
  **`N words, M lines`**, then a heading count (e.g. "6 heading(s)"), and — if the
  document is dirty — **", unsaved changes."** An unsaved/new document is named
  "unsaved document". With nothing open it says "No document open".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## MISC-02 — Sync Folder with GitHub… (`sync.sync_folder`)

*What & why.* Point QUILL at any folder and it commits, pulls, and pushes it over
that folder's own git remote — the general-purpose half of QUILL Sync. It never
sets anything up silently: you always confirm before an `init` or a network call.

**Before you start**
- **Precondition:** the user's own **git** is installed and its credentials work
  (SSH key or the system git credential manager). A folder that is already a git
  repo with a remote is the simplest case; otherwise you will be asked for a repo
  URL. If you cannot supply either, mark **Blocked**.
- **Not available in Safe Mode** (it is network activity) — do not run this under
  `QUILL_SAFE_MODE=1`; there it simply reports it is disabled.

**Do this**
1. **Tools menu ▸ Sync ▸ Sync Folder with GitHub…** (or Command Palette).
2. In the folder picker, choose a folder; confirm.
3. If prompted, confirm the setup step (it tells you it will run `git init` and/or
   `git remote add origin <URL>`) and paste the repository URL.

**You should see and hear**
- The folder picker and any confirmation/URL prompts are labelled and
  keyboard-complete; a **No-defaulted** confirmation appears before any `init` or
  remote is added. Progress is announced; on success the result message is spoken.
  If there are **conflicts** they are listed by name in an accessible list
  (never auto-resolved) so you can fix them and sync again.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## MISC-03 — Suggest Document Metadata… (`ai.suggest_metadata`) **[GATED future.ai]**

*What & why.* Ask the configured AI to propose front-matter (title, summary,
tags, category), then accept or reject each field one at a time — the AI
proposes, you dispose, applied as a **single undo step**.

**Before you start**
- **[GATED]** This appears only when the **`future.ai`** flag is on (a dev/admin
  build). On a public 1.0 build it is absent — mark **N/A** and confirm its
  absence in `gated-absence.md`.
- **Precondition:** an AI connection is configured (AI Connection). If none, QUILL
  will prompt for it; if you cannot supply one, mark **Blocked**.
- Open a document with real prose (e.g. **`formatting.md`**), not empty.

**Do this**
1. Run **Suggest Document Metadata…** from the Command Palette (or its menu item).
2. In the **Review Metadata Suggestions** dialog, Tab through each proposed field;
   accept some and leave others; confirm with **OK**.

**You should see and hear**
- QUILL announces **"Asking the AI for metadata suggestions."** then opens a
  field-by-field review dialog that is labelled and keyboard-complete. Only the
  fields you accept are written into the front matter; a **No-defaulted**
  confirmation guards overwriting any non-empty existing field. On apply it
  announces how many fields were applied and names them, **as one undo step**. An
  empty document says "Document is empty - nothing to describe."; accepting
  nothing says "No metadata was applied; the document is unchanged."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## MISC-04 — Media: Sleep Timer… (`media.sleep_timer`) **[GATED core.radio]**

*What & why.* Set a countdown that fades out and stops the editor-embedded media
(Internet Radio / Podcasts) after N minutes and restores your volume — for
falling asleep to a stream.

**Before you start**
- **[GATED]** This lives in **Tools ▸ Media** and depends on the editor-embedded
  **Internet Radio / Podcasts**, which are **gated out** of the public 1.0 build.
  On a public build the Media submenu / this item is absent — mark **N/A** and
  confirm absence in `gated-absence.md`. It appears only in a dev/admin build with
  the media feature on.
- Start something playing (Internet Radio or a Podcast) so the timer has a target.

**Do this**
1. **Tools menu ▸ Media ▸ Sleep Timer…** (or Command Palette).
2. In the dialog, set a number of minutes (e.g. **15**); confirm.

**You should see and hear**
- The dialog is labelled and keyboard-operable. On confirm QUILL announces
  **"Sleep timer set for 15 minutes"** (matching your value). Setting **0** (or
  confirming with the timer cleared) cancels it with "Sleep timer cancelled".
  When the countdown reaches zero playback stops, the volume is restored, and
  QUILL announces **"Sleep timer: playback stopped, volume restored."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## MISC-05 — Media: Cancel Sleep Timer (`media.cancel_sleep_timer`) **[GATED core.radio]**

*What & why.* Cancel a running sleep timer before it fires.

**Before you start**
- **[GATED]** Same gating as MISC-04 — absent from a public build (mark **N/A**).
- A sleep timer currently **running** (set one via MISC-04 first).

**Do this**
1. Run **Media: Cancel Sleep Timer** from the Command Palette (or its menu item).

**You should see and hear**
- With a timer running, QUILL announces **"Sleep timer cancelled"** and playback
  is no longer scheduled to stop. With **no** timer running it says **"No sleep
  timer is running."** rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 22
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
