# QuillLite — User Guide

QuillLite is a text editor. It opens a file, lets you change it, and saves it
back exactly as it found it.

If you have used Notepad or WordPad, almost every key you already know works
here. Where QuillLite does something different, this guide says so, and says
why.

You do not need to read this guide to use QuillLite. Start it, type, press
**Ctrl+S**. Come back here when you want more.

---

## The first minute

Start QuillLite and you get one window with one empty document in it, called
**1: Untitled**. Type. Press **Ctrl+S** when you want to keep it.

That is the whole thing. The rest of this guide is optional.

Three keys are worth knowing straight away:

- **F1** tells you where you are. Press it anywhere — in your document, on a
  button, in any window — and QuillLite says what that window is for and what
  the thing you are on does.
- **F6** takes you to the status bar, which is where the useful facts live.
  Arrow along it, press **Escape** to come back.
- **Ctrl+F1** lists every key QuillLite has.

---

## Your documents are numbered

QuillLite opens your documents **inside one window**, and numbers them. Your
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
**not** appear in Alt+Tab. Alt+Tab shows you *QuillLite*, once. The four ways
above are how you move between documents. We would rather tell you that here
than have you hunting for a document you thought you had lost.

**Ctrl+N** makes a new document. **Ctrl+W** closes the one you are in.
**Ctrl+Q** closes everything, asking about anything you have not saved.

### Opening a second QuillLite

If you open a file from your file manager while QuillLite is already running, it
opens in the QuillLite you already have. That is what keeps the numbering
meaningful.

If you really do want two separate QuillLite windows — one per monitor, say —
start it with the extra option `--new-instance`.

---

## Two kinds of document

Every document is one of two kinds, and the title bar tells you which.

**Plain text** is like Notepad. One font, no formatting. Text you paste in
arrives as plain text. This is what you want for notes, lists, and any file that
another program is going to read.

**Rich text** is like WordPad. Bold, italic, headings, alignment, bullet points,
line spacing. It saves as a Rich Text file, which Word and WordPad both open.

QuillLite chooses the kind from the file's name. Rich Text files open as rich
text; everything else opens as plain. **Ctrl+Shift+M** switches the document you
are in. Going from rich to plain throws the formatting away, so it asks first.

---

## Saving

**Ctrl+S** saves. **Ctrl+Shift+S** saves under a new name.

QuillLite makes you one promise here: **open a file, change nothing, save it,
and it is exactly the file you started with.** Nothing is quietly tidied up
behind your back.

To keep that promise it remembers three things about every file it opens, and
puts them back the same way:

- **How the text is stored** — different files store letters and accents
  differently, and QuillLite keeps whichever way yours already used.
- **How the lines end** — files made on Windows and files made on other systems
  mark the end of a line differently, and QuillLite does not change yours.
- **Whether the file ended with a blank line** — if it did not, it will not
  suddenly start.

You can see both of the first two in the status bar (**F6**), and you can
deliberately change them from **Tools ▸ File Encoding and Line Endings**
(**Ctrl+Alt+E**) when you actually want to — for instance when somebody needs a
copy of an old file in a newer format. The change takes effect the next time you
save.

### If something goes wrong

While a document has changes you have not saved, QuillLite keeps a copy of it
aside, about once a minute. That copy sits **beside** your file and never on top
of it.

If QuillLite or your computer stops unexpectedly, that work is offered back to
you the next time you start, in its own document.

Save it, or close normally, and the copy is deleted. So there is never anything
in there except work you actually need.

### Going back to an earlier version

There is a separate **timestamped backups** option (**View ▸ Customize
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

Until version 1.0 QuillLite wrote these files and gave you no way to read one:
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
| **Ctrl+G** | Go to a line by number |

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

### Searching for things you cannot type

The Find and Replace windows have a **Search mode** with three settings.

**Normal** is the ordinary one: what you type is what is looked for,
punctuation and all.

**Escapes** lets you write the characters there is no key for. `\t` is a tab,
`\n` a line break, `\u2014` an em dash, and `\N{NO-BREAK SPACE}` is exactly
what it says. This is the companion to **Describe Character**: that tells you
which invisible character you are standing on, and this is how you then find
every other one like it, or replace them all with an ordinary space.

**Regular expression** treats what you typed as a search pattern -- `.` matches
any character, `*` repeats the thing before it, `[abc]` matches any one of
those, `^` and `$` are the start and end of a line. If the pattern is not valid,
QuillLite says which character is wrong rather than quietly finding nothing: a
search that failed and a search that found nothing are different problems, and
only one of them is fixed by retyping.

Whole word works with all three. In regular expression mode it wraps the whole
pattern, so `cat|dog` means "the word cat or the word dog", not "the word cat,
or dog anywhere".

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
  folder; the list lives in QuillLite's own settings folder, keyed by the file's
  location. If the file has been shortened by something else since you last had
  it open, bookmarks past the new end are pulled back to the end rather than
  sending you nowhere.

You can turn all of this off with the rest of bookmarks in **View ▸ Customize
Features**, and then nothing is written at all.

### Going back where you came from

| Key | What it does |
|---|---|
| **Alt+Left** | Go back to where you were before the last jump |
| **Alt+Right** | Go forward again |

They are in the **Edit** menu rather than under Navigate, and deliberately: the
Navigate menu is headings and bookmarks, both of which you can switch off, and
these two belong to neither. They are always there.

Every jump QuillLite makes is remembered: going to a line, following a heading,
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
| **Ctrl+Alt+F8** | Turn selecting-as-you-move on or off without moving |
| **Ctrl+Shift+F8** | Put back the selection you just had |
| **Alt+Shift+F8** | Go to the beginning of what is selected |

**Ctrl+Shift+F8** is worth remembering for the moment an arrow key has just
thrown away a selection that took six keystrokes to build.

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
| **Ctrl+Alt+Shift+K** | Set a mark here |
| **Ctrl+M** | Go back to the last mark |
| **Alt+M** | List your marks and pick one |
| **Ctrl+Alt+X** | Swap between the cursor and the mark, selecting what is between |

### Two more

**Ctrl+Shift+Y** reads back what is currently selected. There is no glance that
confirms you took what you meant to, and the next key you press might replace
it. Long selections are summarised rather than read out in full.

**Ctrl+Alt+Q** puts a second copy of the selection right after the first — or
duplicates the line you are on if nothing is selected.

### The ones Windows gives you anyway

These work in QuillLite as they do everywhere, and have no menu row because they
need none:

| **Shift+Home** / **Shift+End** | Select to the start / end of the line |
| **Ctrl+Shift+Home** / **Ctrl+Shift+End** | Select to the start / end of the document |

---

## Formatting

These are WordPad's keys, deliberately unchanged. They work in rich text
documents.

| Key | What it does |
|---|---|
| **Ctrl+B**, **Ctrl+I**, **Ctrl+U** | Bold, italic, underline |
| **Ctrl+Shift+>** / **Ctrl+Shift+<** | Bigger / smaller text |
| **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J** | Left, centre, right, justify |
| **Ctrl+Shift+L** | Bullet points |
| **Ctrl+1**, **Ctrl+5**, **Ctrl+2** | Single, one-and-a-half, double spacing |
| **Ctrl+Alt+1** to **Ctrl+Alt+4** | Heading 1 to 4 |
| **Ctrl+Alt+0** | Back to ordinary text |
| **Ctrl+Shift+D** | Describe the formatting where the cursor is |

A heading is bold text at a larger size — 20, 16, 14 and 12 point for levels 1
to 4, with ordinary text at 11 point. These are the same sizes QUILL for All
uses, chosen so that a document you save here still reads as having headings
when somebody opens it in Word.

**Ctrl+Shift+D** is the one worth remembering. It tells you what you are
standing in — "Arial, 16 point, heading 2, bold" — which is the question a
formatted document raises and that nothing else can answer for you.

### Moving between headings

| Key | What it does |
|---|---|
| **Ctrl+Alt+H** / **Ctrl+Alt+Shift+H** | Next / previous heading |
| **Ctrl+Alt+L** | The list of every heading |

### Rearranging them — Format ▸ Structure

| Key | What it does |
|---|---|
| **Alt+Shift+Left** | Promote heading — one level shallower |
| **Alt+Shift+Right** | Demote heading — one level deeper |
| **Alt+Shift+Up** | Move this whole section up, past the one before it |
| **Alt+Shift+Down** | Move this whole section down, past the one after it |

Until now QuillLite could make headings and walk between them but never move
them about, which left cut-and-paste as the only way to reorganise a document —
and that is the operation it is worst at. Moving a section by hand means
selecting from one heading to exactly the start of the next: a boundary you
cannot see, that you have to find by ear, and that takes your place in the
document with it when you get it wrong. **Alt+Shift+Up** does the same thing in
one keystroke and tells you it happened.

"Section" means the heading you are in plus everything under it, down to the
next heading at the same level or higher. Moving a Heading 2 takes its Heading 3s
with it.

Two things to know:

- **Promoting a Heading 1 leaves it a Heading 1.** It does not turn into
  ordinary text — losing a heading altogether is not what Alt+Shift+Left is for,
  and it would quietly drop the paragraph out of your headings list.
- **Moving sections works in plain text documents**, where headings are Markdown
  `#` lines. In a rich text document a heading is a font size rather than
  something written in the text, and there is nothing there to move; QuillLite
  says so rather than doing nothing. Promoting and demoting work in both.

These are QUILL for All's own four keys, so they behave the same in both.

---

## Spell check

WordPad never had a spell checker. Notepad only got one recently. QuillLite has
one, and it is the same one QUILL for All uses.

**F7 checks the whole document.** It walks you through it one word at a time
with suggestions you can arrow through. For each word you can change it, change
every one like it, skip it, or add it to your dictionary so it is never
questioned again.

| Key | What it does |
|---|---|
| **F7** | Check the whole document |
| **Shift+F7** | Suggestions for the word you are on |
| **Ctrl+F7** / **Ctrl+Shift+F7** | Go to the next / previous mistake |
| **Alt+F7** | Add this word to your dictionary |
| **Ctrl+Alt+F7** | Turn checking-as-you-type on or off here |

**Ctrl+F7** selects the word it lands on, so your screen reader reads it to you
when you get there.

### When it stays quiet

Some files are not writing at all. They hold settings and instructions that
programs read, and they are full of made-up words, abbreviations and names that
no dictionary contains. Checking one of those as you type would give you a
constant stream of warnings that are every one of them wrong.

So **QuillLite does not check those files as you type.** It recognises them by
the kind of file they are, and it tells you once when you open one, so you are
never left wondering whether something is broken.

If you want checking in one anyway, press **Ctrl+Alt+F7**. It changes only the
document you are in — a letter and a settings file open at the same time can
quite happily disagree about this. The **Spelling** menu shows a tick beside
**Check While Typing** so you can always see which way it is set.

**F7 always works, in every file.** Staying quiet is only about what happens
when you have not asked. If you ask for a check, you get one.

### Your dictionary

Words you teach QuillLite are yours, kept in QuillLite's own folder. If you also
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

**F6** takes you into it. The arrow keys and **Home**/**End** move along it,
**Enter** acts on the part you are on, and **Escape** puts you back in your
document. Each part says its own name and value.

| Part | What it tells you | Enter does |
|---|---|---|
| **Status Message** | The last thing QuillLite told you, so speech you missed can be heard again | repeats it |
| **Position** | Which line and column you are on, out of how many lines | Go to a line |
| **Word Count** | How many words the document has | repeats it |
| **Character Count** | How many characters, spaces included | repeats it |
| **Selection** | How much is selected, or "No selection" | repeats it |
| **Typing Mode** | Whether typing inserts or overwrites | switches between them |
| **Tab Mode** | Whether the Tab key types a tab or indents the line | switches between them |
| **Format** | Plain text or rich text | switches between them |
| **Heading** | Which heading you are inside | lists every heading |
| **Encoding** | How this file stores its letters and accents | change it |
| **Line Endings** | How this file marks the end of a line | change it |
| **Saved State** | Whether you have unsaved changes | saves |

Five of these are worth pointing out.

**Typing Mode** is the one you cannot find out any other way. Every Windows
editor has an overwrite mode, where what you type replaces the letters already
there instead of pushing them along, and none of them will tell you which mode
you are in — you find out by typing over a sentence you meant to keep. Press
**Ctrl+Alt+Shift+W** to switch, or **Enter** on this part of the status bar.

The **Insert** key switches it too, because the editing control answers that key
whether QuillLite asks it to or not. QuillLite does not claim the key — it is
NVDA's and JAWS's own modifier and taking it would fight your screen reader —
but it does watch for it, so this part of the status bar stays right either way.

**Tab Mode** is the same idea. QuillLite starts where Notepad does: the **Tab**
key types a tab character. Switch it with **Ctrl+Alt+Shift+I** and Tab indents
the whole line instead, which is what QUILL does by default and what you
probably want when the file is code. **Shift+Tab** outdents either way, so a tab
you did not mean to type can always be taken back without switching modes first.

**Encoding** and **Line Endings** are the two things that decide whether your
file opens properly on somebody else's computer, and almost no other editor
shows them at all. You will rarely need to change them — but when a file arrives
looking like nonsense, this is where the answer is.

**Status Message** exists because speech is gone the moment it is spoken. If you
missed something QuillLite said, this is where you go to read it again.

---

## Copying and pasting more than one thing

The Windows clipboard holds one thing at a time. QuillLite gives you three ways
around that, in the **Clipboard** menu.

**The copy tray** is twelve numbered slots that survive closing the app. Copy
into a slot with **Ctrl+Alt+Y**, and paste from any of them an hour later with
**Ctrl+Alt+V**. **Ctrl+Alt+Shift+Y** empties it.

**The collector** gathers things up. Each **Ctrl+Alt+G** adds what you have
selected to one growing pile, and **Ctrl+Alt+Shift+G** pastes the whole pile.
This is what you want when you are pulling five quotes out of a long document.
**Ctrl+Alt+Shift+C** empties the pile.

**The clip library** happens by itself — a rolling history of what you have
copied, whether or not you decided at the time that it mattered. **Ctrl+Alt+M**
keeps the current clip deliberately, and **Ctrl+Alt+Shift+M** opens the list.

And **Ctrl+Shift+V** pastes text with none of its formatting, which is what you
want when something copied from a web page arrives wearing its own fonts and
colours.

---

## Tools

The **Tools** menu is for things you need to *do* to text. Each one works on
what you have selected, or on the whole document if you have not selected
anything.

Sort lines (**Ctrl+Alt+S**, or **Ctrl+Alt+Shift+S** for Z to A), remove blank
lines, remove duplicate lines, trim trailing spaces, and change text to
UPPERCASE (**Ctrl+Shift+U**), lowercase (**Ctrl+Shift+K**) or Title Case
(**Ctrl+Shift+G**).

Two more case changes sit beside those. **Sentence case**
(**Ctrl+Alt+Shift+U**) puts a capital at the start and lowers the rest, which is
what a heading typed in shouting needs. **Invert Case**
(**Ctrl+Alt+Shift+N**) swaps every letter, which is the cure for a sentence
typed with Caps Lock on.

Under **Tools ▸ More Line Work** there are three more: **Reverse Lines**
(**Alt+Shift+Z**), **Tidy Whitespace** (**Ctrl+Alt+Shift+T**), which collapses
the runs of spaces and tabs that arrive with pasted-in text, and **Number
Lines** (**Alt+Shift+N**).

Each one counts as a single undo, so **Ctrl+Z** takes back the whole sort rather
than putting back one line at a time.

### Working on one line at a time

The tools above rewrite a whole selection. These work on the line the cursor is
already on, which is usually the one you want.

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

### Getting deleted text back somewhere else

**Restore Deleted Text** (**Ctrl+Alt+Shift+Z**) puts your most recent deletion back
**at the cursor**, wherever the cursor now is.

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

These matter more here than they look. QuillLite already goes quiet about
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

### Abbreviations

Type a short form, press space, and get the long one. Useful for an address, a
sign off, or anything you type often and would rather not spell out every time.

**Ctrl+Alt+A** manages your list. It is QuillLite's own list to begin with; if
you also use QUILL for All or Quill Inkwell, Preferences has a switch that makes
all three share one list.

---

## Finding a command

**Ctrl+Shift+P** opens a search box for commands. Type part of what you want —
"sort", "bookmark", "print" — and pick it from the list. You do not have to
remember which menu it lives in.

Each command shows its keyboard shortcut beside it, which is a comfortable way
to learn the keys over time.

---

## Making QuillLite smaller (or larger)

**View ▸ Customize Features** (**Ctrl+Alt+Shift+F**) lets you switch whole parts
of QuillLite off. Turning something off removes it from the menus **and**
unhooks its keys, so it is properly gone rather than just hidden.

That is how QuillLite stays small without being poor: you take out what you do
not want, rather than learning to ignore it. Uncheck the first box and QuillLite
is essentially Notepad.

| Area | What goes | Starts |
|---|---|---|
| **Rich text and the Format menu** | Bold, headings, alignment, bullets, spacing | on |
| **Heading navigation** | Next and previous heading, the headings list | on |
| **Bookmarks** | All nine, and the list | on |
| **The Tools menu** | Sort, remove duplicates, trim, change case, file settings | on |
| **Copy Tray and the clip library** | The Clipboard menu (Paste Text Only stays) | on |
| **Printing** | Print and Page Setup | on |
| **Abbreviations** | Short forms, and the list that manages them | on |
| **Spell check** | The Spelling menu, and checking as you type | on |
| **The Selection submenu** | F8 selecting, whole-structure selecting, marks | on |
| **Autocorrect while typing** | Curly quotes, long dashes, sentence capitals | **off** |
| **Timestamped backups** | A dated copy kept every time you save | **off** |
| **Go To Anything** | One box that searches everything at once | **off** |

The last three start switched off, and they sit in this same list rather than
being hidden away, because something you cannot find might as well not exist.

Autocorrect is off because curly quotes are lovely in a letter and unhelpful in
a settings file. Backups are off because they quietly fill a folder. Go To
Anything is off because the command search, the headings list and the bookmark
list already each do their own part of the job.

---

## Settings

**View ▸ Preferences** (**Ctrl+,**) has everything in one place.

Six settings live only there: what **Ctrl+N** creates, how often unsaved work is
copied aside, whether last session's documents reopen, whether spelling is
checked as you type, and whether your abbreviations and your taught words are
shared with QUILL for All.

The rest — dark mode, word wrap, the editor font — are on the **View** menu too,
where you will reach them faster.

**Dark mode is on by default.** It changes what you see and nothing else. The
colours are never written into your files, so a dark theme can never leave grey
text in a document you send somebody.

---

## Printing

**Ctrl+P** prints. **Ctrl+Alt+U** is Page Setup.

Long lines are wrapped to fit the page whatever your Word Wrap setting says,
because a printed line that runs off the edge of the paper is simply gone.

**In this version, rich formatting does not print.** Your text prints in the
editor's font, with headings marked rather than styled. We would rather tell you
that here than have you find it on paper.

---

## Speech

QuillLite talks through **NVDA or JAWS**, and nothing else. There is no built-in
voice, and that is on purpose: a second voice talking over your screen reader is
worse than silence.

It also says as little as it can. Your screen reader already announces window
titles, where your focus has moved, the names of buttons and what you have
selected. QuillLite only tells you things it alone knows — that a save happened,
that a search wrapped around, that bold went on, that four things were replaced.

Everything it says also goes into the first part of the status bar, so **F6**
will bring back a message you missed.

If you have no screen reader running, QuillLite says nothing out loud — but
every message is still there in the status bar.

---

## Where your files are kept

Your settings, recent files, copy tray and any recovered work are kept in a
QuillLite folder inside your own Windows user folder. **Help ▸ About QuillLite**
shows you the exact location.

It is deliberately **not** inside QUILL for All's folder. QuillLite is offered
as an alternative to QUILL, not as part of it, and installing or removing one
should never affect the other.

Uninstalling QuillLite does not delete that folder. Recovered work is the one
thing you might not have finished with, and an uninstaller is the worst possible
moment to discover that.

### The portable copy keeps everything on the stick

If you are running the **portable** QuillLite -- the `.zip` you unpack rather
than the installer -- then none of the above applies. Everything goes into the
`data\QuillLite` folder inside the bundle, right next to `QuillLite.exe`, and
nothing at all is written to the computer you are plugged into. That is what
portable means, and QuillLite does it from the very first launch: there is no
setting to find first.

Until version 1.0 it did not. A portable QuillLite quietly used
`%LOCALAPPDATA%\QuillLite` on the host machine instead, and said nothing about
it -- so settings did not travel with the stick, and, worse, recovered copies of
documents you had not saved were left behind on someone else's computer. If you
have been carrying a portable QuillLite, that folder is where anything you seem
to have lost will be, and it is worth deleting once you have what you want out
of it.

Delete the `data` folder from the bundle and QuillLite goes back to using this
computer's own profile -- that folder is what marks the copy as portable.

---

## What QuillLite is not

QuillLite is a companion to **QUILL for All**, not a replacement for it.

If you want artificial intelligence, dictation, document conversion, comparing
two documents, publishing or braille tools, those are QUILL, and QuillLite is
built so that it will not slowly grow into them.

Both are free, both are built for screen reader users, and they install
perfectly happily side by side.

---

## Every key, in one table

<!-- keys:start -->

Generated from the same table that builds the menus, so it cannot drift from
what is actually bound. **Ctrl+F1** shows this list inside the app.

### File

| Key | Command |
|---|---|
| **Ctrl+N** | New |
| **Ctrl+Shift+N** | New Rich Text Document |
| **Ctrl+Alt+N** | New Plain Text Document |
| **Ctrl+O** | Open... |
| **Ctrl+S** | Save |
| **Ctrl+Shift+S** | Save As... |
| **Ctrl+Alt+Shift+E** | Earlier Versions... |
| **Ctrl+Alt+U** | Page Setup... |
| **Ctrl+P** | Print... |
| **Ctrl+W** | Close Window |
| **Ctrl+Q** | Exit QuillLite |

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
| **F5** | Insert Date and Time |
| **Ctrl+Shift+C** | Describe Character |
| **Ctrl+Alt+C** | Character Details... |
| **Ctrl+F** | Find... |
| **F3** | Find Next |
| **Shift+F3** | Find Previous |
| **Ctrl+H** | Replace... |
| **Ctrl+G** | Go to Line... |
| **Alt+Left** | Go Back |
| **Alt+Right** | Go Forward |

### Edit ▸ Matches

| Key | Command |
|---|---|
| **Ctrl+Shift+F3** | All Matches... |
| **Ctrl+Alt+Shift+F3** | Count Occurrences |

### Edit ▸ Selection

| Key | Command |
|---|---|
| **F8** | Start Selection |
| **Shift+F8** | Complete Selection |
| **Ctrl+Shift+F8** | Reselect Last Selection |
| **Alt+Shift+F8** | Go to Start of Selection |
| **Ctrl+Alt+F8** | Extend Selection Mode |
| **Ctrl+Shift+W** | Select Word |
| **Ctrl+Shift+E** | Select Line |
| **Ctrl+Shift+H** | Select Paragraph |
| **Ctrl+Space** | Select Sentence |
| **Ctrl+Alt+Shift+B** | Select Block |
| **Ctrl+Shift+X** | Expand Selection |
| **Ctrl+Alt+Shift+X** | Shrink Selection |
| **Ctrl+Shift+A** | Unselect All |
| **Ctrl+Alt+Shift+K** | Set Mark |
| **Ctrl+M** | Pop Mark |
| **Alt+M** | List Marks |
| **Ctrl+Alt+X** | Exchange Cursor and Mark |
| **Ctrl+Shift+Y** | Say Selection |
| **Ctrl+Alt+Q** | Duplicate Selection |

### View

| Key | Command |
|---|---|
| **Alt+Shift+D** | Dark Mode |
| **Alt+Z** | Word Wrap |
| **Ctrl+Alt+Shift+W** | Overwrite Mode |
| **Ctrl+Alt+Shift+I** | Tab Key Inserts a Tab Character |
| **Ctrl+=** | Increase Text Size |
| **Ctrl+-** | Decrease Text Size |
| **Ctrl+0** | Reset Text Size |
| **Ctrl+Alt+F** | Editor Font... |
| **Ctrl+Alt+W** | Document Statistics |
| **F6** | Status Bar |
| **Ctrl+,** | Preferences... |
| **Ctrl+Alt+Shift+F** | Customize Features... |
| **Ctrl+Shift+P** | Command Palette... |
| **Ctrl+Alt+Shift+A** | Go To Anything... |

### Format

| Key | Command |
|---|---|
| **Ctrl+B** | Bold |
| **Ctrl+I** | Italic |
| **Ctrl+U** | Underline |
| **Ctrl+Shift+.** | Grow Font |
| **Ctrl+Shift+,** | Shrink Font |
| **Ctrl+Alt+1** | Heading 1 |
| **Ctrl+Alt+2** | Heading 2 |
| **Ctrl+Alt+3** | Heading 3 |
| **Ctrl+Alt+4** | Heading 4 |
| **Ctrl+Alt+0** | Body Text |

### Format ▸ Structure

| Key | Command |
|---|---|
| **Alt+Shift+Left** | Promote Heading |
| **Alt+Shift+Right** | Demote Heading |
| **Alt+Shift+Up** | Move Section Up |
| **Alt+Shift+Down** | Move Section Down |

### Format

| Key | Command |
|---|---|
| **Ctrl+L** | Align Left |
| **Ctrl+E** | Centre |
| **Ctrl+R** | Align Right |
| **Ctrl+J** | Justify |
| **Ctrl+Shift+L** | Bullets |
| **Ctrl+1** | Single Spacing |
| **Ctrl+5** | One and a Half Spacing |
| **Ctrl+2** | Double Spacing |
| **Ctrl+Shift+F** | Font for Selection... |
| **Ctrl+Shift+D** | Describe Formatting at Cursor |
| **Ctrl+Shift+M** | Switch Document Mode |

### Clipboard

| Key | Command |
|---|---|
| **Ctrl+Alt+Y** | Copy to Tray |
| **Ctrl+Alt+V** | Paste from Tray... |
| **Ctrl+Alt+Shift+Y** | Clear Copy Tray |
| **Ctrl+Alt+G** | Collect Selection |
| **Ctrl+Alt+Shift+G** | Paste Everything Collected |
| **Ctrl+Alt+Shift+C** | Clear the Collector |
| **Ctrl+Alt+M** | Keep Clip |
| **Ctrl+Alt+Shift+M** | Recent Clips... |

### Navigate

| Key | Command |
|---|---|
| **Ctrl+Alt+H** | Next Heading |
| **Ctrl+Alt+Shift+H** | Previous Heading |
| **Ctrl+Alt+L** | List Headings... |
| **Ctrl+Shift+B** | Set Bookmark |
| **Alt+Shift+G** | Go to Bookmark... |
| **F2** | Next Bookmark |
| **Shift+F2** | Previous Bookmark |
| **Ctrl+Alt+B** | Clear All Bookmarks |
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
| **Ctrl+Alt+S** | Sort Lines A to Z |
| **Ctrl+Alt+Shift+S** | Sort Lines Z to A |
| **Ctrl+Alt+K** | Remove Blank Lines |
| **Ctrl+Alt+D** | Remove Duplicate Lines |
| **Ctrl+Alt+T** | Trim Trailing Spaces |
| **Ctrl+Shift+Up** | Move Line Up |
| **Ctrl+Shift+Down** | Move Line Down |
| **Ctrl+D** | Duplicate Line |
| **Ctrl+Alt+Shift+J** | Join Lines |
| **Ctrl+Shift+Delete** | Delete Line |
| **Ctrl+Shift+Backspace** | Delete to Start of Line |
| **Ctrl+Alt+Shift+Delete** | Delete to End of Line |
| **Ctrl+Alt+Shift+Backspace** | Delete Paragraph |
| **Ctrl+Alt+Shift+Z** | Restore Deleted Text |
| **Ctrl+Shift+U** | UPPERCASE |
| **Ctrl+Shift+K** | lowercase |
| **Ctrl+Shift+G** | Title Case |
| **Ctrl+Alt+Shift+U** | Sentence case |
| **Ctrl+Alt+Shift+N** | Invert Case |
| **Ctrl+Alt+E** | File Encoding and Line Endings... |
| **Ctrl+Alt+A** | Manage Abbreviations... |

### Tools ▸ Indenting

| Key | Command |
|---|---|
| **Ctrl+]** | Indent |
| **Ctrl+[** | Outdent |
| **Ctrl+Alt+Shift+V** | Describe Indent Depth |

### Tools ▸ More Line Work

| Key | Command |
|---|---|
| **Alt+Shift+Z** | Reverse Lines |
| **Ctrl+Alt+Shift+T** | Tidy Whitespace |
| **Alt+Shift+N** | Number Lines |

### Spelling

| Key | Command |
|---|---|
| **F7** | Check Spelling... |
| **Shift+F7** | Spelling for This Word |
| **Ctrl+F7** | Next Misspelling |
| **Ctrl+Shift+F7** | Previous Misspelling |
| **Alt+F7** | Add Word to Dictionary |
| **Ctrl+Alt+F7** | Check While Typing |

### Window

| Key | Command |
|---|---|
| **Ctrl+Tab** | Next Window |
| **Ctrl+F6** | Next Window (MDI) |
| **Ctrl+Shift+Tab** | Previous Window |

### Help

| Key | Command |
|---|---|
| **F1** | Help for This Window |
| **Ctrl+F1** | Keyboard Shortcuts |
| **Shift+F1** | About QuillLite |

### Built per window

| Key | Command |
|---|---|
| **Alt+1** to **Alt+9** | Go to that numbered document |
| **Alt+Shift+1** to **Alt+Shift+9** | Reopen that recent file |

Two of these read differently on a keyboard than in a table: **Ctrl+Shift+>**
and **Ctrl+Shift+<** are the keys your fingers know, and they are listed above
as `Ctrl+Shift+.` and `Ctrl+Shift+,` because that is the same physical key and
the spelling wx understands.

<!-- keys:end -->
