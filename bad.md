# QUILL and QuillLite: the parity and viability plan

**Status: plan of record, 2026-09-16.** Second pass. The 2026-09-15 pass
compared every command and every chord mechanically and audited seven feature
families for bugs; this pass re-ran that diff against today's tree, deleted
what has shipped, and added the three dimensions the first pass did not cover:
**is each app actually viable for the job it claims** (0.5, 4.3, 6.9); **does it
behave the way Notepad, WordPad and Word behave** in the places a person's hands
and habits already know (4.4, 4.5); and **which of QUILL's capabilities belong
in QuillLite** now that the one-way rule has been read the way it was meant
(4.0, 4.2). Nothing here is changed in code. **Completed items are deleted
from this file**; git history is the record of what landed, which is why numbers
have gaps.

## 0. What this is

QuillLite and QUILL implement the same user-facing behaviours twice. Sometimes
that is deliberate and right (QuillLite keeps its own data folder and has no
tabs, AI, speech, dictation, preview, Quillins, remote files or companion apps).
Sometimes it is an accident of two people solving the same problem on different
days, and then one of them is worse -- or the small product has a thing the big
one does not, which `CLAUDE.md` and the QuillLite PRD both forbid.

The goal is a **golden state** with four properties:

1. **Notepad, WordPad and Word keys, unchanged.** Where Microsoft binds a key
   for a function both editors have, both editors use that key. A person who
   knows Word should be able to sit down at either editor and press what they
   already know.
2. **One family keymap.** A chord that means something in one editor means the
   same thing in the other, or nothing at all. Never a *different* thing.
3. **Growing up is free.** Somebody who outgrows QuillLite opens QUILL and finds
   the same nine menus, the same keys and their own settings, with more behind
   them. QuillLite itself stays lite: anything it gains is editor-core, shared,
   and switchable off.
4. **Each app is good at its own job.** A shared keymap is worth nothing if
   QuillLite stalls on a large file or QUILL cannot make its text bigger. The
   keys are the visible half of this plan; section 0.5 is the other half.

### Method

For each behaviour both editors have: read both implementations; write down the
*model* each uses (the promise, not the code); where they differ decide which is
better **for a listener** and why; record it with evidence so it can be argued
with. The chord comparison was done by script against `DEFAULT_KEYMAP`,
`DEFAULT_ALIASES` and QuillLite's `COMMANDS` table, with a hand-written map of
which QuillLite handler is which QUILL command id (that map becomes the parity
gate in section 9). It was re-run on 2026-09-16 and the numbers in section 2
are that run, not the first one.

The second pass added a different question to the same method: **for each app,
what would make it unusable for the job it claims, and is that true today?**
That question does not compare the two editors at all, and it is what produced
6.9's numbers, 4.3's absence and section 0.5's three bars.

Severity is about the person, not the code:

| | |
| --- | --- |
| **Broken** | The feature does not do what it says, or cannot be used as designed. |
| **Worse** | Both work; one costs the listener more keystrokes, more uncertainty, or more silence. |
| **Parity** | One editor has a capability the other lacks. Lite-only is a rule violation; QUILL-only is a decision. |
| **Divergent** | Different on purpose, or harmlessly different. Recorded so nobody re-litigates it. |

## 0.5 What each app is for, and what "viable" means

The keyboard work below is worthless if either app fails at the job it is for.
Two products, two jobs, two different bars:

**QuillLite is a Notepad and WordPad replacement for somebody who listens.**
The scenario is: a file arrives, or a thought does; open it, read it, change it,
save it, close it, in under a minute, with a screen reader, without learning
anything. Its PRD also accepts that people edit `.py`, `.json` and `.conf`
there. Viable means: it opens anything Notepad opens, at any size Notepad
opens it, and never corrupts what it did not understand.

**QUILL is the writing environment somebody moves into.** The scenario is a
document worked on over days: structure, revision, reading back, publishing,
and the AI, speech, braille and companion surfaces around it. Viable means the
editing core underneath all that is at least as good as the small product's,
because every hour in QUILL is spent in the editor, not in the features that
justify it.

Three viability bars follow from that, and this pass found all three failing:

| Bar | Who fails it | Consequence |
| --- | --- | --- |
| **You can change the text's typeface and size.** | QUILL | QUILL never calls `SetFont` on an editor control, has no `font_name`/`font_size` setting and no text-size command. A low-vision user cannot make the text bigger. See 4.3. |
| **A big file behaves.** | QuillLite | No size guard, and three full-document scans per status refresh. See 6.9. |
| **A file survives the round trip.** | both | Section 6.3's F1-F6, already P0. |

A fourth bar -- **the keys you already know work** -- is what sections 1 through
3 are about, and is the one both apps fail most visibly.

## 0.6 Decisions taken (2026-09-16)

Four questions that gate P0 were put to the user and answered. They are
decisions, not proposals, and the rows below follow them:

| Question | Answer |
| --- | --- |
| `Ctrl+Shift+1..9` -- tray paste or bookmarks? | **Full swap.** Set Bookmark N in both; QUILL's numbered tray paste moves to `Ctrl+Alt+Shift+1..9`. No first-use notice; the mis-press is harmless and the release note carries the change. |
| Where does Extend Selection Mode live? | **`Ctrl+Alt+Shift+F8`, in both.** `Ctrl+Alt+F8` becomes the F8-marker toggle in both, which is QuillLite's shipped meaning. Extend mode is kept and fixed (5.3a, P1.2a), then offered to QuillLite. |
| How far does the menu restructure go? | **Full restructure** (4.5, P1.20): the Search menu is folded into Edit and deleted, Format gains Font, alignment, Bullets and Line Spacing, Edit gains Delete, Paste Text Only and Go To, and View says Word Wrap. |
| Do the x.md authoring chords move when Microsoft and QuillLite agree on a key? | **Yes for three, no for the fourth.** Justify `Ctrl+Alt+J` -> `Ctrl+J`, Paste Text Only `Ctrl+Alt+V` -> `Ctrl+Shift+V`, Insert Link `Ctrl+Alt+K` -> `Ctrl+K` (which only makes QUILL's existing hard-coded hook official). **Insert Table keeps `Ctrl+Alt+T`**: Trim Trailing Spaces takes a different chord in QUILL and the pair becomes a documented divergence, because an authorized chord for a verb that builds structure outranks one that strips whitespace. Every further authoring-chord move is asked before it is made. |
| How ambitious is QUILL's new editor font? | **Match QuillLite exactly**: `font_name` and `font_size` settings, Format > Font... on `Ctrl+Alt+F`, and `Ctrl+=` / `Ctrl+-` / `Ctrl+0`, from shared code, with view zoom rather than run sizes in rich documents. `format.font_dialog`'s Markdown-only refusal is left for P1.7. |

## 1. The rules

These decide every row below. When two rules conflict the lower number wins.

1. **Microsoft's key wins.** Where Word, WordPad or Notepad bind a key for a
   function both editors have, that is the family key. Exceptions, each because
   a different Microsoft product or a family-wide habit already owns the chord:
   `F3`/`Shift+F3` are Notepad's find next/previous (not Word's case cycle);
   `F5` is Notepad's date and time (not Word's Go To); `Ctrl+D` duplicates a
   line (the text-editor convention -- Word's font dialog is covered by
   `Ctrl+Shift+F`); `Ctrl+]`/`Ctrl+[` indent and outdent (Word grows the font a
   point, which `Ctrl+Shift+>`/`<` already do); `Ctrl+Q` exits.
2. **The command both products have keeps the chord; the product-only command
   moves.** This resolves every "same chord, different command" collision
   without a debate per row.
3. **Frequency breaks ties.** When both products have both commands on one
   chord, the one used in the editing loop keeps the shorter chord.
4. **Destructive first.** A habit that does damage in the other editor (pastes,
   teaches the dictionary, rewrites lines) is fixed before one that merely
   opens the wrong dialog.
5. **A chord free in both editors is adopted as an alias**; nothing moves.
6. **Nothing QuillLite reaches on a plain chord lives on QUILL's leader chord.**
   The leader (`Ctrl+Shift+Grave, X`) is for QUILL-only depth. It is also
   nearly full -- four of sixty-two positions are free -- so section 5.9
   reclaims it.
7. **Editor chords are for the editor.** Media transport, radio favourites,
   favourite folders, AI, GitHub and remote-file commands do not sit on
   three-modifier chords that QuillLite uses for editing. They live on the
   leader, on the owning app's `APP_KEYMAPS`, or in a menu.
8. **Every registered editor command has a key or a written reason not to.**
   A capability with no key is invisible; the 2026-09 sweep found six such
   commands and this pass found thirty-three more (section 2).
9. **Once-a-year commands need *a* key in both editors, not the same key.**
   Backup/restore settings, customize features, keyboard manager, sound scheme,
   about, check for updates. The menu is an acceptable route for these, but the
   QuillLite gate requires every item to advertise a key, so they still get
   one, and where it is free in both the plan uses the same one anyway.
10. **Value flows both ways, violations flow one.** QuillLite may never be
    ahead of QUILL (4.0); that is a hard rule about *violations*. It is not a
    reason to starve QuillLite of QUILL's editor-core work. A QUILL capability
    that is editor-core, shared, worth a listener's time and switchable off
    belongs in QuillLite too (4.2) -- and when it is genuinely new, it lands in
    QUILL or in shared core first, never in the small product first.
11. **Every remaining divergence is a comment in `keymap.py` *and* an entry in
    the parity gate's exception table.** `CLAUDE.md` already asks for the
    comment; nothing enforced it, which is how sixty-seven divergences
    accumulated.

## 2. The numbers

Re-measured against the tree on 2026-09-16 (`DEFAULT_KEYMAP` 360 entries, 294
of them bound, plus 7 aliases; QuillLite 220 rows, 175 bound, plus 2 aliases):

| | |
| --- | --- |
| Chords bound in **both** editors | 136 |
| ...of which the two editors **agree** | 79 |
| ...of which the two editors run **different commands** | 53 |
| Chords QuillLite binds that are **free in QUILL** | 39 (6 are native verbs: Cut, Copy, Paste, Delete, Select All) |
| ...so QuillLite commands QUILL has but leaves **keyless** | 33 |
| Chords only QUILL binds | 163 |
| `DEFAULT_KEYMAP` entries registered with **no key at all** | 66 |
| QUILL editor commands with no default key (all categories, registry-wide) | 216 |
| Free positions on QUILL's leader chord | 4 of 62 |

The 33 keyless QUILL commands that QuillLite binds: Body Text, Character
Details, Remove Duplicate Lines, Editor Font, Document Language, Check While
Typing, Collect Selection, List Headings, Keep Clip, Page Setup, Sort A-Z,
Sort Z-A, Select Block, Clear the Collector, Spelling Announcements, Set Mark,
Recent Clips, Shrink Selection, Clear Copy Tray, Check for Updates, Exchange
Cursor and Mark, Copy to Tray, Text Size in/out/reset, Keyboard Shortcuts
window, Align Left, Align Right, Special Character, New Rich Text Document,
UPPERCASE, Say Selection, Underline, Date and Time, About.

Four of those are not merely keyless. **Underline** works in QUILL only because
`Ctrl+U` is hard-coded in `main_frame.py:2059-2067` for rich mode, outside the
keymap, so it is not in the keyboard reference and cannot be rebound; **Insert
Link** is the same on `Ctrl+K` (`main_frame.py:2046-2053`), a second,
undocumented binding beside the keymap's `Ctrl+Alt+K`; **Encoding** and **Line
Endings** are reachable in QUILL only by activating a status-bar cell, and are
in no menu; and **Editor Font and Text Size do not exist in QUILL at all**
(4.3), so they cannot be bound until they are written.

## 3. The golden family keymap

Every row is a decision. "Golden" is the chord both editors will use. "Moves"
names what is displaced in which editor and where it goes. Where a row depends
on another (a chord freed by an earlier move), the dependency is named. Rows
marked **(new)** are commands QUILL does not have today and gains in section 4.

### 3.1 Word, WordPad and Notepad keys (rule 1)

| Command | QuillLite today | QUILL today | Golden | Moves |
| --- | --- | --- | --- | --- |
| Underline | `Ctrl+U` | hard-coded, no keymap entry | `Ctrl+U` | QUILL: keymap entry; the char hook dispatches the registered command instead of a method |
| Bullets | `Ctrl+Shift+L` | `Ctrl+Alt+B` | `Ctrl+Shift+L` | WordPad's key, and WordPad *cycles* (bullets, numbered, off): one key replaces QUILL's separate numbered-list toggle on `Ctrl+Alt+N`. QUILL `misspelling_list_ranked` loses its chord and becomes a "rank by frequency" toggle inside the `Alt+Shift+L` list |
| Insert Link | (none; Lite has Markdown/HTML kinds) | hard-coded `Ctrl+K` + keymap `Ctrl+Alt+K` | `Ctrl+K` | QUILL: keymap entry, hook removed, `Ctrl+Alt+K` released (row 3.4). Lite gains Insert Link for Markdown/HTML kinds (section 4.2) |
| Document Statistics (Word Count) | `Ctrl+Alt+W` | `Ctrl+Shift+W` (Word Count) | `Ctrl+Shift+G` | Word's Word Count key. QUILL `go_to_page` folds into the Go To dialog (5.4); Lite Title Case -> `Ctrl+Shift+T` (free in both). Frees `Ctrl+Shift+W` and `Ctrl+Alt+W` for row 3.3 |
| Font for Selection | `Ctrl+Shift+F` | `format.font_dialog`, no key | `Ctrl+Shift+F` | Word's font key. QUILL `search_in_files` -> `Ctrl+Alt+Shift+F`; QUILL `toggle_fold` -> `Ctrl+Shift+[` and `list_folds` -> `Ctrl+Shift+]` (free in both); Lite Customize Features -> `Ctrl+Alt+F10` (rule 9) |
| Editor Font | `Ctrl+Alt+F` | (Preferences only) | `Ctrl+Alt+F` | QUILL gains a direct command **(new)**; free |
| Next window / document | `Ctrl+F6` (MDI) + `Ctrl+Tab` | `Ctrl+Tab`; `Ctrl+F6` = `focus_preview` | `Ctrl+F6` and `Ctrl+Tab` | Word's `Ctrl+F6`. QUILL `focus_preview` -> `Ctrl+Shift+F6` (free in both) |
| Text size in / out / reset | `Ctrl+=` `Ctrl+-` `Ctrl+0` | (none) | same | Notepad's keys. QUILL gains the commands **(new)**, see 5.5 |
| Date and Time | `F5` | Quillin item, no key, gone in Safe Mode | `F5` | QUILL re-registers a core command backed by the shared `quill.core.datetime_insert`; the `insert-tools` Quillin keeps its date-only/time-only variants |
| Save As / Open / Print aliases | -- | -- | `F12`, `Ctrl+F12`, `Ctrl+Shift+F12` | Word's function-key trio; free in both; aliases only (rule 5) |
| Go to Bookmark dialog alias | -- | -- | `Ctrl+Shift+F5` | Word's bookmark key; free in both; alias for row 3.5's list |
| Body Text | `Ctrl+Alt+0` | (none) | `Ctrl+Alt+0` | Word uses `Ctrl+Shift+N`, which Notepad and Lite spend on a new document; the ladder's zero is the family key. QUILL gains the command **(new)** |
| Thesaurus | (none) | `Shift+F7` | `Shift+F7` | Word's key; QUILL already right. Lite's `Shift+F7` moves (3.6) and stays **unbound** so the habit does nothing rather than something else |

### 3.2 Destructive overlaps (rule 4)

| Chord | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| `Ctrl+Shift+1`..`9` | Set Bookmark N | Paste tray slot N | **Set Bookmark N** in both | Bookmarks will exist in both (4.1); numbered tray paste is QUILL-only (5.1), so it moves to `Ctrl+Alt+Shift+1`..`9`,`0`,`-`,`=`. Radio favourites vacate the *editor* keymap for Quill Radio's own `APP_KEYMAPS` (rule 7); the multi-press peek/dialog dispatcher moves with the paste chords |
| `Alt+F7` | Add Word to Dictionary | Spelling for This Word | **Next Misspelling** (Word's key) | Neither habit can do harm: Spelling for This Word -> `Alt+Shift+F7` in both, Add Word -> `Ctrl+Alt+F9` in both (3.6) |
| `Ctrl+Alt+T` | Trim Trailing Spaces | Insert Table | **divergent, on purpose** | Decided 2026-09-16: Insert Table keeps `Ctrl+Alt+T` in QUILL (an authorized x.md authoring chord for a verb that builds structure), and QUILL's Trim Trailing Spaces takes another chord. The one row in 3.2 that does not converge; it goes in the gate's exception table with this reason |

### 3.3 The structural selection family (one decision, six chords)

QuillLite's chords are all three-key; QUILL's are four-key or on the leader.
Rule 6 and rule 3 both say QuillLite's win.

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| Select Word | `Ctrl+Shift+W` | `Ctrl+Alt+W` | `Ctrl+Shift+W` | freed by Document Statistics (3.1) |
| Select Line | `Ctrl+Shift+E` | `Ctrl+Alt+E` | `Ctrl+Shift+E` | `insert_equation` -> `Ctrl+Alt+=` (free in both) |
| Select Sentence | `Ctrl+Space` | `select_chunk` (a run of one character class) | `Ctrl+Space` = **Select Sentence** | QUILL gains sentence selection from the shared `sentence_span` **(new)**; `select_chunk` **moves rather than retires** -- it is renamed Select Token and rebound. See 5.3a: it duplicates Select Word on words and is the only way to select a run of punctuation or whitespace |
| Select Paragraph | `Ctrl+Shift+H` | `Ctrl+Alt+Shift+P` | `Ctrl+Shift+H` | see 3.2 |
| Select Block | `Ctrl+Alt+Shift+B` | `Ctrl+Shift+B` | `Ctrl+Alt+Shift+B` | `Ctrl+Shift+B` goes to Set Bookmark (3.5) |
| Expand Selection | `Ctrl+Shift+X` | leader `J` | `Ctrl+Shift+X` | `exchange_point_mark` -> `Ctrl+Alt+X` (Lite's) |
| Shrink Selection | `Ctrl+Alt+Shift+X` | leader `Shift+J` | `Ctrl+Alt+Shift+X` | free in QUILL |
| Set Mark | `Ctrl+Alt+Shift+K` | `Ctrl+Shift+M` | `Ctrl+Shift+M` | rule 3: Set Mark is an editing-loop verb; Lite's Switch Document Mode -> `Alt+Shift+F` in both (free in both; QUILL's leaves leader `K`) |
| Exchange Cursor and Mark | `Ctrl+Alt+X` | `Ctrl+Shift+X` | `Ctrl+Alt+X` | as above |
| Duplicate Selection | `Ctrl+Alt+Q` | `Ctrl+Alt+Shift+Q` | `Ctrl+Alt+Q` | QUILL `format.blockquote` merges with `edit.quote_lines` (one verb, `Ctrl+Shift+Q`); `unquote_lines` -> `Ctrl+Alt+Shift+Q`; Lite Back Up Settings -> `Ctrl+Alt+F11` (rule 9) |
| Say Selection | `Ctrl+Shift+Y` | no key | `Ctrl+Shift+Y` | free |

### 3.4 Lines, case and whitespace

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| Sort A-Z / Z-A | `Ctrl+Alt+S` / `Ctrl+Alt+Shift+S` | no key | same | `ai_spell_check` vacates (5.8) |
| Remove Duplicate Lines | `Ctrl+Alt+D` | `keep_unique_lines` `Alt+Shift+K` + `remove_duplicate_lines` no key (same engine, two names) | `Ctrl+Alt+D` | one command; `Alt+Shift+K` released for `previous_inline_note` (3.5) |
| Sort / whitespace / case scope | selection, else whole document | current line, whole document, or whole document depending on which of three helpers | **one helper**: selection, else whole document for line tools, else the word at the caret for case (Word's `Shift+F3` scope); rich text warns before a whole-document rewrite | 6.7 |
| Tidy Whitespace | `Ctrl+Alt+Shift+T` | no key | same | `ai_translate_selection` vacates |
| UPPERCASE / lowercase | `Ctrl+Shift+U` / `Ctrl+Shift+K` | no key | same | `unquote_lines` moves (3.3) |
| Title Case | `Ctrl+Shift+G` | no key | `Ctrl+Shift+T` | both move; `Ctrl+Shift+G` is Word's word count |
| Tab Key Inserts a Tab | `Ctrl+Alt+Shift+I` | leader `U` | `Ctrl+Alt+Shift+I` | `ai_spell_check_interactive` vacates |
| Toggle Block Comment | -- | `Shift+Alt+A` | `Ctrl+Shift+/` | rule 2: `Alt+Shift+A` is Expand Abbreviations in both |
| Numbered list toggle | -- | `Ctrl+Alt+N` | (folded into `Ctrl+Shift+L` cycle) | frees `Ctrl+Alt+N` for New Plain Text Document (3.7) |

### 3.5 Navigation and bookmarks

| Command | QuillLite | QUILL | Golden | Moves in QUILL |
| --- | --- | --- | --- | --- |
| Next / Previous Heading | `Ctrl+Alt+H` / `Ctrl+Alt+Shift+H` | no key | same | `horizontal_rule` -> `Ctrl+Alt+-` (free in both); `ai_thesaurus` vacates. `next_structure`/`previous_structure` (`Alt+Up/Down`) stay: they walk every block, not only headings |
| List Headings | `Ctrl+Alt+L` | `outline_navigator` `Ctrl+Shift+O` | both | alias (rule 5) |
| Go To Anything | `Ctrl+Alt+Shift+A` | leader `G`; `quick_nav` unbound | `Ctrl+Alt+Shift+A` | favourite folders (`Ctrl+Alt+Shift+O/A/R`) -> leader after reclaim (5.9); `quick_nav` and `go_to_anything` become one command |
| Set Bookmark | `Ctrl+Shift+B` | no key | `Ctrl+Shift+B` | `select_block` moves (3.3). Note the `markdown-helpers` Quillin also claims `Ctrl+Shift+B` (7.4) |
| Go to Bookmark... (list) | `Alt+Shift+G` | `Alt+Shift+B` | `Alt+Shift+G` + `Ctrl+Shift+F5` alias | `previous_inline_note` -> `Alt+Shift+K`; `Alt+Shift+B` becomes Status Bar (3.8) |
| Next / Previous Bookmark | `F2` / `Shift+F2` | `list_studio` / `insert_special_character` | `F2` / `Shift+F2` | `list_studio` -> `Ctrl+Alt+Shift+L` (folds moved in 3.1); Special Character -> `Ctrl+Shift+F2` (Lite's, free in QUILL) |
| Clear All Bookmarks | `Ctrl+Alt+B` | (none) | `Ctrl+Alt+B` | freed by Bullets (3.1) |
| Set Bookmark 1..9 | `Ctrl+Shift+N` | tray paste | `Ctrl+Shift+N` | 3.2 |
| Go to Bookmark N | -- | -- | (no chord) | Lite can *set* by number but only *go* by list or `F2`. `Alt+Shift+1..9` is taken by Lite's Recent File N, so no chord family: the list's rows begin with the digit, so digit then Enter is two keys and no new binding |
| Recent File 1..9 | `Alt+Shift+1`..`9` | (none) | `Alt+Shift+1`..`9` | QUILL gains the nine commands **(new)**; free |
| Temp bookmark set / go | -- | `Ctrl+J` / `Ctrl+Shift+J` | `Ctrl+Alt+J` / `Ctrl+Shift+J` | QUILL-only; candidate for retirement once numbered bookmarks land |

### 3.6 Spelling

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| Check Spelling | `F7` | `F7` | `F7` | -- |
| Thesaurus | (none) | `Shift+F7` | `Shift+F7` | Word's key; Lite leaves it unbound |
| Next / Previous Misspelling | `Ctrl+F7` / `Ctrl+Shift+F7` | same | same, plus **`Alt+F7` = Next** as Word's alias in both | The two destructive-by-habit chords become navigation: QUILL's word-at-cursor and Lite's Add Word both leave `Alt+F7` |
| Spelling for This Word | `Shift+F7` | `Alt+F7` | `Alt+Shift+F7` | both move; QUILL's `spell_check_ranked` (today on `Alt+Shift+F7`) becomes a "ranked" option in the F7 dialog |
| Add Word to Dictionary | `Alt+F7` | no command in keymap | `Ctrl+Alt+F9` | deliberately **off the F7 row**, so no spelling habit lands on a command that changes a setting; QUILL registers the command over `_add_word_to_dictionary_scope`; both announce which dictionary the word went to |
| Check While Typing | `Ctrl+Alt+F7` | `toggle_spellcheck_as_you_type` no key | `Ctrl+Alt+F7` | free in QUILL; Lite unchanged |
| Spelling Announcements | `Ctrl+Alt+Shift+F7` | Settings rows only | `Ctrl+Alt+Shift+F7` | free in QUILL; Lite unchanged |

### 3.7 File, clipboard, tools, help

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| New Rich Text / New Plain Text Document | `Ctrl+Shift+N` / `Ctrl+Alt+N` | (none) | same | QUILL gains both **(new)**; `Ctrl+Shift+N` free, `Ctrl+Alt+N` freed in 3.4 |
| Earlier Versions | `Ctrl+Alt+Shift+E` | `restore_previous_version` no key | same | `ai_switch_engine` vacates |
| Page Setup | `Ctrl+Alt+P` | no key | same | free |
| File Encoding and Line Endings | `Ctrl+Alt+E` | two status-cell-only commands | `Ctrl+Alt+E` | QUILL gains one dialog in the File menu **(new)**; `select_line` moves (3.3) |
| Describe Character / Character Details | `Ctrl+Shift+C` / `Ctrl+Alt+C` | `power.describe_character` no key / (none) | same | `copy_with_source` -> `Alt+Shift+C` (free in both); QUILL gains Character Details **(new)** |
| Copy to Tray (next empty) | `Ctrl+Alt+Y` | `copy_to_next_slot` no key | same | free |
| Clear Copy Tray | `Ctrl+Alt+Shift+Y` | `clear_all_tray_slots` no key | same | free |
| Copy to Tray Slot... **(new in Lite)** | -- | leader `Shift+N` (slot N) | `Alt+Shift+Y` chooser in both; QUILL keeps its leader digits | 5.1 |
| Collect / Paste Collected / Clear Collector | `Ctrl+Alt+G` / `Ctrl+Alt+Shift+G` / `Ctrl+Alt+Shift+C` | `collect_clipboard_now` no key / (none) / (none) | same | `ai_grammar_style` vacates; QUILL gains the two missing verbs **(new)** |
| Keep Clip / Recent Clips | `Ctrl+Alt+M` / `Ctrl+Alt+Shift+M` | no key / no key | same | free |
| Markdown Tag | `Ctrl+Alt+I` | `insert_markdown_tag` no key | same | `insert_image` -> `Ctrl+Shift+I`; `document_intake_report` -> leader after reclaim |
| Document Language | `Ctrl+Alt+F6` | `set_language` no key | same | free |
| Expand Abbreviations (toggle) | `Alt+Shift+A` | leader `E` | `Alt+Shift+A` | block comment moves (3.4) |
| Keyboard Shortcuts window | `Ctrl+F1` | `key_cheatsheet` `Alt+Shift+/`; `Ctrl+F1` is a **literal** menu accelerator on Open User Guide outside the keymap | both | alias; Open User Guide -> `Ctrl+Shift+F1` as a keymap entry (free in both) |
| Keyboard Manager | `Ctrl+Alt+Shift+R` | `keymap_editor` no key | same | `remove_favorite_folder` -> leader after reclaim |
| Customize Features | `Ctrl+Alt+Shift+F` | `individual_feature_toggles` no key | `Ctrl+Alt+F10` | both move (rule 9); frees `Ctrl+Alt+Shift+F` for Search in Files (3.1) |
| Back Up / Restore Settings | `Ctrl+Alt+Shift+Q` / `Ctrl+Alt+Shift+D` | `share_export` / `share_import` no key | `Ctrl+Alt+F11` / `Ctrl+Alt+F12` | both move (rule 9); frees `Ctrl+Alt+Shift+Q` (3.3) and removes the collision with QUILL's compare chord |
| Sound Scheme | `Ctrl+Alt+Shift+O` | `sound_events` no key | same | `open_from_favorite_folder` -> leader after reclaim |
| Check for Updates / About | `Ctrl+Alt+U` / `Shift+F1` | no key / no key | same | free |

### 3.8 View and window

| Command | QuillLite | QUILL | Golden | Moves |
| --- | --- | --- | --- | --- |
| Status Bar (show/hide) | `Alt+Shift+B` | (no command, no setting) | `Alt+Shift+B` | QUILL gains it **(new)**; `list_bookmarks` moves (3.5) |
| Focus the status bar | `F6` | `F6` next region | `F6` | see 5.6: QUILL's `F6` already lands in the status bar when it is the next region; the plan makes the status bar the *first* stop from the editor in both |
| Switch Document Mode | `Ctrl+Shift+M` | leader `K` | `Alt+Shift+F` | 3.3 |
| Preview | -- | `Ctrl+Shift+V` | `Alt+Shift+V` | 3.2 |
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

### 4.0 The rule, restated, with the count

`CLAUDE.md` and the QuillLite PRD both say it: **QuillLite may never be ahead of
QUILL.** The small product exists on the condition that anything it needs goes
into the *shared* package and QUILL gets a door to it in the same change. The
reason is not tidiness. A feature the small product has and the big one does not
is invisible: nobody opens QUILL and notices the absence of something they have
only ever seen elsewhere, so it is never reported, and the bigger product
quietly becomes the worse editor.

As of 2026-09-16 that rule is broken **seventeen** times (4.1), and the largest
break is not in the table at all -- it is that QUILL cannot change the size of
its own text (4.3).

The rule has a second half that has never been written down and is the reason
Lite keeps drifting ahead: **value flows both ways.** QUILL is where the editor
work was done; QuillLite reuses those engines and re-implements the doors.
Where QUILL has a capability that is editor-core, shared, and worth a
listener's time, QuillLite should have a door to it too -- switchable off, so
"lite" remains something the user controls rather than something the developer
enforces by omission. That is 4.2, and it is where most of the remaining value
in this plan sits.

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
| Add Word to Dictionary as a command | `_add_word_to_dictionary_scope` reachable only from the context menu | registered command with a key (3.6) |
| Spelling Announcements (spell aloud after a delay, on navigation, suggestions) | `lite_spelling_voice_dialog.py`, `lite_check.py` | **verify** in the spelling audit (section 6) whether QUILL has the feature; if not, the engine moves to `quill/core` and QUILL gets the dialog |
| New Rich Text / New Plain Text Document | `lite_window_file.py` | two commands; QUILL's `default_new_document_format` setting already knows the kinds |
| Keyboard Shortcuts window on `Ctrl+F1`, About on `Shift+F1`, Check for Updates on `Ctrl+Alt+U` | Lite table | keys (3.7) |
| Feature profiles named after what a person wants ("Notepad", "WordPad") that also set the default document kind | `quill/core/lite/features.py` | see 5.8, the grow-up profile |
| Alignment **registered**, not alignment *added* | `format_align` in `main_frame_format_codes.py` already did all four, in rich and Markdown | **Corrected 2026-09-16, and landed.** The first pass said QUILL lacked Align Left/Centre/Right. It did not: they were in the Format > Align submenu and were never registered commands, so they had no key, no palette entry, no keyboard-reference row and no way to be rebound -- the same shape as Underline's hard-coded `Ctrl+U`. Registering them was the whole fix |
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
| Insert Link `Ctrl+K` in Markdown and HTML kinds | Lite has those kinds and a tag picker; a link is the one tag everybody inserts, and Word's key for it is universal | small; shared `quill/core/links` |
| List style cycle on `Ctrl+Shift+L` (bullets -> numbered -> off) | Lite's PRD 8.1 says "revisit numbered lists first" because an ordered list is structure a reader announces; WordPad cycles on this key | small in rich (`ITextPara.ListType`), small in Markdown |
| Toggle Line Comment `Ctrl+/` in plain kind | Lite's PRD accepts that people edit `.py`, `.json`, `.conf` there and already silences spelling for them; a comment toggle is the second half of that concession | small; shared `line_ops` |
| Go To dialog with Line / Bookmark / Heading targets | Word's Go To (5.4); the shared dialog replaces Lite's line-only one | medium, shared |
| Copy All `Ctrl+F8` | trivial and Lite-shaped | trivial |
| Copy to Tray Slot... chooser | Lite's own docstring argues for chosen slots (5.1) | small |
| Set Mark on `Ctrl+Shift+M` | family key (3.3) | keymap |
| A large-file guard | QUILL's `large_file_guard` is the whole fix for V1, and Lite is the app people will open a log in | trivial; move the module to shared |
| The document-text mirror and revision-keyed stats cache | QUILL's #1346 work is the whole fix for V2/V3/S8 | small once V4's `DocumentText` exists |
| An announcement throttle | A5; QUILL's `announcement_throttle_ms` already exists | trivial |

#### Tier 2 -- take these; they are small, shared, and a listener feels them immediately

| Capability | Why Lite | Cost |
| --- | --- | --- |
| **Review Buffer** (`edit.open_review_buffer`) | a read-only dialog holding the selection, so somebody can arrow through text and read it letter by letter with no possibility of typing into their own document. This is the most Lite-shaped thing QUILL has: it costs one dialog and removes a whole class of accident | trivial; `main_frame_selection.py:267-290` moves to a shared dialog |
| **Misspelling List** (`tools.misspelling_list`) | every misspelling in the document as one list you can jump from, instead of `Ctrl+F7` N times. Lite already builds the same data for its live check | small; shared `quill.core.spellcheck` |
| **Quote / Unquote Lines** | replying to email and quoting a log excerpt are Notepad-scale tasks; the engine is `line_ops`, already shared, and Lite already has every other line tool | trivial |
| **Convert Indentation to Spaces / to Tabs** | the code-file concession again: this is the single most common fix a person makes to somebody else's file | trivial; shared |
| **Delete Lines Containing...** and **Hard Wrap** | log triage and email are exactly why people open a plain-text editor; both are QUILL power tools over shared engines with no rich-text complication | small |
| **Heading Organizer** | Lite already lists headings and moves sections; the organizer is the two combined into one list where reordering is arrow keys instead of four commands | medium; shared |
| **Find All Matches results that jump** | Lite has All Matches; QUILL's list is the model where Enter goes to the match | small |
| **Extend Selection Mode**, once P1.2a has fixed it | a sticky Shift: select by navigating, no modifier held, and no "selected" from the reader on every keystroke. QuillLite deleted its own broken attempt at this (`d20fabe`) and has had nothing since; QUILL's mechanism is the one that works on wxMSW | small, after P1.2a; shared |
| **Open Link / Copy Link Address** in the context menu | QUILL offers both when the caret sits on a link (`find_link_at_cursor`); Lite's context menu has spelling and the six clipboard verbs and nothing else. A URL in a text file is the commonest actionable thing in one | trivial; shared `find_link_at_cursor` |
| **Word-count-style Line Statistics** on demand | Lite has Document Statistics; QUILL's per-line statistics answer "how long is this line" for somebody formatting for a screen | trivial |

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


### 4.3 Editor font and text size: QUILL has neither (P0 viability)

The first pass recorded "Editor Font | (Preferences only)". That was wrong, and
the truth is worse. In the whole of `quill/ui`, **no code ever calls `SetFont`
on an editor control** -- every `SetFont` call site is a dialog heading or the
print DC (`grep -rn "SetFont" quill/ui`). `quill.core.settings.Settings` has no
`font_name` and no `font_size` field. There is no zoom command and no text-size
command. QUILL's editor renders in whatever font wx picked, forever.

The one thing called "Font" in QUILL is `format.font_dialog`, menu-labelled
**"&More Font Options..."**, which:

- refuses outside Markdown -- `"Font is only available in Markdown documents"`
  (`main_frame_format_codes.py:343-345`);
- writes *hidden Markdown format codes* into the text rather than changing
  anything about the display or the rich run;
- carries no keyboard shortcut and no entry in the keyboard reference.

So in QUILL: a `.rtf` cannot have the font of a selection changed through a
Font dialog although the rich run mapper exists; a plain document cannot be
made bigger; and the Format menu never says the word "Font".

QuillLite has **Editor Font** (`Ctrl+Alt+F`, the display font for every window),
**Font for Selection** (`Ctrl+Shift+F`, Word's key, the document's own runs) and
**text size in/out/reset** (`Ctrl+=`, `Ctrl+-`, `Ctrl+0`, Notepad's keys).

For an application whose audience includes low-vision users, "you cannot make
the text bigger" is not a parity row, it is a viability failure. It is P0.6a
below. The fix is three commands and two settings in shared code, plus the
rich/plain split already decided in 5.5, plus a Format menu item that says
**Font...** the way WordPad and Word do.

### 4.4 What neither editor has, that Microsoft's three do

Recorded so the omissions are decisions rather than oversights:

| Capability | Where it exists | Decision |
| --- | --- | --- |
| Drag a file onto the window to open it | Notepad, WordPad, Word | **Neither app has a `wx.FileDropTarget` anywhere.** Low value for the audience, real value for a sighted colleague sitting down at the machine. P3, both. |
| Formatted printing | WordPad, Word | Neither prints formatting. Lite at least prefixes `[H2]` to headings (`lite_printing.py:145-162`); QUILL prints a rich document as flat text with no structural marker at all, so QUILL is *behind* Lite on paper. The real fix is RichEdit's `EM_FORMATRANGE` in the shared surface, which makes both genuine. P2. |
| Print preview | WordPad, Word | QUILL has Print Studio, which is the accessible equivalent and is better than a picture of a page. Lite has nothing. P2 for Lite, via the shared `print_pagination` core. |
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

## 5. Model alignments

### 5.1 Copy tray

Both use `quill.core.copy_tray.CopyTray`. QUILL chooses the slot (twelve leader
chords) and pastes by slot with peek on double press; Lite takes the first
empty slot and pastes through a chooser. Golden:

- **Copy to next empty slot** (`Ctrl+Alt+Y`) and **Paste from Tray chooser**
  (`Ctrl+Alt+V`) in both -- the overview path.
- **Copy to Tray Slot...** (`Alt+Shift+Y`) in both: a list of the twelve slots
  with previews, Enter copies into the highlighted one. QUILL keeps its twelve
  leader chords as the fast path; Lite gets chosen slots without twelve chords.
- **Paste slot N** stays QUILL-only (`Ctrl+Alt+Shift+N`) with the peek. Lite's
  chooser previews already answer "what is in slot 3?" without a paste.
- A **full tray** refuses in both (QUILL's model): "Tray is full; choose a slot
  to replace" rather than Lite's silent overwrite of slot 1. Same sentence in
  both, from the core.
- **Recent Clips pastes on Enter** in both (Lite's model); QUILL's dialog keeps
  "Copy to Clipboard" as the second button.
- **The collector is a buffer, not a mode** (Lite's model): Collect Selection
  appends to a buffer and says "Collected 3 pieces"; Paste Everything Collected
  inserts at the caret; nothing is saved unasked and the caret never moves.
  QUILL's system-wide clipboard watcher stays as an optional *source* feeding
  that buffer instead of the document.
- **Restore Deleted Text** offers the last three in both (QUILL's model) with
  Lite's wording ("Restored 42 characters: preview").
- **Paste in a plain document is plain** in both (Lite's model).

### 5.2 Bookmarks

One model in both: nine numbered slots that move with the text and persist per
file, plus a list. QUILL keeps its *named* bookmark vault as the writing
environment's extra, under the same list. Set N `Ctrl+Shift+N`, next/previous
`F2`/`Shift+F2`, list `Alt+Shift+G` (`Ctrl+Shift+F5`) whose rows begin with the
digit so "3, Enter" goes to bookmark 3, clear `Ctrl+Alt+B`. Positions survive
edits by snippet re-anchoring (QUILL's `BookmarkAnchor`, moved under the shared
`BookmarkSet`) rather than Lite's length-delta guess, and every change is
written at once in both.

### 5.3 Selection

Same six structural commands on the same six chords (3.3); the F8 family and
its home-row aliases already agree. `Ctrl+Space` means *sentence* in both.
`Ctrl+Alt+F8` means the same thing in both: a toggle of the F8 marker, which is
Lite's design after `d20fabe`. QUILL's live extend machine is kept and fixed, not
deleted -- see 5.3a, which reverses the first pass on this. One announcement shape in core: scope, then words, and the line
range only when F8 completes. Marks live on the shared `MarkRing` in both, clamp
on pop, and every jump (bookmark, mark, named mark, temp) goes through one
recording seam so `Alt+Left` undoes it.

### 5.3a QUILL's selection extras, re-judged

The first pass proposed retiring three QUILL selection commands. Reading the
code rather than the plan, two of those were wrong, and the correction matters
because it reverses a deletion.

**Extend Selection Mode: keep it, fix it, and consider giving it to Lite.**
The first pass called it "the live-extend design Lite deleted". It is not.
Lite's deleted design stretched a selection on every navigation key-**up**;
QUILL's intercepts the key **before** the control, moves the caret in Python,
and collapses the selection after each move so the control never sees a
selection to fight. That collapse -- which the first pass read as a defect -- is
the mechanism that makes it work where Lite's did not.

What it is *for* is the part no other command covers: a **sticky Shift**. You
select by navigating normally, with no modifier held down, and because the
selection does not exist between keystrokes the reader announces the line or
character you moved to rather than saying "selected" on every press. For a
one-handed user, a switch user, or anyone who finds `Ctrl+Shift+End` a chord
too far, that is the difference between being able to select and not. The F8
marker does not replace it: the marker is for "from here to somewhere I will
navigate to by any means, including Find"; extend mode is for growing a
selection a character or a word at a time.

Its four real defects, all fixable, none architectural:

| | |
| --- | --- |
| O(N) per keystroke | `_move_extend_selection_caret` rebuilds the full line-start table by scanning the whole text on every arrow. `DocumentText` (P0.6c) already has to answer this; use it. |
| PgUp/PgDn are ten lines | Hardcoded `move_vertical(±10)`. The control knows its own page height; ask it. |
| Up/Down break under soft wrap | Movement is by *logical* line, so in a wrapped paragraph one press jumps the whole paragraph. The control moves by visual line; this must too. |
| Word movement stops only at whitespace | Windows word movement also stops at punctuation, so `foo.bar` is one word here and two everywhere else. |

The key collision with Lite's marker toggle is a separate question from whether
the feature lives, and is decided in 3.3: `Ctrl+Alt+F8` becomes the marker
toggle in **both** editors, and extend mode takes its own chord in both.
Once fixed it is a 4.2 Tier 2 candidate for QuillLite -- QUILL to Lite, the
direction the rules allow.

**Select Chunk: keep it, rename it, move it.** `chunk_span` and `word_span`
both use `\w`, so on a word -- `my_variable_name` included -- the two commands
select exactly the same span and Select Word says so more clearly. The
difference is everywhere else: on `-->`, `!==` or `);` Select Chunk takes the
whole operator run and Select Word takes one character; on an indent it takes
the whole whitespace run. That is a code-editing primitive, in a product whose
PRD accepts code editing, and nothing else in either editor offers it. So it
keeps its behaviour, loses `Ctrl+Space` to Select Sentence, and is renamed
**Select Token** -- because "chunk" describes the implementation and "token"
describes what a person gets.

**Temporary bookmark: still the weak one, but decide it later.** `Ctrl+J` set,
`Ctrl+Shift+J` go, one unnamed slot per document, not persisted, no list. Once
nine persistent numbered bookmarks exist with `F2`/`Shift+F2` to walk them, its
only remaining claim is "one key, no list, no commitment" -- a pin you drop and
forget rather than a bookmark you keep. That is a real habit for some people
and it costs two keymap rows. It must leave `Ctrl+J` regardless, because that
is Word's Justify. Whether it then earns `Ctrl+Alt+J` is a question worth
asking a user, not one worth answering from the source.

### 5.4 Go To

Word's Go To is one dialog with a target kind. QUILL has Go to Line, Go to Page
and two Go To Anything commands; Lite has Go to Line and Go To Anything. Golden:
`Ctrl+G` opens a shared Go To with targets Line, Page (QUILL only), Bookmark,
Heading; `Ctrl+Alt+Shift+A` stays the fuzzy Go To Anything in both.

### 5.5 Text size

Lite's "text size" writes `settings.font_size` for every window and re-applies
it with `control.SetFont`, which its own PRD (2.3) says is wrong for rich text:
run point sizes *are* the heading ladder, and wxMSW's `SetFont` on a populated
RichEdit applies to the whole text (6.4, R5 -- verify live). Golden, in both:
in plain, Markdown and HTML kinds the keys change the editor font size; in rich
kind they change the **view zoom** (`RichEditDocument.set_zoom`, already in the
shared surface and used by nothing). Grow/Shrink Font (`Ctrl+Shift+>`/`<`)
stay the *document* change and are unaffected, once the ladder gains the H5 and
H6 sizes it is missing (R7).

### 5.6 Status bar

Both editors have a status bar of focusable cells (QUILL:
`main_frame_statusbar.py`; Lite copied the design). The earlier finding that
QUILL's was "regions plus a spoken summary" was wrong: `F6` cycles regions and
the status bar is one of them. Golden: `F6` from the editor lands in the status
bar first in both; `Shift+F6` walks back; Escape returns to the document;
`Alt+Shift+B` hides and shows it in both. QUILL keeps its layout dialog and
speak-summary chord as extras.

### 5.7 Window model

Lite is one document per MDI child; QUILL is tabs in one frame. Both number
documents (`Alt+1..9`), both walk with `Ctrl+Tab`, and after 3.1 both answer
Word's `Ctrl+F6`. `Ctrl+W` closes the document, `Alt+F4` closes the window
(QUILL: the app, unless tray mode), `Ctrl+Q` exits. Divergent by design;
recorded.

### 5.8 Growing up: the QuillLite profile in QUILL

QUILL's feature profiles (essential, writer, author/student, developer,
accessibility professional, full) are about *audiences*. Lite's (Recommended,
Everything, WordPad, Notepad) are about *shapes*, and two of them carry the
default document kind. The grow-up path is a QUILL profile named **QuillLite**
that:

- shows Lite's nine menus in Lite's order (File, Edit, View, Insert, Format,
  Navigate, Tools, Window, Help) with Lite's items and the golden keys, and
  nothing else -- the AI menu, companions, Quillins and the leader-chord depth
  are off, not hidden;
- carries `default_new_document_format` the way Lite's WordPad/Notepad carry
  `default_mode`;
- on first activation offers **Bring my QuillLite settings**: settings,
  keymap overrides, abbreviations, personal dictionary, copy tray, clip library,
  collector and per-file bookmarks, all of which already share on-disk shapes
  (`share_quill_abbreviations` / `share_quill_dictionary` prove the seam works).

AI leaves the three-modifier chords as part of this: an AI command lives on the
AI menu, the palette and `Alt+Q`; the six chords in 3.4 are returned to editing.

### 5.9 Reclaiming the leader chord

Fifty-eight of sixty-two leader positions are taken, and twenty-one of them are
GitHub, remote-file and local-git administration (`github.*`,
`file.open_github_*`, `file.*_remote`, `manage_remote_sites`). Nobody presses
a chord to rename a repository. Those retire to their menus and the palette,
freeing the positions the relocations in section 3 need (favourite folders,
Insert Table, Replace All, intake report, sound enhancements). Media transport
stays on the leader digits: listening while writing is a real use.

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
| S1 | Broken | Lite | **F7's "Add to Dictionary" writes into QUILL's data folder**, not QuillLite's: `ReviewSession.add_to_dict` passes no `personal_dir`, so a Lite-only machine grows `%APPDATA%\Quill`, the word is flagged again next session unless `share_quill_dictionary` is on, and the completion line cannot say where it went. `Alt+F7` and the context menu write to the right place. | `quill/core/spelling/session.py:230-238`, `spellcheck.py:731-733`, `lite_window_spelling.py:356-366` |
| S2 | Broken | QUILL | **The as-you-type alert is spoken even when `spelling_alert_speech` is off**, and twice when it is on: `_announce_spellcheck_hint` goes through `_set_status`, which always announces. Lite's status write is silent, so the same setting means opposite things in the two editors. | `main_frame_spell_voice.py:351-355`, `main_frame_statusbar.py:938-949`, `lite_window_status.py:440-448` |
| S3 | Broken | QUILL | **"Ignore" in Spelling for This Word writes the document sidecar** (a permanent `.quill-dict.json`), not a session ignore; on an unsaved document the write silently does nothing and the command still announces `Added "word" to dictionary`. | `main_frame_spellcheck.py:543-545, 697-698`; `spellcheck.py:658-660, 734-736` |
| S4 | Worse | both | **Word boundaries are ASCII in the tokenizer and Unicode in the walk-left**: `cafe` with an accent is flagged as `caf`, `naive` with a diaeresis as `na` and `ve`, `dogs'` keeps its apostrophe, and a curly apostrophe splits `don't`. The same word is silent on one path and flagged on another. | `spellcheck.py:67, 514-520, 574-575`; `spelling/voicing.py:103-118` already expects the token the tokenizer cannot produce |
| S5 | Worse | both | **The caret just past a word is "no word"**: `misspelling_at_position` needs `start <= pos < end`, and the caret sits at `end` right after typing. The context menus retry at `pos - 1`; the four keyboard commands do not. | `spellcheck.py:566`; `lite_window_spelling.py:391-396, 500-505`; `main_frame_spellcheck.py:513-522` |
| S6 | Worse | both | **F7 ignores session ignores** in both editors: `ReviewSession` is built without the `IgnoreList` that live check, `Ctrl+F7` and word-at-cursor honour. Lite's docstring claims "every route". | `main_frame_spellcheck.py:169-175`, `spell_review.py:411-416`, `lite_window_spelling.py:49-57` |
| S7 | Worse | both | **Dead settings**: `spell_aloud_delay_ms` is never read (every caller passes its own delay); Lite's "spell misspelled words out letter by letter" does not switch off spelling inside F7 (no `spell_review_spell_word` field); `spell_review_wrap_to_beginning` and `announce_wrap_prompt` have no callers; `_choose_misspelling_with_context` and `_spell_word_for_speech` are dead code carrying a second spelling engine. | `settings_specs.py:2447`, `lite_spelling_voice_dialog.py:283-295`, `announcements.py:50-52, 133, 179, 200`, `main_frame_spellcheck.py:219-365` |
| S8 | Worse | Lite | **Timers outlive the window**: `stop_timers` stops autosave and status only; `_spell_timer` and the pending spell-aloud `CallLater` fire on a destroyed frame (swallowed by a bare except). `check_spelling_at_caret` marshals `GetValue()` out of the RichEdit on every navigation key-up, O(N) per arrow press on a large file; QUILL reuses the document string. | `lite_window_file.py:243-249`, `lite_window_spelling.py:172-180, 200, 303`, `main_frame_typing.py:115-122` |
| S9 | Worse | Lite | F7 on an empty document is silent (QUILL says "Document is empty"); next/previous say "No further misspellings" with no count (QUILL gives "N behind"). | `spell_review.py:408-410`, `lite_window_spelling.py:367-369, 456`, `main_frame_spellcheck.py:153-155, 437-459` |
| S10 | Divergent | both | `share_quill_dictionary` is real but **one-directional and not live**: Lite reads and writes QUILL's `personal.json`; QUILL never reads Lite's; no locking on the read-modify-write; each app caches, so a word taught in one is unseen by the other until restart. QUILL's "project" scope is `Path.cwd()`, i.e. wherever the process was launched. | `core/lite/spelling.py:47-59`, `spellcheck.py:661-663, 686-714`, `main_frame_spellcheck.py:671-683` |
| S11 | Divergent | both | Context menu: QUILL puts corrections at top level; Lite has one "Spelling: word" submenu (asked for 2026-09-13). A menu whose length is the same every time is the one a listener can learn. **Adopt Lite's in QUILL** -- but see the note below the table: QUILL's code argues the opposite, in writing, and the argument is good. | `main_frame_spell_context.py:8-13`, `lite_window_context_menu.py:21-30` |
| S12 | Divergent | both | Earcon fallback: QUILL falls back to `wx.Bell`, Lite to silence; neither resolves through `action_feedback.resolve` as `CLAUDE.md` requires. | `spell_voice.py:357-371`, `lite_window_spelling.py:313-325` |

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

**Parity, Lite ahead (rule violations):** the caret-landing check (arrow onto a word and hear it) exists only in Lite; suggestions spelled aloud as you arrow through the word-at-cursor list exist only in Lite (QUILL uses a bare `wx.SingleChoiceDialog`); Lite announces the check-while-typing state once on open, QUILL never says it. **QUILL ahead (fine):** review of a selection, ranked review, three add scopes, language chooser and on-demand packs (Lite never calls `set_active_language`, so an installed `fr_FR` is ignored), misspelling lists, thesaurus, dictionary status.

### 6.2 Selection, marks and bookmarks

Engine: shared (`quill/core/selection.py`, `marks.py`, `locations.py`, `bookmarks.py`, `numbered_bookmarks.py`); the F8 state machine is duplicated by design.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| L2 | Worse | QUILL | **Extend Selection Mode (`Ctrl+Alt+F8`) collides with QuillLite's marker toggle on the same key, and carries four movement bugs** -- but it is *not* the design Lite deleted, and the first pass was wrong to say so. Lite's `d20fabe` bug was a key-**up** hook that stretched a live selection from anchor to caret after every arrow; on wxMSW an arrow pressed while text is selected collapses to the edge and stops, so the caret never advanced. QUILL's version intercepts the key **before** the control, moves the caret itself, and collapses the selection after each move *precisely so the control cannot fight it*, applying the span only when a non-movement key commits. Opposite mechanism, and QUILL's works. What it costs: `_move_extend_selection_caret` rebuilds every line start by scanning the whole text on each keystroke (O(N) per key); PgUp/PgDn are hardcoded to ten lines rather than a real page; Up/Down move by *logical* line, so soft wrap sends the caret a whole paragraph away; and word movement stops only at whitespace where Windows also stops at punctuation. | `main_frame.py:1218-1219, 2704-2724, 2813-2900`; `lite_window_selection.py:135-145`; `d20fabe` |
| L3 | Worse | QUILL | **Shrink pops a stack that is never cleared**: expand, arrow away, select something else, Shrink jumps to the old span; the stack can hold an empty pair, so Shrink collapses the selection and announces "Shrank selection". Lite computes shrink every time. | `main_frame_selection.py:89-93, 121-127` |
| L4 | Worse | both | **The F8 marker cannot be cancelled.** QUILL's Escape only clears extend mode; Lite's `cancel_extend_selection` has no callers outside tests, and a test asserts Escape does not reach it. F8 twice silently moves the marker in both. | `main_frame.py:2697-2700`, `main_frame_selection_span.py:39-53`, `lite_window_selection.py:91-106, 200-210` |
| L5 | Worse | both | **Reselect only knows some selections**: QUILL's Unselect All and the structural selects never record `_last_selection` (only F8 does); Lite records Select Sentence/Block but not Word/Line/Paragraph. | `main_frame.py:7558-7561`, `main_frame_selection.py:33-96`, `lite_window_marks.py:68-78`, `lite_window_selection.py:232` |
| L6 | Worse | both | **Marks are bare offsets**: no shift on edit, no persistence, in either editor; Lite clamps on pop, QUILL does not. Lite re-implements the mark ring as a plain list (cap 10, no de-dup) instead of using the shared `MarkRing` (cap 20, de-dups). | `quill/core/marks.py:4-58`, `main_frame_selection.py:337`, `lite_window_selection.py:68, 278-355` |
| L7 | Worse | QUILL | **List Bookmarks shows stale positions**: jumps re-anchor by snippet but the list prints the raw stored offset, and the resolved offset is written back without saving, so tab and disk keep the old value until the next Set. | `main_frame.py:11533-11549, 11607-11610` |
| L8 | Worse | both | **Back (`Alt+Left`) does not undo a bookmark or mark jump**: QUILL records only go-to-line/page; Lite routes bookmarks through its `_go_to` seam but pop/list/exchange set the caret directly. | `main_frame.py:11572-11653`, `main_frame_selection.py:258-265, 332-353`, `lite_window_commands.py:314-330`, `lite_window_selection.py:292, 326, 346` |
| L9 | Worse | Lite | **Bookmark shifting is a heuristic**: net length delta plus caret position, so Replace All, undo or any multi-site edit moves the wrong bookmarks; the hook has no loading guard, so a reload that changes length shifts every bookmark. QUILL's snippet re-anchoring is the better model but exists only for named bookmarks. | `lite_window_marks.py:292-307`, `lite_window.py:194`, `quill/core/bookmark_anchor.py:1-30` |
| L10 | Worse | Lite | Bookmarks and last position are written only on close and after save; a remove or clear-all is lost in a crash. QUILL writes on every Set. | `lite_window_marks.py:269-286`, `main_frame.py:11563, 11674` |
| L11 | Worse | QUILL | Shift+F8 with the caret still on the marker announces "Selected 0 characters, line N column M to line N column M"; Lite says "Selection cancelled, nothing selected". Select Word/Line/Paragraph/Block on a blank line announces "Selected line, 0 words"; Lite says "No line at the cursor". | `main_frame_selection_span.py:63-74`, `main_frame_selection.py:71-76`, `lite_window_marks.py:72-74` |
| L12 | Worse | QUILL | List Marks is a message box nothing in it can be jumped to (Lite's list jumps). Exchange Point and Mark only moves (Lite selects the span). Say Selected speaks the whole selection with no cap and is a conditional `Shift+Space` intercept that no menu shows (Lite summarises over 200 characters on `Ctrl+Shift+Y`). | `main_frame_selection.py:344-371`, `main_frame.py:2686-2696, 7563-7570`, `lite_window_selection.py:297-383` |
| L13 | Worse | Lite | Go to Start of Selection calls `SetInsertionPoint(start)` then `SetSelection(start, end)`; on wxMSW the caret ends at `end`, so the promise is doubtful. Needs a live check. | `lite_window_selection.py:176-178` |
| L14 | Divergent | both | Selection announcements differ in shape: QUILL "Selected paragraph, 41 words"; Lite "Selected paragraph, 412 characters, 41 words"; F8 completion differs again. One format in core: scope, words, and the line range only for F8. | `main_frame_selection.py:71-76`, `lite_window_selection.py:414-420` |

**Parity, Lite ahead:** numbered bookmarks with next/previous/clear/labelled list and per-file persistence; Select Sentence as a command; a mark list that jumps; an exchange that selects; Say Selection with a summary and a real key; Unselect remembered for Reselect; empty-structure guards; every bookmark jump feeding Back. **QUILL ahead:** Go To Page, `line,column` in Go To Line, temp bookmark, named bookmarks with snippet re-anchoring and PDF outline import, named marks, review buffer, selection actions (all keyless).

### 6.3 Files, saving and recovery

Engines duplicated: `quill/io/text.py` vs `quill/core/lite/textfile.py`; `core/recovery.py` vs `core/lite/recovery.py`; `core/backups.py` and `core/restore_points.py` vs `core/lite/backups.py`.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| F1 | Broken | Lite | **Save As converts the window before the write.** Rich to plain and HTML to Markdown both `ChangeValue()` the buffer, keep `self.path` pointing at the old `.rtf`/`.html`, and leave the modified flag as it was. If `save(target)` then fails (locked file, full disk) the window holds flattened text under the old name and the next `Ctrl+S` writes it over the original. `ChangeValue` is off the undo stack, so the formatting is gone from the window too. | `lite_window_commands.py:111-159`, `lite_window_markup.py:200-244`, `lite_window_file.py:143-158` |
| F2 | Broken | Lite | **Crash recovery silently rewrites encoding and line endings**: the slot is always UTF-8/LF, `_load_recovery` adopts the slot's encoding, so a cp1252/CRLF or UTF-16 document recovered after a crash is saved back as UTF-8/LF. The original's encoding is never recorded in the slot meta. | `lite_window_file.py:116-117, 227-229`, `core/lite/recovery.py:351-364` |
| F3 | Broken | both | **Unencodable characters are handled silently in both directions**: Lite's `encode_text` uses `errors="replace"`, so a cp1252 file that gained an em dash or emoji saves with `?` and announces "Saved"; QUILL's save raises `UnicodeEncodeError`, which `_run_command` swallows into "Command failed: file.save". Notepad warns and offers UTF-8. Neither editor tells the user. | `core/lite/textfile.py:99-107`, `main_frame.py:7876-7880, 8719-8725` |
| F4 | Broken | QUILL | **Save As HTML and Save As Plain Text are not atomic and force UTF-8**, discarding the read encoding and BOM; rich-mode `.md`/`.html` saves ignore `document.encoding` and `line_ending` (always UTF-8, LF); the remote save copy is a plain `write_text`. Every other document writer is atomic. | `quill/io/export.py:245-252`, `main_frame_rich_mode.py:170-187`, `main_frame.py:8521` |
| F5 | Broken | QUILL | **The external-change watcher auto-reloads a clean tab of any suffix with `path.read_text()`**: a `.docx`/`.rtf`/`.pdf`/`.epub` tab rewritten by Word is replaced with binary decoded as replacement characters and marked clean. The "Open Disk Version in New Tab" button selects the existing tab instead of opening a second one, so the compare it promises never happens. | `main_frame.py:3137-3230, 6870-6876` |
| F6 | Broken | QUILL | **Encoding and line-ending changes do not dirty the document**, so Close does not prompt and the change is lost unless `Ctrl+S` is pressed; the two commands are in no menu (status-cell or palette only); the chooser has no "UTF-8 with BOM" although `encoding_tools.ENCODING_CHOICES` has the label; **UTF-16 is never detected on open** (decodes as cp1252 NUL garbage). Lite detects UTF-16, offers BOM, dirties, and has a menu item. | `main_frame.py:7581-7612`, `quill/io/text.py:44-96`, `core/lite/textfile.py:45-50, 85-93` |
| F7 | Worse | Lite | Earlier Versions of an `.rtf` are plain text (the backup stores `GetValue()` and restore replaces every run) and the dialog does not say so. File Encoding and Line Endings is enabled in rich mode, dirties, announces "Saving as UTF-16, CRLF", and `_write_rtf` never reads either; the status cells show "UTF-8 / CRLF" for every `.rtf`. | `lite_window_tools.py:308-386`, `core/lite/backups.py:224`, `lite_window_file.py:186-197`, `lite_window_status.py:390-391` |
| F8 | Worse | Lite | "No Markdown could be made from this HTML; saved unchanged" and "Converted HTML to Markdown" are spoken *before* the save runs. A classic-Mac CR file opens the format dialog with CRLF preselected, so OK silently converts it. UTF-16 big-endian round-trips as little-endian on a no-edit save, against the module's own byte-honesty contract. | `lite_window_markup.py:229, 243`, `lite_dialogs.py:331, 350-355`, `core/lite/textfile.py:87-88, 107` |
| F9 | Worse | Lite | A failed `_load_recovery` still sets the slot, marks modified and adopts the path; closing that empty window and answering "No" deletes the only copy of the work. A forced close (`CanVeto() == False`) skips the prompt *and* deletes the slot; no `EVT_END_SESSION` handler exists, so recovery survives shutdown only because children are destroyed rather than closed. | `lite_window_file.py:120-129`, `lite_window.py:443-457` |
| F10 | Worse | QUILL | `save_all_files` never restores the active tab; `save_file` relies on `EVT_TEXT` having synced the document (Save As syncs explicitly); the OS session-end handler is bound on the frame while wx delivers the event to the App, so a logoff with dirty documents never prompts. | `main_frame.py:7915-7923, 7840-7913, 3860-4046` |
| F11 | Worse | both | New documents default to **LF** in QUILL and **CRLF** in Lite; Notepad, WordPad and Word all write CRLF. No setting exposes it in either. | `quill/core/document.py:9-13`, `lite_window.py:139-140` |
| F12 | Worse | both | Close prompt wording differs and both use Yes/No: Lite "Save changes to notes.txt?", QUILL "You have unsaved changes. Save before Close?". Notepad and Word name the file and label the buttons Save / Don't Save / Cancel, which a listener does not have to hold a question in memory to answer. | `lite_window.py:428-441`, `main_frame.py:6020-6047` |
| F13 | Worse | Lite | Print settings are in-memory only (page setup lost at exit); the print and page-setup dialogs bypass the Lite modal contract; the settings-backup `.qsf` is the one non-atomic writer in the Lite tree; opening a missing path offers to create it and `touch()`es it before anything is typed. | `lite_printing.py:60, 184-203`, `lite.py:138, 283-284, 324-343`, `lite_window_settings_backup.py:66` |
| F14 | Divergent | both | Lite restores every crash slot as a window without asking (one spoken line after); QUILL shows a recovery dialog. Word's Document Recovery lets the user choose. Lite session restore is automatic (Notepad 11 behaviour); QUILL has only manual, keyless Snapshots. Neither detects a read-only file at open. | `lite.py:195-198, 254-259`, `main_frame.py:4373` |

**Parity, Lite ahead:** New Rich / New Plain commands, UTF-16 detection, UTF-8-with-BOM choice, encoding change dirtying the document, a menu-bound encoding command, lossy-flatten confirmation, automatic session restore, bounded backup retention (20 per file), offer-to-create on a missing path. **QUILL ahead:** real conversion at write time through `quill/io`, restore points thinned by age, external-change detection (buggy), Save All, Open from URL, Snapshots, Print Studio.

### 6.4 Formatting and document kinds

Rich engine shared (`richedit_editing.py`, `richedit_rtf_surface.py`, `heading_ladder.py`, `heading_levels.py`, `markdown_sections.py`, `structure_announce.py`); the wrappers are duplicated.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| R1 | Broken | QUILL | **Rich bullets are unreachable.** `format_rich_bullets` is defined and never called; `toggle_bullet_list` has no rich branch and refuses with "Bullet List is only available in Markdown or HTML documents". The module docstring promises the opposite. | `main_frame_rich_paragraph.py:11-14, 77`, `main_frame.py:16483, 5420-5437` |
| R2 | Broken | QUILL | **Turning a list off strips every list in the document** (`strip_list_markers` over the whole text, then `SetValue`, which also clears the RichEdit undo stack) and announces only "Bullet List removed". | `main_frame.py:16497-16505`, `markdown_sections.py:747` |
| R3 | Broken | QUILL | **Heading N in Markdown prepends** instead of rewriting: `### Notes` becomes `## ### Notes`; mid-line with no selection gives `foo ## bar`; a multi-line selection heads only the first line. Lite fixed exactly this with the shared `set_heading_level`, whose docstring names the bug; QUILL never adopted it. | `main_frame.py:16299-16318`, `tagging.py:274-280`, `heading_levels.py:188-236` |
| R4 | Broken | QUILL | **Dark mode may write grey text into every saved `.rtf`**: `_apply_theme` calls `SetForegroundColour` on the rich control (wxMSW applies it as `SCF_ALL` character colour) and nothing resets to `tomAutoColor` before the native save. Lite guards both directions. Verify live before fixing. | `main_frame.py:4632-4636`, `main_frame_rich_mode.py:110`, `lite_window_theme.py:9-15`, `lite_window_file.py:194, 213` |
| R5 | Broken | Lite | **Text size and theme changes may re-level every heading in a rich document**: `_apply_editor_font` calls `control.SetFont(11pt)` on a populated rich control on every `Ctrl+=`, dark-mode toggle or font change in any window; wxMSW `SetFont` applies to the whole text, which is what the module docstring says it avoids. Tests use a fake control. Verify live. | `lite_window_theme.py:91-113`, `lite.py:417`, `test_lite_view_commands.py:72-106` |
| R6 | Broken | Lite | **Switch Document Mode discards formatting**: rich to plain is `GetValue()` text only (confirmed, No default) with no Markdown conversion; plain to rich leaves `## Title` as literal hashes; `ChangeValue` twice clears undo; `path` is dropped on suffix mismatch. QUILL converts both ways with a lossy inventory. | `lite_window_theme.py:63-91`, `main_frame_rich_mode.py:589-666` |
| R7 | Worse | both | **The font ladder lacks H5 (11.5) and H6 (10.5)**: Shrink on H4 lands on 11 = bold body, heading gone; Grow on H6 likewise. Neither editor announces the level change, only "N point". | `richedit_editing.py:104-121`, `heading_ladder.py:27`, `main_frame_rich_paragraph.py:140`, `lite_window_format.py:311` |
| R8 | Worse | QUILL | Rich `Ctrl+B/I/U` announce the verb ("Bold") with no state; the shared `toggle_font_attr` returns the state and Lite says "Bold on / Bold off". | `main_frame_rich_mode.py:377-399`, `richedit_editing.py:285-297` |
| R9 | Worse | both | **Native RichEdit hotkeys leak into plain and Markdown documents** because plain documents are `TM_RICHTEXT` controls: in QUILL unbound `Ctrl+U`, `Ctrl+L`, `Ctrl+R` underline or re-align a Markdown buffer natively (not dirty, not announced, not saved, but visible and undo-stacked); in Lite every native chord it does not bind (`Ctrl+Shift+=` superscript and friends) does the same. Paste is guarded; keys are not. | `main_frame.py:2052-2068`, `richedit_editing.py:243-254`, `lite_window_commands.py:223-236` |
| R10 | Worse | Lite | "Press Control Shift M to switch to rich text" is wrong: the ring is plain, Markdown, HTML, rich, so from Markdown that key lands on HTML. | `lite_window_format.py:78-94`, `lite_window_markup.py:93-98` |
| R11 | Worse | QUILL | Choosing "Convert to Rich Text" in the plain-text formatting prompt converts and then **drops the Bold that was asked for**. | `main_frame_rich_mode.py:463-482`, `main_frame.py:16161-16163` |
| R12 | Worse | QUILL | Outline Navigator and Quick Nav are text-only: an `.rtf`/`.docx` tab is "plain" so "Outline is not available"; `all_headings()` on the shared surface is called only by Lite. `next_structure` (`Alt+Down`) is blind in rich mode. | `main_frame.py:10176-10228, 10850, 11000-11002`, `richedit_editing.py:348` |
| R13 | Worse | Lite | Describe Formatting answers "Plain text" inside `**bold**` or `## ` in a Markdown document; QUILL parses it. Move Section passes no `markup_kind`, so HTML sections are not moved. | `lite_window_format.py:163, 339-346`, `format_codes.py:494-524` |
| R14 | Worse | both | `set_heading` assigns `font.Size` then `font.Bold` as two TOM assignments with no edit collection: one `Ctrl+Z` after "Heading 2" likely leaves a 16-point non-bold paragraph nothing recognises as a heading. Same shape in Lite's selection font dialog. Verify live. | `richedit_rtf_surface.py:430-461`, `lite_window_format.py:325-326` |
| R15 | Divergent | both | Heading navigation is duplicated with different wording ("Moved to next heading, H2: title" vs "Heading 2: title"); word wrap uses `TE_DONTWRAP` in QUILL and `EM_SETTARGETDEVICE` in Lite; the structure-cue wrappers are duplicated around one shared `StructureAnnouncer`. | `main_frame.py:10061-10125, 7669-7683`, `lite_window_headings.py:84-140, 225-262` |

**Parity, Lite ahead:** Body Text; absolute heading rewrite in Markdown; bold state announced; rich bullets that work; headings list in rich; next/previous heading on a plain key; underline, alignment, text size, selection font (QUILL's `open_font_dialog` refuses outside Markdown although the rich run mapper exists), document language and editor font all keyed. **QUILL ahead:** real conversion on mode switch; Markdown lists, task list, table, link, image, rule, blockquote, code block, footnote on chords; Describe in Markdown; hidden-codes font/size/colour/highlight; Reveal Codes; Style Headings; List Manager; move-section in HTML.

### 6.5 Shell: status bar, windows, help, features

Shared: the palette, Go To Anything, the support dialog, the F1 dialog and `app_features`. Duplicated: the status bars, keymap editors, feature models and F1 resolvers.

The disputed fact first: QUILL's status bar **is** a row of focusable button cells that `F6` reaches as one of up to five regions (Editor, Reveal Codes, Document Tabs, Preview, Status Bar), with arrows, Enter, Escape; the spoken summary on the leader chord is an extra. What QUILL lacks is a whole-bar show/hide. The first-pass finding is corrected in 5.6.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| H1 | Broken | Lite | **A hand-edited keymap can bind a bare letter**: `normalise_chord` accepts `Win`/`Cmd`, `wx.AcceleratorEntry.FromString("Win+A")` returns True with no modifier, so `"cmd_x": "Win+A"` in `lite_keymap.json` runs the command when the user types `A`. `load_keymap` is the trust boundary and does not reject it. | `core/lite/keymap.py:83-95, 415-420`, `lite_window_menus.py:183-192` |
| H2 | Worse | Lite | The Keyboard Manager's wx-can-fire check runs only from the Audit button, never at assign time, so a chord wx refuses is assigned and inert (the one failure that looks like success). QUILL's editor checks at assign time. | `lite_keymap_editor.py:341-369, 482-497`, `keymap_editor.py:333-341` |
| H3 | Worse | QUILL | **GATE-13 over-announce in the status bar**: every cell focus, including each arrow press, announces "label, value" although the button already carries the name and label, so each press is spoken twice; leaving the bar announces "Returned to editor", which is a focus move the reader already speaks. The gate cannot see it (lambda-bound handler, announce one call deeper). Lite deliberately does neither. | `main_frame_statusbar.py:628-631, 757-776, 800-802`, `lite_window_status.py:469-483, 519` |
| H4 | Worse | QUILL | `Open User Guide` carries a **literal** `\tCtrl+F1` accelerator outside the keymap: absent from the keyboard reference, unrebindable, and a silent double claim for anyone who binds `Ctrl+F1`. | `main_frame_menu.py:3331` |
| H5 | Worse | QUILL | Mnemonic collisions inside Tools > Customize and Support (`&Export...` three times, `&Import...` twice); the access-key test checks only top-level titles. | `main_frame_menu.py:3254-3262`, `test_menu_bar_access_keys.py:82-104` |
| H6 | Worse | QUILL | Two Go To Anything front doors: `navigate.go_to_anything` (the shared dialog, leader) and `navigate.quick_nav` ("Quick Nav (Go to Anything)", a landmark index, unbound). Both registered with `binding=None` although the keymap binds one, so the palette shows no key. | `main_frame_commands.py:1825-1829, 2332-2341`, `main_frame.py:4752-4770, 10204-10228` |
| H7 | Worse | Lite | Contradictory comments on `Alt+F4`: the child says it closes the document, the shell says it exits the app (MDI convention); nothing binds `Ctrl+F4`, the MDI child-close key. Needs a live check; the child comment is probably wrong. | `lite_window.py:112-127`, `lite_shell.py:115-124` |
| H8 | Worse | QUILL | Word Count is a message box, Line Statistics and `document.summary` are unbound; Describe Character is an unbound modal. Lite speaks all of these. | `main_frame.py:11955, 4730`, `main_frame_power_tools_menu.py:734, 742`, `classic_editor.py:118` |
| H9 | Divergent | both | QUILL has two "quiet" concepts (`tools.sound_toggle` writing `sound_enabled`, and `verbosity.toggle_quiet`); Lite has one, on the same shared setting. Lite reserves the Insert key in its keymap editor; QUILL reserves nothing. Lite's keymap editor lacks assign-time checks; QUILL's lacks a reserved list. Port each guard to the other. | `main_frame.py:8989`, `verbosity.py:63`, `core/lite/keymap.py:137-142` |

**Parity, Lite ahead:** whole-bar status show/hide; recent file N on `Alt+Shift+1..9`; spoken Describe Character with a detail window; spoken statistics; every Help-menu item keyed. **QUILL ahead:** per-cell status layout, `Shift+F6`, tutorials, searchable shortcut dialog plus HTML reference, ten profiles with per-feature toggles, key describer, leader chord. **Gap in both:** no QUILL profile reproduces QuillLite's shape (5.8).

### 6.6 Clipboard family

Engines shared (`copy_tray.py`, `clip_library.py`, `clipboard_collector.py`, `deletion_ring.py`); everything a person touches is duplicated per app.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| C1 | Broken | Lite | **The automatic clip-library tier is dead code**: `_remember_copy` is defined and never called; the copy/cut cue handler only plays the earcon. The module docstring, the Recent Clips help text and the Preferences blurb all promise "a rolling history of the last two hundred things copied". Only Keep Clip fills it. QUILL's auto-capture works but is opt-in and never captures a Cut. | `lite_window_clipboard.py:22-25, 121-149, 268-294`, `core/lite/features.py:107-110`, `main_frame.py:2035`, `core/settings.py:79` |
| C2 | Broken | QUILL | **Tray paste, Restore Deleted Text, Duplicate Selection and the collector rewrite the whole document** for a local insert (`_replace_document_text` = select all + `WriteText` of plain text) with no rich-mode guard. On the RichEdit surface that is every heading, bold and font run replaced by the format at position 0 in exchange for one pasted line. Lite inserts locally. **Verify live in an `.rtf`**; if confirmed it is data loss with one `Ctrl+Z` as the cure. The same helper serves every QUILL line and case tool (6.7). | `main_frame_copy_tray.py:235, 319`, `main_frame_power_tools.py:97-108, 449`, `main_frame_line_commands.py:187`, `main_frame.py:17393-17398` |
| C3 | Worse | QUILL | **The Copy Tray dialog destroys labels and pins on edit**: `CopyTray.copy_to` builds a fresh slot (no label, unpinned) and every write path uses it; editing a slot's text drops its label and its pin; Copy to Tray Slot and promoting a clip overwrite a pinned slot without a word. A pin protects only an *empty* slot from Copy to Next Empty. | `core/copy_tray.py:50-57, 97-102`, `copy_tray_dialog.py:186-189, 238-251`, `main_frame_copy_tray.py:156`, `main_frame_clip_library.py:369` |
| C4 | Worse | QUILL | **The clipboard collector saves the file unasked and speaks twice**: every collected clip appends to the document, moves the caret to the end, calls `save_file()` whenever the document has a path (from a 750 ms poll), so "Saved name" and "Collected clipboard text" are spoken per copy in any program. Read-only, empty-clipboard and already-collected refusals are silent. | `main_frame_power_tools.py:397-408, 436-456`, `main_frame.py:7892` |
| C5 | Worse | QUILL | **Single-press tray paste is delayed by the multi-press window** (400 ms): characters typed inside it land before the pasted text; nothing says so. | `main_frame_copy_tray.py:143, 187-205` |
| C6 | Worse | both | **The two editors document opposite facts about `Replace` and undo**: QUILL's `_atomic_replace` (#131) says wx `Replace` records two undo entries and avoids it; Lite's `_insert` and `_apply_line_op` promise one undo step and use `Replace`; QUILL's own Paste Text Only uses `Replace` over a selection. No test settles it; in at least one app `Ctrl+Z` after Paste Text Only lands on an intermediate state. | `main_frame.py:17349-17359`, `lite_window_clipboard.py:92-102`, `lite_window_lines.py:24-27, 72-74`, `main_frame_rich_paragraph.py:175-179` |
| C7 | Worse | Lite | The tray-empty message names the wrong key ("Control Shift 0 copies into it"; Copy to Tray is `Ctrl+Alt+Y` and rebindable, and `Ctrl+Shift+0` is QUILL's paste slot 10). "Collector cleared" is announced whether or not anything was in it. The collected-piece count counts dividers, so a piece containing `----` miscounts. | `lite_window_clipboard.py:178, 224, 235-237` |
| C8 | Worse | QUILL | GATE-13: the Copy Tray dialog announces "Slot N loaded" on every list move. Keep Clip, Copy All, Copy with Source, Restore Deleted Text, Duplicate Selection and every collector message report through `_set_status`, which is throttled and bypasses the verbosity/braille service, so none reach braille or the announcement log. `_copy_to_clipboard` has no retry and no `try` around `SetData`; a locked clipboard raises past the handler. `read_clipboard_text` shows wx's own error dialog on its last retry and is called from the collector timer and from the tray dialog's selection handler, so a modal can appear from a timer or a list move. Open Clip Library bypasses `_show_modal_dialog`. | `copy_tray_dialog.py:174, 208, 218-225`, `main_frame_clip_library.py:296-298, 346`, `main_frame.py:19489-19498`, `clipboard_retry.py:80-81` |
| C9 | Divergent | both | Tray full: QUILL refuses and says so, Lite overwrites slot 1 and reports success (**QUILL's wins**). Restore Deleted Text: QUILL lists the last three, Lite offers only the newest so two of the ring's three entries are unreachable there (**QUILL's list, Lite's wording** "Restored 42 characters: preview"). Recent Clips: QUILL's dialog only copies to the system clipboard and expects a second `Ctrl+V`; Lite pastes on Enter (**Lite's**). Clear tray: QUILL asks Yes/No without a count, Lite counts without asking (**both**: "Clear 7 filled slots?"). Paste in a plain document: Lite makes `Ctrl+V` plain there; QUILL pastes whatever the control accepts (**Lite's**). Collector: QUILL is a mode where the document is the collector; Lite is a buffer filled by an explicit key and pasted where the caret is (**Lite's** for a listener: the caret never moves and nothing is written unasked; keep QUILL's system-wide watcher as a *source* for the buffer). Magic Paste's keymap comment says it "moves to QUILL key, V"; no handler references it and it is menu-only. | `copy_tray.py:155-175`, `classic_editor.py:80-118`, `lite_window_lines.py:171-186`, `clip_library_dialog.py:194-202`, `lite_window_clipboard.py:194-211, 254-279`, `lite_window_commands.py:223-236`, `keymap.py:621-623` |

**Parity, QUILL ahead:** chosen-slot copy, direct paste and peek, tray search, slot label/pin/edit/fill, clip-library search/favourite/rename/remove/combine/promote/save-as-abbreviation, Copy with Source, Copy All, Magic Paste, three-deep restore. **Lite ahead:** Recent Clips pastes, plain paste in plain documents, local inserts, counted announcements. **Neither:** a Clear Clip Library command (`ClipLibrary.clear` is unreachable in both); Backspace, Delete, Cut and Undo never feed the deletion ring in either app.

### 6.7 Lines, case and whitespace

Engines shared (`quill/core/line_ops.py`, `format_ops.py`, `transforms.py`); the wiring is duplicated.

The seventh family audit was cut short by a rate limit; these are the findings from a direct read of the three QUILL helpers and Lite's one.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| N1 | Worse | QUILL | **Three helpers, three scopes.** With no selection, `_apply_text_block_operation` (sort, reverse, dedupe, trim, tidy, quote, indentation) acts on the **current line**, so Sort Lines with no selection sorts one line and announces "Sorted lines ascending"; `_power_tools_transform_selection_or_document` (trim blank, remove blank, keep unique, numeric/length/date sorts, shuffle) and `_transform_selection_or_document` (case) act on the **whole document**. Lite's one helper always means "selection, else whole document" and warns before a whole-document rewrite in rich text. | `main_frame.py:17439-17462, 16175-16188`, `main_frame_power_tools.py:110-123`, `lite_window_tools.py:62-122` |
| N2 | Worse | QUILL | **No no-op detection and no counts**: every QUILL line tool announces its past-tense status even when nothing changed; Lite says "No lines to change" and otherwise "Sorted 12 lines" / "Removed 2 lines" with the count chosen per verb. | same |
| N3 | Worse | QUILL | All three helpers write through `_replace_document_text` (select all + `WriteText`), the same path as C2: rich formatting at risk, and the whole document replaced for a one-line change. Lite uses one `Replace` on the changed span. | `main_frame.py:17393-17398, 17459`, `lite_window_tools.py:102` |
| N4 | Worse | QUILL | **The same verb is registered twice with different words**: `power.keep_unique_lines` ("Kept unique lines (removed duplicates)", `Alt+Shift+K`) and `edit.remove_duplicate_lines` ("Removed duplicate lines", no key) both call `format_ops.remove_duplicate_lines`. `power.trim_blank_lines` (two ends only, `Ctrl+Shift+Enter`) and `power.remove_blank_lines` (every blank line, no key) are two commands whose names a listener cannot tell apart; Lite's "Remove Every Blank Line" is the second one. The `line-tools` Quillin ships Duplicate Line, Delete Line and Move Line Up/Down a third time. | `main_frame_power_tools.py:1477-1487, 1519-1523`, `keymap.py:582-583`, `quill/quillins_bundled/line-tools/manifest.json` |
| N5 | Divergent | both | Case tools with no selection act on the whole document in both editors. Word's `Shift+F3` acts on the word at the caret. A whole-document UPPERCASE from a stray chord is one `Ctrl+Z` away in both, but Lite at least warns in rich text. Recommendation: no selection means the **word at the caret** in both, as Word does. | `lite_window_tools.py:157-176`, `main_frame.py:16175-16188` |

**Parity:** the engines are one and the same in both editors; the differences are in scope, wording and the write path. QUILL-only extras (numeric/length/date sort, shuffle, delete lines containing, indentation conversion, hard wrap) are fine as extras once they share the one helper.

### 6.8 Typing and input

Engines shared (`quill.core.autoformat`, `quill.core.abbreviations`); the
wiring, the gating and the defaults are all duplicated.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| T1 | Worse | Lite | **Autoformat marshals the whole document on every keystroke.** `_autoformat` calls `control.GetValue()` to read *one* preceding character, and `_maybe_expand` calls it again for abbreviations. QUILL reads `GetRange(pos-1, pos)`. O(N) per character against O(1), on the hottest path in the app. Same root cause as V2 and S8. | `lite_window_typing.py:227, 264`; `main_frame.py:2094, 2105` |
| T2 | Worse | Lite | **The feature description promises a rule that does not exist**: Customize Features says autoformat gives "curly quotes, em dashes, and a capital at the start of a sentence"; `_autoformat` implements quotes and dashes only. Either write sentence capitals or stop advertising them. | `core/lite/features.py:143-148`, `lite_window_typing.py:222-236` |
| T3 | Worse | both | **Tab means the opposite thing by default**: QUILL `_tab_inserts_literal = False` (Tab indents), Lite `= True` (Tab inserts a tab character). Both status bars then say "Indent" or "Tab char" for the same cell, so each bar is honest and the defaults still disagree. Notepad inserts a tab; Word indents. Rule 1 gives it to the document kind: a tab character in plain and code kinds, an indent in rich -- decided once, in core. | `main_frame.py:1311`, `lite_window_typing.py:91`, `main_frame_statusbar.py:257`, `lite_window_status.py:386` |
| T4 | Worse | both | **Autoformat is gated by app, never by document kind.** QUILL has two settings (`autoformat_smart_quotes`, `autoformat_dashes`) in Preferences; Lite has one feature flag in Customize Features, off by default with the right reason written down ("actively wrong in a configuration file"). Once either is on, a typed quote curls inside a `.json` or a `.py` in both editors. The gate belongs on the kind, which both editors already know. | `main_frame.py:2093-2094`, `core/lite/features.py:145-147` |
| T5 | Divergent | both | Same concept, two control surfaces and two granularities: one flag in Lite's Customize Features, two checkboxes in QUILL's Preferences. Take QUILL's granularity and Lite's default, and expose both in both. | as above |

### 6.9 Large documents (the QuillLite viability bar)

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| V1 | Broken | Lite | **No large-file guard of any kind.** QUILL has `quill/ui/large_file_guard.py` -- it sizes the file, warns, and opens deliberately. Lite's open path never calls `stat()`; a 200 MB log opens by `read_text` into a `wx.TextCtrl` with no warning, no progress and no way out. For a Notepad replacement this is the scenario, not an edge case. | `main_frame.py:6898-6949`; nothing matching `st_size` in `quill/apps/lite_*` or `core/lite/textfile.py` |
| V2 | Broken | Lite | **Three full-document scans per status refresh, with no cache.** `_cell_values` calls `GetValue()` and runs `compute_document_stats` over the whole text, then `_heading_text` calls `heading_level_at(GetValue(), ...)`, then `_list_text(text)` scans again. QUILL solved exactly this (#1346): stats are cached against `document.revision`, and display code reads the document's own Python string through `_document_text_for_display` -- "zero marshals", by contract. Lite has neither the mirror nor the cache, so every coalesced refresh -- every pause after typing or arrowing -- costs three passes plus a wx marshal. | `lite_window_status.py:367-392, 405-412`; `main_frame_statusbar.py:140-175` |
| V3 | Worse | Lite | The live spell check marshals `GetValue()` on navigation key-up (S8) and the heading cue does it again. Five separate O(N) readers of a buffer that has a Python-side copy available. | `lite_window_headings.py:84, 151-154, 203, 220`, plus S8 |
| V4 | Worse | both | **Neither editor's document model is incremental.** QUILL's mirror makes reads free but every edit still re-sets a whole string; Lite has no mirror at all. The shared fix is one `DocumentText` object in core, owned by both editors, holding the Python string, bumping a revision, answering `line_column_for_position` and `stats` from a cache, and being the only thing display code may read. That one object retires V1-V3, S8 and half of 6.7's write-path problems. | -- |

The acceptance test for this family is a number, not a feeling: open a 50 MB
`.log` in both editors, hold Down for five seconds, and measure. Lite must not
be more than 20% slower than QUILL, and neither may exceed one status refresh
per 250 ms.

### 6.10 Printing

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| PR1 | Worse | QUILL | **A rich document prints as flat text with no structural marker.** Lite prefixes a heading line with its level so the structure survives paper; QUILL prints `editor.GetValue()` and nothing else. The small product is ahead on paper. | `main_frame_print.py:245-251`; `lite_printing.py:145-162` |
| PR2 | Worse | Lite | **Print settings live in memory only**: page setup and printer choice are lost at exit, so margins are re-entered every session (F13, repeated here because it belongs to this family). Lite also has no print preview of any kind, while QUILL's Print Studio computes real pagination from the same DC the job uses. | `lite_printing.py:60, 175-203`; `main_frame_print.py:253-288` |
| PR3 | Worse | both | **Neither prints formatting.** RichEdit exposes `EM_FORMATRANGE`, which is how WordPad prints; the shared `richedit_rtf_surface` is where it belongs. Until then, adopt Lite's honest heading marker in QUILL (one afternoon) rather than leaving QUILL's silent flattening. | as above |
| PR4 | Divergent | both | QUILL has header/footer editing, page selection and Print Studio; Lite has page setup and print. Right for the two products; recorded. | `main_frame_print.py:210-244` |

### 6.11 Settings, profiles and the grow-up path

Measured: `quill.core.settings.Settings` has **341** fields;
`quill.core.lite.settings.Settings` has **38**. Twenty-two names are shared.

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| G1 | Worse | both | **The same concept has two names in eight places**, which is precisely how the two apps drift without anyone deciding to: `autosave_seconds` / `autosave_interval_seconds`, `word_wrap` / `soft_wrap`, `spell_check_while_typing` / `spellcheck_as_you_type`, `default_mode` / `default_new_document_format`, `font_name`+`font_size` / (nothing), `show_status_bar` / (nothing), `restore_session`+`session_files` / (nothing), `recent_files` / `recent_files_limit`. Each pair needs either one name or one row in the mapping table 5.8's "Bring my QuillLite settings" depends on. | `core/settings.py`, `core/lite/settings.py` |
| G2 | Worse | both | **`theme` is one shared name with two defaults**: Lite `"dark"`, QUILL `"system"`. The same person launching both gets two different-looking editors on day one, from one setting spelled one way. Pick one -- `"system"` is the accessible answer, because it follows the OS high-contrast choice -- or write down why Lite differs. | `core/lite/settings.py`, `core/settings.py` |
| G3 | Worse | QUILL | **QUILL has no whole-bar status toggle**, which the first pass got half right: `status_bar_hidden` is a list of *cells* to hide, not a switch for the bar. Lite's `show_status_bar` is the switch. QUILL needs the switch as well as the list (3.8, P1.10). | `core/settings.py:527`, `settings_normalizers.py:83-134` |
| G4 | Worse | QUILL | **No session restore.** Lite has `restore_session` and `session_files` and reopens last session's documents unless files were named on the command line (Notepad 11's behaviour). QUILL has manual, keyless Snapshots only (F14). | `lite.py:185-186, 228-252` |
| G5 | Divergent | both | Lite's feature model is `core/lite/features.py` (areas, `DEFAULT_OFF`, four shape-profiles); QUILL's is `FeatureManager` with ten audience-profiles. Both are right for their product; 5.8's QuillLite profile is the bridge. Recorded so nobody unifies them by accident. | `core/lite/features.py:205-300` |

### 6.12 Startup, shell integration and announcements

| # | Severity | Editor | Finding | Evidence |
| --- | --- | --- | --- | --- |
| A1 | Worse | Lite | **The installer offers "Open with" for `.txt` and `.rtf` only**, though QuillLite edits Markdown and HTML as first-class kinds. `.md`, `.markdown` and `.html` belong in the same optional component. | `standalone/quilllite/installer/quilllite.iss:157-158` |
| A2 | Worse | QUILL | **QUILL's `OpenWithList` covers `.txt .md .rst .log .csv .json` and omits every format `quill/io` converts** -- `.rtf`, `.docx`, `.odt`, `.html`, `.epub`. A person who installed QUILL to open `.docx` files cannot reach it from Explorer's Open With. | `installer/quill.iss:160-167` |
| A3 | Divergent | both | Neither app ever takes a default handler, both by explicit decision, and QuillLite's installer writes the reason down. That part is right; only the extension lists are wrong. | `quilllite.iss:150-153` |
| A4 | Worse | Lite | **No braille.** `ScreenReaderVoice` speaks through Prism/`accessible_output2` and nothing else; nothing in `quill/apps/lite_*` or `quill/core/lite/*` mentions braille. QUILL routes announcements through a braille service. The mitigation is real and deliberate -- every message also lands on a focusable status-bar cell, which a display reaches by routing -- but a deafblind user gets no announcement at all, and that belongs in the PRD as a decision rather than existing as an absence. | `lite_voice.py:16-76` |
| A5 | Worse | Lite | **No announcement throttle.** QUILL has `announcement_throttle_ms` and applies it; Lite hands every message straight to the engine, so a held key that announces per repeat floods the reader. | `main_frame_statusbar.py:942-946`; `lite_voice.py:57-75` |
| A6 | Worse | QUILL | **No single-instance check.** Lite uses `wx.SingleInstanceChecker`, so a second launch hands its files to the running copy, and `--new-instance` is the documented escape. QUILL has neither, so two QUILLs can run against one data folder and one recovery store. | `lite.py:25, 472-543`; `quill/__main__.py:558-620` |
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

**Ctrl+K: fixed 2026-09-16, and there were three of them, not one.** The first
pass named `_on_editor_char_hook`. A grep for `self.insert_link()` found the
same hard-coded key code in three separate handlers -- the editor char hook, the
frame-level hook and the editor key-down handler -- each an undocumented second
binding beside the keymap's, invisible to the Keyboard Manager, the generated
reference and the Key Describer, and deaf to a rebinding. All three now call
`_run_chord_through_registry("Ctrl+K")`, which asks the registry what the chord
is bound to and runs that, so the hooks deliver a chord rather than deciding
what it means. A test asserts `self.insert_link()` never returns to that file.

**Still open: rich-mode `Ctrl+B/I/U`.** The same hook binds those three by key
code in rich mode (`main_frame.py`), for the same good reason -- the native
RichEdit would otherwise eat them silently -- and with the same defect. They
should go through `_run_chord_through_registry` too; the helper is written and
the change is three lines (P1).

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
| P0.3 | `Alt+F7` = Next Misspelling in both; Spelling for This Word -> `Alt+Shift+F7`; Add Word -> `Ctrl+Alt+F9` as a registered QUILL command that says which dictionary it wrote to | both | S | pressing `Alt+F7` never teaches the dictionary in either editor |
| **P0.6a** | **An editor font, a font size, and text size in/out/reset in QUILL** (4.3): two settings, `SetFont` on the editor, three commands on Notepad's `Ctrl+=` / `Ctrl+-` / `Ctrl+0`, a Format menu item that says **Font...**, and `format.font_dialog` made to work on a rich selection instead of refusing outside Markdown | QUILL | M | a low-vision user can make QUILL's text bigger; a rich selection's font can be changed; the rich kind zooms rather than re-levelling headings (5.5) |
| **P0.6b** | **A large-file guard in QuillLite** (V1): move `quill/ui/large_file_guard.py` to shared, size the file before reading, warn once, open deliberately | Lite | S | a 200 MB log announces its size and opens on purpose or not at all |
| **P0.6c** | **`DocumentText` in core** (V2-V4, T1, S8): the Python-side mirror, a revision counter, cached stats and `line_column_for_position`, and the rule that display code reads it and never the control. Lite's status bar, live spell check, heading cue and autoformat all move onto it | both | M | holding Down for five seconds in a 50 MB file costs Lite no more than 20% over QUILL, and no status refresh runs more than once per 250 ms |
| P0.7 | The **Broken** rows of section 6, each with a regression test: F1 Lite Save As converts the window before the write; F2 Lite recovery rewrites encoding; F3 unencodable characters silent in both (one shared prompt: "3 characters cannot be saved as Windows-1252. Save as UTF-8?"); F4 QUILL non-atomic Save As HTML / Plain Text; F5 QUILL watcher replaces a `.docx` tab with decoded binary; F6 QUILL encoding change does not dirty, UTF-16 undetected; R1 rich bullets unreachable; R2 list-off strips every list and clears undo; R3 Markdown heading prepends; R6 Lite mode switch discards formatting; S1 Lite F7 Add writes into QUILL's folder; S2 QUILL live alert speaks with speech off; S3 QUILL Ignore writes a sidecar and lies; C1 Lite clip history is dead code; H1 Lite keymap can bind a bare letter | per bug | S each | regression test per bug |
| P0.8 | **Verify live, then fix if confirmed**: R4 dark mode writing grey text into every saved `.rtf`; R5 Lite `SetFont` re-levelling headings on `Ctrl+=`; C2/N3 QUILL whole-document rewrite for a local insert or line tool in an `.rtf`; R14 two-step undo after Heading N; L13 Lite's Go to Start of Selection | both | S each | a rich document survives each with its runs intact |
| P0.9 | `_run_command` reports the exception class and message, not "Command failed"; `save_file` handles `UnicodeEncodeError` and `UnsupportedSaveFormatError` with the same sentences as `OSError`; Lite stops `errors="replace"` | both | S | a cp1252 document that gains an emoji says so on `Ctrl+S` in both |

### P1 -- parity violations and the rest of the family keymap

| # | Item | Editors | Cost | Done when |
| --- | --- | --- | --- | --- |
| P1.1 | Bind the 33 keyless QUILL commands per section 3 | QUILL | S | rule 8 gate passes |
| P1.2 | Structural selection family on Lite's six chords; Set Mark `Ctrl+Shift+M`, Exchange `Ctrl+Alt+X`, Duplicate Selection `Ctrl+Alt+Q`; Switch Document Mode `Alt+Shift+F`; `Ctrl+Alt+F8` becomes the marker toggle in **both** and Extend Selection Mode takes its own chord in both (5.3a); Shrink drops its stack; Reselect remembers every structural select; F8 gains a cancel; marks on the shared ring, clamped, recorded for Back | both | M | -- |
| P1.2a | **Fix Extend Selection Mode's four movement bugs** (5.3a): page keys ask the control for a real page, Up/Down follow visual lines under soft wrap, word movement stops at punctuation as Windows does, and the line table comes from `DocumentText` instead of an O(N) rescan per keystroke | QUILL | S | holding Down inside a wrapped paragraph moves one visual line per press, and a 50 MB file costs nothing extra per key |
| P1.2b | `select_chunk` renamed **Select Token**, off `Ctrl+Space`, with help text that says what it does that Select Word does not (5.3a) | QUILL | T | -- |
| P1.3 | Lite's rich kind switched from `SetFont` to view zoom (5.5), now that QUILL has the same three commands from P0.6a | Lite | S | a rich document's heading ladder is unchanged after `Ctrl+=` |
| P1.4 | Body Text `Ctrl+Alt+0`; Next/Previous Heading `Ctrl+Alt+H`/`+Shift+H`; List Headings alias | QUILL | S | -- |
| P1.5 | Bullets `Ctrl+Shift+L` as a list-style cycle in both; QUILL's numbered-list command folded in | both | S | -- |
| P1.6 | Document Statistics `Ctrl+Shift+G` in both; Title Case `Ctrl+Shift+T`; Go To dialog with targets (5.4) | both | M | -- |
| P1.7 | Font for Selection `Ctrl+Shift+F`, Editor Font `Ctrl+Alt+F` (the keys for P0.6a); Search in Files and folds relocated | QUILL | S | -- |
| P1.8 | File Encoding and Line Endings dialog in QUILL's File menu (dirtying, with UTF-8 BOM, UTF-16 detection on open) | QUILL | M | round-trip test per encoding |
| P1.9 | Date and Time as a core command on `F5` in QUILL | QUILL | S | works in Safe Mode |
| P1.10 | Status bar show/hide in QUILL on `Alt+Shift+B` -- the whole-bar switch beside the existing per-cell `status_bar_hidden` list (G3); `F6` lands in the status bar first in both | QUILL | S | -- |
| P1.11 | AI commands vacate `Ctrl+Alt+Shift+{S,I,G,T,H,E}`; favourite folders to the leader; leader reclaim (5.9) | QUILL | S | -- |
| P1.12 | Clipboard verbs: Copy to Tray / Clear / Collect / Paste Collected / Clear Collector / Keep Clip / Recent Clips on Lite's chords in QUILL | QUILL | S | -- |
| P1.13 | New Rich / New Plain Text Document in QUILL; Earlier Versions, Page Setup, Character Details, Document Language, Check for Updates, About, Keyboard Shortcuts, Keyboard Manager, Sound Scheme, Recent File N keys; Open User Guide off its literal accelerator | QUILL | S | -- |
| P1.14 | Spelling parity into QUILL: the caret-landing check, suggestions spelled as you arrow, the "Spelling: word" context submenu, the Announcements dialog on `Ctrl+Alt+Shift+F7`, Check While Typing on `Ctrl+Alt+F7` and its state said once on open; F7 honours session ignores in both; the tokenizer goes Unicode in core (S4, S5) | both | M | a word with an accent is one word in both editors |
| P1.15 | The **parity gate** (section 9) with its exception table, so P0/P1 cannot regress | tests | S | gate green with zero undocumented divergences |
| P1.16 | One line-tool helper in QUILL with Lite's scope, no-op detection, counts and rich warning (N1-N3); one command per verb (N4) | QUILL | S | Sort with no selection sorts the document and says how many lines |
| P1.17 | QUILL adopts `set_heading_level` for Markdown headings, `all_headings()` for the outline in rich, bold state announcements, the H5/H6 ladder sizes, and a rich-aware Describe in Lite (R3, R7, R8, R12, R13) | both | M | -- |
| P1.18 | Status bar: GATE-13 fixes in QUILL's cells (H3), Lite's assign-time wx check and QUILL's Insert reservation swapped into each other (H2, H9), `Win`/`Cmd` rejected in Lite's keymap loader (H1) | both | S | -- |
| P1.19 | Clipboard: tray labels and pins survive edits (C3); collector becomes a buffer (C4, 5.1); tray paste no longer waits for the multi-press window on a plain single press (C5); Lite's clip history captures copies as promised or the promise is removed (C1); one verified undo story for `Replace` (C6) | both | M | -- |
| P1.20 | **The menu bar answers to Word** (4.5): fold Search into Edit and delete the menu (M1); a Format menu item that says Font... (M2, with P0.6a); alignment, Bullets and Line Spacing in Format (M3); Go To in Edit as well as Navigate (M4); "Word Wrap" not "Toggle Soft Wrap" (M5); Delete and Paste Text Only in Edit (M7) | QUILL | S | a person who knows Word finds each verb in the menu Word puts it in |
| P1.21 | **Typing defaults decided once** (T3, T4): Tab's meaning follows the document kind in both; autoformat gated by kind as well as by setting; QUILL's two-setting granularity and Lite's off-by-default adopted in both; Lite's feature blurb stops promising sentence capitals (T2) | both | S | typing a quote in a `.json` inserts a straight quote in both, whatever the setting says |

### P2 -- model alignments, and the value that crosses into Lite

| # | Item | Editors | Cost |
| --- | --- | --- | --- |
| P2.1 | Copy to Tray Slot... chooser in both; "tray is full" wording from the core (5.1) | both | S |
| P2.2 | Bookmark re-anchoring under the shared `BookmarkSet`, written on every change, list rows led by the digit (5.2) | both | S |
| P2.3 | **Tier 1 of 4.2 into Lite**: Insert Link, list-style cycle, line comment, Copy All, Go To dialog, Set Mark, tray-slot chooser | Lite | M |
| P2.4 | The QuillLite profile in QUILL with "Bring my QuillLite settings" (5.8), on the settings-name mapping from G1 | QUILL | M |
| P2.5 | One verb, one registration: retire duplicate ids and Quillin re-shipments (7.1); char hook dispatches through the registry (7.2) | QUILL | M |
| P2.6 | Keymap profile JSONs become deltas over `DEFAULT_KEYMAP` (7.3) | QUILL | S |
| P2.7 | Word aliases `F12`, `Ctrl+F12`, `Ctrl+Shift+F12`, `Ctrl+Shift+F5` in both | both | T |
| P2.8 | The remaining **Worse** rows of section 6 not named in P1: F7-F13, S6-S9, L3-L13, R9-R11, C7-C8, N5, PR1-PR3, A1-A7 | per bug | S each |
| P2.9 | Once-a-year commands on `Ctrl+Alt+F10/F11/F12` in both (rule 9) | both | T |
| P2.10 | New documents default to CRLF in QUILL as in Notepad, WordPad, Word and Lite, with the default exposed in Settings in both (F11); close prompts name the file and say Save / Don't Save / Cancel in both, from one core string (F12) | both | S |
| P2.11 | Lossy Save As warns before the write in every lossy direction in both, and converts at write time, never in the buffer (F1); Lite's Earlier Versions says "formatting is not kept" for rich documents (F7); Lite persists print settings (F13, PR2) | both | S |
| P2.12 | Session restore in QUILL on the shared rule Lite uses, command-line files winning (G4); crash recovery in Lite lists slots and lets the user decline (F14); read-only detected at open in both | both | M |
| P2.13 | **Tier 2 of 4.2 into Lite**: Review Buffer, Misspelling List, Quote/Unquote Lines, indentation conversion, Delete Lines Containing, Hard Wrap, Heading Organizer, jumping Find All results, Line Statistics | Lite | M |
| P2.14 | **Settings names reconciled** (G1) and `theme` given one default or one written reason (G2) | both | S |
| P2.15 | **Shell integration told the truth** (A1, A2): Lite's Open With gains `.md`, `.markdown`, `.html`; QUILL's gains `.rtf`, `.docx`, `.odt`, `.html`, `.epub`; neither ever takes a default handler | both | T |
| P2.16 | QUILL takes Lite's `SingleInstanceChecker` and `--new-instance`, and `--rich` / `--plain` (A6, A7) | QUILL | S |
| P2.17 | An announcement throttle in Lite (A5); Lite's braille position written into the PRD as a decision (A4) | Lite | S |

### P3 -- polish, docs, the long tail, and the magical tier

| # | Item | Cost |
| --- | --- | --- |
| P3.1 | Re-judge QUILL's temp bookmark once numbered bookmarks land (5.3a); `select_chunk` is **kept** and renamed, not retired | S |
| P3.2 | A QuillLite tutorial book on `Ctrl+Alt+F1` | M |
| P3.3 | Documentation drift (7.6): Lite PRD 2.2/3.2/8.1, both user guides' key tables, CHANGELOGs, release notes; regenerate keyboard and F1 references; Key Describer titles for every new QUILL chord | S |
| P3.4 | Quillin hotkey collision gate (7.4) | S |
| P3.5 | Bugs from section 6 rated Divergent, where a decision was taken | S each |
| P3.6 | **Tier 3 of 4.2**: snippets as one concept in both, Markdown folding in Lite, print preview in Lite, `EM_FORMATRANGE` formatted printing in the shared rich surface (PR3) | M each |
| P3.7 | **The magical tier** (4.2, last table): "What changed?", a spoken undo over the `DocumentText` journal, repeat-the-last-announcement, and a one-sentence structure summary on open. QUILL first or shared-simultaneous, never Lite first | M each |
| P3.8 | A `wx.FileDropTarget` in both, so a file dragged onto the window opens (4.4) | S |

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
9. **Editor-font gate**: `quill/ui` must contain a `SetFont` call on an editor
   control, and `Settings` a font name and size. A one-line gate, because the
   absence of a whole capability is exactly the kind of thing no test notices
   (4.3).
10. Existing gates that must stay green and will need regeneration: menu
   accelerators, GATE-KEYREF, GATE-HELPREF, GATE-DESCRIBE (Key Describer
   titles for every new QUILL chord), GATE-LITE-COVER (every new Lite handler
   needs a behavioural test), module size budgets.

## Recorded, so nobody looks again

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
