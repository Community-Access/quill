# Section — Braille display & tables (`braille.*`, 45 commands)

Everything QUILL does with **braille-formatted documents** (BRF / BRL — the ASCII
"braille ready format" a transcription house produces): reading where you are on a
braille page, moving by braille and print page, translating text to and from
braille, proofing a transcription page by page, and validating the physical page
layout. These are the tools of a **braille transcriber / proofreader**. Finish
**Part 0** first.

Surface reference (label + command id) is
`../../planning/signoff/SIGNOFF-editor.md` → `braille.*` (45 commands, none with a
default keyboard shortcut). Read §2–§3 of `README.md` for the scenario layout and
the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible boxes.

## Where these commands live

All 45 are under one menu tree: **Tools menu (Alt, T) ▸ Braille**, which opens into
seven submenus — **Status**, **Navigation**, **Page Tools**, **Translation**,
**Proofing**, **Validation**, and **Repair**. None has a default shortcut, so every
scenario also gives you the **Command Palette** route: press
**Ctrl+Shift+Grave** then **K** (or **Tools menu ▸ Command Palette…**), type the
command name, press **Enter**. Where a menu label and the palette label differ,
both are printed — check the one you actually used for **Surface-exact**.

## Before you start — read this once for the whole section

Three preconditions decide what you can run. Set them up now.

1. **A refreshable braille display (strongly recommended, not always required).**
   QUILL sends every spoken announcement to an attached braille display as a
   **flash message** as well as speaking it (this is a real, deliberate output
   channel — braille was previously silent). A BRF document's text is *itself*
   braille (ASCII-braille cells), so as the caret jumps your display shows the
   braille under the caret. So for every scenario there are **three** things to
   confirm: what you **hear** (speech), what you **see** (status bar / new
   document), and — with a display — what you **feel** (the flash message and the
   cells the caret lands on).
   - If you **have** a display: confirm all three. Note in each scenario that the
     announcement reached the display and that the caret's braille line is under
     your fingers after a jump.
   - If you have **no** display: run the scenario by ear and eye, sign **Works** /
     **Accessible** on the spoken + status outcome, and mark the *feel-on-display*
     observation **Blocked** in Notes (it is not a Fail — the command still works).
     Each scenario says what a tester *with* a display should feel so the display
     run is unambiguous.
   - Commands that need **no display at all** (settings toggles, translation/table
     selection, profile switching, trailing-space repair) are flagged in their
     **Before you start** so you never mark them Blocked for lack of hardware.

2. **A real braille (BRF) document.** Most commands do nothing useful unless the
   active document is a braille file — QUILL only treats a document as braille when
   it was opened from a `.brf`, `.brl`, `.pef`, or `.ueb` file. **`qa-samples/` does
   not ship one**, so make one now (it also exercises the translator):
   1. Open **`plain.txt`** from `../qa-samples/`.
   2. **Tools ▸ Braille ▸ Translation ▸ UEB ▸ Translate to Contracted (Grade 2)** —
      a new document of braille cells opens (needs the pack, see #3).
   3. **File ▸ Save As…**, type the name **`sample.brf`** (choose *All files* if no
      BRF type is offered), save it to `qa-samples`.
   4. **File ▸ Open File… ▸ `sample.brf`.** *Now* the active document is a braille
      file and the Braille commands have something to resolve against.
   - If translation is unavailable, bring any real `.brf` from an NLS/transcription
     source and open it. Scenarios that need a braille file open say **"BRF sample
     open"**; if you have none, mark them **Blocked**.

3. **The Braille Translation Pack** (for the eight Translation commands and the
   auto-detect back-translation). If it is **not** installed, the whole
   **Translation** submenu is replaced by a single **Download Braille Translation
   Pack…** item, and the translation commands are unavailable — mark those
   scenarios **Blocked** and note the pack was missing. Installing the pack is
   covered in the Tools/Speech section; do it before the Translation scenarios.

Also set your page geometry once under **Tools ▸ Preferences ▸ Braille** (or accept
defaults): **cells per line** (default 40) and **lines per page** (default 25) feed
the status, metrics, and validation scenarios.

Common inputs used below: `plain.txt`, and the **`sample.brf`** you just created.

---

## Status submenu

## BRL-01 — Read Braille Status (`braille.read_status`)

*What & why.* The one-key "where am I?" for a braille page — the transcriber's most
used call: which braille page, line, and cell the caret is on.

**Before you start**
- **BRF sample open** (`sample.brf`); put the caret somewhere in the middle.
- A display is recommended but not required; the answer is spoken.

**Do this**
1. **Tools menu (Alt, T) ▸ Braille ▸ Status ▸ Read Status**, or Command Palette →
   **"Read Braille Status"**.

**You should see and hear (and feel on the display)**
- A spoken/status summary of the current braille position — in substance **braille
  page N (of the total), line, and cell**, drawn from the live page map. On a
  non-braille document it instead says **"This is not a braille document."** With a
  display, the same status text flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-02 — Read Detailed Braille Status (`braille.read_detailed_status`)

*What & why.* The full picture for proofing: braille position **plus** the detected
print page, continuation letter, running head, and a confidence level for the
detection.

**Before you start**
- **BRF sample open**; caret a few pages in.
- The running head is included only if the "include running head" setting is on
  (see BRL-08/09).

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Read Detailed Status**, or Command Palette →
   **"Read Detailed Braille Status"**.

**You should see and hear (and feel on the display)**
- A longer spoken status than BRL-01: braille page/line/cell **and** the detected
  **print page**, any **continuation letter**, the **running head** (only if the
  setting is on), and a **detection confidence** (high / medium / low). Non-braille
  document → "This is not a braille document." With a display the detailed line
  flashes across the cells (pan to read it all — QUILL never truncates it).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-03 — Read Current Line and Cell (`braille.read_line_and_cell`)

*What & why.* Pinpoints the caret within the page: which line of the page and which
cell of the line — the exact coordinate you quote when reporting a transcription
error.

**Before you start**
- **BRF sample open**; place the caret partway along a line.

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Read Current Line and Cell**, or Command Palette →
   **"Read Current Line and Cell"**.

**You should see and hear (and feel on the display)**
- Spoken in substance **"Line X of N. Cell Y of W."** — the line number within the
  current braille page (of the page's line count) and the cell number within the
  line (of the cells-per-line width). Non-braille document → "This is not a braille
  document." With a display the coordinate flashes and your fingers are already on
  that cell.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-04 — Read Current Braille Page (`braille.read_braille_page`)

*What & why.* Just the braille page number and total — a quick "how far in am I."

**Before you start**
- **BRF sample open**.

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Read Current Braille Page**, or Command Palette →
   **"Read Current Braille Page"**.

**You should see and hear (and feel on the display)**
- Spoken **"Braille page N of M."** Non-braille document → "This is not a braille
  document." Flashes to the display if attached.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-05 — Read Current Print Page (`braille.read_print_page`)

*What & why.* The **print** page (the original book's page) the caret sits on —
detected from print-page indicators in the BRF, not the braille page count.

**Before you start**
- **BRF sample open**. Print pages are only reported if the file carries print-page
  indicators; a freshly translated `sample.brf` may report "unknown."

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Read Current Print Page**, or Command Palette →
   **"Read Current Print Page"**.

**You should see and hear (and feel on the display)**
- Spoken **"Print page N."** when an indicator at or before the caret is found;
  otherwise **"Print page unknown."** Non-braille document → "This is not a braille
  document." Both outcomes are correct behavior — note which you got.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-06 — Read Progress Summary (`braille.read_progress_summary`)

*What & why.* How far through the document you are, as a percentage — for pacing a
long transcription.

**Before you start**
- **BRF sample open**; caret roughly mid-document. (Palette label:
  **"Read Progress Summary"** — do not confuse it with the *proofing* progress in
  BRL-31, whose palette label is "Read Proofing Progress Summary".)

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Read Progress Summary**, or Command Palette →
   **"Read Progress Summary"**.

**You should see and hear (and feel on the display)**
- Spoken **"Braille page N of M, P percent through the document."** Non-braille
  document → "This is not a braille document." Flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-07 — Announce Running Head (`braille.announce_running_head`)

*What & why.* Speaks the **running head** (the repeated page-top title line)
detected for the current braille page.

**Before you start**
- **BRF sample open**. A file with no repeated header line will honestly report
  none — that is a valid result.

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Announce Running Head**, or Command Palette →
   **"Announce Running Head"**.

**You should see and hear (and feel on the display)**
- Spoken **"Running head: <text>."** when one is detected for this page; otherwise
  **"No running head detected for this page."** Non-braille document → "This is not
  a braille document." The head text flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-08 — Include Running Head in Status (`braille.use_running_head_in_status`)

*What & why.* Turns **on** inclusion of the running head in the detailed status
(BRL-02). A preference toggle, not a document action.

**Before you start**
- **No display and no BRF file needed** — this only flips a setting. (Verify its
  effect afterward with BRL-02 on a file that has a running head.)

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Include Running Head in Status**, or Command
   Palette → **"Include Running Head in Status"**.

**You should see and hear**
- Spoken **"Running head will be included in the detailed status."** The
  `braille_include_running_head` preference is now on; a later Read Detailed Status
  includes the head.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-09 — Omit Running Head from Status (`braille.ignore_running_head_for_status`)

*What & why.* Turns the same preference **off** again — the counterpart to BRL-08.

**Before you start**
- **No display and no BRF file needed.** Run BRL-08 first so there is something to
  turn off.

**Do this**
1. **Tools ▸ Braille ▸ Status ▸ Omit Running Head from Status**, or Command Palette
   → **"Omit Running Head from Status"**.

**You should see and hear**
- Spoken **"Running head will be omitted from the detailed status."** A later Read
  Detailed Status no longer speaks the head. Toggle back and forth to confirm both
  directions.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Navigation submenu

## BRL-10 — Go to Braille Page… (`braille.go_to_page`)

*What & why.* Jump straight to a braille page by number.

**Before you start**
- **BRF sample open**. Note the total page count (from BRL-04) so you can pick a
  valid target.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Go to Braille Page…**, or Command Palette →
   **"Go to Braille Page…"**.
2. In the dialog **"Enter a braille page number (1-N):"** type a page (e.g. **2**);
   press **Enter**.

**You should see and hear (and feel on the display)**
- The caret moves to the start of that page, focus returns to the editor, and QUILL
  speaks **"Braille page N of M."** A non-numeric entry raises a spoken/visible
  error **"Page number must be a number."** and does not move. With a display, the
  first cells of the target page are now under your fingers.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-11 — Next Braille Page (`braille.next_page`)

*What & why.* Step forward one braille page.

**Before you start**
- **BRF sample open**; caret not on the last page.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Next Braille Page**, or Command Palette →
   **"Next Braille Page"**.

**You should see and hear (and feel on the display)**
- Caret jumps to the next page start; spoken **"Braille page N of M."** On the last
  page it instead says **"No next braille page."** and does not move. Display
  follows the caret to the new page.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-12 — Previous Braille Page (`braille.previous_page`)

*What & why.* Step back one braille page — the mirror of BRL-11.

**Before you start**
- **BRF sample open**; caret not on the first page.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Previous Braille Page**, or Command Palette →
   **"Previous Braille Page"**.

**You should see and hear (and feel on the display)**
- Caret jumps to the previous page start; spoken **"Braille page N of M."** On the
  first page it says **"No previous braille page."** and does not move.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-13 — Go to Print Page… (`braille.go_to_print_page`)

*What & why.* Jump to a **print** page (original book page) by number — QUILL finds
the braille page that hosts it.

**Before you start**
- **BRF sample open** with detected print pages. If none are detected the command
  says so (see below); a plain translated `sample.brf` may have none.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Go to Print Page…**, or Command Palette →
   **"Go to Print Page…"**.
2. In **"Enter a print page number:"** type a page; press **Enter**.

**You should see and hear (and feel on the display)**
- If print pages exist and your number matches one, the caret moves to that braille
  page and QUILL speaks **"Print page X on braille page Y."** If no print pages were
  detected: **"No print pages detected. Try recalculating the page map."** If your
  number was not among them: **"Print page X was not detected."** A non-numeric
  entry → spoken error. All are correct — note which.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-14 — Next Print Page Change (`braille.next_print_page_change`)

*What & why.* Jump forward to the next place where the **print** page number
changes — the transcriber's way to hop print page to print page.

**Before you start**
- **BRF sample open** with detected print-page indicators.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Next Print Page Change**, or Command Palette →
   **"Next Print Page Change"**.

**You should see and hear (and feel on the display)**
- Caret moves to the next print-page-change and QUILL speaks **"Print page change:
  print page X on braille page Y."** (or **"an unknown print page"** when the number
  could not be read). With none ahead: **"No next print page change."** Display
  follows the caret.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-15 — Previous Print Page Change (`braille.previous_print_page_change`)

*What & why.* The backward mirror of BRL-14.

**Before you start**
- **BRF sample open** with detected print-page indicators; caret past the first
  change.

**Do this**
1. **Tools ▸ Braille ▸ Navigation ▸ Previous Print Page Change**, or Command Palette
   → **"Previous Print Page Change"**.

**You should see and hear (and feel on the display)**
- Caret moves back to the previous print-page-change; spoken **"Print page change:
  print page X on braille page Y."** With none behind: **"No previous print page
  change."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Page Tools submenu

## BRL-16 — Insert Braille Page Break (`braille.insert_page_break`)

*What & why.* Insert a form-feed (the braille page-break character) at the caret.

**Before you start**
- Any document with an editor focused (a BRF sample is ideal so the map updates).

**Do this**
1. Place the caret where the new page should begin.
2. **Tools ▸ Braille ▸ Page Tools ▸ Insert Braille Page Break**, or Command Palette
   → **"Insert Braille Page Break"**.

**You should see and hear (and feel on the display)**
- A form-feed character is written at the caret and QUILL speaks **"Braille page
  break inserted."** On a BRF file the page total from BRL-04 goes up by one after
  a recalculate (BRL-19). Display flashes the confirmation.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-17 — Remove Braille Page Break (`braille.remove_page_break`)

*What & why.* Delete a braille page-break character at (or just before) the caret.

**Before you start**
- A document containing a page break; put the caret on or right after the break you
  inserted in BRL-16.

**Do this**
1. **Tools ▸ Braille ▸ Page Tools ▸ Remove Braille Page Break**, or Command Palette
   → **"Remove Braille Page Break"**.

**You should see and hear (and feel on the display)**
- If a break is at or immediately before the caret it is removed and QUILL speaks
  **"Braille page break removed."** If there is none there: **"No braille page break
  at the cursor."** and nothing changes.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-18 — Normalize Line Endings (`braille.normalize_line_endings`)

*What & why.* Intended to normalize the file's line endings for clean BRF output.
**Known state:** this is a Phase-1 stub in 1.0 — the wiring exists but the action
is not implemented yet.

**Before you start**
- Any document; no display or BRF file needed.

**Do this**
1. **Tools ▸ Braille ▸ Page Tools ▸ Normalize Line Endings**, or Command Palette →
   **"Normalize Line Endings"**.

**You should see and hear**
- Spoken/status **"Normalize line endings is not available yet."** and no change to
  the document. This is the **expected** 1.0 behavior — pass it if you hear exactly
  that (an honest "not yet", never a silent no-op or a crash). If it silently does
  nothing with **no** announcement, fail **Accessible**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-19 — Recalculate Page Map (`braille.recalculate_page_map`)

*What & why.* Force QUILL to rebuild the braille page map — do this after editing
breaks or changing page geometry so status and navigation are accurate again.

**Before you start**
- **BRF sample open** (ideally after inserting/removing a break in BRL-16/17).

**Do this**
1. **Tools ▸ Braille ▸ Page Tools ▸ Recalculate Page Map**, or Command Palette →
   **"Recalculate Page Map"**.

**You should see and hear (and feel on the display)**
- Spoken **"Braille page map recalculated."**, the status bar refreshes, and a
  following BRL-04 reflects any new page count. Flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-20 — Save As Clean BRF (`braille.save_as_clean`)

*What & why.* Intended to save a "cleaned" copy of the BRF. **Known state:** a
Phase-1 stub in 1.0 — registered so the wiring is stable, action not implemented.
It is **not** on the Braille menu; reach it from the Command Palette only.

**Before you start**
- Any document; no display needed. (There is no menu item — use the palette.)

**Do this**
1. Command Palette (**Ctrl+Shift+Grave, K**) → **"Save As Clean BRF"** → **Enter**.

**You should see and hear**
- Spoken/status **"Save as clean BRF is not available yet."** and nothing is
  written. This is the **expected** 1.0 behavior — pass on hearing exactly that. A
  silent no-op or a crash is a fail.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Translation submenu (Braille Translation Pack required)

> If the Translation submenu is missing and a **Download Braille Translation
> Pack…** item is in its place, the pack is not installed — mark **BRL-21…BRL-28
> Blocked** and note it. None of these need a braille *display*; they operate on the
> editor text and open the result as a new document.

## BRL-21 — Translate to UEB Grade 2 / Contracted (`braille.translate_ueb_g2`)

*What & why.* Forward-translate the whole document into **UEB contracted** braille
— the default modern English braille. Table selection, no display needed.

**Before you start**
- Open **`plain.txt`** (or any text). Pack installed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ UEB ▸ Translate to Contracted (Grade 2)**, or
   Command Palette → **"Translate to UEB Grade 2 (Contracted)"**.

**You should see and hear (and feel on the display)**
- QUILL translates via the braille worker and opens a **new document** of braille
  cells, focus in it; spoken **"Translated to UEB G2. N braille pages."** Empty
  source → **"Nothing to translate."** A worker failure shows a spoken **and**
  dialog error ("Translation failed: …"), never silence. With a display, the new
  document's cells are readable under your fingers.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-22 — Translate to UEB Grade 1 / Uncontracted (`braille.translate_ueb_g1`)

*What & why.* Forward-translate into **UEB uncontracted** (letter-for-letter, no
contractions) — used for early readers and some technical text.

**Before you start**
- Text document open; pack installed. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ UEB ▸ Translate to Uncontracted (Grade 1)**,
   or Command Palette → **"Translate to UEB Grade 1 (Uncontracted)"**.

**You should see and hear (and feel on the display)**
- New braille document opens; spoken **"Translated to UEB G1. N braille pages."**
  It should be visibly longer than the Grade 2 result of the same text (no
  contractions). Empty source / failure handled as in BRL-21.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-23 — Translate Selection to UEB (`braille.translate_selection`)

*What & why.* Translate just the **selected** text to UEB contracted — for spot
work without converting the whole file.

**Before you start**
- Text document open; **select a sentence or two**. Pack installed. No display
  needed.

**Do this**
1. Select the text.
2. **Tools ▸ Braille ▸ Translation ▸ UEB ▸ Translate Selection**, or Command Palette
   → **"Translate Selection to UEB"**.

**You should see and hear (and feel on the display)**
- Only the selection is translated and opened as a new braille document; spoken
  **"Translated selection to UEB G2. N braille pages."** With nothing selected the
  source is empty → **"Nothing to translate."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-24 — Back-Translate UEB (draft) (`braille.back_translate`)

*What & why.* Turn braille back into readable text (a **draft** for proofreading).
Uses the selection if there is one, else the whole document, assuming UEB.

**Before you start**
- **`sample.brf` open** (or select some braille). Pack installed. No display needed.

**Do this**
1. Optionally select a braille passage.
2. **Tools ▸ Braille ▸ Translation ▸ UEB ▸ Back-Translate (draft)**, or Command
   Palette → **"Back-Translate UEB (draft)"**.

**You should see and hear (and feel on the display)**
- A new text document opens with the recovered words; spoken **"Back-translation
  draft from selection/document. N words. Review against the BRF."** The word "draft"
  matters — it is not guaranteed exact. Empty/failure handled as in BRL-21.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-25 — Back-Translate to Text, Auto-Detect Code (`braille.back_translate_auto`)

*What & why.* The "just read this braille to me" path — QUILL detects the braille
code itself (UEB G1/G2, EBAE G1/G2, computer braille) and back-translates without
asking you to pick a table.

**Before you start**
- **`sample.brf` open** (or a braille selection). Pack installed. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ Back-Translate to Text (Auto-Detect Code)**, or
   Command Palette → **"Back-Translate to Text (Auto-Detect Braille Code)"**.

**You should see and hear (and feel on the display)**
- First a spoken **"Detecting braille code…"**, then a new draft document and a
  spoken **"Detected <code>. Back-translation draft from … : N words. Use Save As to
  export it as Markdown, HTML, Word, or plain text."** A detection failure surfaces a
  spoken + dialog error, never silence.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-26 — Convert BRF File to Document… (`braille.convert_brf_file`)

*What & why.* One-shot: pick any `.brf`/`.brl` **on disk**, auto-detect its code,
and open it as a normal editable document you can then Save As to any format — BRF
in, anything out.

**Before you start**
- A `.brf`/`.brl` file on disk (e.g. your `sample.brf`). Pack installed. No display
  needed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ Convert BRF File to Document…**, or Command
   Palette → **"Convert BRF File to Document…"**.
2. In the file dialog choose the `.brf`; **Enter**.

**You should see and hear (and feel on the display)**
- A new draft document opens with the recovered text; spoken **"Converted
  <name>. Detected <code>: N words. Use Save As to export it…"**. An unreadable file
  reports a spoken + dialog error naming the file. Confirm you can then **File ▸ Save
  As…** it to `.md`/`.docx`/`.txt`.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-27 — Translate to Standard American Contracted / Legacy Grade 2 (`braille.translate_standard_g2`)

*What & why.* Forward-translate into **EBAE / Standard American English contracted**
(the pre-UEB legacy code) — for shops still producing legacy braille.

**Before you start**
- Text document open; pack installed. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ Standard American English (Legacy) ▸ Translate
   to Contracted (Grade 2)**, or Command Palette → **"Translate to Standard American
   Braille Contracted (Legacy Grade 2)"**.

**You should see and hear (and feel on the display)**
- New braille document; spoken **"Translated to Standard American Grade 2. N braille
  pages."** Empty/failure handled as in BRL-21.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-28 — Translate to Standard American Uncontracted / Legacy Grade 1 (`braille.translate_standard_g1`)

*What & why.* The uncontracted legacy counterpart to BRL-27.

**Before you start**
- Text document open; pack installed. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Translation ▸ Standard American English (Legacy) ▸ Translate
   to Uncontracted (Grade 1)**, or Command Palette → **"Translate to Standard
   American Braille Uncontracted (Legacy Grade 1)"**.

**You should see and hear (and feel on the display)**
- New braille document; spoken **"Translated to Standard American Grade 1. N braille
  pages."**

> **Also present, not a numbered scenario:** a **More Languages** item appears under
> Translation when the installed pack ships extra `brf_profiles.json` profiles. It
> is a dynamic, pack-dependent list (no fixed `braille.*` command id in the 45), so
> it is out of scope for this section — if it is present, spot-check that picking a
> language translates and announces "Translated using <profile>. N braille pages",
> and record it under Notes here.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Proofing submenu (per-page proofreading; state saved to the file's sidecar)

> Proofing marks and notes are stored in a **sidecar** file next to the BRF, so the
> BRF itself is never modified and the file must be **saved to disk** first. If the
> document has never been saved, every proofing command says **"Save the braille
> file before tracking proofing."** — that is correct behavior, not a failure.

## BRL-29 — Mark Current Page Proofed (`braille.mark_page_proofed`)

*What & why.* Flag the braille page at the caret as **proofed** — the core
transcription-QA gesture.

**Before you start**
- **`sample.brf` open and saved on disk**; caret on the page to mark. No display
  needed to sign the spoken outcome.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Mark Current Page Proofed**, or Command Palette →
   **"Mark Current Braille Page as Proofed"**.

**You should see and hear (and feel on the display)**
- Spoken confirmation that the current braille page is marked proofed (the sidecar
  is written). On an unsaved document → "Save the braille file before tracking
  proofing." Flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-30 — Mark Current Page Needs Review (`braille.mark_page_needs_review`)

*What & why.* Flag the current braille page as **needs review** — the "come back to
this" marker.

**Before you start**
- **`sample.brf` open and saved**; caret on the page.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Mark Current Page Needs Review**, or Command
   Palette → **"Mark Current Braille Page Needs Review"**.

**You should see and hear (and feel on the display)**
- Spoken confirmation the page is marked needs-review; sidecar written. Unsaved →
  the save-first message.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-31 — Clear Proofing Mark (`braille.clear_proofing_mark`)

*What & why.* Remove any proofed / needs-review mark from the current braille page.

**Before you start**
- **`sample.brf` open and saved**; caret on a page you marked in BRL-29/30.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Clear Proofing Mark**, or Command Palette →
   **"Clear Proofing Mark on Current Page"**.

**You should see and hear (and feel on the display)**
- Spoken confirmation the mark is cleared; sidecar updated. A later Read Proofing
  Progress (BRL-33) shows the counts drop.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-32 — Add Proofing Note… (`braille.add_proofing_note`)

*What & why.* Attach a free-text note to the current braille page (e.g. "check
this contraction").

**Before you start**
- **`sample.brf` open and saved**; caret on the page. A note text ready, e.g.
  **`Check dropped word`**.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Add Proofing Note…**, or Command Palette →
   **"Add Proofing Note to Current Page"**.
2. In **"Note for braille page N:"** type your note; **Enter**.

**You should see and hear (and feel on the display)**
- The labelled entry dialog is keyboard-complete; on confirm the note is saved to
  the sidecar and QUILL speaks a confirmation. Escape cancels with no note added.
  Unsaved document → the save-first message.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-33 — Read Proofing Progress Summary (`braille.read_proofing_progress`)

*What & why.* How much of the transcription has been proofed — proofed vs
needs-review vs remaining. (Distinct from the plain progress in BRL-06.)

**Before you start**
- **`sample.brf` open and saved**, with a few pages marked (BRL-29/30). Palette
  label: **"Read Proofing Progress Summary"**.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Read Progress Summary**, or Command Palette →
   **"Read Proofing Progress Summary"**.

**You should see and hear (and feel on the display)**
- A spoken summary of proofing progress across the page count (proofed / needs
  review counts, current page). Unsaved → the save-first message. Flashes to the
  display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-34 — List Proofed Pages… (`braille.list_proofed_pages`)

*What & why.* A pick-list of every page marked proofed; choosing one jumps there.

**Before you start**
- **`sample.brf` open and saved**, with at least one page marked proofed.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ List Proofed Pages…**, or Command Palette →
   **"List Proofed Braille Pages"**.
2. Arrow the list; pick a page; **Enter**.

**You should see and hear (and feel on the display)**
- A keyboard-navigable **single-choice** dialog titled "Proofed Pages (N)" listing
  "Braille page X" entries; choosing one moves the caret there and speaks "Braille
  page N of M." With none marked: spoken **"No proofed pages."** and no dialog.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-35 — List Pages Needing Review… (`braille.list_pages_needing_review`)

*What & why.* The needs-review counterpart to BRL-34.

**Before you start**
- **`sample.brf` open and saved**, with at least one page marked needs-review.

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ List Pages Needing Review…**, or Command Palette →
   **"List Braille Pages Needing Review"**.
2. Pick a page; **Enter**.

**You should see and hear (and feel on the display)**
- A single-choice dialog titled "Pages Needing Review (N)"; choosing one jumps there
  and speaks the page. With none: spoken **"No pages needing review."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-36 — Export Proofing Report… (`braille.export_proofing_report`)

*What & why.* Write a plain-text report of the proofing state (proofed pages,
pages needing review, notes) to a file to hand off.

**Before you start**
- **`sample.brf` open and saved**, with some marks/notes. A target name is
  suggested for you (`<name>-proofing.txt`).

**Do this**
1. **Tools ▸ Braille ▸ Proofing ▸ Export Proofing Report…**, or Command Palette →
   **"Export Proofing Report"**.
2. In the Save dialog accept or change the name; **Enter**.

**You should see and hear (and feel on the display)**
- A keyboard-navigable Save dialog defaulting to `<name>-proofing.txt`; on confirm a
  UTF-8 text report is written and QUILL speaks **"Proofing report saved to
  <name>."** Open the file to confirm it lists the pages and notes. Unsaved braille
  document → the save-first message.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Validation submenu

## BRL-37 — Validate BRF Layout… (`braille.validate_layout`)

*What & why.* Check the file against your page geometry (cells per line, lines per
page) and list every layout warning — overlong lines, overfull pages, etc.

**Before you start**
- **`sample.brf` open**. Geometry set under Preferences ▸ Braille (defaults 40×25
  are fine). No display needed to sign the spoken/dialog outcome.

**Do this**
1. **Tools ▸ Braille ▸ Validation ▸ Validate BRF Layout…**, or Command Palette →
   **"Validate BRF Layout"**.

**You should see and hear (and feel on the display)**
- If clean: spoken **"No braille layout warnings found."** If not: a keyboard-
  navigable single-choice dialog "N layout warning(s)" listing each as **"Line L,
  page P, <severity>: <message>"**; choosing one jumps the caret to it and speaks
  "Warning k of N: <message>". This also arms BRL-38…BRL-40.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-38 — Next Braille Layout Warning (`braille.next_warning`)

*What & why.* Step to the next warning from the last validation run.

**Before you start**
- Run **BRL-37** first and get at least one warning. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Validation ▸ Next Warning**, or Command Palette →
   **"Next Braille Layout Warning"**.

**You should see and hear (and feel on the display)**
- Caret moves to the next warning and QUILL speaks **"Warning k of N: <message>."**
  Past the last: **"No next warning."** With no validation run yet: **"No warnings.
  Run Validate BRF Layout first."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-39 — Previous Braille Layout Warning (`braille.previous_warning`)

*What & why.* Step back to the previous warning — mirror of BRL-38.

**Before you start**
- Validation run with warnings; caret past the first warning. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Validation ▸ Previous Warning**, or Command Palette →
   **"Previous Braille Layout Warning"**.

**You should see and hear (and feel on the display)**
- Caret moves to the previous warning; spoken **"Warning k of N: <message>."** Before
  the first: **"No previous warning."** No run yet: the "Run Validate BRF Layout
  first" message.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-40 — Braille Layout Warnings Summary (`braille.warnings_summary`)

*What & why.* A spoken tally of the current warnings — how many and the top
categories — without stepping through them.

**Before you start**
- Run **BRL-37** first. No display needed.

**Do this**
1. **Tools ▸ Braille ▸ Validation ▸ Warnings Summary**, or Command Palette →
   **"Braille Layout Warnings Summary"**.

**You should see and hear (and feel on the display)**
- Spoken **"N layout warning(s). Top categories: <kind> (c), …."** If the run found
  none: **"No braille layout warnings found."** If nothing has been validated:
  **"No validation run yet. Run Validate BRF Layout first."**

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## Repair submenu (NLS-BRT parity: width/depth diagnostics)

## BRL-41 — Read Braille Layout Metrics (`braille.read_layout_metrics`)

*What & why.* Speak the NLS-style layout metrics for the file at the caret —
cells/line and lines/page usage against your configured limits.

**Before you start**
- **`sample.brf` open**. Geometry set (defaults 40×25). No display needed to sign
  the spoken outcome.

**Do this**
1. **Tools ▸ Braille ▸ Repair ▸ Read Layout Metrics**, or Command Palette →
   **"Read Braille Layout Metrics"**.

**You should see and hear (and feel on the display)**
- A spoken description of the layout metrics (line/page dimensions relative to the
  configured limits). Non-braille document → "This is not a braille document."
  Flashes to the display.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-42 — Go to Longest Braille Line (`braille.go_to_longest_line`)

*What & why.* Jump straight to the longest line in the document — the usual suspect
for a "page width exceeded" error.

**Before you start**
- A document with text (a BRF sample is ideal). Works on any document's editor text
  — no braille resolver required. No display needed to sign the spoken outcome.

**Do this**
1. **Tools ▸ Braille ▸ Repair ▸ Go to Longest Line**, or Command Palette →
   **"Go to Longest Braille Line"**.

**You should see and hear (and feel on the display)**
- Caret jumps to the longest line; spoken **"Longest line: C cells."**, plus
  **" Page width exceeded."** appended when C exceeds your cells-per-line. Empty
  document → **"The document is empty."** With a display, the offending line is under
  your fingers.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-43 — Go to Longest Braille Page (`braille.go_to_longest_page`)

*What & why.* Jump to the page with the most lines — the usual suspect for a "page
depth exceeded" error.

**Before you start**
- **`sample.brf` open** (needs the braille page map). No display needed to sign the
  spoken outcome.

**Do this**
1. **Tools ▸ Braille ▸ Repair ▸ Go to Longest Page**, or Command Palette →
   **"Go to Longest Braille Page"**.

**You should see and hear (and feel on the display)**
- Caret jumps to that page; spoken **"Longest page: braille page N of M, L lines."**,
  plus **" Page depth exceeded."** when L exceeds your lines-per-page. Non-braille
  document → "This is not a braille document."

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-44 — Remove Trailing Spaces on Current Line (`braille.strip_trailing_spaces_line`)

*What & why.* Strip trailing spaces from the caret's line — trailing spaces are a
classic hidden cause of "page width exceeded" in BRF.

**Before you start**
- A document; put the caret on a line you have padded with trailing spaces. Works on
  any document. No display needed. (Read-only documents are refused with a spoken
  "Document is read-only".)

**Do this**
1. **Tools ▸ Braille ▸ Repair ▸ Remove Trailing Spaces on This Line**, or Command
   Palette → **"Remove Trailing Spaces on Current Line"**.

**You should see and hear (and feel on the display)**
- The trailing spaces on that line vanish and QUILL speaks **"Removed K trailing
  character(s)."** With none present: **"No trailing spaces on this line."** and no
  change. The caret is kept sensible.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## BRL-45 — Remove Trailing Spaces in Whole File (`braille.strip_trailing_spaces_document`)

*What & why.* Strip trailing spaces from every line at once — the bulk fix before
sending a BRF to emboss.

**Before you start**
- A document with trailing spaces on several lines. Works on any document. No
  display needed.

**Do this**
1. **Tools ▸ Braille ▸ Repair ▸ Remove Trailing Spaces in Whole File**, or Command
   Palette → **"Remove Trailing Spaces in Whole File"**.

**You should see and hear (and feel on the display)**
- Every line's trailing spaces are removed and QUILL speaks **"Removed K trailing
  character(s) from the file."** With none present: **"No trailing spaces found."**
  and no change. Re-run BRL-41/BRL-37 to confirm width warnings drop.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

### Section sign-off
- Tester:
- Screen reader(s) + version(s):
- Refreshable braille display (model / none):
- Braille Translation Pack installed (yes/no):
- Build / commit tested:
- Environment (E1–E6):
- Date:
- Scenarios passed / total: ___ / 45
- Release blockers found (must be zero to ship):
- Result: Pass / Pass-with-notes / Fail
- Notes:
