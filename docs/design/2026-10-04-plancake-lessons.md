# What PlanCake teaches us about reviewing a document by ear

Date: 2026-10-04. An internal design note: what QUILL and QUILL Lite can learn
from PlanCake, and what we should build because of it.

## Where the ideas come from

PlanCake is a small Windows app by Andre of Oire Software (Menelion on GitHub),
announced by its author on a blind-tech mailing list; website
plan-cake.oire.dev, source github.com/Oire/plan-cake, Apache License 2.0.
It opens a Markdown file, shows it as a rendered page, and lets you leave a
note after any block by pressing Enter on it. It was built for one job:
reviewing the long implementation plans that AI coding assistants write. Every
idea in this note that is not already in QUILL is PlanCake's, and the credit is
Andre's.

How this was researched: PlanCake's README, its 1.0.0 release notes, its
English user manual (`src/PlanCake/help/en/manual.html`) and a design note in
its repository about JAWS behaviour inside WebView2 (`docs/jaws-spike.md`). We
looked at the repository's layout to understand how notes are stored, and read
no further into the code. Nothing of theirs is copied here, and nothing in this
note proposes reading or importing PlanCake's files. That is the standing
family rule for competitors: learn from the idea, never from the data.

On the QUILL side, every menu path and key below was checked against the code
on 2026-10-04 (`quill/core/keymap.py`, `quill/core/lite/commands.py`,
`quill/ui/main_frame_menu.py` and the modules named in each section), and
every key proposed was checked free in both `DEFAULT_KEYMAP` (with
`DEFAULT_ALIASES`) and QUILL Lite's command table, and against the dynamic
rows those tables do not show (Recent Documents on Alt+Shift+1 to 9, the
QuillVille launchers on Ctrl+Alt+Shift+F7 to F12).

## What PlanCake does well for a screen-reader user

Each of these is one sentence on purpose; the sections after this one take
them in turn.

1. **Enter is the note key.** You read the plan in your screen reader's own
   browse mode, and pressing Enter on whatever block you are on opens a tiny
   note dialog, already focused, that shows the start of the block so you can
   check you picked the right one.
2. **The note lives in the file, right after the block it is about.** Nothing
   to save, no side file; whoever opens the file next, a colleague or an AI
   assistant, finds each note exactly where it belongs.
3. **One place lists every note.** A notes list beside the document gives each
   note's first sentence, its lines, and the first sentence of the block it
   follows, and F9 and Shift+F9 walk the notes from anywhere.
4. **Notes are a review loop, not just text.** Delete one, delete all (with a
   count, always asked), undo any of it, and a command line (`list`, `check`,
   `clear`, `export`) lets an AI assistant read your notes, work through them
   and prove none are left, with exit code 3 meaning "notes still open".
5. **Task lists you can tick.** A `- [ ]` item is a real checkbox; Space or
   Enter asks, writes `[x]` on that one line, says "Task checked", and undo
   reverses it.
6. **Plans arrive however they arrive.** Ctrl+V with a file copied in File
   Explorer, a path copied as text (quotes and all), or a web link; Ctrl+L for
   a link, which understands an ordinary GitHub page link and fetches the raw
   Markdown behind it; the command line; drag and drop.
7. **It refuses to destroy what it cannot read.** A file in a legacy encoding
   opens read-only and says which encoding it is; conversion to UTF-8 is an
   opt-in setting; a file whose encoding is uncertain is never written.
8. **It never overwrites a change it has not seen.** When an AI assistant
   rewrites the plan while you read, PlanCake reloads in place and keeps your
   reading position; if the file changed while you typed a note, the write is
   refused and nothing is lost on either side.
9. **Every outcome is spoken, and only the outcome.** "Note added", "No more
   notes", "File reloaded", "Undone: note added" -- through the status bar and
   a UI Automation notification, so they are heard wherever focus is.
10. **A shareable page.** Export to a single self-contained HTML file with the
    notes marked and no scripts, and notes to JSON for other tools.
11. **Privacy stated plainly.** Two network uses, named: downloading a file you
    asked for, and the update check. No usage data.

Two smaller touches are worth remembering even though they are not proposals:
each note in the rendered page is a region named "User note", so a screen
reader can tell your words from the plan's; and PlanCake's JAWS notes record
that giving every block a permanent `tabindex` threw JAWS into forms mode on
Enter, so blocks only become focusable for the moment the app moves the
virtual cursor. That is a hard-won lesson for anyone who ever builds a web
view with per-block actions.

## Idea by idea: what we have, the gap, and what to build

A note on keys before the detail. The family keyspace is close to full, so
every key below was chosen from the short list of chords that are free in
*both* `DEFAULT_KEYMAP` and QUILL Lite's command table. PlanCake's own keys
mostly cannot come across: Ctrl+L and Ctrl+E are Word's Align Left and Centre
in both editors (rule 1), F9 is Repeat Last Result and Shift+F9 is Activity in
both, Alt+Shift+Up and Down are Move Section in both, F5 is Date and Time, and
in an editor Ctrl+V has to paste. That is not a criticism of PlanCake -- it is
a reader, and a reader can spend its keys differently -- but it is why none of
its chords appear here.

### 1. A note is one keystroke away, and the dialog is tiny

**PlanCake.** Enter on any block opens Add note, focused on the note box, with
"Note on" showing the start of the block. Enter saves, Ctrl+Enter is a new
line, Escape cancels, and the setting can swap Enter and Ctrl+Enter.

**QUILL today.** Inline notes (`quill/ui/main_frame_inline_notes.py`, core in
`quill/core/inline_notes.py`). On **Tools > Writing and Language**:

- **Add Inline Note...** `Alt+Shift+I` -- notes the selection, or the current
  line if nothing is selected. Says "Inline note added."
- **Next Inline Note** `Alt+Shift+J` and **Previous Inline Note**
  `Alt+Shift+K` -- wrap, and say "Inline note 2 of 5: ...".
- **Speak Inline Note (double to edit)** `Alt+Shift+H` -- says the note at the
  caret; pressed twice within 0.6 seconds it opens Edit Inline Note, which has
  Save, Delete and Cancel. That double press is the only way to edit or delete
  a note.

**QUILL Lite today.** No inline notes at all. `quill/core/lite/parity.py`
records this as one of four note chords Lite does not have, and Lite spends
`Alt+Shift+I` on **Tools > Snippets...**.

**The gap.** The QUILL dialog is already small and already anchored, so the
gap is not the dialog. It is that Lite has none, that the dialog does not show
which text the note is on (PlanCake's "Note on" line is a good check before
saving), and that the only way to delete a note is a timed double press.

**Proposal.**

- Bring inline notes to QUILL Lite (shortlist item 6). The core is already
  wx-free and shared; Lite needs four rows in its command table on the same
  four chords (rule 2: the command both products have keeps the chord). Lite's
  Snippets moves off `Alt+Shift+I` to `Ctrl+Alt+Shift+Home`, free in both, and
  QUILL gains the same chord as an alias for its snippet gallery (rule 5),
  which also eases the existing rule 6 strain of Lite reaching on a plain chord
  what QUILL keeps on the leader. Update the `cmd_snippet_gallery` entry in
  `parity.py` in the same change. (Any chord ending in Insert would be the
  mnemonic and is out: Insert is the screen reader's modifier and
  `quill/core/reserved_keys.py` refuses it in every combination. The
  `cmd_snippet_gallery` docstring in `quill/apps/lite_window_typing.py` still
  names `Ctrl+Shift+Insert`, which is stale.)
- Add a read-only **Note on** line to the Add/Edit Inline Note dialog showing
  the first sentence of the anchor text, with `SetHelpText` at construction.
  The screen reader reads it as part of the dialog; the app announces nothing
  extra (GATE-13).
- Add **Delete Inline Note** on `Alt+Shift+Delete` (free in both), on the same
  menu. It deletes the note at the caret after a Yes/No that names the note,
  and says "Inline note deleted." The double press stays as a shortcut to
  editing.

**Status: built (2026-10-04).** Lite has all four chords plus Delete and List,
from the shared `quill/ui/inline_notes_commands.py`; Snippets moved to
`Ctrl+Alt+Shift+Home` in Lite and QUILL aliases it; the note dialog has the
Note on line; Delete Inline Note is on `Alt+Shift+Delete`.

### 2. The note lives in the file

**PlanCake.** Notes are plain text inside the Markdown file, right after the
block, between `[usernote]` and `[/usernote]` (markers changeable in
Settings). Markers inside code spans, code blocks and HTML comments are
ignored, so a document that shows the markers as an example is left alone.

**QUILL today.** The opposite choice, made deliberately: notes go to a
sidecar, `inline_notes.json` in the app data folder, keyed by the document's
path like bookmarks. Each note keeps its quote and 40 characters of context
either side, so it follows its text through edits; if the text is deleted the
note is kept, orphaned. The user guide says "Notes are yours alone and are
never written into the document." It works in every format because it never
touches the file.

**The gap.** A sidecar note cannot be handed to anybody. The PlanCake use case
-- read an AI-written plan, leave notes, hand the file back to the assistant
-- is impossible: the assistant never sees them. Moving or renaming the file
loses them too, since the key is the path.

**Storage options, with trade-offs.**

- *Sidecar JSON (what we have).* Private, format-agnostic, never alters the
  document, survives any edit. But invisible to collaborators and tools, lost
  on rename, not in version control, and not in backups of the document.
- *Visible custom markers in the text (PlanCake's choice).* Everyone sees
  them: a text editor, GitHub's rendered view, an AI assistant. Simple to parse.
  But they show in every rendering, including a published one if somebody
  forgets to clear them; they need their own escaping rules; and making the
  markers configurable means changing them hides every existing note, which
  PlanCake's manual has to warn about at length.
- *HTML comments in Markdown.* `<!-- ... -->` is valid CommonMark and GFM, so
  the file stays a correct Markdown document. Renderers (GitHub, Pandoc's HTML
  writer) hide comments, so a forgotten note never shows up in a published
  page. Plain-text editors and AI assistants still see them. Costs: a sighted
  reviewer on GitHub does not see them either; the text cannot contain `-->`;
  and our own preview and Save As HTML currently print comments as literal
  text (`quill/core/browser_preview.py` escapes raw HTML), which would need
  fixing anyway.

**Proposal (shortlist item 8).** Keep the sidecar as the default, and add a
second kind of note for Markdown and HTML documents only: a **note in the
file**, written as an HTML comment on its own line after the paragraph or list
item the note is on, in one fixed, QUILL-owned form, for example:

    <!-- quill-note: Back up the uploads folder too. -->

- The form is fixed, not configurable, for the reason above.
- `-->` in the note text is written as `--&gt;` and read back; a note never
  spans a code fence, and one placed on a code block goes after the fence.
- A checkbox in the Add Inline Note dialog, **Write this note into the file**,
  defaults from one new shared setting (both editors' `Settings`, so the
  settings-vocabulary gate sees `shared`). It is disabled with a reason in its
  help text for formats other than Markdown and HTML.
- Next, Previous, Speak and the notes list treat both kinds the same and say
  which kind a note is only in the list's column, not in every announcement.
- Because the note is now document text, adding, editing and deleting it go
  through the editor's undo stack -- Ctrl+Z undoes it like any typing, which
  sidecar notes cannot offer today.
- We recognise only our own `quill-note:` comments. No reading of PlanCake's
  markers or anyone else's (the competitor-data rule).
- Preview and Save As HTML render a `quill-note` comment as a visibly marked
  `aside` with an accessible name "Note" (PlanCake's "User note" region is the
  model), behind an export option that defaults to leaving notes out.

**Status: built (2026-10-04).** `quill/core/inline_notes_file.py`; the check box
defaults from the shared `inline_notes_in_file` setting and then from each
document's last choice. Preview shows notes as asides; export leaves them
out unless the user says Yes.

### 3. One place lists every note, and keys walk them

**PlanCake.** A notes list beside the document (note, lines, the block it
follows), Enter to go there, Delete to delete with the selection moving to the
nearest note, F6 between list and document, F9 and Shift+F9 from anywhere.

**QUILL today.** Next and previous (`Alt+Shift+J` / `Alt+Shift+K`) and speak
(`Alt+Shift+H`). No list, no count, no export, no remove-all. Nothing in Lite.
(`quill/ui/notes_reader.py` is unrelated: it is the podcast show-notes viewer.)

**Proposal (shortlist item 5).** **List Inline Notes...** on `Alt+Shift+Enter`
(free in both; it sits with the other four note chords on Alt+Shift), on the
same menu, through `_show_modal_dialog` in QUILL and Lite's dialog entry.

- A list view with columns Note, Line, and On (the first sentence of the
  anchor text, or "Text deleted" for an orphaned note -- which finally gives
  orphans a way to be seen and removed).
- Enter goes to the note and closes the list; Delete deletes, asking per a
  shared "Ask before deleting a note" setting, and keeps the selection on the
  nearest note; F2 or the Edit button edits.
- Buttons: **Edit**, **Delete**, **Remove All** (always asks, naming the
  count), **Copy All** (plain text, one note per paragraph with its line and
  anchor), **Export...** (JSON or Markdown). Close carries no access key
  (GATE-14).
- Spoken: only outcomes the reader cannot see -- "3 notes removed", "Notes
  copied". The list's own rows are read by the screen reader.
- F1: every control gets inline `SetHelpText`; the window's purpose goes in
  QUILL's and Lite's `surface_help` catalogues.
- Remove All and Export have no keys of their own, with the written reason
  that they live in the list (rule 8 allows a reason).
- An empty document answers `Alt+Shift+Enter` with "No inline notes in this
  document", the same sentence Next already uses, rather than an empty window.

QUILL also has browse mode (leader then N), where single letters move by
structure and `N` is unused inside the mode. Adding **N / Shift+N: next and
previous note** there is a small QUILL-only nicety (shortlist item 12); QUILL
may be ahead of Lite, never the reverse.

**Status: built (2026-10-04),** including browse mode `N` / `Shift+N`. The
list's Delete asks every time (Yes/No naming the note) rather than through a
separate "Ask before deleting" setting, which was not added.

### 4. Notes as a review loop for AI-written plans

**PlanCake.** `plancake list FILE --json`, `check` (exit 0 none, 3 some, 1
error), `clear` and `export`, documented as the way Claude reads a review and
proves every note is dealt with.

**QUILL today.** The command line opens files (`quill/__main__.py`: paths,
`--line`, `--goto`, `--diff`, `--wait` and more) but has nothing for notes.

**Proposal (shortlist item 11, later).** Once notes can live in the file,
`python -m quill notes list|check|clear FILE [--json]`, wx-free, in
`quill/core`, reading only `quill-note:` comments. It is a small module but it
is a new public surface, and it only makes sense after item 8 ships, so it
ranks low. Sidecar notes stay out of it: they are private by design.

**Status: built (2026-10-04)** as `quill --notes list|check|clear FILE [--json]`
(also `QuillLite.exe --notes ...`), `quill/core/inline_notes_cli.py`. Exit 0
done, 3 notes left, 1 read or write error, 2 usage.

### 5. Task lists you can tick

**PlanCake.** A `- [ ]` item is a real checkbox; Space or Enter asks
(optional), writes `[x]` on that one line, says "Task checked", and undo
reverses it. A parent with mixed children shows as partly checked but writes
nothing.

**QUILL today.** **Insert > List > Task** (no key) inserts `- [ ] ` per line;
Enter on a task line continues the list. Structured List Studio
(`Ctrl+Alt+Shift+L`) has a "Task is complete" checkbox for one item at a time.
`quill/core/lists/announce.py` already has `checklist_toggle_announcement`
("Checked: X. 2 of 7 tasks complete.") and nothing calls it. The preview's
renderer does not render task lists at all; `- [ ]` shows as literal text.

**QUILL Lite today.** **Insert > Markdown Tag...** (`Ctrl+Alt+I`) can insert
a task list. No toggle.

**Proposal (shortlist item 2).** **Toggle Task Done** on `Ctrl+Alt+Enter`,
free in both editors, in both Format menus beside the list commands. On a
Markdown task line (or every task line in a selection) it flips `[ ]` and
`[x]` through the ordinary editor edit, so Ctrl+Z undoes it. Spoken, via the
existing announcement: "Done: Write the tests. 3 of 7 tasks done." -- the count
is the part a listener cannot get any other way. On a line that is not a task
it says "Not a task line" and changes nothing. No confirmation: in an editor
the change is visible, undoable and unsaved until you save, which is why
PlanCake needs a question and we do not. Two small companions: the preview and
Save As HTML render task items as disabled checkboxes with their state in the
accessible name, and the Markdown Tag picker's task entry and this command use
the same core function. (Ctrl+Alt+Enter is Word's style separator; neither
editor has that function, so rule 1 does not bite. It is also Add to Up Next
inside Quill Radio's Local Media window, a different app window, which rule 7
allows.)

**Status: built (2026-10-04).** `quill/core/task_lists.py` and the shared
`quill/ui/task_list_commands.py`; QUILL has the row in Insert > List, Lite in
Format. The Markdown Tag picker was not changed.

### 6. Plans arrive however they arrive

**PlanCake.** Ctrl+V opens a file copied in File Explorer, a path copied as
text (with or without quotes), or an http(s) link. Ctrl+L opens a link,
prefilled from the clipboard, understands GitHub page links, saves to
Downloads with `.md` forced and the mark of the web, 30 seconds and 10 MB
limits. Command line and drag and drop too. One window per file.

**QUILL today.**

- Command line: yes, many files, single instance with forwarding, and an
  already-open file selects its tab. **Lite** likewise, one window per file.
- **File > New Document from Clipboard** (no key) makes a new buffer from
  clipboard *text*. Nothing opens a file copied in Explorer or a copied path,
  in either editor.
- **File > Open from URL...** (no key). It has real problems, found while
  researching this note, and they are bugs rather than gaps:
  - the user guide promises "QUILL checks with you first, naming the host and
    the expected size"; the code asks for the URL and downloads immediately;
  - `download_url` raises `RemoteTransportError`, but `open_url` catches only
    `HTTPError` and `URLError`, so a network failure most likely escapes as an
    unhandled error instead of a message (`quill/ui/main_frame.py` around line
    7370, `quill/io/http_transport.py` line 115);
  - the download runs on the UI thread, and the egress audit entry for
    `download_url` claims a visible progress callback that is not passed;
  - the temp file (`quill-url-*`) is never removed.
- **File > Open from Remote > GitHub File URL...** takes github.com blob links
  only.
- **Lite**: no Open from URL. Neither editor accepts drag and drop.

**Proposal.**

- *Fix Open from URL first* (shortlist item 1): add the consent the guide
  promises (host and size, asked before any bytes), catch the coded error and
  say it plainly, run on `QuillTaskManager` with a cancellable progress
  dialog, delete the temp file when the tab closes, and route github.com blob
  links through the raw URL as PlanCake does.
- *Open from Clipboard* (shortlist item 3) on `Ctrl+Alt+Shift+Enter`, free
  in both (every letter chord with Ctrl+Alt+Shift is taken, and
  `Ctrl+Alt+Shift+Q` is QUILL's global show-and-hide hotkey; Enter at least
  says "open"). On **File**, beside Open, in both editors. It
  looks at the clipboard in order: files copied in Explorer
  (`wx.FileDataObject`; open each, or the first if there are many and say how
  many were skipped), a path as text (quotes stripped), an http(s) link
  (handed to Open from URL, consent and all). Otherwise it says "The clipboard
  holds no file, path or link." Ctrl+V stays paste. The shared logic -- the
  classification -- goes in `quill/core` so both editors call one function.
- *Lite gets Open from URL* on the same terms as QUILL, through the same
  `quill/io/http_transport` and the same egress entry; no new outbound call
  site.
- *Drag and drop open* (shortlist item 10), a `wx.FileDropTarget` on the
  frame of each editor. Small, and mostly for low-vision and sighted users.

**Status: built (2026-10-04), items 1, 3 and 10.** Open from URL is
`quill/ui/open_from_url.py`, shared: `download_url` gained `confirm` (called
after the headers, before the body) and `should_cancel`, removes a partial file
on any failure, and runs on the task manager with an `AIProgressDialog`; GitHub
blob links become raw links; failures are one sentence from
`open_sources.failure_sentence`; QUILL removes the temp file when the tab
closes, Lite as soon as it is read, and `sweep_stale_downloads` clears day-old
leftovers. Lite gains the command (no key, as in QUILL, with a written reason).
Open from Clipboard is `Ctrl+Alt+Shift+Enter` in both, classification in
`quill/core/open_sources.py`. Drops use `quill/ui/open_sources_ui.py`: a
`FileDropTarget` on the frame and a composite target on the editor that still
inserts dropped text.

### 7. Refusing to destroy what it cannot read

**PlanCake.** Legacy-encoding files open read-only, naming the encoding;
conversion to UTF-8 is opt-in; an uncertain encoding is never written.

**QUILL today.** `quill/io/text.py` tries the BOMs, strict UTF-8, then cp1252,
then latin-1, and says "Opened using cp1252 text encoding (not UTF-8)." in the
status bar. **File > File Format...** (`Ctrl+Alt+E`) changes how the file is
saved. There is no "reopen with encoding".

**QUILL Lite today.** `quill/core/lite/textfile.py` falls back to cp1252 with
`errors="replace"`. That is lossy: bytes 0x81, 0x8D, 0x8F, 0x90 and 0x9D
become U+FFFD, and saving writes the replacement characters back. Nothing is
said on open. This is the one place in this note where PlanCake's caution
points at a real data-loss risk in the family.

**Proposal (shortlist item 4).** One shared decoder for both editors (QUILL's,
which never needs `replace`), and one rule from PlanCake: a file decoded by a
fallback is announced on open in both editors, "Opened as Windows-1252, not
UTF-8", once, as an outcome (GATE-13 allows it; the reader cannot know). A
**Reopen with Encoding...** button inside the File Format dialog (no new key)
re-reads the bytes from disk under a chosen code page. We do not convert on
open; the buffer becomes UTF-8 only when the user saves, and the existing
"characters cannot be saved" prompt covers the reverse.

**Status: built (2026-10-04).** `quill/core/text_decoding.py` is the one
decoder (BOM, strict UTF-8, strict cp1252, latin-1; never `replace`), used by
`quill/io/text.py` and `quill/core/lite/textfile.py`; Lite's RTF read went to
latin-1 both ways for the same reason. It also registers a `utf-16-be-bom`
codec, so QUILL keeps big-endian UTF-16 as Lite already did. Both editors say
`open_notice()` once on open. **Reopen with Encoding...** is a button in both
File Format windows (`choose_reopen_encoding` in
`quill/ui/file_format_dialog.py`), strict, saving back in the chosen code page
until the person picks UTF-8. Byte-fixture round trips:
`tests/unit/core/test_text_decoding_lossless.py`.

### 8. Never overwrite a change it has not seen

**PlanCake.** Reloads in place on outside change, keeping position; refuses a
note write if the file changed underneath and says "The file changed. Please
try again."

**QUILL today.** A real watcher (`quill/core/external_change.py`,
`quill/ui/main_frame_external_change.py`): it asks Reload / Keep Mine / Open
Disk Version in New Tab, with **File > Reload from Disk**, **File > Check for
External Changes...** and **File > Forget Remembered File-Change Answers**
(`Ctrl+Shift+F11`). But Save does not re-check the disk before writing, so a
change landing between two polls is overwritten silently.

**QUILL Lite today.** No watcher, no prompt, no save-time check.

**Proposal (shortlist item 7).** A save-time check in shared code: compare the
file's snapshot with the one taken at open or last save, and if it differs,
ask before writing, with the same choices the watcher offers. Then move the
watcher's decision logic, which is already wx-free, into Lite. This is the
PlanCake idea that matters most for the "AI assistant rewrites the plan while
I read it" workflow, and it is correctness, not a feature. Reload should keep the
caret where it was, as PlanCake keeps the reading position.

**Status: built (2026-10-04), the save-time check in both.**
`external_change.changed_since` compares size, mtime and SHA-256 with the
baseline taken at open, save, reload, reopen and Keep Mine;
`quill/ui/save_conflict_dialog.py` asks Save As (Enter) / Reload from Disk /
Overwrite / Cancel (Escape) in both editors.

**Status: built (2026-10-04), the watcher in Lite too.** The decisions QUILL's
mixin still held moved into `quill/core/external_change.py` (`decide_for`,
`remember_answer`, `forget_answers`, `poll_disk`, which stats every tick and
hashes only when size or mtime moved); the clock is the shared
`quill/ui/external_change_timer.py`, which pauses under any modal window; the
question is the shared `external_change_dialog.py`, with Save As as Lite's
third answer and Keep Mine on Enter. Lite stores QUILL's six
`external_change_*` fields (four in Preferences, plus Forget remembered
file-change answers), watches each document from `quill/apps/lite_window_watch.py`
on the save check's own baseline, reloads an unchanged document quietly
keeping the caret line, and says a deletion once.

### 9. A page you can share

**PlanCake.** Export to one self-contained HTML file, styles inside, no
scripts, local images embedded, notes marked; notes to JSON.

**QUILL today.** **File > Export > HTML...** runs Pandoc (`gfm`), but without
`--standalone`, so it most likely writes a fragment rather than a page. Save
As `.html` uses the in-house renderer: a full page, no CSS, no task lists,
strikethrough or nested lists, and it makes the open document become the
`.html` file. **QUILL Lite**: no HTML export.

**Proposal (shortlist item 9).** Make Export > HTML pass `--standalone` with a
small built-in accessible stylesheet and the document language, offer
"include inline notes" (marked asides, item 2) and bring the same command to
Lite through the same shared function. Teach the in-house renderer task
lists and strikethrough, which the Markdown Tag picker already inserts.

**Status: built (2026-10-04).** `quill/io/html_page.py` and the shared
`quill/ui/html_export_commands.py`, on `Ctrl+Alt+Shift+End` in both editors.
Notes are included as marked asides only when the user says Yes.

### 10. Every outcome is spoken, and only the outcome

PlanCake's status messages are a good fit with our GATE-13: it says "Note
added", "No more notes", "Undone: note added" and nothing about focus or
titles. Every proposal above follows the same rule, and we already have the
machinery (`action_feedback`, failures and counts always spoken). One borrowed
detail is worth adopting everywhere: when undo reverses a note or task change,
say what was undone ("Undone: task done"), which QUILL already does for text
through Undo and Say (`Alt+Shift+F3`).

### 11. Privacy stated plainly

PlanCake's manual has a short "What goes over the network" section naming
exactly two uses. QUILL has far more network features and an egress audit, so
the equivalent is a generated page, not a paragraph; nothing to build here
beyond making sure every proposal above adds no new call site (they do not:
Open from Clipboard reuses Open from URL's).

## Ranked shortlist

Highest value for the lowest cost first. S is a day or less, M a few days with
tests and docs, L a week or more. Every item lands in shared code and reaches
both editors in the same change, except item 12, which is QUILL-only and so
cannot put Lite ahead.

1. **Fix Open from URL** (S). The consent the user guide already promises,
   catch `RemoteTransportError`, run off the UI thread with progress, delete
   the temp file, rewrite GitHub blob links to raw. A bug fix, not a feature.
2. **Toggle Task Done**, `Ctrl+Alt+Enter`, both editors (S). Plus task items
   rendered in preview and Save As HTML. Uses the announcement that already
   exists and is never called.
3. **Open from Clipboard**, `Ctrl+Alt+Shift+Enter`, both editors (S). File
   copied in Explorer, path as text, or link (via item 1).
4. **Honest legacy encodings** (M). One shared, lossless decoder; announce a
   fallback on open in both editors; Reopen with Encoding inside the File
   Format dialog. Removes a real data-loss path in Lite.
5. **List Inline Notes**, `Alt+Shift+Enter` (M). Go to, edit, delete, remove
   all, copy all, export; orphaned notes finally visible. Plus Delete Inline
   Note on `Alt+Shift+Delete` and the "Note on" line in the note dialog.
6. **Inline notes in QUILL Lite** (M). Same four chords; Lite's Snippets moves
   to `Ctrl+Alt+Shift+Home`, aliased in QUILL. Can ship with or after item 5.
7. **Never overwrite an unseen change** (M). Save-time disk check in both;
   the external-change watcher comes to Lite.
8. **Notes in the file** for Markdown and HTML, as `<!-- quill-note: ... -->`
   (M to L). The PlanCake idea proper: notes an AI assistant or a colleague can
   read. Includes preview and export rendering, and undo for free.
9. **A page you can share** (M). Standalone Pandoc HTML export with a small
   accessible stylesheet and an "include notes" option, in both editors; task
   lists and strikethrough in the in-house renderer.
10. **Drag and drop open** in both editors (S).
11. **Notes on the command line**, `list` / `check` / `clear` with `--json`,
    for in-file notes only (M). Only after item 8.
12. **Browse mode N and Shift+N** for next and previous note, QUILL only (S).

## The three to do first

- **Toggle Task Done (item 2).** The smallest change with the most daily
  value: AI plans are full of checklists, ticking one is two keys, and the
  spoken count ("3 of 7 tasks done") is information a listener otherwise has
  to count line by line.
- **Open from Clipboard (item 3), together with the Open from URL fix (item
  1).** Plans arrive as a file in Explorer, a path in a chat, or a link.
  Today none of the three opens in one step in either editor, and the one URL
  path we have is broken in ways that will bite the first time a network
  hiccups. The fix is a prerequisite anyway.
- **List Inline Notes (item 5).** It turns notes from something you can only
  meet one at a time into a review you can see whole, remove when done, and
  hand on as text or JSON. It is also the surface item 8 needs, so building it
  first means "notes in the file" becomes a storage change rather than a new
  feature.

## What we should not copy, and why

- **Enter as the note key in the editor.** PlanCake is a reader; in an editor
  Enter must make a new line. The idea survives where it fits: Enter on a
  block in our preview pane could offer Add Inline Note later, but not in the
  edit control.
- **Ctrl+V meaning "open".** Paste has to paste (rule 1). Open from Clipboard
  gets its own key.
- **Configurable note markers.** PlanCake's own manual spends a warning and a
  troubleshooting entry on the fact that changing the markers hides every
  existing note. One fixed form avoids the whole class of problem. We also do
  not adopt `[usernote]` or any other tool's form, and do not read them: notes
  in the file are ours, written and read in our own form only.
- **Visible plain-text markers as the default.** They show in every rendering,
  including a published page if somebody forgets to clear them. An HTML
  comment keeps the file valid and the published page clean.
- **Reloading silently on outside change.** Right for a reader that never has
  unsaved edits; wrong for an editor, where a silent reload throws away work.
  QUILL already asks, and Lite should too.
- **Converting the file on disk at open.** PlanCake's opt-in conversion
  rewrites the file the moment it opens. An editor should convert in the
  buffer and write only on Save, so opening a file never changes it.
- **A web view as the main reading surface.** It is right for PlanCake, and
  PlanCake's JAWS notes show what it costs (forms mode on Enter, a click and
  Enter indistinguishable). Our edit control with Quick Nav and the preview
  pane already give both kinds of reading without that cost.
- **Its keys.** Ctrl+L, Ctrl+E, F5, F9, Shift+F9 and Alt+Shift+Up and Down
  all mean something else in both editors, mostly by rule 1 (see the start of
  the detailed section).
- **A forced `.md` suffix on downloads as a safety measure.** Clever for a
  Markdown-only reader; QUILL opens many formats, and its downloads already
  open as read-only remote tabs that save only as a copy, which is the same
  protection without renaming the user's file.

## Keys proposed, and how they were checked

All checked on 2026-10-04 against `DEFAULT_KEYMAP` and `DEFAULT_ALIASES`
(`quill/core/keymap.py`), `APP_KEYMAPS` and the QuillVille launcher row
(`quill/core/app_keymaps.py`), QUILL Lite's `COMMANDS`
(`quill/core/lite/commands.py`), the Recent Documents rows on Alt+Shift+1
to 9, QUILL's global show-and-hide hotkey (`quill/ui/main_frame_hotkeys.py`)
and the reserved Insert key (`quill/core/reserved_keys.py`). Each is free in
both editors, so each is a rule 5 adoption rather than a move.

- `Ctrl+Alt+Enter` -- Toggle Task Done.
- `Ctrl+Alt+Shift+Enter` -- Open from Clipboard.
- `Alt+Shift+Enter` -- List Inline Notes.
- `Alt+Shift+Delete` -- Delete Inline Note.
- `Alt+Shift+I`, `J`, `K`, `H` -- the existing inline-note chords, adopted by
  Lite (rule 2), which moves Lite's Snippets to `Ctrl+Alt+Shift+Home` (free in
  both; QUILL aliases it for its own gallery).

Each new command also needs, in the same change: a menu row in both editors
built from the bound key (`_menu_label` in QUILL, the table in Lite), a
Key Describer title (GATE-DESCRIBE), behavioural tests that call the Lite
handler (GATE-LITE-COVER), inline `SetHelpText` on any new dialog control,
regenerated `docs/keyboard-reference.md`, and user-guide text in both guides.

## Small things found along the way

These are not PlanCake lessons, but the research turned them up and they
should not be lost.

- `docs/user guide/userguide.md` says inline notes are on "Tools > Writing";
  the menu is **Tools > Writing and Language**. (Fixed 2026-10-04.)
- The same guide puts Sticky Notes under Tools; the code has them under
  **Navigate > Sticky Notes**. (Fixed 2026-10-04.)
- The `quill/ui/main_frame_inline_notes.py` docstring still says the previous
  note key is G; it is K. (Fixed 2026-10-04.)
- QUILL's guide says leader then G opens Quick Nav (Landmarks); since
  2026-10-03 it is `Ctrl+Shift+Z`, and G is an ordinary chord key. (Fixed
  2026-10-04.)
- The Lite guide says the Heading Organizer does not work in rich text; it has
  since 2026-09-22.
- `quill/apps/lite_window_markup.py` docstrings name `Ctrl+Shift+M` for
  Switch Document Mode; it is `Alt+Shift+F` (`Ctrl+Shift+M` is Set Mark).
- Save As `.html` makes the open document become the HTML file
  (`document.mark_saved`), which surprises anyone who meant "export".
