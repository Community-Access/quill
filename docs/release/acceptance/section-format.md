# Section — Format & Insert (`format.*`, 56 commands)

Everything about **shaping** a document: making words bold or italic, adding
headings, lists, tables, quotes and code, changing case, moving lines and
sections, and — the part screen-reader users lean on hardest — **hearing what
formatting is at the cursor**. Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `format.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

Two things that recur below, so they are explained once here:

- **The menus.** These commands live in two menu bar menus. **Format menu
  (Alt, O)** holds bold/italic/underline, case changes, indent, comments, and
  line/section moves. **Insert menu (Alt, I)** holds the *structural* inserts —
  its **Heading** and **List** submenus, plus tables, quotes, code, rules,
  snippets and abbreviations. A few commands have **no menu entry**; reach those
  through the **Command Palette** (**Ctrl+Shift+P**, then type the command name).
- **The chord shortcuts.** Some shortcuts are a two-key *chord*: press
  **Ctrl+Shift+Grave** (Grave is the backtick <code>`</code> key, top-left),
  release, then the second key. Where a scenario uses one it is spelled out.
- **Markdown vs rich text.** Most of these behave in a **Markdown** document by
  inserting literal Markdown/HTML markup (so bold becomes `**word**`), and the
  spoken confirmation names the surface, e.g. "(markdown)". In a rich-text
  document the same command applies real styling and speaks the bare style name.
  Every scenario below is written for the **Markdown** sample so the outcomes are
  concrete; if you test in rich text, expect the rich-text wording instead.

Common inputs used below (copy the `../qa-samples/` folder onto the machine
first): **`formatting.md`** (the ideal input — it already contains bold/italic/
underline/strikethrough words, bullet and numbered lists, a blockquote, inline and
fenced code, a link, and an image) and **`plain.txt`**.

---

## FMT-01 — Bold (`format.bold`, Ctrl+B)

*What & why.* Make selected text bold — the most-used emphasis, and the first
place to prove "what I formatted was announced."

**Before you start**
- Open **`formatting.md`**. In the first paragraph, select the word **`sample`**
  (double-click by keyboard is not available — use **Shift+Ctrl+Right** from the
  word start, or Shift+arrows, to select exactly `sample`).

**Do this**
1. Press **Ctrl+B**, or **Format menu (Alt, O) ▸ Bold**.
2. Now test "off": select the just-bolded text **including its `**` markers** and
   read it with the review cursor; delete the markers (or re-select and Clear
   Formatting, FMT-06) to confirm emphasis can be removed.

**You should see and hear**
- The selection is wrapped as `**sample**`; QUILL announces the action in
  substance — "Applied bold (markdown)" (in a rich-text document it speaks
  "Bold" instead). The change is *not* silent. Note: in Markdown, bold is
  expressed as literal `**` markers, not a hidden on/off attribute — so "turning
  it off" means removing those markers, and re-applying bold does not report a
  spoken "bold off" state. If the profile forbids it you hear "Bold is
  unavailable in this profile" (mark **N/A**, not Fail).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-02 — Italic (`format.italic`, Ctrl+I)

*What & why.* Make selected text italic.

**Before you start**
- `formatting.md` open. Select the word **`exercises`** in the first paragraph.

**Do this**
1. Press **Ctrl+I**, or **Format menu ▸ Italic**.
2. Test "off" as in FMT-01: inspect the `*…*` markers and remove them to confirm
   the emphasis is reversible.

**You should see and hear**
- The selection is wrapped as `*exercises*`; QUILL announces "Applied italic
  (markdown)" (rich text: "Italic"). Not silent. Disabled profile:
  "Italic is unavailable in this profile" → **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-03 — Underline (`format.underline`)

*What & why.* Underline selected text. There is **no default shortcut** — reach
it from the menu or palette.

**Before you start**
- `formatting.md` open. Select the word **`inline`** in the first paragraph.

**Do this**
1. **Format menu ▸ Underline** (or Command Palette → "Underline").

**You should see and hear**
- The selection is wrapped with an HTML underline tag, `<u>inline</u>` (underline
  has no plain-Markdown form, so it is inserted as inline HTML in both Markdown and
  HTML documents); QUILL announces "Applied underline (markdown)" (rich text:
  "Underline"). Not silent. Disabled profile: "Underline is unavailable in this
  profile" → **N/A**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-04 — Describe Formatting at Cursor (`format.describe_formatting`, Ctrl+Shift+D)

*What & why.* Speak the formatting **at the caret** on demand — the single most
important accessibility command in this section. This is the manual version of
core-journey TC-001d.

**Before you start**
- Open **`formatting.md`**. The first paragraph contains four styled words:
  **bold** (`**bold**`), **italic** (`*italic*`), **underline**
  (`<u>underline</u>`), and **strike** (`~~strike~~`).

**Do this**
1. Place the caret **inside the word `bold`**. Press **Ctrl+Shift+D** (or Command
   Palette → "Describe Formatting at Cursor").
2. Repeat with the caret inside **`italic`**, then **`underline`**, then
   **`strike`**.
3. Finally, place the caret in an **unstyled** word (e.g. `paragraph`) and press
   **Ctrl+Shift+D** again.

**You should see and hear**
- Each invocation speaks a formatting phrase, led by "Formatting: …": **bold**
  reads as **bold**, **italic** as **italic**, **underline** as **underlined**,
  **strike** as **strikethrough** — each state is *named*, none is silent
  (matching TC-001d). On a heading line the phrase begins with "heading level N";
  inside a list it says "bullet". On the unstyled word it reports the equivalent
  of **"plain text, no formatting"**. In a non-Markdown/rich document that cannot
  be described it says formatting description is available in Markdown documents.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-05 — Announce Formatting on Cursor Move (`format.toggle_announce_formatting`)

*What & why.* Turn on continuous formatting announcements: as you arrow through
text, QUILL speaks only the *change* (entering bold, leaving bold), so you always
know what you are standing in without asking. No default shortcut.

**Before you start**
- `formatting.md` open, caret at the top (**Ctrl+Home**).

**Do this**
1. Command Palette → **"Announce Formatting on Cursor Move"** (this is the label
   for `format.toggle_announce_formatting`). Note the spoken state.
2. Arrow **Right** through the first paragraph, crossing into and out of the
   `bold` word.
3. Invoke the command a second time to turn it back off; confirm the spoken state
   flips.

**You should see and hear**
- Toggling announces the new state in substance: "Formatting announcements on
  cursor move: on" then, on the second invocation, "…: off". While **on**, moving
  the caret into `bold` speaks the change (e.g. "bold") and moving out speaks the
  return to plain — a delta, not the whole phrase. While **off**, arrowing is
  silent about formatting again.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-06 — Clear Formatting (`format.clear_formatting`)

*What & why.* Strip run-level formatting from the selection (or the current
paragraph), returning it to plain text. No default shortcut.

**Before you start**
- `formatting.md` open. Select the bold word (with its markers) or place the caret
  in a styled paragraph.

**Do this**
1. Command Palette → **"Clear Formatting"**.

**You should see and hear**
- The formatting is removed and QUILL announces "Formatting cleared" (spoken, not
  silent). In a non-Markdown document it reports that clear formatting is only
  available in Markdown documents; a disabled profile says clear formatting is
  unavailable in this profile (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-07 — Font… (`format.font_dialog`)

*What & why.* Open an accessible Font dialog to set family, size, and colour.
No default shortcut. Most meaningful in rich-text documents.

**Before you start**
- `formatting.md` open (Markdown), plus — if you have one — a rich-text/`.docx`
  document to see the applied font.

**Do this**
1. Command Palette → **"Font..."**.
2. Tab through the family, size, and colour controls by keyboard; choose a value;
   confirm with **Enter** (or **Escape** to cancel).

**You should see and hear**
- The dialog's controls are labelled and keyboard-complete. On confirm QUILL
  announces "Font applied"; with no change it says "Font unchanged" / "No font
  changes selected". In a Markdown document it may report that font is only
  available in Markdown documents / a disabled profile says font tools are
  unavailable (**N/A**). Escape cancels with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-08 — Upper Case (`format.upper_case`)

*What & why.* Convert the selection (or, with no selection, the current word) to
UPPER CASE. No default shortcut.

**Before you start**
- `plain.txt` open. Select a short phrase, e.g. **`the quick brown fox`**.

**Do this**
1. **Format menu ▸ Upper Case** (or Command Palette → "Upper Case").

**You should see and hear**
- The text becomes `THE QUICK BROWN FOX`; QUILL announces in substance "Upper case
  applied to selection" (with no selection: "…applied to current word"). With
  neither a selection nor a word under the caret it says "No current word to
  transform" rather than doing nothing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-09 — Lower Case (`format.lower_case`)

*What & why.* Convert the selection/current word to lower case. No default
shortcut.

**Before you start**
- `plain.txt` open. Select **`THE QUICK BROWN FOX`** (reuse FMT-08's result).

**Do this**
1. **Format menu ▸ Lower Case**.

**You should see and hear**
- The text becomes `the quick brown fox`; QUILL announces "Lower case applied to
  selection" (or "…to current word"). Empty target: "No current word to transform".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-10 — Title Case (`format.title_case`)

*What & why.* Capitalise the first letter of each word. No default shortcut.

**Before you start**
- `plain.txt` open. Select **`the quick brown fox`**.

**Do this**
1. **Format menu ▸ Title Case**.

**You should see and hear**
- The text becomes `The Quick Brown Fox`; QUILL announces "Title case applied to
  selection" (or "…to current word").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-11 — Sentence Case (`format.sentence_case`)

*What & why.* Capitalise only the first letter of the selection/sentence. No
default shortcut.

**Before you start**
- `plain.txt` open. Select **`THE QUICK BROWN FOX`**.

**Do this**
1. **Format menu ▸ Sentence Case**.

**You should see and hear**
- The text becomes `The quick brown fox`; QUILL announces "Sentence case applied to
  selection" (or "…to current word").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-12 — Toggle Case (`format.toggle_case`)

*What & why.* Invert the case of each letter (upper becomes lower and vice-versa).
No default shortcut.

**Before you start**
- `plain.txt` open. Select **`The Quick`**.

**Do this**
1. **Format menu ▸ Toggle Case**.

**You should see and hear**
- The text becomes `tHE qUICK`; QUILL announces "Toggle case applied to selection"
  (or "…to current word"). Invoking again returns to the original.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-13 … FMT-18 — Insert Heading 1 through 6 (`format.heading_1`…`format.heading_6`, Ctrl+Alt+1 … Ctrl+Alt+6)

*What & why.* Turn the current line into a heading of the chosen level — the
backbone of a navigable document. Six commands, one per level; each has its own
sign-off below.

**Before you start**
- Open a **new Markdown document** (Ctrl+N). Type six short lines, one per level,
  e.g. `Alpha`, `Bravo`, `Charlie`, `Delta`, `Echo`, `Foxtrot`, each on its own
  line.

**Do this**
1. Put the caret on the first line. Press **Ctrl+Alt+1**, or **Insert menu
   (Alt, I) ▸ Heading ▸ Heading 1**.
2. Move to the next line; press **Ctrl+Alt+2** (Heading 2). Continue **Ctrl+Alt+3**,
   **Ctrl+Alt+4**, **Ctrl+Alt+5**, **Ctrl+Alt+6** on lines 3–6.

**You should see and hear**
- Each command prefixes the line with the right number of `#` marks (`#` … `######`)
  and announces in substance "Inserted heading N (markdown)" (rich text speaks
  "Heading N"). Afterwards, the screen reader's heading quick-key **H** should walk
  all six in order, each spoken with its level — confirming the levels are real, not
  cosmetic. Disabled profile: "Heading tools are unavailable in this profile"
  (**N/A**).

**Sign off (Heading 1 — `format.heading_1`, Ctrl+Alt+1)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Heading 2 — `format.heading_2`, Ctrl+Alt+2)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Heading 3 — `format.heading_3`, Ctrl+Alt+3)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Heading 4 — `format.heading_4`, Ctrl+Alt+4)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Heading 5 — `format.heading_5`, Ctrl+Alt+5)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Heading 6 — `format.heading_6`, Ctrl+Alt+6)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-19 — Increase Heading Level (`format.increase_heading_level`, Alt+Shift+Right)

*What & why.* Demote the heading on the current line by one level (H2 → H3),
without retyping the `#` marks.

**Before you start**
- The document from FMT-13…18 (or `formatting.md`). Put the caret on a **Heading 2**
  line.

**Do this**
1. Press **Alt+Shift+Right**, or **Insert menu ▸ Heading ▸ Increase Level**.

**You should see and hear**
- The line gains one `#` (H2 becomes H3); QUILL announces "Adjusted heading level".
  At the deepest level it says "Heading already at maximum level"; off a heading
  line, "Place cursor on a heading line to adjust its level"; in a non-markup
  document, "Headings are only available in Markdown or HTML documents".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-20 — Decrease Heading Level (`format.decrease_heading_level`, Alt+Shift+Left)

*What & why.* Promote the heading on the current line by one level (H3 → H2).

**Before you start**
- Caret on the **Heading 3** line you just made in FMT-19.

**Do this**
1. Press **Alt+Shift+Left**, or **Insert menu ▸ Heading ▸ Decrease Level**.

**You should see and hear**
- The line loses one `#` (H3 becomes H2); QUILL announces "Adjusted heading level".
  At the top level it says "Heading already at minimum level"; the same off-heading
  and non-markup messages as FMT-19 apply.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-21 — Style Headings… (`format.style_headings`)

*What & why.* Apply a heading *style* across the whole document by level (bulk
restyle rather than line-by-line). No default shortcut.

**Before you start**
- `formatting.md` open (it has all six heading levels).

**Do this**
1. **Insert menu ▸ Heading ▸ Style Headings…** (or Command Palette → "Style
   Headings").
2. Choose the level scope and a style in the dialog by keyboard; confirm (or
   **Escape** to cancel).

**You should see and hear**
- The dialog controls are labelled and keyboard-navigable. On confirm QUILL
  announces how many were changed — "Styled 1 heading" / "Styled N headings";
  with no matches, "No headings matched the selected level"; Escape reports
  "Heading styling cancelled". In a non-markup document it says headings are only
  available in Markdown or HTML documents.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-22 — Insert Bullet List (`format.insert_bullet_list`)

*What & why.* Insert an unordered (bulleted) list at the caret. No default
shortcut.

**Before you start**
- New Markdown document, caret on an empty line.

**Do this**
1. **Insert menu (Alt, I) ▸ List ▸ Bullet** (or Command Palette → "Insert Bullet
   List").

**You should see and hear**
- A bullet list marker (`- `) is inserted; QUILL announces "Inserted bullet list
  (markdown)". In a non-markup document it says "Bullet List is only available in
  Markdown or HTML documents".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-23 — Insert Numbered List (`format.insert_numbered_list`)

*What & why.* Insert an ordered (numbered) list at the caret. No default shortcut.

**Before you start**
- New Markdown document, caret on an empty line.

**Do this**
1. **Insert menu ▸ List ▸ Numbered** (or Command Palette → "Insert Numbered
   List").

**You should see and hear**
- A numbered marker (`1. `) is inserted; QUILL announces "Inserted numbered list
  (markdown)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-24 — Toggle Bullet List (`format.toggle_bullet_list`, Ctrl+Alt+B)

*What & why.* One command that **adds** bullets if the caret is on a plain line and
**removes** them if it is already inside a bullet list.

**Before you start**
- Open **`formatting.md`** and put the caret inside the unordered list under
  "Heading Two — Lists" (e.g. on the `Apples` line). Then, for the add path, put the
  caret on a plain paragraph line.

**Do this**
1. On the plain line, press **Ctrl+Alt+B** (or **Insert menu ▸ List ▸ Toggle
   Bullet**) to **add** bullets.
2. On an existing bullet line, press **Ctrl+Alt+B** again to **remove** them.

**You should see and hear**
- Adding announces "Inserted bullet list (markdown)"; removing (caret already in a
  bullet list) strips the markers and announces "Bullet List removed". Non-markup
  document: "Bullet List is only available in Markdown or HTML documents".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-25 — Toggle Numbered List (`format.toggle_numbered_list`, Ctrl+Alt+N)

*What & why.* Add numbering to plain lines, or strip it from a numbered list —
and, when adding, it can auto-number the lines that follow.

**Before you start**
- `formatting.md` open. Use the ordered list under "Heading Two — Lists" (the
  `First / Second / Third` lines) for the remove path, and a plain multi-line block
  for the add path.

**Do this**
1. On plain lines, press **Ctrl+Alt+N** (or **Insert menu ▸ List ▸ Toggle
   Numbered**) to **add** numbering.
2. Inside the existing numbered list, press **Ctrl+Alt+N** again to **remove** it.

**You should see and hear**
- Adding announces "Inserted numbered list (markdown)"; if the auto-fill path fires
  it says "Numbered list applied (with numbers)" and arms auto-numbering for a few
  minutes. Removing announces "Numbered List removed".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-26 — Insert Task List (`format.insert_task_list`)

*What & why.* Insert a checkbox (task) list item (`- [ ] `). No default shortcut.

**Before you start**
- New Markdown document, caret on an empty line.

**Do this**
1. **Insert menu ▸ List ▸ Task** (or Command Palette → "Insert Task List").

**You should see and hear**
- A task-list item is inserted; QUILL announces "Inserted task list (markdown)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-27 — List Manager… (`format.list_manager`, Ctrl+Shift+Grave then L)

*What & why.* Open a dialog to edit the Markdown list the caret is inside — reorder,
renumber, change marker — by keyboard.

**Before you start**
- `formatting.md` open, caret **inside** the bullet list under "Heading Two".

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **L** — or **Insert menu ▸
   List ▸ List Manager…**.
2. Make a change in the dialog by keyboard; confirm (or **Escape** to cancel).

**You should see and hear**
- The dialog is labelled and keyboard-operable. On confirm QUILL announces "Applied
  list manager changes"; Escape says "List Manager cancelled"; a no-op confirm says
  "List Manager closed without changes". If the caret is **not** in a list it says
  "Place the cursor inside a Markdown list to open List Manager"; in a non-Markdown
  document, "List Manager is only available in Markdown documents"; disabled profile,
  "List Manager is unavailable in this profile" (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-28 — Structured List Studio (`format.list_studio`, F2)

*What & why.* A richer list-building workspace: turn a selection (or the list at the
caret, or nothing) into a structured, multi-level list with a full undo path.

**Before you start**
- `formatting.md` open. Select the three bullet lines under "Heading Two", or place
  the caret in that list.

**Do this**
1. Press **F2**, or **Insert menu ▸ List ▸ Structured List Studio…**.
2. Build/adjust the list by keyboard; confirm with the dialog's OK (or **Escape**).

**You should see and hear**
- Studio opens as a keyboard-navigable, announced surface. On OK it inserts or
  replaces and speaks a summary followed by "Inserted. Press Control+Z to undo." or
  "Replaced. Press Control+Z to undo."; Escape says "Structured List Studio
  cancelled"; an empty build says "Structured List Studio: nothing to insert"; a
  validation failure says "…list not inserted (validation)". Disabled profile /
  read-only document are announced ("…unavailable in this profile" → **N/A**;
  "Document is read-only").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-29 — Structured List Studio Settings (`format.list_studio_settings`)

*What & why.* Edit the defaults Structured List Studio uses, with an
all-documents or this-document scope. No default shortcut.

**Before you start**
- Any document open.

**Do this**
1. **Insert menu ▸ List ▸ List Studio Settings…** (or Command Palette).
2. Change a default; choose a scope; confirm.

**You should see and hear**
- The settings dialog is labelled and keyboard-complete. Saving announces the scope:
  "List Studio settings saved for all documents" or "…saved for this document";
  clearing a document override says "…for this document cleared (back to defaults)";
  a no-change confirm says "List Studio settings unchanged".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-30 — Insert Code Block (`format.insert_code_block`)

*What & why.* Wrap the selection in a fenced code block, optionally with a language
hint (like the Python block in the sample). No default shortcut.

**Before you start**
- New Markdown document. Type and select a line, e.g. `print("hello")`.

**Do this**
1. **Insert menu (Alt, I) ▸ Insert Code Block** (or Command Palette).
2. At the language prompt, type **`python`** (or leave blank); confirm.

**You should see and hear**
- The selection is wrapped in a ```` ``` ```` fence; QUILL announces "Inserted code
  block (markdown, python)" (blank language reports "…plain"); Escape at the prompt
  says "Insert code block cancelled". Non-markup document: "Code Block is only
  available in Markdown or HTML documents".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-31 — Insert Footnote (`format.insert_footnote`)

*What & why.* Insert a Markdown footnote reference and its definition. No default
shortcut.

**Before you start**
- New Markdown document, caret at the end of a sentence.

**Do this**
1. **Insert menu ▸ Insert Footnote** (or Command Palette).

**You should see and hear**
- A footnote marker and definition stub are inserted; QUILL announces "Inserted
  footnote (markdown)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-32 — Insert Table (`format.insert_table`, Ctrl+Alt+T)

*What & why.* Insert a Markdown table of chosen size, with or without a header row.

**Before you start**
- New Markdown document, caret on an empty line.

**Do this**
1. Press **Ctrl+Alt+T**, or **Insert menu ▸ Insert Table…**.
2. In the prompt, choose **3** rows, **4** columns, header **yes**; confirm.

**You should see and hear**
- A 3×4 Markdown table is inserted; QUILL announces "Inserted 3x4 table (markdown)";
  Escape says "Insert table cancelled". (You can later verify cell navigation in the
  Table section.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-33 — Insert Block Quote (`format.blockquote`, Ctrl+Alt+Q)

*What & why.* Wrap the selection as a blockquote (`> `) — like the quote line in the
sample.

**Before you start**
- New Markdown document. Type and select a sentence, e.g.
  `The quick brown fox jumps over the lazy dog.`

**Do this**
1. Press **Ctrl+Alt+Q**, or **Insert menu ▸ Insert Block Quote**.

**You should see and hear**
- The line is prefixed with `> `; QUILL announces "Inserted block quote (markdown)";
  Escape (if a prompt appears) says "Insert block quote cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-34 — Insert Horizontal Rule (`format.horizontal_rule`, Ctrl+Alt+H)

*What & why.* Insert a thematic break (`---`) between sections.

**Before you start**
- New Markdown document, caret on an empty line between two paragraphs.

**Do this**
1. Press **Ctrl+Alt+H**, or **Insert menu ▸ Insert Horizontal Rule**.

**You should see and hear**
- A `---` rule is inserted on its own line; QUILL announces "Inserted horizontal
  rule (markdown)"; a cancel says "Insert horizontal rule cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-35 — Insert Page Break (`format.insert_page_break`)

*What & why.* Insert an export-only page-break marker (it shows up in print/export,
not as visible text). No default shortcut; Markdown documents only.

**Before you start**
- `formatting.md` open (Markdown), caret on an empty line.

**Do this**
1. Command Palette → **"Insert Page Break"**.

**You should see and hear**
- A page-break marker is inserted on its own line; QUILL announces "Page break
  inserted". In a non-Markdown document it says "Page break is only available in
  Markdown documents"; a disabled profile says "Page break is unavailable in this
  profile" (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-36 — Insert HTML Tag… (`format.insert_html_tag`, Ctrl+Shift+Grave then H)

*What & why.* Pick an HTML tag from a searchable list and wrap the selection in it,
with optional attributes.

**Before you start**
- New Markdown document. Type and select a word, e.g. `emphasis`.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **H** — or **Insert menu ▸
   Insert HTML Tag…**.
2. Search/select a tag (e.g. `span`), fill any attributes by keyboard; confirm.

**You should see and hear**
- The selection is wrapped in the chosen tag; QUILL announces "Inserted HTML tag
  <span>" (the tag name reflects your choice). A disabled profile says "HTML tag
  tools are unavailable in this profile" (**N/A**); cancel returns quietly to the
  editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-37 — Insert Markdown Tag… (`format.insert_markdown_tag`)

*What & why.* Pick a Markdown construct (link, image, emphasis, etc.) from a
searchable list; for link/image it prompts for the URL. No default shortcut. This is
the ideal way to reproduce the sample's `[QUILL project](…)` link and
`![Red circle]` image.

**Before you start**
- New Markdown document. To make a link, type and select the link text `QUILL
  project`.

**Do this**
1. **Insert menu ▸ Insert Markdown Tag…** (or Command Palette).
2. Choose **Link**; at the URL prompt type `https://example.com/quill`; confirm.

**You should see and hear**
- A Markdown link `[QUILL project](https://example.com/quill)` is inserted; QUILL
  announces "Inserted markdown link" (the kind reflects your choice, e.g. "…image").
  A disabled profile says "Markdown tag tools are unavailable in this profile"
  (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-38 — Insert Snippet… (`format.insert_snippet`, Ctrl+Shift+Grave then S)

*What & why.* Insert a saved snippet, filling any placeholders as you go.

**Before you start**
- At least one snippet defined (see FMT-39 to create one if none exist). New Markdown
  document, caret on an empty line.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **S** — or **Insert menu ▸
   Insert Snippet…**.
2. Pick a snippet; fill any placeholder prompts; confirm.

**You should see and hear**
- The rendered snippet is inserted; QUILL announces `Inserted snippet "<name>".`. If
  none are defined it says "No snippets available. Open Manage Snippets to add one.";
  Escape says "Snippet insertion cancelled"; a bad placeholder is reported, not
  crashed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-39 — Manage Snippets… (`format.manage_snippets`, Ctrl+Shift+Grave then Shift+S)

*What & why.* Create, edit, delete, import, or export snippets.

**Before you start**
- Any document open.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **Shift+S** — or **Insert
   menu ▸ Manage Snippets…**.
2. Add a snippet by keyboard; save; then reopen to confirm it persisted.

**You should see and hear**
- The manager's action chooser (create/edit/delete/import/export) is labelled and
  keyboard-operable; a cancel says "Manage snippets cancelled". Import outcomes are
  spoken clearly (e.g. "No snippets found in selected file", "Snippet import
  cancelled"). The snippet you add is available in FMT-38.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-40 — Indent (`format.indent`, Ctrl+])

*What & why.* Indent the selected line(s) by one indent unit.

**Before you start**
- `plain.txt` open. Put the caret on a line (or select several lines).

**Do this**
1. Press **Ctrl+]**, or **Format menu (Alt, O) ▸ Indent**.

**You should see and hear**
- The line(s) shift right by one indent unit; QUILL announces "Indented lines"
  (force-announced, never silent).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-41 — Outdent (`format.outdent`, Ctrl+[)

*What & why.* Remove one indent unit from the selected line(s).

**Before you start**
- Reuse the indented line from FMT-40.

**Do this**
1. Press **Ctrl+[**, or **Format menu ▸ Outdent**.

**You should see and hear**
- The line(s) shift left by one indent unit; QUILL announces "Outdented lines"
  (force-announced).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-42 — Toggle Tab Key Mode (Indent / Tab Character) (`format.toggle_tab_insert_mode`, Ctrl+Shift+Grave then U)

*What & why.* Switch what the **Tab** key does: insert a literal tab character, or
indent the current line. Matters for code vs prose.

**Before you start**
- `plain.txt` open.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **U** — or **Format menu ▸
   Tab Key Inserts Tab Character** (the menu item toggles this mode).
2. Press **Tab** on a line and observe the behaviour; invoke the toggle again and
   press **Tab** to see the other behaviour.

**You should see and hear**
- Toggling announces the new mode: "Tab key inserts a tab character" or "Tab key
  indents the line". Pressing **Tab** then does exactly what was announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-43 — Auto-Indent Newline (`format.auto_indent_newline`)

*What & why.* Insert a newline that keeps the current line's leading whitespace (and
adds one level after a trailing `:` or `{`) — the smart-Enter used while writing
indented text. No default shortcut.

**Before you start**
- `plain.txt` open. Type an indented line, e.g. four spaces then `item:` , and leave
  the caret at the end of it.

**Do this**
1. Command Palette → **"Auto-Indent Newline"**.

**You should see and hear**
- A new line is created that carries the previous line's indentation (and one extra
  level after the `:`); QUILL announces "Auto-indent newline". The caret lands ready
  to type at the new indent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-44 — Toggle Line Comment (`format.toggle_line_comment`, Ctrl+/)

*What & why.* Comment or uncomment the selected line(s) using the document
language's line-comment syntax.

**Before you start**
- Open a document whose language has line comments (e.g. a `.py` file, or paste a
  line of Python). Put the caret on a line (or select several).

**Do this**
1. Press **Ctrl+/**, or **Format menu ▸ Comments ▸ Toggle Line Comment**.
2. Press **Ctrl+/** again on the same line(s) to uncomment.

**You should see and hear**
- The line(s) gain (then lose) the language's comment marker; QUILL announces
  "Toggled line comment" each time.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-45 — Toggle Block Comment (`format.toggle_block_comment`, Shift+Alt+A)

*What & why.* Wrap (or unwrap) the selection in a block comment.

**Before you start**
- Same code document as FMT-44; select a few lines.

**Do this**
1. Press **Shift+Alt+A**, or **Format menu ▸ Comments ▸ Toggle Block Comment**.
2. Repeat to unwrap.

**You should see and hear**
- The selection is wrapped (then unwrapped) in a block comment; QUILL announces
  "Toggled block comment".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-46 — Move Line Up (`format.move_line_up`)

*What & why.* Swap the current line (or selected block) with the line above. No
default shortcut.

**Before you start**
- `plain.txt` with several lines; caret on the **second** line.

**Do this**
1. **Format menu ▸ Move Line Up** (or Command Palette).

**You should see and hear**
- The line moves up one position; QUILL announces "Moved line up" (or "Moved N lines
  up" for a multi-line selection). At the top it says "Already at the top" rather
  than doing nothing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-47 — Move Line Down (`format.move_line_down`)

*What & why.* Swap the current line (or selected block) with the line below. No
default shortcut.

**Before you start**
- `plain.txt`; caret on a line that is **not** the last.

**Do this**
1. **Format menu ▸ Move Line Down** (or Command Palette).

**You should see and hear**
- The line moves down one position; QUILL announces "Moved line down" (or "Moved N
  lines down"). At the bottom it says "Already at the bottom".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-48 — Duplicate Line (`format.duplicate_line`)

*What & why.* Copy the current line and paste the copy directly below. No default
shortcut.

**Before you start**
- `plain.txt`; caret on any non-empty line.

**Do this**
1. **Format menu ▸ Duplicate Line** (or Command Palette).

**You should see and hear**
- An identical line appears below the current one; QUILL announces "Duplicated
  line".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-49 — Delete Line (`format.delete_line`)

*What & why.* Delete the entire current line. No default shortcut.

**Before you start**
- `plain.txt`; caret on the line you duplicated in FMT-48.

**Do this**
1. **Format menu ▸ Delete Line** (or Command Palette).

**You should see and hear**
- The whole line is removed and the caret lands sensibly on an adjacent line; QUILL
  announces "Deleted line". (Undo with **Ctrl+Z** to confirm it is recoverable.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-50 — Join Lines (`format.join_lines`)

*What & why.* Merge the selected lines (or the current paragraph) into a single
line. No default shortcut.

**Before you start**
- `plain.txt`; select two or three consecutive lines.

**Do this**
1. **Format menu ▸ Join Lines** (or Command Palette).

**You should see and hear**
- The selected lines become one; QUILL announces "Joined N lines" (or "Joined
  lines"). With nothing to join it says "No lines to join".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-51 — Move Section Up (`format.move_section_up`, Alt+Shift+Up)

*What & why.* Move an entire heading section (the heading and everything under it,
down to the next sibling) above its previous sibling — restructuring by ear.
Markdown/HTML only.

**Before you start**
- Open **`formatting.md`**. Put the caret on the **"Heading Two — Lists"** heading
  line (it has a sibling section above and below it).

**Do this**
1. Press **Alt+Shift+Up**, or **Format menu ▸ Move Section Up**.

**You should see and hear**
- The whole "Heading Two" section swaps above the section before it; QUILL speaks
  "Section moved above <sibling>" (naming the section it jumped over). At the top it
  says "Top!"; with no sibling, "No sibling to swap with"; off a heading, "No section
  to move"; in a non-markup document, "Section move is only available in Markdown or
  HTML documents".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-52 — Move Section Down (`format.move_section_down`, Alt+Shift+Down)

*What & why.* Move a heading section below its next sibling. Markdown/HTML only.

**Before you start**
- `formatting.md` open; caret on the **"Heading Two — Lists"** heading line (or wherever
  it now sits after FMT-51).

**Do this**
1. Press **Alt+Shift+Down**, or **Format menu ▸ Move Section Down**.

**You should see and hear**
- The section swaps below the next one; QUILL speaks "Section moved below
  <sibling>". At the bottom it says "Bottom!"; the same no-op / non-markup messages
  as FMT-51 apply.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-53 — Expand Abbreviation (`format.expand_abbreviation`, Ctrl+Shift+Grave then A)

*What & why.* Expand the abbreviation before the caret into its full text (like a
text-expander). [GATED] Present only when the **Abbreviations** feature is enabled;
otherwise mark **N/A**.

**Before you start**
- An abbreviation defined (add one via FMT-54 first, e.g. `qq` → `QUILL Quick
  Test`). New document; type **`qq`** and leave the caret right after it.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **A** — or **Insert menu ▸
   Expand Abbreviation**.

**You should see and hear**
- The `qq` is replaced by its expansion; QUILL speaks "Expanded to: <preview>" (the
  preview is truncated with "…" if long). If expansion is disabled it says
  "Abbreviation expansion is disabled"; with nothing before the caret, "No word
  before cursor"; with no match, "No abbreviation match".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-54 — Manage Abbreviations… (`format.manage_abbreviations`, Ctrl+Shift+Grave then Shift+A)

*What & why.* Create, edit, and remove abbreviations. [GATED] Abbreviations feature
only; else **N/A**.

**Before you start**
- Any document open.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **Shift+A** — or **Insert
   menu ▸ Manage Abbreviations…**.
2. Add an abbreviation (e.g. `qq` → `QUILL Quick Test`) by keyboard; save.

**You should see and hear**
- The manager is labelled and keyboard-operable; on save QUILL announces
  "Abbreviations updated". The abbreviation you add is then usable in FMT-53.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-55 — Toggle Abbreviation Expansion (`format.toggle_abbreviation_expansion`, Ctrl+Shift+Grave then E)

*What & why.* Turn automatic abbreviation expansion on or off. [GATED] Abbreviations
feature only; else **N/A**.

**Before you start**
- Any document open.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **E** — or **Insert menu ▸
   Toggle Abbreviation Expansion**.
2. Invoke again to flip it back.

**You should see and hear**
- QUILL speaks "Abbreviation expansion on" then, on the second invocation,
  "Abbreviation expansion off" (status line: "Abbreviations on" / "Abbreviations
  off"). The state genuinely changes — with it off, typing an abbreviation does not
  auto-expand.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## FMT-56 — Switch Document Format (`format.switch_document_format`, Ctrl+Shift+Grave then K)

*What & why.* Change how the current document is treated/saved (e.g. Markdown vs
plain text vs rich) from a quick menu — this is what decides whether the format
commands above insert Markdown markup or apply real styling.

**Before you start**
- `formatting.md` open. Note it is currently a Markdown document.

**Do this**
1. Press the chord **Ctrl+Shift+Grave**, release, then **K** — or **Format menu
   (Alt, O) ▸ Document Format…**.
2. Arrow the radio menu of formats; pick a **different** format and activate it.
3. Reopen the menu and re-select the **current** format to confirm the no-op path.

**You should see and hear**
- The format menu is a native radio list whose items and checked state the screen
  reader announces as you arrow. Choosing a new format converts the document and
  announces the change in substance (e.g. "Now saving as <format>"); choosing the
  format it already is says "Already editing as <format>". An unknown target is
  reported, not applied silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 50
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
