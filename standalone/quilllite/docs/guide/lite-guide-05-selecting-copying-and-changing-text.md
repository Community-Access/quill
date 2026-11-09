# Chapter 5: Selecting, copying and changing text

Holding Shift and pressing an arrow is fine for two letters, and slow for four
paragraphs. This chapter gives you better ways. You will select from here to
there without holding anything down, take a whole word, line or paragraph in
one key, and read a selection without risking it. Then you will keep more than
one thing on the clipboard, move, sort and tidy whole lines, and get back text
you deleted. Everything here tells you how much it took or changed, so you
always know what you have.

## Selecting

Holding Shift and pressing an arrow selects one character at a time. That is
fine for two letters. For four paragraphs it is slow, and it is easy to lose
track of how far you have got.

**Edit > Selection** gives you better ways. Each one tells you how much it
took, for example "Selected paragraph, 41 words". That way you know what you
have before you press anything that might replace it.

If you would like to try this with the app guiding you, the tutorial
*Selecting more than a few words* walks through each of these ways.

### Start a selection and walk to the end of it

This is the one to learn first.

1. Put the cursor where you want the selection to start.
2. Press **F8**.
3. Move any way you like: arrows, Home, End, Page Down, or Ctrl with an arrow.
4. When you reach the end, press **Shift+F8**. QUILL Lite tells you how much
   you selected.

You do not have to hold anything down, and you do not have to count. Use it
whenever what you want does not start and end neatly on a word or a paragraph.

| Key | What it does |
|---|---|
| **F8** | Start selecting from here |
| **Shift+F8** | Finish, and say how much was taken |
| **Ctrl+Alt+F8** | **Toggle Selection Marker**: drop the starting point or pick it up, without moving the cursor |
| **Ctrl+Shift+F8** | Put back the selection you just had |
| **Alt+Shift+F8** | Go to the beginning of what is selected |

#### A Shift that stays down (Alt+Shift+F9)

**Extend Selection Mode** is another way to do the same job. Try both and use
the one you like.

1. Press **Alt+Shift+F9**. QUILL Lite says "Extend selection mode on" and tells
   you where you are.
2. Move with the arrows, Home, End, Page Down or Ctrl with an arrow. Each move
   makes the selection bigger, as if you were holding Shift. Your screen reader
   does not say "selected" on every key press, so it stays quiet while you
   work.
3. Press **Alt+Shift+F9** again, or **Escape**, to stop.

If you type something that is not a movement key, it replaces the selection,
just as it would if you had been holding Shift.

How is this different from **F8**? With F8, nothing is selected until you press
**Shift+F8**, so in between you can use anything to get there: Find, Go To, a
bookmark. Extend Selection Mode selects as you go, so what you hear is always
what you have.

**Ctrl+Shift+F8** is worth remembering. If an arrow key has just thrown away a
selection that took you a while to build, press it to get the selection back,
however you made it.

#### What you hear when something is selected

Every selection tells you two things, in the same order: what it took, and how
many words. For example, "Selected paragraph, 41 words".

When you finish an **F8** selection, you also hear where it reaches, for
example "Selected 120 words, lines 14 to 31". It could start and end anywhere,
so this tells you how far it went.

QUILL says exactly the same things, so you hear the same sentences in both
editors.

### Take a whole word, line or paragraph at once

| Key | What it does |
|---|---|
| **Ctrl+Shift+W** | Select the word |
| **Ctrl+Shift+E** | Select the line |
| **Ctrl+Shift+H** | Select the paragraph |
| **Ctrl+Space** | Select the sentence |
| **Ctrl+Alt+Shift+B** | Select the block: the run of lines between blank lines |
| **Ctrl+Shift+X** | Grow the selection outwards a step |
| **Ctrl+Alt+Shift+X** | Shrink it back in a step |
| **Ctrl+Shift+A** | Clear the selection, staying where you are |
| **Ctrl+A** | Select everything |

You do not need to find where any of these start. Just put the cursor
somewhere inside.

Growing goes word, line, sentence, paragraph, block, then the whole document,
and tells you which one it took each time. Shrinking goes back the other way.
So if you press **Ctrl+Shift+X** once too often, **Ctrl+Alt+Shift+X** puts it
right.

### Marks: where you were a moment ago

A mark is lighter than a bookmark. A bookmark is a place you mean to keep. A
mark is where you were standing before you went off to check something.

| Key | What it does |
|---|---|
| **Ctrl+Shift+M** | Set a mark here |
| **Ctrl+M** | Go back to the last mark |
| **Alt+M** | List your marks and pick one |
| **Ctrl+Alt+X** | Swap between the cursor and the mark, selecting what is between |

QUILL Lite keeps your last twenty marks. Marking the same place twice only uses
one.

A mark moves with your text. Drop one on a paragraph, add three paragraphs
above it, and **Ctrl+M** still takes you to that paragraph.

Every way of reaching a mark counts as a jump, so **Alt+Left** can take you
back again, the same as after a bookmark or a Go To.

### Two more

**Ctrl+Shift+Y** reads back what is selected. Use it to check you took what you
meant to before your next key replaces it. A long selection is summarised
instead of read out in full.

**Ctrl+Alt+Q** puts a second copy of the selection right after it. If nothing
is selected, it copies the line you are on.

### The ones Windows gives you anyway

These work in QUILL Lite the same way they do everywhere else, so they have no
place on the menu:

| Key | What it does |
|---|---|
| **Shift+Home** / **Shift+End** | Select to the start / end of the line |
| **Ctrl+Shift+Home** / **Ctrl+Shift+End** | Select to the start / end of the document |
| **Shift** and an arrow | Select one character, or one line, at a time |
| **Ctrl+Shift** and Left or Right | Select a word at a time |

## Reading a selection without risking it

When you have a long selection and want to read it through, there is a small
danger. If you arrow around your document while text is selected, the next key
you type replaces all of it.

**Alt+Shift+U** opens the **Review Buffer**. It is a copy of what you selected,
in its own window, and you cannot change it. Read it as slowly as you like. When
you are done, press **Escape**. You are back where you were, and your selection
is still there.

You will also find it at **Edit > Selection > Review Buffer...**.

## Hearing what is on the clipboard

You copy something in a web page, come back to QUILL Lite, and wonder: did
that copy actually work, and what exactly did I get? You no longer have to
paste it somewhere to find out. The first four rows of **Edit > Clipboard**
(**Alt+E**, then **B**) let you hear the Windows clipboard, add to it, keep it
and empty it, without pasting a thing. QUILL has the same four, on the same
keys.

### Say Clipboard (Alt+Shift+Home)

Press **Alt+Shift+Home** and QUILL Lite reads you what is on the clipboard.
Press it again quickly, within half a second, and it does more. Every press is
answered straight away, so you never wait to find out whether a second press
is coming.

- **Once:** you hear it. Short text is read in full. A long piece is read up
  to its first 2,000 characters, and then you hear how much is left: "and
  4,312 more characters. Press three times quickly to read it all."
- **Twice:** you hear it spelled, letter by letter. Capital letters are said
  as "cap". It is the way to check a web address, a code or a name before you
  type it into a form. Spelling stops after the first 200 characters.
- **Three times:** a small window opens, titled **Clipboard**, with all of it
  inside. Read it line by line with the arrow keys; nothing you do there
  changes the clipboard. Press **Escape** and you are back in your document,
  where you were.

When there is nothing to read, it says so plainly:

- Nothing copied: "The clipboard is empty".
- A picture, or anything else that is not text: "The clipboard holds something
  that is not text, such as a picture".
- Files you copied in File Explorer: how many, and their names, such as "2
  files on the clipboard: report.docx, notes.txt". After ten names you hear
  how many more there are. Press twice to hear each file's full path, and
  three times to see the paths in the window, one to a line.

### Append Selection to Clipboard (Alt+Shift+End)

Copying throws away whatever was on the clipboard before. Sometimes you want
to add to it instead. Select the next piece and press **Alt+Shift+End**. It
goes on the end of the clipboard's text, on a new line, and you hear where
things stand: "Appended 5 characters to the clipboard, which now holds 11
characters."

- No blank line is put between the pieces.
- If the clipboard was empty, it now holds just your selection.
- If nothing is selected, you hear "Select text first to append it to the
  clipboard", and the clipboard is left alone.
- If the clipboard held files, your selection replaces them.

Gather a name from here, an address from further down and a phone number from
the end, then paste the lot with **Ctrl+V**, here or in any other program.

The collector, further down this chapter, does something similar inside QUILL
Lite. The difference is that Append Selection to Clipboard builds up the real
Windows clipboard, so you can paste the result anywhere.

### Save Clipboard to File and Clear Clipboard

These two have no key. You reach them from the menu.

- **Edit > Clipboard > Save Clipboard to File...** (**Alt+E**, **B**, **F**)
  saves the clipboard's text in a file of its own, without making a new
  document first. The Save window suggests a name made from the date and time,
  such as "clipboard 2026-11-06 1405.txt". Keep it or type your own, and press
  **Enter**. It is saved as UTF-8 text, written safely so a full disk cannot
  leave half a file behind, and you hear "Saved 1,204 characters to clipboard
  2026-11-06 1405.txt". If the clipboard holds files, you hear "The clipboard
  holds files, not text, so there is nothing to save".
- **Edit > Clipboard > Clear Clipboard** (**Alt+E**, **B**, **B**) empties the
  Windows clipboard, for every program. You hear "Cleared the clipboard", or
  "The clipboard was already empty". Do it after you copy a password, so the
  next paste, wherever it is, cannot put it somewhere it should not go.

### Paste Copied Files

Copy a file in File Explorer, come back to QUILL Lite and press **Ctrl+V**, and
nothing useful happens. **Edit > Clipboard > Paste Copied Files...** asks what you
meant (**Alt+E**, **B**, **D**). A small window says how many files you copied and
names them, then offers two choices:

- **Each file's text** puts in what each file says, read the way QUILL Lite
  opens it, so a Word document or a PDF comes in as its words. Two files are
  separated by a blank line.
- **Each file's full path** puts in one path per line.

Arrow to the one you want and press **Enter**; **Escape** pastes nothing. It
goes in at your cursor, over anything selected, and one **Ctrl+Z** takes it
back. A file over 5 MB, a folder, or anything that is not text, such as a
picture, is left out, and you hear which and why: "Pasted the text of 2 files.
Not pasted: photo.png is not a text file".

Why no keys for these three? When they were added there was no key left that
was free in both QUILL Lite and QUILL, and they are things you do now and
then. Clear
Clipboard has a second reason: a key you could press by accident would throw
away what you had just copied. If you want one anyway, the Keyboard Manager
(**Ctrl+Alt+Shift+Space**) can give it a key.

## Copying and pasting more than one thing

The Windows clipboard holds one thing at a time. QUILL Lite gives you three
more places to keep things, all in **Edit > Clipboard**.

### The copy tray: twelve numbered slots

The copy tray holds twelve things, each in its own numbered slot. They stay
there even after you close QUILL Lite.

- **Ctrl+Alt+Y** copies what you selected into the next free slot.
- **Alt+Shift+Y** lets you choose the slot yourself. Each slot in the list says
  what is in it now, so you never overwrite something without hearing it first.
  Picking your own number makes it easier to remember later.
- **Ctrl+Alt+V** pastes from any slot, even an hour later.
- **Ctrl+Alt+Shift+Y** empties the tray.

### The collector: gather now, paste once

The copy tray has twelve numbered slots for things you want to keep. The
**collector** is for something different: you are reading along and want to
pick up several pieces as you go, without deciding where each one goes.

1. Select a piece of text and press **Alt+Shift+C** (**Edit > Clipboard >
   Collect Selection**). It is added to the pile. Do this as often as you like.
   Each piece goes on the end, and nothing is replaced.
2. When you are ready, move to where you want it all and use **Paste Everything
   Collected** (**Ctrl+Alt+Shift+G**). The whole pile goes in, in the order you
   collected it.
3. When you are done, press **Ctrl+Alt+Shift+C** (**Clear the Collector**) to
   empty it.

If you used an older version, Collect Selection used to be on Alt+Shift+S, and
before that on Ctrl+Alt+G. Alt+Shift+S is now the clipboard collector, below,
the same key as in QUILL. Ctrl+Alt+G moved because Google Drive for desktop
takes that key for itself. If you find a
key that does nothing, the Keyboard Manager can tell you when another program
has taken it.

### The clipboard collector: copy anywhere, it lands here

Sometimes the pieces you want are not in QUILL Lite at all. They are in a web
page, an email, a PDF or a terminal. The **clipboard collector** turns a QUILL
Lite window into a place where everything you copy ends up, whichever program
you copy it in. It is the same collector QUILL has, and it works the same way.

1. Open the window you want to collect into. A new, empty one is a good choice.
2. Press **Alt+Shift+S** (**Edit > Clipboard > Clipboard Collector**). You hear
   "Clipboard collector on; anything you copy, in any program, appends to this
   document."
3. Go and work wherever you like. Each time you copy text, in any program, it
   is added to the end of that window, with a short line of dashes between
   pieces. If the window already has a file name, it is saved straight away
   and you hear "Collected and saved." If it has never been saved, you hear
   "Collected clipboard text." Copying the same thing twice in a row adds it
   only once.
4. Press **Alt+Shift+S** again in that window to stop. You hear "Clipboard
   collector off."

A few things worth knowing:

- **It saves a named window for you.** After each new piece, a window that
  already has a file name is saved quietly. An untitled window is never saved
  and no Save As window ever opens: it is marked as changed, and it reaches the
  disk when you save it. If a save cannot happen, for example the disk is full,
  another program has changed the file, or the file's encoding cannot hold a
  character you copied, you hear "Collected, but not saved" and the reason, and
  collecting carries on; save it yourself to decide. To have collected text
  wait for you to save, clear **Save after every clip the clipboard collector
  adds** (**Alt+Y**) in **Preferences**. QUILL has the same setting.
- **One window at a time.** Turn the collector on in a second window and it
  moves there, and tells you so. **Edit > Clipboard > Clipboard Collector** has
  a check mark in the window that is collecting.
- **It stops when that window closes.**
- **It only takes text.** Pictures and files on the clipboard are left alone.
  A read-only window never collects.
- **Each piece can be undone.** **Ctrl+Z** takes back the last piece collected.

### The clip library: things you want to keep

Select something and press **Ctrl+Alt+M** to keep it in your clip library.
**Ctrl+Alt+Shift+M** opens the list so you can paste one back.

The library can also fill itself. In Preferences, check **Keep everything I copy
in the clip library**. From then on, every copy and every cut you make in a
QUILL Lite document is saved there, up to the last two hundred. It only sees
what you copy in QUILL Lite, never in other programs.

It starts switched off, and here is why you might leave it that way: the
library is a file on your computer. If you ever copy a password, it will be in
there too.

### Two more handy keys

- **Ctrl+Shift+V** pastes text without its formatting. Use it when something
  copied from a web page arrives with its own fonts and colours.
- **Ctrl+F8** copies the whole document. You could press Select All and then
  Copy, but that leaves everything selected, and the next key you type would
  replace it all. Ctrl+F8 copies without selecting anything.

## Working on lines

**Edit > Lines** holds everything you can do to whole lines. Most of these work
on the line your cursor is on, so you do not need to select anything first.

### Moving, copying and joining lines

- **Move Line Up** (**Ctrl+Shift+Up**) and **Move Line Down**
  (**Ctrl+Shift+Down**) move the current line past the one next to it. It is
  much quicker than cutting and pasting, and your cursor goes with the line.
- **Duplicate Line** (**Ctrl+D**) makes a copy of the line just below it.
- **Join Lines** (**Ctrl+Alt+Shift+J**) pulls the next line up onto the end of
  this one.

### Deleting lines

- **Delete Line** (**Ctrl+Shift+Delete**) removes the whole line.
- **Delete to Start of Line** (**Ctrl+Shift+Backspace**) removes everything
  before the cursor on this line.
- **Delete to End of Line** (**Ctrl+Alt+Shift+Delete**) removes everything after
  the cursor on this line.
- **Delete Paragraph** (**Ctrl+Alt+Shift+Backspace**) removes the whole
  paragraph.

Each one tells you what it did. If there was nothing to do, it says that too,
for example "Already the first line", so you are never left wondering.

### Putting lines in order, and tidying them up

These work on what you have selected. If nothing is selected, they work on the
whole document.

To change the order:

- **Sort Lines A to Z** (**Ctrl+Alt+S**), or **Sort Lines Z to A**
  (**Ctrl+Alt+Shift+S**).
- **Reverse Lines** (**Alt+Shift+Z**) turns the list upside down.
- **Number Lines** (**Alt+Shift+N**) puts a number in front of each line.

To clean up:

- **Remove Every Blank Line** (**Ctrl+Alt+K**) removes every empty line,
  including the ones between your paragraphs. A line with only spaces on it
  counts as empty. This is great for text from a web page that arrives
  double-spaced, but you probably do not want it on a letter.
- **Remove Duplicate Lines** (**Ctrl+Alt+D**) keeps one copy of each line.
- **Trim Trailing Spaces** (**Ctrl+Alt+R**) removes spaces at the ends of lines.
  It was Ctrl+Alt+T until version 2.0.0; that key is now Insert Table, as it
  is in QUILL.
- **Tidy Whitespace** (**Ctrl+Alt+Shift+T**) shrinks runs of spaces and tabs,
  the kind that often come along with pasted text.

If you also use QUILL, it has these same commands, plus one more called **Trim
Blank Lines at the Ends**. QUILL Lite has just the one blank line command.

Each of these is a single undo. One press of **Ctrl+Z** puts the whole sort
back, not one line at a time.

### Quoting, wrapping, and throwing lines away

These also work on what you have selected, or on the whole document if nothing
is selected.

- **Quote Lines** (**Ctrl+Shift+Q**) puts `> ` in front of each line, the way an
  email reply does. **Remove Quote Marks** (**Alt+Shift+.**, Alt, Shift and the
  period) takes them off again.
- **Hard Wrap Lines...** (**Alt+Shift+W**) asks for a width, then rearranges the
  lines so none is longer than that. It keeps your paragraphs apart and never
  breaks a word. This really changes your file. **View > Word Wrap** is
  different: it only changes how the lines are shown.
- **Delete Lines Containing** (**Alt+Shift+X**) asks for some text, then
  removes every line that has it. The text is matched exactly as you type it.
  You hear how many lines went, and one **Ctrl+Z** brings them all back. This
  is a big help when you are trimming a long log file by ear.

### Commenting lines out

**Toggle Line Comment** (**Ctrl+/**) turns the selected lines into comments.
Press it again to turn them back. It says how many lines it changed.

QUILL Lite picks the comment mark from the file's name:

- `# ` in a `.py`, `.yml`, `.ini` or `.conf` file
- `-- ` in a `.sql` file
- `<!-- -->` in HTML and Markdown
- `// ` in anything else

QUILL uses the same marks, so a file commented in one can be uncommented in the
other. A document you have not saved yet gets `// `. Once you save it with its
proper name, the right mark is used from then on.

### Tabs or spaces

**Tools > Indenting** has **Convert to Spaces** (**Alt+F11**) and **Convert to
Tabs** (**Alt+F12**). They change only the indentation at the start of each
line, and count four spaces to a tab. This is a common change to make to a file
somebody else wrote.

### Changing case

**Tools > Change Case** has five choices:

- **UPPERCASE** (**Ctrl+Shift+U**)
- **lowercase** (**Ctrl+Shift+K**)
- **Title Case** (**Ctrl+Shift+T**)
- **Sentence case** (**Ctrl+Alt+Shift+U**) puts a capital at the start and makes
  the rest small. Good for a heading that was typed in capitals.
- **Invert Case** (**Ctrl+Alt+Shift+N**) swaps every letter. Good for a sentence
  typed with Caps Lock on by mistake.

They work on what you have selected. **If nothing is selected, they change the
word your cursor is in**, the same as Shift+F3 in Word. That keeps a slip of the
finger small: a whole document in the wrong case sounds just the same when it is
read aloud, so you might not notice.

### Getting deleted text back somewhere else

**Restore Deleted Text** (**Ctrl+Alt+Shift+Z**) puts something you deleted back
**where your cursor is now**. QUILL Lite remembers your last three deletions. If
the one you want is not the most recent, you get a short list with a preview of
each.

This is different from undo. **Ctrl+Z** puts text back where it came from. This
puts it where you are. So you can delete a paragraph, move down, and restore it
there. That is a way to move text without using the clipboard, so whatever you
had copied is still waiting for you.

It only remembers deletions made with the delete commands above, not every
letter you backspaced over.

### Indenting

**Tools > Indenting** has **Indent** (**Ctrl+]**) and **Outdent** (**Ctrl+[**).
They move every line your selection touches, or just the line you are on if
nothing is selected. You hear how many lines moved. If you edit code or
settings files, you will use these a lot.

#### Asking how deep a line is

**Describe Indent Depth** (**Ctrl+Alt+Shift+V**) tells you how far the current
line is indented: "4 spaces", "1 tab", "1 tab, 3 spaces", or "No indentation".

Your screen reader reads the words on a line, but not the spaces and tabs in
front of them. In a Python file, a YAML file or a nested list, that indentation
matters a lot. This command lets you hear it.

It also tells you when a line uses a different kind of space from the lines
around it, for example a tab where the others use spaces. You cannot hear that
difference any other way, and in a Python file it stops the program running.

#### Making Tab indent instead

When you start, the **Tab** key types a tab character, the way it does in
Notepad. You can see this in **View > Tab Key Inserts a Tab Character**, which
is checked. Press **Ctrl+Alt+Shift+I** to clear the check mark, and Tab indents the
whole line instead, telling you the new depth as it goes. That is usually what
you want for code.

**Shift+Tab** outdents in either mode, so one key always takes back a tab you
typed by accident. The **Tab Mode** part of the status bar tells you which mode
is on.

### Snippets (Ctrl+Alt+Shift+Home)

**Ctrl+Alt+Shift+Home** opens **Snippets...**. (It was
**Alt+Shift+I** before version 2.0, which is now Add Inline Note, the same as
in QUILL.) It lists every abbreviation you have,
the ones you use most at the top, with a preview of what each one writes. Pick
one and press **Enter**, and it goes in at your cursor.

Some abbreviations have blanks to fill in. Write `${field:Name}` (or
`${input:Name}`, the way QUILL's snippets spell it) where a name should go,
`${field:Name=Sam}` to offer a starting value, or `${choice:Reminder|first|second}`
for a list to pick from. Before the text goes in, a small form asks for each
one in turn: Tab between them, **Enter** on the last one to put it in,
**Escape** to put nothing in. The same blank used twice is asked once. This
works when you type the short form too, and it is the same form QUILL and
Quill Inkwell show, so one list of abbreviations behaves the same in all three.
[QUILL's guide has more on fields](https://www.quillforall.org/docs/quill-guide-04-writing-and-editing.html).

This is the easy way in when you cannot remember a short form. The six you use
every day you will type from memory. The one you set up months ago, you can find
here. Anything you add in **Manage Abbreviations...** shows up in this list too.

### Abbreviations

An abbreviation is a short form that grows into a longer one. Type the short
form, press **Space**, and the long text appears. It is great for your address,
how you sign off, or anything else you type often.

- **Ctrl+Alt+A** opens **Manage Abbreviations...**, where you add and change
  them.
- **Alt+Shift+A** turns expanding on and off. **Tools > Expand Abbreviations**
  shows a check mark when it is on.

That on and off key is there for the moment an abbreviation has just grown into
something you did not want. You can turn it off right away, without looking for
a setting. It is the same switch as the Abbreviations box in Customize Features.

If you also use QUILL or Quill Inkwell, there is a switch in Preferences that
lets all three share one list of abbreviations.

Your own AutoCorrect corrections (Chapter 11, Correcting misspellings as you
type) are kept in this same list, under the category **AutoCorrect**. You will
see them in Manage Abbreviations if you choose that category. They are not
abbreviations, though: they never expand just because **Expand Abbreviations**
is on, and they are not in **Snippets**.

### Word Prediction (Ctrl+.)

Halfway through a long word, press **Ctrl+.** (Edit > Word Prediction...).
A short list of suggestions opens, and you hear how many there are and the
first one, such as "8 prediction(s). elephant". Your focus stays in the
document.

- **Up** and **Down** move through the list and say each suggestion.
- **Enter** or **Tab** puts the one you've chosen in place of the part of the
  word you typed, and nothing else.
- **Escape** closes the list and leaves your text exactly as it was.
- Keep typing with the list open and it narrows to match.

The suggestions come from the spelling dictionary and the words already in
your document, plus Markdown and HTML tags where they fit. It's QUILL's list
on QUILL's key. QUILL can also open it on its own as you type; QUILL Lite
only opens it when you ask.

In a code file, such as a `.py`, `.js` or `.html` file, the list offers the
file's own names instead of dictionary words, nearest first, and says what
kind each one is: "8 suggestions. count_words, function". In HTML, CSS,
JSON, JavaScript, TypeScript and Python, the language server for that
language answers first, so `console.lo` offers `log`, said as "log, method". When there's room,
it adds names from the other code files in the same project folder, which
QUILL Lite reads in the background the first time you ask.

## Undo, and getting text back

| Key | What it does |
|---|---|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Ctrl+Alt+Shift+Z** | **Restore Deleted Text**: put a recent deletion back **where the cursor is now** |

You already know the first two. The third one is worth learning. **Ctrl+Z puts
deleted text back where it came from, and Restore Deleted Text puts it where
you are standing.** So a deletion is never final, even after you have typed
more.

### Big changes are one undo

When a command changes a lot at once, one **Ctrl+Z** takes the whole change
back. That includes sorting nine hundred lines, applying a heading, moving a
whole section, going back to an earlier version of the file, or tidying all the
spaces. One key did it, so one key undoes it.

## What you learned, and where to go next

You can start a selection with **F8** and walk to the end of it, use Extend
Selection Mode, take a whole word, line or paragraph in one key, and grow or
shrink what you have. Marks take you back to where you were a moment ago, and
the Review Buffer on **Alt+Shift+U** lets you read a selection safely.

The copy tray holds twelve numbered things, the collector gathers several
pieces to paste together, and the clip library keeps what you want to keep.
**Ctrl+Shift+V** pastes plain text, and **Ctrl+F8** copies the whole document
without selecting it. Edit > Lines moves, sorts, tidies, quotes, wraps and
deletes lines, Tools > Indenting and Tools > Change Case look after spacing
and capitals, and snippets and abbreviations save you typing. Every big change
is one **Ctrl+Z**, and Restore Deleted Text puts a deletion back wherever you
are now.

The tutorial *Selecting more than a few words* walks you through the
selecting keys, and finishes with the Review Buffer.

Next, Chapter 6, Formatting, headings and the Insert menu, shows you what to
do with text once it is in.

---

- Previous: [Chapter 4: Moving around a document](lite-guide-04-moving-around-a-document.html)
- Next: [Chapter 6: Formatting, headings and the Insert menu](lite-guide-06-formatting-headings-and-the-insert-menu.html)
- [Contents](../userguide.html)
