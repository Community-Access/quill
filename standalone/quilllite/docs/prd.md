# QuillLite — Product Requirements

**Version 1.0.0 · Windows · MIT · part of the QuillVille family**

## 1. Statement

QuillLite is QUILL with everything removed except the editor. One document per
window, plain text or rich text, and nothing else.

It exists for one person: someone who wants Notepad or WordPad with QUILL's
accessibility, and who finds the full writing environment more than they need.
That is not a small group. QUILL for All is a writing environment — AI,
dictation, conversion, comparison, publishing, braille tooling, extensions — and
for a great deal of what people actually do with a text editor, all of that is
in the way. Opening a `.txt` file to change one line should not start a product
with a setup wizard.

QuillLite is **not a replacement for QUILL** and **not a place new features go**.
Anyone who wants any of the list above wants QUILL. This is stated here, in the
requirements, because the pressure will be to add things: it is built so that it
cannot grow into QUILL without somebody deliberately deciding to abandon the
product it is.

### Provenance

QuillLite began as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`), offered under this repository's MIT licence.
That PR also isolated a real bug in QUILL's own Rich Edit surface — see §7 — and
deliberately did not fix it, so that adding an app and changing the editor stayed
separate decisions. Both decisions were taken; the fix ships with this release
and reaches every QUILL user, not only QuillLite's.

## 2. Architecture

**QuillLite is not a fork.** That is the single most important architectural
statement in this document, and it is the difference between a sibling and a
copy that rots.

| Layer | Where | What |
|---|---|---|
| The app | `quill/apps/lite*.py` | The shell, the windows, their menus, commands, status bar and dialogs |
| Its own domain logic | `quill/core/lite/` | Settings, paths, recovery, the command table, file encoding, backups, the inbox, the feature areas |
| Logic QUILL should also have | `quill/core/numbered_bookmarks.py` | Nine slots that move with the text -- shared, not QuillLite's; see 2.2 |
| Its F1 catalogue | `quill/core/lite_surface_help.py` | What every window is *for* |
| The editor surface | `quill/ui/richedit_editing.py` over `quill/ui/richedit_rtf_surface.py` | QUILL's own control, extended — not copied |
| The product shell | `standalone/quilllite/` | Entry point, icon, installers, docs |

Everything under `quill/` is therefore covered by the repository's existing
gates — module-size budget, access-key uniqueness, the over-announce gate, the
dialog registry, the F1 audit — which is the reason the app code lives there
rather than in the product folder. A surface that no gate can see is a surface
that silently rots; QUILL Cast shipped an unreachable first-run dialog for two
releases exactly that way.

### 2.1 What QuillLite reuses rather than reimplements

Each of these is a QUILL finding that cost real on-device testing to establish.
QuillLite gets them by *using* QUILL's code, not by copying its conclusions:

- **The native `RICHEDIT50W` control** (a `wx.TextCtrl` with `TE_RICH2`). QUILL
  keeps it because its `IAccessible` value is reported correctly to NVDA and
  JAWS where a classic EDIT control's is not.
- **RTF through the Text Object Model, never `EM_STREAMIN`.** A `ctypes`
  `EDITSTREAM` callback hard-crashes msftedit — the control access-violates the
  instant it calls back into Python. The TOM path never calls back into Python.
- **`scan_rtf_safety` before a byte reaches the control.** RTF can embed OLE
  objects, executables, binary blobs and fields that fetch remote resources.
  QuillLite runs the identical scanner QUILL runs, from `quill/io/rtf_safety.py`.
- **The heading ladder.** Bold plus 20, 16, 14, 12, 11.5 and 10.5 point for
  levels 1 to 6, and 11 point body text — close enough to Word's own ladder that
  a saved RTF reads as headings in Word. Each level has a size of its own so the
  ladder can be read *back*: a level the editor can set and heading navigation
  cannot find is worse than a level that does not exist.
- **Saying that a heading is a heading** (`quill/core/structure_announce.py`,
  shared with QUILL). The ladder is invisible to a screen reader, and not
  because the reader is failing: no Windows edit control exposes a paragraph
  style at all, so `RICHEDIT50W` can offer JAWS the font size and the weight and
  has no property that means "heading". Word announces heading levels only by
  shipping an accessibility provider of its own. QuillLite therefore says
  **"Heading 2, Installing"** itself, on arrival, once -- the level first, then
  the heading's own words, as one sentence it owns. The ordering is not a
  preference about tidiness: a cue *queued behind* the reader is at the reader's
  mercy, and on a large caret jump -- Ctrl+Home, a search hit, a bookmark --
  NVDA and JAWS cancel what is pending and start again on the new line, so a
  level waiting its turn is never heard. Reported exactly that way. Said first,
  carrying the line's words, it survives every kind of move, and interrupting is
  safe *because* the text the reader was about to speak is inside the sentence
  replacing it. `heading_announce_position = "after"` restores the older
  level-alone-behind-the-reader ordering for anyone who prefers it. Plain-text
  documents get the same cue over Markdown hashes or `<h2>` tags -- but only
  where those mean a heading, never in the `.py` / `.sh` / `.ini` files a
  Notepad replacement opens all day. **Ctrl+Alt+F3** turns the cue off and on in
  place, because whether structure is what you are listening for is a decision
  per document rather than a preference to set once.
- **Saying what list you are in** (`quill/core/list_structure.py`, shared with
  QUILL). The same gap one level along, and the one a screen reader closes
  everywhere else: in a browser an `<ul>` reaches the accessibility tree as a
  list with a count, and in an editor a list is characters. "Bulleted list, 5
  items" going in, "Level 2, 3 items" a rung down, "Out of list" coming out --
  over Markdown and HTML alike, and over bullets, numbers and definition lists,
  with "Term" and "Definition" as the two halves of a `<dl>` alternate. Items
  are counted **at the caret's own level inside its own parent**, never totalled:
  an outline read as "7 items" is a lie somebody reorganises on. **Ctrl+Alt+F5**
  is its own switch, separate from the heading one, because reorganising an
  outline the list level is the work and proof-reading the same file it is a
  phrase between you and every item.
- **A markup language for a plain document** (`quill/apps/lite_window_markup.py`,
  over `quill/core/lite/filetypes.py`). Ctrl+B in a `.md` used to refuse and
  send you to rich text, which is true and unhelpful: somebody writing Markdown
  wants two asterisks and knows it. One rule -- `markup_language_for` -- decides
  four things at once so they cannot disagree: what the run keys write, what the
  heading keys write, which of the two tag pickers the Insert menu offers, and
  whether the caret cue can see a list. The language is read from the file name
  and is never binding: **Ctrl+Shift+M** rings through all four kinds of
  document, **Ctrl+Alt+F6** goes straight to one, and the status bar's Format
  cell names whichever you are in.
- **Whole form controls, not tags** (`quill/core/html_forms.py`, shared with
  QUILL). Offering `<select>` alone is offering the easy half: a usable dropdown
  is a `<label>`, a `for` matching the field's `id`, the field and its options,
  and three of those four are invisible. Twenty controls therefore insert whole
  — labelled, named, grouped, with `aria-describedby` wiring a required field to
  its hint and its error, and with **the generated `id` checked against the
  buffer first**, because two fields sharing one id is the commonest way a form
  that was accessible when written stops being so when copied, and its only
  symptom is that the second label focuses the first field. A selection becomes
  the label and the id is derived from it, so the pair cannot drift. The radio
  group is the case that justifies the whole module: without a shared `name` the
  buttons are not a group and all of them can be on at once; without a
  `fieldset` and `legend` they are a group with no name. Four elements, two
  attributes, and no visible evidence of any of it.
- **A picker that is complete.** 111 HTML elements and 22 Markdown
  constructions, because a *searchable* list has no cost to being complete —
  searching 111 is no harder than searching 46 — and a missing entry is a dead
  end somebody leaves the app to resolve. The forty-six that shipped before left
  out `<dl>`/`<dt>`/`<dd>` (which this editor announces), `<figure>`,
  `<figcaption>`, the accessible-table parts, `<abbr>`, and `<br>` and `<hr>`,
  which were handled as void elements and could not be chosen. Both pickers rank
  by **what a thing does** as well as by its name: "glossary" finds `<dl>`,
  "subtitles" finds `<track>`, "dropdown" finds the labelled control and the
  bare `<select>` together.
- **The dialog contract.** Every modal goes through `show_modal_dialog`, which
  announces the transition, installs F1 help and infers the accessible names
  macOS VoiceOver needs.
- **The F1 context-help engine** (`quill/ui/app_context_help.py`) and the
  **announcement path** (`AnnouncementEngine`).
- **Document counting** — `compute_document_stats` and
  `line_column_for_position`, the same functions QUILL's own status bar uses, so
  the two products cannot disagree about the length of the same file.
- **The line and case tools** — `format_ops` and `transforms`. QuillLite has no
  second implementation of "sort these lines"; a first draft did, and it was
  deleted, because two implementations is two places for them to start
  disagreeing about what a trailing newline means.
- **The clipboard stores** — `copy_tray`, `clip_library`, `clipboard_collector`.
- **Abbreviations** — the engine, the store, and the manager dialog.
- **The command palette**, the **feature-areas dialog**, **char_describe**,
  **selection**, **print pagination**, and the **announcement path**.

### 2.2 QuillLite is never allowed to be ahead of QUILL

This is a rule, not an aspiration, and it has already cost work twice.

If QuillLite needs something the editor cannot do, the capability goes into the
**shared** package and the editor gets a way to reach it in the same release. A
feature the small product has and the big one does not is exactly backwards --
and worse, it is invisible: nobody opens QUILL and notices the absence of a
thing they have only ever seen elsewhere.

In this release that meant:

- `create_richedit_rtf` now builds `RichEditDocument`, so every QUILL tab has
  the paragraph and view capabilities QuillLite needed, by construction rather
  than through a second factory;
- QUILL gained **Justify**, **line spacing**, **Grow/Shrink Font**, **Paste Text
  Only** and **rich-mode bullets** -- five commands whose capability had always
  been in the surface with nothing bound to it;
- numbered bookmarks live in `quill/core/numbered_bookmarks.py`, not under
  `lite/`, so QUILL's editor can adopt them;
- a first draft of QuillLite's own line and case tools was deleted and replaced
  with QUILL's;
- **`select_word` was added to QUILL**, which could select a line, a paragraph
  and a block but never a single word -- the innermost rung of its own expansion
  ladder was the one thing nothing could ask for; `select_line` gained a key,
  having sat in the Edit menu registered, working, and advertising no shortcut
  because it was in no keymap at all; and `select_paragraph`,
  `duplicate_selection` and `toggle_extend_selection_mode` gained keys, each
  having been left unbound for a reason that no longer holds;
- **`shrink_selection` was added to `quill/core/selection.py`** as a computed
  inverse of `expand_selection`, and QUILL's own shrink now falls back to it.
  QUILL's shrink was an undo of the expansion stack, so it could only retrace a
  path you had walked: select a paragraph outright, ask to shrink, and it
  answered "no selection to shrink" -- which is indistinguishable, by ear, from
  a command that is broken;
- the **spell check file-type rule** was written into shared core
  (`quill/core/spellcheck_filetypes.py`) and wired into QUILL's own live alert
  in the same change, so the editor stays quiet in source and configuration
  files exactly as QuillLite does;
- `load_combined_dictionary`, `load_scope_dictionary` and `add_word_to_scope`
  gained an optional `personal_dir`, so a sibling app can keep taught words in
  its own folder. QUILL passes nothing and behaves precisely as before -- the
  extension point exists because QuillLite needed it, and it lives in QUILL's
  module rather than in a copy of it.

Where the two must differ, they differ **on purpose and in writing**. QUILL
takes `Ctrl+Alt+J` and `Ctrl+Alt+V` where QuillLite uses WordPad's `Ctrl+J` and
`Ctrl+Shift+V`, because `Ctrl+J` has been Set Temporary Bookmark and
`Ctrl+Shift+V` has been Preview in QUILL for far longer. An existing binding
somebody's hands already know outranks a new command's convention, and the
reason is a comment in `keymap.py` rather than folklore.

### 2.3 What QuillLite adds to the shared package

`quill/ui/richedit_editing.py` is a subclass of QUILL's surface, not a copy of
it. A *document* window — one file, one window, switchable between plain and
rich, themed by itself — needs five things a notebook tab does not, and every one
is a Rich Edit message or a TOM call that wx has no spelling for: text-mode
switching (`EM_SETTEXTMODE`), word wrap (`EM_SETTARGETDEVICE`), view background
and zoom (`EM_SETBKGNDCOLOR`, `EM_SETZOOM`), whole-document recolour for the
theme, and heading enumeration.

The zoom detail is load-bearing: in rich text the text-size control is a *view*
zoom rather than a font change, because run point sizes **are** the heading
ladder and rewriting them would silently re-level every heading in the document.

## 3. Scope

### 3.1 What it keeps, and why

| Kept | Why |
|---|---|
| Plain text and rich text, one document each | The two things Notepad and WordPad are |
| Headings 1–4, bold/italic/underline, alignment, fonts | The formatting a WordPad user expects, on QUILL's ladder |
| Heading navigation and a headings list, in **both** modes | The reason a screen-reader user prefers a structured document at all; plain text has Markdown headings and they are real |
| A spoken "Heading 2" on arrival | Nothing else in the stack can say it — see the heading ladder above |
| Describe Formatting at the cursor | QUILL's own answer to "what am I standing in?" |
| Find, Replace, Go to Line | Non-negotiable in any editor |
| A **focusable** status bar (F6) | See §4.2 |
| Unsaved-work recovery, and session restore | See §5.2 |
| Byte-honest encoding and line endings, and a way to change them | See §5.1 |
| Dark mode, on by default | See §4.4 |
| Nine numbered bookmarks that move with the text | No scrollbar to remember the position of |
| Structural selection (word, line, paragraph, expand) | Shift+arrow is the wrong tool for a paragraph |
| Describe Character | A reader says "space" for four different characters |
| A twelve-slot copy tray, a collector and a clip library | The system clipboard holds one thing |
| Abbreviations, over QuillLite's own library | Expansion is an accessibility feature, not a typing one |
| Sort, de-duplicate, trim, and three case conversions | Work, not writing — and expensive by keyboard |
| Printing and Page Setup | Every text editor Windows has ever shipped has Ctrl+P |
| The Command Palette | Answers "how do I sort lines?", which is the real question |
| Switchable feature areas | See §3.3 |

### 3.2 What it drops, and why

Tabs, AI, dictation, self-voicing, preview, Quillins, remote files, GitHub,
braille tooling, the setup wizard, the command palette, comparison, publishing,
and every companion app.

Two of those deserve their reasoning stated rather than assumed:

- **No tabs.** Documents are numbered children of one window instead — see
  §3.3, including what that costs.
- **No self-voicing.** Speech goes to a running NVDA or JAWS and nowhere else —
  no SAPI, no synthesised voice of its own. A second voice talking over a screen
  reader is worse than silence, and a listener with no reader running is not the
  person this editor is for. For them, every message is in the status bar, which
  is exactly why the status bar is focusable.

### 3.3 Two decisions that shape everything else

**Numbered documents in one window.** Documents are MDI children of a single
`QuillLiteShell`, numbered from 1, and a number is never reused while its
document is open. "Document 3" is a name a person can hold and say out loud;
"the other Untitled" is not.

The cost is real and is written into the module that causes it: **MDI children
do not appear in Alt+Tab.** The whole burden of moving between documents falls
on the app, so it carries it four ways -- `Ctrl+F6` (the Windows convention),
`Ctrl+Tab` (what people actually press), `Alt+1` to `Alt+9`, and the Window menu
-- and every document's title leads with its number, because the title is the
one string a screen reader announces on arrival.

**Switchable feature areas.** QuillLite stays small by being *switchable*, not
by being poor. `Tools > Customize Features` turns whole areas off, and switching
one off removes its menu **and** its keys -- a key that still fires for a feature
somebody turned off is the feature not being off. Somebody who wants Notepad
unchecks rich text, and the Format menu is gone entirely.

Three areas ship **switched off** and are found in that same checklist rather
than hidden, because a feature nobody can find is a feature that does not exist:
autocorrect (welcome in prose, actively wrong in a config file), timestamped
backups (reassuring, and they fill a folder), and Go To Anything (the palette,
the headings list and the bookmark list each already answer their own part).

**Seventeen areas, not twelve** (2026-09-10). Five features belonged to no area
at all, which meant no switch in the dialog could reach them: the Matches
submenu, Go Back and Go Forward, the Command Palette, Describe Character, and
text size. That is a different failure from a feature being un-switchable on
purpose -- there was nothing to find and nothing to complain about. Going the
other way, **File Encoding and Line Endings stopped being switchable**: it
belonged to the line-tools area, so turning off Sort Lines also took away the
dialog that decides whether a file round-trips byte-for-byte, which for a
Notepad replacement is most of the job.

### 3.3a Profiles: a name is a promise, not a preset

Seventeen checkboxes is the right way to change one thing and the wrong way to
say "give me the small one". :data:`quill.core.lite.features.PROFILES` is four
named starting points -- **Recommended**, **Everything**, **WordPad**,
**Notepad** -- and the design rules behind them are worth stating, because each
one has a cheaper wrong version.

**A profile is a baseline, not a mode.** Applying one ticks and unticks every
box, and then the boxes are the truth again. There is nothing to escape from:
the very next change is an ordinary per-area override, and the Choice reads back
**Custom** the moment the boxes stop matching. The alternative -- a mode that
owns the dialog and reverts what you do -- makes the checklist a lie.

**A profile is written as what it takes away.** `AppProfile.disabled` lists the
areas switched off, never the ones kept, so an area added in a later version is
*on* in all four profiles until somebody decides otherwise. A profile written
before a feature existed must not silently remove it.

**Two of them carry a setting, and only those two.** "Notepad" does not mean
*these menus*; it means the thing you type in is plain text. A Notepad profile
that removed the Format menu and went on creating rich text documents on Ctrl+N
would keep the letter of its name and break its promise -- and the user would
find out one document later, at a Save As dialog offering a format they thought
they had turned off. So Notepad claims `default_mode = "plain"` and WordPad
claims `"rich"`. **Recommended** and **Everything** claim nothing: they are
statements about which areas exist and have no opinion about the rest, and a
profile that quietly rewrote a setting the user chose would be the mode this
design refuses to be.

**A description you cannot read is not documentation.** Every profile has
carried a paragraph since profiles existed and nothing displayed it -- the
Choice listed four bare names. Every other profile system in the codebase shows
its description; this was the one that did not. It is now under the Choice, it
is the Choice's F1 answer, and it is spoken once when Use Profile is pressed.
Not on every arrow of the Choice: the reader is already saying the name, and a
paragraph over the top of that is what GATE-13 exists to stop.

| Profile | Areas on | Ctrl+N | For |
|---|---|---|---|
| Recommended | 14 of 17 | unchanged | the shipped answer, and the way back from experimenting |
| Everything | 17 of 17 | unchanged | turning things off as they annoy you rather than finding them one at a time |
| WordPad | 5 of 17 | **rich** | letters and notes that should look like something |
| Notepad | 2 of 17 | **plain** | config files, logs, and anything where hidden formatting would be a problem |

Notepad keeps two areas and still has Find, Replace, Go To Line, Select All,
Insert Date and Time, Word Wrap, the font picker, the status bar, Undo, printing
and text size -- everything Notepad has had since 1985 -- because those live
outside the switchable areas by design. It also keeps File Encoding and Line
Endings, per the paragraph above.

### 3.4 Non-goals

- **Not a feature destination.** If a proposal here would also make sense in
  QUILL, it belongs in QUILL.
- **Not a macOS product in 1.0.** The rich surface needs `RICHEDIT50W`. Every
  module imports on every platform and rich features report as unavailable
  rather than failing, but there is no `nstextview` path here.
- **Not a thin client.** It does not share data with QUILL — see §5.3.
- ~~**Not keymap-customisable.**~~ **Reversed 2026-09-10.** This said QuillLite
  had one fixed table and that was that. The table is still the *defaults* --
  it is what the uniqueness gates assert against -- but
  `quill/core/lite/keymap.py` puts a resolution layer over it and
  `Tools > Keyboard Manager` (Ctrl+Alt+Shift+R) edits it. What stays true is the
  reason the non-goal was written: QUILL's chord grammar, its `APP_KEYMAPS`
  overrides and its Key Describer are a writing environment's features and are
  still not here. Rebinding a key is not.
- **Not a second clipboard manager.** The tray, the collector and the library
  are QUILL's own stores, kept in QuillLite's folder. Nothing is reimplemented.

## 4. Accessibility

The four family rules, applied here.

### 4.1 Every menu item shows its key, and no key is claimed twice

The menu bar is generated from one table, so the keys the menus advertise, the
keys that are bound and the keys the Keyboard Shortcuts window lists are one
list read three times. `tests/unit/core/lite/test_lite_commands.py` asserts, of
that table: every item carries a key; no key is claimed twice; no `&` mnemonic
is claimed twice inside one menu (Windows *cycles* focus between duplicates
instead of pressing, so one of a pair silently cannot be reached); and every key
string is one `wx.AcceleratorEntry` can actually parse — wx silently drops what
it cannot, leaving a menu advertising a dead key.

### 4.2 Every window answers F1, and so does every control

F1 answers with what this window is for, then what the focused control does,
through the family's shared engine. GATE-LITE-HELP
(`quill/tools/lite_help_audit.py`) refuses to let a new window ship without a
purpose or a new control ship without help.

QuillLite adds a stricter check of its own
(`tests/unit/tools/test_lite_control_help.py`), because the shared scanner has
two blind spots that matter here: it does not treat `wx.CheckBox` as helpable
(and the Find and Replace windows are half checkboxes), and it cannot see a
control built by a factory in another module — which is *the document itself*,
the control a listener is in for all but a few seconds of a session.

### 4.3 The status bar is navigable, not decorative

QUILL's status bar is a row of focusable cells rather than painted text, and
QuillLite's is the same: **F6** lands in it, arrows and Home/End move between
cells, each cell announces its value, Enter acts on it, and Escape returns to the
document. Ten cells: the last announcement, position, words, characters,
selection, format, heading, encoding, line endings, and saved state.

Two of those exist nowhere else in the app. **Encoding** and **line endings**
are what decide whether a file round-trips byte-for-byte, which for a Notepad
replacement is most of the job — and in every other editor they are invisible.

Refreshes are coalesced through a restarting 90 ms timer (QUILL's own window):
counting words is O(document), and a refresh per keystroke is several full scans
per keypress.

### 4.4 Say only what the screen reader does not already say (GATE-13)

The reader announces window titles, focus moves, control names, roles, states
and selection changes. QuillLite announces only outcomes it alone knows: "Bold
on", "Saved notes.txt", "Replaced 4 occurrences", "Wrapped to the start",
"Heading 2: Installing". Nothing is announced from a focus handler; the one
exception is the F6 landing in the status bar, which names the region once,
because moving from a text control to a strip of buttons is described by the
reader as "button" and nothing more.

Announcements also land in the status bar's message cell, so speech that was
missed can be read again.

Two smaller decisions in the same spirit: **OK, Cancel and Close carry no `&`
mnemonic at all** — Enter and Escape already serve them, and every letter they
give up resolves a collision elsewhere (GATE-14) — and **dark mode is the
default**, because the users this editor is for are disproportionately
light-sensitive and a first launch that is bright white is a first launch some of
them cannot read.

## 5. Safety and data

### 5.1 Byte honesty

Open a file, change nothing, save it, and the bytes must be the bytes you
started with. `quill/core/lite/textfile.py` owns this: a UTF-8 BOM is kept, a
UTF-16 file stays UTF-16, and the enormous installed base of Windows text files
that are neither is cp1252 — tried *last*, because it can never fail to decode.
Line endings are remembered and re-applied, so a file that arrived from a shell
script does not silently gain carriage returns because it was opened once.

Every write is atomic (temp file in the same directory, then `os.replace`), so a
power cut during a save leaves either the old file or the new one, never a
truncated one. In rich mode the theme colour is reset to automatic before the
save and restored afterwards, so dark mode never leaks light grey text into
somebody's document.

### 5.2 Recovery

Every modified window owns one recovery slot: a copy of the content beside the
original, written on a timer and removed the moment the document is saved or
closed cleanly. A clean shutdown leaves the folder empty; anything still there
on the next start is work the last session did not keep, and is reopened in its
own window, unsaved. The original file is never touched, so a crash mid-save
cannot leave somebody with a truncated original *and* no recovery.

The interval is a setting (15–600 seconds, default 60) and is one of the two
settings that exist only in Preferences.

### 5.3 Its own data folder

Settings, recent files and recovered work live in `%LOCALAPPDATA%\QuillLite`,
deliberately **not** in `%APPDATA%\Quill`. QuillLite is offered as an
alternative to QUILL rather than as a client of it: a Notepad-scale editor that
silently adopted a writing environment's settings would be making a decision
nobody asked it to make, and uninstalling it could then cost somebody something
QUILL owns. A machine that has never had QUILL installed must not grow a Quill
folder because somebody opened a text file.

This is why QuillLite does not use `quill.core.ipc` for its single-instance
guard — that lock lives in QUILL's data directory. It uses
`wx.SingleInstanceChecker` (a kernel object, with no file to go stale) plus its
own inbox directory. Uninstalling never removes the data folder either: recovery
slots are the one thing somebody may not have finished with, and an uninstaller
is the worst possible moment to discover that.

### 5.4 File associations

The full installer offers "Open .txt and .rtf files with QuillLite" as an
**optional** component that registers an *Open With* verb, never a default
handler. A text editor that quietly takes over every `.txt` on the machine is a
text editor people uninstall, and Notepad, WordPad and QUILL stay exactly where
they were.

### 5.5 Getting help, without an account and without an audience

**Help > Get Help from Support...** (`Ctrl+Alt+F2`) writes an email to
`support@community-access.org`, where a person reads it and the reply comes
back to the person who wrote it.

That is a correction, not a feature. The family's reporting item used to file a
**GitHub issue in a public repository**, through a token baked into every
installer, and it left the reporter with no way to be answered: a GitHub issue
is not a conversation you can join without an account, which is precisely the
account a screen-reader user reporting that an editor went silent is least
likely to have. Worse, somebody describing a failure names their configuration,
their employer, or the document they were working on — and every word of it was
published, permanently and searchably, the moment they pressed Submit.

QuillLite had neither half of that. It shipped with **no reporting item at
all**, only an address printed in the About box to copy out by hand.

The form is the same one every app in the family opens
(`quill/ui/support_dialog.py` over `quill/core/support_message.py`): what kind
of message this is, a subject, and what happened. What you expected and how to
reproduce it are optional. **Your email address is optional too** — a problem
can be reported without giving one; you simply cannot be replied to. Send opens
**your own mail program with the message already written**, with QuillLite's
name and version, your Windows version and your screen reader appended. Nothing
leaves the machine until you send it there, and the app says so out loud rather
than claiming to have sent something it has not. A machine with no mail program
set up — webmail only — gets the whole message and the address on the
clipboard, so nothing typed is ever lost.

Writing to `support@community-access.org` directly works exactly as well. There
is no form anybody is required to use.

## 6. Release packaging

Four artifacts, the family contract:

| Artifact | Built from | Output | Measured |
|---|---|---|---|
| Full installer | `installer/quilllite.iss` | `QuillLite-Setup-Shared-1.0.0.exe` | 113 MB |
| Lite thin installer | `installer/quilllite-lite.iss` | `QuillLite-Lite-Setup-1.0.0.exe` | 2.8 MB |
| Full portable | `build_portable.py --product quilllite` | `QuillLite-Portable-1.0.0.zip` | 91 MB |
| Companion zip | the launcher without an interpreter | `QuillLite-Companion-1.0.0.zip` | 0.1 MB |

The download names spell the product as one mixed-case word, `QuillLite-*`,
never `Quill-Lite-*`: a screen reader speaks `QuillLite` as the product's name,
where a hyphenated form is read out punctuation and all, and the thin flavour
would have been the genuinely silly "Quill dash Lite dash Lite dash Setup".

The installer scripts are named `quilllite*.iss`, not `quill-lite*.iss`: the
family reserves the `*-lite.iss` suffix for the *thin* installer flavour, and
`quill-lite.iss` ends in it -- so the shared installer was being audited as a
thin one. Every other identifier for this product is already `quilllite` (the
folder, the `AppRefId`, the launcher product key), so the installers match it.

`portable-inventory.json` is committed and enforced: the portable build fails on
any drift from it, which is the class of defect that once put 82 MB of
undeclared payload into a runtime installer.

All four come from `scripts/build_release.ps1`. The shared QuillVille Runtime at
`%LOCALAPPDATA%\QuillVille\Runtime\3.13\` is reused: the full installer ships it,
and the Lite and Companion editions download it once on first launch through the
runtime's accessible download page. **Neither ffmpeg nor libmpv is staged** —
QuillLite declares no media components, and the build strips any a sibling app
left in the shared work area, so build order cannot change what ships.

Code signing is opt-in (`-Sign` / `QUILL_SIGN=1`), the same convention as every
sibling; see `docs/code-signing.md`.

Releases publish to `Community-Access/quill` rather than to a repo of their own,
and are told apart by the `QuillLite-*` asset prefix. **Deviation from the
siblings, noted deliberately:** Radio, Cast, Weather and Studio each have their
own release repo. Revisit if it bites.

### 6.1 Updating in place

**Help > Check for Updates...** on `Ctrl+Alt+U`, the key eight sibling apps
already answer, plus a silent once-a-day check at launch
(`check_updates_on_launch`, on by default, one checkbox in Settings). Page Setup
gave up `Ctrl+Alt+U` for it and took `Ctrl+Alt+P`, which is free in both editors
and a better letter besides: a chord that means one thing in eight apps and
something else in the ninth is the kind of difference nobody finds until it does
the wrong thing.

Before this, QuillLite could not tell its user that a newer version existed. It
is the app most likely to be somebody's only Quill product — installed by a
person who wanted Notepad — and therefore the app whose users are least likely
to go looking on GitHub. They would have stayed on 1.0.0 forever with no way to
know that was happening.

**The dialog is shared, and it always shows what changed.** `quill/ui/
update_notice.py` is the one "an update is available" surface for QUILL, the
eight companion apps and QuillLite: the release notes flattened out of Markdown,
capped and never empty, with **Update** as the affirmative and default and
**Close** as the escape. Focus lands on the notes rather than on a button, so
the first thing read is the release notes and not the word "Update". QUILL alone
adds **Skip this version**, because QUILL alone has a settings field to remember
the answer in. The download, its spoken 25/50/75 milestones, and the
Install-and-restart dialog are `quill/ui/update_download.py`, shared the same
way — QuillLite has no `TaskManager`, so it supplies a one-shot thread instead
and gets the identical experience.

Releases resolve from `RELEASE_REPO` and `RELEASE_ASSET_PREFIX` in
`quill/core/lite/__init__.py`, deliberately **not** from
`companion_install.ASSET_PREFIX`: that table is the set of QuillVille apps QUILL
can offer to *install for you*, and QuillLite is a separate product rather than
a sibling QUILL launches.

The silent launch check says nothing in every direction but one: nothing while
it runs, nothing when there is nothing, and nothing when the network is down.
Only a genuine newer version speaks, and even then it only offers — nothing is
downloaded until the user presses Update.

**Two family-wide defects were fixed to make this honest** (2026-09-12), both
older than QuillLite and both live in every companion app:

* *The wrong edition was offered.* `updates._app_asset_url` — the path every
  companion app takes — chose between the four assets by file extension alone,
  so of the two `-setup-*.exe` files it took whichever GitHub listed **last**,
  and a Companion listener was handed an `.exe` that cannot install their copy.
  It now asks `install_edition.detect()` first, as QUILL's own `_pick_asset`
  has since August. `matches_asset` gained an `app_prefix`, without which
  QuillLite is unresolvable: the product **name** contains "lite", so every one
  of its assets read as the thin installer.
* *The app never came back.* The full installers' shortcuts named
  `{code:RuntimeExe} -m quill.apps.<app>` directly, bypassing the per-app
  launcher that is the only thing exporting `QUILL_APP_ROOT` — so edition
  detection read the shared runtime's folder and concluded the user was running
  the Companion zip. They now go through `{app}\<App>.exe`, exactly as the thin
  installers always have. And `self_update` relaunched `sys.executable` bare;
  since the runtime layering landed (2026-08-17) that is
  `QuillVilleRuntime.exe`, which with no arguments writes a usage line and exits
  2 — invisibly, from a windowed build. It now carries `-m <module>`, resolved
  from `__main__.__spec__`, whenever the running executable is a generic
  interpreter rather than the app's own exe.

## 7. The QUILL-side fixes this work produced

Both were isolated by PR #1490 and both ship in
`quill/ui/richedit_rtf_surface.py`, where every QUILL user gets them.

**`_TOM_TRUE` was `tomUndefined`.** `tom.h` defines `tomTrue` as `-1`;
`-9999999` is `tomUndefined`, which means "leave this property alone". Assigning
it to `ITextFont.Bold` therefore asked the control to change nothing — and
succeeded. `set_heading` applied the point size, silently never applied the bold,
and raised nothing. Because `heading_level_for_font` requires bold before it will
call a paragraph a heading, **QUILL could not then find the headings QUILL had
just made**: heading navigation and Describe Formatting both went blind in rich
mode. Measured on `RICHEDIT50W` / Riched20 10.0.26100:

```
Bold = -9999999 (tomUndefined)  ->  Bold=0   Weight=400
Bold = -1       (tomTrue)       ->  Bold=-1  Weight=700
```

`standalone/quilllite/tests/repro_tom_true.py` reproduces it in isolation and
imports neither QUILL nor QuillLite, so it can be run against a clean checkout.

**A collapsed caret described the wrong paragraph.** A collapsed TOM range
reports the formatting of the character *before* it, so standing at the start of
a heading described the paragraph above it. `caret_format_description` now probes
the character *after* the caret, which is what a screen reader describes.

### 7.1 The spell checker, and the exception that makes it usable

QuillLite ships a spell checker because the products it is measured against
have moved: WordPad never had one and never will, but the Notepad on a Windows
11 machine today has had spell check and autocorrect since 2024. An editor
claiming Notepad parity without one is behind the thing it is copying.

None of the checking is new. The wordlist, the suggestion ranking and the
guided F7 review are QUILL's, reached through the same helper the Mastodon
compose box uses. What QuillLite added -- and what QUILL now shares -- is the
rule about **when not to speak**.

A live spell checker in `settings.json` flags every key; in `main.py` it flags
every identifier. Those alerts are not merely useless, they are asymmetrically
expensive: a sighted user's eye skates over a red underline it has learned to
distrust, while for this product's actual users each one is a status line to
read past. A feature that interrupts fifty times a minute is one people switch
off permanently, and a feature switched off permanently is a feature that was
never shipped.

So the default follows the file's extension, decided once per document, and
three things follow from it:

- **It is per document, not per app.** A letter and a config file open at the
  same time can honestly disagree, and `Ctrl+Alt+F7` changes only the one you
  are in.
- **It is announced when it is not the obvious answer.** A checker that is
  silently off cannot be told apart from one that is broken, so opening a
  skipped file says so once, and the menu item carries a check mark that reads
  the true state.
- **`F7` is never gated by it.** A default decides what happens when nobody has
  said anything. Pressing F7 is saying something.

QUILL already suppressed live alerts inside URLs, code spans and fenced blocks
(`spellcheck_live`), which is the right granularity in prose and no help at all
in a source file, where the whole document is the exception. It now consults
the same file-type rule QuillLite does, behind `spellcheck_skip_code_files`.

Markdown is deliberately *not* on the code list. It is where people write, and
suppressing the whole file would silence the prose along with the code; its
code regions are handled by `spellcheck_live`, at the granularity that fits.

### 7.2 Selection is three features, not one

Edit > Selection is the largest single surface QuillLite adds, and it is worth
saying why an editor this small carries one at all. It is a *submenu*: nineteen
items poured into Edit would swamp it, and another top-level menu on a small
editor's bar is a cost paid on every visit by everyone. A submenu is one
Alt+E, N away, and gives the group its own mnemonic namespace.

Selecting text without sight is a different job from selecting it with a mouse,
and the difference is not one of degree. There is no drag. There is no glance
afterwards that confirms you took what you meant to. Shift and an arrow key --
the answer every editor offers -- is fine for two letters and useless for four
paragraphs, because it gives no feedback and no sense of position.

So the menu offers three genuinely different mechanisms rather than one with
variations:

**Mark and extend** (F8). Anchor, move by any means, complete. The only way to
take an arbitrary run of text without holding a modifier down throughout, and
the only one that composes with *every* navigation key the editor has rather
than with a fixed set of chords. Ported key for key from QUILL, because a user
of both should not have to hold two versions of it.

**Structure.** Word, line, sentence, paragraph, block -- taken whole, without
needing to know where they start, then grown or shrunk a rung at a time. This is
the one that removes counting.

**Marks.** Throwaway positions, deliberately distinct from the nine bookmarks: a
bookmark is a place you decided to keep, a mark is where you were standing
before you went to look something up, and conflating them makes both worse.

One rule runs through all of it: **every command says how much it took.**
"Selected paragraph, 412 characters" is a fact somebody can act on. A selection
that announces nothing has to be verified by pressing something destructive and
seeing what disappears, which is not a test anybody should have to run.

Select All stays in Edit itself on Ctrl+A, outside this switchable area, so
turning the submenu off can never remove the one selection command that
predates all of it.

## 8. Future directions

### 8.1 Accepted for a later release (decided 2026-09-08)

QUILL's editor surface was diffed against QuillLite's, command table against
command table and user guide against user guide, and the result reviewed
against one test: does the absence read as a **defect against a promise this
product already makes** -- "Notepad and WordPad's keys, unchanged", and "QUILL's
accessibility" -- or as the restraint §1 asks for? Thirteen were accepted on
that basis. Every one of them already exists in QUILL, so §3.4's "not a feature
destination" is not in play: none is a new invention, each is shared code given
a door here, behind its own switchable area in the §3.3 sense.

**The Notepad baseline.** Insert/Overwrite mode -- Notepad has had it since
1985, and it becomes one more readable cell in the status bar §4.2 already
argues for. Tab as indent versus a literal tab, with Indent and Outdent on a
selection. Line operations: Move Line Up/Down, Delete Line, Join Lines --
today reordering two lines costs a select, cut, move and paste, which is four
keystrokes and a lost cursor for the reader this editor is for. Structured
deletion (to line start/end, delete paragraph) with QUILL's deletion ring,
which re-inserts recently deleted text *at the cursor* and so turns a delete
into a move -- something undo cannot do.

The first two settle an argument this document currently leaves half-made:
§5.4 already accepts that people edit `.json` and `.py` here, which is why
spell check goes quiet in them. Shipping that concession without Tab control
and block indent is one half of a position.

**Find and Replace**, which has Match case and nothing else. Whole word and
regular expressions; extended escapes (`\n`, `\t`, `\uNNNN`) so the invisible
characters **Describe Character** already names can also be *searched for* --
the two are halves of one workflow; Count Occurrences and a match list to arrow
through; and peek navigation with a spoken match count, so a search's shape is
known before it is committed rather than discovered one F3 at a time.

**Navigation.** Bookmarks that persist between sessions, and the last cursor
position restored -- §3.1 justifies bookmarks with "no scrollbar to remember
the position of", and that argument does not stop when the document closes.
Back and Forward location (Alt+Left/Right), the undo for navigation.

**Parity and the safety net.** A way to browse and restore the timestamped
backups QuillLite *already writes* -- a safety net nobody can reach is not one,
and this is the missing half of a feature that ships today. Heading promote and
demote, and moving a section with its body, so a document can be restructured
without the cut-and-paste most likely to lose a reader's place. Sentence Case
and Toggle Case, and the line transforms people actually reach for (numeric
sort, sort by length, reverse, number lines, hard wrap).

**Considered in the same pass and declined**, so the reasoning is not lost:
*browse mode / Quick Nav* single-key jumping -- the strongest accessibility case
of anything reviewed, and a modal layer over every keystroke, so it is its own
project rather than an item on a list; *match bracket and first-non-blank*, too
narrow for prose; *strikethrough, superscript, subscript and numbered lists* --
revisit numbered lists first if this is reopened, since an ordered list is
structure a reader announces rather than decoration.

### 8.2 Out of scope

Out of scope for 1.0, and each stated so it is a decision rather than an
oversight:

- **macOS**, via an `nstextview` surface.
- **A SAPI fallback**, as an opt-in setting, disabled by default — for a
  low-vision user with no screen reader running.
- **Preserving text colour in rich mode.** Colour is treated as presentation
  here, not as document content, which is what makes the dark theme safe.
- **Word paragraph styles.** Headings are presentational — the size-and-bold
  ladder — exactly as in QUILL's rich mode.
- **A portable inventory baseline.** `portable-inventory.json` can only be
  generated from a real build; QuillLite adopts one when it first builds on a
  release machine, as Inkwell and Converter still must.
- **Formatted printing**, via `EM_FORMATRANGE`. 1.0 prints the text in the
  editor's font with headings marked rather than styled, and the user guide says
  so -- shipping an untested ctypes printing path that produces blank pages
  would have been worse than shipping a plain one that is honest about it.
- **Reveal Codes**, considered for 1.0 and declined.
- **The `.LOG` file trick** -- a file whose first line is `.LOG` gaining a
  timestamp on open. In Notepad since 1985, and still not here.

## 9. Validation

- `ruff check .`, `ruff format --check .`, and scoped `mypy quill/core/lite`.
- `python -m quill.tools.platform_report` — every repo-wide gate, including the
  new GATE-LITE-HELP.
- The unit tier: the command table, settings, recovery, file encoding, the
  inbox, the file-type table, the two Rich Edit regressions, and the app shape.
- `standalone/quilllite/tests/repro_tom_true.py` and `probe_live.py` against a
  real `RICHEDIT50W` in a Windows desktop session (manual).
- A JAWS and NVDA pass by hand, against
  [`docs/qa/quilllite-signoff.md`](../../../docs/qa/quilllite-signoff.md) -- 80
  numbered steps, each saying what to press and what decides pass or fail, with
  a fifteen-minute subset named at the top. Matching Studio (#839) and Inkwell,
  this is **not** required for the change to merge but **is** required for the
  release to publish. It is the only thing on this list a machine cannot do:
  everything else here is automated, and what a person actually *hears* is not.
