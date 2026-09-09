# QuillLite changelog

## 1.0.0 -- 2026-09-09

### Fixed

- **The portable copy stopped leaving itself on the host machine.** A portable
  QuillLite wrote its settings, recent files and -- worse -- its *recovery
  copies of unsaved documents* into `%LOCALAPPDATA%\QuillLite` on whatever
  computer it was plugged into, instead of into the `data` folder on the stick.
  Nothing said so, and the bundle even shipped a file asking for portable mode
  that was never read, because a bundle has to be recognised as portable before
  that file can be found -- and `QuillLite.exe` was missing from the list of
  names that counts as recognition. Inkwell, Beacon, Social and Cast were
  missing from it too. If you have been carrying a portable QuillLite, that
  folder is where anything you seem to have lost will be, and it is worth
  deleting once you have what you want out of it.

### Added

- **Bookmarks and your place in the file survive closing the document.** The
  reason to have numbered bookmarks at all is that there is no scrollbar thumb
  to glance at in a long file -- and that does not stop being true when the
  window closes. Marking nine places and losing them on the way out is the same
  loss, deferred. Reopen a file and the bookmarks and the cursor are where you
  left them; a document you have never saved is not remembered, because there is
  nothing stable to key it by, and nothing is ever written next to your own
  files. Switching bookmarks off in Customize Features stops it being written at
  all.

- **Go Back and Go Forward** -- **Alt+Left** and **Alt+Right**, in the Edit
  menu. The undo for moving about. Every jump is remembered: going to a line,
  following a heading, picking from the heading or bookmark list, landing on a
  search hit. Without it, pressing F3 to check a word elsewhere is a one-way
  trip, and finding your way back means knowing a line number you were never
  told.

- **Earlier Versions** (**Ctrl+Alt+Shift+E**, File menu). QuillLite has written
  a dated copy of every save since backups shipped and gave you no way to read
  one: the files were correct, correctly named, and reachable only by knowing
  where the app keeps them. A safety net nobody can reach is a folder that fills
  up. The list reads "Today at 4:12 PM -- 2,341 words"; **Restore** puts a
  version into the window without saving, so Ctrl+Z takes it back and the file
  on disk is untouched until you decide, and **Open a Copy** puts it in a new
  window and leaves your document alone.

- **Format ▸ Structure**: **Promote Heading** and **Demote Heading**
  (**Alt+Shift+Left** / **Right**), **Move Section Up** and **Down**
  (**Alt+Shift+Up** / **Down**). QuillLite could make headings and walk between
  them but never move them, which left cut-and-paste as the only way to
  reorganise -- the operation it is worst at, since moving a section by hand
  means selecting to a boundary you cannot see and usually costs you your place.
  QUILL's own four keys. Section moves work in plain text, where headings are
  Markdown; promoting and demoting work in both modes.

- **Overwrite mode**, with a **Typing Mode** cell in the status bar
  (**Ctrl+Alt+Shift+W**). A mode you cannot ask about is one you discover by
  typing over your own work. The **Insert** key still works, because the editing
  control answers it whether QuillLite asks or not -- QuillLite watches for it
  rather than claiming it, since Insert is NVDA's and JAWS's own modifier, so
  the cell stays right either way.

- **Tab Key Inserts a Tab Character** (**Ctrl+Alt+Shift+I**), with a **Tab
  Mode** status cell. QuillLite starts where Notepad does -- Tab types a tab --
  and clearing the tick makes Tab indent the line instead, announcing the new
  depth. **Shift+Tab** outdents in either mode, so a tab typed by accident is
  always one keystroke away from being undone.

- **Describe Indent Depth** (**Ctrl+Alt+Shift+V**, Tools ▸ Indenting). How far
  the current line is indented: "4 spaces", "1 tab", "1 tab, 3 spaces". A screen
  reader reads a line's words and not the whitespace in front of them, so in a
  YAML or Python file the structure of the document is not there when you listen
  to it -- and it also tells you the thing nothing else will, that this line is
  indented with a tab while its neighbours use spaces. Added to QUILL first, on
  the same key, because QuillLite may never be ahead of the editor.

## 1.0.0 -- 2026-09-08

First release. QUILL with everything removed except the editor: numbered
documents in one window, plain text or rich text, and nothing else.

Contributed as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`) under this repository's MIT licence, and
adopted into the QuillVille family here.

### Added

- **An application icon of its own.** A white page with a folded corner and two
  amber lines of writing, on a forest-green tile. Every other glyph in the
  family is round, pointed, or built from bars, so this is the only one that
  blurs to a rectangle with a bite out of it -- which is the test that matters,
  because the other one is 16x16 in a taskbar. Generated by
  `scripts/build_app_icons.py` like every sibling, and gated so it cannot
  silently become a copy of another app's face.

- **Numbered documents in one window.** Documents open as numbered children of
  one QuillLite window, and a number never changes while that document is open
  -- so "document 3" stays a name a person can hold rather than "the other
  Untitled". Alt+1 to Alt+9 jump straight to one, Ctrl+Tab and Ctrl+F6 walk
  them, and the Window menu lists them all with a mark on the one you are in.
  The title carries the number, because that is the one string a screen reader
  reads on arrival.

  The cost is recorded rather than hidden: documents inside one window do not
  appear in Alt+Tab, so those four routes carry the whole job of moving between
  them, and all four are bound rather than one.

- **Notepad's and WordPad's keys, unchanged.** Ctrl+N, Ctrl+O, Ctrl+S,
  Ctrl+Shift+S and Ctrl+P; Ctrl+F, F3, Shift+F3, Ctrl+H and Ctrl+G; F5 for the
  date and time; Ctrl+B, Ctrl+I and Ctrl+U; Ctrl+L, Ctrl+E, Ctrl+R and Ctrl+J
  for the four alignments; Ctrl+1, Ctrl+5 and Ctrl+2 for single, one-and-a-half
  and double spacing; Ctrl+Shift+L for bullets; Ctrl+Shift+> and Ctrl+Shift+< to
  grow and shrink; Ctrl+=, Ctrl+- and Ctrl+0 for zoom. Somebody moving from
  either should not have to learn anything.

- **A status bar that can be read.** Ten focusable cells on QUILL's own model:
  F6 lands in it, the arrow keys and Home/End move between them, Enter acts on
  the cell, and Escape returns to the document. The last message, the position,
  words, characters, the selection, the mode, the heading you are in, the
  encoding, the line endings, and whether anything is unsaved.

  Two of those are facts no editor most people have used shows at all --
  encoding and line endings -- and they are exactly what decides whether a file
  survives a round trip. Refreshes are coalesced through a 90 ms timer (QUILL's
  own window), because counting words is O(document) and doing it per keystroke
  is felt while typing.

- **Byte-honest files.** Open, change nothing, save, and the bytes are the bytes
  you started with: the encoding is kept including a byte order mark, the line
  endings are kept, and a file that did not end in a newline does not grow one.
  UTF-8 is tried before Windows-1252 precisely because cp1252 cannot fail to
  decode, so trying it first would mean never detecting anything else.

- **Encoding and line endings on purpose** (Ctrl+Alt+E). The round trip is the
  default and this is the deliberate exception, for the person who needs a UTF-8
  copy of an old file or Unix line endings for a build server. It takes effect
  at the next save, which is the moment it means anything.

- **Nine numbered bookmarks** that move with the text as you edit around them --
  a bookmark that is wrong is worse than one that does not exist, because it is
  trusted. Ctrl+Shift+B drops one, Ctrl+Shift+1 to 9 set a numbered one, F2 and
  Shift+F2 walk them, Alt+Shift+G lists them.

- **Structural selection.** Select the word, the line or the paragraph, or press
  Ctrl+Shift+X to expand outwards -- word, line, sentence, paragraph, block,
  document -- with the scope announced each time. Shift+arrow selects by
  character, which is the right tool for two letters and the wrong one for a
  paragraph.

- **Describe Character** (Ctrl+Shift+C). Exactly which character the cursor is
  on: its name, its code point, and the plain-language note for the invisibles
  that bite writers. A screen reader says "space" for four different characters,
  and this is the only way to tell which one broke the search.

- **Three answers to a clipboard that holds one thing.** A twelve-slot copy tray
  that survives a restart; a collector that gathers several copies into one
  buffer; and a rolling clip library that remembers what was copied whether or
  not you decided at the time that it mattered. Plus Ctrl+Shift+V, which pastes
  text with none of its formatting.

- **Tools.** Sort lines, remove blank lines, remove duplicates, trim trailing
  spaces, and UPPERCASE / lowercase / Title Case -- each on the selection if
  there is one and the document if not, and each a single undo step, so Ctrl+Z
  takes back the whole sort rather than forty separate line moves.

- **Abbreviations.** QUILL's own engine and manager dialog, over QuillLite's own
  library. A switch in Preferences -- off by default -- points it at the library
  QUILL and Quill Inkwell share instead. Off by default because a machine that
  has never had QUILL installed must not grow a Quill data folder because
  somebody opened a text file.

- **Spell check**, which neither Notepad nor WordPad had when this editor's
  keyboard was designed -- WordPad never gained one at all, and Notepad only in
  2024. QUILL's dictionary, QUILL's suggestions and QUILL's guided review: F7
  reviews the document, Shift+F7 suggests for the word at the cursor, Ctrl+F7
  and Ctrl+Shift+F7 move between misspellings and *select* them so the word is
  what the reader reads on arrival, and Alt+F7 teaches it.

  The load-bearing part is where it does **not** speak. Spell check while typing
  is off by extension in source and configuration files
  (`quill.core.spellcheck_filetypes`), because every identifier in one is a word
  no dictionary has and each false alert costs a status line to read past --
  the cost a sighted user pays for a red underline and a screen-reader user pays
  in full. Markdown is prose and is checked; its fenced blocks and code spans
  are suppressed by region instead. The state is per document, so a letter and
  a config file open together can honestly disagree, and Ctrl+Alt+F7 changes
  only the one you are in. Opening a skipped file says so once: a checker that
  is silently off is indistinguishable from one that is broken.

  Taught words live in QuillLite's own folder unless Preferences says to share
  QUILL's, for the same reason the abbreviation switch exists and defaults the
  same way. A document may also carry its own `.quill-dict.json` sidecar.

- **A Selection submenu under Edit**, and it is three features rather than one. *Mark and
  extend* (F8 anchors, any navigation key extends, Shift+F8 completes,
  Ctrl+Shift+F8 reselects, Alt+Shift+F8 goes to the start) is the only way to
  take an arbitrary run without holding a modifier down the whole way. *Struct-
  ural* selection takes the word, line, paragraph, sentence or block in one
  keystroke, and Expand/Shrink walk the ladder in both directions. *Marks* are
  throwaway positions -- deliberately not bookmarks, which are the ones you mean
  to keep -- with set, pop, list and exchange-with-cursor.

  Every one of them announces **how much** it took. A selection that says
  nothing is one the user has to test by pressing something destructive, and
  the count is the whole difference between "I have it" and "I think I have it".

  Select All keeps its place in the Edit menu on Ctrl+A, so switching this whole
  area off never removes it.

- **Printing** (Ctrl+P) and Page Setup. Long lines wrap to the page whatever the
  Word Wrap setting says, because a printed line that runs off the paper is gone
  rather than scrolled to.

- **Unsaved-work recovery.** A copy of every modified document written aside on
  a timer, beside your file and never over it, offered back on the next launch
  and deleted the moment you save or close cleanly.

- **Session restore.** Reopen the documents that were open last time, in the same
  numbered order. Distinct from recovery, which is only ever about work that was
  never saved.

- **Customize Features** (View menu). Whole areas can be switched off -- rich
  text and the Format menu, headings, bookmarks, the Tools menu, the clipboard,
  printing, abbreviations, spell check, the Selection submenu -- and switching
  one off removes its menu *and* its
  keys, because a key that still fires for a feature you turned off is the
  feature not being off. This is how QuillLite stays a small editor without
  being a poor one.

  Three areas ship switched off and are found in the same list rather than
  hidden: autocorrect (welcome in prose, actively wrong in a config file),
  timestamped backups (reassuring, and they fill a folder), and Go To Anything.

- **The Command Palette** (Ctrl+Shift+P), which answers "how do I sort lines?"
  rather than "what is under Format?", and shows each command's key beside its
  name -- which is how a key gets learned.

- **F1 everywhere.** What this window is for, then what the control you are on
  does, through the family's shared engine. Gated by GATE-LITE-HELP, plus a
  stricter QuillLite-only check that covers the two things the shared scanner
  cannot see: checkboxes, and the document control itself.

- **Dark mode by default,** view-only and stripped back to automatic colour
  before every save, so a theme can never land in a document you send somebody.

- **Speech to NVDA and JAWS only.** No self-voicing fallback: a second voice
  talking over a screen reader is worse than silence. Only outcomes are
  announced -- a save, a wrapped search, a formatting change -- because titles,
  focus moves, control names and selections are the reader's to say. Everything
  spoken also lands in the status bar, so a missed message can be read again.

- **Its own data folder** (`%LOCALAPPDATA%\QuillLite`), deliberately not
  `%APPDATA%\Quill`. Uninstalling does not remove it: recovered work is the one
  thing somebody may not have finished with, and an uninstaller is the worst
  moment to discover that.

- **A settings file that only records what you changed.** A fresh profile's
  `settings.json` is `{"schema": 1}` and nothing else. That is not tidiness: a
  file that spells out every field freezes today's defaults into every user's
  profile forever, so a later version that changes the default theme would leave
  behind exactly the people who never expressed a preference. Writing deltas is
  what QUILL's versioned-store contract buys, taken directly.

- **A sign-off checklist** ([`docs/qa/quilllite-signoff.md`](../../../docs/qa/quilllite-signoff.md)):
  89 numbered steps for a person at a keyboard with a screen reader, each saying
  what to press and what decides pass or fail, with a fifteen-minute subset named
  at the top. It exists because everything a machine can check here is already
  checked -- and what somebody actually *hears* is not one of those things.

- **Four release artifacts** on the family contract -- full installer, thin
  installer, portable zip and companion zip -- sharing the QuillVille Runtime,
  with neither ffmpeg nor libmpv staged because QuillLite has no media pipeline.

- **An optional file association.** The full installer offers *Open with
  QuillLite* for `.txt` and `.rtf` as a component, never as the default handler.
  An editor that quietly takes over every `.txt` on a machine is an editor
  people uninstall.

### Fixed (in QUILL, for every QUILL user)

Both were isolated in PR #1490 and left unapplied so that adding an app and
changing the editor stayed separate decisions. Both decisions were taken.

- **`_TOM_TRUE` was `tomUndefined`, so every rich-mode heading lost its bold.**
  `tom.h` defines `tomTrue` as `-1`; QUILL used `-9999999`, which the same
  header defines as `tomUndefined` -- "leave this property alone". Assigning it
  to `ITextFont.Bold` asked the control to change nothing and *succeeded*, so
  `set_heading` applied the point size, silently never applied the bold, and
  raised nothing. Because `heading_level_for_font` requires bold before it will
  call a paragraph a heading, QUILL could not then find the headings QUILL had
  just made: heading navigation and Describe Formatting both went blind.
  Measured on RICHEDIT50W / Riched20 10.0.26100 -- `Bold = -9999999` gives
  `Weight=400`, `Bold = -1` gives `Weight=700`. Reproduced standalone in
  `tests/repro_tom_true.py`, which imports neither QUILL nor QuillLite.

- **A collapsed cursor described the paragraph above it.** A collapsed range in
  the Text Object Model reports the formatting of the character *before* it, so
  standing at the head of a heading and asking "what is this?" answered with the
  body text above. `caret_format_description` now probes the character after the
  cursor, which is what a screen reader describes.

### Added (in QUILL, so the editor is never behind its own small sibling)

- **Justify** (Ctrl+Alt+J), completing the four alignments -- the Rich Edit
  surface has always supported it and nothing was bound to it.
- **Line spacing** -- single, one-and-a-half and double (Ctrl+1, Ctrl+5, Ctrl+2).
- **Grow and Shrink Font** (Ctrl+Shift+> and Ctrl+Shift+<), stepping a ladder of
  real point sizes that includes the heading sizes, so growing a heading stays
  on the heading ladder rather than falling off it.
- **Paste Text Only** (Ctrl+Alt+V), which neither product had.
- **Bullets in rich mode**, driving the real list type instead of inserting a
  Markdown dash into a Rich Text document.
- **`edit.select_word` (Ctrl+Alt+W)**, which did not exist. QUILL could select a
  line, a paragraph and a block, and the innermost rung of its own expansion
  ladder was the one thing it could not be asked for directly.
- **A key for `edit.select_line` (Ctrl+Alt+E)**, which was registered, was in the
  Edit menu, and was in no keymap at all -- so its label advertised no shortcut.
- **Keys for three commands that had none**: `edit.select_paragraph`
  (Ctrl+Alt+Shift+P, unbound since Ctrl+Alt+P was dropped under §10.8, which the
  authored Ctrl+Alt set reverses), `edit.duplicate_selection` (Ctrl+Alt+Shift+Q;
  §4.17 avoided Ctrl+D, not the command) and
  `edit.toggle_extend_selection_mode` (Ctrl+Alt+F8, previously reachable only by
  opening the keymap editor to assign one).
- **`quill.core.selection.shrink_selection`**, a computed inverse of
  `expand_selection`, and `MainFrame.shrink_selection` now falls back to it when
  there is no expansion history. The stack only knew about selections reached
  *by expanding*: selecting a paragraph outright and asking to shrink said "no
  selection to shrink", which a listener cannot tell apart from a broken
  command.
- **A live spell check that stays quiet in code** (`spellcheck_skip_code_files`,
  on by default). `spellcheck_live` already suppressed URLs, code spans and
  fenced blocks, which is the right granularity *inside* prose and no help
  whatever in `main.py`, where the whole file is the exception. QUILL now
  consults the shared file-type rule before every live alert. The F7 review is
  deliberately not gated: a default decides what happens when nobody has said
  anything, and running the review is saying something.
- **`load_combined_dictionary` and friends take a `personal_dir`**, so a sibling
  app can keep its own taught words in its own folder instead of growing a
  `%APPDATA%\Quill` on a machine that has never had QUILL installed. QUILL
  passes nothing and gets exactly what it got before.
- Every QUILL editor tab is now built on the extended surface, so all of the
  above is available by construction rather than through a second code path.

QUILL takes Ctrl+Alt+J and Ctrl+Alt+V where QuillLite uses WordPad's Ctrl+J and
Ctrl+Shift+V, because Ctrl+J has been Set Temporary Bookmark and Ctrl+Shift+V
has been Preview in QUILL for far longer. An existing binding somebody's hands
already know outranks a new command's convention; the divergence is recorded in
the keymap rather than left to be discovered.
