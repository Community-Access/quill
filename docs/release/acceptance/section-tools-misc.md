# Section — Tools: compare, keymap, macros & utilities (`tools.*`, 73 commands)

The **catch-all** part of the Tools menu: everything under `tools.*` that is **not**
an AI writing tool (those live in `section-tools-ai.md`) and **not** a
dictation / OCR / read-aloud / speech / spell-check / dictionary tool (those live
in `section-tools-speech.md`). What is left is the workbench: **document compare**,
the **keymap / keyboard-pack** editor and import/export, **macros**, **CSV / Table
Studio**, the **Calculator**, **sticky notes**, **sound events**, **notifications**,
**updates**, **watch-folder**, **profiles & feature toggles**, **share / back-up**,
**shell integration**, the **developer consoles**, **Quillins**, **Mastodon**, the
**extraction-quality** reports, and the experimental **GLOW** accessibility engine.

Surface reference (label + shortcut) is
`../../planning/signoff/SIGNOFF-editor.md` → `tools.*`. Read §2–§3 of `README.md`
for the scenario layout and the Pass/Fail/Blocked/N-A + Works/Surface-exact/Accessible
boxes, and §5 for what **[GATED]** means.

**Reliable route to any command.** Every command below can be reached from the
**Command Palette** — press **Ctrl+Shift+P**, type the command name, press
**Enter**. Where a command also has a menu entry it is given as **Tools menu
(Alt, T) ▸ …**; where a command has a default keyboard shortcut it is printed in the
heading. If a menu path differs from what this book prints, that is a
**Surface-exact** failure — write down what the menu actually said.

Common inputs used below (copy the `../qa-samples/` folder onto the machine first):

- **`compare-original.txt`** and **`compare-revised.txt`** — a known before/after
  pair. There are **three content edits**: line 2 **March → April**; line 3 gains
  **“and performance”**; the revised file adds a fourth line **“A follow-up review
  is scheduled for February.”**
- **`data.csv`** — three columns **Region, Units, Revenue**, four data rows
  (North/South/East/West). Known totals: **Units = 465**, **Revenue = 9300**;
  4 rows, 3 columns.

> **Note on the compare engine (read before TMI-03…TMI-11).** QUILL’s
> difference navigator groups **contiguous** differing lines into one *line group*.
> In the sample pair the three edits sit on adjacent lines (2, 3, and the new 4),
> so the navigator reports them as **one differing line group spanning lines 2–4**,
> not as three separate stops. That is correct behaviour, not a miss — the three
> edits are all *inside* that one group, and the copied/summary text and the
> unified-diff preview spell out all three. Judge Compare on whether it finds the
> three edits and reports nothing spurious, **not** on a literal “3 differences”
> count.

---

## TMI-01 — Calculator (`tools.calculator`)

*What & why.* An accessible scientific calculator that also computes statistics
over selected numbers, a pasted column, a CSV, or a table — and can insert the
result at the cursor.

**Before you start**
- Open **`data.csv`**. Select the whole document (**Ctrl+A**) so the four rows of
  numbers are the input.

**Do this**
1. Open **Calculator…** (Command Palette → “Calculator”, or **Tools menu ▸
   Calculator…**). The current selection pre-fills the input box.
2. Tab to the **operation** control and choose **sum**; Tab to the **scope**
   control and choose **Down each column**; activate the data/compute button.
3. Read the result. Then change scope to **Full summary** and re-compute.
4. Optionally use **Insert** to drop the result into the document, then **Copy**.

**You should see and hear**
- The dialog is fully labelled and keyboard-complete; the input, operation, and
  scope controls all announce their names and values.
- Sum **down each column** announces **“Sum down each column. Column 2: 465;
  Column 3: 9300”** (Column 1 is the non-numeric Region column and is skipped).
- A plain calculation (type `2+2`, compute) returns **4**. **Full summary**
  announces a count/sum/average line over the numbers.
- **Insert** writes the last result at the cursor and says “Result inserted.”;
  **Copy** says “Result copied.” **Escape** / Close returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-02 — Word Count… (`tools.word_count`, Ctrl+Shift+W)

*What & why.* Report the document’s word, line, and character counts.

**Before you start**
- Open **`plain.txt`** (three plain paragraphs).

**Do this**
1. Press **Ctrl+Shift+W**, or Command Palette → “Word Count”.

**You should see and hear**
- A **Word Count** message box listing **Words**, **Lines**, and **Characters**;
  the status bar also announces “Word count: N words”. Dismissing the box (Enter /
  Escape) returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-03 — Compare with File… (`tools.compare_with_file`)

*What & why.* Compare the document you are editing against another file on disk and
start a keyboard-navigable difference session.

**Before you start**
- Open **`compare-original.txt`**. Have **`compare-revised.txt`** on disk.

**Do this**
1. Command Palette → “Compare with File”, or **Tools menu ▸ Compare with File…**.
2. In the file dialog pick **`compare-revised.txt`**; press **Enter**.
3. Read the unified-diff preview box, then dismiss it (Enter / Escape).

**You should see and hear**
- The file dialog is keyboard-navigable. A **Compare with File** preview box shows a
  unified diff that reflects all three edits in substance (**March → April**, the
  added **“and performance”**, and the added **“A follow-up review…”** line).
- On dismiss, a compare session starts: the status announces something like
  **“Compare session started. 2 documents. 1 differing line group found”** and the
  first difference is announced (see the engine Note above). Status ends “Compared
  with compare-revised.txt”.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-04 — Compare Open Documents… (`tools.compare_open_documents`)

*What & why.* Compare all currently open documents against each other (no file
picker) and start the same difference session.

**Before you start**
- Open **both** `compare-original.txt` and `compare-revised.txt` as two tabs.

**Do this**
1. Command Palette → “Compare Open Documents”, or **Tools menu ▸ Compare Open
   Documents…**.

**You should see and hear**
- With two open docs, a session starts and the status announces **“Compare session
  started. 2 documents. 1 differing line groups found”** and the first difference.
- With **only one** document open it says **“Open at least two documents to
  compare”** and does nothing destructive.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-05 — Compare Options… (`tools.compare_options`)

*What & why.* Choose whether trailing spaces and CRLF-vs-LF line-ending differences
are ignored when comparing.

**Before you start**
- A compare session active (from TMI-03 or TMI-04).

**Do this**
1. Command Palette → “Compare Options”, or **Tools menu ▸ Compare Options…**.
2. Answer the two Yes/No prompts: **Ignore trailing spaces?** then **Ignore
   line-ending differences (CRLF vs LF)?**

**You should see and hear**
- Two clearly spoken Yes/No questions, each cancellable. After answering, the active
  session is **re-compared** with the new options and the status says **“Updated
  compare options”**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-06 — Next / Previous Difference (`tools.compare_next_difference`, Ctrl+Alt+Shift+. — `tools.compare_previous_difference`, Ctrl+Alt+Shift+,)

*What & why.* Step forward and back through the differences in the active session.

**Before you start**
- A compare session active (TMI-03/04).

**Do this**
1. Press **Ctrl+Alt+Shift+.** (Next Difference) a few times; then **Ctrl+Alt+Shift+,**
   (Previous Difference).

**You should see and hear**
- Each press moves the current difference and **announces it** (“Difference 1 of
  1. changed. …lines 2–3 / lines 2–4 …”); navigation **wraps** at the ends. With
  only one group, a soft “no more differences” sound plays and the same difference
  is re-announced. With no active session, “No active compare session”.
- **Note:** the session’s own status line references **F8 / Shift+F8 / Ctrl+F8** for
  next/previous/current. Try both the printed `Ctrl+Alt+Shift` shortcuts and the
  F8 family; if the spoken hint and the working key disagree, flag **Surface-exact**.

**Sign off (Next Difference)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Previous Difference)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-07 — Announce Current Difference (`tools.compare_announce_difference`, Ctrl+Alt+Shift+D)

*What & why.* Re-speak the current difference without moving, and (when
synchronization is on) move the caret to that difference in the document.

**Before you start**
- A compare session active with a difference selected.

**Do this**
1. Press **Ctrl+Alt+Shift+D**, or Command Palette → “Announce Current Difference”.

**You should see and hear**
- The current difference is re-announced (index, kind, and the affected lines/text).
  With synchronization on (TMI-11), the caret in the active document jumps to that
  difference’s starting line. With no session, “No active compare session”.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-08 — Open Difference List… (`tools.compare_difference_list`)

*What & why.* Jump to any difference from a single keyboard list.

**Before you start**
- A compare session active.

**Do this**
1. Command Palette → “Open Difference List”, or **Tools menu ▸ Open Difference
   List…**.
2. Arrow through the list; select an entry; press **Enter**.

**You should see and hear**
- A **Difference List** single-choice dialog whose entries read like “Difference 1:
  changed at line 2. …”; the current one is pre-selected. Choosing one makes it
  current and announces it. Escape cancels with no change.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-09 — Copy Current / Copy All Differences (`tools.compare_copy_current_difference` — `tools.compare_copy_all_differences`)

*What & why.* Put the current difference, or the whole difference report, on the
clipboard.

**Before you start**
- A compare session active.

**Do this**
1. Command Palette → “Copy Current Difference”, then paste (**Ctrl+V**) into a scratch
   document to inspect.
2. Command Palette → “Copy All Differences”, then paste to inspect.

**You should see and hear**
- Copy Current says **“Copied current difference”**; the pasted text is that one
  difference (index, kind, per-document lines/text).
- Copy All says **“Copied all differences”**; the pasted text is the full **Compare
  Summary** (documents, options line, count, and every difference — spelling out the
  March→April, +“and performance”, and the added follow-up line). With no session:
  “No active compare session”.

**Sign off (Copy Current Difference)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Copy All Differences)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-10 — Create Difference Summary (`tools.compare_create_summary`)

*What & why.* Open the full compare report as a new document you can read, save, or
share.

**Before you start**
- A compare session active.

**Do this**
1. Command Palette → “Create Difference Summary”, or **Tools menu ▸ Create Difference
   Summary**.

**You should see and hear**
- A **new document tab** opens containing the Compare Summary (documents compared,
  the options line, the difference count, and each difference); status says
  **“Opened compare summary document”**. Focus lands in the new document.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-11 — Toggle Compare Synchronization (`tools.compare_toggle_sync`)

*What & why.* Turn on/off whether navigating differences also moves the caret in the
document.

**Before you start**
- A compare session active.

**Do this**
1. Command Palette → “Toggle Compare Synchronization”. Then navigate a difference and
   observe whether the caret follows. Toggle again.

**You should see and hear**
- The status announces **“Synchronized compare navigation on”** / **“…off”**. With
  it on, TMI-07/TMI-06 move the caret to the difference; with it off, they only
  speak. With no session: “No active compare session”.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-12 — Open CSV in Table Studio (`tools.csv_studio`) [experimental]

*What & why.* Load a CSV into QUILL’s accessible table grid to read, edit, and
re-insert it as Markdown/HTML.

**Before you start**
- **Precondition:** enable **Preferences ▸ Experimental ▸ Enable experimental
  features** and **Table Studio**. If off, the command says “Table Studio is an
  experimental feature; enable it in Preferences > Experimental” — mark **N/A** on a
  build where you cannot enable it.
- Have **`data.csv`** on disk.

**Do this**
1. Command Palette → “Open CSV in Table Studio”.
2. Pick **`data.csv`**; press **Enter**. Navigate the grid by keyboard.
3. Optionally choose **Insert as Markdown** (OK) or **Insert as HTML** (Apply).

**You should see and hear**
- The CSV opens in the accessible grid titled **“Table Studio — …”** with the
  header row **Region / Units / Revenue** and **4 body rows**; cells are announced
  with row/column context on arrow. Insert-as-Markdown says “Table inserted as
  Markdown” (Insert-as-HTML says “…as HTML”). A bad file reports an error, not a
  crash.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-13 — Table Studio (`tools.table_studio`) [experimental]

*What & why.* Build a new table from scratch in the same accessible grid, then
insert it.

**Before you start**
- Same experimental precondition as TMI-12.

**Do this**
1. Command Palette → “Table Studio”. A 3×3 grid titled **“Table Studio”** opens with
   a caption “New table”.
2. Type into cells by keyboard; add/remove rows/columns via the labelled controls;
   choose **Insert as Markdown** or **Insert as HTML**.

**You should see and hear**
- The grid and its row/column controls are labelled and keyboard-complete; edits are
  announced. Insert drops a valid Markdown/HTML table at the cursor and says which
  format. Escape leaves the document unchanged.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-14 — Regular Expression Helper… (`tools.regex_helper`)

*What & why.* Build and test a regular expression against sample text, with a recipe
library, before using it in Find/Replace.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Regular Expression Helper”, or **Tools menu ▸ Regular
   Expression Helper…**.
2. Browse the recipe categories; type a pattern and sample text; read the match
   results.

**You should see and hear**
- A **Regular Expression Helper** dialog with labelled pattern, test-text, and
  results controls, plus a categorized recipe list; matches are reported in a
  screen-reader-readable way. Escape/Close returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-15 — Search in Files… (`tools.search_in_files`, Ctrl+Shift+F)

*What & why.* Search a folder tree for text or a regex and open the results as a
report.

**Before you start**
- Point the search at the **`qa-samples`** folder. Search term: **`QUILL`**.

**Do this**
1. Press **Ctrl+Shift+F**, or Command Palette → “Search in Files”.
2. Fill in the search root (qa-samples), the query, and options; run it.

**You should see and hear**
- A labelled, keyboard-complete search prompt; progress is reported. A **new results
  tab** (“Search - QUILL”) opens and the status says **“Search complete: N match(es)
  in M file(s)”**. Cancelling before running says “Search in files cancelled”.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-16 — Replace Across Files… (`tools.replace_in_files`, Ctrl+Shift+R)

*What & why.* Find-and-replace text across a folder tree — with a **preview** before
anything is written.

**Before you start**
- Work on a **disposable copy** of a folder (replacement edits files on disk). Do not
  run this against `qa-samples` you want to keep byte-stable.

**Do this**
1. Press **Ctrl+Shift+R**, or Command Palette → “Replace Across Files”.
2. Enter the search root, the pattern, and the replacement; keep **preview** on; run.
3. Read the **Replace Preview** tab, then confirm to apply (or cancel).

**You should see and hear**
- With preview on, a **Replace Preview** tab lists every prospective change before
  any file is touched; “No matches found” when there are none. Applying reports how
  many files/occurrences changed. Nothing is written without your confirmation.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-17 — Macros: Start / Stop Recording, Play Last (`tools.start_macro_recording` — `tools.stop_macro_recording` — `tools.play_last_macro`)

*What & why.* Record a sequence of commands and replay it — automation without code.

**Before you start**
- Open `plain.txt`.

**Do this**
1. Command Palette → “Start Macro Recording”. Name it **`My Macro`**; confirm.
2. Perform two or three commands (e.g. select a line, upper-case it).
3. Command Palette → “Stop Macro Recording”.
4. Move the caret elsewhere, then Command Palette → “Play Last Macro”.

**You should see and hear**
- Start prompts for a **name** and then says **“Recording macro My Macro”**; an empty
  name is refused; starting twice says “Already recording …”.
- Stop says **“Saved macro My Macro with N step(s)”**; stopping when not recording
  says “No macro is being recorded”.
- Play Last replays the steps and says **“Played macro My Macro”**; with nothing
  recorded it says “No recorded macro to play”.

**Sign off (Start Macro Recording)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Stop Macro Recording)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Play Last Macro)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-18 — Manage Macros… (`tools.manage_macros`)

*What & why.* View, play, and delete your recorded macros.

**Before you start**
- At least one macro recorded (TMI-17).

**Do this**
1. Command Palette → “Manage Macros”, or **Tools menu ▸ Manage Macros…**.
2. Select a macro in the list; play it; delete another; close.

**You should see and hear**
- A **Manage Macros** dialog with a labelled macro list and Play/Delete controls, all
  keyboard-operable; actions are announced. Deleting is confirmed before it happens.
  Escape/Close returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-19 — Keymap Editor… (`tools.keymap_editor`)

*What & why.* Search commands by name, or by typing/recording a shortcut, and rebind
any command’s key.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Keymap Editor”, or **Tools menu ▸ Keymap Editor…**.
2. In **Search**, type a command name (e.g. “word count”); select it in the list.
3. Choose **Edit** / **Record Keys…** to assign a shortcut; confirm; then close.

**You should see and hear**
- A **Keymap Editor** dialog with a labelled **Search** field, a **Record Keys…**
  button, a shortcut-status line, and a **Keyboard shortcuts** list. Typing a chord
  (e.g. Ctrl+M) reveals what it is bound to; recording/assigning a key is announced;
  conflicts are reported. Changes persist after Close.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-20 — Export / Import Keymap… (`tools.export_keymap` — `tools.import_keymap`)

*What & why.* Save your keybindings to a `.json` file and load them back (e.g. onto
another machine).

**Before you start**
- Any document open. Pick a scratch folder for the export.

**Do this**
1. Command Palette → “Export Keymap”. Save as **`my-keymap.json`**.
2. Change a binding in the Keymap Editor (TMI-19).
3. Command Palette → “Import Keymap”. Choose **`my-keymap.json`**.

**You should see and hear**
- Export writes the JSON and says **“Exported keymap to my-keymap.json”**.
- Import re-reads it, re-applies shortcuts live, and says **“Imported keymap from
  my-keymap.json”** — your changed binding reverts to the exported one.

**Sign off (Export Keymap)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Import Keymap)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-21 — Export / Import Keyboard Pack (.kqp)… (`tools.export_keyboard_pack` — `tools.import_keyboard_pack`)

*What & why.* Package your whole keyboard layout as a named, describable **`.kqp`**
pack to share, and import someone else’s.

**Before you start**
- Any document open; a scratch folder.

**Do this**
1. Command Palette → “Export Keyboard Pack (.kqp)”. Give it a **name** and optional
   **description**; save the `.kqp`.
2. Command Palette → “Import Keyboard Pack (.kqp)”. Choose the file you just saved.

**You should see and hear**
- Export first asks for **Pack name** and **Description** (both labelled), then a file
  picker that defaults the `.kqp` extension; status says **“Exported keyboard pack to
  …”**.
- Import merges and re-applies the pack live and says **“Imported keyboard pack:
  <name>. <description>”**; an invalid pack reports “Import Failed” rather than
  corrupting your keymap.

**Sign off (Export Keyboard Pack)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (Import Keyboard Pack)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-22 — Reset Keymap (`tools.reset_keymap`)

*What & why.* Restore every keybinding to the shipped defaults.

**Before you start**
- Have at least one custom binding (from TMI-19).

**Do this**
1. Command Palette → “Reset Keymap”. Read the warning; choose **Yes** (try **No**
   first to confirm it cancels).

**You should see and hear**
- A spoken **“Reset all keybindings to defaults?”** confirmation you can cancel. On
  Yes, bindings return to defaults, the keyboard pack resets to the default pack, and
  status says **“Reset keymap to defaults”**. On No: “Reset keymap cancelled”.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-23 — Reset Everything to Factory Defaults… (`tools.reset_all_defaults`)

*What & why.* One command to reset settings, shortcuts, menu customizations, and the
feature profile — documents are never touched.

**Before you start**
- Any state. Understand this is broad; run it near the end of a test pass.

**Do this**
1. Command Palette → “Reset Everything to Factory Defaults”. Read the warning; choose
   **No** to confirm it cancels, then repeat and choose **Yes** if you intend to reset.

**You should see and hear**
- A single **“Reset EVERYTHING to factory defaults?”** warning that spells out what
  resets and states documents are **not** affected and that it **cannot be undone**;
  it is cancellable. On Yes, settings/shortcuts/menus/profile return to factory state
  and persist; your open documents, autosaves, and backups are untouched.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-24 — Undo Recent Shortcut Change (`tools.undo_recommended_updates`)

*What & why.* If a QUILL upgrade re-mapped a shortcut (a “recommended update”, e.g.
Find → Ctrl+F), restore your previous binding.

**Before you start**
- Any document open. This has something to undo only right after an upgrade that
  applied a recommended shortcut change; otherwise expect the “nothing to undo” path.

**Do this**
1. Command Palette → “Undo Recent Shortcut Change”.

**You should see and hear**
- If a change was applied this launch, it is reverted and QUILL says **“Restored your
  previous keyboard shortcuts.”** (and won’t re-apply it next launch). If there is
  nothing to undo, it says **“Nothing to undo”** — not an error.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-25 — Open Keyboard Reference (`tools.open_keyboard_reference`)

*What & why.* Open an HTML table of every current shortcut in your browser (QUILL is
highly configurable, so this reflects your live keymap).

**Before you start**
- A default browser available.

**Do this**
1. Command Palette → “Open Keyboard Reference”, or **Tools menu ▸ Open Keyboard
   Reference**.

**You should see and hear**
- A self-contained, screen-reader-friendly HTML shortcut table opens in the browser;
  status says **“Opened keyboard reference in browser”**. A write/open failure is
  reported in the status, not silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-26 — Global Hotkeys… (`tools.global_hotkeys`)

*What & why.* Assign **system-wide** hotkeys that trigger safe QUILL commands even
when QUILL is in the background (Windows).

**Before you start**
- Any document open. (Global hotkeys are a Windows feature.)

**Do this**
1. Command Palette → “Global Hotkeys”, or **Tools menu ▸ Global Hotkeys…**.
2. Assign a hotkey to a listed command; save; test it from another app; then clear it.

**You should see and hear**
- A **Global Hotkeys** dialog listing the commands that may be bound globally, with
  labelled, keyboard-operable assign/clear controls. A saved hotkey fires its command
  system-wide; conflicts are reported. Escape cancels cleanly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-27 — Sticky Notes… (`tools.sticky_notes`)

*What & why.* Browse and open your saved sticky notes.

**Before you start**
- Any document open (create a note first via TMI-28 if you have none).

**Do this**
1. Command Palette → “Sticky Notes”, or **Tools menu ▸ Sticky Notes…**.
2. Read the list; open a note; close.

**You should see and hear**
- A keyboard-navigable list of notes (announced with their text/titles); opening one
  shows its content; the dialog is fully labelled. Escape returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-28 — New Sticky Note… (`tools.sticky_note_capture`, Ctrl+Shift+Grave then Shift+N)

*What & why.* Capture a quick note without leaving your document.

**Before you start**
- Any document open. Chord: **Ctrl+Shift+Grave**, release, then **Shift+N** (Grave is
  the backtick key).

**Do this**
1. Open the command via the chord, or Command Palette → “New Sticky Note”.
2. Type a short note; confirm.

**You should see and hear**
- A labelled note editor opens; on confirm QUILL saves it and says **“Note saved”**.
  The note then appears in Sticky Notes (TMI-27). Escape discards with no note saved.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-29 — Toggle Sound Notifications (`tools.sound_toggle`)

*What & why.* Turn QUILL’s earcons (sound cues) on or off.

**Before you start**
- Speakers/headphones on.

**Do this**
1. Command Palette → “Toggle Sound Notifications”. Toggle it twice.

**You should see and hear**
- Turning **on** plays the “sound on” cue; turning **off** plays the “sound off” cue
  first; either way it announces **“Sound notifications on”** / **“…off”** and the
  setting persists.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-30 — Manage Sound Events (`tools.sound_events`)

*What & why.* Choose which individual events play a sound.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Manage Sound Events”, or **Tools menu ▸ Manage Sound Events**.
2. Disable one event; **OK**. Reopen to confirm it stuck; re-enable it.

**You should see and hear**
- A **Sound Events** dialog listing events with a per-event enable/disable control,
  all labelled and keyboard-operable. OK saves your choices (the disabled set
  persists); Cancel/Escape discards.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-31 — Open Notifications… (`tools.notifications`)

*What & why.* Read QUILL’s stored notifications (e.g. update or GLOW messages) and
clear them.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Open Notifications”, or **Tools menu ▸ Open Notifications…**.
2. Read the list; use **Clear** if offered; close.

**You should see and hear**
- A **Notifications** dialog listing stored notifications (keyboard-navigable). Clear
  empties them and says **“Cleared notifications”**; with none, status says **“No
  notifications”**. Escape/Close returns focus to the editor.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-32 — Check for Updates… (`tools.check_updates`)

*What & why.* Ask whether a newer QUILL is available. Invoking it is your consent for
this one network check; nothing installs without a further confirmation.

**Before you start**
- Network available. Note whether this is a **portable** or **installer** build.

**Do this**
1. Command Palette → “Check for Updates”, or **Tools menu ▸ Check for Updates…**.

**You should see and hear**
- QUILL announces **“Checking for updates”**, then reports either **up to date** or a
  **newer version** with a download/apply prompt (portable offers the `.zip`,
  installer offers the setup). Nothing downloads or installs without your explicit
  confirmation; a network failure is reported clearly, not silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-33 — Watch Folder Monitoring (`tools.watch_folder_toggle`)

*What & why.* Reach the setting that turns automatic watch-folder monitoring on/off.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Watch Folder Monitoring”.

**You should see and hear**
- Settings opens at (or points you to) the **Watch Folders** area; status says
  **“Watch folder monitoring setting is in Settings > Watch Folders”**. The toggle
  there is labelled and keyboard-operable.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-34 — Watch Folder Settings… (`tools.watch_folder_settings`)

*What & why.* Manage watch-folder **profiles** (which folders are watched and how).

**Before you start**
- Watch folder available in this feature profile (else it says “Watch folder is
  unavailable in this profile” — mark **N/A**).

**Do this**
1. Command Palette → “Watch Folder Settings”, or **Tools menu ▸ Watch Folder
   Settings…**.
2. Add/edit a profile; save; close.

**You should see and hear**
- A **Watch Folder Profiles** dialog with labelled, keyboard-operable add/edit/remove
  controls; changes save and persist. Escape cancels cleanly.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-35 — Watch Folder Status… (`tools.watch_folder_status`)

*What & why.* Open the accessible Watch Queue Monitor to see what has been picked up.

**Before you start**
- Watch folder available in this profile (else it announces “Watch folder is
  unavailable in this profile” — mark **N/A**).

**Do this**
1. Command Palette → “Watch Folder Status”, or **Tools menu ▸ Watch Folder Status…**.

**You should see and hear**
- The **Watch Queue Monitor** opens (re-raised if already open) and is keyboard- and
  screen-reader-navigable. When the feature is off, the unavailability is **spoken**,
  not silent.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-36 — Cycle Autosave Interval (`tools.cycle_autosave_interval`)

*What & why.* Step the autosave interval through its choices with one command.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Cycle Autosave Interval”. Invoke it several times to cycle
   through 15 s → 30 s → 60 s → 5 min → off → 15 s…

**You should see and hear**
- Each press announces the new interval — **“Autosave every 15 s”**, **“…every 30
  s”**, **“…every 1 min”**, **“…every 5 min”**, **“Autosave off”** — and updates the
  status bar.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-37 — Status Bar Layout… (`tools.status_bar_settings`)

*What & why.* Reorder and show/hide the status-bar cells.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Status Bar Layout”, or **Tools menu ▸ Status Bar Layout…**.
2. Hide one cell and reorder another; **OK**; confirm the status bar changed.

**You should see and hear**
- A **Status Bar Layout** dialog with labelled order/visibility controls (and working
  OK/Cancel + Escape). OK applies and persists the layout; Escape discards.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-38 — Profiles and Features… (`tools.profiles_and_features_settings`)

*What & why.* The overview surface for feature **profiles** (Essential, etc.) and how
they shape which features are available.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Profiles and Features”, or **Tools menu ▸ Profiles and
   Features…**.
2. Read the profile choices and their descriptions; close without changing (or switch
   and confirm the announcement).

**You should see and hear**
- A **Profiles and Features** dialog explaining and letting you pick a profile, fully
  labelled and keyboard-operable; a profile change is announced and persists.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-39 — Manage Individual Features… (`tools.individual_feature_toggles`)

*What & why.* Turn individual features on/off on top of the active profile.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Manage Individual Features”, or **Tools menu ▸ Manage
   Individual Features…**.
2. Toggle one feature off; **OK**; reopen to confirm the state stuck; re-enable it.

**You should see and hear**
- A dialog listing user-toggleable features, each as a **checkbox** whose checked
  state your screen reader announces on arrow (locked-on/off features are omitted). A
  filter (e.g. “disabled only”) is offered. OK persists; Escape discards.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-40 — Work Personas… (`tools.work_personas`)

*What & why.* Save and apply named “personas” — bundles of settings/feature choices
you switch between for different kinds of work.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Work Personas”, or **Tools menu ▸ Work Personas…**.
2. Create a persona; apply it; confirm the announced change; then delete it.

**You should see and hear**
- A **Work Persona** manager with labelled create/apply/remove controls, all
  keyboard-operable; applying a persona is announced (and reconfigures the app); a
  missing persona is reported (“Work Persona ‘…’ was not found.”). Escape/Close
  returns focus.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-41 — External Tools and Format Support… (`tools.external_tools`)

*What & why.* See which optional external tools (e.g. converters) are installed and
what each one unlocks — with safe install guidance.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “External Tools and Format Support”, or **Tools menu ▸ External
   Tools and Format Support…**.

**You should see and hear**
- An **External Tools and Format Support** dialog listing each tool with its status
  (installed / not), what it unlocks, and how to install it; fully labelled and
  keyboard-navigable. Escape/Close returns focus to the editor. Nothing is installed
  without your action.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-42 — Export and Back Up… (`tools.share_export`)

*What & why.* Package your settings, feature profile, and customizations — either a
privacy-clean **profile** to share, or a full **backup** for yourself.

**Before you start**
- A scratch folder for the output.

**Do this**
1. Command Palette → “Export and Back Up”, or **Tools menu ▸ Export and Back Up…**.
2. Choose **Profile** vs **Backup**; review what is included; write the package.

**You should see and hear**
- A dialog that lets you pick the package **kind** and shows what each includes;
  labelled and keyboard-complete. **Profile** mode omits machine-specific paths and
  **secrets**; **Backup** keeps everything for personal restore. The package is
  written to the chosen path with a spoken confirmation.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-43 — Import or Restore… (`tools.share_import`)

*What & why.* Load a package made by TMI-42 back into QUILL.

**Before you start**
- A package file created in TMI-42.

**Do this**
1. Command Palette → “Import or Restore”, or **Tools menu ▸ Import or Restore…**.
2. Choose the package; review what will be applied; confirm.

**You should see and hear**
- A dialog that names what the package contains and lets you confirm before applying;
  keyboard-complete. On confirm the settings/customizations are applied and the result
  is announced; a bad/incompatible package is reported, not silently ignored.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-44 — Install Shell Integration… (`tools.shell_install`)

*What & why.* Add per-user “Open with Quill” associations and Explorer verbs
(Windows).

**Before you start**
- Windows. Any document open.

**Do this**
1. Command Palette → “Install Shell Integration”, or **Tools menu ▸ Install Shell
   Integration…**.
2. Read the confirmation (which lists the paths/verbs); choose **No** to confirm it
   cancels, then repeat and choose **Yes**.

**You should see and hear**
- A **Shell Integration** confirmation you can cancel (“…install cancelled”). On Yes,
  associations install and a box lists what was installed with **“Installed shell
  integration”**; a partial/no-op install reports **why** rather than a false success.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-45 — Remove Shell Integration (`tools.shell_remove`)

*What & why.* Undo TMI-44 for this user account.

**Before you start**
- Shell integration installed (TMI-44).

**Do this**
1. Command Palette → “Remove Shell Integration”, or **Tools menu ▸ Remove Shell
   Integration**.
2. Confirm the removal (try **No** first).

**You should see and hear**
- A **Shell Integration** removal confirmation you can cancel (“…removal cancelled”).
  On Yes, the associations and context-menu entries are removed and status says
  **“Removed shell integration”**.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-46 — Open Welcome Guide (`tools.open_welcome_guide`)

*What & why.* Open the built-in welcome/orientation document.

**Before you start**
- Any state.

**Do this**
1. Command Palette → “Open Welcome Guide”, or **Tools menu ▸ Open Welcome Guide**.

**You should see and hear**
- A new document tab with the welcome guide opens, focus lands in it, and status says
  **“Opened welcome guide”**. Its content reflects your current feature set.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-47 — Document Intake Report… (`tools.document_intake_report`, Ctrl+Shift+I)

*What & why.* Show what QUILL learned when it opened/converted the current document —
the “how did this come in?” report.

**Before you start**
- Open **`formatting.md`** (rich content) so there is something to report.

**Do this**
1. Press **Ctrl+Shift+I**, or Command Palette → “Document Intake Report”.

**You should see and hear**
- A **Document Intake Report** message box describing the document’s source/format and
  intake details; keyboard-dismissable. It is content-about-the-document, not a change
  to it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-48 — Review Extraction Quality… (`tools.review_extraction_quality`)

*What & why.* Report how confident QUILL is that a converted/OCR’d document extracted
cleanly.

**Before you start**
- A document that was imported/converted (e.g. open `formatting.html` or an OCR
  result). Any open document works to see the report shape.

**Do this**
1. Command Palette → “Review Extraction Quality”, or **Tools menu ▸ Review Extraction
   Quality…**.

**You should see and hear**
- An **Extraction Quality Review** message box summarizing extraction quality for the
  current document; keyboard-dismissable; read-only.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-49 — Report Bad Extraction… (`tools.report_bad_extraction`)

*What & why.* Save a diagnostic report (JSON) when a document imported badly, to help
fix the converter.

**Before you start**
- Any document open; a scratch folder.

**Do this**
1. Command Palette → “Report Bad Extraction”, or **Tools menu ▸ Report Bad
   Extraction…**.
2. In the save dialog, name the `.json`; confirm (try **Cancel** first).

**You should see and hear**
- A save dialog (JSON default). Cancel says **“Bad extraction report cancelled”**. On
  save it writes the report and says **“Saved extraction report to <name>”**. The
  report is a local file — nothing is sent anywhere automatically.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-50 — Copy Diagnostic Summary (`tools.copy_diagnostic_summary`)

*What & why.* Put a scrubbed environment/diagnostic summary on the clipboard for a bug
report — no document content included.

**Before you start**
- Any document open.

**Do this**
1. Command Palette → “Copy Diagnostic Summary”. Paste (**Ctrl+V**) into a scratch
   document to inspect.

**You should see and hear**
- QUILL says **“Diagnostic summary copied to clipboard.”** The pasted text describes
  the build/environment and editor surface **without** your document’s text. If the
  clipboard cannot open it says so (“Could not open clipboard.”).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-51 — Open Python Console… (`tools.open_python_console`)

*What & why.* A scripting console over QUILL’s API (`q.help()` for the reference).

**Before you start**
- **Preconditions:** not in **Safe Mode** (`QUILL_SAFE_MODE=1` disables it) and the
  Developer Console enabled in settings. A first-run **consent** prompt may appear —
  approve it. If gated off, mark **Blocked/N-A** per the spoken reason.

**Do this**
1. Command Palette → “Open Python Console”, accept any consent prompt.
2. Type `q.help()` and run it; read the output.

**You should see and hear**
- Safe Mode / disabled states are **spoken** (“Developer Console is disabled in Safe
  Mode.” / “…in settings.”). Otherwise the console window opens; on first open it
  announces **“Python console ready. Type q.help() for the scripting API
  reference.”**; history and a document-name status line are present.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-52 — Open TypeScript Console… (`tools.open_typescript_console`)

*What & why.* The TypeScript-flavoured developer console (a background worker runs the
code).

**Before you start**
- Same Safe-Mode / enabled / consent preconditions as TMI-51.

**Do this**
1. Command Palette → “Open TypeScript Console”, accept any consent prompt.
2. Wait for the worker to start; run a simple expression.

**You should see and hear**
- Safe Mode / disabled states are spoken. Otherwise the console opens with a
  **“Ready - TypeScript | <document>”** status; the background worker starts and
  announces when ready before you can rely on it.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-53 — Restart TypeScript Worker (`tools.restart_typescript_worker`)

*What & why.* Restart the TypeScript console’s background worker if it wedges.

**Before you start**
- Open the TypeScript console first (TMI-52).

**Do this**
1. Command Palette → “Restart TypeScript Worker”.

**You should see and hear**
- If the console was never opened, status says **“Open the TypeScript console first,
  then restart the worker.”** Otherwise the worker restarts (and re-announces ready).

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-54 — Manage Quillins (`tools.quillins_manager`)

*What & why.* Manage installed Quillins (QUILL’s sandboxed extensions): enable,
disable, reload, remove, install.

**Before you start**
- Any document open. Note Quillin contributions are disabled in **Safe Mode**.

**Do this**
1. Command Palette → “Manage Quillins”, or **Tools menu ▸ Manage Quillins**.
2. Read the installed list and each Quillin’s detail (including its signature status);
   try enable/disable/reload on one; close.

**You should see and hear**
- A hardened **Manage Quillins** dialog with a keyboard-navigable list; the detail
  pane names each Quillin and shows a **Signature** line (verified / invalid /
  unsigned). Enable/disable/reload/remove/install are labelled and confirmed;
  permission requests are spoken. In Safe Mode, contributions stay disabled.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-55 — New Quillin (`tools.quillin_wizard`)

*What & why.* Scaffold a new Quillin manifest in-app.

**Before you start**
- A scratch folder for the new Quillin.

**Do this**
1. Command Palette → “New Quillin”, or **Tools menu ▸ New Quillin**.
2. Walk the wizard fields (name, description, license, etc.) by keyboard; finish.

**You should see and hear**
- A wizard with labelled, keyboard-complete fields that produces a valid Quillin
  scaffold/manifest; the outcome is announced. Escape cancels with nothing written.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-56 — Submit to Quillin Hub (`tools.quillin_hub_submit`)

*What & why.* Validate a shareable Quillin/artifact and guide you through submitting
it to the Quillin Hub.

**Before you start**
- A Quillin to submit (e.g. from TMI-55).

**Do this**
1. Command Palette → “Submit to Quillin Hub”, or **Tools menu ▸ Submit to Quillin
   Hub**.
2. Follow the validation and submission guidance.

**You should see and hear**
- The artifact is validated and any problems are reported clearly; the submission
  steps are labelled and keyboard-navigable. Nothing is published without your
  action.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-57 — Mastodon Accounts… (`tools.manage_mastodon_accounts`)

*What & why.* Connect, view, set default, and remove the Mastodon accounts the social
commands use. Do this **before** TMI-58…TMI-60. Disabled in Safe Mode.

**Before you start**
- A Mastodon account (instance + sign-in) you can use. If none, mark **Blocked**.

**Do this**
1. Command Palette → “Mastodon Accounts”, or **Tools menu ▸ Mastodon Accounts…**.
2. Add an account by keyboard; set it default; then remove it to confirm removal.

**You should see and hear**
- A **Mastodon Accounts** dialog with labelled add/remove/set-default controls, all
  keyboard-operable; actions are announced. **Tokens are stored in the platform secret
  store**, never in plain text. In Safe Mode the feature is refused with a spoken
  reason.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-58 — Post to Mastodon… (`tools.post_to_mastodon`, Ctrl+Shift+Grave then Shift+P)

*What & why.* Publish the selection (or the whole document) to Mastodon. Disabled in
Safe Mode.

**Before you start**
- A connected Mastodon account (TMI-57). Chord: **Ctrl+Shift+Grave** then **Shift+P**.
- Select a short line of text to post.

**Do this**
1. Open the command via the chord, or Command Palette → “Post to Mastodon”.
2. Review/edit the compose text; choose the account; post.

**You should see and hear**
- If no account is set up, QUILL says **“Add a Mastodon account to post.”** and opens
  the accounts manager first. Otherwise a labelled compose dialog opens pre-filled
  with your selection (or the whole document); on post it says **“Posted to
  Mastodon.”** (with the URL when available). Safe Mode refuses with a spoken message.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-59 — Add a User to a Mastodon List… (`tools.mastodon_add_user_to_list`)

*What & why.* Look up an account and add it to one of your Mastodon lists.

**Before you start**
- A connected Mastodon account (TMI-57).

**Do this**
1. Command Palette → “Add a User to a Mastodon List”, or **Tools menu ▸ Add a User to
   a Mastodon List…**.
2. Enter the handle; pick a list; confirm.

**You should see and hear**
- A labelled handle prompt (“Looking up <handle> and your lists…” is spoken), then a
  list picker; the add is confirmed by voice. Mastodon requires you to **follow** the
  account first — if you don’t, QUILL reports that clearly rather than failing
  silently.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-60 — View Mastodon Profile… (`tools.view_mastodon_profile`)

*What & why.* Look up an account, see your relationship both ways, and Follow/Unfollow.

**Before you start**
- A connected Mastodon account (TMI-57).

**Do this**
1. Command Palette → “View Mastodon Profile”, or **Tools menu ▸ View Mastodon
   Profile…**.
2. Enter a handle; read the profile; use Follow/Unfollow.

**You should see and hear**
- A labelled handle prompt (“Looking up <handle>…” spoken), then a profile view that
  states the relationship (following / follows you) with a keyboard-operable
  **Follow/Unfollow** button whose action is announced.

**Sign off** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-61 — GLOW Audit: Current Document / Selection / File (`tools.glow_audit_document` — `tools.glow_audit_selection` — `tools.glow_audit_file`) [GATED core.glow]

*What & why.* Run QUILL’s experimental **GLOW** accessibility auditor and open a
scored report.

**[GATED] precondition.** GLOW is experimental. Enable **Preferences ▸ Experimental ▸
Enable experimental features**, then **GLOW accessibility review and repair**. If it
is **off**, invoking any GLOW command shows an info box titled **“GLOW
(Experimental)”** explaining how to turn it on — on a public build where you do not
enable it, mark these **N/A** (do not fail for being gated).

**Before you start**
- GLOW enabled. Open **`formatting.md`**. For the *selection* variant, select a
  heading/paragraph. For the *file* variant, have a structured file on disk.

**Do this**
1. **Audit Current Document:** Command Palette → “GLOW Audit Current Document”.
2. **Audit Selection:** select text, then “GLOW Audit Selection”.
3. **Audit File:** “GLOW Audit File”, pick a file.

**You should see and hear**
- Each opens a **GLOW Audit** report in a new scratch tab; document/selection variants
  say **“Opened GLOW audit for …”**. The **file** variant runs in the background and
  then announces **“GLOW audit for <file>: score N, grade X, K findings.”** A gated
  invocation shows the enable-instructions box instead.

**Sign off (GLOW Audit Current Document)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (GLOW Audit Selection)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (GLOW Audit File)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-62 — GLOW Fix: Current Document / Selection / File (`tools.glow_fix_document` — `tools.glow_fix_selection` — `tools.glow_fix_file`) [GATED core.glow]

*What & why.* Apply GLOW’s deterministic accessibility fixes — safely, with preview
for the whole document and a non-destructive copy for files.

**[GATED] precondition.** Same as TMI-61 (enable Experimental ▸ GLOW; else the enable
box appears and you mark **N/A** on a public build).

**Before you start**
- GLOW enabled. Open a document with fixable issues (e.g. `formatting.md`); for
  *selection*, select part of it; for *file*, have a structured file on disk.

**Do this**
1. **Fix Current Document:** Command Palette → “GLOW Fix Current Document”.
2. **Fix Selection:** select text, then “GLOW Fix Selection”.
3. **Fix File:** “GLOW Fix File”, pick a file, read/confirm the copy path.

**You should see and hear**
- **Document:** opens a **GLOW Fix Preview** tab and **starts a compare session**
  between the original and the fixed text; status names how many changes. If nothing
  is fixable it opens a report and says **“No deterministic GLOW fixes were
  available”** (the original is untouched).
- **Selection:** applies the fixes in place, re-selects the result, and says
  **“Applied N GLOW fixes to <scope>”** (or the no-fixes message).
- **File:** first shows a box stating it will write a **new** `-accessible` copy and
  that the **original is never modified**, and is cancellable; on success it opens a
  report and announces **“GLOW applied N fixes. The repaired copy is <name>.”**

**Sign off (GLOW Fix Current Document)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (GLOW Fix Selection)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

**Sign off (GLOW Fix File)** — `[ ] Pass  [ ] Fail  [ ] Blocked  [ ] N/A`
`[ ] Works` `[ ] Surface-exact` `[ ] Accessible`  · Notes: ____________________

---

## TMI-63 — Check for GLOW Updates… (`tools.check_glow_updates`) [GATED core.glow]

*What & why.* Check for, and optionally install, a newer GLOW accessibility engine.

**[GATED] precondition.** Same as TMI-61 (enable Experimental ▸ GLOW). If off, the
enable box appears — mark **N/A** on a public build. Network required.

**Before you start**
- GLOW enabled; network available. Invoking is your consent for the network check.

**Do this**
1. Command Palette → “Check for GLOW Updates”.

**You should see and hear**
- Status says **“Checking for GLOW engine updates…”**, then reports up-to-date or an
  available engine. A **second confirmation** is required before anything downloads;
  the engine is verified (signed manifest + per-wheel SHA-256) and installed offline,
  a failed install rolls back to the vendored wheels, and the new engine loads on
  restart. Network failures are reported, not silent.

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
