# QUILL 1.0.0 is here

## A writing suite for people who work by ear and by touch

*From Community Access. Free. AI only if you want it. Your documents stay on your
computer.*

QUILL is a complete writing and document program for blind and print-disabled
readers, writers, students, proofreaders and braille transcribers, and for anyone
who uses the keyboard instead of a mouse. If you write, read, proofread or
transcribe braille without looking at the screen, you know how most software goes:
the feature technically works, and using it wears you out.

QUILL was built the other way round. Every feature started with two questions: what
will you hear, and what will your fingers read? If a feature could not be made to
work well by ear, it was redesigned until it could, or it was left out. That is
what 1.0.0 is.

---

## It talks to you properly

Everything QUILL says goes out on four channels at once: speech, braille, sound and
the status line. Speech goes through your own screen reader, so you hear it in your
own voice at your own rate. QUILL works with JAWS, NVDA and Narrator on Windows, and
VoiceOver on macOS. While a screen reader is running, QUILL's own built-in voice
stays silent, so it never talks over you.

Sounds do some of the work too, and a sound never talks over your screen reader.
Starting a selection plays a rising two-note sound, and finishing it plays the same
two notes falling. The top of a document answers with a ceiling tick and the end
with a floor thud.

QUILL also tells you things your screen reader cannot. In an ordinary Windows edit
box, a heading is just a line and a nested list is just some dashes. So QUILL says
it for you: **"Heading 2, Installing"** when you arrive on a heading,
**"Bulleted list, 5 items"** as you enter a list, **"Level 2, 3 items"** one
level down, **"Out of list"** on the way out, and **"Table, 4 rows, 3 columns"**
when you walk into a table. This works in Markdown and HTML, for bulleted,
numbered and definition lists.
You hear the level even right after **Ctrl+Home**, when your screen reader starts
talking again. Each of these cues has a key that switches it off where you are, for
the times you are reading a document and do not need to hear its structure.

It helps you write markup other people can use, too. The HTML picker offers 111
elements and, above them, **twenty whole form controls**: a labelled dropdown, a
radio group in a fieldset with one shared name, a required field tied to its hint
and its error with `aria-describedby`. A `<select>` on its own is only half a
dropdown. The other half is a `for` that matches an `id`, and you cannot see it on
screen. QUILL writes both halves together, checks the `id` against the rest of your
document so a second field cannot quietly reuse it, and turns whatever you had
selected into the label. Both pickers search by what a thing does: "glossary" finds
a definition list, "subtitles" finds a caption track, and "error message" finds the
whole pattern for a checked field.

You decide how much QUILL says. There are four verbosity profiles, plus Quiet Mode
and Meeting Mode for when you need it to stop talking right now. The
**Spoken Echo** (**Alt+Shift+E**) keeps the last twenty announcements in a list you can
arrow through, and the **Announcement Self-Test** tells you which channels actually
reached you.

## The keyboard is the interface

QUILL has more than seven hundred named commands, and you can reach every one three
ways: from the menu bar, from the Command Palette (**Ctrl+Shift+P**), and from a
shortcut you assign. Nothing hides in a toolbar without a menu item. In the palette
you can type words in any order, or type a shortcut to find its command. Each
result is read with its shortcut, so you pick up the faster way as you go. The
status bar is a control panel too: arrow to any cell and press Enter to act on it.

## Braille files, kept exactly as they are

QUILL opens and saves `.brf`, `.brl`, `.pef` and `.ueb` files without changing
their bytes. Form feeds, line endings and layout come back out exactly as they went
in, and a round trip gives you an identical file. For a transcriber, that is what
matters most.

Text in QUILL starts in **braille cell 1**, not cell 2, fixing the offset that
RichEdit controls share with Microsoft Word. Selected text shows dots 7-8, so you
can feel your selection again. Both fixes are on by default, because braille
readers tried them and asked for them.

To back-translate a braille file in most programs, you have to know which code it
uses already, and a wrong guess gives you nonsense with no explanation.
**Back-Translate to Text (Auto-Detect Code)** does the guessing for you. QUILL
checks the file against every English braille code it knows and tells you the
winner, for example "Detected UEB Grade 2 (contracted)." Around it you also get print-page navigation,
page-by-page proofing status, layout checking and a report you can export.

> **QUILLBert found something.** He opened a braille file nobody had labelled,
> chose **Back-Translate to Text (Auto-Detect Code)**, and QUILL told him what code
> it was before he had even started guessing. He has been opening mystery files
> ever since.

## Every format, handled the right way

Plain text, Markdown, HTML, Word, RTF, OpenDocument, EPUB, PowerPoint, spreadsheets,
PDF, LaTeX, CSV, JSON, XML, braille formats, and images through OCR. The PDF and
spreadsheet readers come with every install, so a brand-new copy opens a PDF or an
`.xlsx` without downloading anything first.

Press **Ctrl+B** and you get bold the right way for the document you are in:
asterisks around a Markdown selection, `<strong>` in HTML, and real bold in Word or
RTF. Formatting sits beside your text as hidden codes. That is why search, spell
check, Read Aloud, bookmarks and braille all behave the same however much
formatting a document has. **Reveal Codes** (**Alt+F3**) shows every code and
reads it to you whenever you want. If you miss that feature from WordPerfect, it
is back, built for screen readers.

Changing a document's format really converts it. **Format > Document Format** moves
the document you are in between plain text, Markdown, HTML and Rich Text, and
everything comes with it: headings, bold, italic, underline, strikethrough, super
and subscript, fonts, sizes, colours, highlights, lists, links, code, quotes,
alignment, spacing, indents, named styles, page breaks, tables and images. Switch to
HTML and back a dozen times and you still have the document you started with. Rich
Text is written with Word's own styles, so a file you send opens in Word with real
Heading 1 and Quote styles.

Plain text has two sensible answers, so QUILL asks you which one you want. It can
take the `#` and `**` marks off for strictly plain text, or keep them as ordinary
characters. A .txt file is allowed to contain them, and plenty of people keep their
notes that way.

QUILL also tells you what it cannot do. If a Word file has features QUILL cannot
carry, it names them and asks how you want to go on. The first rich save over a
file like that makes a timestamped backup beside it. QUILL never quietly rewrites a
complex file and leaves you hoping everything survived.

## Reading, speaking and dictating

Read Aloud speaks the whole document, a section or a selection, and leaves out
Markdown punctuation so you hear words, not a string of hash marks. Voices include
Windows SAPI 5, DECtalk, eSpeak-NG, the local neural engines Piper and Kokoro, the
macOS system voice, and optional cloud voices with your own key. Audiobook and
Batch Speech turns a whole folder into chaptered audio, with real MP3 chapter
markers and ACX loudness normalization.

Dictation runs **on your own machine**, using whisper.cpp, Faster Whisper, Vosk or
NVIDIA's Nemotron. A model manager checks your actual RAM and GPU before it
recommends one. Your audio is saved before transcription starts, so a failed
transcription never costs you a session.

## AI, only if you want it

QUILL's AI is optional. It stays off and silent until you set it up, and if you
never do, no menu nags you. If you do, the setup wizard shows you the free ways
first. Run Ollama and everything happens on your own computer at no cost. Or pick
OpenRouter, where the wizard chooses a free model for you and marks every free
model "Free." QUILL bundles no keys and takes no cut.

One rule runs through every AI feature: **the AI proposes, you dispose.** Every
suggested edit stops at a review dialog you can judge by ear. Each change is
announced as what it is, and you can hear the sentence before and after it, so you
get the same context a sighted reviewer gets from a highlight. Nothing touches your
document until you agree, and then the change is one undo step. QUILL never quietly
changes which AI is answering you, and never switches between the cloud and your
own computer.

## Your work is safe

A writing tool that loses your work, or does something other than what it said, is
worse than none, and more so when you cannot glance at the screen to catch it.
Autosave keeps copies of your documents all the time, formatting included. Saves
are atomic, so a save is either complete or not done at all. Undo survives from
one session to the next. If your screen reader stops in the middle of a session,
QUILL saves a copy of every open document straight away, then tells you what
happened with whatever can still talk.

QUILL runs on your own computer. It opens your files from your disk and writes them
back to your disk, and it does not upload your documents. Every feature that uses
the internet is optional, asks before you use it the first time, and is turned off
in **Safe Mode**. Safe Mode starts QUILL with extensions, AI and network features
all switched off.

## Start where you want to start

The first time you open QUILL, it asks one question: what kind of writing do you
do? Your answer picks a feature profile, from Just a Text Editor through Writer,
Braille Professional and AI-Powered Author to Full QUILL. Before you choose, you
hear a plain description of what each one turns on. You can switch profiles at any
time or turn any single feature on or off. If something you read about here is not
on your menus, choose **Help > Why Don't I See a Feature?**

Install QUILL with the Windows installer, unpack the portable ZIP onto a USB stick,
or take the Offline Edition, which carries every optional part inside it for a
computer with no internet connection. macOS builds are notarized and Developer-ID
signed.

## Or take the small one

Not everybody wants a writing suite. **QUILL Lite** is QUILL's editor on its own:
about the size of Notepad, made for screen readers, and a separate download that
installs beside QUILL with its own settings. It has the same keys, the same status
bar you can actually read, and the same help when you press **F1**.

One rule holds the two together: **QUILL Lite is never allowed to be ahead of
QUILL.** Anything QUILL Lite can do, QUILL can do too, in the same release. A
twenty-nine item pass made that true both ways. The two keyboards now use the keys
Word, WordPad and Notepad already taught you. A check found and fixed 170 menus
that offered the same Alt letter twice. And QUILL picked up four things QUILL Lite
had first, including spelling suggestions that spell themselves out as you arrow
through them.

If you use both, they can share one setup. **Bring My QUILL Lite Settings** copies
your preferences and changed keys into QUILL, and from then on the two share your
abbreviations, dictionary, copy tray, clips and bookmarks, so a change in one is a
change in both. It tells you what it will do before it does it, and it replaces
nothing you already had.

## Thank you

QUILL is free, and the people who use it helped shape it. The ranked spelling
workflow came from a longtime Kurzweil 1000 user's side-by-side comparison. The
braille cell fix became the default because braille readers tested it and told us.
The Offline Edition works with no connection at all because someone checked that
promise instead of trusting the label.

If something surprises you, good or bad, please tell us. Choose
**Help > Get Help from Support...** (**Ctrl+Alt+F2**). It opens a message to
support@community-access.org in your own mail program. (It used to be called
**Report a Bug**.) A message that says "this works perfectly" helps as much as one
that says it does not.

The full QUILL 1.0.0 release notes go through the editor feature by feature, and
cover the companion apps that come with it too.
