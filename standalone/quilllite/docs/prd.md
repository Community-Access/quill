# QUILL Lite — Product Requirements

**Version 1.2.0 (build 5) · Windows · MIT · part of the QuillVille family**

Status, 2026-10-17: 1.2.0 is in beta for testers and not yet published; the
last published version is 1.1.2 (1.0.0 was first released on 2026-09-25).
Everything in the changelog's Unreleased section is built and documented.

## 1. Statement

QUILL Lite is QUILL with everything removed except the editor. One document per
window, plain text or rich text, and nothing else.

It exists for one person: someone who wants Notepad or WordPad with QUILL's
accessibility, and who finds the full writing environment more than they need.
That is not a small group. QUILL for All is a writing environment — AI,
dictation, conversion, comparison, publishing, braille tooling, extensions — and
for a great deal of what people actually do with a text editor, all of that is
in the way. Opening a `.txt` file to change one line should not start a product
with a setup wizard.

QUILL Lite is **not a replacement for QUILL** and **not a place new features go**.
Anyone who wants any of the list above wants QUILL. This is stated here, in the
requirements, because the pressure will be to add things: it is built so that it
cannot grow into QUILL without somebody deliberately deciding to abandon the
product it is.

### Provenance

QUILL Lite began as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`), offered under this repository's MIT licence.
That PR also isolated a real bug in QUILL's own Rich Edit surface — see §7 — and
deliberately did not fix it, so that adding an app and changing the editor stayed
separate decisions. Both decisions were taken; the fix ships with this release
and reaches every QUILL user, not only QUILL Lite's.

## 2. Architecture

Native Preferences search uses the shared `preferences_search` navigator,
installed by the dialog contract. It indexes labels, accessible names, and help
text, never field values; results focus existing controls without accepting the
dialog or mutating settings. Control+F returns to search, Enter navigates, and
Escape clears a query before closing. Disabled controls retain their state.

Activation repair is bounded to an event-loop check and one 75 ms settling
check. Every activation/deactivation changes a generation, so old callbacks
cannot affect a new activation. Repair acts only on shell/MDI containers or
missing focus, never another interactive control. Inactive or hidden shells,
hidden documents, menus, and shutdown suppress repair. It makes no app speech
announcement; native focus changes remain the screen reader's responsibility.

Settings writes return success or failure through
`LiteSettingsPersistenceMixin`. Failed writes keep session values active and
set `settings_dirty`; a coalesced, user-safe warning is spoken and remains in
the status message until a later write succeeds. Preferences never claims a
failed write was saved. Reopening Preferences retries already accepted settings;
new edits still require OK. Existing settings changes and session-close saves
also retry without a loop. Shutdown flushes a pending warning before teardown.
Logs contain only the stable `QUILL-LITE-SETTINGS-WRITE` diagnostic and storage
category, not raw exception text or user paths.

Document Open and Save As dialogs use the configured default document folder
when no saved document location applies. A blank setting resolves to the
Windows Documents folder; a document already saved continues to use its own
folder.

Application shutdown owns the inbox timer through
`QuillLiteApp.stop_background_sources()`. Confirmed Exit and shell close stop
polling before document destruction; `OnExit` repeats that cleanup safely.
Cancelling a close keeps polling active. A queued inbox tick must not consume
requests after shutdown starts, and requests left after a reentrant close are
reposted for the next launch. A deferred launch-update check must not start
after shutdown. Document timers remain each document's responsibility.

**QUILL Lite is not a fork.** That is the single most important architectural
statement in this document, and it is the difference between a sibling and a
copy that rots.

| Layer | Where | What |
|---|---|---|
| The app | `quill/apps/lite*.py` | The shell, the windows, their menus, commands, status bar and dialogs |
| Its own domain logic | `quill/core/lite/` | Settings, paths, recovery, the command table, file encoding, backups, the inbox, the feature areas |
| Logic QUILL should also have | `quill/core/numbered_bookmarks.py` | Nine slots that move with the text -- shared, not QUILL Lite's; see 2.2 |
| Its F1 catalogue | `quill/core/lite_surface_help.py` | What every window is *for* |
| The editor surface | `quill/ui/richedit_editing.py` over `quill/ui/richedit_rtf_surface.py` | QUILL's own control, extended — not copied |
| The product shell | `standalone/quilllite/` | Entry point, icon, installers, docs |

Everything under `quill/` is therefore covered by the repository's existing
gates — module-size budget, access-key uniqueness, the over-announce gate, the
dialog registry, the F1 audit — which is the reason the app code lives there
rather than in the product folder. A surface that no gate can see is a surface
that silently rots; QUILL Cast shipped an unreachable first-run dialog for two
releases exactly that way.

### 2.1 What QUILL Lite reuses rather than reimplements

Each of these is a QUILL finding that cost real on-device testing to establish.
QUILL Lite gets them by *using* QUILL's code, not by copying its conclusions:

- **The native `RICHEDIT50W` control** (a `wx.TextCtrl` with `TE_RICH2`). QUILL
  keeps it because its `IAccessible` value is reported correctly to NVDA and
  JAWS where a classic EDIT control's is not.
- **RTF through the Text Object Model, never `EM_STREAMIN`.** A `ctypes`
  `EDITSTREAM` callback hard-crashes msftedit — the control access-violates the
  instant it calls back into Python. The TOM path never calls back into Python.
- **`scan_rtf_safety` before a byte reaches the control.** RTF can embed OLE
  objects, executables, binary blobs and fields that fetch remote resources.
  QUILL Lite runs the identical scanner QUILL runs, from `quill/io/rtf_safety.py`.
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
  shipping an accessibility provider of its own. QUILL Lite therefore says
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
  and is never binding: **Alt+Shift+F** rings through all four kinds of
  document, **Ctrl+Alt+F6** goes straight to one, and the status bar's Format
  cell names whichever you are in. (The ring was Ctrl+Shift+M until the family
  pass gave that chord to Set Mark, under rule 3: frequency breaks the tie, and
  a mark is dropped mid-sentence where a mode is switched once per document.)
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
- **The line and case tools** — `format_ops` and `transforms`. QUILL Lite has no
  second implementation of "sort these lines"; a first draft did, and it was
  deleted, because two implementations is two places for them to start
  disagreeing about what a trailing newline means.
- **The clipboard stores** — `copy_tray`, `clip_library`, `clipboard_collector`.
- **Abbreviations** — the engine, the store, and the manager dialog.
- **Typing assists** (2026-10-16) — AutoCorrect for misspellings
  (`quill/core/autocorrect.py`, its built-in list and the AutoCorrect Entries
  window, `quill/ui/autocorrect_entries_dialog.py`) and Enter in a list
  (`quill/core/list_continuation.py`). QUILL had list continuation and QUILL
  Lite did not; both have AutoCorrect, on the same settings
  (`autocorrect_misspellings`, `continue_lists_in_plain_text`, both off by
  default) and the same key (Alt+Shift+9).
- **The command palette**, the **feature-areas dialog**, **char_describe**,
  **selection**, **print pagination**, and the **announcement path**.

### 2.2 QUILL Lite is never allowed to be ahead of QUILL

This is a rule, not an aspiration, and it has already cost work twice.

If QUILL Lite needs something the editor cannot do, the capability goes into the
**shared** package and the editor gets a way to reach it in the same release. A
feature the small product has and the big one does not is exactly backwards --
and worse, it is invisible: nobody opens QUILL and notices the absence of a
thing they have only ever seen elsewhere.

In this release that meant:

- `create_richedit_rtf` now builds `RichEditDocument`, so every QUILL tab has
  the paragraph and view capabilities QUILL Lite needed, by construction rather
  than through a second factory;
- QUILL gained **Justify**, **line spacing**, **Grow/Shrink Font**, **Paste Text
  Only** and **rich-mode bullets** -- five commands whose capability had always
  been in the surface with nothing bound to it;
- numbered bookmarks live in `quill/core/numbered_bookmarks.py`, not under
  `lite/`, so QUILL's editor can adopt them;
- a first draft of QUILL Lite's own line and case tools was deleted and replaced
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
  files exactly as QUILL Lite does;
- `load_combined_dictionary`, `load_scope_dictionary` and `add_word_to_scope`
  gained an optional `personal_dir`, so a sibling app can keep taught words in
  its own folder. QUILL passes nothing and behaves precisely as before -- the
  extension point exists because QUILL Lite needed it, and it lives in QUILL's
  module rather than in a copy of it.

Where the two must differ, they differ **on purpose and in writing**, and the
reason is a comment in `keymap.py` rather than folklore.

That principle stands; the example it used to give does not. This paragraph
recorded `Ctrl+Alt+J` and `Ctrl+Alt+V` as deliberate divergences from WordPad's
`Ctrl+J` and `Ctrl+Shift+V`, on the grounds that an existing binding somebody's
hands already know outranks a new command's convention. The family keymap
reversed both (bad.md §3, rule 1: Microsoft's key wins where Word, WordPad or
Notepad bind one for a function both editors have). Keeping the paragraph would
have left the PRD describing a divergence the products no longer have -- which
is worse than describing none, because somebody reads it and writes code to
match.

The divergences that remain are listed in the family keymap's exception table
and each carries its own reason. **QUILL Lite may never be ahead of QUILL**
remains the rule (`CLAUDE.md`); value crosses both ways, violations cross one.

### 2.3 What QUILL Lite adds to the shared package

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
| Theme, following the system by default | See §4.4 |
| Nine numbered bookmarks that move with the text | No scrollbar to remember the position of |
| Structural selection (word, line, paragraph, expand) | Shift+arrow is the wrong tool for a paragraph |
| Describe Character | A reader says "space" for four different characters |
| A twelve-slot copy tray, a collector and a clip library | The system clipboard holds one thing |
| Abbreviations, over QUILL Lite's own library | Expansion is an accessibility feature, not a typing one |
| AutoCorrect for common misspellings, with your own entries in that same library | A misspelling found by ear costs a read-back; one fixed as it is typed costs nothing |
| Enter continues a Markdown list (and, if asked, a plain-text one) | A marker typed by hand is a marker that can be forgotten, and the reader never says one was |
| Sort, de-duplicate, trim, and three case conversions | Work, not writing — and expensive by keyboard |
| Printing and Page Setup | Every text editor Windows has ever shipped has Ctrl+P |
| The Command Palette | Answers "how do I sort lines?", which is the real question |
| Switchable feature areas | See §3.3 |

### 3.2 What it drops, and why

Tabs, dictation, self-voicing, preview, Quillins, remote files, GitHub, braille
tooling, the setup wizard, comparison, publishing, and every companion app.

**The command palette is not on that list any more**, and was listed here in
error: §3.1 and the command table have always had it, and it ships. A document
that says a shipped feature was dropped is worse than one that says nothing,
because somebody reads it and does not go looking for the key.

**AI came off the list on 2026-09-23**, and the distinction matters because the
list is not meaningless now. What arrived is **five commands behind one pad** on
QUILL's own free hosted service, under two gates (§5.6). What is still dropped
is everything else QUILL's AI is: bring-your-own-key, the provider list and the
default cascade, local models, the agent harness, the conversation, alt text,
and the setup wizard that configures them. The reason for the exception is the
reason the product exists: summarizing and explaining a passage is
disproportionately valuable to somebody who cannot skim, and an editor that is
only usable by somebody who reads a screen quickly is not much of an accessible
editor.

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

**Switchable feature areas.** QUILL Lite stays small by being *switchable*, not
by being poor. `Tools > Customize Features` turns whole areas off, and switching
one off removes its menu **and** its keys -- a key that still fires for a feature
somebody turned off is the feature not being off. Somebody who wants Notepad
unchecks rich text, and the Format menu is gone entirely.

Four areas ship **switched off** and are found in that same checklist rather
than hidden, because a feature nobody can find is a feature that does not exist:
autocorrect (welcome in prose, actively wrong in a config file; since
2026-10-16 it holds three rules, curly quotes, em dashes and misspelling
correction, each its own Preferences checkbox, all off), timestamped
backups (reassuring, and they fill a folder), Go To Anything (the palette, the
headings list and the bookmark list each already answer their own part), and AI
help, which is off because it sends what you ask about off this computer -- a
different kind of reason, and the one that needs a second question as well as a
switch (§5.6).

**Nineteen areas now.** *Markdown and HTML* arrived on 2026-09-15 with the rule
that decides what Ctrl+B writes in a `.md`, and *AI help* on 2026-09-23. Both
are areas rather than bare settings for the same reason the rest are: switching
one off has to take its menu rows and its keys with it, and a setting cannot do
that.

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

Nineteen checkboxes is the right way to change one thing and the wrong way to
say "give me the small one". :data:`quill.core.lite.features.PROFILES` is four
named starting points -- **Recommended**, **Everything**, **WordPad**,
**Notepad** -- and the design rules behind them are worth stating, because each
one has a cheaper wrong version.

**A profile is a baseline, not a mode.** Applying one checks and unchecks every
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
| Recommended | 17 of 21 | unchanged | the shipped answer, and the way back from experimenting |
| Everything | 21 of 21 | unchanged | turning things off as they annoy you rather than finding them one at a time |
| WordPad | 5 of 21 | **rich** | letters and notes that should look like something |
| Notepad | 2 of 21 | **plain** | config files, logs, and anything where hidden formatting would be a problem |

The four Recommended leaves off are autocorrect, timestamped backups, Go To
Anything and **AI help** -- and the last of those is off for a different kind of
reason from the other three. Those would be *wrong* on; this one is off because
using it sends the passage you ask about over the internet, which is not a
choice a default gets to make on somebody's behalf. See §5.6: the area switch
and the agreement are two separate questions, and Everything can turn the first
on without ever answering the second.

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
- ~~**Not keymap-customisable.**~~ **Reversed 2026-09-10.** This said QUILL Lite
  had one fixed table and that was that. The table is still the *defaults* --
  it is what the uniqueness gates assert against -- but
  `quill/core/lite/keymap.py` puts a resolution layer over it and
  `Tools > Keyboard Manager` (Ctrl+Alt+Shift+Space) edits it. What stays true is the
  reason the non-goal was written: QUILL's chord grammar, its `APP_KEYMAPS`
  overrides and its Key Describer are a writing environment's features and are
  still not here. Rebinding a key is not.
- **Not a second clipboard manager.** The tray, the collector and the library
  are QUILL's own stores, kept in QUILL Lite's folder. Nothing is reimplemented.

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

QUILL Lite adds a stricter check of its own
(`tests/unit/tools/test_lite_control_help.py`), because the shared scanner has
two blind spots that matter here: it does not treat `wx.CheckBox` as helpable
(and the Find and Replace windows are half checkboxes), and it cannot see a
control built by a factory in another module — which is *the document itself*,
the control a listener is in for all but a few seconds of a session.

### 4.3 The status bar is navigable, not decorative

QUILL's status bar is a row of focusable cells rather than painted text, and
QUILL Lite's is the same: **F6** lands in it, arrows and Home/End move between
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
and selection changes. QUILL Lite announces only outcomes it alone knows: "Bold
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

### 4.5 Speech, and braille through QUILL's coalescer

QUILL Lite announces through a running screen reader and nowhere else.
`ScreenReaderVoice` reaches NVDA and JAWS through Prism or accessible_output2
and Narrator through a UIA notification, and hands nothing to the engine unless
a reader is actually running. There is **no self-voicing fallback**.

**Braille (corrected 2026-10-16).** This section used to say QUILL Lite had no
braille output. That stopped being true when the shared engine began mirroring
every announcement to the display (#1283), and when dictation's live preview
gained `ScreenReaderVoice.braille`. What QUILL Lite lacked was QUILL's burst
coalescing, so a dictation preview or a run of status changes replaced the
display faster than it could be read. Now the engine's inline braille is
switched off when the voice builds it (`set_braille_enabled(False)`), and every
braille write -- the mirror of a spoken message, after the speech and only when
the speech went out, and every `braille()` preview -- goes through one
`quill.ui.announce_wiring.CoalescingBrailleWriter`, QUILL's own class: the first
message of a quiet moment writes at once, and a burst lands as its newest
message one 150 ms window later. Speech timing is unchanged. QUILL Lite has no
braille settings group and gains none; what follows is about why it still does
not have one.

The rest of this section was written about a second output channel with its own
settings, and still stands as the reason QUILL Lite has no braille *settings*.

**Why.** A braille route is not a line of code; it is a delivery channel with
its own verbosity rules, its own truncation problems, and its own way of being
wrong -- QUILL's braille surface is several modules and a settings group. The
editor this PRD describes is meant to stay small enough to be read in an
afternoon, and adding a second output channel is the kind of thing that makes a
Notepad-scale product stop being one.

**What a deafblind user gets instead, and why it is not nothing.** Every
message QUILL Lite speaks also lands in the status bar's message cell (4.3), and
the status bar is a row of real focusable buttons rather than a painted strip.
A braille display reaches it by cursor routing like any other control, and F6
puts the caret there in one keystroke. So the information is available; it is
pull rather than push. What is genuinely lost is the *unprompted* announcement
-- a background result a listener would have heard, a deafblind user has to go
and look for.

**What would have to change.** The announcement path is one seam
(`ScreenReaderVoice.speak`), so the work is not in QUILL Lite: it is deciding
whether QUILL's braille service can be lifted into the shared package without
bringing its settings group with it. If it can, QUILL Lite gets braille for the
cost of one call. Until somebody has answered that question, this section is
the honest description of where the product stands.

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

The interval is a setting (`autosave_seconds`, 15–600 seconds, **default 30**),
reachable only from Preferences -- **Copy unsaved work aside every (seconds)**.
It has no key and no menu row, deliberately: it is a number somebody sets once.

### 5.2a When the screen reader dies (2026-10-16)

QUILL's screen-reader watchdog, through the same wx-free core
(`quill/core/sr_watchdog.py`) and a small mixin on the app
(`quill/apps/lite_sr_watchdog.py`). Every 30 seconds the running reader is
detected; two consecutive misses confirm a death (one, a routine restart, never
does). Then every window with unsaved changes writes its recovery copy at once
(5.2) and the shared sentence -- "NVDA appears to have stopped. Your work is
safe: 2 documents snapshotted to autosave. QUILL Lite keeps running; restart
your screen reader when ready." -- goes to the active window's status bar and
to the voice, which speaks only if another reader is running. A recovery
re-probes the voice and says "NVDA is running again." It never closes the app,
and no setting gates it, in either editor.

### 5.3 Its own data folder

Settings, recent files and recovered work live in `%LOCALAPPDATA%\QuillLite`,
deliberately **not** in `%APPDATA%\Quill`. QUILL Lite is offered as an
alternative to QUILL rather than as a client of it: a Notepad-scale editor that
silently adopted a writing environment's settings would be making a decision
nobody asked it to make, and uninstalling it could then cost somebody something
QUILL owns. A machine that has never had QUILL installed must not grow a Quill
folder because somebody opened a text file.

This is why QUILL Lite does not use `quill.core.ipc` for its single-instance
guard — that lock lives in QUILL's data directory. It uses
`wx.SingleInstanceChecker` (a kernel object, with no file to go stale) plus its
own inbox directory. Uninstalling never removes the data folder either: recovery
slots are the one thing somebody may not have finished with, and an uninstaller
is the worst possible moment to discover that.

**The one bridge, and why it does not contradict any of that (2026-09-18).**
QUILL Lite has always been able to *read* QUILL's abbreviations and personal
dictionary, behind a switch the person turns on. QUILL now has the other half:
`quill/core/lite_bridge.py` and **Tools > Customize and Support > Bring My
QUILL Lite Settings...** (`Alt+Shift+F11`) merge QUILL Lite's copies of five
content stores into QUILL's folder, copy the settings and rebound keys that
translate, and turn those sharing switches on so the two editors stop keeping
separate copies. Five properties keep this inside the principle above rather
than against it:

* **Nothing moves without an explicit ask.** The command is a menu item and a
  key. The one place it is offered rather than invoked -- activating the
  QUILL Lite feature profile in QUILL -- asks a Yes/No question, once ever, and a
  No is remembered.
* **The plan is described before it is applied**, counts first and what is being
  *left behind* last, because "it copied your settings" is not something a
  listener can verify afterwards by looking at the screen.
* **QUILL wins every collision** and nothing already in QUILL is replaced.
  `merge_json_store` is shape-agnostic on purpose -- these five files are a dict,
  a list, or a dict with a list in it, and five mergers would be five schemas to
  keep in step -- and it writes nothing at all when the two sides are different
  shapes. A merge that cannot be done safely is not done: these files are the
  user's work.
* **QUILL Lite's own settings file is written once, for two booleans.** That is
  the only thing this module writes into `%LOCALAPPDATA%\QuillLite`, and it is
  the half without which a "shared" store looks broken -- QUILL holding the words
  while QUILL Lite still reads its own copy.
* **The direction is QUILL Lite -> QUILL.** A machine that has never had QUILL
  still grows no Quill folder, because the command lives in QUILL and cannot run
  where QUILL is not installed.

Both write sites are classified in `quill/tools/persistence_audit.py`
(`merge_json_store` as content, `enable_lite_sharing` as marker), so neither can
be added to or moved without somebody re-stating what they do.

### 5.3a Two instances, one settings file (F-11, 2026-10-01)

`--new-instance` runs two processes against one settings file. Each used to
write its whole in-memory copy, so the last to save undid every preference the
other had changed -- atomic writes stop a half-written file, not a valid older
snapshot replacing a valid newer one. A save is now a three-way merge
(`quill/core/lite/settings_merge.py`): the app keeps the settings it loaded or
last wrote as a baseline; at save it re-reads the file, writes its own value
for every field it changed since the baseline, and keeps the file's value for
every other field. Last writer wins per field, not per file. The running
instance's in-memory settings are never replaced by the other's -- a silent
change to theme, font or speech mid-session is the thing this product must not
do -- so the other's choices apply at its next launch. An unreadable file is
not merged against (that would reset untouched fields to defaults); the save
falls back to the whole-object write.

### 5.3b When a focus repair does not take (F-04, 2026-10-01)

The activation repair (one check after the event loop, one 75 ms later) can
still be overruled -- Windows restoring focus after the second check, or a
control that refuses it. That is the residue a listener reports as "sometimes
it works", so `lite_shell._note_repair_miss` counts it per shell
(`focus_repair_misses`) and logs `QUILL-LITE-FOCUS-MISS` with the class of
whatever holds focus and the session count -- never a title, a label or a word
of a document, because the log travels in support bundles. Nothing is
announced. It is not a family helper yet: QUILL's own repair (#170) is a
different mechanism, and a shared helper with one caller is speculation; it is
extracted when a second app adopts this shape.

### 5.3c Opening is prepare, then commit (F-05, 2026-10-01)

`DocumentFrame.load` read, decoded and RTF-scanned on the UI thread, so a
large file, a slow share, a scanner holding the read or a damaged RTF froze
the window with nothing said. Opening is now two halves:
`quill/core/lite/open_prepare.prepare` (wx-free, any thread: read, decode or
scan, return an immutable `PreparedDocument`) and
`DocumentFileMixin._commit_load` (UI thread only: the Rich Edit control and
everything a load implies). `load()` still runs both synchronously, so every
existing caller is unchanged. `open_prepare.prepare_in_background` routes a
file of 1 MiB or more, or a UNC path, through
`lite_window_open.DocumentBackgroundOpenMixin.begin_background_load`: a new
window, read-only while empty-and-loading, "Opening <name>" announced once
and on the status bar, the read on the app's lazily created two-worker
`TaskManager`, the commit on the UI thread only when the open generation still
matches, the window's `UiLifetimeToken` is alive and the app is not shutting
down. Closing the window is Cancel. Failure asks Try Again; declining closes a
window that holds nothing else. A file still opening counts for the
already-open check, so a second request focuses it instead of reading it twice.
The app's shutdown owner stops the pool. Not done: Open as Plain Text on
failure (a rich file that fails the scan still reports through the box).

### 5.4 File associations

The full installer offers "Open .txt and .rtf files with QUILL Lite" as an
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

QUILL Lite had neither half of that. It shipped with **no reporting item at
all**, only an address printed in the About box to copy out by hand.

The form is the same one every app in the family opens
(`quill/ui/support_dialog.py` over `quill/core/support_message.py`): what kind
of message this is, a subject, and what happened. What you expected and how to
reproduce it are optional. **Your email address is optional too** — a problem
can be reported without giving one, and because the message goes from the
reader's own mail account, support can still reply to that (corrected
2026-09-26; this used to say nobody could answer). Send opens
**your own mail program with the message already written**, with QUILL Lite's
name and version, your Windows version and your screen reader appended. Nothing
leaves the machine until you send it there, and the app says so out loud rather
than claiming to have sent something it has not. A machine with no mail program
set up — webmail only — gets the whole message and the address on the
clipboard, so nothing typed is ever lost.

Writing to `support@community-access.org` directly works exactly as well. There
is no form anybody is required to use.

**No GitHub credential, anywhere (2026-09-26).** Every piece of feedback from
QUILL Lite and Quill Radio goes to `support@community-access.org`; nothing is
filed as a GitHub issue. So the build no longer generates or embeds the bundled
"feedback token" (`scripts/build_release.ps1` lost `-TokenFile`/`-SkipToken`,
and a public build no longer fails without one), and the support form no
longer tries the feedback-hub dialog first: email is its only route. The mail handoff is `support_dialog.send_by_mail`, shared with
Quill Radio's Suggest a Station or Podcast so both cut, copy and fall back
identically.

### 5.6 AI help: two gates, not one

QUILL Lite carries five AI commands -- summarize, rewrite, proofread, explain, and
ask a question about the open document -- on QUILL's own hosted service. They are
the *only* part of this product that sends anything off the machine, which is why
they sit in this section rather than in Scope.

**Two independent gates, both of which must be true before a byte leaves.** The
feature area answers *does this exist in my copy*; the agreement answers *have I
agreed to what it does*. Collapsing them into one switch gets the second one
wrong, because an area can be switched on by a profile, by a settings import, or
by another person using the machine, and none of those is consent.

The agreement is therefore:

- **Asked for on its own**, never as a side effect of enabling something.
- **Stored as a version, not a boolean.** A material change to what is sent or
  retained asks again, rather than an old yes being read as covering a new thing.
- **Reachable by three doors** -- `Tools > AI > Privacy Agreement`
  (`Ctrl+Alt+Shift+K`), a Preferences check box, and switching the area on in
  Customize Features -- because which door somebody finds depends on which part
  of the app they already know. All three read and write the same value, so they
  cannot disagree.
- **Never dimmed.** The Privacy Agreement row opens whether or not the area is
  enabled and whether or not the agreement has been accepted. A door reachable
  only by first agreeing to something is not a door, and withdrawal has to be as
  easy as acceptance.

**Withdrawal signs the machine out.** Keeping a sign-in for a service just
declined would leave the key in a door the user has closed. Signing out, by
contrast, does *not* withdraw the agreement: it is a smaller action and must not
silently perform a larger one.

**Shape: one pad behind one key, not five keyed commands.** Measured across
Ctrl+Alt, Ctrl+Shift, Alt+Shift and Ctrl+Alt+Shift, the chords free in *both*
editors are few, and family rule 2 requires a command both products have to keep
its chord -- so five separate keyed commands were never available. The single pad
is the better shape regardless: one surface showing what is about to be sent, one
showing what remains, one consent surface.

**Family rule 10 holds.** The capability is shared rather than QUILL Lite's own,
so QUILL runs the same five commands on the same five chords from the same
module. QUILL Lite is not ahead of QUILL here; QUILL has more AI, not less, and
none of its existing provider list, default cascade, bring-your-own-key, agent or
local-model paths changed to make room for this.

### 5.6a Conversations: memory without a multiplier (1.1)

A conversation was the one AI shape deliberately left out of the free tier,
because it resends its history on every turn and so each reply costs more than
the last. It ships in 1.1 on the condition that removes the multiplier: **the
conversation so far is trimmed to the same input ceiling every request has**,
newest turns first, on this computer (`quill/core/ai/hosted_chat.py`) and again,
authoritatively, on the service. A turn is one request and never costs more than
any other; conversations have a monthly share of their own (`feature_cap.chat`,
40 of 100). What a long conversation loses is memory of its opening, and the
window says so aloud the first time that happens rather than leaving somebody to
infer it from a puzzling answer.

**No new command, no new chord.** Chords free in both editors are the scarcest
resource in the family (section 5.6), so a conversation is reached from the pad
(**Have a conversation**, a seventh choice) and from the result window (**Follow
Up**, which seeds the conversation with that question and answer, and keeps a
document question's excerpts attached). The window is modeless; focus lives in
the message box and each reply is announced, because it lands in a transcript
that does not have focus -- the one case GATE-13 says the app must speak.

**With the user's own API key (OpenAI or Google Gemini) there is no trimming**: the whole conversation
goes, and is shortened only past what the model can read at once.

**Family rule 10 holds**: the window, the pad row and Follow Up live in the
shared `quill/ui/hosted_ai_*` modules, so QUILL has them in the same release on
the same keys.

### 5.6b Ten writing tools (1.1)

The pad grows from seven choices to seventeen: Shorten, Simplify, Make more
formal, Make friendlier, Turn into a list, Find action items, Suggest headings,
Continue writing, Write an email reply, and Translate. The rule for admitting a
tool is the same one that admitted Summarize: **one passage in, one result out,
at the ordinary size**, so no tool is a new worst case for the free service
(each is one request, with a monthly share of 60). Each is a fixed template on
the service; the client sends only the passage, and Translate's target language
is the one value it fills in, from a fixed list of twenty checked on both ends,
because a free-text field there would be a place to smuggle instructions.

The choice of tools is aimed at the people this product is for: **Simplify**
for letters from banks, hospitals and lawyers; **Turn into a list** and **Find
action items** because a list is far quicker to review by ear than a
paragraph; **Suggest headings** because headings are what a screen reader
navigates by, so it turns a flat passage into one you can move through. The
list of seventeen is a list box, so a first letter jumps to a tool.

**New tools without a release (2026-10).** The service's `GET /v1/config` now
carries a feature catalogue: each shipped tool's id, label, one-sentence help
and input kind (`selection`, `prompt` or `document`). Any entry this build does
not have built in becomes a row at the end of the pad's list, after Have a
conversation: its help is the row's F1 text and Send runs it through the same
path as the built-in rows. Requirements: every field is validated as remote
input (id shape, plain text with control characters removed, length caps, at
most 40 entries); an unknown input kind is skipped, never guessed; an entry
duplicating a built-in id or label is dropped; rows arriving while the pad is
open are appended at the end and not announced (GATE-13); a per-tool input
ceiling may only lower the pad's pre-check; the answer opens in the ordinary
AI Result window. Only on the free service, since the tool's instructions live
there. Shared code (`quill/core/ai/gateway_catalogue.py`,
`quill/ui/hosted_ai_pad_catalogue.py`), so QUILL has it in the same release
(family rule 10).

**QUILL's saved conversations, Prompt Library and word-level review
(2026-10-15).** Brought from QUILL through shared code, never copied, with QUILL
moved onto the extracted pieces in the same change. Requirements: every AI
conversation is saved as it goes in QUILL's session format
(`quill/core/ai/sessions.py`, `record_exchange`) in QUILL Lite's own
`ai-sessions` folder, and **Saved Conversations** (Alt+V in the conversation
window) opens one to continue or deletes one after asking; **Prompt Library**
(Ctrl+7) is QUILL's `PromptLibraryDialog` over QUILL's library format
(`prompts.json`, `.pqp` packs) in QUILL Lite's data folder, and Run fills the
prompt, closes, and sends it as a general question, refusing before sending if
it is over the input ceiling; **Review Changes** in the result window opens
QUILL's Review AI Changes (`quill/ui/ai_diff_review_dialog.py`), offered only
when Replace is and the answer differs, and applies only accepted changes as one
undo step. Every control in the three windows has F1 help.

**Going back over a conversation, and exporting it (2026-10-17, todo item
44).** Shared with QUILL's Ask Quill and AI Conversation window
(`quill/core/ai/chat_navigation.py`, `quill/ui/ai_conversation_tools.py`), so
neither editor is ahead (family rule 10). Requirements: Alt+1 to Alt+0 read
the ten newest messages aloud with position and speaker ("Message 4 of 9, AI:
..."), never moving focus or the half-typed message, and say how many there
are when fewer than asked; **Messages...** (Alt+G) lists every message, Enter
opens one with real headings and tables, Read as Text shows it verbatim, and
closing returns to the same row; **Export Conversation...** (Alt+X) writes the
whole conversation, every message with its speaker and in order, to `.docx` or
`.txt` through the shared document writers, asks before overwriting, and never
receives the active document; a reply arriving while the transcript has focus
keeps the reader's caret. The same on the free AI, an own key and a ChatGPT
plan, each saving to the same `ai-sessions` store.

**Answer delivery and the Chat Key (2026-10-15).** No spec existed, so the
minimum: the pad's **Put the answer in** list chooses the AI Result window
(default), the document at the caret (one undo step, read aloud), or the
clipboard (read aloud; falls back to the window if the clipboard is busy), kept
as `ai_answer_delivery` (QUILL's field name too) and applied to every answer.
**Ask AI a Question** (Ctrl+6), the Chat Key, opens the pad on Ask a General
Question with the caret in the question box.

**Web search on the free AI (2026-10-15).** The service's `web_search` feature
ships off behind a feature flag, ten searches per account per month; while on,
the catalogue offers **Search the web** in the pad. **Web Searches Left**
(Ctrl+9) reads `/v1/config`'s `web_search` entry and `/v1/quota`'s count and
says how many are left, or that search is not offered; on an own key or plan it
says search is the free service's. QUILL has the same three commands on the same
three chords (rule 2).

### 5.6c Your own API key: a provider chosen, never inferred (1.2, qc.md X-07)

**Use My Own API Key** (`Alt+F2`, formerly Use My Own OpenAI Key) sends AI help
straight to the provider the person chooses -- **OpenAI or Google Gemini** --
on their own key, with no QUILL server and no allowance. The requirement that
shaped it came from reviewing PR #1615, which made Gemini keys work by inferring
the provider from a model name and falling back to whichever key was stored.
That half was not taken. The requirements instead:

- **The provider is an explicit choice**, the first control in the window, and
  the persisted setting `ai_own_key_provider` (`"openai"` or `"gemini"`) is the
  only thing that decides where a request goes. Nothing is inferred from a key's
  shape or a model's name (`quill/core/ai/own_key.py`, `chosen_provider`).
- **No fallback between providers.** With Gemini chosen and only an OpenAI key
  saved, the route is not active and AI help is on the free service; OK says so
  and names the unused key. A request made anyway is refused with a sentence
  before anything is sent.
- **Earlier consent is kept.** An empty `ai_own_key_provider` means OpenAI, the
  only provider there was when 1.1 keys were saved. An unknown value means *no*
  provider, never a guess.
- **One key per provider, in the existing secure store**: the AI Hub's
  per-provider credential targets (Windows Credential Manager, or the encrypted
  file in a portable copy), shared with QUILL; never plaintext, never shown
  again. A typed key is cleared, and the clearing announced, when the provider
  choice moves, so a key cannot be saved under the wrong company.
- **Gemini requests stream** from `streamGenerateContent?alt=sse` on
  `generativelanguage.googleapis.com`, HTTPS only, the key in `x-goog-api-key`,
  the gateway's instructions in `systemInstruction`
  (`quill/core/ai/own_key_gemini.py`, built from the shared pure builders in
  `quill/core/ai/endpoints.py` and `assistant_ai.build_chat_body`). OpenAI
  requests are unchanged and not streamed, because OpenAI refuses streaming
  from unverified organisations for some models.
- **Stop works.** The pad's Send button is Stop while a request is on its way;
  `AiService.cancel(request)` sets only that request's event, so stopping one
  window cannot cancel work started by another. On Gemini the stream is closed
  before the next piece is read; on every other route the outcome is dropped on
  arrival. Neither an answer nor a failure is delivered after Stop.
- **Errors are one sentence, spoken, actionable, and never contain the key.**
  Gemini answers a wrong key with HTTP 400 `API_KEY_INVALID`, not 401, so the
  key-rejected case is read from the body; 401 and 403 are rejections too
  (`QUILL-AI-OWN-KEY-REJECTED`). 404, 429 and 5xx each have their own sentence
  (`QUILL-AI-OWN-KEY-FAILED`), a busy Gemini is tried once more, and every
  sentence passes through `own_key.scrub`.
- **Model ordering is deterministic** (`quill/core/ai/own_key_models.py`):
  Gemini's list is filtered (embeddings, Imagen, Veo, speech, live audio, image
  generation, AQA) and ordered stable before preview, newest version first,
  Flash, Flash-Lite, Pro, then by name; OpenAI's order is unchanged. Cost
  estimates are per provider, and Gemini's note says what Google's free tier
  means for privacy.
- **Shared, so QUILL has it the same day** (family rule 10): the window
  (`quill/ui/hosted_ai_own_key.py`), the service (`quill/ui/hosted_ai_service.py`,
  with its route sentences split into `quill/ui/hosted_ai_route_words.py` under
  GATE-11) and the pad are the shared `hosted_ai_*` modules both editors use.
- One new egress site, `own_key_gemini._open_stream`, reviewed in the egress
  audit. Tests: `tests/unit/core/ai/test_own_key_gemini_route.py` runs the
  shipped code against a loopback server shaped like both providers, with
  synthetic keys.

### 5.6d What is spoken, and where a request goes (2026-10-16)

**Spoken answers are speech-safe.** An answer delivered at the cursor or on the
clipboard, and every conversation reply, is spoken through
`quill.core.ai.spoken_answer.speakable_line`: Markdown symbols and link
addresses are left out of what the reader is handed. The inserted, copied and
transcript text is the answer as it came.

**A route change asks first.** The shared `AiService` remembers which route
requests took this session (ChatGPT plan, own key, free AI). A request that
would take another without the listener having chosen it -- a key gone from the
store, a sign-in that stopped working -- is a substitution
(`quill.core.ai.fallback.plan_substitution`) and asks in a Yes/No box, No the
default; No sends nothing. Signing in or out of ChatGPT and saving or removing a
key mark the new route as chosen. Shared with QUILL, which has the same pad.

### 5.7 Every switch has a way back, from inside the app

A preference somebody can turn off and cannot turn back on is not a preference;
it is a trapdoor. The rule is that the surface that sets a value is a surface
that can also unset it, and that the way back is reachable **without editing a
file** -- because the population this product is written for is exactly the one
that cannot be told "open the JSON in your profile folder".

The one place this was broken until 2026-09-24 is worth recording, because it is
the shape the rule exists to catch. The Reopen Last Session window's **Never Ask
Again** wrote `session_restore_ask = "never"`. Nothing else in either editor ever
wrote that key: not Preferences, not the window itself on any later visit. The
window then stopped appearing at launch, and although `File > Reopen Last
Session...` still *opened* it, there was no control in it that could undo the
setting. The button's help text made it worse by naming a real setting that is
not this one -- "Reopen last session" is `restore_session`, whether to reopen at
all -- so following the instruction produced a different effect and no clue.

**Ask Me Next Time** is its twin. Exactly one of the pair is enabled, decided by
the mode the caller passes in, and the disabled one is **greyed rather than
hidden**: a removed control leaves somebody hunting the window for it, where a
disabled one announces itself as unavailable the moment a reader arrives on it.
The same choice the two tag pickers make, for the same reason.

Not a Preferences row, deliberately. The window that asks the question is where
somebody looks to answer it, and adding a row to QUILL Lite's Preferences that
QUILL's Settings does not have would put the small product ahead of the large
one (§2.2) over a control that belongs in the shared window anyway. Both editors
gained it in the same change, which is what rule 10 requires.

### 5.8 Dictation: the reliability pass, and words taught in a window (2026-09-28)

Nine sections of the dictation plan (`dict.md` 2.2, 2.3, 2.5, 2.6, 2.7, 2.8,
3.1, 3.3 and 5; that plan is now `docs/design/2026-10-05-dictation-plan-and-status.md`,
whose Appendix A maps its section numbers), implemented in the shared Live Dictation stack so QUILL has
every one of them on the same keys (rule 10). The design constraint from that
plan holds throughout: nothing here costs the baseline machine anything while
dictation is idle, and the watchdog's only running cost is one comparison per
audio block.

**Requirements, and where each lives.**

- **Escape cancels the phrase being heard** (2.2). `controller.cancel_phrase`
  answers only in the *recognising* state, asks the recogniser to `discard()`
  what it has (the local engine drains its queue, resets the voice detector and
  drops any transcription already under way by a generation counter; Windows
  speech purges and re-arms), ignores a phrase the engine finalises afterwards
  until the next utterance starts, and says "Cancelled". Routed by a char hook
  on the document window, so it runs before the control sees the key and
  consumes it only when there was something to cancel
  (`core/windows_dictation/resilience.py`, `ui/windows_dictation_tools.py`).
- **The microphone watchdog** (2.3). The local recogniser's worker declares the
  device lost after two seconds with no audio blocks or three seconds of exact
  zeros (a quiet room never produces exact zeros), closes the stream, and tries
  to reopen it every two seconds. The controller gains a *paused* state that is
  still "on" -- the menu mark stays, no phrase is written, the status cell says
  "paused, microphone lost" -- and resumes on the device's return, both said in
  the plan's words (`local_recognizer.py`, `resilience.py`).
- **One Ctrl+Z per phrase** (2.5). The document port writes every phrase
  through `replace_as_one_undo`, the path the AI inserts and paste already
  used; remove-then-write over a selection had been two steps.
- **Read-only refusal** (2.6), before the microphone opens, in the plan's
  wording.
- **The self-healing engine** (2.7), in two layers: a decode that raises is
  retried once on a freshly loaded engine inside the worker; a recogniser that
  fails outright is reopened once, silently, by the controller. The second
  failure names the engine and the one to try instead
  (`resilience.engine_failure_message`). A fresh session earns a fresh restart.
- **One session at a time** (2.8). Ctrl+F11 in another document while dictation
  runs retargets the one controller and says "Dictation moved to <name>".
- **Dictate into any text field** (3.1). `bind_field_dictation` gives Find,
  Replace and the AI pad's question box the toggle chord and the Escape; the
  document port answers `single_line()`, so a paragraph break becomes a space
  and no closing full stop is added.
- **Recent phrases** (3.3). The controller keeps the last twenty phrases of the
  app session, separate from the scratch-that history that a stop clears;
  `RecentPhrasesDialog` offers Insert Again (one undo step) and Copy.
- **Teaching dictation your words** (5, as the plan's option A plus a window
  instead of a file). `words_file.py` models `dictation.md` as words, phrases
  and corrections; the writer regenerates the file in the parser's own shape,
  with a `## Corrections` heading the profile parser already folds into
  replacements, so a correction is applied after recognition on every engine
  with no new runtime code. `DictationWordsDialog` is the window; the Dictation
  Settings button opens it. Found on the way: the starter file's explanatory
  sentences were being parsed as vocabulary, now excluded (`looks_like_prose`).
- **Import, Export and the shared list** (dict.md D-12, 2026-10-15). My Words
  and Phrases exports to Markdown or CSV (`say,write,kind`) and imports either,
  merging only: new entries are added after a preview, entries already there or
  different keep the person's own, and the list is copied to
  `dictation-before-import.md` first (`words_exchange.py`). "Use the shared word
  list" (`share_quill_dictation_words`, off) points QUILL Lite at the family's
  `dictation.md`, the one QUILL, QUILL Transcribe and Quill Inkwell read, after
  merging QUILL Lite's own entries into it; never offered in a portable copy.
  Since 2026-10-16 that file lives in `%LOCALAPPDATA%\QuillVille\Dictation`,
  copied there from QUILL's data folder with the old file kept as the backup
  (dictation design record section 30). "Share dictation settings with the
  family" (`windows_dictation_share_family`, More Dictation Settings, Alt+Q)
  keeps the shared dictation settings in `family_dictation.json` beside it,
  written on OK and taken when the window is activated (dict.md D-13).

**Tests.** The core behaviours against a fake recogniser and a fake document
(`tests/unit/core/test_windows_dictation.py`), the words model round-trip and
its edits (`test_dictation_words_file.py`), and each Lite handler through the
window it runs in (`tests/unit/apps/test_lite_dictation.py`); the command
coverage gate stays at zero `shape_only`.

### 5.9 Dictation: holding the key, live words, the AI, and OpenAI (2026-10-05)

The rest of the dictation plan, after studying VS Code's dictation (credited,
behaviour by behaviour, in `docs/design/2026-10-05-dictation-plan-and-status.md`,
which also holds everything still to do). All of it is shared code, and
`tests/unit/ui/test_dictation_parity.py` fails if QUILL and QUILL Lite differ in
a dictation command, key or setting.

- **Hold-to-talk** (`hold.py`, `windows_dictation_hold.py`): hold Ctrl+F11 for
  half a second and talk, let go to stop; a quick press toggles; key repeats are
  ignored. Off by default (owner, 2026-10-05): one press starts, the next
  stops; **More Dictation Settings** turns it on.
- **Finishing, not cutting off**: stopping while a phrase is being heard waits
  for it (`LiveMixin.finish`, the worker's `finish`), with a four-second limit.
- **The live preview** (`streaming.py`, `recognizer_worker.py`, `live.py`):
  Nemotron runs as a streaming model on one stream per session; its provisional
  words show as "Hearing: ..." in the status cell and on braille, never in the
  document; the mark it writes once it hears the next phrase corrects the last
  one (so its questions end in question marks).
- **Words go where you started** (`EditorDocument.anchor`): measured on speech
  start, honoured even if the caret moved or the focus left.
- **"Correct that"** and "choose one" to "choose three", with Windows speech
  recognition's alternates. Since 2026-10-16 (D-19), with Moonshine, Whisper or
  a downloaded model, the other built-in engine re-decodes the last phrase's
  audio (memory only, dropped at the next phrase) and offers its answer as
  choice 2; OpenAI, the speech companies and Spanish still say there is none.
- **Replace, change that, delete by paragraph, kept revisions** (D-19,
  2026-10-16, `corrections.py`): "replace X with Y" (nearest before the cursor,
  else after), "change that to Y" (the last phrase), "delete previous
  paragraph"; what choose, replace and change that replaced goes into Recent
  Phrases labelled "(before correction)".
- **Talk to the AI** (`hosted_ai_chat._talk_to_it`): the AI Conversation
  window's message box dictates with the **Talking to AI** profile, sends at the
  pause (or on Enter), and mutes the microphone while the reply is read.
- **OpenAI dictation, own key only** (`openai_models.py`, `openai_transcribe.py`,
  `openai_recognizer.py`): off by default, a plain consent, the model chosen
  from OpenAI's live list without retiring models, Realtime transcription for
  `gpt-live-transcribe`, never a silent switch, refused in Safe Mode, three
  reviewed egress entries, and a Dictation section in the privacy statement.
- **Speech providers, own account only** (2026-10-16, dictation design record
  section 23, D-31 to D-37; the same as QUILL through the shared
  `quill/core/windows_dictation/cloud/` package and `quill/ui/speech_providers_dialog.py`):
  Dictation Settings' **Speech Providers...** (Alt+V) sets up Azure, Google,
  Amazon, Deepgram, AssemblyAI, Speechmatics, ElevenLabs, Gladia, Rev.ai, Groq,
  Mistral or IBM Watson; secrets in Windows Credential Manager, Test Connection
  never sends speech, a generated consent with No the default, refused in Safe
  Mode, never recommended, never a silent switch.
- **Model tiers and a recommendation** (D-22) and **one sherpa-onnx store**
  (D-26): Speech Models names Lightweight, Balanced or High accuracy on every
  model and recommends one for this computer (What matters most, Alt+W);
  downloads are shared with QUILL and QUILL Transcribe. Since 2026-10-22 the
  advice, tiers and memory budgets come from real speech; see "Dictation model
  advice from real speech, and five models removed (2026-10-22)" at the end of
  this document.
- **My Dictation Instructions** (`instructions.py`) for Tidy Dictated Text.
- **Kind to a modest computer** (`keep_up.py`): the keep-up watchdog and models
  unloaded five minutes after the last session.
- **Settings**: eight new `windows_dictation_*` fields, and all 24 now declared
  once (`settings_fields.DictationSettings`), inherited by both editors'
  `Settings`.

### 5.9a Dictation: correcting yourself, styles, polish and learning (2026-10-16)

The same as QUILL (QUILL PRD, the D-20/D-21 addendum; dictation design record
section 28), through the shared dictation package, so QUILL Lite is never
ahead. **Fix it when I correct myself** (Alt+X, off) keeps the second of
"Thursday, no, Friday" between two days, months, numbers or names in My Words,
locally and conservatively. **Dictation style** (Alt+Y) names Verbatim, Clean
and, only with AI on, Polished, and stores nothing itself. **Allow polishing my
dictation with AI when I ask** (Alt+G in More Dictation Settings, off) lets
"QUILL polish that" and **Polish** (Ctrl+P) in Review Dictation send one fixed
request through the review's own consent and AI routes; it is never automatic.
A second identical voice correction offers to add it to Corrections, in a
Yes/No window with No the default; nothing is stored without a yes.

### 5.10 Transcribing a recording (2026-10-06)

QUILL Lite's **Transcribe a Recording** command (Shift+F5) transcribes supported
audio files in the background using the shared dictation speech engines. Its
window reports recording length and estimated transcription time; on Windows,
duration lookup falls back to Media Foundation when the other metadata readers
cannot determine the length. Several selected recordings run in sequence.

The transcript is saved privately and is not inserted into the document the
user was editing. A completion notice in Notifications opens the saved
transcript when activated; Activity retains the outcome and failure reason.
There is no destination picker.

**Translate into English** (2026-10-16, dict.md D-26): for a recording in a
language other than English, with a model that translates (the built-in
Whisper, or a downloaded multilingual Whisper), the transcript can be written
in English instead. The check box is unavailable otherwise and off unless
checked. QUILL's offline transcription translates on the same models, because
all three apps now run every local model through one shared sherpa-onnx layer.

## 6. Release packaging

**Two** artifacts: the portable build and the system installer. That is the
family contract for every app (2026-10-11), and QUILL Lite reached it first:

| Artifact | Built from | Output | Measured |
|---|---|---|---|
| Installer | `installer/quilllite.iss` | `QuillLite-Setup-Shared-1.0.0.exe` | 117 MB |
| Full portable | `build_portable.py --product quilllite` | `QuillLite-Portable-1.0.0.zip` | 94 MB |

**Why two** (2026-09-15). QUILL Lite used
to ship the thin `QuillLite-Lite-Setup` and the launcher-only
`QuillLite-Companion` zip as well, and both were wrong for this product. The
Companion zip installs nothing, so it binds to whatever shared runtime is
already on the machine -- including one frozen before QUILL Lite existed, which
fails at launch with `No module named quill.apps.lite` and cannot repair itself,
because the launcher's runtime bootstrap only fires when *no* runtime resolves
and a stale one resolves perfectly well. The thin installer traded a 117 MB
download for a 110 MB first-launch download plus a network dependency, on the
one app somebody installs *because* they have nothing else -- so the runtime is
usually absent and the saving is notional. Retiring both is safe for anyone
already on one: the two installers share an AppId, so this one upgrades a thin
install in place, and `core/updates.py` falls through to an installable asset
when a release publishes none for the running edition. On 2026-10-11 the rest
of the family followed: every app now ships only the portable build and the
installer.

The download names spell the product as one mixed-case word, `QuillLite-*`,
never `Quill-Lite-*`: a screen reader speaks `QUILL Lite` as the product's name,
where a hyphenated form is read out punctuation and all.

The installer script is named `quilllite.iss`, not `quill-lite.iss`: the family
used the `*-lite.iss` suffix for the retired *thin* installer flavour, and
`quill-lite.iss` ends in it -- so the installer was being audited as a thin one.
Every other identifier for this product is already `quilllite` (the folder, the
`AppRefId`, the launcher product key), so the installer matches it.

`portable-inventory.json` is committed and enforced: the portable build fails on
any drift from it, which is the class of defect that once put 82 MB of
undeclared payload into a runtime installer.

Both come from `scripts/build_release.ps1`. The shared QuillVille Runtime at
`%LOCALAPPDATA%\QuillVille\Runtime\3.13\` is reused: the installer ships it and
lays it down only when what is already there is older, and the portable bundle
carries its own interpreter and never touches it at all.
**Neither ffmpeg nor libmpv is staged** —
QUILL Lite declares no media components, and the build strips any a sibling app
left in the shared work area, so build order cannot change what ships.

The installer is per-user: `PrivilegesRequired=lowest`, with no elevated
all-users override. App files and the shared runtime are installed for the
signed-in user. The optional runtime setting that replaces Notepad for every
user remains a separate, explicitly elevated action.

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

Before this, QUILL Lite could not tell its user that a newer version existed. It
is the app most likely to be somebody's only Quill product — installed by a
person who wanted Notepad — and therefore the app whose users are least likely
to go looking on GitHub. They would have stayed on 1.0.0 forever with no way to
know that was happening.

**The dialog is shared, and it always shows what changed.** `quill/ui/
update_notice.py` is the one "an update is available" surface for QUILL, the
eight companion apps and QUILL Lite: the release notes flattened out of Markdown,
capped and never empty, with **Update** as the affirmative and default and
**Close** as the escape. Focus lands on the notes rather than on a button, so
the first thing read is the release notes and not the word "Update". QUILL alone
adds **Skip this version**, because QUILL alone has a settings field to remember
the answer in. The download, its spoken 25/50/75 milestones, and the
Install-and-restart dialog are `quill/ui/update_download.py`, shared the same
way — QUILL Lite has no `TaskManager`, so it supplies a one-shot thread instead
and gets the identical experience.

Releases resolve from `RELEASE_REPO` and `RELEASE_ASSET_PREFIX` in
`quill/core/lite/__init__.py`, deliberately **not** from
`companion_install.ASSET_PREFIX`: that table is the set of QuillVille apps QUILL
can offer to *install for you*, and QUILL Lite is a separate product rather than
a sibling QUILL launches.

The silent launch check says nothing in every direction but one: nothing while
it runs, nothing when there is nothing, and nothing when the network is down.
Only a genuine newer version speaks, and even then it only offers — nothing is
downloaded until the user presses Update.

**Two family-wide defects were fixed to make this honest** (2026-09-12), both
older than QUILL Lite and both live in every companion app:

* *The wrong edition was offered.* `updates._app_asset_url` — the path every
  companion app takes — chose between the four assets by file extension alone,
  so of the two `-setup-*.exe` files it took whichever GitHub listed **last**,
  and a Companion listener was handed an `.exe` that cannot install their copy.
  It now asks `install_edition.detect()` first, as QUILL's own `_pick_asset`
  has since August. `matches_asset` gained an `app_prefix`, without which
  QUILL Lite is unresolvable: the product **name** contains "lite", so every one
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

### 6.2 When it cannot start, it says so (2026-09-28)

`QuillLite.exe` is the family's native launcher, and until 2026-09-28 it
spawned `pythonw.exe`, waited, and threw the exit code away. A portable Quill
Radio that "just doesn't return anything" was the report that ended that.
Now the launcher writes the engine's stdout and stderr to a launch log
(`data\logs\launch.log` beside a portable copy,
`%APPDATA%\Quill\logs\QuillLite-launch.log` for an installed one, replaced on
every launch) and, on a non-zero exit, shows one `MessageBox` a screen reader
reads unaided: "QUILL Lite did not start", the reason in words, the log's
path and the support address. Windows' silent endings (a DLL not found, a
damaged or 32-bit file, access denied) are translated; a Python traceback's
last line is quoted with a hint. Pressing Enter on the exe *inside* the zip is
recognised from the archive tool's scratch-folder name and explained as
"extract the whole zip first". Exit 0 stays silent, so the single-instance
hand-off is unchanged. Shared code (`quill/native/launcher/launch_report.c`,
pinned to a Python mirror in `tests/unit/native/test_launch_failure.py`);
QUILL Lite gains it at its next launcher build, and the user guide's Getting
help chapter already opens with "If QUILL Lite does not start".

## 6a. The family pass (2026-09-18)

A twenty-nine item audit of the two editors against each other, closed in
September 2026. It is recorded here because three of its outcomes are now
constraints on this product rather than one release's work.

**The eleven rules are code.** `quill/core/family_rules.py` holds them and both
`keymap.py` and `lite/parity.py` cite them **by number**; a test checks that
every citation resolves, so the rules cannot be renumbered into lies. Lower
number wins when two conflict. Rule 1 -- Microsoft's key wins for a function both
editors have -- is itself a gate (`tests/unit/core/test_microsoft_habits.py`),
checked against both keymaps rather than believed; it found the last disagreement
on the day it was written, and Word's `F12`, `Ctrl+F12` and `Ctrl+Shift+F12` are
aliases in both products because of it.

**Divergence is a written argument.** `DIVERGENCES` in `quill/core/lite/parity.py`
holds the eight handlers whose chord is allowed to differ, each with the reason,
and the gate prints the reason when it reports the pair -- so the next person
reads the argument instead of re-having it. `SETTINGS_ALIASES` does the same for
the five settings one concept is stored under two names for, and the vocabulary
gate (`quill/tools/settings_vocabulary_audit.py`, in `platform_report`) fails a
new setting that is neither shared, aliased, nor a reviewed one-sided field. Two
of the five real pairs share no word at all, which is why it is a reviewed table
and not a name-similarity check.

**Rule 10 now cuts both ways in practice.** QUILL Lite may never be ahead of
QUILL, and the audit found places where it was: QUILL got the `DocumentText`
model QUILL Lite already had, the spelled suggestions QUILL Lite already spoke, the
Spelling Announcements window, and the swallowed-formatting-key guard. Where
QUILL Lite was behind, it gained Word's F12 family and the shared-store bridge
(5.3). Neither direction is a favour: a capability in one product and not the
other is invisible to the person who only has the other one.

---

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
imports neither QUILL nor QUILL Lite, so it can be run against a clean checkout.

**A collapsed caret described the wrong paragraph.** A collapsed TOM range
reports the formatting of the character *before* it, so standing at the start of
a heading described the paragraph above it. `caret_format_description` now probes
the character *after* the caret, which is what a screen reader describes.

### 7.1 The spell checker, and the exception that makes it usable

QUILL Lite ships a spell checker because the products it is measured against
have moved: WordPad never had one and never will, but the Notepad on a Windows
11 machine today has had spell check and autocorrect since 2024. An editor
claiming Notepad parity without one is behind the thing it is copying.

None of the checking is new. The wordlist, the suggestion ranking and the
guided F7 review are QUILL's, reached through the same helper the Mastodon
compose box uses. What QUILL Lite added -- and what QUILL now shares -- is the
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
the same file-type rule QUILL Lite does, behind `spellcheck_skip_code_files`.

Markdown is deliberately *not* on the code list. It is where people write, and
suppressing the whole file would silence the prose along with the code; its
code regions are handled by `spellcheck_live`, at the granularity that fits.

### 7.2 Selection is three features, not one

Edit > Selection is the largest single surface QUILL Lite adds, and it is worth
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

### 7.8 The thesaurus and the dictionary came to QUILL Lite, and Look Up came back to QUILL (2026-10-02)

The family rule ran both ways in one change. QUILL Lite had no thesaurus at
all -- a comment in the command table said it needed an asset download, which
was never true: the 18 MB MyThes file ships in every copy. QUILL's thesaurus,
meanwhile, looked up the word as typed and offered headwords, so "running"
found nothing and "sprint" was offered where "sprinting" was needed. Both are
fixed once, in shared code: `quill/core/word_lookup.py` walks a word back to
the headwords the data knows and inflects every replacement forward, and
`quill/ui/word_tools_commands.py` is the one `WordToolsMixin` both editors mix
in through `HostedAiMixin` -- Shift+F7, the *Thesaurus for "word"* and
*Dictionary for "word"* submenus on the context menu, Say Word Summary, and
the AI dictionary. QUILL's `show_thesaurus` now delegates to it.

**Look Up** (`quill/ui/lookup_window.py`, DICT-2's window) had been reachable
in QUILL only when the thesaurus data was missing, and it went online whenever
the dictionary feature was on, which is not consent. It is now Tools > Writing
> Look Up Word (Alt+F10) in QUILL and Tools > Look Up Word in QUILL Lite, the
online half is behind **Use online sources** in the window itself
(`dictionary_online_lookups`, the same field name in both settings files, so
the vocabulary gate sees one setting), and the online answer arrives on a
worker and replaces the offline one with a sentence said when it lands.

**The AI dictionary** (`quill/core/ai/word_tools.py`: one feature id, one
system instruction asking for JSON -- prose for listening and exact
replacement texts -- and thirteen prompts; `quill/ui/word_tools_window.py`:
the answer window) runs only on a direct route, because the free service is
metered per person and a dictionary is asked a hundred times a day. QUILL
reaches the same thirteen commands through a Dictionary submenu of its AI
menu (`quill/ui/main_frame_hosted_ai.py`), on QUILL Lite's chords exactly.

Gates that moved: a new Customize Features area, `dictionary`, with the
profile counts now 17, 21, 5 and 2 of 21; `commands_words.py` split out of
the command table under GATE-11; the Lite coverage snapshot has sixteen new
handlers, every one called by a test in `tests/unit/apps/test_lite_words.py`;
and menu_lint's rule against bare Ctrl+Alt chords (AltGr) decided the keys the
less-used rows carry.

## 8. Future directions

### 8.1 Accepted for a later release (decided 2026-09-08; shipped 2026-09)

**Everything in this section has shipped.** It is kept as the record of *why*
each item was accepted, because the reasoning is the part worth having and the
list itself is now the command table. Overwrite mode, tab mode, the line
operations, the deletion ring, persistent bookmarks, back and forward, Earlier
Versions, promote and demote, sentence and toggle case, reverse and number
lines are all in the shipped product; so, since 2026-09-17, are three of the
four things the last paragraph declined --- Extend Selection Mode, the Heading
Organizer and folding over Markdown sections --- which arrived by the other
route, as crossings from QUILL rather than as inventions here (bad.md 4.2).

Read it as history. The live list of what is still open is the family parity
plan, not this section.


QUILL's editor surface was diffed against QUILL Lite's, command table against
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
backups QUILL Lite *already writes* -- a safety net nobody can reach is not one,
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
- **Word paragraph styles beyond the shared vocabulary.** Revised
  2026-10-17: QUILL Lite now edits `.docx` through QUILL's own Word code (see
  *Word documents and table navigation*), so Heading 1-6, the list styles and
  Title, Subtitle, Quote and Caption go out as real Word styles. In the editor
  headings stay presentational -- the size-and-bold ladder -- exactly as in
  QUILL's rich mode, and every other Word style arrives as a normal paragraph
  with its visible formatting. That is the honest boundary: style sheets,
  custom styles and style editing remain out of scope.
- **A portable inventory baseline.** `portable-inventory.json` can only be
  generated from a real build; QUILL Lite adopts one when it first builds on a
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
  [`docs/qa/quilllite-signoff.md`](https://github.com/Community-Access/quill/blob/main/docs/qa/quilllite-signoff.md) -- 254
  numbered steps, each saying what to press and what decides pass or fail, with
  a fifteen-minute subset named at the top. Matching Studio (#839) and Inkwell,
  this is **not** required for the change to merge but **is** required for the
  release to publish. It is the only thing on this list a machine cannot do:
  everything else here is automated, and what a person actually *hears* is not.

## Find in Open Documents (2026-10-15)

QUILL's command from the same shared code (QUILL has it on Ctrl+Shift+F10, because its Ctrl+Alt+Shift+F8 is a QuillVille launcher; `parity.DIVERGENCES`) (QUILL Lite may never be ahead of QUILL, and here it is not behind either): **Edit > Find in Open Documents...** (**Ctrl+Alt+Shift+F8**; in Edit > Matches until 2026-10-16, see the placement note under Search in Files) finds and replaces across every open window's live text. The window and the model are QUILL's (`quill/ui/open_documents_find.py`, `quill/core/open_documents_search.py`); QUILL Lite supplies `quill/apps/lite_open_documents.py`, which lists `app.frames`, brings one to the front with `focus_frame`, and keeps the search state on the app so F3 in any window carries on the same search. Find and Replace end it (`cmd_find`, `cmd_replace`). Handler `cmd_find_open_docs`, parity `edit.find_in_open_documents`. Asked for on QUILLVille by Chris Nova.

## Search in Files and Replace Across Files (2026-10-15)

**Placement, revised 2026-10-16.** Find in Open Documents, Search in Files and Replace Across Files are rows of **Edit** itself, directly under Replace, in that order (`&Edit`, "F&ind in Open Documents...", "&Search in Files...", "Replace Across Files..."), and QUILL has the same three rows in the same order under Find All Matches. They first shipped inside **Edit > Matches**, and Jeff, launching from source with the changelog in hand, could not find either: a listener arrowing down Edit hears "Matches, submenu", and nothing in that word says a folder search is behind it, while QUILL filed the same commands in a different place again (Edit for one, Edit > Search Tools for two, and the two only in profiles with regular-expression search). Family rules 1 and 2 decide it: one placement for a command both editors have, and the placement a newcomer looks in first. **Edit > Matches** keeps the two commands about the document in front of you, All Matches and Count Occurrences. The three stay in the `matches` area (`command_areas.COMMAND_AREA`), now labelled "Matches and wider searches": on in a new install, off in the Notepad and WordPad profiles, whose promise is to have only what those programs had. Search in Files took the access letter S from Character Details, whose title has no other free letter in Edit; it keeps Ctrl+Alt+C. Replace Across Files has no access letter for the same reason and is reached by Ctrl+Shift+R or by arrow (GATE-14: no mnemonic beats a duplicate). Keys are unchanged. GATE-DOCMENU (`tests/unit/docs/test_documented_menus_lite.py`) now checks every menu path and every command named beside a key in this app's changelog and guide against the menus a new install builds, and pins the three Edit rows.

QUILL's two commands, on QUILL's keys -- Ctrl+Alt+Shift+F had been reserved for Search in Files since the keyboard parity work and never filled. The window moved from `quill/ui/main_frame_file_search_prompt.py` into the shared `quill/ui/file_search_prompt.py` (QUILL's mixin now only supplies its folder, parent and modal helpers), and the work is QUILL's `quill/core/file_search.py`. QUILL Lite's `quill/apps/lite_file_search.py` runs it on the app task manager and puts each report in a new untitled window, where QUILL opens a generated tab. Handlers `cmd_search_in_files` and `cmd_replace_in_files`, parity `tools.search_in_files` and `tools.replace_in_files`.

## The clipboard collector (2026-10-15)

QUILL's system-wide collector (#964), on QUILL's key, from QUILL's pieces: `quill/apps/lite_clipboard_collector.py` polls the OS clipboard change counter (`ui/main_frame_clipboard_collector._clipboard_change_counter`), appends with `core/clipboard_collector.append_collected`, collects each distinct payload once, keeps one collecting window per app, and stops when it closes. With QUILL's shared setting `clipboard_collector_saves` (2026-10-15, on by default, Preferences "Save after every clip the clipboard collector adds", Alt+Y) a window with a file name is saved quietly after each clip through `DocumentFileMixin.save_quietly`, which shares the write and the settling with Save, and the one announcement is "Collected and saved"; an untitled window is never saved and no window ever opens. Anything Save would ask about in a window (characters the encoding cannot hold, a file changed on disk) and a failed write are spoken instead ("Collected, but not saved." and the reason), and collecting carries on. The rule and the words are `core/clipboard_collector`, the same as QUILL's. Handler `cmd_clipboard_collector` (Alt+Shift+S, a check row on Edit > Clipboard), parity `power.toggle_clipboard_collector`. The parity table had mapped `cmd_collect_selection` to that command, which was never the same verb; Collect Selection is now `LITE_ONLY` with Paste and Clear, on Alt+Shift+C (rule 2: the command both editors have keeps the chord). Asked for on QUILLVille by Dean Martineau.

QUILL's system-wide collector (#964), on QUILL's key, from QUILL's pieces: `quill/apps/lite_clipboard_collector.py` polls the OS clipboard change counter (`ui/main_frame_clipboard_collector._clipboard_change_counter`), appends with `core/clipboard_collector.append_collected`, collects each distinct payload once, never saves, keeps one collecting window per app, and stops when it closes. Handler `cmd_clipboard_collector` (Alt+Shift+S, a check row on Edit > Clipboard), parity `power.toggle_clipboard_collector`. The parity table had mapped `cmd_collect_selection` to that command, which was never the same verb; Collect Selection is now `LITE_ONLY` with Paste and Clear, on Alt+Shift+C (rule 2: the command both editors have keeps the chord). Asked for on QUILLVille by Dean Martineau.

## PDFs, opened as text (2026-10-15)

QUILL Lite opened text files and nothing else; it now opens PDFs, as their text, and never writes one. Everything comes from QUILL (QUILL Lite may never be ahead of QUILL, and here it may not have a second implementation either): `quill/core/pdf_open.py` reads through QUILL's `quill/io/pdf.py` reader (pdfplumber, then pypdf, repaired text, form feeds between pages, at most 200 pages, the outline); `quill.io.structured._format_pdf`, which QUILL's File > Open uses, reads through the same function. QUILL Lite's half is `quill/apps/lite_window_pdf.py`:

- **Open.** `*.pdf` is in the Open filter's "All supported files" and has its own row. `open_prepare.prepare` reads a PDF into a `PreparedDocument` carrying the `PdfOpen` result, and `prepare_in_background` sends every PDF to the worker; `load` does too.
- **Password.** A locked PDF asks in QUILL's password box (`quill/ui/pdf_password.py`), then re-reads in the background with the password; a wrong one asks again saying so; Cancel opens nothing. The password travels in one `wx.CallAfter` and the worker closure, and is stored nowhere.
- **Damaged or no reader.** A failure box with the reader's own sentence; nothing opens.
- **Scanned** (no text, or under 50 characters a page): QUILL's question (`scanned_question`). Yes runs `ocr_pdf_for_open` as a background open -- Tesseract if installed, otherwise Windows OCR from the shared runtime, which needs no download (`quill/io/docconvert_windows.py`) -- with "Recognizing page N of M" on the message cell only, and opens the result with form feeds, marked modified. No opens the little text there is, or nothing. QUILL asks the same question on File > Open.
- **Pages.** The status bar gains a **Page** cell ("Page 3 of 12"), shown only while the document has form feeds, skipped by the arrow keys when hidden; Enter on it opens Go To on its Page kind. Go To (Ctrl+G) offers **Page** and **Outline** only when the document has them (`page_places`, `outline_places`, the same rows QUILL's Go To shows); outline rows resolve their page from the text at the time of the jump. The numbered bookmarks are untouched: nine slots cannot hold an outline.
- **Save.** The window keeps the PDF's path (title, Recent Documents, document memory), so Save refuses with QUILL's sentence (`save_refusal`, `EXPORT_ONLY_SUFFIXES`) and goes to Save As with `<name>.txt` proposed; Save As refuses a `.pdf` name; Reopen with Encoding is not offered; a reload after another program changes the PDF runs the whole open again.
- **No new command, no new key.** Ctrl+O and Ctrl+G, as in QUILL. Not done yet: headings and tables from the PDF (phase 3). File > Import / Convert Document and the portable build's dependency groups followed on 2026-10-17 (next section).

## Import / Convert Document, the portable PDF reader, page breaks and the 200-page gate (2026-10-17)

**File > Import / Convert Document (OCR)...** is QUILL's `file.import_convert` on QUILL Lite's File menu (handler `cmd_import_convert`, `quill/apps/lite_window_import.py`, parity `file.import_convert`). No key in either editor: rule 2 (the shared command keeps QUILL's binding, which is none) and rule 9 (occasional, and the next thing it does is ask which file); the reasons are rows in `KEYLESS_WITH_REASON` and `UNBOUND_WITH_REASON`, and `file.import_convert` is now in `DEFAULT_KEYMAP` as an unbound id so the parity table can name it. Mnemonic **I** (File's D belongs to Recent Documents). Nothing is reimplemented: `quill.io.docconvert.convert_document` reads (QUILL's Office readers, the PDF's own text through `quill.io.pdf`, OCR), and every sentence -- the scanned question, the opened sentence per tier, the failure box, the file list -- moved out of `quill/ui/main_frame_docconvert.py` into the wx-free `quill/core/import_convert.py`, which both editors call with their own `app_name`. QUILL's wording is unchanged and its tests are untouched.

- **Where the text goes.** This window when `_is_blank()`, otherwise `app.new_window(PLAIN)`; committed with the Open from URL path (`_commit_download`): untitled, `download_name` = `"<stem> (converted)"`, modified. Never the source path, so Save cannot write over it.
- **OCR.** A Tier 1 outcome flagged `offer_local_ocr` asks `scanned_import_question` (Yes / No / Cancel, Yes the default); Yes runs `convert_with_on_device_ocr` (Tesseract if installed, else Windows OCR). QUILL Lite never offers the Tesseract download and has no Datalab tier. A picture goes straight to OCR: `convert_document` now routes images through `convert_with_on_device_ocr` as well, which fixed the same dead end in QUILL (Tesseract-only, "Install it from Tools > OCR...").
- **Background and cancel.** The app's task manager, a `UiLifetimeToken` per conversion (`_import_lifetime`), progress on the message cell only, and `cancel_background_load` (called as the window closes) invalidates it, which also stops OCR between pages.
- **Spoken.** "Converting <name>" (or "Reading <name> with OCR on this computer") once; the opened sentence plus any outcome warning; failures through `_report_failure`. The reader's "Download Optional Components" sentence is replaced with `NO_PDF_READER`, as on Open.
- **GATE-LITE-COVER.** `tests/unit/apps/test_lite_import_convert.py` calls the handler for cancel, a Word file, a busy window, a warning, the three scanned answers, two failures, no OCR engine, and a window closed mid-conversion.

**The portable build** (`standalone/studio/scripts/build_portable.py`): the `quilllite` product gains the `office-text` and `ocr` dependency groups, and a `must_import` tuple (pdfplumber, pypdf, pypdfium2, the two winrt namespaces, `quill.io.pdf`, `quill.io.docconvert`) that step 8 imports inside the bundle, failing the build if any cannot load. `portable-inventory.json` is regenerated only from a real build: the next build's inventory gate reports the new packages as unexpected until it is rebaselined with `check_runtime_inventory.py <dist> --layout portable --manifest standalone/quilllite/portable-inventory.json --write` after review.

**Page breaks.** A PDF's text reaches the Rich Edit control with U+000C between pages, in plain mode and (unchanged, as `.pdf` is plain language) after a switch to rich. The Page cell and Go To's Page kind count those characters through `quill.core.navigation` and display numbers only. Two fixes: `quill/core/speakable.py` (`speakable_controls`, form feed and vertical tab to a newline, other C0/C1 controls dropped, tab/CR/LF kept) runs in `AnnouncementEngine.announce` and `.braille` -- every announcement in the family -- and in QUILL Lite's `_announce` before the status cell; and `char_describe` names U+000C "Page break". What a screen reader says when the caret is on the character, and whether Rich Edit draws a line break there, is a live check (`docs/qa/screen-reader-checks-2026-10.md`).

**GATE-PERF for PDFs.** `tests/unit/core/test_pdf_open_budget.py` (marked `perf`) opens a 200-page synthetic PDF through `open_prepare.prepare` within 150 ms a page, then builds the Page rows and the last page's position within 500 ms. The 60-page corpus budget (todo item 52, 293 ms a page against 250 on a loaded machine) was timing a read under `tracemalloc`, about four times slower than the reader itself (121-129 ms against 28-29 ms a page here, 2026-10-17); memory and time are now two separate reads, and no reader code changed.

## The Read-Only Guard, Word names, and typing a name in a list (2026-10-16)

**Read-Only Guard.** QUILL's command (EDS-8) on QUILL's key: **Tools > Read-Only Guard** (**Ctrl+Alt+Backspace**, a check row), handler `cmd_toggle_read_only`, parity `power.toggle_read_only_guard`. The memory is QUILL's module, `quill/core/read_only_guards.py`, with QUILL Lite's own file in its data folder (`paths.data_file`, which does not create the folder to read). Keys are normalised the way document memory is, so a file opened from File Explorer under another spelling finds its guard. A failed write is spoken, never swallowed. While on, the control is read-only and `quill/core/lite/read_only.TEXT_CHANGING_HANDLERS` are refused by name at the menu and status-cell dispatch (`DocumentReadOnlyMixin.run_unless_read_only`) with "Document is read-only"; reading, Find, Go To, bookmarks and inline notes work, a note going beside the file through the shared `_host_read_only`; a word tool's Replace refuses through `refuse_if_guarded`. A file that cannot be written opens guarded, as in QUILL.

**Word names.** (As of 2026-10-16; the first clause was overtaken the next day, see below.) QUILL Lite then neither opened nor wrote Word documents; a typed `.docx`, `.docm`, `.dotx` or `.dotm` was refused with one sentence naming Rich Text (`filetypes.word_save_refusal`) before anything else is asked, on Save As, Save and the collector's quiet save. Before this, the window's text was written under the Word name. QUILL writes `.docx`; QUILL Lite is behind here, not ahead. *Superseded 2026-10-17: a rich window writes `.docx` through QUILL's writer; see Word documents and table navigation.*

# QUILL Lite — Product Requirements

**Version 1.0.0 · released 2026-09-25 · Windows · MIT · part of the QuillVille family**

## 1. Statement

QUILL Lite is QUILL with everything removed except the editor. One document per
window, plain text or rich text, and nothing else.

It exists for one person: someone who wants Notepad or WordPad with QUILL's
accessibility, and who finds the full writing environment more than they need.
That is not a small group. QUILL for All is a writing environment — AI,
dictation, conversion, comparison, publishing, braille tooling, extensions — and
for a great deal of what people actually do with a text editor, all of that is
in the way. Opening a `.txt` file to change one line should not start a product
with a setup wizard.

QUILL Lite is **not a replacement for QUILL** and **not a place new features go**.
Anyone who wants any of the list above wants QUILL. This is stated here, in the
requirements, because the pressure will be to add things: it is built so that it
cannot grow into QUILL without somebody deliberately deciding to abandon the
product it is.

### Provenance

QUILL Lite began as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`), offered under this repository's MIT licence.
That PR also isolated a real bug in QUILL's own Rich Edit surface — see §7 — and
deliberately did not fix it, so that adding an app and changing the editor stayed
separate decisions. Both decisions were taken; the fix ships with this release
and reaches every QUILL user, not only QUILL Lite's.

## 2. Architecture

Native Preferences search uses the shared `preferences_search` navigator,
installed by the dialog contract. It indexes labels, accessible names, and help
text, never field values; results focus existing controls without accepting the
dialog or mutating settings. Control+F returns to search, Enter navigates, and
Escape clears a query before closing. Disabled controls retain their state.

Activation repair is bounded to an event-loop check and one 75 ms settling
check. Every activation/deactivation changes a generation, so old callbacks
cannot affect a new activation. Repair acts only on shell/MDI containers or
missing focus, never another interactive control. Inactive or hidden shells,
hidden documents, menus, and shutdown suppress repair. It makes no app speech
announcement; native focus changes remain the screen reader's responsibility.

Settings writes return success or failure through
`LiteSettingsPersistenceMixin`. Failed writes keep session values active and
set `settings_dirty`; a coalesced, user-safe warning is spoken and remains in
the status message until a later write succeeds. Preferences never claims a
failed write was saved. Reopening Preferences retries already accepted settings;
new edits still require OK. Existing settings changes and session-close saves
also retry without a loop. Shutdown flushes a pending warning before teardown.
Logs contain only the stable `QUILL-LITE-SETTINGS-WRITE` diagnostic and storage
category, not raw exception text or user paths.

Document Open and Save As dialogs use the configured default document folder
when no saved document location applies. A blank setting resolves to the
Windows Documents folder; a document already saved continues to use its own
folder.

Application shutdown owns the inbox timer through
`QuillLiteApp.stop_background_sources()`. Confirmed Exit and shell close stop
polling before document destruction; `OnExit` repeats that cleanup safely.
Cancelling a close keeps polling active. A queued inbox tick must not consume
requests after shutdown starts, and requests left after a reentrant close are
reposted for the next launch. A deferred launch-update check must not start
after shutdown. Document timers remain each document's responsibility.

**QUILL Lite is not a fork.** That is the single most important architectural
statement in this document, and it is the difference between a sibling and a
copy that rots.

| Layer | Where | What |
|---|---|---|
| The app | `quill/apps/lite*.py` | The shell, the windows, their menus, commands, status bar and dialogs |
| Its own domain logic | `quill/core/lite/` | Settings, paths, recovery, the command table, file encoding, backups, the inbox, the feature areas |
| Logic QUILL should also have | `quill/core/numbered_bookmarks.py` | Nine slots that move with the text -- shared, not QUILL Lite's; see 2.2 |
| Its F1 catalogue | `quill/core/lite_surface_help.py` | What every window is *for* |
| The editor surface | `quill/ui/richedit_editing.py` over `quill/ui/richedit_rtf_surface.py` | QUILL's own control, extended — not copied |
| The product shell | `standalone/quilllite/` | Entry point, icon, installers, docs |

Everything under `quill/` is therefore covered by the repository's existing
gates — module-size budget, access-key uniqueness, the over-announce gate, the
dialog registry, the F1 audit — which is the reason the app code lives there
rather than in the product folder. A surface that no gate can see is a surface
that silently rots; QUILL Cast shipped an unreachable first-run dialog for two
releases exactly that way.

### 2.1 What QUILL Lite reuses rather than reimplements

Each of these is a QUILL finding that cost real on-device testing to establish.
QUILL Lite gets them by *using* QUILL's code, not by copying its conclusions:

- **The native `RICHEDIT50W` control** (a `wx.TextCtrl` with `TE_RICH2`). QUILL
  keeps it because its `IAccessible` value is reported correctly to NVDA and
  JAWS where a classic EDIT control's is not.
- **RTF through the Text Object Model, never `EM_STREAMIN`.** A `ctypes`
  `EDITSTREAM` callback hard-crashes msftedit — the control access-violates the
  instant it calls back into Python. The TOM path never calls back into Python.
- **`scan_rtf_safety` before a byte reaches the control.** RTF can embed OLE
  objects, executables, binary blobs and fields that fetch remote resources.
  QUILL Lite runs the identical scanner QUILL runs, from `quill/io/rtf_safety.py`.
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
  shipping an accessibility provider of its own. QUILL Lite therefore says
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
  and is never binding: **Alt+Shift+F** rings through all four kinds of
  document, **Ctrl+Alt+F6** goes straight to one, and the status bar's Format
  cell names whichever you are in. (The ring was Ctrl+Shift+M until the family
  pass gave that chord to Set Mark, under rule 3: frequency breaks the tie, and
  a mark is dropped mid-sentence where a mode is switched once per document.)
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
- **The line and case tools** — `format_ops` and `transforms`. QUILL Lite has no
  second implementation of "sort these lines"; a first draft did, and it was
  deleted, because two implementations is two places for them to start
  disagreeing about what a trailing newline means.
- **The clipboard stores** — `copy_tray`, `clip_library`, `clipboard_collector`.
- **Abbreviations** — the engine, the store, and the manager dialog.
- **Typing assists** (2026-10-16) — AutoCorrect for misspellings
  (`quill/core/autocorrect.py`, its built-in list and the AutoCorrect Entries
  window, `quill/ui/autocorrect_entries_dialog.py`) and Enter in a list
  (`quill/core/list_continuation.py`). QUILL had list continuation and QUILL
  Lite did not; both have AutoCorrect, on the same settings
  (`autocorrect_misspellings`, `continue_lists_in_plain_text`, both off by
  default) and the same key (Alt+Shift+9).
- **The command palette**, the **feature-areas dialog**, **char_describe**,
  **selection**, **print pagination**, and the **announcement path**.

### 2.2 QUILL Lite is never allowed to be ahead of QUILL

This is a rule, not an aspiration, and it has already cost work twice.

If QUILL Lite needs something the editor cannot do, the capability goes into the
**shared** package and the editor gets a way to reach it in the same release. A
feature the small product has and the big one does not is exactly backwards --
and worse, it is invisible: nobody opens QUILL and notices the absence of a
thing they have only ever seen elsewhere.

In this release that meant:

- `create_richedit_rtf` now builds `RichEditDocument`, so every QUILL tab has
  the paragraph and view capabilities QUILL Lite needed, by construction rather
  than through a second factory;
- QUILL gained **Justify**, **line spacing**, **Grow/Shrink Font**, **Paste Text
  Only** and **rich-mode bullets** -- five commands whose capability had always
  been in the surface with nothing bound to it;
- numbered bookmarks live in `quill/core/numbered_bookmarks.py`, not under
  `lite/`, so QUILL's editor can adopt them;
- a first draft of QUILL Lite's own line and case tools was deleted and replaced
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
  files exactly as QUILL Lite does;
- `load_combined_dictionary`, `load_scope_dictionary` and `add_word_to_scope`
  gained an optional `personal_dir`, so a sibling app can keep taught words in
  its own folder. QUILL passes nothing and behaves precisely as before -- the
  extension point exists because QUILL Lite needed it, and it lives in QUILL's
  module rather than in a copy of it.

Where the two must differ, they differ **on purpose and in writing**, and the
reason is a comment in `keymap.py` rather than folklore.

That principle stands; the example it used to give does not. This paragraph
recorded `Ctrl+Alt+J` and `Ctrl+Alt+V` as deliberate divergences from WordPad's
`Ctrl+J` and `Ctrl+Shift+V`, on the grounds that an existing binding somebody's
hands already know outranks a new command's convention. The family keymap
reversed both (bad.md §3, rule 1: Microsoft's key wins where Word, WordPad or
Notepad bind one for a function both editors have). Keeping the paragraph would
have left the PRD describing a divergence the products no longer have -- which
is worse than describing none, because somebody reads it and writes code to
match.

The divergences that remain are listed in the family keymap's exception table
and each carries its own reason. **QUILL Lite may never be ahead of QUILL**
remains the rule (`CLAUDE.md`); value crosses both ways, violations cross one.

### 2.3 What QUILL Lite adds to the shared package

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
| Theme, following the system by default | See §4.4 |
| Nine numbered bookmarks that move with the text | No scrollbar to remember the position of |
| Structural selection (word, line, paragraph, expand) | Shift+arrow is the wrong tool for a paragraph |
| Describe Character | A reader says "space" for four different characters |
| A twelve-slot copy tray, a collector and a clip library | The system clipboard holds one thing |
| Abbreviations, over QUILL Lite's own library | Expansion is an accessibility feature, not a typing one |
| AutoCorrect for common misspellings, with your own entries in that same library | A misspelling found by ear costs a read-back; one fixed as it is typed costs nothing |
| Enter continues a Markdown list (and, if asked, a plain-text one) | A marker typed by hand is a marker that can be forgotten, and the reader never says one was |
| Sort, de-duplicate, trim, and three case conversions | Work, not writing — and expensive by keyboard |
| Printing and Page Setup | Every text editor Windows has ever shipped has Ctrl+P |
| The Command Palette | Answers "how do I sort lines?", which is the real question |
| Switchable feature areas | See §3.3 |

### 3.2 What it drops, and why

Tabs, dictation, self-voicing, preview, Quillins, remote files, GitHub, braille
tooling, the setup wizard, comparison, publishing, and every companion app.

**The command palette is not on that list any more**, and was listed here in
error: §3.1 and the command table have always had it, and it ships. A document
that says a shipped feature was dropped is worse than one that says nothing,
because somebody reads it and does not go looking for the key.

**AI came off the list on 2026-09-23**, and the distinction matters because the
list is not meaningless now. What arrived is **five commands behind one pad** on
QUILL's own free hosted service, under two gates (§5.6). What is still dropped
is everything else QUILL's AI is: bring-your-own-key, the provider list and the
default cascade, local models, the agent harness, the conversation, alt text,
and the setup wizard that configures them. The reason for the exception is the
reason the product exists: summarizing and explaining a passage is
disproportionately valuable to somebody who cannot skim, and an editor that is
only usable by somebody who reads a screen quickly is not much of an accessible
editor.

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

**Switchable feature areas.** QUILL Lite stays small by being *switchable*, not
by being poor. `Tools > Customize Features` turns whole areas off, and switching
one off removes its menu **and** its keys -- a key that still fires for a feature
somebody turned off is the feature not being off. Somebody who wants Notepad
unchecks rich text, and the Format menu is gone entirely.

Four areas ship **switched off** and are found in that same checklist rather
than hidden, because a feature nobody can find is a feature that does not exist:
autocorrect (welcome in prose, actively wrong in a config file; since
2026-10-16 it holds three rules, curly quotes, em dashes and misspelling
correction, each its own Preferences checkbox, all off), timestamped
backups (reassuring, and they fill a folder), Go To Anything (the palette, the
headings list and the bookmark list each already answer their own part), and AI
help, which is off because it sends what you ask about off this computer -- a
different kind of reason, and the one that needs a second question as well as a
switch (§5.6).

**Nineteen areas now.** *Markdown and HTML* arrived on 2026-09-15 with the rule
that decides what Ctrl+B writes in a `.md`, and *AI help* on 2026-09-23. Both
are areas rather than bare settings for the same reason the rest are: switching
one off has to take its menu rows and its keys with it, and a setting cannot do
that.

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

Nineteen checkboxes is the right way to change one thing and the wrong way to
say "give me the small one". :data:`quill.core.lite.features.PROFILES` is four
named starting points -- **Recommended**, **Everything**, **WordPad**,
**Notepad** -- and the design rules behind them are worth stating, because each
one has a cheaper wrong version.

**A profile is a baseline, not a mode.** Applying one checks and unchecks every
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
| Recommended | 17 of 21 | unchanged | the shipped answer, and the way back from experimenting |
| Everything | 21 of 21 | unchanged | turning things off as they annoy you rather than finding them one at a time |
| WordPad | 5 of 21 | **rich** | letters and notes that should look like something |
| Notepad | 2 of 21 | **plain** | config files, logs, and anything where hidden formatting would be a problem |

The four Recommended leaves off are autocorrect, timestamped backups, Go To
Anything and **AI help** -- and the last of those is off for a different kind of
reason from the other three. Those would be *wrong* on; this one is off because
using it sends the passage you ask about over the internet, which is not a
choice a default gets to make on somebody's behalf. See §5.6: the area switch
and the agreement are two separate questions, and Everything can turn the first
on without ever answering the second.

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
- ~~**Not keymap-customisable.**~~ **Reversed 2026-09-10.** This said QUILL Lite
  had one fixed table and that was that. The table is still the *defaults* --
  it is what the uniqueness gates assert against -- but
  `quill/core/lite/keymap.py` puts a resolution layer over it and
  `Tools > Keyboard Manager` (Ctrl+Alt+Shift+Space) edits it. What stays true is the
  reason the non-goal was written: QUILL's chord grammar, its `APP_KEYMAPS`
  overrides and its Key Describer are a writing environment's features and are
  still not here. Rebinding a key is not.
- **Not a second clipboard manager.** The tray, the collector and the library
  are QUILL's own stores, kept in QUILL Lite's folder. Nothing is reimplemented.

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

QUILL Lite adds a stricter check of its own
(`tests/unit/tools/test_lite_control_help.py`), because the shared scanner has
two blind spots that matter here: it does not treat `wx.CheckBox` as helpable
(and the Find and Replace windows are half checkboxes), and it cannot see a
control built by a factory in another module — which is *the document itself*,
the control a listener is in for all but a few seconds of a session.

### 4.3 The status bar is navigable, not decorative

QUILL's status bar is a row of focusable cells rather than painted text, and
QUILL Lite's is the same: **F6** lands in it, arrows and Home/End move between
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
and selection changes. QUILL Lite announces only outcomes it alone knows: "Bold
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

### 4.5 Speech, and not braille

QUILL Lite announces through a running screen reader and nowhere else.
`ScreenReaderVoice` reaches NVDA and JAWS through Prism or accessible_output2
and Narrator through a UIA notification, and hands nothing to the engine unless
a reader is actually running. There is **no self-voicing fallback** and there is
**no braille output**: nothing in the QUILL Lite tree routes an announcement to a
braille display, where QUILL has a braille service that does.

This is a decision, recorded so it stops reading as an oversight.

**Why.** A braille route is not a line of code; it is a delivery channel with
its own verbosity rules, its own truncation problems, and its own way of being
wrong -- QUILL's braille surface is several modules and a settings group. The
editor this PRD describes is meant to stay small enough to be read in an
afternoon, and adding a second output channel is the kind of thing that makes a
Notepad-scale product stop being one.

**What a deafblind user gets instead, and why it is not nothing.** Every
message QUILL Lite speaks also lands in the status bar's message cell (4.3), and
the status bar is a row of real focusable buttons rather than a painted strip.
A braille display reaches it by cursor routing like any other control, and F6
puts the caret there in one keystroke. So the information is available; it is
pull rather than push. What is genuinely lost is the *unprompted* announcement
-- a background result a listener would have heard, a deafblind user has to go
and look for.

**What would have to change.** The announcement path is one seam
(`ScreenReaderVoice.speak`), so the work is not in QUILL Lite: it is deciding
whether QUILL's braille service can be lifted into the shared package without
bringing its settings group with it. If it can, QUILL Lite gets braille for the
cost of one call. Until somebody has answered that question, this section is
the honest description of where the product stands.

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

The interval is a setting (`autosave_seconds`, 15–600 seconds, **default 30**),
reachable only from Preferences -- **Copy unsaved work aside every (seconds)**.
It has no key and no menu row, deliberately: it is a number somebody sets once.

### 5.3 Its own data folder

Settings, recent files and recovered work live in `%LOCALAPPDATA%\QuillLite`,
deliberately **not** in `%APPDATA%\Quill`. QUILL Lite is offered as an
alternative to QUILL rather than as a client of it: a Notepad-scale editor that
silently adopted a writing environment's settings would be making a decision
nobody asked it to make, and uninstalling it could then cost somebody something
QUILL owns. A machine that has never had QUILL installed must not grow a Quill
folder because somebody opened a text file.

This is why QUILL Lite does not use `quill.core.ipc` for its single-instance
guard — that lock lives in QUILL's data directory. It uses
`wx.SingleInstanceChecker` (a kernel object, with no file to go stale) plus its
own inbox directory. Uninstalling never removes the data folder either: recovery
slots are the one thing somebody may not have finished with, and an uninstaller
is the worst possible moment to discover that.

**The one bridge, and why it does not contradict any of that (2026-09-18).**
QUILL Lite has always been able to *read* QUILL's abbreviations and personal
dictionary, behind a switch the person turns on. QUILL now has the other half:
`quill/core/lite_bridge.py` and **Tools > Customize and Support > Bring My
QUILL Lite Settings...** (`Alt+Shift+F11`) merge QUILL Lite's copies of five
content stores into QUILL's folder, copy the settings and rebound keys that
translate, and turn those sharing switches on so the two editors stop keeping
separate copies. Five properties keep this inside the principle above rather
than against it:

* **Nothing moves without an explicit ask.** The command is a menu item and a
  key. The one place it is offered rather than invoked -- activating the
  QUILL Lite feature profile in QUILL -- asks a Yes/No question, once ever, and a
  No is remembered.
* **The plan is described before it is applied**, counts first and what is being
  *left behind* last, because "it copied your settings" is not something a
  listener can verify afterwards by looking at the screen.
* **QUILL wins every collision** and nothing already in QUILL is replaced.
  `merge_json_store` is shape-agnostic on purpose -- these five files are a dict,
  a list, or a dict with a list in it, and five mergers would be five schemas to
  keep in step -- and it writes nothing at all when the two sides are different
  shapes. A merge that cannot be done safely is not done: these files are the
  user's work.
* **QUILL Lite's own settings file is written once, for two booleans.** That is
  the only thing this module writes into `%LOCALAPPDATA%\QuillLite`, and it is
  the half without which a "shared" store looks broken -- QUILL holding the words
  while QUILL Lite still reads its own copy.
* **The direction is QUILL Lite -> QUILL.** A machine that has never had QUILL
  still grows no Quill folder, because the command lives in QUILL and cannot run
  where QUILL is not installed.

Both write sites are classified in `quill/tools/persistence_audit.py`
(`merge_json_store` as content, `enable_lite_sharing` as marker), so neither can
be added to or moved without somebody re-stating what they do.

### 5.3a Two instances, one settings file (F-11, 2026-10-01)

`--new-instance` runs two processes against one settings file. Each used to
write its whole in-memory copy, so the last to save undid every preference the
other had changed -- atomic writes stop a half-written file, not a valid older
snapshot replacing a valid newer one. A save is now a three-way merge
(`quill/core/lite/settings_merge.py`): the app keeps the settings it loaded or
last wrote as a baseline; at save it re-reads the file, writes its own value
for every field it changed since the baseline, and keeps the file's value for
every other field. Last writer wins per field, not per file. The running
instance's in-memory settings are never replaced by the other's -- a silent
change to theme, font or speech mid-session is the thing this product must not
do -- so the other's choices apply at its next launch. An unreadable file is
not merged against (that would reset untouched fields to defaults); the save
falls back to the whole-object write.

### 5.3b When a focus repair does not take (F-04, 2026-10-01)

The activation repair (one check after the event loop, one 75 ms later) can
still be overruled -- Windows restoring focus after the second check, or a
control that refuses it. That is the residue a listener reports as "sometimes
it works", so `lite_shell._note_repair_miss` counts it per shell
(`focus_repair_misses`) and logs `QUILL-LITE-FOCUS-MISS` with the class of
whatever holds focus and the session count -- never a title, a label or a word
of a document, because the log travels in support bundles. Nothing is
announced. It is not a family helper yet: QUILL's own repair (#170) is a
different mechanism, and a shared helper with one caller is speculation; it is
extracted when a second app adopts this shape.

### 5.3c Opening is prepare, then commit (F-05, 2026-10-01)

`DocumentFrame.load` read, decoded and RTF-scanned on the UI thread, so a
large file, a slow share, a scanner holding the read or a damaged RTF froze
the window with nothing said. Opening is now two halves:
`quill/core/lite/open_prepare.prepare` (wx-free, any thread: read, decode or
scan, return an immutable `PreparedDocument`) and
`DocumentFileMixin._commit_load` (UI thread only: the Rich Edit control and
everything a load implies). `load()` still runs both synchronously, so every
existing caller is unchanged. `open_prepare.prepare_in_background` routes a
file of 1 MiB or more, or a UNC path, through
`lite_window_open.DocumentBackgroundOpenMixin.begin_background_load`: a new
window, read-only while empty-and-loading, "Opening <name>" announced once
and on the status bar, the read on the app's lazily created two-worker
`TaskManager`, the commit on the UI thread only when the open generation still
matches, the window's `UiLifetimeToken` is alive and the app is not shutting
down. Closing the window is Cancel. Failure asks Try Again; declining closes a
window that holds nothing else. A file still opening counts for the
already-open check, so a second request focuses it instead of reading it twice.
The app's shutdown owner stops the pool. Not done: Open as Plain Text on
failure (a rich file that fails the scan still reports through the box).

### 5.4 File associations

The full installer offers "Open .txt and .rtf files with QUILL Lite" as an
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

QUILL Lite had neither half of that. It shipped with **no reporting item at
all**, only an address printed in the About box to copy out by hand.

The form is the same one every app in the family opens
(`quill/ui/support_dialog.py` over `quill/core/support_message.py`): what kind
of message this is, a subject, and what happened. What you expected and how to
reproduce it are optional. **Your email address is optional too** — a problem
can be reported without giving one, and because the message goes from the
reader's own mail account, support can still reply to that (corrected
2026-09-26; this used to say nobody could answer). Send opens
**your own mail program with the message already written**, with QUILL Lite's
name and version, your Windows version and your screen reader appended. Nothing
leaves the machine until you send it there, and the app says so out loud rather
than claiming to have sent something it has not. A machine with no mail program
set up — webmail only — gets the whole message and the address on the
clipboard, so nothing typed is ever lost.

Writing to `support@community-access.org` directly works exactly as well. There
is no form anybody is required to use.

**No GitHub credential, anywhere (2026-09-26).** Every piece of feedback from
QUILL Lite and Quill Radio goes to `support@community-access.org`; nothing is
filed as a GitHub issue. So the build no longer generates or embeds the bundled
"feedback token" (`scripts/build_release.ps1` lost `-TokenFile`/`-SkipToken`,
and a public build no longer fails without one), and the support form no
longer tries the feedback-hub dialog first: email is its only route. The mail handoff is `support_dialog.send_by_mail`, shared with
Quill Radio's Suggest a Station or Podcast so both cut, copy and fall back
identically.

### 5.6 AI help: two gates, not one

QUILL Lite carries five AI commands -- summarize, rewrite, proofread, explain, and
ask a question about the open document -- on QUILL's own hosted service. They are
the *only* part of this product that sends anything off the machine, which is why
they sit in this section rather than in Scope.

**Two independent gates, both of which must be true before a byte leaves.** The
feature area answers *does this exist in my copy*; the agreement answers *have I
agreed to what it does*. Collapsing them into one switch gets the second one
wrong, because an area can be switched on by a profile, by a settings import, or
by another person using the machine, and none of those is consent.

The agreement is therefore:

- **Asked for on its own**, never as a side effect of enabling something.
- **Stored as a version, not a boolean.** A material change to what is sent or
  retained asks again, rather than an old yes being read as covering a new thing.
- **Reachable by three doors** -- `Tools > AI > Privacy Agreement`
  (`Ctrl+Alt+Shift+K`), a Preferences check box, and switching the area on in
  Customize Features -- because which door somebody finds depends on which part
  of the app they already know. All three read and write the same value, so they
  cannot disagree.
- **Never dimmed.** The Privacy Agreement row opens whether or not the area is
  enabled and whether or not the agreement has been accepted. A door reachable
  only by first agreeing to something is not a door, and withdrawal has to be as
  easy as acceptance.

**Withdrawal signs the machine out.** Keeping a sign-in for a service just
declined would leave the key in a door the user has closed. Signing out, by
contrast, does *not* withdraw the agreement: it is a smaller action and must not
silently perform a larger one.

**Shape: one pad behind one key, not five keyed commands.** Measured across
Ctrl+Alt, Ctrl+Shift, Alt+Shift and Ctrl+Alt+Shift, the chords free in *both*
editors are few, and family rule 2 requires a command both products have to keep
its chord -- so five separate keyed commands were never available. The single pad
is the better shape regardless: one surface showing what is about to be sent, one
showing what remains, one consent surface.

**Family rule 10 holds.** The capability is shared rather than QUILL Lite's own,
so QUILL runs the same five commands on the same five chords from the same
module. QUILL Lite is not ahead of QUILL here; QUILL has more AI, not less, and
none of its existing provider list, default cascade, bring-your-own-key, agent or
local-model paths changed to make room for this.

### 5.6a Conversations: memory without a multiplier (1.1)

A conversation was the one AI shape deliberately left out of the free tier,
because it resends its history on every turn and so each reply costs more than
the last. It ships in 1.1 on the condition that removes the multiplier: **the
conversation so far is trimmed to the same input ceiling every request has**,
newest turns first, on this computer (`quill/core/ai/hosted_chat.py`) and again,
authoritatively, on the service. A turn is one request and never costs more than
any other; conversations have a monthly share of their own (`feature_cap.chat`,
40 of 100). What a long conversation loses is memory of its opening, and the
window says so aloud the first time that happens rather than leaving somebody to
infer it from a puzzling answer.

**No new command, no new chord.** Chords free in both editors are the scarcest
resource in the family (section 5.6), so a conversation is reached from the pad
(**Have a conversation**, a seventh choice) and from the result window (**Follow
Up**, which seeds the conversation with that question and answer, and keeps a
document question's excerpts attached). The window is modeless; focus lives in
the message box and each reply is announced, because it lands in a transcript
that does not have focus -- the one case GATE-13 says the app must speak.

**With the user's own API key (OpenAI or Google Gemini) there is no trimming**: the whole conversation
goes, and is shortened only past what the model can read at once.

**Family rule 10 holds**: the window, the pad row and Follow Up live in the
shared `quill/ui/hosted_ai_*` modules, so QUILL has them in the same release on
the same keys.

### 5.6b Ten writing tools (1.1)

The pad grows from seven choices to seventeen: Shorten, Simplify, Make more
formal, Make friendlier, Turn into a list, Find action items, Suggest headings,
Continue writing, Write an email reply, and Translate. The rule for admitting a
tool is the same one that admitted Summarize: **one passage in, one result out,
at the ordinary size**, so no tool is a new worst case for the free service
(each is one request, with a monthly share of 60). Each is a fixed template on
the service; the client sends only the passage, and Translate's target language
is the one value it fills in, from a fixed list of twenty checked on both ends,
because a free-text field there would be a place to smuggle instructions.

The choice of tools is aimed at the people this product is for: **Simplify**
for letters from banks, hospitals and lawyers; **Turn into a list** and **Find
action items** because a list is far quicker to review by ear than a
paragraph; **Suggest headings** because headings are what a screen reader
navigates by, so it turns a flat passage into one you can move through. The
list of seventeen is a list box, so a first letter jumps to a tool.

**New tools without a release (2026-10).** The service's `GET /v1/config` now
carries a feature catalogue: each shipped tool's id, label, one-sentence help
and input kind (`selection`, `prompt` or `document`). Any entry this build does
not have built in becomes a row at the end of the pad's list, after Have a
conversation: its help is the row's F1 text and Send runs it through the same
path as the built-in rows. Requirements: every field is validated as remote
input (id shape, plain text with control characters removed, length caps, at
most 40 entries); an unknown input kind is skipped, never guessed; an entry
duplicating a built-in id or label is dropped; rows arriving while the pad is
open are appended at the end and not announced (GATE-13); a per-tool input
ceiling may only lower the pad's pre-check; the answer opens in the ordinary
AI Result window. Only on the free service, since the tool's instructions live
there. Shared code (`quill/core/ai/gateway_catalogue.py`,
`quill/ui/hosted_ai_pad_catalogue.py`), so QUILL has it in the same release
(family rule 10).

**QUILL's saved conversations, Prompt Library and word-level review
(2026-10-15).** Brought from QUILL through shared code, never copied, with QUILL
moved onto the extracted pieces in the same change. Requirements: every AI
conversation is saved as it goes in QUILL's session format
(`quill/core/ai/sessions.py`, `record_exchange`) in QUILL Lite's own
`ai-sessions` folder, and **Saved Conversations** (Alt+V in the conversation
window) opens one to continue or deletes one after asking; **Prompt Library**
(Ctrl+7) is QUILL's `PromptLibraryDialog` over QUILL's library format
(`prompts.json`, `.pqp` packs) in QUILL Lite's data folder, and Run fills the
prompt, closes, and sends it as a general question, refusing before sending if
it is over the input ceiling; **Review Changes** in the result window opens
QUILL's Review AI Changes (`quill/ui/ai_diff_review_dialog.py`), offered only
when Replace is and the answer differs, and applies only accepted changes as one
undo step. Every control in the three windows has F1 help.

**Answer delivery and the Chat Key (2026-10-15).** No spec existed, so the
minimum: the pad's **Put the answer in** list chooses the AI Result window
(default), the document at the caret (one undo step, read aloud), or the
clipboard (read aloud; falls back to the window if the clipboard is busy), kept
as `ai_answer_delivery` (QUILL's field name too) and applied to every answer.
**Ask AI a Question** (Ctrl+6), the Chat Key, opens the pad on Ask a General
Question with the caret in the question box.

**Web search on the free AI (2026-10-15).** The service's `web_search` feature
ships off behind a feature flag, ten searches per account per month; while on,
the catalogue offers **Search the web** in the pad. **Web Searches Left**
(Ctrl+9) reads `/v1/config`'s `web_search` entry and `/v1/quota`'s count and
says how many are left, or that search is not offered; on an own key or plan it
says search is the free service's. QUILL has the same three commands on the same
three chords (rule 2).

### 5.6c Your own API key: a provider chosen, never inferred (1.2, qc.md X-07)

**Use My Own API Key** (`Alt+F2`, formerly Use My Own OpenAI Key) sends AI help
straight to the provider the person chooses -- **OpenAI or Google Gemini** --
on their own key, with no QUILL server and no allowance. The requirement that
shaped it came from reviewing PR #1615, which made Gemini keys work by inferring
the provider from a model name and falling back to whichever key was stored.
That half was not taken. The requirements instead:

- **The provider is an explicit choice**, the first control in the window, and
  the persisted setting `ai_own_key_provider` (`"openai"` or `"gemini"`) is the
  only thing that decides where a request goes. Nothing is inferred from a key's
  shape or a model's name (`quill/core/ai/own_key.py`, `chosen_provider`).
- **No fallback between providers.** With Gemini chosen and only an OpenAI key
  saved, the route is not active and AI help is on the free service; OK says so
  and names the unused key. A request made anyway is refused with a sentence
  before anything is sent.
- **Earlier consent is kept.** An empty `ai_own_key_provider` means OpenAI, the
  only provider there was when 1.1 keys were saved. An unknown value means *no*
  provider, never a guess.
- **One key per provider, in the existing secure store**: the AI Hub's
  per-provider credential targets (Windows Credential Manager, or the encrypted
  file in a portable copy), shared with QUILL; never plaintext, never shown
  again. A typed key is cleared, and the clearing announced, when the provider
  choice moves, so a key cannot be saved under the wrong company.
- **Gemini requests stream** from `streamGenerateContent?alt=sse` on
  `generativelanguage.googleapis.com`, HTTPS only, the key in `x-goog-api-key`,
  the gateway's instructions in `systemInstruction`
  (`quill/core/ai/own_key_gemini.py`, built from the shared pure builders in
  `quill/core/ai/endpoints.py` and `assistant_ai.build_chat_body`). OpenAI
  requests are unchanged and not streamed, because OpenAI refuses streaming
  from unverified organisations for some models.
- **Stop works.** The pad's Send button is Stop while a request is on its way;
  `AiService.cancel(request)` sets only that request's event, so stopping one
  window cannot cancel work started by another. On Gemini the stream is closed
  before the next piece is read; on every other route the outcome is dropped on
  arrival. Neither an answer nor a failure is delivered after Stop.
- **Errors are one sentence, spoken, actionable, and never contain the key.**
  Gemini answers a wrong key with HTTP 400 `API_KEY_INVALID`, not 401, so the
  key-rejected case is read from the body; 401 and 403 are rejections too
  (`QUILL-AI-OWN-KEY-REJECTED`). 404, 429 and 5xx each have their own sentence
  (`QUILL-AI-OWN-KEY-FAILED`), a busy Gemini is tried once more, and every
  sentence passes through `own_key.scrub`.
- **Model ordering is deterministic** (`quill/core/ai/own_key_models.py`):
  Gemini's list is filtered (embeddings, Imagen, Veo, speech, live audio, image
  generation, AQA) and ordered stable before preview, newest version first,
  Flash, Flash-Lite, Pro, then by name; OpenAI's order is unchanged. Cost
  estimates are per provider, and Gemini's note says what Google's free tier
  means for privacy.
- **Shared, so QUILL has it the same day** (family rule 10): the window
  (`quill/ui/hosted_ai_own_key.py`), the service (`quill/ui/hosted_ai_service.py`,
  with its route sentences split into `quill/ui/hosted_ai_route_words.py` under
  GATE-11) and the pad are the shared `hosted_ai_*` modules both editors use.
- One new egress site, `own_key_gemini._open_stream`, reviewed in the egress
  audit. Tests: `tests/unit/core/ai/test_own_key_gemini_route.py` runs the
  shipped code against a loopback server shaped like both providers, with
  synthetic keys.

### 5.7 Every switch has a way back, from inside the app

A preference somebody can turn off and cannot turn back on is not a preference;
it is a trapdoor. The rule is that the surface that sets a value is a surface
that can also unset it, and that the way back is reachable **without editing a
file** -- because the population this product is written for is exactly the one
that cannot be told "open the JSON in your profile folder".

The one place this was broken until 2026-09-24 is worth recording, because it is
the shape the rule exists to catch. The Reopen Last Session window's **Never Ask
Again** wrote `session_restore_ask = "never"`. Nothing else in either editor ever
wrote that key: not Preferences, not the window itself on any later visit. The
window then stopped appearing at launch, and although `File > Reopen Last
Session...` still *opened* it, there was no control in it that could undo the
setting. The button's help text made it worse by naming a real setting that is
not this one -- "Reopen last session" is `restore_session`, whether to reopen at
all -- so following the instruction produced a different effect and no clue.

**Ask Me Next Time** is its twin. Exactly one of the pair is enabled, decided by
the mode the caller passes in, and the disabled one is **greyed rather than
hidden**: a removed control leaves somebody hunting the window for it, where a
disabled one announces itself as unavailable the moment a reader arrives on it.
The same choice the two tag pickers make, for the same reason.

Not a Preferences row, deliberately. The window that asks the question is where
somebody looks to answer it, and adding a row to QUILL Lite's Preferences that
QUILL's Settings does not have would put the small product ahead of the large
one (§2.2) over a control that belongs in the shared window anyway. Both editors
gained it in the same change, which is what rule 10 requires.

### 5.8 Dictation: the reliability pass, and words taught in a window (2026-09-28)

Nine sections of the dictation plan (`dict.md` 2.2, 2.3, 2.5, 2.6, 2.7, 2.8,
3.1, 3.3 and 5; that plan is now `docs/design/2026-10-05-dictation-plan-and-status.md`,
whose Appendix A maps its section numbers), implemented in the shared Live Dictation stack so QUILL has
every one of them on the same keys (rule 10). The design constraint from that
plan holds throughout: nothing here costs the baseline machine anything while
dictation is idle, and the watchdog's only running cost is one comparison per
audio block.

**Requirements, and where each lives.**

- **Escape cancels the phrase being heard** (2.2). `controller.cancel_phrase`
  answers only in the *recognising* state, asks the recogniser to `discard()`
  what it has (the local engine drains its queue, resets the voice detector and
  drops any transcription already under way by a generation counter; Windows
  speech purges and re-arms), ignores a phrase the engine finalises afterwards
  until the next utterance starts, and says "Cancelled". Routed by a char hook
  on the document window, so it runs before the control sees the key and
  consumes it only when there was something to cancel
  (`core/windows_dictation/resilience.py`, `ui/windows_dictation_tools.py`).
- **The microphone watchdog** (2.3). The local recogniser's worker declares the
  device lost after two seconds with no audio blocks or three seconds of exact
  zeros (a quiet room never produces exact zeros), closes the stream, and tries
  to reopen it every two seconds. The controller gains a *paused* state that is
  still "on" -- the menu mark stays, no phrase is written, the status cell says
  "paused, microphone lost" -- and resumes on the device's return, both said in
  the plan's words (`local_recognizer.py`, `resilience.py`).
- **One Ctrl+Z per phrase** (2.5). The document port writes every phrase
  through `replace_as_one_undo`, the path the AI inserts and paste already
  used; remove-then-write over a selection had been two steps.
- **Read-only refusal** (2.6), before the microphone opens, in the plan's
  wording.
- **The self-healing engine** (2.7), in two layers: a decode that raises is
  retried once on a freshly loaded engine inside the worker; a recogniser that
  fails outright is reopened once, silently, by the controller. The second
  failure names the engine and the one to try instead
  (`resilience.engine_failure_message`). A fresh session earns a fresh restart.
- **One session at a time** (2.8). Ctrl+F11 in another document while dictation
  runs retargets the one controller and says "Dictation moved to <name>".
- **Dictate into any text field** (3.1). `bind_field_dictation` gives Find,
  Replace and the AI pad's question box the toggle chord and the Escape; the
  document port answers `single_line()`, so a paragraph break becomes a space
  and no closing full stop is added.
- **Recent phrases** (3.3). The controller keeps the last twenty phrases of the
  app session, separate from the scratch-that history that a stop clears;
  `RecentPhrasesDialog` offers Insert Again (one undo step) and Copy.
- **Teaching dictation your words** (5, as the plan's option A plus a window
  instead of a file). `words_file.py` models `dictation.md` as words, phrases
  and corrections; the writer regenerates the file in the parser's own shape,
  with a `## Corrections` heading the profile parser already folds into
  replacements, so a correction is applied after recognition on every engine
  with no new runtime code. `DictationWordsDialog` is the window; the Dictation
  Settings button opens it. Found on the way: the starter file's explanatory
  sentences were being parsed as vocabulary, now excluded (`looks_like_prose`).
- **Import, Export and the shared list** (dict.md D-12, 2026-10-15). My Words
  and Phrases exports to Markdown or CSV (`say,write,kind`) and imports either,
  merging only: new entries are added after a preview, entries already there or
  different keep the person's own, and the list is copied to
  `dictation-before-import.md` first (`words_exchange.py`). "Use the shared word
  list" (`share_quill_dictation_words`, off) points QUILL Lite at the family's
  `dictation.md`, the one QUILL, QUILL Transcribe and Quill Inkwell read, after
  merging QUILL Lite's own entries into it; never offered in a portable copy.
  Since 2026-10-16 that file lives in `%LOCALAPPDATA%\QuillVille\Dictation`,
  copied there from QUILL's data folder with the old file kept as the backup
  (dictation design record section 30). "Share dictation settings with the
  family" (`windows_dictation_share_family`, More Dictation Settings, Alt+Q)
  keeps the shared dictation settings in `family_dictation.json` beside it,
  written on OK and taken when the window is activated (dict.md D-13).

**Tests.** The core behaviours against a fake recogniser and a fake document
(`tests/unit/core/test_windows_dictation.py`), the words model round-trip and
its edits (`test_dictation_words_file.py`), and each Lite handler through the
window it runs in (`tests/unit/apps/test_lite_dictation.py`); the command
coverage gate stays at zero `shape_only`.

### 5.9 Dictation: holding the key, live words, the AI, and OpenAI (2026-10-05)

The rest of the dictation plan, after studying VS Code's dictation (credited,
behaviour by behaviour, in `docs/design/2026-10-05-dictation-plan-and-status.md`,
which also holds everything still to do). All of it is shared code, and
`tests/unit/ui/test_dictation_parity.py` fails if QUILL and QUILL Lite differ in
a dictation command, key or setting.

- **Hold-to-talk** (`hold.py`, `windows_dictation_hold.py`): hold Ctrl+F11 for
  half a second and talk, let go to stop; a quick press toggles; key repeats are
  ignored. Off by default (owner, 2026-10-05): one press starts, the next
  stops; **More Dictation Settings** turns it on.
- **Finishing, not cutting off**: stopping while a phrase is being heard waits
  for it (`LiveMixin.finish`, the worker's `finish`), with a four-second limit.
- **The live preview** (`streaming.py`, `recognizer_worker.py`, `live.py`):
  Nemotron runs as a streaming model on one stream per session; its provisional
  words show as "Hearing: ..." in the status cell and on braille, never in the
  document; the mark it writes once it hears the next phrase corrects the last
  one (so its questions end in question marks).
- **Words go where you started** (`EditorDocument.anchor`): measured on speech
  start, honoured even if the caret moved or the focus left.
- **"Correct that"** and "choose one" to "choose three", with Windows speech
  recognition's alternates. Since 2026-10-16 (D-19), with Moonshine, Whisper or
  a downloaded model, the other built-in engine re-decodes the last phrase's
  audio (memory only, dropped at the next phrase) and offers its answer as
  choice 2; OpenAI, the speech companies and Spanish still say there is none.
- **Replace, change that, delete by paragraph, kept revisions** (D-19,
  2026-10-16, `corrections.py`): "replace X with Y" (nearest before the cursor,
  else after), "change that to Y" (the last phrase), "delete previous
  paragraph"; what choose, replace and change that replaced goes into Recent
  Phrases labelled "(before correction)".
- **Talk to the AI** (`hosted_ai_chat._talk_to_it`): the AI Conversation
  window's message box dictates with the **Talking to AI** profile, sends at the
  pause (or on Enter), and mutes the microphone while the reply is read.
- **OpenAI dictation, own key only** (`openai_models.py`, `openai_transcribe.py`,
  `openai_recognizer.py`): off by default, a plain consent, the model chosen
  from OpenAI's live list without retiring models, Realtime transcription for
  `gpt-live-transcribe`, never a silent switch, refused in Safe Mode, three
  reviewed egress entries, and a Dictation section in the privacy statement.
- **My Dictation Instructions** (`instructions.py`) for Tidy Dictated Text.
- **Kind to a modest computer** (`keep_up.py`): the keep-up watchdog and models
  unloaded five minutes after the last session.
- **Settings**: eight new `windows_dictation_*` fields, and all 24 now declared
  once (`settings_fields.DictationSettings`), inherited by both editors'
  `Settings`.

### 5.9a Dictation: correcting yourself, styles, polish and learning (2026-10-16)

The same as QUILL (QUILL PRD, the D-20/D-21 addendum; dictation design record
section 28), through the shared dictation package, so QUILL Lite is never
ahead. **Fix it when I correct myself** (Alt+X, off) keeps the second of
"Thursday, no, Friday" between two days, months, numbers or names in My Words,
locally and conservatively. **Dictation style** (Alt+Y) names Verbatim, Clean
and, only with AI on, Polished, and stores nothing itself. **Allow polishing my
dictation with AI when I ask** (Alt+G in More Dictation Settings, off) lets
"QUILL polish that" and **Polish** (Ctrl+P) in Review Dictation send one fixed
request through the review's own consent and AI routes; it is never automatic.
A second identical voice correction offers to add it to Corrections, in a
Yes/No window with No the default; nothing is stored without a yes.

### 5.10 Transcribing a recording (2026-10-06)

QUILL Lite's **Transcribe a Recording** command (Shift+F5) transcribes supported
audio files in the background using the shared dictation speech engines. Its
window reports recording length and estimated transcription time; on Windows,
duration lookup falls back to Media Foundation when the other metadata readers
cannot determine the length. Several selected recordings run in sequence.

The transcript is saved privately and is not inserted into the document the
user was editing. A completion notice in Notifications opens the saved
transcript when activated; Activity retains the outcome and failure reason.
There is no destination picker.

**Translate into English** (2026-10-16, dict.md D-26): for a recording in a
language other than English, with a model that translates (the built-in
Whisper, or a downloaded multilingual Whisper), the transcript can be written
in English instead. The check box is unavailable otherwise and off unless
checked. QUILL's offline transcription translates on the same models, because
all three apps now run every local model through one shared sherpa-onnx layer.

## 6. Release packaging

**Two** artifacts: the portable build and the system installer. That is the
family contract for every app (2026-10-11), and QUILL Lite reached it first:

| Artifact | Built from | Output | Measured |
|---|---|---|---|
| Installer | `installer/quilllite.iss` | `QuillLite-Setup-Shared-1.0.0.exe` | 117 MB |
| Full portable | `build_portable.py --product quilllite` | `QuillLite-Portable-1.0.0.zip` | 94 MB |

**Why two** (2026-09-15). QUILL Lite used
to ship the thin `QuillLite-Lite-Setup` and the launcher-only
`QuillLite-Companion` zip as well, and both were wrong for this product. The
Companion zip installs nothing, so it binds to whatever shared runtime is
already on the machine -- including one frozen before QUILL Lite existed, which
fails at launch with `No module named quill.apps.lite` and cannot repair itself,
because the launcher's runtime bootstrap only fires when *no* runtime resolves
and a stale one resolves perfectly well. The thin installer traded a 117 MB
download for a 110 MB first-launch download plus a network dependency, on the
one app somebody installs *because* they have nothing else -- so the runtime is
usually absent and the saving is notional. Retiring both is safe for anyone
already on one: the two installers share an AppId, so this one upgrades a thin
install in place, and `core/updates.py` falls through to an installable asset
when a release publishes none for the running edition. On 2026-10-11 the rest
of the family followed: every app now ships only the portable build and the
installer.

The download names spell the product as one mixed-case word, `QuillLite-*`,
never `Quill-Lite-*`: a screen reader speaks `QUILL Lite` as the product's name,
where a hyphenated form is read out punctuation and all.

The installer script is named `quilllite.iss`, not `quill-lite.iss`: the family
used the `*-lite.iss` suffix for the retired *thin* installer flavour, and
`quill-lite.iss` ends in it -- so the installer was being audited as a thin one.
Every other identifier for this product is already `quilllite` (the folder, the
`AppRefId`, the launcher product key), so the installer matches it.

`portable-inventory.json` is committed and enforced: the portable build fails on
any drift from it, which is the class of defect that once put 82 MB of
undeclared payload into a runtime installer.

Both come from `scripts/build_release.ps1`. The shared QuillVille Runtime at
`%LOCALAPPDATA%\QuillVille\Runtime\3.13\` is reused: the installer ships it and
lays it down only when what is already there is older, and the portable bundle
carries its own interpreter and never touches it at all.
**Neither ffmpeg nor libmpv is staged** —
QUILL Lite declares no media components, and the build strips any a sibling app
left in the shared work area, so build order cannot change what ships.

The installer is per-user: `PrivilegesRequired=lowest`, with no elevated
all-users override. App files and the shared runtime are installed for the
signed-in user. The optional runtime setting that replaces Notepad for every
user remains a separate, explicitly elevated action.

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

Before this, QUILL Lite could not tell its user that a newer version existed. It
is the app most likely to be somebody's only Quill product — installed by a
person who wanted Notepad — and therefore the app whose users are least likely
to go looking on GitHub. They would have stayed on 1.0.0 forever with no way to
know that was happening.

**The dialog is shared, and it always shows what changed.** `quill/ui/
update_notice.py` is the one "an update is available" surface for QUILL, the
eight companion apps and QUILL Lite: the release notes flattened out of Markdown,
capped and never empty, with **Update** as the affirmative and default and
**Close** as the escape. Focus lands on the notes rather than on a button, so
the first thing read is the release notes and not the word "Update". QUILL alone
adds **Skip this version**, because QUILL alone has a settings field to remember
the answer in. The download, its spoken 25/50/75 milestones, and the
Install-and-restart dialog are `quill/ui/update_download.py`, shared the same
way — QUILL Lite has no `TaskManager`, so it supplies a one-shot thread instead
and gets the identical experience.

Releases resolve from `RELEASE_REPO` and `RELEASE_ASSET_PREFIX` in
`quill/core/lite/__init__.py`, deliberately **not** from
`companion_install.ASSET_PREFIX`: that table is the set of QuillVille apps QUILL
can offer to *install for you*, and QUILL Lite is a separate product rather than
a sibling QUILL launches.

The silent launch check says nothing in every direction but one: nothing while
it runs, nothing when there is nothing, and nothing when the network is down.
Only a genuine newer version speaks, and even then it only offers — nothing is
downloaded until the user presses Update.

**Two family-wide defects were fixed to make this honest** (2026-09-12), both
older than QUILL Lite and both live in every companion app:

* *The wrong edition was offered.* `updates._app_asset_url` — the path every
  companion app takes — chose between the four assets by file extension alone,
  so of the two `-setup-*.exe` files it took whichever GitHub listed **last**,
  and a Companion listener was handed an `.exe` that cannot install their copy.
  It now asks `install_edition.detect()` first, as QUILL's own `_pick_asset`
  has since August. `matches_asset` gained an `app_prefix`, without which
  QUILL Lite is unresolvable: the product **name** contains "lite", so every one
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

### 6.2 When it cannot start, it says so (2026-09-28)

`QuillLite.exe` is the family's native launcher, and until 2026-09-28 it
spawned `pythonw.exe`, waited, and threw the exit code away. A portable Quill
Radio that "just doesn't return anything" was the report that ended that.
Now the launcher writes the engine's stdout and stderr to a launch log
(`data\logs\launch.log` beside a portable copy,
`%APPDATA%\Quill\logs\QuillLite-launch.log` for an installed one, replaced on
every launch) and, on a non-zero exit, shows one `MessageBox` a screen reader
reads unaided: "QUILL Lite did not start", the reason in words, the log's
path and the support address. Windows' silent endings (a DLL not found, a
damaged or 32-bit file, access denied) are translated; a Python traceback's
last line is quoted with a hint. Pressing Enter on the exe *inside* the zip is
recognised from the archive tool's scratch-folder name and explained as
"extract the whole zip first". Exit 0 stays silent, so the single-instance
hand-off is unchanged. Shared code (`quill/native/launcher/launch_report.c`,
pinned to a Python mirror in `tests/unit/native/test_launch_failure.py`);
QUILL Lite gains it at its next launcher build, and the user guide's Getting
help chapter already opens with "If QUILL Lite does not start".

## 6a. The family pass (2026-09-18)

A twenty-nine item audit of the two editors against each other, closed in
September 2026. It is recorded here because three of its outcomes are now
constraints on this product rather than one release's work.

**The eleven rules are code.** `quill/core/family_rules.py` holds them and both
`keymap.py` and `lite/parity.py` cite them **by number**; a test checks that
every citation resolves, so the rules cannot be renumbered into lies. Lower
number wins when two conflict. Rule 1 -- Microsoft's key wins for a function both
editors have -- is itself a gate (`tests/unit/core/test_microsoft_habits.py`),
checked against both keymaps rather than believed; it found the last disagreement
on the day it was written, and Word's `F12`, `Ctrl+F12` and `Ctrl+Shift+F12` are
aliases in both products because of it.

**Divergence is a written argument.** `DIVERGENCES` in `quill/core/lite/parity.py`
holds the eight handlers whose chord is allowed to differ, each with the reason,
and the gate prints the reason when it reports the pair -- so the next person
reads the argument instead of re-having it. `SETTINGS_ALIASES` does the same for
the five settings one concept is stored under two names for, and the vocabulary
gate (`quill/tools/settings_vocabulary_audit.py`, in `platform_report`) fails a
new setting that is neither shared, aliased, nor a reviewed one-sided field. Two
of the five real pairs share no word at all, which is why it is a reviewed table
and not a name-similarity check.

**Rule 10 now cuts both ways in practice.** QUILL Lite may never be ahead of
QUILL, and the audit found places where it was: QUILL got the `DocumentText`
model QUILL Lite already had, the spelled suggestions QUILL Lite already spoke, the
Spelling Announcements window, and the swallowed-formatting-key guard. Where
QUILL Lite was behind, it gained Word's F12 family and the shared-store bridge
(5.3). Neither direction is a favour: a capability in one product and not the
other is invisible to the person who only has the other one.

---

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
imports neither QUILL nor QUILL Lite, so it can be run against a clean checkout.

**A collapsed caret described the wrong paragraph.** A collapsed TOM range
reports the formatting of the character *before* it, so standing at the start of
a heading described the paragraph above it. `caret_format_description` now probes
the character *after* the caret, which is what a screen reader describes.

### 7.1 The spell checker, and the exception that makes it usable

QUILL Lite ships a spell checker because the products it is measured against
have moved: WordPad never had one and never will, but the Notepad on a Windows
11 machine today has had spell check and autocorrect since 2024. An editor
claiming Notepad parity without one is behind the thing it is copying.

None of the checking is new. The wordlist, the suggestion ranking and the
guided F7 review are QUILL's, reached through the same helper the Mastodon
compose box uses. What QUILL Lite added -- and what QUILL now shares -- is the
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
the same file-type rule QUILL Lite does, behind `spellcheck_skip_code_files`.

Markdown is deliberately *not* on the code list. It is where people write, and
suppressing the whole file would silence the prose along with the code; its
code regions are handled by `spellcheck_live`, at the granularity that fits.

### 7.2 Selection is three features, not one

Edit > Selection is the largest single surface QUILL Lite adds, and it is worth
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

### 7.8 The thesaurus and the dictionary came to QUILL Lite, and Look Up came back to QUILL (2026-10-02)

The family rule ran both ways in one change. QUILL Lite had no thesaurus at
all -- a comment in the command table said it needed an asset download, which
was never true: the 18 MB MyThes file ships in every copy. QUILL's thesaurus,
meanwhile, looked up the word as typed and offered headwords, so "running"
found nothing and "sprint" was offered where "sprinting" was needed. Both are
fixed once, in shared code: `quill/core/word_lookup.py` walks a word back to
the headwords the data knows and inflects every replacement forward, and
`quill/ui/word_tools_commands.py` is the one `WordToolsMixin` both editors mix
in through `HostedAiMixin` -- Shift+F7, the *Thesaurus for "word"* and
*Dictionary for "word"* submenus on the context menu, Say Word Summary, and
the AI dictionary. QUILL's `show_thesaurus` now delegates to it.

**Look Up** (`quill/ui/lookup_window.py`, DICT-2's window) had been reachable
in QUILL only when the thesaurus data was missing, and it went online whenever
the dictionary feature was on, which is not consent. It is now Tools > Writing
> Look Up Word (Alt+F10) in QUILL and Tools > Look Up Word in QUILL Lite, the
online half is behind **Use online sources** in the window itself
(`dictionary_online_lookups`, the same field name in both settings files, so
the vocabulary gate sees one setting), and the online answer arrives on a
worker and replaces the offline one with a sentence said when it lands.

**The AI dictionary** (`quill/core/ai/word_tools.py`: one feature id, one
system instruction asking for JSON -- prose for listening and exact
replacement texts -- and thirteen prompts; `quill/ui/word_tools_window.py`:
the answer window) runs only on a direct route, because the free service is
metered per person and a dictionary is asked a hundred times a day. QUILL
reaches the same thirteen commands through a Dictionary submenu of its AI
menu (`quill/ui/main_frame_hosted_ai.py`), on QUILL Lite's chords exactly.

Gates that moved: a new Customize Features area, `dictionary`, with the
profile counts now 17, 21, 5 and 2 of 21; `commands_words.py` split out of
the command table under GATE-11; the Lite coverage snapshot has sixteen new
handlers, every one called by a test in `tests/unit/apps/test_lite_words.py`;
and menu_lint's rule against bare Ctrl+Alt chords (AltGr) decided the keys the
less-used rows carry.

## 8. Future directions

### 8.1 Accepted for a later release (decided 2026-09-08; shipped 2026-09)

**Everything in this section has shipped.** It is kept as the record of *why*
each item was accepted, because the reasoning is the part worth having and the
list itself is now the command table. Overwrite mode, tab mode, the line
operations, the deletion ring, persistent bookmarks, back and forward, Earlier
Versions, promote and demote, sentence and toggle case, reverse and number
lines are all in the shipped product; so, since 2026-09-17, are three of the
four things the last paragraph declined --- Extend Selection Mode, the Heading
Organizer and folding over Markdown sections --- which arrived by the other
route, as crossings from QUILL rather than as inventions here (bad.md 4.2).

Read it as history. The live list of what is still open is the family parity
plan, not this section.


QUILL's editor surface was diffed against QUILL Lite's, command table against
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
backups QUILL Lite *already writes* -- a safety net nobody can reach is not one,
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
- **Word paragraph styles beyond the shared vocabulary.** Revised
  2026-10-17: QUILL Lite now edits `.docx` through QUILL's own Word code (see
  *Word documents and table navigation*), so Heading 1-6, the list styles and
  Title, Subtitle, Quote and Caption go out as real Word styles. In the editor
  headings stay presentational -- the size-and-bold ladder -- exactly as in
  QUILL's rich mode, and every other Word style arrives as a normal paragraph
  with its visible formatting. That is the honest boundary: style sheets,
  custom styles and style editing remain out of scope.
- **A portable inventory baseline.** `portable-inventory.json` can only be
  generated from a real build; QUILL Lite adopts one when it first builds on a
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
  [`docs/qa/quilllite-signoff.md`](https://github.com/Community-Access/quill/blob/main/docs/qa/quilllite-signoff.md) -- 254
  numbered steps, each saying what to press and what decides pass or fail, with
  a fifteen-minute subset named at the top. Matching Studio (#839) and Inkwell,
  this is **not** required for the change to merge but **is** required for the
  release to publish. It is the only thing on this list a machine cannot do:
  everything else here is automated, and what a person actually *hears* is not.

## Find in Open Documents (2026-10-15)

QUILL's command from the same shared code (QUILL has it on Ctrl+Shift+F10, because its Ctrl+Alt+Shift+F8 is a QuillVille launcher; `parity.DIVERGENCES`) (QUILL Lite may never be ahead of QUILL, and here it is not behind either): **Edit > Find in Open Documents...** (**Ctrl+Alt+Shift+F8**; in Edit > Matches until 2026-10-16, see the placement note under Search in Files) finds and replaces across every open window's live text. The window and the model are QUILL's (`quill/ui/open_documents_find.py`, `quill/core/open_documents_search.py`); QUILL Lite supplies `quill/apps/lite_open_documents.py`, which lists `app.frames`, brings one to the front with `focus_frame`, and keeps the search state on the app so F3 in any window carries on the same search. Find and Replace end it (`cmd_find`, `cmd_replace`). Handler `cmd_find_open_docs`, parity `edit.find_in_open_documents`. Asked for on QUILLVille by Chris Nova.

## Search in Files and Replace Across Files (2026-10-15)

**Placement, revised 2026-10-16.** Find in Open Documents, Search in Files and Replace Across Files are rows of **Edit** itself, directly under Replace, in that order (`&Edit`, "F&ind in Open Documents...", "&Search in Files...", "Replace Across Files..."), and QUILL has the same three rows in the same order under Find All Matches. They first shipped inside **Edit > Matches**, and Jeff, launching from source with the changelog in hand, could not find either: a listener arrowing down Edit hears "Matches, submenu", and nothing in that word says a folder search is behind it, while QUILL filed the same commands in a different place again (Edit for one, Edit > Search Tools for two, and the two only in profiles with regular-expression search). Family rules 1 and 2 decide it: one placement for a command both editors have, and the placement a newcomer looks in first. **Edit > Matches** keeps the two commands about the document in front of you, All Matches and Count Occurrences. The three stay in the `matches` area (`command_areas.COMMAND_AREA`), now labelled "Matches and wider searches": on in a new install, off in the Notepad and WordPad profiles, whose promise is to have only what those programs had. Search in Files took the access letter S from Character Details, whose title has no other free letter in Edit; it keeps Ctrl+Alt+C. Replace Across Files has no access letter for the same reason and is reached by Ctrl+Shift+R or by arrow (GATE-14: no mnemonic beats a duplicate). Keys are unchanged. GATE-DOCMENU (`tests/unit/docs/test_documented_menus_lite.py`) now checks every menu path and every command named beside a key in this app's changelog and guide against the menus a new install builds, and pins the three Edit rows.

QUILL's two commands, on QUILL's keys -- Ctrl+Alt+Shift+F had been reserved for Search in Files since the keyboard parity work and never filled. The window moved from `quill/ui/main_frame_file_search_prompt.py` into the shared `quill/ui/file_search_prompt.py` (QUILL's mixin now only supplies its folder, parent and modal helpers), and the work is QUILL's `quill/core/file_search.py`. QUILL Lite's `quill/apps/lite_file_search.py` runs it on the app task manager and puts each report in a new untitled window, where QUILL opens a generated tab. Handlers `cmd_search_in_files` and `cmd_replace_in_files`, parity `tools.search_in_files` and `tools.replace_in_files`.

## The clipboard collector (2026-10-15)

QUILL's system-wide collector (#964), on QUILL's key, from QUILL's pieces: `quill/apps/lite_clipboard_collector.py` polls the OS clipboard change counter (`ui/main_frame_clipboard_collector._clipboard_change_counter`), appends with `core/clipboard_collector.append_collected`, collects each distinct payload once, keeps one collecting window per app, and stops when it closes. With QUILL's shared setting `clipboard_collector_saves` (2026-10-15, on by default, Preferences "Save after every clip the clipboard collector adds", Alt+Y) a window with a file name is saved quietly after each clip through `DocumentFileMixin.save_quietly`, which shares the write and the settling with Save, and the one announcement is "Collected and saved"; an untitled window is never saved and no window ever opens. Anything Save would ask about in a window (characters the encoding cannot hold, a file changed on disk) and a failed write are spoken instead ("Collected, but not saved." and the reason), and collecting carries on. The rule and the words are `core/clipboard_collector`, the same as QUILL's. Handler `cmd_clipboard_collector` (Alt+Shift+S, a check row on Edit > Clipboard), parity `power.toggle_clipboard_collector`. The parity table had mapped `cmd_collect_selection` to that command, which was never the same verb; Collect Selection is now `LITE_ONLY` with Paste and Clear, on Alt+Shift+C (rule 2: the command both editors have keeps the chord). Asked for on QUILLVille by Dean Martineau.

QUILL's system-wide collector (#964), on QUILL's key, from QUILL's pieces: `quill/apps/lite_clipboard_collector.py` polls the OS clipboard change counter (`ui/main_frame_clipboard_collector._clipboard_change_counter`), appends with `core/clipboard_collector.append_collected`, collects each distinct payload once, never saves, keeps one collecting window per app, and stops when it closes. Handler `cmd_clipboard_collector` (Alt+Shift+S, a check row on Edit > Clipboard), parity `power.toggle_clipboard_collector`. The parity table had mapped `cmd_collect_selection` to that command, which was never the same verb; Collect Selection is now `LITE_ONLY` with Paste and Clear, on Alt+Shift+C (rule 2: the command both editors have keeps the chord). Asked for on QUILLVille by Dean Martineau.

## PDFs, opened as text (2026-10-15)

QUILL Lite opened text files and nothing else; it now opens PDFs, as their text, and never writes one. Everything comes from QUILL (QUILL Lite may never be ahead of QUILL, and here it may not have a second implementation either): `quill/core/pdf_open.py` reads through QUILL's `quill/io/pdf.py` reader (pdfplumber, then pypdf, repaired text, form feeds between pages, at most 200 pages, the outline); `quill.io.structured._format_pdf`, which QUILL's File > Open uses, reads through the same function. QUILL Lite's half is `quill/apps/lite_window_pdf.py`:

- **Open.** `*.pdf` is in the Open filter's "All supported files" and has its own row. `open_prepare.prepare` reads a PDF into a `PreparedDocument` carrying the `PdfOpen` result, and `prepare_in_background` sends every PDF to the worker; `load` does too.
- **Password.** A locked PDF asks in QUILL's password box (`quill/ui/pdf_password.py`), then re-reads in the background with the password; a wrong one asks again saying so; Cancel opens nothing. The password travels in one `wx.CallAfter` and the worker closure, and is stored nowhere.
- **Damaged or no reader.** A failure box with the reader's own sentence; nothing opens.
- **Scanned** (no text, or under 50 characters a page): QUILL's question (`scanned_question`). Yes runs `ocr_pdf_for_open` as a background open -- Tesseract if installed, otherwise Windows OCR from the shared runtime, which needs no download (`quill/io/docconvert_windows.py`) -- with "Recognizing page N of M" on the message cell only, and opens the result with form feeds, marked modified. No opens the little text there is, or nothing. QUILL asks the same question on File > Open.
- **Pages.** The status bar gains a **Page** cell ("Page 3 of 12"), shown only while the document has form feeds, skipped by the arrow keys when hidden; Enter on it opens Go To on its Page kind. Go To (Ctrl+G) offers **Page** and **Outline** only when the document has them (`page_places`, `outline_places`, the same rows QUILL's Go To shows); outline rows resolve their page from the text at the time of the jump. The numbered bookmarks are untouched: nine slots cannot hold an outline.
- **Save.** The window keeps the PDF's path (title, Recent Documents, document memory), so Save refuses with QUILL's sentence (`save_refusal`, `EXPORT_ONLY_SUFFIXES`) and goes to Save As with `<name>.txt` proposed; Save As refuses a `.pdf` name; Reopen with Encoding is not offered; a reload after another program changes the PDF runs the whole open again.
- **No new command, no new key.** Ctrl+O and Ctrl+G, as in QUILL. Not done yet: File > Import / Convert Document (spec phase 2's menu row), headings and tables from the PDF (phase 3), and the portable build's dependency groups (the installed build already carries pdfplumber, pypdf, pypdfium2 and winrt in the shared runtime).

## The Read-Only Guard, Word names, and typing a name in a list (2026-10-16)

**Read-Only Guard.** QUILL's command (EDS-8) on QUILL's key: **Tools > Read-Only Guard** (**Ctrl+Alt+Backspace**, a check row), handler `cmd_toggle_read_only`, parity `power.toggle_read_only_guard`. The memory is QUILL's module, `quill/core/read_only_guards.py`, with QUILL Lite's own file in its data folder (`paths.data_file`, which does not create the folder to read). Keys are normalised the way document memory is, so a file opened from File Explorer under another spelling finds its guard. A failed write is spoken, never swallowed. While on, the control is read-only and `quill/core/lite/read_only.TEXT_CHANGING_HANDLERS` are refused by name at the menu and status-cell dispatch (`DocumentReadOnlyMixin.run_unless_read_only`) with "Document is read-only"; reading, Find, Go To, bookmarks and inline notes work, a note going beside the file through the shared `_host_read_only`; a word tool's Replace refuses through `refuse_if_guarded`. A file that cannot be written opens guarded, as in QUILL.

**Word names.** (As of 2026-10-16; the first clause was overtaken the next day, see below.) QUILL Lite then neither opened nor wrote Word documents; a typed `.docx`, `.docm`, `.dotx` or `.dotm` was refused with one sentence naming Rich Text (`filetypes.word_save_refusal`) before anything else is asked, on Save As, Save and the collector's quiet save. Before this, the window's text was written under the Word name. QUILL writes `.docx`; QUILL Lite is behind here, not ahead. *Superseded 2026-10-17: a rich window writes `.docx` through QUILL's writer; see Word documents and table navigation.*

**Typing a name in a list.** Every `apply_listbox_activation` list (Snippets, Recent Documents, the bookmark and heading lists, Recent Clips) has type-ahead from QUILL's `TypeAheadBuffer`; Space while a name is being typed is part of the name. Manage Abbreviations is a virtual list (`quill/ui/virtual_report_list.py`) whose search matches every word in any order and keeps the selection by identity.

## Highlighted passages (2026-10-16)

QUILL's three commands, shared (`quill/ui/highlight_commands.py`), on QUILL's
chords: **Navigate > Highlighted Passages > Next Highlighted Passage**
(**Alt+PageDown**, `cmd_next_highlight`), **Previous Highlighted Passage**
(**Alt+PageUp**, `cmd_previous_highlight`) and **List Highlighted Passages...**
(**Ctrl+F2**, `cmd_list_highlights`). A Word file opens here as text, so its
highlights are read from the `.docx` itself by the standard-library reader
`quill/io/docx_highlights.py` (QUILL Lite ships no python-docx) and placed on
the text by words and paragraph; a rich text document's come from the control.
Arrival says colour, count and words; the list's rows are words, colour and
paragraph, Enter goes there and Escape stays. Not listed: headers, footers,
footnotes, text boxes, shading.

## Word documents and table navigation (2026-10-17)

**One implementation, moved.** QUILL's wx-free Word decisions left
`quill/ui/main_frame_rich_mode.py` for the shared `quill/core/docx_open.py`, and
QUILL calls them in the same change: the fidelity scan (`fidelity_findings`,
over `scan_docx_features`), the question and its three rows
(`fidelity_question`, `fidelity_choices`, `choice_for_selection`; Cancel is
`text`), the one-time backup (`backup_path_for`, `backup_original`,
`needs_backup`: `name.backup-YYYYMMDD-HHMMSS.docx`, once per session, only for
a flagged original that exists), read-to-RTF (`read_docx_as_rtf`) and
RTF-to-Word (`rtf_to_docx_bytes`, `write_docx_from_rtf`, atomic). The opened
sentence is `OPENED_RICH_SENTENCE` in both editors. QUILL's tests
(`tests/unit/ui/test_rich_mode.py`) pass unchanged.

**Open.** `.docx` only (`docx_open.RICH_WORD_SUFFIXES`), as in QUILL, whose
rich Word path is also `.docx` only: a `.docm` written without its macros is a
file Word refuses under that name, so `.docm`, `.doc` and `.odt` stay read-only
text. `lite_window_word.open_mode_for` makes a `.docx` RICH when the control
has the TOM and python-docx is present; otherwise the 2026-10-16 read-only
text path is unchanged. `open_prepare.prepare_word` runs on the worker: scan,
RTF, and the extracted text only when the scan flagged something (the text
answer). A rich read that fails opens the text with "Opened NAME as extracted
text; the rich load failed." The commit (`DocumentWordMixin.settle_word_open`)
asks QUILL's question in a native `wx.SingleChoiceDialog` through
`show_modal_dialog`, row 0 preselected, inline F1 help.

**Save.** `saves_as_word(target)` is the rule: a RICH window and a `.docx`
name. It lifts the Word refusal (`refuse_word_target`), the read-only-source
refusals (`refuse_save_over_source`, `refuse_save_as_target`) and the
`.txt` proposal; a plain window, and `.docm`/`.dotx`/`.dotm` from any window,
are still refused, now with a sentence that names Switch Document Mode's key
for a `.docx` (`filetypes.word_save_refusal(name, switch_key=...)`). The RTF is
read with the theme colour off (`_set_whole_document_colour(None)`, restored in
`finally`), the guard every rich save has. Save As gained "Word document
(*.docx)" as `SAVE_WILDCARD_RICH` row 1 (`SAVE_FILTER_WORD`), preselected for a
Word document; the Open list gained "Word documents (*.docx)".

**Still saving.** Ctrl+S (`cmd_save` -> `save(background=True)`) writes a Word
document on the app's task manager (`begin_word_save`, `safe_to_cancel=False`,
a `UiLifetimeToken` invalidated by `cancel_background_load`). While it runs,
every save path answers "Still saving NAME" and starts nothing:
`save()` (so the close prompt waits), Save As, and the collector's quiet save.
The close prompt, Save As and the quiet save write synchronously, because they
need the answer. Text typed during a background save leaves the window
modified.

**Two shared fixes found by the round trip** (both editors): the RTF reader
now drops a heading's bold and ladder size when `\outlinelevel` follows them,
the order the Rich Edit control writes (Heading 5, 11.5 pt read back as 11,
became bold Normal text on the second save); and `rtf_to_docx_bytes` drops the
control's trailing NUL and trailing empty paragraphs (each save added one).
Heading 5 and 6 survive: `tests/unit/ui/test_word_rich_round_trip.py` runs
Heading 1-6, a bold run and a table through the real control three times.
QUILL Lite already had Heading 5 and 6 commands (Ctrl+Alt+5, Ctrl+Alt+6), so
nothing was added to its command set for this.

**Table navigation.** `quill/apps/lite_window_tables.py`, over the shared
`quill/core/table_nav.py` that QUILL's `main_frame_table_nav.py` calls: eight
handlers on QUILL's chords (family rule 2), parity rows `table.*`, a
**Navigate > Table** submenu. Outside a table: "Not in a table".
GATE-LITE-COVER: `tests/unit/apps/test_lite_table_nav.py` calls every handler.

**Tests.** `tests/unit/apps/test_lite_word.py` (real `.docx` files: open,
edit, save, reopen with python-docx; flagged files and each answer; Cancel;
backup once; copy; theme colour guard including a failed save; Save As row;
Still saving; typing during a save), `test_lite_save_as_typed_extensions.py`,
`tests/unit/io/test_rtf_heading_styles.py`, and the real-control round trip.

**Manual checks** are listed, not yet done, in `docs/qa/screen-reader-checks-2026-10.md`.

## Word-level AI review, the AI retry ladder, and the note-line cue (2026-10-17)

**Review AI Changes, word by word.** QUILL's window (`quill/ui/ai_diff_review_dialog.py`), so QUILL Lite has what QUILL has: for a change with two or more word edits, **Words in this change** (Alt+W) lists each with its sentence; Space keeps or drops one, and the rest of the change still goes in. Dropping every edit drops the change. Accept All takes everything and is exactly the AI's version; Reject All takes nothing; Ctrl+Z takes back the whole apply. F1 catalogue entry updated (`quill/core/lite_surface_help.py`).

**The AI tries again when the service is busy.** QUILL's ladder (`quill/core/ai/retry_ladder.py`) on all three routes QUILL Lite uses -- the free AI, the user's own key, a ChatGPT plan: three attempts on 408, 409, 429 and 5xx busy answers, one second then two, or the service's `Retry-After` up to 20 s; never a request the service says must not be repeated, a used-up allowance or plan, or a stream already under way. Only the last failure is said.

**A cue on arriving at a noted line.** QUILL's shared mixin (`InlineNotesCommandsMixin.cue_inline_note_line`), called from `DocumentFrame._on_caret_moved`. Setting `inline_note_line_cue`, the same name, default and choices as QUILL's, in Preferences (`quill/apps/lite_preferences_note_cue.py`): Play a sound, Say "note", Nothing. Sound event `inline_note_line` is in QUILL Lite's roster. Braille gets "note" when the cue is a sound (`app.voice.braille`).

**Not here, and why.** QUILL's browse-mode keys M (misspelling) and F (page) are QUILL-only: QUILL Lite has no browse mode. Its status bar's Page cell already shows "Page N of M" from the same `quill.core.navigation.page_position`.

## Word documents in every build, and one Office story (2026-10-17)

**Installed copies could not edit Word.** The shared QuillVille runtime that the installed QUILL Lite runs on excluded `lxml`, so python-docx (frozen in, but unable to import) left `docx_open.word_rich_available()` False. Every `.docx` took the read-only text path described in *PDFs, opened as text* and the Office readers, and the portable copy, which installs lxml with python-docx, was the only one that edited Word. Jeff's decision (2026-10-17) was to ship lxml whatever the size. The runtime spec no longer excludes it. The build proves Word works in every bundle with `quill/io/word_selfcheck.py`: `check_runtime_imports.py` runs it in the runtime, and `build_portable.py` (`check_word=True` for `quilllite`) runs it in the portable, so a build that would open Word as text does not finish. `tests/unit/scripts/test_word_support_in_runtime.py` simulates the runtime by blocking every spec exclude. The text path stays, as the safety net and for the "open for reading and plain editing" answer.

**The behaviour, the same as QUILL's** (QUILL also offers its read-only structured Word view; QUILL Lite has none):

| File type | Opens as | Save back to it |
| --- | --- | --- |
| `.docx` | Rich text to edit (`open_mode_for` RICH); the fidelity question when the scan flags something | Yes, as Word (`saves_as_word`); a flagged original is backed up once per session |
| `.docm` | Text; macros never run | No: `refuse_save_over_source`, then Save As with a `.txt` name |
| `.doc`, `.xls`, `.ppt` | Text through a LibreOffice temporary copy; without it, the reader's sentence naming the Save As type | No |
| `.odt`, `.xlsx`, `.pptx` | Text through QUILL's readers | No |
| `.xlsm`, `.ods`, `.odp` | Not in `OFFICE_OPEN_SUFFIXES` (QUILL's File > Open does not open them either); File > Import / Convert Document reads them | Not applicable (a new untitled document) |

Import / Convert always makes a new, untitled document that does not point back at the source; Ctrl+O opens the file itself, and only a `.docx` saves back to it. The user guide's "Office files at a glance" carries this table in plain words, and the changelog's Unreleased section has one consolidated entry for it instead of three written in build order.

## Dictation model advice from real speech, and five models removed (2026-10-22)

**Why.** Until now the recommendation (D-22) rested on ten recordings of a synthetic voice, which flattered every engine: every model scored 3 to 5 percent. The 2026-10-22 machine run measured every model on real people instead. The record is `docs/qa/dictation-real-speech-benchmark-2026-10-22.md` (data beside it in `dictation-real-speech-benchmark-2026-10-22.json`; engineering record in section 36 of `docs/design/2026-10-05-dictation-plan-and-status.md`). QUILL Lite shares QUILL's dictation engine and catalogue (`quill/core/windows_dictation/`), so QUILL, QUILL Lite and QUILL Transcribe changed together and QUILL Lite is not ahead of QUILL (section 2.2).

**How it was measured.** `scripts/dictbench.py`, run by `scripts/bench_machine_run.py`: one phrase at a time, one processor thread, processor only, each model in its own process. Sets: LibriVox held-out audiobooks in English (101) and Spanish (82), catalogued after every model's training cutoff; LibriSpeech test-clean and test-other (200 each); FLEURS English and Spanish (200 each). Decisions lean on the held-out audiobooks. One computer (Intel Core Ultra 7 265H, 16 cores, 64 GB), one day.

| Requirement | Met by | Evidence |
|---|---|---|
| The recommendation uses measured real-speech figures, and says so | `model_types.MEASURED` holds the held-out English figure, the mean of the two Spanish sets and the peak memory on any set; only models with a Spanish figure are offered for Spanish. `model_advice.ESTIMATE_NOTE`: "These figures come from our tests with real recordings, on one computer; yours may differ." | Benchmark doc, "The results" and "What changed in the apps" |
| English on 8 GB with four cores: NVIDIA Parakeet Unified 0.6B | Fewest words wrong of every model inside the 0.25 one-thread budget | 3.2% held-out, 6.3% FLEURS, 0.21 per thread, 1.2 GB peak |
| English on 8 GB with two cores, and Spanish on 8 GB: NVIDIA Parakeet TDT 0.6B v3 | Most accurate Spanish model measured; quickest of the 0.6B models | Spanish 4.4% FLEURS, 7.3% held-out; English 3.8% held-out; 0.11 per thread, 1.1 GB peak |
| 4 GB, or little memory free: the built-in Moonshine tiny (English) and Whisper tiny (Spanish) | Built in, and inside the 600 MB budget beside a screen reader, where the Parakeet models (1.1 GB and more) are not | Moonshine tiny 6.5% held-out, 584 MB; Whisper tiny 30.5% FLEURS Spanish, 27.0% held-out, 521 MB |
| "The quickest response" names Moonshine tiny | Unchanged | 0.06 per thread |
| An 8 GB baseline, and free memory counts | `model_types.RAM_TIERS` gives 1.6 GB on an 8 GB computer (was 1 GB), 600 MB on 4 GB; `model_advice._FREE_RESERVE_MB` caps at what is free less 500 MB | Benchmark doc, "An 8 GB baseline, and free memory counts" |
| Tiers follow real speed | Cost factors against Moonshine tiny from the English FLEURS run: Parakeet TDT v3 3.2, Parakeet Unified 3.8, Whisper base.en 4.3 (Lightweight, at most 5); Nemotron 5.8 (Balanced) | Benchmark doc, the speed-factor paragraph under the Spanish table |
| Five English-only models removed in this release, with one spoken notice, never silently | `quill/core/windows_dictation/removed_models.py`: Distil-Whisper small.en, Whisper small.en, Distil-Whisper medium.en, Whisper medium.en, Distil-Whisper large-v3 are gone from the catalogue and the model list. Whisper base.en and every multilingual Whisper size stay. Someone who was using one moves to Parakeet Unified if it is already downloaded, otherwise to the built-in model; nothing is downloaded. The next time dictation starts it says one sentence, once across every QuillVille program (recorded in `removed-model-notices.json` in the family's shared dictation folder): "Whisper small.en was removed in this release. Dictation now uses Parakeet Unified, which you already have." or "Whisper small.en was removed in this release, so dictation uses the built-in model. Parakeet Unified, in the model list, is more accurate." (with the model's own name). Downloaded files are not deleted; they stay in the shared models folder (`whisper-small.en-int8`, `whisper-distil-small.en-int8`, `whisper-medium.en-int8`, `whisper-distil-medium.en-int8`, `whisper-distil-large-v3-int8`). This replaces the plan's deprecate-for-one-release policy (dictation design section 32.6); the decision is section 37 of `docs/design/2026-10-05-dictation-plan-and-status.md` | Parakeet Unified 3.2% held-out against 5.9, 4.3, 6.3, 3.6 and 4.5; faster on one thread, in the same or a smaller memory tier |
| Moonshine base hears phrases longer than about 8.5 seconds | Long phrases are cut into pieces of 8 seconds or less at the quietest moment and joined (PR #1683) | 5.9% held-out after the fix; before it, every recording over 8.5 seconds came back empty |
| The user-facing documents tell the same story | User guide: "Better accuracy: optional speech models", new "How we chose: tested on real speech", rewritten "Nemotron or Parakeet: which should I try?", "Which engine should I choose?", "Which model for which recording"; release notes build 5; changelog Unreleased; announcement | The guide's tables are copied from the benchmark doc |

**Not settled by this run** (from the benchmark doc): a real 4 GB Windows computer with NVDA or JAWS running (B-8: speed, memory, screen-reader lag, battery) still needs a person; whether Whisper writes the opening "¿" and "¡" itself needs recordings with questions; Whisper medium and large-v3-turbo were too slow to re-run and keep their earlier figures.
