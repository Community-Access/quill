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

### The rest, briefly

- **Numbered documents** in one window — Alt+1 through Alt+9, and a Window menu
  that lists them all
- **Bookmarks** - nine of them, and a list you can jump from
- **A copy tray and a clip history**, because one clipboard is not enough
- **Abbreviations** — type a short form, get the long one
- **Structural selection** — a word, a line, a sentence, a paragraph, a block,
  each in one keystroke
- **Line tools** — move, duplicate, join, sort, number, de-duplicate
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
