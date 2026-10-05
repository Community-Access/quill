# QUILL Lite 1.0

*Released September 25, 2026.*

Welcome to QUILL Lite, a simple, friendly text editor for people who use a
screen reader. If you like Notepad or WordPad, you will feel at home in about a
minute. The keys are the ones you already press. The difference is that QUILL
Lite tells you what is going on, out loud, and in a status bar you can actually
read.

New in 1.0 is free AI help, built in. Select a paragraph, press
**Ctrl+Alt+G**, and have it summarized, rewritten, proofread or explained, or
ask a question about the document you have open. There is no account, no
password and no card. *Free AI help*, near the end of these notes, tells you
how to start.

QUILL Lite is the editor from QUILL for All, on its own, with everything else
taken out. You can have both. Each keeps its own settings unless you ask
otherwise, and QUILL's **Bring My QUILL Lite Settings** command lets the two
share your abbreviations, dictionary, copy tray, clips and bookmarks.

## Try this first

1. Open QUILL Lite. You are in a blank document, ready to type.
2. Type something.
3. Press **Ctrl+S** to save it.

That is it. Everything else is there when you want it, and out of your way
until then. If you ever wonder where you are, press **F1**: QUILL Lite tells
you what window you are in and what the thing you are on does. Press
**Ctrl+F1** for a list of every key, and **Ctrl+Alt+F1** for nine short
lessons.

## The keys you already know

If you have used Notepad or WordPad, you already know QUILL Lite.

### Files

- **Ctrl+N**: new document
- **Ctrl+O**: open
- **Ctrl+S**: save
- **Ctrl+Shift+S**: save as
- **Ctrl+P**: print
- **Ctrl+W**: close this document
- **Ctrl+Q**: close QUILL Lite

### Finding things

- **Ctrl+F**: find
- **F3**: find the next one
- **Shift+F3**: find the previous one
- **Ctrl+H**: replace
- **Ctrl+G**: go to a line number, a bookmark or a heading
- **F5**: put today's date and time in

### Making text look different

- **Ctrl+B**, **Ctrl+I**, **Ctrl+U**: bold, italic, underline
- **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J**: left, centre, right, justify
- **Ctrl+Shift+L**: bullet points
- **Ctrl+1**, **Ctrl+5**, **Ctrl+2**: single, one-and-a-half, double spacing
- **Ctrl+Shift+>** and **Ctrl+Shift+<**: bigger and smaller text
- **Ctrl+=**, **Ctrl+-**, **Ctrl+0**: zoom in, zoom out, back to normal

Word's **F12**, **Ctrl+F12** and **Ctrl+Shift+F12** (Save As, Open, Print)
work here too.

## Moving around

### Your documents are numbered

Open several files and each one gets a number: document 1, document 2,
document 3. The number stays the same while that document is open, so
"document 3" is a name you can hold on to.

- **Alt+1** through **Alt+9**: go straight to that one
- **Ctrl+Tab** or **Ctrl+F6**: go to the next one
- The **Window** menu: the full list

**One thing to know.** Your documents live inside one QUILL Lite window, so
**Alt+Tab will not step between them.** Use the four ways above instead. We
would rather tell you now than have you think a document went missing.

### Bookmarks and marks

Press **Ctrl+Shift+B** to drop a bookmark where you are, and **F2** to come
back to it. You get nine numbered ones, and they move with the text as you
edit around them. **Alt+Shift+G** lists them all.

A mark is where you were standing before you went to look something up.
**Ctrl+Shift+M** drops one, **Ctrl+M** goes back to it, and **Alt+M** lists
them.

### Finding a command without hunting through menus

**Ctrl+Shift+P** opens a search box for commands. Type "sort" and you get the
sorting commands, without remembering which menu they are in. Each one shows
its key beside it, which is an easy way to pick up the keys.

## Hearing what is in front of you

### A heading tells you it is a heading

Make a line a heading, arrow away, and arrow back onto it. QUILL Lite says
**"Heading 2, Installing"**: the level, then the heading's own words.

In other editors, a heading sounds exactly like an ordinary sentence. Your
screen reader can only read what a program gives it, and the kind of text box
Notepad, WordPad and QUILL Lite are built on has no way to say "this is a
heading". So QUILL Lite says it for you.

- **The level comes first, with the words**, as one sentence, the way a web
  browser gives it to you. It works however you got there, including
  **Ctrl+Home**, a search result or a bookmark.
- **Once, when you get there.** Moving around inside the heading stays quiet.
  Leave and come back, and you hear it again.
- **You can turn the order around.** Choose **Preferences > Say a heading's
  level > After the text**.

It works the same in a plain-text document, where a heading is a line
starting with `#`. **Next Heading**, **Previous Heading** and the headings list
now walk plain documents too, and the status bar's **Heading** part reads the
level there as well. A `#` only counts as a heading where it means one: in a
Markdown or text file, yes; in a script or settings file, no. You will not hear
"Heading 1" all the way down a script.

To turn it off, press **Ctrl+Alt+F3**, or choose **View > Announce Headings**.
Press it again to turn it back on. It tells you which way it went.

### And a list tells you it is a list

Arrow into a list and you hear **"Bulleted list, 5 items"**. Go a level deeper
and you hear **"Level 2, 3 items"**. Arrow out and you hear **"Out of list"**.

On a web page your screen reader already does this. In an editor, a list was
just a row of dashes, and you had to count spaces by ear to know how deep you
were. Now you are told. It works with Markdown and HTML lists, and in a
definition list you hear **"Term"** and **"Definition"** as you move between
the two.

Each level is counted on its own. If a list has three items and the second has
four sub-items, you hear "3 items" at the top and "4 items" inside, never
seven. That matters when you rearrange an outline by ear.

It stays quiet where it should: as you move down a list, on a dividing line,
inside a block of code, in a script, and in rich text where the bullets are
real bullets. To turn it off, press **Ctrl+Alt+F5**, or choose **View >
Announce Lists**. It has its own switch, separate from headings. The status
bar's **List** part tells you which item you are on, out of how many.

### A status bar you can read

Press **F6** to step into the status bar, then use the arrow keys to move
along it. Each part says its name and what it shows. Press **F6** again,
**Shift+F6** or **Escape** to go back to your document.

It tells you ten things: **Status Message**, **Position**, **Word Count**,
**Character Count**, **Selection**, **Format**, **Heading**, **Encoding**,
**Line Endings**, and **Saved State**. Press **Enter** on one to act on it.
Position takes you to a line, Format switches between plain and formatted
text, and Saved State saves.

Encoding and Line Endings decide whether a file opens properly on someone
else's computer, and most editors never show them. Now you can check.

### "What is this character?"

**Ctrl+Shift+C** tells you exactly which character you are on. A screen reader
says "space" or "dash" for several characters that look the same but behave
differently, and one of them is often why a search will not find something you
know is there.

## Writing

### Markdown and HTML, written for you

**Ctrl+B** in a Markdown file used to tell you to switch to rich text. But when
you are writing Markdown, you do not want rich text. You want two asterisks.

So a plain document now has a **language**, and it decides what the keys
write:

| In a | **Ctrl+B** writes | **Ctrl+Alt+2** writes |
|---|---|---|
| Markdown document | `**bold**` | `## Heading` |
| HTML document | `<strong>bold</strong>` | `<h2>Heading</h2>` |
| Plain text document | nothing, and says why | nothing, and says why |

QUILL Lite guesses the language from the file name, and the guess is never
final:

- **Alt+Shift+F** steps through all four kinds of document, plain text,
  Markdown, HTML and rich text, and each one says its name.
- **Ctrl+Alt+F6** goes straight to the one you want.
- The status bar's **Format** part tells you which one you are in.

When you press a formatting key, you hear what was written, like "Bold in
Markdown" rather than "Bold on".

### An Insert menu, with emoji and two tag pickers

Insert is now a menu of its own, just before Format, because you usually put
something in first and format it after. Nothing you already press has moved.

- **Alt+.** opens the **emoji picker**. Search by name, by keyword, by what it
  looks like, or by a typed smiley (`:)` finds the smiling face). Every emoji
  comes with a written description of what it shows.
- **Ctrl+Alt+I** opens the **Markdown tag picker**, with every Markdown tag,
  including Underline, Horizontal Rule, Strikethrough and Definition List.
- **Ctrl+Alt+O** opens the **HTML tag picker**: 111 tags and 20 whole form
  fields. Search by what a tag does: "dropdown" finds the list box,
  "checkbox" finds the checkbox, "collapsible" finds the details tag.

Only the picker that matches your document is available. The other one is
greyed out, not hidden, so your screen reader tells you it is unavailable
rather than leaving you hunting for it.

### Web forms that are accessible from the start

The first twenty rows in the HTML picker are finished form fields, and they
are the best reason to use it. Whether anyone can use a form depends on
wiring you cannot see on the page: the label joined to the right field, the
options inside, radio buttons that really belong together. A missing link
looks exactly like one that is there.

So the picker puts the wiring in for you:

- **Text, email, password, telephone, web address, number, date, search and
  file upload** fields, each labelled, and each set up so a browser can help
  fill it in.
- **A dropdown** with its label, its options, and an empty first choice.
- **A radio group** with a group name, three buttons that work together, and
  one chosen to start with.
- **A checkbox**, and a group of checkboxes.
- **A field with its own suggestion list.**
- **A required field with a hint and an error message**, both joined to the
  field so a screen reader says the error instead of just showing red text.
- **A whole contact form**, if you want everything in one go.

Select a word first and it becomes the label. Select "Postcode", choose a text
field, and you have a Postcode field already wired up. QUILL Lite checks your
document first, so a second email field never clashes with the first.

### Spell check

WordPad never had a spell checker, and Notepad only got one recently. QUILL
Lite has the same one QUILL for All uses.

- **F7**: check the whole document, one word at a time, with suggestions
- **Alt+Shift+F7**: suggestions for the word you are on right now
- **Ctrl+F7** and **Ctrl+Shift+F7**: jump to the next or previous mistake
  (**Alt+F7**, Word's key for the next one, works here too)
- **Ctrl+Alt+F9**: add a word to your dictionary
- **Alt+Shift+L**: every misspelling in one list, each with its line

#### It spells the word out for you

"Receive" and "recieve" sound exactly the same, so hearing the word tells you
nothing. When you land on a misspelling, QUILL Lite says the word and then,
after a short pause, spells it. If you already know what is wrong, press your
next key and you will not hear the spelling.

You choose how the letters come: plainly, in the phonetic alphabet (romeo,
echo, charlie), or both. The phonetic alphabet is the easiest way to tell B,
D, E, P, T and V apart on a fast voice. You choose whether capitals are named,
and how long each pause is. All of this is in **Tools > Spelling >
Announcements** (**Ctrl+Alt+Shift+F7**), with an example that speaks your
choices as you change them.

#### The Applications key, on a misspelled word

Press the **Applications key** (or Shift+F10) on a word QUILL Lite thinks is
wrong. The corrections are at the top of the menu: press Down once and Enter,
and the word is replaced, with no dialog. Below them you can ignore the word,
add it to your dictionary, or add it only for this file, and every row names
the word it is about.

#### While you type

Finish a word that is not in the dictionary and you hear a short, quiet
falling blip, and the status bar shows which word it was. It is a sound, not
speech, so it does not interrupt your sentence. You can turn it off, or have
the word spoken as well.

#### It knows when to stay quiet

Some files hold settings and instructions for computers, and nearly every word
in them looks wrong to a dictionary. QUILL Lite recognises those files, stays
quiet as you type, and tells you once when you open one. Press
**Ctrl+Alt+F7** to check as you type in that document anyway. **F7** always
works, in every file.

Words you teach QUILL Lite are yours, and one setting in Preferences lets
QUILL for All share the same list.

### Selecting

Holding Shift and tapping an arrow key is fine for two letters and miserable
for four paragraphs. **Edit > Selection** gives you better ways, and each one
tells you how much it selected.

- **Start a selection and walk to the end of it.** Press **F8**, move however
  you like, and the selection follows. **Shift+F8** finishes.
  **Ctrl+Shift+F8** brings back a selection you just lost to a stray arrow key.
- **Take a whole thing at once**: a word, line, sentence, paragraph or block.
  **Ctrl+Shift+X** grows the selection a step at a time and
  **Ctrl+Alt+Shift+X** shrinks it back.
- **Ctrl+Alt+X** swaps the cursor and the mark.
- **Ctrl+Shift+Y** reads back what is selected, so you can check before your
  next key replaces it.

### More than one thing on the clipboard

- A **Copy Tray** with twelve numbered slots, still there after you close the
  app.
- A **Collector** that gathers several copies into one paste.
- A **Clip Library** that remembers what you copied.
- **Ctrl+Shift+V** pastes text with none of its formatting.

### Tidying up text

Sort lines, remove blank lines, remove duplicate lines, trim spaces from the
ends of lines, and change to UPPERCASE, lowercase or Title Case. Each works on
your selection, or the whole document if nothing is selected, and each is a
single **Ctrl+Z**.

**Abbreviations** let you type a short form, press space, and get the long
one: an address, a sign-off, anything you type often.

### Headings you can move, not just make

- **Alt+Shift+Left** and **Alt+Shift+Right** promote and demote the heading
  you are on.
- **Alt+Shift+Up** and **Alt+Shift+Down** move a whole section, with its
  subsections, past the one next to it. One edit, one **Ctrl+Z**.
- **Alt+Shift+F5** selects the section you are in, so you can cut it and paste
  it anywhere.
- **Ctrl+Alt+Shift+F5** is **Move Section To...**, which asks where you want
  it. Much easier than pressing Alt+Shift+Up forty times.
- **Alt+Shift+O** opens the **Heading Organizer**: every heading in one list.
  Tab and Shift+Tab demote and promote, and the whole rearrangement is a
  single undo.
- **Ctrl+Shift+F9** folds the section you are in down to its heading, and
  **Ctrl+Shift+F10** unfolds everything. **Ctrl+Alt+Shift+Down** and
  **Ctrl+Alt+Shift+Up** step between sections.

## Your work is safe

### Your file comes back exactly as it was

Open a file, change nothing, save it, and it is exactly the file you started
with. Nothing is reformatted, no invisible characters are added or removed,
and a file that did not end with a blank line does not suddenly get one. When
you do want to change how a file is saved, use **Tools > File Encoding and
Line Endings**.

### Unsaved work is looked after

While a document has unsaved changes, QUILL Lite keeps a copy beside your
file, never on top of it. If the power goes out, that work is offered back the
next time you open the app. And close QUILL Lite with three documents open,
and it comes back with the same three. You can turn that off in Preferences.

### Going back to an earlier version of a file

Switch on **Timestamped backups** in Customize Features. Then **File > Earlier
Versions...** (**Ctrl+Alt+Shift+E**) lists every save of the document you are
in, newest first, like "Today at 4:12 PM, 2,341 words". It keeps up to twenty.
Two saves a minute apart sound alike, but the one that is suddenly two
thousand words shorter is usually the one you want.

- **Restore** puts that version into the window and does not save. **Ctrl+Z**
  undoes it.
- **Open a Copy** puts it in a new window and leaves your document alone.

If you already had backups on, the ones from before this version are in the
list too.

## Printing you can read before you print

**Ctrl+Alt+Shift+P** is **Print Preview**, and it is not a picture of a page.
It tells you in words how many pages there are, where each one breaks, and
what is in the margins.

Rich text prints as rich text: headings, bold and alignment go to the printer
the way they are on screen. **Ctrl+Alt+P** is Page Setup, for paper,
orientation and margins.

## Making it yours

### Make it smaller, or bigger

**Tools > Customize Features** lets you switch whole parts of QUILL Lite off.
When you turn something off, it leaves the menus and its keys stop working,
so it is really gone. Uncheck the first one and QUILL Lite is pretty much
Notepad.

There are nineteen areas. Fifteen start switched on: Rich text and the Format
menu, Heading navigation, Markdown and HTML, Bookmarks, Line tools and change
case, Copy Tray and the clip library, Printing, Abbreviations, Spell check, The
Selection submenu, The Matches submenu, Go Back and Go Forward, The Command
Palette, Describe Character, and Text size.

Four start switched off, in the same list:

- **Autocorrect while typing**: curly quotes and long dashes. Lovely in a
  letter, unhelpful in a settings file.
- **Timestamped backups**: a dated copy every time you save.
- **Go To Anything**: one box that searches everything at once.
- **AI help**: off because using it sends the passage you ask about over the
  internet, and that should be your choice.

### Every key is yours to change

**Tools > Keyboard Manager** (**Ctrl+Alt+Shift+Space**) lists every command with
its key. Type part of a name to find one, and press **Enter** on its row to
give it a different key. If something else already has that key, QUILL Lite
tells you which command and asks what you want to do.

- **Record a Key** works the other way round: press a key and hear what it
  does now, or that it is free, or that another program has taken it.
- **Reset to Default** puts one command back, and **Reset Everything** puts
  them all back. Nothing is saved until you press Save.
- **Check for Problems** finds a key used twice, a key QUILL Lite cannot read,
  and a key Windows accepts but never delivers.
- **Insert can never be taken**, because NVDA and JAWS use it.

Only the keys you change are stored, so if we improve a key later, you still
get the improvement.

### Sounds you can hear, change, and switch off

QUILL Lite plays a short sound when something happens that your screen reader
does not mention: a cut, a copy, a paste, a delete, an undo, a save, a
document closed, printing, and the app opening and closing.

The sounds come in families, so you learn them once. Undo and redo are the
same little sound played backwards. Open and close are a pair of bells, rising
and falling. Cut, copy and paste are one dry tick in three shapes.

**Tools > Sound Scheme** (**Ctrl+Alt+Shift+O**) lists them all and plays each
one as you arrow onto it. You can switch one off, choose a sound file of your
own, save your whole set under a name, and always restore the originals.
**Alt+Shift+M** is Quiet Mode, which silences everything at once, for a call
or a quiet room. Press it again and they come back.

### A few more choices

- **Start with a blank document, or don't.** QUILL Lite opens with an empty
  document, like Notepad. If you always open an existing file, a switch in
  Preferences turns that off.
- **It follows the contrast you already chose in Windows.** **View > Dark
  Mode** (**Alt+Shift+D**) switches to dark whenever you want. The colours you
  see are never saved into your file.
- **Close a lot of documents at once.** **Window > Close Other Documents**
  (**Ctrl+Shift+F4**) keeps the one you are in, asks once about everything
  unsaved, and tells you how many it closed.

## Free AI help

This is the newest part of QUILL Lite, and probably the one you are least
likely to have used before, so this part takes a little longer.

### One pad, five things it can do

All five work on what you have selected, or on the paragraph or section you
are in. The pad shows you exactly what will be sent before anything goes.

| Ask for | You get |
|---|---|
| **Summarize** | What this says, in a few sentences |
| **Rewrite** | The same meaning, clearer and shorter |
| **Proofread** | A list of what is wrong. Nothing is changed without you |
| **Explain** | What this passage means, in plain language |
| **Ask about this document** | An answer to a plain question, with the part of the document it came from |

**Ctrl+Alt+G** opens the pad where you are. **Ctrl+Alt+Z** opens it ready for
a question about your document. The answer arrives in a box you can read,
with **Replace My Selection**, **Insert Below**, **Copy** and **Try Again**
under it, so nothing changes until you choose.

### Starting from nothing: four steps, once

1. **Open the agreement.** Choose **Tools > AI > Privacy Agreement**
   (**Ctrl+Alt+Shift+K**). It is there even while AI help is off.
2. **Read it and choose I Agree.** That switches AI help on.
3. **Connect this computer.** The **Connect or Sign Out** window
   (**Ctrl+Alt+Shift+F10**) opens by itself and shows an eight-character code.
   **Open the Connect Page** fills it in for you in your browser. There is no
   account, no password and no email address.
4. **Try the short one.** Select a paragraph, press **Ctrl+Alt+G**, and choose
   **Summarize**.

Each computer connects separately, and signing one out does not sign out the
others.

### How much you can use

- About 2,250 words in one question, and an answer of a few hundred words.
- 100 requests a month, no more than 20 in a day and 8 in an hour, so one
  mistake cannot use up a month in an afternoon.

If what you asked about is too big, the pad tells you in words before anything
is sent, so you can select less. Ask About This Document never sends the whole
file: it picks the three passages most likely to answer your question, each
with the heading it sits under, and shows you which before anything goes. So
you can ask about a hundred-page document.

### Your choice, and your privacy

AI help is off until you turn it on and accept the agreement, even if a
profile or someone else switched the area on. If what is sent or kept ever
changes in a way that matters, you are asked again.

Nothing leaves this computer until you ask. Not as you type, and not in the
background. **Usage** (**Ctrl+Alt+Shift+F9**) tells you what you have left.
The lesson *Asking a question about a document* walks through all of this.

## When you need a hand

- **F1** in every window tells you what the window is for, and then what the
  thing you are on does.
- **Ctrl+Alt+F1** opens **Tutorials**: nine guided lessons in two groups,
  about forty-two minutes in all. Every step tells you what to press, why, and
  what you should hear when it worked, using your own keys.
- **Help > Get Help from Support...** (**Ctrl+Alt+F2**) writes to
  support@community-access.org, where a person reads your message. Fill in a
  short form, and your own email program opens with the message written,
  including QUILL Lite's version, your Windows version and your screen reader.
  Your email address is optional. Nothing is sent until you send it, and with
  no email program, the message goes on your clipboard.
- **Help > Check for Updates...** (**Ctrl+Alt+U**) opens on what changed in
  the new version, so the first thing you hear is what is new. **Update**
  downloads it and offers to install it and restart, keeping your settings and
  recovered work. QUILL Lite also looks once a day when it starts, and says
  nothing unless there is something new. You can turn that off in Settings.
  To make room, Page Setup moved to **Ctrl+Alt+P**.

## September 2026: the two editors became one family

QUILL Lite came first and, for a while, did a few things better than QUILL
for All. That was backwards, so both were put right. Here is what you will
notice in QUILL Lite.

### Your keys are the family's keys

Sixteen commands that QUILL kept behind a two-step key moved onto the plain
keys you already press. Where the two editors disagreed, the key you already
know from Microsoft usually won. Eight keys still differ on purpose, each for
a reason we have written down.

### Every menu letter works

When two items in a menu share an Alt letter, Windows does not press either
one; it moves between them and waits. We found 170 of these across the whole
family, and fixed them all.

### Formatting keys in plain documents tell you the truth

Some formatting keys, such as Ctrl+U and Ctrl+E, used to seem to work in a
Markdown or plain document, but nothing was saved or announced. Now they do
nothing in a document that cannot hold formatting, and QUILL Lite tells you
once, for example: "Underline has no meaning in a plain text document."

### Your file's encoding stays the same

Saving a file in a less common encoding no longer changes it behind your back.
The File Encoding and Line Endings window also shows what your file really is,
and if it is something the lists do not offer, a **keep as is** row is already
chosen. And for a rich text document, the status bar no longer claims an
encoding and line endings it does not have.

### Suggestions spell themselves

As you arrow through spelling suggestions, each one is spelled out, the same
way the misspelled word is.

### One set of abbreviations, if you want one

**Bring My QUILL Lite Settings**, in QUILL, brings your abbreviations,
dictionary, copy tray, clip library and bookmarks into QUILL and shares them
from then on, along with your preferences and changed keys. Nothing already in
QUILL is replaced, and it tells you what it will do first.

## QUILL for All gained things too

QUILL Lite is never allowed to do something QUILL for All cannot, so anything
it needed went into QUILL as well:

- **Justify**, line spacing, and bigger and smaller text in sensible steps
- **Paste Text Only**, and bullet points that are real bullet points
- **A spell checker that stays quiet** in settings files
- **Select Word**, and keys for Select Line, Select Paragraph, Duplicate
  Selection and Extend Selection Mode
- **Shrink Selection that always works**
- **Ctrl+J** for Justify and **Ctrl+Shift+V** for Paste Text Only now mean the
  same in both editors

Building QUILL Lite also turned up two problems in QUILL for All's editor,
both now fixed for everyone. Making a heading did not make it bold, so moving
between headings stopped working in formatted documents. And asking "what
formatting is this?" at the start of a heading described the line above it.
A heading saved in a rich text file is now a proper Word heading too, so it
shows in Word's navigation pane.

## Good to know

- **Windows only**, for now.
- **Rich text prints as rich text.** A plain text or Markdown document prints
  as it reads, so a Markdown heading carries its own `#` onto the page.
- **QUILL Lite does not have its own voice.** It speaks through NVDA or JAWS,
  so you never have two voices talking over each other. Everything it says
  also appears in the status bar.
- **The colours you see are never saved into your file.** Colour you add
  yourself in a rich document is kept.

## Which download do I want?

| Download | Size | Choose this if |
|---|---|---|
| **QuillLite-Setup-Shared-1.0.0.exe** | 117 MB | You just want to install it. Everything is included. |
| **QuillLite-Portable-1.0.0.zip** | 94 MB | You want to run it from a USB stick, with your settings on the stick too. |

If you are not sure, take the first one. The installer offers to put QUILL
Lite in the "Open with" list for text files. That is optional, and it never
makes itself the default. If Windows warns you about the installer, choose
**More info**, then **Run anyway**.

## Thank you

QUILL Lite was contributed by Steven Scott. He not only offered the app, he
also tracked down the two heading problems above and left them for us to fix
separately. That is a thoughtful way to give something away, and it is why
this release makes QUILL for All better as well.

## Where to learn more

The QUILL Lite User Guide, in the Start menu beside QUILL Lite, covers
everything here. Its chapters include The first minute, Your documents are
numbered, Four kinds of document, Spell check, Selecting, The status bar,
Changing what a key does, Sounds, AI help and Getting help.

In the app, **Help > Tutorials** (**Ctrl+Alt+F1**) has two groups of lessons.
Your first documents covers Open a file, and give it back unchanged; Four kinds
of document, and how to say which; Your documents are numbered; and What to
press when you are lost. Working in a document covers Selecting more than a few
words; Finding your way back; Skimming something long; Spelling, without a red
squiggle; and Asking a question about a document.

If you get stuck, choose **Help > Get Help from Support** (**Ctrl+Alt+F2**),
or write to support@community-access.org. A person at Community Access reads
every message.
