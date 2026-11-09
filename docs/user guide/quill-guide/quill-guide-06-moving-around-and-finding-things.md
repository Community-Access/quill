# Chapter 6: Moving around and finding things

Long documents are where a screen reader user loses the most time, so QUILL
gives you a lot of ways to get from here to there without listening to
everything in between. This chapter starts with the everyday things: finding a
word, jumping to a line or a heading, and getting back to where you were. Then
it moves on to bookmarks, Quick Nav, folding, inline notes and the tools for
code and tidy text. If you work with transcripts, legal text, long Markdown
notes, HTML source or text pulled out of a PDF, this is the chapter to spend
time with.

## Search and replace

### Finding text (Ctrl+F)

These are the keys you will use every day:

- `Ctrl+F` opens Find.
- `F3` finds the next match, and `Shift+F3` finds the previous one.
- `Ctrl+Shift+F3` opens **Find All Matches**, a summary of every match in one
  list. (It used to be on `Alt+F3`, which now belongs to Reveal Codes.)
- `Ctrl+H` opens Replace.
- `Ctrl+Shift+Grave` then `X` replaces all.
- `Ctrl+Shift+F10` opens **Find in Open Documents**, which finds and
  replaces across every document you have open (see below).

**Find Next**, **Find Previous** and **Find All Matches** live on the **Edit**
menu, beside Find and Replace.

### Search modes

You can search for plain text, whole words, wildcards or a regular expression.
If regular expressions are new to you, the Regular Expression Helper
(**Tools > Advanced > Regular Expression Helper...**) explains the syntax
when you need it. QUILL also keeps your search history, so a search you run
often is there waiting for you next time.

**What you type in Replace with is what goes in.** Unless you are searching
with a regular expression, the Replace box is taken exactly as typed, in plain
and wildcard searches alike. A backslash is just a backslash: replacing a
folder name with `C:\new\reports` puts exactly that into every match, and `\1`
goes in as the two characters you typed. With a regular expression, **Replace
All** (`Ctrl+Shift+Grave` then `X`) and **Edit > Replace Across Files...**
(`Ctrl+Shift+R`) can refer back to the match: `\1` is the first part you
wrapped in brackets and `\2` the second, so searching for `(\w+), (\w+)` and
replacing all with `\2 \1` turns "Bishop, Jeff" into "Jeff Bishop".

### Searching a whole folder of files

QUILL no longer has a top-level Search menu. Its commands now live on the
**Edit** menu. Three searches reach wider than the document in front of you,
and they sit together directly under **Find All Matches**, in every feature
profile, including the one a new install starts with:

- **Edit > Find in Open Documents...** (`Ctrl+Shift+F10`) searches every
  document you have open (see below).
- **Edit > Search in Files...** (`Ctrl+Alt+Shift+F`) searches every file in a
  folder, and every folder inside it, without opening them.
- **Edit > Replace Across Files...** (`Ctrl+Shift+R`) does the same search and
  replaces what it finds, in the files on disk.

QUILL Lite has the same three rows in the same order on its own Edit menu, on
the same keys, so what you learn in one editor works in the other.

Both folder commands open one window. Fill in the **Starting folder** (it
starts as the folder of the document you have open), a **File pattern** such
as `*.md` or `*.txt`, and the **Search text**. Under **Match mode** choose
Plain text, Wildcard or Regular expression, and check **Case sensitive** or
**Whole word** if you need them. **Output format** decides how much the results
tell you: filenames only, filenames with line numbers and counts, counts only,
or each filename with the matching lines around it. Replace Across Files adds a
**Replacement** box and **Preview before replacing**, which shows you every
change in a tab of its own and asks before it writes anything.

The **File pattern** can name more than one kind of file. Put `|` between two
patterns to take either, `&` to need both, and `!` before one to leave it out;
double quotes around a name mean that one exact file. `*.md | *.txt` searches
your Markdown and text files together, `* !*.bak` searches everything except
backups, and `*.md !drafts/*` skips the Markdown files in a `drafts` folder
(a pattern with a slash is matched against the path inside the starting
folder). Capitals do not matter. A pattern without `|`, `&`, `!` or quotes, such
as `*.md`, works exactly as before. These rules apply only to the file pattern:
the **Search text** still follows the Match mode you chose.

**An example.** You want every note in your `Clients` folder that mentions
Rosa Diaz. Press `Ctrl+Alt+Shift+F`, check that the starting folder is
`Clients`, type `*.md` as the file pattern and `Rosa Diaz` as the search text,
and press Enter. QUILL searches in the background, then opens the results in a
new tab and tells you, for example, "Search complete: 7 match(es) in 3
file(s)". Arrow through the tab to hear each file and line. If she has
changed her name, press `Ctrl+Shift+R` instead, fill in the replacement, keep
Preview before replacing checked, read the preview tab, and answer Yes.

Search in Files reads files only; Replace Across Files changes files on disk
that are not open in QUILL, so keep the preview on until you are sure of your
search text.

The rest of the search commands are on **Edit > Search Tools**:

- **Count Regular Expression Matches...** and **Extract Regular Expression
  Matches...** tell you how many times a regular expression matches, or pull
  every match out for you.
- **Lines in First Block Only** and **Lines Common to Both Blocks** compare two
  marked blocks of lines and keep the lines that are only in the first, or the
  lines both share.
- **Multi Replace...** runs up to four find-and-replace pairs in one pass.
  For a list you will want again, use a replace job, below.
- **Count Occurrences...** (`Ctrl+Alt+Shift+F3`) tells you how many times a
  piece of text appears in the document.

### Saved replace jobs

Some clean-ups are the same every time: the same six replacements on every
exported transcript, the same curly quotes straightened in every pasted email.
A replace job is a list like that, saved under a name, so you set it up once
and run it with a couple of keystrokes after that.

**Edit > Search Tools > Run Replace Job...** lists your saved jobs. Arrow to
one and press Enter. Every step runs in order, each on the result of the one
before, and QUILL tells you what happened: "Tidy spaces: 14 replacements", or
"Tidy spaces: 3 replacements in the selection. Step 1 found nothing". If you
selected some text first, the job runs on the selection only; otherwise it runs
on the whole document. Either way it is one change, so one `Ctrl+Z` takes the
whole job back. If a step has a pattern that cannot be used, nothing changes
at all, and you hear which step and why.

**Edit > Search Tools > Manage Replace Jobs...** is where you make them. The
window lists your jobs, with buttons to make a **New** one, **Edit** the steps
of the one you are on, **Rename** it and **Delete** it (QUILL asks first).
Editing a job shows its name and its steps in order, with **Add Step**,
**Edit Step**, **Remove Step**, **Move Up** and **Move Down**. Each step has
four things:

- **Find what**, the text to look for.
- **Replace with**, what it becomes. Leave it empty to delete what was found.
- **Regular expression**, to treat Find what as a pattern. With it checked,
  `^` and `$` mean the start and end of a line, and `\1` in Replace with puts
  back the first group. Without it, both fields are taken exactly as typed.
- **Match case**, to find only the same capital letters.

QUILL starts you off with three jobs you can keep, change or delete: **Tidy
spaces** (tabs to spaces, runs of spaces to one, no spaces at line ends),
**Straighten quote marks** (curly quotes to straight ones) and **Close up blank
lines** (three or more line breaks to one blank line). Your jobs are saved in
QUILL's own data folder, in `replace_jobs.json`. QUILL Lite has the same two
commands, on its Edit menu under Replace Jobs, and keeps its own list.

Neither command has a key: there was none free in both editors, and both ask
you a question straight away. You can give them one in the Keymap Editor.

### Find and replace in all your open documents

Sometimes the thing you are looking for is in one of a dozen documents you have
open, or you need to change a name in all of them. **Find in Open Documents...**
(**Ctrl+Shift+F10**, on **Edit**) searches every document QUILL has open,
not just the one in front of you.

It searches the text exactly as it is in each tab, so it finds:

- changes you have not saved yet,
- new documents you have never saved,
- formatted documents, such as Word and RTF files, searched as you see them.

Anything that is not open is left alone, and it never writes to a file on disk.
If you want to search files that are saved in a folder instead, that is
**Edit > Search in Files...** (`Ctrl+Alt+Shift+F`), described just above.

The window has the same choices as Find and Replace:

- **Find what** and **Replace with**.
- **Search mode**: Normal, Extended or Regular expression, just as in Find.
- **Match case**, **Whole word only**, and **Wrap around**, which is checked
  when it opens. With it checked, the search goes on from the first document
  after the last one, and comes back to where you started.

Its buttons:

- **Find Next** (**Enter**) and **Find Previous** go to the next or previous
  match. When one document has no more, they move on to the next document and
  bring it to the front, and you hear its name and the line: "Chapter 3.txt,
  line 12: She opened the door." While you stay in one document you only hear
  the line, the way Find works. If the search goes past the last document and
  starts again from the first, you hear "Back to the start" first.
- **Find All** lists every match in every open document, in order, each with
  the document's name, the line number and the line. Arrow through it and press
  **Enter** to go straight to that match. It is the quickest way to check what
  Replace All is about to change.
- **Replace All** does nothing until you have heard what it found, for example:
  "312 matches in 87 of 104 open documents. Replace them all?" Press **Yes** to
  go ahead.
  - Each document is changed on its own, so **Ctrl+Z** in any one window takes
    back just that document's replacements. In a formatted document each
    replacement is its own undo step, which keeps the formatting around it
    exactly as it was.
  - Nothing is saved for you. Every changed document is marked as changed, and
    you save them when you are ready, one at a time or with **Save All**.
  - Documents that cannot be changed, such as a read-only file or a report
    QUILL wrote for you, are still searched, but Replace All leaves them alone
    and tells you how many it skipped.
- **Close** (**Escape**) puts the window away.

After you close it, **F3** and **Shift+F3** keep searching across all your open
documents, so you can work through them one match at a time without opening the
window again. As soon as you start an ordinary Find (**Ctrl+F**) or Replace
(**Ctrl+H**), F3 goes back to searching just the document you are in.

QUILL and QUILL Lite share this window and work the same way, on the same key.

## Navigation

The **Navigate** menu is built for moving through large, dense material
without looking at it. Here are the commands in the order you are likely to
want them.

### Go To (Ctrl+G)

**Go To...** (`Ctrl+G`) is one window for four kinds of place: a **line**
number, a **page**, a **bookmark** or a **heading**. A PDF with an outline adds
a fifth, **Outline**.

1. Press `Ctrl+G`.
2. Choose the kind of place from the radio buttons at the top.
3. Type a number, or pick from the list, and press Enter.

The number field and the list follow your choice. The one that does not apply
is dimmed but stays where it is, so the window never changes shape under you.
Pages are exact in a PDF and marked `~4 (estimated)` everywhere else.

QUILL Lite opens the same window on the same key. It offers the Page row only
for a PDF, because only a PDF has real pages there. The old **Go To Line** and
**Go To Page** commands both land here now, so a key you gave them still works.

**Go to Percent...** moves you a part of the way through the document, for
example halfway.

### Going back after a jump

Every jump leaves a trail. **Back Location** takes you back to where you were
before, and **Forward Location** takes you forward again.

- **Back Location**: `Alt+Left` on Windows, `Cmd+[` on macOS.
- **Forward Location**: `Alt+Right` on Windows, `Cmd+]` on macOS.

### Searching a list with more than one word

Go to Anything is one search box for the headings in your document and every
command. It has no menu row of its own: press `Ctrl+Alt+Shift+A`, or type "go
to anything" in the Command Palette. Start your search with `#` to
see headings only, or `>` to see commands only. Type part of a heading and the
list narrows as you type; arrow to the one you want and press Enter to go
there. QUILL says how many results there are and which is on top, for example
"3 result(s). Top: [heading] Chapter two".

That box, and every other list in QUILL that you narrow by typing, understands
a few characters that let one search say more:

- **Words** match anywhere in a row, and capitals do not matter, just as
  before.
- **`&`** needs both words: `#budget & 2026` finds only headings with both.
  Two words side by side mean the same thing, so a search with an operator in
  it reads `budget 2026 !draft` as "budget and 2026 and not draft".
- **`|`** takes either: `#introduction | summary` lists both kinds of heading
  at once.
- **`!`** leaves a word out: `#chapter !draft` finds every chapter except the
  drafts.
- **`*`** stands for any run of letters inside a word, and **`?`** for exactly
  one: `#chap*` finds Chapter and Chapters, and `#r?ad` finds read and road.
  Neither reaches past a space.
- **Double quotes** match exact text, spaces included, with nothing inside
  taken as an operator: `#"to do"` finds "To do this week" but not "Do this
  today too".

`!` is read first, then `&`, then `|`, so `#draft | notes !old` means "draft,
or notes that are not old". A search with none of these characters works
exactly as it always has, so nothing you already type changes. You never get
an error for a half-finished search: `#notes |` is simply read as `#notes`
until you type the next word.

The same rules work in **Insert Snippet**, **Insert HTML Tag**, **Insert
Markdown Tag**, both lists of **Move Section To** (`Ctrl+Alt+Shift+F5`), the
abbreviation manager and the Copy Tray search. In Insert HTML Tag, for
example, `h? !h1` lists every heading tag except the top one. The **File
pattern** of Search in Files takes them too, described in "Searching a whole
folder of files" above. Press `F1` in any of those search boxes to hear a short
reminder of the rules. The Command Palette (`Ctrl+Shift+P`) keeps its own
looser search and its `:`, `?` and `~` prefixes, and so do those prefixes in
Go to Anything.

### Moving by heading and structure

Headings are the table of contents of a document, and moving by them is the
fastest way around a long one.

- **Next Heading** (`Ctrl+Alt+H`) and **Previous Heading**
  (`Ctrl+Alt+Shift+H`) move between headings only: the `#`, `##` and `###`
  lines in Markdown, and real headings elsewhere.
- **Next Structure** (`Alt+Down`) and **Previous Structure** (`Alt+Up`) move
  between every structural element: headings, and also list items, code
  blocks, tables and block quotes. This steps you through the full outline.
- **Next Region** (`F6`) and **Previous Region** (`Shift+F6`) cycle the larger
  parts of the window.

So a heading is one kind of structure. Next Structure is the wide sweep, and
Next Heading is the headings-only part of it.

A few more commands on the same menu:

- **Outline Navigator...** (`Ctrl+Shift+O`) lists the document's outline so
  you can jump to any part of it.
- **Heading Organizer...** (`Alt+Shift+O`) is for changing heading levels,
  moving whole sections, and checking that your headings are in a sensible
  order.
- **Next Block** and **Previous Block** move by block. In prose a block is a
  paragraph. In code it is whatever that language is built from, so you jump
  from one function to the next and hear its first line; see
  [Moving by block in code](#moving-by-block-in-code). They are also on
  **Navigate > Code**.
- **Match Bracket** (`Ctrl+Shift+\`) jumps to the bracket that pairs with the
  one at the cursor.
- **First Non-Blank** and **Last Non-Blank** move to the first or last
  character on the line that is not a space.

Not on the menu, but worth knowing: press `Ctrl+Alt+Shift+A` for **Go to
Anything**, a quick search box for jumping to anything by name. It has no menu
item; you can also find it in the Command Palette (`Ctrl+Shift+P`).

### Asking where you are

Three commands on the Navigate menu answer "where am I?" without moving you.
Each one starts with the QUILL key (`Ctrl+Shift+Grave`):

- **Speak Window Title** (QUILL key, then `F`) reads QUILL's title bar, which
  names the document and says whether it has unsaved changes.
- **Speak Full Path** (QUILL key, then `P`) reads where the document is saved,
  folder and all. A document that has never been saved says so.
- **Speak Status Summary** (QUILL key, then `Q`) gives the lot in one breath:
  the document's name, where it is, whether it is saved or modified, and its
  encoding.

What they say also goes on the status bar, so you can read it again in
braille.

### Asking the time, and what is open

Two more questions you can ask without leaving your writing. Both answer on
the first press, and say a little more if you press again quickly, within
half a second.

- **Say Time and Date** (`Alt+Shift+Space`, on the Navigate menu just after
  Speak Status Summary). Press it once and QUILL says the time, the way a clock
  reads it: "2:05 PM". Press it twice, quickly, and you hear the date in full:
  "Friday, November 6, 2026". It is quicker than hunting for the clock in the
  system tray, and it does not move you out of your document.
- **Say Windows Open** (`Ctrl+Shift+Space`, found on the Window menu just after Close Other
  Documents). Press it once to hear how many documents you have open: "3
  documents open". Press it twice, quickly, to hear their names, in the order
  of their tabs, with the one you are in marked: "3 documents: notes.txt
  (current), chapter 2.docx, letter.md". It is a fast way to check whether you
  left something open before you close QUILL, without walking the Window menu.

QUILL Lite has both, on the same keys. There they count and name its document
windows, since QUILL Lite has no tabs.

## Search, Replace, and Deep Navigation

QUILL knows what headings, lists and tables are, and it tells you about them
as you move. That is the deeper layer of navigation: line and page jumps,
block and heading movement, bracket matching, structural next and previous,
back and forward history, the outline and bookmarks, all working together.
Combined with marks and compare sessions, it makes a long review much less
fragile.

### Hearing that a paragraph is a heading

Apply Heading 2 to a paragraph, arrow away and arrow back, and your screen
reader reads the line but does not say it is a heading. That is not your
reader's fault. No Windows edit control has paragraph styles. The control can
tell JAWS or NVDA the font name, the point size and the weight, but it has no
way to say that a paragraph is a heading. Word
can do it only because it ships its own accessibility support for that.

So QUILL says it for you. Move onto a heading and you hear "Heading 2,
Installing": the level first, then the heading's own words, as one sentence.

- **The level comes first.** On a big jump, such as `Ctrl+Home`, a search hit
  or a bookmark, NVDA and JAWS drop anything that was waiting to be spoken. A
  level said first, as part of the sentence, is never lost that way. It is
  also the order a web browser uses.
- **Once, when you arrive.** Moving around inside a heading says nothing more.
  You hear it again when you leave and come back.
- **Every kind of heading.** Rich text, Markdown, HTML and a real `Heading 2`
  style in a Word document all sound the same.

If you would rather hear the words first, open **Settings > Accessibility and
Announcements** and change "Say a heading's level" (the
`heading_announce_position` setting) to `after`. Your reader then reads the
line and QUILL adds "Heading 2" behind it. It is a little quieter when you
read line by line, but on a big jump you may miss the level.

Applying a heading already tells you what happened, so you never hear it
twice. A document that opens on its own title does not greet you with
"Heading 1" over your reader's first reading of the line.

Sometimes you want to read a document simply as text, and one extra phrase
per heading is one too many. **View > Announce Headings** (`Ctrl+Alt+F3`)
turns the cue off and on without leaving the document, and it controls the
table cue too. QUILL tells you which way it went, "Headings announced on
arrival" or "Headings will not be announced", so an accidental press is never
a mystery. Your choice is remembered (the `announce_headings` setting), but
think of it as something you press per document.

Headings are only found where they really exist. A `#` at the start of a line
is a heading in Markdown and HTML, but in a shell script or a Python file it
is a comment, and QUILL says nothing.

### Hearing that you are in a list

Arrow into a list and QUILL says "Bulleted list, 5 items". Go a level deeper
and it says "Level 2, 3 items". Arrow out and it says "Out of list".

On a web page your screen reader tells you about lists itself. In an editor a
list is only characters, so a nested outline would otherwise sound like a run
of lines beginning with a dash, and you would have to count spaces to tell
level two from level three.

It works in Markdown and in HTML, for all three kinds of list:

| | Markdown | HTML |
|---|---|---|
| **Bulleted list** | `-`, `*`, `+` | `<ul>` |
| **Numbered list** | `1.`, `1)` | `<ol>` |
| **Definition list** | a line, then `: the definition` under it | `<dl>` |

In a definition list you also hear "Term" and "Definition" as you move
between the two, so you can tell if you have written one inside out.

Items are counted at your own level, inside your own list. A three-item list
whose second item has four sub-items is "3 items" at level one and "4 items"
at level two, never "7". Two sub-lists under two different bullets are two
lists.

QUILL stays quiet:

- **As you move down a list.** Your reader is already speaking each item.
- **On `- - -` or `***`.** Those are horizontal rules.
- **Inside a fenced code block.** A `- ` in a code sample is part of the
  sample.
- **In a plain document.** A letter is full of hyphens.
- **In rich text.** There the bullets belong to the control, and a `-` you
  type is a hyphen.

To turn the list cue off, use **View > Announce Lists** (`Ctrl+Alt+F5`). It is
a separate switch from the heading one, because when you are reorganising an
outline you want the levels, and when you are proofreading the same file you
may not. QUILL tells you which way it went, "Lists will not be announced" or
"Lists announced as you enter them", and remembers your choice as the
`announce_lists` setting.

The key is `Ctrl+Alt+F5` rather than `Ctrl+Alt+F4` on purpose: miss the
Control key on that one and you have pressed `Alt+F4`, which closes the
window.

### Moving through a table cell by cell

Arrowing along a table line tells you the characters but not the shape. QUILL
gives tables their own keys, and every move tells you where you are before
it tells you what is there.

- `Ctrl+Alt+Right` and `Ctrl+Alt+Left` move one cell along the row.
- `Ctrl+Alt+Down` and `Ctrl+Alt+Up` move one cell down or up the column.
- `Alt+Home` and `Alt+End` jump to the first or last cell of the row.
- `Ctrl+Alt+Home` and `Ctrl+Alt+End` jump to the first or last cell of the
  whole table.

Each move says what changed and then the contents: along a row, the column
("Column 3: Portland"); down a column, the row ("Row 4: Portland"); a jump to
another row and column, both. The table's size is said once, when you arrive.
An empty cell is called "blank". When there is nowhere to
go, QUILL says so and stays put: "No more cells" at the end of a row, "No more
rows" at the end of a column, and "No more cells, end of table" (or "No more
rows, end of table") on the very last cell. That way you know whether the row
stopped or the whole table did.

**The arrow keys read a table cell by cell.** Inside a table, **Up** and
**Down** go to the cell above and below in the same column and say it, "Row
3: Ann", instead of the screen reader reading the whole row as one line.
**Right** at the end of a cell's text goes to the next cell, and **Left** at
its start to the end of the cell before, "Column 2, Role: Lead"; inside a
cell's text they move letter by letter as always. **Down** from the line above
a table lands in its first cell and says its shape once, "Table, 3 rows, 2
columns. Name"; **Up** past the first row or **Down** past the last leaves
the table, and you hear "Out of table". Shift with the arrows still selects.
This works the same with JAWS, NVDA and Narrator, in rich text and in `|`
tables, with nothing to install. JAWS keeps **Ctrl+Alt** with the arrows for
its own table commands, so with JAWS use the arrows, **Tab** and the
**Navigate > Table** menu.

Outside a table the table keys do no harm; QUILL just says "Not in a table".

When a table has a header row (a `| --- |` row under its first row), moving
into a new column also says the column's header: "Column 3, City: Portland". Moving up or down the same column does not repeat it.

All of these are also on **Navigate > Table**, the same submenu as in QUILL
Lite.

This works on Markdown tables you type yourself and on tables QUILL brings in
from Word. A `.docx` table arrives as a real table laid out as Markdown rows,
so the same keys and announcements apply. So does a real table in an `.rtf`
file. A cell whose text contains a `|` character stays one cell and does not
throw the column count off.

### Editing a table

- **Tab** and **Shift+Tab** move to the next and previous cell, on to the next
  row at the end of one, as in Word. **Tab** in the very last cell adds a row
  and puts you in its first cell.
- **Navigate > Table** also has **Insert Row Below**, **Insert Column Right**,
  **Delete Row**, **Delete Column** and **Tidy Table**. Each is one Undo, and
  each says what it did: "Added row 3",
  "Deleted column 2, City. 4 columns left". Deleting a header row makes the next
  row the header. Tidy Table lines the columns up by padding every cell to its
  column's widest, so the table is easier to read on screen; the cells you hear
  are unchanged.
- **Insert > Insert Table...** (`Ctrl+Alt+T`) makes a new one.

**Real tables in rich text.** In a rich text document a table is a real table:
a grid on screen, with no `|` characters, which your screen reader, Word and
WordPad all see as a table. Insert Table makes one there, and a Word or RTF
document's tables open as them. Every key above works on a real table the
same way, and Tab in its last cell adds a row. Tidy Table says a real table is
already lined up. Adding or deleting a row or a column rebuilds a real table
with its text in place, but bold, italic or a font *inside* its cells does not
survive the rebuild, so format cell text once the table has its shape.

Saved as `.rtf` or as a Word document, a real table stays one, its first row
marked as the header row. A `|` table in a Markdown document you switch to
rich text becomes a real table, and switching back to Markdown or plain text
turns a real table into `|` rows.

## QUILL Quick Nav Mode

Quick Nav is like browse mode on a web page. Single letters move you around a
long document, and nothing you press changes the text. It only moves the
cursor.

### Turning Quick Nav on

There are two ways in:

- **Locked Quick Nav, the usual way.** Press `Ctrl+Shift+Grave` twice in a
  row. The first press starts the QUILL key; the second locks Quick Nav on
  until you press `Esc`. QUILL says "QUILL browse mode locked. It stays active
  until you press Escape."
- **For one move.** Press `Ctrl+Shift+Grave` then `N`. Quick Nav is on for the
  next move. If the `browse_mode_sticky` setting is on, it stays locked until
  `Esc`; otherwise it ends when the QUILL key times out.

### Quick Nav keys

Once Quick Nav is on, the keys are the same either way:

- `H` moves to the next heading, and `Shift+H` to the previous one.
- `1` through `6` move to the next heading at that level, and `Shift+1`
  through `Shift+6` to the previous one.
- `A` and `Shift+A` move by link.
- `L` and `Shift+L` move by list.
- `I` and `Shift+I` move by list item.
- `T` and `Shift+T` move by table.
- `Q` and `Shift+Q` move by block quote.
- `B` and `Shift+B` move by bookmark.
- `'` and `Shift+'` move by code block.
- `N` and `Shift+N` move by inline note.
- `M` and `Shift+M` move by misspelled word.
- `F` and `Shift+F` move by page, in a document with page breaks.
- `P` and `Shift+P` move by paragraph.
- `S` and `Shift+S` move by sentence.
- `Tab` and `Shift+Tab` move by block.
- `C` opens the table of contents (the Outline Navigator).
- `.` (period) repeats your last move.
- `]` jumps to the line after the current list or table, and `[` to the line
  above it.
- `Esc` leaves Quick Nav.

The key table at the top of this guide and the QUILL key cheat sheet are the
up-to-date reference.

A few things to know:

- If there is nothing of that kind to move to, QUILL tells you.
- Find and replace commands take you back to normal editing on their own.
- After each move QUILL tells you where you landed. **QUILL browse move
  detail**, in **Settings > Navigation and QUILL Key**, sets how much it says:
  *Line and column* (the default), *Line only* or *Say nothing*.
- **Preload QUILL browse cache in background**, on the same page, is on by
  default. If you turn it off, QUILL builds the cache the first time you use
  Quick Nav.

### Moving by misspelling and by page

**`M` and `Shift+M`** move to the next and previous misspelled word. QUILL
selects the word and tells you what it is and where: "Misspelled: recieve,
line 12". It uses the same spelling check as the Misspellings list in the
Quick Nav panel, with your own dictionaries, so the key and the panel always
agree. With the word selected you can type the right spelling straight over
it, or press `Esc` to leave Quick Nav and use the spelling commands. At the
last misspelling, `M` goes round to the first (unless you turned off wrapping
in Settings); with none at all you hear "No misspelled words in this document."

**`F` and `Shift+F`** move to the next and previous page. Pages here are the
page breaks in the text itself: a PDF opened in QUILL has one between every
page, and so does a braille file or a text file with page breaks. (F is for
form feed, the character that marks a page break; `P` was already Paragraph.)
QUILL says "Page 5 of 12". `Shift+F` from the middle of a page goes to the top
of that page first, and from the top of a page to the page before. In a
document with no page breaks you hear "This document has no page breaks."

QUILL also tells you the page **once** when the cursor crosses a page break by
any other means: an arrow key, `Page Down`, a search or a jump. Arrow down past
the end of page 4 and you hear "Page 5 of 12"; keep arrowing through page 5
and you hear nothing more about pages until you reach page 6. Moving with `F`
does not make QUILL say the page twice. A document with no page breaks never
mentions pages at all.

For example, open a 12-page PDF and press `Ctrl+Shift+Grave` twice to lock
Quick Nav. Press `F` four times to reach page 5 and read it with the arrow
keys. Press `M` to jump to the first misspelled word after the cursor, fix it,
and press `Esc` to leave Quick Nav.

QUILL Lite has no Quick Nav, so it has neither key; its status bar shows the
same "Page 5 of 12".

### How Quick Nav finds things

QUILL builds a list of the places in the document once, and reuses it until
the text or the kind of document changes. That keeps Quick Nav quick on long
Markdown and HTML files.

- Headings come from Markdown and HTML headings.
- List items come from Markdown list markers and HTML `<li>` tags.
- Paragraphs come from blank lines in text and Markdown, and from block tags
  in HTML.
- Sentences come from sentence-ending punctuation.
- Tables come from Markdown tables and HTML `<table>` tags.
- Block quotes come from Markdown `>` lines and HTML `<blockquote>` tags.
- Code blocks come from Markdown fences and HTML `<pre>` or `<code>` tags.
- Bookmarks come from your bookmarks.
- The list is rebuilt after you edit, replace the whole document, or switch
  tabs.

### QUILL key prefix actions

Press the QUILL key (`Ctrl+Shift+Grave`) once and it waits briefly for a
second key:

- `N` turns on Quick Nav, as described above. Pressing the QUILL key a second
  time instead locks it on whatever the setting says.
- `M` pastes web content as Markdown. QUILL reads the rich HTML on the
  clipboard (the `HTML Format` copied from web pages and word processors),
  turns headings, lists, links, bold and italic, code and block quotes into
  Markdown, and inserts it at the cursor. If there is no rich HTML, the plain
  text on the clipboard is treated as HTML. A read-only document is never
  changed.
- `A` opens selection actions when text is selected.
- `F` speaks the window title, `P` speaks the full path of the current file,
  and `Q` speaks a short status summary. These are handy when several
  documents are open and you want to check where you are.
- `?` shows the QUILL key cheat sheet, and `Esc` cancels.

Quick Nav (Landmarks) has a key of its own, `Ctrl+Shift+Z`, rather than a QUILL
key letter. It lists everything in the document you can move to (headings,
links, lists, tables, block quotes, bookmarks, code blocks) with a filter that
shows how many of each there are. It also lists the document's misspellings
and, while a search is active, the search hits, so you can jump to a misspelled
word or a match from the same place.

### Quick Nav and QUILL key settings

The **Navigation and QUILL Key** page in Settings holds the rest of the
choices for Quick Nav and the QUILL key:

- **Wrap QUILL browse navigation** carries on from the other end of the
  document when there is nothing more in the direction you are moving. On to
  begin with.
- **QUILL browse feedback** is how each move is signalled: **Speech only**
  (the default), **Sound only**, **Speech and sound** or **Silent**.
- **Sticky browse mode** keeps Quick Nav on after a move instead of going back
  to editing.
- **QUILL key prefix timeout (seconds)** is how long the QUILL key waits for
  its second key. The default is 2.5 seconds, and 0 means it waits until you
  press something.
- **Browse mode follow-on timeout** is how long Quick Nav stays on between
  moves after you start it with `N`: **Instant**, **Fast** (one and a half
  seconds), **Normal** (four seconds), **Slow** (eight seconds), **Custom...**
  or **Unlimited**, which is the default. With Custom, type your own time in
  milliseconds in the box that follows it.
- **Custom sound for browse mode entry (WAV file)**, **Custom sound for browse
  mode exit (WAV file)**, **Custom sound for browse navigation (WAV file)** and
  **Custom sound for browse not-found (WAV file)** replace the four Quick Nav
  beeps with sounds of your own. Each has a **Choose WAV file...** button and
  a **Preview** button. Leave one blank to keep the beep.
- **Include headings in Quick Nav**, **Include links in Quick Nav** and
  **Include lists in Quick Nav** decide what the Quick Nav list
  (`Ctrl+Shift+Z`) offers. All three are on to begin with.
- **Quick Nav debounce (milliseconds)** is how long that list waits after you
  stop typing in its filter before it searches. The default is 250.
- **Quick Nav minimum characters** is how many letters you type before the
  filter starts matching, from 1 to 5. The default is 1.

> **QUILLBee's tip:** Lost in a long document? Press `Ctrl+Shift+Grave` twice,
> then `H` to hop from heading to heading. `Esc` puts you back to typing.

## Bookmarks and marks

### Bookmarks

A bookmark is a place you want to come back to, even days later. The
commands live together on **Navigate > Bookmarks**:

- **Set Bookmark** (`Ctrl+Shift+B`) drops a bookmark in the next free
  numbered slot.
- **Next Bookmark** (`F2`) and **Previous Bookmark** (`Shift+F2`)
- **Clear All Bookmarks** (`Ctrl+Alt+B`)
- **Set Bookmark 1** to **Set Bookmark 9** (`Ctrl+Shift+1` to
  `Ctrl+Shift+9`), described under Numbered bookmarks below
- **Set Named Bookmark...**, which asks for a name
- **Go To Named Bookmark...**
- **List Named Bookmarks...** (`Alt+Shift+G`)
- **Set Temporary Bookmark** (`Ctrl+Alt+J`)
- **Go to Temporary Bookmark** (`Ctrl+Shift+J`)

Bookmarks belong to each document and are kept between sessions. When you
reopen a file, its bookmarks are still there. QUILL also remembers your last
cursor position in each saved document and puts you back there when you
reopen it. A new document that has never been saved keeps its bookmarks only
until you close it; save it, and they are kept.

Bookmarks also stay on the right words as you edit. Each one remembers the
text around it, so it follows that text even after you add or delete
paragraphs above it. If the bookmarked text itself is deleted, the bookmark
goes back to the position it remembered. This works for named and numbered
bookmarks alike, and you do not have to do anything.

### Temporary bookmark

Sometimes you just want to say "right here" and come straight back, with no
name and no dialog. That is the temporary bookmark. Both commands are on
**Navigate > Bookmarks**, just under **List Named Bookmarks...**, and in the
command palette:

- **Set Temporary Bookmark** (`Ctrl+Alt+J`) sets it at the cursor.
- **Go to Temporary Bookmark** (`Ctrl+Shift+J`) jumps back to it.

Set it, move away, jump back. Setting a new one quietly replaces the old one.
It is not kept between sessions: it is scratch paper for the work in front of
you. Use a named bookmark for anything you want to find next week.

If you used the 0.9.0 betas, the temporary bookmark was on `Ctrl+Shift+K` and
`Alt+Shift+K`. Those keys now belong to Lower Case and Previous Inline Note.

### Numbered bookmarks

Numbered bookmarks give you fixed slots you set with one keystroke, no menu
and nothing to type:

- `Ctrl+Shift+1` through `Ctrl+Shift+9` set the bookmark for that slot at the
  cursor.
- `Ctrl+Shift+B` drops a bookmark in the next free slot.
- `Ctrl+Alt+B` clears them all.

To get back to one, use `F2` and `Shift+F2`, the bookmark list
(`Alt+Shift+G`), or **Go To...** (`Ctrl+G`) with Bookmark chosen. They are
stored like named bookmarks, under names such as "Quick 3", so they are kept
with the document. Going to a slot you have not set tells you so plainly.

### Highlighted passages

Somebody has gone through a contract, a set of meeting notes or a draft with
Word's highlighter: the yellow bits are the ones you must read. A sighted
reader sees them at a glance. QUILL lets you go straight to them by ear, in the
same way bookmarks take you to places you marked yourself. The three commands
are on **Navigate > Highlighted Passages**:

- **Next Highlighted Passage** (`Alt+PageDown`) moves the cursor to the start
  of the next highlighted passage and says its colour, where it is in the count
  and its words, for example "Yellow highlight, 2 of 5: budget is final". After
  the last passage it goes round to the first.
- **Previous Highlighted Passage** (`Alt+PageUp`) does the same backwards.
- **List Highlighted Passages...** (`Ctrl+F2`) shows every passage in one list,
  in document order. Each row starts with the passage's words, so typing a
  letter finds a row, then gives the colour and the paragraph it sits in:
  "budget is final, yellow highlight, in: The budget is final unless the board
  objects." The list opens on the passage you are in, or the next one after
  the cursor. Enter (or **Go To**) closes the list and puts the cursor on the
  passage; Escape closes it and leaves the cursor where it was.

`Alt+Left` (Back) returns you to where you were before a jump, as it does
after any other jump.

**Where the highlights come from.** QUILL reads them fresh every time you
press one of these keys, so a highlight you have just added with **Format >
Highlight**, or just taken off with **Format > Clear Formatting**
(`Ctrl+Shift+N`), is already counted, and typing above a passage never sends
you to the wrong place.

- A Word document you edit as Rich Text, and any RTF document: the highlights
  in the document itself.
- A Markdown document: the hidden highlight codes that **Format > Highlight**
  writes, such as `[budget is final]{highlight="yellow"}`.
- A Word document you chose to open for reading and plain editing: the
  highlights in the `.docx` file on disk, placed on the text by their words
  and the paragraph they are in. If you have since retyped a passage's words,
  that passage is left out rather than guessed at.

**Describe Formatting at Cursor** (`Ctrl+Shift+D`) now also names the
highlight in a rich document:
"Calibri, 11 point, yellow highlight". Before this it said nothing about
highlighting there.

It names the **text colour** too, just before the highlight: red text on a
yellow highlight reads "Calibri, 11 point, red, yellow highlight". A colour you
chose from **Format > Text Color** comes back under the name you chose it by,
so green is "green" and orange is "orange". Any other colour, such as one that
came in with a Word document, is named after the nearest colour in the list
below, so you hear a word rather than a number. Text nobody has coloured,
plain black, and the light text a dark theme paints on the page say nothing
about colour at all, which keeps the description short for ordinary body text.
QUILL Lite gives the same answer, from the same code, on the same key.

**Colours.** QUILL knows all fifteen of Word's highlight colours by name:
yellow, green, turquoise, pink, blue, red and gray, and the darker dark blue,
teal, dark green, violet, dark red, dark yellow, dark gray and black. Saving a
rich Word document now keeps each passage's colour. Before 2026-10-16 a green
or pink highlight came back yellow after a save from rich mode, Pink and
Turquoise on the Highlight menu did nothing in a rich document, and the darker
colours were dropped when the document was opened.

**Limits.** Highlights in headers, footers, footnotes, comments and text boxes
are not listed, because QUILL does not show that text in the editor. A
highlight that comes only from a Word character style, rather than from the
highlighter, is not counted. Shading (a paragraph's background colour) is not
a highlight and is not listed.

### Marks, bookmarks and selecting a block

These three all "mark a spot", so they are easy to mix up. Here is what each
one does.

**Bookmarks are named places that are saved.** They travel with the file, as
described above. Use **Set Named Bookmark...**, **Go To Named Bookmark...** and
**List Named Bookmarks...** when you want to name a place and come back to it
days later.

**The mark ring is a short stack of temporary jump points.** It lasts only
for the current session and is never saved.

- **Set Temporary Mark** (`Ctrl+Shift+M`) drops a point at the cursor. The
  status bar says "Mark ring point set at line ..., column ... (temporary
  jump)".
- **Jump to Previous Mark** (`Ctrl+M`) jumps back to the most recent mark and
  removes it from the ring.
- **Swap Cursor and Mark** (`Ctrl+Alt+X`) moves the cursor to the mark.
- **List Recent Marks** (`Alt+M`) shows the marks in the ring.

These commands only move the cursor. They do not select text and they do not
copy anything. In some other editors you drop a mark, move away, and cut or
copy everything in between. QUILL's mark is not that. It is a breadcrumb you
can jump back to.

**To copy or cut from one point to another, select the text.** Put the cursor
at the start, then either hold Shift while you move to the end (arrows,
`Ctrl` with the arrows, the Page keys, Home and End) or use one of the
selection commands below. Then press `Ctrl+C` to copy or `Ctrl+X` to cut.
There is no separate "copy from the mark to the cursor" command; the
selection is what gets copied.

**Selecting a block, a line or a paragraph.** A block here means the indented
block at the cursor: a run of lines at the same indent, like the inside of a
list item or a code block. The selection commands are on **Edit > Selection**:

- **Select Line** (`Ctrl+Shift+E`) selects the current line.
- **Select Paragraph** (`Ctrl+Shift+H`) selects the paragraph around the
  cursor.
- **Select Block** (`Ctrl+Alt+Shift+B`) selects the indented block at the
  cursor.
- **Select to Start/End of Line** and **Select to Start/End of Document**.
- **Expand Selection** (`Ctrl+Shift+X`) grows the selection one step at a
  time: word, line, paragraph, block, document, telling you the new size each
  time.

Each one tells you what it selected and how many words, so you know exactly
what you have before you copy or delete it.

## Favorite folders

Favorite folders are a short list of folders you want to reach quickly. They
are different from the recent folders Windows keeps. Recent folders track
what you opened lately; favorites track what you actually want to hand. A
folder you use all the time but have not touched in months still belongs here.

- **Add Current Folder to Favorites** (`Ctrl+Shift+Grave` then `Shift+F`)
  adds the current document's folder. Save the document first if it is new.
- **Remove Favorite Folder...** (`Ctrl+Shift+Grave` then `Shift+X`) lets you
  choose a favorite to take off the list.
- **Open From Favorite Folder...** (`Ctrl+Shift+Grave` then `G`) opens Quick
  Open, described next.

All three are on **File > Favorite Folders**.

### Open From Favorite Folder

**Open From Favorite Folder...** opens a small window with a text box already
focused, much like Quick Open in Visual Studio Code.

1. Start typing part of a file name. The list below narrows as you type,
   across every favorite folder at once, and capital letters do not matter.
2. Arrow to the file you want. Each entry tells you which favorite folder it
   came from.
3. Press Enter, or choose **OK**, to open it.

By default QUILL looks only at the files directly inside each favorite
folder, not in folders inside them, which keeps the list instant. Check
**Include subfolders** to search every subfolder too. That search stops at a
few thousand files, so even a very large folder cannot hang the window.

## Folding and inline notes

### Code folding

Folding lets you tuck away a heading section or a fenced code block
(` ``` `...` ``` `) so it is out of your way, without ever hiding it from you.

- **Toggle Fold** (`Ctrl+Shift+[`) folds or unfolds the smallest region around
  the cursor and tells you what happened: "Folded: 14 lines under 'Chapter
  Two'" or "Unfolded: 'Chapter Two'."
- **Next Fold** (`Alt+Shift+]`) and **Previous Fold** (`Alt+Shift+[`) jump
  between regions you can fold, folded or not, and tell you the region's
  name, whether it is folded, and how many lines it has.
- **List Folds** (`Ctrl+Shift+]`) opens a list of every region you can fold,
  with its state and line count. Pick one to jump to it, or fold and unfold it
  from there.

In most editors, folding hides lines and the arrow keys skip right over them,
so a screen reader user cannot tell whether text was folded or deleted. QUILL
never does that. Folding never changes the text, and arrowing by character,
word or line works exactly as before. Arrow through a folded region and you
will read every word of it. Folding only changes where the jump commands take
you.

### Inline notes

Inline notes are comments you attach to a line or a selection: a question, a
reminder, a note to yourself while you draft, or your thoughts on a plan
somebody sent you. They are on **Tools > Writing and Language**, and you can
change any of their keys in the Keymap Editor.

- **Add Inline Note...** (`Alt+Shift+I`) attaches a note to the selected text,
  or to the current line if nothing is selected. The **Note on** line at the
  top shows the start of that text, so you can check you are in the right
  place. Type the note and choose Save.
- **Next Inline Note** (`Alt+Shift+J`) and **Previous Inline Note**
  (`Alt+Shift+K`) move to the next or previous noted text, and QUILL reads the
  note.
- **Speak Inline Note** (`Alt+Shift+H`) reads the note at the cursor. Press it
  twice quickly to open the note so you can read, change or delete it.
- **Delete Inline Note...** (`Alt+Shift+Delete`) deletes the note at the
  cursor. QUILL reads you the note and asks first, and No is the default.
- **List Inline Notes...** (`Alt+Shift+Enter`) shows every note in the
  document in one list: the note, the line it is on, the text it is about, and
  whether it is private or in the file. Press `Enter` to go to a note,
  `Delete` to delete one and `F2` to edit one. The buttons also let you
  **Remove All** notes (QUILL asks first), **Copy All** of them as plain text,
  or **Export** them to a Markdown or JSON file.
- In Quick Nav, `N` and `Shift+N` move to the next and previous note too.

Each note remembers the exact text it was placed on, plus a little around it,
so it follows that text as you edit. If that text is deleted, the note is kept,
not lost: the list shows it last, marked "the text it was on is gone", so you
can read it and remove it. A new document keeps its notes until you close it;
save it and they are kept.

#### Hearing which lines have notes

As you arrow through a document, QUILL plays a soft two-tap sound when the
cursor arrives on a line that has an inline note, private or in the file. It
plays once as you arrive, and never while you move along that same line with
the left and right arrows, `Home`, `End` or `Ctrl+Left` and `Ctrl+Right`. Move
off the line and back, and you hear it again. A note on a selection that runs
over several lines counts as one place: you hear it as you enter, not on every
line of it.

For example, you have a note on the line "Back up the uploads folder." Arrow
down: on the line before, nothing; on that line, the tap; then press `Alt+Shift+H`
to hear the note itself.

To change it, open **Settings**, go to the **Editing** page and find **When the
caret reaches a line with an inline note** (the `inline_note_line_cue`
setting). The choices are **Play a sound** (the default), **Say "note"**, and
**Nothing**. A few things to know:

- With the sound chosen, a braille display also shows the word "note", because
  a sound does not reach somebody reading in braille without speech. With the
  word chosen, your screen reader's braille shows it already.
- If your sound pack has no sound for this, QUILL says "note" instead, so the
  setting never ends up silent by accident. You can change or switch off the
  sound itself in **Sound Scheme**, where it is listed as "Arrived on a line
  with an inline note".
- **Next Inline Note** and **Previous Inline Note** read you the note itself,
  so arriving with them plays no tap on top.

#### Private notes and notes in the file

Normally a note is private. It is kept in QUILL's own settings folder, the
document itself is never changed, and nobody else ever sees it. That works in
every kind of document.

In a Markdown or HTML document you can also write a note **into the file**.
Check **Write this note into the file** in the Add Inline Note window, and the
note goes into the document as a hidden comment on its own line, right after
the text it is about:

    Back up the uploads folder.
    <!-- quill-note: And the database dump. -->

The file is still a perfectly good Markdown or HTML file. Web pages, GitHub and
other programs hide the comment, but anyone who opens the file in a text
editor, and any AI assistant you hand the file to, can read your note. That
makes it the way to review a plan an AI assistant wrote: read it, leave your
notes in the file, and give the file back. Because a note in the file is part
of the text, `Ctrl+Z` takes back adding, changing or deleting one.

The check box remembers your last choice for each document. To start every
new note in the file, turn on **Write new inline notes into the file** (the
`inline_notes_in_file` setting) on the **Editing** page in Settings. It is off
unless you change it.

#### Notes on the command line

A script, or an AI assistant working in a terminal, can read and clear the
notes written into a file without opening QUILL:

- `quill --notes list plan.md` prints every note with its line and the text
  it is about. Add `--json` for a list a program can read.
- `quill --notes check plan.md` says how many notes are left.
- `quill --notes clear plan.md` removes them all and saves the file, keeping
  its encoding and line endings.

The exit code tells a script what happened: 0 means done (or, for `check`, no
notes left), 3 means `check` found notes still in the file, 1 means the file
could not be read or written, and 2 means the command was mistyped. Private
notes are never shown here; they stay yours.

## Working in code

### Code-aware editing

When you open a source file, QUILL loads a language profile based on the file
extension. It knows HTML, Markdown, CSS, Python, JavaScript, TypeScript, C,
C++, C#, Java, PHP, Go, Rust, Kotlin, Ruby, Perl, Shell, PowerShell, batch
files, LaTeX, XML, YAML, JSON, TOML, INI, CSV and SQL, and treats anything else
as plain text. The profile tells QUILL how the language is put
together, so moving and announcements make sense for code.

- **Next Token** and **Previous Token**, on the Navigate menu, move by code
  token instead of by word. You land on the next name, keyword, operator or
  value, which is much easier to follow by ear than moving by character or
  word.
- Token movement goes well with the optional indentation tones described
  under [Sound notifications and earcons](quill-guide-11-accessibility-speech-and-braille.html#sound-notifications-and-earcons),
  so you hear the structure as pitch while you move.

### Setting the document language

QUILL normally goes by the file extension, but you can set the language
yourself for the current document. That helps with an unsaved document, an
unusual extension, or code you pasted into a plain `.txt` file. You get the
whole of that language's editing support:

- **Bold** and **Italic** insert the right markup (`<strong>`/`<em>` for HTML,
  `**...**`/`*...*` for Markdown).
- The **heading, table, list, and tag** menu items become available for HTML
  and Markdown.
- **Toggle Line/Block Comment** uses the language's comment style (`#`, `//`,
  `<!-- -->`, `-- `).
- Heading and structure navigation, the outline, link insertion and live
  preview all follow the language you chose.

There are three ways to set it, and they all do the same thing:

- **Key:** `Ctrl+Alt+F6` opens the language picker. Type to find a language;
  the current one is already selected.
- **Menus:** **Navigate > Set Document Language...** opens the same picker.
  **Format > Document Language** is a checkable list where you can switch with
  one key press and hear which language is active.
- **Status bar:** the **Language** part shows the current language, with
  **(set)** after it when you chose it yourself. Press Enter on it to open the
  picker.

Choose **Auto-detect from file** to go back to following the file name.
Setting a language never renames the file. If you set HTML on a `.txt` file,
QUILL reminds you to use **Save As** to save it as `.html`. The choice applies
to the current tab and is forgotten when you close the file.

### Automatic language detection

QUILL can guess the language when you paste or type code into a plain `.txt`
or new document. This is off by default. Turn it on in **Settings > Editing >
Auto-detect document language**, which has four choices:

- **Off**: never guess. This is the default.
- **Hint in the status bar only**: the status bar quietly shows something like
  "Looks like HTML". Nothing changes and nothing is spoken.
- **Suggest and announce, you confirm**: QUILL tells you which language it
  thinks this is ("This looks like HTML") and you decide whether to set it.
- **Switch automatically**: QUILL sets the language and tells you.

QUILL waits a moment after you stop typing or pasting, then looks at the
first several thousand characters. It is careful: it only acts when it is
confident, never guesses on ordinary prose, and never overrides a real file
extension or a language you set yourself. It also learns a little from the
languages you use during a session. In every mode you either stay in control
or hear what changed. Braille files and pasted braille are not affected,
because braille has its own Braille Mode.

### Moving by block in code

**Next Block** and **Previous Block** are on the Navigate menu and on
**Navigate > Code**. They have no key of their own, because every chord near
them is already taken; in Quick Nav, `Tab` and `Shift+Tab` do the same thing,
and you can give them a key in the Keyboard Manager.

What a block is depends on the document's language:

- **Python:** each `def`, `async def` and `class`. A decorator counts as the
  start of the function it decorates.
- **C#, Java and Kotlin:** class, interface, struct, enum, record and namespace
  declarations, and methods (a line with a modifier such as `public` or
  `static`, a name and an opening parenthesis).
- **JavaScript and TypeScript:** functions, classes, functions assigned to a
  name (`const add = (a, b) => ...`), methods inside a class and, in
  TypeScript, interfaces, enums, namespaces and type aliases.
- **C and C++:** function definitions at the left margin, and class, struct,
  union, enum and namespace blocks.
- **Go, Rust, PHP, Ruby, Perl, Shell, PowerShell and SQL:** functions and the
  language's type or package declarations (`func` and `type`; `fn`, `struct`,
  `impl` and `mod`; `sub` and `package`; `CREATE`, `ALTER` and `DROP`).
- **INI and TOML:** each `[section]`, and TOML's `[[array of tables]]`.
- **Batch files** (`.bat` and `.cmd`): each `:label`. A line starting with `::`
  is a comment, not a label, and is skipped.
- **LaTeX:** `\part`, `\chapter`, `\section`, `\subsection`,
  `\subsubsection` and `\paragraph`, starred or not.
- **HTML:** headings, the landmark elements (`header`, `nav`, `main`, `aside`,
  `section`, `article`, `footer` and `form`), and any element with a landmark
  `role`.
- **Markdown, plain text and anything else:** paragraphs, as before.

When you land on a block in a language like these, QUILL says the line you
landed on, such as "def save_file(path):, line 42", so you know where you are
without reading further. If a file has none of these at all, a Python script
with no functions for instance, the commands fall back to moving by paragraph
rather than doing nothing. The language is the one QUILL picked from the file
extension, or the one you set with **Set Document Language**.

### Moving by indentation

In Python, YAML and any other indented text, the indentation is the structure.
Two commands follow it:

- **Next Indent Change** (`Alt+Shift+PageDown`) moves down to the next line
  whose indentation is different from the line you are on: the first line
  inside a block, or the first line after it.
- **Previous Indent Change** (`Alt+Shift+PageUp`) does the same going up,
  which is how you get back to the `if` or `def` a block belongs to.

Blank lines are skipped. The caret lands on the first character that is not a
space, and you hear how the line is indented, for example "8 spaces", "1 tab"
or "No indent", followed by the line and column. A tab counts as the
language's indent width, so a tab and four spaces in a Python file are the same
depth. At the top or bottom of the file you hear "No change of indent above" or
"No change of indent below". Both commands are on **Navigate > Code**.

### Checking a file for problems

**Check This File** looks through the whole document for mistakes in how it is
written, the kind that stop a program reading it: a missing comma in JSON, a
tag that is never closed, a Python line that will not compile. It is on
**Navigate > Code > Check This File...**, and its key is `Ctrl+Alt+/` (the
question-mark key: "what is wrong here?").

If nothing is wrong you hear "No problems found." Otherwise the **Problems**
list opens. Its first line says how many there are, such as "3 problems: 2
errors, 1 warning", and then each problem is one row, place first: "Line 12,
column 5, error: Expecting ',' delimiter (JSON)". Arrow to one and press Enter
to go straight to it, or press Escape to close the list where you are.

You do not need the list to work through problems:

- **Next Problem** (`Ctrl+Alt+.`) moves the caret to the next problem after it
  and says the problem, for example "Problem 2 of 3, line 12, column 5, error:
  Expecting ',' delimiter".
- **Previous Problem** (`Ctrl+Alt+,`) goes the other way.

Both go round from the last problem to the first, and the numbers tell you
when they have. If you have changed the document since the last check, they
check again first, so the line numbers are always right. A code editor would
use F8 for these, but in QUILL `F8` and `Shift+F8` are Word's extend-selection
keys, so the problem keys sit beside Compare's next and previous difference
keys instead. You can change all three in the Keyboard Manager.

#### The Problems pane

The Problems list closes when you pick a problem. If you'd rather keep the
problems in front of you while you fix them, turn on **View > Problems > Show Pane**
(Alt+V, P, S). It sits under the document, above the status bar, and stays
there until you turn it off again. QUILL remembers whether it's on.

- Turning it on checks the document straight away, and you hear the result,
  such as "Problems pane shown. 2 problems: 1 error, 1 warning."
- While it's on, **Check This File** fills the pane instead of opening the
  list, and says what it found. Your caret stays where it was.
- **F6** moves from the document to the pane, then on to the status bar, in
  the order they are on screen. Shift+F6 goes the other way.
- In the pane, each row starts with how serious the problem is, then where it
  is and what it is: "Error, line 12, column 5: Expecting ',' delimiter (JSON)".
  Press **Enter** to go to that problem in the document.
- **Escape** takes you back to the document without closing the pane.
- If you've changed the document since the check, Enter checks it again first
  and goes to the same problem where it is now. If your change fixed it, you
  hear "That problem is gone." and the new count.
- **Which files it lists is yours to choose, and quick to change.** In the
  pane's list, press **F** to switch between this file and all open files.
  On the menu it's **View > Problems > This File Only** (Alt+V, P, T) or
  **All Open Files** (Alt+V, P, A), which also shows the pane if it's
  hidden, and the pane's **Files** chooser does the same. These switch for
  now. Which one the pane starts with is a setting: **Problems pane lists
  all open files at first**, in Settings under Editing. With all open
  files, each row starts with the document's name,
  such as "notes.md: Warning, line 4, column 1: ...", and Enter on another
  document's problem brings that tab to the front with the caret on it. The
  other documents are checked with QUILL's own checkers only; the tools you
  have installed run for the one in front of you.
- **Shift+Tab** from the list reaches the choosers at the top. **Show**
  picks all problems, errors and warnings, or errors only. **Source** picks
  one checker, such as JSON or ruff. Changing either says the new count, for
  example "4 problems, 1 shown".
- The context key (or Shift+F10) on a row has **Go To** and **Copy Message**.
- While the pane is on, saving checks the file again. If you'd also like it
  checked when you stop typing for a moment, check **Check after a pause**,
  beside the choosers. It's off unless you turn it on, and QUILL remembers it.
  These checks are quiet: you hear only the new count, such as "2 problems",
  and only when it has changed.

The pane has no shortcut key of its own. The obvious one, Ctrl+Shift+M, is Set
Mark, and nothing near it was free in both QUILL and QUILL Lite. Once you've
turned it on it stays on, so you rarely need the menu. You can give it a key
in the Keyboard Manager; the commands are called Problems Pane, Problems:
This File Only and Problems: All Open Files.

#### What QUILL can check

Some languages are checked by QUILL itself, with nothing else installed:

| Language | What is checked |
| --- | --- |
| JSON | That it reads as JSON |
| JSON with comments | The same, allowing `//` and `/* */` comments and trailing commas (`.jsonc`, and VS Code's settings, tasks and `tsconfig.json` files) |
| XML | That it is well formed. Entity declarations are refused, not expanded |
| HTML | Tags closed in the wrong order or never closed, closing tags with nothing open, duplicate `id` values, and pictures without alt text |
| TOML | That it reads as TOML |
| YAML | That it reads as YAML |
| Python | Syntax errors, mistakes Python finds when compiling (such as `return` outside a function), and warnings such as an invalid escape sequence. The code is never run |
| INI and CFG | Settings before any section, sections or settings given twice, and lines that are neither |
| CSV | Rows with a different number of fields from the first row, and badly placed quotes |
| Markdown | Heading levels that skip, pictures without alt text, links with no text or no address, and relative links to files that are not there |

Other languages are checked with a tool you already have installed, if QUILL
can find it on your PATH. QUILL never downloads or installs one:

| Language | Tool QUILL uses |
| --- | --- |
| JavaScript | Node.js (`node --check`), and ESLint if you have it |
| TypeScript | The TypeScript compiler (`tsc --noEmit`), and ESLint if you have it |
| Python | Ruff, if you have it, as well as the built-in check; this adds names that are never defined and imports that are never used |
| PHP | `php -l` |
| Ruby | `ruby -c` |
| Perl | `perl -c` |
| Shell scripts | ShellCheck |
| C and C++ | GCC, or Clang if you do not have GCC (`-fsyntax-only`) |
| Go | `gofmt -e` |
| Rust | `rustc`, which writes nothing you keep |
| C# | `csc`, the C# compiler, for a single file. A whole project needs `dotnet build`, which QUILL does not run |
| XML | `xmllint`, as well as the built-in check |

When a language needs a tool and none is installed, you hear "No checker
installed for Ruby" (or whichever language it is). When QUILL has its own check
for a language, that check always runs, tool or not.

A few things are worth knowing about the tools:

- They run on your computer only. Nothing is sent anywhere.
- QUILL checks what is in the window, not what is on disk. If the document is
  unsaved or changed, QUILL checks a temporary copy with the same name, then
  deletes it.
- Each tool runs in the file's own folder, so it finds your project's settings
  the way it would from a command prompt.
- A tool gets 15 seconds. If it takes longer it is stopped, and you hear that it
  was. While a tool runs you hear "Checking this file", and QUILL stays usable.
- `perl -c` runs a script's `BEGIN` blocks and `use` statements, as it always
  does, and ESLint loads your project's ESLint configuration, which is itself
  JavaScript. Only check files you trust with those two.

### Abbreviation expansion

If you write HTML or CSS, three commands on the **Edit** menu turn short
Emmet-style abbreviations into full markup. You can type
`ul>li.item$*3>a[href]{Item $}` instead of a whole three-item list.

- **Expand Abbreviation** expands the selection, or, with nothing selected,
  the word just before the cursor. It is one undo step, so one Undo puts it
  all back.
- **Preview Abbreviation...** asks for an abbreviation (filled in from your
  selection, if you have one) and shows the result in a new tab without
  touching your document. It is a safe way to try something.
- **Explain Abbreviation...** gives you a plain, indented breakdown of what an
  abbreviation means (tag, id, classes, attributes and how many times it
  repeats) before you expand it. It is the quickest way to learn the grammar
  by ear.

The usual Emmet operators work: child (`>`), sibling (`+`), climb-up (`^`),
grouping (`(...)`), multiplication (`*N`) and numbering (`$`, with `$$` for
zero-padded numbers). So do ids (`#id`), classes (`.a.b`), attributes
(`[attr="value" bool-attr]`) and text (`{...}`). Common tags get sensible
attributes if you leave them out: `a` gets an empty `href`, and `img` gets
`src` and `alt`. Elements like `br` and `img` never get a closing tag.

Some ready-made snippets expand as they are:

- `!` gives a full HTML5 page.
- `!a11y` gives an HTML5 page with a skip link and `header`/`main`/`footer`
  landmarks in place.
- `skiplink` gives just the skip link.
- `form:a11y` gives a labeled form field inside a fieldset.
- `table:a11y` gives a table with a caption and properly scoped header cells.

When the document is a `.css` file, all three commands work with CSS
shorthand instead, such as `d:f` for `display: flex;`, `pos:a` for `position:
absolute;`, `m10-20` for `margin: 10px 20px;` and `mt-10` for `margin-top:
-10px;`.

If QUILL cannot make sense of an abbreviation, the status bar tells you what
it expected and where.

## Quill Eraser

Quill Eraser (**Tools > Writing & Language > Quill Eraser...**) tidies the
small mechanical slips in your text: extra spaces, spaces at the ends of
lines, a missing space after punctuation, too many blank lines, and sentences
that start with a small letter. It offers a fix for each one. It follows
fixed rules, so there is no AI and nothing goes over the network.

To check only part of the document, select it and use **Quill Eraser on
Selection...**. If nothing is selected, it offers to check the whole
document.

### What Quill Eraser checks

Each finding comes with a confidence level (High, Medium or Low) so you can
decide what to fix first.

| Rule | Confidence | What it catches |
|------|-----------|-----------------|
| Multiple spaces between words | High | Two or more spaces where one space belongs |
| Trailing spaces at end of line | High | Spaces or tabs at the end of a line |
| Space before punctuation | High | A space immediately before `,`, `.`, `!`, `?`, `;`, or `:` |
| Excessive blank lines | High | More consecutive blank lines than your configured maximum (default: 2) |
| Missing space after sentence punctuation | Medium | A sentence-ending `.`, `!`, or `?` directly followed by a letter |
| Missing space after comma, semicolon, or colon | Medium | A `,`, `;`, or `:` directly followed by a letter |
| Sentence starts with lowercase letter | Medium | A sentence or paragraph that begins with a lowercase character |

Quill Eraser leaves web addresses, email addresses, file paths, code,
decimal numbers and times alone. In a Markdown file it also skips fenced code
blocks, inline code, front matter and link addresses.

### Code files

If you run Quill Eraser on a code file (`.py`, `.js`, `.ts`, `.html` and so
on), it asks first. You can check only for spaces at the ends of lines, which
is safe in code, or skip the check. The prose rules are never used on code
files.

### The review dialog

When Quill Eraser finds something, it opens a review window that stays open
while you keep working in the editor.

- The **findings list** shows each issue in order: confidence, type and line
  number.
- Select a finding and the pane below tells you what was found, what the fix
  is, and what it means in plain English.
- **Apply Fix** makes the fix and moves on to the next issue.
- **Ignore** hides the finding for this session without changing anything.
- **Go to Issue** takes you to the exact place in the editor with the text
  selected, so you can decide for yourself.
- **Previous / Next** move through the list.
- **Rescan** checks again after you have made changes by hand.
- **Close** closes the window.

QUILL tells you the result of every action.

### Quill Eraser settings

Four settings at the end of the **Spelling** page in Settings (`Ctrl+,`) control
Quill Eraser. Each one's name starts with "Quill Eraser", so typing eraser in
**Find a setting** lists all four:

| Setting | Default | What it does |
|---------|---------|--------------|
| `hygiene_min_confidence` | `high` | Minimum confidence level to report. Set to `medium` or `low` to see more findings. |
| `hygiene_allow_double_space_after_period` | off | Suppresses the "multiple spaces" rule when exactly two spaces follow `.`, `!`, or `?` (two-space-after-period style). |
| `hygiene_max_blank_lines` | 2 | Maximum consecutive blank lines before a finding is raised. |
| `hygiene_rules_disabled` | (empty) | Comma-separated list of rule IDs to disable (e.g. `prose.lowercase_sentence_start,prose.missing_space_after_comma`). |

The rule IDs you can put in the disabled list are
`prose.multiple_spaces`, `prose.trailing_spaces`,
`prose.space_before_punctuation`, `prose.excessive_blank_lines`,
`prose.missing_space_after_sentence_punct`,
`prose.missing_space_after_comma` and `prose.lowercase_sentence_start`.

## What you learned, and where to go next

You can now find text in one document or many, jump by line, page, heading or
bookmark with `Ctrl+G`, and get back with `Alt+Left`. You know what QUILL says
about headings, lists and tables, how Quick Nav moves you with single letters,
and the difference between bookmarks, marks and a selection. Favorite folders,
folding, inline notes, the code tools and Quill Eraser are there when you want
them.

To practise with QUILL guiding you, open **Help > Tutorials...**
(`Ctrl+Alt+F1`) and try "Get around a long document", "Find, replace, and
search across files", "Select, mark, and move text", "Tables, by ear" and
"Quick Nav: single-letter movement". On the website,
[Own the keyboard](https://www.quillforall.org/tutorials/02-own-the-keyboard.html)
covers much of the same ground.

Next, Chapter 7, Spelling and words, shows you how to check spelling and find
the right word.

---

- Previous: [Chapter 5: Formatting, structure and markup](quill-guide-05-formatting-structure-and-markup.html)
- Next: [Chapter 7: Spelling and words](quill-guide-07-spelling-and-words.html)
- [Contents](../userguide.html)
