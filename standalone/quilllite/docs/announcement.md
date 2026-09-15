# QuillLite: the small editor that actually talks to you

**A free, simple text editor for Windows, built from the ground up for people
who use a screen reader.**

If you have ever wanted Notepad to just *tell you things* — which line you are
on, what that file's encoding is, whether the word you typed is spelled right —
this is that editor.

It is free, it is open source, and it installs in about a minute.

---

## The short version

You already know how to use it. Ctrl+O opens. Ctrl+S saves. Ctrl+F finds.
F3 finds the next one. Every key Notepad and WordPad have had for thirty years
does exactly what it has always done.

What is different is that QuillLite **answers**.

- Press **F6** and you land in a status bar you can read, cell by cell: the line
  you are on, the word count, the encoding, the line endings.
- Press **F1** anywhere and it tells you what window you are in and what the
  control you are on actually does.
- Press **Ctrl+F1** and every keystroke it has is in one searchable list.
- Type a word wrong and you hear a short, quiet sound — then press one key and
  it **spells the word out for you**, because "receive" and "recieve" sound
  identical and only the letters can tell you which one you typed.

Nothing is hidden behind a menu you have to go hunting through. Nothing waits
for you to notice a red squiggle you cannot see.

---

## Why we built it

QuillLite is the editor from **QUILL for All** with everything else taken out.

QUILL is a full writing environment, and for a lot of people that is exactly
right. For a lot of other people it is more than they wanted when all they
needed was to open a file, fix a line, and save it. Those people were reaching
for Notepad — and Notepad tells a screen-reader user almost nothing.

So: the same accessibility work, the same careful thinking about what to say and
when to stay quiet, in an editor that opens instantly and gets out of your way.

You can install both. They sit side by side and neither touches the other's
settings.

---

## What you get

### It sounds like something

QuillLite makes a short, quiet sound when things happen that your screen reader
says nothing about — a cut, a copy, a paste, an undo, a document saved, a
document closed. These are the moments where speech tells you nothing because
nothing moved and nothing gained focus, and where silence has always meant
guessing.

Every one of those sounds can be **changed, replaced with a file of your own, or
switched off**, in a window that plays each sound as you arrow through the list.
And **Alt+Shift+M** silences all of them instantly, for when you are on a call
or in a quiet room. Press it again and they come back.

### It tells you the shape of what you are reading

Arrow onto a heading and QuillLite says **"Heading 2, Installing"**. Arrow into
a list and it says **"Bulleted list, 5 items"**. Go a level deeper and it says
**"Level 2, 3 items"**. Arrow out and it says **"Out of list"**.

Your screen reader cannot tell you either of those, and it is not failing. The
text box every Windows editor is built on — Notepad's, WordPad's, ours — can
pass on the font and the size and has no way at all to say "this paragraph is a
heading" or "this is a list of five". On a web page your reader tells you both,
because the *browser* hands it both. In an editor a heading is a line and a list
is some dashes, and nobody says anything.

So QuillLite says it. Both cues stay narrow on purpose — once, on arrival,
never while you move about inside the thing you have already been told about —
and each has a key that turns it off where you stand, because whether structure
is what you are listening for depends on whether you are writing the document or
reading it.

### It knows Markdown and HTML, and writes them for you

Open a `.md` and press **Ctrl+B** with a word selected: you get `**word**`.
Open a `.html` and press the same key: you get `<strong>word</strong>`. The
heading keys write `## Installing` or `<h2>Installing</h2>`. Open a `.py` and
those keys politely decline, because a Python file has no markup and putting
asterisks in one would be a small disaster nobody could see.

There is a searchable picker for each — 111 HTML elements and the whole Markdown
vocabulary, both looked up by what they *do* rather than what they are called
("glossary" finds a definition list, "subtitles" finds a caption track) — and
the one your document cannot use is greyed out rather than hidden, so you are
told rather than left hunting.

And the HTML picker inserts **whole form fields**, not tags. Choose a dropdown
and you get the label, the field, the options, and a `for` that actually points
at the right `id`. Choose a radio group and you get a fieldset, a legend, and
three buttons that share a name — which is the difference between a group and
three unrelated buttons that can all be on at once. None of that wiring is
visible, which is exactly why it gets left out, and exactly why it should not be
left to memory. Select a word first and it becomes the label, with the `id`
built from it so the two always agree.

### An emoji picker you can actually use

Every emoji picker ever made is a wall of little pictures, which is precisely
the one control shape that cannot be used without sight. **Alt+.** opens a list
instead: search by name, by keyword, by a typed smiley (`:)` finds the smiling
face), or browse by category — and every single one comes with a **written
description of what it actually shows**. Insert one and QuillLite tells you
which one went in, by name.

### Spell check that tells you what is actually wrong

Being told "recieve is misspelled" is being told a word that sounds exactly like
the correct one. The letters are the answer, so QuillLite spells them — after a
short pause, as a separate thing it says, so if you already knew you can press
the next key and never hear it.

You choose how: plain letters, the phonetic alphabet ("romeo, echo, charlie" —
which is unambiguous when B, D, E, P, T and V all sound the same through a fast
synthesiser), or both. You choose whether capitals are named. You choose how
long each pause is, and there are separate pauses for the three places it
happens, because moving through a document quickly and stopping to decide are
not the same thing.

Land on a misspelled word and press the **Applications key**: the corrections are
right there at the top of the menu, one Down arrow away. Under them, everything
else you might want — ignore it once, ignore it in this document, add it to your
dictionary, or add it just for this file.

### Your file comes back exactly as it went in

Encoding, byte order mark, line endings, the final newline — all of it survives
a round trip. If you open a file somebody sent you and save it again without
changing anything, it is byte-for-byte the same file. That matters more than it
sounds like it does, and most editors quietly get it wrong.

**Tools ▸ File Encoding and Line Endings** shows you what those actually are, and
lets you change them deliberately. Almost nothing else will tell you.

### Make it exactly as big or as small as you want

QuillLite has seventeen switchable areas and four one-word answers:

- **Notepad** — two areas. No formatting, no bookmarks, no line tools. Ctrl+N
  makes a plain text file. If you are replacing Notepad, choose this.
- **WordPad** — bold, italic, headings, alignment, bullets, printing, and a
  spell checker WordPad never had.
- **Recommended** — what a fresh install is.
- **Everything** — all of it.

Choose one and every switch below it moves. Pick **Custom** and they go back to
how you found them. The window tells you, in a box you can read line by line,
exactly what each profile keeps, what it removes, and what else it changes —
worked out from the actual feature list, so it can never be out of date.

### If something goes wrong, you write to a person

**Ctrl+Alt+F2** — Help > Get Help from Support... — opens a short form and then
your own mail program, with the message already written and QuillLite's version,
your Windows version and your screen reader filled in at the bottom. It goes to
**support@community-access.org**, where a person reads it and replies to you by
email.

Not a bug tracker. Not a public issue thread you need an account to join, with
your configuration and your document's name in it forever. An email, to somebody
who answers. Your address is optional — you can report a problem without giving
one, you just cannot then be replied to — and nothing is sent until you send it
yourself.

### And it tells you when there is a new version

**Ctrl+Alt+U** asks. If there is nothing newer it says so, out loud and in a
dialog, because a key that answers with silence might as well be broken.

If there is, the window opens on **what changed** — the release notes, in a box
you can arrow through — with **Update** and **Close** beside them. Your focus
lands in the notes, so the first thing you hear is what is in the release rather
than the word "Update". Update downloads it and offers to install and restart
for you; everything you have set is kept. Nothing downloads until you say so.

It also looks once a day when it starts and says nothing unless there is
something — not while it checks, not when there is nothing, not when the network
is down. One tick box in Settings turns even that off.

### The rest, briefly

- **Numbered documents** in one window — Alt+1 through Alt+9, and a Window menu
  that lists them all
- **Bookmarks** - nine of them, and a list you can jump from
- **A copy tray and a clip history**, because one clipboard is not enough
- **Abbreviations** — type a short form, get the long one
- **Structural selection** — a word, a line, a sentence, a paragraph, a block,
  each in one keystroke
- **Line tools** — move, duplicate, join, sort, number, de-duplicate
- **Four kinds of document in one key** — plain text, Markdown, HTML, rich text,
  and Ctrl+Shift+M rings between them, each saying its own name
- **"What is this character?"** — the difference between a hyphen, an en dash
  and a minus sign, which a screen reader reads identically
- **It looks after work you have not saved**, and reopens what you had open
- **Dark mode by default**, because the people this is for are disproportionately
  light-sensitive and a first launch that is bright white is one some of them
  cannot read

---

## Getting it

Download from the releases page. There are four files; you want the first one
unless you know otherwise.

| Download | Take this if |
|---|---|
| `QuillLite-Setup-Shared-<version>.exe` | You want the normal installer. |
| `QuillLite-Lite-Setup-<version>.exe` | You already have another QuillVille app. |
| `QuillLite-Portable-<version>.zip` | You want it on a USB stick. |
| `QuillLite-Companion-<version>.zip` | You already have the QuillVille runtime. |

Windows may warn about the installer until code signing is finished. Choose
**More info**, then **Run anyway**.

Installing offers *Open .txt and .rtf files with QuillLite* as an **optional**
extra. It adds QuillLite to the Open With list and **never** makes itself the
default — Notepad, WordPad and QUILL stay exactly where they were.

---

## One minute to your first document

1. Open QuillLite. You are in a blank document, ready to type.
2. Type something.
3. Press **Ctrl+S**.

That is the whole thing. Everything else is there when you want it and silent
until then.

If you would rather *not* start with a blank document — because you always open
an existing file and were closing an empty one every time — there is a setting
for that in Preferences.

---

## It is free, and it is yours

QuillLite is MIT-licensed and open source. No account, no subscription, no
telemetry, nothing phoning home. Your settings and your recovered work live in a
folder on your machine, and uninstalling does not delete them.

If it does something wrong, or does not do something you need, please say so.
Every single thing in this release exists because somebody said so.

- **Download and source:** https://github.com/Community-Access/quill
- **The full guide:** `docs/userguide.md`
- **What changed:** `docs/CHANGELOG.md`

---

## Please pass it on

If you know somebody who has been putting up with an editor that does not talk
to them, send them this. That is the entire point.
