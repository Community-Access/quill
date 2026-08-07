# QUILL 1.0.0 — Core-Journey Test Plan (hand-held)

Rigorous, end-to-end validation of QUILL's critical editor journeys, each keyed to
a known sample file in `qa-samples/`. Where the screen-reader plan
(`screen-reader-test-plan.md`) proves a single fix is announced, this plan proves
a whole task works from start to finish, on a real build, by ear and by keyboard.

How to use this plan:
- Test with **NVDA and JAWS** on a real Windows build (Narrator where noted). Run
  each journey twice: once **keyboard-only with the mouse unplugged**, then again
  reading with the screen reader's review/virtual cursor.
- Copy the whole `qa-samples/` corpus onto the machine first. Every step names the
  exact sample file it opens; do not substitute your own document.
- Record **Pass / Fail / Blocked / Not tested** and the **actual spoken text** for
  each case. "Expected" describes the intended announcement; exact wording varies
  by screen reader, but the field name, role, state, and the load-bearing values
  (counts, cell contents, format labels) must be present and correct.
- A case fails if focus is lost, a value is wrong, an outcome is silent, an error
  is not announced, or the produced file does not match the "Expected" structure.

General keyboard contract to confirm throughout: Tab / Shift+Tab move predictably,
Escape cancels, Enter activates the default, and focus returns to a sensible place
when a dialog closes. No destructive action happens without a confirmation you can
hear.

Preconditions common to every journey (confirm once, per environment):
- A packaged 1.0.0 build installed per the master sign-off §A environment matrix.
- NVDA or JAWS running and speaking.
- The `qa-samples/` folder present on a local disk; note its full path here: ______.
- AI configured with a working provider **only** for JOURNEY-005 (Improve Reading
  Order); all other journeys run with AI off.

---

## JOURNEY-001 — Open and heading navigation

Sample: `formatting.md` (six headings, one of each level H1–H6, in order).

- TC-001a — Open the document
  - Precondition: no document open, or a scratch document.
  - Steps: File > Open (`file.open`, `Ctrl+O`); pick `qa-samples/formatting.md`;
    confirm the dialog with Enter.
  - Expected: the file opens; focus lands in the editor, announced as "Document",
    edit/text-area role, multi-line (screen-reader TC-EDIT-001); the title bar
    reads `formatting.md - QUILL ...` with no "[modified]" marker.
- TC-001b — Walk all six heading levels forward
  - Steps: place the caret at the top (`Ctrl+Home`). Invoke **Next Heading**
    (`navigate.next_heading`, Navigate menu) six times; then use the screen
    reader's own quick key `H` from the top as a cross-check.
  - Expected: each invocation lands on the next heading in turn and announces the
    heading text and its level — "Heading One — Formatting Sample, heading level
    1", then level 2, 3, 4, 5, 6. All six are reached; a seventh invocation
    reports no further headings rather than wrapping silently.
- TC-001c — Walk headings backward
  - Steps: from the last heading (level 6), invoke **Previous Heading**
    (`navigate.previous_heading`) five times; cross-check with `Shift+H`.
  - Expected: headings are announced in descending order level 6 → level 1; the
    caret lands on each heading line; no level is skipped or repeated.
- TC-001d — Confirm the inline styles read correctly
  - Steps: read the first paragraph under Heading One with the review cursor;
    place the caret in each styled word and invoke **Describe Formatting at
    Cursor** (`format.describe_formatting`, `Ctrl+Shift+D`).
  - Expected: **bold** reads/announces as bold, *italic* as italic, `underline`
    as underlined, `strike` as strikethrough — each state named, none silent.

## JOURNEY-002 — Table cell navigation

Sample: `table.md` (caption sentence, then a 3-column table: header row + 3 body
rows; the South row's Device cell holds the literal pipe `Phone \| Watch`).

- TC-002a — Enter the table and read the first cell
  - Steps: open `qa-samples/table.md`; place the caret on the header row; press
    **Ctrl+Alt+Right** (`table.next_cell`).
  - Expected: the landing announcement leads with position then content —
    "Row 1 of 4, column 2 of 3: Device" (the table is 4 rows including the
    header). Position is spoken as well as the cell value.
- TC-002b — The escaped pipe stays one cell
  - Steps: navigate to the South row's Device cell (row 3): from the header,
    Ctrl+Alt+Down twice to reach row 3, then Ctrl+Alt+Right to column 2 as
    needed.
  - Expected: the Device cell announces as **one** cell containing "Phone | Watch"
    — the escaped pipe `\|` is read as a literal pipe inside the cell and does
    **not** split it into two columns. Position stays "column 2 of 3".
- TC-002c — "End of row" vs "end of table"
  - Steps: from any body row's last cell (Notes column), press **Ctrl+Alt+Right**.
    Then navigate to the final cell of the final row (East / Backordered) and
    press **Ctrl+Alt+Right** again; also press **Ctrl+Alt+Down** there.
  - Expected: at a non-final row's last cell, Ctrl+Alt+Right announces
    **"No more cells"** (the row ends, the table does not). At the final cell of
    the final row, Ctrl+Alt+Right announces **"No more cells, end of table"** and
    Ctrl+Alt+Down announces **"No more rows, end of table"**. The caret does not
    move past the edge in either case.
- TC-002d — Chord outside a table is harmless
  - Steps: move the caret up into the caption sentence above the table; press
    Ctrl+Alt+Right.
  - Expected: QUILL says the caret is not in a table and leaves it where it is —
    no crash, no jump.

## JOURNEY-003 — Save-As format fidelity

Sample: `formatting.md`. Verifies the CHANGELOG fidelity promise: headings, lists,
links, the image, and a table survive Save-As to Word and HTML.

- TC-003a — Save As Word (.docx)
  - Steps: with `formatting.md` open, File > Save As (`file.save_as`,
    `Ctrl+Shift+S`); switch the type to Word Document; name it `formatting.docx`;
    Enter.
  - Expected: the converting-Save-As announcement speaks, in substance: "Saved as
    formatting.docx, Word format. You are still editing QUILL text; each save
    converts it to Word." The title bar updates to `formatting.docx` with no
    "[modified]"; a second `Ctrl+S` saves silently with no dialog.
  - Expected (open the file in Word): all six headings map to Word heading styles
    1–6; the bullet and numbered lists are real Word lists; the **QUILL project**
    link is a live hyperlink; the image carries alt text "Red circle"; bold /
    italic / underline / strikethrough are applied to the right words.
- TC-003b — Save As HTML (.html)
  - Steps: from the same document, Save As with type HTML; name it
    `formatting.html`; Enter.
  - Expected: the status line speaks the HTML format label; a standalone HTML
    page is written. Opening it in a browser shows an `<h1>`…`<h6>` outline, a
    `<ul>` and an `<ol>`, a `<blockquote>`, a fenced block as `<pre><code>`, the
    link as an `<a href>`, and an `<img alt="Red circle">`.
- TC-003c — Round-trip a table's header row
  - Steps: open `qa-samples/table.md`; Save As Word (`table.docx`); open in Word.
  - Expected: the 3-column table is a **real, editable Word table with a
    repeating header row**; the `Phone | Watch` cell is a single cell; no column
    split from the escaped pipe.
- TC-003d — Nothing is dropped silently
  - Steps: repeat TC-003a but Save As to a format that cannot hold rich
    formatting (e.g. plain `.txt` via `file.save_as_plain_text`).
  - Expected: QUILL tells you before committing what will be dropped (per the
    Links-in-plain-text setting), rather than dropping it silently.

## JOURNEY-004 — Insert Equation and math reading

Sample: `math.md` (two inline `\(...\)` equations, one `$$...$$` block, one MathML
block).

- TC-004a — Insert an inline equation
  - Steps: open a scratch document; place the caret in a sentence; Insert
    Equation (`edit.insert_equation`, `Ctrl+Shift+E`); type `E=mc^2`; when the
    mode step appears, choose **Inline**.
  - Expected: a mode step (inline vs block) is offered and announced; on confirm,
    `\(E=mc^2\)` is inserted at the caret in QUILL's default inline delimiters.
- TC-004b — Insert a block equation
  - Steps: repeat Ctrl+Shift+E; type `\int_0^1 x^2 \, dx = \frac{1}{3}`; choose
    **Block**.
  - Expected: the formula is inserted wrapped in a single-line `$$...$$` block.
- TC-004c — MathML is inserted verbatim, no mode step
  - Steps: copy the `<math>...</math>` block from `math.md`; Ctrl+Shift+E and
    paste the MathML fragment.
  - Expected: the MathML is inserted verbatim with **no** inline/block mode step
    (it is already complete markup).
- TC-004d — Re-invoke on a selected LaTeX equation
  - Steps: in `math.md`, select the text of an existing `\(...\)` equation and
    press Ctrl+Shift+E.
  - Expected: the delimiters are stripped and the bare formula pre-fills the
    prompt for editing.
- TC-004e — Read the math aloud
  - Steps: place the caret in the block equation; run "Read this part aloud".
  - Expected: with the optional MathCAT engine installed, the equation is spoken
    as natural-language math (integral from 0 to 1 of x squared…); without it,
    the built-in template reading speaks it and nothing errors. Note which path
    ran.

## JOURNEY-005 — Improve Reading Order (AI)

Sample: `reading-order.txt` (a four-step recipe printed out of order, one step
broken across a mid-sentence line break; the file states the intended order).

- TC-005a — Precondition and confirm-before-send
  - Precondition: AI configured with a working provider; not Safe Mode.
  - Steps: open `qa-samples/reading-order.txt`; Tools > Improve Reading Order
    (`tools.ai_reading_order`).
  - Expected: a confirmation dialog appears **before anything is sent**, naming
    the provider and the approximate size — in substance: "QUILL will send this
    document — about 1 page — to <provider name> to repair its reading order …
    The result opens as a new, unsaved document; your current document is not
    changed …. Send the document now?" Default is No. Cancelling announces
    "Improve Reading Order cancelled — nothing was sent."
- TC-005b — Run it and check the result opens unsaved
  - Steps: re-run and confirm Yes; wait for completion.
  - Expected: a progress status speaks ("Improving reading order… this can take a
    moment."); on success a **new, unsaved** document opens, announced in
    substance "Reading order improved — opened as a new unsaved document (Save As
    to keep it)." The original `reading-order.txt` is unchanged on disk and in its
    tab.
- TC-005c — Wording is preserved, order is fixed
  - Steps: read the new document top to bottom.
  - Expected: the four steps read in order **First → Second → Third → Fourth**,
    the broken "Third … steep …" step is rejoined into one sentence, and the
    wording matches the intended order recorded in the sample (no invented or
    dropped words). The tester's note block at the bottom of the sample is not
    treated as a step.
- TC-005d — Safe Mode and size guard
  - Steps: relaunch with `--safe-mode` and invoke the command; separately, lower
    `reading_order_max_pages` in Settings below the document's size and invoke it.
  - Expected: in Safe Mode it says it is unavailable and sends nothing; over the
    page limit it refuses with the over-limit message and sends nothing.

## JOURNEY-006 — Find, Replace, and Regex Helper

Sample: `formatting.md`.

- TC-006a — Find and Find Next
  - Steps: open `formatting.md`; Find (`edit.find`, `Ctrl+F`); search `Heading`;
    Enter; then Find Next (`edit.find_next`, `F3`) repeatedly.
  - Expected: matches are found, counted, and announced; F3 steps through each
    "Heading" occurrence and reports position; at the end it reports wrap or
    end-of-document, not silence.
- TC-006b — Replace and Replace All
  - Steps: Replace (`edit.replace`, `Ctrl+H`); replace `Oranges` with `Lemons`
    (single); then Replace All (`edit.replace_all`, `Ctrl+Shift+H`) `Heading`
    with `Section`.
  - Expected: the single replace changes exactly one word; Replace All announces
    the count of replacements (six headings → six changes); a single Undo
    (`Ctrl+Z`) reverts the bulk replace cleanly.
- TC-006c — Regex Helper builds a valid pattern
  - Steps: Tools > Regular Expression Helper (`tools.regex_helper`); build a
    pattern that matches an ordered-list item (e.g. `^\d+\. `); apply it in
    Replace with regex mode on; then feed an **invalid** regex.
  - Expected: the helper is keyboard/SR navigable and its fields are named; the
    valid pattern matches the three ordered-list lines; the invalid regex is
    reported as an error and does not crash.

## JOURNEY-007 — Read Aloud

Sample: `plain.txt` (baseline) and `formatting.md`.

- TC-007a — Start and pause
  - Steps: open `plain.txt`; Read Aloud Start/Pause
    (`tools.read_aloud_start_pause`, `Ctrl+Shift+Grave, R`); press it again to
    pause.
  - Expected: QUILL speaks the document with the configured Read-Aloud voice
    (distinct from the screen reader); the second press pauses; state is
    announced, not silent.
- TC-007b — Stop is immediate
  - Steps: start Read Aloud, then Read Aloud Stop
    (`tools.read_aloud_stop`, `Ctrl+Shift+Grave, Shift+R`).
  - Expected: speech stops immediately; a subsequent Start begins again from the
    document start or caret per the Read Aloud setting.
- TC-007c — Markup is spoken sensibly
  - Steps: open `formatting.md`; Read Aloud from the top.
  - Expected: markup and the URL are spoken as sensible words/pauses, not as raw
    syntax character-by-character; the fenced code block is read as code, not as
    backtick noise.

## JOURNEY-008 — Open from URL and paste-path robustness

Sample: `plain.txt` (as the local comparison), plus a small text URL you provide.

- TC-008a — Open from URL confirms before writing
  - Precondition: network available; a small plain-text URL staged.
  - Steps: File > Open from URL (`file.open_url`); paste the URL; proceed.
  - Expected: the host and expected size are confirmed **before** any download;
    nothing writes to disk before you confirm; a blocked/unreachable host is
    reported clearly, not silently.
- TC-008b — Pasting a file path does not misfire
  - Steps: copy the full local path to `qa-samples/plain.txt`; in the Open-from-
    URL field (and in the editor), paste it.
  - Expected: a local path pasted into the URL field is handled gracefully (opened
    as a local file or reported as not a URL), and pasting a path **into the
    editor** inserts it as text — it does not silently trigger a network fetch.
- TC-008c — Paste HTML as Markdown
  - Steps: open `qa-samples/sample.html` in a browser and copy its rendered body;
    in a scratch QUILL document, Paste HTML as Markdown
    (`power.paste_html_as_markdown`, `Ctrl+Shift+Grave, M`).
  - Expected: clean Markdown is inserted — an `#` heading "Trip Checklist", a
    `-` list of three items, a Markdown table (Day/City with two rows), the
    **QUILL project** link, and an image with alt "Red circle" — not raw HTML
    tags.

## JOURNEY-009 — Plain-text round-trip and HTML import (baseline)

Sample: `plain.txt`, `sample.html`.

- TC-009a — Plain text round-trip is byte-faithful
  - Steps: open `plain.txt`; without editing, Save As a new `.txt` (e.g.
    `plain-copy.txt`); reopen the copy and compare.
  - Expected: the reopened copy matches the original **character for character**
    (including line breaks); no partial or zero-byte file is ever written.
- TC-009b — HTML import yields navigable structure
  - Steps: File > Open `qa-samples/sample.html`.
  - Expected: the document opens with a readable heading ("Trip Checklist"), the
    three-item list, the two-column table (Day/City) navigable with the table
    chords from JOURNEY-002, the **QUILL project** link, and the image alt
    "Red circle" — all as navigable text.

---

## Sign-off

- Tester:
- Screen reader(s) and version(s):
- Build / commit tested:
- Environment (per master sign-off §A: E1–E6):
- Date:
- Journeys attempted (range) / total 9:
- Release blockers found (must be zero to ship):
- Overall result: Pass / Pass-with-notes / Fail
- Notes:
