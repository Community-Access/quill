# QuillLite changelog

## Unreleased

### Added

- **Copy All (Ctrl+F8)** puts the whole document on the clipboard without
  selecting it. Select All then Copy is two keys and leaves everything selected
  afterwards, so the next character typed replaces the document.
- **Copy to Tray Slot... (Alt+Shift+Y)** lets you choose which of the twelve
  slots to copy into, with each row saying what is in that slot now. Ctrl+Alt+Y
  still takes the next free one.
- **The clip library can fill itself.** Preferences has a new switch, **Keep
  everything I copy in the clip library**, and with it on every copy and every
  cut made inside a QuillLite document is remembered, up to the last two
  hundred. It is off until you ask for it: a history of everything you copy is a
  file on your disk holding whatever you last took out of a document. The help
  text in Preferences says so. Until now the app promised this history in three
  places and never kept any of it -- only Keep Clip ever put anything in the
  library.

- **A temporary bookmark** -- **Ctrl+Alt+J** drops a pin where the cursor is and
  **Ctrl+Shift+J** goes back to it. Use it when you are about to go and look
  something up and want to come straight back. It has no number, no label and no
  row in the bookmark list, setting it again simply moves it, and it is gone when
  the document closes. QUILL has had these two keys for years; they now mean the
  same thing here.
- **Save an HTML page as Markdown.** The Save As box offers **Markdown
  (*.md)** again, and this time it converts: an HTML document saved as `.md`
  has its tags turned into Markdown as it saves -- `#` headings, `**bold**`,
  `-` lists, links that keep their text and address -- and QuillLite says
  "Converted HTML to Markdown". The document on screen changes with the file,
  so the window and the file never disagree. Tags Markdown cannot write are
  dropped and their text kept; a page that would convert to nothing is left
  exactly as it was and says so. Plain text and Markdown documents saved as
  `.md` are untouched. Rich text is not offered the row -- flatten to plain
  text first, which the dialog already asks about.
- **Lists announce themselves.** Arrow into a list and QuillLite says "Bulleted
  list, 5 items"; a level deeper, "Level 2, 3 items"; on the way out, "Out of
  list". This is the one cue a screen reader gives you everywhere else -- a
  browser hands it a list with a count, and an editor hands it characters.
  Markdown and HTML, over bullets, numbers and definition lists alike, with
  "Term" and "Definition" as you move between the two halves of a `<dl>`.
  Items are counted at your own level inside your own list, never totalled.
  **View > Announce Lists (Ctrl+Alt+F5)** turns it off and on where you stand.
- **A plain document now has a language**, and it decides what the keys write.
  **Ctrl+B in a `.md` writes `**bold**`; in a `.html` it writes `<strong>`**,
  where both used to refuse and send you to rich text. Same for italic,
  underline and the six heading levels. `.html`, `.htm` and `.xhtml` are
  recognised; `.md`, `.markdown`, `.mdx` and `.txt` are Markdown; a `.py` or a
  `.conf` is plain and says so.
- **An Insert menu**, before Format, holding what used to be Edit > Insert plus
  three new rows. Every existing key is unchanged.
- **Insert > Emoji (Alt+.)** -- QUILL's picker, key for key: search by name,
  keyword, description or a typed smiley, browse by category, and read a
  written description of every glyph. In every document, rich text included.
- **Insert > Markdown Tag (Ctrl+Alt+I)** and **Insert > HTML Tag
  (Ctrl+Alt+O)**. Exactly one is ever live -- whichever the document is -- and
  the other is dimmed rather than hidden, so a reader is told it is unavailable
  rather than left hunting for it. The HTML picker searches by what a tag
  *does*: "dropdown" finds `select`, "checkbox" finds `input`.
- **Whole form fields in the HTML picker** -- twenty of them, each arriving
  labelled and wired: a `for` that matches the field's `id`, a `name` that
  submits, options inside a select, a legend inside a fieldset, one shared
  `name` across a radio group, and `aria-describedby` joining a field to its
  hint and its error. The `id` is checked against your document first, so a
  second email field is `email-2` rather than a silent duplicate. Select a word
  and it becomes the label, with the `id` derived from it so the two agree.
- **The HTML picker now offers 111 tags**, up from 46. The forty-six left out
  `<dl>`, `<dt>` and `<dd>` -- which this editor *announces* as you arrow
  through them -- along with `<figure>`, `<figcaption>`, `<caption>`, `<thead>`,
  `<tbody>`, `<abbr>`, and `<br>` and `<hr>`, which were handled as void
  elements and simply could not be chosen. A searchable list should be
  complete: searching 111 is no harder than searching 46, and a missing tag is a
  dead end.
- **The Markdown picker gained Underline, Horizontal Rule, Strikethrough and
  Definition List.** The first two had builders and no menu row for months.
- **Format > Document Language (Ctrl+Alt+F6)**, and the status bar's Format
  cell, for saying the language is not what the file name implies.
- **A List cell on the status bar**, which says which item you are on as well
  as which list you are in -- the one thing the speech deliberately does not.
- **Customize Features gained a Markdown and HTML area** (18, not 17).

### Changed

- **Two downloads, not four.** QuillLite publishes an installer and a portable
  zip. The thin `QuillLite-Lite-Setup` and the launcher-only
  `QuillLite-Companion` zip are retired, and neither was right for this
  product: the Companion zip installs nothing, so it ran against whatever
  shared runtime happened to be on the machine -- including one built before
  QuillLite existed, which failed at launch with "No module named
  quill.apps.lite" and could not repair itself. The thin installer swapped a
  113 MB download for a 110 MB first-launch download and a network dependency,
  on the one app people install *because* they have nothing else. If you
  already installed the thin edition, the installer upgrades it in place --
  same AppId, nothing to uninstall -- and Check for Updates offers it to you.
  The other QuillVille apps are unchanged.
- **A heading now says its level first**: "Heading 2, Installing" rather than
  the line followed by "Heading 2". Not a matter of taste -- a cue queued behind
  the reader is cancelled outright on a big caret jump, which is why Ctrl+Home
  onto a heading announced nothing while arrowing onto it announced it.
  **Preferences > "Say a heading's level" > After the text** restores the old
  order for anyone who prefers it.
- **Ctrl+Shift+M rings through all four kinds of document** -- plain text,
  Markdown, HTML, rich text, and round again -- where it used to toggle between
  two of them. Each stop says its own name. Enter on the Format cell does the
  same.
- **The status bar's Format cell names all four kinds.** It said "Plain text" or
  "Rich text" and nothing else, so two thirds of the states its own Enter key
  produced were invisible in the one place somebody would check.
- **Applying a heading rewrites the line** instead of stacking on it:
  Ctrl+Alt+2 on `### Notes` gives `## Notes`, never `## ### Notes`.
- **Alt+Shift+Left and Right walk HTML headings** in an HTML document, instead
  of looking for hashes it will never contain.
- **A formatting refusal names the document it is refusing in**, and offers both
  ways out: rich text, or giving the document a markup language.

### Changed

- **Large documents stopped costing what they did.** QuillLite read its whole
  buffer out of the text control five separate times -- the status bar's counts,
  the heading cue, the list cue, the live spell check on every arrow press, and
  the autocorrect rule on every single keystroke. In a big file that is what made
  arrowing feel heavy. It reads once per edit now and answers everything else
  from what it already has, and the autocorrect rule asks for one character
  instead of the document. Nothing looks different; a long file simply behaves
  like a short one.

### Fixed

- **Two timers could fire on a window that had been closed.** The live spell
  check and the pending "and here is how it is spelled" were left running when a
  document window went away, and the failure that followed was swallowed. Both
  are stopped now, with everything else on a clock.
- **The empty copy tray named the wrong key.** "Control Shift 0 copies into it"
  was a chord that had not been Copy to Tray since before 1.0, and could not be
  right anyway once the key was rebindable. It now reads whatever Copy to Tray
  actually answers to.
- **The collector's count no longer counts dashes.** Collecting a piece with a
  line of `----` in it -- which is most log files -- inflated "Collected N
  pieces". The pieces are counted now rather than inferred from the text.
- **Clearing an empty collector says so**, instead of reporting "Collector
  cleared" whether it discarded five gathered quotes or nothing at all. When it
  did discard something it now says how much.
- **F6 now leaves the status bar as well as entering it.** Escape still works;
  so does the key that got you there. Shift+F6 too.
- **Announce Headings is remembered between launches in QUILL too.** It never
  was: QUILL wrote the setting and never read it back. QuillLite was never
  affected -- its loader walks the dataclass fields rather than naming each one
  -- but the two products share the switch, so it is fixed here as well.
- **Ctrl+Home onto a heading announces it.** See the heading-order change above.

### Added

- **Headings announce themselves.** Arrow onto a heading and QuillLite says
  "Heading 2". It has to say it, because no Windows edit control exposes a
  paragraph style to a screen reader -- JAWS and NVDA could see the font size
  and the weight and nothing else, so a heading read out exactly like body text.
  The level only, once on arrival, and in both rich text and Markdown.
- **Heading navigation works in plain text.** Next Heading, Previous Heading and
  the headings list refused outright in a plain document -- "Headings are only
  available in rich text" -- in documents whose Markdown headings Alt+Shift+Right
  would happily re-level. They now walk the hashes, and a `#` inside a fenced
  code block is correctly not a heading. The status bar's **Heading** cell read
  "Not in rich text" in those same documents -- wrong twice over, since pressing
  Enter on it has always opened a working list of them -- and now reads the
  level.
- **View > Announce Headings (Ctrl+Alt+F3)** turns the cue off and back on where
  you stand, saying which way it went rather than "on" and "off". Reading a
  document as text is a different job from writing one.
- **A `#` is only a heading where `#` means heading.** A `.md`, a `.txt` or an
  untitled buffer has Markdown headings; a `.py`, `.sh`, `.ini`, `.yml` or
  `.conf` does not, because there a leading `#` is a comment -- and QuillLite is
  the editor people open build scripts in.

- **Tools > Back Up Settings... (Ctrl+Alt+Shift+Q)** and **Tools > Restore
  Settings... (Ctrl+Alt+Shift+D).** Write your configuration to a `.qsf` file
  and put it back on another machine. What describes *this* computer -- the
  recent-files list, the restored session, the window size, the update
  timestamp -- is deliberately left out, so a restore cannot point QuillLite at
  files that are not there. Restoring says what came across, what has been added
  since the file was written, and what was left alone.

- **Edit > Insert > Line Break (Shift+Enter).** Ends the line without starting
  a new paragraph -- the distinction a blank line cannot make, and the chord
  Word uses for the same thing. QuillLite says which spelling it wrote, because
  the older one (two trailing spaces) is invisible on screen and silent to a
  screen reader. **Markdown line break style** in Settings chooses; the default
  is a backslash.

- **Edit > Insert > Special Character... (Ctrl+Shift+F2).** A searchable picker
  for the 357 characters a keyboard has no key for. Type part of a name
  (`dash`, `euro`, `acute`, `arrow`) or a word Unicode does not use but people
  do (`gbp`, `copyright`, `eszett`), or clear the box and browse one of fifteen
  groups: whitespace, dashes and hyphens, quotes, invisible and control,
  typography, legal and reference marks, currency, maths and units, fractions,
  superscripts and ordinals, arrows, accented letters small and capital, Greek
  letters, and punctuation from other languages. Each row shows the character,
  its name and its code point, with a description pane that updates as you
  arrow. Enter inserts, and QuillLite reads back what it put in -- "Inserted --
  U+2014 Em dash" -- because most of the list is invisible on the page and the
  reader says nothing when an app writes text on its own behalf. The search box
  is also a code-point box: `2014`, `U+2014` and `d8212` all find the em dash,
  and a code point in no group still resolves, so the picker reaches every
  character Unicode has. QUILL has the same picker on Shift+F2.

  **Insert Date and Time moved with it**, from Edit to **Edit > Insert > Date
  and Time**. Its key is still **F5**.

### Changed

- **The spelling context menu is one submenu.** The Applications key on a
  misspelled word used to add a dozen rows to the top of the popup, which put
  Undo and Cut a different distance down the menu depending on whether the word
  under the cursor happened to be misspelled. Everything about the word is now
  under one row named after it -- *Spelling: "wrold"* -- and the first thing
  inside it is still the first suggestion. One extra press: Down, then Right.

## 1.0.0 -- 2026-09-12

First release. QUILL with everything removed except the editor: numbered
documents in one window, plain text or rich text, and nothing else.

Contributed as [PR #1490](https://github.com/Community-Access/quill/pull/1490)
by Steven Scott (`doubletaponair`) under this repository's MIT licence, and
adopted into the QuillVille family here.

### Changed

- **Page Setup moved to Ctrl+Alt+P.** It had Ctrl+Alt+U, which is Check
  for Updates in every other app in the family -- a chord that means one thing
  in eight apps and something else in the ninth is the kind of difference nobody
  finds until it does the wrong thing.

- **The menu bar is Notepad's and WordPad's again: File, Edit, View, Format,
  Navigate, Tools, Window, Help.** Eight menus where there were ten. Clipboard
  and Spelling were top-level menus of their own -- two more things to walk past
  on every Alt press, for two features neither Notepad nor WordPad puts on the
  bar at all. They are now **Edit ▸ Clipboard** and **Tools ▸ Spelling**.

- **Line work moved from Tools to Edit ▸ Lines**, which is where editing
  belongs: moving, duplicating, joining and deleting lines, sorting, reversing
  and numbering them, and removing blanks, duplicates, trailing spaces and
  stray whitespace -- all in one submenu, grouped by what they do, instead of
  spread down a Tools menu with a *More Line Work* submenu hanging off it.
  Change Case became **Tools ▸ Change Case**. **No shortcut changed**: every
  key is exactly where your fingers left it.

- **Navigate ▸ Bookmarks.** Set Bookmark 1 to 9 was nine of the fourteen rows in
  Navigate and almost none of its use, so a listener arrowing down the menu
  walked past all nine to reach anything else. They are a submenu now. Go Back
  and Go Forward moved here from Edit, to the top, where the moving-about
  commands are.

- **Format ▸ Editor Font**, moved from View, because Notepad has kept Font under
  Format since 1985 and because the editor font is not a rich-text feature. It
  is the one row the Format menu keeps if you switch rich text off -- which
  leaves you with Notepad's Format menu, exactly.

- **Preferences and Customize Features moved to Tools**, where Windows
  applications have kept their settings since Word 6.

### Added

- **Get Help from Support (Ctrl+Alt+F2).** QuillLite shipped with no way to
  report anything: only an address printed in the About box to copy out by
  hand. Help > Get Help from Support... now opens a short form -- what kind of
  message this is, a subject, what happened, and optionally what you expected
  and how to reproduce it -- and hands the finished message to **your own mail
  program**, addressed to support@community-access.org, with QuillLite's
  version, your Windows version and your screen reader already filled in.

  Your email address is optional: you can report a problem without giving one,
  you simply cannot be replied to. Nothing leaves the machine until you send it
  yourself, and QuillLite says so out loud rather than claiming to have sent
  something it has not. On a machine with no mail program set up -- webmail
  only -- the whole message and the address go to the clipboard instead, so
  nothing typed is lost. Writing to support@community-access.org directly works
  exactly as well; there is no form anybody has to use.

  The family's old reporting item filed a **public GitHub issue** through a
  token baked into every installer, which published whatever the reporter
  mentioned -- their configuration, their employer, the document they were
  working on -- permanently and searchably, and left them no way to be answered
  without a GitHub account. That transport is gone everywhere, not just here.

- **The feature profile is in Preferences too**, at the top: the same four whole
  answers (Recommended, Everything, WordPad, Notepad) with a read-only box that
  says exactly what each would change. Customize Features is named after a
  mechanism; "make this Notepad" is a preference.

- **A spelling context menu.** With the caret in a misspelled word, the
  Applications key opens with the corrections at the top -- then Ignore Once,
  Ignore in This Document, Add to My Dictionary, Add to This Document Only, and
  the way on to More Suggestions, Check Document and Next/Previous Misspelling
  with their keys. Every row names the word. A correctly spelled word gets the
  ordinary edit menu, and that menu keeps everything Windows put in it.

- **Check for Updates (Ctrl+Alt+U).** QuillLite shipped with no way at all to
  learn that a newer version existed -- the app most likely to be somebody's
  only Quill product, and the one whose users are least likely to go looking on
  GitHub. Help ▸ Check for Updates... now opens on **what changed** in the newer
  version, with **Update** and **Close** beside it, and offers to install and
  restart for you when the download finishes. Nothing downloads until you press
  Update. It is the same key and the same window every other app in the family
  uses.

- **A quiet daily look, off by one tick.** QuillLite also checks once a day when
  it starts and says nothing unless there is something -- not while it checks,
  not when there is nothing, and not when the network is down. Settings ▸ "Look
  for updates when QuillLite starts" turns it off; Ctrl+Alt+U still works.

- **Sound works at all.** Two bugs meant no earcon in either editor had ever
  played: the sound pack was never loaded (the manager reloads only when the
  pack path *changes*, and the default path equals its own initial value), and
  the audio backend freed each sound before it could be heard. Both fixed.

- **Earcons for the ordinary moments**: app start and exit, document new, open,
  save and close, printing, cut, copy, paste, delete, undo, redo, nothing left
  to undo, abbreviation expanded, autocorrect, search found, not found and
  wrapped, and errors. These are the moments a screen reader says nothing about,
  which is what makes a sound the only feedback they can have.

- **The Sound Scheme window lists twenty-two events, not a hundred and forty-one
  -- and every one of them fires.** It used to list the whole catalogue, most of
  which QuillLite never posts.

- **Tools ▸ Sound Scheme (Ctrl+Alt+Shift+O)**: every sound QuillLite can make,
  in a list that plays each one as you arrow onto it. Per event: Play, switch it
  off, Browse for a WAV of your own, No Sound, or Use Default. Save the set as a
  scheme of your own -- an ordinary folder you can copy or send -- and Restore
  All Defaults always works, because the shipped sounds are never overwritten.
  The same window QUILL opens, over the same schemes.

- **A sound when you type a misspelling.** QuillLite had none at all: the alert
  was a line in the status bar, which on a bar nobody is watching is not an
  alert.

- **Tools ▸ Spelling ▸ Announcements (Ctrl+Alt+Shift+F7)**: twelve settings for
  how a misspelling is said. Whether the sound plays, whether the word is spoken
  too, how long before the same word is reported again, whether words are
  spelled out and after how long, and whether the letters come plainly, in the
  phonetic alphabet, or both. An example box says what your choices sound like.

- **Ctrl+F7 now spells the misspelling it lands on**, after a pause. "receive"
  and "recieve" are the same sound, so hearing the word tells you nothing; the
  letters are the answer. Press the next key and the spelling is cancelled
  unheard.

- **View ▸ Status Bar (Alt+Shift+B)** hides and shows the status bar, the way
  Notepad's has since Windows 95. Nothing is lost while it is away: Ctrl+Alt+W
  speaks the counts and Ctrl+G asks for a line. Pressing **F6** with the bar
  hidden says so rather than doing nothing -- and F6 itself is now listed in
  **Navigate ▸ Status Bar**, because going there is a move, not a setting.

- **Format ▸ Headings**, with **Heading 1 to 6** on Ctrl+Alt+1 to Ctrl+Alt+6 and
  Body Text on Ctrl+Alt+0. Line spacing moved into **Format ▸ Line Spacing** in
  the same tidy-up.

- **Tools ▸ Expand Abbreviations (Alt+Shift+A)** turns expansion off and on
  from the keyboard, with a tick showing which way it is set. Expansion is the
  one feature that acts *while you type*, so the moment you want it off is
  usually the moment it has just expanded something you meant to keep -- and a
  dialog three keystrokes away is three too many. It is the same switch as the
  Abbreviations box in Customize Features.

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

### Fixed

- **Choosing a profile in Customize Features now applies it.** It used to need a
  second press of a **Use Profile** button that nothing mentioned, so choosing
  Notepad and pressing Save kept every feature you had -- and the Format menu the
  description had just promised would be gone. Choosing applies; Custom puts the
  boxes back to how you found them; nothing is saved until Save.

- **Each profile now shows what it would do**, computed from the feature list so
  it cannot go stale, in a read-only box a screen reader can arrow through
  rather than a caption it can only read all at once.

- **Spelling for This Word (Shift+F7) and Add Word to Dictionary (Alt+F7) work
  from anywhere in the word.** They used to answer only when the caret was on
  its first character, and said "No misspelling at the cursor" everywhere else.

- **Spell check as you type had never once fired.** It asked for a word
  beginning exactly at the cursor, which typing left to right never produces --
  the cursor is always at or past the end of the word you just finished. The
  status line, the file-type exemptions and the setting all existed and none of
  them had ever run.

- **Ordinals are no longer misspellings.** "the 13th of May" reported "th" as a
  misspelling, at a position inside a number, for a word you never typed. The
  same fix covers 3D, 1080p, 500ml and 12pt.

- **A screen reader read the line above the cursor on every empty line.** Type a
  line, press Enter, and ask JAWS to read the current line: it said the line you
  had just finished instead of "blank". Not a speech bug and not a JAWS bug --
  the control was answering the question wrongly. QuillLite put the Rich Edit
  into its own plain-text mode (`EM_SETTEXTMODE` / `TM_PLAINTEXT`), and in that
  mode RICHEDIT50W does not count the position after a trailing line break as a
  line of its own: asked which line the caret was on, it named the previous one,
  and a screen reader read out what it was told. The control now stays in
  rich-text mode whatever the document is, and the plain/rich distinction lives
  where it belongs -- in the document, deciding what the Format menu allows and
  what a save writes. One consequence, deliberately: **pasting into a plain text
  document is always a plain paste**, because a plain document must not pick up
  formatting it would silently drop at the next save.

- **Page Setup and Customize Features did nothing.** Two menu items that opened
  no window and said nothing: Page Setup used `with` on the one wx dialog that
  is not a context manager, and Customize Features called a method by a name it
  does not have. Both failed inside the menu handler, where wx swallows the
  error, so there was nothing to see.

- **Ampersands showed in the Find and Replace search-mode boxes.** The three
  rows read "&Normal", "&Escapes" and "Re&gular expression" on screen and out
  loud. An ampersand is an access key in a button or a menu item and a literal
  character in a list row, and these were list rows. They are also better named
  now: "Normal text", "Special characters (	, 
)" and "Regular expression",
  because "Escapes" names the mechanism rather than the job.

- **"Entered Preferences dialog" / "Exited Preferences dialog".** QuillLite no
  longer speaks either, for any dialog. A screen reader announces a dialog by
  its title when it opens and says where focus lands when it closes; saying it
  again is the app talking over the reader.

- **The Preferences font button said only "Choose".** A button is announced on
  its own, so "Choose button" named no noun and the only way to find out what it
  chose was to press it. It is "Change Font..." now. Two access keys in that
  window were also claimed twice, so one of each pair could not be pressed.

- **Heading 5 and Heading 6 could be applied and never found again.** Both sat
  at the 11-point body size, so the ladder could not tell either from an
  ordinary paragraph: heading navigation and the headings list walked straight
  past them. They have sizes of their own now (11.5 and 10.5), which is what
  made it honest to offer all six in **Format ▸ Headings**, each on its own
  digit — Alt+O, H, 3 and Ctrl+Alt+3 are the same three.

- **Format ▸ Structure survived rich text being switched off**, offering to
  promote and demote headings in a plain text document that cannot have any.

- **All Matches and Count Occurrences refused instead of asking.** With nothing
  searched for yet they said "Search for something first", which is true and a
  dead end. They open Find now.

- **Markdown is gone from the Save As type list.** A type in a Save As box is a
  promise about what will be written, and there is no Markdown writer: picking
  it saved the same plain text under a different extension. Opening a `.md` is
  unchanged.

- **The menu bar had a "Document" item before File, and two menus called
  Window.** Both came from the MDI machinery rather than from QuillLite.
  Windows adds a maximised child's system menu to the menu bar as an untitled
  icon, which a screen reader announces as "Document", so pressing Alt landed
  on "Document" instead of File; and wxWidgets builds a *Window* menu of its own
  (Cascade, Tile, Arrange Icons) and inserted it beside the one QuillLite
  builds, so the bar said "Window" twice with no way to tell which was which.
  The system menu is gone -- along with the three unnamed minimise, restore and
  close icons at the other end -- and wx's Window menu with it. QuillLite's own
  Window menu, the one that lists your documents by number, is the one that
  stayed.

- **Format ▸ Structure survived rich text being switched off**, offering to
  promote and demote headings in a plain text document that cannot have any.

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
