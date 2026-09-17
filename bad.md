# QUILL and QuillLite: the parity and viability plan

**Working list, 2026-09-16.** What is left, not what happened -- a landed item
is **deleted** from this file and git history is the record. Three dimensions:
the two editors' keys and capabilities must agree, each app must be viable for
its own job, and both must behave the way Notepad, WordPad and Word do where a
person's hands already know the answer.

## 0.3 Where this stands

**Working from the top of section 10 down, deleting a row as it lands.** The
count at the head of that table is the number that matters; everything else in
this file is the detail behind a row.

The save-path work that was held under 0.6 ("write and test, do not commit
anything touching startup, the save path or the external-change watcher") has
been **reviewed and committed**: F1, F2, F3 and F9. That unblocks R6, which
wanted F1's Markdown conversion, and P0.9, which reuses F3's sentence.

### The one gate still red, and why

`test_repo_layout::test_repository_root_markdown_is_limited_to_sanctioned_files`
fails because **this file** is an unsanctioned root Markdown file. It goes green
the moment this file is empty and deleted, which is the point of the exercise.

## 0.5 The viability bars

**QuillLite** replaces Notepad and WordPad for somebody who listens: open
anything Notepad opens, at any size, and never corrupt what it did not
understand. Its PRD also accepts `.py`, `.json` and `.conf` editing.
**QUILL** is the writing environment somebody moves into; its editing core must
be at least as good as the small product's, because every hour in QUILL is
spent in the editor.

| Bar | Fails | Why |
| --- | --- | --- |
| A big file behaves | **passed** | The size guard landed 2026-09-16; the document mirror (`quill/core/document_text.py`) retired the three scans per status refresh and the O(N) read per keystroke. What is left is the gate that keeps it that way (section 9, item 8) |
| The text's typeface and size can be changed | **passed** | 2026-09-16 (P0.6a). Kept by GATE-9, `tests/unit/tools/test_editor_font_gate.py` -- an existence gate, because the absence of a whole capability is the one thing a suite of feature tests cannot notice |
| A file survives the round trip | QUILL | 6.3. F1, F2, F3 and F9 landed 2026-09-17, so **QuillLite passes**: Save As converts the file rather than the window, a character the encoding cannot hold is asked about, and a recovery restores the document's own encoding or claims nothing. What is left is QUILL's: F4, F5, F6 |

## 0.6 Decisions (2026-09-16) -- the standing mandate

Answered by the user. These are settled; do not re-litigate them.

| Question | Answer |
| --- | --- |
| AI's six three-modifier chords | **All six vacate.** `Ctrl+Alt+Shift+{S,I,G,T,H,E}` go to Sort Z-A, Tab Inserts a Tab, Paste Collected, Tidy Whitespace, Previous Heading and Earlier Versions -- QuillLite's meanings. AI keeps its menu, the palette and `Alt+Q`. |
| The leader reclaim | **Retire all 16** GitHub, remote-file and local-git administration positions; menu and palette only. Navigation on the leader is untouched. |
| Insert Image | Moves `Ctrl+Alt+I` -> `Ctrl+Shift+I`, freeing `Ctrl+Alt+I` for Insert Markdown Tag. Document Intake Report -> leader. |
| Blockquote | **Merges into Quote Lines** on `Ctrl+Shift+Q`; `format.blockquote` retires; `Ctrl+Alt+Q` -> Duplicate Selection. |
| Numbered list | **Folds into the `Ctrl+Shift+L` cycle** (bullets -> numbered -> off, WordPad's behaviour); `Ctrl+Alt+N` -> New Plain Text Document. QuillLite rings on that key as of 2026-09-16; QUILL's `Ctrl+Alt+N` is still its own command. |
| `keep_unique_lines` / `remove_duplicate_lines` | **Merge**: one verb, QuillLite's `Ctrl+Alt+D` and its wording. `Alt+Shift+K` freed. |
| `trim_blank_lines` / `remove_blank_lines` | **Both kept, renamed** so a listener can hear the difference: "Trim Blank Lines at the Ends" and "Remove Every Blank Line". |
| Spelling context menu (S11) | **Corrections first, fixed tail**, in both. The first Down arrow lands on a correction; everything after it is always the same rows in the same order. |
| QuillLite's clip history (C1) | **Make the promise true in both**, OFF by default, with setting text that says plainly it stores everything you copy including from a password field. QUILL's capture gains Cut. |
| New-document line endings (F11) | **CRLF in both**, with a setting. Opened files keep whatever they had. |
| Crash recovery and session restore (F14, G4) | **Both editors ask, then restore.** Recovery lists what it found; QUILL gains session restore on QuillLite's rule (command-line files win). |
| QUILL -> QuillLite crossings (4.2) | **All three tiers approved.** |
| The magical tier | **All four approved**: repeat the last announcement, structure on arrival, "what changed?", spoken undo. |
| `DocumentText` (P0.6c) | **Build it fully.** |
| The QuillLite profile in QUILL (P2.4) | **Build it**, after the G1 settings-name reconciliation it depends on. |
| Temporary bookmark | **Kept, and crosses to QuillLite.** Not retired -- a pin you drop and forget is a different thing from a bookmark you keep, and QuillLite should have it too. |
| Drag-and-drop file opening (P3.8) | **Declined.** |
| QuillLite and braille (A4) | Write the position into QuillLite's PRD as a decision. Implementing braille there stays out of scope. |
| Keymap profile snapshots (P2.6) | **Convert to deltas.** |
| Quick Nav | **Kept, not merged.** Go To Anything -> `Ctrl+Alt+Shift+A` (QuillLite's chord); Quick Nav -> **`Ctrl+Shift+Z`**, which also **closes** it, so the key is a toggle -- Escape still closes it too. Free in both, and Redo is `Ctrl+Y` here as it is in Word, so nothing collides. Worth knowing: `Ctrl+Shift+Z` is Redo in VS Code and browsers, so somebody arriving from those may press it expecting Redo. Leader `G` is then free for a favourite-folder command. See 3.5. |

**Working rules while unattended.** Commit each logical chunk with all 40 gates
green. Stop and leave a note for: a feature removal beyond this table; a move
of an x.md authoring chord not in this table. Write, test, but do **not**
commit anything touching startup, the save path or the external-change watcher.

## 1. The rules

Lower number wins when two conflict.

1. **Microsoft's key wins** where Word, WordPad or Notepad bind one for a
   function both editors have. Exceptions, each because another Microsoft
   product or a family habit owns the chord: `F3`/`Shift+F3` find next and
   previous, `F5` date and time, `Ctrl+D` duplicate line, `Ctrl+]`/`Ctrl+[`
   indent and outdent, `Ctrl+Q` exit.
2. **The command both products have keeps the chord**; the product-only command
   moves.
3. **Frequency breaks ties**: the verb used in the editing loop keeps the
   shorter chord.
4. **Destructive first**: a habit that does damage in the other editor is fixed
   before one that merely opens the wrong dialog.
5. **A chord free in both is adopted as an alias**; nothing moves.
6. **Nothing QuillLite reaches on a plain chord lives on QUILL's leader.**
7. **Editor chords are for the editor.** Media, radio favourites, favourite
   folders, AI, GitHub and remote-file commands live on the leader, in the
   owning app's `APP_KEYMAPS`, or in a menu.
8. **Every registered editor command has a key or a written reason not to.**
9. **Once-a-year commands need *a* key, not the same key** -- the F-keys past
   F9 are where they go.
10. **Value flows both ways, violations flow one** (4.0).
11. **Every remaining divergence is a comment in `keymap.py` *and* an entry in
    the parity gate's exception table.**

## 3. The golden family keymap

Every row is a decision. "Golden" is the chord both editors will use. "Moves"
names what is displaced in which editor and where it goes. Where a row depends
on another (a chord freed by an earlier move), the dependency is named. Rows
marked **(new)** are commands QUILL does not have today and gains in section 4.

### 3.1 Word, WordPad and Notepad keys (rule 1)

| Command | QuillLite today | QUILL today | Golden | Moves |
| --- | --- | --- | --- | --- |
| Underline | `Ctrl+U` | hard-coded, no keymap entry | `Ctrl+U` | QUILL: keymap entry; the char hook dispatches the registered command instead of a method |
| Document Statistics (Word Count) | `Ctrl+Shift+G` | `Ctrl+Shift+W` (Word Count) | `Ctrl+Shift+G` | Word's Word Count key. Lite moved 2026-09-16; QUILL's half is outstanding and frees `Ctrl+Shift+W` for Select Word. `go_to_page` folds into the Go To dialog (5.4) |
| Font for Selection | `Ctrl+Shift+F` | `format.font_dialog`, no key | `Ctrl+Shift+F` | Word's font key. QUILL `search_in_files` -> `Ctrl+Alt+Shift+F`; QUILL `toggle_fold` -> `Ctrl+Shift+[` and `list_folds` -> `Ctrl+Shift+]` (free in both); Lite Customize Features -> `Ctrl+Alt+F10` (rule 9) |
| Editor Font | `Ctrl+Alt+F` | (Preferences only) | `Ctrl+Alt+F` | QUILL gains a direct command **(new)**; free |
| Next window / document | `Ctrl+F6` (MDI) + `Ctrl+Tab` | `Ctrl+Tab`; `Ctrl+F6` = `focus_preview` | `Ctrl+F6` and `Ctrl+Tab` | Word's `Ctrl+F6`. QUILL `focus_preview` -> `Ctrl+Shift+F6` (free in both) |
| Text size in / out / reset | `Ctrl+=` `Ctrl+-` `Ctrl+0` | (none) | same | Notepad's keys. QUILL gains the commands **(new)**, see 5.5 |
| Date and Time | `F5` | Quillin item, no key, gone in Safe Mode | `F5` | QUILL re-registers a core command backed by the shared `quill.core.datetime_insert`; the `insert-tools` Quillin keeps its date-only/time-only variants |
| Body Text | `Ctrl+Alt+0` | (none) | `Ctrl+Alt+0` | Word uses `Ctrl+Shift+N`, which Notepad and Lite spend on a new document; the ladder's zero is the family key. QUILL gains the command **(new)** |

### 3.2 Destructive overlaps (rule 4)

| Chord | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| `Ctrl+Alt+T` | Trim Trailing Spaces | Insert Table | **divergent, on purpose** | Decided 2026-09-16: Insert Table keeps `Ctrl+Alt+T` in QUILL (an authorized x.md authoring chord for a verb that builds structure), and QUILL's Trim Trailing Spaces takes another chord. The one row in 3.2 that does not converge; it goes in the gate's exception table with this reason |

### 3.3 The structural selection family (one decision, six chords)

QuillLite's chords are all three-key; QUILL's are four-key or on the leader.
Rule 6 and rule 3 both say QuillLite's win.

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| Select Word | `Ctrl+Shift+W` | `Ctrl+Alt+W` | `Ctrl+Shift+W` | freed by Document Statistics (3.1) |
| Select Line | `Ctrl+Shift+E` | `Ctrl+Alt+E` | `Ctrl+Shift+E` | `insert_equation` -> `Ctrl+Alt+=` (free in both) |
| Select Sentence | `Ctrl+Space` | `select_chunk` (a run of one character class) | `Ctrl+Space` = **Select Sentence** | QUILL gains sentence selection from the shared `sentence_span` **(new)**; `select_chunk` **moves rather than retires** -- it is renamed Select Token and rebound. See 5.3a: it duplicates Select Word on words and is the only way to select a run of punctuation or whitespace |
| Expand Selection | `Ctrl+Shift+X` | leader `J` | `Ctrl+Shift+X` | `exchange_point_mark` -> `Ctrl+Alt+X` (Lite's) |
| Shrink Selection | `Ctrl+Alt+Shift+X` | leader `Shift+J` | `Ctrl+Alt+Shift+X` | free in QUILL |
| Exchange Cursor and Mark | `Ctrl+Alt+X` | `Ctrl+Shift+X` | `Ctrl+Alt+X` | as above |
| Duplicate Selection | `Ctrl+Alt+Q` | `Ctrl+Alt+Shift+Q` | `Ctrl+Alt+Q` | QUILL `format.blockquote` merges with `edit.quote_lines` (one verb, `Ctrl+Shift+Q`); `unquote_lines` -> `Ctrl+Alt+Shift+Q`; Lite Back Up Settings -> `Ctrl+Alt+F11` (rule 9) |

### 3.4 Lines, case and whitespace

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| Sort / whitespace / case scope | selection, else whole document | current line, whole document, or whole document depending on which of three helpers | **one helper**: selection, else whole document for line tools, else the word at the caret for case (Word's `Shift+F3` scope); rich text warns before a whole-document rewrite | 6.7 |
| Tidy Whitespace | `Ctrl+Alt+Shift+T` | no key | same | `ai_translate_selection` vacates |
| Tab Key Inserts a Tab | `Ctrl+Alt+Shift+I` | leader `U` | `Ctrl+Alt+Shift+I` | `ai_spell_check_interactive` vacates |
| Toggle Block Comment | -- | `Shift+Alt+A` | `Ctrl+Shift+/` | rule 2: `Alt+Shift+A` is Expand Abbreviations in both |
| Numbered list toggle | -- | `Ctrl+Alt+N` | (folded into `Ctrl+Shift+L` cycle) | frees `Ctrl+Alt+N` for New Plain Text Document (3.7) |

### 3.5 Navigation and bookmarks

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| List Headings | `Ctrl+Alt+L` | `outline_navigator` `Ctrl+Shift+O` | both | alias (rule 5) |
| Go To Anything | `Ctrl+Alt+Shift+A` | leader `G` | `Ctrl+Alt+Shift+A` | favourite folders (`Ctrl+Alt+Shift+O/A/R`) -> leader after the reclaim |
| Quick Nav | -- | **unbound** | `Ctrl+Shift+Z` (toggles: the chord closes it, and so does Escape) | **Corrected 2026-09-16: NOT a duplicate of Go To Anything.** Go To Anything is a palette over commands, headings, bookmarks and recent files; Quick Nav is a category-filtered landmark index over headings, links, lists, list items, tables, block quotes and code blocks, with counts. The first pass proposed merging them, which would have deleted the index. It has a key for the first time; leader `G` is freed for a favourite-folder command |
| Go to Bookmark... (list) | `Alt+Shift+G` | `Alt+Shift+B` | `Alt+Shift+G` + `Ctrl+Shift+F5` alias | `previous_inline_note` -> `Alt+Shift+K`; `Alt+Shift+B` becomes Status Bar (3.8) |
| Set Bookmark 1..9 | `Ctrl+Shift+N` | tray paste | `Ctrl+Shift+N` | 3.2 |
| Go to Bookmark N | -- | -- | (no chord) | Lite can *set* by number but only *go* by list or `F2`. `Alt+Shift+1..9` is taken by Lite's Recent File N, so no chord family: the list's rows begin with the digit, so digit then Enter is two keys and no new binding |
| Recent File 1..9 | `Alt+Shift+1`..`9` | (none) | `Alt+Shift+1`..`9` | QUILL gains the nine commands **(new)**; free |

### 3.6 Spelling

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| Thesaurus | (none) | `Shift+F7` | `Shift+F7` | Word's key; Lite leaves it unbound |
| Spelling Announcements | `Ctrl+Alt+Shift+F7` | Settings rows only | `Ctrl+Alt+Shift+F7` | free in QUILL; Lite unchanged |

### 3.7 File, clipboard, tools, help

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| New Rich Text / New Plain Text Document | `Ctrl+Shift+N` / `Ctrl+Alt+N` | (none) | same | QUILL gains both **(new)**; `Ctrl+Shift+N` free, `Ctrl+Alt+N` freed in 3.4 |
| Earlier Versions | `Ctrl+Alt+Shift+E` | `restore_previous_version` no key | same | `ai_switch_engine` vacates |
| File Encoding and Line Endings | `Ctrl+Alt+E` | two status-cell-only commands | `Ctrl+Alt+E` | QUILL gains one dialog in the File menu **(new)**; `select_line` moves (3.3) |
| Copy to Tray Slot... **(new in Lite)** | -- | leader `Shift+N` (slot N) | `Alt+Shift+Y` chooser in both; QUILL keeps its leader digits | 5.1 |
| Collect / Paste Collected / Clear Collector | `Ctrl+Alt+G` / `Ctrl+Alt+Shift+G` / `Ctrl+Alt+Shift+C` | `collect_clipboard_now` no key / (none) / (none) | same | `ai_grammar_style` vacates; QUILL gains the two missing verbs **(new)** |
| Keep Clip / Recent Clips | `Ctrl+Alt+M` / `Ctrl+Alt+Shift+M` | no key / no key | same | free |
| Markdown Tag | `Ctrl+Alt+I` | `insert_markdown_tag` no key | same | `insert_image` -> `Ctrl+Shift+I`; `document_intake_report` -> leader after reclaim |
| Expand Abbreviations (toggle) | `Alt+Shift+A` | leader `E` | `Alt+Shift+A` | block comment moves (3.4) |
| Keyboard Manager | `Ctrl+Alt+Shift+R` | `keymap_editor` no key | same | `remove_favorite_folder` -> leader after reclaim |
| Sound Scheme | `Ctrl+Alt+Shift+O` | `sound_events` no key | same | `open_from_favorite_folder` -> leader after reclaim |

### 3.8 View and window

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| Status Bar (show/hide) | `Alt+Shift+B` | (no command, no setting) | `Alt+Shift+B` | QUILL gains it **(new)**; `list_bookmarks` moves (3.5) |
| Focus the status bar | `F6` | `F6` next region | `F6` | see 5.6: QUILL's `F6` already lands in the status bar when it is the next region; the plan makes the status bar the *first* stop from the editor in both |
| Switch Document Mode | `Alt+Shift+F` | leader `K` | `Alt+Shift+F` | QUILL's half is outstanding: leader `K` stays until the reclaim (5.9) |
| Reveal Codes | -- | `Alt+F3` | `Alt+F3` | QUILL-only, no collision; documented divergence (Lite declined it in its PRD) |

### 3.9 Documented divergences (rule 11)

These stay different and get a comment in both keymaps plus a gate exception:

- `Ctrl+Shift+F` **Search in Files** would be the code-editor convention; the
  family follows Word (Font). QUILL's Search in Files is `Ctrl+Alt+Shift+F`.
- `Ctrl+D` Duplicate Line, `Ctrl+]`/`[` indent, `F5` date, `F3` find next,
  `Ctrl+Q` exit: rule-1 exceptions, listed there.
- `Ctrl+Alt+F1` Tutorials, `Alt+F1` Why Unavailable, `Alt+I` Document Summary,
  `Alt+Q` Ask Quill, `Alt+F8` Read All, `Ctrl+F8` Copy All, `Ctrl+.` Word
  Prediction, `Ctrl+Enter` Follow Link, `Alt+F3` Reveal Codes, `Ctrl+Shift+\`
  Match Bracket, `Alt+Shift+[`/`]` folds, `Alt+Shift+I/J/H/K` inline notes,
  table navigation on `Ctrl+Alt+Arrows`: QUILL-only, no collision with any Lite
  chord, recorded so the gate knows they are deliberate.
- QuillLite's `Ctrl+F6` walks MDI children; QUILL's walks tabs. Same key, same
  idea, different window model (5.7).

## 4. Capability parity: what crosses, and in which direction

### 4.0 The rule

**QuillLite may never be ahead of QUILL** (`CLAUDE.md`, QuillLite PRD). A
feature the small product has and the big one does not is invisible -- nobody
notices the absence of a thing they have only seen elsewhere -- so it is never
reported and the bigger product quietly becomes the worse editor. Broken
**sixteen** times (4.1), and the largest break is not in that table: QUILL
cannot change the size of its own text (4.3).

The half that was never written down: **value flows both ways.** A QUILL
capability that is editor-core, shared, worth a listener's time and switchable
off belongs in QuillLite too (4.2). When it is genuinely new it lands in QUILL
or shared core first, never in the small product first.

### 4.1 QuillLite has it, QUILL does not (rule violations; all P1)

| Capability | Where it lives today | What QUILL gets |
| --- | --- | --- |
| Numbered bookmarks (set 1..9, next/prev, list, clear, persistence) | `quill/core/numbered_bookmarks.py`, whose docstring says it lives in core *so QUILL can adopt it*; only `lite_window_marks.py` and `core/bookmarks.py` import it | a `NumberedBookmarksMixin` on `MainFrame`, storing through the same `DocumentMemory` QUILL already keeps, with the same `to_records` shape so a file's bookmarks are the same in both editors |
| Text size (view zoom) | `lite_window_view.py` | `view.text_size_up/down/reset` -- see 5.5 for the rich/plain split |
| Body Text (heading level 0) | `lite_window_headings.py` | `format.heading_0` in every kind |
| Date and Time | `insert-tools` Quillin only | a core command again (`power.insert_date_time`), so it survives Safe Mode and has a key |
| Editor Font (direct command) | `lite_window_view.py` | command that opens the font chooser and writes the editor-font settings |
| Status bar show/hide | `lite_window_status.py` + `show_status_bar` setting | `view.toggle_status_bar` + setting; the layout dialog already exists |
| File Encoding and Line Endings, one dialog, in the File menu, dirtying the document | `lite_window_tools.py` | replaces the two status-cell-only commands; must mark the document modified (7.x, the QUILL bug) and offer "UTF-8 with BOM" |
| Character Details | `lite_window_special_character.py` | command beside Describe Character |
| Paste Everything Collected / Clear the Collector | `lite_window_clipboard.py` | two commands over the existing `clipboard_collector` core |
| Copy to Tray, next empty slot -- as a *bound* command | `copy_to_next_slot` is registered in QUILL and keyless | a key (3.7) |
| Spelling Announcements (spell aloud after a delay, on navigation, suggestions) | `lite_spelling_voice_dialog.py`, `lite_check.py` | **verify** in the spelling audit (section 6) whether QUILL has the feature; if not, the engine moves to `quill/core` and QUILL gets the dialog |
| New Rich Text / New Plain Text Document | `lite_window_file.py` | two commands; QUILL's `default_new_document_format` setting already knows the kinds |
| Keyboard Shortcuts window on `Ctrl+F1`, About on `Shift+F1`, Check for Updates on `Ctrl+Alt+U` | Lite table | keys (3.7) |
| Feature profiles named after what a person wants ("Notepad", "WordPad") that also set the default document kind | `quill/core/lite/features.py` | see 5.8, the grow-up profile |
| **Editor font, font for selection, and text size** | `lite_window_view.py`, `lite_window_format.py`, `lite_window_theme.py` | the whole of 4.3 -- this is the one that is P0, not P1 |

### 4.2 QUILL has it, QuillLite should take it

The rule is one-directional about *violations* and two-directional about
*value*. QuillLite may never be ahead; that does not mean QuillLite should be
starved. A QUILL capability belongs in QuillLite when all four are true:

1. it is **editor-core** -- it acts on the text in front of you, not on a
   service, a network, a model or a companion app;
2. the engine is already **shared**, or moving it to `quill/core` is a day's
   work and makes both editors better;
3. it earns its place for somebody who listens -- it saves keystrokes, removes
   uncertainty, or says something the reader cannot;
4. it can be **switched off** in Customize Features, so "lite" stays a promise
   the user can hold the app to.

Everything below passes all four. The tiers are about confidence, not size.

#### Tier 1 -- take these; they are defects against a promise Lite already makes

| Capability | Why Lite | Cost |
| --- | --- | --- |
| Go To dialog with Line / Bookmark / Heading targets | Word's Go To (5.4); the shared dialog replaces Lite's line-only one | medium, shared |

#### Tier 2 -- take these; they are small, shared, and a listener feels them immediately

| Capability | Why Lite | Cost |
| --- | --- | --- |
| **Heading Organizer** | Lite already lists headings and moves sections; the organizer is the two combined into one list where reordering is arrow keys instead of four commands | medium; shared |
| **Extend Selection Mode**, once P1.2a has fixed it | a sticky Shift: select by navigating, no modifier held, and no "selected" from the reader on every keystroke. QuillLite deleted its own broken attempt at this (`d20fabe`) and has had nothing since; QUILL's mechanism is the one that works on wxMSW | small, after P1.2a; shared |

#### Tier 3 -- worth doing, once the P0s are out of the way

| Capability | Why Lite | Cost |
| --- | --- | --- |
| **Snippets** with a gallery | Lite has abbreviations, which are the same idea with a worse name and no list. One concept, one surface, in both | medium; shared |
| **Folding over Markdown sections** | Lite already parses heading blocks for its outline; collapsing to headings is how a listener skims a long document without a mouse | medium |
| **Print preview** (Print Studio's accessible pagination, not a picture) | PR2; the `print_pagination` core is already shared and wx-free | small |
| **A single-instance check in QUILL** and `--rich` / `--plain` | A6/A7 -- this one goes the other way: Lite's is better and QUILL should take it | small |
| **`EM_FORMATRANGE` formatted printing** | PR3, in the shared rich surface, so both editors gain it at once | medium |

#### Explicitly **not** going to Lite, so nobody proposes them again

Tabs, AI, speech, dictation, read aloud, preview, Quillins, remote/GitHub/git,
vault, sticky and inline notes, table and CSV studio, compare, word prediction,
match bracket (declined in its PRD), thesaurus (needs an asset download), key
describer, the leader chord, Quill Eraser (a redaction tool is a promise about
data that a Notepad-scale product should not be making), Open from URL (a text
editor that reaches the network is a different product), Go To Page (there is
no pagination model in Lite), and citations, equations and footnotes.

#### Magical, and therefore for QUILL first

Ideas that would delight in either editor. Each lands in QUILL first or in
shared core simultaneously, because QuillLite may never be the one that has it:

| Idea | What it does | Where |
| --- | --- | --- |
| **"What changed?"** | one key, one sentence: how the file on disk differs from the buffer -- "Disk version has 3 more lines; first difference on line 41". QUILL has compare and a (broken) external-change watcher (F5); joining them answers the question the watcher currently asks badly. Lite gets the same sentence with no diff UI at all | QUILL first; shared `core/compare` |
| **A spoken undo** | `Ctrl+Z` says what it undid ("Undid: typed 14 characters", "Undid: Sort Lines"), not just a tone. wx gives no undo labels, so this needs an edit journal in the shared `DocumentText` (V4) -- which is being built anyway | shared, after V4 |
| **Say what the last command did, again** | one key that repeats the last announcement verbatim, because the reader interrupted it. Every screen-reader user has wanted this in every app | shared; `announcements` already keeps a log in QUILL |
| **Structure on arrival** | after opening a file, one sentence: "Markdown, 412 lines, 9 headings, longest line 180 characters". Both editors compute all four already for the status bar | shared `metrics`; both |


### 4.3 What neither editor has, that Microsoft's three do

Recorded so the omissions are decisions rather than oversights:

| Capability | Where it exists | Decision |
| --- | --- | --- |
| Drag a file onto the window to open it | Notepad, WordPad, Word | **Neither app has a `wx.FileDropTarget` anywhere.** Low value for the audience, real value for a sighted colleague sitting down at the machine. P3, both. |
| Formatted printing | WordPad, Word | Neither prints formatting. Lite at least prefixes `[H2]` to headings (`lite_printing.py:145-162`); QUILL prints a rich document as flat text with no structural marker at all, so QUILL is *behind* Lite on paper. The real fix is RichEdit's `EM_FORMATRANGE` in the shared surface, which makes both genuine. P2. |
| Print preview | WordPad, Word | QUILL has Print Studio, which is the accessible equivalent and is better than a picture of a page. Lite has nothing -- its page setup persists as of 2026-09-16, but there is still no way to see the pagination. P3.6 for Lite, via the shared `print_pagination` core. |
| A ruler and tab stops | WordPad, Word | Declined in both. Nothing a listener can use. |
| Insert Object / Picture | WordPad, Word | Declined in Lite. QUILL has Insert Image for Markdown/HTML. No change. |
| Styles (named, applied, redefined) | Word | QUILL has Style Headings and the heading ladder; a full style sheet is out of scope for both. Recorded. |
| "Set as default font" | WordPad | Follows 4.3 -- once an editor font exists, it is a setting, which *is* the default. |

### 4.5 The menu bar, against Word's

Word 2003, the last menu-bar Word and the shape every later product still
echoes, is nine menus: File, Edit, View, Insert, Format, Tools, Table, Window,
Help. QuillLite is nine: File, Edit, View, Insert, Format, Navigate, Tools,
Window, Help -- Word's, with Navigate where Table was, which is right for an
editor with no tables and a listener who navigates constantly.

QUILL is up to **thirteen**: File, Edit, View, Insert, Format, Navigate,
**Search**, Tools, **AI**, **Audio Description Project**, Window,
**QuillVille**, Help. Each extra menu is a stop on every Alt-arrow sweep.

| # | Finding | Evidence |
| --- | --- | --- |
| M1 | **"Search" is a top-level menu with two items** -- Search in Files, Replace Across Files -- while Find, Replace, Find Next, Find Previous and Find All live in Edit. Word has no Search menu. Fold both items into Edit (or Tools) and delete the menu. | `main_frame_menu.py:736-740, 3408` |
| M2 | **The Format menu never says "Font"**. Its only font item is "&More Font Options...", which refuses outside Markdown. WordPad and Notepad both have Format > Font; Word has it on `Ctrl+Shift+F`. See 4.3. | `main_frame_format_codes.py:136` |
| M3 | **Format has no alignment except Justify**, no Bullets, no Line Spacing. Lite has all four alignments, Bullets and a Line Spacing submenu, on Word's keys. QUILL's Format instead offers Sort and Filter, Whitespace, HTML and Encoding -- tools, in the menu where Word puts appearance. | `main_frame_menu.py:1121-1327` |
| M4 | **Go To is not in Edit.** Word and Notepad both put Go To in Edit on `Ctrl+G`; Lite does too. QUILL has Go To Line and Go To Page under Navigate only. | `main_frame_menu.py:882-886`; Lite `&Edit` row `cmd_goto_line` |
| M5 | **View says "Toggle Soft Wrap"**. Notepad, WordPad, Word and Lite all say "Word Wrap". The command id `view.toggle_soft_wrap` can stay; the label a listener hears should be the label they know. | `main_frame_menu.py:782` |
| M6 | **Eight submenus stand between Open and Save in the File menu** (Open Recent, Favorite Folders, Open over SSH, Open from Remote, Snapshots, Publish, Import, Export) plus Notebook further down. Word's File has one submenu. Everything after Publish is a candidate for Tools or the QuillLite-profile's "off". | `main_frame_menu.py:158-478` |
| M7 | **Edit has no Delete and no Paste Special row.** Notepad, WordPad, Word and Lite all offer Delete; Word offers Paste Special. QUILL binds `Ctrl+Shift+V` to Preview instead of Paste Text Only (3.2) and never shows the plain-paste verb in Edit at all. | `main_frame_menu.py:539-617` |
| M8 | **Help > Open User Guide carries a literal `	Ctrl+F1` accelerator** outside the keymap -- invisible to the reference, unrebindable, and a silent double claim once `Ctrl+F1` becomes the family's Keyboard Shortcuts key (3.7). Same finding as H4; repeated here because it is a menu defect, not only a keymap one. | `main_frame_menu.py:3331` |

The QuillLite profile (5.8) is where most of this lands for QUILL: nine menus,
Word's order, Lite's items. M1, M2, M4, M5 and M7 should be fixed for
**every** profile, because they are wrong in all of them.

## 5. Target models

The decision only. The arguments that produced these are in git history.

**5.1 Copy tray.** Copy to next empty slot (`Ctrl+Alt+Y`) and Paste from Tray
chooser (`Ctrl+Alt+V`) in both; **Copy to Tray Slot...** (`Alt+Shift+Y`) as a
previewing chooser in both, with QUILL keeping its twelve leader chords as the
fast path. A full tray refuses and names the problem (QUILL's model), Recent
Clips pastes on Enter (Lite's), Restore Deleted Text offers the last three
(QUILL's) in Lite's wording, paste in a plain document is plain (Lite's), and
the collector is a buffer rather than a mode (Lite's) with QUILL's system-wide
watcher kept as an optional *source* for it.

**5.2 Bookmarks.** Nine numbered slots, per file, plus a list whose rows begin
with the digit so "3, Enter" needs no extra chord. QUILL keeps its named vault
as the writing environment's extra, under the same list. Positions survive
edits by snippet re-anchoring (QUILL's `BookmarkAnchor` moved under the shared
`BookmarkSet`), not by Lite's length-delta guess, and every change is written
at once.

**5.3 Selection.** The six structural commands on Lite's six chords; `Ctrl+Space`
means *sentence* in both; `Ctrl+Alt+F8` is the F8-marker toggle in both. One
announcement shape in core: scope, then words, and the line range only when F8
completes. Marks on the shared `MarkRing`, clamped on pop, with every jump
going through one recording seam so `Alt+Left` undoes it.

**5.3a Extend Selection Mode and Select Chunk are kept, not retired.** The
first pass called QUILL's extend mode "the live-extend design Lite deleted". It
is not: Lite's deleted design stretched a selection on every navigation
key-**up**, where QUILL's intercepts the key *before* the control, moves the
caret itself, and collapses the selection after each move so the control never
has one to fight. It is a **sticky Shift** -- select by navigating, no modifier
held, and no "selected" from the reader on every press. Four fixable bugs, none
architectural: an O(N) line-start rescan per keystroke, PgUp/PgDn hardcoded to
ten lines, Up/Down by logical line so soft wrap breaks it, and word movement
stopping only at whitespace. It takes `Ctrl+Alt+Shift+F8` in both (P1.2a), then
becomes a Tier 2 candidate for QuillLite, which has had nothing since it
deleted its own. **Select Chunk** duplicates Select Word on words (both use
`\w`) and is the only way to select a run of punctuation or whitespace, so it
keeps its behaviour, loses `Ctrl+Space`, and is renamed **Select Token**.

**5.4 Go To.** `Ctrl+G` opens one dialog with a target kind -- Line, Page (QUILL
only), Bookmark, Heading. `Ctrl+Alt+Shift+A` stays the fuzzy Go To Anything in
both, and `quick_nav` merges into it.

**5.5 Text size.** In plain, Markdown and HTML the keys change the editor font
size; in rich they change **view zoom** (`RichEditDocument.set_zoom`, already
shared and used by nothing), because run point sizes *are* the heading ladder.
Grow/Shrink Font (`Ctrl+Shift+>`/`<`) stay the document change, once the ladder
gains the H5 and H6 sizes it is missing (R7).

**5.6 Status bar.** `F6` lands in the status bar first in both, `Shift+F6` walks
back, Escape returns to the document, `Alt+Shift+B` hides and shows the whole
bar. QUILL keeps its per-cell layout dialog and speak-summary chord. Note
QUILL's `status_bar_hidden` is a list of hidden *cells*, not a switch for the
bar -- it needs both (G3).

**5.7 Window model.** Lite is MDI, QUILL is tabs. Both number documents
(`Alt+1..9`), both walk with `Ctrl+Tab` and Word's `Ctrl+F6`. `Ctrl+W` closes
the document, `Alt+F4` the window, `Ctrl+Q` exits. Divergent by design.

**5.8 The QuillLite profile in QUILL.** A QUILL feature profile that shows
Lite's nine menus in Lite's order with Lite's items and nothing else -- AI,
companions, Quillins and the leader depth off, not hidden -- carries
`default_new_document_format` the way Lite's WordPad/Notepad profiles carry
`default_mode`, and offers **Bring my QuillLite settings** on first activation
(settings, keymap overrides, abbreviations, personal dictionary, copy tray,
clip library, collector, per-file bookmarks -- all already sharing on-disk
shapes). Needs the settings-name reconciliation in G1.

**5.9 Reclaiming the leader chord.** Fifty-eight of sixty-two positions are
taken and twenty-one are GitHub, remote-file and local-git administration.
Nobody presses a chord to rename a repository. Those retire to their menus and
the palette, freeing what section 3's relocations need (favourite folders,
Insert Table, intake report). Media transport stays on the leader digits:
listening while writing is a real use.

## 6. Bugs found in the family audit

**Twelve** feature families now. Seven were read on 2026-09-15 by parallel
audits (6.1-6.7); five more were added on 2026-09-16 by direct reading
(6.8-6.12: typing, large documents, printing, settings, and
startup/shell/announcements). Every row cites the evidence. Severity is the
section-0 scale. The rows rated **Broken** are P0.7, P0.8 and the three
viability items P0.6a-c; the rest are P1 where a section-3 or 4 item already
covers them, and P2.8 otherwise.

The five new families are where the *viability* findings live, and they are
lopsided in a way the first seven were not: 6.8-6.9 are almost entirely
QuillLite paying for work QUILL already did, and 6.10-6.12 are almost entirely
QUILL missing things the small product got right. Neither editor is ahead
overall; each is ahead where it spent its attention.

### 6.1 Spelling

Engine: one and shared (`quill.core.spellcheck`, `quill.core.spelling.*`, `SpellingReviewDialog`).

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| S4 | Worse | both | **Word boundaries are ASCII in the tokenizer and Unicode in the walk-left**: `cafe` with an accent is flagged as `caf`, `naive` with a diaeresis as `na` and `ve`, `dogs'` keeps its apostrophe, and a curly apostrophe splits `don't`. The same word is silent on one path and flagged on another. | `spellcheck.py:67, 514-520, 574-575`; `spelling/voicing.py:103-118` already expects the token the tokenizer cannot produce |
| S5 | Worse | both | **The caret just past a word is "no word"**: `misspelling_at_position` needs `start <= pos < end`, and the caret sits at `end` right after typing. The context menus retry at `pos - 1`, and so does Add Word via `_word_at_caret_for_spelling`; the other four keyboard commands do not. | `spellcheck.py:566`; `lite_window_spelling.py:391-396, 500-505`; `main_frame_spellcheck.py:513-522` |

**S11 is the one contested row in this plan.** QUILL's
`_on_editor_context_menu` carries a seven-line comment explaining why
corrections are first and not in a submenu: "a sighted user finds a misspelling
by looking for a red squiggle and right-clicks it, and a screen-reader user has
no squiggle. The Applications key is their squiggle -- so the first Down arrow
has to land on the correction itself" (`main_frame.py:3382-3389`). That is a
better reason than "the menu is always the same length", and it was written by
somebody thinking about the same listener. Resolve it with the person who asked
for the submenu on 2026-09-13 rather than by fiat: the likely answer is
corrections first *and* a fixed tail, which satisfies both arguments.


### 6.2 Selection, marks and bookmarks

Engine: shared (`quill/core/selection.py`, `marks.py`, `locations.py`, `bookmarks.py`, `numbered_bookmarks.py`); the F8 state machine is duplicated by design.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| L3 | Worse | QUILL | **Shrink pops a stack that is never cleared**: expand, arrow away, select something else, Shrink jumps to the old span; the stack can hold an empty pair, so Shrink collapses the selection and announces "Shrank selection". Lite computes shrink every time. | `main_frame_selection.py:89-93, 121-127` |
| L7 | Worse | QUILL | **List Bookmarks shows stale positions**: jumps re-anchor by snippet but the list prints the raw stored offset, and the resolved offset is written back without saving, so tab and disk keep the old value until the next Set. | `main_frame.py:11533-11549, 11607-11610` |


### 6.3 Files, saving and recovery

Engines duplicated: `quill/io/text.py` vs `quill/core/lite/textfile.py`; `core/recovery.py` vs `core/lite/recovery.py`; `core/backups.py` and `core/restore_points.py` vs `core/lite/backups.py`.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| F4 | Broken | QUILL | **Save As HTML and Save As Plain Text are not atomic and force UTF-8**, discarding the read encoding and BOM; rich-mode `.md`/`.html` saves ignore `document.encoding` and `line_ending` (always UTF-8, LF); the remote save copy is a plain `write_text`. Every other document writer is atomic. | `quill/io/export.py:245-252`, `main_frame_rich_mode.py:170-187`, `main_frame.py:8521` |
| F5 | Broken | QUILL | **The external-change watcher auto-reloads a clean tab of any suffix with `path.read_text()`**: a `.docx`/`.rtf`/`.pdf`/`.epub` tab rewritten by Word is replaced with binary decoded as replacement characters and marked clean. The "Open Disk Version in New Tab" button selects the existing tab instead of opening a second one, so the compare it promises never happens. | `main_frame.py:3137-3230, 6870-6876` |
| F6 | Broken | QUILL | **Encoding and line-ending changes do not dirty the document**, so Close does not prompt and the change is lost unless `Ctrl+S` is pressed; the two commands are in no menu (status-cell or palette only); the chooser has no "UTF-8 with BOM" although `encoding_tools.ENCODING_CHOICES` has the label; **UTF-16 is never detected on open** (decodes as cp1252 NUL garbage). Lite detects UTF-16, offers BOM, dirties, and has a menu item. | `main_frame.py:7581-7612`, `quill/io/text.py:44-96`, `core/lite/textfile.py:45-50, 85-93` |
| F7 | Worse | Lite | **Half fixed 2026-09-16**: Earlier Versions now says a rich restore keeps the words and loses the formatting, and File Encoding and Line Endings is refused in rich mode rather than lying about a change `_write_rtf` never reads. What is left is the status bar, whose Encoding and Line Endings cells still read "UTF-8 / CRLF" for every `.rtf` -- they should read the document's own format instead. | `lite_window_status.py:390-391` |
| F8 | Worse | Lite | "No Markdown could be made from this HTML; saved unchanged" and "Converted HTML to Markdown" are spoken *before* the save runs. A classic-Mac CR file opens the format dialog with CRLF preselected, so OK silently converts it. UTF-16 big-endian round-trips as little-endian on a no-edit save, against the module's own byte-honesty contract. | `lite_window_markup.py:229, 243`, `lite_dialogs.py:331, 350-355`, `core/lite/textfile.py:87-88, 107` |
| F10 | Worse | QUILL | `save_all_files` never restores the active tab; `save_file` relies on `EVT_TEXT` having synced the document (Save As syncs explicitly); the OS session-end handler is bound on the frame while wx delivers the event to the App, so a logoff with dirty documents never prompts. | `main_frame.py:7915-7923, 7840-7913, 3860-4046` |
| F11 | Worse | both | New documents default to **LF** in QUILL and **CRLF** in Lite; Notepad, WordPad and Word all write CRLF. No setting exposes it in either. | `quill/core/document.py:9-13`, `lite_window.py:139-140` |
| F12 | Worse | both | Close prompt wording differs and both use Yes/No: Lite "Save changes to notes.txt?", QUILL "You have unsaved changes. Save before Close?". Notepad and Word name the file and label the buttons Save / Don't Save / Cancel, which a listener does not have to hold a question in memory to answer. | `lite_window.py:428-441`, `main_frame.py:6020-6047` |
| F14 | Divergent | both | Lite restores every crash slot as a window without asking (one spoken line after); QUILL shows a recovery dialog. Word's Document Recovery lets the user choose. Lite session restore is automatic (Notepad 11 behaviour); QUILL has only manual, keyless Snapshots. Neither detects a read-only file at open. | `lite.py:195-198, 254-259`, `main_frame.py:4373` |


### 6.4 Formatting and document kinds

Rich engine shared (`richedit_editing.py`, `richedit_rtf_surface.py`, `heading_ladder.py`, `heading_levels.py`, `markdown_sections.py`, `structure_announce.py`); the wrappers are duplicated.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| R4 | Broken | QUILL | **Dark mode may write grey text into every saved `.rtf`**: `_apply_theme` calls `SetForegroundColour` on the rich control (wxMSW applies it as `SCF_ALL` character colour) and nothing resets to `tomAutoColor` before the native save. Lite guards both directions. Verify live before fixing. | `main_frame.py:4632-4636`, `main_frame_rich_mode.py:110`, `lite_window_theme.py:9-15`, `lite_window_file.py:194, 213` |
| R8 | Worse | QUILL | Rich `Ctrl+B/I/U` announce the verb ("Bold") with no state; the shared `toggle_font_attr` returns the state and Lite says "Bold on / Bold off". | `main_frame_rich_mode.py:377-399`, `richedit_editing.py:285-297` |
| R9 | Worse | both | **Native RichEdit hotkeys leak into plain and Markdown documents** because plain documents are `TM_RICHTEXT` controls: in QUILL unbound `Ctrl+U`, `Ctrl+L`, `Ctrl+R` underline or re-align a Markdown buffer natively (not dirty, not announced, not saved, but visible and undo-stacked); in Lite every native chord it does not bind (`Ctrl+Shift+=` superscript and friends) does the same. Paste is guarded; keys are not. | `main_frame.py:2052-2068`, `richedit_editing.py:243-254`, `lite_window_commands.py:223-236` |
| R11 | Worse | QUILL | Choosing "Convert to Rich Text" in the plain-text formatting prompt converts and then **drops the Bold that was asked for**. | `main_frame_rich_mode.py:463-482`, `main_frame.py:16161-16163` |
| R12 | Worse | QUILL | Outline Navigator and Quick Nav are text-only: an `.rtf`/`.docx` tab is "plain" so "Outline is not available"; `all_headings()` on the shared surface is called only by Lite. `next_structure` (`Alt+Down`) is blind in rich mode. | `main_frame.py:10176-10228, 10850, 11000-11002`, `richedit_editing.py:348` |
| R14 | Worse | both | `set_heading` assigns `font.Size` then `font.Bold` as two TOM assignments with no edit collection: one `Ctrl+Z` after "Heading 2" likely leaves a 16-point non-bold paragraph nothing recognises as a heading. Same shape in Lite's selection font dialog. Verify live. | `richedit_rtf_surface.py:430-461`, `lite_window_format.py:325-326` |


### 6.5 Shell: status bar, windows, help, features

Shared: the palette, Go To Anything, the support dialog, the F1 dialog and `app_features`. Duplicated: the status bars, keymap editors, feature models and F1 resolvers.

The disputed fact first: QUILL's status bar **is** a row of focusable button cells that `F6` reaches as one of up to five regions (Editor, Reveal Codes, Document Tabs, Preview, Status Bar), with arrows, Enter, Escape; the spoken summary on the leader chord is an extra. What QUILL lacks is a whole-bar show/hide. The first-pass finding is corrected in 5.6.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| H3 | Worse | QUILL | **GATE-13 over-announce in the status bar**: every cell focus, including each arrow press, announces "label, value" although the button already carries the name and label, so each press is spoken twice; leaving the bar announces "Returned to editor", which is a focus move the reader already speaks. The gate cannot see it (lambda-bound handler, announce one call deeper). Lite deliberately does neither. | `main_frame_statusbar.py:628-631, 757-776, 800-802`, `lite_window_status.py:469-483, 519` |
| H5 | Worse | QUILL | Mnemonic collisions inside Tools > Customize and Support (`&Export...` three times, `&Import...` twice); the access-key test checks only top-level titles. | `main_frame_menu.py:3254-3262`, `test_menu_bar_access_keys.py:82-104` |


### 6.6 Clipboard family

Engines shared (`copy_tray.py`, `clip_library.py`, `clipboard_collector.py`, `deletion_ring.py`); everything a person touches is duplicated per app.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| C2 | Broken | QUILL | **Tray paste, Restore Deleted Text, Duplicate Selection and the collector rewrite the whole document** for a local insert (`_replace_document_text` = select all + `WriteText` of plain text) with no rich-mode guard. On the RichEdit surface that is every heading, bold and font run replaced by the format at position 0 in exchange for one pasted line. Lite inserts locally. **Verify live in an `.rtf`**; if confirmed it is data loss with one `Ctrl+Z` as the cure. The same helper serves every QUILL line and case tool (6.7). | `main_frame_copy_tray.py:235, 319`, `main_frame_power_tools.py:97-108, 449`, `main_frame_line_commands.py:187`, `main_frame.py:17393-17398` |
| C3 | Worse | QUILL | **The Copy Tray dialog destroys labels and pins on edit**: `CopyTray.copy_to` builds a fresh slot (no label, unpinned) and every write path uses it; editing a slot's text drops its label and its pin; Copy to Tray Slot and promoting a clip overwrite a pinned slot without a word. A pin protects only an *empty* slot from Copy to Next Empty. | `core/copy_tray.py:50-57, 97-102`, `copy_tray_dialog.py:186-189, 238-251`, `main_frame_copy_tray.py:156`, `main_frame_clip_library.py:369` |
| C4 | Worse | QUILL | **The clipboard collector saves the file unasked and speaks twice**: every collected clip appends to the document, moves the caret to the end, calls `save_file()` whenever the document has a path (from a 750 ms poll), so "Saved name" and "Collected clipboard text" are spoken per copy in any program. Read-only, empty-clipboard and already-collected refusals are silent. | `main_frame_power_tools.py:397-408, 436-456`, `main_frame.py:7892` |
| C5 | Worse | QUILL | **Single-press tray paste is delayed by the multi-press window** (400 ms): characters typed inside it land before the pasted text; nothing says so. | `main_frame_copy_tray.py:143, 187-205` |
| C6 | Worse | both | **The two editors document opposite facts about `Replace` and undo**: QUILL's `_atomic_replace` (#131) says wx `Replace` records two undo entries and avoids it; Lite's `_insert` and `_apply_line_op` promise one undo step and use `Replace`; QUILL's own Paste Text Only uses `Replace` over a selection. No test settles it; in at least one app `Ctrl+Z` after Paste Text Only lands on an intermediate state. | `main_frame.py:17349-17359`, `lite_window_clipboard.py:92-102`, `lite_window_lines.py:24-27, 72-74`, `main_frame_rich_paragraph.py:175-179` |
| C8 | Worse | QUILL | GATE-13: the Copy Tray dialog announces "Slot N loaded" on every list move. Keep Clip, Copy All, Copy with Source, Restore Deleted Text, Duplicate Selection and every collector message report through `_set_status`, which is throttled and bypasses the verbosity/braille service, so none reach braille or the announcement log. `_copy_to_clipboard` has no retry and no `try` around `SetData`; a locked clipboard raises past the handler. `read_clipboard_text` shows wx's own error dialog on its last retry and is called from the collector timer and from the tray dialog's selection handler, so a modal can appear from a timer or a list move. Open Clip Library bypasses `_show_modal_dialog`. | `copy_tray_dialog.py:174, 208, 218-225`, `main_frame_clip_library.py:296-298, 346`, `main_frame.py:19489-19498`, `clipboard_retry.py:80-81` |
| C9 | Divergent | both | **QuillLite's three halves landed 2026-09-16**: a full tray refuses and names both ways out, Restore Deleted Text offers the ring's three with a preview of each, and clearing the tray asks *and* counts. What is left is QUILL's side of the same four: its tray refusal is fine, its Restore list is fine, its Clear must gain the count, and its Recent Clips dialog must paste on Enter rather than copying to the system clipboard and expecting a second `Ctrl+V` (**Lite's**). Paste in a plain document: Lite makes `Ctrl+V` plain there; QUILL pastes whatever the control accepts (**Lite's**). Collector: QUILL is a mode where the document is the collector; Lite is a buffer filled by an explicit key and pasted where the caret is (**Lite's** for a listener: the caret never moves and nothing is written unasked; keep QUILL's system-wide watcher as a *source* for the buffer). Magic Paste's keymap comment says it "moves to QUILL key, V"; no handler references it and it is menu-only. | `copy_tray.py:155-175`, `classic_editor.py:80-118`, `lite_window_lines.py:171-186`, `clip_library_dialog.py:194-202`, `lite_window_clipboard.py:194-211, 254-279`, `lite_window_commands.py:223-236`, `keymap.py:621-623` |


### 6.7 Lines, case and whitespace

Engines shared (`quill/core/line_ops.py`, `format_ops.py`, `transforms.py`); the wiring is duplicated.

The seventh family audit was cut short by a rate limit; these are the findings from a direct read of the three QUILL helpers and Lite's one.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| N1 | Worse | QUILL | **Three helpers, three scopes.** With no selection, `_apply_text_block_operation` (sort, reverse, dedupe, trim, tidy, quote, indentation) acts on the **current line**, so Sort Lines with no selection sorts one line and announces "Sorted lines ascending"; `_power_tools_transform_selection_or_document` (trim blank, remove blank, keep unique, numeric/length/date sorts, shuffle) and `_transform_selection_or_document` (case) act on the **whole document**. Lite's one helper always means "selection, else whole document" and warns before a whole-document rewrite in rich text. | `main_frame.py:17439-17462, 16175-16188`, `main_frame_power_tools.py:110-123`, `lite_window_tools.py:62-122` |
| N2 | Worse | QUILL | **No no-op detection and no counts**: every QUILL line tool announces its past-tense status even when nothing changed; Lite says "No lines to change" and otherwise "Sorted 12 lines" / "Removed 2 lines" with the count chosen per verb. | same |
| N3 | Worse | QUILL | All three helpers write through `_replace_document_text` (select all + `WriteText`), the same path as C2: rich formatting at risk, and the whole document replaced for a one-line change. Lite uses one `Replace` on the changed span. | `main_frame.py:17393-17398, 17459`, `lite_window_tools.py:102` |
| N4 | Worse | QUILL | **The same verb is registered twice with different words**: `power.keep_unique_lines` ("Kept unique lines (removed duplicates)", `Alt+Shift+K`) and `edit.remove_duplicate_lines` ("Removed duplicate lines", no key) both call `format_ops.remove_duplicate_lines`. `power.trim_blank_lines` (two ends only, `Ctrl+Shift+Enter`) and `power.remove_blank_lines` (every blank line, no key) are two commands whose names a listener cannot tell apart; Lite's "Remove Every Blank Line" is the second one. The `line-tools` Quillin ships Duplicate Line, Delete Line and Move Line Up/Down a third time. | `main_frame_power_tools.py:1477-1487, 1519-1523`, `keymap.py:582-583`, `quill/quillins_bundled/line-tools/manifest.json` |

**Parity:** the engines are one and the same in both editors; the differences are in scope, wording and the write path. QUILL-only extras (numeric/length/date sort, shuffle, delete lines containing, indentation conversion, hard wrap) are fine as extras once they share the one helper.

### 6.8 Typing and input

Engines shared (`quill.core.autoformat`, `quill.core.abbreviations`); the
wiring, the gating and the defaults are all duplicated.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| T3 | Worse | both | **Tab means the opposite thing by default**: QUILL `_tab_inserts_literal = False` (Tab indents), Lite `= True` (Tab inserts a tab character). Both status bars then say "Indent" or "Tab char" for the same cell, so each bar is honest and the defaults still disagree. Notepad inserts a tab; Word indents. Rule 1 gives it to the document kind: a tab character in plain and code kinds, an indent in rich -- decided once, in core. | `main_frame.py:1311`, `lite_window_typing.py:91`, `main_frame_statusbar.py:257`, `lite_window_status.py:386` |

### 6.9 Large documents (the QuillLite viability bar)

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| V4 | Worse | both | **Neither editor's document model is incremental.** QUILL's mirror makes reads free but every edit still re-sets a whole string; Lite has no mirror at all. The shared fix is one `DocumentText` object in core, owned by both editors, holding the Python string, bumping a revision, answering `line_column_for_position` and `stats` from a cache, and being the only thing display code may read. That one object retires V1-V3, S8 and half of 6.7's write-path problems. | -- |

The acceptance test for this family is a number, not a feeling: open a 50 MB
`.log` in both editors, hold Down for five seconds, and measure. Lite must not
be more than 20% slower than QUILL, and neither may exceed one status refresh
per 250 ms.

### 6.10 Printing

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |

### 6.11 Settings, profiles and the grow-up path

Measured: `quill.core.settings.Settings` has **341** fields;
`quill.core.lite.settings.Settings` has **38**. Twenty-two names are shared.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| G4 | Worse | QUILL | **No session restore.** Lite has `restore_session` and `session_files` and reopens last session's documents unless files were named on the command line (Notepad 11's behaviour). QUILL has manual, keyless Snapshots only (F14). | `lite.py:185-186, 228-252` |

### 6.12 Startup, shell integration and announcements

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| A7 | Divergent | both | Command lines differ in shape: Lite hand-parses four flags plus paths and prints its own usage; QUILL uses `argparse` with fourteen options. Harmless, but `--rich`/`--plain` are worth adopting in QUILL alongside `default_new_document_format`. | as above |

## 7. Architecture findings

### 7.1 One verb, three registrations

QUILL registers the same editing verbs in up to three places: the command
registry (`main_frame_commands.py`), the power-tools manifest
(`main_frame_power_tools_menu.py`), and bundled Quillins (`line-tools` ships
Duplicate Line, Delete Line, Move Line Up/Down a second time; `text-tools`
ships Number Lines; `insert-tools` owns Date and Time outright). Lite has one
table. Each duplicate is a place for behaviour and wording to drift, and the
audit found pairs that already have (`keep_unique_lines` vs
`remove_duplicate_lines`, `blockquote` vs `quote_lines`, `trim_blank_lines` vs
Lite's Remove Every Blank Line). Golden: one command id per verb; a Quillin may
*add* a verb but never re-ship one the core has.

### 7.2 Keys outside the keymap

Rich-mode `Ctrl+B/I/U` are still bound by key code in `_on_editor_char_hook`,
for the good reason that the native RichEdit would otherwise eat them silently
-- and with the bad consequence that they are a second binding the keymap
cannot see or change. `_run_chord_through_registry` exists now, so the change
is three lines (P1).

### 7.3 Keymap profile snapshots

`quill/core/keymap/profile_default.json` and `profile_sr_friendly.json` are
full snapshots (184 and 168 entries) and already disagree with `DEFAULT_KEYMAP`
on 29 commands. Every move in section 3 must be applied to them too, or
generated from `DEFAULT_KEYMAP` plus a delta -- the same shape the user file
uses. Prefer the delta.

### 7.4 Quillin hotkeys collide with the core

`markdown-helpers` binds `ext.mdh.bold` to `Ctrl+Shift+B`, which is
`edit.select_block` in QUILL today and Set Bookmark after this plan. No gate
checks a Quillin's `hotkeys` against `DEFAULT_KEYMAP`.

### 7.5 The parity gate does not exist

`tests/unit/core/test_keymap.py::test_the_two_editors_agree_about_the_home_row_pair`
checks two chords. Everything else in section 3 accumulated unobserved.

### 7.6 Documentation drift

- QuillLite PRD 2.2 records `Ctrl+Alt+J`/`Ctrl+Alt+V` as deliberate
  divergences; this plan reverses both, so the paragraph goes.
- PRD 3.2 says the command palette is dropped; 3.1 and the table keep it.
- PRD 8.1 lists as "accepted for a later release" a dozen things the command
  table shows shipped (overwrite mode, tab mode, line operations, deletion
  ring, persistent bookmarks, back/forward, Earlier Versions, promote/demote,
  sentence/toggle case, reverse, number lines).
- The first-pass audit's own intro said Lite reads `.txt` and `.rtf` only; it
  has four kinds (plain, Markdown, HTML, rich).
- QUILL's generated keyboard reference is regenerated by
  `quill/tools/build_keymap_reference.py` and gated; Lite's user guide key
  tables are hand-written and gated by nothing.

### 7.7 Two vocabularies for one product family

The same concept is spelled two ways in eight settings (G1), the same verb is
registered under two names inside QUILL alone (N4), the same status cell is
described in two wordings (T3), and the same announcement has two shapes (L14).
None of these is a bug on its own; together they are the mechanism by which the
two editors drift, because there is no place where a name is decided once. The
cure is not a rename pass -- it is that every *new* shared concept lands in
`quill/core` with one name, and that the parity gate (section 9) compares
resolved behaviour rather than trusting that two identifiers that look alike
mean the same thing.

### 7.8 The document string has no owner

Both editors keep the document's text in a wx control and read it back with
`GetValue()` -- QUILL 175 times, QuillLite 54 -- and QUILL has since grown a
private mirror (`_document_text_for_display`) plus a revision-keyed stats cache
to stop paying for it, which QuillLite has not. Every performance finding in
6.9, the spelling scan in S8, and the whole-document rewrite in C2/N3 are the
same missing object: nobody owns the text. `DocumentText` (P0.6c) is the fix,
and it belongs in `quill/core` where both editors and the tests can reach it
without a display.

## 8. The prioritised list

Cost: **T** trivial (a keymap line), **S** small (a day), **M** medium (a
week), **L** large. Order within a tier is the order to do them. Every item
names the test that says it is finished.

The tiers answer different questions, and that is why they are ordered this
way:

- **P0** -- the app loses work, corrupts a file, or cannot do the job it is
  for. Viability.
- **P1** -- a person's hands do the wrong thing, or a capability exists in one
  editor and not the other. Parity.
- **P2** -- the two editors behave differently where one of them is better.
  Model alignment, and the value that crosses from QUILL into Lite.
- **P3** -- polish, documentation, and the long tail.

### P0 -- data loss, corruption, and the three viability bars

| # | Item | Editors | Cost | Done when |
| --- | --- | --- | --- | --- |
| **P0.6c** | **QUILL adopts `DocumentText`** (V4). The object exists (`quill/core/document_text.py`) and QuillLite is on it: the mirror, the revision counter, the cached stats and line table, and the rule that display code reads it and never the control. QUILL still has its own half-answer -- `document.text` plus a stats cache in `main_frame_statusbar.py` -- and should move onto the shared object, which is what makes the edit journal the spoken undo needs (P3.7) possible at all | QUILL | M | one mirror, owned by core, read by both |
| P0.7 | The remaining **Broken** rows of section 6, each with a regression test, and all three are QUILL's: **F4** non-atomic Save As HTML / Plain Text; **F5** the watcher replaces a `.docx` tab with decoded binary; **F6** an encoding change does not dirty, UTF-16 undetected. (R2, R3, S2, S3 landed 2026-09-16; F1, F2, F3, F9, R6 landed 2026-09-17.) | QUILL | S each | regression test per bug |
| P0.8 | **Verify live, then fix if confirmed**: R4 dark mode writing grey text into every saved `.rtf`; C2/N3 QUILL whole-document rewrite for a local insert or line tool in an `.rtf`; R14 two-step undo after Heading N. (R5 was confirmed by reading and fixed 2026-09-16. L13 was settled by reading on 2026-09-17: wx leaves the caret at the *to* end of a selection, so `SetInsertionPoint(start)` then `SetSelection(start, end)` cannot work whatever the platform does -- `SetSelection(end, start)` is the fix, and the test fake now models the direction so it cannot come back.) | QUILL | S each | a rich document survives each with its runs intact |
| P0.9 | `_run_command` reports the exception class and message, not "Command failed"; `save_file` handles `UnicodeEncodeError` and `UnsupportedSaveFormatError` with the same sentences as `OSError`; Lite stops `errors="replace"` | both | S | a cp1252 document that gains an emoji says so on `Ctrl+S` in both |

### P1 -- parity violations and the rest of the family keymap

| # | Item | Editors | Cost | Done when |
| --- | --- | --- | --- | --- |
| P1.1 | Bind the keyless QUILL commands **still waiting on a displacement**: Sort Z-A (`Ctrl+Alt+Shift+S` in Lite, `tools.ai_spell_check` here), Tidy Whitespace (`Ctrl+Alt+Shift+T` / `ai_translate_selection`), Keyboard Manager (`Ctrl+Alt+Shift+R` / `file.remove_favorite_folder`), lowercase (`Ctrl+Shift+K` / `edit.unquote_lines`), Earlier Versions, Sound Scheme, Markdown Tag. Every one of the first four wants a chord P1.11 is already scheduled to free, so they wait for it rather than being resolved twice. (Previous Heading landed with P1.4; the five QuillLite-keyed line tools landed 2026-09-17 on QuillLite's own chords.) | QUILL | S | rule 8 gate passes |
| P1.2 | Structural selection family on Lite's six chords; Set Mark `Ctrl+Shift+M`, Exchange `Ctrl+Alt+X`, Duplicate Selection `Ctrl+Alt+Q`; Switch Document Mode `Alt+Shift+F`; `Ctrl+Alt+F8` becomes the marker toggle in **both** and Extend Selection Mode takes its own chord in both (5.3a); Shrink drops its stack; Reselect remembers every structural select; F8 gains a cancel; marks on the shared ring, clamped, recorded for Back | both | M | -- |
| P1.8 | File Encoding and Line Endings dialog in QUILL's File menu (dirtying, with UTF-8 BOM, UTF-16 detection on open) | QUILL | M | round-trip test per encoding |
| P1.11 | AI commands vacate `Ctrl+Alt+Shift+{S,I,G,T,H,E}`; favourite folders to the leader; leader reclaim (5.9) | QUILL | S | -- |
| P1.12 | Clipboard verbs: Copy to Tray / Clear / Collect / Paste Collected / Clear Collector / Keep Clip / Recent Clips on Lite's chords in QUILL | QUILL | S | -- |
| P1.13 | New Rich / New Plain Text Document, Character Details, Recent File N and Editor Font in QUILL -- the four that need a command written, not just a key; Open User Guide off its literal accelerator | QUILL | S | -- |
| P1.14 | Spelling parity into QUILL: the caret-landing check, suggestions spelled as you arrow, the "Spelling: word" context submenu, the Announcements dialog on `Ctrl+Alt+Shift+F7`, Check While Typing on `Ctrl+Alt+F7` and its state said once on open; the tokenizer goes Unicode in core (S4, S5). F7 honours session ignores as of 2026-09-16 -- the shared ReviewSession takes an ignore list and QuillLite hands its own through; QUILL has none to pass until S3 gives it one | both | M | a word with an accent is one word in both editors |
| P1.15 | The **parity gate** (section 9) with its exception table, so P0/P1 cannot regress | tests | S | gate green with zero undocumented divergences |
| P1.16 | One line-tool helper in QUILL with Lite's scope, no-op detection, counts and rich warning (N1-N3); one command per verb (N4); **and the case tools take the word at the caret with no selection**, which QuillLite does as of 2026-09-16 and QUILL still does not (N5, 3.4) | QUILL | S | Sort with no selection sorts the document and says how many lines |
| P1.17 | QUILL adopts `set_heading_level` for Markdown headings, `all_headings()` for the outline in rich, bold state announcements, the H5/H6 ladder sizes, and a rich-aware Describe in Lite (R3, R7, R8, R12, R13) | both | M | -- |
| P1.18 | Status bar: GATE-13 fixes in QUILL's cells (H3) -- the last of this row. H9 landed 2026-09-17: the reserved-key list moved to the shared `quill/core/reserved_keys.py` and QUILL's Keyboard Manager refuses the screen reader's own keys, which it never did, so a binding on Insert was assigned, shown as assigned and never fired. Lite's assign-time wx check landed 2026-09-16 (H2), and `Win` is rejected there (H1) | QUILL | S | -- |
| P1.19 | Clipboard: tray labels and pins survive edits (C3); collector becomes a buffer (C4, 5.1); tray paste no longer waits for the multi-press window on a plain single press (C5); Lite's clip history captures copies as promised or the promise is removed (C1); one verified undo story for `Replace` (C6) | both | M | -- |
| P1.20 | **The menu bar answers to Word** (4.5): fold Search into Edit and delete the menu (M1); a Format menu item that says Font... (M2, with P0.6a); alignment, Bullets and Line Spacing in Format (M3); Go To in Edit as well as Navigate (M4); "Word Wrap" not "Toggle Soft Wrap" (M5); Delete and Paste Text Only in Edit (M7) | QUILL | S | a person who knows Word finds each verb in the menu Word puts it in |
| P1.21 | **Typing defaults decided once** (T3, T4): Tab's meaning follows the document kind in both; autoformat gated by kind as well as by setting; QUILL's two-setting granularity and Lite's off-by-default adopted in both | both | S | typing a quote in a `.json` inserts a straight quote in both, whatever the setting says |

### P2 -- model alignments, and the value that crosses into Lite

| # | Item | Editors | Cost |
| --- | --- | --- | --- |
| P2.1 | Copy to Tray Slot... chooser **in QUILL** (Lite has it, `Alt+Shift+Y`, with each row saying what it would overwrite); "tray is full" wording from the core (5.1) | QUILL | S |
| P2.2 | Bookmark re-anchoring landed in the shared `BookmarkSet` on 2026-09-16 and QuillLite is on it; **QUILL still has no numbered bookmarks at all** (4.1), so what is left here is QUILL adopting the set -- and, in both, list rows led by the digit (5.2) | both | S |
| P2.4 | The QuillLite profile in QUILL with "Bring my QuillLite settings" (5.8), on the settings-name mapping from G1 | QUILL | M |
| P2.5 | One verb, one registration: retire duplicate ids and Quillin re-shipments (7.1); char hook dispatches through the registry (7.2) | QUILL | M |
| P2.6 | Keymap profile JSONs become deltas over `DEFAULT_KEYMAP` (7.3) | QUILL | S |
| P2.8 | The remaining **Worse** rows of section 6 not named in P1: F7-F13, S6-S9, L3-L13, R9-R11, C7-C8, N5, PR1-PR3, A1-A7 | per bug | S each |
| P2.10 | New documents default to CRLF in QUILL as in Notepad, WordPad, Word and Lite, with the default exposed in Settings in both (F11); close prompts name the file and say Save / Don't Save / Cancel in both, from one core string (F12) | both | S |
| P2.11 | Lossy Save As warns before the write in every lossy direction in both, and converts at write time, never in the buffer (F1); Lite's Earlier Versions says "formatting is not kept" for rich documents (F7). Lite's print settings persist as of 2026-09-16 | both | S |
| P2.12 | Session restore in QUILL on the shared rule Lite uses, command-line files winning (G4); crash recovery in Lite lists slots and lets the user decline (F14); read-only detected at open in both | both | M |
| P2.16 | A7's `--rich` / `--plain` only. **A6 was already done**: `core/ipc.py`'s advisory file lock has guarded against a second QUILL since #609, and it is the better mechanism -- the kernel owns the lock's lifecycle, so unlike a PID file or Lite's named object a stale lock cannot happen. A7 needs a seam QUILL does not have (nothing starts a document in a chosen kind; the switcher changes one afterwards), so it is S for real rather than T | QUILL | S |

### P3 -- polish, docs, the long tail, and the magical tier

| # | Item | Cost |
| --- | --- | --- |
| P3.3 | Documentation drift (7.6): Lite PRD 2.2/3.2/8.1, both user guides' key tables, CHANGELOGs, release notes; regenerate keyboard and F1 references; Key Describer titles for every new QUILL chord | S |
| P3.5 | Bugs from section 6 rated Divergent, where a decision was taken | S each |
| P3.7 | **The magical tier** (4.2, last table): "What changed?", a spoken undo over the `DocumentText` journal, repeat-the-last-announcement, and a one-sentence structure summary on open. QUILL first or shared-simultaneous, never Lite first | M each |

### Shipping order and the migration story

Both keymaps are delta-stored, so a changed default reaches every existing user
on the next launch with no migration entry (`keymap.py` KEYMAP_DEFAULTS_EPOCH
comment; Lite `keymap.py` docstring). The cost of P0-P1 is habit churn, not
code. Ship the keymap moves as **one release** ("family keymap") with one
release note listing every changed chord, rather than dribbling them, so a
person relearns once. Do not bump the epoch. A user who rebound a moved command
keeps their binding, which the parity gate must treat as user data, not a
divergence.

The three viability items (P0.6a, P0.6b, P0.6c) do not touch a keybinding and
have no habit cost, so they ship whenever they are ready -- ideally before the
keymap release, because a person relearning their keys should not also be
meeting a slow status bar.

## 9. Gates that ship with this

1. **Family parity gate** (`tests/unit/core/test_family_keymap.py`): a shared
   table `quill/core/lite/parity.py` mapping every QuillLite handler to its
   QUILL command id. For each pair, the resolved chord identities must match
   unless the pair is in `DIVERGENCES` with a reason string; and no chord may
   resolve to two *different* mapped commands across the editors. The table is
   the review: adding a Lite command without a mapping fails.
2. **Bound-command gate**: every registered QUILL command in the editor
   categories (`edit`, `format`, `navigate`, `view`, `file`, `power`, `tools`
   spelling/clipboard) has a default chord or an allowlist entry with a reason.
3. **Hook gate**: `check_banned_patterns.py` flags `ord("X")` key dispatch in a
   char hook that does not go through `self.commands`.
4. **Quillin hotkey gate**: a bundled or installed Quillin's `hotkeys` may not
   claim a chord in `DEFAULT_KEYMAP` or `DEFAULT_ALIASES`.
5. **Profile-delta gate**: keymap profile JSONs contain only overrides.
6. **Menu-shape gate**: the QUILL menu bar's top-level titles and the menu each
   of a named set of verbs lives in (Find, Replace, Go To, Font, Word Wrap,
   Delete, Paste Text Only, alignment, bullets) are asserted against the
   Word/WordPad/Notepad table in 4.5. A verb that moves out of its Microsoft
   menu fails the build.
7. **Settings-vocabulary gate**: a field added to either `Settings` dataclass
   whose concept already exists in the other under a different name fails
   unless it is in the mapping table `quill/core/lite/parity.py` carries for
   5.8's "Bring my QuillLite settings".
8. **Large-document budget** (GATE-PERF): a synthetic 50 MB buffer, one status
   refresh, one autoformat keystroke and one live-spell pass in each editor,
   asserted against a ceiling rather than against each other, so neither can
   regain an O(N) reader. This is the gate that keeps P0.6c from rotting.
9. Existing gates that must stay green and will need regeneration: menu
   accelerators, GATE-KEYREF, GATE-HELPREF, GATE-DESCRIBE (Key Describer
   titles for every new QUILL chord), GATE-LITE-COVER (every new Lite handler
   needs a behavioural test), module size budgets.

## Recorded, so nobody looks again

- **`F6` walks the regions in the order they appear on screen**, and 5.6's
  "F6 lands in the status bar first in both" is **withdrawn** (Jeff,
  2026-09-17, after it was implemented and heard). The status bar is the
  most-visited region, which is the argument that produced 5.6; the better
  argument is that F6 is a *spatial* key. Somebody who knows their window has a
  Reveal Codes pane under the editor and a status bar at the bottom can predict
  where three presses land. Ordering the ring by how often each region is
  wanted makes it unpredictable, and a navigation key you cannot predict is one
  you press and then have to listen to find out where you are. A region that is
  not showing is not in the ring at all, which is the same rule from the other
  side. Both editors already did this; the change was the mistake.

- **Turning the document tabs off is already possible in both**, and was when
  the row was written. QUILL's `show_tab_control` defaults to **False**, so
  there is no tab strip and no `F6` stop out of the box; **View > Show Tab
  Control** toggles it, and `Ctrl+Tab`, `Ctrl+Shift+Tab` and the Window menu's
  per-document rows are bound independently of the strip, so the walk is
  unaffected either way. QuillLite is MDI and has never had a strip: `F6` is
  editor <-> status bar only, and documents are reached by `Ctrl+Tab`,
  `Ctrl+F6`, `Alt+1`-`Alt+9` and the Window menu. (Verified 2026-09-17.)

- **A6 was already fixed when the audit called it broken.** "No single-instance
  check" was wrong: `quill/core/ipc.py` has guarded against a second QUILL
  since #609, with an OS **advisory file lock** (`flock` / `msvcrt.locking`)
  rather than QuillLite's `wx.SingleInstanceChecker`. QUILL's is the better of
  the two -- the kernel owns the lock's lifecycle, so a stale lock is
  impossible, where a PID file or a named object can outlive the process that
  made it. `--force-new-window` is the escape hatch, spelled differently from
  Lite's `--new-instance` and doing the same job. Nothing to take; recorded so
  the row is not reopened. (Found 2026-09-17 while starting P2.16.)

- **Find and replace** is shared where it matters: the wrap setting, the two
  not-found sentences and the feedback channel are one implementation. One
  divergence survives and is worth one line of work, not an audit: QUILL's Find
  dialog exposes **Wrap around** and a **Direction** radio box, which is
  Notepad's shape; QuillLite's exposes the search mode, Match case and Whole
  word only, and keeps wrap as an invisible setting with a Find previous button
  instead of a direction. Give Lite the wrap checkbox; leave the direction to
  the button, which is better. (`find_dialog.py:107-127`,
  `lite_find_dialogs.py:132-172`)
- **Recovery** is two implementations with the same two promises, divergent
  because QuillLite keeps its own data folder. Correct as it stands; the bugs
  in it are F2, F9 and F14.
- **The command palette, Go To Anything and the support dialog** are already
  one shared implementation each. Nothing to do.
- **Emoji and special-character pickers** are shared and were re-measured for
  speed in `9eeb16c`. Nothing to do.

## 10. Everything left, in one table

**34 items open.** Delete a row when it lands. Tiered items first,
then the section-6 findings no tiered item has claimed.

| # | Item |
| --- | --- |
| P0.7 | The REMAINING Broken rows, all QUILL's: F4, F5, F6 (save path / watcher). F1, F2, F3, F9, R6 landed 2026-09-17 |
| P0.8 | Verify live, then fix if confirmed: R4 dark mode grey text in saved .rtf; C2/N3 whole-document rewrite; R14 two-step undo. R5 fixed 2026-09-16, L13 2026-09-17 |
| P0.9 | _run_command reports the exception class and message, not "Command failed"; save_file handles UnicodeEncodeError and U |
| P1.1 | Keyless QUILL commands still waiting on the chords P1.11 frees: Sort Z-A, Tidy Whitespace, lowercase, Earlier Versions, Markdown Tag. Keyboard Manager and Sound Scheme landed 2026-09-17 on the favourite-folder move |
| P1.2 | Structural selection family on Lite's six chords; Set Mark Ctrl+Shift+M, Exchange Ctrl+Alt+X, Duplicate Selection Ctrl |
| P1.8 | File Encoding and Line Endings dialog in QUILL's File menu (dirtying, with UTF-8 BOM, UTF-16 detection on open) |
| P1.11 | AI commands vacate Ctrl+Alt+Shift+{S,I,G,T,H,E}; leader reclaim (5.9). Favourite folders went to the leader 2026-09-17 |
| P1.12 | Clipboard verbs: Copy to Tray / Clear / Collect / Paste Collected / Clear Collector / Keep Clip / Recent Clips on Lite |
| P1.13 | New Rich / New Plain Text Document, Character Details, Recent File N and Editor Font in QUILL -- the four that need a  |
| P1.14 | Spelling parity into QUILL: the caret-landing check, suggestions spelled as you arrow, the "Spelling: word" context su |
| P1.15 | The parity gate (section 9) with its exception table, so P0/P1 cannot regress |
| P1.16 | One line-tool helper in QUILL with Lite's scope, no-op detection, counts and rich warning (N1-N3); one command per ver |
| P1.17 | QUILL adopts set_heading_level for Markdown headings, all_headings() for the outline in rich, bold state announcements |
| P1.18 | Status bar: GATE-13 fixes in QUILL's cells (H3). H9 landed 2026-09-17 -- the reserved-key list is shared (core/reserved_keys.py) and QUILL's Keyboard Manager refuses the reader's own keys, which it never did |
| P1.19 | Clipboard: tray labels and pins survive edits (C3); collector becomes a buffer (C4, 5.1); tray paste no longer waits f |
| P1.20 | The menu bar answers to Word (4.5): fold Search into Edit and delete the menu (M1); a Format menu item that says Font. |
| P1.21 | Typing defaults decided once (T3, T4): Tab's meaning follows the document kind in both; autoformat gated by kind as well as by setting |
| P2.1 | Copy to Tray Slot... chooser in QUILL (Lite has it); "tray is full" wording from the core |
| P2.2 | QUILL adopts the shared BookmarkSet (4.1); list rows led by the digit in both (5.2) |
| P2.4 | The QuillLite profile in QUILL with "Bring my QuillLite settings" (5.8), on the settings-name mapping from G1 |
| P2.5 | One verb, one registration: retire duplicate ids and Quillin re-shipments (7.1); char hook dispatches through the regi |
| P2.6 | Keymap profile JSONs become deltas over DEFAULT_KEYMAP (7.3) |
| P2.8 | The remaining Worse rows of section 6 not named in P1: F7-F13, S6-S9, L3-L13, R9-R11, C7-C8, N5, PR1-PR3, A1-A7 |
| P2.10 | New documents default to CRLF in QUILL as in Notepad, WordPad, Word and Lite, with the default exposed in Settings in  |
| P2.11 | Lossy Save As warns before the write in every lossy direction in both (F1); Lite's Earlier Versions says formatting is not kept (F7) |
| P2.12 | Session restore in QUILL on the shared rule Lite uses, command-line files winning (G4); crash recovery in Lite lists s |
| P2.16 | **A6 is already done and the row's premise was stale**: QUILL has had a single-instance guard since #609 (`core/ipc.py`, an OS advisory file lock, which is BETTER than Lite's kernel object -- a stale lock is impossible) plus `--force-new-window`. What is left is A7's `--rich` / `--plain`, and it is not the one-liner it looks like: QUILL has no "start a document in this kind" seam at all, so the flag needs threading through run_app into the Document Format switcher. A flag that parses and does nothing is the bug class this whole plan is about |
| P3.3 | Documentation drift (7.6): Lite PRD 2.2/3.2/8.1, both user guides' key tables, CHANGELOGs, release notes; regenerate k |
| P3.5 | Bugs from section 6 rated Divergent, where a decision was taken |
| P3.7 | The magical tier (4.2, last table): "What changed?", a spoken undo over the DocumentText journal, repeat-the-last-anno |
| C9 (D) | [both] Tray full: QUILL refuses and says so, Lite overwrites slot 1 and reports success (QUILL's wins). Restor |
| F10 (W) | [QUILL] save_all_files never restores the active tab; save_file relies on EVT_TEXT having synced the document ( |
| L7 (W) | [QUILL] List Bookmarks shows stale positions: jumps re-anchor by snippet but the list prints the raw stored off |
| N2 (W) | [QUILL] No no-op detection and no counts: every QUILL line tool announces its past-tense status even when nothi |
