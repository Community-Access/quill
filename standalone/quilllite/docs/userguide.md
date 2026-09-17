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

## Four kinds of document

Every document is one of four kinds. The title bar names the first two; the
status bar's **Format** and **Language** cells name all four.

**Plain text** is like Notepad. One font, no formatting, no markup. Text you
paste in arrives as plain text. This is what a `.py`, a `.conf` or a log file
is, and it is what you want when another program is going to read the file.

**Markdown** is plain text that means something: `#` starts a heading, `-`
starts a bullet, `**` makes a word bold. QuillLite writes those for you — see
[Formatting](#formatting) — and reads them back, so the caret can tell you you
have arrived at a Heading 2 or walked into a list of five.

**HTML** is the same idea in tags: `<h2>`, `<ul>`, `<strong>`. Everything
Markdown gets, HTML gets, in HTML's own spelling.

**Rich text** is like WordPad. Bold, italic, headings, alignment, bullet points,
line spacing. It saves as a Rich Text file, which Word and WordPad both open.

QuillLite chooses the kind from the file's name, and it is only ever a first
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
- **Enter on the status bar's Language cell** opens that same chooser, because
  the bar is where you notice the answer is wrong.

Moving between plain, Markdown and HTML changes **nothing in your document** —
it changes what the keys write from now on. Going to or from rich text is a real
conversion, and going *from* it throws the formatting away, so it asks first.

The choice lasts as long as the window. It describes what you are typing, not
what the file is.

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

### Saving an HTML page as Markdown

**Ctrl+Shift+S** offers **Markdown (*.md)** in its list of types, and in one
case that is a real conversion rather than a new name: if the document you are
saving is **HTML**, the tags are turned into Markdown as it saves. A heading
becomes `#`, bold becomes `**bold**`, a list becomes `-` lines, and links keep
both their text and their address. QuillLite says **"Converted HTML to
Markdown"** when it happens, and the document in front of you changes to match
the file -- the window and the file never disagree about what you just saved.

Tags Markdown has no way to write are dropped and their text kept, so nothing
you typed disappears. If the conversion would produce nothing at all -- a page
that is only a comment, say -- QuillLite keeps your text exactly as it was and
tells you so, rather than writing an empty file.

Saving a plain text or Markdown document as `.md` changes nothing at all: plain
text is already what it claims to be, and Markdown already is Markdown. A
**rich text** document is not offered Markdown, because turning real formatting
back into `#` and `**` means guessing which bold lines were meant as headings.
Save it as plain text first -- QuillLite asks before it drops the formatting --
and the Markdown row is waiting.

### If something goes wrong

While a document has changes you have not saved, QuillLite keeps a copy of it
aside, about every thirty seconds. That copy sits **beside** your file and never on top
of it.

If QuillLite or your computer stops unexpectedly, that work is offered back to
you the next time you start, in its own document.

Save it, or close normally, and the copy is deleted. So there is never anything
in there except work you actually need.

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
| **Ctrl+Shift+F2** | Special Character — search 1,400 of them by name |
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

**Edit ▸ Insert ▸ Special Character...** (**Ctrl+Shift+F2**) opens a picker for
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

**Enter inserts the character you are on**, and QuillLite **reads back what it
put in** -- "Inserted — U+2014 Em dash". That is not a nicety: most of this list
is invisible on the page, so without the read-back the command would be a
keystroke after which something you cannot see may or may not have appeared.

**The search box is also a code-point box.** Type `2014`, `U+2014` or `d8212`
and the em dash is the first result. A code point that is in no group at all
still finds its character, so the picker reaches everything Unicode has and not
only the 357 that are grouped.

QUILL has the same picker on **Shift+F2**, over the same list.

### Moving your settings to another computer

**Tools ▸ Back Up Settings...** (**Ctrl+Alt+Shift+Q**) writes your configuration
to a `.qsf` file. **Tools ▸ Restore Settings...** (**Ctrl+Alt+Shift+D**) reads
one back.

The file holds preferences, not a picture of this computer. Your recent-files
list, the session QuillLite restores at startup, the window size and the last
time it looked for an update are all **left out on purpose** — carrying them to
another machine would give you an editor pointing at files that are not there.
The backup tells you how many locations it left behind.

Restoring tells you what was different: how many settings came across, how many
have been added to QuillLite since the file was written (those keep their
defaults), and how many the file had that this version does not recognise. If
the file has nothing QuillLite recognises at all, nothing is changed — a wrong
file should not reset your editor.

QUILL has the same thing, on buttons in its Preferences window. The two products
use the same file extension but do not read each other's backups: they are
different editors with different settings.

### Ending a line without starting a paragraph

**Edit ▸ Insert ▸ Line Break** (**Shift+Enter**, the same chord Word uses) ends
the line you are on and starts the next one **without** starting a new
paragraph.

That distinction matters in Markdown and nowhere else is it visible. A blank
line between two lines makes them two paragraphs, which most renderers show with
a gap. A hard break makes them two lines of one paragraph, which is what you
want for an address, a verse, or a run of scene-break lines that should sit
tight against each other.

QuillLite writes the break in whichever spelling **Markdown line break style**
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
QuillLite says which character is wrong rather than quietly finding nothing: a
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
  folder; the list lives in QuillLite's own settings folder, keyed by the file's
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
| **Ctrl+Shift+M** | Set a mark here |
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

**Ctrl+Shift+L rings**, the way WordPad's own button does: bulleted list,
numbered list, no list, round again. Each stop says its own name, so you press it
until you hear the one you meant. In rich text the control draws the markers and
renumbers them for you; in Markdown it writes `- ` and `1. ` on the lines you
have selected — and only on those, never on the rest of the file.

| Key | What it does |
|---|---|
| **Ctrl+B**, **Ctrl+I**, **Ctrl+U** | Bold, italic, underline |
| **Ctrl+Shift+>** / **Ctrl+Shift+<** | Bigger / smaller text |
| **Ctrl+L**, **Ctrl+E**, **Ctrl+R**, **Ctrl+J** | Left, centre, right, justify |
| **Ctrl+Shift+L** | Lists: bulleted, numbered, none, round again |
| **Ctrl+1**, **Ctrl+5**, **Ctrl+2** | Single, one-and-a-half, double spacing |
| **Ctrl+Alt+1** to **Ctrl+Alt+6** | Heading 1 to 6 |
| **Ctrl+Alt+0** | Back to ordinary text |
| **Ctrl+Shift+D** | Describe the formatting where the cursor is |

They are gathered in **Format ▸ Headings**, where the digit in the menu is the
digit in the shortcut.

A heading is bold text at its own size — 20, 16, 14, 12, 11.5 and 10.5 point for
levels 1 to 6, with ordinary text at 11 point. These are the same sizes QUILL
for All uses, chosen so that a document you save here still reads as having
headings when somebody opens it in Word. Every level has a size of its own on
purpose: levels 5 and 6 used to share the 11-point body size, which meant
QuillLite could apply them and then could not find them again — heading
navigation and the headings list both walked straight past them.

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

### Hearing that you have arrived at one

Arrow onto a heading and QuillLite says **"Heading 2"**.

It has to, because your screen reader cannot. **No Windows edit control has
paragraph styles** — the control QuillLite hosts can tell JAWS or NVDA the font
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
`.ini`, `.yml` or `.conf` it is a comment, and QuillLite says nothing and lists
nothing — otherwise a build script would announce "Heading 1" on most of its
lines. In an HTML document it is neither: there the headings are `<h1>` to
`<h6>`, and QuillLite reads and writes those instead.

### Hearing that you are in a list

Arrow into a list and QuillLite says **"Bulleted list, 5 items"**. Go a level
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

With the cursor in a word QuillLite thinks is misspelled, press the
**Applications key** (or Shift+F10, or right-click) and the menu grows a
**Spelling** submenu at the top, named after the word: *Spelling: "wrold"*. One
**Down** arrow, then **Right**, and you are on the first suggestion; **Enter**
replaces the word. No dialog opens and the cursor does not move.

Everything about the word is in that one submenu, so the ordinary rows below it
-- Undo, Redo, Cut, Copy, Paste, Delete, Select All -- are in the same place
whether the word is misspelled or not.

Inside the submenu, under the suggestions:

| Row | What it does |
|---|---|
| **Ignore Once** | Skip this one place. Nothing is remembered after you close the window. |
| **Ignore in This Document** | Stop reporting this word anywhere in this document, until you close it. |
| **Add "word" to My Dictionary** | Keep it for good, in your own dictionary. |
| **Add to This Document Only** | Keep it beside this file, so anyone who opens the file gets it too. |
| **More Suggestions...** | The full list, in a window you can arrow through. |
| **Check Document...** | The F7 review, from here. |
| **Next / Previous Misspelling** | Move on without leaving the keyboard. |

Every row names the word it is about, so a menu you reached by keyboard still
tells you what it is going to do. On a word that is spelled correctly there is
no Spelling submenu at all -- just the ordinary edit rows.

Ignoring is honoured everywhere: a word you have ignored stops being announced
as you type, stops being a stop for **Ctrl+F7**, and stops being offered by
**Shift+F7**. To keep a word for longer than the session, add it to a
dictionary.

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
quite happily disagree about this. **Tools ▸ Spelling** shows a tick beside
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
| **Status Message** | The last thing QuillLite told you, so speech you missed can be heard again | repeats it |
| **Position** | Which line and column you are on, out of how many lines | Go to a line |
| **Word Count** | How many words the document has | repeats it |
| **Character Count** | How many characters, spaces included | repeats it |
| **Selection** | How much is selected, or "No selection" | repeats it |
| **Typing Mode** | Whether typing inserts or overwrites | switches between them |
| **Tab Mode** | Whether the Tab key types a tab or indents the line | switches between them |
| **Format** | Plain text or rich text | rings on to the next kind of document |
| **Heading** | Which heading you are inside | lists every heading |
| **List** | Which list you are inside, how many items, which one you are on | stops or resumes announcing lists |
| **Language** | Markdown, HTML, or plain text with no markup | change it |
| **Encoding** | How this file stores its letters and accents | change it |
| **Line Endings** | How this file marks the end of a line | change it |
| **Saved State** | Whether you have unsaved changes | saves |

Seven of these are worth pointing out.

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

**List** answers the question the speech deliberately does not. Entering a list
you hear "Bulleted list, 5 items"; this cell also tells you **which item you are
on** — "Bulleted list, 4 of 9, level 2". Saying that aloud on every arrow press
would be too much to listen to, and having no way at all to find out is its own
problem when you are halfway through reordering nine things.

**Language** is what decides the rest. It says whether this document is Markdown,
HTML or plain text, and that one fact decides what **Ctrl+B** writes, what the
heading keys write, which of the two tag pickers the Insert menu offers, and
whether the List part above has anything to say. QuillLite reads it from the file
name; **Enter** here says otherwise. See [Four kinds of
document](#four-kinds-of-document).

**Status Message** exists because speech is gone the moment it is spoken. If you
missed something QuillLite said, this is where you go to read it again.

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

The Windows clipboard holds one thing at a time. QuillLite gives you three ways
around that, in **Edit ▸ Clipboard**.

**The copy tray** is twelve numbered slots that survive closing the app. Copy
into a slot with **Ctrl+Alt+Y**, and paste from any of them an hour later with
**Ctrl+Alt+V**. **Ctrl+Alt+Shift+Y** empties it.

**Ctrl+Alt+Y** takes the next free slot, which is fine until you want to *choose*
the number — and choosing is the whole point of a numbered slot, because a number
you picked is one you can remember. **Alt+Shift+Y** offers all twelve, each row
saying what is in that slot now, so nothing gets overwritten unheard.

**The collector** gathers things up. Each **Ctrl+Alt+G** adds what you have
selected to one growing pile, and **Ctrl+Alt+Shift+G** pastes the whole pile.
This is what you want when you are pulling five quotes out of a long document.
**Ctrl+Alt+Shift+C** empties the pile.

**The clip library** is where clips you want to keep go. **Ctrl+Alt+M** keeps
what you have selected, and **Ctrl+Alt+Shift+M** opens the list to paste one back.

It can also fill itself. **Preferences ▸ Keep everything I copy in the clip
library** turns that on, and then every copy and every cut you make inside a
QuillLite document is added automatically, up to the last two hundred. It is off
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
the blank lines before the first line of text and after the last; QuillLite has
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
(**Ctrl+Shift+K**) and Title Case (**Ctrl+Shift+G**) are the ones you would
expect. **Sentence case** (**Ctrl+Alt+Shift+U**) puts a capital at the start and
lowers the rest, which is what a heading typed in shouting needs, and **Invert
Case** (**Ctrl+Alt+Shift+N**) swaps every letter, which is the cure for a
sentence typed with Caps Lock on.

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

**Alt+Shift+A** turns expansion off and on again, and **Tools ▸ Expand
Abbreviations** shows a tick when it is on. This is the one feature that acts
while you type, so the moment you want it off is usually the moment it has just
expanded something you meant to keep — which is too late to go looking for a
dialog. It is the same switch as the Abbreviations box in Customize Features,
reached in one keystroke.

---

## Finding a command

**Ctrl+Shift+P** opens a search box for commands. Type part of what you want —
"sort", "bookmark", "print" — and pick it from the list. You do not have to
remember which menu it lives in.

Each command shows its keyboard shortcut beside it, which is a comfortable way
to learn the keys over time.

---

## The window

QuillLite opens **maximized**, and after that it opens the way you left it. Make
it smaller and that size comes back next time; put it back to full screen and so
does that.

Maximized is the default because a small window is where text gets cut off and
where a list shows four rows on a screen with room for thirty -- and neither
costs anything to the person who chose the size. It is one keystroke to change
and QuillLite will not ask again.

Every app in the family behaves the same way now: QUILL, Quill Radio, Cast,
Weather, Audio Studio, Inkwell, the Converter, the Media Player and Beacon.

---

## Changing what a key does

**Tools ▸ Keyboard Manager** (**Ctrl+Alt+Shift+R**) is where every key in
QuillLite can be changed. The list has every command with the key it answers to;
type part of a command's name to find it, and press **Enter** on a row to give it
a different key.

### Finding out what a key already does

The other question is the harder one: *is this key free?* Press **Record a Key**,
then press the combination you are thinking of. QuillLite says what it does today
-- "Ctrl+S is File ▸ Save" -- or says it is free. That is faster and more
reliable than reading a list of two hundred rows.

### When a key is taken

Assigning a key somebody else already has does not silently steal it and does not
silently refuse. QuillLite names the command that owns it and asks. If you say
yes, that command is left with **no key** until you give it one -- which is the
honest outcome, because a key claimed twice means one of the pair never fires and
nothing tells you which.

### What cannot be changed

**Insert is never bindable.** It is the key NVDA and JAWS use as their own
modifier, and taking it would take away the key you would need to get it back.
QuillLite watches it go past -- that is what the Typing Mode cell reads -- but
never claims it. A key on its own with no Ctrl, Alt or Shift is refused too: it
would type itself instead.

### Putting things back

**Reset to Default** puts the command you are on back to the key QuillLite ships
with. **Reset Everything** does it for all of them, after asking. Nothing is
saved until you press **Save**, so Escape leaves your keys exactly as they were.

**Check for Problems** reports anything wrong with the set as a whole: a key
claimed twice, a key QuillLite cannot read, and -- the one you would otherwise
never find out about -- a key Windows will accept and then never actually send to
a menu, so it is assigned and inert.

Your changes live in your own settings folder and only what you changed is
written down, so a key we improve in a later version still reaches you.

---

## Making QuillLite smaller (or larger)

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

**Tools ▸ Sound Scheme** (**Ctrl+Alt+Shift+O**) is every sound QuillLite can
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
all on, and it cannot half-succeed -- the sounds QuillLite ships are never
overwritten, so getting back to them is always one press.

QUILL opens the same window over the same schemes, so a scheme you build in one
is offered in the other.

**Tools ▸ Customize Features** (**Ctrl+Alt+Shift+F**) lets you switch whole parts
of QuillLite off. Turning something off removes it from the menus **and**
unhooks its keys, so it is properly gone rather than just hidden.

That is how QuillLite stays small without being poor: you take out what you do
not want, rather than learning to ignore it.

### Profiles: four ways to say it in one word

The **Profile** box at the top is the short way. **Choosing one sets every
checkbox below, there and then** -- there is no second button to find. Nothing
is saved until you press **Save**, so you can look at what a profile would do
and change your mind.

Under the box is a **read-only description you can read line by line**, and it
answers two different questions. First, what the profile *is*, in its own words.
Then what it would actually *do* to the app in front of you: how many of the
18 areas it keeps and which, which ones it removes, and anything else it
changes -- Notepad, for instance, also makes **Ctrl+N** create a plain text
document. **F1** on the Profile box reads the same thing.

What is spoken when you choose a profile is the short version -- "Notepad
profile: 2 of 18 features on. New documents will be plain text." -- because your
screen reader is already reading the name and the description is there to be
read at your own pace.

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
lives. Preferences offers the whole answers; the 18 individual
checkboxes stay in Customize Features.

Here is what each one is, at a glance and then in full.

| Profile | Areas on | Ctrl+N makes |
|---|---|---|
| **Recommended** | 15 of 18 | plain text (unchanged) |
| **Everything** | 18 of 18 | plain text (unchanged) |
| **WordPad** | 5 of 18 | **rich text** |
| **Notepad** | 2 of 18 | **plain text** |

#### Recommended

**What a new install is.** 15 of the 18 areas: rich text, headings, Markdown and
HTML, bookmarks, the line tools, the clipboard history, printing, abbreviations,
the Selection submenu, spell check, Matches, Go Back and Go Forward, the Command
Palette, Describe Character and text size.

**Off:** autocorrect, timestamped backups, Go To Anything. Those three are not
missing features; they are the ones that would be *wrong* on by default rather
than merely unused. Autocorrect rewrites a configuration file's quotes. Backups
quietly fill a folder. Go To Anything is a fourth way to jump when the command
palette, the headings list and the bookmark list already cover it.

**Choose this** to get back to the shipped answer after experimenting.

#### Everything

**All 18 areas on**, including those three. Autocorrect will straighten
your quotes and capitalise your sentences, every save keeps a dated copy under
your data folder, and Go To Anything joins the palette and the two lists.

**Choose this** if you would rather turn things off as they annoy you than find
them one at a time.

#### WordPad

**What WordPad was.** Rich text you can format, print, and check the spelling
of: bold, italic, underline, headings, alignment, bullets, indenting and line
spacing, plus Find and Replace, printing and text size. Five of the 18
areas.

**Off:** the writing tools behind the formatting. No Edit ▸ Lines, no clipboard
history or Copy Tray, no bookmarks, no abbreviations, no Selection submenu, no
Matches list, no Back and Forward, no Command Palette, no Describe Character, no
autocorrect and no backups.

**Ctrl+N makes a rich text document.** That is the half of this name a list of
menus cannot say, and it is why choosing WordPad changes a setting as well as a
set of checkboxes.

**Not in real WordPad:** the spell checker. It is kept because a word processor
without one in 2026 is a surprise rather than a simplification.

**Choose this** for letters, notes and anything you want to look like something.

#### Notepad

**The smallest QuillLite gets**, and the one most people arriving here are
replacing something with. Two of the 18 areas: **printing** and **text
size**.

**Off:** the Format menu and everything under it, headings, bookmarks, the line
tools, Change Case, the clipboard history, abbreviations, the Selection submenu,
spell check, Matches, Back and Forward, the Command Palette, Describe Character,
autocorrect, backups and Go To Anything. Nothing Notepad does not have -- which
is the point of choosing it.

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

Seventeen checkboxes is a long way to Tab through, so the box below the profile
row filters them as you type. It matches what an area **does** as well as what it
is called, so typing "curly quotes" finds Autocorrect and typing "dictionary"
finds Spell check. The line under the box says how many are left, and **Down**
from the box moves straight into the list.

### The 18 areas

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
| **Autocorrect while typing** | Curly quotes, long dashes, sentence capitals | **off** |
| **Timestamped backups** | A dated copy kept every time you save | **off** |
| **Go To Anything** | One box that searches everything at once | **off** |

The last three start switched off, and they sit in this same list rather than
being hidden away, because something you cannot find might as well not exist.

Autocorrect is off because curly quotes are lovely in a letter and unhelpful in
a settings file. Backups are off because they quietly fill a folder. Go To
Anything is off because the command search, the headings list and the bookmark
list already each do their own part of the job.

Two things are never switchable, on purpose. **Tools ▸ Preferences** and
**Customize Features** stay, because switching off the menu that holds the switch
is a door that locks from the inside. And **File Encoding and Line Endings**
stays, because getting a file to save back byte-for-byte the way it arrived is
most of what a Notepad replacement is for.

---

## Settings

**Tools ▸ Preferences** (**Ctrl+,**) has everything in one place.

Seven settings live only there: what **Ctrl+N** creates, whether you start with
a blank document at all, how often unsaved work is copied aside, whether last
session's documents reopen, whether spelling is checked as you type, and whether
your abbreviations and your taught words are shared with QUILL for All.

**Start with a blank document** is on, the way Notepad and WordPad do it. Turn
it off if you always open an existing file: without it you are handed an empty
Untitled to close on every launch. Files you open by double-clicking, last
session's documents and recovered work all still appear either way. QUILL has
the same setting under **General**.

The rest are a keystroke away instead: dark mode and word wrap are on the
**View** menu, and the editor font is **Format ▸ Editor Font** — which is where
Notepad has always kept it, and which is the one row the Format menu keeps if
you switch rich text off.

**Dark mode is on by default.** It changes what you see and nothing else. The
colours are never written into your files, so a dark theme can never leave grey
text in a document you send somebody.

---

## Printing

**Ctrl+P** prints. **Ctrl+Alt+P** is Page Setup, and what you set there — paper
size, orientation and all four margins — is remembered for next time.

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

### If it says too much

Holding a key down can make QuillLite speak faster than anybody can listen.
**Preferences ▸ Shortest gap between spoken messages** sets a floor, in
milliseconds: anything it would say too soon after the last thing it said is
dropped. Zero, the default, says everything as it happens. Nothing is lost by
turning it up — the status bar is written either way, and **F6** reads it
back.

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

## Keeping QuillLite up to date

**Help > Check for Updates...** (**Ctrl+Alt+U**) asks whether a newer QuillLite
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

QuillLite also looks once a day when it starts, and says **nothing** unless
there is something -- not while it checks, not when there is nothing, and not
when the network is down. Only a genuine new version speaks, and even then it
only offers. Turn the daily look off in **Settings** ("Look for updates when
QuillLite starts"); Ctrl+Alt+U still works either way.

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
| **Ctrl+Alt+P** | Page Setup... |
| **Ctrl+P** | Print... |
| **Ctrl+W** | Close Window |
| **Ctrl+F4** | Close Window (MDI) |
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
| **Ctrl+Alt+Shift+T** | Tidy Whitespace |
| **Ctrl+/** | Toggle Line Comment |
| **Ctrl+Shift+Q** | Quote Lines |
| **Ctrl+Alt+Shift+Q** | Remove Quote Marks |
| **Alt+Shift+X** | Delete Lines Containing... |
| **Alt+Shift+W** | Hard Wrap Lines... |

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
| **Ctrl+Shift+M** | Set Mark |
| **Ctrl+M** | Pop Mark |
| **Alt+M** | List Marks |
| **Ctrl+Alt+X** | Exchange Cursor and Mark |
| **Ctrl+Shift+Y** | Say Selection |
| **Ctrl+Alt+Q** | Duplicate Selection |
| **Alt+Shift+U** | Review Buffer... |

### Edit ▸ Clipboard

| Key | Command |
|---|---|
| **Ctrl+Alt+Y** | Copy to Tray |
| **Alt+Shift+Y** | Copy to Tray Slot... |
| **Ctrl+Alt+V** | Paste from Tray... |
| **Ctrl+Alt+Shift+Y** | Clear Copy Tray |
| **Ctrl+Alt+G** | Collect Selection |
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

### Navigate

| Key | Command |
|---|---|
| **Alt+Left** | Go Back |
| **Alt+Right** | Go Forward |
| **Ctrl+Alt+H** | Next Heading |
| **Ctrl+Alt+Shift+H** | Previous Heading |
| **Ctrl+Alt+L** | List Headings... |
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
| **Ctrl+Alt+A** | Manage Abbreviations... |
| **Alt+Shift+A** | Expand Abbreviations |
| **Ctrl+,** | Preferences... |
| **Ctrl+Alt+F11** | Back Up Settings... |
| **Ctrl+Alt+F12** | Restore Settings... |
| **Ctrl+Alt+F10** | Customize Features... |
| **Ctrl+Alt+Shift+R** | Keyboard Manager... |

### Tools ▸ Spelling

| Key | Command |
|---|---|
| **F7** | Check Spelling... |
| **Alt+Shift+L** | List Misspellings... |
| **Alt+Shift+F7** | Spelling for This Word |
| **Ctrl+F7** | Next Misspelling |
| **Ctrl+Shift+F7** | Previous Misspelling |
| **Ctrl+Alt+F9** | Add Word to Dictionary |
| **Ctrl+Alt+F7** | Check While Typing |
| **Ctrl+Alt+Shift+F7** | Announcements... |

### Tools

| Key | Command |
|---|---|
| **Alt+Shift+M** | Quiet Mode |
| **Ctrl+Alt+Shift+O** | Sound Scheme... |

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

### Help

| Key | Command |
|---|---|
| **F1** | Help for This Window |
| **Ctrl+F1** | Keyboard Shortcuts |
| **Ctrl+Alt+F2** | Get Help from Support... |
| **Ctrl+Alt+U** | Check for Updates... |
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
written**, addressed to support, with QuillLite's name and version and your Windows
version filled in at the bottom. Nothing is sent until you send it there, so you
can read it over, add anything, or change your mind.

If this machine has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. And writing to **support@community-access.org** yourself always
works just as well: there is no form you have to use. Say which app you were
using and what happened.
