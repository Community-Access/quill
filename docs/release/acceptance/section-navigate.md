# Section — Navigate menu (`navigate.*`, 28 commands)

Everything about **moving around a document by keyboard and by ear**: jumping by
heading, block, structure, and window region; go-to line/page; the location
history; bookmarks (named, listed, and a one-shot temporary one); the Outline
Navigator and Heading Organizer; the "Go to Anything" and Quick Nav pickers;
per-document language; and the three "speak the current context" commands a
screen-reader user leans on constantly. Finish **Part 0** first.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `navigate.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A +
Works/Surface-exact/Accessible boxes.

Most items live under the **Navigate menu (Alt, N)**; bookmarks are under
**Navigate ▸ Bookmarks**. A few pickers (Quick Nav, Go to Anything) are reached by
their chord or the Command Palette. Every scenario is keyboard-first and its
outcome must be **announced out loud** — a silent move is an accessibility fail.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):
`plain.txt`, and above all **`formatting.md`** — it holds exactly six headings, one
of each level **H1–H6, in order** — and `table.md`. Cross-references to the
core-journey plan (`../qa-core-journeys.md`) JOURNEY-001 (heading navigation) and
JOURNEY-002 (table/structure) are noted where the established wording applies.

**A note on chords.** Several commands use QUILL's two-step chord: press
**Ctrl+Shift+Grave** (Grave is the backtick key, top-left), release, then press the
second key. This section spells each one out.

---

## NAV-01 — Next Heading (`navigate.next_heading`)

*What & why.* Jump the caret to the next heading — the single most-used way a
screen-reader user skims a structured document. No default shortcut; this is the
menu twin of your screen reader's own **H** quick key.

**Before you start**
- Open **`formatting.md`**. Press **Ctrl+Home** to put the caret at the very top.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Next Heading**.
2. Invoke it **six** times in a row (re-open the menu each time, or repeat from the
   Command Palette).
3. As a cross-check, from the top press your screen reader's **H** key six times.

**You should see and hear**
- Each invocation lands the caret on the next heading in turn and announces the
  heading text, its level, and its position — in substance "Moved to next heading,
  H1, 1 of 6: Heading One … at line N, column 1", then H2 (2 of 6), and so on to H6
  (6 of 6). A **seventh** invocation reports **no further headings** ("No next
  heading") rather than wrapping silently. The screen reader's own H key visits the
  same six lines.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-02 — Previous Heading (`navigate.previous_heading`)

*What & why.* Jump the caret to the previous heading — the reverse of NAV-01.

**Before you start**
- `formatting.md` open with the caret on the **last** heading (H6). If unsure, run
  NAV-01 to the bottom first.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Previous Heading** five times.
2. Cross-check with your screen reader's **Shift+H**.

**You should see and hear**
- Headings are announced in descending order — H6 → H5 → … → H1 — each with its
  level and "N of 6" position and landing at line/column. No level is skipped or
  repeated. From H1 a further invocation reports "No previous heading" and the caret
  does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-03 — Next Block (`navigate.next_block`)

*What & why.* Move to the start of the next block (paragraph / list item / other
block), a coarser step than a line and finer than a heading.

**Before you start**
- Open `formatting.md`; caret at the top (**Ctrl+Home**).

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Next Block**.
2. Invoke it repeatedly down through the document.

**You should see and hear**
- The caret jumps to the start of each successive block; QUILL announces "Moved to
  next block at line N, column C". At the end of the document a further invocation
  says **"No next block"** and the caret stays put — never silence.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-04 — Previous Block (`navigate.previous_block`)

*What & why.* Move to the start of the previous block — the reverse of NAV-03.

**Before you start**
- `formatting.md` open with the caret partway down (e.g. after running NAV-03 a few
  times).

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Previous Block** repeatedly up toward the top.

**You should see and hear**
- The caret jumps to the start of each earlier block, announced "Moved to previous
  block at line N, column C". At the top a further invocation says **"No previous
  block"** and the caret does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-05 — Next Structure (`navigate.next_structure`, Alt+Down)

*What & why.* Step to the next structural element for the document's type
(headings, list items, table rows, code fences, and so on) — a markup-aware jump.

**Before you start**
- Open `formatting.md`; caret at the top (**Ctrl+Home**).

**Do this**
1. Press **Alt+Down**, or **Navigate menu (Alt, N) ▸ Next Structure**.
2. Invoke it repeatedly down the document.

**You should see and hear**
- The caret advances to each successive structural element and QUILL announces
  "Moved to next structure at line N, column C". At the end a further press reports
  **"No next structure"**; the caret holds.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-06 — Previous Structure (`navigate.previous_structure`, Alt+Up)

*What & why.* Step to the previous structural element — the reverse of NAV-05.

**Before you start**
- `formatting.md` open, caret partway down.

**Do this**
1. Press **Alt+Up**, or **Navigate menu (Alt, N) ▸ Previous Structure**, repeatedly.

**You should see and hear**
- The caret moves back through structural elements, each announced "Moved to
  previous structure at line N, column C". At the top a further press reports **"No
  previous structure"** with no movement.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-07 — Next Region (`navigate.next_region`, F6)

*What & why.* Cycle keyboard focus between the window's major **regions** — the
editor, the status bar, and (when open) the document tab bar, the Reveal Codes
pane, and the rendered Preview. This is how a keyboard user reaches everything
without a mouse.

**Before you start**
- Open `formatting.md`. To exercise the full rotation, also turn on the **Preview**
  split and the **document tab control** if your build offers them (View menu);
  otherwise the rotation is just Editor and Status Bar, which is still valid.

**Do this**
1. With focus in the editor, press **F6**, or **Navigate menu (Alt, N) ▸ Next
   Region**.
2. Keep pressing **F6** to cycle all the way around back to the editor.

**You should see and hear**
- Each press moves focus to the next region and the **region name is announced**
  (Editor, Reveal Codes, Document Tabs, Preview, Status Bar — only those actually
  present). Focus visibly and audibly lands inside the region, and the cycle wraps
  back to the editor. With only two regions present it toggles between them.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-08 — Previous Region (`navigate.previous_region`, Shift+F6)

*What & why.* Cycle focus between regions in the reverse direction — the reverse of
NAV-07.

**Before you start**
- Same setup as NAV-07; focus somewhere in the region rotation.

**Do this**
1. Press **Shift+F6**, or **Navigate menu (Alt, N) ▸ Previous Region**, repeatedly.

**You should see and hear**
- Focus moves to the previous region each time, the region name announced, cycling
  in the opposite order to NAV-07 and wrapping correctly. No region is skipped or
  unreachable.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-09 — Next Token (`navigate.next_token`)

*What & why.* Move to the next code/text **token** and hear it classified — a
programmer's fine-grained, spoken step through identifiers, keywords, numbers,
brackets, strings, and operators.

**Before you start**
- Open a small code-like document, or use `plain.txt`. Caret at the top
  (**Ctrl+Home**). If you have a code file with a language profile, its keywords
  will be named as keywords.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Next Token**.
2. Invoke it several times across a line that mixes words, a number, and a bracket.

**You should see and hear**
- The caret lands on each next token and QUILL **speaks a classification label** —
  in substance "identifier: myName", "keyword: def", "number: 42", "open paren",
  "string: …", or "operator: +=". At the end of the document it reports **"End of
  document"** (with a boundary sound) and does not move past the edge.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-10 — Previous Token (`navigate.previous_token`)

*What & why.* Move to the previous token and hear it classified — the reverse of
NAV-09.

**Before you start**
- Same document as NAV-09, caret partway along a line.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Previous Token** several times.

**You should see and hear**
- The caret steps back token by token, each announced with the same classification
  labels as NAV-09. At the start it reports **"Beginning of document"** (with a
  boundary sound) and holds the caret.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-11 — Match Bracket (`navigate.match_bracket`, Ctrl+Shift+\)

*What & why.* Jump between a bracket and its partner — indispensable for checking
that parentheses/brackets/braces are balanced.

**Before you start**
- A document containing a matched pair, e.g. type `foo(bar[1] + 2)` on a line. Place
  the caret on the opening `(`.

**Do this**
1. Press **Ctrl+Shift+\\** (Ctrl, Shift, and the backslash key), or **Navigate menu
   (Alt, N) ▸ Match Bracket**.
2. From the matching `)`, invoke it again to jump back.

**You should see and hear**
- The caret jumps to the matching bracket and QUILL announces **"Moved to matching
  bracket"**. With the caret **not** on a bracket, or on an unmatched one, it says
  **"No matching bracket found"** and the caret does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-12 — Go To Line… (`navigate.go_to_line`, Ctrl+G)

*What & why.* Jump straight to a line — or a line and column — by number.

**Before you start**
- Open `formatting.md`.

**Do this**
1. Press **Ctrl+G**, or **Navigate menu (Alt, N) ▸ Go To Line…**.
2. In the **"Enter line or line,column:"** field, type **`5`**; press **Enter**.
3. Re-open it and type **`5,3`** (line 5, column 3); press **Enter**.
4. Re-open it and type a line **past the end** (e.g. `9999`); press **Enter**.

**You should see and hear**
- The text-entry dialog is labelled and keyboard-complete. Line `5` moves the caret
  to the start of line 5 and announces **"Moved to line 5"**; `5,3` announces **"Moved
  to line 5, column 3"**. An out-of-range line raises a spoken error box in substance
  **"Document has only N lines."**; bad input ("use a line number or line,column")
  is likewise reported, never a silent no-op. Escape cancels with no move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-13 — Go To Page… (`navigate.go_to_page`, Ctrl+Shift+G)

*What & why.* Jump to a page. For paged documents this is exact; for plain flowing
text it is an estimate based on word count, and QUILL says so.

**Before you start**
- Open `formatting.md` (or any multi-page-ish document).

**Do this**
1. Press **Ctrl+Shift+G**, or **Navigate menu (Alt, N) ▸ Go To Page…**.
2. Read the prompt, type **`1`**, press **Enter**.
3. Re-open it and type a page **past the end**; press **Enter**.

**You should see and hear**
- The prompt states the page range and, for flowing text, warns it is **estimated
  from word count, not an exact printed page count**. A valid page moves the caret
  and announces **"Moved to page N"**. Out of range raises a spoken **"Document has
  only N page(s)."**; non-numeric input is reported, not swallowed. Escape cancels.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-14 — Back Location (`navigate.back_location`, Alt+Left)

*What & why.* Step back through your **location history** — the places the caret
jumped from — like a browser Back button for the document.

**Before you start**
- Open `formatting.md`. Make a couple of jumps first (e.g. NAV-12 to line 5, then
  Go To Line 20) so there is history to walk.

**Do this**
1. Press **Alt+Left**, or **Navigate menu (Alt, N) ▸ Back Location**, a few times.

**You should see and hear**
- The caret returns to each earlier recorded location and QUILL announces **"Moved
  back"**. When there is no earlier location it says **"No earlier location"** and
  holds.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-15 — Forward Location (`navigate.forward_location`, Alt+Right)

*What & why.* Step forward again through location history — the reverse of NAV-14.

**Before you start**
- Immediately after NAV-14 (so there is a forward history to replay).

**Do this**
1. Press **Alt+Right**, or **Navigate menu (Alt, N) ▸ Forward Location**, a few
   times.

**You should see and hear**
- The caret advances to each later recorded location, announced **"Moved forward"**.
  With nothing ahead it says **"No later location"** and holds.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-16 — Outline Navigator… (`navigate.outline_navigator`, Ctrl+Shift+O)

*What & why.* Open a keyboard-navigable tree of the document's headings (or an
ePub's table of contents, or a YAML file's keys) and jump to any one.

**Before you start**
- Open `formatting.md` (six headings). For the negative check, also have `plain.txt`
  ready.

**Do this**
1. Press **Ctrl+Shift+O**, or **Navigate menu (Alt, N) ▸ Outline Navigator…**.
2. Arrow through the heading tree; press **Enter** on "Heading Four".
3. Repeat with `plain.txt` open.

**You should see and hear**
- A dialog titled **Outline Navigator** lists all six headings as a navigable tree,
  each item announced with its text. Enter jumps the caret to that heading (in
  substance "Moved to heading") and returns focus to the editor. **Escape** cancels
  ("Outline navigation cancelled"). With `plain.txt` (no markup) it reports **"Outline
  is not available for plain text files"** instead of opening an empty dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-17 — Heading Organizer… (`navigate.heading_organizer`, Ctrl+Shift+Grave, then O)

*What & why.* Restructure a document's headings — promote/demote a level, reorder
whole sections, and rename — from one keyboard-driven dialog, without hand-editing
`#` markers.

**Before you start**
- Open `formatting.md`. This works only for **Markdown or HTML**.
- Chord: **Ctrl+Shift+Grave**, release, then **O**.

**Do this**
1. Invoke the chord, or **Navigate menu (Alt, N) ▸ Heading Organizer…**.
2. Arrow to a heading in the list; press **Demote** (or Tab) then **Promote** (or
   Shift+Tab) and hear the level change; use **Move Up / Move Down** to reorder;
   use **Rename…** to change one heading's text.
3. Press **Apply** to commit, or **Escape/Cancel** to discard.

**You should see and hear**
- A dialog titled **Heading Organizer** lists every heading with its level and text;
  its Promote/Demote/Move Up/Move Down/Rename/Validate/Apply/Cancel buttons are all
  labelled and keyboard-operable, and a preview updates as you edit. **Apply**
  rewrites the document ("Applied heading organizer changes"); closing with no edits
  says "closed without changes"; **Cancel/Escape** says "Heading Organizer
  cancelled" and changes nothing. On a plain-text document it reports it is only
  available for Markdown or HTML.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-18 — Quick Nav (Go to Anything) (`navigate.quick_nav`)

*What & why.* One type-ahead picker of every navigable landmark in the document —
headings, links, lists and list items, tables, block quotes, code blocks, and
bookmarks — filterable by category with live counts. No default shortcut; reach it
from the Command Palette.

**Before you start**
- Open `formatting.md` (it has headings, lists, a link, and a code block).

**Do this**
1. Open the **Command Palette** and choose **"Quick Nav"** (or **"Go to Anything"**).
2. In the **"Type to filter"** field type part of a heading (e.g. `Heading`).
3. Arrow the **Category** list to narrow by type and read its counts; select a
   result and press **Enter** (the **Go** button).

**You should see and hear**
- A dialog titled **Quick Nav** with a labelled filter field, a **Category** list
  whose entries show counts (e.g. "All (N)", "Headings (6)", "Links (1)"), and a
  **Results** list. Typing filters the results; choosing a category narrows them;
  **Enter/Go** jumps the caret to that element (in substance "Moved to heading /
  link / list …") and returns focus to the editor. **Escape** cancels ("Quick Nav
  cancelled"). An empty document reports "No navigable elements found".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-19 — Go to Anything (`navigate.go_to_anything`, Ctrl+Shift+Grave, then G)

*What & why.* The universal palette: one search box that jumps to **commands,
headings, bookmarks, and recent files** at once. Type-ahead with prefix
conventions (`>` for commands, `#` for headings, and so on).

**Before you start**
- Open `formatting.md`. Have opened a couple of files recently so "recent files"
  has entries.
- Chord: **Ctrl+Shift+Grave**, release, then **G**.

**Do this**
1. Invoke the chord (or the Command Palette entry "Go to Anything").
2. Type part of a heading (or prefix with **`#`**); select it and press **Enter**.
3. Re-open it and type a command name prefixed with **`>`** to confirm commands
   surface too.

**You should see and hear**
- A search-as-you-type palette that mixes commands, this document's headings,
  bookmarks, and recent files; each result is announced as you arrow. Choosing a
  heading jumps the caret to it; choosing a recent file opens it; choosing a command
  runs it. Escape closes with focus returned. The palette is fully operable by
  keyboard and every row is spoken.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-20 — Set Bookmark… (`navigate.set_bookmark`)

*What & why.* Drop a **named** jump point at the caret so you can return to it later
by name. Bookmarks are saved with the document.

**Before you start**
- Open `formatting.md`; place the caret on the H4 line.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Bookmarks ▸ Set Bookmark…**.
2. The field pre-fills a default name (e.g. **`Bookmark 1`**); type
   **`Section Four`**; press **Enter**.

**You should see and hear**
- A labelled text-entry dialog ("Enter bookmark name (named jump point):"). On
  confirm QUILL announces **`Set bookmark "Section Four"`**. Clearing the name and
  confirming (or Escape) says "Set bookmark cancelled" and adds nothing.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-21 — Go To Bookmark… (`navigate.go_to_bookmark`)

*What & why.* Jump to a previously set named bookmark, chosen from a list.

**Before you start**
- `formatting.md` open with **`Section Four`** set (NAV-20). Move the caret
  somewhere else first so the jump is visible.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Bookmarks ▸ Go To Bookmark…**.
2. In the list, select **`Section Four`**; press **Enter**.

**You should see and hear**
- A labelled single-choice dialog ("Choose bookmark (named jump point):") listing
  your bookmarks with a valid default selection. Enter moves the caret to that
  bookmark and announces **`Jumped to bookmark "Section Four"`**. With **no**
  bookmarks set, invoking it says **"No bookmarks available. Bookmarks are named
  jump points."** rather than opening an empty dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-22 — List Bookmarks… (`navigate.list_bookmarks`, Alt+Shift+B)

*What & why.* Browse all bookmarks in a tree that shows each one's line and column,
and jump from there.

**Before you start**
- `formatting.md` open with at least one bookmark set (NAV-20); set a second on a
  different line for a fuller list.

**Do this**
1. Press **Alt+Shift+B**, or **Navigate menu (Alt, N) ▸ Bookmarks ▸ List
   Bookmarks…**.
2. Arrow the list; press **Enter** on a bookmark.

**You should see and hear**
- A dialog titled **List Bookmarks** under "Bookmarks (Named Jump Points)", each row
  announced with its name and position (e.g. "Section Four (Ln 7, Col 1)"). Enter
  jumps to it and announces `Jumped to bookmark "…"`; Escape says "Bookmark list
  cancelled". With none set it reports "No bookmarks available…".

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-23 — Set Temporary Bookmark (`navigate.set_temp_bookmark`, Ctrl+J)

*What & why.* Drop a single, unnamed, disposable "come back here" mark with **no
dialog** — the fastest possible scratch jump point. It is silently overwritten each
time and forgotten on restart.

**Before you start**
- Open `formatting.md`; place the caret anywhere memorable.

**Do this**
1. Press **Ctrl+J**, or **Navigate menu (Alt, N) ▸ Bookmarks ▸ Set Temporary
   Bookmark**.

**You should see and hear**
- No dialog appears; QUILL announces **"Temporary bookmark set"** immediately.
  Setting it again elsewhere silently replaces the old one (no prompt) — that is by
  design.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-24 — Go to Temporary Bookmark (`navigate.go_to_temp_bookmark`, Ctrl+Shift+J)

*What & why.* Jump straight back to the temporary bookmark — no picker, the twin of
NAV-23.

**Before you start**
- A temporary bookmark set (NAV-23); move the caret elsewhere so the jump is
  visible.

**Do this**
1. Press **Ctrl+Shift+J**, or **Navigate menu (Alt, N) ▸ Bookmarks ▸ Go to
   Temporary Bookmark**.

**You should see and hear**
- The caret returns to the marked spot and QUILL announces **"Jumped to temporary
  bookmark"**. With none set (e.g. right after a restart) it says **"No temporary
  bookmark set"** and holds.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-25 — Set Document Language… (`navigate.set_language`)

*What & why.* Pick the language/syntax profile QUILL uses for **this document's**
editing behaviour (token classification, indentation, structure). It changes
behaviour only — it never renames or converts the file — and is not remembered when
the file is reopened.

**Before you start**
- Open `plain.txt`.

**Do this**
1. Open **Navigate menu (Alt, N) ▸ Set Document Language…**.
2. From the list (which starts with **"Auto-detect from file"**, then the language
   profiles, then **"Plain text"**), choose a profile such as **Python**; press
   **Enter**.
3. Re-open it and choose **"Auto-detect from file"** to clear the override.

**You should see and hear**
- A labelled single-choice dialog stating the change is editing-behaviour only and
  does not rename the file. Choosing a profile announces **"Language set to
  Python."**, and — because `plain.txt`'s extension does not match — appends a spoken
  **Save As tip** (in substance "use File, Save As to save it as a Python (.py)
  file"). Choosing **Auto-detect** announces **"Language set to auto-detect from
  file"**. The file on disk is untouched. Escape cancels.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-26 — Speak Window Title (`navigate.speak_window_title`, Ctrl+Shift+Grave, then F)

*What & why.* Speak the window title bar on demand — the quickest way for a
screen-reader user to confirm which document and app state they are in.

**Before you start**
- Open `formatting.md`.
- Chord: **Ctrl+Shift+Grave**, release, then **F**.

**Do this**
1. Invoke the chord, or **Navigate menu (Alt, N) ▸ Speak Window Title**.

**You should see and hear**
- QUILL speaks the current title bar text (in substance "formatting.md — QUILL …")
  and mirrors it in the status bar. Type an unsaved change and invoke it again: the
  title now reflects the modified marker.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-27 — Speak Full Path (`navigate.speak_full_path`, Ctrl+Shift+Grave, then P)

*What & why.* Speak the current document's full file path on demand — so you always
know exactly which file on disk you are editing.

**Before you start**
- Open `formatting.md` (a saved file). Also have a brand-new unsaved document for
  the negative check.
- Chord: **Ctrl+Shift+Grave**, release, then **P**.

**Do this**
1. Invoke the chord, or **Navigate menu (Alt, N) ▸ Speak Full Path**.
2. Switch to the unsaved document and invoke it again.

**You should see and hear**
- For the saved file, QUILL speaks the **full path** (e.g. `…\qa-samples\formatting.md`)
  and shows it in the status bar. For an unsaved document it speaks in substance
  **"Untitled — not saved to disk"** rather than erroring or going silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## NAV-28 — Speak Status Summary (`navigate.speak_status_summary`, Ctrl+Shift+Grave, then Q)

*What & why.* Speak a one-shot summary of the document's state — name, path,
saved/modified status, and encoding — the "where am I, what state is this file in"
command.

**Before you start**
- Open `formatting.md`; type one character so it is modified, then invoke; optionally
  save (**Ctrl+S**) and invoke again to hear the state flip.
- Chord: **Ctrl+Shift+Grave**, release, then **Q**.

**Do this**
1. Invoke the chord, or **Navigate menu (Alt, N) ▸ Speak Status Summary**.

**You should see and hear**
- QUILL speaks a summary in substance **"formatting.md. <full path>. modified.
  encoding UTF-8"**, mirrored to the status bar. After saving, the same command
  reports **"saved"** in place of "modified". The name, path, modified/saved state,
  and encoding must all be present and correct.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 28
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
