# QUILL and QuillLite: what is left

Five items, audited against the code 2026-09-18. A landed item is deleted; git
history is the record. Audit a row against the code before working it.

## The rules

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
10. **Value flows both ways, violations flow one**: a capability may cross in
    either direction, but QuillLite is never allowed to be ahead of QUILL.
11. **Every remaining divergence is a comment in `keymap.py` *and* an entry in
    the parity gate's exception table.**

Commit each logical chunk with all 41 gates green. Write and test, but do
**not** commit anything touching startup, the save path or the external-change
watcher. Stop and leave a note for a feature removal beyond this file, or a
move of an x.md authoring chord.

## Decisions still to apply

Answered 2026-09-16; settled, do not re-litigate.

| Question | Answer |
| --- | --- |
| Blockquote | **Merges into Quote Lines** on `Ctrl+Shift+Q`; `format.blockquote` retires; `Ctrl+Alt+Q` -> Duplicate Selection (P2.5, P1.2). |
| `keep_unique_lines` / `remove_duplicate_lines` | **Merge**: one verb, QuillLite's `Ctrl+Alt+D` and its wording. `Alt+Shift+K` freed (P2.5). |
| `trim_blank_lines` / `remove_blank_lines` | **Both kept, renamed**: "Trim Blank Lines at the Ends" and "Remove Every Blank Line" (P2.5). |
| Crash recovery and session restore | **Both editors ask, then restore.** Recovery lists what it found; QUILL gains session restore on QuillLite's rule, command-line files winning (P2.12). |
| `DocumentText` | **Build it fully** (P0.6c). |
| The QuillLite profile in QUILL | **Build it** (P2.4). |
| The magical tier | **All four approved**: repeat the last announcement, structure on arrival, "what changed?", spoken undo (P3.7). |
| QuillLite and braille | Write the position into QuillLite's PRD as a decision. Implementing braille there stays out of scope (P3.3). |

## The list

| # | Editors | Batch |
| --- | --- | --- |
| [P2.8](#p28) the remaining Worse rows | per bug | L |
| [P2.4](#p24) the QuillLite profile in QUILL | QUILL | M |
| [P0.6c](#p06c) QUILL adopts `DocumentText` | QUILL | N |
| [P3.7](#p37) the magical tier | both | N |
| [P3.3](#p33) documentation drift | docs | Z (last) |

### P2.8

Seven **Worse** rows no other item names. Cheap each.

| # | Editor | Finding | Evidence |
| --- | --- | --- | --- |
| F7 | Lite | The status bar's Encoding and Line Endings cells read "UTF-8 / CRLF" for every `.rtf`; they should read the document's own format. (The rest of F7 landed 2026-09-16.) | `lite_window_status.py:390-391` |
| F8 | Lite | "No Markdown could be made from this HTML; saved unchanged" and "Converted HTML to Markdown" are spoken *before* the save runs. A classic-Mac CR file opens the format dialog with CRLF preselected, so OK silently converts it. UTF-16 big-endian round-trips as little-endian on a no-edit save, against the module's own byte-honesty contract. | `lite_window_markup.py:229, 243`, `lite_dialogs.py:331, 350-355`, `core/lite/textfile.py:87-88, 107` |
| L7 | QUILL | **List Bookmarks shows stale positions**: jumps re-anchor by snippet but the list prints the raw stored offset, and the resolved offset is written back without saving, so tab and disk keep the old value until the next Set. | `main_frame.py:11533-11549, 11607-11610` |
| R9 | both | **Native RichEdit hotkeys leak into plain and Markdown documents** because plain documents are `TM_RICHTEXT` controls: in QUILL unbound `Ctrl+U`, `Ctrl+L`, `Ctrl+R` underline or re-align a Markdown buffer natively (not dirty, not announced, not saved, but visible and undo-stacked); in Lite every native chord it does not bind (`Ctrl+Shift+=` and friends) does the same. Paste is guarded; keys are not. | `main_frame.py:2052-2068`, `richedit_editing.py:243-254`, `lite_window_commands.py:223-236` |
| R11 | QUILL | Choosing "Convert to Rich Text" in the plain-text formatting prompt converts and then **drops the Bold that was asked for**. | `main_frame_rich_mode.py:463-482`, `main_frame.py:16161-16163` |
| H5 | QUILL | Mnemonic collisions inside Tools > Customize and Support (`&Export...` three times, `&Import...` twice); the access-key test checks only top-level titles. | `main_frame_menu.py:3254-3262`, `test_menu_bar_access_keys.py:82-104` |
| C8 | QUILL | GATE-13: the Copy Tray dialog announces "Slot N loaded" on every list move. Keep Clip, Copy All, Copy with Source, Restore Deleted Text, Duplicate Selection and every collector message report through `_set_status`, which is throttled and bypasses the verbosity/braille service, so none reach braille or the announcement log. `_copy_to_clipboard` has no retry and no `try` around `SetData`; a locked clipboard raises past the handler. `read_clipboard_text` shows wx's own error dialog on its last retry and is called from the collector timer and from the tray dialog's selection handler, so a modal can appear from a timer or a list move. Open Clip Library bypasses `_show_modal_dialog`. | `copy_tray_dialog.py:174, 208, 218-225`, `main_frame_clip_library.py:296-298, 346`, `main_frame.py:19489-19498`, `clipboard_retry.py:80-81` |

### P2.4

A QUILL feature profile that shows QuillLite's nine menus in its order with its
items and nothing else -- AI, companions, Quillins and the leader depth off,
not hidden -- carrying `default_new_document_format` the way Lite's
WordPad/Notepad profiles carry `default_mode`, and offering **Bring my
QuillLite settings** on first activation (settings, keymap overrides,
abbreviations, personal dictionary, copy tray, clip library, collector,
per-file bookmarks -- all already sharing on-disk shapes). Unblocked: the
settings-name mapping it needed is `quill/core/lite/parity.py`.

### P0.6c

QUILL adopts the shared `DocumentText`. The object exists and QuillLite is on
it; QUILL still has `document.text` plus a stats cache in
`main_frame_statusbar.py`. Architectural, in the largest module in the tree,
and P3.7's spoken undo cannot start until its edit journal lands.

V4 (both, Worse): **neither editor's document model is incremental.** QUILL's
mirror makes reads free but every edit re-sets a whole string; Lite has no
mirror. One `DocumentText` in core, owned by both, holds the string, bumps a
revision, answers `line_column_for_position` and `stats` from a cache, and is
the only thing display code may read. It retires V1-V3, S8 and half of 6.7.

### P3.7

The magical tier, all four approved: "What changed?", a spoken undo over the
`DocumentText` journal, repeat-the-last-announcement, and a one-sentence
structure summary on arrival. None has a command yet. QUILL first or
shared-simultaneous, never QuillLite first.

### P3.3

Documentation drift: both user guides' key tables, the release notes, the
QuillLite PRD's braille position, and the reversed external-change default
(nothing auto-reloads; the question carries a per-format "do not ask me again",
stored in the internal `external_change_always_reload` / `_always_keep`). **Last deliberately** -- it documents
everything above. The generated references (keyboard, F1 help, tutorials)
regenerate per change and are gated, so they are not this row.

## Gates still to ship

1. **Bound-command gate**: every registered QUILL editor command has a default
   chord or an allowlist entry with a reason (rule 8, enforced).
2. **Quillin hotkey gate**: a Quillin's `hotkeys` may not claim a chord in
   `DEFAULT_KEYMAP` or `DEFAULT_ALIASES`.
3. **Menu-shape gate**: the top-level titles, and the menu each of Find,
   Replace, Go To, Font, Word Wrap, Delete, Paste Text Only, alignment and
   bullets lives in, asserted against Word/WordPad/Notepad.
4. **Settings-vocabulary gate**: a field added to either `Settings` whose
   concept exists in the other under a different name fails unless it is in
   `quill/core/lite/parity.py`.
5. **Large-document budget** (GATE-PERF): a synthetic 50 MB buffer, one status
   refresh, one autoformat keystroke and one live-spell pass in each editor,
   against a ceiling rather than against each other. This is what keeps P0.6c
   from rotting.

The 41 in `platform_report` must stay green.

## How to work it

| Batch | Rows | One verification covers |
| --- | --- | --- |
| **L** | P2.8 | scattered; verify once at the end |
| **M** | P2.4 | profiles |
| **N** | P0.6c then P3.7 | the document model, in that order |
| **Z** | P3.3 | the docs gates |

1. **Per item: run only the touched suite.**
2. **Per batch: `platform_report` once.** It catches the snapshot, budget and
   reference drift unit tests never will.
3. **Full suite twice a session**, in slices (`tests/unit/core`,
   `tests/unit/ui`, `tests/unit/apps`): the whole suite in one process has been
   killed twice for memory.
4. **Audit the row before writing it**, against the code.
5. **Two batches never move at once.**

## Known red, and none of it ours

- `tests/unit/core/expansion/test_matcher.py` -- four tests call
  `match_buffer(..., snippet_library=...)` and `match_buffer` has no such
  parameter. Committed in `3aaa96b` ahead of the implementation: snippet
  expansion in the *global* expander is half-landed.
- `mypy quill/core quill/io` fails on `quill/core/spelling/session.py:168`
  (`"object" has no attribute "start"`).
