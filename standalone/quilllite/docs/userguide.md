# QUILL Lite — User Guide

*For QUILL Lite 1.0, released September 25, 2026.*

QUILL Lite is a text editor. It opens a file, lets you change it, and saves it
back exactly as it found it.

If you have used Notepad or WordPad, almost every key you already know works
here. Where QUILL Lite does something different, this guide says so, and says
why.

You do not need to read this guide to use QUILL Lite. Start it, type, press
**Ctrl+S**. Come back here when you want more.

<!-- contents:start -->

## What is in this guide

Every section, in order. Your screen reader's heading navigation reaches the
same places; this list is here for reading through, and for the EPUB.

- [The first minute](#the-first-minute)
- [Step by step: thirty things, start to finish](#step-by-step-thirty-things-start-to-finish)
- [Your documents are numbered](#your-documents-are-numbered)
- [Four kinds of document](#four-kinds-of-document)
- [Saving](#saving)
- [Finding things](#finding-things)
- [The Insert menu](#the-insert-menu)
- [Going somewhere](#going-somewhere)
- [Bookmarks](#bookmarks)
- [Selecting](#selecting)
- [Formatting](#formatting)
- [Spell check](#spell-check)
- [What is this character?](#what-is-this-character)
- [The status bar](#the-status-bar)
- [Reading a selection without risking it](#reading-a-selection-without-risking-it)
- [Copying and pasting more than one thing](#copying-and-pasting-more-than-one-thing)
- [Links](#links)
- [Working on lines](#working-on-lines)
- [Nine lessons, inside the app](#nine-lessons-inside-the-app)
- [The View menu](#the-view-menu)
- [Undo, and getting text back](#undo-and-getting-text-back)
- [Finding a command](#finding-a-command)
- [The window](#the-window)
- [Closing a lot of windows at once](#closing-a-lot-of-windows-at-once)
- [Changing what a key does](#changing-what-a-key-does)
- [Sounds](#sounds)
- [Making QUILL Lite smaller (or larger)](#making-quilllite-smaller-or-larger)
- [Reopening what you had open](#reopening-what-you-had-open)
- [Settings](#settings)
- [Printing](#printing)
- [Speech](#speech)
- [Dictation](#dictation)
- [AI help](#ai-help)
- [Where your files are kept](#where-your-files-are-kept)
- [Keeping QUILL Lite up to date](#keeping-quilllite-up-to-date)
- [What QUILL Lite is not](#what-quilllite-is-not)
- [Every key, in one table](#every-key-in-one-table)
- [Getting help](#getting-help)

<!-- contents:end -->

---

## The first minute

Start QUILL Lite and you get one window with one empty document in it, called
**1: Untitled**. Type. Press **Ctrl+S** when you want to keep it.

That is the whole thing. The rest of this guide is optional.

Three keys are worth knowing straight away:

- **F1** tells you where you are. Press it anywhere — in your document, on a
  button, in any window — and QUILL Lite says what that window is for and what
  the thing you are on does.
- **F6** takes you to the status bar, which is where the useful facts live.
  Arrow along it, press **Escape** to come back.
- **Ctrl+F1** lists every key QUILL Lite has.
- **Ctrl+Alt+F1** opens **Tutorials...**: nine short lessons that walk you
  through the things that are hard to work out by pressing keys.

---

## Step by step: thirty things, start to finish

The rest of this guide explains **why**. This section is the other half: what to
press, in order, and what you should hear when it worked. Every key here is
QUILL Lite's shipped key — if you have rebound something, **Ctrl+F1** is the list
of what you actually have.

Each recipe assumes nothing except that QUILL Lite is open.

### Getting started

**1. Open a file and save it back untouched.**

1. **Ctrl+O**. Choose the file. Enter.
2. Change nothing.
3. **Ctrl+S**.

You hear the file's name on opening and a save cue on saving. The file on disk
is byte-for-byte what it was — same encoding, same line endings, same final
line or lack of one.

**2. Find out where you are.**

1. **F6** — you land in the status bar.
2. Arrow left and right. Each cell says its name and its value: Line, Column,
   Words, Encoding, Line Endings, Format, Typing Mode, and the rest.
3. **Escape** — back to your document, in the same place you left it.

**3. Find out what a window or a control is for.**

Press **F1**. Anywhere. It tells you what window you are in, in a sentence, and
then what the thing you are focused on does.

**4. Take a lesson.**

1. **Ctrl+Alt+F1**.
2. Arrow to a lesson in the tree. Enter.
3. Read the step, press **Try it** if you would rather it did the step for you,
   then **Next**.

**5. See every key QUILL Lite has.**

**Ctrl+F1**. Type part of a name to narrow it.

### Writing and editing

**6. Make a heading.**

1. Put the cursor anywhere on the line.
2. **Ctrl+Alt+2** for Heading 2 (1 to 6 are **Ctrl+Alt+1** to **Ctrl+Alt+6**).
3. **Ctrl+Alt+0** puts it back to body text.

In a Markdown file this writes `## `; in HTML it writes `<h2>...</h2>`; in a
rich text document it applies a real heading style. Arrow off the line and back
onto it and you hear **"Heading 2"** and the heading's own words.

**7. Select a whole paragraph without counting.**

**Ctrl+Shift+H**. You hear "Selected paragraph" and a word count.

**8. Select something that does not line up with anything.**

1. **F8** where you want the selection to start.
2. Move however you like — arrows, **Ctrl+End**, a search, **Ctrl+G**, a
   bookmark. Nothing held down.
3. **Shift+F8** when you get there.

You hear how many words it took and which lines it spans.

**9. Get back a selection you just lost.**

**Ctrl+Shift+F8**. It puts back whatever you last had selected, however you
selected it.

**10. Move a line up or down.**

**Ctrl+Shift+Up** and **Ctrl+Shift+Down**. It tells you when it did nothing —
"Already the first line" is a different fact from silence.

**11. Move a whole section, heading and subsections and all.**

- One place at a time: **Alt+Shift+Up** / **Alt+Shift+Down**.
- Somewhere far away: **Ctrl+Alt+Shift+F5** (**Move Section To...**) and choose
  the destination from a list.
- Rearrange several at once: **Alt+Shift+O** (**Heading Organizer**), Tab and
  Shift+Tab to demote and promote, then close it.

Each of those is **one Ctrl+Z**, not one per line.

**12. Change the case of something.**

Select it, then: **Ctrl+Shift+U** upper, **Ctrl+Shift+K** lower,
**Ctrl+Shift+T** title, **Ctrl+Alt+Shift+U** sentence, **Ctrl+Alt+Shift+N**
invert.

**13. Put a deleted paragraph somewhere else.**

1. Put the cursor on it and press **Ctrl+Alt+Shift+Backspace** (Delete
   Paragraph).
2. Go where you want it.
3. **Ctrl+Alt+Shift+Z** (Restore Deleted Text).

**Ctrl+Z** would have put it back where it came from. This puts it where you
are.

### Finding things

**14. Find a word, and know how many there are.**

1. **Ctrl+F**.
2. Type. The count updates as you type — your reader reads it because it is a
   label, not an announcement.
3. **Ctrl+Down** and **Ctrl+Up** hear the next and previous match *without
   leaving the box*. **Enter** commits and puts you in the document.
4. **F3** and **Shift+F3** carry on afterwards.

**15. See every match before you replace anything.**

**Ctrl+Shift+F3** (**All Matches**). Every one, with its line, its column and
the words around it. **Ctrl+Alt+Shift+F3** just counts them.

**16. Find a character you cannot type.**

1. **Ctrl+F**, then Tab to **Search mode** and choose **Special characters**.
2. Type `\t` for a tab, `\u2014` for an em dash, `\N{NO-BREAK SPACE}` for
   exactly that.

**17. Go to a line, a bookmark or a heading.**

**Ctrl+G**, then arrow between **Line**, **Bookmark** and **Heading** at the top
and pick from what appears below.

### Keeping your place

**18. Drop a bookmark and come back tomorrow.**

1. **Ctrl+Shift+B** where you are. Or **Ctrl+Shift+1** to **Ctrl+Shift+9** for a
   numbered one.
2. **F2** and **Shift+F2** walk between them; **Alt+Shift+G** lists them.

Bookmarks are kept per file and survive closing the document.

**19. Nip off to check something and come straight back.**

1. **Ctrl+Shift+M** (Set Mark) before you go.
2. Go anywhere.
3. **Ctrl+M** (Pop Mark) comes back.

**Alt+Left** undoes the jump either way — it is the undo for navigation.

**20. Skim a long document.**

1. **Ctrl+Alt+H** and **Ctrl+Alt+Shift+H** step between headings.
2. **Ctrl+Alt+L** lists them all.
3. **Ctrl+Shift+F9** folds the section you are in; **Ctrl+Shift+F10** unfolds
   everything.

### Spelling

**21. Check the whole document.**

**F7**. It starts where your cursor is, walks you through one word at a time,
and carries on from the top when it reaches the end.

**22. Fix the word you are standing on, with no dialog.**

Press the **Applications key** (or **Shift+F10**). The first **Down** arrow
lands on a suggestion. **Enter** replaces the word.

**23. Teach QUILL Lite a word.**

**Ctrl+Alt+F9** with the cursor anywhere in the word.

**24. See every misspelling at once.**

**Alt+Shift+L**. Each row carries its line; Enter goes there.

### Clipboards and reuse

**25. Keep more than one thing on the clipboard.**

1. **Ctrl+Alt+Y** puts the selection in the next free tray slot (there are
   twelve). **Alt+Shift+Y** lets you choose the slot.
2. **Ctrl+Alt+V** pastes from any slot, an hour later if you like.
3. **Ctrl+Alt+Shift+Y** empties the tray.

**26. Gather six things and paste them once.**

1. **Alt+Shift+S** on each thing you select — it adds to one growing pile.
2. **Ctrl+Alt+Shift+G** pastes the whole pile.
3. **Ctrl+Alt+Shift+C** empties it.

**27. Type a long thing with a short one.**

1. **Ctrl+Alt+A** (**Manage Abbreviations**), add a trigger and what it writes.
2. Type the trigger and a space.
3. Forgotten a trigger? **Alt+Shift+I** (**Snippets**) lists them all with a
   preview, most used first.

### Making it yours

**28. Change a key.**

1. **Ctrl+Alt+Shift+R** (**Keyboard Manager**).
2. Find the command. Press the chord you want. It tells you if something else
   has it.
3. **Check for Problems** before you leave. **Save**.

**29. Make QUILL Lite smaller.**

1. **Ctrl+Alt+F10** (**Customize Features**).
2. Choose **Notepad** in the Profile box — every checkbox below moves there and
   then.
3. Read the description under it. **Save**.

**Recommended** puts the shipped answer back.

**30. Silence everything, right now.**

**Alt+Shift+M**. Again to bring it back. For one event at a time,
**Ctrl+Alt+Shift+O** (**Sound Scheme**).

---

## Your documents are numbered

QUILL Lite opens your documents **inside one window**, and numbers them. Your
first is 1, the next is 2, and a number never changes for as long as that
document is open — even if you close the one before it.

That number is how you get back to it:

| Key | What it does |
|---|---|
| **Alt+1** to **Alt+9** | Go straight to that document |
| **Ctrl+Tab** / **Ctrl+Shift+Tab** | Next / previous document |
| **Ctrl+F6** | Next document (the usual Windows key; same thing) |
| **Window menu** | Every open document, by number, with a mark on the one you are in |

**One thing to know.** Because your documents sit inside one window, they do
**not** appear in Alt+Tab. Alt+Tab shows you *QUILL Lite*, once. The four ways
above are how you move between documents. We would rather tell you that here
than have you hunting for a document you thought you had lost.

**Ctrl+N** makes a new document. **Ctrl+W** closes the one you are in.
**Ctrl+Q** closes everything, asking about anything you have not saved.

### Opening a second QUILL Lite

If you open a file from your file manager while QUILL Lite is already running, it
opens in the QUILL Lite you already have. That is what keeps the numbering
meaningful.

If you really do want two separate QUILL Lite windows — one per monitor, say —
start it with the extra option `--new-instance`.

---

## Four kinds of document

Every document is one of four kinds. The title bar names the first two; the
status bar's **Format** cell names all four.

**Plain text** is like Notepad. One font, no formatting, no markup. Text you
paste in arrives as plain text. This is what a `.py`, a `.conf` or a log file
is, and it is what you want when another program is going to read the file.

**Markdown** is plain text that means something: `#` starts a heading, `-`
starts a bullet, `**` makes a word bold. QUILL Lite writes those for you — see
[Formatting](#formatting) — and reads them back, so the caret can tell you you
have arrived at a Heading 2 or walked into a list of five.

**HTML** is the same idea in tags: `<h2>`, `<ul>`, `<strong>`. Everything
Markdown gets, HTML gets, in HTML's own spelling.

**Rich text** is like WordPad. Bold, italic, headings, alignment, bullet points,
line spacing. It saves as a Rich Text file, which Word and WordPad both open.

QUILL Lite chooses the kind from the file's name, and it is only ever a first
guess:

| The file is called | You get |
|---|---|
| `notes.rtf` | Rich text |
| `notes.md`, `.markdown`, `.mdx` — and `.txt` | Markdown |
| `page.html`, `.htm`, `.xhtml` | HTML |
| `build.py`, `nginx.conf`, `app.log`, anything else | Plain text |
| nothing yet — a new, unsaved document | Markdown |

`.txt` and a brand-new document are Markdown because that is what somebody
typing `## Notes` into one means. A `.py` or a `.conf` is plain text because in
those a `#` is a **comment** and a `-` is a flag, and an editor that announced
"Heading 1" on most lines of a build script would be exhausting.

### Saying otherwise

The guess is not binding. Writing HTML in a `.txt` scratch file is an entirely
reasonable thing to do, and there are three ways to say so:

- **Alt+Shift+F** rings through all four kinds — plain text, Markdown, HTML,
  rich text, and round again. Each stop says its own name, so you press it until
  you hear the one you meant. This is the fast way.
- **Ctrl+Alt+F6** (**Format ▸ Document Language**) goes straight to one, and
  tells you what each choice will do before you make it.
- **Enter on the status bar's Format cell** rings on to the next kind, exactly
  as Alt+Shift+F does — because the bar is where you notice the answer is
  wrong, and the fix should not mean leaving it.

Moving between plain, Markdown and HTML changes **nothing in your document** —
it changes what the keys write from now on. Going to or from rich text is a real
conversion, and it asks first, because it rewrites what is in the window.

### What the conversion keeps

Going **out of rich text** turns the formatting into Markdown rather than
throwing it away. A Heading 2 becomes `## `, a bold word becomes `**bold**`, a
bullet list becomes `- ` lines. The document is then a Markdown document, and
says so in the **Format** cell — so heading navigation, the headings list and
the outline all still find everything they found a moment ago. If the document
holds something Markdown cannot carry — a table, a picture, a footnote —
QUILL Lite names it before it asks.

Until version 1.0 this direction took the letters and left everything else. An
afternoon of headings and bold became a wall of unmarked text, and the only
announcement was "Plain text mode".

Going **into rich text** converts in the other direction: a Markdown document's
`## Title` becomes a real Heading 1, `**bold**` becomes really bold, and an HTML
document goes through Markdown on the way. A **plain text** document is left as
characters, deliberately — the asterisks in a shopping list are not bold, and
there would be no way back from deciding they were.

**What comes with you, in both directions.** Headings, bold, italic, underline,
strikethrough, superscript and subscript, font family and size, text colour and
highlight, bullet and numbered lists, links, code, block quotes, alignment, line
spacing, indents, spacing before and after, named styles, page breaks, tables,
pictures and horizontal rules. Underline used to be the exception — Markdown has
no underline syntax, so the tag picker writes `<u>text</u>`, and the rich-text
writer did not recognise it, which put those four characters on the page beside
the word they were meant to be formatting. It does now, and so do
`~~strikethrough~~`, page breaks and tables, all of which used to be lost on the
way.

**A rich text file opens properly in Word.** Headings carry Word's own heading
styles, and Quote, Title, Subtitle and Caption are written under the names Word
knows them by — so the style box says Quote rather than showing text that merely
happens to be indented and italic.

Your file keeps its name. Because a rich document cannot be written over a
`.txt`, the next **Ctrl+S** offers you `notes.rtf` instead of `notes.txt` — the
name filled in, ready to accept. Nothing is written under a name that does not
match what is in it.

The choice lasts as long as the window. It describes what you are typing, not
what the file is.

---

## Saving

**Ctrl+S** saves. **Ctrl+Shift+S** saves under a new name.

QUILL Lite makes you one promise here: **open a file, change nothing, save it,
and it is exactly the file you started with.** Nothing is quietly tidied up
behind your back.

To keep that promise it remembers three things about every file it opens, and
puts them back the same way:

- **How the text is stored** — different files store letters and accents
  differently, and QUILL Lite keeps whichever way yours already used.
- **How the lines end** — files made on Windows and files made on other systems
  mark the end of a line differently, and QUILL Lite does not change yours.
- **Whether the file ended with a blank line** — if it did not, it will not
  suddenly start.

You can see both of the first two in the status bar (**F6**), and you can
deliberately change them from **Tools ▸ File Encoding and Line Endings**
(**Ctrl+Alt+E**) when you actually want to — for instance when somebody needs a
copy of an old file in a newer format. The change takes effect the next time you
save.

### How this file is written: encoding and line endings

**Tools ▸ File Encoding and Line Endings...** (**Ctrl+Alt+E**) is one window for
the two facts above, and it is the same window QUILL opens from **File ▸ File
Format...**. Neither list is applied until you save; the window says so.

**Encoding** offers UTF-8 for anything new, UTF-8 with BOM for the Windows tools
that expect one, UTF-16, and Windows-1252 for the older `.txt` files that are in
it. **Line endings** offers CRLF, which is what Windows programs write and what a
new QUILL Lite document is born with, and LF, which is what Unix, macOS and most
build tools expect.

A file that arrived in something neither list offers keeps it. A UTF-16
big-endian file, or a file whose lines end with a single CR the way classic Mac
OS wrote them, shows a **keep as is** row at the top of the list and starts in
it — so answering the window with Enter cannot convert a file you only opened to
read. Until September 2026 the list quietly started on its first row instead: a
CR file read "CRLF", and confirming the window rewrote every line ending in it.
A big-endian file had a subtler version of the same problem — both byte orders
were read through the one codec that always *writes* little-endian, so saving a
file you had not otherwise touched swapped every pair of bytes in it.

### When a character will not fit

Older files store only a limited set of letters. If you type an em dash, a
curly quote or an emoji into a file that cannot hold one, QUILL Lite asks before
it saves rather than after:

> 3 characters cannot be saved as Windows-1252. Save as UTF-8 instead?

- **Yes** saves the file as UTF-8 and keeps every character. The **Encoding**
  cell in the status bar changes to match, because from now on the file really
  is UTF-8.
- **No** saves it the way it already was, and those characters become question
  marks. Sometimes that is what you want — a file something else has to read
  back.
- **Cancel** stops, and nothing is written.

Until version 1.0 there was no question. The characters became question marks,
QUILL Lite said "Saved", and the only way to find out was to read that line
again.

### Saving an HTML page as Markdown

**Ctrl+Shift+S** offers **Markdown (*.md)** in its list of types, and in one
case that is a real conversion rather than a new name: if the document you are
saving is **HTML**, the tags are turned into Markdown as it saves. A heading
becomes `#`, bold becomes `**bold**`, a list becomes `-` lines, and links keep
both their text and their address. QUILL Lite says **"Converted HTML to
Markdown"** when it happens, and the document in front of you changes to match
the file -- the window and the file never disagree about what you just saved.

Tags Markdown has no way to write are dropped and their text kept, so nothing
you typed disappears. If the conversion would produce nothing at all -- a page
that is only a comment, say -- QUILL Lite keeps your text exactly as it was and
tells you so, rather than writing an empty file.

The conversion happens **to the file**, and the window follows only once the
file is safely written. If the save fails — the file is locked, the disk is
full — the document in front of you is untouched, still HTML, with its undo
history intact. The same is true of flattening a rich text document to plain:
QUILL Lite asks, writes the plain file, and only then drops the formatting from
the window.

Saving a plain text or Markdown document as `.md` changes nothing at all: plain
text is already what it claims to be, and Markdown already is Markdown. A
**rich text** document is not offered Markdown, because turning real formatting
back into `#` and `**` means guessing which bold lines were meant as headings.
Save it as plain text first -- QUILL Lite asks before it drops the formatting --
and the Markdown row is waiting.

### If something goes wrong

While a document has changes you have not saved, QUILL Lite keeps a copy of it
aside, about every thirty seconds. That copy sits **beside** your file and never on top
of it.

If QUILL Lite or your computer stops unexpectedly, that work is offered back to
you the next time you start, in its own document. It comes back **the way it
was**: a file stored in an older encoding, or written with Unix line endings,
is still that file after a recovery. The copy kept aside is always written in
one format, because it has to hold whatever you typed — but what it records
alongside is what *your* document was, and that is what is put back.

If a copy cannot be read back — a damaged disk, a file something else is
holding — QUILL Lite says so and leaves it exactly where it is. The window does
not take your file's name, and the copy is offered again next time. It is still
the only copy of that work.

Save it, or close normally, and the copy is deleted. So there is never anything
in there except work you actually need.

**What you are offered is tidied first, and you are told.** Before the window
opens, QUILL Lite drops three kinds of row: copies that are identical to each
other (a crash can write the same work several times, and that is one
document, not four), copies nobody has come back for in **thirty days**, and
untitled documents if you have turned those off in Preferences. If everything
it found was one of those, no window opens and QUILL Lite **says so** --
"Tidied up unsaved work from last time" -- because silence there is
indistinguishable from work having vanished.

The window itself lists what is left, one row each, with a checkbox, and a
read-only **What this would do** field you can arrow through. Six buttons:
**Restore Checked**, **Restore All**, **Not Now** (which changes nothing and
offers the same list next time), **Discard Checked**, **Discard Everything**,
and **Never Offer Untitled** — that last one for somebody who uses QUILL Lite as
a scratchpad and does not want yesterday's throwaway notes back. It is a
preference, not a trapdoor: **Offer untitled unsaved work back after a crash**
in Preferences turns it on again.

### Going back to an earlier version

There is a separate **timestamped backups** option (**Tools ▸ Customize
Features**), which keeps a dated copy every time you save. That is for the
paragraph you deleted an hour ago rather than for a crash. It starts switched
off, because it does fill up a folder.

Turn it on and **File ▸ Earlier Versions...** (**Ctrl+Alt+Shift+E**) lists them,
newest first, as "Today at 4:12 PM — 2,341 words". Up to twenty are kept per
document; after that the oldest go.

The word count is there to be compared rather than read. Two saves a minute
apart are otherwise almost impossible to tell apart by ear, and the version that
is suddenly two thousand words shorter is usually the one you are hunting for.

There are two ways to take one:

- **Restore** puts that version into the window you are in. It does **not** save,
  so the file on disk is untouched until you decide, and **Ctrl+Z** undoes it. A
  restore chosen by mistake costs you one keystroke.
- **Open a Copy** puts the old version in a new untitled window and leaves the
  document you are working on completely alone. Use this one when the question
  is "what did this say yesterday" rather than "put yesterday back".

Until version 1.0 QUILL Lite wrote these files and gave you no way to read one:
they were there, correctly dated, and reachable only if you knew where the app
kept them. If you have had backups switched on, everything from before this
version is in the list too.

---

## Finding things

| Key | What it does |
|---|---|
| **Ctrl+F** | Find |
| **F3** / **Shift+F3** | Find next / previous |
| **Ctrl+H** | Replace |
| **Ctrl+G** | Go To: a line, a bookmark or a heading |

When a search runs off the end of the document it starts again at the top, and
it tells you it has done so. That matters more than it sounds: without it, a
document with one match sounds exactly like a document with none, every time you
press F3.

### How many are there?

The Find window keeps a running count of what you have typed so far, before you
press anything. Type three letters and it says how many matches there are; add a
fourth and the number changes. Your screen reader reads it as it changes,
because it is a label rather than an announcement -- a count spoken on every
keystroke would talk over the typing it is describing.

**Ctrl+Down** and **Ctrl+Up** step through the matches *without leaving the
search box*, so you can hear the next one and still adjust what you typed.
Enter is what commits and puts you in the document.

Outside the window, **Ctrl+Alt+Shift+F3** counts the current search anywhere,
and **Ctrl+Shift+F3** opens **All Matches**: every match in the document, in
order, each with its line and column and the words around it. That is the list
you want before a Replace All, because it is the only way to see what you are
about to change rather than finding out afterwards.

## The Insert menu

Everything that puts something into your document that is not typing.

| Key | What it does |
|---|---|
| **F5** | Today's date and the time |
| **Ctrl+Shift+F2** | Special Character — 357 of them, in 15 groups, searchable by name or code point |
| **Alt+.** | Emoji — search or browse, with a description of each one |
| **Shift+Enter** | A line break that does not start a paragraph |
| **Ctrl+Alt+I** | Markdown Tag — the whole Markdown vocabulary |
| **Ctrl+Alt+O** | HTML Tag — 111 tags and 20 whole form fields, searchable by what they do |

These were spread through Edit before there were six of them. Insert sits
**before Format** on the bar for the reason Word puts it there: you insert a
thing and then you format it, so the menus are in the order the work happens.
Every key is unchanged.

### Emoji — Alt+.

QUILL's own picker, and the same key. Search by name, by keyword, by what it
*looks like*, or by a typed smiley — `:)` finds the smiling face and `<3` finds
the heart. Or browse by category, starting with **Favourites** and **Recent**.

Every emoji comes with a **written description** of what it actually shows,
which is the whole point: a picture wall is exactly the shape of control that
cannot be used without sight, so this is a list you arrow through with a
description pane beside it. What you insert is announced by name, because a bare
emoji character is read as anything from its own name to silence depending on
your synthesiser.

It works in every kind of document, rich text included. An emoji is a character,
not markup.

### The two tag pickers

**Exactly one of them is ever available**, and it is whichever your document's
language is. The other is **greyed out rather than hidden** — a greyed row tells
your reader it is unavailable the moment you arrive on it, while a row that has
vanished leaves you hunting the menus for something you know the app has. Press
the key anyway and it tells you what the document is, what it would need to be,
and that **Ctrl+Alt+F6** is how to change that.

**Markdown Tag (Ctrl+Alt+I)** offers bold, italic, inline code, a fenced code
block, the six heading levels, bullet, numbered and task lists, blockquote,
link, image, table and footnote. Type to narrow the list. Link and Image ask for
the address afterwards.

**HTML Tag (Ctrl+Alt+O)** offers **111 tags and 20 whole form fields**, and
**searches by what they do as well as what they are called**: type "dropdown"
and find both a finished labelled dropdown and the bare `select`, type
"glossary" and find `<dl>`, type "acronym" and find `<abbr>`, type "subtitles"
and find `<track>`. For a bare tag you can then give it attributes —
`class=note; id=summary; aria-label=Summary` — and Enter on an empty box skips
that step, because an `<h2>` needs none. A whole form field skips the box
entirely: it arrives with the attributes that make it work.

Anything selected is wrapped. Otherwise the cursor lands between the tags.

### Whole form fields, wired up

The HTML picker's top rows are not tags — they are **finished controls**. Choose
**Form field: dropdown** and you get a label, a `for` that matches the field's
`id`, the `<select>` and three `<option>`s, all at once.

This is where the picker earns its place. Inserting `<select>` on its own is the
easy half; the half that matters is the wiring, and the wiring is invisible. A
missing `for` renders identically to a present one. A radio group without a
shared `name` looks exactly like one with — except every button can be on at
once. Two fields that share an `id` look perfect until somebody clicks the
second label and the first field takes focus. None of that is something you can
check by looking, which is precisely why it should not be left to memory.

So every one of these arrives complete:

| Choose | You get |
|---|---|
| **text**, **email**, **password**, **telephone**, **web address**, **number**, **date**, **search**, **file upload** | a labelled input of that type, with `autocomplete` where the browser can help |
| **long answer (textarea)** | a labelled, five-row text area |
| **dropdown (select)** | label, select, and an empty first option so it cannot submit an answer nobody gave |
| **dropdown with groups** | the same, with two `<optgroup>`s |
| **checkbox** | box first, then its label — the convention, and the label becomes part of the click target |
| **checkbox group** | a `<fieldset>`, a `<legend>`, and boxes sharing one `name` |
| **radio group** | the same, with three radios, one shared `name`, and exactly one default |
| **autocomplete (input + datalist)** | an input joined to its own suggestion list |
| **required, with hint and error** | a hint and an empty error, both named by `aria-describedby`, plus `aria-invalid` and `role="alert"` |
| **submit button** | a `<button type="submit">` with real text, not an `<input value="">` |
| **whole form** | a contact form: fieldset, legend, three labelled fields, and a submit |
| **grouped fields (fieldset)** | an empty fieldset with a legend, for grouping what you already have |

**Select a word first and it becomes the label** — and the `id` is made from it,
so the two agree. Select "Postcode", choose **Form field: text**, and you get a
Postcode field with `id="postcode"` and `for="postcode"` already matching.

**The `id` is checked against your document first.** Insert a second email field
and it will be `email-2`, not a duplicate of the first. That one line of
behaviour is the difference between a form that stays accessible when it is
copied and one that stops being so without anybody noticing.

The bare tags are all still there, one row further down, for when a bare tag is
what you meant.

---

### Typing things there is no key for

**Insert ▸ Special Character...** (**Ctrl+Shift+F2**) opens a picker for
the 357 characters a keyboard has no key for. Two ways in, and the window opens
on the first one:

- **Type what you are after.** The search box takes part of a name -- `dash`,
  `euro`, `acute`, `arrow`, `apostrophe` -- or one of the words Unicode does not
  use but people do: `gbp`, `sterling`, `copyright`, `eszett`, `micro`. Press
  **Enter** to move into the results.
- **Or clear the box and browse a group.** Fifteen of them: Whitespace, Dashes
  and hyphens, Quotes, Invisible and control, Typography, Legal and reference
  marks, Currency, Maths and units, Fractions, Superscripts and ordinals,
  Arrows, Accented letters (small and capital, listed separately), Greek
  letters, and Punctuation from other languages.

The results list has three columns -- the character, its name, and its code
point -- and the **Description** pane below updates on every row you arrow onto,
with the same detail **Character Details...** gives for a character already in
the document. The code point column is what tells apart rows that sound the
same: "Thin space" and "Hair space" are U+2009 and U+200A.

**Enter inserts the character you are on**, and QUILL Lite **reads back what it
put in** -- "Inserted — U+2014 Em dash". That is not a nicety: most of this list
is invisible on the page, so without the read-back the command would be a
keystroke after which something you cannot see may or may not have appeared.

**The search box is also a code-point box.** Type `2014`, `U+2014` or `d8212`
and the em dash is the first result. A code point that is in no group at all
still finds its character, so the picker reaches everything Unicode has and not
only the 357 that are grouped.

QUILL has the same picker on the same key, **Ctrl+Shift+F2**, over the same
list.

### Moving your settings to another computer

**Tools ▸ Back Up Settings...** (**Ctrl+Alt+F11**) writes your configuration
to a `.qsf` file. **Tools ▸ Restore Settings...** (**Ctrl+Alt+F12**) reads
one back.

The file holds preferences, not a picture of this computer. Your recent-files
list, the session QUILL Lite restores at startup, the window size and the last
time it looked for an update are all **left out on purpose** — carrying them to
another machine would give you an editor pointing at files that are not there.
The backup tells you how many locations it left behind.

Restoring tells you what was different: how many settings came across, how many
have been added to QUILL Lite since the file was written (those keep their
defaults), and how many the file had that this version does not recognise. If
the file has nothing QUILL Lite recognises at all, nothing is changed — a wrong
file should not reset your editor.

QUILL has the same thing, on buttons in its Preferences window. The two products
use the same file extension but do not read each other's backups: they are
different editors with different settings.

### Ending a line without starting a paragraph

**Insert ▸ Line Break** (**Shift+Enter**, the same chord Word uses) ends
the line you are on and starts the next one **without** starting a new
paragraph.

That distinction matters in Markdown and nowhere else is it visible. A blank
line between two lines makes them two paragraphs, which most renderers show with
a gap. A hard break makes them two lines of one paragraph, which is what you
want for an address, a verse, or a run of scene-break lines that should sit
tight against each other.

QUILL Lite writes the break in whichever spelling **Markdown line break style**
names in Settings, and **says which one it used** — the default is a backslash
at the end of the line, because the alternative is two trailing spaces, which
are invisible on screen, silent to a screen reader, and stripped by many tools
when they save a file. If you have ever added two spaces to the end of a line
and had nothing happen, that is why.

QUILL has the same command on the same key.

### Searching for things you cannot type

The Find and Replace windows have a **Search mode** with three settings.

**Normal text** is the ordinary one: what you type is what is looked for,
punctuation and all.

**Special characters** lets you write the characters there is no key for. `\t` is a tab,
`\n` a line break, `\u2014` an em dash, and `\N{NO-BREAK SPACE}` is exactly
what it says. This is the companion to **Describe Character**: that tells you
which invisible character you are standing on, and this is how you then find
every other one like it, or replace them all with an ordinary space.

**Regular expression** treats what you typed as a search pattern -- `.` matches
any character, `*` repeats the thing before it, `[abc]` matches any one of
those, `^` and `$` are the start and end of a line. If the pattern is not valid,
QUILL Lite says which character is wrong rather than quietly finding nothing: a
search that failed and a search that found nothing are different problems, and
only one of them is fixed by retyping.

Whole word works with all three. In regular expression mode it wraps the whole
pattern, so `cat|dog` means "the word cat or the word dog", not "the word cat,
or dog anywhere".

---

## Going somewhere

**Ctrl+G** opens **Go To**, which is Word's rather than Notepad's: one window,
and a choice of what to go to. Arrow between **Line**, **Bookmark** and
**Heading** at the top, and what is below follows — a number box for a line, a
list of places for the other two. Bookmark rows are led by their digit and
heading rows by their level, so you can pick one out by its first word.

**Alt+Shift+G** and **Ctrl+Alt+L** still go straight to the bookmark list and
the heading list. Those are faster when you already know which kind you want;
Ctrl+G is the one to press when you do not.

---

## Bookmarks

A bookmark is a place you meant to come back to.

| Key | What it does |
|---|---|
| **Ctrl+Shift+B** | Drop a bookmark in the next free slot |
| **Ctrl+Shift+1** to **Ctrl+Shift+9** | Set that numbered bookmark |
| **F2** / **Shift+F2** | Next / previous bookmark |
| **Alt+Shift+G** | The bookmark list — go to one, or remove one |
| **Ctrl+Alt+B** | Clear them all |

Bookmarks follow the text as you edit around them, so they stay on the right
words rather than drifting.

### They are still there tomorrow

Close the document and open it again and your bookmarks are where you left them,
along with the place the cursor was. You do not have to do anything to keep
them.

This matters more than it sounds. The reason to have bookmarks at all is that
there is no scrollbar thumb to glance at and no way to see at a glance where you
are in a long file -- and that does not stop being true when you close the
window. Marking nine places and losing them on the way out is the same loss as
never marking them, just later.

Two details worth knowing:

- **A document you have never saved is not remembered.** There is no filename to
  remember it by. Save it once and its bookmarks are kept from then on.
- **Nothing is written next to your file.** No stray sidecar file appears in your
  folder; the list lives in QUILL Lite's own settings folder, keyed by the file's
  location. If the file has been shortened by something else since you last had
  it open, bookmarks past the new end are pulled back to the end rather than
  sending you nowhere.

You can turn all of this off with the rest of bookmarks in **Tools ▸ Customize
Features**, and then nothing is written at all.

### The one with no number

| Key | What it does |
|---|---|
| **Ctrl+Alt+J** | Set Temporary Bookmark — drop a pin where the cursor is |
| **Ctrl+Shift+J** | Go to Temporary Bookmark — go back to it |

There is one more bookmark, and it is a different kind of thing. Use it when you
are about to go and look something up and you want to come straight back: press
Ctrl+Alt+J before you go, Ctrl+Shift+J when you are done.

It has no number, no label and no row in the list, and setting it again simply
moves it — nothing asks whether you meant to. It is not kept when you close the
document. That is the point: a place you did not name is a place you did not
mean to keep, and having to name one is exactly the interruption you were trying
to avoid.

QUILL has had these two keys for years and they are the same two keys here.

### Going back where you came from

| Key | What it does |
|---|---|
| **Alt+Left** | Go back to where you were before the last jump |
| **Alt+Right** | Go forward again |

They are at the top of the **Navigate** menu, above the headings and the
bookmarks, and they belong to neither of those — so switching both of those off
does not take Back and Forward with them. They are always there.

Every jump QUILL Lite makes is remembered: going to a line, following a heading,
picking something out of the heading list or the bookmark list, and landing on a
search hit. **Alt+Left** takes you back to where you were standing before it.

It is the undo for moving about, and the keys are the ones every web browser and
file window has used for thirty years. Without it, pressing F3 to check a word
somewhere else in the document is a one-way trip: you can find your way back
only if you happened to know the line number you were on, which is exactly the
thing you were never told.

Unlike bookmarks, this is only remembered while the window is open. It is about
where you have been in this sitting, not about the document.

---

## Selecting

Holding Shift and tapping an arrow key selects one character at a time. That is
right for two letters and miserable for four paragraphs — you press, and press,
and have no idea where you have got to.

So **Edit ▸ Selection** gives you three better ways. Everything in it tells you
how much it took, which is the part that matters: "Selected paragraph, 412
characters" is something you can act on, where a silent selection is one you
have to test by pressing something you might regret.

### Start a selection and walk to the end of it

This is the one to learn first. Press **F8**, then move however you like —
arrows, Home, End, Page Down, Ctrl and an arrow — and the selection follows you
from where you started. Press **Shift+F8** when you get there.

No modifier held down the whole way, and no counting. It is the answer whenever
the thing you want does not line up neatly with a word or a paragraph.

| Key | What it does |
|---|---|
| **F8** | Start selecting from here |
| **Shift+F8** | Finish, and say how much was taken |
| **Ctrl+Alt+F8** | **Toggle Selection Marker** — drop or pick it up, without moving the cursor |
| **Ctrl+Shift+F8** | Put back the selection you just had |
| **Alt+Shift+F8** | Go to the beginning of what is selected |

#### A Shift that stays down — Alt+Shift+F9

**Extend Selection Mode** is the other way to do the same job, and which one
suits you is a matter of taste rather than of which is better.

Press **Alt+Shift+F9** and QUILL Lite says "Extend selection mode on" and
tells you where you are. From then on every arrow, Home, End, Page Down and
Ctrl+arrow *extends* instead of moving — no modifier held, and, the part that
matters, **no "selected" from your screen reader on every press**. That is what
makes holding Shift and pressing Down forty times so unpleasant, and it is the
whole reason this mode exists.

Press it again, or **Escape**, to stop. Typing anything that is not a movement
key finishes the selection and replaces it, exactly as it would have if you had
been holding Shift.

The difference from **F8**: F8 marks a spot and computes the span when you press
Shift+F8, so between the two you can use *anything* — Find, Go To Line, a
bookmark. This mode is live, so what you have is always what is highlighted.
Both are here because both are genuinely the better answer sometimes.

**Ctrl+Shift+F8** is worth remembering for the moment an arrow key has just
thrown away a selection that took six keystrokes to build. It puts back whatever
you last selected, however you selected it — F8, Select Word, Select Paragraph,
Grow, or simply clearing one by accident.

#### What you hear when something is selected

Every selection says the same thing in the same order: **what** it took and
**how many words** — "Selected paragraph, 41 words". A word count is a size you
can picture; a character count is a number you then have to divide.

The **F8** span is the one exception, and it says more because it has to: it
reaches between two arbitrary points, so "Selected 120 words, lines 14 to 31"
is the only way to know how far it went. Everything else is named by its scope
already.

QUILL says exactly the same sentences. One of the two used to add a character
count and the other did not, so the same key reported the same fact two ways
depending on which editor you happened to be in.

### Take a whole word, line or paragraph at once

| Key | What it does |
|---|---|
| **Ctrl+Shift+W** | Select the word |
| **Ctrl+Shift+E** | Select the line |
| **Ctrl+Shift+H** | Select the paragraph |
| **Ctrl+Space** | Select the sentence |
| **Ctrl+Alt+Shift+B** | Select the block — the run between blank lines |
| **Ctrl+Shift+X** | Grow the selection outwards a step |
| **Ctrl+Alt+Shift+X** | Shrink it back in a step |
| **Ctrl+Shift+A** | Clear the selection, staying where you are |
| **Ctrl+A** | Select everything |

You do not need to know where any of these begin. Growing goes word, line,
sentence, paragraph, block, whole document, and says which one it took each
time. Shrinking walks back the other way — so you can over-press **Ctrl+Shift+X**
without it costing you anything.

### Marks — where you were a moment ago

A mark is not a bookmark. A bookmark is a place you mean to keep. A mark is
where you were standing before you went off to check something.

| Key | What it does |
|---|---|
| **Ctrl+Shift+M** | Set a mark here |
| **Ctrl+M** | Go back to the last mark |
| **Alt+M** | List your marks and pick one |
| **Ctrl+Alt+X** | Swap between the cursor and the mark, selecting what is between |

Twenty marks are kept, and marking the same place twice does not use up two of
them.

A mark **moves with your text**. Drop one on a paragraph, insert three
paragraphs above it, and Ctrl+M still takes you to that paragraph — the mark
remembers the words around it, not a count of characters from the top.

And **Alt+Left comes back**. Every way of reaching a mark — Ctrl+M, choosing one
from the list, Ctrl+Alt+X — is a jump the Back key can undo, the same as a
bookmark or a Go To.

### Two more

**Ctrl+Shift+Y** reads back what is currently selected. There is no glance that
confirms you took what you meant to, and the next key you press might replace
it. Long selections are summarised rather than read out in full.

**Ctrl+Alt+Q** puts a second copy of the selection right after the first — or
duplicates the line you are on if nothing is selected.

### The ones Windows gives you anyway

These work in QUILL Lite as they do everywhere, and have no menu row because they
need none:

| Key | What it does |
|---|---|
| **Shift+Home** / **Shift+End** | Select to the start / end of the line |
| **Ctrl+Shift+Home** / **Ctrl+Shift+End** | Select to the start / end of the document |
| **Shift** and an arrow | Select one character, or one line, at a time |
| **Ctrl+Shift** and Left or Right | Select a word at a time |

---

## Formatting

These are WordPad's keys, deliberately unchanged.

**The same key, the document's own answer.** Ctrl+B used to say "Not available
in plain text. Press Alt Shift F to switch to rich text", which is true and
unhelpful — somebody writing Markdown does not want rich text, they want two
asterisks, and they know it. So what Ctrl+B writes now depends on what kind of
document you are in:

| In a | **Ctrl+B** writes | **Ctrl+Alt+2** writes |
|---|---|---|
| Markdown document | `**bold**` | `## Heading` |
| HTML document | `<strong>bold</strong>` | `<h2>Heading</h2>` |
| Rich text document | real bold | a 16-point bold paragraph |
| Plain text document | nothing, and says why | nothing, and says why |

Select a word first and it is wrapped. With nothing selected the markup goes in
empty and **the cursor lands in the middle of it**, ready to type — which
matters, because otherwise you would be typing after the closing tag with no way
to see that you were.

In Markdown and HTML the announcement names the *markup* rather than the effect
— "Bold in Markdown", not "Bold on". Nothing on the screen went bold; two
asterisks appeared, and you need to know which of the two happened.

HTML gets `<strong>` and `<em>`, never `<b>` and `<i>`. They are not synonyms to
the thing that reads them out: `<strong>` carries importance into the
accessibility tree, and `<b>` carries only a typeface.

Applying a heading **rewrites the line** rather than adding to it. Pressing
Ctrl+Alt+2 on a line that is already `### Notes` gives you `## Notes`, not
`## ### Notes` — and an `id=` on an HTML heading is carried across, because it
is very often the anchor somebody else's link points at.

The rest of the Format menu — alignment, line spacing, font — is rich text only,
and says so when it cannot run. Lists are not: **Ctrl+Shift+L** works in a rich
text document and in a Markdown one.

**The keys the editing control brings with it.** Every QUILL Lite document is
built on the same Windows editing control that WordPad uses, because that is what
gives your screen reader and your braille display a text surface worth reading.
The cost is that the control has its own keyboard: **Ctrl+U** underlines,
**Ctrl+E**, **Ctrl+L**, **Ctrl+R** and **Ctrl+J** re-align, **Ctrl+=** and
**Ctrl+Shift+=** move the baseline, and a few more besides. In a rich text
document that is exactly right, and they work.

In a Markdown, HTML or plain document they used to *appear* to work. The
formatting was really applied — it was on the screen and on the undo stack — but
the document was not marked as changed, nothing was announced, and none of it
was saved. A document that differs from the file it is about to become, with
nothing in the app willing to mention it, is the worst version of this bug for
somebody who cannot see the screen.

Now the key is swallowed in a document that has no formatting, and QUILL Lite says
so once:

> Underline has no meaning in a plain text document.

Once per effect per document, not once per press: a key that does nothing and
explains nothing is indistinguishable from a key that is broken, and a key that
explains itself on every press becomes noise inside a minute. QUILL says the same
sentence for the same key, from the same place in the shared code.

**Ctrl+Shift+L rings**, the way WordPad's own button does: bulleted list,
numbered list, no list, round again. Each stop says its own name, so you press it
until you hear the one you meant. In rich text the control draws the markers and
renumbers them for you; in Markdown it writes `- ` and `1. ` on the lines you
have selected — and only on those, never on the rest of the file.

| Key | What it does |
|---|---|
| **Ctrl+B**, **Ctrl+I**, **Ctrl+U** | Bold, italic, underline |
| **Ctrl+Shift+.** / **Ctrl+Shift+,** | Bigger / smaller text |
| **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J** | Left, centre, right, justify |
| **Ctrl+Shift+L** | Lists: bulleted, numbered, none, round again |
| **Ctrl+1**, **Ctrl+5**, **Ctrl+2** | Single, one-and-a-half, double spacing |
| **Ctrl+Alt+1** to **Ctrl+Alt+6** | Heading 1 to 6 |
| **Ctrl+Alt+0** | Back to ordinary text (removes the heading) |
| **Ctrl+Shift+N** | Normal Text: take *all* formatting off |
| **Ctrl+Shift+D** | Describe the formatting where the cursor is |

They are gathered in **Format ▸ Headings**, where the digit in the menu is the
digit in the shortcut.

A heading is bold text at its own size — 20, 16, 14, 12, 11.5 and 10.5 point for
levels 1 to 6, with ordinary text at 11 point. These are the same sizes QUILL
for All uses, chosen so that a document you save here still reads as having
headings when somebody opens it in Word. Every level has a size of its own on
purpose: levels 5 and 6 used to share the 11-point body size, which meant
QUILL Lite could apply them and then could not find them again — heading
navigation and the headings list both walked straight past them.

**Ctrl+Shift+N** is Normal Text, and it is the way back. Every other command
in this menu is a toggle or a setting, so each one needs you to already know
what is applied: turning bold off means knowing bold is on, and a twenty-point
run means walking the size back down a step at a time. Normal Text does not
ask. It takes off bold, italic, underline and strikethrough, puts the size back
to ordinary body text, clears the colour and the highlight, returns the
paragraph to left aligned and single spaced, and takes it out of any list --
all in one press, and one **Ctrl+Z** puts it all back. It leaves the *typeface*
alone, because the face a document is written in is part of the document;
**Format ▸ Editor Font** is where that is chosen. It is Word's key for the same
idea. In a Markdown or HTML document the same key takes the heading marks off
the line instead, which is what "normal" means to a line written in markup.

**Ctrl+Shift+D** is the one worth remembering. It tells you what you are
standing in — "Arial, 16 point, heading 2, bold" — which is the question a
formatted document raises and that nothing else can answer for you.

### Moving between headings

| Key | What it does |
|---|---|
| **Ctrl+Alt+H** / **Ctrl+Alt+Shift+H** | Next / previous heading |
| **Ctrl+Alt+L** | The list of every heading |

These work in **every kind of document**. In rich text they walk the point-size
ladder above; in Markdown they walk the lines that start with `#`; in HTML they
walk `<h1>` to `<h6>`. They used to refuse in a plain document ("Headings are only available
in rich text"), which was wrong in the way that matters: plain-text headings are
real enough for **Alt+Shift+Right** to change their level, and only *navigation*
pretended the document had no shape. A `#` inside a fenced code block is not
treated as a heading.

### Skimming a long one — folding

A sighted reader finds out what is in a long document by scrolling and glancing.
Folding is the same thing for somebody who cannot.

| Key | What it does |
|---|---|
| **Ctrl+Shift+F9** | **Fold or Unfold Section** — the one you are in |
| **Ctrl+Alt+Shift+Down** | **Next Section** |
| **Ctrl+Alt+Shift+Up** | **Previous Section** |
| **Ctrl+Shift+F10** | **Unfold Everything** |

Walking between sections says the heading, whether it is folded, and how many
lines are under it — "Installing, expanded, 34 lines". That sentence is the
skim: it is what a glance down the page would have told you.

**Nothing is hidden from your cursor.** A folded section reads exactly as it
reads unfolded, arrow for arrow, and Find still finds things in it. A fold that
really hid your text would be a document whose contents depend on how you happen
to be looking at it, and the first thing that breaks is Find. What a fold *is*
here is a note to yourself that you have dealt with that section, and you hear
it when you pass by.

Markdown documents, where a `#` heading marks where a section starts.

### Hearing that you have arrived at one

Arrow onto a heading and QUILL Lite says **"Heading 2"**.

It has to, because your screen reader cannot. **No Windows edit control has
paragraph styles** — the control QUILL Lite hosts can tell JAWS or NVDA the font
name, the size and the weight, and has no way to say "this paragraph is a
heading". Word manages it only by shipping an accessibility provider of its own.

The rules are narrow on purpose:

- **The level, not the text.** Your reader is already reading the line. Saying
  the title here would speak every heading twice.
- **Once, on arrival.** Moving about inside the heading says nothing further.
  You hear it again if you leave and come back.
- **Both modes.** A rich-text heading and a Markdown heading announce alike.

Applying a heading already tells you so, and the two do not double up. Opening a
document whose first line is its title does not greet you with "Heading 1".

**Turning it off — View ▸ Announce Headings (Ctrl+Alt+F3).** Sometimes you are
reading a document *as text* and the levels are one sentence too many. The key
turns the cue off and on where you stand, and says which way it went —
"Headings will not be announced", or "Headings announced on arrival" — rather
than "off" and "on", so a key pressed by accident is never a mystery. The
choice is remembered, but it is meant to be pressed rather than set: it is a
decision per document.

**A `#` is not always a heading.** In a `.md` or a `.txt`, or a document you
have not named yet, a line starting with `#` is a heading. In a `.py`, `.sh`,
`.ini`, `.yml` or `.conf` it is a comment, and QUILL Lite says nothing and lists
nothing — otherwise a build script would announce "Heading 1" on most of its
lines. In an HTML document it is neither: there the headings are `<h1>` to
`<h6>`, and QUILL Lite reads and writes those instead.

### Hearing that you are in a list

Arrow into a list and QUILL Lite says **"Bulleted list, 5 items"**. Go a level
deeper and it says **"Level 2, 3 items"**. Arrow out and it says **"Out of
list"**.

This is the one cue in the set your screen reader gives you **everywhere except
here**. On a web page a list reaches the reader as a list with a count, and NVDA
says almost exactly this. In an editor a list is not a list — it is characters —
so the reader has nothing to go on, and a nested outline sounds like a run of
ordinary lines starting with a dash. The only thing separating level two from
level three is the number of spaces, counted by ear.

It works in **Markdown and in HTML**, over all three kinds of list:

| | Markdown | HTML |
|---|---|---|
| **Bulleted list** | `-`, `*`, `+` | `<ul>` |
| **Numbered list** | `1.`, `1)` | `<ol>` |
| **Definition list** | a line, then `: the definition` under it | `<dl>` |

A definition list also says **"Term"** and **"Definition"** as you move between
the two, because which of them you are standing in decides what the words mean
— and a definition list written inside out is not something you can see you have
done.

The counting rule matters and is easy to get wrong: **items are counted at your
own level, inside your own list.** A three-item list whose second item has four
sub-items is "3 items" at level one and "4 items" at level two, never "7". Two
sub-lists under two different bullets are two lists, not one.

What it never says:

- **Nothing as you move down a list.** That is what the caret does nearly all
  the time, and your reader is already speaking each item.
- **Nothing about `- - -` or `***`.** Those are horizontal rules, not one-item
  lists.
- **Nothing inside a fenced code block.** A `- ` in a code sample is a sample.
- **Nothing in a plain text document.** A letter is full of hyphens, and a cue
  that fired on them would be superstition rather than help.

**Turning it off — View ▸ Announce Lists (Ctrl+Alt+F5).** Its own switch, next
to the heading one and deliberately separate from it: reorganising an outline,
the level is the work; proof-reading the same file, it is a phrase between you
and every item. Like its sibling it says which way it went — "Lists will not be
announced", or "Lists announced as you enter them".

**And the status bar's List cell says something the speech never does:** which
item you are on. "Bulleted list, 4 of 9, level 2". Saying that aloud on every
arrow press would be too much; never being able to find out is its own problem,
and a cell answers on demand and costs nothing until you read it. **Enter** on
the cell turns the spoken cue off and on.


### All of them at once — the Heading Organizer

**Alt+Shift+O** opens **Heading Organizer...**: every heading in the document
as one list.

Arrow through it and each row says its level and its text — "Heading 2:
Installing". **Tab** demotes the one you are on, **Shift+Tab** promotes it, and
**Move Up** and **Move Down** take the heading *and everything under it* past
its neighbour. **Rename** changes the wording without moving anything, and
**Validate** checks the result against the rules a screen reader relies on: it
must start at Heading 1, and it must not skip a level on the way down.

There is a preview beside the list showing the section under whichever heading
you are on, which is how you tell two similarly named headings apart before you
move either of them.

Nothing happens to your document until you press **Apply**, and everything that
does happen is one change — one **Ctrl+Z** puts it all back.

This is the same window QUILL has, and it is here for the reason everything else
in this section is: restructuring a document with four separate commands means
holding its shape in your head while you change it, because nothing reads the
result back to you. In the list, the list *is* the shape.

Markdown and HTML documents only. Rich text headings are a font size rather than
a marker, so reordering them means moving formatted text rather than lines,
which is a different job.

### Rearranging them one at a time — Format ▸ Structure

| Key | What it does |
|---|---|
| **Alt+Shift+Left** | Promote heading — one level shallower |
| **Alt+Shift+Right** | Demote heading — one level deeper |
| **Alt+Shift+Up** | Move this whole section up, past whatever is above it |
| **Alt+Shift+Down** | Move this whole section down, past whatever is below it |
| **Alt+Shift+F5** | Select this section, subsections and all |
| **Ctrl+Alt+Shift+F5** | Move Section To… — pick a destination instead of a direction |

Until now QUILL Lite could make headings and walk between them but never move
them about, which left cut-and-paste as the only way to reorganise a document —
and that is the operation it is worst at. Moving a section by hand means
selecting from one heading to exactly the start of the next: a boundary you
cannot see, that you have to find by ear, and that takes your place in the
document with it when you get it wrong. **Alt+Shift+Up** does the same thing in
one keystroke and tells you it happened.

"Section" means the heading you are in plus everything under it, down to the
next heading at the same level or higher. Moving a Heading 2 takes its Heading 3s
with it.

**The keys always move.** They used to look for a heading at the same level under
the same parent and refuse when there wasn't one, which meant a document whose
headings step `#`, `##`, `###` never moved at all — in one of those, no heading
has a sibling anywhere. Now, when there is no sibling that way, the section trades
places with whatever *is* next to it, exactly as Word's outline Move Up and Move
Down do on these same keys. A first section inside its parent rises above the
parent's own heading.

**The moved section keeps its level.** Moving never renumbers your headings: press
the other key and you are exactly back where you were. A key that said "move" and
also rewrote `##` as `#` would have edited more than it said. Changing a level is
what Alt+Shift+Left and Alt+Shift+Right are for, and the two compose — move it,
then promote it.

**It says where the section landed**, not just what it jumped: *"Section moved
below Soup. Now 2 of 3 at this level."* That last part is what somebody looking at
the page gets for free and a listener cannot get any other way — the screen reader
says the text changed, never where in the outline the thing now sits.

There is one refusal no rule can fix, and it explains itself rather than closing
the door. In a strictly nested document everything below the heading you are in is
*inside* it, so there is nothing left for it to move below: *"Bottom of Heading 1.
Everything below is inside this section. Alt+Shift+Left promotes Heading 3 to make
it a sibling."* The key named in that sentence is read out of your own keymap, so
it stays right if you rebind it.

#### Select Section — Alt+Shift+F5

**Alt+Shift+F5** selects the section you are in, including every subsection, and
stops just before the blank line that separates it from the next one. Then ordinary
**Ctrl+X** and **Ctrl+V** put it anywhere — somewhere else in this document,
another document, or another program altogether. No new idea to learn, and it is
the honest answer to "move it somewhere there is no heading to move past".

It announces how much you now have: *"Selected Bread and 1 section under it, 7
lines"*, or *"Selected Bread, 4 lines"* when nothing is nested inside. The counts
are the point. Your screen reader tells you a selection changed; it does not tell
you how much is in it, and "did that take the sub-headings with it?" is the whole
question at that moment.

#### Move Section To… — Ctrl+Alt+Shift+F5

Pressing Alt+Shift+Up forty times is not a way to move a section across a long
document, and it is worse by ear than by eye: every press is a fresh announcement,
and you have to count them, because there is no page to glance at to see how far
you have got. **Ctrl+Alt+Shift+F5** asks where instead.

Two questions, both answered from a list you can type into:

1. **Which heading?** Every heading in the document, in the order they appear, one
   row each: `3 of 7, level 2 - Bread`. The position comes first so that two
   sections both called "Notes" are two different choices rather than a coin toss,
   and the level is there because "before Bread" means something different
   depending on whether Bread is a chapter or a paragraph heading. Type to narrow
   the list; the order never reshuffles itself as you type, because a list that
   reorders is one you cannot navigate by position. Focus starts in the search box,
   and **Enter** there moves you into the results rather than accepting whatever
   happens to be highlighted.
2. **Before it, after it, or inside it?** Three rows, because "next to that
   heading" is genuinely ambiguous and guessing would be worse than asking. **After
   it** is the one people expect to mean something narrower than it does: it puts
   your section below that heading *and everything under it*.

The whole move is **one edit and one Ctrl+Z**, and it says where the section
landed: *"Moved Salad before Bread. Now 1 of 3 at this level."*

**Inside it is the only one that changes a level.** It makes your section the last
one under the heading you chose, renumbers it and everything under it one step
deeper, and says the new level out loud: *"Moved Bread inside Soup, now Heading 3.
Now 1 of 2 at this level."* A renumbering nobody was told about would be a silent
edit, which is the one thing these keys must never do.

Two things it will not do, and it explains both rather than just declining:

- **A section cannot move inside itself.** Choose a heading that sits under the one
  you are moving and it says *"Sourdough is inside Bread, so Bread cannot move into
  it. Promote Sourdough first if you want them side by side."* Those headings are
  still listed rather than hidden — a heading you can see in your document and
  cannot find in the list has no way to explain itself.
- **Nothing goes deeper than Heading 6**, because Markdown cannot write one. It
  names the limit and offers **After it** instead.

**Escape at either question changes nothing and says nothing.** Nothing happened,
so there is nothing to announce.

Two more things to know about all six keys:

- **Promoting a Heading 1 leaves it a Heading 1.** It does not turn into ordinary
  text — losing a heading altogether is not what Alt+Shift+Left is for, and it
  would quietly drop the paragraph out of your headings list.
- **Moving and selecting sections need a Markdown or HTML document**, where a
  heading is written in the text. In a rich text document a heading is a font size
  rather than something the text says, so there is nothing to find and nothing to
  move; QUILL Lite says so rather than doing nothing. Promoting and demoting work in
  both.

These are QUILL for All's own six keys, and all six behave the same in both
editors. Anything you learn here you have learned in QUILL, and the sentences you
hear are composed in one place, so the two products cannot describe the same action
two different ways.

---

## Spell check

WordPad never had a spell checker. Notepad only got one recently. QUILL Lite has
one, and it is the same one QUILL for All uses.

**F7 checks the whole document.** It walks you through it one word at a time
with suggestions you can arrow through. For each word you can change it, change
every one like it, skip it, or add it to your dictionary so it is never
questioned again.

It **starts where your cursor is**, the way F7 has in Word since there was an
F7, and when it reaches the end it says so and carries on from the beginning.
Before version 1.0 it always started at the top, which walked you back through
everything you had already checked to reach the paragraph you were working in.
You can turn the wrap off in Preferences if you would rather it simply stopped.

| Key | What it does |
|---|---|
| **F7** | Check the whole document |
| **Alt+Shift+F7** | Suggestions for the word you are on |
| **Ctrl+F7** / **Ctrl+Shift+F7** | Go to the next / previous mistake |
| **Alt+Shift+L** | List every misspelling, with its line |
| **Ctrl+Alt+F9** | Add this word to your dictionary |
| **Ctrl+Alt+F7** | Turn checking-as-you-type on or off here |
| **Ctrl+Alt+Shift+F7** | Spelling Announcements: how a misspelling is said |

**Ctrl+F7** selects the word it lands on, so your screen reader reads it to you
when you get there -- and then, after a short pause, **spells it out**. That is
the part that matters: "receive" and "recieve" are the same sound, so hearing
the word tells you nothing, and the letters are the answer. Press the next key
and the spelling is cancelled unheard, so it costs you nothing when you did not
need it.

**Alt+Shift+L** lists every misspelling at once, with the line each one is on,
and Enter on a row goes there. That answers a different question from Ctrl+F7:
that one moves you to the next mistake, and this one tells you how many there
are and lets you choose which. Words you have chosen to ignore are left out.

**Alt+Shift+F7** and **Ctrl+Alt+F9** work from anywhere in a word, not only from
its first letter.

### While you type

When you finish a word that is not in the dictionary -- finish it, so a space or
a comma or a new line, not while you are still in the middle of typing it -- you
hear a **short falling blip** and the status bar says which word it was. It is a
sound rather than speech on purpose: speech there would interrupt the sentence
you are writing, which is the one moment you can least afford it.

You can silence the sound, have the word spoken as well, or change how long it
waits before repeating itself on the same word. All of that is in **Tools ▸
Spelling ▸ Announcements** (**Ctrl+Alt+Shift+F7**).

### Spelling Announcements

Twelve settings, in one window, in three groups.

**While you are typing.** Whether the sound plays at all, whether the word is
spoken too (off by default), and the shortest gap before the same word is
reported again -- zero means every time.

**Spelling a word out.** Whether words are spelled at all, and how. Plain
**letters** are fastest. The **phonetic alphabet** -- romeo, echo, charlie -- is
unambiguous where B, D, E, P, T and V are one sound with a rumour attached: a
fast voice, a poor speaker, a noisy room. **Both** is for learning a word rather
than checking one. You can also have capitals named, so "cap M, A, C, cap D"
tells MacDonald from Macdonald. An example box shows what your choices sound
like and says it out loud as you change them.

**When the letters follow.** Three pauses, because the right pause is not the
same in three places: longer in the F7 review, where you are stopped and
deciding; shorter when moving between misspellings, where you may be travelling;
and shorter again in a list of suggestions, where you are arrowing. Each can be
switched off on its own.

QUILL has the same twelve settings under **Spelling** in its Settings window, so
tuning this once tunes both.

### The word you are on: the Applications key

With the cursor in a word QUILL Lite thinks is misspelled, press the
**Applications key** (or Shift+F10, or right-click) and **the first Down arrow
lands on a suggestion**. **Enter** replaces the word. No dialog opens, the
cursor does not move, and there is nothing to arrow past first.

That is the whole point of this menu. A sighted person finds a misspelling by
looking for a red squiggle and right-clicking it; you have no squiggle, so the
Applications key *is* the squiggle, and what it says first should be the answer.

Under the suggestions there is a separator and then **one row** — *Spelling
Actions for "wrold"* — and then the ordinary rows: Undo, Redo, Cut, Copy, Paste,
Delete, Select All. That order never changes. The part that varies in length is
at the **top**, so everything below the suggestions is always where you left it,
and what you learn is not a row number but "after the suggestions, the menu is
the menu".

Inside **Spelling Actions**:

| Row | What it does |
|---|---|
| **Ignore Once** | Skip this one place. Nothing is remembered after you close the window. |
| **Ignore in This Document** | Stop reporting this word anywhere in this document, until you close it. |
| **Add "word" to My Dictionary** | Keep it for good, in your own dictionary. |
| **Add to This Document Only** | Keep it beside this file, so anyone who opens the file gets it too. |
| **More Suggestions...** | The full list, in a window you can arrow through. |
| **Check Document...** | The F7 review, from here. |
| **Next / Previous Misspelling** | Move on without leaving the keyboard. |

QUILL's menu is the same menu, in the same order, with one extra dictionary in
it (it has projects; QUILL Lite opens files).

Every row names the word it is about, so a menu you reached by keyboard still
tells you what it is going to do. On a word that is spelled correctly there is
no Spelling submenu at all -- just the ordinary edit rows.

Ignoring is honoured everywhere: a word you have ignored stops being announced
as you type, stops being a stop for **Ctrl+F7**, and stops being offered by
**Alt+Shift+F7**. To keep a word for longer than the session, add it to a
dictionary.

### When it stays quiet

Some files are not writing at all. They hold settings and instructions that
programs read, and they are full of made-up words, abbreviations and names that
no dictionary contains. Checking one of those as you type would give you a
constant stream of warnings that are every one of them wrong.

So **QUILL Lite does not check those files as you type.** It recognises them by
the kind of file they are, and it tells you once when you open one, so you are
never left wondering whether something is broken.

If you want checking in one anyway, press **Ctrl+Alt+F7**. It changes only the
document you are in — a letter and a settings file open at the same time can
quite happily disagree about this. **Tools ▸ Spelling** shows a tick beside
**Check While Typing** so you can always see which way it is set.

**F7 always works, in every file.** Staying quiet is only about what happens
when you have not asked. If you ask for a check, you get one.

### Your dictionary

Words you teach QUILL Lite are yours, kept in QUILL Lite's own folder. If you also
use QUILL for All, one setting in Preferences makes both share the same list, so
a word taught in either is known to both.

A single document can also have its own short list of words, kept in a small
file beside it. That is useful for names that belong to one piece of work and
nowhere else.

---

## What is this character?

**Ctrl+Shift+C** tells you exactly which character the cursor is on — its name,
and what it does to a search.

This sounds like a small thing and is not. Your screen reader says "space" for
several different characters that look identical and behave differently, and one
of them is very often the reason a search is not finding something you can
plainly see is there.

**Ctrl+Alt+C** opens the full description in a window you can read line by line.

---

## The status bar

**F6** takes you into it — it is **Navigate ▸ Status Bar**, because going there
is a move rather than a setting. The arrow keys and **Home**/**End** move along
it, **Enter** acts on the part you are on, and **Escape** puts you back in your
document. Each part says its own name and value.

**View ▸ Status Bar** (**Alt+Shift+B**) takes the bar off the screen
altogether, the way Notepad's does, and puts it back. Nothing is lost when it is
away: **Ctrl+Shift+G** speaks the counts, **Ctrl+Alt+W** speaks the line widths
— the longest line, which line it is, and the average, which is what you want
when you are formatting for a braille display or a narrow window — and **Ctrl+G**
asks for the line number
the Position part would have shown you. F6 with the bar hidden says so rather
than doing nothing.

| Part | What it tells you | Enter does |
|---|---|---|
| **Status Message** | The last thing QUILL Lite told you, so speech you missed can be heard again | repeats it |
| **Position** | Which line and column you are on, out of how many lines | Go to a line |
| **Word Count** | How many words the document has | repeats it |
| **Character Count** | How many characters, spaces included | repeats it |
| **Selection** | How much is selected, or "No selection" | repeats it |
| **Typing Mode** | Whether typing inserts or overwrites | switches between them |
| **Tab Mode** | Whether the Tab key types a tab or indents the line | switches between them |
| **Format** | Which of the four kinds this document is: plain text, Markdown, HTML or rich text | rings on to the next kind |
| **Heading** | Which heading you are inside | lists every heading |
| **List** | Which list you are inside, how many items, which one you are on | stops or resumes announcing lists |
| **Dictation** | What dictation is doing: off, listening, hearing you, writing, spelling, or waiting for the wake phrase | starts or stops dictation |
| **Encoding** | How this file stores its letters and accents | change it |
| **Line Endings** | How this file marks the end of a line | change it |
| **Saved State** | Whether you have unsaved changes | saves |

Fourteen cells, in that order. Six of them are worth pointing out.

**Typing Mode** is the one you cannot find out any other way. Every Windows
editor has an overwrite mode, where what you type replaces the letters already
there instead of pushing them along, and none of them will tell you which mode
you are in — you find out by typing over a sentence you meant to keep. Press
**Ctrl+Alt+Shift+W** to switch, or **Enter** on this part of the status bar.

The **Insert** key switches it too, because the editing control answers that key
whether QUILL Lite asks it to or not. QUILL Lite does not claim the key — it is
NVDA's and JAWS's own modifier and taking it would fight your screen reader —
but it does watch for it, so this part of the status bar stays right either way.

**Tab Mode** is the same idea. QUILL Lite starts where Notepad does: the **Tab**
key types a tab character. Switch it with **Ctrl+Alt+Shift+I** and Tab indents
the whole line instead, which is what QUILL does by default and what you
probably want when the file is code. **Shift+Tab** outdents either way, so a tab
you did not mean to type can always be taken back without switching modes first.

**Encoding** and **Line Endings** are the two things that decide whether your
file opens properly on somebody else's computer, and almost no other editor
shows them at all. You will rarely need to change them — but when a file arrives
looking like nonsense, this is where the answer is.

In a **rich text** document these two read **"RTF (rich text)"** and **"Not
applicable (rich text)"**, because a rich document has neither: RTF stores an
accented letter as an escape sequence of its own and marks a paragraph its own
way. They used to read "UTF-8" and "CRLF" there, which are the two answers a
plain file gives — a cell stating a fact about a file that has no such fact.

Both cells answer for the file you actually have. A file that arrived in a
format this window cannot offer — UTF-16 big-endian, say, or the classic-Mac
single-CR line ending — shows a **keep as is** row and stays in it, so
pressing Enter and confirming cannot quietly convert a file you only opened to
read. See [How this file is written](#how-this-file-is-written-encoding-and-line-endings).

**List** answers the question the speech deliberately does not. Entering a list
you hear "Bulleted list, 5 items"; this cell also tells you **which item you are
on** — "Bulleted list, 4 of 9, level 2". Saying that aloud on every arrow press
would be too much to listen to, and having no way at all to find out is its own
problem when you are halfway through reordering nine things.

**Format** is what decides the rest. It says whether this document is plain text,
Markdown, HTML or rich text, and that one fact decides what **Ctrl+B** writes,
what the heading keys write, which of the two tag pickers the Insert menu offers,
and whether the List part above has anything to say. QUILL Lite reads it from the
file name; **Enter** here rings on to the next kind and says its name, and
**Ctrl+Alt+F6** goes straight to one. See [Four kinds of
document](#four-kinds-of-document).

**Status Message** exists because speech is gone the moment it is spoken. If you
missed something QUILL Lite said, this is where you go to read it again.

---

## Reading a selection without risking it

**Alt+Shift+U** opens the **Review Buffer**: a copy of what you have selected,
in a window of its own, that cannot be edited.

The point is what you cannot do in it. Reading a long selection back means
arrowing through it, and arrowing through your own document while a selection is
live means the next character you type replaces all of it. A copy that refuses
to be edited removes that whole class of accident. Escape closes it and puts you
back where you were, with the selection intact.

---

## Copying and pasting more than one thing

The Windows clipboard holds one thing at a time. QUILL Lite gives you three ways
around that, in **Edit ▸ Clipboard**.

**The copy tray** is twelve numbered slots that survive closing the app. Copy
into a slot with **Ctrl+Alt+Y**, and paste from any of them an hour later with
**Ctrl+Alt+V**. **Ctrl+Alt+Shift+Y** empties it.

**Ctrl+Alt+Y** takes the next free slot, which is fine until you want to *choose*
the number — and choosing is the whole point of a numbered slot, because a number
you picked is one you can remember. **Alt+Shift+Y** offers all twelve, each row
saying what is in that slot now, so nothing gets overwritten unheard.

**The collector** gathers things up. Each **Alt+Shift+S** adds what you have
selected to one growing pile, and **Ctrl+Alt+Shift+G** pastes the whole pile.
This is what you want when you are pulling five quotes out of a long document.
**Ctrl+Alt+Shift+C** empties the pile.

**The clip library** is where clips you want to keep go. **Ctrl+Alt+M** keeps
what you have selected, and **Ctrl+Alt+Shift+M** opens the list to paste one back.

It can also fill itself. **Preferences ▸ Keep everything I copy in the clip
library** turns that on, and then every copy and every cut you make inside a
QUILL Lite document is added automatically, up to the last two hundred. It is off
until you ask, and the reason is worth stating plainly: a history of everything
you copy is a file on your disk holding whatever you last took out of a
document, a password you had pasted somewhere included. It never sees what you
copy in other programs.

And **Ctrl+Shift+V** pastes text with none of its formatting, which is what you
want when something copied from a web page arrives wearing its own fonts and
colours.

**Ctrl+F8** copies the whole document. Select All then Copy does the same thing
in two keys and leaves the document selected afterwards, which is a hazard when
you cannot glance at it: the next character you type replaces everything.

---

## Links

**Ctrl+K** puts a link in, in whatever markup the document is written in —
`[text](address)` in Markdown, `<a href="address">text</a>` in HTML. Select the
words first and they arrive in the box already; leave the display box empty and
the address shows as its own text.

Rich text says so instead: a link there is something the control owns, and
writing brackets into one would just put brackets on the page.

---

## Working on lines

**Edit ▸ Lines** is everything that happens to whole lines. It is in Edit
because line work *is* editing — it belongs beside Cut and Paste rather than
three menus away from the text it changes.

The first group works on the line the cursor is already on, which is usually the
one you want.

**Move Line Up** (**Ctrl+Shift+Up**) and **Move Line Down**
(**Ctrl+Shift+Down**) move the current line past its neighbour. Reordering two
lines any other way means selecting one, cutting it, finding the new place and
pasting -- four steps, each of which leaves the cursor somewhere the last one
did not. **Duplicate Line** is **Ctrl+D**, and **Join Lines**
(**Ctrl+Alt+Shift+J**) pulls the line below onto the end of this one.

**Delete Line** is **Ctrl+Shift+Delete**. **Delete to Start of Line**
(**Ctrl+Shift+Backspace**) and **Delete to End of Line**
(**Ctrl+Alt+Shift+Delete**) remove everything to one side of the cursor, and
**Delete Paragraph** (**Ctrl+Alt+Shift+Backspace**) takes the whole paragraph.

Each of these tells you what it did, and tells you when it did nothing --
"Already the first line" is a different fact from silence, and you should not
have to press an arrow key to find out which one you got.

### Putting lines in order, and tidying them up

The rest of **Edit ▸ Lines** works on what you have selected, or on the whole
document if you have not selected anything.

Sort lines (**Ctrl+Alt+S**, or **Ctrl+Alt+Shift+S** for Z to A), **Reverse
Lines** (**Alt+Shift+Z**) and **Number Lines** (**Alt+Shift+N**) change the
order; **Remove Every Blank Line** (**Ctrl+Alt+K**), **Remove Duplicate Lines**
(**Ctrl+Alt+D**), **Trim Trailing Spaces** (**Ctrl+Alt+T**) and **Tidy
Whitespace** (**Ctrl+Alt+Shift+T**), which collapses the runs of spaces and tabs
that arrive with pasted-in text, clean them up.

**Remove Every Blank Line** means every one, including the blank lines between
your paragraphs -- it is the cure for text copied out of a web page that arrives
double-spaced, not a tidy-up you want on prose. A line of nothing but spaces
counts as blank, because it is blank to everyone reading the document and to
every tool that will ever open it. QUILL has this command under the same name,
beside a second one called **Trim Blank Lines at the Ends**, which takes only
the blank lines before the first line of text and after the last; QUILL Lite has
just the one.

Each one counts as a single undo, so **Ctrl+Z** takes back the whole sort rather
than putting back one line at a time.

### Quoting, wrapping, and throwing lines away

**Ctrl+Shift+Q** puts `> ` in front of the lines you have selected, the way an
email reply does, and **Ctrl+Alt+Shift+Q** takes the marks off again.

**Alt+Shift+W** is **Hard Wrap Lines**. It asks for a width and re-flows the
lines so none is longer than that, keeping paragraphs apart and never breaking a
word. This changes the document, so it is saved -- which is what makes it
different from **View ▸ Word Wrap**, which only changes what you see.

**Alt+Shift+X** is **Delete Lines Containing**. Type what the lines to go have
in them -- taken exactly, not as a pattern -- and they are removed. It says how
many went, and **Ctrl+Z** takes them all back in one step. This is log triage,
which by ear otherwise means reading the whole file twice.

All three work on what you have selected, or on the whole document if you have
selected nothing.

### Commenting lines out

**Ctrl+/** comments the lines you have selected out, and pressing it again brings
them back. The prefix comes from the file's name — `# ` in a `.py`, `.yml`,
`.ini` or `.conf`, `-- ` in a `.sql`, `<!-- -->` in HTML and Markdown, `// ` in
anything else — which is the same rule QUILL follows, so a file commented in one
uncomments in the other. It says how many lines it changed.

An unsaved document gets `// `, because there is nothing else to go on. Save it
once under the name you mean and the key gets it right from then on.

### Tabs or spaces

**Tools ▸ Indenting** has **Convert to Spaces** (**Alt+F11**) and **Convert to
Tabs** (**Alt+F12**), which rewrite the indentation at the start of each line
without touching anything else. Four spaces to a tab. It is the single most
common change anybody makes to somebody else's file.

### Changing case

**Tools ▸ Change Case** has five. UPPERCASE (**Ctrl+Shift+U**), lowercase
(**Ctrl+Shift+K**) and Title Case (**Ctrl+Shift+T**) are the ones you would
expect. **Sentence case** (**Ctrl+Alt+Shift+U**) puts a capital at the start and
lowers the rest, which is what a heading typed in shouting needs, and **Invert
Case** (**Ctrl+Alt+Shift+N**) swaps every letter, which is the cure for a
sentence typed with Caps Lock on.

All five work on what you have selected. **With nothing selected they change the
word the cursor is in**, which is what Word's Shift+F3 has always done -- and
which matters here more than it does for a sighted user: a whole document that
has changed case reads exactly the same out loud, so a chord half-pressed would
be a change you could not hear.

### Getting deleted text back somewhere else

**Restore Deleted Text** (**Ctrl+Alt+Shift+Z**) puts a recent deletion back **at
the cursor**, wherever the cursor now is. QUILL Lite remembers the last three, so
if what you want is not the last thing you deleted it offers a list with a
preview of each.

That is what makes it different from undo, and it is the reason it exists.
Ctrl+Z puts text back where it came from; this puts it where you are now, so
deleting a paragraph and restoring it further down is a way to *move* it that
never touches the clipboard -- which means whatever you were already carrying on
the clipboard is still there afterwards.

It remembers your last three deletions, and only the deliberate ones: the delete
commands above, not every character you backspaced over.

### Indenting

**Tools ▸ Indenting** has **Indent** (**Ctrl+]**) and **Outdent**
(**Ctrl+[**). They work on every line the selection touches, or on the line the
cursor is on if nothing is selected, and they say how many lines moved.

These matter more here than they look. QUILL Lite already goes quiet about
spelling in a `.json` or a `.py` file, which is an admission that people edit
configuration and code in it -- and for that person, moving a block in or out a
level is the single most common thing to want and the most tedious to do by
arrow key.

#### Asking how deep a line is

**Describe Indent Depth** (**Ctrl+Alt+Shift+V**) says how far the line you are on
is indented: "4 spaces", "1 tab", "1 tab, 3 spaces", or "No indentation".

This is the one question about a line that nothing else will answer. A screen
reader reads a line's *words*; it does not read the spaces and tabs in front of
them. So in a YAML file, a Python file or a deeply nested list, the shape of the
document -- which is most of its meaning -- is simply not there when you listen
to it, and there has never been a way to ask.

It also tells you something the words cannot: whether this line is indented with
the same *kind* of whitespace as its neighbours. A file where one line uses a tab
and the rest use spaces looks identical however carefully you read it, and in a
Python file it will not run.

#### Making Tab indent instead

By default the **Tab** key types a tab character, the way Notepad's does. **View
▸ Tab Key Inserts a Tab Character** is ticked to say so. Clear that tick --
**Ctrl+Alt+Shift+I** -- and Tab indents the whole line instead, announcing the
new depth as it goes. Working on code, that is usually the one you want.

**Shift+Tab** outdents in *either* mode. That is deliberate: it means a tab you
typed by accident can always be undone with one keystroke, without first working
out which mode you were in.

The status bar's **Tab Mode** part always says which one is on.

### Snippets — Alt+Shift+I

**Alt+Shift+I** opens **Snippets...**: every abbreviation you have, most used
first, with a preview of what each one writes. Choose one, press Enter, and it goes in at the
cursor.

This is the way in when you cannot remember the trigger. Abbreviations expanding
as you type is perfect for the six you use every day and no help at all for the
fortieth one, which you set up in March — and a manager is for *editing* them,
not for reaching them.

It is the same list either way. Anything here expands from its trigger too, and
anything you add in Manage Abbreviations appears here.

### Abbreviations

Type a short form, press space, and get the long one. Useful for an address, a
sign off, or anything you type often and would rather not spell out every time.

**Ctrl+Alt+A** manages your list. It is QUILL Lite's own list to begin with; if
you also use QUILL for All or Quill Inkwell, Preferences has a switch that makes
all three share one list.

**Alt+Shift+A** turns expansion off and on again, and **Tools ▸ Expand
Abbreviations** shows a tick when it is on. This is the one feature that acts
while you type, so the moment you want it off is usually the moment it has just
expanded something you meant to keep — which is too late to go looking for a
dialog. It is the same switch as the Abbreviations box in Customize Features,
reached in one keystroke.

---

## Nine lessons, inside the app

**Ctrl+Alt+F1** (**Help ▸ Tutorials...**) opens the lesson book. Nine lessons
in two tracks, about forty-two minutes in all if you did every one back to back,
which nobody does.

**Your first documents**

| Lesson | About |
|---|---|
| Open a file, and give it back unchanged | The one promise QUILL Lite makes, and the three things it remembers in order to keep it |
| Four kinds of document, and how to say which | What a plain, Markdown, HTML or rich document changes about the keys |
| Your documents are numbered | Getting between the things you have open |
| What to press when you are lost | F1, F6, Ctrl+F1, and Escape |

**Working in a document**

| Lesson | About |
|---|---|
| Selecting more than a few words | F8, extend mode, and taking a whole paragraph in one key |
| Finding your way back | Bookmarks, marks, and Go Back |
| Skimming something long | Headings, folding, and the headings list |
| Spelling, without a red squiggle | F7, the sound, and the Applications key |
| Asking a question about a document | AI help, from a standing start |

**How a lesson works.** The window has the list of lessons on the left and the
steps of the one you are on beside it. Each step is three things:

1. **What to press** — and it shows **your** key, not the shipped one, so a
   lesson stays right after you have rebound something in the Keyboard Manager.
2. **Why**, in a sentence. Not "press Control F6"; "the status bar is a row of
   cells you can arrow along, and three of them are the promise".
3. **What you should hear when it worked.** This is the part a manual never has
   and the part you most need, because nothing on the screen is going to tell
   you.

Some steps also carry a **Worth knowing** line for the thing that would
otherwise bite you later.

**Getting around it.** The window opens on **Contents**: a tree of the two
tracks with the lessons under them, and a filter box over it -- type part of a
name, or the word `here` for the lessons about the window you came from. Under
the tree are **Start**, **Read it all**, **The whole book as a document**, and
**Forget my progress**. The lesson page is the step in a read-only field you can
arrow through — and copy from with Ctrl+C — with five buttons under it:

| Button | What it does |
|---|---|
| **Try it** | Runs this step's command for you, exactly as its key would |
| **Next** | The next step, and reads it |
| **Back** | The previous step, and reads it |
| **Say it again** | Reads the step out in full |
| **Contents** | Back to the list, keeping your place |

**Try it** is why this is a window and not a document: a lesson can open the
thing it is teaching and then talk you through what you are standing in, so
you are never blocked on a key you have not learned yet.

There is also a **Follow me** tick box, and **in QUILL Lite it is greyed out**.
In the apps that have it, Follow me watches what changed in the app and moves
you on by itself. QUILL Lite's lessons have nothing for it to watch: every step
here ends in a sentence the editor already says out loud, so the step tells you
it worked and there is no state to poll. It is disabled rather than removed, so
that arriving on it tells you it is unavailable instead of leaving you hunting
a window for a control you last used in Quill Radio.

The window is a **peer**, not a dialog: it stays open beside your document,
Alt+F4 or Escape closes it, and QUILL Lite remembers which lessons you have
finished and where you had got to in the one you were in.

Every QuillVille app has the same window on the same key. The whole book is
also a document you can read straight through: **The whole book as a document**
opens `docs/tutorials.html` from beside the program, in your browser.

---

## The View menu

Seven switches and three sizes. Every one of them says its new state out loud
when you press it, so you never have to go and check.

| Key | Switch | Starts |
|---|---|---|
| **Alt+Shift+D** | **Dark Mode** — force dark, whatever Windows is set to | following Windows |
| **Alt+Z** | **Word Wrap** — long lines fold into the window instead of scrolling | on |
| **Ctrl+Alt+F3** | **Announce Headings** — say "Heading 2, Installing" on arrival | on |
| **Ctrl+Alt+F5** | **Announce Lists** — say "Bulleted list, 5 items" on entering one | on |
| **Ctrl+Alt+Shift+W** | **Overwrite Mode** — typing replaces instead of inserting | off |
| **Ctrl+Alt+Shift+I** | **Tab Key Inserts a Tab Character** — off means Tab indents the line | on |
| **Alt+Shift+B** | **Status Bar** — show or hide the bar itself | on |

Each row carries a tick that reads the true state, so arrowing onto it tells you
which way it is set without changing anything.

**The two announcement switches are per document**, not per app. A settings file
where every line starts with `#` and a letter with six real headings in it can
disagree about this, and they should.

**Overwrite Mode** is also on the status bar's **Typing Mode** cell — press
**F6**, arrow to it, and **Enter** toggles it. QUILL Lite watches the **Insert**
key go past and reports what it did, but never claims it: Insert is your screen
reader's own modifier.

### Making the text bigger or smaller

| Key | What it does |
|---|---|
| **Ctrl+=** | Increase Text Size |
| **Ctrl+-** | Decrease Text Size |
| **Ctrl+0** | Reset Text Size |

This is the size on the screen and nothing else. It changes nothing in the file,
and it changes nothing about what a screen reader says. **Ctrl+Shift+.** and
**Ctrl+Shift+,** are a different thing entirely — they change the font size of
the text you have *selected*, in a rich text document, and that does go into the
file.

### What is in this document, in numbers

**Ctrl+Shift+G** (**Document Statistics**) speaks the size of the whole
document: characters, words, lines and paragraphs. **Ctrl+Alt+W** (**Line
Statistics**) answers the narrower question for the line you are on, which is
what you want when you are formatting to a width — a braille display, a narrow
window, a column limit in a code file.

---

## Undo, and getting text back

| Key | What it does |
|---|---|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+Alt+Shift+Z** | **Restore Deleted Text** — put a recent deletion back **where the cursor is now** |

The first two are the ones you know. The third is the one worth learning:
**Ctrl+Z puts deleted text back where it came from, and Restore Deleted Text
puts it where you are standing.** That is the difference between undoing a
mistake and moving a paragraph, and it means a delete is never a one-way trip
even after you have typed something else.

The big commands are **one undo each**, deliberately. Sorting nine hundred
lines, applying a heading, moving a whole section, restoring an earlier version
of the file, tidying every run of whitespace — each of those is a single
**Ctrl+Z**, not one per line. A command that took one keystroke should take one
keystroke back.

---

## Finding a command

**Ctrl+Shift+P** opens a search box for commands. Type part of what you want —
"sort", "bookmark", "print" — and pick it from the list. You do not have to
remember which menu it lives in.

Each command shows its keyboard shortcut beside it, which is a comfortable way
to learn the keys over time — and it shows **your** key, so the palette stays
right after you have rebound something.

### One box for everything — Go To Anything

**Ctrl+Alt+Shift+A** (**Navigate ▸ Go To Anything...**) is the palette's
bigger sibling: one box that searches **commands, headings and bookmarks
together**. Type three letters and the list has every command whose name
matches, every heading in this document, and every bookmark you have set.
Enter runs the command or goes to the place.

**It starts switched off**, and the reason is not that it is a poor feature.
The Command Palette, the headings list (**Ctrl+Alt+L**) and the bookmark list
(**Alt+Shift+G**) each already answer their own part of this, so a fourth front
door is a fourth thing to explain to somebody who has not asked for it. Turn it
on in **Tools ▸ Customize Features** (**Ctrl+Alt+F10**) if you would rather
have one key than three.

Headings only appear in it for a **rich text** document, because that is where
QUILL Lite can ask the control itself what the headings are. In a Markdown or
HTML file the headings list on Ctrl+Alt+L is the one to use.

---

## The window

QUILL Lite opens **maximized**, and after that it opens the way you left it. Make
it smaller and that size comes back next time; put it back to full screen and so
does that.

Maximized is the default because a small window is where text gets cut off and
where a list shows four rows on a screen with room for thirty -- and neither
costs anything to the person who chose the size. It is one keystroke to change
and QUILL Lite will not ask again.

Every app in the family behaves the same way now: QUILL, Quill Radio, Cast,
Weather, Audio Studio, Inkwell, the Converter, the Media Player and Beacon.

---

## Closing a lot of windows at once

**Window > Close Other Documents (Ctrl+Shift+F4)** keeps the document you are in
and closes every other one. QUILL has had it since 2026-06; QUILL Lite has it now
too, on the same key, because a key you learn in one editor should work in the
other.

If any of those documents has unsaved changes, you are asked about it -- and the
question carries two answers that settle the rest at once:

- **Save All** saves this document and every other one waiting behind it,
  without asking again. A document that has never been saved still asks you
  where to put it.
- **Don't Save Any** closes the rest and loses their changes, without asking
  again. There is no undo for that one.
- **Save** and **Don't Save** apply to the document in front of you only, and
  you are asked about the next one.
- **Cancel** stops the whole thing. Whatever is still open stays open, and you
  are told how many closed before you stopped it.

The question says how many more documents are waiting, so you know at the first
prompt whether this is one more keystroke or sixty-seven.

**Enter answers Save**, never one of the two that lose work. If a save fails --
a full disk, a file that has gone read-only -- the close stops there rather than
treating a failed save as permission to throw the document away, and "Save All"
stops meaning "save all" until you say so again.

---

## Changing what a key does

**Tools ▸ Keyboard Manager** (**Ctrl+Alt+Shift+R**) is where every key in
QUILL Lite can be changed. The list has every command with the key it answers to;
type part of a command's name to find it, and press **Enter** on a row to give it
a different key.

### Finding out what a key already does

The other question is the harder one: *is this key free?* Press **Record a Key**,
then press the combination you are thinking of. QUILL Lite says what it does today
-- "Ctrl+S is File ▸ Save" -- or says it is free. That is faster and more
reliable than reading a list of two hundred rows.

### When a key is taken

Assigning a key somebody else already has does not silently steal it and does not
silently refuse. QUILL Lite names the command that owns it and asks. If you say
yes, that command is left with **no key** until you give it one -- which is the
honest outcome, because a key claimed twice means one of the pair never fires and
nothing tells you which.

### When another program has the key

Some programs claim a key across the whole of Windows -- Google Drive takes
**Ctrl+Alt+G**, and it is not the only one. A key claimed that way never reaches
QUILL Lite at all: Windows hands it to the program that registered it, even while
QUILL Lite is the window you are typing in. The command is not broken and the key
is not misassigned; the keystroke simply goes somewhere else.

This used to be invisible, which made it look like a bug in the editor. Record a
Key now says so -- "already claimed by another application running on this
computer" -- and so does the Keyboard Manager if you assign a key somebody else
has taken. It is a warning rather than a refusal: the key may be yours again
tomorrow when that program is not running, and it is not this editor's place to
forbid a key you chose deliberately.

QUILL Lite cannot say *which* program. Windows does not offer the owner's name,
and guessing from a list of the usual suspects would be wrong the first time you
installed something that was not on it.

### What cannot be changed

**Insert is never bindable.** It is the key NVDA and JAWS use as their own
modifier, and taking it would take away the key you would need to get it back.
QUILL Lite watches it go past -- that is what the Typing Mode cell reads -- but
never claims it. A key on its own with no Ctrl, Alt or Shift is refused too: it
would type itself instead.

### Putting things back

**Reset to Default** puts the command you are on back to the key QUILL Lite ships
with. **Reset Everything** does it for all of them, after asking. Nothing is
saved until you press **Save**, so Escape leaves your keys exactly as they were.

**Check for Problems** reports anything wrong with the set as a whole: a key
claimed twice, a key QUILL Lite cannot read, and -- the one you would otherwise
never find out about -- a key Windows will accept and then never actually send to
a menu, so it is assigned and inert.

Your changes live in your own settings folder and only what you changed is
written down, so a key we improve in a later version still reaches you.

---

## Sounds

### Quiet mode

**Alt+Shift+M** silences every sound at once, and pressing it again brings them
back. One key, because "make it stop" is something you need *while* the noise is
happening -- on a call, in a quiet room, or having simply had enough of an
earcon today. A feature you have to go and find is one that does not help at the
moment you need it.

It is the blunt instrument on purpose; the per-event answer is one menu item
away. It is shared with QUILL, so silencing one editor silences both -- which is
what somebody who wanted quiet meant. **Tools ▸ Quiet Mode** carries a check
mark that reads the true state.

### Every sound, in a list you can hear

**Tools ▸ Sound Scheme** (**Ctrl+Alt+Shift+O**) is every sound QUILL Lite can
make, in a list you can hear. Arrow through it and each event plays as you land
on it -- that is what turns a list of names into a catalogue, and you can turn
it off with the checkbox under the list if you would rather move in silence.

Each row says everything about itself: the event, whether it is switched on,
which file it plays and how long that file is. The buttons underneath act on
whichever row you are on:

| Button | What it does |
|---|---|
| **Play** | Play this event's sound now, even if the event is switched off |
| **Switched on** | Silence this one event without changing which sound it has |
| **Browse...** | Use a WAV file of your own |
| **No Sound** | Remove the sound from this event entirely |
| **Use Default** | Put this one event back to the sound the scheme ships |

**Save As Scheme** saves the whole set under a name of your own. A scheme is an
ordinary folder with the sounds in it, so you can copy it, back it up, or send
it to somebody. **Restore All Defaults** puts every event back and switches them
all on, and it cannot half-succeed -- the sounds QUILL Lite ships are never
overwritten, so getting back to them is always one press.

QUILL opens the same window over the same schemes, so a scheme you build in one
is offered in the other.

---

## Making QUILL Lite smaller (or larger)

**Tools ▸ Customize Features** (**Ctrl+Alt+F10**) lets you switch whole parts
of QUILL Lite off. Turning something off removes it from the menus **and**
unhooks its keys, so it is properly gone rather than just hidden.

That is how QUILL Lite stays small without being poor: you take out what you do
not want, rather than learning to ignore it.

### Profiles: four ways to say it in one word

The **Profile** box at the top is the short way. **Choosing one sets every
checkbox below, there and then** -- there is no second button to find. Nothing
is saved until you press **Save**, so you can look at what a profile would do
and change your mind.

Under the box is a **read-only description you can read line by line**, and it
answers two different questions. First, what the profile *is*, in its own words.
Then what it would actually *do* to the app in front of you: how many of the
20 areas it keeps and which, which ones it removes, and anything else it
changes -- Notepad, for instance, also makes **Ctrl+N** create a plain text
document. **F1** on the Profile box reads the same thing.

What is spoken when you choose a profile is the short version -- "Notepad
profile: 2 of 20 features on. New documents will be plain text. Nothing is saved
until you press Save." -- because your screen reader is already reading the name
and the description is there to be read at your own pace.

**Custom puts everything back.** Arrow onto a profile you did not mean and
select **Custom**: every checkbox returns to how you found it when the window
opened. Custom is also what the box reads back as soon as you tick or untick
anything yourself, which is not a warning -- picking your own is what the list
is for.

Afterwards the boxes are just boxes again: change any one of them without having
to leave the profile first. **Use Profile** is still there for when you have
hand-edited a profile and want to start it over.

**The same four profiles are in Preferences**, at the top, with the same
description box. "Make this Notepad" is a preference like any other, and you
should not have to know that a dialog called Customize Features is where it
lives. Preferences offers the whole answers; the 20 individual
checkboxes stay in Customize Features.

Here is what each one is, at a glance and then in full.

| Profile | Areas on | Ctrl+N makes |
|---|---|---|
| **Recommended** | 16 of 20 | plain text (unchanged) |
| **Everything** | 20 of 20 | plain text (unchanged) |
| **WordPad** | 5 of 20 | **rich text** |
| **Notepad** | 2 of 20 | **plain text** |

#### Recommended

**What a new install is.** 16 of the 20 areas: rich text, headings, Markdown and
HTML, bookmarks, the line tools, the clipboard history, printing, abbreviations,
the Selection submenu, spell check, Matches, Go Back and Go Forward, the Command
Palette, Describe Character, text size and dictation.

**Off:** autocorrect, timestamped backups, Go To Anything and AI help. Those four
are not missing features; they are the ones that would be *wrong* on by default
rather than merely unused. Autocorrect rewrites a configuration file's quotes.
Backups quietly fill a folder. Go To Anything is a fourth way to jump when the
command palette, the headings list and the bookmark list already cover it. And AI
help sends what you ask about over the internet, which is not something a default
gets to decide for you.

**Choose this** to get back to the shipped answer after experimenting.

#### Everything

**All 20 areas on**, including those four -- and that includes **AI help**, which
is the one area here that sends anything off this computer, so choose this profile
only if that is what you meant. Autocorrect will straighten your quotes and turn
two hyphens into a dash (and nothing else -- it does not capitalise sentences),
every save keeps a dated copy under your data folder, and Go To Anything joins the
palette and the two lists.

**Choose this** if you would rather turn things off as they annoy you than find
them one at a time.

#### WordPad

**What WordPad was.** Rich text you can format, print, and check the spelling
of: bold, italic, underline, headings, alignment, bullets, indenting and line
spacing, plus Find and Replace, printing and text size. Five of the 20
areas.

**Off**, all fifteen of them: the writing tools behind the formatting. No
line tools (Edit ▸ Lines) and no Change Case, no clipboard history or Copy
Tray, no bookmarks, no abbreviations, no Selection submenu, no Matches list, no
Back and Forward, no Command Palette, no Go To Anything, no Describe Character,
no dictation, no autocorrect, no backups, **no Markdown or HTML** (Ctrl+B in a `.md` goes back
to meaning rich text and saying so), and **no AI help**.

**Ctrl+N makes a rich text document.** That is the half of this name a list of
menus cannot say, and it is why choosing WordPad changes a setting as well as a
set of checkboxes.

**Not in real WordPad:** the spell checker. It is kept because a word processor
without one in 2026 is a surprise rather than a simplification.

**Choose this** for letters, notes and anything you want to look like something.

#### Notepad

**The smallest QUILL Lite gets**, and the one most people arriving here are
replacing something with. Two of the 20 areas: **printing** and **text
size**.

**Off**, all eighteen of them: the Format menu and everything under it,
headings, Markdown and HTML, bookmarks, the line tools, Change Case, the
clipboard history, abbreviations, the Selection submenu, spell check, Matches,
Back and Forward, the Command Palette, Go To Anything, Describe Character,
dictation, autocorrect, backups and AI help. Nothing Notepad does not have -- which is the
point of choosing it.

**Ctrl+N makes a plain text document**, and the Save As dialog stops offering
you formats you have turned off.

**What stays that you might not expect**, because Notepad has always had them:
Find, Find Next, Replace, Go To Line, Select All, Insert Date and Time, Word
Wrap, the font picker, the status bar and Undo. And **Tools ▸ File Encoding and
Line Endings**, which Notepad only grew recently and which is most of what a
Notepad replacement is *for*: getting a file to save back exactly as it arrived.

**Choose this** for configuration files, logs, quick notes, and anything where a
document that secretly carries formatting would be a problem.

#### Moving between them

Nothing is one-way. Choosing **Notepad** and then **Everything** puts it all
back, including the Format menu and the keys that go with it. The one thing a
profile does *not* put back is a setting you changed by hand afterwards --
profiles only ever set what they claim.

Two things are never switchable whatever you choose: **Tools ▸ Preferences** and
**Customize Features** themselves, because switching off the menu that holds the
switch is a door that locks from the inside.

### Searching the list

Twenty checkboxes is a long way to Tab through, so the box below the profile
row filters them as you type. It matches what an area **does** as well as what it
is called, so typing "curly quotes" finds Autocorrect and typing "dictionary"
finds Spell check. The line under the box says how many are left, and **Down**
from the box moves straight into the list.

### The 20 areas

| Area | What goes | Starts |
|---|---|---|
| **Rich text and the Format menu** | Bold, headings, alignment, bullets, spacing | on |
| **Heading navigation** | Next and previous heading, the headings list | on |
| **Markdown and HTML** | The two tag pickers, Document Language, and markup Bold | on |
| **Bookmarks** | All nine, and the list | on |
| **Line tools and change case** | Edit ▸ Lines, Tools ▸ Change Case | on |
| **Copy Tray and the clip library** | Edit ▸ Clipboard (Cut, Copy, Paste and Copy All stay) | on |
| **Printing** | Print and Page Setup | on |
| **Abbreviations** | Short forms, and the list that manages them | on |
| **Spell check** | Tools ▸ Spelling, and checking as you type | on |
| **The Selection submenu** | F8 selecting, whole-structure selecting, marks | on |
| **The Matches submenu** | All Matches and Count Occurrences (Find itself stays) | on |
| **Go Back and Go Forward** | The trail of places you jumped from | on |
| **The Command Palette** | Ctrl+Shift+P, the search box for commands | on |
| **Describe Character** | What the character under the cursor actually is | on |
| **Text size** | Bigger, smaller, and reset | on |
| **Dictation** | Tools ▸ Dictation: speaking into the document, and choosing the microphone | on |
| **Autocorrect while typing** | Curly quotes and em dashes (see below -- it does not capitalise sentences) | **off** |
| **Timestamped backups** | A dated copy kept every time you save | **off** |
| **Go To Anything** | One box that searches everything at once | **off** |
| **AI help (sends your text to QUILL's servers)** | Tools ▸ AI: summarize, rewrite, proofread, explain, and questions about a document | **off** |

The last four start switched off, and they sit in this same list rather than
being hidden away, because something you cannot find might as well not exist.

**AI help is off for a different reason from the other three.** Those would be
*wrong* on -- autocorrect rewriting a configuration file's quotes, backups
quietly filling a folder. This one is off because using it sends the passage
you ask about over the internet, and that is not a choice anybody else gets to
make for you. Its row in Customize Features spells out the whole trade before
you switch it on, and an area that is off owns nothing: no menu, no keys, no
sign-in stored on disk, and no connection of any kind.

**And switching it on is not enough.** Before anything is sent, QUILL Lite shows
you the whole agreement -- what is sent, what QUILL keeps, what it does not
keep, what OpenAI does with it, and how to say no -- and nothing happens until
you accept it. Turning the area on and declining the agreement leaves the menu
there and the feature unusable, which is deliberate: you did turn it on, and
what you declined was the sending. The switch does not flip itself back behind
you.

There are **three ways to the same agreement**, because the place you look for
it depends on which part of the app you already know:

- **Tools ▸ AI ▸ Privacy Agreement...** (**Ctrl+Alt+Shift+K**) -- read it, accept
  it, or take it back. Taking it back also signs this computer out, because
  keeping the sign-in for a service you have just withdrawn from would be
  keeping the key to the thing you declined.
- **Preferences**, where a tick box says *Use QUILL's free AI help*. Ticking it
  shows the agreement; unticking it withdraws.
- **Customize Features**, where switching the area on asks you straight away.

All three read and write the same answer, so none of them can disagree with the
others. If the agreement ever changes in a way that matters -- what is sent, or
what is kept -- you will be asked again rather than the old answer being taken
to cover the new thing.

Autocorrect is off because curly quotes are lovely in a letter and unhelpful in
a settings file. Backups are off because they quietly fill a folder. Go To
Anything is off because the command search, the headings list and the bookmark
list already each do their own part of the job.

**Autocorrect is two rules, and switching the area on does not switch either of
them on.** The area decides whether QUILL Lite has the feature at all; two tick
boxes in **Tools ▸ Preferences** decide which rules run -- **Curl quotes as I
type** and **Turn two hyphens into an em dash** -- and both start off, so turning
the area on and typing a quote correctly does nothing until you tick one. They
are separate because they are different opinions: plenty of people want the long
dash and not the curly quotes. Neither runs in a plain text, source or
configuration document whatever the boxes say, because a curly quote in a `.json`
is a syntax error and no setting can express "except in code".

And there is no third rule: QUILL Lite does **not** capitalise the start of a
sentence, has never done so, and will not start doing it behind you.

Two things are never switchable, on purpose. **Tools ▸ Preferences** and
**Customize Features** stay, because switching off the menu that holds the switch
is a door that locks from the inside. And **File Encoding and Line Endings**
stays, because getting a file to save back byte-for-byte the way it arrived is
most of what a Notepad replacement is for.

---

## Reopening what you had open

QUILL Lite remembers the saved documents you had open and offers them back next
time. Until September 2026 it simply opened all of them without asking, and
skipped any whose file had gone without saying so. That is right for one document
and wrong for four: four windows appearing unbidden is four things to identify
before you can start, and the one you wanted is not necessarily the first.

So it asks — **when it matters**:

| Last time you had | What happens |
|---|---|
| one or two documents, both still there | they open, as before |
| three or more | you are asked |
| any document whose file has moved or gone | you are asked |

The window lists what was open, one row each, with a checkbox. Everything that
can be opened starts ticked, so **Enter** is "all of it" and unticking two is
"not those two". A row whose file has gone says so and cannot be ticked.

- **Open Checked** opens the ticked rows and leaves the list alone.
- **Open All** opens everything still on disk, ticked or not.
- **Not Now** opens nothing and changes nothing. The same documents are offered
  next time. Escape does the same.
- **Forget Checked** takes the ticked rows off the list so they stop being
  offered, and **Clear the List** does it to all of them. **Neither touches a
  file.** Forgetting is about what QUILL Lite offers you, not about what is on
  your disk, and the window says so in a line under the buttons.
- **Never Ask Again** opens the ticked documents and stops asking from then on.
- **Ask Me Next Time** is its twin, and undoes it: you are asked again the way
  a new install asks — when there are several documents, or one whose file has
  moved. The ticked documents open as well.

**Exactly one of that pair is ever available**, and the other is greyed rather
than hidden, so arriving on it tells you which way the setting currently is.
If you have pressed Never Ask Again and want the window back, open it yourself
with **File ▸ Reopen Last Session...** (**Alt+Shift+F12**) and press **Ask Me
Next Time**. That is the only place the setting lives — it is deliberately not
in Preferences, because the window that asks the question is the obvious place
to answer it, and until this release it was the one answer in here that could
not be taken back at all.

Then it tells you what happened — "Reopened all 3 documents", "Reopened 1 of 2",
"Forgot 2 documents. 1 still remembered. The files themselves are untouched." A
count is the one thing you cannot go and read off the screen.

**File ▸ Reopen Last Session...** (**Alt+Shift+F12**) opens the same window
whenever you want it. That is what makes Not Now safe to press: the answer is
put off rather than lost, and a list that needs tidying can be tidied without
waiting for a restart. QUILL has the same window on the same key.

## Settings

**Tools ▸ Preferences** (**Ctrl+,**) is one window, one long column of
controls, and an **OK** and a **Cancel** at the bottom. Tab moves down it,
Shift+Tab moves back up, **F1** on anything reads what that one control does,
and **nothing is written until you press OK** — so Escape is always safe.

Here is every control in it, in the order you meet them.

**Profile** is the same four-answer chooser Customize Features has, with the
same read-only description under it. It is here as well as there because "make
this Notepad" is a preference like any other. See [Making QUILL Lite smaller (or
larger)](#making-quilllite-smaller-or-larger).

**New documents are:** — **Plain text** or **Rich text**. This is what
**Ctrl+N** creates, and nothing else. **New Plain Text Document**
(**Ctrl+Alt+N**) and **New Rich Text Document** (**Alt+Shift+T**) ignore it and
always make what their names say. Choosing the **Notepad** or **WordPad**
profile moves this control in front of you rather than behind your back, so you
can see what the profile claimed and overrule it before you press OK.

**Theme:** — **Dark** or **Follow the system**. **Follow the system is the
default**, and it is the one that does not guess. QUILL Lite shipped dark,
because the people this editor is for are disproportionately light-sensitive
and a first launch that is bright white is one some of them cannot read — but
light-sensitive does not mean *dark*: somebody who depends on high-contrast
black on white is harmed by a dark default in exactly the same way. Anybody
with a strong requirement has already told Windows about it, in the one place
every other program on the machine reads, so QUILL Lite reads that instead.
Choose **Dark** to have it dark whatever Windows says. Either way it changes
what is on the screen and nothing else: the colours are never written into your
files, so a theme can never leave grey text in a document you send somebody.
The View menu has the same switch on **Alt+Shift+D** for when you want it now,
and it says "Dark mode on" or "Dark mode off" so you never have to look.

If you chose dark in an earlier version, you keep dark. Only somebody who never
chose comes with the new default.

**Reopen the documents I had open last time** — on. Off means QUILL Lite starts
with whatever you open yourself. This is a different question from recovering
unsaved work, which happens either way.

**Offer untitled unsaved work back after a crash** — on. An untitled document
is the one with no file to fall back on, so this is the copy you would miss
most. Off if you use QUILL Lite as a scratchpad and would rather it forgot.

**Start with a blank document** — on, the way Notepad and WordPad do it. Turn it
off if you always open an existing file: without it you are handed an empty
Untitled to close on every launch. Files you open by double-clicking, last
session's documents and recovered work all still appear either way. QUILL has
the same setting under **General**.

**Share QUILL's abbreviation library** — off. On, QUILL Lite reads and writes
QUILL for All's list instead of its own, so a short form added in either is
there in both. It does nothing if you do not have QUILL installed.

**Share QUILL's dictionary of taught words** — off, and the same idea for
spelling: a word you teach in either editor is known to both.

**Keep everything I copy in the clip library** — off. On, every Ctrl+C is kept
in the clip library automatically instead of only the ones you press
**Ctrl+Alt+M** on. Useful, and it does mean the library fills up by itself.

**Look for updates when QUILL Lite starts** — on. It looks once a day and says
nothing unless there is something. **Ctrl+Alt+U** asks on demand either way.

**Check spelling as I type** — on. This is the same switch as **Tools ▸
Spelling ▸ Check While Typing** (**Ctrl+Alt+F7**), which is the quick way to
reach it while you are in a document.

**Curl quotes as I type** — off. Turns a straight quote into a matching curly
one. **Turn two hyphens into an em dash** — off. Typing the second hyphen of
`--` replaces both with a single long dash. Both need **Autocorrect while
typing** switched on in Customize Features as well, and neither ever runs in a
plain text, source or configuration document however they are set.

**When a command does something, give me:** — **a sound**, **the action
spoken**, **both**, or **nothing**. This is what a cut, a copy, a paste, an undo
or a started selection reports back with. A sound is what the app has always
done; speech says the word instead, which is what you want before you have
learned the tones. Two things are outside this setting on purpose: a command
that has no tone in your sound pack **speaks** rather than falling silent, and a
command that could not do what you asked **always says so in words**, because no
tone has ever carried "it did not work".

**When a search misses:** — the same four answers, asked separately. F3 is
pressed in runs, and hearing "Not found" spoken on every press is the fastest
way to end up turning speech off altogether. The status bar carries the words
whichever you pick, so nothing is lost by choosing the tone.

**Say a heading's level:** — **before the text** or **after the text**. Before
is one sentence QUILL Lite says on its own — "Heading 2, Installing" — and it is
the one that survives a jump, because pressing Ctrl+Home or landing on a search
hit makes a screen reader cancel whatever it was about to say, and a level
waiting its turn behind that is never heard. After lets your reader read the
line and adds the level behind it, which is quieter on ordinary line-by-line
reading.

**Searching carries on from the other end** — on. Find Next reaching the end
starts again at the top and tells you it has. Off, it stops and says which end
you are at, so you know the word is not absent — you are just at the bottom.

**Wrap long lines to the window** — on. Off, long lines run past the right edge
and scroll. **Alt+Z** is the same switch on the View menu.

**Shortest gap between spoken messages (ms):** — 0 to 2000, and 0 is the
default, meaning say everything as it happens. A larger number drops anything
QUILL Lite would say too soon after the last thing it said, which is what you
want if holding a key down floods your screen reader. Nothing is lost by it: the
status bar is written either way and **F6** reads it back.

**Copy unsaved work aside every (seconds):** — 15 to 600, 30 by default. How
often a changed document is copied to the recovery folder. The copy is *beside*
your file, never over it, and is removed the moment you save.

**Editor font:** — a read-only box saying the face and size, and a **Change
Font...** button that opens the chooser. The box reads back whatever you pick,
and QUILL Lite says it out loud as well, because a box you are not focused on is
exactly what a screen reader does not announce. The same chooser is on
**Ctrl+Alt+F** (**Format ▸ Editor Font**), which is where Notepad has always
kept it and which is the one row the Format menu keeps if you switch rich text
off.

**Use QUILL's free AI help** — off. This one is **not** held until OK. Ticking
it shows you the whole agreement there and then and records your answer
immediately; unticking it withdraws immediately. Consent recorded because
somebody pressed OK on an unrelated window would be consent of a worse kind. If
you decline the agreement the tick goes back by itself, and QUILL Lite says so
out loud, because a checkbox changed in code is not a checkbox your reader
announces. See [AI help](#ai-help).

### What is not in here, and where it is instead

Some switches are a keystroke away rather than a window away, because they are
the ones you change *while* you are working:

| Not in Preferences | Where it is |
|---|---|
| Dark mode | **View ▸ Dark Mode** (**Alt+Shift+D**) |
| Word wrap | **View ▸ Word Wrap** (**Alt+Z**) |
| Announce Headings, Announce Lists | **View** (**Ctrl+Alt+F3**, **Ctrl+Alt+F5**) |
| Overwrite mode, Tab key behaviour, the status bar | **View** |
| Quiet mode | **Tools ▸ Quiet Mode** (**Alt+Shift+M**) |
| Which sound each event makes | **Tools ▸ Sound Scheme** (**Ctrl+Alt+Shift+O**) |
| Which of the 20 areas exist at all | **Tools ▸ Customize Features** (**Ctrl+Alt+F10**) |
| What any key does | **Tools ▸ Keyboard Manager** (**Ctrl+Alt+Shift+R**) |
| The twelve spelling announcement settings | **Tools ▸ Spelling ▸ Announcements** (**Ctrl+Alt+Shift+F7**) |
| Whether you are asked about last session | The **Reopen Last Session** window itself (**Alt+Shift+F12**) |

That last one is worth saying out loud, because it is the one people go looking
for in Preferences and do not find. See [Reopening what you had
open](#reopening-what-you-had-open).

### Taking your settings with you

**Tools ▸ Back Up Settings...** (**Ctrl+Alt+F11**) and **Tools ▸ Restore
Settings...** (**Ctrl+Alt+F12**) are described under [Moving your settings to
another computer](#moving-your-settings-to-another-computer).

---

## Printing

**Ctrl+P** prints. **Ctrl+Alt+P** is Page Setup, and what you set there — paper
size, orientation and all four margins — is remembered for next time.

Long lines are wrapped to fit the page whatever your Word Wrap setting says,
because a printed line that runs off the edge of the paper is simply gone.

**Rich text prints as rich text.** A rich document is printed by the editor
itself, so a heading arrives on paper as a heading and a bold word arrives bold.
This was not true before version 1.0: everything printed flat, in one size.

A plain text or Markdown document prints as it reads, which is the right answer
— a Markdown heading already carries its own `#` onto the page.

### Print Preview... — Ctrl+Alt+Shift+P

Not a picture of a page. A picture of a page is the one kind of preview that
answers nothing at all if you cannot see it, which is why WordPad's and Word's
have never been much use here.

This one answers the questions you actually have: **how many pages**, on what
paper, with what margins — and then, page by page, what is at the top of each
one. "Page 3 of 7: Installing" is how you find out whether the section you care
about starts where you wanted it to, without printing anything.

The page count is worked out against your real printer, using the same
measurements the print itself uses, so the number here is the number that comes
out.

---

## Speech

QUILL Lite talks through **NVDA or JAWS**, and nothing else. There is no built-in
voice, and that is on purpose: a second voice talking over your screen reader is
worse than silence.

It also says as little as it can. Your screen reader already announces window
titles, where your focus has moved, the names of buttons and what you have
selected. QUILL Lite only tells you things it alone knows — that a save happened,
that a search wrapped around, that bold went on, that four things were replaced.

Everything it says also goes into the first part of the status bar, so **F6**
will bring back a message you missed.

If you have no screen reader running, QUILL Lite says nothing out loud — but
every message is still there in the status bar.

### If it says too much

Holding a key down can make QUILL Lite speak faster than anybody can listen.
**Preferences ▸ Shortest gap between spoken messages** sets a floor, in
milliseconds: anything it would say too soon after the last thing it said is
dropped. Zero, the default, says everything as it happens. Nothing is lost by
turning it up — the status bar is written either way, and **F6** reads it
back.

---

### What formatting is here?

**Ctrl+Shift+D** (**Format ▸ Describe Formatting at Cursor**) says what the
formatting is where your cursor is standing. It is the answer to the question a
sighted reader settles with a glance and a listener otherwise cannot ask at all.

It gives a different kind of answer in each kind of document, because there is a
different kind of truth to tell:

- In a **rich text** document it asks the control itself, and reads back the
  real thing: *"Arial, 14 point, bold, centred."*
- In a **Markdown** document it reads the markup around your cursor: standing
  inside `**bold**` it says bold, and on a `##` line it says Heading 2.
- In a **plain text** document it says so, because that is the honest answer
  rather than a denial.

There are two narrower questions beside it, for when the answer you want is
smaller:

- **Ctrl+Shift+C** (**Describe Character**) names the character under the
  cursor, which is how you tell a hyphen from an en dash from a minus sign —
  three characters a screen reader reads identically.
- **Ctrl+Alt+Shift+V** (**Describe Indent Depth**) says how far the current line
  is indented, and whether with tabs or spaces.

### How big is this document?

**Ctrl+Shift+G** (**View ▸ Document Statistics**) speaks the size of the whole
document: *"1,240 words, 7,315 characters, 96 lines."*

The same three numbers live in the status bar, and this command exists because
a listener is not watching the status bar. Pressing it is quicker than going to
find the cell and reading it.

**Ctrl+Alt+W** (**Line Statistics**) answers the narrower question for the line
you are on, or for what you have selected.

### The collector: gather now, paste once

The copy tray holds twelve numbered slots you put things into deliberately. The
**collector** is the other half of that idea, for when you are reading through
something and want several pieces of it without stopping to decide where each
one goes.

1. **Alt+Shift+S** (**Edit ▸ Clipboard ▸ Collect Selection**) adds the
   selection to the pile. Press it as often as you like; each one is added to
   the end, and nothing is overwritten.
2. **Paste Everything Collected** puts the whole pile into your document in the
   order you collected it.
3. **Ctrl+Alt+Shift+C** (**Clear the Collector**) empties it when you are done.

The collector used to be on Ctrl+Alt+G. It moved to Alt+Shift+S in September
2026 because Google Drive for desktop claims Ctrl+Alt+G across the whole of
Windows — and a key claimed system-wide never reaches the application at all,
so the command looked broken on any machine with Drive installed. If you find
another key that does nothing, the Keyboard Manager will now tell you when
something outside QUILL Lite has taken it.

## Dictation

Press **Ctrl+F11**, talk, and pause. Each time you pause, what you said is
written into the document at the cursor, you hear a short soft tone, and QUILL
Lite reads the words back so you know they are right. Then it keeps listening,
so you can go straight on to the next sentence. Press **Ctrl+F11** again, or say
"stop dictation", to stop.

You do not need to say punctuation. The built-in speech engines put in full
stops, commas, question marks and capitals by themselves, the way you would
write them. When you want a particular mark, say it -- "comma", "new
paragraph" -- and your word always wins.

Everything happens on this computer. The speech engines come with QUILL Lite,
nothing is downloaded, nothing you say is sent anywhere, and no recording is
kept: the words are recognised, written into your document, and forgotten.

### Your first dictation, step by step

1. Put the cursor where you want the words. If you select some text first, the
   first phrase you say replaces it.
2. Press **Ctrl+F11**. The first time after opening QUILL Lite it takes a second
   or two while the speech engine loads. Then you hear two rising tones and
   "Dictation on".
3. Say a sentence the way you would say it to a person, and pause.
4. A moment later the sentence is in the document, you hear the soft tone, and
   the words are read back to you.
5. Keep going. There is no need to press anything between sentences.
6. When you are done, press **Ctrl+F11** or say "stop dictation". You hear two
   falling tones and "Dictation off".

A phrase is written when you have been quiet for a little under a second, so a
breath in the middle of a sentence does not cut it in two. If a pause does
split a sentence and the next part starts with a word like *and*, *but*,
*which* or *to*, the full stop the pause put in is taken back out and the
sentence carries on.

### What you hear

| When | Tones | Words |
|---|---|---|
| Dictation starts | two rising tones | "Dictation on" |
| A phrase is written | one short, soft tone | the words that were written |
| Dictation stops | two falling tones | "Dictation off" |
| Something goes wrong | a low double tone | what happened, and what to do |

Every row can be changed in **Dictation Settings**, and every tone can be
changed or silenced in **Tools ▸ Sound Scheme**. Two things are never silenced:
a failure is always spoken, and so is the answer to a command, because both
answer a question.

The soft tone plays only once the words are really in the document, so hearing
it means they arrived. If you choose speech for each phrase, the words are
read back a quarter of a second after they are written, so they are not cut
off by your screen reader's own reaction to the new text.

**Use headphones if the read-back is on.** Read back through speakers, the
microphone can hear it and write it down a second time. With speakers, set
"After each phrase is written, give me" to a sound only.

### The speech engines

Choose one in **Dictation Settings**. The first two come with QUILL Lite.

| Engine | What it is like |
|---|---|
| **Moonshine** (the one it starts with) | Fast even on a modest computer, and punctuates by itself. English. |
| **Whisper** | Punctuates by itself, a little slower. Try it if Moonshine often mishears your voice or your microphone. English. |
| **Windows speech recognition** | Windows' own recogniser. Does not punctuate by itself -- say every mark -- and mishears an untrained voice often. Can use any speech language installed in Windows. |
| **Windows voice typing (Windows+H)** | Hands over to Windows' own voice typing panel. Windows does the recognising and the typing, so none of the commands, tones, read-back or wake phrase apply here. |

Moonshine and Whisper were chosen after measuring eight candidates on the same
sentences for accuracy, punctuation, speed on one processor core, and size;
Moonshine was the most accurate and by far the fastest.

### Saying punctuation and layout

You can say these anywhere in a phrase:

- **Punctuation:** "period" or "full stop", "comma", "question mark",
  "exclamation point", "colon", "semicolon", "ellipsis", "apostrophe", "open
  quote" and "close quote", "open single quote" and "close single quote".
- **Brackets:** "open parenthesis" and "close parenthesis", "open bracket" and
  "close bracket", "open brace" and "close brace".
- **Joining:** "hyphen", "dash", "slash", "backslash", "underscore".
- **Symbols:** "at sign", "hash sign", "dollar sign", "percent sign",
  "ampersand", "asterisk", "plus sign", "minus sign", "equals sign".
- **Layout:** "new line" ends the line, "new paragraph" leaves a blank line,
  and "tab" or "tab key" types a tab.

Spaces go where they belong -- none before a comma, one after a full stop, none
at the start of a line -- and the first word of each sentence gets its capital.
What "dash" writes is your choice in Dictation Settings: an em dash, a spaced en
dash, or two hyphens.

To write one of these words as a word, say **"literal"** first: "literal new
line" writes *new line*, and "literal comma" writes *comma*.

### Commands

A command works only when it is **the whole phrase**, said on its own after a
pause. "Delete that line of text" inside a longer sentence is just words, and
is written as words.

**Correcting what you said:**

| Say | What happens |
|---|---|
| "scratch that" or "delete that" | Removes the phrase you dictated last. Say it again to remove the one before. |
| "undo that" or "undo" | The same as Ctrl+Z. |
| "select that" | Selects the last phrase, so you can fix it with the keyboard. The next phrase you say replaces it. |
| "capitalize that" | Gives every word of the last phrase a capital. |
| "all caps that" | Puts the last phrase in capitals. |
| "no caps that" | Puts the last phrase in small letters. |
| "delete word" | Deletes the word before the cursor. |
| "delete sentence" | Deletes the sentence the cursor is at the end of. |
| "read that" or "repeat that" | Reads the last phrase aloud again. |

**Moving the cursor:** "go to beginning of line", "go to end of line", "go to
top", "go to end of document".

**Dictation itself:** "start spelling" and "stop spelling" (below), "what can I
say" (opens the full list), and "stop dictation".

The commands that change the last phrase only change it while it is still
exactly as it was written. If you have typed into it since, it is left alone
and QUILL Lite says so, because changing it would change your typing too.

### Spelling a word

For a name the engine will never get right, say **"start spelling"**. Until you
say **"stop spelling"**, everything you say is written as letters:

- Say letters by name ("bee", "see") or, far more reliably, with the phonetic
  alphabet: alpha, bravo, charlie, delta, echo, foxtrot, golf, hotel, india,
  juliet, kilo, lima, mike, november, oscar, papa, quebec, romeo, sierra,
  tango, uniform, victor, whiskey, x-ray, yankee, zulu.
- Say "capital" before a letter for a capital, and "space" for a space.
- Numbers are written as digits: "one", "two" and so on.

"Start spelling", then "capital bravo alpha delta", then "stop spelling" writes
*Bad*. The letters are read back as they are written, so a wrong one is heard at
once -- say "scratch that" to take the last run back.

### The full list

Say **"what can I say"** while dictating, or press **Dictation Commands...** in
Dictation Settings, and QUILL Lite opens a window listing every phrase it acts
on, with your own phrases and your wake phrase included. Read it with the arrow
keys; Escape closes it. The same list is published as its own page,
**Dictation commands**, next to this guide.

### Starting with your voice: the wake phrase

Switch on **Listen for the wake phrase while dictation is off** in Dictation
Settings, and you can start dictation by saying the wake phrase instead of
pressing a key. It is **"Quill dictate"** unless you choose another.

- Say the wake phrase, pause, and start talking -- or say it and carry straight
  on: "Quill dictate, dear Sam, thank you for your letter" wakes dictation and
  writes *Dear Sam, thank you for your letter.*
- "Stop dictation" (or Ctrl+F11) stops writing and goes back to waiting for the
  wake phrase.
- The wake phrase only counts at the start of what you say. "I told Quill to
  dictate this" in a conversation does not start anything.
- A near miss still works: "Quil dictate" wakes it.

**Choosing your own.** Type any phrase in the **Wake phrase** box. It needs at
least two words, and should be something you would not say in passing -- a
name and a verb works well. A single word is refused, because it would start
dictation by accident.

**What it means for the microphone.** While the wake phrase is on, the
microphone is open whenever QUILL Lite is the window in front. Nothing it hears
is written, kept or sent anywhere unless it begins with the wake phrase; what
does not is dropped the moment it has been checked. When another program comes
to the front, the microphone closes, and dictation stops if it was running.
When QUILL Lite comes back to the front, it listens for the wake phrase again.
It does not listen while QUILL Lite is in the background: waking up would mean
taking the focus from whatever you were doing, and that is not a surprise
anyone should have to deal with. The wake phrase is off until you turn it on.

The wake phrase works with Moonshine, Whisper and Windows speech recognition,
but not with Windows voice typing, which Windows runs itself.

### Stopping with your voice: the stop phrase

Say **"stop dictation"** on its own, after a pause, and dictation stops. You can
choose your own words as well: type them in the **Stop phrase** box in Dictation
Settings, and saying them stops dictation just the same. "Stop dictation" keeps
working either way.

- The stop phrase counts only when it is **everything you said** in that breath.
  "I will stop dictation for today" in the middle of a paragraph is written, not
  obeyed.
- Like the wake phrase, it forgives a near miss, and it needs at least two words
  so ordinary talk does not stop you by accident.
- With the wake phrase on, stopping goes back to listening for the wake phrase,
  so you can start and stop without touching the keyboard at all.

### Your own words and phrases

Press **Edit My Words and Phrases...** in Dictation Settings. QUILL Lite opens a
small file of your own in a new window; change it, save it with Ctrl+S, and the
next phrase you dictate uses it. It has two parts:

- **Vocabulary** -- names, jargon and acronyms, one per line, spelled the way you
  want them. When the engine writes something that sounds or looks close to one
  of these, it is corrected to your spelling: add *Tucson* and "tuxon" becomes
  *Tucson*.
- **Replacements** -- your own spoken phrases. `my email address =>
  someone@example.com` writes the address whenever you say *my email address*.
  Use `\n` for a new line and `\t` for a tab, so a signature can be two lines.

Your own phrases appear in the "what can I say" list with everything else.

### Choosing the microphone

**Dictation Settings** lists every microphone by name. The first choice follows
whatever Windows is using as the default recording device; choose a named
microphone to keep using that one whatever the default becomes. If the
microphone you chose is unplugged, starting dictation tells you so, rather than
quietly listening on another one.

### Talking in one long run: Just write what I say

Some people think out loud in one long run and pause wherever the thought
pauses. Normally each pause is where a phrase ends: it is written with a full
stop, a tone plays, and the words are read back. Switch on **Just write what I
say: nothing happens at a pause** in Dictation Settings, and a pause does
nothing at all:

- **No full stop because you paused.** The words carry on as one sentence until
  you say "period", "question mark" or another mark yourself. Marks inside what
  you say are still put in by Moonshine and Whisper.
- **No tone and no read-back** after each phrase, so nothing talks over you.
- **No voice commands.** "Scratch that" or "select that" said on its own is
  written as words. Punctuation and layout you say -- "comma", "new paragraph"
  -- still work, and so does the **stop phrase**, so there is always a way out
  by voice.

Everything is still written as you go, and **Ctrl+Z** still takes back a phrase
at a time. Turn it off again when you want the commands back.

### The finer choices

- **Automatic punctuation (Moonshine and Whisper).** On, the engine puts in full
  stops, commas and question marks by itself. Off, it adds none, and you say
  every mark, exactly as with Windows speech recognition.
- **Pause before a phrase is written.** Short (half a second), Normal (under a
  second) or Long (about a second and a half). If dictation cuts you off while
  you are still thinking, choose Long. Windows speech recognition is asked for
  the same length.
- **Remove filler words like um and uh.** Hesitations -- um, uh, erm, hmm -- are
  left out instead of written. Real words are never removed.
- **Stop dictation after silence.** Never, or after 1, 5 or 10 minutes of hearing
  nothing, so dictation is not left writing in an empty room. With the wake
  phrase on, it goes back to waiting for the wake phrase instead. You hear why:
  "Dictation off after 5 minutes of silence."
- **Test Microphone.** Beside the microphone list. Press it, wait for "Speak
  now", and talk for four seconds. You hear how loud the microphone was --
  almost nothing, quiet, working, or very loud -- and, with Moonshine or Whisper,
  exactly what the engine heard. Nothing is kept. The result also stays in the
  box beside the button, to read again.

### Dictation Settings, every option

**Tools ▸ Dictation ▸ Dictation Settings...** (**Alt+Shift+F6**). The
window has two columns: what is heard and written on the left, starting and
stopping on the right.

| Option | What it does | Starts as |
|---|---|---|
| Speech engine | Moonshine, Whisper, Windows speech recognition, or Windows voice typing | Moonshine |
| Automatic punctuation (Moonshine and Whisper) | The engine puts in the marks you do not say | On |
| Language for Windows speech recognition | Which installed Windows speech language to use; the other engines understand English | Windows default |
| Microphone | Which microphone to listen on | Windows default |
| Test Microphone (button) | Four seconds of listening: how loud, and what was heard | -- |
| After each phrase is written, give me | A sound, speech (the words read back), both, or neither | Both |
| Saying "dash" writes | Em dash, spaced en dash, or two hyphens | Em dash |
| Pause before a phrase is written | Short, Normal or Long | Normal |
| Remove filler words like um and uh | Leave hesitations out | Off |
| Just write what I say: nothing happens at a pause | No full stop, sound, read-back or command at a pause | Off |
| Play sounds when dictation starts, stops or fails | The start, stop and error tones | On |
| Say "Dictation on" and "Dictation off" | The words that go with those tones | On |
| Listen for the wake phrase while dictation is off | Start dictation by voice | Off |
| Wake phrase | The words that start it | Quill dictate |
| Stop phrase | The words that stop it, said on their own | stop dictation |
| Stop dictation after silence | Never, or after 1, 5 or 10 minutes | Never |

Two buttons sit below them: **Dictation Commands...** opens the full list, and
**Edit My Words and Phrases...** saves these settings and opens your own file.

### Knowing what dictation is doing

- **The status bar** has a **Dictation** part: Off, Listening, Hearing you,
  Writing, Spelling, or Waiting for wake phrase. Press F6 to reach the status
  bar and move to it; Enter there starts or stops dictation.
- **Tools ▸ Dictation ▸ Dictation On** is checked while dictation is writing.
- **The tones and the words** say when it starts and stops.

### Where the words go

Into the document you started dictation in, at the cursor, each phrase one step
for **Ctrl+Z**. With the wake phrase, into whichever document is in front when
you say it.

Dictation stops by itself when that document closes, when you switch it between
plain and rich text, or when you move somewhere else -- another window, another
program, or a dialog -- and speak. What you said then is not written anywhere,
and QUILL Lite tells you why it stopped. There is one microphone, so pressing
Ctrl+F11 in a second document while dictation runs in the first stops it; press
it again to start in the second.

### If something goes wrong

Dictation always says what happened and what to do. The usual reasons:

- **No microphone was found.** Connect one and press Ctrl+F11 again.
- **The microphone you chose is not connected.** Plug it in, or choose another
  in Dictation Settings.
- **The microphone could not be opened.** In Windows Settings, go to Privacy and
  security, Microphone, and make sure desktop apps are allowed to use it.
- **A speech engine is not included in this copy.** Choose another engine in
  Dictation Settings; reinstalling QUILL Lite puts the missing one back.
- **With Windows speech recognition: no speech recogniser is installed.** Add a
  speech language in Windows Settings, Time and language, Speech.

**If it keeps mishearing you:** try Whisper instead of Moonshine, or the other
way round; use a headset microphone rather than a laptop's built-in one; turn
the read-back to a sound only if you are using speakers; and add names you use
often to your own vocabulary.

Dictation is on in every profile except WordPad and Notepad, and can be
switched off in **Customize Features** like any other area; switching it off
removes the menu, the keys and the wake phrase.

## AI help

AI help is **off until you turn it on and accept the agreement** — both, not
either. See *AI help* under Customize Features for the reason the switch and the
agreement are two separate things, and for the three doors to the agreement.

Once it is on, there is **one pad**, five things it can do, and two keys into
it.

**AI Assistant** (**Ctrl+Alt+G**) opens the pad where you are. **Ask About
This Document** (**Ctrl+Alt+Z**) opens the same pad with the last of the five
already chosen, because that one takes a question rather than a selection and
is worth a chord instead of one more row to arrow past.

### What the pad looks like, top to bottom

1. **What will be sent** — a read-only box holding *exactly* the text that
   will go, and nothing else from your document. Arrow through it before you
   press anything.
2. **Send this much** — a chooser, when there is more than one sensible
   answer: what you selected, the paragraph you are in, or the whole section.
   The box above rewrites itself as you change it.
3. **What do you want done?** — a list of the five:

| Choose | You get |
|---|---|
| **Summarize** | A few plain sentences saying what this passage says |
| **Rewrite** | The same meaning, clearer and shorter |
| **Proofread** | Spelling, grammar and punctuation corrected, wording left alone |
| **Explain** | What this passage means, in plain language |
| **Ask a question about the document** | You type a question; QUILL Lite finds the parts of the document that answer it and sends only those |

4. **Your question** — which appears only for that last one.
5. **Send** — and nothing at all has left this computer until you press it.

### What comes back, and what you can do with it

The answer arrives in a read-only box of its own, with buttons under it:
**Replace My Selection**, **Insert Below**, **Copy**, and **Try Again**. The
first two appear only when they make sense — there is nothing to replace if
you selected nothing.

**Nothing is applied for you.** Proofread in particular reports what it found
and changes not one character until you press Replace My Selection. An AI that
edits your document behind you is one you have to proofread twice.

**What is sent, and when.** Nothing goes anywhere until you run one of those two
commands. When you do, the text you asked about — the selection, or the document
— is sent to QUILL's own service and the answer comes back. Nothing is sent as
you type, nothing is sent in the background, and closing the pad without asking
sends nothing at all.

### Connecting this computer

Before anything can be sent, this computer has to be connected once. There is
**no account, no password and no email address**.

1. **Tools ▸ AI ▸ Connect or Sign Out** (**Ctrl+Alt+Shift+F10**). Accepting
   the agreement brings you here too, straight away, if this computer is not
   connected yet.
2. The window asks QUILL for an **eight-character code** as it opens, puts it in
   a read-only box you can arrow through one character at a time, and **says it
   out loud**. **Say the Code Again** repeats it; **Copy the Code** puts it on
   the clipboard.
3. Press **Open the Connect Page**. Your browser opens the page with the code
   already filled in; press **Confirm** there. Or type the code into the web
   address the window names on any other device — a phone, anything with a
   browser.
4. The window confirms **in place**, and says so, because the content changing
   under a window you already have open is exactly what your screen reader will
   not tell you. Focus does not jump to a window you did not open.

The same window afterwards holds **Sign Out This Computer** and **Copy Support
ID**, which is the identifier to quote if you ever write to support about AI.

Each computer connects separately, and signing one out does not sign out the
others.

**What is recorded.** When you use AI, the text you asked about is sent to QUILL
and on to the model that writes the answer. QUILL records **how many requests you
make and how big they were**. QUILL does **not** record what you wrote or what
came back.

### How much you can send, and how often

The service is free, so it has limits. They are read from the service rather than
built into the program, which means a limit can be raised without you installing
anything.

**How much in one question:** about **3,000 tokens**, which is roughly **2,250
words** or **12,000 characters**, counting the document text, your question and
the instructions together. If what you asked about is bigger than that, the pad
says so *before* sending, in words rather than tokens — "that is about 4,000
words, and the free limit is about 2,250" — so you can select less and try again.
Nothing is sent in the meantime. The answer itself is capped at about 500 tokens,
a few hundred words.

**A long document still works.** Ask About This Document does not send the whole
file. It picks the **three passages most likely to answer your question**, each
about 180 words and carrying the heading it sits under, and sends those. So a
hundred-page document is a fair thing to ask about — what the limit bounds is how
much goes in one request, not how big your document may be. The pad shows you
which passages were chosen before anything is sent.

**How often:** there is a monthly, a daily and an hourly allowance, and a
smaller one for a computer's first 48 hours. *Limits, and when they start
again*, just below, has every number and every rule.

**Usage** (**Ctrl+Alt+Shift+F9**) shows what you have used and what is left. The
service is free and has a fair-use ceiling; this is where you find out where you
stand, before you are told by being refused. **Help ▸ About QUILL Lite** shows the
same allowance, and this computer's **support ID**, under **QUILL's free AI** —
the numbers are asked for fresh each time, so give it a moment after About opens.

**Connect or Sign Out** (**Ctrl+Alt+Shift+F10**) connects *this computer* to the
service, or disconnects it. Signing out does not withdraw your agreement, and
withdrawing your agreement does sign you out — keeping the key to a service you
have just declined would be the wrong way round.

**Privacy Agreement** (**Ctrl+Alt+Shift+K**) is always reachable, whether or not
the area is switched on and whether or not you have accepted. It is the one
command in this menu that never needs permission to open, because a door you can
only reach by agreeing to something is not a door.

Every key named here is listed again in *Every key, in one table*, under
**Tools ▸ AI**.

### Limits, and when they start again

QUILL's free AI is free because it is shared, so it has limits. This is every
one of them, in one place.

#### Your allowance at a glance

These are the service's current settings. They are read from the service every
time, never built into the program, so one can change without an update — and
**Usage** always shows the numbers that actually apply to you right now.

| Limit | How many | Starts again |
|---|---|---|
| Requests a month | 100 | The 1st of the month |
| Requests a day | 20 | Every night |
| Requests an hour | 8 | At the top of each hour |
| Any one kind of request a month | 60 | The 1st of the month |
| A new connection's first 48 hours | 15 | Rises to 100 on its own |

"Any one kind" means Summarize, Rewrite, Proofread, Explain and Ask About This
Document each have a monthly share of 60, so one of them cannot use up the whole
month. The daily and hourly numbers are there to stop a runaway loop spending a
month's worth in an afternoon, not to ration ordinary work.

#### When the counts start again

The service keeps time in **UTC**, not in your time zone:

- **The hour** starts again on the hour.
- **The day** starts again at **midnight UTC**. That is **8 PM Eastern** or
  **5 PM Pacific** in summer, an hour earlier in winter — so in North America
  the new day's requests arrive in the evening, not at midnight.
- **The month** starts again at **midnight UTC on the 1st**. Usage shows the
  exact date.

#### What counts as a request

One request is one press of **Send** that comes back with an answer. **Try
Again** is another request. A request that does not produce an answer is **not
counted**: if it was too long, if there was no connection, if the service had a
problem, or if a limit had already been reached, nothing is used. Showing Usage
or About never uses anything.

#### When you reach a limit

The AI window says **which** limit you reached and **when it starts again**, and
focus moves to that message so you can read it again with the arrow keys. It
ends with an error code — `QUILL-AI-GATEWAY-QUOTA` for a limit — which is worth
including if you write to support. Nothing is used, nothing in your document
changes, and everything else in the editor carries on as normal. Wait until the
time it names, or ask for more (below).

If the message says QUILL's free AI is **paused**, that is not about you: the
service has a spending ceiling for everybody together, and when it is reached
the free AI pauses for everyone until the 1st. This is rare, and it is announced
rather than silent.

#### A new connection starts smaller

For its **first 48 hours**, a computer that has just connected gets **15
requests** instead of the full monthly allowance, and then the full allowance
applies **on its own** — there is nothing to do. It is how a free service with no
accounts and no passwords stops somebody scripting connection after connection
for a fresh allowance each time; somebody trying the feature out rarely reaches
15 on the first day. While it applies, **Usage** and **About** say so and name
the exact time it ends. Signing out and connecting again starts a new
connection, so it is never a way to get more.

#### Computers that share an internet connection

A household, a classroom or a library usually reaches the internet through one
address, and a few limits apply to that address as a whole: how many computers
can be connected from it at once, how many new connections it can make in an
hour, and a monthly total shared by every computer on it. They are generous for
a home and are there to stop one address minting connections by the hundred;
the exact numbers are not published, for the same reason. Signing a computer out
gives its place back.

If a class or a lab runs into these, write to support — this is exactly the
situation they can help with.

#### Asking for more

Choose **Get Help from Support** in the Help menu and say what you need and why:
a course, a deadline, a book. When this computer is connected, its **support ID**
goes into the message automatically, and that is all support needs to find your
account — there is no account name or password to give. Support can raise your
monthly allowance, including lifting the new-connection allowance early. The
change applies from your next request; you do not need to sign out, reconnect
or update anything, and Usage shows the new number the next time you open it.

Your support ID is also on **Help ▸ About** and in **Usage**, with a **Copy
Support ID** button, if you would rather write from somewhere else.

### Using your own OpenAI key: no limits

If you have an OpenAI account, you can use **your own key** instead of QUILL's
free service, and **every limit goes away**: no monthly, daily or hourly
allowance, no 2,250-word ceiling, no smaller first 48 hours.

**Tools ▸ AI ▸ Use My Own OpenAI Key** (**Alt+F2**) opens one window:

1. **About this** — a read-only box saying exactly where your text goes.
   Arrow through it once.
2. **OpenAI API key** — paste your key here. You make one at
   platform.openai.com, under API keys. It starts with `sk-`.
3. **Model** — a list of every model your key can use for text, filled
   from your OpenAI account once the key is checked: **Luna 6 first, then the
   other GPT-6 models**, then the rest by name. Each row says roughly what it
   costs, for example "gpt-6-luna, about $0.57 per 100 requests (estimate)", so
   arrowing down the list is enough to compare them. Models that cannot answer
   text — speech, transcription, images, embeddings — are left out.
4. **Cost estimate** — the chosen model's estimate per request and per 100
   requests. **These are estimates to help you compare, not OpenAI's prices.**
   A typical request here is about a page in and a paragraph back; the real
   prices are at openai.com/api/pricing.
5. **Status** — whether a key is saved, and what the last test said.
6. **Test the Key** — checks the key with OpenAI, fills the model list,
   then sends one tiny request to the chosen model and says whether it
   answered. The request costs a fraction of a cent.
7. **Remove the Saved Key** — forgets the key **at once** and puts AI help
   straight back on QUILL's free service.

Press **OK** and the key is saved. QUILL Lite says "AI help uses your own OpenAI
key, with no limits."

**Change the model at any time.** With a key saved, opening this window
lists your models straight away: press **Alt+F2**, pick another, press OK.

**There is no separate switch.** While a key is saved, AI help uses it; remove
the key and AI help is back on the free service, with its free allowance, the
moment you do. Nothing else to find and turn off.

**What changes with your own key:**

- Your text goes **straight from this computer to OpenAI**, on your account.
  Nothing passes through QUILL's servers, so QUILL records nothing at all —
  not even the count it keeps for the free service.
- **OpenAI bills you** for each request, under OpenAI's own terms and privacy
  policy.
- **Usage** (**Ctrl+Alt+Shift+F9**) opens a different window: which model is
  answering, that no allowance applies, and an **Open My OpenAI Usage** button
  that takes you to your OpenAI account's usage page, which is where your
  requests and charges are. There is no Sign Out and no support ID in it,
  because neither applies. **Help ▸ About** likewise shows the model and that
  page's address instead of the free allowance.
- You do not need to connect this computer, and the free service's agreement
  is not asked for: it is about QUILL's servers, which this route never touches.
- The pad, the five things it can do, and what comes back are **exactly the
  same**, down to the instructions sent with your text. The pad still tells you
  before sending something very large, because with your own key a large request
  costs you money.

**Where the key is kept.** In Windows' own credential store, not in a settings
file, and it is never shown again once saved — the box stays empty and says
a key is saved. A portable copy keeps it in an encrypted file instead. QUILL and
QUILL Lite share it: a key saved in either works in both, and removing it in
either removes it from both.

**If a request fails**, you hear why, followed by error code
`QUILL-AI-OWN-KEY-FAILED`. The usual causes are a mistyped key, a model your
account cannot use, or an OpenAI account with no credit. **Test the Key** tells
you which.

## Where your files are kept

Your settings, recent files, copy tray and any recovered work are kept in a
QUILL Lite folder inside your own Windows user folder. **Help ▸ About QUILL Lite**
shows you the exact location.

It is deliberately **not** inside QUILL for All's folder. QUILL Lite is offered
as an alternative to QUILL, not as part of it, and installing or removing one
should never affect the other.

Uninstalling QUILL Lite does not delete that folder. Recovered work is the one
thing you might not have finished with, and an uninstaller is the worst possible
moment to discover that.

### The portable copy keeps everything on the stick

If you are running the **portable** QUILL Lite -- the `.zip` you unpack rather
than the installer -- then none of the above applies. Everything goes into the
`data\QuillLite` folder inside the bundle, right next to `QuillLite.exe`, and
nothing at all is written to the computer you are plugged into. That is what
portable means, and QUILL Lite does it from the very first launch: there is no
setting to find first.

Until version 1.0 it did not. A portable QUILL Lite quietly used
`%LOCALAPPDATA%\QuillLite` on the host machine instead, and said nothing about
it -- so settings did not travel with the stick, and, worse, recovered copies of
documents you had not saved were left behind on someone else's computer. If you
have been carrying a portable QUILL Lite, that folder is where anything you seem
to have lost will be, and it is worth deleting once you have what you want out
of it.

Delete the `data` folder from the bundle and QUILL Lite goes back to using this
computer's own profile -- that folder is what marks the copy as portable.

---

## Keeping QUILL Lite up to date

**Help > Check for Updates...** (**Ctrl+Alt+U**) asks whether a newer QUILL Lite
has been published. It is the same key, and the same window, in every app in the
family.

If there is nothing newer you are told so in a dialog, which is deliberate: a
key that answers with silence is indistinguishable from a key that is not bound.

If there **is** something newer, the window opens on **what changed** -- the
release notes for that version, in a read-only box you can arrow through like a
document. Tab from there reaches two buttons:

- **Update** downloads the new version and then offers to install it and restart
  for you. Your settings, your recent files and your recovered work are kept.
- **Close** does nothing at all. Nothing is downloaded until you press Update.

While the download runs you hear it reach a quarter, a half and three quarters,
and then that it has finished.

QUILL Lite also looks once a day when it starts, and says **nothing** unless
there is something -- not while it checks, not when there is nothing, and not
when the network is down. Only a genuine new version speaks, and even then it
only offers. Turn the daily look off in **Settings** ("Look for updates when
QUILL Lite starts"); Ctrl+Alt+U still works either way.

---

## What QUILL Lite is not

QUILL Lite is a companion to **QUILL for All**, not a replacement for it.

If you want document conversion, comparing two documents, publishing or braille
tools, those are QUILL, and QUILL Lite is built so that it will not slowly grow
into them.

**Dictation moved in 1.1.** QUILL Lite has [Dictation](#dictation) -- built-in
speech recognition that writes each phrase as you pause -- and QUILL has the very same
feature on the same keys, in Tools ▸ Speech ▸ Live Dictation. QUILL's offline
Locked Dictation, which records a passage and transcribes it with a model you
download, stays QUILL's.

**AI is the one line that moved**, and only a little. QUILL Lite has the five
free commands described under [AI help](#ai-help) -- summarize, rewrite,
proofread, explain, and a question about the document you have open -- because
an editor that can only be used by somebody who can read a screen quickly is not
much of an accessible editor. What it does **not** have is the rest of QUILL's
AI: bringing your own key, choosing a provider, running a model on your own
machine, the agents, the conversation, the alt-text work. Five commands behind
one pad, on one free service, and nothing else.

Both are free, both are built for screen reader users, and they install
perfectly happily side by side.

**And they can share what you have built up.** QUILL Lite keeps its own settings
folder on purpose --- an editor this size should not quietly adopt a writing
environment's preferences, and uninstalling it should never cost you something
QUILL owns. But the things you *accumulate* are worth having in one place, so
each is an opt-in switch rather than a default:

- **Preferences ▸ Share QUILL's abbreviations** and **Share QUILL's personal
  dictionary** point QUILL Lite at QUILL's copy, so a short form you add or a word
  you teach in either editor is there in both.
- From QUILL's side, **Tools ▸ Customize and Support ▸ Bring My QUILL Lite
  Settings...** does the whole thing in one step: it merges your QUILL Lite
  abbreviations, dictionary, copy tray, clip library and bookmarks into QUILL,
  turns those switches on for you, and copies your preferences and rebound keys
  across once. Nothing already in QUILL is replaced, and nothing in QUILL Lite is
  removed.

QUILL also has a **QUILL Lite profile** now (Preferences ▸ Profiles and Features),
which makes QUILL show these nine menus and nothing else --- including making
Ctrl+N a plain text document, the way it does here. It is there for the day you
want one of QUILL's tools without giving up the shape you are used to.

---

## Every key, in one table

<!-- keys:start -->

Generated from the same table that builds the menus, so it cannot drift from
what is actually bound. **Ctrl+F1** shows this list inside the app.

### File

| Key | Command |
|---|---|
| **Ctrl+N** | New |
| **Alt+Shift+T** | New Rich Text Document |
| **Ctrl+Alt+N** | New Plain Text Document |
| **Ctrl+O** | Open... |
| **Ctrl+S** | Save |
| **Ctrl+Shift+S** | Save As... |
| **Ctrl+Alt+Shift+E** | Earlier Versions... |
| **Alt+Shift+F12** | Reopen Last Session... |
| **Ctrl+Alt+P** | Page Setup... |
| **Ctrl+Alt+Shift+P** | Print Preview... |
| **Ctrl+P** | Print... |
| **Ctrl+W** | Close Window |
| **Ctrl+F4** | Close Window (MDI) |
| **Ctrl+Q** | Exit QUILL Lite |

### Edit

| Key | Command |
|---|---|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+X** | Cut |
| **Ctrl+C** | Copy |
| **Ctrl+V** | Paste |
| **Ctrl+Shift+V** | Paste Text Only |
| **Del** | Delete |
| **Ctrl+A** | Select All |
| **Ctrl+F8** | Copy All |
| **Ctrl+F** | Find... |
| **F3** | Find Next |
| **Shift+F3** | Find Previous |
| **Ctrl+H** | Replace... |
| **Ctrl+G** | Go To... |
| **Ctrl+Shift+C** | Describe Character |
| **Ctrl+Alt+C** | Character Details... |

### Edit ▸ Matches

| Key | Command |
|---|---|
| **Ctrl+Shift+F3** | All Matches... |
| **Ctrl+Alt+Shift+F3** | Count Occurrences |

### Edit ▸ Lines

| Key | Command |
|---|---|
| **Ctrl+Shift+Up** | Move Line Up |
| **Ctrl+Shift+Down** | Move Line Down |
| **Ctrl+D** | Duplicate Line |
| **Ctrl+Alt+Shift+J** | Join Lines |
| **Ctrl+Shift+Delete** | Delete Line |
| **Ctrl+Shift+Backspace** | Delete to Start of Line |
| **Ctrl+Alt+Shift+Delete** | Delete to End of Line |
| **Ctrl+Alt+Shift+Backspace** | Delete Paragraph |
| **Ctrl+Alt+Shift+Z** | Restore Deleted Text |
| **Ctrl+Alt+S** | Sort Lines A to Z |
| **Ctrl+Alt+Shift+S** | Sort Lines Z to A |
| **Alt+Shift+Z** | Reverse Lines |
| **Alt+Shift+N** | Number Lines |
| **Ctrl+Alt+K** | Remove Every Blank Line |
| **Ctrl+Alt+D** | Remove Duplicate Lines |
| **Ctrl+Alt+T** | Trim Trailing Spaces |
| **Ctrl+/** | Toggle Line Comment |
| **Ctrl+Shift+Q** | Quote Lines |
| **Ctrl+Alt+Shift+Q** | Remove Quote Marks |
| **Alt+Shift+X** | Delete Lines Containing... |
| **Alt+Shift+W** | Hard Wrap Lines... |
| **Ctrl+Alt+Shift+T** | Tidy Whitespace |

### Edit ▸ Selection

| Key | Command |
|---|---|
| **F8** | Start Selection |
| **Shift+F8** | Complete Selection |
| **Ctrl+Shift+F8** | Reselect Last Selection |
| **Alt+Shift+F8** | Go to Start of Selection |
| **Ctrl+Alt+F8** | Toggle Selection Marker |
| **Alt+Shift+F9** | Extend Selection Mode |
| **Ctrl+Shift+W** | Select Word |
| **Ctrl+Shift+E** | Select Line |
| **Ctrl+Shift+H** | Select Paragraph |
| **Ctrl+Space** | Select Sentence |
| **Ctrl+Alt+Shift+B** | Select Block |
| **Ctrl+Shift+X** | Expand Selection |
| **Ctrl+Alt+Shift+X** | Shrink Selection |
| **Ctrl+Shift+A** | Unselect All |
| **Ctrl+Shift+M** | Set Mark |
| **Ctrl+M** | Pop Mark |
| **Alt+M** | List Marks |
| **Ctrl+Alt+X** | Exchange Cursor and Mark |
| **Ctrl+Shift+Y** | Say Selection |
| **Alt+Shift+U** | Review Buffer... |
| **Ctrl+Alt+Q** | Duplicate Selection |

### Edit ▸ Clipboard

| Key | Command |
|---|---|
| **Ctrl+Alt+Y** | Copy to Tray |
| **Alt+Shift+Y** | Copy to Tray Slot... |
| **Ctrl+Alt+V** | Paste from Tray... |
| **Ctrl+Alt+Shift+Y** | Clear Copy Tray |
| **Alt+Shift+S** | Collect Selection |
| **Ctrl+Alt+Shift+G** | Paste Everything Collected |
| **Ctrl+Alt+Shift+C** | Clear the Collector |
| **Ctrl+Alt+M** | Keep Clip |
| **Ctrl+Alt+Shift+M** | Recent Clips... |

### View

| Key | Command |
|---|---|
| **Alt+Shift+D** | Dark Mode |
| **Alt+Z** | Word Wrap |
| **Ctrl+Alt+F3** | Announce Headings |
| **Ctrl+Alt+F5** | Announce Lists |
| **Ctrl+Alt+Shift+W** | Overwrite Mode |
| **Ctrl+Alt+Shift+I** | Tab Key Inserts a Tab Character |
| **Alt+Shift+B** | Status Bar |
| **Ctrl+=** | Increase Text Size |
| **Ctrl+-** | Decrease Text Size |
| **Ctrl+0** | Reset Text Size |
| **Ctrl+Shift+G** | Document Statistics |
| **Ctrl+Alt+W** | Line Statistics |
| **Ctrl+Shift+P** | Command Palette... |

### Insert

| Key | Command |
|---|---|
| **F5** | Date and Time |
| **Ctrl+Shift+F2** | Special Character... |
| **Alt+.** | Emoji... |
| **Shift+Enter** | Line Break |
| **Ctrl+K** | Link... |
| **Ctrl+Alt+I** | Markdown Tag... |
| **Ctrl+Alt+O** | HTML Tag... |

### Format

| Key | Command |
|---|---|
| **Ctrl+B** | Bold |
| **Ctrl+I** | Italic |
| **Ctrl+U** | Underline |
| **Ctrl+Shift+.** | Grow Font |
| **Ctrl+Shift+,** | Shrink Font |
| **Ctrl+Shift+N** | Normal Text |
| **Ctrl+L** | Align Left |
| **Ctrl+E** | Centre |
| **Ctrl+R** | Align Right |
| **Ctrl+J** | Justify |
| **Ctrl+Shift+L** | Lists |
| **Ctrl+Alt+F** | Editor Font... |
| **Ctrl+Shift+F** | Font for Selection... |
| **Ctrl+Shift+D** | Describe Formatting at Cursor |
| **Alt+Shift+F** | Switch Document Mode |
| **Ctrl+Alt+F6** | Document Language... |

### Format ▸ Line Spacing

| Key | Command |
|---|---|
| **Ctrl+1** | Single Spacing |
| **Ctrl+5** | One and a Half Spacing |
| **Ctrl+2** | Double Spacing |

### Format ▸ Headings

| Key | Command |
|---|---|
| **Ctrl+Alt+1** | Heading 1 |
| **Ctrl+Alt+2** | Heading 2 |
| **Ctrl+Alt+3** | Heading 3 |
| **Ctrl+Alt+4** | Heading 4 |
| **Ctrl+Alt+5** | Heading 5 |
| **Ctrl+Alt+6** | Heading 6 |
| **Ctrl+Alt+0** | Body Text |

### Format ▸ Structure

| Key | Command |
|---|---|
| **Alt+Shift+Left** | Promote Heading |
| **Alt+Shift+Right** | Demote Heading |
| **Alt+Shift+Up** | Move Section Up |
| **Alt+Shift+Down** | Move Section Down |
| **Alt+Shift+F5** | Select Section |
| **Ctrl+Alt+Shift+F5** | Move Section To... |
| **Alt+Shift+O** | Heading Organizer... |

### Navigate

| Key | Command |
|---|---|
| **Alt+Left** | Go Back |
| **Alt+Right** | Go Forward |
| **Ctrl+Alt+H** | Next Heading |
| **Ctrl+Alt+Shift+H** | Previous Heading |
| **Ctrl+Alt+L** | List Headings... |
| **Ctrl+Shift+F9** | Fold or Unfold Section |
| **Ctrl+Alt+Shift+Down** | Next Section |
| **Ctrl+Alt+Shift+Up** | Previous Section |
| **Ctrl+Shift+F10** | Unfold Everything |
| **F6** | Status Bar |
| **Ctrl+Alt+Shift+A** | Go To Anything... |

### Navigate ▸ Bookmarks

| Key | Command |
|---|---|
| **Ctrl+Shift+B** | Set Bookmark |
| **Alt+Shift+G** | Go to Bookmark... |
| **F2** | Next Bookmark |
| **Shift+F2** | Previous Bookmark |
| **Ctrl+Alt+B** | Clear All Bookmarks |
| **Ctrl+Alt+J** | Set Temporary Bookmark |
| **Ctrl+Shift+J** | Go to Temporary Bookmark |
| **Ctrl+Shift+1** | Set Bookmark 1 |
| **Ctrl+Shift+2** | Set Bookmark 2 |
| **Ctrl+Shift+3** | Set Bookmark 3 |
| **Ctrl+Shift+4** | Set Bookmark 4 |
| **Ctrl+Shift+5** | Set Bookmark 5 |
| **Ctrl+Shift+6** | Set Bookmark 6 |
| **Ctrl+Shift+7** | Set Bookmark 7 |
| **Ctrl+Shift+8** | Set Bookmark 8 |
| **Ctrl+Shift+9** | Set Bookmark 9 |

### Tools

| Key | Command |
|---|---|
| **Ctrl+Alt+E** | File Encoding and Line Endings... |
| **Alt+Shift+I** | Snippets... |
| **Ctrl+Alt+A** | Manage Abbreviations... |
| **Alt+Shift+A** | Expand Abbreviations |
| **Ctrl+,** | Preferences... |
| **Ctrl+Alt+F11** | Back Up Settings... |
| **Ctrl+Alt+F12** | Restore Settings... |
| **Ctrl+Alt+F10** | Customize Features... |
| **Ctrl+Alt+Shift+R** | Keyboard Manager... |
| **Alt+Shift+M** | Quiet Mode |
| **Ctrl+Alt+Shift+O** | Sound Scheme... |

### Tools ▸ Spelling

| Key | Command |
|---|---|
| **F7** | Check Spelling... |
| **Alt+Shift+F7** | Spelling for This Word |
| **Alt+Shift+L** | List Misspellings... |
| **Ctrl+F7** | Next Misspelling |
| **Ctrl+Shift+F7** | Previous Misspelling |
| **Ctrl+Alt+F9** | Add Word to Dictionary |
| **Ctrl+Alt+F7** | Check While Typing |
| **Ctrl+Alt+Shift+F7** | Announcements... |

### Tools ▸ AI

| Key | Command |
|---|---|
| **Ctrl+Alt+G** | AI Assistant... |
| **Ctrl+Alt+Z** | Ask About This Document... |
| **Ctrl+Alt+Shift+F9** | Usage... |
| **Ctrl+Alt+Shift+F10** | Connect or Sign Out... |
| **Ctrl+Alt+Shift+K** | Privacy Agreement... |
| **Alt+F2** | Use My Own OpenAI Key... |

### Tools ▸ Dictation

| Key | Command |
|---|---|
| **Ctrl+F11** | Dictation On |
| **Alt+Shift+F6** | Dictation Settings... |

### Tools ▸ Change Case

| Key | Command |
|---|---|
| **Ctrl+Shift+U** | UPPERCASE |
| **Ctrl+Shift+K** | lowercase |
| **Ctrl+Shift+T** | Title Case |
| **Ctrl+Alt+Shift+U** | Sentence case |
| **Ctrl+Alt+Shift+N** | Invert Case |

### Tools ▸ Indenting

| Key | Command |
|---|---|
| **Ctrl+]** | Indent |
| **Ctrl+[** | Outdent |
| **Ctrl+Alt+Shift+V** | Describe Indent Depth |
| **Alt+F11** | Convert to Spaces |
| **Alt+F12** | Convert to Tabs |

### Window

| Key | Command |
|---|---|
| **Ctrl+Tab** | Next Window |
| **Ctrl+F6** | Next Window (MDI) |
| **Ctrl+Shift+Tab** | Previous Window |
| **Ctrl+Shift+F4** | Close Other Documents |

### Help

| Key | Command |
|---|---|
| **F1** | Help for This Window |
| **Ctrl+Alt+F1** | Tutorials... |
| **Ctrl+F1** | Keyboard Shortcuts |
| **Ctrl+Alt+F2** | Get Help from Support... |
| **Ctrl+Alt+U** | Check for Updates... |
| **Shift+F1** | About QUILL Lite |

### Built per window

| Key | Command |
|---|---|
| **Alt+1** to **Alt+9** | Go to that numbered document |
| **Alt+Shift+1** to **Alt+Shift+9** | Reopen that recent file |

### Second keys

A few commands answer to two keys. The first is the one the menu shows; the
second is here because it is the key a hand trained on Word or on a home-row
editor already reaches for. Both work, always, and rebinding the first in the
Keyboard Manager leaves the second alone.

| Second key | Command | The key the menu shows |
|---|---|---|
| **Ctrl+;** | Start Selection | **F8** |
| **Ctrl+'** | Complete Selection | **Shift+F8** |
| **Alt+F7** | Next Misspelling | **Ctrl+F7** |
| **F12** | Save As... | **Ctrl+Shift+S** |
| **Ctrl+F12** | Open... | **Ctrl+O** |
| **Ctrl+Shift+F12** | Print... | **Ctrl+P** |

Two of these read differently on a keyboard than in a table: **Ctrl+Shift+>**
and **Ctrl+Shift+<** are the keys your fingers know, and they are listed above
as `Ctrl+Shift+.` and `Ctrl+Shift+,` because that is the same physical key and
the spelling wx understands.

<!-- keys:end -->

## Getting help

Support is run by **Community Access**, and the address is
**support@community-access.org**. A person reads it, and replies come back by
email.

The quickest way there is **Help > Get Help from Support...** (Ctrl+Alt+F2),
which every app in the family answers with the same form: what kind of message
this is, a subject, what happened, and -- if you want an answer -- an email
address to reply to. What you expected and how to reproduce it are optional,
and worth more than anything else when you can give them.

Press Send and your **own mail program opens with the whole message already
written**, addressed to support, with QUILL Lite's name and version and your Windows
version filled in at the bottom. Nothing is sent until you send it there, so you
can read it over, add anything, or change your mind.

If this machine has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. And writing to **support@community-access.org** yourself always
works just as well: there is no form you have to use. Say which app you were
using and what happened.

### The one thing worth attaching

If QUILL Lite is starting but behaving oddly -- no formatting, every word called
a misspelling, nothing spoken -- run it once with **`--check`**:

```
QuillLite.exe --check
```

It opens no window. It writes a dozen lines to **`check.log`** in your data
folder (**Help ▸ About QUILL Lite** says where that is) and prints the same
lines, saying which version this is, whether it is a frozen build, whether the
native rich-text surface came up, which text mode it is in, which screen reader
it can reach, whether the spelling dictionary actually loaded, and where your
data lives.

Those are the failures that make an app **start and then be quietly wrong**,
which is the worst shape a fault can take when you cannot see the window. Paste
that into your email and the first three questions are already answered.

There are three other options on the same command line: **`--rich`** and
**`--plain`** open with a new document of that kind whatever your setting says,
and **`--new-instance`** starts a second, separate QUILL Lite instead of handing
the file to the one you already have.
