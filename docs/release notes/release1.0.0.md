# QUILL 1.0.0

## The screen-reader-first writing suite, built by the people who depend on it.

*From Community Access. Free. Optional by design. Private by default. Built with you.*

QUILL is a writing, reading, and document suite for people who work by ear and by
touch. It was designed from the first line of code for blind and print-disabled
readers, writers, students, proofreaders, and braille transcribers, and for anyone
who navigates a computer with a keyboard rather than a mouse.

That is not a compatibility claim. Most software is built to be looked at, and then
made reachable afterward: a label is added, a focus order is repaired, a warning that
flashed red is given a word. QUILL starts at the other end. Every feature here begins
with the question of what you will *hear* and what your fingers will *read*, and the
visible interface is what falls out of that answer. When a feature could not be made
to work well by ear, it was redesigned until it could, or it was not shipped.

This document is the complete description of QUILL 1.0.0. It is written for someone
opening QUILL for the first time. It describes the whole product as it stands today,
not the difference between this version and the last one. Every shortcut named here
is real, every limitation is stated plainly, and nothing important is left for you to
discover by accident.

---

## What ships in 1.0.0

Three programs carry the QUILL name in this release.

**QUILL** is the editor: a complete writing and document environment covering plain
text, Markdown, HTML, rich text, Word, braille, e-books, PDFs, spreadsheets, and
more, with reading aloud, dictation, spell checking, note-taking, version history,
git and GitHub, an optional AI suite, and an extension system. It is the program most
of this document is about.

**Quill Radio** is a standalone internet radio player: a real window with its own menu
bar, its own tray icon, favorites, recording, scheduled recording, and a built-in
weather center. Nearly all of it is also available inside the editor, because both run
the same code and share the same favorites and settings, but Quill Radio opens in
seconds when you just want the radio on and do not want to load an editor to get it,
and a handful of listener-side features live only in the standalone app. Those are
named where they come up in the Quill Radio section below.

**Quill Weather** is a standalone tray application that watches the National Weather
Service for watches, warnings, and advisories at the places you care about, and speaks
them to you the moment they are issued, whether or not anything else is running.

All three are free. All three are keyboard-first. All three speak through the same
announcement service, so QUILL sounds like QUILL wherever you are in it.

### Platforms

Windows is the primary platform, with full support for JAWS, NVDA, and Narrator.
macOS is supported from the same codebase, with VoiceOver-routed announcements, a
native Cmd-based keymap, Preferences in the standard application-menu location, and
notarized, Developer-ID-signed builds. Linux and other Unix systems are not a target
for QUILL and no promises are made about them.

### How you can install it

- **Windows installer.** The ordinary choice. Installs per-user or for all machines,
  creates Start Menu entries for QUILL, Quill Radio, and Quill Weather, and offers
  optional desktop icons, file associations, and an **Add Quill to PATH** task so the
  command `quill somefile.txt` works from any terminal. All of those are opt-in
  checkboxes, unchecked by default, because your desktop and your PATH belong to you.
- **Portable ZIP.** Unpack it anywhere, including a USB stick, and run it. Everything
  QUILL stores lives in a `data` folder beside the program, so nothing is written to
  the system drive and nothing is left behind.
- **Offline Edition.** A larger installer and portable bundle that carries every
  optional component inside it, described in its own section below. It is the right
  choice for an air-gapped machine or a locked-down laptop that cannot reach the
  internet.
- **macOS.** An application bundle delivered as a `.dmg` or `.pkg`.

QUILL keeps its everyday download small by fetching bigger optional pieces only when
you reach for them: Pandoc, offline speech engines, neural voices, the braille
translation pack, OCR, portable copies of git and the GitHub CLI, and more. They all
live in one place, **Help > Download Optional Components**, with a plain-language
description and size for each, a Test button, and a Remove button. Nothing is fetched
without you asking for it.

### The first two minutes

The first launch opens a startup wizard built around a single question: what kind of
writing do you do? Your answer selects a **feature profile**, and the profile decides
how much of QUILL is switched on to begin with. The profiles are Just a Text Editor,
Writer, Markdown and Web Author, Accessibility Professional, Braille Professional,
AI-Powered Author, and Developer and Power User, plus Full QUILL for everything at
once. A live plain-English preview tells you what each one turns on before you commit.

No profile is a trap. **Alt+Shift+P** switches profiles at any time, **Manage
Individual Features** turns any single capability on or off regardless of profile, and
**Help > Why Don't I See a Feature?** answers the question directly when something you
read about here is not on your menus. If you would rather skip the wizard, Full QUILL
gives you everything and you can prune later.

### Safe Mode

**Safe Mode** is QUILL's known-good state. Start it with `--safe-mode` or by setting
`QUILL_SAFE_MODE=1`, and QUILL launches with extensions, AI, network features, watch
folders, background monitoring, indexing, themes, and session restore all switched
off. It behaves identically in a portable copy and an installed one. Use it when
something has gone wrong and you need to get to your documents, or when you want a
session that provably reaches nothing outside your machine. Throughout this document,
"off in Safe Mode" appears next to every feature that can touch a network, and it
means exactly what it says.

### Privacy, stated once

QUILL is a local program. It opens your files from your disk and writes them back to
your disk. Nothing about your documents is uploaded anywhere as a matter of course.

Every feature that reaches the internet is optional, is named as such, asks before its
first use, and is disabled in Safe Mode. That includes the AI suite, the book library,
radio streams, weather alerts, GitHub, remote file sites, update checks,
and cloud transcription. QUILL ships no API keys and adds nothing to anyone's bill; if
you use a paid AI provider, it is your account and your key. Secrets you do give QUILL
(provider keys, remote-site passwords, service tokens) go through a single hardened
store backed by the Windows Credential Manager, a DPAPI-encrypted file in portable
mode, or the macOS Keychain. A secret is never written to a settings file, a log, or a
diagnostic bundle, and signing out of a service erases everything it stored in one
step.

Crash reports and diagnostic bundles never include your document text, and they are
scrubbed for tokens and keys before they are written.

---

## How QUILL Talks to You

Before any individual feature, it is worth describing the layer underneath all of them,
because it is the part that makes the rest usable.

### One announcement service, four channels

Everything QUILL says reaches you through one shared service, and that service speaks
on four channels at once: **speech**, **braille**, **sound**, and the **status line**.

Speech goes to your screen reader through a dedicated bridge for each one, so
announcements arrive in your own voice at your own rate rather than through a second,
competing synthesizer. JAWS and NVDA have long had that treatment. Narrator now does
too: QUILL raises announcements as UI Automation notification events, the channel
Narrator supports, and separately reads the marker Windows maintains while Narrator is
running so it can never fail to detect it. On macOS, announcements are routed to
VoiceOver. When any screen reader is running, QUILL's own built-in voice stays silent
so it can never talk over you.

Braille is a first-class channel, not an afterthought. Status and informational
messages go to your braille display through Prism, JAWS, or NVDA, with nothing
truncated. An identical message repeating immediately is suppressed, and a burst of
different messages settles rather than flickering: the first writes instantly and
anything arriving in the next moment collapses to the newest, so a fast status cascade
does not shove each line off the display before you can read it. Errors are exempt and
always come through at once. Braille can never cost you speech: if the display fails,
the announcement is still spoken. Turn it off in **Preferences > Accessibility** if you
prefer.

Sound is the third channel, and it exists because a sound never talks over a screen
reader. QUILL ships a full earcon system with the synthesized Ink pack, an indentation
tone family, and pluggable custom packs. Every one of QUILL's sounds has its own on
and off switch in the **Sound Events** dialog, and a single **Toggle Sound
Notifications** command silences the lot.

The status line is the fourth, for anything you might want to go back and read.

Two commands make the whole thing inspectable. **Repeat Last Announcement** says the
last thing again. **Announcement Self-Test** sends a test message through every channel
and reports which ones actually reached you, which turns "is my braille display getting
QUILL's messages?" from a guess into an answer.

### The status bar is a control panel, not a decoration

QUILL's status bar carries cells for word count, selection, file information, spelling,
autosave, background tasks, notifications, read-aloud, the Copy Tray, the current
document format, the current section, the page indicator, the detected screen reader,
and, when it is playing, Radio. Every cell is directly activatable:
arrow to it and press Enter to act on it, or open its context menu for more. The
spelling cell opens spelling. The Format cell opens the format switcher. The Radio cell
plays and pauses. A status bar you can only look at would be worthless here, so this one
is a place you can go.

### Verbosity: how much QUILL says

Different people want radically different amounts of speech, and the same person wants
different amounts at different moments. QUILL's verbosity system has four profiles
(Beginner, Normal, Expert, and Quiet) plus **Quiet Mode** and **Meeting Mode** toggles
for the moments when you need QUILL to stop talking right now.

Underneath the profiles, announcements can be reworded. A token-and-filter system lets
you write your own phrasing for any announcement, a Preview Lab lets you hear a change
before you keep it, an Announcement History shows what QUILL has said, **Undo Verbosity
Change** backs out a setting you regret, and anti-flood collapsing keeps a busy moment
from turning into a wall of speech. Safe Mode resets verbosity to a sane default so a
misconfigured profile can never leave you deaf to QUILL.

**Spoken Echo** (**Alt+Shift+E**) replays the last twenty announcements in an arrowable,
copyable list, for the message you half-heard while your screen reader was busy.

### The keyboard is the interface

Every feature in QUILL has a menu home and a place in the command registry. There are
more than seven hundred named commands, and all of them are reachable three ways: from
the menu bar, from the Command Palette, and from a keyboard shortcut you can assign.

The menu bar is conventional and complete: File, Edit, View, Insert, Format, Navigate,
Search, Tools, AI, Audio Description Project, Window, QuillVille, and Help. That is
thirteen top-level menus in a default installation, and nothing hides in a toolbar with
no menu equivalent.

**Audio Description Project** is the one name on that list you may not have expected, so
it should not arrive as a surprise. It holds two items, **Ask ADP** and **ADP Settings**,
and it is a preview of a search built around the American Council of the Blind's Audio
Description Project: ask in ordinary language which films and series are audio described,
or what is described on television tonight, and read or hear the answer in an accessible
results list. It reaches a hosted ADP service over HTTPS when you ask it a question and
does nothing at all until then, it refuses to run in Safe Mode, and it is early enough
that it is fairly described as a preview rather than a finished feature. If you would
rather not carry the menu, turn **ADP Assistant** off in Profiles and Features and it
leaves the menu bar entirely.

The **Command Palette** finds any command by name. Multi-word queries match in any
order, so `url open` and `open url` both find **Open From URL**. A command's shortcut
is searchable, so typing `ctrl+o` finds Open. Common intent words work as aliases:
`settings` finds Preferences, `quit` finds Exit, `theme` finds dark mode. Arrowing
through the results speaks each command's shortcut along with its name, so the palette
quietly teaches you the faster route while it runs the command for you. And when a
command is unavailable, the palette says why on the row itself rather than leaving a
bare "(unavailable)" behind.

Keyboard control is deep. The **Keymap Editor** rebinds anything, with reverse lookup
("what does this key do?"), a Record Keys capture mode so you can press a chord instead
of describing it, and a diagnostics pass with a **Heal** action that finds duplicate,
orphaned, or inert bindings. Complete keybinding sets export and import as **keyboard
packs** (`.kqp`), which are validated JSON files you can share. The **Dynamic Keyboard
Reference** is generated live from your actual bindings and active profile rather than
from a hand-maintained list, and exports as semantic HTML.

Many QUILL commands live behind a prefix chord called the **QUILL Key**, so they never
collide with your screen reader's own key map. **Change QUILL Key** reassigns the prefix
for every one of those chords in a single step, warning you about conflicts and
OS-reserved combinations before it commits.

**Global Hotkeys** (**Tools > Global Hotkeys**) go one step further: system-wide
combinations that work from any application. The safety design is the point. Only a
curated allowlist can ever be bound globally: Radio play/pause, stop, mute, and volume up
and down; New Sticky Note, the Sticky Notes Browser, posting to Mastodon (which opens the
compose dialog and never auto-sends), and show/hide to the tray.
Nothing that edits a document, deletes anything, or acts invisibly can be bound, no
matter what a settings file says, because the allowlist is enforced in code and guarded
by its own test. A global press always announces its outcome, so you hear what happened
even with QUILL minimized. The default show/hide chords are **Ctrl+Alt+Shift+Q** for
QUILL, **Ctrl+Alt+Shift+R** for Quill Radio, and **Ctrl+Alt+Shift+W** for Quill
Weather, and all three are rebindable. Global hotkeys are Windows-only, because macOS
offers no equivalent; the same commands remain on menus and the palette everywhere.

### Help that answers the question you actually asked

**F1** gives per-control help. **Shift+F1** answers "What Can I Do Here?" for the
surface you are on. A context-help chord speaks the shortcuts most relevant to where
your focus is. Every command in QUILL carries a plain-language description and its
shortcut, so nothing in the palette is a bare identifier. And three discoverability
commands exist specifically for the moments when software usually goes silent: **Why
Don't I See a Feature?**, **Why Is This Unavailable?**, and the Feature Profile health
check.

---

## Writing and Editing

### The document surface

QUILL is a multi-document editor. Documents open as tabs, **Ctrl+Tab** and
**Ctrl+Shift+Tab** move between them, **Alt+1** through **Alt+0** jump directly to a
numbered document, **Ctrl+Shift+F4** closes everything but the one you are in, and the
Window menu lists them all. Recent files, save and save-all, and session restore all
behave the way you expect.

**Notebooks** collect a folder of related files into a project with entries, headings,
bookmarks, sticky notes, saved versions, and optional writing goals. **Workspace
Snapshots** save and restore an entire working environment, open documents and tabs
included, so you can put a project down and pick it up exactly as you left it.

QUILL remembers where you were. Your caret position is saved with every autosave cycle
and every workspace snapshot, and a persistent per-document bookmark returns you to
your last position when you reopen a file.

### Selection and movement

Selection is a workflow, not a drag. Structured selection commands start, extend,
complete, and reselect a previous selection, and expand or shrink it by word, sentence,
line, paragraph, or block. Starting a selection with **F8** opens with a rising two-note
gate and completing it plays the mirror image, so selection mode is always audible
rather than something you have to remember you are in.

Long-document navigation moves you between headings, paragraphs, blocks, links, lists,
tables, bookmarks, code blocks, and search results. The **Outline Navigator**
(**Ctrl+Shift+O**) presents the document's heading structure as one navigable tree.
**Go to Anything** is a single search panel across commands and headings; the
element-by-element index — links, lists, tables, block quotes, bookmarks, code
blocks — belongs to Quick Nav below. Back and Forward walk your location
history. Match Bracket, Next and Previous Token, and structure and region movement fill
in the rest.

**QUILL Quick Nav** is a browse-style cursor mode, entered from the QUILL Key, with
single-key element movement in the tradition your screen reader already taught you:
**H** for headings, **A** for links, **L** for lists, **I** for list items, **T** for
tables, **Q** for block quotes, **B** for bookmarks, **C** for the table of contents,
**P** for paragraphs, **S** for sentences, and Tab for blocks, with configurable
wrapping and a feedback mode of speech, sound, both, or nothing.

The very top and the very end of a document answer with a high ceiling tick and a low
floor thud, so hitting an edge is something you hear rather than something you infer
from silence.

### Bookmarks, four kinds

- **Named bookmarks.** Unlimited and persistent. **Set Bookmark**, **Go To Bookmark**,
  and **List Bookmarks** (**Alt+Shift+B**).
- **Named marks and a mark stack**, for the code-editor habit of setting a mark, going
  somewhere, and popping back.
- **Ten numbered quick bookmarks.** **Alt+Shift+0** through **Alt+Shift+9** set slots
  zero through nine; **Ctrl+Alt+Shift+0** through **Ctrl+Alt+Shift+9** jump to them.
  Direct chords, no mode to enter. They persist per document like named bookmarks,
  because that is what they are underneath.
- **One temporary bookmark.** **Set Temporary Bookmark** (**Ctrl+J**) drops a single
  unnamed jump point at the cursor with no dialog, and **Go to Temporary Bookmark**
  (**Ctrl+Shift+J**) returns to it. Setting it again just moves it, and it is deliberately
  forgotten when QUILL closes: it is the come-right-back-here marker, not something to
  keep. Both are on the Navigate menu.

The persistent kinds re-anchor to the text around them, so inserting or deleting above
a bookmark moves the bookmark with its sentence instead of leaving it pointing at a
line number that now means something else.

### Structured authoring

Headings, lists, links, tables, code blocks, block quotes, horizontal rules, footnotes,
and a table of contents all have insert commands, and every one of them is
**format-aware**: the same command writes Markdown in a Markdown document and HTML in
an HTML document. If a document's format is not established yet, QUILL asks once,
remembers your answer for that document, and never asks again.

Headings have direct chords (**Ctrl+Alt+1** through **Ctrl+Alt+6**), list toggles sit on
**Ctrl+Alt+B** and **Ctrl+Alt+N**, and **Alt+Shift+Up** and **Alt+Shift+Down** move a
whole heading section past its sibling. A status-bar cell reports "Section: Heading 2
(3 of 11)" so you always know where in the structure you are standing.

The **Heading Organizer** (the QUILL Key followed by **O**) is a keyboard-first view of the whole
heading tree for promoting, demoting, reordering, and renaming sections, with an
accessibility validation pass that flags skipped levels and, optionally, duplicate H1s.
**Style Headings** applies a font family, size, and alignment to the current level or to
every heading at once.

Lists get two dedicated tools. The **List Manager** (the QUILL Key followed by **L**) restructures an
existing list as a tree: move, promote, demote, add, edit, delete. The **Structured List
Studio** (**F2**) builds a new one by concept, choosing bulleted, numbered, checklist, or
definition, nesting as you go, moving whole subtrees, with a live view of the source it
is producing. In Markdown, ordinary typing does the ordinary thing: Enter continues a
list item, Enter on an empty marker exits the list, and Tab and Shift+Tab nest and
promote.

**Update Outline Numbering** writes numeric or legal-style heading numbers into the
document as literal text, removable and re-runnable, for documents that need real
section numbers rather than a rendering trick.

### Finding and changing text

The find and replace suite covers plain search, wildcard search, regular expressions,
search history, and a find-all report. **Multi Replace** runs up to four search and
replace pairs in a single pass. **Count Occurrences** speaks how many times a term
appears. **Search in Files** (**Ctrl+Shift+F**) and **Replace Across Files**
(**Ctrl+Shift+R**) work over a folder.

The **Regular Expression Helper** exists because regular expressions are the least
speakable syntax in common use. It offers ready-made presets, explains what a pattern
does in plain language, and previews it against sample text before you turn it loose on
a document.

Line-level tools round it out: sort ascending, descending, by length, numerically, or by
date; reverse; shuffle; remove duplicates; quote and unquote; and **Number Lines
(Advanced)** with a configurable start, increment, digit or Roman-numeral style,
zero-padding, suffix, and alignment.

**Sort Lines by Date** deserves its own note, because dates are written a dozen ways. It
recognizes ISO dates, slash and dot forms, and English month names, and for an ambiguous
numeric date it reads day-month order the way your region does. Lines with no
recognizable date stay together at the bottom in their original order, so nothing is
lost.

**Line Statistics** counts, totals, averages, and reports the median, mode, and standard
deviation of one number per line, for the everyday case of a column of figures in a text
file.

The **Calculator** (**Tools > Calculator**) evaluates scientific and natural-language
expressions through a safe parser that can never execute arbitrary code, and computes
sums, averages, medians, and more over selected data, a table column, or a row.

### Typing less

- **Snippets** expand a trigger word into a template with placeholders, choices,
  date and time values, and defined cursor stops. Snippet packs group them, and
  starter packs install from an ordinary accessible multi-select list.
- The **Snippet Gallery** adds parameterized templates contributed by extensions,
  each with its own prompt sequence, including a set of ready-made math formulas.
- **Abbreviations** expand short triggers into boilerplate, signatures, notes, code,
  or markup, and can be toggled off entirely.
- **Emmet-style expansion** brings the HTML and CSS shorthand grammar (children,
  siblings, climb-up, grouping, multiplication) to QUILL, along with accessible
  built-ins such as `!a11y`, `skiplink`, and `form:a11y`.
- **Smart Insert** provides built-in typed abbreviations (`qbug`, `qmeet`, `qlog`,
  `qtodo`) that expand as you type. A fifth trigger, `qbrf`, generates a BRF test
  document, which means it has to run code rather than paste fixed text, and the
  type-ahead expander deliberately never runs code in the middle of a word. So `qbrf`
  is reached the two other ways instead: **Insert > Insert BRF Test Document**, or
  typing `=brftest()` on its own line.
- **Smart text triggers** go further: type `=meeting()`, `=todo(5)`, or `=rand(3,4)`
  and QUILL inserts the generated content. The parser is deliberately strict and
  single-line, and a large insertion asks for confirmation first.
- **Word Prediction** (**Ctrl+Period**) suggests completions drawn from the words
  already in your document and from HTML and Markdown tags.

### The clipboard, expanded

The **Copy Tray** holds twelve numbered slots. Copy to a slot, paste from a slot, and
search within slots. Beneath it, the **Clip Library** keeps a rolling, searchable
history of up to two hundred copied selections, any of which can be favorited or
promoted into a tray slot.

Every tray slot and every quick bookmark plays its own note on a shared musical scale:
the Copy Tray as soft marimba taps, bookmarks as brighter chirps. After a little use,
slot seven is a pitch you simply recognize, and "copied to slot seven" stops needing to
be said at all.

The **Clipboard Collector** reaches outside QUILL. Turn it on, then copy from a browser,
an email, a terminal, or anything else, and every captured item is appended to your open
document and saved as it goes. It checks the clipboard cheaply about once a second and
touches it only when the contents have actually changed, and each distinct item is
collected exactly once.

**Magic Paste** inspects what is on the clipboard, recognizes a URL, a Markdown block, or
a base64 image, and offers you a choice of how to insert it. It ships without a default
chord, so give it one in the Keymap Editor if you want it under your fingers.

### Notes on your work

**Sticky Notes** are timestamped, searchable, and exportable. **Inline anchored notes**
(**Alt+Shift+I**) attach to a place in the text, follow your edits, reload with the
document, and have next, previous, hear, and edit commands of their own. The **Sticky
Notes Browser** is the fast way back to any of them: start typing and the list filters
live across titles and bodies, newest first; Down drops into the results; Tab reaches a
read-only preview so you can skim a whole note without opening it; Enter opens it for
editing. Give it a global hotkey and it opens from anywhere in Windows, with QUILL's
window restored first so it genuinely appears.

### Comparing documents

**Compare Mode** is a keyboard-first diff. **Ctrl+Alt+Shift+Period** and
**Ctrl+Alt+Shift+Comma** move to the next and previous difference, and
**Ctrl+Alt+Shift+D** re-announces the current one. Word-level detail and a
whitespace-sensitivity toggle are available alongside them. Differences are described in
words with character-level precision, and each kind of change has its own sound cue.
From the command line, `--diff` opens two files straight into compare mode, and
`--goto` opens a file at a position.

### Folding without losing anything

QUILL folds heading sections and fenced code blocks, and the accessibility design here
is deliberately different from every other editor's.

- **Ctrl+Alt+Shift+F** toggles the fold containing the cursor, announcing exactly what
  happened: "Folded: 14 lines under 'Chapter Two'."
- **Alt+Shift+]** and **Alt+Shift+[** move to the next and previous foldable boundary
  and announce its label, state, and line count.
- **Ctrl+Alt+Shift+L** lists every foldable region with its state and size.

Mainstream folding hides lines and makes ordinary arrow navigation skip silently over
them, which means a screen reader user cannot tell whether text was folded, deleted, or
simply passed over. QUILL never creates that ambiguity. **The document text is never
changed and normal character, word, and line navigation is never intercepted.** Fold
state exists for the four folding commands to describe and use. Arrow through a folded
region and every word is still there. Folding changes what the jump commands do; it
never makes reachable content silently unreachable.

### Macros and repetition

**Macros** record and replay a sequence of commands. **Repeat Next Command** sets a count
so the next command or macro runs that many times. **Restore Deleted Text** recovers any
of the last three blocks removed by a structured delete, for the moment when a "delete
paragraph" turns out to have been the wrong paragraph.

### Preview

The **In-App Preview** and **Side-by-Side Preview** render Markdown and HTML with
keyboard-first movement between the editor and the rendered view. From any block in the
preview, the context menu (Applications key, Shift+F10, or right-click) offers **Go to
this location in the editor**, which puts your caret on that block's source line. It
opens a menu rather than firing an action, which is the behavior screen-reader users
expect from that key. A separate browser preview renders the document as a page, with
MathJax for equations.

### Insert Emoji

QUILL already has Insert Special Character for when you know the code point you want.
Emoji are the opposite problem: you do not know the code point, you may not remember the
exact name, and you cannot recognize one from a grid of small pictures. Every mainstream
emoji picker is built around exactly that grid, which makes the entire category of
feature unusable without sight. Insert Emoji is built the other way around.

**Insert > Insert Emoji** (**Alt+Period**) opens on every standard emoji Unicode
currently defines, 3,781 of them, current as of Unicode's 16.0 emoji release, in the
nine categories Unicode itself uses:

| Category | Emoji |
| --- | --- |
| People and Body | 2,261 |
| Flags | 270 |
| Objects | 264 |
| Symbols | 224 |
| Travel and Places | 218 |
| Smileys and Emotion | 169 |
| Animals and Nature | 159 |
| Food and Drink | 131 |
| Activities | 85 |

People and Body includes every skin-tone and gesture variant Unicode defines as its own
standalone emoji, which is why it dwarfs the others.

There are two ways in. **Search** live-filters as you type and matches in order of
confidence: the emoji character itself if you paste one, a legacy typed alias like `:)`
or `<3`, the official Unicode name or one of its keywords, and finally a match inside the
emoji's written description, so a half-remembered word like "melting" or "puddle" can
still find the right result. **Category** is the browse path for exploring rather than
searching.

Whichever way you arrive, arrowing through results updates a live description pane with
the category and subgroup, the official name, the keywords, any typed alias, and, the
part that makes this usable at all, a real one-to-two-sentence description of what the
emoji actually looks like: colors, shape, expression, pose. Two extra entries sit above
Unicode's nine groups: **Favorites**, which you curate, and **Recent**, which fills
itself with the last thirty emoji you actually inserted.

Every one of those descriptions is text QUILL wrote for this feature, generated ahead of
time from Unicode's own names, categories, and keywords rather than scraped from another
picker's website. The whole catalogue ships as a single bundled file, and using the
picker makes no network connection at all, in Safe Mode or anywhere else.

### Equations

**Insert Equation** takes a LaTeX or MathML equation as text and places it at your cursor
with the right delimiters, inline or as its own block. Selecting an equation you already
wrote reopens it for editing with the delimiters stripped. Math AutoCorrect-style
shortcuts (`\alpha`, `\sqrt`) work while you type. **Explore Equation Structure** steps
through the parts of an equation (numerator, exponent, radicand) instead of reading it as
one undifferentiated string.

Typing math as text is the accessible route: keyboard-only, reviewable character by
character, and readable by screen readers that speak math. The preview and HTML export
render it through MathJax, and Word export writes real, editable Word equation objects
that round-trip back to text when you reopen the file. With the optional MathCAT engine
installed, "read this part aloud" speaks math the way NVDA does.

This feature was contributed by @salorajan.

---

## Spelling, Language, and Words

**F7** runs the full guided Spelling Review over the document: Change, Change All,
Ignore Once, Ignore All, Add to Dictionary, and Undo Last. **Ctrl+R** inside the dialog
reads the whole sentence around the current misspelling aloud, so you can judge a
correction in context without leaving the review to go find the word.

**Alt+F7** is the focused version: **Spell Check Word** checks only the word under the
cursor. If it is correct, QUILL says so and gives you back your place. If not, a compact
list offers the suggestions, Add to Dictionary, and Ignore.

Two ranked views exist for documents where the same mistake happens over and over, such
as rough OCR or a systematic autocorrect failure. **Ctrl+Shift+L** opens a misspelling
list ordered by how often each word recurs, with the count in each entry ("teh (Ln 12,
Col 4, 8 occurrences)"). **Alt+Shift+F7** opens the complete F7 review in that same
frequency order, and choosing Change All on the first item immediately recalculates the
ranking so the next-largest group of errors rises to the top. **Alt+Shift+L** keeps the
plain document-order list for anyone who prefers to work from the beginning.

With spell check as you type enabled, finishing an unrecognized word plays a soft,
distinct spelling sound from your sound pack rather than a bare system beep. A sound
rather than speech is deliberate: it never talks over your screen reader. The live alert
also has judgment. Words inside web addresses, email addresses, Markdown inline code, and
fenced code blocks do not alert, because those regions are wall-to-wall "misspellings"
that a sighted reader filters out with a glance. The full F7 review still covers the whole
document; only the ambient alert holds back.

An in-editor **thesaurus** is available when its data is installed. **Proofread before
publish** can run a spelling pass automatically on save, on save-as, or on the text of a
Mastodon post before it goes out.

**Set Document Language** pins the language of an unsaved buffer or an unusual file
extension, which drives what Ctrl+B produces, what comment syntax is used, and how the
heading, table, and list tools behave. Automatic detection is available in hint, prompt,
or automatic modes.

QUILL's display language can be changed in-app under **Tools > Writing and Language**.
Italian is the first shipped display language beyond English, covering menus, dialogs,
and spoken messages.

---

## Reading and Speech

### Reading aloud

**Read Aloud** speaks the document, a section, or a selection, with start, pause, stop,
and voice selection all on commands you can bind. It strips Markdown punctuation as it
reads, so you hear the words rather than a recital of hash marks and asterisks, and it
does the same for exported audio. A text cleanup pass fixes typography and reads phone
numbers, email addresses, and URLs the way a person would say them.

The voices available to it are:

- **Windows SAPI 5** voices, including every language you have installed.
- **DECtalk**, for the people who have been reading with it for thirty years.
- **eSpeak-NG**, with its very wide multilingual data.
- **Piper**, a fast local neural engine, including Italian.
- **Kokoro**, a higher-quality local neural engine, covering English plus Spanish,
  French, Hindi, Italian, and Brazilian Portuguese.
- The **macOS system voice**, backed by the same engine VoiceOver uses.
- **Cloud voices** by bring-your-own-key: OpenAI, Google Gemini, and ElevenLabs, each
  with a cost estimate shown before anything is spent, and MP3 export.

Every voice previews before you commit to it, and the default engine can be set right
from the Download Optional Components list when you install one.

The **SSML Builder** composes emphasis, pauses, say-as instructions, phonemes, and
prosody, and plays the result natively on SAPI 5 and eSpeak-NG. **Manage Pronunciations**
keeps global and per-project pronunciation dictionaries with live preview, for the names
and terms every synthesizer gets wrong.

**Read the document aloud in your browser** is an experimental alternative that builds a
self-contained, accessible reader page using the browser's own voices, including Edge's
Online (Natural) voices, section by section, with a Pause that remembers your position.

### Turning documents into audio

**Audiobook and Batch Speech** exports a whole folder of documents to audio in one run.
It produces chaptered output with real MP3 chapter markers, applies ACX loudness
normalization, can rotate through several voices round-robin, and offers a dry run that
tells you what it would do before it does it. A Cancel button (and Escape) stops a run
cleanly: the file currently being synthesized finishes normally, so you never end up with
a half-written audio file, and the run stops before starting the next one. The
diagnostics log mirrors the same chunk-by-chunk progress the dialog shows. WAV output
lands in an **Audio Output** subfolder beside the source document rather than cluttering
the folder itself, and a recursive export gives each subfolder its own.

**Export to Translated Speech Audio** translates and then narrates into the languages you
choose, using any configured AI provider or a local LibreTranslate instance, with a
combined cost estimate up front.

Closing QUILL while one of these exports is running asks first, and offers **Window >
Send to System Tray** as a way to keep it running quietly instead. Routine background work (search
and replace, dictation, downloads) does not trigger the warning; only genuinely
hard-to-redo jobs do.

### Speech to text

QUILL transcribes on your own machine. The bundled engine is **whisper.cpp**, with
**Faster Whisper** (GPU-accelerated) and **Vosk** (low-resource, CPU-only) as
alternatives. **NVIDIA Nemotron** (Nemotron Speech Streaming EN) is a fourth option:
NVIDIA's 600M streaming model, run int8 through sherpa-onnx, the same runtime Visual
Studio Code uses for its own on-device dictation. It is English-only, runs on the CPU
with no GPU and no PyTorch, and is an optional install (the `quill[nemotron]` extra,
or the engine's entry in **Help > Download Optional Components**); its model is
fetched checksum-pinned from QUILL's own release assets and is off in Safe Mode.
**Manage Speech Models** checks your actual RAM and GPU, flags a model
that is too big for your machine, recommends the best fit, and downloads with a
checksum-pinned, cancelable progress dialog.

- **Locked Dictation** is the reliable path for speaking into a document:
  **Ctrl+F9** starts and stops, **Ctrl+Shift+F9** pauses and resumes, **Alt+F9** speaks
  the current state. Everything you dictate arrives as a single undoable edit.
- A **dictation safety net** saves your audio to a recovery folder before transcription
  runs, and a History and Review window lets you insert, copy, or discard a recovered
  recording. A dictation session is never lost because a transcription failed.
- **Transcribe Audio or Video** handles a file rather than a microphone, producing plain
  text, Markdown, or HTML, speaker-labeled when diarization is installed, across a wide
  range of formats with ffmpeg fetched on demand.
- **Generate Captions** writes timestamped SRT or VTT subtitle files.
- A **Watch Folder** automates the whole thing: drop audio or video in, and QUILL
  transcribes it to text, SRT, VTT, or Markdown without being asked again.
- **Cloud transcription** is available opt-in through OpenAI Whisper, Groq Whisper, or
  ElevenLabs Scribe (which does speaker diarization), for when local accuracy is not
  enough and you have decided the tradeoff is worth it.

### Voice commands

**Voice Command (Offline)** drives QUILL hands-free through a curated set of safe
commands recognized entirely on your device. **Voice Conversation Mode** chains follow-up
commands, and the **"Hey QUILL"** wake word makes it always-on when you want it to be.
Every voice command also has an ordinary key, so voice is always a faster path and never
the only one.

### Teaching dictation your words

Every voice has its own vocabulary, and dictation should not fight yours. QUILL reads a
small plain file called **`dictation.md`** in your data folder, with three optional
sections:

- **Vocabulary** lists the names, jargon, and acronyms you use, so the recognizer writes
  "wxPython" and "GitHub" rather than sounding them out.
- **Replacements** are spoken-to-written fixes you write yourself, one per line. "New
  line" can insert an actual line break; "get hub" can become GitHub.
- **Commands** add your own spoken phrases for existing actions, still bound by the same
  safe-command allowlist that governs all of voice.

It applies everywhere dictation transcribes, and it does nothing at all until you decide
to write one.

### Performance

Speech models are large. A setting unloads idle models after a number of minutes you
choose, and a **low-resource mode** (which enables itself automatically on a very
low-memory machine) keeps QUILL usable on modest hardware.

---

## Braille

QUILL treats braille as a document format and a reading medium in its own right, not as a
rendering of print.

Turn it on through the startup wizard's **Braille Professional** profile, through **Help
> Enable Braille Mode**, or through Manage Individual Features.

### Braille files, byte for byte

QUILL opens and saves `.brf`, `.brl`, `.pef`, and `.ueb` files while **preserving the
bytes**: form feeds, line endings, and layout come back out exactly as they went in. A
round trip produces an identical file. For a transcriber, that is the whole ballgame.

A braille status cell reports what a transcriber actually needs to know, in one place:
`BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7`. A single detailed-status command speaks
all of it at once. When you reopen a braille file, QUILL returns you to the exact cursor
position with spoken page, line, and cell detail.

### The braille display starts in cell 1

Text in QUILL begins in **braille cell 1**, not cell 2, eliminating the long-standing
offset that RichEdit controls share with Microsoft Word. When text is selected, the
display shows **dots 7-8**, restoring the tactile selection feedback braille readers
expect.

Two checkboxes under **Preferences > Braille** control this, and both are checked by
default:

- **Fix braille cell alignment and selection dots (recommended)**, which enables the
  system-edit emulation that produces the behavior above.
- **Hide editor border (required for braille cell alignment)**, because testing showed
  the visible editor border itself shifts braille output away from cell 1. The borderless
  frame is a functional part of the correction, not a visual preference. Unchecking it
  warns you clearly that braille cell alignment will break.

Both settings are Windows-only, and both ask you to restart QUILL so the change applies
everywhere.

**Report Editor Surface** is a single command that speaks everything a braille bug report
needs: the active editor surface, its native window class, whether the system-edit
braille fix is applied, whether the border is hidden, and whether braille output is live
and through which backend. Nothing from your document is included. If braille ever looks
wrong, run this first and paste what it says into a report; "braille starts in cell 2"
plus that one sentence is a report that can be investigated immediately.

### Translation, without being quizzed

Back-translating a braille file elsewhere requires that you already know which code it uses,
and picking wrong produces garbage with no explanation.

**Back-Translate to Text (Auto-Detect Code)** removes that burden. QUILL samples the
document or your selection, back-translates it through every English braille code it
knows, scores how much each result reads like real English, and announces the winner:
"Detected UEB Grade 2 (contracted)." The candidates are UEB Grade 2, UEB Grade 1,
Standard American Grade 2 (EBAE, legacy), Standard American Grade 1 (EBAE, legacy), and
8-dot computer braille. You learn what your file is instead of being asked.

**Convert BRF File to Document** is the one-command path from a braille file on disk to
something you can read, edit, and share: pick any `.brf` or `.brl`, and QUILL detects the
code, back-translates the whole file, and opens the result as a clearly labeled draft.
From there, Save As exports it to Markdown, HTML, Word, or plain text. Braille is also a
first-class source in the general converter: **File > Convert File** accepts `.brf` and
`.brl` in the same picker as every other document type.

Forward translation runs through the optional **QUILL Braille Pack**, whose Translation
menu offers UEB Grade 1 and Grade 2, Standard American English (Legacy), and an
auto-populated More Languages section covering dozens of languages. Translation works
from every kind of install, including a source checkout, because the worker uses the
pack's own bundled engine when a Python binding is not present. Large files translate
correctly regardless of size, because the document travels to the worker over standard
input rather than as a command-line argument.

### Proofreading braille

- **Print-page and running-head detection** identifies print page numbers and running
  heads from BRF separators and margin numbers, and labels its own confidence rather than
  asserting.
- **Print-page navigation**: Go to Print Page, Next and Previous Print Page Change,
  Announce Running Head, and Include or Omit Running Head in the status readout.
- **Proofreading tracking**: mark pages as proofed or needing review, attach notes, hear
  a spoken progress summary, jump to the next unfinished page, and export a proofing
  report.
- **Layout validation** flags over-long lines and pages, missing page breaks, mixed line
  endings, stray non-braille characters, numbering gaps, and running-head mismatches,
  with next-warning and previous-warning navigation.
- **Read Layout Metrics**, **Go to Longest Line or Page**, and **Remove Trailing Spaces**
  pinpoint and clear page-width violations directly.
- **Page Tools** insert and remove page breaks, recalculate the page map, and normalize
  line endings.

---

## Documents and Formats

### What QUILL can open

Plain text, Markdown, CommonMark, GitHub-flavored Markdown, HTML, CSV and TSV, Word
(`.docx`), RTF, OpenDocument, EPUB, PowerPoint, spreadsheets, PDF, LaTeX, JSON, XML,
TOML, YAML, Jupyter notebooks, SQLite databases, Apple Pages extraction, braille formats,
and images through OCR. Pandoc, installed on demand, extends that list further in both
directions, and every complex extraction comes with a **Document Intake Report** telling
you honestly how well it went.

PDF and spreadsheet readers ship with every install, so a brand-new copy of QUILL opens a
PDF or an `.xlsx` immediately with nothing to fetch first. Word files read through
python-docx by default, which means headings arrive as headings, lists as lists, and
tables as tables, in document order, rather than as one flat line per paragraph.

A few specific reading improvements are worth naming because they are the difference
between a document you can use and one you cannot:

- **PDF text repair on open** removes hyphenation across line breaks, reflows paragraphs,
  collapses letter-spaced titles, and repairs ligatures.
- **Password-protected PDFs** simply open: QUILL asks for the password, reads the file,
  and never stores, logs, or writes the password anywhere. A wrong password says so and
  lets you try again.
- **A PDF's own bookmarks** (the outline you would see in Adobe Reader's bookmarks pane)
  import into QUILL's Bookmarks Manager the first time you open the file, and respect any
  renaming or deleting you do afterward.
- **EPUB heading navigation** renders chapter-internal headings inline so single-key
  heading navigation walks them, and infers headings from structure when a chapter has
  none.
- **PowerPoint import** turns slide titles into headings and bullet levels into nested
  lists, and brings tables and speaker notes along.

Your documents open as your documents. There is no engine banner or extraction header
prepended to your text; everything QUILL knows about how a file was read lives in the
intake report and the spoken open announcement.

### Rich editing

QUILL's editing buffer is clean plain text. Formatting lives beside it as hidden codes.
That is what makes search, spell check, AI commands, read aloud, bookmarks, inline notes,
and braille all work identically no matter how formatted a document is.

Open an `.rtf` file and the formatting is genuinely there, not simulated. Bold is bold.
Headings carry real sizes. **Ctrl+B** applies true rich-text bold. **Describe Formatting
at Cursor** reads the live state of the document: "Arial, 14 point, bold, centered."

The rule underneath is that **QUILL speaks the language of the document you are editing**.
In Markdown, Ctrl+B wraps the selection in `**`. In HTML, it produces `<strong>`. In RTF
or Word, it applies real formatting. One command, one intention, the correct result for
the current format.

A `.docx` file opens for genuine rich editing and saves back as a real Word document, and
QUILL is honest about the limits of that:

- A clean Word file containing nothing QUILL cannot carry opens directly in rich mode.
- A Word file containing unsupported features names those features specifically and asks
  how you want to proceed: open for reading and plain editing (the safe default), edit as
  rich text knowing exactly what cannot survive a save, or edit a copy and leave the
  original untouched.
- The first rich save over a flagged original automatically creates a timestamped backup
  beside it.

QUILL never silently rewrites a complex Word file and asks you to trust that everything
survived.

Plain text stays plain. The first time you use a formatting command in a `.txt` file,
QUILL asks once whether to treat it as Markdown, convert it to rich text, or keep it
plain, and remembers your answer rather than asking again.

On macOS, rich mode is ready on first launch with nothing to install. If the rich-text
bridge is ever unavailable on a particular system, the document opens as editable text
with a clear explanation in the status area rather than failing.

**Illuminations** solve the opposite problem. When a file must remain a genuinely plain
`.txt`, a `.txt.illumination` sidecar stores the formatting (bold, italic, font, color,
alignment) beside it, and reopening the file restores it exactly. The plain file stays
plain for every other tool that reads it.

### The Document Format switcher

**Format > Document Format** moves the current document between plain text, Markdown,
HTML, Rich Text, and Word, mid-session, without opening a different program. It is also
on the Command Palette and on the **Format** cell of the status bar.

The conversion is meaningful rather than cosmetic. Moving a Markdown draft into rich text
turns `# headings` into real headings. Moving a rich document into Markdown first warns
you by name about anything that will not survive.

A format change never silently overwrites the old file. The next save proposes a filename
with the correct extension, so `notes.md` becomes `notes.rtf` and the file on disk always
tells the truth about what is inside it.

### Reveal Codes

QUILL keeps formatting codes hidden so the editing buffer stays clean. **Reveal Codes**
(**Alt+F3**, or **View > Reveal Codes**) is the on-demand companion that makes every one
of them visible and speakable. It is the WordPerfect feature many people still miss,
rebuilt screen-reader-first.

The default **Flowed** view reads like your document with the scaffolding shown inline
(`[Bold On]Hello[Bold Off]`), and the caret moves the way it does in the editor. Left and
Right walk one character at a time through text but step over a whole code as a single
unit, so one press crosses `[Bold On]` and you hear "bold on" rather than a spelled-out
bracket. Ctrl+Left and Ctrl+Right move by word; Up and Down move by line and read it;
Home, End, Ctrl+Home, and Ctrl+End go to the ends.

The pane is a single voice while you navigate. The region is named once when you enter,
and after that you hear only the character, word, line, or code you landed on,
identically in JAWS and NVDA. **Reveal Codes: Speak Codes Aloud** is an opt-in setting for
anyone who wants QUILL to speak each code as well.

Press **F2** on text sitting between a pair of codes to edit that run in place. The pane
restricts you to that region, Enter applies the change back into the document, Escape
cancels, and the surrounding codes are untouched. A run containing a tab or a nested code
edits as one unit.

The two carets stay locked together however you move: arrows, word jumps, Home and End,
Page Up and Down, a mouse click, or a jump from Find. A **Structured** list view, one
labelled item per code, remains available for scanning, and your view and verbosity
choices persist between sessions. **Describe Formatting at Cursor** and **Describe
Character at Cursor** (Unicode name, code point, category, and notes about invisible
characters) answer the same questions without opening the pane at all.

### Converting between formats

**File > Convert File** converts to any format Pandoc supports, with a choice of Convert
File or Convert and Open, and it remembers your last folder and format. The **Pandoc
Conversion Wizard** walks the same ground in steps. The **Batch Conversion wizard** does
a whole folder at once through four pages (intro and tool probe, folder and options,
format and profile, review and start) with live per-file progress rows.

Seven built-in conversion profiles cover the common destinations: Clean Word Document,
Accessible HTML Page, EPUB Book, GitHub README, Print PDF, Instructor Handout, and Plain
Text for Screen Readers.

The Tier-1 import and export set is Markdown, CommonMark, GitHub-flavored Markdown, HTML,
DOCX, ODT, RTF, plain text, CSV and TSV, EPUB, and LaTeX, plus PDF export.

QUILL has also written down honestly what carries over between formats, in the
"What carries over between formats" section of the User Guide. The short version: the
common formatting (headings, emphasis, links, lists, and tables) travels between Markdown,
HTML, and Word; numbered lists keep their starting number; a hyperlink survives a Word
round trip as a real Word hyperlink; a table saved to Word becomes a genuine editable Word
table with a repeating header row your screen reader announces as column headers. A few
things are format-specific: a table saved to RTF is written as readable pipe-text rather
than a native RTF table, Word-embedded images are not pulled into the text, and plain text
never carries formatting, by design.

**DAISY 2.02 text-only talking book export** (**File > Export > DAISY Talking Book**)
produces a navigable-by-heading talking book from any document.

### Optical character recognition

**Import/Convert Document (OCR)** routes Word, PowerPoint, Excel, HTML, EPUB, PDF, and
image files through a free local converter first, then falls back to on-device OCR
(Tesseract) for scanned or image-only PDFs, reporting confidence per page. **Review Last
OCR Result** presents a checklist of the low-confidence lines with jump-to-page, and
**Delete OCR Temporary Files** cleans up afterward. OCR is also available directly on an
image file, on the clipboard, and on a region of the screen.

When on-device OCR genuinely cannot rescue a document, a consent-gated,
bring-your-own-key cloud escalation is available. It is never automatic.

### Headers, footers, and printing

The **Header and Footer Builder** offers named presets or a custom mix of tokens (title,
filename, date, page number), a different first page, and numeric or Roman numbering.
These are real parts of the saved document, not a print-time overlay: save as `.docx` and
the header becomes a genuine Word header with a live page-number field that Word keeps
renumbering; save as `.rtf` and QUILL writes the equivalent native RTF groups. A custom
starting page number and a different first page both carry through. An empty
specification changes nothing, and a header can never be the reason a save fails.

**Print Studio** (**File > Print Studio**) is an accessible print preview that is spoken
and textual rather than a picture of a page, with all, odd, or even pages, reverse order,
and skip-first-page options.

A **page indicator** on the status bar reports exact page numbers for PDFs and an
estimated page count (with a tunable words-per-page figure) for text, Markdown, and Word.

### Text encoding

Legacy text is a real, ongoing accessibility problem, and QUILL takes it seriously:

- **Show Non-ASCII Characters** reports every one, says whether it is convertible to
  Latin-1 or Windows-1252, and jumps to it in the source.
- **Convert Non-ASCII to HTML Entities** and **Decode HTML Entities**.
- **Re-encode As** UTF-8, UTF-8 with BOM, Latin-1, Windows-1252, or ASCII.
- **Analyze and Save Using Minimum Required Encoding**.
- **Remove Email Quote Markers**, **Strip Low or High ASCII Characters**, **Convert to Hex
  Dump**, OEM (DOS) to ANSI conversion in both directions, and conversion or stripping of
  line-drawing characters.
- RTF files declare their code page, and QUILL reads it, so Cyrillic and other
  non-Western RTF decodes correctly instead of arriving as noise.
- JSON, XML, TOML, YAML, and notebook files that begin with a byte order mark open
  normally and keep their original line endings.

### Version history

**File > Restore Previous Version** keeps a plain-language history of a document. Restore
takes you back (snapshotting the current text first, so restoring is itself undoable), or
Open as Copy leaves the current file alone. Identical content is deduplicated, and older
entries age out on a tiered retention schedule rather than growing forever. Inside a
notebook, **Manage Versions** does the same for named versions, and tells you plainly
when there are none yet instead of showing a blank list.

An **extracted-text overwrite guard** stops **Ctrl+S** on a document derived from a PDF,
EPUB, PowerPoint, or spreadsheet from destroying the binary original, and opens Save As
instead.

### Citations

QUILL formats citations in MLA 9, Chicago 17, and APA 7 from a labelled form, producing an
in-text citation, a bibliography entry, or both, and lets you select whether Markdown
citations use footnotes or a bibliography.

### Remote files

QUILL opens and saves files over **FTP**, **SFTP**, **WebDAV**, **S3**, **HTTPS**, and
**GitHub**, with a Site Manager for your saved sites and an SSH Quick Connect for the
one-off case. SSH host-key checking defaults to rejecting an unknown key; automatically
adding one requires an explicit trust-on-first-use opt-in, which is a setting you turn on
deliberately rather than a prompt you dismiss.

### Publishing, read-only in 1.0

If you run the **Full Quill** profile, the File menu carries a **Publish** submenu with
three items: **Publishing Connections**, **Verify Current Publishing Connection**, and
**Browse Publishing Content**. Together they let you save a WordPress site account, check
that the credentials still work, and browse that site's posts and pages and open one into
QUILL as an ordinary document to read or edit locally.

That is the whole of it in 1.0, and the boundary is deliberate. The half that sends
content back to a site (create a draft, publish, update a remote item, schedule a post) is
a separate feature that is locked off in this release and cannot be switched on from
Settings. It is written and it is under review; it is not in your hands yet, and we would
rather say so than ship a Publish button whose behavior we are not ready to stand behind.
Site credentials are stored in the Windows credential vault rather than in a settings
file, and every call the read-only half makes goes through QUILL's audited network layer.
Other profiles leave the Publish submenu off the File menu entirely; you can light it for
yourself in Profiles and Features, under Publishing (Read-Only).

---

## The AI Suite

QUILL's AI is entirely optional, entirely opt-in, and silent until invited. If you never
set it up, nothing here bothers you and no menu nags you. If you do set it up, it is
yours: your provider, your account, your key, or a model running on your own machine with
nothing leaving it. QUILL bundles no keys and takes no cut.

Everything lives under a top-level **AI** menu, and everything is disabled in Safe Mode.

### Setting it up

The **AI Setup Wizard** asks one question at a time, offers a Basic and an Advanced mode,
and ends with a Test Connection that either works or tells you specifically why it did
not. Supported providers are Ollama (local or cloud), OpenAI, Claude, Google Gemini,
OpenRouter, and any custom OpenAI-compatible endpoint.

There is a genuinely free path, and the wizard shows it rather than hiding it behind the
paid options. Run **Ollama** locally and everything runs on your own machine at no cost.
Or choose OpenRouter, where the wizard preselects a free model and labels every free
model as "Free" in the list. Each provider that needs a key has a **Get API key** button
that takes you to the right page. If you point QUILL at Ollama, it verifies that a server
actually answers before treating it as configured, and the API key field greys out for
providers that do not need one.

Ollama does not have to be on this machine. An **Ollama server address** field on the
Connect step drives verification, the model list, and the finish step, so a LAN or
self-hosted server is a real, working choice. And you never need a terminal to get a
model: the Model step shows which recommended models are already installed and offers a
**Pull model** button on the rest, with live download progress.

On-device AI is a first-class option, not a fallback: Apple Foundation Models on macOS,
and llama.cpp with GGUF models on Windows.

The **AI Hub** is the settings home, and it has eight tabs: Provider, Engines, On-Device,
Audio Services, Services, Instructions, Sessions, and Advanced. Provider and On-Device
hold the connection settings; **Engines** is where the agent harnesses described under
Agents below are signed into and configured; **Audio Services** covers transcription and
speech; **Services** is the document conversion and OCR page, which states plainly that
the free on-device converter and the local OCR engine run first and that the one paid
cloud service is bring-your-own-key and asks consent before every upload; **Instructions**
holds your standing writing instructions; **Sessions** lists your saved AI sessions; and
**Advanced** holds the consent and diagnostic settings. The Hub probes a running Ollama
server automatically and shows each model's real capabilities (vision, tools) rather than
guessing from a name.

### Ask Quill

**Ask Quill** is the conversational surface: a single context-aware conversation that
knows what document you are in. It can answer questions, and it can propose changes, but
it can never make one.

That is the discipline underneath every AI feature in QUILL: **the AI proposes, you
dispose.** Every edit an AI suggests stops at a review dialog. Nothing touches your
document until you agree, and when you do, the whole set of changes lands as a single
undo step.

The review is built to be judged by ear. Changes are announced as what they are:
"Changed 'quick' to 'rapid' at line 3." Adjacent edits merge into one phrase instead of
several fragments. The details pane shows the sentence before and the sentence after each
change, so you can judge a one-word edit with the same context a sighted reviewer gets
from a highlight, with the complete old and new lines still available below. Two
deliberate limits keep it honest: a genuine rewrite with many scattered edits is presented
as whole lines, because forty spoken word pairs is worse than hearing the lines; and
spacing-only changes are never announced as word edits.

### Writing help

- **Rewrite**, **Summarize**, **Expand**, **Continue**, and **Fix Grammar** work with or
  without a selection, falling back to the paragraph or the whole document.
- **Check Grammar with AI** and **AI Spell Check** produce a structured list of
  issues with the original phrasing, the proposed fix, and an explanation of why. With no
  AI configured, they fall back to the lexical spell checker rather than failing.
- The **AI Thesaurus** (**Ctrl+Alt+Shift+H**) gives synonyms with usage notes about
  register and connotation, using the sentence around your cursor as context
  automatically.
- **Generate Table of Contents** builds one from the document's structure.
- **AI Translate Document or Selection** offers a target-language picker driven by your
  provider, with a local LibreTranslate fallback that keeps the whole job on your machine.
- The **Prompt Library** holds named one-click tools: Generate FAQs, Draft a Speech,
  Summary Email, Social Media Post, Step-by-Step Instructions, Paraphrase, and the
  summarize, rewrite, tone, and expand presets. Each runs over your selection or the whole
  document, and you can edit any of them or switch it off.
- **Custom Instructions** override the system prompt per task across the built-in tasks,
  so the assistant can be told once how you want it to behave rather than every time.
- **Train Writing Style** conditions the assistant on your own writing.
- **Suggest Document Metadata** proposes a title, a summary, topic tags, and a category,
  and hands every decision back to you field by field: you hear the field, what it says
  now, and what the AI proposes, and choose Accept, Accept and Next, Skip, or just copy
  the value. If a field already has content, QUILL asks before replacing it and the safe
  answer is the default. Nothing is written until you choose Apply Accepted.

### Reading help

- **Document Q&A** is a multi-turn session grounded in the open document, navigable by
  heading, with middle-trimming for documents too large to send whole. When a document
  has to be trimmed, QUILL tells you the working size rather than quietly answering from
  less than you sent.
- **Improve Reading Order** repairs a document whose text arrives in the wrong order: a
  two-column PDF that extracts as one scrambled stream, a page with sidebars, lines out of
  sequence. It merges columns into one flow, joins mid-sentence line breaks, and infers
  headings, lists, and tables, while preserving your exact wording, because it never
  summarizes or invents. A confirmation names the provider, its host, and the approximate
  size before anything is sent, the result opens as a new unsaved document leaving your
  original untouched, and it refuses documents over a page limit you control so a huge or
  costly send cannot happen by accident. With no cloud provider configured, it runs on the
  bundled on-device model instead, entirely on your computer.
- **Describe Image with AI** carries a library of twelve evaluated description prompt
  styles, all editable, with a "try a different prompt" action and a manager for your own.
  HEIC and HEIF images are supported.
- The **Insert Image** dialog will not let you insert an image without either real alt
  text or an explicit "decorative" choice, and **Describe Image at Cursor** reports the
  filename and alt text or flags it as MISSING. With a vision model connected, one button
  drafts alt text for you to review and edit; you always approve what goes in, and the
  button is simply absent in Safe Mode. Inserting into HTML, you can also set width and
  height so the page does not jump as the image loads, keep the image responsive, and add
  a caption properly tied to it with `<figure>` and `<figcaption>`.

### Agents

QUILL can run multi-step agentic tasks, and it lets you choose the engine that runs them:
**GitHub Copilot** through device-code sign-in, the **Claude Agent SDK** or the **OpenAI
Agents SDK** through your existing API keys, or QUILL's own built-in **Native** engine.
An in-app dialog pastes, saves, and removes those keys.

Vendor agents run text-only and their edits go through the same previewed, undoable
approval as everything else. Agentic writing tasks (rewrite, summarize, expand, generate
a table of contents) run in the background with cancellation and a reviewable step log.

Sixteen named agent personas ship ready to run: Accessibility Editor, Citation
and Link Fixer, Code Doctor, Data Cleaner, GitHub Maintainer, Markdown Publisher, Math
Tutor, Meeting Notes to Actions, Plain-Language Rewriter, PRD Architect, QUILL Concierge,
Release Notes Builder, Researcher, Reviewer, Summarizer, and Writing Companion. The **AI
Library** manages prompts, skills, and agents in one place, with a promotion path from a
prompt you wrote once, to a reusable skill, to a full agent.

### The Listening Companion

The Listening Companion turns a recording into something you can use. Transcribe it, with
optional translation and speaker identification, and then generate Meeting Minutes, Action
Items, an Executive Summary, Interview or Study Notes, a Q&A, a Follow-Up Email, Key
Quotes, a Decisions Log, or simply a clean draft. An **Action Builder** with no syntax to
learn lets you describe your own output rather than choosing from a list, and watch-folder
automation runs the whole pipeline on anything you drop in.

### Honesty guarantees

Three commitments hold across every AI feature:

- **QUILL never quietly changes what is answering you.** If a chat has to start on a
  different engine than the one you configured, because your provider was unreachable, it
  says so the moment the chat opens.
- **Fallback offers work in both directions, and never happen by themselves.** A failed
  cloud call points you at your on-device model; a failed on-device model points you at
  the cloud provider you have configured, while telling you plainly that switching would
  send your text to the cloud. QUILL never switches for you.
- **Connection problems are diagnosed, not generalized.** QUILL distinguishes a rejected
  key from a key with no model access, from rate limiting, from a model still warming up,
  from a local server that is not running, and reports the actual HTTP status. If a saved
  key cannot be decrypted on this device (a portable copy moved to a new machine), QUILL
  asks you to re-enter it rather than failing obscurely.

Prompt caching routes system prompts through each provider's own caching mechanism where
one exists, which cuts token cost on repeated work.

---

## Accessible Vault

The Accessible Vault is QUILL's linked-notes system: a personal knowledge base built out
of ordinary plain-text files in an ordinary folder. There is no proprietary database and
no graph picture to look at, because a graph picture is exactly the wrong interface for
this.

Open a vault on a folder of notes and QUILL indexes it and speaks a summary: "Vault name:
312 notes, 480 links."

- **Wikilinks.** Write `[[Another Note]]`. **Follow Wikilink** jumps to the exact heading
  or block, offers to create the note if it does not exist, and disambiguates when a name
  is ambiguous.
- **Show Backlinks** answers "what links here" as a spoken list, each entry read with the
  sentence that contains the mention, and Enter opens that note at the mention itself.
- **Note Neighborhood** shows what sits around the current note in the link graph, as a
  list rather than a picture.
- **Go to Note** is a type-ahead jump box that narrows by title and speaks the match count
  as you type.
- **Search Vault** does phrase and word search with regex and whole-word options, and
  reads results as note, line, and sentence.
- **Show Tags** presents a spoken tag pane with per-tag counts and nested tag rollup.
- **Unlinked Mentions** finds places where a note's name appears without a link.
- **Embeds** pull one note into another: `![[Note]]`, `![[Note#Heading]]`, and
  `![[Note#^block]]`, with **Speak Embed at Cursor** and **Resolve Embed Inline**.
- **Insert Template** fills `{{date}}`, `{{time}}`, and `{{title}}`, prompts for
  `{{prompt:Question}}`, and leaves your cursor at `{{cursor}}`.
- **Daily notes**: Open Today's Note, and Previous and Next Daily Note.
- **Export Vault as Website** produces a self-contained accessible site, one page per
  note, with links and embeds resolved and an index page.
- **Sync Vault** commits, pulls, and pushes over your own git remote, and when the same
  file changed in both places it lists the conflicts by name and stops rather than
  overwriting anything.

---

## Story Studio

Story Studio is a binder for a long work: a novel, a thesis, a manual.

**Tools > Story Studio** opens a keyboard-navigable tree with a Manuscript branch (parts,
chapters, and scenes derived from your headings) alongside groups for Characters, Places,
Plot threads, Research, and Brainstorm. An accessible details form records a character's
role, goal, motivation, and arc, a plot thread's status, and tags, all saved as ordinary
front matter in the file itself.

**Compile manuscript** stitches every manuscript file together in order into one document,
which then goes out through the normal File > Export path to Word, EPUB, PDF, or anything
else.

The project format is deliberately boring: an ordinary folder of plain-text files plus one
small companion file recording order and groupings. Your book is never trapped inside
QUILL.

---

## Tables and CSV

**Table Studio** (experimental) opens a CSV or TSV file, or builds a new table, in a
keyboard-accessible grid designed for screen readers rather than for the eye. Left and
Right speak the column heading as you move, **F2** edits a cell, Alt with the arrow keys
moves an entire row or column, and Ctrl+Insert adds a row. An optional native UIA provider
gives NVDA and JAWS richer cell events where it is installed.

The result inserts into your document as a headed Markdown or HTML table, or saves back
out as CSV.

Inside a document, table navigation commands move by cell: next, previous, above, below,
first, last, row start, and row end. Word tables opened for rich editing appear as
accessible tables you can read and jump to with single-key navigation rather than being
silently dropped.

---

## The Book Library

**The Book Library**, at **Tools > Media > Book Library**, is one search box across free,
accessible reading sources:

- **Project Gutenberg**, through the Gutendex API.
- **Standard Ebooks** and **Feedbooks**, through their public OPDS catalogues.
- **Google Books**.
- **NLS BARD**, the catalogue of the National Library Service for the Blind and Print
  Disabled at the Library of Congress.

Search by title, author, or subject, with results in a single-select, fully keyboard- and
screen-reader-friendly list, a find-in-results box, and a spoken status line. For
Gutenberg, Standard Ebooks, and Feedbooks, a chosen title opens directly in QUILL's reader
as plain text or EPUB.

BARD works differently, and QUILL is explicit about why. BARD catalogue entries are
listings, not files: borrowing a title requires an eligible BARD patron account, which you
set up and use on the BARD website. Every BARD result therefore offers **Open in BARD**,
which opens that title's official Library of Congress page in your browser, where you sign
in and download. QUILL never asks for or stores your BARD credentials. The search itself
uses BARD's free public API, with nothing sent but the words you searched for.

Like every library source, it is disabled in Safe Mode.

---

## Git and GitHub

Version control is one of the least accessible corners of computing: punctuation-heavy
text, visually arranged differences, and interactive tools that assume you can see two
columns at once. QUILL is a text editor that a screen reader user already trusts, which
makes it the right place to fix that.

### Files on GitHub

QUILL opens files directly from a GitHub repository, browses a repository's tree, and
saves a file back, with your token held in the system credential store and a first-use
consent prompt. The repository field accepts `owner/repo`, a pasted `github.com` URL, or a
`git@github.com:` remote.

### The Items viewer

The GitHub Items viewer browses issues, pull requests, branches, commits, workflows, and
workflow runs in an accessible list.

- **Pinned repositories** hold a short, intentional list of the ones you use most, so you
  are not retyping `owner/repo`. **Favorites** (**Ctrl+D**) bookmark an individual issue,
  pull request, branch, or release, across repositories, and stay entirely on your machine.
- **Full GitHub search syntax** (**Ctrl+F**) accepts a real query such as
  `label:bug is:open crash` scoped to the loaded repository.
- **Quick filter** (**Ctrl+Shift+F**) is the other kind of narrowing: it filters the rows
  already loaded, live as you type, with no network round trip. It never steals focus from
  the box you are typing in, and it stays silent while you type, speaking the result count
  only once you stop, because re-announcing "12 items" on every keystroke would fight your
  screen reader's own character echo.
- **Local git awareness** fills in the repository automatically when the document you are
  editing lives in a clone whose origin points at GitHub.
- **View Upstream** loads a fork's parent repository in place.
- **Columns** chooses which fields appear for the current view and remembers it.

**Diff** on a pull request browses its changed files, and rather than a wall of plus and
minus signs it routes each file through the same comparison engine **Compare Documents**
uses, presenting a numbered walk through meaningful changes: "Difference 2 of 5. Text
changed at line 41." A newly added file is read as its content, a deleted file is announced
as deleted, and a binary or oversized file falls back honestly to its change counts.
**Compare** on a branch does the same between two branches, and needs no sign-in because it
never writes.

**Summarize** hands a hundred-comment thread to your AI and gets back a plain-prose
summary of what it is about, where it stands, what is unresolved, and the apparent next
step. It uses the same AI connection, privacy, and consent gates as everything else, and
nothing is sent until you press it.

**Batch** operates on a multi-selection: close, reopen, or label several items at once. It
is the deliberate exception to the viewer's read-only foundation, so the fence is explicit:
batch actions require a signed-in account, anonymous viewing stays fully read-only, the
confirmation names the exact action and the exact item numbers, and a partial failure tells
you which items failed and why while letting the rest complete.

**Actions** covers the per-item write operations: New Issue, New Pull Request, Merge Pull
Request, Delete Branch, Re-run Workflow, View Artifacts, Reply to Thread, Edit This
Comment, and Delete This Comment. The comment actions build on **Alt+N** and **Alt+P**
comment navigation: move to the comment, then act on that one.

**View Artifacts** lists a workflow run's build artifacts with name, size, and expiry, and
downloads one or all of them to a folder you choose, with a cancelable progress dialog and
an overwrite prompt. That download needed a deliberate decision rather than a default one:
GitHub's artifact link redirects to a short-lived signed URL on another host, and your
GitHub token must never travel there. QUILL blocks the automatic redirect, reads the target
itself, and makes exactly one more request to that address with no authorization header
attached. Your token only ever goes to github.com.

### Administering a repository

**Tools > Git and GitHub > GitHub** is a command center for the operations that would otherwise send you to a
browser: **Create Repository** (with an immediate offer to synchronize a local folder, so
you go from nothing to a folder pushing to GitHub without opening a browser), **Fork
Repository**, **Rename Repository**, **Change Repository Visibility**, **Change Default
Branch**, **Delete Branch**, **Configure Branch Protection**, and **Commit Multiple Files**
(several local files in one atomic commit, which is deliberately different from Save to
GitHub's single open document).

Alongside them: **Browse Organization Repositories**, **Create Release** (with GitHub's
auto-generated notes from merged pull requests as an option, published or left as a draft),
**Dispatch Workflow**, **Notifications** (a genuine inbox across all repositories, not just
the loaded one), and **Security Alerts** for open Dependabot alerts.

None of the write commands works anonymously, and when you are not signed in, QUILL offers
to start sign-in from the point of need rather than refusing and leaving you to find another
route. Four high-consequence actions need more than a Yes/No: renaming a repository,
changing visibility, deleting a branch, and merging a pull request each require you to
retype the exact name or number. Every other write action uses a confirmation that names
precisely what is about to change.

Two more commands run through your own installed `gh` command-line tool: **Ask Copilot for a
Command** describes what you are trying to do and gets a suggested git or `gh` command back,
and **Explain a Command** takes a command you do not recognize and explains it in plain
language. Codespaces management is there too, and because Codespaces consume real compute
and storage minutes, its confirmation says so explicitly rather than using the generic "this
changes something on GitHub" wording.

If you do not have `git` or `gh` installed, both are available from **Help > Download
Optional Components**: a portable copy of Git for Windows and the GitHub CLI for Windows and
macOS, each checksum-verified. QUILL always prefers a copy already on your system.

Some things are deliberately absent, and the reasons are worth stating: **Discussions**
needs a hand-written GraphQL field selection that would ship as a guess without live
validation; **Projects (v2)** has no supported library path (only the classic Projects API
GitHub is sunsetting); **Packages** likewise; and **transferring a repository to another
owner** has no wrapped method. They remain candidates for when they can be implemented and
verified responsibly.

### Local git

This part is not about GitHub. It is about `git` itself, and it may be the capability in
QUILL we are proudest of.

**Resolve Conflicts.** Anyone who has used git has met the conflict markers `<<<<<<<`,
`=======`, and `>>>>>>>`, which a screen reader encounters as line noise unless you
manually reconstruct the surrounding structure by hand. QUILL parses each conflicted file
into its real parts and walks you through the conflicts one at a time: "Conflict 1 of 3:
your version says X; their version says Y." For each one you choose to keep yours, keep
theirs, keep both, or type a different replacement. The process continues through every
conflict in every affected file, with the decision explicit each time.

**Interactive Rebase.** `git rebase -i` normally opens a generated text file and expects
you to reorder lines and change words like `pick`, `squash`, `reword`, and `drop` without
breaking the syntax. QUILL replaces that with a real dialog: one commit per row, an action
chosen from a dropdown, and Move Up and Move Down to reorder. Underneath, it uses the same
mechanism graphical git clients use, standing in as git's sequence editor and returning the
structured list your dialog built. If a step causes a conflict, the guided conflict resolver
opens automatically and the rebase continues afterward.

**The rest of the toolkit.** **Uncommitted Changes** stages and unstages through an
accessible comparison rather than a raw diff. **Switch Branch** guards against uncommitted
work following you unexpectedly. **Stash Changes** and **Manage Stashes** are guided.
**Who Wrote This Line** makes `git blame` useful by speaking the answer for the current
line. **Start Bisect** and **End Bisect** turn `git bisect` into a plain conversation about
whether the current version is good or bad.

**Worktrees.** Here is a problem that almost never gets named, because most people never
notice it. When you switch branches the ordinary way, git rewrites every file in the folder.
The names stay the same. The paths stay the same. The contents become something else. If you
can see the screen, the text changes in front of you and you know instantly. If you are
reading with a screen reader, nothing tells you anything: the paragraph under your review
cursor is now a paragraph from a different branch, in a file that still calls itself the file
you opened, and you keep reading words that no longer belong to what you thought you were
reading.

A worktree is the structural fix rather than a warning message. It is a second folder
attached to the same repository with a different branch checked out inside it. One history,
one set of branches, two folders. Nothing under your cursor ever changes, because the two
never share a file. Switching context becomes "open a different file", something you choose
and hear yourself doing, instead of "this file is now a different file", which happens to you
without a sound.

**Tools > Git and GitHub > Local Git > Worktrees** announces the count as it opens, and every row is a whole
sentence you hear once and understand ("Linked worktree at D:\usb\quill-spike, on branch
spike, locked: on a USB drive") rather than four narrow columns you would have to arrow
across. **New Worktree** asks where the folder goes and which branch it holds, or creates a
brand-new branch with an optional starting point, and its folder field takes whatever you
actually paste. QUILL checks before it runs git, so a mistake is a sentence you hear rather
than an error you decode: the folder already has files in it, the folder is inside the
repository, or that branch is already open in another worktree, and in that last case QUILL
tells you which folder has it. **Open in QUILL** opens the same document you are reading from
the worktree you picked, and offers a file picker pointed at the right folder if that file
does not exist on that branch. **Remove** deletes the folder, never the branch, defaults to
No, and if git refuses because of uncommitted changes it passes that on in plain language and
asks a second, separate question rather than forcing it. **Lock** and **Unlock** protect a
worktree on a USB drive or network share that git would otherwise think had vanished, with a
reason you can record and hear later. **Prune** clears records for folders that really are
gone and says which ones it tidied, or that nothing needed doing.

Throughout local git, raw git error output is never read at you. Every message is a finished
sentence written to be spoken. None of these commands contacts GitHub or any network service.

### Synchronizing a folder

**Tools > Git and GitHub > GitHub > Sync Folder with GitHub** works with any folder: notes, a writing project, source
code, a whole body of work. If it is already a git repository with a remote, QUILL commits,
pulls, and pushes in the background. If it is not, QUILL explains exactly what it proposes
("this runs `git init`, then adds the remote repository you provide as origin") and changes
nothing until you approve. If the same file changed in both places, it lists the conflicts by
name and stops; it never resolves a conflict by silently overwriting.

QUILL uses your installed git and the credentials git already knows, an SSH key or your
system's git credential manager. It creates no second set of credentials. The behavior mirrors
a normal `git push` from a terminal.

There is a second, simpler kind of sync that needs no git at all. QUILL's data location can be
pointed at a folder already synchronized by OneDrive, Dropbox, Google Drive, or iCloud, and
your settings, snippets, dictionaries, and keymap then travel with that folder between
machines. QUILL writes ordinary files and the provider's client handles transport. The setup
wizard explains this and names the limitation plainly: do not run QUILL on two machines at
once against the same synchronized data folder, because there is no cross-device conflict
resolution.

We considered building a full QUILL synchronization service, with accounts and hosted storage
and an engine of our own, and chose not to build a new cloud merely because we could. Folder
sync and git already solve the essential problem.

Everything across these sections is taught end to end in
[Tutorial 8: GitHub inside QUILL](../tutorials/08-github-inside-quill.md).

---

## Quill Radio

Quill Radio is a full internet radio player. It comes two ways. Inside the editor it lives
on **Tools > Media**, where the radio commands sit directly on that menu rather than in a
submenu of their own: Browse Stations, Add Custom Station, Find Streams from a Website,
Manage Favorites, Play Last Station, What's Playing, the transport and volume controls, and
the whole recording group. Separately, it is a standalone application with its own window,
menu bar, and tray icon, for the times you want the radio on without loading an editor.

They are the same code and the same settings: a station you favorite in one is there in the
other. What the standalone app adds is the listener-side furniture that an editor has no
sensible place for, and this document flags each of those as it comes up. They are: **Sound
Enhancements** and the **radio output device** chooser (in the editor, Sound Enhancements is
reachable from the Command Palette but is not on any menu, and the output device is a saved
setting with no chooser); the **Station Details** command on a favorite; **back up and
restore**; **Customize Features**; and **Start Quill Radio with Windows**.

### Finding something to listen to

**Browse Stations** searches [RadioBrowser](https://api.radio-browser.info), a free,
keyless, community-run directory, with a name box and optional narrowing by tag or genre
and by country. A unified **Find Stations** search spans RadioBrowser, iHeart, TuneIn, and
SomaFM at once, and can also take a website address directly.

The browse tree also carries sources that need no search at all. There are twelve branches
on it, in this order:

- **Favorites**, your own saved stations in nested folders you arrange, with search,
  reordering, and a scoped "find in this folder".
- **Popular Stations**, the directory's most-listened stations, for when you want something
  on and do not much mind what.
- **Radio Browser (by Genre)**, the community directory browsed as genre folders rather
  than searched.
- **Weather / NOAA**, an authoritative directory of real NWR transmitters browsable and
  searchable by state, SAME code, or call sign, with a three-tier offline fallback so it
  works even when the directory cannot be refreshed.
- **ACB Media**, the American Council of the Blind's ten Live365 stations, bundled directly
  into QUILL so they are there before any network call, because the mission overlap is
  direct.
- **NFB Radio**, the National Federation of the Blind's NFB-NEWSLINE Radio Network stream,
  bundled the same way and for the same reason: one long-lived speech and talk mount, there
  before any network call.
- **Radio Reading Services**, twenty vetted audio-reading services for blind and
  print-disabled listeners, bundled offline with a live refresh.
- **SomaFM**, the listener-supported independent channel family, fetched live from
  somafm.com and listed as its own branch.
- **TuneIn**, browsed through TuneIn's own folder tree rather than flattened into a list.
- **iHeart**, browsable by genre and A to Z.
- **Community M3U (Music Genres)**, a community-maintained playlist catalogue organized by
  musical genre.
- **Xiph / Icecast Directory**, the open Icecast directory, also by genre.

Whatever you select, a read-only details pane reports what QUILL knows about it: country,
language, tags, codec and bitrate, community vote count, homepage, and the stream address,
so you know what you are about to hear before you press Play. **Station Details** gives the
same readout for any favorite.

Not every station is in a directory. **Add Custom Station** takes any stream link with an
optional homepage and tags, and a **Test** button plays it right there before you save.
**Find Streams from a Website** takes an address, fetches that one page, and lists every
stream-shaped link it finds (an `<audio>` tag, a `.pls` or `.m3u` playlist, a Shoutcast or
Icecast mount point) with a plain-language reason for each, a Test to preview, and **Use
This Link** to carry the guessed name and address into Add Custom Station. This deliberately
reads one page rather than embedding a browser, because station pages almost always list
their stream as a plain link and a screen-reader-native results list beats navigating an
embedded browser for this particular job.

Two link formats get special handling. **Live365** station pages, player links, and even a
bare station id are recognized and rewritten to the real stream address, as a pure text
rewrite with no network lookup and nothing sent anywhere; a URL that is not Live365 passes
through untouched. **YouTube** links, including YouTube Live, behave like any other station:
paste one into Add Custom Station and you get a station with the same player, favorites,
Record Now, and scheduled recording. What is saved is the page link rather than the stream,
because YouTube stream addresses expire within hours, so QUILL finds the audio again every
time the station plays or records. That lookup runs through **yt-dlp**, which QUILL never
bundles: it installs on demand after a one-time notice the first time you add a YouTube
station, and that notice includes the plain reminder to record only what you have the right
to record. You are asked when you add the station rather than when it plays, so a recording
that fires at 3 a.m. is never the first time QUILL reaches YouTube. It is off entirely in
Safe Mode. And because finding a stream is a network round trip, it happens off the interface
thread: you hear "Connecting" immediately, the window never freezes, and if you press Stop or
choose a different station mid-lookup, the one you chose last is the one that plays.

### Listening

One player outlives every dialog. Closing the station browser, the custom-station dialog, or
the link finder never stops the music, which is what makes "listen while you keep writing"
actually work.

Playback controls cover Play and Pause, Stop, Play Last Station, Jump to Live, Rewind 30
seconds and Forward 30 seconds, volume up and down, mute, and a volume boost, in both the
editor and the standalone app. Two more are standalone-app menu items: **Sound
Enhancements**, a three-band equalizer and compressor that can be set once for everything or
remembered per station, and the **radio output device** chooser, which sends the music to a
different device than your screen reader. Radio's volume is its own, separate from your Windows system
volume and separate from your screen reader's speech volume, so you can set the music quietly
under your speech without touching either. Your volume is remembered between sessions.

**Tools > Media > Sleep Timer**, in the editor, ends a listening session gently: choose a
preset or type a custom duration, and the radio fades to silence rather than cutting off
mid-sentence, then stops, with your volume restored to what it was so pressing play later
is not a quiet surprise.

**Announce Track Titles** can be toggled. **What's Playing** speaks the current track;
**What's Playing (Review and Copy)** opens a read-only window you can arrow through and copy
from; **Copy What's Playing** puts it on the clipboard. A stream that carries no titles says
so rather than going silent on you.

Inside the editor, a **Radio** status-bar cell appears once something is playing, showing the
station and state, with play and pause on Enter and a context menu offering Stop, Mute, a
Favorite Stations quick-switch, and a way back into the browser. Minimize to the tray and the
same controls follow, along with a live now-playing line. Direct chords reach it without
leaving the editor at all, and every one of them is remappable.

The standalone app opens onto a real working surface rather than an empty window: focus starts
in your Favorite stations list, so you arrow to a station and press Enter and you are
listening. Its menu bar carries a Station menu (Browse Stations, Add Custom Station, Find
Streams from a Website, and your favorites listed right in the menu for one-keystroke
switching), a Playback menu with a live now-playing line, and a Record menu. Its Browse,
Favorites, Schedule, and Weather windows are modeless frames sharing one menu bar, one Window
menu, and Ctrl+Tab cycling between them. The **QuillVille** menu's **Open Quill** is there for
the moment you decide you do want the full editor after all.

### Recording

With FFmpeg installed (an on-demand optional component), **Record Now** captures whatever is
playing straight to a file, from the menu, the status-bar cell, or the tray. **Schedule
Recording** queues one for later: once, daily, or weekly at a chosen time. **Recording
Settings** covers format, bitrate, destination folder, a filename pattern with `{station}`, `{date}`, and `{time}` tokens, an optional temporary folder for
in-progress files (moved atomically into place when finished), and a maximum-length safety cap
so a recording you forgot about cannot quietly fill your disk.

There are five recording formats. **MP3** and **OGG Vorbis** re-encode to a lossy file and
are the two that use the bitrate setting. **FLAC** and **WAV** re-encode losslessly.
**Raw stream** is the fifth and the one worth knowing about: it copies the broadcast
through to disk exactly as it was sent, with no re-encoding at all, so nothing is lost and
nothing is added, and QUILL picks the file extension from the stream's own codec. Choose
Raw stream when you are archiving; the bitrate control hides itself, because it would do
nothing.

Recording is built to survive the real world. A dropped connection reconnects rather than
ending the recording. Filenames are made unique rather than overwriting. A fatal error is
distinguished from a transient one. Scheduled recordings fire anywhere within their window
rather than only at the exact second. A recording interrupted by a restart offers to resume,
and a recording that was missed while the app was closed is reported at the next launch.
Stopping a recording asks FFmpeg to finish cleanly rather than killing it, so the file's
container closes properly. The recordings list updates in place with live elapsed time, and
finished recordings land in a visible default folder rather than somewhere you have to hunt
for.

### Weather inside Radio

The standalone Quill Radio app carries the full Weather menu described in the next section,
so the app you leave running all day is also the one watching for a tornado warning. This is
one of the two places that menu exists (the other is Quill Weather itself); the editor does
not have it.

### Housekeeping

- **Wake-Up Timer** starts a station at a time you choose. It is in both the editor and the
  standalone app.
- **Remove All** clears every favorite in one step, behind a confirmation and with an
  undoable backup written first. It lives in the Favorites manager, so it is in both.

The rest of this list is the standalone app only:

- **Start Quill Radio with Windows** registers a per-user autostart entry, and then tells you
  what actually took, because a locked-down registry can refuse silently.
- **Back up and restore** writes a portable `.qrbackup` archive of favorites, settings, wake
  timer, and recording schedule (and optionally your recordings), and reads it back on
  another machine.
- **Customize Features** turns whole menu areas (Recording, Weather) on or off, so the app can
  be exactly as small as you want it.
- Radio writes a configurable log for when something needs diagnosing.

---

## Quill Weather

Quill Weather watches the United States National Weather Service and tells you when something
is happening where you are. It runs as a standalone tray application, and the same Weather
menu is carried by Quill Radio, so if you already leave the radio running you already have
the whole of what follows. The QUILL editor does not have a Weather menu; weather is the
companion apps' job, and running Quill Weather in the tray beside the editor is how you get
it there.

**Weather Now** (**Ctrl+Shift+W**) opens the Weather Center: current conditions, an
hour-by-hour forecast of configurable length with temperature, conditions, and chance of
precipitation, and a moon almanac (phase, illumination, moonrise, and moonset) computed locally
with no extra service and no extra dependency. The current local time at the searched location
leads the readout, because "what time is it there" is usually the first thing you want to know
about somewhere else. **Quick Weather** (**Ctrl+Shift+Q**) is the short spoken version.

**Weather Guardian** is the part that matters most. It monitors your location in the background
for watches, warnings, and advisories, speaks them, and interrupts for genuinely severe events
rather than waiting politely behind whatever else is being said. During severe weather it
tightens its polling (down to the National Weather Service's own 30-second floor) and relaxes
again afterward. A Windows toast accompanies the announcement. An "already told you" check is
shared between the live watch and the background check, so the same warning is never announced
twice.

The **alert sounder** is fully under your control: on or off, your own `.wav` file with a
preview button, and a repeat count. **Test Alert** plays the entire alert experience through
from beginning to end, clearly marked as a test, changing no state and requiring no network, so
you can find out how it will sound at 3 a.m. at a time of your choosing.

**Active Alerts** lists what is currently in effect. **Add Location** adds a place to watch.
**Start and Stop Weather Monitoring** (**Ctrl+Shift+M**) and **Pause and Resume Alert Checks**
give you direct control over whether it is running. **Listen to Local NOAA Weather Radio**
tunes the nearest transmitter, and **Update NOAA Weather Radio Directory** refreshes that list.

The standalone app can **start with Windows**, start minimized to the tray, and keep monitoring
when you close its window. It can also register a **per-user Windows Scheduled Task** so alert
checking happens with no process running at all, delivering a Windows toast your screen reader
announces. **Ctrl+Alt+Shift+W** shows and hides it from anywhere.

---

## Quillins: extending QUILL

Quillins are QUILL's extensions. The model is capability-and-consent: a Quillin declares in its
manifest exactly what it needs (read text, write text, use the clipboard, fetch a URL, read or
write files, change core settings), and every action in those categories requires consent at
the moment it happens, not once at install time. A network-using Quillin must also declare the
specific hosts it may reach.

Quillins can be written declaratively, or as out-of-process handlers in Python or Node.js.
There is a `@quill/api` package for JavaScript authors and a scaffold tool that generates a
manifest, an extension file, a README, and a license to start from.

What a Quillin can contribute: commands and menu items, settings pages (declared in the
manifest as control type, label, default, and validation, rendered as accessible tabbed
preferences), status-bar cells, snippet-gallery templates, abbreviations, insert triggers,
subscriptions to fourteen document and lifecycle events with per-subscription condition
filters, timer events for scheduled background work, file-type contributions that fire on a
matching extension, category labels, and dependency declarations.

A set of Quillins ships bundled and enabled, including Math Equations (contributed by Robert
Danaraj), BRF Tools, Smart Insert, Journal Stamp, Document Guardian, Status Scribe, Insert
Tools, Insert Character, Line Tools, Text Tools, Markdown Helpers, and a Node.js word-count
example that exists to prove the JavaScript path works end to end.

**Third-party Quillins are disabled by default** in a standard 1.0.0 build. A default install
never loads extension code it did not ship with. When you do enable them, the **Quillins
Manager** handles enable, disable, reload, and remove, and the menu bar rebuilds itself
immediately afterward so a newly enabled Quillin's contributions appear without a restart.

The **Quillin Hub** is the community store. **Submit to Quillin Hub** validates your artifact
locally before any network contact happens. Published artifacts are cryptographically signed,
the Hub fails closed on an unsigned submission, and the storefront shows a spoken "Signed by"
badge so you can hear who published something before installing it.

One honest limitation: Node.js-based Quillins still require an internet connection the first
time they are used, even in the Offline Edition. It is a known and tracked gap, not an oversight.

---

## The Offline Edition

QUILL normally keeps its everyday installer small by downloading its bigger optional pieces on
demand. The **Offline Edition** inverts that: every optional component ships inside the
installer and the portable bundle up front, so QUILL is fully functional the moment it is
installed with no internet connection ever needed. It is the right choice for an air-gapped
machine, a locked-down work laptop, or anywhere your first login cannot reach the internet.

"Offline" here means what it says, and the claim has been audited rather than assumed:

- **Kokoro** neural voices install and speak entirely from local files, engine included.
- **whisper.cpp**, the default speech-to-text engine, ships with its starter model present.
  This mattered most: whisper.cpp is not merely an engine you might choose later, it is the
  path QUILL reaches for automatically, and an offline edition that could not transcribe until
  it downloaded a model was not genuinely offline.
- **Faster Whisper**, **Vosk**, and **MP3 chapter-marker support** all install with no network
  connection, down to the supporting libraries that other packagings leave to be fetched from
  the internet even when the main package is local.
- **Piper** arrives with its engine, integrity verification against a pinned fingerprint at both
  build and install time, and a ready-to-speak starter voice (Lessac, US English, medium
  quality). Additional voices remain available from the online catalogue whenever you do have a
  connection and want them.

**Help > Download Optional Components** tells the truth about the difference: in the Offline
Edition each component shows as already **Bundled**, or as **Not included** for the handful the
offline build does not carry, rather than offering a Download button with nothing left to fetch.

The regular, smaller installer and portable download are unchanged and remain the default for
everyone else.

The one remaining gap is the Node.js Quillin runtime noted above.

---

## Reliability, Recovery, and Safety

Trust is the product. A writing tool that loses work, or that silently does something other
than what it said, is worse than no writing tool at all, and that is doubly true when you cannot
glance at the screen to catch it.

### Your work is protected

- **Autosave** snapshots your documents continuously, including their formatting, so crash
  recovery restores bold and headings rather than only the words. Snapshots are written
  atomically (write to a temporary file, flush, rename) and always in UTF-8, so a document in an
  unusual encoding can never break a save.
- **Document saves are atomic** by the same mechanism. A power failure mid-save cannot leave you
  with half a file.
- **Persistent undo** survives a session.
- **Restore Backup** and **Restore Previous Version** cover the slower kinds of mistake.
- **If your screen reader stops, your work is already safe.** Losing a screen reader mid-session
  is one of the most disorienting things that can happen at a computer. QUILL watches for it, and
  if the screen reader it detected goes away and stays away past a grace check (so restarting
  JAWS or NVDA never triggers this), it immediately snapshots every open document and then tells
  you what happened using whatever can still talk: another screen reader if one is running, or
  QUILL's own built-in voice. A note lands in Notifications too, so the explanation is waiting
  even if you missed the announcement. QUILL keeps running throughout, and announces when it
  hears your screen reader come back.

### When something goes wrong

- An unhandled crash shows a **plain Win32 message box** that screen readers can read, even when
  the toolkit itself is down and could not draw a normal dialog.
- **Crash recovery is offered only when there is evidence of a crash**: an error, a critical, or
  a traceback in the log. An inconclusive exit, such as a forced shutdown or a killed process,
  does not produce a recovery dialog, because there is nothing to diagnose. The autosave snapshot
  is kept either way; the only thing that changes is whether QUILL asks.
- A **recovery diff preview** shows a read-only snippet of what would be restored before you
  restore it.
- **Crash reports** bundle diagnostics with the actual traceback and the specific log lines that
  triggered the offer, so a report is self-explanatory to whoever reads it. They never include
  document content, and they are scrubbed for GitHub tokens, OpenAI keys, AWS credentials, Slack
  tokens, and long alphanumeric secrets before they are written.
- **Every internal error type carries a short support code** in the form `[QUILL-...]`, which
  rides along in crash reports and turns "it said something went wrong" into a specific,
  searchable fact. A build gate enforces that no new error type ships without one.
- **Errors end with what to do next.** A coded error increasingly finishes with the concrete
  action: "Install Pandoc from Help > Download Optional Components to convert this format", or
  "Check the address, credentials, and connection under File > Manage Remote Sites." Voice and
  component downloads, extension problems, and remote transfers over SSH, FTP, S3, and WebDAV all
  do this. A soft "What to try next" toggle appears on file-open, export, and import failures.
- **Corrupt configuration cannot stop you working.** A damaged `settings.json` or `keymap.json`
  is quarantined and defaults are used, rather than crashing at launch. Settings are
  schema-versioned with delta-based migration and backups of the previous shape.

### Safety by construction

- **Destructive confirmations always default to No.** Pressing Enter out of habit on "Delete
  this?" is never the destructive answer, across every dialog in every app in the family. A build
  gate makes sure no future dialog can ship with a destructive Yes-default.
- **Every modal dialog goes through one hardened path** that guarantees the keyboard contract,
  and an automated inventory audits compliance across hundreds of dialogs.
- **Every outbound network call site is inventoried** by a build gate. A new network call cannot
  be added without an explicit entry and explicit consent.
- **The Python snippet sandbox** blocks dunder attribute access statically, allows only a
  restricted set of imports, and caps time and memory.
- **External engines are allowlisted** by executable name before any input or output happens.
- **Update manifests are signature-verified**, and an unconfigured or placeholder signature is
  rejected rather than trusted. Update discovery is HTTPS-only against an allowlist of trusted
  hosts. A portable copy receives a ZIP (applied by mirroring, excluding your `data` folder, with
  zip-slip and zip-bomb guards) and an installed copy receives the installer; QUILL never hands a
  Windows user a macOS download.
- **A signed safety-advisory system** can remotely disable one specific misbehaving feature, in a
  way that is announced, reversible, honored offline, and overridable locally. A menu item
  disabled by an advisory explains itself right there in the menu rather than being mysteriously
  greyed out.
### Resetting and moving

**Reset Everything to Factory Defaults** puts settings, shortcuts, menu customizations, and the
feature profile back behind one confirmation. **Import data from a previous QUILL install** brings
settings, shortcuts, and documents forward from an older copy. **Work Personas** (**Tools > Work
Personas**) bundle a feature profile, a working folder, favorite files, and a keymap profile under
a name, launchable with `quill --persona NAME` or from a generated shortcut, for the people whose
day has two or three genuinely different modes in it.

---

## Everyday details that add up

Some things are too small for a section of their own and too useful to leave out.

- **Favorite folders.** Recent folders answer "what did I open lately?" Favorite folders answer
  the more useful question, "what must always be easy to reach?" **Ctrl+Alt+Shift+A** adds the
  current document's folder, **Ctrl+Alt+Shift+R** removes one, and **Ctrl+Alt+Shift+O** opens the
  Quick Open dialog scoped to them. All three are also under **File > Favorite Folders**.
- **Quick Open** puts focus straight in a search box and filters live and case-insensitively
  across every favorite folder as you type, naming which folder each result came from. By default
  it searches only the top level of each folder, which keeps results instant and reinforces the
  curated nature of the list; **Include subfolders** goes deeper, capped so a very large tree
  cannot freeze the dialog.
- **Paste any path and it works.** The file-open path field accepts a path with the quotes File
  Explorer wrapped around it, a `file://` link with invisible characters in it, `%APPDATA%\Quill`,
  a `~`, or smart quotes, and cleans it up before using it, so "path does not exist" stops being
  the answer to a path that exists perfectly well.
- **Document Summary** (**Alt+I** on Windows) speaks the word, line, and heading counts, the
  last-saved time, and whether a recovery snapshot exists.
- **Speak-status commands** say the window title, the full file path, or a status summary on
  demand.
- **A filename is suggested from your first line** when you save an untitled document. It never
  overrides a name you already gave a file, and it can be turned off.
- **Send as Email** hands your selection or document to your mail client; **Copy as Email Body**
  copies it formatted for pasting.
- **Post to Mastodon** composes, posts, and manages accounts and lists from inside QUILL, with an
  optional automatic proofread of the post text first.
- **Progress sings.** Long downloads and installs play a short blip every five percent that rises
  as the work approaches done, with a touch of harmony at the quarter marks and a two-note finish
  at the end. A blip never talks over your screen reader, and the spoken milestones at 25, 50, and
  75 percent stay where they were for the big picture.
- **Keep the sound device awake.** If your USB or Bluetooth speakers clip the first instant of
  sound after a quiet pause, a common power-saving quirk, this setting keeps the device listening
  with a silent pulse.
- **Soft wrap and tab-control toggles** live on the View menu; **dark mode** is chosen in
  Settings, with system dark-mode and high-contrast detection on both platforms; and the
  contrast-ratio announcement and overwrite-mode toggle are command-palette commands you can
  bind to keys.
- **QUILL can be Thunderbird's external editor.** QUILL's one-process-per-file model matches what
  Thunderbird's External Editor Revived add-on expects: point the add-on at `quill.exe`, press
  **Ctrl+E** in a compose window, write in the full QUILL environment, save and close, and the
  text returns to your message. The User Guide has the complete walkthrough.
- **The QUILL Developer Console** provides Python and TypeScript consoles with session history,
  output capture, and a `q.*` host API, for the people who want to script the editor they are
  writing in. It is off in Safe Mode.
- **The QuillVille menu** is the cross-app switcher, present in every app in the family, for
  jumping between QUILL, Quill Radio, and Quill Weather.
- **Background watchers all answer the same three questions.** The watch folder, weather
  monitoring, and GitHub monitors share one policy model covering how often
  they poll, whether they tick audibly, and whether a result interrupts you. You configure the
  behavior once and it means the same thing everywhere.

---

## Getting help, and helping back

**Help > Report a Bug** is the direct line. It opens with focus in the Summary field, remembers
your name and email if you want it to, and includes a screen-reader picker, because "which screen
reader" is the first question every accessibility bug raises. Reports carry the full version
string, so an older installation is immediately recognizable. **Save Diagnostics** writes a bundle
you can attach, already scrubbed of secrets.

**Help > About Quill** carries a live contributor list (with an offline fallback) and a **Golden
Quills** tab recognizing the people who support the project financially.

QUILL is free, and it is built by and with the community that uses it. Features in this release
exist because people asked for them: the ranked spelling workflow and favorite folders came from a
longtime Kurzweil 1000 user's side-by-side comparison; the Clipboard Collector came from a request
for EdSharp's behavior; the Thunderbird integration came from someone who wanted to write email in
QUILL; the braille cell-alignment correction became the default because braille readers tested it
and reported back; the Offline Edition became genuinely offline because someone checked the promise
instead of assuming the label was enough. The GitHub integration owes its shape to
[GHManage](https://github.com/kellylford/GHManage), Kelly Ford's open-source screen-reader-first
GitHub browser, which shipped many of these ideas first and which QUILL learned from rather than
reinvented.

If something surprises you, beautifully or badly, tell us. A report that says "this works
perfectly" is worth as much as one that says it does not.

**QUILL 1.0.0. One editor. Every format. Built with you.**
