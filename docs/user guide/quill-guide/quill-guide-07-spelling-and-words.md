# Chapter 7: Spelling and words

This chapter is about getting the words right. You will check spelling a
whole document at a time or one word at a time, hear exactly how a misspelled
word is spelled, find a better word in the thesaurus, look up what a word
means, and count what you have written. Near the end you will also find how to
quieten QUILL's sounds, or choose new ones. Everything here works on your own
computer, with no AI and no internet connection, unless you choose otherwise.
AI spelling and grammar help is in Chapter 10, AI, when you want it.

## Spelling

QUILL checks spelling on your own computer. Nothing you write is uploaded, and
no AI provider is involved. The everyday commands are on the **Tools** menu:

- **Spell Check...** (`F7`) opens the Spelling Review, which walks you through
  every misspelling.
- **Spell Check Word** (`Alt+Shift+F7`) checks only the word you are on.
- **Next Misspelling** (`Ctrl+F7`) moves straight to the next one in the
  document, and `Ctrl+Shift+F7` goes back to the previous one.

### Spelling Review (F7)

Press `F7` to start a guided spelling review.

- **What it checks.** If you have text selected, QUILL checks only the
  selection. With nothing selected, it reviews the whole document, starting at
  your caret.
- **Where you land.** The **Spelling Review** dialog opens with focus in a
  read-only **Context** field. The misspelled word is selected inside its
  sentence, so you hear it in context. You can arrow through it letter by
  letter or copy the text, just as you would in a read-only document.

The controls, in Tab order, are: Context, Change to, Suggestions, the **Review
most-frequent words first** checkbox, then the buttons Change, Change All,
Ignore Once, Ignore All, Read Sentence, Add to Dictionary, Undo Last and Close.

- **Suggestions** lists the corrections QUILL has for the word. Arrow through
  them; choosing one fills **Change to** for you.
- **Change** replaces this occurrence and moves to the next problem. Pressing
  **Enter** in the **Change to** field does the same.
- **Change All** replaces every remaining occurrence in the part you are
  checking, and keeps the capitals as they were (`teh` becomes `the`, `Teh`
  becomes `The`, `TEH` becomes `THE`).
- **Ignore Once** skips this occurrence. **Ignore All** skips every
  occurrence, for this session only.
- **Add to Dictionary** adds the word to your personal dictionary for good.
- **Undo Last** takes back your last spelling action without closing the
  dialog. It is unavailable until you have done something.
- **Read Sentence** (`Ctrl+R`) reads aloud the whole sentence around the
  misspelling, so you can hear the word in context without leaving the
  dialog. The **Read Sentence** button does the same thing.
- `Alt+W` takes you back to Context and selects the current word again, at
  any point. It is handy after you have been arrowing around the context.

When every problem has been dealt with, QUILL tells you how many words were
changed, ignored and added to the dictionary, and puts you back in the
document.

#### Review most-frequent words first

Normally the review goes from top to bottom. Check **Review most-frequent words
first** in the dialog and it walks the misspellings by how often each word
turns up instead, with the most common first. It is the same dialog and the
same buttons (Change, Change All, Ignore Once, Ignore All, Add to Dictionary,
Undo Last); only the order changes.

This is for really messy documents: a rough scan that came through OCR, or a
document with one mistake repeated many times. Press **Change All** on the top
word and the order is worked out again straight away, so whatever is now most
common among what is left comes to the front. You clear the worst offenders
first, without hunting for them in reading order. QUILL remembers the
checkbox for next time.

#### How much the review says

**Spelling review announcement verbosity**, on the **Spelling** page of
Settings, chooses how much the review tells you:

- **Concise**: progress numbers and the result of each action, and nothing
  else.
- **Balanced** (the default): the kind of problem, the current word, your
  progress and the results.
- **Detailed**: all of that, plus hints about the controls and reminders of
  what you are checking.

Four more settings on the same page belong to the review:

- **Spelling review context display mode**: the Context box usually shows
  the sentence with the misspelling plus the sentences either side. Choose
  **Full paragraph** to see the whole paragraph instead; Read Sentence then
  reads the paragraph.

- **Spell out the misspelled word letter by letter**: after telling you the
  misspelling, QUILL reads it letter by letter. On to begin with.
- **Pause before spelling the word (milliseconds)** is how long it waits
  before spelling starts, from 100 to 3000. The default is 800.
- **Wrap spelling review to the beginning**: when the review reaches the end
  of the document, it offers to carry on from the top back to where you
  started. On to begin with.

### Spell Check Word (Alt+Shift+F7)

If you are used to checking just the word under the cursor in another word
processor, **Spell Check Word** (`Alt+Shift+F7`) is that. It checks only the
word at your cursor and leaves the rest of the document alone.

- If the word is spelled correctly, QUILL says so and that is all. No dialog
  opens.
- If it is misspelled, a small list opens with the same choices as the
  right-click spelling menu: suggested corrections, **Add to Dictionary** and
  **Ignore**. Pick one and you are back to typing.

Use `F7` when you want to work through a whole document or selection. Use
`Alt+Shift+F7` when you only want to check the one word in front of you.

### Moving between misspellings

Sometimes you would rather stay in the document and hop from one problem to
the next. `Ctrl+F7` moves to the next misspelling and `Ctrl+Shift+F7` to the
previous one. When you land on one, QUILL says the word and then spells it
(see How a misspelling is said, later in this chapter).

> **QUILLBee's shortcut:** Coming from Word? `Alt+F7` also jumps to the next
> misspelling, just as it does there.

To hear them all in one place, open the **Misspelling List** (`Alt+Shift+L`).
It lists every misspelling in document order. Arrow through it and press
Enter to jump to any one.

#### Ranked spelling

**Tools > Writing and Language > Misspelling List (Ranked by Frequency)...**
(`Alt+Shift+R`) shows
the same list in a different order. The word that turns up most often comes
first, and each entry carries its count, for example "teh (Ln 12, Col 4, 8
occurrences)."

A repeated typo or a single OCR misreading is usually the quickest thing to
fix first. Deal with one entry, by correcting it or with **Add to
Dictionary**, and you have dealt with every occurrence of that word at once.
Arrow through the list and press Enter to jump to any occurrence, exactly as
in the regular list. The document-order list on `Alt+Shift+L` stays as it
was, and it is still the default.

### Spell check as you type

With **spell check as you type** turned on, finishing a word the dictionary
does not know plays a soft spelling sound, and the status line shows "Possible
misspelling" with the word. The sound comes from your current sound pack; if
the pack has no spelling sound, you hear the Windows beep instead. QUILL uses a
sound here, not speech, so it never talks over your screen reader in the
middle of a sentence.

The check waits until you have **finished** a word, with a space, a comma or a
new line. It does not judge a word you are still typing, so "recie" on the way
to "receive" never sets it off.

Web addresses, email addresses, file paths and code are never treated as
misspellings. **What spell check reads**, below, has the details.

You can switch the spelling sound on or off by itself in **Tools > Reading and
Dictation > Sound Scheme...** (look for "Possible misspelling as you type"). The spell check as you
type toggle turns the whole live check on or off.

#### Quiet in code files

In source and configuration files the live check says nothing at all. That
covers `.py`, `.json`, `.js`, `.css`, `.ps1`, `.log`, `.yml` and the other
coding file types. Almost every name and setting in a file like that is a word
no dictionary knows, so you would hear nothing but wrong alerts.

Markdown is writing, so `.md` files **are** checked. Only the code blocks,
inline code, web addresses and email addresses inside them are skipped.

The setting is **`spellcheck_skip_code_files`**, and it is on by default.
Turn it off if you want the live check everywhere, whatever the file type.

`F7` is never silenced by this setting. The Spelling Review checks whatever
document you run it on, a code file included, reading its strings and
comments. Pressing `F7` is you asking for a check.

#### What spell check reads

Spell check reads what you wrote as language, and passes over the rest. This
applies everywhere: checking as you type, the **F7** review, next and previous
misspelling, the list of every misspelling, the context menu and browse
mode.

The file's extension picks one of four rules: writing, Markdown, markup or
code. The rule follows the document's name at the moment you check, so a new
document is read as writing, and once you save it as `notes.md` or
`script.py` the next check uses the Markdown or code rule.

**Every rule** skips these, wherever they appear:

- web addresses: `https://...`, `www.example.com`, `mailto:` and `file:`
  links, and a bare `example.com` (a common ending such as `.com`, `.org`,
  `.io` or `.uk`, or any domain followed by a path);
- email addresses;
- file paths: `C:\Users\...`, `\\server\share`, `./notes`, `~/notes`,
  `/usr/local/bin` and `docs\guide`;
- file names with an extension people recognise, such as `notes.txt`,
  `report.docx`, `song.mp3` or `setup.exe`.

Before this, checking `www.example.com` stopped on `www`, `example` and `com`
one by one.

**Writing.** Plain text, a document you have never saved, and any extension
not named below. The only things skipped are the ones above. Logs, tables and
patches (`.log`, `.csv`, `.tsv`, `.diff`, `.patch`) are read this way too,
because there is no code in them to find.

**Markdown.** `.md`, `.markdown`, `.mdown`, `.mkd` and `.mdx`. The writing
rule, and it also skips:

- inline code, with any number of backticks;
- fenced code blocks, between ```` ``` ```` or `~~~` lines;
- link and image addresses, and the address in a reference line such as
  `[1]: https://...`;
- HTML tags, and an HTML comment on one line.

It still checks link text and image alt text, because someone wrote those to
be read.

**Markup.** `.html`, `.htm`, `.xhtml`, `.xml`, `.xsl`, `.xslt`, `.svg`,
`.opml`, `.rss` and `.atom`. Spell check reads the text between the tags and
the comments. It skips the tags, attribute names and attribute values, except
the values people read or hear: `alt`, `title`, `aria-label`,
`aria-description` and `placeholder`. Inside `<script>` and `<style>` it reads
only the strings and comments, as it would in code.

**Code.** Only string literals and comments are checked. These extensions use
the code rule:

- C, C++ and other compiled languages: `.c`, `.h`, `.cc`, `.cpp`, `.cxx`,
  `.hpp`, `.hxx`, C# (`.cs`), Java, Go, Rust (`.rs`), Swift, Objective-C
  (`.m`, `.mm`), Kotlin (`.kt`, `.kts`), Scala, D (`.d`), Pascal (`.pas`),
  Fortran (`.f`, `.f90`) and assembly (`.asm`, `.s`);
- scripting: Python (`.py`, `.pyi`, `.pyw`), Ruby, Perl (`.pl`, `.pm`), PHP,
  Lua, Tcl, R, Julia (`.jl`), Dart, Groovy, Visual Basic and VBScript (`.vb`,
  `.vbs`);
- the web: JavaScript (`.js`, `.jsx`, `.mjs`, `.cjs`), TypeScript (`.ts`,
  `.tsx`), Vue, Svelte, and CSS with `.scss`, `.sass`, `.less` and `.styl`;
- shells and builds: `.sh`, `.bash`, `.zsh`, `.fish`, PowerShell (`.ps1`,
  `.psm1`, `.psd1`), batch files (`.bat`, `.cmd`), makefiles (`.mk`), CMake,
  Gradle, Inno Setup (`.iss`) and `.spec`;
- settings and data: JSON (`.json`, `.jsonc`, `.json5`), YAML (`.yaml`,
  `.yml`), TOML, `.ini`, `.cfg`, `.conf`, `.properties`, `.env`, `.plist`,
  `.reg`, `.lock`, `.map`, SQL, GraphQL (`.graphql`, `.gql`) and Protocol
  Buffers (`.proto`).

Inside a string or a comment it still skips:

- placeholders: `{0}`, `{name}`, `{0:N2}`, `{{` and `}}`, `%s`, `%d`,
  `%(name)s`, `${x}`, `$name` and `$(name)`;
- escapes such as `\n`, `\t`, `\x41` and `\u00e9`;
- words shaped like names in code: `snake_case`, any word with a digit in it,
  `camelCase`, and names like `HTTPServer`;
- the quote marks, and a string's prefix such as the `f` in `f"..."`, so a
  misspelled word in single quotes is reported without a quote stuck to it.

**How code and markup are read.** QUILL uses Pygments, which knows over five
hundred languages, to find the strings, comments and text. With Pygments it
also passes over regular expressions, single characters, the interpolated
parts of a string, preprocessor lines such as `#include`, and the `#!` line at
the top of a script. Pygments loads the first time you check a code or markup
file, so it costs nothing when QUILL starts.

A simpler built-in reader takes over when Pygments cannot load, when it has no
reader for an extension, or when the file is over 100,000 characters, where
Pygments would be slow. It knows the comments and strings of these families:

- `#` comments: Python, Ruby, Perl, the shells, PowerShell, R, Julia, Tcl,
  YAML, TOML, CMake, makefiles, `.conf`, `.properties`, `.env`, GraphQL and
  `.spec`;
- CSS and its relatives; SQL, with `--` comments; Lua; JSON, including `//`
  and `/* */` comments;
- Visual Basic and VBScript; batch files (`rem` and `::`); `.ini`, `.cfg`,
  `.reg` and `.iss` (`;` and `#` comments);
- everything else in the code list is read the C way: `//` and `/* */`
  comments and strings in double quotes, single quotes or backticks.

For markup, the built-in reader reads the text, comments and the attributes
above, reads `<script>` and `<style>` as code, and skips character entities
such as `&amp;`. It is less precise than Pygments, but it is never silent.

### Spell check a document before saving

Turn on **Settings > Editing > Spell check a document before saving** (off by
default) and QUILL opens the Spelling Review for you each time you save, so
you can fix misspellings before the file is written. Fix or skip them as
usual; the save then goes ahead with your corrections. This applies to
**Save** and **Save As** for the document you are working on.

### Spell-check language

**Tools > Writing and Language > Spell Check Language...** chooses the language the spell checker
uses. It affects both the `F7` review and the check as you type.

**English (United States)** is built in and works offline straight away. Other
languages are downloaded when you first choose them. Pick **Spanish (Spain)**
or **French (France)**, for example, and QUILL fetches that dictionary from
its own verified source. The download is checksum-checked, and a progress
window lets you cancel it. After that the language works offline, just like
English.

QUILL remembers your choice between sessions. If you are offline, or you
cancel the download, English keeps working and nothing else changes. The
downloaded dictionaries are kept in your QUILL data folder, so reinstalling or
upgrading QUILL never makes you fetch them again.

## How a misspelling is said

Speech alone cannot tell you what is wrong with a misspelled word. "receive"
and "recieve" sound the same, so hearing the word tells you nothing. **The
letters are the answer.** So when you land on a misspelling, with Next or
Previous Misspelling or in the `F7` review, QUILL says the word, pauses, and
then spells it.

The spelling comes as a second, separate announcement, so you can cut it off.
Press your next key and the spelling is cancelled before you hear it. If you
are moving fast you lose nothing, and if you want the letters they are there.

Twelve settings under **Spelling** in Settings control all of this. Both
editors also gather them in a window of their own. In QUILL it is **Spelling
Announcements**, on `Ctrl+Alt+Shift+F6`, or type its name in the command
palette (`Ctrl+Shift+P`); it has no menu item in QUILL. In QUILL Lite it is
**Announcements...**, on the Spelling submenu of its Tools menu. They are the same twelve settings in the same file, so
setting them up once sets up both editors.

### While you are typing

- **Play a sound when you type a misspelling** (`spelling_alert_sound`)
  plays the falling blip when you finish a misspelled word. Turn it off for
  silence.
- **Also say the word when you type a misspelling** (`spelling_alert_speech`)
  speaks the word as well. It is off by default, because being interrupted
  while you are writing costs more than it tells you.
- **Shortest gap between two alerts for the same word (milliseconds)**
  (`spelling_alert_repeat_ms`) is the shortest time before the same word is
  reported again, so one stubborn name does not become a drumbeat. Zero means
  every time. The default is 750.

Whichever way you set those two, the status bar always shows the word, for
example "Possible misspelling: teest", so you can read it with your screen
reader whenever you like. QUILL does not speak that status line on its own;
it is spoken only when **Also say the word when you type a misspelling** is
on, which is what the setting means in QUILL Lite too.

### Spelling a word out

- **Spell misspelled words out letter by letter** (`spell_aloud_enabled`)
  is the main switch.
- **How letters are spoken** (`spell_aloud_style`) chooses how the letters
  are said. Plain **Letters (R, E, C)** are fastest. The **Phonetic alphabet
  (romeo, echo, charlie)** is clear where B, D, E, P, T and V all sound alike.
  **Letters, then the phonetic alphabet** is for learning a word rather than
  checking one.
- **Say which letters are capitals** (`spell_aloud_capitals`) says "cap"
  before a capital letter, so you can tell MacDonald from Macdonald. It is
  worth having, because letters are always spoken as capitals, whatever the
  word does (several voices read a single lower-case letter as a word).

### When the letters follow

There are three pauses, because the right wait is different in each place.

- **Pause before spelling a word (milliseconds)** (`spell_aloud_delay_ms`)
  is the pause in the `F7` review, where you have stopped to decide. The
  default is 800 ms.
- **Spell the word when you move to a misspelling**
  (`spell_aloud_on_navigation`) and **Pause before spelling when moving
  between misspellings (milliseconds)** (`spell_aloud_navigation_delay_ms`)
  cover Next and Previous Misspelling. There you may just be passing through,
  so the default pause is shorter, 600 ms.
- **Spell each suggestion as you arrow through them**
  (`spell_aloud_suggestions`) and **Pause before spelling a suggestion
  (milliseconds)** (`spell_aloud_suggestion_delay_ms`) spell whichever
  correction you arrow onto in the suggestions. Choosing between two
  spellings by ear is as hard in a list as it is in the document.
- **Spell the first suggestion on arrival** (`spell_aloud_first_suggestion`)
  also spells the top suggestion when the review reaches a new word. It is
  off by default, because it doubles what you hear each time you arrive.

## The thesaurus, Look Up and other word tools

The rest of the writing and language commands on the **Tools** menu are about
words themselves: finding a better one, finding out what one means, and
counting them. Chapter 4, Writing and editing, gives a short introduction;
this is the fuller story.

### Thesaurus (Shift+F7)

**Tools > Writing and Language > Thesaurus...** (`Shift+F7`) opens a two-pane picker for the word you
are on. It finds the word even when it is in another form, so "running" finds
"run", and when you choose a replacement it goes back in the form your
sentence needs.

### Look Up Word (Alt+F10)

**Look Up Word...** (`Alt+F10`) is a dictionary with no AI. Out of the box it
uses the thesaurus, which works offline. Check **Use online sources** in the
window and it also brings definitions, more words, and a Wikipedia summary
from three free online services. Nothing goes online until you check that box.

### Say Word Summary and Dictionary Status

- Press `Ctrl+Alt+Shift+[` for **Say Word Summary**, which says what the
  thesaurus knows about the word you are on, without opening a window. There is
  no menu item for it; the key or the Command Palette (`Ctrl+Shift+P`) reaches
  it.
- **Dictionary Status...** (`Alt+Shift+;`) shows which spelling engine QUILL
  is using, how many words are in your personal, document and project
  dictionaries, and whether the thesaurus is installed.

### Document Statistics (Ctrl+Shift+G)

**Tools > Writing and Language > Document Statistics...** (`Ctrl+Shift+G`)
says how big your document is, without opening a window. It used to be
called Word Count. It now has the same name and key as in Word and QUILL Lite.

Press it once and you hear the counts, for example *"1,240 words, 96 lines,
7,315 characters."*

Press it twice quickly and you hear the full writing report as well:
paragraphs, sentences, how many sentences run over 30 words, the reading time
and the reading grade. For example: *"1,240 words, 96 lines, 7,315
characters, 31 paragraphs, 84 sentences, 3 long sentences over 30 words,
about 7 minutes to read, reading grade about 9th grade."*

- **Select some text first** and both presses count only the selection. The
  sentence then starts with *"Selection:"* so you know which you got.
- **Paragraphs.** When your text leaves a blank line between paragraphs, as
  Markdown does, a paragraph is everything between blank lines. When it never
  does, each line is a paragraph, the way a word processor counts them.
- **Long sentences** are the ones worth a second look. Thirty words is about
  the point where a listener starts to lose the thread.
- **Reading time** assumes 200 words a minute, the same figure the status bar's
  reading-time cell uses, so the two always agree.
- **Reading grade** is the Flesch-Kincaid grade level: roughly the school year
  a reader needs to follow the text easily. From grade 13 up you hear *"college
  level"*. With too little text to judge you hear *"no reading grade"*.
- **How quick is quickly?** The second press must come within the
  **Multi-press time window (ms)** in **Settings > Editing** (400
  milliseconds to start with), the same window the Copy Tray keys use. Wait
  longer and you just hear the counts again.

The long report is always spoken, even if you have turned off spoken counts:
pressing twice is asking for it.

## Sounds, and turning them off

QUILL plays short sounds, called earcons, for things your screen reader does
not mention, like a misspelling or a paste. Here is how to silence them all at
once, change one, or build a set of your own.

### Where QUILL's sounds play, and turning them off

QUILL makes short sounds of its own. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns QUILL's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Tools > Reading and Dictation > App Sounds** has a check mark that shows whether they are on.
- The **App Sounds Play On...** button in **Tools > Reading and Dictation > Sound Scheme...** (`Ctrl+Alt+Shift+O`) lets you pick where they play:
  - **System default**. This is where it starts. The sounds go where Windows sends sound.
  - **None (no sounds)**. QUILL makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and QUILL tells you once. When the device comes back, the sounds go back to it by themselves.

This changes QUILL only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved. Until October 2026, Alt+Shift+M silenced QUILL and QUILL Lite together. Now every QUILL app has its own, on the same key; to silence all of them at once, turn off **Sound notifications** in Settings.

### The Sound Scheme window

**Tools > Reading and Dictation > Sound Scheme...** (`Ctrl+Alt+Shift+O`) lists every sound QUILL can
make, and lets you hear them.

As you arrow through the list, each event plays as you land on it. That turns
a list of about a hundred and forty sound names into something you can
browse by ear. It is a checkbox under the list, so if you are hunting for one
row you can turn it off and pass the rest in silence.

Each row tells you everything about itself: its group, the event, whether it
is switched on, which file it plays and how long that file is. Your screen
reader reads it all as you arrive, so you never have to Tab away to find out.
The buttons underneath work on the row you are on:

| Button | What it does |
|---|---|
| **Play** | Play this event now, even when the event is switched off |
| **Switched on** | Silence this one event without changing which sound it has |
| **Browse...** | Use a WAV file of your own |
| **No Sound** | Remove the sound from this event entirely |
| **Use Default** | Put this one event back to the sound the scheme ships |

QUILL refuses a file that is not a WAV, is longer than ten seconds, or is
bigger than two megabytes, and tells you why when you choose it. Better to
hear about it then than to have the event go silent later with no clue why.

- **Save As Scheme** saves the whole set under a name you choose, as an
  ordinary folder with the sounds copied into it. It keeps working after you
  tidy your Downloads folder, and you can zip it up and send it to a friend.
- **Delete Scheme** removes one of your own schemes. The schemes that come
  with QUILL cannot be deleted.
- **Restore All Defaults** puts every event back and switches them all on.
  It always works completely, because QUILL never overwrites the sounds it
  ships.

QUILL Lite opens the same window over the same schemes, so a scheme you make
in one editor is offered in the other.

The **Scheme** list at the top also offers **VS Code Signals**: the sounds
Visual Studio Code plays for its own accessibility signals, used under the MIT
licence. They cover errors, warnings, saving, finished and failed tasks, AI
requests and answers, dictation and recording starting and stopping, and undo
and redo. Anything they have no sound for stays quiet, or is spoken where QUILL
speaks instead. Choose it in one app and the rest of the family plays it too,
each from the next time it starts.

### The sounds themselves

The **Ink** pack that comes with QUILL has a sound for every event. That
includes the ones desktop programs have had for decades: open, close, cut,
copy, paste, delete, undo, redo, print, information, question and task
finished. Those are the moments a screen reader says nothing about; nothing
is announced when a paste lands, for example.

Related sounds share a tone and differ by direction, so you learn a family
once instead of one sound at a time.

- **Undo and redo are the same figure, played backwards from each other.**
- Open and close are one pair of bells, rising and falling. App start and app
  exit are the same pair, one note longer.
- Cut, copy and paste are one dry wooden tick in three gestures. Delete is
  that tick dropped an octave and a half, with a breath of noise underneath.
- Nothing to undo does not move in pitch at all, because nothing moved.

## Starting with a blank document, or not

When you start QUILL without opening anything, it gives you an empty
**Untitled** document, as most editors do. If you always open an existing
file and would rather not close a blank one every time, turn off
**open_blank_document_at_startup**, under **General** in Settings.

Turning it off changes only that one case. A file you double-clicked, a file
named on the command line, the documents from your last session and recovered
unsaved work all still open. QUILL Lite has the same setting, with the same
name, in **Preferences**.

## Spelling keys at a glance

These work straight from the document, without opening a dialog first.

| Key | Action |
|---|---|
| `F7` | Open the Spelling Review |
| `Alt+Shift+F7` | Spell Check Word, the word at the cursor |
| `Ctrl+F7` | Jump to the next misspelling |
| `Ctrl+Shift+F7` | Jump to the previous misspelling |
| `Alt+Shift+L` | Misspelling List |
| `Alt+Shift+R` | Misspelling List, ranked by frequency |
| `Shift+F7` | Thesaurus |
| `Alt+F10` | Look Up Word |
| `Ctrl+Alt+Shift+[` | Say Word Summary |
| `Alt+Shift+;` | Dictionary Status |
| `Ctrl+Alt+F9` | Add Word to Dictionary, the word at the cursor |

Press `Ctrl+Alt+F9` for **Add Word to Dictionary**. It teaches your personal
dictionary the word at the cursor, so a name or a word from your work stops
being called a misspelling, in this document and every other. If the word is
already there, QUILL tells you and changes nothing. It has no row on the menu
bar: use the key, the Command Palette (`Ctrl+Shift+P`), or **Add to
Dictionary** in the spelling choices for a misspelled word.

## What you learned, and where to go next

You can now check a whole document with `F7`, or one word with
`Alt+Shift+F7`, and hop between misspellings with `Ctrl+F7`. You know how to
put the most common mistakes first, how QUILL spells a word out and how to
tune that, and how to pick a spell-check language. You met the thesaurus,
Look Up Word and Document Statistics, and you can silence QUILL's sounds with
`Alt+Shift+M` or change them in the Sound Scheme window.

To practise with QUILL open, try the lesson "Spelling, words, and the
thesaurus" in **Help > Tutorials...** (`Ctrl+Alt+F1`).

Next, Chapter 8, Reading, reviewing and listening, shows you how to have your
work read back to you and how to check a document before you share it.

---

- Previous: [Chapter 6: Moving around and finding things](quill-guide-06-moving-around-and-finding-things.html)
- Next: [Chapter 8: Reading, reviewing and listening](quill-guide-08-reading-reviewing-and-listening.html)
- [Contents](../userguide.html)
