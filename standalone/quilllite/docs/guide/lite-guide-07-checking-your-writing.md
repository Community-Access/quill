# Chapter 7: Checking your writing

WordPad never had a spell checker. QUILL Lite has the same one QUILL uses, and
it is made to be heard rather than seen: a short sound when you finish a word
it does not know, the letters spelled out when you want them, and the
Applications key to fix the word you are on. This chapter covers all of that,
then the thesaurus and the dictionary for finding a better word, and finally
how to find out exactly which character your cursor is on.

## Spell check

QUILL Lite has a spell checker, the same one QUILL uses. WordPad never had
one. You can check as you type, check the whole document, or fix one word at
a time.

### Checking the whole document

Press **F7** to check the whole document. Here is what happens:

1. QUILL Lite finds the next misspelled word and shows you suggestions.
2. Arrow through the suggestions.
3. Choose what to do: change this word, change every one like it, skip it, or
   add it to your dictionary so it is never questioned again.

The check starts where your cursor is, just as in Word. When it reaches the
end of the document, it tells you, then carries on from the beginning. If
you would rather it simply stopped at the end, you can turn that off in
Preferences.

### What spell check reads

Spell check reads what you wrote as language, and passes over the rest. This
applies everywhere: checking as you type, the **F7** review, next and previous
misspelling, the list of every misspelling and the context menu, exactly
as in QUILL, which shares this code.

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

**How code and markup are read.** QUILL Lite uses Pygments, which knows over five
hundred languages, to find the strings, comments and text. With Pygments it
also passes over regular expressions, single characters, the interpolated
parts of a string, preprocessor lines such as `#include`, and the `#!` line at
the top of a script. Pygments loads the first time you check a code or markup
file, so it costs nothing when QUILL Lite starts.

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

### The spelling keys

| Key | What it does |
|---|---|
| **F7** | Check the whole document |
| **Alt+Shift+F7** | Suggestions for the word you are on |
| **Ctrl+F7** / **Ctrl+Shift+F7** | Go to the next / previous mistake |
| **Alt+Shift+L** | List every misspelling, with its line |
| **Ctrl+Alt+F9** | Add this word to your dictionary |
| **Ctrl+Alt+F7** | Turn checking-as-you-type on or off here |
| **Ctrl+Alt+Shift+F7** | Spelling Announcements: how a misspelling is said |

**Alt+Shift+F7** and **Ctrl+Alt+F9** work from anywhere in a word, not only
from its first letter.

#### Hearing the letters

**Ctrl+F7** takes you to the next mistake and selects it, so your screen
reader reads the word. Then, after a short pause, QUILL Lite spells it out.
That matters because "receive" and "recieve" sound exactly the same. The
letters tell you what is wrong. If you do not need the spelling, just press
your next key and it stops.

#### Every misspelling in one list

**Alt+Shift+L** lists every misspelling at once, with the line each one is
on. Press **Enter** on a row to go there. This is handy when you want to know
how many mistakes there are, or pick which one to fix first. Words you have
chosen to ignore are left out.

### While you type

When you finish a word that is not in the dictionary, you hear a short
falling blip, and the status bar shows which word it was. "Finish" means you
typed a space, a comma or a new line after it, so you are never interrupted
in the middle of a word. It is a sound rather than speech, so it does not
talk over the sentence you are writing.

You can silence the sound, have the word spoken as well, or change how long
it waits before mentioning the same word again. All of that is in
**Tools > Spelling > Announcements...** (**Ctrl+Alt+Shift+F7**).

If you would like to try spelling with the app guiding you, the tutorial
*Spelling, without a red squiggle* walks through typing a mistake, fixing it,
teaching a word and checking the whole document.

### Spelling Announcements

The Spelling Announcements window has twelve settings in three groups. QUILL
has the same twelve settings under **Spelling** in its Settings window, so
setting them up once sets up both.

#### While you are typing

Whether the sound plays at all, whether the word is spoken too (off to begin
with), and how long to wait before the same word is mentioned again. Zero
means every time.

#### Spelling a word out

Whether words are spelled out at all, and how:

- **Letters** are the fastest.
- **The phonetic alphabet** (romeo, echo, charlie) is clearer when B, D, E, P,
  T and V all sound alike, such as with a fast voice, a poor speaker or a
  noisy room.
- **Both** is good for learning a new word.

You can also have capitals named, so "cap M, A, C, cap D" tells MacDonald
from Macdonald. An example box shows what your choices sound like, and says
it out loud as you change them.

#### When the letters follow

There are three pauses before a word is spelled out, one for each place it
happens:

- in the **F7** check, where you have stopped to decide, the pause is longer;
- when moving between misspellings, it is shorter;
- in a list of suggestions, where you are arrowing, it is shorter again.

You can switch each one off on its own.

### The word you are on: the Applications key

This is the quickest way to fix a word as you go:

1. Put your cursor in a word QUILL Lite thinks is misspelled.
2. Press the **Applications key** (or **Shift+F10**).
3. Press **Down Arrow** once. You land on the first suggestion.
4. Press **Enter** to use it.

No window opens and your cursor stays where it was. A sighted person spots a
red squiggle and right-clicks it. For you, the Applications key is the
squiggle, and the first thing it offers is the answer.

The menu is always laid out the same way:

1. The suggestions, at the top.
2. A separator, then one row called *Spelling Actions for "wrold"* (with your
   word in it).
3. The **Thesaurus** and **Dictionary** submenus for the word (see below).
4. When your cursor is on a web address, two rows for it: **Open** followed by
   the address, which opens it in your web browser, and **Copy Link
   Address**. They are there for a plain address, a Markdown link and an HTML
   link alike, and they are simply not in the menu when there is no link.
5. The everyday rows: Undo, Redo, Cut, Copy, Paste, Delete, Select All.

Only the number of suggestions changes. Everything after them stays in the
same order, so you can learn it once.

#### Inside Spelling Actions

| Row | What it does |
|---|---|
| **Ignore Once** | Skip this one place. Nothing is remembered after you close the window. |
| **Ignore in This Document** | Stop reporting this word anywhere in this document, until you close it. |
| **Add "word" to My Dictionary** | Keep it for good, in your own dictionary. |
| **Add to This Document Only** | Keep it beside this file, so anyone who opens the file gets it too. |
| **More Suggestions...** | The full list, in a window you can arrow through. |
| **Check Document...** | The F7 check, from here. |
| **Next / Previous Misspelling** | Move on without leaving the keyboard. |

A word you ignore is ignored everywhere: you stop hearing about it as you
type, **Ctrl+F7** stops going to it, and **Alt+Shift+F7** stops offering
suggestions for it. Ignoring lasts until you close the document. To keep a
word for good, add it to a dictionary.

### Thesaurus and Dictionary on any word

The Applications key menu has two more submenus on **any** word, spelled
right or not. They come after the spelling rows and before the everyday rows,
and both name the word they are about, so you always know what they will do.

- **Thesaurus for "running"** opens on the best replacements. Press **Enter**
  on *sprinting* and it replaces *running*. QUILL Lite looks the word up as
  *run*, then gives you the replacement back in the *-ing* form, with the
  same capitals as your word. Below the first meaning, each other meaning has
  its own submenu (for example "As a noun: ..."), then an **Opposites**
  submenu, then **Say Word Summary**, which tells you what the thesaurus knows
  without opening anything, and **More in Thesaurus...**, which opens the full
  thesaurus window.
- **Dictionary for "running"** starts with **Look Up "running"...**, the
  dictionary that works without AI (see *Dictionary*,
  later in this chapter). When AI
  help is on, it then offers the twelve questions the AI dictionary can
  answer about the word as it is used in *this* sentence: Define in Context,
  Synonyms That Fit, Simpler Word, More Formal Word, More Vivid Word,
  Opposites, Is This the Right Word?, Use It in a Sentence, Where It Comes
  From, How to Say It, Rhymes, and the Word Explorer, which answers all of
  them at once. Last comes **Find the Word For...**, the reverse dictionary.
  If AI help is on but the AI in use is the free one, the submenu has one row
  that tells you so and opens Choose Your AI.

If you have selected a single word, that word is used instead of the one at
the cursor. There is no Thesaurus row on a number or on empty space.

On a word that is spelled correctly, there is no Spelling Actions row at all,
just the thesaurus, the dictionary and the everyday rows.

QUILL has the same menu in the same order, with one extra dictionary for its
projects.

### When it stays quiet

Some files are not writing at all. They hold settings and instructions for
programs, full of made-up words and abbreviations that no dictionary knows.
Checking those as you type would give you a stream of warnings that are all
wrong.

So QUILL Lite does not check those files as you type. It recognises them by
the kind of file they are, and tells you once when you open one, so you know
nothing is broken.

If you do want checking in one of them, press **Ctrl+Alt+F7**. It changes
only the document you are in. **Tools > Spelling** shows a check mark beside
**Check While Typing** so you can always see which way it is set.

**F7** always works, in every file. If you ask for a check, you get one.

### Your dictionary

Words you teach QUILL Lite are kept in your own dictionary, in QUILL Lite's
folder. If you also use QUILL, one setting in Preferences lets both share the
same list, so a word you teach either one is known to both.

A single document can also have its own short word list, kept in a small file
beside it. That is useful for names that belong to one piece of work and
nowhere else.

## Thesaurus

The thesaurus helps you find a different word for the one you have. Press
**Shift+F7**, the same key as in Word and QUILL, or choose
**Tools > Thesaurus...**. It opens on the word you are on, or the word you
selected. If your cursor is not on a word, it asks you for one.

It is the same thesaurus QUILL uses, and it comes inside QUILL Lite. Nothing
is downloaded and nothing is sent anywhere.

### It finds the word you mean

A thesaurus lists plain forms of words: *run*, not *running*; *happy*, not
*happier*. QUILL Lite works your word back to its plain form for you
(running to run, studies to study, happier to happy, stopped to stop) and
tells you so in the title, for example "running (as run)", and in each
meaning's row, for example "verb, from run: sprinting, dashing, ...".

### Replacements come back in the right form

Choose *sprint* for *running* and your document gets *sprinting*. Choose
*glad* for *Happier* and you get *More glad*, because QUILL Lite knows which
words take *-er* and which take *more*. It knows irregular verbs too:
replacing *sought* with *seek* gives you *sought*. If it is not sure of a
form, it gives you the plain word rather than guess.

### Using the thesaurus window

1. You start in the **Senses** list. There is one row per meaning, with the
   part of speech first. Type **n** to jump to the nouns, or **v** to the
   verbs.
2. Press **Tab** to reach the words for the meaning you picked. You get
   replacements first, then *broader:* words, then *opposite:* words, each
   labelled.
3. Press **Enter**, or choose **Replace**, to put the word in place of yours.
   The selection is then cleared, so your next keystroke cannot type over it.

Other choices:

- **Copy** puts the word on the clipboard instead, and tells you so.
- **Escape** closes the window and changes nothing.
- If you typed the word into the thesaurus rather than starting from your
  document, Replace is not available and Copy is the default.

### A quick summary without opening anything

**Say Word Summary** (**Ctrl+Alt+Shift+[**) tells you what the thesaurus
knows about a word, without opening a window. You hear something like:
"running, looked up as run: 27 meanings as a verb, 6 as an adjective, 3 as a
noun. First: sprinting, dashing, ... Opposites: standing, ...". It is also in
the Thesaurus submenu of the Applications key menu. It is a good way to
decide whether the full window is worth opening.

### Checking your word lists

**Tools > Spelling > Dictionary Status...** (**Alt+Shift+;**) tells you
how many words are in your personal dictionary and in this document's own
list, where each file is kept, and whether the thesaurus is there.

### Turning it off

The thesaurus and dictionary are one switch in Customize Features, called
**Dictionary and thesaurus**. It is on to begin with, and off in the WordPad
and Notepad profiles.

## Dictionary

QUILL Lite has two dictionaries. The first, Look Up, works without AI. The
second uses AI to answer questions about a word as it is used in your
sentence.

### Look Up: the dictionary without AI

To open it, press **Alt+F10** (**Tools > Look Up Word...**), or choose
**Look Up "word"...** at the top of the Dictionary submenu on any word. It is
the same Look Up window QUILL has.

1. You start in the **Result**, a read-only box you can arrow through. It
   gives the word, then a labelled section for each kind of answer.
2. Under it, **Words you can use** lists every synonym, opposite, related
   word and rhyme, each saying which it is.
3. Press **Enter**, or choose **Replace Word**, to put the selected word in
   place of yours.

You can also choose **Copy** to copy the selected word (or the whole result,
if nothing is selected), or **Add to Dictionary** to teach the word to your
spelling dictionary.

#### Without the internet

When you are offline, Look Up gives you synonyms, opposites and related words
from the word list inside QUILL Lite. Nothing leaves your computer.

#### With the internet, when you say so

There is a checkbox called **Use online sources**. It is off until you check
it. When it is on, the word, and only the word, never your sentence or your
document, is sent to three free services that need no account and no key:

- the Free Dictionary, for definitions with examples,
- Datamuse, for more synonyms, opposites, rhymes and related words,
- and Wikipedia, for a short summary with a link to the article.

You see the offline answer straight away and hear "Looking up online". When
the online answer arrives, it replaces the result and you are told. If
Wikipedia has no real article for the word, there is simply no encyclopedia
section.

QUILL Lite remembers your choice, and so does QUILL if the two share
settings, so you are not asked again. Uncheck the box and you are offline
again from the next lookup.

### The AI dictionary

The rest of **Tools > Dictionary**, and of the Dictionary submenu on a word,
uses AI to read the sentence your word is in. The offline thesaurus knows
every meaning of *bank*, but it cannot tell which one your sentence means.
These twelve questions send **the word and the sentence it is in** (never the
rest of your document) and answer in plain words written to be listened to.
Where it helps, you also get a list of choices, each with a reason.

| Row | Key | What comes back |
|---|---|---|
| **Define in Context** | Ctrl+Alt+Shift+' | What the word means *here*, its part of speech, and the meaning you might be confusing it with |
| **Word Explorer...** | Ctrl+F10 | Everything at once: meaning, how to say it, an example, where it comes from, what it is confused with, and the best replacements |
| **Synonyms That Fit** | Ctrl+Shift+; | Replacements that keep this sentence's meaning and tone, already in the right form |
| **Simpler Word** | Ctrl+Shift+- | Plainer, more widely known words, and what is lost |
| **More Formal Word** | Ctrl+Shift+= | Words suited to professional writing |
| **More Vivid Word** | Ctrl+Shift+' | Livelier or more specific words |
| **Opposites** | Alt+Shift+- | Opposites that would fit in the word's place |
| **Is This the Right Word?** | Ctrl+Alt+Shift+/ | Affect or effect, complement or compliment: a plain yes, or the difference and the right word first |
| **Use It in a Sentence** | Alt+Shift+= | Three short example sentences in the same sense |
| **Where It Comes From** | Alt+Shift+, | The word's origin and how its meaning developed |
| **How to Say It** | Alt+Shift+' | Syllables with the stress in capitals, a plain respelling, the IPA, and the common mispronunciation |
| **Rhymes** | Ctrl+Alt+Shift+; | Perfect rhymes first, then near rhymes, with syllable counts |
| **Find the Word For...** | Ctrl+Alt+Shift+] | The reverse dictionary: describe the meaning, get the word, inserted at the cursor |

#### The answer window

1. You start on the answer, so your screen reader reads it to you.
2. Press **Tab** to reach **Choices**: one line per replacement, with a note.
3. Press **Enter**, or choose **Use This Word**, to put the selected word in
   place of yours (or at the cursor, for Find the Word For). One **Ctrl+Z**
   takes it back.

Other buttons:

- **Copy Choice** and **Copy Answer** copy to the clipboard.
- **Ask Something Else...** closes the answer and opens the Dictionary
  submenu again on the same word.

If you typed over the word while the answer was on its way, Use This Word is
not available and tells you why. Copy still works.

#### What you need for it

The AI dictionary works on any AI except the free one: your ChatGPT plan,
GitHub Copilot, Codex or your own key. It does not use QUILL's free AI service,
because a dictionary gets asked many times a day and would use up the free
allowance quickly. On the free AI, every row tells you so and opens Choose Your
AI. All
of these rows switch off together when you turn off **AI help** in Customize
Features. Chapter 10, AI help, explains how to connect a key or sign in.

## Inline notes

An inline note is a comment you attach to a line or a selection: a question, a
reminder, or what you think of a plan somebody sent you. They are on **Tools >
Inline Notes**, on the same keys as in QUILL.

- **Alt+Shift+I** (**Add Inline Note...**) adds a note to the selected text, or
  to the line you are on if nothing is selected. The **Note on** line at the
  top shows the start of that text, so you can check you are in the right
  place before you save.
- **Alt+Shift+J** and **Alt+Shift+K** (**Next Inline Note** and **Previous
  Inline Note**) move to the next or previous note and read it to you. They
  go round from the end to the start.
- **Alt+Shift+H** (**Speak Inline Note**) reads the note you are on. Press it
  twice quickly to change or delete the note.
- **Alt+Shift+Delete** (**Delete Inline Note...**) deletes the note you are
  on. QUILL Lite reads you the note and asks first; No is the default.
- **Alt+Shift+Enter** (**List Inline Notes...**) shows every note in the
  document: the note, the line it is on, the text it is about, and whether it
  is private or in the file. **Enter** goes to a note, **Delete** deletes one
  and **F2** edits one. The buttons let you **Remove All** of them (you are
  asked first), **Copy All** of them as plain text, or **Export** them to a
  Markdown or JSON file.

A note follows its text as you edit. If the text is deleted, the note is not
lost: the list shows it at the end, marked "the text it was on is gone", so you
can read it and remove it.

### Hearing which lines have notes

As you arrow through a document, QUILL Lite plays a soft two-tap sound when the
cursor arrives on a line that has an inline note, private or in the file. It
plays once as you arrive, and never while you move along that same line with
the left and right arrows, `Home`, `End` or `Ctrl+Left` and `Ctrl+Right`. Move
off the line and back, and you hear it again. A note on a selection that runs
over several lines counts as one place: you hear it as you enter, not on every
line of it.

For example, you have a note on the line "Back up the uploads folder." Arrow
down: on the line before, nothing; on that line, the tap; then press `Alt+Shift+H`
to hear the note itself.

To change it, open **Preferences** and find **When the
caret reaches a line with an inline note** (the `inline_note_line_cue`
setting). The choices are **Play a sound** (the default), **Say "note"**, and
**Nothing**. A few things to know:

- With the sound chosen, a braille display also shows the word "note", because
  a sound does not reach somebody reading in braille without speech. With the
  word chosen, your screen reader's braille shows it already.
- If your sound pack has no sound for this, QUILL Lite says "note" instead, so the
  setting never ends up silent by accident. You can change or switch off the
  sound itself in **Sound Scheme**, where it is listed as "Arrived on a line
  with an inline note".
- **Next Inline Note** and **Previous Inline Note** read you the note itself,
  so arriving with them plays no tap on top.

### Private notes and notes in the file

Normally a note is private. It is kept in QUILL Lite's own folder, the document
is never changed, and nobody else sees it. That works in every kind of document.

In a Markdown or HTML document, you can check **Write this note into the file**
instead. The note goes into the document as a hidden comment on its own line,
right after the text it is about:

    Back up the uploads folder.
    <!-- quill-note: And the database dump. -->

The file is still a proper Markdown or HTML file, and web pages hide the
comment. But anyone who opens the file in a text editor, or an AI assistant you
give it to, can read your note. That is the way to review a plan an AI
assistant wrote for you: leave your notes in the file and hand it back. Because
the note is part of the text, **Ctrl+Z** takes back adding, changing or deleting
it.

The check box remembers your choice for each document. To start every new note
in the file, turn on **Write new inline notes into the file** in
**Preferences**. It is off unless you change it.

### Notes from the command line

A script, or an AI assistant working in a terminal, can read and clear the
notes in a file without opening a window:

- `QuillLite.exe --notes list plan.md` prints every note, its line and the text
  it is about. Add `--json` for a list a program can read.
- `QuillLite.exe --notes check plan.md` says how many notes are left.
- `QuillLite.exe --notes clear plan.md` removes them all and saves the file.

The exit code is 0 when it worked (or, for `check`, when no notes are left), 3
when `check` finds notes still there, 1 when the file cannot be read or
written, and 2 when the command is mistyped. Private notes never appear here.

## What is this character?

Press **Ctrl+Shift+C** to hear exactly which character your cursor is on: its
name, and how it behaves when you search.

This helps more than you might think. Your screen reader says "space" for
several different characters that sound the same but act differently. One of
them is often the reason a search will not find text that is plainly there.

For the full details, press **Ctrl+Alt+C**. It opens a window you can read
line by line.

A **page break**, the character a PDF has between its pages, is named as one:
**Ctrl+Shift+C** says "Page break", and **Ctrl+Alt+C** adds that one page ends
there and the next begins. See [Page breaks, and what you hear](lite-guide-03-opening-saving-and-printing.html#page-breaks-and-what-you-hear).

## What you learned, and where to go next

**F7** checks the whole document, **Ctrl+F7** hops between mistakes and spells
each one out, and the Applications key fixes the word you are on, or opens
or copies a web address your cursor is on. You can
quiet or tune the spelling sounds, and teach QUILL Lite your own words.
**Shift+F7** opens the thesaurus and puts a better word in place, already in
the right form, and **Say Word Summary** tells you what it knows without
opening anything. **Alt+F10** looks a word up, offline or online as you
choose, and the AI dictionary answers questions about a word as it is used in
your sentence. **Ctrl+Shift+C** names the character under your cursor, which
helps when a search will not find something you know is there.

To practise spelling with the app guiding you, try the tutorial *Spelling,
without a red squiggle*.

Next, Chapter 8, What you hear, explains what QUILL Lite says out loud, the
sounds it plays, and how to catch a message you missed.

---

- Previous: [Chapter 6: Formatting, headings and the Insert menu](lite-guide-06-formatting-headings-and-the-insert-menu.html)
- Next: [Chapter 8: What you hear](lite-guide-08-what-you-hear.html)
- [Contents](../userguide.html)
