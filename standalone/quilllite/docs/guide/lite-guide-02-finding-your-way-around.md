# Chapter 2: Finding your way around

You have typed something, and now you want to know where everything lives.
QUILL Lite keeps all your documents inside one window and gives each one a
number, so you can always get back to it. In this chapter we will look at
that window, close several documents at once, walk along the status bar where
the facts about your document live, flip the switches on the View menu, and
find any command just by typing part of its name. Have QUILL Lite open while
you read, and try each thing as you meet it.

## Your documents are numbered

QUILL Lite opens your documents **inside one window**, and gives each one a
number. Your first document is 1, the next is 2, and so on. A document keeps
its number for as long as it is open, even if you close the one before it.

The number is how you get back to it:

| Key | What it does |
|---|---|
| **Alt+1** to **Alt+9** | Go straight to that document |
| **Ctrl+Tab** / **Ctrl+Shift+Tab** | Next / previous document |
| **Ctrl+F6** | Next document (the usual Windows key, same thing) |
| **Window menu** | Every open document, by number, with a mark on the one you are in |

**One thing to know.** Because your documents live inside one window, they do
**not** appear in Alt+Tab. Alt+Tab shows *QUILL Lite* once. Use the four ways
above to move between your documents. If a document seems to have
disappeared, it has not: press **Alt+1** or open the Window menu and it is
there.

**Ctrl+N** makes a new document. **Ctrl+W** closes the one you are in.
**Ctrl+Q** closes everything, and asks you about anything you have not saved.

Lost count? Press **Ctrl+Shift+Space** (**Window > Say Windows
Open**) and you hear "3 documents open". Press it twice, quickly, to hear
their names in order, with the one you are in marked "(current)". Chapter 8
has more.

If you would like to practise this with the app guiding you, the tutorial
*Your documents are numbered* opens a second file and walks you between them.

### Opening a large file, or one on a network drive

A file of a megabyte or more, or any file on a network drive, opens without
freezing the window. Here is what happens:

1. A new document window appears straight away. Its title has its number,
   the word "Opening" and the file's name, and QUILL Lite says "Opening" and
   the name once.
2. While the file is loading, the window is read-only, so nothing you type
   can get lost.
3. When the file arrives, the text appears and your cursor is at the top,
   ready to read.

To cancel, close that window with **Ctrl+W**. If the file cannot be read, for
example because the network drive went away or the disk is busy, QUILL Lite
tells you why and asks whether to try again. Yes tries again. No closes the
empty window.

Smaller files on your own computer open all at once, as you would expect.

### Opening a second QUILL Lite

If you open a file from File Explorer while QUILL Lite is already running, it
opens in the QUILL Lite you already have. That keeps all your documents, and
their numbers, in one place.

If you really do want two separate QUILL Lite windows, one on each monitor
for example, start it with the extra option `--new-instance`.

The two share one settings file, and they do not undo each other's choices.
When one saves its settings, it writes only the settings it changed. If both
changed the same setting, the one that saves last wins. A setting you change
in one window does not change the other window while it is open. It takes
effect there the next time you start QUILL Lite.

## The window

QUILL Lite opens **maximized**, filling the screen, the first time you start
it. After that, it opens the way you left it. Make it smaller, and it opens at
that size next time. Make it full screen again, and that is remembered too.

Full screen is the starting point because a small window can cut text off, or
show only a few rows of a list. You can change it with one key, and QUILL Lite
will not ask again.

All the QuillVille apps work this way: QUILL, Quill Radio, Cast, Weather, Audio
Studio, Inkwell, the Converter, QUILL Transcribe, the Media Player and Beacon.
QUILL Transcribe, released on 1 November 2026, is the one that types what you
say into other programs; in QUILL Lite itself you dictate with Ctrl+F11.

## Closing a lot of windows at once

**Window > Close Other Documents** (**Ctrl+Shift+F4**) keeps the document you
are in and closes all the others. QUILL uses the same key, so you only need to
learn it once.

### When some have unsaved changes

If any of those documents has changes you have not saved, QUILL Lite asks you
about it. The question also tells you how many more documents are waiting, so
you know right away whether this is one question or sixty-seven. You can
answer:

- **Save**: save this document, then ask about the next one.
- **Don't Save**: close this document without saving, then ask about the next
  one.
- **Save All**: save this one and every other one waiting, without asking again.
  A document that has never been saved will still ask where to put it.
- **Don't Save Any**: close all the rest and lose their changes, without asking
  again. This cannot be undone.
- **Cancel**: stop. Whatever is still open stays open, and you hear how many
  documents closed before you stopped.

**Pressing Enter chooses Save**, so you never lose work by pressing Enter. If a
save fails, for example because the disk is full or the file has become
read-only, QUILL Lite stops there and does not close that document. Save All
also stops, and you will be asked about each one again.

### Coming back with Alt+Tab, and leaving

When you Alt+Tab back to QUILL Lite, it puts you back in the document you were
working in, ready to type. If you were in the Find box, another control or an
open menu, you stay there.

When you close QUILL Lite, it stops taking in new files to open before it
closes its windows. Any files that were still waiting to open are opened the
next time you start it. If you press Cancel on a save question while closing,
QUILL Lite stays open and carries on as normal.

## The status bar

The status bar is a row of small facts about your document: where you are, how
long it is, what kind of file it is, and whether you have saved. It is the
first place to go when you want to know something.

Here is how to use it:

1. Press **F6**. You land in the status bar. (In the menus this is **Navigate >
   Status Bar**.)
2. Press **Left Arrow** and **Right Arrow** to move along it, or **Home** and
   **End** to jump to either end. Each part says its name and its value.
3. Press **Enter** on a part to act on it. What Enter does is in the table
   below.
4. Press **Escape** to go back to your document, right where you left it.

### Hiding the bar

**View > Status Bar** (**Alt+Shift+B**) takes the bar off the screen and puts it
back, just like Notepad's. You lose nothing while it is hidden. A few keys give
you the same facts out loud:

- **Ctrl+Shift+G** speaks the counts for the whole document.
- **Ctrl+Alt+W** speaks the line widths: the longest line, which line that is,
  and the average. That is handy when you are writing for a braille display or
  a narrow window.
- **Ctrl+G** asks for a line number to go to, which is what the Position part
  would have told you.

If you press F6 while the bar is hidden, QUILL Lite tells you it is hidden.

### Every part, in order

| Part | What it tells you | Enter does |
|---|---|---|
| **Status Message** | The last thing QUILL Lite told you, so speech you missed can be heard again | repeats it |
| **Position** | Which line and column you are on, out of how many lines | Go to a line |
| **Page** | Which page you are on, out of how many. Only a PDF has pages, so this part is only there when a PDF is open | Go to a page |
| **Word Count** | How many words the document has | repeats it |
| **Character Count** | How many characters, spaces included | repeats it |
| **Selection** | How much is selected, or "No selection" | repeats it |
| **Typing Mode** | Whether typing inserts or overwrites | switches between them |
| **Tab Mode** | Whether the Tab key types a tab or indents the line | switches between them |
| **Format** | Which of the four kinds this document is: plain text, Markdown, HTML or rich text | rings on to the next kind |
| **Heading** | Which heading you are inside | lists every heading |
| **List** | Which list you are inside, how many items, which one you are on | stops or resumes announcing lists |
| **Dictation** | What dictation is doing: off, listening, hearing you, writing, spelling, command mode, waiting for a command, or waiting for the wake phrase | starts or stops dictation |
| **Notifications** | Progress and results from background work, including audio transcription | reads a notification or opens its result |
| **Encoding** | How this file stores its letters and accents | change it |
| **Line Endings** | How this file marks the end of a line | change it |
| **Saved State** | Whether you have unsaved changes | saves |
| **Workbench** | The repository the GitHub menu works on, such as "Workbench: community-access/quill", or just "Workbench" when the document isn't in a GitHub repository. Only there while GitHub Workbench Mode is on | says it again |
| **Project** | The open project and its git branch, and "waiting for you" when the project task needs an answer. Only there while a project is open, in the Developer profile | opens Do a Project Task |
| **AI** | Which AI is in use, such as "AI: ChatGPT plan" | opens Choose Your AI |

That is seventeen parts, or sixteen when the document has no pages, and an
eighteenth, Project, while a project is open. Most of
them explain themselves. A few are worth a
closer look.

#### Status Message

Speech is gone the moment it is spoken. If QUILL Lite said something and you
missed it, this is where you go to hear it again.

#### Typing Mode

Every Windows editor has an overwrite mode, where what you type replaces the
letters already there instead of pushing them along. Most editors never tell
you which mode you are in, so you find out by typing over a sentence you wanted
to keep. This part tells you.

To switch, press **Ctrl+Alt+Shift+W**, or press **Enter** on this part.

The **Insert** key switches it too. QUILL Lite does not take the Insert key for
itself, because your screen reader uses it. It just notices when you press it,
so this part always tells you the truth.

#### Tab Mode

When you start, the **Tab** key types a tab character, just as it does in
Notepad. Press **Ctrl+Alt+Shift+I** and Tab indents the whole line instead,
which is usually what you want when you are working on code. **Shift+Tab**
outdents in either mode, so you can always take back a tab you did not mean.

#### Format

This tells you whether the document is plain text, Markdown, HTML or rich text.
That one fact decides a lot: what **Ctrl+B** writes, what the heading keys
write, which tag picker the Insert menu offers, and whether the List part has
anything to say.

QUILL Lite guesses the kind from the file's name. Press **Enter** here to move
on to the next kind; you will hear its name. **Ctrl+Alt+F6** takes you straight
to the one you want. There is more in [Four kinds of
document](lite-guide-03-opening-saving-and-printing.html#four-kinds-of-document), in Chapter 3.

#### List

When you arrive in a list, you hear something like "Bulleted list, 5 items".
You do not hear more on every arrow press, because that would be a lot to sit
through. When you want to know exactly where you are, this part tells you which
item you are on, for example "Bulleted list, 4 of 9, level 2".

#### Encoding and Line Endings

These two decide whether your file opens properly on somebody else's computer.
You will rarely need to change them. But when a file arrives looking like
nonsense, this is where to look.

In a rich text document they read **"RTF (rich text)"** and **"Not applicable
(rich text)"**. A rich text file keeps its letters and its line breaks in its
own way, so these two questions do not apply to it.

If a file came in a form QUILL Lite cannot write back, such as UTF-16
big-endian or the old Mac style of line ending, the list you get from Enter
shows a **keep as is** choice and stays on it. That way you cannot convert a
file by accident when you only opened it to read. There is more in [How this
file is written](lite-guide-03-opening-saving-and-printing.html#how-this-file-is-written-encoding-and-line-endings),
in Chapter 3.

## The View menu

The View menu has seven switches and three text sizes. Each switch tells you
its new setting out loud when you press it, so you never have to go and check.

| Key | Switch | Starts |
|---|---|---|
| **Alt+Shift+D** | **Dark Mode**: dark colours, whatever Windows is set to | following Windows |
| **Alt+Z** | **Word Wrap**: long lines fold to fit the window instead of running off the side | on |
| **Ctrl+Alt+F3** | **Announce Headings**: say "Heading 2, Installing" when you arrive on one | on |
| **Ctrl+Alt+F5** | **Announce Lists**: say "Bulleted list, 5 items" when you enter one | on |
| **Ctrl+Alt+Shift+W** | **Overwrite Mode**: what you type replaces what is there | off |
| **Ctrl+Alt+Shift+I** | **Tab Key Inserts a Tab Character**: when off, Tab indents the line | on |
| **Alt+Shift+B** | **Status Bar**: show or hide the bar | on |

When you arrow onto one of these in the menu, its check mark tells you whether it is
on, without changing it.

**The two announcement switches belong to each document**, not to the whole
app. So you can have headings announced in a letter, and switched off in a
settings file full of lines that start with `#`.

**Overwrite Mode** can also be changed from the status bar: press **F6**, arrow
to **Typing Mode**, and press **Enter**. The **Insert** key switches it too, and
QUILL Lite tells you what happened. It does not take that key for itself,
because your screen reader uses it.

### Making the text bigger or smaller

| Key | What it does |
|---|---|
| **Ctrl+=** | Increase Text Size |
| **Ctrl+-** | Decrease Text Size |
| **Ctrl+0** | Reset Text Size |

These change only how big the text looks on screen. Your file is not changed,
and your screen reader says the same things.

**Ctrl+Shift+.** and **Ctrl+Shift+,** are something else. In a rich text
document they change the font size of the text you have selected, and that is
saved in the file.

### What is in this document, in numbers

- **Document Statistics** (**Ctrl+Shift+G**) tells you the size of the whole
  document, or of the selection: words, lines and characters. Press it twice
  quickly to add paragraphs, sentences, long sentences, the reading time and
  the reading grade. Chapter 8 has the details.
- **Line Statistics** (**Ctrl+Alt+W**) tells you about line widths. It is useful
  when you are writing to fit something, like a braille display, a narrow
  window, or a line limit in code.

## Finding a command

Cannot remember where something is? Press **Ctrl+Shift+P** to open the
**Command Palette...**. It is also the first item in the **Tools** menu, the
same place as in QUILL. Type part of what you want, such as "sort",
"bookmark" or "print", then choose it from the list and press **Enter**. You do
not need to know which menu it is in.

Each command in the list shows its key beside it. That is a gentle way to learn
keys as you go. If you have changed a key, the palette shows your key.

### Typing a name to reach it in a list

Most lists in QUILL Lite, such as Snippets, Recent Documents, the bookmark and
heading lists and Recent Clips, let you type the start of a row's name to move
to it. You can type the **whole** name, spaces included:

1. Press **Ctrl+Alt+Shift+Home** to open Snippets.
2. Type `meeting notes` at an ordinary pace. The list moves to the first row
   that starts with "meeting notes", and stays on it while the row still
   matches.
3. Press **Enter** to put that snippet in.

While you are typing a name, **Space is part of the name**. It used to open
whatever row the first word had reached, so typing "meeting notes" could
insert "Meeting agenda". If you pause for about a second, the next key starts
a new name, and **Space** on its own opens the selected row as before. **Enter**
always opens the selected row and **Escape** always closes the list.

Typing the same letter again and again steps through the rows that start with
it. If nothing starts with what you typed, you hear "No match for" and what you
typed, and the selection stays where it was.

### One box for everything: Go To Anything

**Navigate > Go To Anything...** (**Ctrl+Alt+Shift+A**) is like the Command
Palette, but it searches more. Type a few letters and the list shows matching
commands, headings in this document, and bookmarks you have set, all together.
Press **Enter** to run the command or go to the place.

**It starts switched off.** You can already do each of these with its own key:
the Command Palette, the headings list (**Ctrl+Alt+L**) and the bookmark list
(**Alt+Shift+G**). If you would rather have one key for all three, turn it on in
**Tools > Customize Features** (**Ctrl+Alt+F10**).

Headings only show up here in a **rich text** document. In a Markdown or HTML
file, use the headings list on Ctrl+Alt+L instead.

### Saying more in one search

Start a Go To Anything search with `#` to see headings only, or `>` to see
commands only. The search box, and the other lists you narrow by typing, also
understand a few characters that let one search say more:

- **Words** match anywhere in a row, and capitals do not matter.
- **`&`** needs both words: `#budget & 2026` finds only headings with both. Two
  words side by side mean the same, so `budget 2026 !draft` is "budget and 2026
  and not draft".
- **`|`** takes either: `#introduction | summary` lists both kinds of heading.
- **`!`** leaves a word out: `#chapter !draft` skips the drafts.
- **`*`** stands for any run of letters inside a word, and **`?`** for exactly
  one: `#chap*` finds Chapter and Chapters. Neither reaches past a space.
- **Double quotes** match exact text, spaces and all: `#"to do"`.

`!` is read first, then `&`, then `|`, so `draft | notes !old` means "draft, or
notes that are not old". A search with none of these characters works exactly
as before, and a half-finished one such as `notes |` is just read as `notes`
until you type the next word.

The same rules work in **Insert > Markdown Tag...** (**Ctrl+Alt+I**),
**Insert > HTML Tag...** (**Ctrl+Alt+O**), where `h? !h1` lists every heading
tag except the top one, and in both lists of **Move Section To...**
(**Ctrl+Alt+Shift+F5**). The **File pattern** of Search in Files takes them
too; chapter 4 has the details. Press **F1** in any of these search boxes to
hear a short reminder.

## What you learned, and where to go next

Your documents share one window, and each has a number, so **Alt+1** to
**Alt+9**, **Ctrl+Tab** and the Window menu always find them, even though
Alt+Tab does not. Big files and files on a network drive open without
freezing. The window starts maximized and then remembers the size you choose.
**Ctrl+Shift+F4** closes every document except the one you are in, and Enter
on its question always means Save.

The status bar is a row of facts you reach with **F6**, walk with the arrow
keys and leave with **Escape**, and Enter on a part acts on it. The View menu
turns things on and off and tells you the new setting, **Ctrl+Shift+G** and
**Ctrl+Alt+W** give you the numbers, and **Ctrl+Shift+P** finds any command by
name.

If you would like some practice, Help > Tutorials has *Your documents are
numbered*, which walks you between two documents, and *What to press when you
are lost*, which starts at the status bar.

Next, Chapter 3, Opening, saving and printing, explains the four kinds of
document and how QUILL Lite gives your file back exactly as it came.

---

- Previous: [Chapter 1: Your first minutes](lite-guide-01-your-first-minutes.html)
- Next: [Chapter 3: Opening, saving and printing](lite-guide-03-opening-saving-and-printing.html)
- [Contents](../userguide.html)
