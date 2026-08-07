# Section — Power-user commands (`power.*`, 75 commands)

The **power tools**: keyboard-first text surgery, encoding and HTML utilities,
line transforms, abbreviation expansion, and small conveniences that a
long-time editor user reaches for daily. None of these needs the mouse, the
network, or AI (two exceptions are flagged below). Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `power.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/
Accessible boxes.

**How these commands are reached.** After the menus.md re-shuffle the power
tools live where a user expects them, spread across **Insert**, **Edit**,
**File**, **Format**, **Navigate**, **Search**, and a cohesive
**Tools ▸ Advanced** submenu. Each scenario gives the exact menu path. **Every**
one of them is also in the **Command Palette** — open it and type the command's
name — so if a menu path has moved, the palette is the fallback and you should
fail **Surface-exact** for the menu, not **Works**.

Most transforms follow one rule worth learning once: **if you have a selection,
the command acts on the selection; if nothing is selected, it acts on the whole
document.** Where a command instead opens its result in a **new untitled
buffer** (reports, extracts, hex dumps), the scenario says so.

Common inputs used below (copy the `../qa-samples/` folder onto the machine
first): `plain.txt`, `formatting.md`, `table.md`, `sample.html`,
`data.csv`, `encoding-cp1252.txt`, `line-endings-crlf.txt`,
`compare-original.txt`.

---

## POW-01 — Insert Special Character (`power.insert_special_character`, Shift+F2)

*What & why.* Insert any Unicode character by its code point when you cannot type
it — an em dash, a Greek letter, an arrow.

**Before you start**
- `plain.txt` open; put the caret somewhere in the text.
- Input: the code point **`2014`** (that is EM DASH, `—`).

**Do this**
1. Press **Shift+F2**, or **Insert menu (Alt, I) ▸ Special Character…**.
2. In the **"Unicode code point (hex, d-prefix for decimal, or U+):"** field type
   **`2014`**; press **Enter**.

**You should see and hear**
- An em dash **`—`** is inserted at the caret and the status/announcement reads
  **"Inserted U+2014"**. Hex is the default; `d8212` (decimal) or `U+2014` are
  also accepted. A nonsense value is rejected with a spoken error, not a crash.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-02 — Insert File Content (`power.insert_file_content`)

*What & why.* Drop the text of another file into the current document at the
caret, without leaving the editor.

**Before you start**
- A new empty document; caret at the start.
- You will insert **`plain.txt`** from `qa-samples`.

**Do this**
1. **Insert menu ▸ File Content…**.
2. In the file dialog, choose **`plain.txt`**; press **Enter**.

**You should see and hear**
- The three paragraphs of `plain.txt` appear at the caret; the announcement reads
  **"Inserted contents of plain.txt"**. QUILL auto-detects the text encoding
  (UTF-8 / UTF-16 / Latin-1 fallback), so accented text comes in readable.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-03 — Insert Table of Contents (`power.insert_table_of_contents`)

*What & why.* Build a table of contents straight from the document's headings —
no AI, always exactly matching the headings present.

**Before you start**
- Open **`formatting.md`** (it has one heading of each level, H1–H6). Put the
  caret at the very top.

**Do this**
1. **Insert menu ▸ Table of Contents**.

**You should see and hear**
- A TOC built from the six ATX headings is inserted; the announcement reads
  **"Inserted table of contents (6 headings)"**. On a document with no headings
  it does nothing and says **"No headings were found to build a table of
  contents"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-04 — Insert Image… (`power.insert_image`, Ctrl+Alt+I)

*What & why.* Insert an image with **mandatory alt text** (or an explicit
"decorative" choice) — the one insertion path built so no image ships unlabelled.

**Before you start**
- `formatting.md` open (a Markdown document, so the result is Markdown image
  syntax). Caret on a blank line. Have any image file path ready (the
  `red-circle.png` reference from the samples is fine even if the binary is
  absent).

**Do this**
1. Press **Ctrl+Alt+I**, or **Insert menu ▸ Image…**.
2. In the dialog, choose an image file; type alt text **`Red circle`** in the
   Alt-text field (or tick **Decorative**); confirm.

**You should see and hear**
- Every field is labelled and keyboard-reachable; the Alt-text field is required
  unless Decorative is ticked. On confirm, Markdown image markup with the alt text
  is inserted and the status reads **"Image inserted (md)."** (In an HTML document
  the dialog offers width/height/caption and the status reads **"…(html)."**) If
  an AI provider is connected, a **Suggest alt text** control may appear — that
  part is **[GATED]** on AI and may be marked **Blocked**; the manual path must
  still work.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-05 — Snippet Gallery… (`power.open_snippet_gallery`, Ctrl+Shift+Grave then Shift+G)

*What & why.* Browse reusable snippets contributed by Quillin extensions and
insert one at the caret.

**Before you start**
- Any document open. The chord is a two-step: press **Ctrl+Shift+Grave**, release,
  then **Shift+G**. (Grave is the backtick key, top-left.)

**Do this**
1. Open the command via the chord, or **Insert menu ▸ Snippet Gallery…**.
2. Arrow through the **Gallery snippets** list; read the **Preview**; press
   **Insert** (Enter) on one, or **Escape** to cancel.

**You should see and hear**
- A dialog with a labelled snippet list, a read-only **Preview** pane, and
  **Insert / Cancel** buttons — all keyboard-reachable. Insert drops the snippet
  at the caret. If no Quillin contributes gallery snippets, the command says
  **"No gallery snippets are available."** rather than opening an empty dialog
  (mark **N/A** for the gallery if your build ships none).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-06 — Paste HTML as Markdown (`power.paste_html_as_markdown`, Ctrl+Shift+Grave then M)

*What & why.* Convert rich HTML on the clipboard (copied from a web page) into
clean Markdown and paste it at the caret.

**Before you start**
- Open a web page or `sample.html` in a browser and **copy** a chunk that
  includes a heading, a list, and a link, so the clipboard carries real HTML.
- New empty Markdown document; caret at the start. Chord: **Ctrl+Shift+Grave**,
  release, then **M**.

**Do this**
1. Trigger the command via the chord, or **Edit menu (Alt, E) ▸ Paste HTML as
   Markdown**.

**You should see and hear**
- The HTML is converted to Markdown (headings become `#`, lists become `-`/`1.`,
  links become `[text](url)`) and inserted at the caret; the status reads
  **"Pasted HTML as Markdown"**. If the clipboard has only plain text it is treated
  as HTML; an empty clipboard says **"Clipboard is empty"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-07 — Paste Markdown as HTML (`power.paste_markdown_as_html`)

*What & why.* The reverse of POW-06: turn Markdown on the clipboard into an HTML
body fragment and paste it.

**Before you start**
- Copy a few lines of Markdown (e.g. `# Title` and `- one`/`- two`) to the
  clipboard. New empty document; caret at the start.

**Do this**
1. **Edit menu ▸ Paste Markdown as HTML**.

**You should see and hear**
- Rendered HTML (`<h1>`, `<ul><li>…`) is inserted at the caret using the same
  renderer as preview/export; the status reads **"Pasted Markdown as HTML"**. An
  empty clipboard says **"Clipboard is empty"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-08 — New Document from Clipboard (`power.new_document_from_clipboard`)

*What & why.* Open whatever text is on the clipboard as a brand-new document.

**Before you start**
- Copy any block of text to the clipboard.

**Do this**
1. **File menu (Alt, F) ▸ New Document from Clipboard** (it sits beside New), or
   the Command Palette.

**You should see and hear**
- A new untitled document opens containing the clipboard text, with focus in the
  editor; the status reads **"New document from clipboard"**. If the clipboard was
  empty, an empty document opens and the status reads **"New document (clipboard
  was empty)"** — never an error.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-09 — Expand Abbreviation (`power.expand_abbreviation`)

*What & why.* Emmet-style expansion: type a shorthand like `ul>li*3` and expand it
into full HTML (or CSS) in place. A fast way to scaffold markup.

**Before you start**
- Open a new document and **Save As `scratch.html`** (the `.html` suffix puts
  expansion in HTML mode; a `.css` file switches it to CSS mode).
- Type the abbreviation **`ul>li*3`** and leave the caret right after it.

**Do this**
1. **Edit menu ▸ Expand Abbreviation**.

**You should see and hear**
- The abbreviation just before the caret is replaced with an unordered list
  containing three `<li>` items; the status reads **"Abbreviation expanded"**. An
  unrecognized abbreviation reports a clear message (e.g. a syntax error or
  **"Unknown CSS abbreviation"**) and changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-10 — Preview Abbreviation… (`power.preview_abbreviation`)

*What & why.* See what an abbreviation would expand to **without** touching the
document — a safe dry run.

**Before you start**
- Same `scratch.html` open. Input abbreviation: **`div.card>h2+p`**.

**Do this**
1. **Edit menu ▸ Preview Abbreviation…**.
2. Type **`div.card>h2+p`** in the **Abbreviation:** field; confirm.

**You should see and hear**
- The expansion opens in a **new untitled buffer** titled *Abbreviation preview*;
  your original document is untouched. An empty entry says **"Enter an
  abbreviation to preview"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-11 — Explain Abbreviation… (`power.explain_abbreviation`)

*What & why.* Plain-language description of what an abbreviation means — a
learning aid for the Emmet syntax.

**Before you start**
- Same `scratch.html` open. Input: **`ul>li*3`**.

**Do this**
1. **Edit menu ▸ Explain Abbreviation…**.
2. Type **`ul>li*3`**; confirm.

**You should see and hear**
- A new untitled buffer titled *Abbreviation explanation* opens describing the
  structure in words (an unordered list with three list items). Empty entry says
  **"Enter an abbreviation to explain"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-12 — Rename Current File… (`power.rename_current_file`)

*What & why.* Rename the file on disk from inside QUILL, keeping the document open
under its new name.

**Before you start**
- Make a throwaway copy of `plain.txt` named **`rename-me.txt`** and open it
  (so you are not renaming a shared sample).

**Do this**
1. **File menu ▸ Rename Current File…**.
2. In **New file name:** type **`renamed.txt`**; confirm.

**You should see and hear**
- The file is renamed on disk, the title bar updates, and the status reads
  **"Renamed to renamed.txt"**. If the target name already exists it refuses with
  **"A file named renamed.txt already exists"**. An unsaved/untitled document says
  **"Save the document before renaming it"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-13 — Delete Current File… (`power.delete_current_file`)

*What & why.* Delete the current file from disk and close its tab — guarded by a
confirmation you can hear and cancel.

**Before you start**
- Open the throwaway **`renamed.txt`** from POW-12 (or another disposable copy).

**Do this**
1. **File menu ▸ Delete Current File…**.
2. Read the warning **"Delete renamed.txt from disk? This cannot be undone."**;
   choose **No** first (nothing happens), then repeat and choose **Yes**.

**You should see and hear**
- **No** cancels with the file intact. **Yes** deletes the file, closes the tab,
  and the status reads **"Deleted renamed.txt"**. An unsaved document says
  **"This document has not been saved to disk"** instead of erroring. The **No**
  button is the safe default.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-14 — Send as Email… (`power.send_as_email`)

*What & why.* Hand the selection (or whole document) to your mail client as the
body of a new message.

**Before you start**
- `plain.txt` open; select a sentence (or select nothing to send the whole
  document). A default mail client configured on the machine. If none, mark
  **Blocked**.

**Do this**
1. **File menu ▸ Send as Email…**.

**You should see and hear**
- Your mail client opens a new message with the content as the body (rendered per
  the *content handoff format* setting) and the document name as the subject; the
  status reads **"Opened your mail client with this content as the body."** An
  empty document says **"Nothing to send: the document is empty."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-15 — Copy as Email Body (`power.copy_as_email_body`)

*What & why.* The practical alternative to POW-14 for long text: put the rendered
content on the clipboard so you can paste it into a compose window (many clients
truncate a long `mailto:` body).

**Before you start**
- `plain.txt` open; select some text or nothing (whole document).

**Do this**
1. **File menu ▸ Copy as Email Body**.

**You should see and hear**
- The rendered content lands on the clipboard and the status reads **"Copied to
  the clipboard as an email body."** Paste into any editor to confirm. An empty
  document says **"Nothing to copy: the document is empty."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-16 — Number Lines… (`power.number_lines`, Alt+Shift+N)

*What & why.* Prefix each line with a running number — quick numbered output for a
list or a log.

**Before you start**
- New document; type five short lines (`alpha`, `bravo`, `charlie`, `delta`,
  `echo`), one per line. No selection numbers all lines; a selection numbers only
  the selected lines.

**Do this**
1. Press **Alt+Shift+N**, or **Format menu (Alt, O) ▸ Number Lines…**.
2. In **Start numbering at:** accept **`1`** (or type another start); confirm.

**You should see and hear**
- Each line gains a running number starting at 1; the status reads **"Numbered
  lines"**. A non-numeric start says **"Start value must be a whole number"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-17 — Number Lines (Advanced)… (`power.number_lines_advanced`)

*What & why.* Numbering with full control: start, increment, digits or Roman
numerals, zero-padding, custom suffix, and left/right justification.

**Before you start**
- Same five-line document as POW-16 (undo the numbering first, or start fresh).

**Do this**
1. **Format menu ▸ Number Lines (Advanced)…**.
2. In the form set **Start = 1**, **Increment = 1**, **Number style = Roman
   numerals**, **Zero-pad = 0**, **Text after the number = `. `**, **Justify =
   Left**; press **Number**.

**You should see and hear**
- A keyboard-navigable form with labelled fields; on confirm the lines are prefixed
  `I. `, `II. `, `III. `… and the status reads **"Numbered lines"**. Non-numeric
  Start/Increment/pad values say **"Start, increment, and pad width must be whole
  numbers"**. Cancel says **"Number Lines (Advanced) cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-18 — Hard-Wrap Lines… (`power.hard_wrap_lines`)

*What & why.* Insert real line breaks so no line is wider than a chosen column —
for plain-text email or fixed-width output.

**Before you start**
- New document; type one long paragraph (one line, well over 40 characters).

**Do this**
1. **Format menu ▸ Hard-Wrap Lines…**.
2. In **Wrap width:** type **`40`**; confirm. (The default offered is the widest
   line's width.)

**You should see and hear**
- The paragraph is broken into lines no wider than 40 characters; the status reads
  **"Hard-wrapped at 40 characters"**. Zero or negative width says **"Wrap width
  must be greater than zero"**; non-numeric says it must be a whole number.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-19 — Delete Paragraph (`power.delete_paragraph`)

*What & why.* Remove the whole paragraph the caret is in, in one stroke.

**Before you start**
- `plain.txt` open (three paragraphs). Put the caret in the middle paragraph.

**Do this**
1. **Format menu ▸ Delete Paragraph**.

**You should see and hear**
- The paragraph under the caret is removed; the status reads **"Deleted
  paragraph"**. The remaining two paragraphs stay intact and the caret lands
  sensibly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-20..23 — Delete to bounds (`power.delete_to_line_start`, `power.delete_to_line_end`, `power.delete_to_document_start`, `power.delete_to_document_end`)

*What & why.* Four "delete from the caret to an edge" commands: to the start or end
of the current line, or to the top or bottom of the document.

**Before you start**
- `plain.txt` open. Before each, position the caret in the middle of a word (for
  the line variants) or in the middle paragraph (for the document variants).

**Do this** (Format menu ▸ each item; run one, undo with **Ctrl+Z**, run the next)
1. **Delete to Line Start** — announces **"Deleted to start of line"**.
2. **Delete to Line End** — announces **"Deleted to end of line"**.
3. **Delete to Document Start** — announces **"Deleted to top of document"**.
4. **Delete to Document End** — announces **"Deleted to bottom of document"**.

**You should see and hear**
- Each removes exactly the text between the caret and the named edge and speaks the
  matching phrase above; **Ctrl+Z** restores it each time.

**Sign off (Delete to Line Start)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Delete to Line End)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Delete to Document Start)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Delete to Document End)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-24 — Update Outline Numbering (`power.apply_auto_outline_numbering`)

*What & why.* Number every heading by its nesting level as literal text (1, 1.1,
1.2, 2 …) — a real outline you can read and search, driven by the *Auto Outline
Style* setting (numeric or legal).

**Before you start**
- Open **`formatting.md`** (headings H1–H6). This command always acts on the whole
  document.

**Do this**
1. **Format menu ▸ Update Outline Numbering**.

**You should see and hear**
- Each heading gains a literal outline number matching its level; the status reads
  **"Outline numbering updated."** A document with no headings says **"No headings
  to number."** A read-only document says **"Document is read-only"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-25 — Remove Outline Numbering (`power.remove_auto_outline_numbering`)

*What & why.* Strip the literal numbers POW-24 added, returning the headings to
their bare text.

**Before you start**
- `formatting.md` still showing the numbers from POW-24.

**Do this**
1. **Format menu ▸ Remove Outline Numbering**.

**You should see and hear**
- The numbers are removed and the status reads **"Outline numbering removed."** If
  there is nothing to remove it says **"No outline numbering to remove."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-26 — Shuffle Lines (`power.shuffle_lines`)

*What & why.* Randomly reorder the lines of the selection (or document) — handy for
randomizing a list.

**Before you start**
- New document; type five distinct lines (`one` … `five`).

**Do this**
1. **Format menu ▸ Shuffle Lines**.

**You should see and hear**
- The same five lines come back in a random order (no lines added or lost); the
  status reads **"Shuffled lines"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-27..29 — Sort lines (`power.sort_lines_numeric`, `power.sort_lines_by_date`, `power.sort_lines_by_length`)

*What & why.* Three sorts tuned for real data: by numeric value (not string order),
by the date each line contains, and by line length.

**Before you start**
- **Numeric:** type lines `10`, `2`, `33`, `4`. **Date:** type lines
  `2026-03-01`, `2025-12-25`, `2026-01-15`. **Length:** type lines `aaaa`, `a`,
  `aa`. (Run each on its own small document.)

**Do this** (Format menu ▸ each item)
1. **Sort Lines Numerically** → **"Sorted lines numerically"**.
2. **Sort Lines by Date** → **"Sorted lines by date"**.
3. **Sort Lines by Length** → **"Sorted lines by length"**.

**You should see and hear**
- Numeric sort yields `2, 4, 10, 33` (numeric, so `10` is **not** before `2`).
  Date sort yields chronological order (day-first vs month-first follows your
  spell-check locale for ambiguous dates). Length sort yields `a, aa, aaaa`. Each
  speaks its matching phrase.

**Sign off (Sort Numerically)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Sort by Date)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Sort by Length)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-30 — Keep Unique Lines (`power.keep_unique_lines`, Alt+Shift+K)

*What & why.* Remove duplicate lines, keeping the first occurrence of each
(case-sensitive).

**Before you start**
- New document; type `apple`, `banana`, `apple`, `cherry`, `banana` (five lines,
  two duplicates).

**Do this**
1. Press **Alt+Shift+K**, or **Format menu ▸ Keep Unique Lines**.

**You should see and hear**
- Only `apple`, `banana`, `cherry` remain (first occurrences kept, in order); the
  status reads **"Kept unique lines (removed duplicates)"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-31 — Delete Lines Containing… (`power.delete_lines_containing`)

*What & why.* Filter out every line matching a regular expression.

**Before you start**
- New document; type `keep 1`, `drop this`, `keep 2`, `drop that`. Input regex:
  **`drop`**.

**Do this**
1. **Format menu ▸ Delete Lines Containing…**.
2. In **Regular expression:** type **`drop`**; confirm.

**You should see and hear**
- The two `drop…` lines are removed, `keep 1`/`keep 2` remain; the status reads
  **"Deleted lines containing pattern"**. An invalid regex reports **"Invalid
  pattern: …"** and changes nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-32 — Delete Lines Not Containing… (`power.delete_lines_not_containing`)

*What & why.* The inverse of POW-31: keep only lines that match, delete the rest.

**Before you start**
- Same four-line document (`keep 1`, `drop this`, `keep 2`, `drop that`). Input
  regex: **`keep`**.

**Do this**
1. **Format menu ▸ Delete Lines Not Containing…**.
2. In the field (labelled **"Regular expression (keep matching lines):"**) type
   **`keep`**; confirm.

**You should see and hear**
- Only the two `keep…` lines remain; the status reads **"Kept only lines
  containing pattern"**. An invalid regex reports **"Invalid pattern: …"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-33 — Trim Blank Lines (`power.trim_blank_lines`, Ctrl+Shift+Enter)

*What & why.* Collapse runs of blank lines so the document is tidy.

**Before you start**
- New document; type three lines with **two blank lines between** each pair.

**Do this**
1. Press **Ctrl+Shift+Enter**, or **Format menu ▸ Trim Blank Lines**.

**You should see and hear**
- Excess blank lines are removed; the status reads **"Trimmed blank lines"**. The
  three text lines survive.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-34 — Strip HTML Tags (`power.strip_html_tags`)

*What & why.* Remove HTML markup, leaving the readable text.

**Before you start**
- Open `sample.html` (or paste some HTML into a new document).

**Do this**
1. **Format menu ▸ Strip HTML Tags**.

**You should see and hear**
- Tags such as `<h1>`, `<li>`, `<a>` are gone and only the text remains; the status
  reads **"Stripped HTML tags"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-35..36 — HTML entities (`power.decode_html_entities`, `power.encode_html_entities`)

*What & why.* Convert between HTML entities and their characters — decode
`&amp;`/`&lt;` back to `&`/`<`, or encode the reverse.

**Before you start**
- **Decode:** type `Tom &amp; Jerry &lt;3`. **Encode:** type `Tom & Jerry <3`.

**Do this** (Format menu ▸ each item)
1. **Decode HTML Entities** → **"Decoded HTML entities"**.
2. **Encode HTML Entities** → **"Encoded HTML entities"**.

**You should see and hear**
- Decode turns `&amp;`→`&` and `&lt;`→`<`. Encode turns `&`→`&amp;` and
  `<`→`&lt;`. Each speaks its matching phrase; running one then the other returns
  the original.

**Sign off (Decode HTML Entities)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Encode HTML Entities)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-37 — Convert Non-ASCII to HTML Entities (`power.encode_all_non_ascii`)

*What & why.* Replace every non-ASCII character with its HTML entity so the file
becomes pure ASCII — safe for systems that mangle Unicode.

**Before you start**
- Open **`encoding-cp1252.txt`** as UTF-8 (it has `é`, `£`, `€`, etc.). Select all,
  or leave unselected for the whole document.

**Do this**
1. **Format menu ▸ Convert Non-ASCII to HTML Entities**.

**You should see and hear**
- A brief progress announcement (this runs on a background thread so QUILL and the
  screen reader stay responsive), then every accented/currency character becomes a
  numeric or named HTML entity; the status reads **"Converted non-ASCII characters
  to HTML entities"**. A read-only document says **"Document is read-only"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-38 — Show Non-ASCII Characters… (`power.show_non_ascii`)

*What & why.* Open a read-only report listing every non-ASCII character with its
line and column — a map of what a legacy encoding cannot hold. Pairs with POW-39
and POW-40 to jump between the report and the source.

**Before you start**
- Open **`encoding-cp1252.txt`** (read as UTF-8 so the accents are present).

**Do this**
1. **Format menu ▸ Show Non-ASCII Characters…**.

**You should see and hear**
- A **new untitled buffer** titled *Non-ASCII characters* opens, one entry per
  offending character in a `line:column` + character layout, keyboard-navigable and
  readable by the screen reader.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-39 — Jump to Source Line (`power.non_ascii_jump_to_source`)

*What & why.* From an entry in the Non-ASCII report, jump to that exact line in the
original document.

**Before you start**
- The report from POW-38 open; put the caret on one of its `line:column` entries.

**Do this**
1. **Format menu ▸ Jump to Source Line**.

**You should see and hear**
- Focus switches to the source document's tab and moves to the referenced line. If
  the current line is not a `line:column` entry it says so; if you have not run
  Show Non-ASCII it says **"Run Show Non-ASCII Characters first."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-40 — Jump Back to Non-ASCII Report (`power.non_ascii_jump_to_report`)

*What & why.* The return trip: from the source document back to the report tab.

**Before you start**
- Having just done POW-39, you are now in the source document.

**Do this**
1. **Format menu ▸ Jump Back to Non-ASCII Report**.

**You should see and hear**
- Focus returns to the *Non-ASCII characters* report tab. If the report is closed
  it says **"No Non-ASCII report is open. Run Show Non-ASCII Characters first."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-41 — Analyze Encoding Requirements (`power.analyze_encoding_requirements`)

*What & why.* Report the document's current encoding versus the **minimum**
encoding that would still hold every character losslessly.

**Before you start**
- Open **`encoding-cp1252.txt`** (has non-ASCII) or `plain.txt` (pure ASCII) to
  contrast the two.

**Do this**
1. **Format menu ▸ Analyze Encoding Requirements**.

**You should see and hear**
- A **new untitled buffer** titled *Encoding requirements* opens describing the
  current encoding and the simplest encoding that would still be lossless (ASCII
  for `plain.txt`; a wider encoding for the accented file).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-42 — Save Using Minimum Required Encoding… (`power.save_minimum_encoding`)

*What & why.* Write a copy in the simplest encoding that still holds all the text
— the actionable follow-up to POW-41.

**Before you start**
- `encoding-cp1252.txt` open.

**Do this**
1. **Format menu ▸ Save Using Minimum Required Encoding…**.
2. Choose a target path and name in the save dialog; confirm.

**You should see and hear**
- QUILL picks the minimum lossless encoding, writes the copy, and the status reads
  **"Saved copy using minimum required encoding (<label>) to <path>"**. Cancel says
  **"Save using minimum required encoding cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-43 — Re-encode As… (`power.reencode_file`)

*What & why.* Save a copy of the document in an encoding **you** choose from a
list (e.g. UTF-8, UTF-16, Windows-1252).

**Before you start**
- `encoding-cp1252.txt` open.

**Do this**
1. **Format menu ▸ Re-encode As…**.
2. Arrow the encoding list and pick one; confirm. Then choose a save path.

**You should see and hear**
- A labelled, keyboard-navigable single-choice encoding list, then a save dialog;
  on success the status reads **"Saved re-encoded copy (<label>) to <path>"**.
  Cancelling either dialog says **"Re-encode cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-44 — Remove Email Quote Markers (`power.remove_email_quote_markers`)

*What & why.* Strip the leading `>` quote characters that pile up in replied-to
email text.

**Before you start**
- New document; type lines like `> > quoted twice`, `> quoted once`, `not quoted`.

**Do this**
1. **Format menu ▸ Remove Email Quote Markers**.

**You should see and hear**
- The leading `>` markers are removed, leaving the plain text; the status reads
  **"Removed email quote markers"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-45..46 — Strip ASCII ranges (`power.strip_low_ascii`, `power.strip_high_ascii`)

*What & why.* Remove control characters (low ASCII), or every non-ASCII character
(high ASCII), when a file is polluted with them.

**Before you start**
- **High ASCII:** open `encoding-cp1252.txt` (accents/currency are the high-ASCII
  characters to strip). **Low ASCII:** paste text that contains a stray control
  character if you have one; otherwise verify it leaves clean text untouched.

**Do this** (Format menu ▸ each item)
1. **Strip Low ASCII Characters** → **"Stripped low ASCII control characters"**.
2. **Strip High ASCII Characters** → **"Stripped high ASCII (non-ASCII)
   characters"**.

**You should see and hear**
- Strip High removes `é`, `£`, `€`, etc., leaving only ASCII. Strip Low removes
  control characters and leaves ordinary text intact. Each speaks its matching
  phrase.

**Sign off (Strip Low ASCII)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Strip High ASCII)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-47 — Convert to Hex Dump (`power.hex_dump`)

*What & why.* View the bytes of the selection (or document) as a classic hex dump
— for inspecting exactly what is in a file.

**Before you start**
- `plain.txt` open (or select a short phrase).

**Do this**
1. **Format menu ▸ Convert to Hex Dump**.

**You should see and hear**
- A **new untitled buffer** titled *Hex dump* opens showing offset, hex bytes, and
  an ASCII gutter. The original document is untouched.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-48..49 — OEM/ANSI code-page conversion (`power.convert_oem_to_ansi`, `power.convert_ansi_to_oem`)

*What & why.* Convert text between the DOS OEM code page (437) and Windows ANSI
(1252) — for old DOS text files whose box characters and accents look wrong.

**Before you start**
- Open a short line with accented text (e.g. from `encoding-cp1252.txt`). Run one
  conversion, then the other to return.

**Do this** (Format menu ▸ each item)
1. **Convert OEM (DOS) to ANSI** → **"Converted OEM (DOS) text to ANSI
   (Windows-1252)"**.
2. **Convert ANSI to OEM (DOS)** → **"Converted ANSI (Windows-1252) text to OEM
   (DOS)"**.

**You should see and hear**
- Each remaps the high-byte characters between the two code pages and speaks its
  matching phrase; applying one then the reverse returns the original text.

**Sign off (OEM to ANSI)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (ANSI to OEM)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-50..51 — Line-drawing characters (`power.convert_box_drawing_to_ascii`, `power.strip_box_drawing`)

*What & why.* Handle the box/line-drawing characters (`│ ─ ┌ ┐ └ ┘`) from DOS-era
tables: either convert them to plain ASCII `+ - |`, or strip them entirely.

**Before you start**
- New document; type a couple of lines using box-drawing characters — insert them
  with POW-01 (e.g. code points `2502` `│`, `2500` `─`, `250C` `┌`) — around some
  text.

**Do this** (Format menu ▸ each item; undo between them)
1. **Convert Line-Drawing Characters to ASCII** → **"Converted line-drawing
   characters to +, -, and |"**.
2. **Strip Line-Drawing Characters** → **"Stripped line-drawing characters"**.

**You should see and hear**
- Convert replaces the box characters with `+`, `-`, `|`; Strip removes them
  outright, leaving the surrounding text. Each speaks its matching phrase.

**Sign off (Convert to ASCII)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Strip Line-Drawing)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-52 — Select Markdown Profile… (`power.select_markdown_profile`)

*What & why.* Choose which Markdown flavour QUILL uses (Standard, GitHub-style,
etc.) by a plain-language name.

**Before you start**
- Any Markdown document open.

**Do this**
1. **Format menu ▸ Select Markdown Profile…**.
2. Arrow the list, pick a profile; confirm.

**You should see and hear**
- A labelled single-choice list with the current profile pre-selected; on confirm
  the status describes the chosen profile. Cancel says **"Markdown profile
  selection cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-53 — Preserve Single Line Breaks (`power.toggle_preserve_line_breaks`)

*What & why.* Apply the "nl2br" transform so single line breaks in Markdown become
real line breaks in the output (some Markdown flavours otherwise fold them).

**Before you start**
- New document; type two lines with a single newline between them.

**Do this**
1. **Format menu ▸ Preserve Single Line Breaks**.

**You should see and hear**
- The transform is applied to the selection (or document) and the status reads
  **"Preserved single line breaks"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-54 — Read Markdown Processing Status (`power.read_markdown_status`)

*What & why.* Announce which Markdown profile is active and which extensions it
enables — a quick "where am I" check.

**Before you start**
- Any document; ideally after POW-52 so you know what to expect.

**Do this**
1. **Format menu ▸ Read Markdown Processing Status**.

**You should see and hear**
- The status/announcement names the active profile and its enabled extensions. No
  document change; nothing but the spoken report.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-55 — Select Citation Style… (`power.select_citation_style`)

*What & why.* Choose the default citation style (footnotes, MLA, Chicago, APA)
used by Insert Citation.

**Before you start**
- Any document open.

**Do this**
1. **Format menu ▸ Select Citation Style…**.
2. Arrow the list, pick a style; confirm.

**You should see and hear**
- A labelled single-choice list with the current style pre-selected; on confirm the
  status reads **"Citation style set to <style>"**. Cancel says **"Citation style
  selection cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-56 — Go to Percent… (`power.go_to_percent`)

*What & why.* Jump the caret to a position a given percentage through the document
— fast, coarse navigation in a long file.

**Before you start**
- Open `formatting.md` (long enough that 50% is clearly the middle).

**Do this**
1. **Navigate menu (Alt, N) ▸ Go to Percent…**.
2. In **Document percentage (0-100):** accept **`50`** (or type another); confirm.

**You should see and hear**
- The caret moves to roughly the middle of the document (the jump is recorded so
  Back works) and the status reads **"Moved to 50%"**. A non-numeric value says
  **"Percentage must be a number"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-57..58 — Non-blank navigation (`power.move_to_first_non_blank`, `power.move_to_last_non_blank`)

*What & why.* Move the caret to the first or last non-blank character of the
current line — quicker than Home/End when there is leading or trailing whitespace.

**Before you start**
- New document; type a line with **leading spaces**, some words, and **trailing
  spaces**. Put the caret anywhere on that line.

**Do this** (Navigate menu ▸ each item)
1. **First Non-Blank** — moves to the first non-space character; announces the
   character there.
2. **Last Non-Blank** — moves to the last non-space character; announces the
   character there.

**You should see and hear**
- The caret lands on the first/last visible character (skipping whitespace) and the
  screen reader speaks that character (or **"End of line"** at a line end).

**Sign off (First Non-Blank)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Last Non-Blank)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-59 — Open Target at Cursor (`power.run_target_at_cursor`)

*What & why.* Open whatever the caret is sitting on — a URL in the browser, an
email address in the mail client, or a file path in its default app.

**Before you start**
- New document; type a line with a URL, e.g. `Visit https://example.com today`.
  Put the caret inside the URL. Network available for the URL case.

**Do this**
1. **Navigate menu ▸ Open Target at Cursor**.

**You should see and hear**
- The URL opens in your browser and the status reads **"Opened
  https://example.com"**. For an email address it opens a `mailto:` compose and
  says **"Opened email to …"**. For a file path it opens the file; a missing path
  says **"Path does not exist: …"**; nothing runnable says **"Nothing to run at the
  cursor"** — never a silent no-op.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-60 — Count Regular Expression Matches… (`power.count_regex_matches`)

*What & why.* Count how many times a regex matches in the selection (or document).

**Before you start**
- `formatting.md` open. Input regex: **`#`** (matches every heading marker).

**Do this**
1. **Search menu (Alt, S) ▸ Count Regular Expression Matches…**.
2. In **Regular expression:** type **`#`**; confirm.

**You should see and hear**
- The announcement reads **"N match(es)"** with the correct count. An invalid regex
  is reported clearly and nothing is counted.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-61 — Extract Regular Expression Matches… (`power.extract_regex_matches`)

*What & why.* Pull every match of a regex out into a new document — e.g. harvest
all the links or all the numbers.

**Before you start**
- `formatting.md` open. Input regex: **`https?://\S+`** (matches URLs).

**Do this**
1. **Search menu ▸ Extract Regular Expression Matches…**.
2. Type **`https?://\S+`**; confirm.

**You should see and hear**
- A **new untitled buffer** titled *Extracted matches* opens listing each match
  (the QUILL project link URL). An invalid regex is reported and nothing opens.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-62..63 — Two-block set operations (`power.set_lines_first_not_second`, `power.set_lines_common`)

*What & why.* Treat the document as **two blocks split at the caret** and compare
them: the lines only in the first block, or the lines common to both. Set algebra
for line lists.

**Before you start**
- New document; type block one (`apple`, `banana`, `cherry`), then block two
  (`banana`, `cherry`, `date`). Put the caret on the **boundary** — the start of
  the `banana` line that begins block two.

**Do this** (Search menu ▸ each item)
1. **Lines in First Block Only** → new buffer; status **"N line(s) in first block
   only"**.
2. **Lines Common to Both Blocks** → new buffer; status **"N line(s) common to both
   blocks"**.

**You should see and hear**
- First-only yields `apple` (the one line unique to block one). Common yields
  `banana`, `cherry`. Each result opens in a new untitled buffer and the status
  reports the count.

**Sign off (First Block Only)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Common to Both Blocks)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-64 — Multi Replace… (`power.multi_replace`)

*What & why.* Apply up to four find/replace pairs in a single pass, with a case
sensitivity switch.

**Before you start**
- New document; type `red green blue red`. Plan: **red→one**, **green→two**,
  **blue→three**.

**Do this**
1. **Search menu ▸ Multi Replace…**.
2. In the form set **Search 1 = `red` / Replace 1 = `one`**, **Search 2 = `green` /
   Replace 2 = `two`**, **Search 3 = `blue` / Replace 3 = `three`**, leave the
   fourth pair blank, keep **Case sensitive** ticked; press **Replace**.

**You should see and hear**
- All three replacements apply in one pass (empty search fields are skipped) giving
  `one two three one`; the status reads **"Applied multi replace"**. Cancel says
  **"Multi Replace cancelled"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-65 — Count Occurrences… (`power.count_occurrences`)

*What & why.* Count how many times a literal string appears (not a regex — plain
text).

**Before you start**
- New document; type `red green blue red green red`. Input: **`red`**.

**Do this**
1. **Search menu ▸ Count Occurrences…**.
2. In **Text to count:** type **`red`**; confirm.

**You should see and hear**
- The status reads **`Found 3 occurrences of "red"`** (singular "occurrence" when
  the count is 1). Empty input says **"Enter text to count"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-66 — Run Current File (`power.run_current_file`)

*What & why.* Open the saved file with its operating-system default application —
run a `.html` in the browser, a `.txt` in Notepad, etc. Guarded so it will not
launch an executable or script.

**Before you start**
- Save a copy of `sample.html` and keep it open (so the document has a path).

**Do this**
1. **Tools menu (Alt, T) ▸ Advanced ▸ Run Current File**.

**You should see and hear**
- QUILL saves first, then opens the file in its default app (the browser for HTML);
  the status reads **"Running sample.html"**. An unsaved document says **"Save the
  document before running it"**. An executable/script (`.exe`, `.bat`, `.ps1`…) is
  refused with **"Refusing to launch an executable or script for safety"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-67 — Toggle Read-Only Guard (`power.toggle_read_only_guard`)

*What & why.* Lock the current document against edits (and remember the lock for
that file across sessions) — protect a reference file from accidental typing.

**Before you start**
- A **saved** document open (so the guard can be remembered by path), e.g.
  `plain.txt`.

**Do this**
1. **Tools menu ▸ Advanced ▸ Toggle Read-Only Guard**. Try to type. Toggle again.

**You should see and hear**
- First toggle announces **"Document is read-only"** and typing is blocked;
  transform commands report **"Document is read-only"** rather than changing text.
  Second toggle announces **"Document is editable"** and typing works again. The
  read-only state persists for that file when reopened.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-68 — Toggle Clipboard Collector (`power.toggle_clipboard_collector`)

*What & why.* Turn the document into a running clipboard collector: anything you
copy — **in any program** — is appended here automatically. A research
scratchpad.

**Before you start**
- A saved document open (so appended text is auto-saved). Have another app (a
  browser, Notepad) ready to copy from.

**Do this**
1. **Tools menu ▸ Advanced ▸ Toggle Clipboard Collector**.
2. Switch to another app and **copy** a line; switch back. Toggle again to stop.

**You should see and hear**
- Turning on announces **"Clipboard collector on; anything you copy, in any
  program, appends to this document"**. Each distinct copy is appended to the end
  (once per payload, not duplicated) and the status reads **"Collected clipboard
  text"**. Turning off announces **"Clipboard collector off"**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-69 — Collect Clipboard Now (`power.collect_clipboard_now`)

*What & why.* Append the clipboard's current text to the document once, on demand,
without leaving the collector running.

**Before you start**
- A saved document open; copy a line to the clipboard.

**Do this**
1. **Tools menu ▸ Advanced ▸ Collect Clipboard Now**.

**You should see and hear**
- The clipboard text is appended to the end of the document and the status reads
  **"Collected clipboard text"**. An empty clipboard, a read-only document, or a
  repeat of the last-collected text is a quiet no-op (nothing duplicated).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-70 — Toggle Key Describer (`power.toggle_key_describer`)

*What & why.* A "what does this key do?" mode: while on, pressing a shortcut speaks
the command it is bound to **instead of running it** — a safe way to learn the
keymap.

**Before you start**
- Any document open.

**Do this**
1. **Tools menu ▸ Advanced ▸ Toggle Key Describer**.
2. Press a known shortcut, e.g. **Ctrl+S**. Toggle the mode off and press it again.

**You should see and hear**
- Turning on announces **"Key Describer on; press a key to hear its action"**.
  While on, **Ctrl+S** is announced as its command label (e.g. "Ctrl+S: Save") and
  is **not** executed; an unbound key says "<key>: no action". Turning off
  announces **"Key Describer off"** and shortcuts run normally again.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-71 — Toggle Indentation Announcements (`power.toggle_indent_announce`)

*What & why.* Speak the indentation level as the caret moves between lines — for
following the shape of indented code or outlines by ear.

**Before you start**
- New document; type three lines at increasing indentation (0, then 4 spaces, then
  8 spaces of leading whitespace).

**Do this**
1. **Tools menu ▸ Advanced ▸ Toggle Indentation Announcements**.
2. Arrow up and down through the three lines. Toggle again to stop.

**You should see and hear**
- Turning on announces **"Indentation announcements on"**; moving to a line at a
  different indent speaks the change (e.g. deeper/shallower). Turning off announces
  **"Indentation announcements off"** and movement is silent again.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-72 — Infer Indentation… (`power.infer_indent`)

*What & why.* Detect whether a document indents with tabs or N spaces and offer to
adopt that as the document's indent setting.

**Before you start**
- New document; type a few lines indented consistently with **4 spaces**.

**Do this**
1. **Tools menu ▸ Advanced ▸ Infer Indentation…**.
2. Read the inferred result; choose **Yes** to adopt (or **No** to just hear it).

**You should see and hear**
- QUILL describes the inferred unit (e.g. "4 spaces") and asks **"Adopt it for this
  document?"** with Yes/No. **Yes** applies it and announces **"Adopted
  indentation: …"**; **No** just re-states the inference. If it cannot infer a
  unit, it reports that via the status bar with no prompt.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-73 — Line Statistics (`power.compute_line_statistics`)

*What & why.* Open a report of line-level statistics (counts, lengths, blanks) for
the selection or whole document.

**Before you start**
- `plain.txt` open (or a selection).

**Do this**
1. **Tools menu ▸ Advanced ▸ Line Statistics**.

**You should see and hear**
- A **new untitled buffer** titled *Line statistics* opens with the computed
  figures; the original document is untouched.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-74 — Describe Character at Cursor (`power.describe_character`)

*What & why.* The screen-reader descendant of "Reveal Codes": name the exact
character under the caret — its Unicode name, code point, and notes for invisibles
(no-break space, zero-width characters, smart quotes, line endings).

**Before you start**
- Use POW-01 to insert an em dash (`U+2014`), then put the caret **on** it. (Any
  character works; an unusual one makes the description obvious.)

**Do this**
1. **Tools menu ▸ Advanced ▸ Describe Character at Cursor**.

**You should see and hear**
- A short summary in the status bar **and** an accessible read-only dialog titled
  **"Character at Cursor"** giving the character's Unicode name, code point (e.g.
  U+2014 EM DASH), category, and any plain-language note. The dialog is read in one
  pass and closes with Escape, returning focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## POW-75 — Describe Image at Cursor (`power.describe_image_at_cursor`)

*What & why.* Read out the details of an image reference at the caret — its alt
text, whether it is decorative, and its source — without any AI.

**Before you start**
- Open **`formatting.md`** and move the caret onto the image reference (alt text
  **"Red circle"**). (This is the offline, markup-reading command; the AI vision
  description is a separate Tools/AI feature.)

**Do this**
1. **Tools menu ▸ Advanced ▸ Describe Image at Cursor**.

**You should see and hear**
- The status/announcement describes the image at the caret — its alt text **"Red
  circle"** and source path. With the caret not on an image it says **"No image at
  the cursor."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 56
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
