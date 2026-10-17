# Editor completion checks: measured before, measured after

Status: built 2026-10-16 on the overnight branch, from Jeff's todo "Editor and
media completion checks" items 37 (persistent read-only reading), 41 (faster
opening and truthful extension-driven Save As) and 45 (named-text startup and
multiword list search). The user-facing descriptions are in the QUILL user
guide (Chapter 3, "The name you type decides"; Chapter 8, "Reading without
changing anything"; Chapter 4, "Finding a snippet by name"), the QUILL Lite
guide (the same three topics) and the Inkwell guide (section 4). Manual
screen-reader checks are listed, not yet checked, in
`docs/qa/screen-reader-checks-2026-10.md`.

The rule for this work was: measure first, change only what the measurement
blames, and prove each gap with a test before closing it.

## How the numbers were taken

Every number below comes from `scripts/bench_editor_completion.py`, run from a
source checkout on the development machine (Intel Core Ultra class, 16 logical
processors, Windows 11, Python 3.14.8, wxPython 4.3), with the worktree on
`PYTHONPATH`:

```text
python scripts/bench_editor_completion.py reading --runs 3 --megabytes 8
python scripts/bench_editor_completion.py open --runs 3
python scripts/bench_editor_completion.py lists --runs 3 --entries 10000
```

- **Cold** is a fresh Python process: importing QUILL and the reader's
  libraries, then one read. That is what the first open after starting the app
  pays. **Warm** is a second read in the same process: every later open.
  Figures are medians of three.
- The reading and list sections build QUILL's real controls (the Rich Edit
  surface, a `wx.ListBox`, a report `wx.ListCtrl`, the new virtual list) in
  memory and never show them. Nothing is typed or clicked, so the script is
  safe beside a running screen reader.
- The fixtures are generated: an 8 MB Markdown book with 2,500 headings; a
  1,500-paragraph `.docx` written with python-docx; a 60-page text PDF written
  with PyMuPDF; and an OLE2 header named `.doc`, because no Word 97 file can be
  written from Python without Word or LibreOffice. The `.doc` figure is
  therefore the time to the *answer* (converted, or a sentence naming what is
  missing), which is what a person waits through.

**Installed and portable builds are for Jeff to measure.** They import from a
frozen bundle, so their cold numbers differ. The method by hand: start the
app, open the same kind of file with File > Open, and time from Enter to the
first line being read (a stopwatch is fine; the differences here are seconds).
Do it twice, the second time without restarting, for cold and warm. Note
which optional parts are installed (Download Optional Components, LibreOffice).

## Item 37: a long document, guarded

| Measure (8 MB, 2,500 headings) | Before | After |
|---|---:|---:|
| Read the file from disk | 11.0 ms | 11.0 ms |
| Put it in the editor (`SetValue`) | 394 ms | 394 ms |
| `SetEditable(False)` (the guard itself) | 0.02 ms | 0.02 ms |
| Copy the text out of the editor (`GetValue`) | 46.1 ms | 46.1 ms |
| Compare two copies of the text | 0.66 ms | 0.66 ms |
| One browse-navigation step, guarded | 46.3 ms | 0.04 ms |

**What this says.** Making the control read-only proves nothing about speed,
and the table shows why: the guard costs 0.02 ms and changes no other figure.
Opening is dominated by `SetValue`, which the guard cannot touch. The one cost
the guard *could* remove was in navigation: every browse key (next heading,
paragraph, link) called `GetValue` to check the cached structure was still
current, which on 8 MB is the whole 46 ms of each keypress. A guarded document
cannot change, so `BrowseModeMixin._browse_text` checks once that
`document.text` equals the control's text and then answers with that string,
which the cache recognises by identity. The check is dropped whenever the
guard is toggled or re-applied, and a mismatch falls back to the control.
Unguarded documents are unchanged.

**Gaps the tests proved, and closed.**

1. No keyboard toggle. `power.toggle_read_only_guard` was a menu row with no
   key. It is now **Ctrl+Alt+Backspace** in both editors (rule 2; free in both;
   every Ctrl+Alt+Shift letter is a family show/hide or taken; Ctrl+Alt with a
   sign is AltGr typing on European layouts; no default JAWS, NVDA or Narrator
   command uses it; `menu_lint._CTRL_ALT_DOCUMENTED` records why).
2. The memory missed a File Explorer open. Keys were the raw path string, so
   `D:\Books\Long Book.md` from Open Recent and `d:\books\long book.md` from
   the shell were two files. `quill/core/read_only_guards.py` keys through
   `DocumentMemory.key_for`, the normalisation bookmarks, positions and notes
   already used, and normalises older lists as it reads them.
3. A failed save was swallowed (`except OSError: pass`) while the toggle said
   "Document is read-only" as if it would be remembered. `ReadOnlyGuards.set`
   returns the reason and the sentence says it.
4. Commands bypassed the guard. A read-only control still obeys programmatic
   writes, so Insert Snippet, the line tools and Copy Tray pastes changed a
   guarded document. QUILL's two shared write paths raise
   `DocumentReadOnlyError`, and `CommandRegistry.set_read_only_refusal` turns
   it into "Document is read-only" at every entry point (keys, palette,
   hotkeys, voice) before the command can announce success. QUILL Lite refuses
   `TEXT_CHANGING_HANDLERS` by name at the menu, status-cell and palette
   dispatch. Word-tool Replace checks at the moment it would write.
5. QUILL Lite had no guard at all; it now has QUILL's, through the shared
   module. Bookmarks and inline notes stay available in both (a note goes
   beside the file while the guard is on).

## Item 41: opening .doc, .docx and PDF

| Format (fixture) | Cold import | Cold read, before | Warm read, before | Cold read, after | Warm read, after | Engine |
|---|---:|---:|---:|---:|---:|---|
| `.docx` (40 KB, 1,500 paragraphs) | 247 ms | 11,979 ms | 857 ms | AFTER_DOCX_COLD | AFTER_DOCX_WARM | MarkItDown |
| PDF (33 KB, 60 pages) | 280 ms | 4,474 ms | 3,191 ms | AFTER_PDF_COLD | AFTER_PDF_WARM | pdfplumber |
| `.doc` (OLE2 header; no LibreOffice) | 292 ms | 11,639 ms, then a raw `UnsupportedFormatException` | 138 ms | AFTER_DOC_COLD | AFTER_DOC_WARM | the missing-LibreOffice sentence |

Dependencies on this machine: markitdown, magika, onnxruntime, python-docx,
PyMuPDF and pypdf present; LibreOffice missing.

**Slow conversion or a missing dependency?** Both, and they are now told apart.

- **`.docx` is slow on a cold start, not missing anything.** `python -X
  importtime -c "import markitdown"` puts 11 to 14 seconds in the import alone:
  MarkItDown imports pandas (3.2 s), pdfminer (2.5 s), openpyxl (1.1 s),
  python-pptx (0.7 s) and the Magika model (1.2 s) before converting anything.
  The conversion itself is the 0.86 s warm figure. The order that decides
  MarkItDown-first for `.docx` is in `quill/io/structured.py`, which another
  agent was changing during this work and which this change was told not to
  touch. **Recommended next step there:** read `.docx` with python-docx first
  (already a base dependency and already the fallback, about one second to
  import) and keep MarkItDown for the formats only it reads, or prewarm it on a
  background thread after startup when Office files are in Recent Documents.
- **`.doc` was missing a dependency, and paid the slow cost to find out.**
  MarkItDown has no `.doc` converter, so the open spent the whole import to be
  told so, then raised MarkItDown's own exception, which none of the callers'
  fallbacks caught: the person heard a library message instead of the sentence
  naming LibreOffice. `quill/io/markitdown_bridge.py` now answers `.doc` and
  `.ppt` without importing MarkItDown, and turns MarkItDown's exception family
  into `ValueError` so every caller falls through to LibreOffice or the
  missing-tool sentence.
- **PDF is conversion time, per page.** pdfplumber spends about 50 ms a page
  warm; the reader is `quill/io/pdf.py`, also another agent's file today.
  Progress and Cancel are unchanged: QUILL and QUILL Lite already read in the
  background with a progress message.
- Office-in-shipped-builds (whether the installed runtime carries MarkItDown,
  Magika and onnxruntime) is Jeff's open decision; the runtime spec is
  unchanged.

**Save As.** QUILL's resolver already let the typed extension win; the new
behavioural test drives `save_file_as` with the real writers and reads the
results back in their real formats, so that is now proved rather than
assumed. QUILL Lite was the gap: it wrote plain text under a `.docx` name. It
now refuses Word names on Save As (before its rich-to-plain question), Save and
the collector's quiet save, naming Rich Text as what Word opens. The PDF
original-protection and export-only guard is unchanged in both.

## Item 45: named-text lists

| Measure (10,000 snippets, 4.5 MB) | Before | After |
|---|---:|---:|
| Import, cold | 167 ms | AFTER_IMPORT |
| Load the library, cold | 25.9 ms | AFTER_LOAD_COLD |
| Load the library, warm | 24.4 ms | AFTER_LOAD_WARM |
| Filter one keystroke (median over "meeting notes") | 6.5 ms | AFTER_FILTER |
| Matches for "notes meeting" | 157 (one order only) | AFTER_MATCHES (either order) |
| Fill the picker's list with all 10,000 | 3,063 ms | not done any more |
| Fill the picker's list with what it now shows | n/a | AFTER_PICKER |
| Fill the Abbreviations report list, 10,000 rows | 3,755 ms | AFTER_VIRTUAL (virtual) |
| Same, with Freeze/Thaw (considered, not used) | 2,377 ms | |
| Load 10,000 abbreviations | 32.8 ms | AFTER_ABBR |

**What this says.** Loading and filtering were never the problem: 25 ms and
6.5 ms for ten thousand entries. Putting rows into a native list was, at a
quarter to a third of a millisecond a row, paid on opening and again after
every key that left thousands of matches. So:

- The searchable picker (`quill/ui/searchable_picker.py`, moved out of
  `main_frame.py`) shows at most 200 rows, says how many matched in its status
  line *and* in the list's accessible name, and for libraries larger than that
  refills 150 ms after the last key; Enter and the arrows flush a pending
  refill first, so they never act on a stale list. Small lists behave exactly
  as before.
- The Abbreviations manager, shared by QUILL, QUILL Lite and Inkwell, became a
  virtual list (`quill/ui/virtual_report_list.py`): a refill is a row count
  and a repaint. Windows' own type-ahead keeps working: the list view asks for
  row text through `LVN_ODFINDITEM`, which wx answers (checked in process with
  `LVM_FINDITEMW`: "meeting n" found its row). Its selection is now kept by
  identity when the search changes.
- Multiword search (`quill/core/list_search.py`) doubled the filter cost to
  12.8 ms a key at 10,000 entries, well under a frame, in exchange for finding
  "Notes from the meeting" from "meeting notes".

**The Space gap.** `apply_listbox_activation`, used by more than a hundred
lists, opened the selected row on Space. Typing "meeting notes" in a list
reached "Meeting..." on the M and then *opened* it at the space. The glue now
feeds printable keys to the shared `TypeAheadBuffer` (which had no caller
until now); while a name is being typed (within 1.2 s of the last key) Space
is part of the name, and a longer name stays on the row it reached instead of
hopping to the next match. Enter and Escape keep their meanings, and Space
after a pause opens the row as before. "No match for X" is said through the
shared announcer when nothing starts with what was typed.

## What is not done

- The `.docx` cold-start cost lives in `quill/io/structured.py`; the measured
  recommendation is above, for after the other agent's work lands.
- PDF per-page cost lives in `quill/io/pdf.py`, likewise.
- Installed and portable build timings, by the method above.
- Every manual screen-reader check in `docs/qa/screen-reader-checks-2026-10.md`.
