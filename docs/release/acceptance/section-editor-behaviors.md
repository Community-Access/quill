# Section — Editor and document behaviors (`core.editor` and the cross-cutting document features)

Everything the **document area itself** does that is *not* a single menu command: how
typing is echoed, how the caret and status bar report where you are, how QUILL keeps
your work safe (autosave, backups, crash recovery), how it reacts to what you type
(live spell-check, abbreviation expansion), and how it reads a file's encoding and
line endings when you open it. These are the behaviors a release must prove work **for
a real person, by keyboard and by ear** — they underpin every command in the other
sections. Finish **Part 0** first.

The individual File / Edit / Navigate / Format / Tools *commands* named here in
passing are signed off in their own sections (`section-file.md`, `section-edit.md`,
`section-navigate.md`, `section-format.md`, `section-tools-*.md`, `section-power.md`);
this section proves the **behaviors**, and cross-references those sections rather than
repeating them. Surface reference (label + shortcut) for every command id below is
`../../planning/signoff/SIGNOFF-editor.md` (namespaces `edit.*`, `navigate.*`,
`view.*`, `window.*`, `verbosity.*`, `format.*`, `power.*`, and `tools.*`). Read §2–§3
of `README.md` for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

**A note on feature profiles (read before you start).** A fresh install opens in the
**Essential** profile, where a few of the features below are *quiet* (present but low
key) or *off*. Where a scenario needs a feature that Essential turns off, its **Before
you start** says so and tells you how to turn it on — usually **Tools ▸ Preferences ▸
Profiles and Features** (enable the named feature individually), or switch to the
**Full Quill** profile to see everything at once. If a command is simply not in the
menu, open the **Command Palette** (**Ctrl+Shift+P**, see GS-10) and type its name.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, `formatting.md`, `encoding-cp1252.txt`, `line-endings-crlf.txt`.

---

## DOC-01 — Typing echoes as you write (`core.editor`)

*What & why.* The heart of the app: you type, and you hear what you typed. QUILL is
screen-reader-first, so it deliberately lets **your screen reader** echo the
characters and words while QUILL stays out of the way — no double-speaking.

**Before you start**
- A new empty document (**Ctrl+N**), focus in the editor. Your screen reader's typing
  echo set to speak characters and/or words (its default).
- Text to type: **`The quick brown fox jumps over the lazy dog.`**

**Do this**
1. Type the sentence slowly, listening after each word.
2. Press **Backspace** a few times and listen.
3. Press **Enter** and type a second line: `Second line.`

**You should see and hear**
- Each character (and/or word, per your screen reader's echo) is spoken **as you
  type**, by the screen reader. Backspace announces the deleted character. QUILL itself
  does **not** re-speak keystrokes or say "Modified" on every key — that would be
  noise over the screen reader. The editor is announced as a multi-line **Document**
  text area. Nothing is silent that should speak, and nothing double-speaks.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-02 — Caret movement and "where am I" (`core.editor`, `navigate.*`, `verbosity.*`)

*What & why.* Moving the caret must always tell you where you landed, and you must be
able to ask "where am I?" at any moment. QUILL keeps a live **Position** status cell
(line and column) and offers a spoken "Where Am I."

**Before you start**
- `plain.txt` open (three paragraphs). Focus in the editor.

**Do this**
1. Press **Ctrl+Home** (top), then **Down Arrow** and **Right Arrow** a few times,
   listening as the screen reader reads each line/character.
2. Press **End**, then **Ctrl+End** (end of document).
3. Run **Where Am I** — open the Command Palette (**Ctrl+Shift+P**), type
   `Where Am I`, and run **`verbosity.where_am_i`**. (It has no default shortcut.)

**You should see and hear**
- Arrowing reads each line/character back **exactly** as written, spoken by the screen
  reader. The **Position** status cell tracks the caret as **`Ln <line>, Col <column>`**
  (1-based) but is not spoken on every move — it is read when you focus the status bar
  (DOC-05) or run a status command (DOC-06).
- **Where Am I** speaks in substance **"Line <n> of <total>, column <c>"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-03 — The modified / unsaved marker (`core.editor`)

*What & why.* You must always be able to tell, by title bar and by tab, whether the
document has unsaved changes — the difference between "safe to close" and "you'll lose
work."

**Before you start**
- `plain.txt` open and **saved** (no unsaved changes).
- The default marker style is the word **`[modified]`**. (Settings can change it to an
  asterisk — see below.)

**Do this**
1. Read the window title (your screen reader's read-title command, e.g. **NVDA+T**).
   Note it shows the file name with **no** modified marker.
2. Type one character. Read the title again.
3. Press **Ctrl+S** (Save). Read the title again.
4. *(Optional surface check.)* Command Palette → run
   **`view.set_dirty_title_style`** / the "dirty title style" setting and switch to
   **asterisk**; type a character and confirm the marker becomes **` *`**.

**You should see and hear**
- Saved: title reads **`plain.txt - QUILL for All <version>`**, no marker.
- After typing: the title and the active tab both gain **` [modified]`** (e.g.
  `plain.txt [modified] - QUILL for All <version>`).
- After Save: the **`[modified]`** marker disappears from both title and tab.
- With the asterisk style, the marker is **` *`** instead; `asterisk_text` shows
  **` * [modified]`**. The style change is announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-04 — Multiple documents open at once, and switching between them (`window.*`)

*What & why.* Real work means several documents open together. QUILL holds them as
tabs and lets you move between them entirely by keyboard, announcing each switch. The
tab **strip** is hidden by default (the switching still works); you can reveal it.

**Before you start**
- Open three documents: `plain.txt`, `formatting.md`, `table.md` (open each with
  **Ctrl+O**).

**Do this**
1. Press **Ctrl+Tab** (**`window.next_document`**) a few times, then
   **Ctrl+Shift+Tab** (**`window.previous_document`**), listening to each switch.
2. Press **Alt+2** (**`window.go_to_document_2`**), then **Alt+1**, then **Alt+3** to
   jump directly to documents by number (**Alt+1**…**Alt+9**, **Alt+0** for the 10th).
3. Open a **new tab** with **Ctrl+T** (**`window.new_document_tab`**).
4. Reveal the tab strip: **Ctrl+Shift+Grave** then **Shift+T**
   (**`view.toggle_tab_control`**); press **F6** to reach the **Document Tabs** region
   and arrow across the tabs. Toggle it back off.
5. Open the **Window menu** (**Alt**, then arrow to **Window**) and confirm the open
   documents are listed at the bottom.

**You should see and hear**
- Each switch announces **"Switched to <name>"** and moves focus into that document's
  editor; the title bar and (if shown) the tab update. **Alt+N** jumps to that document
  or says **"No document <n> open"** if out of range. With only one document open,
  Next/Previous says **"Only one document open."**
- **Ctrl+T** opens a fresh untitled tab. Revealing the tab strip exposes a keyboard-
  reachable **Document Tabs** region (accessible name "Open documents"); each tab
  reads its file name plus the **`[modified]`** marker when dirty. The Window menu
  lists every open document.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-05 — Read the status bar by keyboard (`core.view`, `navigate.next_region`)

*What & why.* Screen readers do not automatically read a status bar. QUILL solves this
by making the status bar a **panel of focusable cells** you can Tab/arrow into and hear
one at a time — the primary way a screen-reader user reads caret position, counts,
format, encoding, and line endings.

**Before you start**
- `formatting.md` open with focus in the editor.

**Do this**
1. Press **F6** (**`navigate.next_region`**) repeatedly until the screen reader says
   you are on the **Status bar** region (Shift+F6 goes back).
2. On the status bar, press **Right Arrow** / **Left Arrow** to move between cells;
   **Home** / **End** jump to the first/last cell. Listen to each cell's name and
   value.
3. Press **Enter** (or **Space**) on the **Position** cell to activate it (this opens
   **Go To Line**); press **Escape** to cancel.
4. Press **Escape** on the status bar to return to the editor.

**You should see and hear**
- Entering the region is announced as **"Status bar"**; then each cell announces
  **"<label>, <value>"** — e.g. **"Position, Ln 1, Col 1"**, **"Word Count, N words"**,
  **"Format, Markdown"**. Enter activates a cell (Position → Go To Line). **Escape**
  returns to the editor with **"Returned to editor."** (A spoken help line is available
  via **Ctrl+Shift+H** describing the Left/Right/Enter/Escape keys.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-06 — Speak the document status in one keystroke (`navigate.speak_status_summary`)

*What & why.* Sometimes you just want a one-shot spoken summary of the current
document without walking every cell. The QUILL-key status summary does that.

**Before you start**
- `formatting.md` open and **saved**; then type one character so it is modified.

**Do this**
1. Press **Ctrl+Shift+Grave** (release), then **Q** (**`navigate.speak_status_summary`**;
   also **Speak &Status Summary** on the Navigate menu).
2. Press **Ctrl+S**, then run the summary again.

**You should see and hear**
- The summary speaks, in substance, the **document name**, its **path**,
  **"modified"** (before saving) or **"saved"** (after), and **"encoding <encoding>"**
  — e.g. *"formatting.md … modified. encoding utf-8."* then *"… saved. encoding utf-8."*
- **Note.** This command reads *document* status, not every status-bar cell; to hear
  individual cells (counts, line endings, etc.) use DOC-05.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-07 — The status-bar cells and choosing which to show (`tools.status_bar_settings`)

*What & why.* The status bar can show many facts about the document. Only a sensible
subset shows by default; you can add or remove cells. This proves the load-bearing
cells exist, read correctly, and are configurable.

**Before you start**
- `plain.txt` open **and saved to disk** (so the file-dependent cells appear).

**Do this**
1. Using DOC-05's method (F6 to the status bar, then arrows), confirm you can find and
   read these cells with correct values:
   - **Position** → `Ln <n>, Col <n>`   · **Word Count** → `<n> words`
   - **Format** → e.g. `Markdown`   · **Keyboard Mode** → `Insert`
2. Open **Tools ▸ Status Bar Layout…** (**`tools.status_bar_settings`**).
3. In the dialog, **add** the **Character Count**, **Encoding**, and **Line Endings**
   cells (they are hidden by default); confirm and return.
4. Re-read the status bar and find **Character Count** → `<n> chars`, **Encoding** →
   `utf-8`, **Line Endings** → `LF` (or `CRLF`).

**You should see and hear**
- Each cell reads its name and value as above. **Encoding** and **Line Endings** cells
  auto-appear for any saved document even before you add them; the Layout dialog is
  keyboard-complete and its changes take effect immediately and are announced.
- **Note.** By default the visible cells are Position, Page, Status Message, Word
  Count, Keyboard Mode, Tab Mode, and Format; Character Count, Line Count, Selection
  Length, Reading Time, Encoding, Line Endings, Spell Check, Autosave, and others are
  available to add.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-08 — Selection announcements and Select All (`edit.*`)

*What & why.* When you select text you must know **what** and **how much** you
selected. Plain Shift+arrow selection is left to your screen reader (so it isn't
double-spoken); QUILL adds spoken feedback for its own structural-selection commands
and for clearing a selection.

**Before you start**
- `plain.txt` open, focus in the editor, caret at the top (**Ctrl+Home**).

**Do this**
1. Hold **Shift** and press **Right Arrow** / **Down Arrow** to select a few words —
   listen (your screen reader announces the growing selection).
2. Press **Ctrl+A** (Select All) and listen.
3. Run **Select Line** (Command Palette → `Select Line`, **`edit.select_line`**), then
   **Select Paragraph** (**`edit.select_paragraph`**).
4. Press **Ctrl+Shift+A** (**`edit.unselect_all`**, Unselect All).

**You should see and hear**
- Plain Shift+arrow selection is announced by the screen reader ("selected …"). **Ctrl+A**
  selects the whole document (announced as all selected).
- QUILL's structural commands announce the scope **and word count** in substance —
  e.g. **"Selected line, N words"**, **"Selected paragraph, N words"**. **Unselect All**
  says **"Selection cleared."** If a **Selection Length** cell is shown it reads
  **`Sel <length>`** while a selection is active.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-09 — Autosave fires quietly, and the interval is adjustable (`tools.cycle_autosave_interval`)

*What & why.* QUILL protects unsaved work by snapshotting it in the background on a
timer — **silently**, so it never interrupts your writing — and you can change how
often it runs. The snapshots are what crash recovery (DOC-10) restores.

**Before you start**
- A new document (**Ctrl+N**); type a sentence but **do not save**.
- The default autosave interval is **30 seconds** (adjustable 5–600 s). The setting is
  **Autosave interval (seconds)** under **Tools ▸ Preferences/Settings ▸ Editing**.

**Do this**
1. Add the **Autosave** status cell (DOC-07) and read it — it shows the current
   interval, e.g. **`Autosave: 30 s`** (or `Autosave off` if disabled).
2. Type some text, then **stop typing and wait past the interval** (35+ seconds).
   Keep listening.
3. Run **Cycle Autosave Interval** (Command Palette → `Cycle Autosave Interval`,
   **`tools.cycle_autosave_interval`**) once or twice and read the Autosave cell again.

**You should see and hear**
- Waiting past the interval causes an autosave to happen with **no announcement and no
  interruption** — silence here is correct (autosave must never talk over you). The
  Autosave cell reflects the interval.
- **Cycle Autosave Interval** announces the new interval each time (e.g. a longer or
  shorter value) and the Autosave cell updates to match.
- **Note.** Autosave snapshots (up to the newest 10 per document) are written under
  the app data folder's `autosave\` directory; they are not the same as `.bak` backups
  (DOC-11). You confirm they actually restore in DOC-10.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-10 — Crash recovery: unsaved work is offered back on restart (`core.recovery`)

*What & why.* If QUILL exits uncleanly with an error, on the next launch it should
notice, and offer to restore your latest autosave snapshot — you should not lose work
to a crash.

**Before you start**
- **Precondition.** You must be able to induce a *real* crash (one that writes an
  ERROR / Traceback to the log). A clean **Task Manager "End task"** that leaves only
  normal heartbeat log lines is, by design, treated like a clean exit and will **not**
  trigger the offer — so a plain kill is not a valid test. If you have no way to force
  an actual crash, mark this **Blocked** and say so.
- **Safe Mode disables recovery** — do not run this under `QUILL_SAFE_MODE=1`.
- A new modified document with at least one autosave snapshot already taken (edit, then
  wait past the autosave interval, DOC-09).

**Do this**
1. With unsaved edits autosaved, cause QUILL to crash (or otherwise exit uncleanly with
   a logged error).
2. Launch QUILL again and wait for the first-run flow to settle.
3. Read the recovery dialog fully; choose **Restore Latest Snapshot**.

**You should see and hear**
- A dialog titled **"Crash Recovery"** appears, saying in substance **"Quill detected
  an unclean exit"** and offering **Restore Latest Snapshot**, **Open Logs Folder**,
  **Save Diagnostics…**, **Send Bug Report**, and **Skip Recovery**; it shows a
  read-only snapshot preview. It is fully keyboard-operable.
- **Restore** opens the recovered text as a **new, modified, untitled tab**, restores
  the caret position, and says in substance **"Recovered latest autosave snapshot."**
  **Skip** says **"Skipped crash recovery."**
- **Note.** This restores one *latest* snapshot per crashed session — it is not a
  "reopen all my tabs" prompt (that is the Session feature, `file.open_session`, see
  FILE-21/22).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-11 — Automatic backups on save (`core.recovery`; restore via FILE-11)

*What & why.* Every time you overwrite a file, QUILL first keeps a timestamped backup
of the previous on-disk content, so a bad save is recoverable. This proves backups are
created; restoring them is FILE-11.

**Before you start**
- `plain.txt` open and saved.

**Do this**
1. Type a change; press **Ctrl+S** (a backup of the *previous* content is taken).
2. Type another change; press **Ctrl+S** again (a second backup is taken).
3. Open **File menu ▸ Restore Backup…** (**`file.restore_backup`**; full steps in
   **FILE-11**).

**You should see and hear**
- The **Restore Backup** dialog ("Choose a backup to restore:") lists one or more
  **timestamped** `.bak` entries for this file, newest first, and is keyboard-
  navigable. Selecting one and confirming replaces the editor text and announces
  **"Restored backup <name>."** If a file was never saved-over there are no backups and
  QUILL says so plainly.
- **Note.** Backups are only taken on save when the document is modified, and are
  stored under the app data folder's `backups\` directory. The full Restore Backup
  command is signed off in **FILE-11**; here you are only proving backups get created.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-12 — Live spell-check surfaces a misspelling as you type (`view.toggle_spellcheck_as_you_type`)

*What & why.* When you type a word wrong, QUILL can flag it immediately — with a
**sound** (not speech, so it never talks over your screen reader) plus a status
message — and mark it visually.

**Before you start**
- **Precondition.** Live spell-check is **off by default**. Turn it on: Command Palette
  → `Toggle Spell Check As You Type` (**`view.toggle_spellcheck_as_you_type`**), or
  **Tools ▸ Preferences/Settings ▸ Editing ▸ Spell check as you type**. Also confirm
  **Announce spelling results** (Settings ▸ Accessibility) is on (its default).
- A new empty document. Word to type: a clear misspelling, **`teh`**, followed by a
  **space**.

**Do this**
1. Type **`teh`** then press **Space**.
2. Read the **Spell Check** status cell (add it via DOC-07 if needed).

**You should see and hear**
- Completing the misspelled word plays a short **spelling-alert sound** (an earcon, or
  a bell fallback) — *not* spoken words over your screen reader — and sets the status
  message **`Possible misspelling: "teh"`**. The word is also marked visually
  (underline). The **Spell Check** cell reads **`On`**.
- **Note.** The alert is suppressed inside URLs, e-mail addresses, and code spans/blocks,
  and a repeat of the same word within a moment is debounced. This is a background cue;
  navigation and correction are DOC-13.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-13 — Navigate to the next / previous misspelling (`tools.next_misspelling`, `tools.previous_misspelling`)

*What & why.* Finding your typos by ear: jump the caret from one misspelling to the
next, hearing each word, without needing to see the underlines.

**Before you start**
- A document containing at least two misspellings on different lines, e.g. type
  **`teh cat sat on the maat.`** on line 1 and **`Anothr line here.`** on line 2.
  Caret at the top (**Ctrl+Home**).

**Do this**
1. Press **Ctrl+F7** (**`tools.next_misspelling`**) — repeat to step through.
2. Press **Ctrl+Shift+F7** (**`tools.previous_misspelling`**) to go back.
3. Open the **Misspelling List** with **Alt+Shift+L** (**`tools.misspelling_list`**);
   arrow the list, then close it.
4. *(Cross-reference.)* The full guided **Spell Check…** dialog is **F7**
   (**`tools.spell_check_dialog`**) — signed off in the Tools/Speech section, not here.

**You should see and hear**
- Each **Next Misspelling** moves the caret to and **selects** the next misspelled
  word, gives it focus, and announces in substance **`Next misspelling: "<word>"`**.
  When none remain ahead it says **"No misspellings ahead; N misspellings behind"** (so
  silence never misleads you). Previous mirrors it. The Misspelling List is keyboard-
  navigable and announced.
- **Surface caveat.** Some in-app help text mentions **Ctrl+Period** for "next
  misspelling," but the shipping default keymap binds it to **Ctrl+F7**. If Ctrl+Period
  does nothing, that is the known text/keymap mismatch — record it under
  Surface-exact, and verify against the build's actual keymap.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-14 — Encoding detection on open (`core.text_encoding`; uses `encoding-cp1252.txt`)

*What & why.* Legacy files aren't always UTF-8. QUILL detects a non-UTF-8 text file,
opens it **correctly** (accents and symbols intact), and tells you it did so — never a
silent wall of mojibake.

**Before you start**
- The byte-exact sample **`encoding-cp1252.txt`** from `../qa-samples/` on disk. Its
  known content is: **`Café résumé — naïve façade. Prices in £ and €.`** saved in
  **Windows-1252**. Do not open-and-resave it in another editor first (that would
  rewrite the bytes).

**Do this**
1. Open **`encoding-cp1252.txt`** (**Ctrl+O**). Listen to the open announcement.
2. Read the document text (arrow through it) and check the accented characters and the
   **£** and **€** symbols.
3. Add and read the **Encoding** and **Line Endings** status cells (DOC-07).

**You should see and hear**
- On open QUILL announces / shows in the status message, in substance, **"Opened using
  cp1252 text encoding (not UTF-8)."** The text reads **correctly** —
  `Café résumé — naïve façade. Prices in £ and €.` — because QUILL detected the code
  page and decoded with it (it does **not** leave mojibake for you to fix).
- The **Encoding** cell reads **`cp1252`**; the **Line Endings** cell reads **`LF`**
  (this sample ends in LF).
- **Cross-reference.** To re-interpret a file in a chosen encoding by hand, use
  **File ▸ Choose Encoding…** (FILE-13). A clean UTF-8 file opens with **no** encoding
  announcement.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-15 — Line-ending detection on open (uses `line-endings-crlf.txt`)

*What & why.* Windows (CRLF) and Unix (LF) files must be recognized so the status bar
tells the truth and a later toggle/save writes the ending you expect.

**Before you start**
- The byte-exact sample **`line-endings-crlf.txt`** from `../qa-samples/` on disk:
  three lines (`Line one` / `Line two` / `Line three`) terminated with **CRLF**. Do not
  resave it elsewhere first.

**Do this**
1. Open **`line-endings-crlf.txt`** (**Ctrl+O**).
2. Add and read the **Line Endings** and **Encoding** status cells (DOC-07).
3. *(Cross-reference.)* Run **File ▸ Toggle Line Endings** (**`file.toggle_line_endings`**,
   FILE-14) and listen.

**You should see and hear**
- The **Line Endings** cell reads **`CRLF`**. Because this sample is pure ASCII it opens
  as **`utf-8`** with **no** encoding announcement (only the line-ending cell
  distinguishes it) — there is no spoken line-ending announcement on open.
- Toggling announces **"Line endings set to LF"** (then **"…set to CRLF"** on a second
  toggle); the cell updates, and the change is written on the next save.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-16 — Watch folder: drop a file in and it opens (`core.watch_folder`) [QUIET / off by default]

*What & why.* QUILL can monitor a folder and automatically open supported files that
appear in it — an "inbox" for documents. It is **off by default** and quiet by design
(no tick sound, no interrupting speech), so you must turn it on and point it at a
folder.

**Before you start**
- **Precondition.** Watch Folder is off by default and **never runs in Safe Mode**. You
  will enable it and create one profile.
- An empty scratch folder you can write to, e.g. `C:\WatchInbox`.
- A file to drop in later: a copy of **`plain.txt`**.

**Do this**
1. Open **Tools ▸ Watch Folder ▸ Watch Folder Profiles…** (**`tools.watch_folder_settings`**).
2. Add a profile: **Browse…** to `C:\WatchInbox`, leave the action at **Open in editor**,
   enable the profile, and confirm. (The default poll interval is ~5 seconds; files
   must settle ~2 seconds before they are picked up.)
3. Turn monitoring on: **Tools ▸ Preferences/Settings ▸ Watch Folders ▸ Enable folder
   watching** (the Tools ▸ Watch Folder ▸ Monitoring item routes you here). Confirm you
   hear monitoring start.
4. Copy **`plain.txt`** into `C:\WatchInbox` and wait several seconds.
5. Open **Tools ▸ Watch Folder ▸ Watch Folder Queue…** (**`tools.watch_folder_status`**)
   to read the queue.

**You should see and hear**
- Starting monitoring announces in substance **"Watch folder monitoring started (1
  profile)"** (or **"…on, but no profiles are enabled"** if you skipped step 2).
- Within a few seconds of the copy, `plain.txt` opens in a **new tab** and QUILL says
  **"Watch folder opened plain.txt."** The **Watch Folder Queue** dialog is keyboard-
  navigable and shows the file as done. A failure would announce **"Watch failed for
  <name>: <message>"** rather than being silent.
- **Note.** If you are testing a build where this feature is gated out, mark **N/A**.
  Turn monitoring back off after the test.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-17 — Markdown editing profiles change how Markdown is handled (`power.select_markdown_profile`)

*What & why.* QUILL can tune its Markdown handling to a named profile (Standard,
GitHub-style, Documentation, Poetry and Lyrics, and more), which governs deterministic
structure features like table-of-contents generation and single-line-break
preservation. This is the non-AI counterpart to the AI Table-of-Contents agent.

**Before you start**
- **Precondition.** In the Essential profile `core.markdown_profiles` is *quiet* (still
  reachable). If the Format ▸ Markdown items aren't visible, enable **Markdown Profiles
  and Extensions** via **Preferences ▸ Profiles and Features**, or use the Command
  Palette.
- `formatting.md` open (a Markdown document).

**Do this**
1. Open **Format ▸ Markdown ▸ Select Markdown Profile…** (**`power.select_markdown_profile`**;
   no default shortcut — use the menu or palette).
2. Choose **Poetry and Lyrics**; confirm. Listen.
3. Run **Format ▸ Markdown ▸ Read Markdown Processing Status**
   (**`power.read_markdown_status`**).
4. Toggle **Format ▸ Markdown ▸ Preserve Single Line Breaks**
   (**`power.toggle_preserve_line_breaks`**).

**You should see and hear**
- Selecting a profile announces in substance **"Markdown profile: Poetry and Lyrics. 1
  extension enabled. <description>."** (The profile names carry their full labels, e.g.
  **"Standard Markdown"**, **"GitHub-Style Markdown"**, **"PRD and Release Notes"**.)
- **Read Markdown Processing Status** speaks the same profile summary. **Preserve Single
  Line Breaks** announces **"Preserved single line breaks."**
- **Note.** Switching a profile stores the choice and changes how Markdown structure is
  generated/rendered (preview, export, TOC, line breaks); it does not reflow the text
  already in the editor. Insert Table of Contents (**`power.insert_table_of_contents`**)
  is signed off in `section-power.md`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-18 — Abbreviations expand as you type (`format.toggle_abbreviation_expansion`) [expansion off by default]

*What & why.* Type a short abbreviation and QUILL expands it to full text — a
writer-level speed feature. The **expansion behavior is off by default** (so nobody is
surprised by auto-changes); the feature and its manager are always reachable.

**Before you start**
- **Precondition.** Auto-expansion is off by default. Turn it on with **Insert ▸ Toggle
  Abbreviation Expansion** (**`format.toggle_abbreviation_expansion`**, chord
  **Ctrl+Shift+Grave** then **E**).
- A new empty document. Built-in abbreviation to use: **`btw`** (expands to
  **`by the way`**).

**Do this**
1. Enable expansion (chord above) and listen for the confirmation.
2. Type **`btw`** then press **Space**. Listen.
3. Immediately press **Backspace** once and listen.
4. Open **Insert ▸ Manage Abbreviations…** (**`format.manage_abbreviations`**, chord
   **Ctrl+Shift+Grave** then **Shift+A**); read the list; close it.

**You should see and hear**
- Enabling announces **"Abbreviation expansion on"**. Typing `btw` + Space replaces it
  with **`by the way `** and announces in substance **"Expanded: by the way"** (a short
  sound may also play). A single **Backspace** right after undoes it — announcing
  **"Expansion deleted"** (or **"Reverted to: btw"**, per the backspace-behavior
  setting).
- The **Manage Abbreviations** dialog is keyboard-complete, lists the built-ins
  (btw, asap, imo, imho, fwiw, …) and any you add, and closing it says **"Abbreviations
  updated."**
- **Note.** The trigger characters include Space, Enter, Tab, and common punctuation.
  Turn expansion back off afterward if you prefer.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-19 — Document analysis: word count and reading time (`tools.word_count`) [quiet in Essential]

*What & why.* A quick, accurate count of what you've written, plus an at-a-glance
reading-time estimate.

**Before you start**
- `formatting.md` open. (`core.analysis` is *quiet* in Essential but reachable; the
  command is in the menu and palette.)

**Do this**
1. Press **Ctrl+Shift+W** (**`tools.word_count`**, or **Tools ▸ Writing and Language ▸
   Word Count…**).
2. Read the dialog fully; close it (**Escape** / OK).
3. Add the **Reading Time** status cell (DOC-07) and read it.

**You should see and hear**
- The **Word Count** dialog reports **Words**, **Lines**, and **Characters** for the
  document, is fully readable by keyboard, and a spoken summary
  (**"Word count: N words"**) is given. The **Reading Time** cell reads e.g.
  **`<1 min read`** or **`N min read`** (about 200 words/minute).
- **Note (surface expectation).** The Word Count dialog reports **only Words / Lines /
  Characters** — there is **no** Flesch/readability score in this dialog. Line
  Statistics (**`power.compute_line_statistics`**) and Compare tools are separate
  `core.analysis` commands (see `section-power.md` / `section-tools-misc.md`).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-20 — Links: insert, follow, and copy (`edit.insert_link`, `edit.follow_link`) [quiet in Essential]

*What & why.* Writing and using hyperlinks by keyboard: build a link in the document's
own markup, follow the link under the caret to a browser, and copy its address.

**Before you start**
- `formatting.md` open — it contains one link labelled **QUILL project**. (`core.links`
  is *quiet* in Essential but reachable.)

**Do this**
1. Move the caret onto the **QUILL project** link text.
2. Press **Ctrl+Enter** (**`edit.follow_link`**) and listen (network optional — you can
   cancel the browser).
3. Open the editor **context menu** (Applications/Menu key or **Shift+F10**) and find
   the **Open Link** and **Copy Link Address** entries; choose **Copy Link Address**.
4. In a blank spot, press **Ctrl+Alt+K** (**`edit.insert_link`**); in the web form,
   Tab through **Display text** and **URL**, enter `Example` and `https://example.com`,
   and confirm.

**You should see and hear**
- With the caret on a link, **Follow Link** announces in substance **"Opening
  <host>…"** and opens the target (a bare anchor `#…` says anchors aren't supported;
  no link at the caret says **"No link at cursor"**).
- The context menu shows **`Open Link  "<target>"`** and **`Copy Link Address`**; Copy
  announces **"Copied link: <target>."**
- **Insert Link** opens a labelled Display-text + URL web form and inserts a link in the
  document's markup (Markdown `[Example](https://example.com)` here), announcing
  **"Inserted link (markdown)."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-21 — Notes anchored in the document: inline notes and sticky notes (`notes.*`, `core.notes`) [off by default]

*What & why.* Attach a private note to a place in the document and jump back to it
later — inline notes follow the text they're anchored to, and sticky notes are a
position-anchored list.

**Before you start**
- **Precondition.** `core.notes` (**Sticky Notes**) is **off in the Essential profile**,
  so its commands are hidden by default. Turn it on: **Preferences ▸ Profiles and
  Features**, enable **Sticky Notes**, or switch to **Full Quill**.
- `plain.txt` open.

**Do this**
1. Select a word or short phrase in the document.
2. Press **Alt+Shift+I** (**`notes.add_inline_note`**); type a note like `check this`;
   confirm.
3. Move the caret elsewhere, then press **Alt+Shift+J** (**`notes.next_inline_note`**)
   and **Alt+Shift+G** (**`notes.previous_inline_note`**).
4. Press **Alt+Shift+H** (**`notes.speak_inline_note`**) on the note; press it twice
   quickly to open the edit dialog.
5. Create a standalone sticky note: **Navigate ▸ Sticky Notes ▸ New Sticky Note…**
   (**`tools.sticky_note_capture`**, chord **Ctrl+Shift+Grave** then **Shift+N**).

**You should see and hear**
- Adding announces **"Inline note added."** (status shows the anchor phrase). Next/
  Previous jump the caret and announce **"Inline note <i> of <n>: <summary>"**, wrapping
  around, or **"No inline notes in this document"** if none. **Speak Inline Note** reads
  **"Inline note: <text>"**; a quick double-press opens an edit dialog whose Delete/OK
  announce **"Inline note deleted" / "Inline note updated."**
- The **New Sticky Note** dialog is keyboard-complete; sticky notes live under
  **Navigate ▸ Sticky Notes** (they are position-anchored, hence the Navigate menu).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-22 — Read the document back from the editor (`edit.read_all`, `edit.say_selected`) (`core.read_aloud`)

*What & why.* Beyond the screen reader's own reading, QUILL can read the whole document
or just your selection aloud with its chosen Read Aloud voice — driven straight from
the editor.

**Before you start**
- `plain.txt` open. (Full Read Aloud settings/voice are in the Tools/Speech section;
  here you prove the two editor-driven read-back commands.)

**Do this**
1. Press **Alt+F8** (**`edit.read_all`**) to read the whole document from the top;
   listen, then stop it (**Ctrl+Shift+Grave** then **Shift+R**, `tools.read_aloud_stop`).
2. Select a sentence, then press **Shift+Space** (**`edit.say_selected`**) in the editor.
3. With nothing selected, press **Shift+Space** again.

**You should see and hear**
- **Read All** moves to the top and reads the document aloud (announcing "Read aloud
  started"). **Say Selected** speaks the selected sentence; with no selection it says
  **"Nothing selected."**
- **Cross-reference.** Start/Pause (**Ctrl+Shift+Grave, R**), voice, speed, and Read
  Aloud settings are signed off in `section-tools-speech.md` — do not duplicate them
  here.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-23 — Type-ahead navigation, and how find works in the editor (`navigate.go_to_anything`)

*What & why.* QUILL's document search is a **dialog** (there is intentionally **no**
incremental "find-as-you-type" that jumps the caret while you type into the editor).
The type-ahead behavior lives in the navigator dialogs, which filter a list as you
type — this proves it and clears up the expectation.

**Before you start**
- `formatting.md` open (it has six headings H1–H6).

**Do this**
1. Open **Go to Anything** / **Quick Nav**: **Ctrl+Shift+Grave** then **G**
   (**`navigate.go_to_anything`**). Focus lands in a filter field.
2. Type a few letters of a heading and listen as the list narrows; arrow to a result
   and press **Enter** to jump there.
3. *(Cross-reference.)* Confirm ordinary find is the dialog: press **Ctrl+F**
   (**`edit.find`**) — signed off in `section-edit.md` — and **Escape** it.

**You should see and hear**
- The Go to Anything field filters its list **as you type** (debounced), announcing the
  changing result set; Enter jumps the caret to the chosen target. Typing into the
  **editor** does *not* silently start a search or move the caret — Find is only via the
  Ctrl+F dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## DOC-24 — Encoding requirements and minimum encoding (`core.text_encoding`) [power tools]

*What & why.* Before publishing text to a picky target, you may need to know which
non-ASCII characters a document contains and the simplest encoding that can hold it
without loss. This is the manual "prepare text for the web" toolset (distinct from the
open-time detection in DOC-14).

**Before you start**
- **`encoding-cp1252.txt`** open (it contains accented letters and the £/€ symbols).
  These commands live under the `power.*` namespace; enable **Text Encoding and HTML
  Entities** via Profiles and Features if the items aren't visible.

**Do this**
1. Run **Analyze Encoding Requirements** (Command Palette →
   `Analyze Encoding Requirements`, **`power.analyze_encoding_requirements`**).
2. Read the report of non-ASCII characters.
3. *(Cross-reference.)* Run **Save Using Minimum Required Encoding**
   (**`power.save_minimum_encoding`**) — full sign-off in `section-power.md`.

**You should see and hear**
- The analysis lists each non-ASCII character (with position and name) and states the
  **minimum required encoding** in substance, e.g. **"Minimum required encoding:
  Windows-1252 / MS-ANSI."** The surface is keyboard-navigable and announced.
- **Note.** This toolset also converts non-ASCII to HTML entities and finds non-ASCII
  characters; those commands are enumerated in `section-power.md`. Here you are
  confirming the analysis behavior works and is accessible.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 24
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
