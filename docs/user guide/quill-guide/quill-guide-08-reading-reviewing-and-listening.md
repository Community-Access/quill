# Chapter 8: Reading, reviewing and listening

This chapter is about taking things in rather than typing them. You will
have QUILL read your document to you, look closely at text you did not write,
see the formatting that normally stays hidden, and compare two versions of a
file. Later on it covers turning documents into audiobooks, and keeping your
place in everything you listen to. Start with Read Aloud. The rest is there
when you need it.

## Read Aloud

Read Aloud speaks your document in a voice of your choosing, separate from
your screen reader. It is handy for proofreading by ear, for resting your
ears from a fast screen reader voice, or for simply listening to a long piece.
You can start, pause, stop, preview, and choose a voice.

### Starting and stopping

Everything for listening lives on **Tools > Reading and Dictation**:

- **Read Aloud** is a submenu:
  - **Start / Pause** (press the QUILL key, then `R`) starts reading from the
    cursor, and pauses or carries on when you press it again.
  - **Voice...** and **Settings...** choose the voice and how fast, how loud
    and how high it speaks.
  - **Generate Audio...** saves the reading as a sound file instead of
    playing it, described below.
  - **Announcement Backend...** chooses how QUILL's own short messages reach
    you: automatically, through your screen reader, or on the status bar only.
  - **Announcement Trace (in Settings)...** opens Settings at the switch that
    keeps a record of QUILL's announcements. It is only useful when support
    asks you for it, and it never records your document.
- **Stop Reading** (press the QUILL key, then `Shift+R`) stops the current
  reading straight away.
- **Say Selected** (`Ctrl+Shift+Y`) reads the text you have selected.
- **Read All** (`Alt+F8`) reads from the cursor to the end of the document.
- **OCR Image...**, **OCR Clipboard Image** and **OCR Screen Capture...** turn
  a picture of text into text you can read. There is more on them under OCR
  Image, later in this chapter.

**Generate Audio...** makes a recording of your document in your Read Aloud
voice. It uses the selection if you have one, and the whole document if you do
not. Choose a name and a type in the save window: a Wave file always, and MP3,
M4A, M4B audiobook, OGG, Opus or FLAC as well when the free ffmpeg tool is on
your computer. Making audio from your documents, later in this chapter, covers
the bigger jobs.

There is one setting worth knowing about. **Move cursor to follow Read
Aloud** (in **Settings > Read Aloud**) makes the cursor select each sentence
as it is read, so the caret tracks what you hear and stops where the reading
stopped. It is **off by default**. With a screen reader running, moving the
selection makes the screen reader say "selected" over the Read Aloud voice.
If you are sighted or have low vision and want the cursor to follow along,
turn it on.

The rest of the **Read Aloud** page in Settings tunes the voice:

- **Read Aloud engine** chooses which speech engine reads. Choosing a voice,
  below, explains them.
- **Read Aloud rate** is the speed of the Windows voice in words per minute,
  from 80 to 450. The default is 200.
- **Read Aloud volume** runs from 0 to 100. The default is 100.
- **Read Aloud pitch** runs from 0 to 100. The default is 50.
- **Read Aloud sentence pause (milliseconds)** adds a pause between
  sentences, up to two seconds. The default is no extra pause.
- **ElevenLabs Read Aloud voice** and **ElevenLabs Read Aloud model** are used
  when the engine is ElevenLabs. Pick a voice in the Voice Browser rather than
  typing one; left blank, ElevenLabs uses its default voice and model.
- **AI Voice provider**, **AI Voice model** and **AI Voice** choose the cloud
  voice used by Read Aloud with AI Voice and by audio export: **OpenAI** (the
  default), **Google Gemini**, or **ElevenLabs (export only)**. Leave the
  model and voice on **Provider default** unless you have a favourite.

### Choosing a voice

Read Aloud uses voices on your own computer. The Windows system voice runs on
**SAPI 5**. It is always there, works offline and needs no download, so Read
Aloud works the moment QUILL is installed. **eSpeak NG**, **Piper**, and
**Kokoro** (neural, offline) are extra downloads from Speech Center, which
keeps the installer smaller. **DECtalk** works if you have installed it
yourself; QUILL no longer downloads or distributes it, because its
redistribution terms are unclear. Before any download starts, QUILL
tells you what is available right now and what it suggests you do next. For
cloud voices, see Read Aloud with AI Voice, which covers OpenAI and Google
Gemini voices.

The **Kokoro** voice models (about 120 MB) and the **eSpeak NG** engine with
its voice data (about 40 MB) are not in the installer. The first time you choose one of these voices,
QUILL downloads it for you from its own verified source. The download is
checksum-checked and has a progress window you can cancel. Your other voices,
including the SAPI 5 system voice, keep working while it downloads. If you
are upgrading from a version that bundled these, your existing copies are
kept and keep working, so there is nothing to download.

### Phonon voices

**Phonon** is a newer neural voice that comes with QUILL, so there is nothing
to download. It has 37 English voices plus its own default voice, and it runs
entirely on your computer. It starts talking quickly, which you notice most
when you press a key and want to hear something now. It reads numbers, dates
and email addresses well on its own.

Pick it in **Manage Voices** like any other engine, choose a voice, and press
**Preview** to hear it. The speed control goes from 0.85 to 1.3 times normal.
That is a narrower range than Kokoro's, because Phonon starts to fall apart
past it, and QUILL would rather tell you than let you pick a speed that sounds
broken. QUILL remembers your choices as `read_aloud_phonon_voice` and
`read_aloud_phonon_speed`.

Phonon needs a processor from about 2015 or later (one with AVX2). On an older
computer the voices are still listed, marked "needs a newer computer", and
choosing one tells you so and suggests Piper, which runs almost anywhere.
Phonon never sends your text anywhere.

Phonon 31m is by Gradium and is free under the Apache 2.0 licence. Phonon
builds on Pocket TTS and the Mimi codec, developed by Kyutai. QUILL offers no
voice cloning, and the voices should not be used to pass speech off as a real
person's.

**Manage Voices** is the **Speech (Offline)** tab of the Speech Settings
dialog. It lists SAPI 5, DECtalk, Piper, Kokoro, Phonon, and eSpeak NG. ElevenLabs,
the only cloud voice, has its own **Speech (Online)** tab, so local and cloud
voices are never mixed in one list. The **Set as Default** button (also on
the voice list's right-click menu) applies your engine and voice choice at
once, without closing the dialog with OK.

To hear a voice before you choose it:

1. In **Manage Voices**, select the voice.
2. Press the **Preview** button.

If the voice is already downloaded, QUILL speaks the preview phrase with that
voice's real model. If it is not downloaded yet (a Kokoro voice, for
example), QUILL plays a short pre-recorded sample so you can still hear it
before you decide. The rate, volume, pitch, and speed controls only apply to
real speech, so they stay dimmed until the voice is downloaded.

Starting a new preview stops the one already playing, so previews never
overlap. Some neural voices take a moment to get going. While they do, QUILL
plays a short earcon and, by default, says "Generating preview, please wait".
You can turn either off on its own: the earcon in **Tools > Reading and
Dictation > Sound Scheme...**, and the announcement in **Settings >
Accessibility and Announcements**. While a preview is generating or playing, the Preview/Test
button becomes a Stop button, so you can cancel it at any time.

### Voices in other languages

Read Aloud speaks more than English. The Windows engine lists every voice
installed on your PC, in any language. Add one in Windows Settings under
**Time & language > Speech > Manage voices** (Italian's Elsa, say, or a
Spanish, French, German, or Japanese voice) and it appears in QUILL's voice
list, ready to use, with nothing to download from QUILL.

The offline neural voices go further too:

- **Kokoro** includes **Spanish, French, Hindi, Italian, and Brazilian
  Portuguese** voices. They are part of the voice pack you already
  downloaded, so picking one just works.
- The **Piper** catalog includes Italian voices (Paola and Riccardo) that you
  download like any other.
- **eSpeak NG** offers those languages from its built-in data.

Pick the voice whose language matches your document, and Read Aloud,
audiobook export, and batch speech all speak it correctly.

### Text cleanup for speech

Real documents are full of typography that trips up speech engines. The
optional **text cleanup** pass (turn it on in Read Aloud settings) fixes
curly quotes, em and en dashes, ellipses, invisible spaces, ligatures,
bullets, symbols, fractions, and emoji, the same way every time. It also
speaks **phone numbers, emails, and URLs** clearly. For each type you choose
whether to announce it, speak it, or speak it and then repeat it, which makes
an address easy to catch. Cleanup runs first, before anything else, so live
Read Aloud and batch export sound the same.

### Teaching QUILL how to say a word

**Tools > Speech > Manage Pronunciations...** teaches QUILL how to say
particular words: names, brands, acronyms, and technical terms. Each entry
is a substitution, either literal or a regular expression, and can be
case-sensitive. QUILL applies it silently to the text just before speaking,
so a correction is heard everywhere speech happens, in batch export and live
Read Aloud alike.

- A dictionary can be **global** (all projects) or belong to one **project**.
- An entry can target a specific engine.
- You can **preview** an entry to hear the result.
- A small **starter dictionary** already covers common terms.

### SSML Builder and SSML playback

For fine control over how a passage is spoken, the **SSML Builder** dialog
writes `<speak>` markup for you from ordinary controls: emphasis, pauses
(`<break>`), say-as, phonemes, and prosody. A read-only preview shows the
markup it made, so you never type the tags yourself. Read Aloud plays this
markup **natively on SAPI 5 and eSpeak NG**, so the pauses and emphasis
happen instead of being read out.

### Read Document in Browser (experimental)

Your web browser has voices QUILL's own engines cannot reach, including
Microsoft Edge's "Online (Natural)" voices. This optional feature reads your
document with them.

To turn it on:

1. Open **Settings > Experimental**.
2. Check the acknowledgement box.
3. Turn on **Read the document aloud in your browser**.
4. Apply Settings. It works straight away, with no restart.

A **Read in Browser (Experimental)** item then appears under **Tools > Reading
& Dictation > Read Aloud**, and the command palette gains **Read Document in
Browser (Experimental)**.

When you use it, QUILL writes a self-contained, accessible reader page and
opens it in the browser you chose under **Settings > General > Preview browser**. The page
has:

- a labelled **Voice** picker. Each voice is marked "on this device" or
  "online", and the list is filtered to your QUILL display language. Check
  **Show all languages** to see the rest.
- a **Speed** slider.
- **Play** and **Stop** buttons.

Focus lands on Play, changes are announced through a live region, and
**Escape** stops. Reading goes section by section, so even a book-length
document stays reliable. **Pause** keeps your place and tells you where you
are ("Paused at section 12 of 300"), and resuming carries on from that
section. **Stop** goes back to the top. Your voice and speed are remembered
between sessions, and the document text carries your display-language tag so
a screen reader reading the page pronounces it correctly.

About privacy: QUILL itself makes no network call, and no audio file is made.
Voices marked "on this device" speak locally. The browser's "Online
(Natural)" voices are made in the voice company's cloud, so choosing one
sends the text being read to that service. Pick an on-device voice to keep
everything local. The reader page holds your document text. It is written to
QUILL's app-data folder and deleted when you close QUILL, so no plain copy is
left behind.

### Voice commands on the same menu

The Speech menus also hold QUILL's voice commands. They are listed here so
you know what they are when you meet them. Chapter 9, Dictation and
transcription, covers them properly.

- **Voice Command (Offline)** (**Tools > Speech**) is push-to-talk for QUILL.
  Run it, speak one command such as "save file", "word count" or "next
  heading", then run it again to stop and act. Recognition happens entirely
  on your computer with the offline speech engine, and only a safe list of
  non-destructive commands can ever run, so a misheard phrase cannot do
  damage. Say "cancel" or "never mind" to give up. Turn it on with the
  **Voice commands (push-to-talk)** setting. It is off by default and always
  off in Safe Mode.
- **Voice Conversation Mode** (**Tools > Speech**) is the hands-free version.
  Run it once and QUILL listens for a command, then keeps a short
  **follow-up window** open after acting, so you can chain commands ("next
  heading", then "read aloud", then "word count") without arming it again.
  A sound marks every state: a rising chime when conversation mode starts, a
  soft two-note when the microphone opens, a gentle rise when your command is
  recognized (with a brief moment to say "cancel" before it runs), a sparkle
  when the action finishes, a quiet tick while QUILL is working, and a calm
  falling tone if nothing matched. Run it again, or say "stop", to turn it
  off. The nine cues are **Sound Events** you can retune or replace in any
  sound pack. Four settings let you pace it to your own rhythm: the pause
  that ends a command, the cancel window, the follow-up window, and the
  "still working" tick interval. Set any of them to 0 to switch that part
  off. It uses the same on-device recognition and the same safe list as
  Voice Command, and is also off in Safe Mode.
- **Listen for Hey QUILL** (**Tools > Speech**) turns on always-listening.
  QUILL listens continuously, on your computer, for the phrase "Hey QUILL".
  Say "Hey QUILL, save file" to run a command straight away, or just "Hey
  QUILL" to start one. The status bar shows that the microphone is live and
  plays a reminder now and then, so an open microphone never takes you by
  surprise. Run the command again, or say "stop", to end it. The **Listen for
  'Hey QUILL' (wake word)** check box on the Transcription page of Settings is
  the same switch, so turning it on in either place turns it on in both; check
  it and press OK, and QUILL starts listening straight away. If voice commands
  are off, QUILL tells you and leaves the box unchecked. Normally listening
  stops when you close QUILL, so the microphone is never on by surprise the
  next time. Turn on **Keep listening for "Hey QUILL" across restarts** and
  QUILL picks up listening again when it starts. Off in Safe Mode.
- **Speak Voice Status** (**Tools > Speech**) tells you what the voice
  features are doing right now: whether QUILL is listening for "Hey QUILL",
  whether conversation mode is on, and whether it is listening for a command.
  When none of them is, it says "Voice is not listening right now", which is
  the quick way to be sure the microphone is closed.
- **Ask a question by voice.** In conversation or wake mode, if you speak a
  question rather than a command (starting with "ask", or shaped like a
  question, such as "how do I save my document"), QUILL opens **Ask QUILL**
  with the question filled in and ready to send. You press Enter to send it,
  so a person always decides what reaches the AI. This needs AI set up.
  Questions are the only thing voice ever sends to a network service, and
  never on their own.

For the complete reference (every voice mode, every spoken command, and the
privacy rules) see [Voice Interaction](../voice-interaction.md).

## Reading without changing anything: the Read-Only Guard

When you open a document only to read it, such as a manual, a long book or
minutes you must not alter, one stray key can change it, and a `Ctrl+S` later
saves the change. The **Read-Only Guard** locks the document against edits
while you read.

Press `Ctrl+Alt+Backspace`, or choose **Tools > Advanced > Toggle Read-Only
Guard**. You hear "Document is read-only". Press it again to hear "Document is
editable".

While the guard is on:

- Typing, `Backspace`, `Delete`, `Enter` and pasting do nothing.
- Commands that change text say "Document is read-only" on the status bar and
  change nothing: snippets, the line tools, case changes, Copy Tray pastes,
  Markdown and HTML inserts, and a thesaurus or dictionary **Replace**, among
  others. They stop *before* they say anything, so you never hear "Inserted
  snippet" about a snippet that was not inserted.
- Reading and moving work as always: the arrow keys, Find (`Ctrl+F`), Go To
  (`Ctrl+G`), browse-mode navigation by heading, paragraph and link, selecting
  and copying, Read Aloud.
- **Bookmarks** work as usual. They are kept beside the document, not inside
  it, so setting one never changes the file.
- **Document notes** work too. A note you add with **Add Inline Note**
  (`Alt+Shift+I`) while the guard is on is kept beside the file instead of
  written into it, and `Alt+Shift+J` and `Alt+Shift+K` still move between
  notes.

QUILL **remembers** the guard for that file. Close QUILL, open the same file
tomorrow by double-clicking it in File Explorer, from **Open Recent** or with
`Ctrl+O`, and it opens locked again, even if File Explorer spells the folder
with different capitals. QUILL Lite has the same guard on the same key, with
its own list.

If QUILL cannot write down that you locked the file, for example because its
settings folder is on a full disk, the document is still locked for now and
you hear why:

> Document is read-only for now, but it could not be remembered for next time
> (There is not enough space on the disk).

An untitled document cannot be remembered either, because it has no file name
yet. Save it first if you want the lock to stay.

A file Windows marks read-only, or one on a share you cannot write to, opens
locked as well, and QUILL says so as it opens. Turn the guard off to type
anyway, then save under a new name.

**Long documents.** Locking a document does not make it open faster: the text
still has to be put into the editor, which for an eight-megabyte book takes
about four tenths of a second on a fast computer. What the guard does speed up
is moving around. Because a locked document cannot change, browse-mode keys
(next heading, next paragraph, next link) read QUILL's own copy of the text
instead of copying the whole document out of the editor on every key. On that
eight-megabyte book a heading jump went from about 46 milliseconds to well
under one.

## Tools for Reading, Review, and Inspection

These tools help when a file is hard to read, or when you need to know
exactly what is in it. They answer questions like "which kind of space is
that?", "where does the bold end?" and "did this scan come through
properly?"

### Describe Character at Cursor

Some characters sound the same but are not: a curly "smart" quote and a
straight apostrophe, a no-break space and an ordinary space, an invisible
zero-width space that quietly breaks a search, or a stray byte-order mark
pasted from the web. **Tools > Advanced > Describe Character at Cursor**
(`Ctrl+Shift+C`) tells you exactly what sits under the cursor. It says the
answer where you are and leaves it in the status bar, so you can read it
again.

When you want to study a character, **Character Details** (`Ctrl+Alt+C`)
opens the full description in a read-only window, the same kind F1 help
uses, so your screen reader can read it all in one pass or line by line. It
gives:

- the character's name (for example "No-break space" or "Right single
  quotation mark"),
- its Unicode code point in both hexadecimal and decimal,
- its category in plain words (uppercase letter, dash punctuation, control
  character, and so on), and
- a note for the invisible characters that are easy to miss, plus a flag
  when the character is not ASCII.

If the cursor is at the very end of the document, it tells you so instead of
guessing.

A **page break** is named as one. A PDF opens with a page break between each
of its pages (a form feed character, which is what Go To's Page list and the
Page part of the status bar count). With the cursor on one, Describe Character
says "Page break U+000C" and Character Details adds that one page ends there
and the next begins. Before 2026-10-17 it said "Unnamed character", which told
you nothing. For example, open a three-page PDF, press **Ctrl+G**, choose
**Page**, pick page 2, then press **Left Arrow** once and **Ctrl+Shift+C**:
you hear "Page break".

QUILL also never hands that character, or any other control character, to
your screen reader inside an announcement. When a message quotes text that
crosses a page, such as the first words of a selection, the page break is read
as a pause rather than as a character name. The text in your document is not
changed.

### Reveal Codes (Alt+F3)

QUILL keeps formatting codes hidden, so your editing text stays clean and
fast. Reveal Codes lets you see and hear every one of them when you ask. If
you used WordPerfect, you will know it: this is the same idea, built for a
screen reader.

Press `Alt+F3` (or check **View > Reveal Codes**) to open a pane below the
editor. It shows your document as an ordered stream of bracketed codes and
text: `[Bold On]`, `[Font: Arial]`, `[Size: 14]`, `[Center]`, `[Heading 2]`,
`[Link: ...]`, `[Tab]`, `[¶ Hard Return]`, `[No-Break Space]`,
`[Smart Quote]`, and so on. The editor itself does not change. Reveal Codes
is a window onto the hidden formatting, not a different way of editing.

Reveal Codes is **hidden by default** and costs nothing until you open it.

> **QUILLBee's tip:** Not sure whether a word is really bold, or where the
> bold stops? Press `Alt+F3`, arrow to it, and you will hear "bold on" right
> where it starts. Press `Alt+F3` again to close the pane.

#### Moving between the panes

`F6` moves through the regions (Editor, then Reveal Codes when it is shown,
then the Status Bar), and `Shift+F6` goes back, just like switching windows.
The two carets stay in step however you move: arrow keys, word jumps, Home
and End, Page Up and Page Down, a mouse click, or a jump from Find. Move in
the editor and the pane follows to the same spot. Move in the pane and the
editor's cursor follows to the matching place. Sit in whichever you like and
your place in the document comes with you.

#### Moving through the codes

In the default **Flowed** view the pane reads like your document with the
hidden formatting showing, and the caret moves the way it does in the
editor:

- `Left Arrow` and `Right Arrow` move one character at a time, but step over a
  whole code in one go. One press moves you across `[Bold On]` and your
  screen reader just says "bold on". It is never spelled out letter by
  letter.
- `Ctrl+Left` and `Ctrl+Right` move by word, stopping at each code.
- `Up Arrow` and `Down Arrow` move by line and read the new line, as in the
  editor.
- `Home` and `End` go to the start and end of the line. `Ctrl+Home` and
  `Ctrl+End` go to the top and bottom of the document.
- Land on a code and you hear it named as one thing: "bold on", "tab",
  "centred", "font Arial". An opening code also tells you how far its
  formatting reaches ("bold on, 12 characters").

While you arrow through the pane, your screen reader does the talking. The
region is named once when you arrive, and after that you hear the character,
word, line, or code your screen reader reads. QUILL puts its fuller phrase
(for example "italic on, 15 characters") quietly in the status bar, where
you can read it whenever you want it. Jumps you ask for (next or previous
code, go to the matching pair) and mouse clicks are still spoken by QUILL.

If you would rather hear QUILL's own phrase on every arrow press, turn on
**Reveal Codes: Speak Codes Aloud** in the command palette. It is off by
default.

In either view you can also jump code to code, skipping the plain text, and
from an opening code to its matching close.

#### Editing a run in place (F2)

1. Move onto text that sits between a pair of formatting codes, for example
   the words inside `[Bold On] ... [Bold Off]`.
2. Press `F2`. The pane limits you to just that stretch of text, and you can
   edit it freely.
3. Press **Enter** to put your change back into the document, or **Escape**
   to cancel.

The codes around it are left exactly as they were. The whole stretch edits as
one piece, so a run that contains a `[Tab]` or a code inside it (bold text
with one italic word, say) comes along together. The inner codes appear as
their markup and are put straight back when you press Enter. If you press F2
on plain text with no formatting around it, QUILL tells you there is nothing
to edit there.

#### Views and how much it says

In **Settings > Editing** (or on the View menu) you can choose:

- **Flowed** (the default): the interactive pane described above, with codes
  shown inside the running text (`[Bold On]Hello[Bold Off]`), movement by
  character, and F2 editing. It is the closest to the classic WordPerfect
  look and the most natural layout on a braille display.
- **Structured**: one item per code in a list. It is clear and labelled, and
  good for scanning structure. Your screen reader reads each item as you
  arrow through it. Movement by character, word and line, and F2 editing,
  belong to the Flowed view only.
- **Verbosity**: *quiet* (just the code name), *balanced* (adds how far an
  opening code reaches), or *detailed* (adds Unicode notes for invisible
  characters).

QUILL remembers your view and verbosity between sessions.

### EPUB Navigator

When you open an EPUB, the navigator lets you move chapter by chapter
instead of scrolling blindly through one long block of text.

Chapter headings are also placed in the text itself, so single-key heading
navigation (`H` and `Shift+H`) walks every heading in the book, not just the
chapter breaks. Many older or home-made EPUBs never used real headings at
all. For those, QUILL works the headings out from the book's layout (a
paragraph styled as a title or chapter, or a short bold line on its own), so
heading navigation and the chapter outline still work where they would
otherwise be empty.

Equations are spoken, not skipped. When a chapter contains mathematics
(MathML, or LaTeX written as a `math` span or between `$$...$$` or `\(...\)`
delimiters), QUILL turns each equation into plain words and places it in the
text as "Math Equation: ..." so you hear the formula as part of its
sentence. It uses the same math speech as the editor: the MathCAT engine
when it is installed, and QUILL's built-in reader otherwise. A formula QUILL
cannot understand is read as its plain source instead of being dropped, and
a book with no math reads just as before.

### OCR Image

**OCR Image...** (on **Tools > Reading and Dictation**) reads the text out of
a picture, using optical character recognition on your own computer. Nothing
happens behind your back: you choose the image, confirm, and hear progress
as it works.

Two more commands on the same menu skip the file altogether:

- **OCR Clipboard Image** reads the picture you have just copied, for example
  with the Print Screen key or Copy Image in a web browser. If there is no
  picture on the clipboard, QUILL tells you so.
- **OCR Screen Capture...** takes a picture of the screen and reads it. QUILL
  asks whether you want **The whole screen** or **The active window**, with
  the active window already chosen.

Both show you the recognised text to review, just like OCR Image.

### Document intake and extraction quality

When you bring in a scanned PDF or another hard-to-read file, the text QUILL
pulls out may not be perfect. These commands help you check. Instead of
assuming every import is right, QUILL helps you ask whether the extraction is
good enough, what may have been lost, and whether you should quote from it
directly.

## Comparing documents

When you have two versions of something (a draft and the edited copy, or
your file and the one that came back by email), comparing them tells you
exactly what changed. Everything happens on your own computer. You can
compare one file with another, review several open documents, move through
the differences one at a time with both documents following along, and make
a summary of what changed.

### The Comparison menu

**Tools > Comparison** holds:

- **Compare with File...**
- **Compare Open Documents**
- **Next Difference** / **Previous Difference**
- **Announce Current Difference**
- **Difference List...**
- **Toggle Synchronized Navigation**
- **Toggle Ignore Whitespace**
- **Compare Options...**
- **Generate Accessible Report**
- **Create Difference Summary**
- **Copy Current Difference** / **Copy All Differences**

**Toggle Ignore Whitespace** decides whether spaces count as a change. Each
press moves one step and says where you are: exact (every space counts),
ignore trailing (spaces at the ends of lines do not count), then ignore all
(no difference in spacing counts), and back to exact. Use it when one copy
went through a program that tidied the spacing and you only care about the
words.

**Generate Accessible Report** writes every difference into a new Markdown
document, under a heading that names the two files and says how many
differences there are. Because it is an ordinary document, you can read it
at your own pace, search it, and save or send it.

### Moving through the differences

Once a comparison is open, these keys do most of the work:

- `Ctrl+Alt+Shift+.` moves to the next difference.
- `Ctrl+Alt+Shift+,` moves to the previous one.
- `Ctrl+Alt+Shift+D` reads the current difference.

The compare dialog is a list you can review with your screen reader, one
difference at a time, entirely from the keyboard.

### Compare sounds

If you use a sound pack, compare mode plays short earcons: one when a
comparison opens, one when it closes, separate ticks for moving to the next
or previous difference, and a soft "blocked" tone when you reach the first or
last difference and there is nothing further. You can turn each one on or
off in **Tools > Reading and Dictation > Sound Scheme...**
(`Ctrl+Alt+Shift+O`), under the Compare section. The topic on sound notifications and earcons has more about
sound packs.

## Making audio from your documents

QUILL can turn your writing into audio files: a single document, a whole
folder, or a chaptered audiobook ready to publish. This section is for when
you want something to keep, share or put on a phone. Live listening is Read
Aloud, earlier in this chapter.

### Audiobook and Batch Speech

**Tools > Speech > Audiobook & Batch Speech...** (`Ctrl+Shift+Grave` then
`Y`) is the guided home for audio production. It turns a whole folder of
documents into speech audio in one pass, and it builds chaptered audiobooks
from documents, from a folder of recordings, or from both. It is a wizard
that asks one thing at a time. It is listed in the command palette under
"Audio Studio...". It replaced the old single-page Batch Export to Speech
Audio dialog; every option is still there, spread across clear steps, and
your saved project settings still fill everything in.

#### What do you want to make

The first page asks what you want to make. It remembers which one you chose
last time and selects it for you.

- **Narrate documents into an audiobook or speech audio.** The steps are:
  What should I read? (folder, file types, filters); Who should read it?
  (engine, voice with a preview button, pace, round-robin voices, voice
  casting rules, translated editions); How should chapters work? (chapter
  mode, spoken headings, the transition sounder and its volume, pauses);
  Output and diagnostics (format, existing-file policy, loudness,
  incremental-rebuild reuse, dry run, temp folder); the book page
  (optional, to put everything together into one audiobook); and a summary
  in plain words.
- **Combine audio files into one chaptered audiobook.** A shorter path: pick
  the folder of recordings, describe the book (title, author, narrator,
  cover, M4B or MP3, ACX loudness), review the summary, and Start. Each file
  becomes one chapter, and you always review the chapter list before the
  book is built. There is more on this under Build an audiobook from a
  folder of recordings, below.
- **Edit an existing audiobook.** Pick a finished MP3 or M4B and it opens in
  the Chapter Workbench, described below. A file with no chapter markers
  opens as one chapter, ready to split up.

#### Moving through the wizard

Each step is announced as you arrive ("Step 2 of 7: What should I read?").
**Back** and **Next** move between steps. **Skip to summary** jumps ahead
when your saved project profile already fills every page, so a repeat run
is three keystrokes. The work runs in the background with progress for each
file, and you can cancel it. It uses the same speech engine as live Read
Aloud, so the voice you audition is the voice you get.

The source pages offer a list of **recent source folders**, and the edit
path's file picker remembers **recently opened audiobooks**. Both lists are
kept between sessions, are separate from your recent documents, and never
grow without limit.

#### What should I read

- **Source folder**, and whether to include subfolders.
- The **file types** to include: `.docx`, `.md`, `.html`/`.htm`, `.txt`.
- Optional **include/exclude filters**: patterns separated by semicolons or
  commas, matched against the file name and its path.
- **Skip files larger than (MB)**: a **maximum file size**, in megabytes
  (`0` means no limit). One accidental 400 MB export in a folder can no
  longer take over an overnight run. Any file over the limit is left out,
  and the live document count on the same step changes as you change the
  limit. Press **Count documents** to hear the settled count.

#### Who should read it

- **Engine, voice, and pace.** Any offline engine (SAPI 5, DECtalk, Piper,
  Kokoro, eSpeak NG), with a **Preview** button to hear the voice first.
- **Round-robin voices** read each article or heading in a different voice,
  cycling through a list you build:
  1. Pick a voice from the **Round-robin voices** combo box.
  2. Press **Add voice**.
  3. Repeat for each voice, and use **Move Up**, **Move Down** and
     **Remove** to set the order.

  Article 1 uses the first voice, article 2 the second, and so on, starting
  again at the top when the list runs out. The list uses voices from the
  engine you selected, so the sound quality stays consistent, and changing
  the engine clears it. Leave the list empty to use the single chosen voice.
- **Voice casting** lets you say exactly who reads what, on top of the
  rotation. On the same page, add rules: a pattern plus the voice that should
  read every matching chapter. A pattern matches the heading title as a
  wildcard (`Chapter *`, `*interview*`, or an exact title, ignoring case) or
  a section number (`#1` for the opener). The first rule that matches wins;
  chapters no rule matches go to the rotation or the single voice. Rules use
  voices of the selected engine (switching engines clears them) and are
  saved in job files. A dialogue-heavy drama or an interview show can cast
  its voices on purpose instead of by rotation order.
- If a voice ever **fails to speak** (a broken system voice, a missing model,
  or a cloud voice the provider rejects), QUILL notes it and **skips it on
  later runs**, so one bad voice in a rotation cannot keep stopping your
  batches.

Your combine and round-robin choices are remembered for each project.

#### Translated editions

**Also export in other languages (translated)** makes a translated audiobook
alongside the original.

1. Choose a **language**.
2. Pick a **voice** for it.
3. Press **Add language**. Repeat for as many languages as you want.
   **Remove language** drops one.
4. Choose **Translate with**: **AI provider** (any AI provider you have set
   up) or **LibreTranslate** (runs locally).

Voices are offered local ones first (eSpeak speaks nearly every language
offline, plus any Windows voice installed for that language), then the
**premium multilingual cloud voices: OpenAI, Gemini, and ElevenLabs**. Those
need the matching provider API key, the same key the AI Voice feature uses.
When you press Start, each document is translated and written as
`<doc> (<Language>).<ext>` next to the original, with the same chapters,
page-turn cue, and loudness. A pronunciation dictionary can be limited to
one language, so it only affects that language's narration. If a cloud
voice you chose has no key set up, that language is skipped with a note and
the run carries on.

You see the cost first for cloud runs. Cloud translation and cloud narration
are paid by use, so if your choices would use a paid cloud service, QUILL
shows a **combined cost estimate** and asks you to confirm before it starts.
Runs that use only local engines and LibreTranslate start straight away.

#### How should chapters work

- **Chapters** turn a long document into a **chaptered** file you can move
  around in. Choose **MP3** (ID3 chapter markers) or **M4B audiobook** (native
  MP4 chapter atoms, the Apple and audiobook format). Apple Podcasts,
  Overcast, VLC, foobar2000, and others recognize both.
- A **transition sound** plays between articles: a natural page-turn by
  default, or a different earcon from your active sound pack. Whichever you
  use is matched to the audio format automatically, so it always joins
  cleanly.
- You choose whether each heading is spoken, and set pauses between articles
  and between sentences, plus a short silence at the end that stops clipping.
- A very long section is split automatically at a safe sentence boundary, so
  no single passage runs past the engine's time limit. The run report lists
  how many chapters each document got.
- **Chapter mode**: keep the whole document as **one chaptered file**, or
  choose **Separate file per article** to write each section under a heading
  as its own `NNN - <heading>` audio file, in a folder for that document.
- **Combine empty headings**: when a heading has no text of its own (a "Part"
  heading followed straight away by a "Chapter" heading), fold it into the
  next article that does have text and join their titles ("Part One: Chapter
  1"), so you do not hear an empty chapter. Off by default. Turn it on with
  the **Combine empty headings into the next article** checkbox.

#### Output and diagnostics

- **Output format**: **WAV** (always available) or, when `ffmpeg` is
  installed, **MP3, M4A, M4B (audiobook), Opus, FLAC, or OGG**. When `ffmpeg`
  is missing, compressed formats fall back to WAV with a note for each file,
  instead of failing. MP3 has a quality setting, and WAV can be made to one
  sample rate and channel count throughout.
- **Normalize loudness**: check **Normalize loudness to audiobook (ACX)
  level** to bring every exported file to the same audiobook loudness, the
  standard the Build Audiobook tool uses. QUILL measures each file and
  re-levels it in two passes, without touching the chapters or their timing.
  Needs ffmpeg; without it, the file is saved as it is, with a note.
- **If a file already exists**: **Skip** (a cheap way to resume),
  **Overwrite**, or **Rename** so both are kept (`name (2).mp3`).
- **Output layout**: mirror the source folders or **flatten** everything into
  one folder. You can also rename outputs with a **template** such as
  `{index:03d} - {stem}`, which gives `001 - chapter-one`.
- **Audiobook metadata**: album, author or narrator, genre, and year are
  written into compressed files. Each file's title comes from its heading or
  name, and its track number from its position.
- **Dry run**: instead of speaking, write a `<doc>.preview.txt` for each
  document with the exact text that would be spoken (after cleanup,
  pronunciation fixes, and polish) and how many pronunciation substitutions
  were made. You can proofread what will be said before waiting on slow
  speech.
- **Audition**: check **Audition** on the output step to convert only the
  first document. You can judge the voice, the pace, and the loudness in a
  couple of minutes before you commit to an overnight run.
- **Run report**: optionally write a `manifest.json` and `manifest.csv`
  listing every file's status, output path, length, and any error.

#### Incremental rebuilds

With **Reuse unchanged audio from the last run** checked (the default), QUILL
takes a fingerprint of each document's text together with every setting that
shapes its audio. On the next run, documents that have not changed, and
whose audio is still on disk, are reused instead of spoken again, and you
hear "Reused ... (unchanged since last run)". Edit one chapter of a
forty-document book and only that chapter is narrated again. Change the
voice or any audio setting and everything rebuilds by itself. Uncheck the box
to force a full rebuild. The fingerprints are kept in the source folder's
`.quill/speech-cache.json`; deleting that file also forces a fresh run.

#### The book page

- **Look up book details.** Type the title (and the author, if you know it)
  and press **Look up book details**. QUILL searches **Open Library** and
  **MusicBrainz**, two free public catalogs, and the match you pick fills in
  the author, genre, and year. QUILL asks before the first contact, and only
  the title and author you typed are sent. If the match has a cover image on
  Open Library and you have not set one, QUILL offers to download it as
  `cover.jpg` next to your audio and fills the cover field. Say no and
  nothing is fetched.
- **Spoken credits.** Check **Add spoken opening and closing credits** and
  QUILL narrates the usual audiobook frame ("My Book. Written by Jane Doe.
  Narrated by Sam Reader.") in the run's own voice, as the first and last
  chapters.
- **Polish during the build.** The audio source page's **Trim silences from
  each recording** and the book page's **fade-in / fade-out / tempo**
  controls are applied while the audiobook is built. Each chapter file is
  prepared first (silence trimmed from the start and end, fades added, and
  the tempo changed without changing pitch) and then joined into the master.
  The prepared copies live in the build's temporary folder, so your source
  recordings are never overwritten. If polishing one file fails, the build
  keeps going with that file as it was. The defaults (no trim, `0` ms fades,
  `1.0` tempo) leave the audio unchanged.

#### Settings that stay with the folder

A folder remembers its whole speech setup in
`<folder>/.quill/speech-project.json`: engine, voice, output format,
chapters, text cleanup, pronunciation dictionaries, metadata, and run policy.
Set up a project once and run it again whenever you like. When you open the
wizard on a folder you have set up before, those settings **fill in by
themselves**, and your choices are **saved when you press Start**. Anything
you change this run beats the folder's saved settings, which beat your
global defaults.

**Job files** go one step further. On the summary page, **Save a job file**
writes a small `.quilljob` file that pins this exact run: folder, voices,
chapters, mastering, and book details. You can edit it by hand. **Load a job
file** on the first page brings everything back, filled in. Keep one per
project, or edit it in Notepad between runs.

#### Running it without you

- **Library mode** (a checkbox on the combine-audio path) builds every
  subfolder as its own audiobook in one unattended run. Point it at a folder
  of book folders and come back to a shelf of finished masters, each titled
  after its folder.
- The watch action **"Build audiobook from the folder"** keeps a drop folder
  working for you. Whenever new recordings land in a watched folder, its
  chaptered master is rebuilt automatically. A batch of files arriving
  together causes one rebuild, not many.

### Export to Translated Speech Audio (one document)

**Tools > Speech > Export to Translated Speech Audio** is the one-document
version of the translated export above. It translates and narrates just the
document you are editing, with no folder involved.

1. Pick the output format.
2. Choose **Translate with**: any AI provider you have set up, or local
   LibreTranslate.
3. Add one or more **language + voice** targets, the same way as in the
   wizard. Local voices are listed first, then the premium cloud voices.
4. Press **Export**.

QUILL writes `<doc> (<Language>).<ext>` next to your document. If the
document has unsaved changes, QUILL offers to save first, so your latest
edits are the ones translated. As with the wizard, a **combined cost
estimate** appears before any paid cloud run.

The dialog also has an **"Open in Audio Studio"** button. It closes the
dialog and opens the Audiobook and Batch Speech wizard with your document
already filled in, for when you want chapters and the rest.

### Build an audiobook from a folder of recordings

The wizard's **Combine audio files** path (**Tools > Speech > Audiobook &
Batch Speech...**, the second choice on the first page) joins a folder of
existing audio files into one chaptered audiobook, the kind your audiobook
or podcast app moves through track by track. Where the narrate path turns
documents into speech, this one stitches a folder of audio (your own
recordings, or speech QUILL exported earlier) into a single master.

- Point it at a **folder of audio files**. Each file becomes one
  **chapter**, in natural sort order, titled from the file name (a leading
  track number such as `01 - ` is removed).
- **Edit the chapters before building.** The dialog lists the chapters, and
  works fully from the keyboard. You can **rename** the selected one (type a
  new title and press Rename or Enter), **move** it **up** or **down**,
  **merge** it into the chapter above (the two files then play as one
  chapter with one marker), or **remove** it from the book. **Restore
  original** undoes every edit in one press.
- **Bring your titles with you.** **Import titles...** reads chapter names, in
  order, from an Audacity label track, a CUE sheet, plain timestamp lines,
  Podcasting 2.0 chapters JSON, or a **CSV spreadsheet**. Any sheet with a
  "Title" column works, and so does a simple `number,title` list, so a
  chapter list you keep in Excel can name your MP3 files in one step.
  **Export titles...** writes the current list back out as text.
- **Honest numbers, before and after.** The run log starts with a
  **pre-flight check**. It names files whose sample rate, channels, or format
  differ (the build still works; it re-encodes them) and gives an estimated
  length and size. After the build, QUILL **re-reads the finished book** and
  tells you what a player will actually see: "verified 24 chapters", or
  exactly what went wrong. A plain-text **chapter report** and a
  **Podcasting 2.0 `...chapters.json`** file are written next to the book.
- Choose **M4B audiobook** (native MP4 chapter atoms, the Apple and audiobook
  format) or **MP3** (ID3 chapter markers). You can move by chapter in both
  in Apple Podcasts, Overcast, VLC, foobar2000, and others.
- Check **Normalize loudness to ACX (Audible/audiobook) spec** to bring the
  master into the loudness range audiobook platforms require (RMS between
  -23 and -18 dB, peak under -3 dB). After the build, QUILL measures the
  result and says in the status bar whether it met the ACX range.
- Fill in the book's **title, author, narrator, genre, and year**. A **cover
  image** in the folder (named like `cover.jpg`, `folder.png`, and so on) is
  picked up automatically, or you can browse for one.
- The build runs in the background, and the status bar tells you when it is
  done.

### The Chapter Workbench

The Workbench is where you fix a finished audiobook by ear. Reach it from the
wizard's **Edit an existing audiobook** path, or, for any recording at all,
from **Tools > Speech > Find Chapters in a Recording...**
(`QUILL Key + Shift+O`).

#### Automatic chapters for a lecture, a meeting or any MP3

A two-hour lecture with no chapters is hard to move around by ear: there is
nothing to skip to. **Find Chapters in a Recording...** fixes that. It asks
for a recording (MP3, M4A or M4B), opens the Workbench on it, and starts
**Propose chapters from silences** straight away.

1. Choose the recording and press Open.
2. The **Propose chapters from silences** window asks two things: how quiet
   counts as silence (in decibels; -30 suits most speech, -40 a noisy room)
   and how long a pause must last (in seconds; 0.8 catches a speaker drawing
   breath between topics, 2 or 3 only the real breaks). OK starts the scan.
3. The scan runs in the background, and you can keep listening while it
   does. Each new chapter starts in the middle of a silence and is titled
   **Proposed chapter 1**, **Proposed chapter 2** and so on, so you can always
   tell a guess from a name somebody chose. You hear how many were proposed.
4. Arrow through the list. Enter plays a chapter from its start; **Hear
   boundary** plays the moments around where it starts; **Set start
   to playhead**, **Split at playhead**, **Nudge back** and **Nudge forward**
   move a boundary until it sounds right; **Merge into previous** removes one
   that should not be there. Rename each one you keep (type the title and
   press Enter).
5. **Save** writes the chapters: an MP3 in place (only its tags change; the
   audio is untouched), an M4B as a new file. **Export chapters...** writes
   them as a CUE sheet, timestamps, Audacity labels, Podcasting 2.0 JSON or a
   spreadsheet instead. Reopen the file and the chapters are there.

Some things to know:

- **Your own chapters are never silently replaced.** If the recording already
  has two or more chapters, QUILL asks first. **Keep mine, add proposals** (the
  default) keeps every chapter you had, with its title and start, and adds a
  proposed chapter only where a silence is at least ten seconds from one of
  yours. **Replace with the proposal** swaps the whole list. Cancel changes
  nothing. A recording with no chapter marks of its own is not asked, because
  there is nothing of yours to lose.
- **Stopping.** While the scan runs the button reads **Stop proposing
  chapters**. Press it again, or close the Workbench, and the scan's answer is
  thrown away and the list stays exactly as it was. (The scan program finishes
  its pass in the background and nothing is written.)
- **Restore original** takes back the whole proposal at once, whichever way
  you answered.
- **Long recordings.** The scan is given time in proportion to the
  recording: at least ten minutes, and a tenth of the recording's length for
  anything over a hundred minutes, so a whole day's recording is scanned to
  the end.
- It needs ffmpeg. Without it you are told so, and the button comes back.
- Silence is a guess about structure, not knowledge of it. A speaker who
  pauses mid-sentence makes a boundary that is not a topic change; that is
  why every proposal is labelled and nothing is saved until you press Save.

#### The chapter list and the player

The chapter list reads each row in full ("3. The Long Road, starts 1:02:03,
runs 12:40"). Press Enter on a chapter to hear it.

The built-in **player** has Play/Pause, Stop, Previous and Next chapter,
Rewind and Forward, a position slider that speaks minutes and seconds, and a
volume slider. The current chapter is announced as playback moves into it.

- It **remembers where you stopped** in each book and picks up there next
  time.
- It has a **playback speed** control, from 0.75x to 2x, with the pitch kept
  natural.
- It answers **"Where am I?"** with the whole picture: "Chapter 4 of 24: The
  Long Road. 3:12 into the chapter, 9:28 left in it. 1:02:03 of 7:41:00 in
  the book, 6:38:57 remaining."

Playback normally uses Windows' built-in media engine, with nothing to
install. For gapless audio, exact seeking, and instant chapter jumps even in
8-hour books, download the **mpv player engine** from **Help > Download
Optional Components** (about 44 MB, checksum-verified; its licenses and a
source offer come inside the download). The player switches to **libmpv**
the next time it opens. If you prefer, you can instead put a
`libmpv-2.dll` into the data folder's `engine-packs\mpv` folder, or set the
`QUILL_LIBMPV` environment variable to point at one. If the DLL is missing
or broken, QUILL quietly stays on the built-in engine.

#### Fixing the chapters

- **Split at playhead**: listen for the spot where a chapter should begin,
  pause there, and press the button. The chapter is cut in two exactly at
  that point. This is how you fix a book whose chapters landed in the wrong
  places.
- **Set start to playhead**: move an existing boundary. Select the chapter,
  park the playhead where it should start, and press. The previous chapter's
  end moves with it, so there are never gaps.
- **Merge into previous**, **Rename** (type and press Enter), and **Restore
  original** (one press undoes every edit).
- **Add chapter...** puts a marker at the playhead, or at a time you type,
  and asks what to call it. Past the end of the last chapter it adds a new
  one at the end instead of refusing.
- **Delete chapter** removes a marker only. The audio joins its neighbour,
  and unlike Merge it works on the first and last chapters too.
- **Edit chapter...** opens a small window for the title and the exact start
  and end (and a chapter link and image, if you publish with Podcasting
  2.0).
- **Preview chapter** plays just that chapter and stops at its end.

#### Nudging a boundary until it sounds right

**Nudge back** and **Nudge forward** move the selected chapter's start by one
step. From the chapter list, `Alt+Left` and `Alt+Right` do the same, and
adding Shift moves ten steps at once.

- The **Step** box goes from 100 milliseconds up to 10 seconds, and
  remembers your choice for next time (`audio_studio_chapter_nudge_ms`, half
  a second to start with).
- **Hear boundary** plays three seconds before the marker and two after it,
  then stops. It is the quickest way to tell whether a boundary falls in the
  middle of a sentence.
- Check **Hear after each nudge** to have that happen automatically after
  every press. It is off by default, so you only get sound on every keypress
  if you ask for it.
- Each nudge speaks only the new time ("0:00:09.500"), so it keeps up when
  you hold the key down. The full sentence follows about half a second after
  you stop.
- Push a marker into its neighbour and it stops there and says "Cannot move
  further" once.

#### Finding chapters for you

- **Propose chapters from silences...** listens for silences in the
  recording, using ffmpeg's `silencedetect`. A small dialog asks for the **noise threshold** (dB, default
  -30) and the **minimum silence** length (seconds, default 0.8), and QUILL
  suggests chapter boundaries in the middle of each silence. The suggestions
  land in the chapter list for you to review; nothing is applied without
  you. Press **Restore original** to undo. So one long recording is no
  problem: open a single 80-minute file (it opens as one chapter), press one
  button, review, and save.
- **Propose AI titles...** names a folder of `track07`-style chapters by
  listening to them. The first minute of each chapter is transcribed on this
  computer by the local speech model, so the audio never leaves your
  computer. Only that text goes to the AI you have set up (a local model
  keeps even the text on your computer). A short suggested title for each
  chapter lands in the list for you to review, and **Restore original**
  undoes the lot. Needs AI set up; not available in Safe Mode.

#### Checking, importing and splitting

- **Check against ACX** measures the file with ffmpeg's loudnorm and shows a result with
  integrated loudness, true peak, and noise floor, plus a plain suggestion
  for each thing that fails ("Integrated loudness is -14.2 LUFS, target -20
  plus or minus 3; make the recording 5.8 dB quieter"). The result is
  announced when the measurement finishes, however you close the dialog.
- **Import chapters...** replaces the whole list from Audacity labels, a CUE
  sheet, timestamp lines, Podcasting 2.0 JSON, or CSV. **Export chapters...**
  writes the list in any of the same five formats.
- **Split into files...** goes the other way: one audio file per chapter,
  named `NN - Title`, in a folder you pick. That gives you podcast episodes
  straight away, or tracks for players without chapter support.

#### Book details and tags

**Book details** (title, author, narrator, genre, year) are edited right in
the Workbench. **All tags...** opens the full **Tag Editor** for everything
else: twenty-six fields over five pages (main, details, publishing, sort
order and cover art). They include track and disc numbers, composer,
publisher, copyright, BPM, ISRC, language, grouping, the compilation flag,
the four sort-order fields, and cover art you can load, save out or remove.
`Ctrl+Tab` moves between pages. The five quick fields and the editor always
agree with each other, in both directions.

You can also open the Tag Editor on its own, without the Workbench: check
**Edit the tags only** on the Studio wizard's *Open a book* page.

The same editor is in podHarvest. A file edited in one reads back exactly as
you left it in the other, with the same fields, operations and keys. If you
use both, you only learn it once.

#### Saving

**Save** writes an MP3's edits **in place**: only the tags are rewritten and
the audio is left alone. An M4B depends on what you changed. Tag edits alone
also save in place and finish at once. A chapter change needs **Save As**,
which copies the audio into a new file without re-encoding, so there is no
loss of quality. Long saves run in the background, so QUILL stays
responsive.

#### Publishing

**Publish...** offers ways to get the finished book out into the world. Each
one is something you choose to do:

- **Podcast feed**: QUILL writes a complete `.rss` file next to the book
  (RSS 2.0 with iTunes and Podcasting 2.0 tags; chapter navigation uses the
  `chapters.json` file beside it). Upload the feed and audio wherever you
  like. Making the feed never touches the network.
- **Folder feed (all episodes)**: run a whole show from one folder. Every
  MP3, M4B, or M4A master becomes an episode (the oldest file is episode 1),
  with its title from its tags or your own, your description for each
  episode (edited in an accessible episode list), its real publication date,
  length, and chapter link. The show settings are kept in the folder, so
  after each new build, one press of **Write feed.rss now** makes the
  complete feed again. **Write show notes page** makes an accessible
  `show-notes.html` beside it, with a heading for each episode, the
  descriptions, and chapter lists, ready to upload with the feed.
- **SFTP upload**: save a destination (host, folder, and the public web
  address that matches it), and QUILL uploads the book and its companion
  files over SSH, with the same strict host-key checking as editing over
  SSH. The password is kept in the **Windows Credential Manager**, never in
  QUILL's settings.
- **Auphonic**: send the book to your own Auphonic account for professional
  post-production. QUILL uploads it, waits for the production to finish, and
  downloads the results into a folder next to the book. Your API token is
  also kept in the credential vault, and you can manage it on the Services
  page of **AI > AI Hub...**, with QUILL's other service keys. (AI Hub is on
  the AI menu once **AI > Show advanced AI features** is checked.) Press **Check account and load
  presets** first: QUILL tells you whose account the token belongs to and
  how many processing credits remain, and fills the **preset picker** with
  your saved Auphonic presets. The confirmation then names the preset and
  your balance before anything uploads. QUILL asks before anything is
  uploaded.

Publishing is not available in Safe Mode. Every upload runs in the
background and tells you when it is done. SFTP uploads and Auphonic
transfers show a progress dialog that speaks whole-percent steps as the file
moves ("Uploading book.m4b: 42%") and has a real **Cancel** button. What
cancelling does depends on when you press it, and QUILL tells you which
happened:

- Cancelling an SFTP upload stops in the middle of the file. Files that
  already finished stay on the server.
- Cancelling Auphonic before the upload finishes means no production starts.
- Cancelling Auphonic after that leaves the production running in your
  Auphonic account and skips the download.

### The Universal Audio Converter

Apart from the audiobook wizard, QUILL has a general **audio converter**. It
changes audio files from one format to another, and pulls the sound out of
video files, entirely on your computer using the bundled ffmpeg. It works in
Safe Mode and never uploads anything. There are three ways in:

- **Voices > Convert Audio...**: the dialog, from the audiobook and batch
  speech wizard.
- **`quill convert`**: a command for scripts, for example
  `quill convert *.wav --to mp3 --preset podcast --out ./done`. Add
  `--dry-run` to see the plan first, `--list-presets` or `--list-formats` to
  see what is available, and any of the Advanced options (`--bitrate`,
  `--sample-rate`, `--channels`, `--loudness`, `--gain`, `--high-pass`,
  `--trim-silence`, `--speed`, `--compress`, `--level`, `--fade-in`,
  `--fade-out`).
- **Convert from URL...**: paste a link (YouTube, and the many sites yt-dlp
  supports) and QUILL downloads the best audio and hands it to the
  converter. This is the only part that uses the internet. yt-dlp is **not**
  bundled, so the first time you use it QUILL asks once, shows a rights
  notice ("only download content you have the right to use"), and installs
  the small yt-dlp component. It is not available in Safe Mode.

#### Building a batch

1. Add single files or whole folders. A folder is searched, and its layout
   of subfolders is copied into the output folder.
2. Choose the output **format**. Only formats your ffmpeg can actually make
   are offered, so a conversion never fails halfway for lack of an encoder.
3. Pick a **preset**: *Just convert* (change the container only), *MP3
   128/192/320*, *Podcast*, *Audiobook*, *Voice memo*, *Web Opus*,
   *Archival FLAC*, or *Hearing-aid mono*.
4. Choose an output folder, or leave it to make a `Converted` folder beside
   the source.
5. Choose what happens when a file already exists: **auto-number** (never
   overwrites an original), **skip**, or **overwrite**.

The batch runs in the background on several files at once, so the window
stays responsive. Progress shows in the status bar and, when QUILL is
minimized, in the tray tooltip. The final summary is spoken and always names
any files that failed, so a problem is never hidden behind "done".

#### Advanced options

Check **Advanced options** to show more controls on top of the preset:

- exact **bit rate**, **sample rate**, **channels** (keep, mono or stereo),
  and **bit depth**
- loudness normalized to an **audiobook** (-20 LUFS, ACX) or **podcast**
  (-16 LUFS) target
- **gain** in decibels
- a **high-pass** filter to remove low rumble
- **trim silence** from the ends
- **speed**, a tempo change from 0.5x to 2x with no change in pitch
- a **compressor** and a volume **leveler**
- **fade in** and **fade out**, in seconds

Each control leaves the preset alone until you change it, so Advanced only
overrides what you set on purpose. The effects are the same ones QUILL uses
elsewhere, so the results match the rest of the app.

## Media

QUILL also plays podcasts, recorded programmes and audiobook chapters. This
part is about keeping your place in all of it, even across computers, and
about letting it stop by itself when you fall asleep.

### Continue Listening

**Continue Listening...** (in the Command Palette) is one list of everything
you started and did not finish, newest first, with the kind named on every
row: a podcast episode you are twenty minutes into, a recorded programme or
LibriVox chapter you were halfway through. It answers the question "what was
I in the middle of?" in one place.

- **Resume** starts the highlighted row where you left off.
- **Forget This One** drops the saved place and removes the row. The episode
  stays unplayed, because "I am not going back to this" and "I finished it"
  are different things. Clearing what you have given up on keeps the list
  worth opening.

### Where you were in each podcast

The Podcasts window remembers, for each podcast, which episode you last had
selected, and puts you back on it the next time you choose that podcast --
after closing the window and after restarting QUILL. It knows the episode by
who it is (its feed's own episode ID, with its address and date as
fall-backs), not by its row number, so it still finds the right one after new
episodes arrive at the top, after you change the episode sort, and after a
refresh.

If the episode has gone -- the feed dropped it, or a filter hides it -- you
land on the remaining episode published closest to it (the newer of two
equally close), so you are still in the same stretch of the back catalogue
rather than back at the top. A podcast you have never opened starts at the
first row, as before.

For example: you are working through a history podcast from its first
episode and stop on episode 41. Next week four new episodes have arrived.
Choose the podcast and the cursor is on episode 41, not on the newest one.

QUILL Cast does the same for a podcast opened from Favorites with Enter. The
places that mix podcasts (New Episodes, the Inbox, the Play Queue) do not
move a podcast's remembered place. Each app keeps its own memory, in
`podcast_episode_cursor.json` in its data folder; deleting the file only
forgets the places.

### Carry My Place Between Machines

If you listen on more than one computer, **Carry My Place Between
Machines...** makes your place follow you. It needs two things: a folder both
computers can see, and a recovery phrase.

The folder is yours. Point it at somewhere inside OneDrive, Dropbox, iCloud
Drive, a network share, or even a memory stick you carry between the two.
QUILL runs no server of its own and never holds your listening history.
Everything is encrypted before it reaches the folder, so whoever runs that
folder learns nothing but file sizes and times.

The recovery phrase is eight ordinary words, made up for you, something like
*earth dock hollow iris farm laser daisy amber*. Write it down. It is the
key, and QUILL cannot get it back for you if you lose it. **Read My Phrase
Aloud** says it back numbered, one word at a time, which is just what you
want while writing it on paper.

To set up the second computer, use the same window:

1. Open **Carry My Place Between Machines...** on the second computer.
2. Point it at the same folder.
3. Type the phrase from the first computer.

QUILL notices the folder is already set up and says so. If the phrase is
wrong it tells you at once ("that recovery phrase does not match this
folder; nothing was changed") instead of half-syncing and failing later.
Typing is forgiving about capitals, spacing and punctuation, and a word that
is not on the word list is named, so you only need to check that one.

**Sync Now** runs it and tells you in a sentence what happened: what came
back, what went out, and whether two computers disagreed about a place (the
most recent wins, and you are told). It can also run when playback stops, if
you like. If both computers remembered a different place in the same thing
and they are more than a few minutes apart, QUILL treats that as a real
disagreement and tells you, instead of quietly picking one.

Everything works normally with no sync at all. Nothing ever waits on the
folder before playing.

### Sharing your place with apps that are not QUILL

The sync above carries your place between two copies of QUILL. It is
encrypted from end to end, which is right, and which is also why no other
app can read it. If you listen on a phone with a podcast app that is not
ours, it does not help you.

**Listening Places** is the other half, and it is a separate checkbox in the
same window. In the folder you already chose, QUILL also writes a small,
plain file in a published format that any podcast app is free to read and
write. There is no account, no server, and no signup. The format is written
down publicly, so another app can simply support it.

What that means for you:

- **Turn on only the half you want.** The encrypted QUILL-to-QUILL sync and
  the shared plain file are separate switches, because they reveal different
  things. You can use either, both, or neither.
- **No recovery phrase is needed for this half.** The shared file cannot be
  encrypted and still be readable by another app, so setting it up is one
  checkbox.
- **Titles are left out unless you say so.** Every show and episode is
  identified by a scrambled fingerprint instead of its name, so a folder you
  share with a family member does not become a list of what you listen to. A
  third checkbox, off by default, adds readable titles if you want them.
- **Each device writes its own file.** That stops a cloud drive ever making a
  "positions (Jeff's conflicted copy)", and it means a third and fourth
  device work with no extra setup.
- **The most recent place wins, not the furthest.** If you jumped back twenty
  minutes on purpose and then opened the episode somewhere else, that jump is
  kept.
- **It reads at launch and when you press Sync Now, and at no other time.**
  So a position from another device never moves the playhead under you in
  the middle of an episode.

**Sync Now** covers both halves in one press and reports on each.

### Sleep Timer

The sleep timer stops whatever is playing after a while, from one place. In
this release radio and podcasts live in their own apps, so you set it in
**Quill Radio** with **Sleep Timer...** on its Playback menu (`Ctrl+Shift+Z`),
or in Quill Cast. The editor's own Tools menu shows a Media submenu with the
same Sleep Timer only in developer builds, where radio and podcasts are still
part of the editor.

1. Choose a preset (15, 30, 45, 60, or 90 minutes), or type your own number
   of minutes.
2. Press **Start**.

Over the last 20 seconds, playback fades gently down and then stops. Your
volume is then set back to what it was before the fade, so pressing play
later is not suddenly quiet. Open the dialog again while a timer is running
to hear how much time is left, or press **Cancel Sleep Timer** (also in the
Command Palette as **Media: Cancel Sleep Timer**) to stop the countdown
early.

## What you learned, and where to go next

You can now have QUILL read to you in the voice and language you like, and
teach it how to say the words it gets wrong. You can inspect a character,
hear the hidden formatting with Reveal Codes (`Alt+F3`), read an EPUB by
chapter, and step through the differences between two documents. You know
where QUILL makes audiobooks, fixes their chapters and publishes them, and
how to keep your place in what you listen to.

To practise with QUILL beside you, open **Help > Tutorials...**
(`Ctrl+Alt+F1`) and try "Have it read to you", "See the formatting that is
normally hidden" and "Inspect a document you did not write". On the website,
[Rescue a scanned PDF](https://www.quillforall.org/tutorials/03-rescue-a-scanned-pdf.html)
and
[From document to published audiobook](https://www.quillforall.org/tutorials/04-document-to-audiobook.html)
walk through the longer jobs.

Next, Chapter 9, Dictation and transcription, turns things around: you speak
and QUILL writes.

---

- Previous: [Chapter 7: Spelling and words](quill-guide-07-spelling-and-words.html)
- Next: [Chapter 9: Dictation and transcription](quill-guide-09-dictation-and-transcription.html)
- [Contents](../userguide.html)
