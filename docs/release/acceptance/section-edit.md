# Section — Edit / insert / find (`edit.*`, 86 commands)

Everything about **changing, selecting, moving, finding, and reusing text**: undo,
the selection engine, the mark ring, the 12-slot Copy Tray, the Clip Library,
find/replace, links and inserts, and the line-transform tools. Finish **Part 0**
first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `edit.*`. Read §2–§3 of `README.md` for
the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible
boxes.

**A word on the QUILL chord.** Several commands use QUILL's two-step chord: you
press **Ctrl+Shift+Grave** (Grave is the backtick key, top-left, above Tab),
**release all keys**, then press the final key. Each scenario spells this out.

**A word on the status announcement.** Almost every command here announces its
result through QUILL's status channel, which your screen reader speaks aloud. Exact
wording varies by screen reader and QUILL version; the scenarios below give the
**substance** you must hear (the count, the name, the mode). A silent success is an
accessibility failure even when the text changed correctly.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, `formatting.md`, `table.md`, `reading-order.txt`.

---

## EDIT-01 — Undo (`edit.undo`, Ctrl+Z)

*What & why.* Take back your last edit — the single most-used safety net in any
editor.

**Before you start**
- Open `plain.txt`. Type the word **`banana`** so there is something to undo.

**Do this**
1. Press **Ctrl+Z**, or open **Edit menu (Alt, E) ▸ Undo**.
2. Press **Ctrl+Z** again with nothing left to undo.

**You should see and hear**
- The typed **`banana`** is removed and QUILL announces the undo in substance
  ("Undo"). On the second press with an empty stack, QUILL says there is nothing to
  undo — it never errors or goes silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-02 — Redo (`edit.redo`, Ctrl+Y)

*What & why.* Re-apply an edit you just undid.

**Before you start**
- Continue from EDIT-01: `plain.txt` with `banana` typed then undone.

**Do this**
1. Press **Ctrl+Y**, or **Edit menu ▸ Redo**.
2. Press **Ctrl+Y** again with nothing left to redo.

**You should see and hear**
- The word **`banana`** returns and QUILL announces the redo in substance ("Redo").
  A second press with nothing to redo announces that there is nothing to redo — no
  error, no silence.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-03 — Repeat Next Command (`edit.repeat_command`)

*What & why.* Arm the **next** command to run several times in a row — e.g. delete
five lines by repeating one delete.

**Before you start**
- Open `plain.txt` with several lines; caret at the top.

**Do this**
1. Open the Command Palette (or **Edit menu**) and choose **Repeat Next Command**.
2. In the prompt "Repeat the next command how many times?", the field shows **`2`**;
   type **`3`** and press **Enter**.
3. Now run one repeatable command (for example **Delete Line**).

**You should see and hear**
- After step 2, QUILL announces that the **next** command will repeat 3 times. When
  you run the next command it applies three times. A non-numeric or zero entry is
  rejected with a spoken "Enter a whole number" / "Enter a count of 1 or more".
  Repeat Next Command cannot repeat itself.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-04 — Start Selection (`edit.start_selection`, F8)

*What & why.* Drop a selection anchor at the caret so you can move somewhere else
and select the span between — selecting by keyboard without holding Shift.

**Before you start**
- Open `plain.txt`; put the caret at the start of a word in the middle of a line.

**Do this**
1. Press **F8** (or **Edit menu ▸ Start Selection**).

**You should see and hear**
- QUILL plays a "selection started" sound and announces that selection started, with
  the anchor's **line and column**. No text is highlighted yet; focus stays in the
  editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-05 — Complete Selection (`edit.complete_selection`, Shift+F8)

*What & why.* Close the selection you started with F8, selecting from the anchor to
where the caret is now.

**Before you start**
- Continue from EDIT-04 (anchor set with F8). Now press **Right Arrow** a few times
  to move the caret past several characters.

**Do this**
1. Press **Shift+F8** (or **Edit menu ▸ Complete Selection**).

**You should see and hear**
- The text from the anchor to the caret becomes selected; QUILL plays a
  "selection completed" sound and announces the **character count** plus the start
  and end line/column. If you never pressed F8 first, QUILL tells you to press F8 to
  set an anchor rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-06 — Reselect (`edit.reselect`, Ctrl+Shift+F8)

*What & why.* Bring back the last selection you had, after the caret has moved away
from it.

**Before you start**
- Continue from EDIT-05 (a completed selection exists). Press an arrow key once to
  collapse/lose the highlight.

**Do this**
1. Press **Ctrl+Shift+F8** (or **Edit menu ▸ Reselect**).

**You should see and hear**
- The previous selection is restored and QUILL announces "Reselected N characters"
  with the start/end line and column. If there is no remembered selection (or it is
  no longer valid for the current text) QUILL says so plainly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-07 — Go to Start of Selection (`edit.go_to_start_of_selection`, Alt+Shift+F8)

*What & why.* Jump the caret to the beginning of the current selection.

**Before you start**
- Make a selection (e.g. select a word with Shift+Ctrl+Right).

**Do this**
1. Press **Alt+Shift+F8** (or **Edit menu ▸ Go to Start of Selection**).

**You should see and hear**
- The caret moves to the start of the selection and QUILL announces the destination
  **line and column**. The selection is collapsed (the range is no longer
  highlighted). With nothing selected, QUILL announces "No selection." and does
  nothing else.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-08 — Toggle Extend Selection Mode (`edit.toggle_extend_selection_mode`)

*What & why.* Turn on a sticky "extend" mode so plain arrow keys keep growing the
selection — hands-free from the Shift key.

**Before you start**
- Open `plain.txt`; caret at the start of a line.

**Do this**
1. **Edit menu ▸ Toggle Extend Selection Mode** (or Command Palette). Hear it turn
   **on**.
2. Press **Right Arrow** a few times, then run the command again to turn it **off**.

**You should see and hear**
- Turning it **on** is announced with the anchor line/column; while on, arrow keys
  extend the selection. Turning it **off** is announced, reporting the last
  selected region's start/end line/column (or just "off" if none).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-09 — Select Line (`edit.select_line`)

*What & why.* Select the whole line the caret is on, in one keystroke.

**Before you start**
- Open `plain.txt`; caret anywhere on a non-empty line.

**Do this**
1. **Edit menu ▸ Select Line** (or Command Palette → "Select Line").

**You should see and hear**
- The current line is selected and QUILL announces "Selected line, N words". Focus
  stays in the editor with the line highlighted.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-10 — Select Paragraph (`edit.select_paragraph`)

*What & why.* Select the whole paragraph around the caret.

**Before you start**
- Open `formatting.md`; caret inside a multi-line paragraph.

**Do this**
1. **Edit menu ▸ Select Paragraph** (or Command Palette).

**You should see and hear**
- The paragraph is selected and QUILL announces "Selected paragraph, N words".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-11 — Select Block (`edit.select_block`, Ctrl+Shift+B)

*What & why.* Select the structural "block" around the caret (a larger unit than a
paragraph, e.g. a list or quoted region).

**Before you start**
- Open `formatting.md`; put the caret inside a list or a block quote.

**Do this**
1. Press **Ctrl+Shift+B** (or **Edit menu ▸ Select Block**).

**You should see and hear**
- The surrounding block is selected and QUILL announces "Selected block, N words".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-12 — Select Chunk (`edit.select_chunk`, Ctrl+Space)

*What & why.* Select the "chunk" (sentence-sized unit) around the caret for quick
review or copy.

**Before you start**
- Open `plain.txt`; caret inside a sentence.

**Do this**
1. Press **Ctrl+Space** (or **Edit menu ▸ Select Chunk**).

**You should see and hear**
- The chunk is selected. If it is 40 characters or fewer QUILL speaks the selected
  text itself ("Selected <text>"); for longer chunks it announces "Selected N
  characters". If there is nothing to select it says so.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-13 — Expand Selection (`edit.expand_selection`, Ctrl+Shift+Grave then J)

*What & why.* Grow the selection outward to the next structural unit
(word → line → paragraph → block …), one step per press.

**Before you start**
- Open `formatting.md`; caret inside a word within a paragraph.

**Do this**
1. Press **Ctrl+Shift+Grave**, release, then press **J**. (Or **Edit menu ▸ Expand
   Selection**.)
2. Repeat the chord once more to grow another level.

**You should see and hear**
- Each press selects the next larger unit and QUILL announces the new scope and word
  count (for example "Selected line, N words", then "Selected paragraph, N words").
  When already at the whole document it says so. Each expansion is remembered so
  Shrink can reverse it (EDIT-14).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-14 — Shrink Selection (`edit.shrink_selection`, Ctrl+Shift+Grave then Shift+J)

*What & why.* Undo the last Expand step, shrinking the selection back down one
level.

**Before you start**
- Continue from EDIT-13 with an expanded selection.

**Do this**
1. Press **Ctrl+Shift+Grave**, release, then press **Shift+J**. (Or **Edit menu ▸
   Shrink Selection**.)

**You should see and hear**
- The previous, smaller selection is restored and QUILL announces "Shrank selection"
  (with a word count when the restored range has words). When there is nothing left
  on the expand stack it announces "No selection to shrink".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-15 — Select to Start of Line (`edit.select_to_start_of_line`, Shift+Home)

*What & why.* Select from the caret back to the beginning of the line.

**Before you start**
- Open `plain.txt`; caret in the middle of a line with text to its left.

**Do this**
1. Press **Shift+Home** (or **Edit menu ▸ Select to Start of Line**).

**You should see and hear**
- Everything from the line start to the caret is selected and QUILL announces
  "Selected to start of line".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-16 — Select to End of Line (`edit.select_to_end_of_line`, Shift+End)

*What & why.* Select from the caret to the end of the line.

**Before you start**
- Open `plain.txt`; caret in the middle of a line with text to its right.

**Do this**
1. Press **Shift+End** (or **Edit menu ▸ Select to End of Line**).

**You should see and hear**
- Everything from the caret to the line end is selected and QUILL announces
  "Selected to end of line".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-17 — Select to Start of Document (`edit.select_to_start_of_document`, Ctrl+Shift+Home)

*What & why.* Select from the caret all the way to the top of the document.

**Before you start**
- Open `plain.txt`; caret somewhere in the middle of the file.

**Do this**
1. Press **Ctrl+Shift+Home** (or **Edit menu ▸ Select to Start of Document**).

**You should see and hear**
- Everything from position zero to the caret is selected and QUILL announces
  "Selected to start of document".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-18 — Select to End of Document (`edit.select_to_end_of_document`, Ctrl+Shift+End)

*What & why.* Select from the caret all the way to the end of the document.

**Before you start**
- Open `plain.txt`; caret somewhere in the middle of the file.

**Do this**
1. Press **Ctrl+Shift+End** (or **Edit menu ▸ Select to End of Document**).

**You should see and hear**
- Everything from the caret to the last position is selected and QUILL announces
  "Selected to end of document".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-19 — Unselect All (`edit.unselect_all`, Ctrl+Shift+A)

*What & why.* Clear the current selection, leaving the caret where it is.

**Before you start**
- Any document with an active selection.

**Do this**
1. Press **Ctrl+Shift+A** (or **Edit menu ▸ Unselect All**).

**You should see and hear**
- The selection collapses to the caret and QUILL announces "Selection cleared." The
  caret does not jump.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-20 — Selection Actions (`edit.selection_actions`)

*What & why.* One menu of context-aware things to do to the current selection
(copy, cut, change case, sort, indent, and more) without hunting for each command.

**Before you start**
- Open `formatting.md`; select **several whole lines** (so multi-line actions
  appear).

**Do this**
1. **Edit menu ▸ Selection Actions** (or Command Palette). A choice dialog titled
   "Selection actions (<scope>, <N words>)" opens.
2. Arrow the list; note the choices (Copy, Cut, Upper/Lower/Title/Sentence/Toggle
   case, Expand/Shrink; on multi-line: Sort lines ascending/descending, Indent,
   Outdent, Toggle line comment; Bold/Italic only on a markup surface).
3. Choose **Copy**; press **Enter**.

**You should see and hear**
- With nothing selected, QUILL says "Select text first to use selection actions". The
  dialog is keyboard-navigable with the first item preselected; Escape announces
  "Selection actions cancelled". Choosing an action runs the matching command, whose
  own outcome is then announced (here, the selection is copied).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-21 — Duplicate Selection (`edit.duplicate_selection`)

*What & why.* Make an immediate copy of the selected text (or the current line if
nothing is selected).

**Before you start**
- Open `plain.txt`; select a short phrase (or place the caret on a line to duplicate
  the whole line).

**Do this**
1. **Edit menu ▸ Duplicate Selection** (or Command Palette).

**You should see and hear**
- A copy of the selection is inserted immediately after it and QUILL announces
  "Duplicated N chars"; the newly inserted duplicate becomes the selection. With no
  selection, the current line is duplicated ("Duplicated line").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-22 — Say Selected (`edit.say_selected`)

*What & why.* Speak the current selection aloud on demand — a quick "read me back
what I just picked."

**Before you start**
- Open `plain.txt`; select a sentence. (Not Safe Mode-dependent, but needs a working
  speech voice — the same one your screen reader uses is fine.)

**Do this**
1. **Edit menu ▸ Say Selected** (or Command Palette).

**You should see and hear**
- QUILL speaks the selected text aloud and sets a quiet status with a short preview
  of it. With nothing selected it announces "Nothing selected." and speaks nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-23 — Open Review Buffer (`edit.open_review_buffer`)

*What & why.* Drop the current selection into a read-only window so you can review
it letter by letter with your screen reader without risk of editing it.

**Before you start**
- Open `formatting.md`; select a paragraph.

**Do this**
1. **Edit menu ▸ Open Review Buffer** (or Command Palette).
2. Read the text with your review cursor; close with **Escape** or the Close button.

**You should see and hear**
- A dialog titled "Review Buffer" opens with a **read-only** multi-line text control
  (named as a read-only copy of the selected text) holding the selection; that
  control takes focus. With nothing selected QUILL says "Select text first to open in
  review buffer". Closing returns focus to the editor with the selection intact and a
  quiet "Closed review buffer (N words)".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-24 — Set Mark (`edit.set_mark`, Ctrl+Shift+M)

*What & why.* Drop a temporary "mark" at the caret onto the mark ring so you can
wander off and jump back later.

**Before you start**
- Open `plain.txt`; caret at a spot you want to remember.

**Do this**
1. Press **Ctrl+Shift+M** (or **Edit menu ▸ Set Mark**).

**You should see and hear**
- QUILL announces "Mark ring point set at line L, column C (temporary jump)". The
  caret and selection do not change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-25 — Pop Mark (`edit.pop_mark`, Ctrl+M)

*What & why.* Jump back to the most recent mark you set, removing it from the ring.

**Before you start**
- Continue from EDIT-24 (a mark is set). Move the caret elsewhere first.

**Do this**
1. Press **Ctrl+M** (or **Edit menu ▸ Pop Mark**).

**You should see and hear**
- The caret jumps to the most recent mark and QUILL announces "Popped to mark ring
  point at line L, column C (temporary jump)". With an empty ring it says "No marks
  in ring…" rather than erroring.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-26 — Exchange Point and Mark (`edit.exchange_point_mark`, Ctrl+Shift+X)

*What & why.* Swap the caret with the top mark — bounce between two spots.

**Before you start**
- Set a mark (EDIT-24), then move the caret somewhere else.

**Do this**
1. Press **Ctrl+Shift+X** (or **Edit menu ▸ Exchange Point and Mark**).

**You should see and hear**
- The caret moves to the mark's position and QUILL announces "Exchanged point and
  mark to line L, column C"; the selection collapses there. With an empty ring it
  says "No marks in ring…".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-27 — List Marks (`edit.list_marks`, Alt+M)

*What & why.* See every temporary mark you have set, newest first.

**Before you start**
- Set two or three marks at different lines (EDIT-24, moving the caret between each).

**Do this**
1. Press **Alt+M** (or **Edit menu ▸ List Marks**).
2. Read the list; close it with **Escape** or Enter.

**You should see and hear**
- A message box titled "Mark Ring (Temporary Jump Points)" lists each mark, numbered,
  with its line and column (newest first). After closing, QUILL announces "Listed N
  mark(s)" and focus returns to the editor. With no marks it just says "No marks in
  ring…".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-28 — Set Named Mark (`edit.set_named_mark`)

*What & why.* Remember a spot under a name you choose, so you can jump to it by name
later.

**Before you start**
- Open `plain.txt`; caret where you want the named mark.

**Do this**
1. **Edit menu ▸ Set Named Mark** (or Command Palette).
2. In the "Set Named Mark" dialog, type **`intro`** in the "Mark name:" field and
   press **Enter**.

**You should see and hear**
- The dialog's single field is labelled and keyboard-complete. On confirm QUILL
  announces "Named mark 'intro' set at line L, column C". An empty name is rejected
  with "Mark name cannot be empty".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-29 — Jump to Named Mark (`edit.jump_to_named_mark`)

*What & why.* Return to a named spot you saved earlier.

**Before you start**
- Continue from EDIT-28 (a named mark **`intro`** exists). Move the caret away.

**Do this**
1. **Edit menu ▸ Jump to Named Mark** (or Command Palette).
2. In the "Named Marks" dialog, arrow to **`intro (line L, col C)`** and press
   **Enter**.

**You should see and hear**
- A choice dialog lists each named mark with its line/column. Choosing one moves the
  caret there, returns focus to the editor, and announces "Jumped to mark 'intro' at
  line L, column C". With none defined it says "No named marks. Use Set Named Mark to
  create one."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-30 — Copy All (`edit.copy_all`, Ctrl+F8)

*What & why.* Copy the entire document to the system clipboard in one keystroke.

**Before you start**
- Open `plain.txt` (non-empty).

**Do this**
1. Press **Ctrl+F8** (or **Edit menu ▸ Copy All**).

**You should see and hear**
- QUILL copies the whole document and announces the character count, e.g. "All text
  copied (N characters)." An empty document announces "Document is empty."; the caret
  and selection are not disturbed.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-31 — Copy With Source (`edit.copy_with_source`, Ctrl+Shift+C)

*What & why.* Copy the selection **plus** a reference to where it came from — handy
when quoting a document into an email.

**Before you start**
- Open a **saved** document (e.g. `formatting.md`); select a sentence.

**Do this**
1. Press **Ctrl+Shift+C** (or **Edit menu ▸ Copy With Source**).
2. Paste into another document (**Ctrl+V**) to inspect the result.

**You should see and hear**
- QUILL announces "Copied selection with source"; the clipboard holds the selected
  text followed by a source reference (file/location). With nothing selected it falls
  back to the current line; a clipboard failure says "Could not copy with source".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-32 — Magic Paste (`edit.magic_paste`)

*What & why.* Paste smartly: QUILL detects what is on the clipboard (URL, Markdown,
HTML, image, or plain text) and offers format-aware options instead of dumping raw
markup.

**Before you start**
- Copy some **HTML** to the clipboard (e.g. select text in a web page and copy).
  Open `plain.txt` and place the caret where you want the paste.

**Do this**
1. **Edit menu ▸ Magic Paste** (or Command Palette).
2. In the "Magic Paste: HTML detected" dialog, arrow the "Paste mode" choices; pick
   one and press the **Paste** button (or Enter).

**You should see and hear**
- For non-plain content a dialog opens with a labelled "Paste mode" radio group and
  Paste/Cancel; plain text pastes immediately with no dialog. The chosen mode inserts
  the transformed text at the caret (e.g. "Pasted cleaned HTML (N chars)"), focus
  returns to the editor, caret after the inserted text. An unreadable clipboard says
  "Clipboard is unavailable".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-33 — Copy to Tray Slots 1–12 (`edit.copy_to_tray_1` … `edit.copy_to_tray_12`, chord then Shift+digit)

*What & why.* The Copy Tray is a **persistent 12-slot clipboard**: each slot keeps
its own text (and its own confirmation sound) so you can carry a dozen snippets at
once, across sessions. These twelve commands copy the selection into a chosen slot.

**Before you start**
- Open `plain.txt`. Select a short phrase.
- Chord + slot key mapping: press **Ctrl+Shift+Grave**, release, then the slot key —
  **Shift+1** for slot 1 … **Shift+9** for slot 9, **Shift+0** for slot 10,
  **Shift+-** (hyphen) for slot 11, **Shift+=** for slot 12.

**Do this**
1. Select the phrase. Press **Ctrl+Shift+Grave**, release, then **Shift+1** — this
   is **Copy to Tray Slot 1**. (Or Command Palette → "Copy to Tray Slot 1".)
2. Select a different phrase and repeat with **Shift+2** for slot 2.
3. Continue for each slot you are signing off (each has its own sign-off line below).

**You should see and hear**
- For each slot, QUILL plays that slot's distinct confirmation sound and announces
  "Copied to slot N" (plus the slot's label in parentheses if one is set), with a
  short preview in the status. With nothing selected it says "Select text first to
  copy to slot N". The paste-menu labels refresh to show the new contents.

**Sign off (Copy to Tray Slot 1)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 2)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 3)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 4)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 5)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 6)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 7)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 8)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 9)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 10)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 11)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy to Tray Slot 12)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-34 — Paste from Tray Slots 1–12 (`edit.paste_from_tray_1` … `edit.paste_from_tray_12`, Ctrl+Shift+digit)

*What & why.* Insert what you stored in a Copy Tray slot. These twelve commands are
**multi-press aware**: press once to paste, twice to "peek" (hear the slot without
pasting), three times to open the full Copy Tray.

**Before you start**
- Fill a few slots first (EDIT-33). Open `plain.txt`; caret where you want to paste.
- Key mapping (no chord — these are direct): **Ctrl+Shift+1** … **Ctrl+Shift+9** for
  slots 1–9, **Ctrl+Shift+0** for slot 10, **Ctrl+Shift+-** for slot 11,
  **Ctrl+Shift+=** for slot 12.

**Do this**
1. Press **Ctrl+Shift+1** once — this pastes **Tray Slot 1** at the caret.
2. Press **Ctrl+Shift+2** **twice quickly** — this **peeks** at slot 2 (announces it,
   pastes nothing).
3. Continue for each slot you are signing off (each has its own sign-off line below).

**You should see and hear**
- A single press pastes the slot's text at the caret (or over the selection), plays
  that slot's sound, and announces "Pasted from slot N"; focus stays in the editor
  with the caret after the inserted text. A double press announces the slot preview
  ("Slot N (label) [pinned]: …") without pasting. An empty slot says "Slot N is
  empty". A triple press opens the Copy Tray dialog (see EDIT-36).

**Sign off (Paste from Tray Slot 1)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 2)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 3)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 4)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 5)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 6)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 7)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 8)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 9)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 10)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 11)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Paste from Tray Slot 12)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-35 — Copy to Next Empty Tray Slot (`edit.copy_to_next_slot`)

*What & why.* Copy the selection into the first free slot automatically — no need to
pick a number.

**Before you start**
- Open `plain.txt`; select a phrase. Leave at least one slot empty.

**Do this**
1. **Edit menu ▸ Copy to Next Empty Tray Slot** (or Command Palette).

**You should see and hear**
- QUILL stores the selection in the first empty, non-pinned slot and announces
  "Copied to slot N (first empty)". With nothing selected it says "Select text
  first"; if all twelve slots are occupied it says "All 12 slots occupied. Open Copy
  Tray to manage slots."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-36 — Open Copy Tray (`edit.open_copy_tray`, Ctrl+Shift+Grave then X)

*What & why.* Open the Copy Tray manager to view, relabel, edit, and paste from any
of the twelve slots.

**Before you start**
- Fill a couple of slots first (EDIT-33). Open `plain.txt`.

**Do this**
1. Press **Ctrl+Shift+Grave**, release, then **X**. (Or **Edit menu ▸ Open Copy
   Tray**.)
2. Arrow the "Copy tray slots" list; Tab to the "&Label" and "&Content" fields to
   review/edit; close or paste a slot.

**You should see and hear**
- A dialog titled "Copy Tray" opens with a labelled slots list (initial focus), a
  status line, and editable Label and Content fields. It is fully keyboard-operable.
  Choosing to paste a slot inserts its text at the caret ("Pasted from slot N") and
  refreshes the paste-menu labels; closing returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-37 — Search Copy Tray Slots (`edit.search_tray_slots`)

*What & why.* Find a slot by typing part of its text, then paste the match — faster
than remembering slot numbers.

**Before you start**
- Fill several slots with distinguishable text (EDIT-33). Open `plain.txt`; caret
  where you want to paste.

**Do this**
1. **Edit menu ▸ Search Copy Tray Slots** (or Command Palette).
2. In the "Search Copy Tray Slots" dialog, type a word that appears in one slot; the
   "Matching slots" list filters live. Arrow to a match and press the **Paste**
   button (or Enter).

**You should see and hear**
- The search field takes focus and typing live-filters the results ("Slot N (label)
  [pinned]: …"). If every slot is empty it announces "All copy tray slots are empty".
  Activating a match pastes that slot at the caret, focus returning to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-38 — Clear All Tray Slots (`edit.clear_all_tray_slots`)

*What & why.* Empty all twelve Copy Tray slots at once. Destructive — so it asks
first.

**Before you start**
- At least one slot filled (EDIT-33).

**Do this**
1. **Edit menu ▸ Clear All Tray Slots** (or Command Palette).
2. In the "Clear Copy Tray" prompt ("Clear all 12 copy tray slots? This cannot be
   undone."), first press **Escape**/**No** to confirm cancel is safe; then repeat
   and choose **Yes**.

**You should see and hear**
- A Yes/No warning dialog (defaulting to **No**) appears — a hearable, cancellable
  confirmation before any loss. On Yes, QUILL announces "All copy tray slots cleared"
  and the status shows "Copy tray cleared"; focus returns to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-39 — Keep Selection in Clip Library (`edit.keep_selection_in_clip_library`)

*What & why.* The Clip Library is a rolling history of saved snippets (separate from
the twelve curated tray slots). This saves the current selection into it.

**Before you start**
- Open `plain.txt`; select a phrase.

**Do this**
1. **Edit menu ▸ Keep Selection in Clip Library** (or Command Palette).

**You should see and hear**
- QUILL saves the selection and announces "Kept in the Clip Library." (or "Already in
  the Clip Library." if it was a duplicate). With nothing selected it says "Select
  text first to keep it in the Clip Library".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-40 — Open Clip Library (`edit.open_clip_library`)

*What & why.* Browse the rolling clip history and, if you like, promote a clip into
one of the twelve Copy Tray slots.

**Before you start**
- Keep at least one clip first (EDIT-39). Open `plain.txt`.

**Do this**
1. **Edit menu ▸ Open Clip Library** (or Command Palette).
2. Browse the clips by keyboard. Optionally promote one: when prompted, type a slot
   number **1–12** and confirm. Close the dialog.

**You should see and hear**
- The Clip Library dialog opens and is keyboard-navigable. Promoting a clip prompts
  for a Copy Tray slot (1–12) and reports "Promoted to Copy Tray slot N." An empty or
  out-of-range entry is rejected ("Enter a slot number." / "Slot must be 1-12.").

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-41 — Restore Deleted Text (`edit.restore_deletion`)

*What & why.* Re-insert text you recently deleted, from QUILL's deletion ring — a
targeted "un-delete" that is distinct from Undo.

**Before you start**
- Open `plain.txt`. Select and delete a phrase (or two, to get multiple entries).
  Move the caret to where you want it back.

**Do this**
1. **Edit menu ▸ Restore Deleted Text** (or Command Palette).
2. If a "Restore Deleted Text" choice dialog appears (more than one deletion), arrow
   to the preview you want and press **Enter**.

**You should see and hear**
- With several deletions, a choice dialog lists previews; with one it restores
  directly. The chosen text is inserted at the caret ("Restored deleted text"). An
  empty ring says "No deleted text to restore"; a read-only document says "Document
  is read-only"; cancelling says "Restore deleted text cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-42 — Find… (`edit.find`, Ctrl+F)

*What & why.* Search the document for text.

**Before you start**
- Open `plain.txt`. Pick a word you know appears (e.g. **`the`**).

**Do this**
1. Press **Ctrl+F** (or **Edit menu ▸ Find…**).
2. Type **`the`** in the find field; check/leave **Match Case** and **Whole Word**;
   activate **Find Next**.

**You should see and hear**
- The native Find dialog opens with a find-string field (seeded with your last
  query), Match Case and Whole Word checkboxes, and Find Next / Cancel — all read by
  your screen reader and keyboard-operable. Find Next selects the next match in the
  editor. (Regex/wildcard live in Find All Matches, not here.)

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-43 — Find Next (`edit.find_next`, F3)

*What & why.* Jump to the next occurrence of your last search without reopening the
dialog.

**Before you start**
- Run a Find first (EDIT-42) so there is a stored query with multiple matches.

**Do this**
1. Press **F3** (or **Edit menu ▸ Find Next**).

**You should see and hear**
- The next match forward is selected and the caret lands at its end; QUILL announces
  a "Found next at position N" style message and plays a found sound. If it wrapped
  past the end it appends "(wrapped)". No matches announces "No matches found" with a
  not-found sound; with no stored query it opens the Find dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-44 — Find Previous (`edit.find_previous`, Shift+F3)

*What & why.* Jump to the previous occurrence of your last search.

**Before you start**
- A stored query with multiple matches (EDIT-42); caret partway down the file.

**Do this**
1. Press **Shift+F3** (or **Edit menu ▸ Find Previous**).

**You should see and hear**
- The previous match is selected; QUILL announces a "Found previous at position N"
  message (appending "(wrapped)" if it wrapped to the bottom). No match announces "No
  matches found".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-45 — Find All Matches (`edit.find_all_matches`, Ctrl+Shift+F3)

*What & why.* Count and list every occurrence at once, with plain-text, whole-word,
regex, or wildcard matching.

**Before you start**
- Open `plain.txt` with a word that repeats.

**Do this**
1. Press **Ctrl+Shift+F3** (or **Edit menu ▸ Find All Matches**).
2. If prompted (no stored query), fill the "Find All Matches" form: the find-text
   field, the **Search mode** select (Plain text / Whole word / Regular expression /
   Wildcard), and the **Case-sensitive** checkbox; submit.
3. Read the results list; close it.

**You should see and hear**
- A summary message box lists up to 25 matches as "N. Line X, Column Y" with a total
  count (and "…and N more" beyond 25). QUILL sets status "Found N match(es)" (or "No
  matches found" / "Find error" on a bad pattern). The editor selection is not moved.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-46 — Replace… (`edit.replace`, Ctrl+H)

*What & why.* Find text and replace it, one match at a time.

**Before you start**
- Open `plain.txt`; choose a word to replace (e.g. **`the`** → **`THE`**).

**Do this**
1. Press **Ctrl+H** (or **Edit menu ▸ Replace…**).
2. Fill the find and replace-with fields; set Match Case / Whole Word as needed;
   activate **Replace** for a single replacement.

**You should see and hear**
- The native Replace dialog opens with find and replace-with fields, Match Case and
  Whole Word checkboxes, and Find Next / Replace / Replace All / Cancel — all
  keyboard-operable and read aloud. A single Replace announces "Replaced at position
  N" (or "No replacements made"); the replaced text becomes the selection.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-47 — Replace All… (`edit.replace_all`, Ctrl+Shift+H)

*What & why.* Replace every occurrence in one action.

**Before you start**
- Open `plain.txt`; a word that repeats.

**Do this**
1. Press **Ctrl+Shift+H** (or **Edit menu ▸ Replace All…**).
2. In the Replace dialog, fill find and replace-with, then activate **Replace All**.

**You should see and hear**
- The same native Replace dialog opens (Replace All is its button). Running it
  announces "Replaced N occurrence(s)" (or "No replacements made"); a bad pattern
  shows a spoken error message box. The document text updates accordingly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-48 — Follow Link (`edit.follow_link`, Ctrl+Enter)

*What & why.* Open the hyperlink under the caret in your web browser.

**Before you start**
- Open `formatting.md` (it contains a **QUILL project** hyperlink). Put the caret on
  the link text. Network available to actually load it.

**Do this**
1. Press **Ctrl+Enter** (or **Edit menu ▸ Follow Link**).

**You should see and hear**
- QUILL detects the link and announces "Opening <host>…", then the system browser
  opens the URL. With no link at the caret it says "No link at cursor"; a bare
  in-page anchor (`#…`) says "Anchor links are not yet supported". If no network is
  available, the browser may fail to load — mark **Blocked** if you cannot verify the
  open.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-49 — Insert Link… (`edit.insert_link`, Ctrl+Alt+K)

*What & why.* Insert a hyperlink in the document's markup style, with display text
and a URL.

**Before you start**
- Open `formatting.md`. Optionally select a word to prefill the display text.

**Do this**
1. Press **Ctrl+Alt+K** (or **Edit menu ▸ Insert Link…**).
2. In the "Insert Link" form, fill the **Display text** field and the **URL** field
   (default `https://`); activate **Insert**.

**You should see and hear**
- The form's fields are labelled and keyboard-complete (display text prefilled from
  any selection). On Insert, the link snippet is inserted and the caret lands after
  it; QUILL announces "Inserted link (<markup kind>)". Cancel or a blank URL announces
  "Insert link cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-50 — Insert Equation… (`edit.insert_equation`, Ctrl+Shift+E)

*What & why.* Insert a LaTeX or MathML equation, inline or as a display block.

**Before you start**
- Open `math.md` (a math sample). Caret where the equation should go.

**Do this**
1. Press **Ctrl+Shift+E** (or **Edit menu ▸ Insert Equation…**).
2. In the "Insert Equation" form, type LaTeX (e.g. **`E = mc^2`**) in the equation
   textarea; choose **Display mode** (Inline or Block); activate **Insert**.

**You should see and hear**
- The equation textarea and the Inline/Block select are labelled and
  keyboard-complete (prefilled if a selection held an equation). On Insert the snippet
  is inserted with the caret after it; QUILL announces "Inserted equation". Cancel
  announces "Insert equation cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-51 — Insert Citation… (`edit.insert_citation`)

*What & why.* Build a formatted citation from fields you fill in, inserting a
bibliography entry, an in-text citation, or both.

**Before you start**
- Open `plain.txt`. Have a reference in mind (author, title, year).

**Do this**
1. **Edit menu ▸ Insert Citation…** (or Command Palette).
2. In the "Insert Citation" form, choose **Source type**, **Citation style** (e.g.
   MLA), and what to **Insert** (Bibliography / In-text / Both); fill Author(s),
   Title, Year, and any other fields; activate **Insert**.

**You should see and hear**
- Every select and field is labelled and reachable by keyboard. On Insert, the
  formatted citation text is inserted into the document. Cancel announces "Insert
  citation cancelled".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-52 — Insert Emoji… (`edit.insert_emoji`, Alt+.)

*What & why.* Pick an emoji from an accessible, searchable picker and insert it at
the caret.

**Before you start**
- Open `plain.txt`; caret where the emoji should go.

**Do this**
1. Press **Alt+.** (Alt plus the period/full-stop key), or **Edit menu ▸ Insert
   Emoji…**.
2. Choose a category, or type in the search field (names, keywords, or typed
   smileys like `:)` or `<3`); arrow to a result; activate **Insert**.

**You should see and hear**
- The Emoji Picker opens with a category list (Favorites, Recent, and Unicode
  categories), a search field, a results list, a description read-out, an
  Add/Remove Favorite button, and Insert — all keyboard-operable and announced. On
  Insert QUILL announces "Inserted <name>" and the emoji appears at the caret. If the
  catalog cannot load, a message box points you to the OS emoji input (Windows key +
  period) instead of failing silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-53 — Word Prediction… (`edit.word_prediction`, Ctrl+.)

*What & why.* Manually pop up word-completion suggestions for the fragment you are
typing.

**Before you start**
- Open `plain.txt`; type the start of a word (e.g. **`docu`**) and leave the caret
  right after it. Word prediction depends on the `core.intellisense` feature being
  enabled in the current profile.

**Do this**
1. Press **Ctrl+.** (Ctrl plus period), or **Edit menu ▸ Word Prediction…**.
2. If suggestions appear, arrow to one and accept it.

**You should see and hear**
- A prediction popup appears near the caret listing up to eight completions; QUILL
  announces "{N} prediction(s). {first suggestion}" and accepting one inserts it,
  editor keeping focus. With no candidates it says "No predictions available". If the
  feature is off in this profile it says "Word prediction is unavailable in this
  profile" — mark **N/A** for that profile.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-54 — Read All (`edit.read_all`, Alt+F8)

*What & why.* Read the whole document aloud from the top — a quick "read it back to
me."

**Before you start**
- Open `reading-order.txt`. **Not available in Safe Mode.**

**Do this**
1. Press **Alt+F8** (or **Edit menu ▸ Read All**).

**You should see and hear**
- Any in-progress read-aloud stops, the caret moves to the very top, and QUILL reads
  the document aloud from the beginning. In Safe Mode this is a no-op — mark **N/A**
  if you are testing Safe Mode.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

The next six commands are **line transforms**. They share one rule: if text is
selected they act on every line the selection touches; if nothing is selected they
act only on the **current line** (not the whole document). Each replaces the target
block and re-selects the transformed result, announcing what it did.

## EDIT-55 — Sort Lines Ascending (`edit.sort_lines_ascending`)

*What & why.* Sort the target lines A→Z (case-insensitive).

**Before you start**
- Open `plain.txt`; select a few lines in mixed order (or type a short unsorted list
  and select it).

**Do this**
1. **Edit menu ▸ Sort Lines Ascending** (or Command Palette).

**You should see and hear**
- The lines are reordered ascending and QUILL announces "Sorted lines ascending"; the
  sorted block is re-selected. If the format feature is off it says "…is unavailable
  in this profile"; a read-only document says "Document is read-only".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-56 — Sort Lines Descending (`edit.sort_lines_descending`)

*What & why.* Sort the target lines Z→A.

**Before you start**
- Select a few unsorted lines in `plain.txt`.

**Do this**
1. **Edit menu ▸ Sort Lines Descending** (or Command Palette).

**You should see and hear**
- The lines are reordered descending and QUILL announces "Sorted lines descending";
  the sorted block is re-selected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-57 — Reverse Lines (`edit.reverse_lines`, Alt+Shift+Z)

*What & why.* Flip the order of the target lines top-to-bottom.

**Before you start**
- Select several lines in `plain.txt`.

**Do this**
1. Press **Alt+Shift+Z** (or **Edit menu ▸ Reverse Lines**).

**You should see and hear**
- The line order is reversed and QUILL announces "Reversed lines"; the block is
  re-selected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-58 — Remove Duplicate Lines (`edit.remove_duplicate_lines`)

*What & why.* Drop repeated lines, keeping the first occurrence of each.

**Before you start**
- In `plain.txt`, type a list with some exact duplicate lines and select it.

**Do this**
1. **Edit menu ▸ Remove Duplicate Lines** (or Command Palette).

**You should see and hear**
- Duplicate lines are removed (first kept) and QUILL announces "Removed duplicate
  lines"; the result is re-selected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-59 — Quote Lines (`edit.quote_lines`, Ctrl+Shift+Q)

*What & why.* Prefix each non-empty target line with `> ` — email-style block
quoting.

**Before you start**
- Select a few lines in `plain.txt`.

**Do this**
1. Press **Ctrl+Shift+Q** (or **Edit menu ▸ Quote Lines**).

**You should see and hear**
- Every non-empty line gains a leading `> ` (blank lines untouched) and QUILL
  announces "Quoted lines"; the block is re-selected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-60 — Unquote Lines (`edit.unquote_lines`, Ctrl+Shift+K)

*What & why.* Remove a leading `> ` quote prefix from each target line — the reverse
of Quote Lines.

**Before you start**
- Continue from EDIT-59 (lines now prefixed with `> `), keeping them selected.

**Do this**
1. Press **Ctrl+Shift+K** (or **Edit menu ▸ Unquote Lines**).

**You should see and hear**
- The leading `> ` (or bare `>`) is stripped from each line and QUILL announces
  "Unquoted lines"; the block is re-selected.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

The final four commands are **[GATED future.cleanup]** — they appear only when the
Unicode Cleanup feature is enabled (a dev/admin build). On a public 1.0 build they
are absent: mark them **N/A** rather than failing them. Like the other line
transforms they act on the selection, or the current line when nothing is selected.

## EDIT-61 — Trim Trailing Whitespace (`edit.trim_trailing_whitespace`) [GATED future.cleanup]

*What & why.* Remove trailing spaces and tabs from the end of each target line.

**Before you start**
- **Precondition:** `future.cleanup` feature enabled. If absent, mark **N/A**.
- Select lines that have trailing spaces (add some to `plain.txt` first).

**Do this**
1. **Edit menu ▸ Trim Trailing Whitespace** (or Command Palette).

**You should see and hear**
- Trailing whitespace is removed and QUILL announces "Trimmed trailing whitespace";
  the block is re-selected. Absent on a public build (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-62 — Normalize Whitespace (`edit.normalize_whitespace`) [GATED future.cleanup]

*What & why.* Collapse runs of internal whitespace to single spaces and trim each
line's ends, keeping blank lines.

**Before you start**
- **Precondition:** `future.cleanup` enabled (else **N/A**).
- Select lines with doubled spaces / stray tabs.

**Do this**
1. **Edit menu ▸ Normalize Whitespace** (or Command Palette).

**You should see and hear**
- Internal whitespace is collapsed and ends trimmed; QUILL announces "Normalized
  whitespace"; the block is re-selected. Absent on a public build (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-63 — Convert Indentation to Spaces (`edit.convert_indentation_to_spaces`) [GATED future.cleanup]

*What & why.* Turn leading tabs into spaces at the profile's indent width (leading
indentation only).

**Before you start**
- **Precondition:** `future.cleanup` enabled (else **N/A**).
- Select tab-indented lines.

**Do this**
1. **Edit menu ▸ Convert Indentation to Spaces** (or Command Palette).

**You should see and hear**
- Leading tabs become spaces and QUILL announces "Converted indentation to spaces";
  the block is re-selected. Absent on a public build (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## EDIT-64 — Convert Indentation to Tabs (`edit.convert_indentation_to_tabs`) [GATED future.cleanup]

*What & why.* Turn leading spaces into tabs at the profile's indent width (leading
indentation only) — the reverse of EDIT-63.

**Before you start**
- **Precondition:** `future.cleanup` enabled (else **N/A**).
- Select space-indented lines.

**Do this**
1. **Edit menu ▸ Convert Indentation to Tabs** (or Command Palette).

**You should see and hear**
- Leading spaces become tabs and QUILL announces "Converted indentation to tabs"; the
  block is re-selected. Absent on a public build (**N/A**).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 62
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
