# QuillLite 1.0 — What's New

**QuillLite is a simple, friendly text editor built for people who use a screen
reader.**

If you like Notepad or WordPad, you will feel at home in about a minute. The
keys are the same ones you already press. What is different is that QuillLite
tells you what is going on — out loud, and in a status bar you can actually read.

It installs alongside QUILL for All. You can have both, and they keep their own
settings unless you ask otherwise — QUILL has a **Bring My QuillLite Settings**
command that copies your preferences across and shares your abbreviations,
dictionary, copy tray, clips and bookmarks from then on. Nothing happens until
you ask for it, and nothing you already had is replaced.

---

## Who this is for

You want to open a file, change a line, and save it. You do not want a whole
writing studio in the way to do that.

That is the idea. QuillLite is the editor from QUILL for All, on its own, with
everything else taken out.

---

## Getting started in one minute

1. Open QuillLite. You are in a blank document, ready to type.
2. Type something.
3. Press **Ctrl+S** to save it.

That is it. Everything below is there when you want it, and out of your way
until then.

Press **F1** at any time and QuillLite tells you what window you are in and what
the thing you are focused on does. Press **Ctrl+F1** for a list of every key.

---

## The keys you already know

If you have used Notepad or WordPad, you already know QuillLite.

**Files**

- **Ctrl+N** — new document
- **Ctrl+O** — open
- **Ctrl+S** — save
- **Ctrl+Shift+S** — save as
- **Ctrl+P** — print
- **Ctrl+W** — close this document
- **Ctrl+Q** — close QuillLite

**Finding things**

- **Ctrl+F** — find
- **F3** — find the next one
- **Shift+F3** — find the previous one
- **Ctrl+H** — replace
- **Ctrl+G** — Go To: a line number, a bookmark or a heading
- **F5** — put today's date and time in

**Making text look different**

- **Ctrl+B**, **Ctrl+I**, **Ctrl+U** — bold, italic, underline
- **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J** — left, centre, right, justify
- **Ctrl+Shift+L** — bullet points
- **Ctrl+1**, **Ctrl+5**, **Ctrl+2** — single, one-and-a-half, double spacing
- **Ctrl+Shift+>** and **Ctrl+Shift+<** — bigger and smaller text
- **Ctrl+=**, **Ctrl+-**, **Ctrl+0** — zoom in, zoom out, back to normal

The full list is in the User Guide, and **Ctrl+F1** shows it inside the app.

---

## What's in it

### Your documents are numbered

Open several files and each one gets a number: document 1, document 2, document
3. The number never changes while that document is open, so "document 3" stays a
name you can hold on to.

To move between them:

- **Alt+1** through **Alt+9** — go straight to that one
- **Ctrl+Tab** or **Ctrl+F6** — go to the next one
- The **Window** menu — the full list

**One thing to know.** Your documents live inside one QuillLite window, so
**Alt+Tab will not step between them.** The four ways above are how you move
around. We would rather tell you that now than have you find it out while
looking for a document you thought you had lost.

### A heading tells you it is a heading

Make a line a heading, arrow away, and arrow back onto it. QuillLite says
**"Heading 2, Installing"** -- the level, then the heading's own words.

That sounds like it should have worked all along, and here is why it did not.
Your screen reader can only read what a program hands it, and the text box every
Windows editor is built on -- Notepad's, WordPad's, ours -- has no way to say
"this paragraph is a heading". It can pass on the font and the size and nothing
more. Word manages it by building its own machinery for the job. So a heading,
to a listener, read exactly like an ordinary sentence.

QuillLite now says it instead. Three things about how:

- **The level first, and the words with it.** This is one sentence QuillLite
  says, not a note added to your reader's. It has to be that way round: a cue
  waiting its turn behind the reader is thrown away whenever the reader starts
  again, which is what happens on every big jump -- **Ctrl+Home**, a search hit,
  a bookmark. Somebody reported exactly that: arrowing onto a heading announced
  it, Ctrl+Home onto the same heading said nothing at all. It is also the order
  a web browser gives you.
- **Once, when you get there.** Moving about inside the heading stays quiet.
  Leave it and come back and you are told again.
- **The other way round is still there.** If you would rather hear the line and
  take the level as a footnote, **Preferences ▸ Say a heading's level ▸ After
  the text** does that. Same information, other order.

It works the same in a plain-text document, where a heading is a line starting
with `#`. That is new too: **Next Heading**, **Previous Heading** and the
headings list used to refuse in plain text -- "Headings are only available in
rich text" -- in documents whose headings the Promote and Demote keys were
perfectly happy to change. They walk those documents now, and the status bar's
**Heading** cell reads the level there as well instead of saying it cannot.

If you would rather not hear it -- you are reading the file as text, and the
levels are between you and the words -- **View ▸ Announce Headings**, or
**Ctrl+Alt+F3**, turns it off where you stand and back on the same way. It tells
you which way it went, not just "on" or "off".

And a `#` is only a heading where a `#` means a heading. In a `.md`, a `.txt` or
a document you have not named yet, it is. In a `.py`, a `.sh` or an `.ini` it is
a comment, and QuillLite leaves it alone -- otherwise opening a build script
would have it announcing "Heading 1" down most of the page.

### And a list tells you it is a list

Arrow into a list and you hear **"Bulleted list, 5 items"**. Go a level deeper
and you hear **"Level 2, 3 items"**. Arrow out and you hear **"Out of list"**.

This one is worth dwelling on, because it is the only thing in this release your
screen reader already does *everywhere else*. Open a web page with a list on it
and your reader will tell you it is a list and how long it is -- because the
browser hands it a list. Open the same list in an editor and it is not a list at
all, it is a row of dashes and some spaces, and your reader has nothing to pass
on. Writing a nested outline, the only thing separating the second level from
the third is the number of spaces, counted by ear.

It works wherever a list is real: Markdown `-`, `*`, `+`, `1.`, and HTML `<ul>`,
`<ol>`, `<dl>` -- and a definition list says **"Term"** and **"Definition"** as
you move between the two, because which of them you are typing into decides what
the words mean.

**The counting is per level.** A list of three whose second item has four
sub-items is "3 items" where you are and "4 items" where they are. Never seven.
Somebody reorganising an outline by ear is relying on that number.

It stays quiet everywhere it should: moving down a list (your reader is already
reading each item), on a `---` rule, inside a code fence, in a `.py` where a
dash is a flag, and in rich text where the bullets are the control's own.

**View ▸ Announce Lists (Ctrl+Alt+F5)** turns it off where you stand. It is a
separate switch from the heading one on purpose -- reorganising an outline, the
level *is* the work; proof-reading the same file, it is one more thing between
you and every item -- and the status bar's new **List** cell will tell you which
item of how many you are on whenever you want to ask.

### Bold now works in a Markdown file

**Ctrl+B** in a `.md` used to say "Not available in plain text. Press Control
Shift M to switch to rich text." True, and beside the point: somebody writing
Markdown does not want rich text. They want two asterisks.

So a plain document now has a **language**, and it decides what the keys write:

| In a | **Ctrl+B** writes | **Ctrl+Alt+2** writes |
|---|---|---|
| Markdown document | `**bold**` | `## Heading` |
| HTML document | `<strong>bold</strong>` | `<h2>Heading</h2>` |
| Plain text document | nothing, and says why | nothing, and says why |

QuillLite reads the language from the file name -- `.md` and `.txt` are
Markdown, the newly-recognised `.html`, `.htm` and `.xhtml` are HTML, a `.py` or
a `.conf` is plain -- and it is never binding. **Alt+Shift+F** rings through
all four kinds of document, one press at a time, each saying its own name;
**Ctrl+Alt+F6** goes straight to one; and the status bar's **Format** cell says
which you are in.

The announcement names the markup rather than the effect -- "Bold in Markdown",
not "Bold on". Nothing went bold. Two asterisks appeared, and you need to know
which of the two just happened.

### An Insert menu, with emoji and two tag pickers

Insert was three rows tucked inside Edit. It is a menu of its own now, sitting
**before Format** -- the order the work happens in: you put a thing in, then you
format it. Nothing you already press has moved.

- **Alt+.** opens the **emoji picker** -- QUILL's own, key for key. Search by
  name, by keyword, by what it looks like, or by a typed smiley (`:)` finds the
  smiling face). Every emoji comes with a written description of what it
  actually shows, which is the entire point: a wall of little pictures is the
  one control shape that cannot be used without sight.
- **Ctrl+Alt+I** opens the **Markdown tag picker** -- the whole vocabulary,
  searchable.
- **Ctrl+Alt+O** opens the **HTML tag picker** -- 111 tags and 20 whole form
  fields, and it searches by
  what they *do*: type "dropdown" and find `select`, "checkbox" and find
  `input`, "collapsible" and find `details`.

Only one of the two tag pickers is ever available, and it is whichever your
document is. The other is **greyed out rather than hidden**, so your reader
tells you it is unavailable the moment you land on it instead of leaving you
hunting the menus for something you know is there.

### Forms that are accessible before you start

The HTML picker's top twenty rows are not tags. They are **finished form
controls**, and they are the reason this picker is worth having.

Putting a `<select>` into a page is the easy half. The half that decides whether
anybody can use the form is the wiring — a `<label>`, a `for` that matches the
field's `id`, the options inside — and every part of that wiring is **invisible**.
A missing `for` renders exactly like a present one. A set of radio buttons
without a shared `name` looks exactly like a group, except every button can be
switched on at once. Two fields that share an `id` look perfect until somebody
clicks the second label and the first field takes focus.

Those are not things you can check by looking, and they are certainly not things
to leave to memory at the moment somebody is trying to write a form. So they
come with the control:

- **Text, email, password, telephone, web address, number, date, search and
  file upload** — each labelled, each with `autocomplete` where a browser can
  help fill it in.
- **A dropdown** with its label, its options, and an empty first choice, so it
  cannot quietly submit an answer nobody gave.
- **A radio group** in a `<fieldset>` with a `<legend>`, three buttons sharing
  one `name`, and exactly one default.
- **A checkbox**, and a checkbox group with the same fieldset treatment.
- **An autocomplete field** joined to its own suggestion list.
- **A required field with a hint and an error message**, both joined to the
  field with `aria-describedby`, plus `aria-invalid` and a live `role="alert"` —
  the pattern that turns red text into something a screen reader reports.
- **A whole contact form**, if you want the lot in one keystroke.

**Select a word first and it becomes the label**, with the `id` made from it so
the two agree: select "Postcode", choose a text field, and you have a Postcode
field already wired. And **the `id` is checked against your document before it
is used** — a second email field is `email-2`, never a silent duplicate of the
first.

The picker also grew from forty-six tags to **111**, which matters more than it
sounds: the missing ones included `<dl>`, `<dt>` and `<dd>` — the very lists
QuillLite now reads aloud to you — along with `<figure>` and `<figcaption>`,
the table parts that make a table readable, `<abbr>`, and `<br>` and `<hr>`,
which the app knew how to write and could not offer. A searchable list ought to
be complete; searching 111 is no harder than searching 46, and a tag that is
missing is a dead end.

The Markdown picker gained **Underline**, **Horizontal Rule**, **Strikethrough**
and **Definition List** for the same reason — the first two it could already
write and had never offered.

### Smaller things you asked for

- **F6 now gets you out of the status bar as well as in.** So does Shift+F6.
  Escape always did, and still does.
- **Ctrl+Home onto a heading announces it.** See above -- the cue moved in front
  of your reader instead of behind it.
- **The status bar's Format cell knows all four kinds of document.** It used to
  say "Plain text" or "Rich text" and nothing else, so two thirds of what
  Alt+Shift+F does were invisible in the one place you would look to check.

One more thing came with it, in QUILL for All rather than here: a heading saved
to an `.rtf` file is now a proper Word heading. It used to be big bold text with
no style attached, so Word's navigation pane showed nothing -- and QUILL itself,
reopening the file, read every level back as a Heading 4.

### A status bar you can read

Press **F6** to step into the status bar, then use the arrow keys to move along
it. Each part says what it is and what it says. Press **Escape** to go back to
your document.

There are ten things it tells you: **Status Message**, **Position**, **Word
Count**, **Character Count**, **Selection**, **Format**, **Heading**,
**Encoding**, **Line Endings**, and **Saved State**.

Press **Enter** on one to act on it — Position takes you to a line, Format
switches between plain and formatted text, Saved State saves.

Two of those are worth pointing out, because most editors never show them at
all: **Encoding** and **Line Endings**. Those two decide whether a file opens
properly on somebody else's computer. It is good to be able to check.

### Your file comes back exactly as it was

Open a file, change nothing, save it, and it is exactly the file you started
with. Nothing is quietly reformatted, no invisible characters are added or taken
away, and a file that did not end with a blank line does not suddenly grow one.

When you *want* to change how a file is saved, **Tools ▸ File Encoding and Line
Endings** does it on purpose.

### Spell check

WordPad never had one. Notepad only got one recently. QuillLite has one, and it
is the same one QUILL for All uses.

- **F7** — check the whole document, one word at a time, with suggestions
- **Alt+Shift+F7** — suggestions for the word you are on right now
- **Ctrl+F7** and **Ctrl+Shift+F7** — jump to the next or previous mistake
  (**Alt+F7** is Word's key for the next one, and works here too)
- **Ctrl+Alt+F9** — add a word to your dictionary, so it stops being questioned
- **Alt+Shift+L** — every misspelling in one list, each with its line

**It knows when to stay quiet.** Some files are not writing at all — they hold
settings and instructions that computers read. In those, almost every word looks
like a mistake to a dictionary, and you would get a steady stream of warnings
that are all wrong. QuillLite recognises those files and says nothing as you
type. It tells you once when you open one, so you are never left wondering.

Press **Ctrl+Alt+F7** if you want checking on in a file like that anyway. It
changes only the document you are in. And **F7** always works, in every file — if
you ask for a check, you get one.

Words you teach QuillLite are yours. If you also use QUILL for All, one setting
in Preferences lets both share the same list.

**And it spells the word out for you.** This is the part that matters most and
the part no other editor does. "Receive" and "recieve" sound *identical* — being
told the word is being told nothing. So when you land on a misspelling,
QuillLite says the word and then, after a short pause, says the letters.

The pause is deliberate. It is a separate thing it says, not one long
announcement, so if you already knew what was wrong you press the next key and
never hear it. You only wait if you want to.

You decide how the letters come: plainly (R, E, C), in the **phonetic
alphabet** (romeo, echo, charlie — which is the only way to tell B from D from E
from P from T from V through a fast synthesiser), or both. You decide whether
capitals are named, so MacDonald and Macdonald are told apart. You decide how
long each pause is, and there are three of them, because moving quickly through
a document and stopping to choose a correction are not the same activity.

All of it is in **Tools ▸ Spelling ▸ Announcements** (**Ctrl+Alt+Shift+F7**),
with an example box that says your choices out loud as you change them.

### The Applications key, on a misspelled word

Put the cursor in a word QuillLite thinks is wrong and press the **Applications
key** (or Shift+F10, or right-click). The menu opens **with the corrections** —
one press of Down and you are on the first one; Enter replaces the word. No
dialog, no moving the cursor.

Underneath: ignore it once, ignore it everywhere in this document, add it to
your dictionary, or add it only for this file. Then the ways onward — more
suggestions, check the whole document, next and previous misspelling — each
showing its key, so the menu teaches you the shortcut instead of replacing it.

Every row names the word it is about, because a menu you reached with the
keyboard is a menu read out of context.

### While you type

Finish a word that is not in the dictionary and you hear a short, quiet falling
blip, and the status bar says which word it was. A sound rather than speech, on
purpose: speech there would interrupt the sentence you are in the middle of
writing, which is the one moment you can least afford it.

You can silence it, have the word spoken as well, or change how long before it
mentions the same word again.

### Bookmarks, and finding your place again

Press **Ctrl+Shift+B** to drop a bookmark where you are, and **F2** to come back
to it. You get nine numbered ones, and they follow the text as you edit around
them, so they do not drift out of place.

**Alt+Shift+G** lists them all.

### A proper Selection menu

Holding Shift and tapping an arrow key is right for two letters and miserable
for four paragraphs. **Edit ▸ Selection** has three better answers, and
everything in it tells you how much it took.

**Start a selection and walk to the end of it.** Press **F8**, move however you
like — arrows, Home, End, Page Down — and the selection follows you. **Shift+F8**
finishes. Nothing held down, nothing counted. **Ctrl+Shift+F8** puts back the
selection you just lost to a stray arrow key.

**Take a whole thing at once.** Word, line, paragraph, sentence or block, in one
keystroke, without knowing where any of them start. **Ctrl+Shift+X** grows the
selection outwards a step at a time and **Ctrl+Alt+Shift+X** shrinks it back —
so over-pressing costs you nothing.

**Marks.** A mark is where you were standing before you went to look something
up. **Ctrl+Shift+M** drops one, **Ctrl+M** goes back, **Alt+M** lists them,
and **Ctrl+Alt+X** swaps the cursor and the mark.

And **Ctrl+Shift+Y** reads back what is selected — because there is no glance
that confirms you took what you meant to, and the next key might replace it.

### "What is this character?"

**Ctrl+Shift+C** tells you exactly which character you are sitting on.

This sounds like a small thing and is not. A screen reader says "space" for
several different characters that look identical and behave differently — and
one of them is usually the reason a search is not finding something you can
plainly see is there.

### Three answers to a clipboard that only holds one thing

- A **Copy Tray** with twelve numbered slots, which survives closing the app
- A **Collector** that gathers several copies into one, to paste together
- A **Clip Library** that quietly remembers what you copied, in case it turns
  out to have mattered

And **Ctrl+Shift+V** pastes text with none of its formatting, which is the one
everybody wants and almost nobody has.

### Tools for tidying up text

Sort lines, remove blank lines, remove duplicate lines, trim trailing spaces, and
change to UPPERCASE, lowercase or Title Case.

Each works on what you have selected, or on the whole document if you have
selected nothing. And each one is a single undo — **Ctrl+Z** takes back the whole
sort, not one line at a time.

### Abbreviations

Type a short form, press space, and get the long one. Handy for an address, a
sign off, or anything you type often and would rather not spell out every time.

### It looks after work you have not saved

While a document has unsaved changes, QuillLite quietly keeps a copy beside your
file — never on top of it. If the power goes out, that work is offered back the
next time you open the app. Save or close normally and the copy disappears.

### It reopens what you had open

Close QuillLite with three documents open and it comes back with the same three,
in the same order. You can turn this off in Preferences.

### Finding a command without hunting through menus

**Ctrl+Shift+P** opens a search box for commands. Type "sort" and you get the
sorting commands, with no need to remember which menu they live under. Each one
shows its keyboard shortcut beside it, which is a good way to pick the keys up.

### Make it smaller, or bigger

**Tools ▸ Customize Features** lets you switch whole parts of QuillLite off.
Turning something off removes it from the menus *and* unhooks its keys, so it is
properly gone rather than just hidden.

Uncheck the first one and QuillLite is essentially Notepad.

There are **nineteen** areas. These fifteen start switched **on**:

Rich text and the Format menu · Heading navigation · Markdown and HTML ·
Bookmarks · Line tools and change case · Copy Tray and the clip library ·
Printing · Abbreviations · Spell check · The Selection submenu · The Matches
submenu · Go Back and Go Forward · The Command Palette · Describe Character ·
Text size

These four start switched **off**, and they sit in the same list rather than
being hidden away, because something you cannot find might as well not exist:

- **Autocorrect while typing** — curly quotes and em dashes. Lovely in a letter,
  unhelpful in a settings file. (It does not capitalise sentences.)
- **Timestamped backups** — a dated copy every time you save. Reassuring, and it
  does fill up a folder.
- **Go To Anything** — one box that searches everything at once.
- **AI help** — off for a different reason from the other three: using it sends
  the passage you ask about over the internet, and that is not a choice a
  default gets to make for you. See *AI help* below.

### Nine lessons, inside the app

**Ctrl+Alt+F1** opens **Tutorials**: nine guided lessons in two tracks, about
forty-two minutes in all. *Your first documents* covers opening a file and
giving it back unchanged, the four kinds of document, your numbered documents,
and what to press when you are lost. *Working in a document* covers selecting
more than a few words, finding your way back, skimming something long, spelling
without a red squiggle, and asking a question about the document in front of
you.

Every step says what to press, **why**, and **what you should hear when it
worked**. That last part is the one a manual never has and the one you actually
need when nothing on the screen is going to tell you. A step shows *your* key
rather than the shipped one, so a lesson stays true after you rebind something.

### Every key is yours to change

**Tools ▸ Keyboard Manager** (**Ctrl+Alt+Shift+R**) is every command in
QuillLite with the key it answers to. Type part of a name to find one, **Enter**
on its row to give it a different key, and if something else already has that
key QuillLite names the command that owns it and asks. **Record a Key** answers
the other question -- press it, press a chord, and hear what that chord does
today, or that it is free, or that another program has claimed it across the
whole of Windows and it never reaches this editor at all.

- **Reset to Default** puts one command back; **Reset Everything** does the lot,
  after asking. Nothing is written until you press Save, so Escape leaves your
  keyboard exactly as it was.
- **Check for Problems** reports the three ways a keyboard goes quietly wrong: a
  key claimed twice, a key QuillLite cannot read, and a key Windows will accept
  and then never actually deliver — assigned, and inert.
- **Insert can never be claimed.** It is NVDA's and JAWS's own modifier, and
  taking it from somebody who cannot then give it back is not a trade-off.

Only what you changed is stored, so a key we improve in a later version still
reaches you.

### Going back to an earlier version of a file

Switch on **Timestamped backups** in Customize Features and **File ▸ Earlier
Versions...** (**Ctrl+Alt+Shift+E**) lists every save of the document you are
in, newest first: "Today at 4:12 PM — 2,341 words". Up to twenty per document.

The word count is there to be compared rather than read. Two saves a minute
apart are almost impossible to tell apart by ear, and the version that is
suddenly two thousand words shorter is usually the one you are hunting.

**Restore** puts that version into the window and does **not** save, so the file
on disk is untouched until you decide and **Ctrl+Z** undoes it. **Open a Copy**
puts it in a new untitled window and leaves your document completely alone.

QuillLite has written these files since backups shipped and gave you no way to
read one back: correct, correctly dated, and reachable only if you knew which
hashed folder was yours. If you have had backups on, everything from before this
version is in the list too.

### Headings you can move, not just make

Making a heading is the easy half. This release is the other half.

- **Alt+Shift+Left** and **Alt+Shift+Right** promote and demote the heading you
  are on.
- **Alt+Shift+Up** and **Alt+Shift+Down** move a whole section — the heading,
  its text, and every subsection under it — past its neighbour. One edit, one
  **Ctrl+Z**.
- **Alt+Shift+F5** selects the section you are in, subsections included, so
  **Ctrl+X** and **Ctrl+V** can put it anywhere.
- **Ctrl+Alt+Shift+F5** is **Move Section To...**, which asks *where* instead.
  Pressing Alt+Shift+Up forty times is not a way to move a section across a long
  document; it is a way to lose it.
- **Alt+Shift+O** opens the **Heading Organizer**: every heading in one list,
  Tab and Shift+Tab to demote and promote, and the whole restructure lands as a
  single undo.
- **Ctrl+Shift+F9** folds the section you are in down to its heading, and
  **Ctrl+Shift+F10** unfolds everything. **Ctrl+Alt+Shift+Down** and
  **Ctrl+Alt+Shift+Up** step between sections.

### Printing you can read before you print

**Ctrl+Alt+Shift+P** is **Print Preview**, and it is not a picture of a page. It
is a readable answer: how many pages there are, where each one breaks, and what
is in the margins. A preview you cannot see is not a preview, so this one is
words.

**Rich text prints as rich text** — the headings, the bold and the alignment go
to the printer the way they are on the screen. **Ctrl+Alt+P** is Page Setup:
paper, orientation and margins, remembered between sessions.

### Closing a lot of documents at once

**Window ▸ Close Other Documents** (**Ctrl+Shift+F4**) keeps the document you
are in and closes the rest, asking once about everything unsaved rather than
once per document. It says how many it closed, because a count is the one thing
you cannot go and read off the screen.

### Sounds you can hear, change, and switch off

QuillLite makes a short sound when something happens that your screen reader
says nothing about: a cut, a copy, a paste, a delete, an undo, a document saved,
a document closed, printing started and finished, the app opening and closing.
These are exactly the moments where speech tells you nothing, because nothing
moved and nothing gained focus — so silence has always meant guessing.

They are designed as families, so you learn them once rather than one at a time.
**Undo and redo are the same little sound played backwards from each other.**
Open and close are one pair of bells, rising and falling. Cut, copy and paste are
one dry tick in three shapes, and delete is that tick dropped low with a breath
of noise under it.

**Tools ▸ Sound Scheme** (**Ctrl+Alt+Shift+O**) is all of them in a list that
**plays each one as you arrow onto it** — which is what turns a list of names
into something you can actually browse. Every row tells you the whole story: what
the event is, whether it is switched on, which file it plays and how long that
file is.

For whichever row you are on: **Play** it (even if it is switched off), switch it
on or off, **Browse** for a WAV of your own, remove its sound entirely, or put it
back to the one QuillLite ships. **Save As Scheme** keeps your whole set under a
name — as an ordinary folder you can copy, back up or send to a friend. **Restore
All Defaults** always works, because the sounds QuillLite ships are never
overwritten.

### Quiet mode

**Alt+Shift+M** silences everything at once. Press it again and it all comes
back.

One key, because "make it stop" is something you need *while* the noise is
happening — on a call, in a quiet room, or having simply had enough today. A
setting you have to go and find is not much help at the moment you need it.

### Every window answers F1

Press **F1** anywhere and QuillLite tells you what this window is for, and then
what the thing you are focused on does. Every window. Every button.

### Start with a blank document, or don't

QuillLite opens with an empty Untitled document, the way Notepad and WordPad do.

If you always open an existing file, that empty document is one more thing to
close on every single launch — so there is a switch in **Preferences** to turn it
off. Files you double-click, last session's documents and any recovered work all
still open either way, because every one of those is you asking for a document.

### It follows the contrast you already chose

QuillLite shipped opening in dark mode, because many of the people it is built
for find a bright white screen genuinely hard to look at. That was half right.
Light-sensitive does not mean *dark*: somebody who depends on high-contrast
black on white — which Windows ships as a theme and which plenty of low-vision
readers use — is hurt by a dark default in exactly the same way, and there are
more ways to need a particular contrast than there are defaults to guess with.

So **QuillLite follows Windows**. Anybody with a strong requirement has already
told the system about it, in the one place every other program reads. **View ▸
Dark Mode** (**Alt+Shift+D**) forces dark whenever you want it, and Preferences
has the same choice as a setting.

If you chose dark in an earlier build you keep dark; only somebody who never
chose comes with the new default.

It changes what *you* see and nothing else. The colours are never saved into your
file, so a document you send somebody will not arrive full of grey text.

---

### When something goes wrong, there is a person at the other end

**Help > Get Help from Support...** — **Ctrl+Alt+F2** — writes to
**support@community-access.org**, where a person reads it and replies to you by
email.

Fill in what kind of message it is, a subject, and what happened. What you
expected and how to reproduce it are optional and worth more than anything else
when you can give them. **Your email address is optional too**: you can report a
problem without giving one, you simply will not be able to be replied to.

Press Send and **your own mail program opens with the whole message already
written** — QuillLite's version, your Windows version and your screen reader
filled in at the bottom, so you do not have to go and find any of it. Nothing is
sent until you send it from there, and QuillLite says so out loud rather than
claiming to have sent something it has not. If you use webmail and have no mail
program set up, the whole message and the address go on your clipboard instead,
so nothing you typed is ever lost.

Writing to **support@community-access.org** yourself works exactly as well.
There is no form you have to use.

---

### It tells you when there is a new version

**Help > Check for Updates...** — **Ctrl+Alt+U**, the same key in every app in
the family.

If there is nothing newer, it says so in a dialog. That is on purpose: a key
that answers with silence is indistinguishable from a key that does nothing.

If there **is** something newer, the window opens on **what changed** — the
release notes for that version, in a read-only box you can arrow through like a
document. Your focus lands in the notes, not on a button, so the first thing you
hear is what is in the release. Tab from there and there are two buttons:
**Update**, which downloads it and then offers to install it and restart for you
— your settings, your recent files and your recovered work are all kept — and
**Close**, which does nothing at all. Nothing is downloaded until you press
Update.

QuillLite also looks once a day when it starts, and says **nothing** unless
there is something. Not while it checks, not when there is nothing, and not when
your network is down. Only a real new version speaks, and even then it only
offers. If you would rather it never looked on its own, there is a tick box in
Settings: *Look for updates when QuillLite starts*. Ctrl+Alt+U still works
either way.

One small consequence: **Page Setup moved to Ctrl+Alt+P**, because Ctrl+Alt+U
means Check for Updates everywhere else in the family and a key that means two
different things is a key you cannot trust.

---

### Free AI help, if you want it — and how to start

This is the newest thing in QuillLite and the one most people will not have used
before, so this section is longer than the others on purpose.

**One pad, and five things it can do.** All of them work on what you have
selected, or on the paragraph or section you are in — the pad has a **Send this
much** chooser and shows you *exactly* what will go before it goes:

| Ask for | You get |
|---|---|
| **Summarize** | What this says, in a few sentences |
| **Rewrite** | The same meaning, clearer and shorter |
| **Proofread** | A **list** of what is wrong. Nothing is changed behind your back |
| **Explain** | What this passage means, in plain language — for jargon, a legal clause, a paragraph that will not sit still |
| **Ask about this document** | A plain question: "what does this say about the deadline?" The answer comes back with the part of the document it came from |

They live in **Tools ▸ AI**, behind two keys: **Ctrl+Alt+G** opens the pad
where you are, and **Ctrl+Alt+Z** opens the same pad with the last row already
chosen — that one takes a question rather than a selection, which is why it is
worth a chord rather than one more row to arrow past.

The answer arrives in a read-only box with **Replace My Selection**, **Insert
Below**, **Copy** and **Try Again** under it, so **nothing is applied for you**.
Proofread in particular reports what it found and changes not one character
until you press Replace My Selection.

**Starting from nothing — four steps, once.**

1. **Turn the area on.** **Tools ▸ Customize Features** (**Ctrl+Alt+F10**),
   tick **AI help**, Save. It ships off.
2. **Read the agreement and accept it.** Turning the area on asks straight away.
   You can decline and keep the menu; the switch does not flip itself back.
3. **Connect this computer.** **Tools ▸ AI ▸ Connect or Sign Out**
   (**Ctrl+Alt+Shift+F10**), where accepting the agreement takes you anyway.
   The window opens on an **eight-character code**; **Open the Connect Page**
   fills it in for you in the browser, or type it into the web page on any
   device. **No account, no password, no email address.** The window confirms
   in place — focus does not jump to something you did not open.
4. **Try the short one.** Select a paragraph, press **Ctrl+Alt+G**, choose
   **Summarize**. It is the shortest round trip there is, so it is the fastest
   way to find out the whole thing is working.

Each computer connects separately, and signing one out does not sign out the
others.

**What it costs, in words you can check.** About **2,250 words** in one question
(3,000 tokens, counting the document text, your question and the instructions
together), and the answer is capped at a few hundred words. **100 requests a
month**, no more than **20 in a day** and **8 in an hour** — the hourly and
daily numbers exist to stop one runaway loop spending a month's worth in an
afternoon, not to ration ordinary work. If what you asked about is too big, the
pad says so *in words* before anything is sent — "that is about 4,000 words, and
the free limit is about 2,250" — so you can select less and ask again.

**A long document still works.** Ask About This Document does not send the whole
file. It picks the **three passages most likely to answer your question**, each
about 180 words and carrying the heading it sits under, and shows you which ones
before anything goes. So a hundred-page document is a fair thing to ask about.

The limits are read from the service rather than built into the program, so one
can be raised without you installing anything.

**It is off until you turn it on and accept the agreement** — both, not either.
Those are separate questions on purpose. Switching the area on answers "does this
feature exist in my copy". The agreement answers "have I agreed to what it does".
An area switched on by a profile, by a settings import, or by somebody else using
the machine is not consent, so the agreement is asked for on its own.

It is stored as a *version* rather than a yes, so if what gets sent or kept ever
changes in a way that matters, you are asked again instead of your old answer
being taken to cover the new thing. And you can reach it three ways — the AI
menu, a tick box in Preferences, or switching the area on — because the place you
look depends on which part of the app you already know. All three are the same
answer.

**Nothing leaves this computer until you ask it to.** Not as you type, not in the
background. You run one of the two commands, the text you asked about goes, the
answer comes back. **Usage** (Ctrl+Alt+Shift+F9) tells you what you have left
before you find out by being refused, and **Privacy Agreement**
(Ctrl+Alt+Shift+K) opens whether or not any of it is switched on — a door you can
only reach by agreeing to something first is not a door.

## Two things this fixed in QUILL for All

Building QuillLite turned up two real faults in QUILL for All's editor. Both are
now fixed for everybody who uses QUILL, not just for QuillLite.

**Headings were losing their bold.** Applying a heading set the size correctly
but quietly failed to make it bold, with no error, so nothing seemed wrong at the
time. Because QUILL partly recognises a heading *by* its bold, it could then no
longer find the headings it had just made — and moving between headings stopped
working in formatted documents.

**Asking "what formatting is this?" described the wrong line.** With the cursor
at the very start of a heading, QUILL described the ordinary paragraph above it
instead. It now describes the text you are actually on, the same way your screen
reader does.

---

## QUILL for All gained things too

QuillLite is never allowed to be better than QUILL for All. Anything it needed
that QUILL could not yet do went into QUILL in the same release:

- **Justify** — the fourth alignment, which was simply missing
- **Line spacing** — single, one-and-a-half and double
- **Bigger and smaller text** in sensible steps, rather than one size at a time
- **Paste Text Only**, which neither of them had
- **Bullet points** that are real bullet points
- **A spell checker that stays quiet** in settings files, the same way
  QuillLite's does
- **Select Word**, which QUILL could select a line, a paragraph and a block but
  never a single word
- **A key for Select Line**, which was sitting in QUILL's menu with no shortcut
  shown beside it, and for Select Paragraph, Duplicate Selection and Extend
  Selection Mode — all of which QUILL could do and none of which had a key
- **Shrink Selection that always works.** It used to be able only to undo an
  expansion you had just made; select a paragraph outright and ask to shrink and
  it said there was nothing to shrink. It now works out the answer from the text

Two keys used to differ between the two apps — **Ctrl+J** for Justify and
**Ctrl+Shift+V** for Paste Text Only, which QUILL for All had long since spent on
other things. In September 2026 QUILL moved those other things instead, and both
keys now mean the same in both products. See the section below for what else
changed with them.

---

## September 2026: the two editors became one family

QuillLite shipped first and, for a while, was better than QUILL for All at a few
things — which is backwards. A twenty-nine item pass fixed that in both
directions. What you will notice in QuillLite:

**Your keys are the family's keys.** Sixteen commands that QUILL kept behind a
leader chord came onto the plain keys you already press here, and where QUILL and
QuillLite disagreed about a key, the one with the better claim won — usually
Microsoft's, because that is the key in your hands already. Word's **F12**,
**F12**, **Ctrl+F12** and **Ctrl+Shift+F12** (Save As, Open, Print) work in
QuillLite now;
QUILL had all three and QuillLite had none. Eight keys still differ on purpose,
and each one has its reason written down beside the code.

**No menu offers the same Alt letter twice.** Windows does not press a duplicated
mnemonic — it moves focus between the matching rows and waits — so the letter
stops being a shortcut and becomes a slow, silent walk. A new check found 170 of
these across the whole family. All 170 are fixed.

**The formatting keys the editing control brings with it** — Ctrl+U, Ctrl+E,
Ctrl+L, Ctrl+R, Ctrl+J, Ctrl+= and a few more — used to *appear* to work in a
Markdown or plain document. The formatting was really applied and never saved,
never announced, and never marked the document as changed. They are now swallowed
in a document that cannot hold formatting, and QuillLite says so once: "Underline
has no meaning in a plain text document."

**A UTF-16 big-endian file stays big-endian.** Both byte orders were read through
the one codec that always writes little-endian, so saving a file you had not
otherwise touched swapped every pair of bytes in it. The File Encoding and Line
Endings window also shows what your file actually is: a file in a format the
lists cannot offer — big-endian, or classic-Mac CR line endings — shows a **keep
as is** row and stays in it, where before the list quietly started on its first
row and confirming the window converted the file.

**The status bar stops answering for a rich document.** Encoding and Line Endings
read "UTF-8" and "CRLF" for every `.rtf`, which has neither. They now say so.

**Suggestions spell themselves** as you arrow through the spelling review, the
same way the misspelled word already did.

**One set of abbreviations, if you want one.** QuillLite could already read
QUILL's abbreviations and personal dictionary. QUILL can now take yours: **Bring
My QuillLite Settings** merges your abbreviations, dictionary, copy tray, clip
library and bookmarks into QUILL, turns the sharing switches on here so both
editors read the one copy, and copies your preferences and rebound keys across.
QUILL wins any collision, nothing already in QUILL is replaced, and it tells you
what it is about to do before it does any of it.

---

## Things worth knowing before you start

- **Windows only**, for now.
- **Rich text prints as rich text.** A rich document is printed by the editor
  itself, so a heading arrives on paper as a heading and a bold word arrives
  bold. This was not true before 1.0 -- everything printed flat, in one size.
  A plain text or Markdown document prints as it reads, which is the right
  answer: a Markdown heading already carries its own `#` onto the page.
- **QuillLite does not talk on its own.** It speaks through NVDA or JAWS, and
  says nothing without one. That is deliberate — a second voice talking over your
  screen reader is worse than silence. Everything it would say also appears in
  the status bar, so you can always go and read it.
- **The theme is never written into your file.** Whatever colours you are
  looking at, the document is stripped back to automatic colour before every
  save -- so a dark theme can never leave grey text in something you send
  somebody. Colour you apply *yourself* in a rich document is yours and is
  kept, in the file and through every conversion.

---

## Which download do I want?

| Download | Size | Choose this if |
|---|---|---|
| **QuillLite-Setup-Shared-1.0.0.exe** | 117 MB | You just want to install it. Everything is included. This is the one. |
| **QuillLite-Portable-1.0.0.zip** | 94 MB | You want to run it from a USB stick, with your settings on the stick too. |

If you are not sure, take the first one.

When you install it, QuillLite offers to appear in the "Open with" list for text
files. That is optional, and it never takes over as the default — Notepad,
WordPad and QUILL all stay exactly where they are.

Windows may warn you about the installer until our certificate is fully
established. Choose **More info**, then **Run anyway**.

---

## Thank you

QuillLite was contributed by Steven Scott, who not only offered the app but
tracked down the two heading faults above and left them for us to fix separately,
so that adding an app and changing the editor stayed two decisions rather than
one.

That is a thoughtful way to give something away, and it is the reason this
release makes QUILL for All better as well.
