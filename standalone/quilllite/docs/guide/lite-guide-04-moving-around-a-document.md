# Chapter 4: Moving around a document

A long document is easy to get lost in when you cannot glance down a page.
This chapter gives you the keys that take you straight to what you want. You
will search for words and hear how many there are, look for characters you
cannot type, jump to a line, a bookmark or a heading, and leave bookmarks that
are still there tomorrow. And whenever you jump somewhere, there is a key that
takes you back.

## Finding things

These are the keys you will use most when you are looking for something:

| Key | What it does |
|---|---|
| **Ctrl+F** | Find |
| **F3** / **Shift+F3** | Find next / previous |
| **Ctrl+H** | Replace |
| **Ctrl+G** | Go To: a line, a page, a bookmark, a heading or a PDF's outline |
| **Ctrl+Alt+Shift+F8** | Find in Open Documents: every open window at once |
| **Ctrl+Alt+Shift+F** | Search in Files: a whole folder |
| **Ctrl+Shift+R** | Replace Across Files |

All seven are rows of the **Edit** menu itself, so if you forget a key, press
**Alt+E** and arrow down: after Replace you hear **Find in Open Documents...**,
**Search in Files...** and **Replace Across Files...**, each with its key. The
two that answer "how many" and "where in this document", **All Matches...** and
**Count Occurrences**, are one step further in, on **Edit > Matches**, and
your saved replace jobs are on **Edit > Replace Jobs**, below.

When a search reaches the end of the document, it goes back to the top and
keeps looking, and it tells you it has done so. That little message is worth
listening for. It is how you know a document has only one match, and not none.

### What is in the Find and Replace windows

The **Find** window (**Ctrl+F**) opens with your cursor in the box where you
type what to look for. If you had something selected, it is already there;
if not, your last search is. Tab past the box and you meet two checkboxes:

- **Match case**: when it is checked, *Cat* and *cat* count as different
  words.
- **Whole word only**: when it is checked, *cat* finds the word on its own
  and not the start of *catalogue*.

After those come the **Search mode** (more about that below) and the buttons.
**Find next** is the one **Enter** presses, and **Shift+Enter** in the box
finds the previous match, just like the **Find previous** button. **Close**,
or **Escape**, puts the window away, and **F3** still remembers what you were
looking for.

The **Replace** window (**Ctrl+H**) has the same box and checkboxes, plus a
**Replace with** box for what each match should become. Leave it empty to
delete the matches. Its buttons are:

- **Find next**, which moves to the next match without changing anything.
- **Replace**, which changes the match you are on and moves on to the next
  one, so you can decide one at a time.
- **Replace all**, which changes every match in the document at once and
  tells you how many it changed, for example "Replaced 12 occurrences".
- **Close**. Anything you have already replaced stays replaced, and
  **Ctrl+Z** takes it back if you change your mind.

Both windows stay open while you work, so you can go back to your document
and return to them.

**What you type in Replace with is what goes in.** A backslash is just a
backslash. Replace a folder name with `C:\new\reports` and that is exactly
what lands in every match, and `\1` goes in as the two characters you typed.
Only one thing reads the box differently: **Replace all** with the **Regular
expression** search mode. There, `\1` puts back the first part of the match
you wrapped in brackets and `\2` the second, so searching for `(\w+), (\w+)`
and replacing all with `\2 \1` turns "Bishop, Jeff" into "Jeff Bishop". If the
box names a part the search does not have, such as `\3` when there are only
two, nothing is changed and you hear "Nothing replaced", with the reason.

### Saved replace jobs

Some clean-ups are the same every time: the same six replacements on every
transcript you export, the same curly quotes straightened in every email you
paste in. A replace job is a list like that, saved under a name, so you set it
up once and run it in a couple of keystrokes from then on.

**Edit > Replace Jobs > Run Replace Job...** (**Alt+E**, **J**, **R**) lists
your jobs. Arrow to one and press **Enter**. Its steps run in order, each one
on the result of the one before, and you hear what happened: "Tidy spaces: 14
replacements", or "Tidy spaces: 3 replacements in the selection. Step 1 found
nothing". Select some text first and the job runs on just that; otherwise it
runs on the whole document. Either way, one **Ctrl+Z** takes the whole job
back. If one of the steps has a pattern that cannot work, nothing changes and
you hear which step and why.

**Edit > Replace Jobs > Manage Replace Jobs...** (**Alt+E**, **J**, **M**) is
where you make them. It lists your jobs, with **New**, **Edit**, **Rename**
and **Delete** buttons (Delete asks first). Editing a job shows its name and its
steps in order, with **Add Step**, **Edit Step**, **Remove Step**, **Move Up**
and **Move Down**. A step is the same four things the Replace window has:
**Find what**, **Replace with**, **Regular expression** and **Match case**.
With Regular expression checked, `\1` in Replace with puts back the first part
in brackets; without it, what you type is what goes in.

Three jobs are there to start with, and you can keep, change or delete them:
**Tidy spaces**, **Straighten quote marks** and **Close up blank lines**. QUILL
has the same two commands, under **Edit > Search Tools**, and keeps its own
list. Neither has a key: none was free in both editors, and both ask you
something straight away. The Keyboard Manager (**Ctrl+Alt+Shift+Space**) can
give them one.

### How many are there?

The Find window counts as you type. Type three letters and it tells you how
many matches there are. Type a fourth and the number changes. Your screen
reader picks up the new count on its own, so you do not have to ask.

**Ctrl+Down** and **Ctrl+Up** step through the matches while you stay in the
search box. You can hear each one and still change what you typed. When you
have the one you want, press **Enter** and you are back in your document,
right on it.

You do not have to open the window to count. **Count Occurrences**
(**Ctrl+Alt+Shift+F3**) counts your current search from anywhere in the
document.

**All Matches** (**Ctrl+Shift+F3**) shows every match in one list, in order,
each with its line, its column and the words around it. Open it before you
press Replace All. It lets you see everything you are about to change before
you change it.

### Find and replace in all your open documents

Sometimes the thing you are looking for is in one of a dozen documents you have
open, or you need to change a name in all of them. **Find in Open Documents...**
(**Ctrl+Alt+Shift+F8**, on the **Edit** menu under Replace) searches every
document QUILL Lite has open, not just the one in front of you.

It searches the text exactly as it is in each window, so it finds:

- changes you have not saved yet,
- new documents you have never saved,
- formatted documents, such as Word and RTF files, searched as you see them.

Anything that is not open is left alone, and it never writes to a file on disk.
If you want to search files that are saved in a folder instead, that is
**Search in Files**, described next.

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

QUILL and QUILL Lite share this window and work the same way, and it is in the
same place in both: the **Edit** menu, under Replace. The key differs by one
chord: QUILL uses **Ctrl+Shift+F10**, because in QUILL Ctrl+Alt+Shift+F8 opens
Quill Weather.

### Searching a whole folder of files

Find in Open Documents works on what you have open. When the files you want are
saved in a folder and you would rather not open them all, use the folder search,
the same one QUILL has:

- **Search in Files...** (**Ctrl+Alt+Shift+F**, on the **Edit** menu, just
  below Find in Open Documents; **Alt+E**, then **S**) looks through every file
  in a folder, and every folder inside it.
- **Replace Across Files...** (**Ctrl+Shift+R**, the row below it) changes
  every match in those files, on disk.

Both are on the same keys and in the same place in QUILL. In a new install they
are there from the start. If you chose the Notepad or WordPad profile in
**Tools > Customize Features...** (**Ctrl+Alt+F10**), they are switched off with
the rest of the **Matches and wider searches** area, because neither program
had them; check that box there to bring all five back.

An example. You remember writing to somebody called Priya about a deadline,
but not which of the forty letters in your Letters folder it was in. Open any
document from that folder, press **Ctrl+Alt+Shift+F**, leave **Starting
folder** as it is, type `*.txt` in **File pattern** and `Priya` in **Search
text**, and press **Enter**. When the search finishes QUILL Lite tells you, for
example, "3 matches in 2 of 40 files", and a new window lists each file with
the matching lines. Press **Ctrl+O** and type the file name it gave you to open
the one you want.

Both open the same window, which asks for:

- **Starting folder**: where to look. It starts at the folder of the document
  you are in.
- **File pattern**: which files, such as `*.txt` or `*.md`. A star on its own
  means every file. To name more than one kind, put `|` between patterns to
  take either, `&` to need both, and `!` before one to leave it out:
  `*.md | *.txt` searches Markdown and text files together, and `* !*.bak`
  searches everything except backups. Double quotes around a name mean that one
  exact file, and a pattern with a slash, such as `!drafts/*`, is matched
  against the path inside the starting folder. A pattern without these
  characters works exactly as before, and the search text still follows the
  Match mode.
- **Search text**, and for Replace Across Files, **Replacement**.
- **Match mode**: Plain text, Wildcard (`*` and `?`) or Regular expression.
- **Output format**: how the results are written out, from just the file names
  to every matching line.
- **Case sensitive** and **Whole word**.

The search runs in the background, so QUILL Lite stays usable while it works,
even on a big folder. When it finishes you hear how many matches it found in
how many files, and the results open in a new untitled window. Read it with
your usual keys, and save it if you want to keep it.

Replace Across Files changes the files on disk, so it is careful:

- **Preview before replacing** is checked when the window opens. With it
  checked, every change it would make opens in a new window first, and you are
  asked "Replace 312 matches in 87 files?" before anything is written. Answer
  **No** and nothing changes.
- When it has finished, a report of what it changed opens in a new window.
- Files you have open in QUILL Lite are changed on disk, not in the window. If
  one of them is open, QUILL Lite notices the file changed and offers to reload
  it.

The first time you use Replace Across Files, try it on a copy of the folder.

### Searching for things you cannot type

The Find and Replace windows have a **Search mode** with three choices.

#### Normal text

This is the everyday one. What you type is what it looks for, punctuation and
all.

#### Special characters

This lets you search for characters that have no key. `\t` is a tab, `\n` is a
line break, `\u2014` is an em dash, and `\N{NO-BREAK SPACE}` is exactly what it
says.

It pairs well with **Describe Character**. Say Describe Character tells you
that you are standing on a no-break space. Special characters mode then lets
you find every other one, or replace them all with an ordinary space.

#### Regular expression

This treats what you type as a search pattern. A `.` matches any character,
`*` repeats the thing before it, `[abc]` matches any one of those letters, and
`^` and `$` are the start and end of a line.

If your pattern has a mistake in it, QUILL Lite tells you which character is
wrong. That way you know the difference between "my pattern is broken" and
"there really is nothing to find".

#### Whole word, in every mode

**Whole word** works with all three modes. In regular expression mode it
applies to the whole pattern, so `cat|dog` finds the word cat or the word dog,
and does not find "dog" in the middle of "hotdogs".

## Going somewhere

Press **Ctrl+G** to open **Go To**. It works like Word's Go To: one window, and
you choose what to go to.

1. Press **Ctrl+G**.
2. At the top, arrow to **Line**, **Bookmark** or **Heading**. A PDF adds
   **Page**, and **Outline** too if the PDF has one.
3. The rest of the window changes to match. For a line you get a number box.
   For everything else you get a list. Bookmarks start with their number,
   headings with their level, and outline entries with their title, so you
   can pick one out by its first word.
4. Press **Enter** to go there.

If you already know which kind you want, there are quicker keys.
**Alt+Shift+G** goes straight to the bookmark list, and **Ctrl+Alt+L** goes
straight to the heading list. **Ctrl+G** is the one to press when you are not
sure.

## Making a table

**Insert > Table...** (**Ctrl+Alt+T**, the same key as in QUILL) asks three
questions: how many columns (1 to 12), how many rows (1 to 50), and whether
the first row is a header row. Then it puts the table on lines of its own and
leaves the cursor in the first cell, ready to type.

What you get depends on the kind of document:

- In a **rich text** document (**Alt+Shift+F** switches to it), the table is a
  **real table**: a grid on screen, with no `|` characters anywhere, which
  your screen reader, Word and WordPad all see as a table. Its first row is
  the header row when you asked for one. Save the document as `.rtf` or as a
  Word document and it stays a real table, the header row marked so a screen
  reader in Word announces the column headers.
- In a **Markdown** or **plain text** document, the table is rows of cells
  divided by `|`, the shape described below.
- In an **HTML** document, the table is a real `<table>`, with its header
  cells marked so a screen reader in a browser announces each cell's column.

Either way the table keys work on it at once.

## Moving through a table

**Navigate > Table** works on every table QUILL Lite shows: a real table in
rich text (every table you make there, and every table in a Word or RTF
document you open as rich text), and rows of cells divided by `|` in Markdown
and plain text. It reads one cell at a time and tells you where you are, on
the same keys as QUILL:

| Key | Command | What it does |
|---|---|---|
| **Ctrl+Alt+Right** | Next Cell | The next cell in the row |
| **Ctrl+Alt+Left** | Previous Cell | The previous cell in the row |
| **Ctrl+Alt+Down** | Cell Below | The cell below, in the same column |
| **Ctrl+Alt+Up** | Cell Above | The cell above, in the same column |
| **Alt+Home** | First Cell in Row | The first cell of this row |
| **Alt+End** | Last Cell in Row | The last cell of this row |
| **Ctrl+Alt+Home** | First Cell | The first cell of the table |
| **Ctrl+Alt+End** | Last Cell | The last cell of the table |

Each move puts the cursor at the start of the cell's text and says the cell's
place, then its text -- but only the part that changed. Moving along a row
says the column, "Column 3: Lead"; moving down a column says the row, "Row
4: Lead"; a jump to another row and column says both. The table's size is
said once, when you arrive in it. An empty cell is "blank". The row of dashes under the header row is skipped; it is not a row
you read.

At an edge the cursor stays where it is and you hear why: "No more cells" at
the end of a row, "No more rows" at the bottom of a column, and "No more
cells, end of table" on the very last cell. Outside a table, every one of
these keys says "Not in a table" and does nothing else. **Alt+Left** (Go Back)
returns from a cell move like any other jump.

For example, in this table:

```
| Name | Role |
| --- | --- |
| Ann | Lead |
| Bo | Tester |
```

put the cursor on "Name" and press **Ctrl+Alt+Down**: you hear "Row 2:
Ann". Press **Alt+End**: "Column 2, Role: Lead" -- a new column says its
header, because this table has a header row. Press **Ctrl+Alt+End**: "Row 3:
Tester" (the same column, so neither the column nor its header is repeated). Press **Ctrl+Alt+Right**: "No more cells, end
of table".

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

The shape and "Out of table" go with **Announce Headings** in the View menu.

A cell whose own text contains a `|` is written `\|` and read as the `|` it
stands for, so it never makes an extra column. If your screen reader uses
**Ctrl+Alt** with the arrow keys for its own table commands, it may answer
these keys first in some modes; the menu rows always work.

## Editing a table

- **Tab** and **Shift+Tab** move to the next and previous cell, on to the next
  row at the end of one, as in Word. **Tab** in the very last cell adds a row
  and puts you in its first cell. Outside a table, Tab works as it always has.
- **Navigate > Table** also has **Insert Row Below**, **Insert Column Right**,
  **Delete Row**, **Delete Column** and **Tidy Table**, the same as in QUILL.
  Each is one Undo and says what it did, such as "Added row 3" or "Deleted
  column 2, Role. 1 columns left". Tidy Table pads every cell to its column's
  widest, so the columns of a `|` table line up on screen; a real table
  already lines up, and says so.
- In a real table, adding or deleting a row or a column rebuilds the table
  with its text in place. Bold, italic or a font *inside* its cells does not
  survive that rebuild; type the formatting after the table has its shape.

A real table in rich text is saved as a real table: in an `.rtf` file with its
first row marked as the header row, and in a Word document the same way. A
`|` table in a Markdown document you switch to rich text becomes a real table,
and switching back to Markdown or plain text turns a real table into `|` rows.

## Blocks, indentation and problems: Navigate > Code

The **Code** submenu of the Navigate menu (**Alt+N**, then **C**) holds a few
commands that help most in HTML, Markdown and anything indented. They are the
same commands, on the same keys, as in QUILL.

### Moving by block

**Next Block** and **Previous Block** move a paragraph at a time in Markdown
and plain text. In an HTML document they move between headings and landmarks:
`header`, `nav`, `main`, `aside`, `section`, `article`, `footer` and `form`
elements, and anything with a landmark `role`. Your screen reader reads the
line you land on. They have no key, as in QUILL; press **Alt+N**, **C**, then
**N** or **P**, or give them a key in the Keyboard Manager. At either end you
hear "No next block" or "No previous block".

### Moving by indentation

**Next Indent Change** (**Alt+Shift+PageDown**) moves down to the next line
whose indentation is different from the line you are on, skipping blank lines.
**Previous Indent Change** (**Alt+Shift+PageUp**) goes up. The caret lands on
the first character that is not a space, your screen reader reads the line,
and QUILL Lite adds how far in it is, such as "4 spaces" or "No indent". This
is the quick way out of a long nested list or a block of indented notes.

### Checking a Markdown or HTML document

**Check This File...** (**Ctrl+Alt+/**) looks through the whole document for
problems:

- in **Markdown**: heading levels that skip (a level 3 heading straight after
  a level 1), pictures without alt text, links with no text or no address, and
  links to files next to the document that are not there;
- in **HTML**: tags closed in the wrong order or never closed, closing tags
  with nothing open, the same `id` used twice, and pictures without alt text.

If nothing is wrong you hear "No problems found." Otherwise the **Problems**
list opens. It starts by saying how many problems there are, then lists them
one to a row, place first: "Line 4, column 1, error: Markdown image is missing
alternative text." Press **Enter** on one to go to it, or **Escape** to stay
where you are.

**Next Problem** (**Ctrl+Alt+.**) and **Previous Problem** (**Ctrl+Alt+,**)
take you to the next or previous problem without the list, and say it: "Problem
2 of 3, line 9, column 1, warning: Heading levels jump by more than one level."
They go round from the last to the first, and check the document again first
if you have changed it.

QUILL Lite checks the two kinds of document it knows. In a plain text document
you hear "Nothing to check: QUILL Lite checks Markdown and HTML documents."
QUILL checks those too, and also code and data files such as JSON, XML, Python
and CSV, using tools you already have installed for languages like JavaScript.

## Reading without changing anything: the Read-Only Guard

When you open a long reference document only to read it, such as a manual, a
book or minutes you must not alter, one stray key can change it, and a Ctrl+S
an hour later saves the change. The **Read-Only Guard** locks the document
against edits while you read.

**Ctrl+Alt+Backspace**, or **Tools > Read-Only Guard**, turns it on and off.
The menu row shows a check mark while it is on. You hear:

- "Document is read-only" when you turn it on;
- "Document is editable" when you turn it off.

While it is on:

- Typing, **Backspace**, **Delete**, **Enter** and pasting do nothing.
- Commands that would change the text say "Document is read-only" and change
  nothing. That covers cutting, pasting, undo and redo, everything in
  **Edit > Lines**, the **Insert** menu (Insert Table too), the row and column
  commands on **Navigate > Table**, the formatting commands, changing case and
  indenting, Snippets, and a word tool's **Replace**. The table keys and the
  arrows still move through a table.
- Everything you use to read still works: the arrow keys and every way of
  moving, **Find** (**Ctrl+F**), **Go To** (**Ctrl+G**), the headings list,
  selecting and copying, Say Selection, the dictionary and the thesaurus
  (looking up, not replacing).
- **Bookmarks** work as usual. Set one with **Ctrl+Shift+B** and come back to
  it with **F2**; a bookmark is kept beside the file, not inside it.
- **Inline notes** work too. A note you add while the guard is on is kept
  beside the file rather than written into it, so the document stays exactly
  as it was.

QUILL Lite **remembers** the guard for that file. Close QUILL Lite, open the
same file tomorrow from File Explorer, from Recent Documents or from Ctrl+O,
and it opens locked again. It is the same file however it was reached, even if
File Explorer spells the folder with different capitals.

If QUILL Lite cannot write down that you locked the file, for example because
its settings folder is on a full disk, the document is still locked for now
and you hear so, with the reason:

> Document is read-only for now, but it could not be remembered for next time
> (There is not enough space on the disk).

A document that has never been saved cannot be remembered either, because it
has no file name yet; save it first if you want the guard to stay.

A file that Windows itself marks read-only, or one on a share you cannot write
to, opens locked as well, and QUILL Lite says so as it opens. Turn the guard
off if you want to type anyway; you can then save under a new name.

The guard is the same command QUILL has, on the same key, so you only learn it
once.

## Bookmarks

A bookmark is a place you want to come back to.

| Key | What it does |
|---|---|
| **Ctrl+Shift+B** | Drop a bookmark in the next free slot |
| **Ctrl+Shift+1** to **Ctrl+Shift+9** | Set that numbered bookmark |
| **F2** / **Shift+F2** | Next / previous bookmark |
| **Alt+Shift+G** | The bookmark list: go to one, or remove one |
| **Ctrl+Alt+B** | Clear them all |

Bookmarks move with your text as you edit around them, so they stay on the
right words.

If you would like to try bookmarks with the app guiding you, the tutorial
*Finding your way back* walks you through them, along with the temporary
bookmark and Go Back.

### They are still there tomorrow

Close a document, open it again, and your bookmarks are right where you left
them. So is the cursor. You do not have to do anything to keep them.

This is a real help in a long file. You cannot glance at a scrollbar to see
where you are, so marking a few places and finding them again next time saves
a lot of hunting.

A few things worth knowing:

- **A document you have never saved is not remembered.** It has no file name
  yet. Save it once and its bookmarks are kept from then on.
- **Nothing extra is saved next to your file.** No extra files appear in your
  folder. QUILL Lite keeps the list in its own settings folder.
- **If the file got shorter while it was closed,** for example because another
  program edited it, any bookmark past the new end is moved to the end.

If you switch bookmarks off in **Tools > Customize Features**, none of this is
saved at all.

### The one with no number

| Key | What it does |
|---|---|
| **Ctrl+Alt+J** | Set Temporary Bookmark: drop a pin where the cursor is |
| **Ctrl+Shift+J** | Go to Temporary Bookmark: go back to it |

There is one more bookmark, and it works differently. Use it when you are
about to look something up and want to come straight back:

1. Press **Ctrl+Alt+J** where you are.
2. Go and look at whatever you need.
3. Press **Ctrl+Shift+J** to come back.

It has no number, no name and no place in the list. Setting it again just moves
it, without asking. It is forgotten when you close the document. It is meant
for a quick trip, so it stays out of your way.

These are the same two keys QUILL uses.

### Going back where you came from

| Key | What it does |
|---|---|
| **Alt+Left** | Go back to where you were before the last jump |
| **Alt+Right** | Go forward again |

These are **Go Back** and **Go Forward**, at the top of the **Navigate** menu.
They are the same keys a web browser uses.

QUILL Lite remembers every jump you make: going to a line, following a heading,
choosing something from the heading list or the bookmark list, and landing on a
search result. **Alt+Left** takes you back to where you were before the jump.
Think of it as undo for moving around. Press **F3** to check a word somewhere
else, then **Alt+Left** to come home.

They are always there, even if you switch headings and bookmarks off.

Unlike bookmarks, this history is only kept while the window is open.

## What you learned, and where to go next

You can find text with **Ctrl+F**, narrow it with Match case and Whole word
only, replace one match at a time or all at once with **Ctrl+H**, hear how
many matches there are, see them all in one list, and search for characters
you cannot type. **Ctrl+G** takes
you to a line, a bookmark or a heading from one window. **Navigate > Code**
moves by block and by indentation, and **Ctrl+Alt+/** checks a Markdown or
HTML document for problems. Numbered bookmarks
are still there after you close the document, the temporary bookmark is there
for a quick trip, and **Alt+Left** takes you back after any jump.

The tutorial *Finding your way back* lets you practise bookmarks, the
temporary bookmark and Go Back with the app guiding you.

Next, Chapter 5, Selecting, copying and changing text, shows you how to take
more than a few words at once, and what you can do with them. It also covers
marks, a lighter kind of bookmark.

---

- Previous: [Chapter 3: Opening, saving and printing](lite-guide-03-opening-saving-and-printing.html)
- Next: [Chapter 5: Selecting, copying and changing text](lite-guide-05-selecting-copying-and-changing-text.html)
- [Contents](../userguide.html)
