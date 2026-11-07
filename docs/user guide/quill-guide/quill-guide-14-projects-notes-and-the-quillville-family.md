# Chapter 14: Projects, notes and the QuillVille family

This chapter is about the work that is bigger than one document. It starts
small, with sticky notes you can jot from anywhere in Windows, and grows from
there: notebooks of related files, a binder for a whole book, a vault of
linked notes, keeping your work in step between computers, posting to
Mastodon and working with git. It ends with the other apps in the QuillVille
family. Dip in when you need a piece of it; none of it changes how ordinary
editing works.

## Sticky Notes

Sticky notes are the quickest way to catch a thought before it gets away.
**Navigate > Sticky Notes > New Sticky Note...** (or its system-wide hotkey)
opens a small editor with a title and a body, from anywhere.
**Navigate > Sticky Notes > Sticky Notes...**
manages the whole collection.

### The Sticky Notes Browser

**Navigate > Sticky Notes > Sticky Notes Browser...** is the fast way back to a note you wrote
last week.

1. Open the browser. Focus starts in a **search field**.
2. Type anything. The list below filters as you type, matching titles and
   bodies (upper or lower case does not matter), newest note first.
3. Press `Down` to move into the results and arrow through them.
4. Press `Tab` to reach a **read-only multi-line preview** of the selected
   note, so you can read the whole thing without opening it.
5. Press **Edit** (or Enter on a note, or double-click) to open the full
   editor. **Close** (or Escape) dismisses the browser.

Every control announces itself by name.

Give the browser a global hotkey (next topic) and it opens from anywhere in
Windows. QUILL restores its own window first, so the browser always appears,
even when QUILL was minimized to the tray.

## Global Hotkeys

Global hotkeys let a key combination work system-wide: in your browser, your
mail client, anywhere, without switching to QUILL first.

### Assigning a global hotkey

1. Open **Tools > Global Hotkeys...**.
2. Arrow to a command and press **Assign...**.
3. Press the combination you want. It must include **Ctrl or Alt**, because a
   bare key would swallow your normal typing everywhere.

**Clear** removes an assignment. If you assign a key that another QUILL
command already holds, it moves over cleanly. If another *application* owns
the key, Windows refuses it. QUILL tells you which binding failed, and that
binding simply stays inactive until you pick something else.

### Show or hide QUILL (Ctrl+Alt+Shift+Q)

QUILL comes with one global hotkey already set. `Ctrl+Alt+Shift+Q` tucks the
window into the system tray when it is showing, and brings it back, focused,
when it is hidden, from wherever you happen to be. You hear "hidden to the
tray" or "shown". Hiding never stops anything QUILL is doing.

It is an ordinary entry in the Global Hotkeys list, so you can change it or
clear it like any other. If some other program already owns
`Ctrl+Alt+Shift+Q`, that combination stays theirs and QUILL leaves it alone;
pick a different one in this dialog.

Quill Radio and Quill Cast have the same convenience on keys of their own,
so they never clash: **Quill Radio uses Ctrl+Alt+Shift+R** and **Quill Cast
uses Ctrl+Alt+Shift+F12**. Quill Weather, Quill Converter, Quill Media Player
and Quill Inkwell have no key until you choose one, in that app's File menu, under **Show and Hide Key...**, and they will not let you choose a key another
QuillVille app already uses. That is handy for apps that live in the tray
(Quill Weather watching for alerts, Quill Radio playing in the background),
because each is then one keystroke away and you never have to hunt for the
tray icon.

### What can be a global hotkey

Only these commands can be bound:

- Radio: Play/Pause, Stop, Mute/Unmute, Volume Up, Volume Down
- New Sticky Note
- Sticky Notes Browser
- Post to Mastodon. This opens the compose window; nothing is ever sent by
  the hotkey itself.
- Show/Hide QUILL to the tray. This hides the window to the system tray, or
  brings it back and focuses it.

Nothing that edits a document, deletes anything, or acts out of sight can
ever be a global hotkey, no matter what a settings file says. Commands that
open a window restore QUILL first. Media commands act right where you are.
Every press speaks its result ("Radio paused", "Note saved"), so you know what
happened even when QUILL isn't visible.

If you already had a system-wide sticky-note hotkey, it keeps working as it
always has unless you reassign it here.

Global hotkeys are Windows-only, because macOS has no equivalent. Every one
of these commands is still on the menus and in the command palette on every
platform.

## Notebooks

A **Notebook** is a named collection of documents that belong together: a
novel's chapters, a research project's notes, a software project's specs. A
notebook lives in a single `.quillnotebook` file. It remembers which files
are entries, where you left the caret in each, any goals you have set, and
saved snapshots of which entries were open.

### Creating a Notebook

- **File > Notebook > New Notebook** creates an empty notebook and asks for
  a name.
- **File > Notebook > New from Folder** imports a whole folder at once. QUILL
  walks the folder and every folder inside it, and creates one entry per
  supported file. You can filter by extension; the default set covers
  Markdown, plain text, HTML, and source code.

### Moving between entries

With a notebook open, **Navigate > Notebook > Go to Entry...** opens a tree
of entries, grouped by subfolder. Select an entry and press Enter (or the
"Open Entry" button) to open that file.

**Navigate > Notebook > Go to Heading...** reads every entry file and gives
you a two-level tree of their headings.

### The Entries panel

Turn on **View > Show Entries Panel** to dock a panel on the left side of
the window. It shows the notebook name, today's goal progress, a filter
field, and the full list of entries. Type in the filter field to narrow the
list by title.

### Goals

Each notebook can carry a daily word-count goal, stored in its
`.quillnotebook` file. When the goal is on, the **Notebook Goal** cell in the
status bar shows your progress, for example "1,234 / 500 words". When you
reach the target it changes to "Goal reached."

### Versions

A version is a named record of which entries were open at one moment. Choose
**File > Notebook > Save Version...**, type a name (QUILL suggests "Version 1",
"Version 2" and so on) and press Enter. **File > Notebook > Manage Versions...**
lists every version you have saved, with the date, and has **Rename** and
**Delete** buttons. **Restore Version...** opens the same list. Versions are
not autosave recovery. They are saves you make yourself, like checkpoints for
a writing session.

Don't confuse them with the **File > Snapshots** menu, which used to be
called "Workspace Snapshots". That one saves and restores the set of
documents open in the editor: a lightweight workspace for any files, not tied
to a notebook. Notebook versions keep the open entries of one notebook.

### A notebook in WSL or on a network share

The Open Notebook dialog is the standard Windows file dialog, so it reaches
anywhere Windows can, including the WSL file system and UNC network shares.
There is no "WSL" button, because Windows shows those places itself.

To open a notebook stored in WSL, type or paste the UNC path into the
dialog's address bar, for example
`\\wsl.localhost\Ubuntu\home\you\writing\my.quillnotebook` (the older
`\\wsl$\Ubuntu\...` form also works). QUILL keeps whatever path you give it,
so the notebook and all its documents can live in WSL. You do not need SSH
to reach your own WSL files; SSH is only for files on a *separate* Linux
machine you want to edit remotely.

Two things to expect: reading and writing across the WSL bridge is slower
than on a Windows drive, and live refresh when a file changes may behave
differently there. For a notebook you edit heavily, a Windows path is
snappier.

## Story Studio

Story Studio organizes a whole book. **Tools > Story Studio...** (also in the
command palette as *Story Studio*) opens a **binder** for a project folder: a
tree of your whole project that you move through with the arrow keys.

- **Manuscript** holds your chapters and scenes, taken from the Markdown
  headings in your manuscript files. Press Enter on a chapter to open its
  file at that heading.
- **Characters, Places, Plot threads, Research, Brainstorm** have one entry
  per element file. Press Enter to open it.

Two buttons act on the binder:

- **Edit details...** works on a selected element. It opens a form for that
  element's fields: a character's Role, Goal, Motivation and Arc, a plot
  thread's Status, and tags. The values are saved as front matter at the top
  of the element's file. Blank fields are left out, and any keys you added by
  hand are kept.
- **Compile manuscript...** joins every manuscript file, in order, into a new
  document, with the front matter taken out. Use **File > Export** on that
  document to save it as Markdown, HTML, Word, DAISY, and more.

A Story project is just a folder of plain-text files plus a small
`project.quillstory.json` file that records the binder order and the element
groups. If you delete that file, none of your writing is lost. Story Studio
is optional and changes nothing about ordinary editing.

## Vault

**Tools > Vault** turns a folder of notes into a linked-notes workspace:
links and backlinks, search, tags, embeds, templates, daily notes, and a
website export. It is built for the keyboard and the ear, with lists you
arrow through instead of a visual graph. Until you open a vault, nothing
about ordinary editing changes.

A vault is just a folder of Markdown files plus a small `.quill` cache.
Delete the cache and nothing is lost. Every command here is in the command
palette, and you can give any of them a key in the Keymap Editor.

### Getting around your notes

- **Open Vault...** Choose a folder of notes. QUILL scans and indexes it,
  remembers it, and says "Vault *name*: N notes, M links." You do this once
  per notes folder.
- **Follow Wikilink** Put the cursor on a `[[Note]]` link and run this to
  open that note. A `[[Note#Heading]]` link opens at the heading, and
  `[[Note#^block]]` at the block. If the note does not exist yet, QUILL
  offers to **create** it. If several notes share the name, QUILL asks which
  one; it never guesses.
- **Show Backlinks** lists every note that links to the one you are in, each
  read with the sentence the link sits in. QUILL tells you how many notes
  link here. Press Enter on one to open it at that mention.
- **Note Neighborhood** gives you both directions in one list: the notes
  this one links out to (marked with a right arrow) and the notes that link
  back to it (marked with a left arrow), so you can step through everything
  connected to where you are. Enter opens the one you land on.
- **Unlinked Mentions** finds places in your other notes that mention this
  note by name but don't link to it yet. Each is read with its sentence, and
  Enter opens that note at the mention so you can turn it into a link.
- **Insert Link to Note...** lets you pick a note by title from a list, and
  inserts `[[Title]]` at the cursor.
- **Rename Note...** gives the current note a new name. First QUILL tells you
  how many links in how many other notes point to it, and asks you to
  confirm. Then it updates all of those `[[links]]`, renames the file, and
  fixes the note's own top heading, so nothing breaks. Nothing changes until
  you say yes, and QUILL stops if a note with the new name already exists.
- **Vault Explorer...** is a tree of every note, grouped by folder. Arrow
  through it and press Enter on a note to open it.
- **Complete Link or Tag...** Start typing `[[` (for a note) or `#` (for a
  tag), run this, and pick from a list that narrows as you type. QUILL
  inserts your choice and, for a link, adds the closing `]]`. It does the job
  of a pop-up that appears as you type, but it speaks and holds focus.
- **Go to Note...** jumps to a note. Start typing part of a title and the
  list narrows as you go, with QUILL speaking the count. Press Down to move
  into the list, or press Enter to open the closest match.
- **Search Vault...** searches every note. Type a word or phrase and hear the
  number of results. Each result reads as its note title, line number, and
  the matching text. Turn on **Regex** for pattern searches, or **Whole
  word** to skip partial matches. Enter opens a result at its exact line.

### Tags, embeds and templates

- **Show Tags...** opens the tag pane. Filter your `#tags` (each shows a note
  count), open a tag, and get the list of notes that carry it. Nested tags
  roll up, so `#area` also finds notes tagged `#area/sub`.
- **Speak Embed at Cursor** With the cursor on an `![[Other Note]]` embed,
  hear the note (or the heading or block) it pulls in, without changing your
  text.
- **Resolve Embed Inline** replaces that `![[embed]]` with the actual
  content, as one change you can undo with `Ctrl+Z`.
- **Insert Template...** Pick a template from a `Templates` folder inside
  your vault. QUILL fills in `{{date}}`, `{{time}}` and `{{title}}`, asks you
  out loud any `{{prompt:Question}}` it finds, inserts the result, and puts
  the cursor where you marked `{{cursor}}`.
- **Open Today's Note**, **Previous Daily Note**, **Next Daily Note** open
  today's dated note (creating it if needed) and step back and forward
  through the days. Daily notes live at `Journal/YYYY-MM-DD.md` by default.

### Sharing your vault

- **Export Vault as Website...** Choose an output folder and QUILL writes a
  small website that needs nothing else: one accessible page per note, your
  `[[links]]` turned into real links between pages, your `![[embeds]]`
  filled in, and an index page listing everything. It runs in the background
  and tells you how many pages it wrote.
- **Sync Vault** If your vault folder is a Git repository with a remote you
  control, this commits your changes, pulls anyone else's, and pushes, all in
  the background. If the same note changed in both places, QUILL lists the
  conflicts and stops instead of overwriting anything. It is disabled in Safe
  Mode. The same sync works on any folder, not just a vault; see
  [QUILL Sync](#quill-sync) below.
- **Vault Settings...** sets the folder your templates live in (default
  `Templates`) and the pattern for daily-note file names (default
  `Journal/{{date:YYYY-MM-DD}}.md`). Leave a box empty to keep the default.

### How links work

Write a link by typing `[[Note Title]]` yourself, or use **Insert Link to
Note...**. Links are plain text in your file, with nothing hidden, and they
are resolved when you follow them, export, or build the website.

When you **preview** a note that lives in your vault, QUILL shows it
resolved: `[[links]]` read as their titles, and `![[embeds]]` filled in.
Every time you **save** a note in the vault, its links, backlinks, tags and
search results update straight away, with no need to reopen anything.

## One Editor, Every Format

Every document opens in the same QUILL editor, and it has a real rich text
mode. The thing to hold onto: **bold means bold, and QUILL speaks your
document's language.** The braille fix is on by default in every format; the
braille troubleshooting entry in Chapter 11, Accessibility, speech and
braille, has the details.

- **Writing Markdown (.md):** `Ctrl+B` wraps your selection in `**`, and
  Insert Heading 2 puts `## ` at the start of the line.
- **Writing HTML (.html):** `Ctrl+B` wraps in `<strong>`, and headings become
  real HTML headings.
- **Writing Rich Text (.rtf):** the document opens *formatted*. `Ctrl+B`
  applies real bold, and Insert Heading 2 applies a real sized heading. The
  Format menu's font, size, color, highlight and alignment commands change
  the actual formatting, and **Describe Formatting at Cursor** answers from
  the live document ("Arial, 14 point, bold, centered"). Search, spell check,
  read aloud, bookmarks, notes and braille all work as in any other document.
- **Writing plain text (.txt):** text stays plain, because that is what a
  .txt file promises. The first time you press a formatting key, QUILL asks
  once: treat this document as Markdown, convert it to Rich Text, or stay
  plain. Your answer is remembered for that document.
- **Editing Word documents (.docx):** a .docx can open for real rich editing
  and save back as a genuine Word file, in an installed copy and a portable
  copy alike (*Office files at a glance* in Chapter 3 lists what every other
  Office file does). If the file holds things QUILL's
  editor cannot keep (images, comments, tracked changes, headers and
  footers), QUILL asks first. That includes a header or footer that only
  appears on the first page, or only on even pages: Word keeps those
  separately from the ordinary ones, and QUILL names them as "headers" or
  "footers" all the same, in any section of the document. You can open it for reading and plain editing
  (the safe default), edit it as Rich Text with those losses named one by
  one, or edit a copy. The first rich save over such a file writes a
  timestamped backup next to it automatically. **Tables are preserved** when
  you open a Word document for rich editing: they appear inline as
  accessible tables, so you can read them and jump to them with single-key
  table navigation (`T`).

  What the three choices look like: a window titled **Open Word document**
  says, for example, "team.docx contains features QUILL's rich editor cannot
  carry: tables (1), comments. How should it open?" The first row, **Open for
  reading and plain editing (recommended)**, is selected, and **Escape** gives
  the same answer. The backup is named after the original with the date and
  time added, for example `team.backup-20261017-143005.docx`, sits beside it,
  and is made once each time you open the file, before your first save; QUILL
  says "Backed up the original to ..." on the status bar. Inside the document,
  **Ctrl+Alt+Right**, **Ctrl+Alt+Left**, **Ctrl+Alt+Down** and
  **Ctrl+Alt+Up** move cell by cell through a table and say where you are
  ("Row 2: Ann"); **Alt+Home** and **Alt+End** go to the
  ends of the row, **Ctrl+Alt+Home** and **Ctrl+Alt+End** to the ends of the
  table.

  QUILL Lite edits Word documents too, since October 2026, with this same
  code: the same question in the same words, the same backup, the same table
  keys. A document saved in one opens the same way in the other.

  Fixed on 2026-10-17, in both: saving a Word document a second time no
  longer turns its Heading 5 and Heading 6 paragraphs into bold ordinary text,
  and saving no longer adds a blank paragraph at the end each time.

### The Document Format switcher

**Format > Document Format...** moves the current document between Plain
text, Markdown, HTML, Rich Text (RTF) and Word (.docx) while you work. You
can also press `Alt+Shift+F`, use the command palette, or press Enter on the
**Format** cell in the status bar, which always shows your current format.

Switching to a rich format turns your Markdown headings into real ones.
Leaving a rich format warns you first, with a list of exactly what will not
survive. A switched document never quietly overwrites its old file: the next
save suggests the matching new name.

**Every switch is a real conversion.** Switching to HTML writes real HTML
(`<h1>` and `<strong>`, not hashes and asterisks under an HTML label), and
switching back reads it in again. Your formatting comes with you in every
direction: headings, bold, italic, underline, strikethrough, superscript and
subscript, font family and size, text colour and highlight, bullet and
numbered lists, links, code spans and fences, block quotes, alignment, line
spacing, indents, spacing before and after, named styles, page breaks,
tables, images and horizontal rules. Switch out and back as often as you
like; you end up with the document you started with.

**Converting to Plain text asks you first.** Plain text has no formatting,
so there are two fair ways to handle Markdown already in your document, and
QUILL won't guess:

- **Remove the markers.** `# Heading` becomes `Heading`, `**bold**` becomes
  `bold`, and the file is strictly plain.
- **Keep them as text.** The `#` and `**` stay as ordinary characters. A .txt
  file is allowed to contain them, and plenty of people keep their notes that
  way.

Escape (or Cancel) leaves the document alone. You are only asked when there
is something to ask about; ordinary prose converts without a question.

### If rich mode is unavailable

On a system where the bundled macOS bridge or the Windows COM bridge cannot
load, .rtf and .docx documents open converted to editable text, the classic
way, and save back through the same converters. Nothing is lost, and QUILL
says so in the status bar. The Mac app includes everything rich mode needs;
only source installs add it themselves (`pip install "quill[mac]"`). If you
ever see the converted fallback on a normal install, please tell us through
**Help > Get Help from Support**.

## Table Studio (experimental)

Turn Table Studio on in the Experimental tab, and **Tools > Writing and Language > Table Studio...**
opens a table in a spreadsheet-style grid made for screen-reader users,
instead of a wall of pipe characters. One grid does two jobs:

- **Table Studio** starts a new table you build up cell by cell.
- **Open CSV in Table Studio** opens a `.csv` or `.tsv` file straight into
  the grid. The delimiter is detected for you.

With Table Studio on, opening a `.csv` from **File > Open** and choosing the
grid view brings it up in the same grid.

### Moving and editing in the grid

The **arrow keys move by cell**. Up and Down change rows, and **Left and
Right move across columns and speak the column heading** as you go, so you
always know where you are.

- **Home** and **End** jump to the first and last column.
- **Ctrl+Home** and **Ctrl+End** jump to the corners.
- **Page Up/Down** move by ten rows.
- **F2** or **Enter** edits the active cell.
- **Alt+arrows** move a whole row or column.
- **Ctrl+Insert** adds a row.
- **Delete** clears a cell.

The same actions are on buttons if you prefer them.

### The table menu

**Shift+F10** (or the Applications key, or right-click) opens a context menu
with every table action in one place: **Sort Ascending / Descending** by the
current column, **Insert / Delete / Move** rows, **Insert / Delete** columns,
**Rename Column Header**, **Promote First Row to Header** (for a CSV whose
header row was read as data), and **Use First Column as Row Headers**.

Headers are stored the standard way: `<th scope="col">` and
`<th scope="row">` in HTML, and a proper header row in Markdown. That way
screen readers and other tools understand your table's structure.

### Finishing a table

**Insert as Markdown** or **Insert as HTML** drops the finished table, with
its headers, into your document. **Save to CSV** writes the grid back to a
file, so a CSV you opened makes the full round trip.

NVDA and JAWS announce the column as you cross a row. Builds that include the
optional native provider give richer cell announcements; without it QUILL
uses a built-in fallback, and the feature works either way.

## QUILL Sync

QUILL has no sync service of its own: no QUILL cloud account and no
QUILL-hosted storage. To carry your work between devices it uses two things
that already do the job well, a folder your cloud provider mirrors, and git.
Both are optional.

### Sync your settings through a folder

1. Open **Help > Personalise QUILL** (or **Preferences**) and find "Where
   should QUILL store your data?". It is the same page the first-run wizard
   shows.
2. Choose **"Choose a folder:"**.
3. Pick a folder that OneDrive, Dropbox, Google Drive or iCloud already keeps
   in step across your devices, or a folder on a USB drive you carry between
   computers.

QUILL writes its settings, snippets, dictionaries and keymap there, and your
cloud provider or drive carries them to your other computers like everything
else in that folder. This is the Data Location setting; there is nothing new
to learn.

One important limit: QUILL cannot merge changes made on two devices at once.
Don't run QUILL on two machines pointed at the same synced folder at the
same time. Treat it like any shared file, one writer at a time.

### Sync a folder with GitHub

**Tools > Git and GitHub > GitHub > Sync Folder with GitHub...** works on any
folder, such as a writing project or a research folder, not just a vault.
Point it at a folder:

- If the folder is already a git repository with a remote set up, QUILL
  commits your changes, pulls anyone else's and pushes, all in the
  background, and tells you when it's done.
- If it isn't set up yet, QUILL says so plainly and asks first, for example:
  *"This folder is not a git repository yet. QUILL can set it up: this runs
  'git init' in the folder, then adds the remote repository you provide as
  'origin'. Continue?"* Say yes, paste your repository's address (for
  example `https://github.com/you/your-repo.git`), and QUILL sets it up and
  syncs.
- If the same file changed in both places, QUILL lists the conflicts and
  stops instead of guessing. Resolve them yourself (the conflict walker under
  Local Git helps), then run Sync Folder with GitHub again.

If you already use **Sync Vault**, this works exactly the same way, for any
folder. Both use your own git installation and the credentials it already
remembers (an SSH key, or a login your system's git credential manager
keeps). QUILL never asks for or stores a separate GitHub password or token
for this. Disabled in Safe Mode.

## Publishing

You can share what you write without leaving QUILL. This topic covers
posting to Mastodon.

### Posting to Mastodon

1. Press the QUILL key (`Ctrl+Shift+Grave`) then `Shift+P`, or choose
   **Tools > Share > Post to Mastodon...**. QUILL takes your selection, or the
   whole document if nothing is selected, and opens a compose window.
2. Edit the text if you like, pick the account to post from, and choose the
   visibility: Public, Unlisted, Followers only, or Direct. A live character
   count keeps track as you type.
3. Press **Post**. Your post appears with "via QUILL" as its source.

The compose window also has a **Post language** picker beside the
visibility choice. The default, "Default (instance)", sends no language, so
your server files the post under your account's default language. Pick a
language such as English or Italian to send its ISO 639-1 code, which keeps
a post in one language from being filed under another.

The character count uses your account's real limit on its own server, not
the classic limit. QUILL asks the server once per session and remembers the
answer, so a server that allows more (for example one with a 9999-character
limit) shows the right count and does not block a longer post.

### Adding a Mastodon account

The first time you post, QUILL offers to add an account. You can also open
**Tools > Share > Mastodon Accounts...** at any time.

1. Choose **Add Account...**, then enter your server (for example
   `mastodon.social`) and a **friendly nickname**. The nickname is what shows
   in the account picker.
2. QUILL registers itself with your server and opens your browser. Sign in if
   needed, approve QUILL, and copy the authorization code your server shows.
3. Paste that code back into QUILL. Your account is saved.

You can add several accounts, each with its own nickname, **set a default**,
or **remove** one (which deletes its saved sign-in from this computer). Your
sign-in is kept in the Windows Credential Manager, never in a plain file.

**Proofread posts before sending.** In **Mastodon Accounts...**, select an
account and check **Spell-check posts before sending**. It is off by default
and set per account, so you can turn it on for some accounts and not
others. When it is on, pressing **Post** for that account first opens the
Spelling Review (`F7`) on the post, and the post is sent only after you
finish or skip the review.

### Adding someone to a Mastodon list

Mastodon lists let you follow a group of accounts in a timeline of their own.
To put someone on one of your lists:

1. Choose **Tools > Share > Add a User to a Mastodon List...**.
2. Type their handle, such as `@name@server`, and press Enter. QUILL looks
   them up and fetches your lists.
3. Choose the list from the list QUILL shows you, and press Enter.

QUILL says "Added", the person and the list. Mastodon only lets you add
someone you already follow, so if they are not on the list afterwards, follow
them first (View Mastodon Profile, below, has a Follow button) and try again.
If you have no lists yet, QUILL tells you; make one on your Mastodon server
first.

### Reading a Mastodon profile aloud

Open **Tools > Share > View Mastodon Profile...** and type a handle such as
`@name@server`. QUILL shows the account's name, whether each of you follows
the other, a Follow or Unfollow button, the account's **Bio**, and its
**Recent posts**.

Everything there is tidied for listening. Mastodon sends bios and posts as
web markup, which a screen reader would otherwise read aloud tags and all.
QUILL turns them into plain text first, so you hear the words. In a link, you
hear the part your server chose to show, not the long hidden tail.

Three more changes make the profile easier on the ear:

- **A pile of mentions is counted, not recited.** A reply that starts by
  addressing several people reads as `@alice and 2 more`, then the message.
  You still learn who was addressed and how many, and you reach the first
  real word straight away. A reply that names one person is left as written.
- **Decorative characters are removed from names and posts.** A screen
  reader says an emoji's full name ("grinning face with smiling eyes") every
  time it appears, in every row. QUILL strips emoji and similar decoration,
  and keeps accented letters, other alphabets, quotation marks, dashes and
  currency signs, which are part of real words. If a display name was
  nothing but decoration, QUILL uses the plain handle.
- **Each post is one line: when, then its first sentence.** For example
  `3 minutes ago: Actually, that is wrong.` The time is in plain words, so
  there is no timestamp to work out in your head, and the summary stops at
  the first sentence, so each arrow press gives you one post. A post with a
  content warning shows the warning instead of the text.

If the account is private, or your server does not share its posts, the
profile still opens; the Recent posts list is simply not there.

## Local Git

**Tools > Git and GitHub > Local Git** brings the two hardest parts of
everyday git into QUILL as guided steps you can follow by ear: resolving a
merge conflict, and reordering commits with an interactive rebase. None of it
needs a GitHub account or the network; it works on any git repository on
your computer.

### Uncommitted changes

**Uncommitted Changes...** shows every file you have changed since your last
commit, split into staged and unstaged. Select a file to read its changes in
the same style as Compare Documents, instead of a raw diff. Press **Stage**
or **Unstage** for the selected file, or **Stage All** to stage everything.

### Resolving a merge conflict

Git marks a conflict with lines of `<<<<<<<`, `=======` and `>>>>>>>`, which
sound like line noise through a screen reader. **Resolve Conflicts...** walks
you through every conflict in every affected file, one at a time: "Conflict 1
of 3: your version says X, their version says Y." For each one you choose:

- keep your version,
- keep their version,
- keep both, or
- type your own replacement.

Move to the next or previous conflict as you go. When you're done, QUILL
writes the resolved file and stages it for you.

The same walker opens on its own if an **Interactive Rebase...** or a **Sync
Folder with GitHub** stops because of a conflict, so you finish in one place.

### Interactive rebase

**Interactive Rebase...** does the job of `git rebase -i`, which normally
drops you in a text editor to reorder and mark up commits by eye. QUILL shows
a real list instead, one commit per row:

1. For each commit, choose an action from the dropdown: pick, squash, reword,
   or drop.
2. Use **Move Up** and **Move Down** to change the order.
3. Press **Start Rebase** when the plan is right.

If a step conflicts, the conflict walker opens; resolve it and the rebase
carries on by itself. **Abort Rebase** puts your branch back exactly where it
started if you change your mind partway.

### More Local Git commands

- **Switch Branch...** lists your local branches and switches to the one you
  choose. If you have uncommitted changes, QUILL warns you and offers to
  switch anyway and bring them along. It never quietly throws them away, and
  it doesn't just refuse.
- **Stash Changes... / Manage Stashes...** put your uncommitted work aside
  under a name you'll recognize, then list, apply or drop any stash later,
  with no `stash@{2}` references to remember.
- **Who Wrote This Line...** runs `git blame` on the line your cursor is on
  and tells you who last changed it, when, and the commit's summary.
- **Start Bisect... / End Bisect** runs a `git bisect` session as plain
  questions and answers. QUILL checks out a commit and asks "Is this version
  good or bad?" Answer, and it narrows the search until it tells you exactly
  which commit brought in the problem.

None of these commands has a default key, because every letter after the
QUILL key is already taken. All twelve are in the command palette and on the
**Tools > Git and GitHub > Local Git** menu, and you can give any of them your
own key in the Keymap Editor.

### Worktrees

A git repository is normally one folder holding one branch at a time.
Switching branches rewrites every file in that folder to match the new
branch, keeping the same names and paths.

A **worktree** is a second folder attached to the same repository, with a
different branch checked out in it. The folders share one history, one set
of branches and one set of stashes, but each has its own copy of the files.
You might have `quill` on `main` and `quill-feature-x` on `feature/x`, side by
side.

This matters more when you use a screen reader. Switch branches in place and
the document you have open in QUILL is replaced by a different document with
the same name. Someone looking at the screen sees the text change. With a
screen reader nothing tells you: the paragraph under your review cursor now
comes from another branch, in a file that still has the name of the one you
opened. With a worktree, nothing under your cursor changes. Moving to other
work means opening a different file, which you do and hear, instead of a file
quietly becoming a different file.

#### Seeing what you have

**Tools > Git and GitHub > Local Git > Worktrees...** opens the list. QUILL
says how many worktrees the repository has as the dialog opens, and each row
reads as a whole sentence, so there are no columns to arrow across:

- *"Main worktree at S:\code\quill, on branch main"*
- *"Linked worktree at S:\code\quill-feature-x, on branch feature/x"*
- *"Linked worktree at D:\usb\quill-spike, on branch spike, locked: on a USB
  drive"*
- *"Linked worktree at S:\code\quill-old, on branch old, missing from disk,
  ready to prune"*

A worktree that is not on a branch reads as *"not on a branch, at commit
3f9a21c"*. After any action, QUILL speaks the result, rereads the list and
puts focus back on it, so you never have to hunt for your place.

#### Creating one

Press **New Worktree...** in the list, or run **Local Git: New Worktree...**
from the command palette to skip the list. The form asks for:

- **Folder for the new worktree**: where the new folder should go. Type or
  paste it, or press **Browse...**. The field accepts whatever you paste: a
  path copied from File Explorer with the quotes still on, an
  `%APPDATA%`-style path, a `file://` link, or a leading `~`.
- **Branch to check out**: a list of your local branches. Branches already
  checked out in another worktree are left out, because git won't allow the
  same branch twice.
- **Create a new branch instead**: check this to make a brand-new branch here
  instead of checking out an existing one.
- **New branch name** and **Start the new branch from**: used only when the
  checkbox is checked. Leave the starting point blank to branch from where you
  are now, or name a branch, tag or commit to start from.

QUILL checks everything before it runs git, and tells you what is wrong if
something is: a folder that already has files in it, a folder inside the
repository itself (git won't allow that), no branch chosen, or no new branch
name typed.

#### Opening one

Select a worktree and press **Open in QUILL**, or just press Enter on the
row. QUILL opens documents, not folders, so this means "open the same file
from over there". QUILL works out where your current document sits in its own
worktree and opens the matching file in the one you chose. If that file
doesn't exist there (it is new on your branch, or nothing was open), QUILL
says so and gives you a file picker already in the worktree's folder.

#### Removing, locking and tidying up

- **Remove...** deletes a worktree's folder from your disk. The branch stays
  in the repository; you are removing the folder, not the work. QUILL always
  confirms first, with **No** as the default button, so pressing Enter out of
  habit never destroys anything.
- **If the worktree still has uncommitted changes, git refuses**, and QUILL
  tells you so in plain language instead of forcing it. Only then does it ask
  a second, separate question: discard those changes and remove it anyway?
  That is two confirmations, never one.
- **Lock** marks a worktree as "leave this alone", with an optional reason
  you'll hear later in the list. Do this for a worktree on a USB drive or a
  network share, which git would otherwise treat as a folder that vanished.
  The button reads **Unlock** when the selected worktree is already locked.
- **Prune** forgets any worktree whose folder is really gone from disk and
  tells you which ones it tidied up. When there is nothing to do, it says
  *"Nothing to tidy up: every worktree is still on disk."*
- The **main** worktree (the repository folder itself) can never be removed
  or locked here; those buttons are unavailable while it is selected.

#### Good to know about worktrees

- **A branch can only be checked out in one worktree at a time.** That is
  git's rule. If you pick a branch that is open somewhere else, QUILL tells
  you which folder has it so you can open that folder instead.
- **A worktree cannot live inside the repository it belongs to.** Put it
  beside the repository folder.
- **Removing a worktree with uncommitted changes is refused** unless you
  confirm twice, as above.
- **Worktrees need `git`**, like everything under Tools > Git and GitHub >
  Local Git, and they are disabled in Safe Mode.

#### Worktree keys

Neither worktree command has a default key, for the same reason as the other
Local Git commands. Both are on **Tools > Git and GitHub > Local Git** and in
the command palette (**Local Git: Worktrees...** and **Local Git: New
Worktree...**), and you can give either a key in the Keymap Editor.

In the Worktrees dialog:

- **Tab** and **Shift+Tab** move between the list and the buttons.
- **Up** and **Down** arrow move through the worktrees.
- **Enter** or **Space** on a row is the same as **Open in QUILL**.
- Access keys: **Alt+N** New Worktree, **Alt+O** Open in QUILL, **Alt+R**
  Remove, **Alt+L** Lock or Unlock, **Alt+P** Prune.
- **Escape** closes the dialog.

In **New Worktree**:

- **Alt+F** the folder field, **Alt+B** Browse, **Alt+C** the branch chooser.
- **Alt+N** the "create a new branch" checkbox, **Alt+A** the new branch
  name, **Alt+R** the starting point.
- **Enter** creates the worktree, and **Escape** cancels.

### Downloading git and the GitHub CLI

The Local Git commands, and the Codespaces commands under
**Tools > Git and GitHub > GitHub**, need `git` and `gh` (the GitHub CLI) on
your computer. QUILL looks for copies you already have first: if `git` or
`gh` is already on your system PATH, QUILL uses it and you need nothing more.

If you don't have them, **Help > Download Optional Components** has a row for
each:

- **Git**: Windows only, a portable copy of Git for Windows, about 40 MB.
- **GitHub CLI**: Windows and macOS, about 14 MB.

Both are exact copies of the official releases, checksum-verified like every
other optional component. Download either one and its commands work
straight away, with no separate install, no PATH changes and no restart. You
can remove either one later from the same dialog; removing one never affects
the other, even though they are stored in the same place.

## Quill Radio and the QuillVille family

Internet radio is not part of QUILL. It is **Quill Radio**, a free app of its
own in the QuillVille family, with its own window, its own keyboard-first
design, and its own complete User Guide (open it from the app's Help menu).
The other companions are the same: **Quill Weather**, **QUILL Audio Studio**,
**Quill Inkwell**, **Quill Converter**, **QUILL Transcribe** (released on 1
November 2026, it types what you say into any program, not only into QUILL),
and the rest.

They share QUILL's code, settings and data where that helps you. A station
you favorite in Quill Radio, or an abbreviation you add in Quill Inkwell, is
the same on both sides. Each app is documented in its own guide, not here.

**The QuillVille menu** sits just before Help in QUILL's menu bar, and in
every QuillVille app. It is where they all meet: it lists every app in the
family, launches the ones you have, and offers to download the ones you
don't. That menu, and this short note, are all QUILL's guide has to say about
them.

> **QUILLBert found something:** he opened the QuillVille menu looking for
> the way back to his document, and launched a radio station instead. He
> stayed for three songs. If that happens to you, `Ctrl+Alt+Shift+R` tucks
> Quill Radio into the tray and the music keeps playing.

## What you learned, and where to go next

You can now catch a thought in a sticky note from anywhere, find it again in
the Sticky Notes Browser, and set up global hotkeys, including
`Ctrl+Alt+Shift+Q` to show or hide QUILL. You know how to gather files in a
notebook, organize a book in Story Studio, link your notes in a vault, move
between formats, build tables in Table Studio, sync with a folder or GitHub,
post to Mastodon, and handle conflicts, rebases and worktrees in Local Git.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try "QUILL and
the apps around it". On the website, read
[Start an Accessible Vault](https://www.quillforall.org/tutorials/05-start-a-vault.html),
[GitHub inside QUILL](https://www.quillforall.org/tutorials/08-github-inside-quill.html),
[Internet Radio with Quill Radio](https://www.quillforall.org/tutorials/09-internet-radio.html)
and
[Podcasts with QUILL Cast](https://www.quillforall.org/tutorials/10-podcasts.html).

Next, Chapter 15, Help, updates and support, shows where to turn when you are
stuck and how to keep QUILL up to date.

---

- Previous: [Chapter 13: Keeping your work safe](quill-guide-13-keeping-your-work-safe.html)
- Next: [Chapter 15: Help, updates and support](quill-guide-15-help-updates-and-support.html)
- [Contents](../userguide.html)
