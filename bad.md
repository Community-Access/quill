# QUILL and QuillLite: what is left

One item, audited against the code 2026-09-18. A landed item is deleted; git
history is the record. Audit a row against the code before working it.

## The rules

Lower number wins when two conflict. The numbers are cited by number in
`keymap.py` and `lite/parity.py`, so they do not get renumbered.

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
| QuillLite and braille | Write the position into QuillLite's PRD as a decision. Implementing braille there stays out of scope (P3.3). |

## The list

| # | Editors | Batch |
| --- | --- | --- |
| [P3.3](#p33) documentation drift | docs | Z (last) |

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

The 41 in `platform_report` must stay green, plus the menu-item access-key
gate added 2026-09-18 (`test_menu_item_access_keys.py`): no two items in one
menu may claim the same Alt letter.

## How to work it

| Batch | Rows | One verification covers |
| --- | --- | --- |
| **Z** | P3.3 | the docs gates |

1. **Per item: run only the touched suite.**
2. **Per batch: `platform_report` once.** It catches the snapshot, budget and
   reference drift unit tests never will.
3. **Full suite twice a session**, in slices (`tests/unit/core`,
   `tests/unit/ui`, `tests/unit/apps`): the whole suite in one process has been
   killed twice for memory.
4. **Audit the row before writing it**, against the code.
5. **Two batches never move at once.**
