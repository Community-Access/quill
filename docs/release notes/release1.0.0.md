# QUILL 1.0

*Version 1.0.0. From Community Access. Free.*

Welcome to QUILL. It is a writing, reading and document suite for people who
work by ear and by touch: blind and print-disabled readers, writers, students,
proofreaders and braille transcribers, and anyone who uses a computer from the
keyboard instead of a mouse.

I built QUILL with a screen reader running, and every feature started with two
questions: what will you hear, and what will your fingers read on a braille
display? The screen comes after that. If a feature could not be made to work
well by ear, we changed it until it did, or we left it out.

These notes describe the whole of QUILL 1.0.0, written for someone opening it
for the first time. They are not a list of what changed since the last
version. Every key named here works, every limit is stated plainly, and you
should not have to discover anything important by accident.

You'll meet two friends in these notes. QUILLBert finds things worth trying,
and QUILLBee explains. They're new around here, and
[Meet QUILLBert and QUILLBee](https://www.quillforall.org/meet-quillbert-and-quillbee.html)
has the proper introductions.

## Try this first

1. Open QUILL. The first time, a short welcome asks what kind of writing you
   do. Answer it, or choose Full QUILL to get everything.
2. Type something, and press **Ctrl+S** to save it.
3. Press **Ctrl+Shift+P** and type a word, such as "sort" or "count". The
   Command Palette finds the command and tells you its key.
4. Press **F1** on anything you are unsure of, and QUILL explains it.
5. When you have ten minutes, press **Ctrl+Alt+F1** for the guided tutorials.

> **QUILLBert found something:** He pressed **F9** just to see what would
> happen, and QUILL said the last thing it had told him, again. Then he tried
> **Shift+F9** and got the whole list. He has been pressing it ever since.

> **A note from QUILLBee:** Coming from a QUILL beta? A few keys have moved
> since then. Type a command's name into the Command Palette
> (**Ctrl+Shift+P**) to hear its key today, or open the Keymap Editor
> (**Ctrl+Alt+Shift+Space**) to put a key back where your fingers expect it.

---

## What ships in 1.0.0

Four programs carry the QUILL name in this release.

**QUILL** is the editor. It handles plain text, Markdown, HTML, rich text,
Word, braille, e-books, PDFs, spreadsheets and more. It reads aloud, takes
dictation, checks spelling, keeps notes and version history, works with git
and GitHub, and has an optional AI suite and an extension system. Most of
these notes are about QUILL.

**Quill Radio** is an internet radio player in its own window, with its own
menu bar and tray icon. It has favorites, recording, scheduled recording and
a weather center. It shares its favorites and settings with the rest of the
family, and opens in seconds when you just want the radio on without loading
an editor. From QUILL it is one keystroke away through the QuillVille
switcher.

**Quill Weather** sits in the tray and watches the National Weather Service
for watches, warnings and advisories at the places you care about. It speaks
them the moment they are issued, whether or not anything else is running.

**Quill Inkwell** sits in the tray and expands your abbreviations in *every*
Windows program: your browser, your mail, a form, a spreadsheet. It uses the
same abbreviations QUILL expands in its own editor. Not a copy of them: the
same ones, in the same file.

All four are free and work from the keyboard. All four speak through the same
announcement service, so QUILL sounds like QUILL wherever you are.

### Platforms

Windows is the main platform, with full support for JAWS, NVDA and Narrator.
macOS is supported too, with announcements routed to VoiceOver, a Cmd-based
keymap, Preferences where Mac programs keep it, and notarized,
Developer-ID-signed builds. Linux and other Unix systems are not a target for
QUILL, and we make no promises about them.

### How you can install it

- **Windows installer.** The usual choice. It installs for you alone or for
  everyone on the machine, and creates Start Menu entries for QUILL, Quill
  Radio and Quill Weather. It also offers desktop icons, file associations and
  an **Add Quill to PATH** task, so that `quill somefile.txt` works from any
  terminal. Those three are checkboxes, all unchecked unless you check them.
- **Portable ZIP.** Unpack it anywhere, a USB stick included, and run it.
  Everything QUILL stores lives in a `data` folder beside the program, so
  nothing is written to the system drive and nothing is left behind.
- **Offline Edition.** A larger installer and portable bundle with every
  optional component inside it, described in its own section later. Choose it
  for a machine that cannot reach the internet, such as an air-gapped
  computer or a locked-down laptop.
- **macOS.** An application bundle, as a `.dmg` or `.pkg`.

The everyday download stays small because bigger optional pieces come only
when you ask for them: Pandoc, offline speech engines, neural voices, the
braille translation pack, OCR, portable copies of git and the GitHub CLI, and
more. They all live in **Help > Download Optional Components**, each with a
plain description, its size, a Test button and a Remove button. Nothing is
downloaded until you ask.

**QUILL can be your text editor.** Installing it tells Windows that QUILL can
open your text, Markdown, rich text, HTML, Word and EPUB files, and takes
nothing over. In **Settings > General**, under **Windows and your files**,
**Make QUILL My Text Editor...** explains what Windows lets an app do and opens
the page where you choose QUILL for `.txt` and anything else. **Open QUILL
instead of Notepad** goes further, for the programs that start Notepad by
name. It is off until you turn it on, asks first, and puts Notepad back when
you turn it off or uninstall QUILL. It works from a portable copy too.

### Staying up to date

**Help > Check for Updates...** looks for a newer QUILL, and by default QUILL
looks by itself each time it starts. It never installs anything without
asking. After an update, QUILL checks that the new version really opens, and
if it does not open within two minutes, it puts back the version you had.

**Help > Release Channel...** chooses which updates you are offered.
**Stable**, the one we recommend, is where every copy starts. **Beta** gets new
features a few weeks early, and **Dev** is the work in progress. Moving to
Beta or Dev saves a copy of your settings and keys first, shows a short
warning you have to agree to, and can move QUILL Lite, Quill Radio and QUILL
Cast in the same step if you tick them. Coming back to Stable is the same
window, and QUILL tells you plainly if it has to wait for Stable to catch up.
The same window is a button away in **Settings > Administration**, and its
**Update History** shows everything the updater has done.

Every version now has a **build number**, so a fix can ship without a new
version number. **Help > About Quill** says "1.0.0 (build 1)", and Check for
Updates offers a later build of the same version to everyone on an earlier
one.

### The first two minutes

The first time you start QUILL, a startup wizard asks one question: what kind
of writing do you do? Your answer picks a **feature profile**, which decides
how much of QUILL is switched on to begin with. The profiles are Just a Text
Editor, Writer, Markdown and Web Author, Accessibility Professional, Braille
Professional, AI-Powered Author, and Developer and Power User, plus Full QUILL
for everything at once. A plain-English preview tells you what each one turns
on before you choose.

You can change your mind at any time. **Alt+Shift+P** switches profiles.
**Manage Individual Features** turns any one feature on or off, whatever your
profile. And when something in these notes is not on your menus, **Help > Why
Don't I See a Feature?** tells you why. To skip the wizard, pick Full QUILL
and trim it later.

### Safe Mode

**Safe Mode** starts QUILL in a known-good state. Start QUILL with
`--safe-mode`, or set `QUILL_SAFE_MODE=1`, and it opens with extensions, AI,
network features, watch folders, background monitoring, indexing, themes and
session restore all switched off. It works the same in a portable copy and an
installed one.

Use it when something has gone wrong and you need to get to your documents,
or when you want a session that reaches nothing outside your machine. In
these notes, "off in Safe Mode" appears beside every feature that can touch a
network, and it means exactly that.

### Privacy

QUILL is a local program. It opens your files from your disk and saves them
back to your disk. Your documents are not uploaded anywhere as a matter of
course.

Every feature that reaches the internet is optional, says so, asks before you
use it the first time, and is off in Safe Mode. That includes the AI suite,
the book library, radio streams, weather alerts, GitHub, remote file sites,
update checks and cloud transcription.

QUILL ships no API keys and adds nothing to anyone's bill. If you use a paid
AI provider, it is your account and your key. The secrets you give QUILL
(provider keys, remote-site passwords, service tokens) go into one protected
store: the Windows Credential Manager, a DPAPI-encrypted file in portable
mode, or the macOS Keychain. A secret is never written to a settings file, a
log or a diagnostic bundle, and signing out of a service erases everything it
stored in one step.

Crash reports and diagnostic bundles never include your document text, and
tokens and keys are scrubbed out before they are written.

---

## The final reliability pass

The last stretch before this release was a reliability pass, shaped by what
people reported. It changed how saving, typing and dictating feel, so it
belongs here. The changelog has every technical detail. These are the parts
you will notice.

### A full disk can no longer close QUILL with your work unsaved

This was the serious one. On a disk with no space left, choosing **Save** on
the close prompt closed QUILL *without saving*. Four things now protect you:

- A backup can never stop a save. If QUILL cannot write one, it says "Could
  not write a backup; saving anyway" and saves.
- Backups are written all at once and always as UTF-8. An interrupted backup
  can never be the one you restore, and a BRF braille file's backup no longer
  fails on an accented character.
- The message tells you what to do: "The disk is full. QUILL could not save
  notes.md. Free some space and try again -- your text is still open and
  unsaved."
- A failed save does not close the window. The first close after one is
  cancelled with an explanation. A second close still goes ahead, so you can
  never be trapped.

Autosave now tells you, too, when a full disk pauses it. It says so once, and
goes quiet again as soon as a save works.

### Typing is faster, and your screen reader keeps up

People told us about "long pauses between text entry and reporting from
either NVDA and JAWS... sometimes the space is not intercepted, so words run
together". The cause was QUILL's own work on every keystroke: three or four
full copies of the document per character. On a 200 KB file that is a
megabyte of copying for each key you press.

Now QUILL reads the document once per keystroke. Only what must happen before
your next key happens straight away. Previews, spell-check hints, prediction
and the rest wait about 120 ms, until after the character has reached your
screen reader, and the periodic autosave runs in the background. A build check
keeps it that way. And **Save no longer announces its word count twice**
when NVDA is running.

### Dictation stops making things up

Silence, breathing and background noise no longer come back as invented
words. QUILL now listens to how sure the speech model is, instead of taking
its guesses.

### Keys, settings and menus you can trust

- Key combinations that quietly fought each other have been separated. When
  two commands claim one key, one of them never runs, and a check now stops
  that from coming back.
- Four settings that used to need a restart now take effect the moment you
  save them.
- Every enabled menu item shows a real key, used by nothing else in that menu
  bar. The key you see is the one that is actually bound, so if you change it,
  the menu follows you.
- Every Close button closes. That is now true in every window in the family.
- **More Preferences is back.** `Ctrl+,` opens Settings straight away, which
  had left Task Recipes and Working Modes, GLOW Accessibility and every
  Quillin's preferences (Smart Insert, BRF Tools, Journal Stamp, Document
  Guardian, Status Scribe) with no way in. **Tools > Customize and Support >
  More Preferences...** (the QUILL key, then `O`) lists them all.
- **The AI and Assistant page shows all its settings.** Voice question reply,
  the assistant's tone, Ask AI's default provider and model, the image
  description style and the rest were never drawn. They are there now, each
  with F1 help.
- **Find a setting finds settings on every page**, including pages you have
  not opened yet. Before, it only searched the page that was showing.
- **Quill Eraser's four settings are on the Spelling page.** The guide said
  they were in Settings, and they were on no page at all.
- **Two keys that did nothing now work.** The QUILL key followed by `C` copies
  your selection ready to paste into an email, and `Alt+F1` on something
  greyed out tells you why it is unavailable.
- **Announce Contrast Ratio always answers out loud.** It used to speak only
  when the startup announcements setting was on, which it is not unless you
  turn it on.

### Settings that now do what they say

Eighteen settings could be changed and saved, and nothing ever read them.
You would tick a box, hear nothing different, and reasonably assume it had
worked. Every one of them now does what its name says. Only one changes
anything before you touch it: Read Detailed Status in Braille Mode now tells
you your proofing progress, which it always promised and never did.

- **Keep an announcement history.** Turn it off and QUILL keeps no list of
  what it said, and clears the one it had. The Spoken Echo tells you it is
  off.
- **Interrupt speech for.** Choose whether warnings and errors cut across
  your screen reader (as they always have), only errors, or nothing at all.
- **Default export preset.** Export > Other Pandoc Format opens on your
  usual format, so Enter does the rest.
- **Markdown clipboard format.** Copy With Source in a Markdown document can
  add a formatted copy, HTML or Rich text, so pasting into Word or an email
  keeps the headings, bold and links. Plain text stays the default.
- **Listen for 'Hey QUILL'** is now the same switch as the Speech menu
  command, and **Keep listening across restarts** really does bring listening
  back when QUILL starts, and only then.
- **Watch Folders.** The default watch folder is watched for real: new files
  dropped into it open in QUILL. **Start watching automatically**, **Include
  subfolders** and **Process existing files on start** all apply to it. Your
  profiles keep their own choices.
- **File types offered to QUILL** decides which files get QUILL on their
  right-click menu, and a change takes effect when you press OK.
- **Python console execution timeout** stops a command that runs away, and
  tells you it did.
- **Spelling review context display mode** can show the whole paragraph
  around a misspelling in the F7 review, in QUILL and in QUILL Lite.
- **Six Braille Mode settings.** QUILL can say the new braille page, the new
  print page, or a line that is too long as you move. Read Detailed Status
  now includes your proofing progress and the continuation letter, and each
  can be left out. Calculate pages from geometry, and Use form feeds for page
  breaks, now decide how a braille file is split into pages.

### Smaller fixes you will feel

- **Updates offer the edition you are running.** Updating a full install used
  to offer the portable download. Three separate faults caused that, and all
  three are fixed.
- **Pages files open again.** `.pages` documents open with current versions
  of keynote-parser.
- **Your place follows you between machines.** QuillSync now carries reading
  and playback positions, so the paragraph you stopped at on one computer is
  where you start on the other.
- **Everything you started, in one list.** Continue Listening gathers
  podcasts, streamed recordings and local files into one list, newest first.
  Each row names where it came from, Resume appears only where it can work,
  and Forget is a button of its own.
- **The Media Player reads your notes back as you reach them.** A bookmark
  with a note speaks it at its moment. It is on by default: **Playback > Read
  My Notes Aloud as I Reach Them**. A plain bookmark stays silent, because a
  place to jump to has nothing to say.
- The Command Palette tells you which way every toggle is set, such as
  "(currently On)", fresh each time it opens.
- Sound Enhancements has a key in full QUILL (the QUILL Key followed by
  **1**), and it goes to the player you can actually hear.
- The Media Player answers to the same classic Winamp transport keys as the
  rest of the family.
- "Show in Explorer" selects the file instead of opening Documents.
- The two Italian Piper voices have preview clips, like the other 37.
- A brief network failure, such as a 503 or a timeout, is retried before
  anything is given up on. One busy moment can never be the reason a live
  subscription is offered for deletion.
- Persistent undo is limited by size as well as count, so a hundred snapshots
  of a large manuscript no longer cost 100 MB and a rewrite every few seconds.
- Find Chapters works for every episode. It used to say "cannot be
  identified" for all of them.
- Player Information counts your notes. It used to report zero.

---

## How QUILL Talks to You

Before the features themselves, here is the layer underneath all of them.
It is what makes the rest usable.

### One announcement service, four channels

Everything QUILL says reaches you through one service, and it speaks on four
channels at once: **speech**, **braille**, **sound** and the **status line**.

**Speech** goes to your screen reader through a bridge made for that reader,
so you hear it in your own voice at your own rate, not through a second
synthesizer competing with the first. JAWS and NVDA have long worked this way.
Narrator does now too: QUILL sends announcements as UI Automation
notifications, which Narrator understands, and it checks the marker Windows
keeps while Narrator runs, so it always knows Narrator is there. On macOS,
announcements go to VoiceOver. Whenever a screen reader is running, QUILL's
own built-in voice stays silent so it never talks over you.

**Braille** gets the same care. Status and information messages go to your
braille display through Prism, JAWS or NVDA, never cut short. A message that
repeats straight away is not sent twice. When several different messages
arrive at once, the first appears immediately and anything in the next moment
is replaced by the newest, so a burst of status does not push each line off
the display before you can read it. Errors always come through at once. If
your display fails, you still hear the message. You can turn braille messages
off in **Preferences > Accessibility**.

**Sound** never talks over your screen reader. QUILL has a full set of sounds,
called earcons: the Ink sound pack, a family of indentation tones, and room
for custom packs. Every sound has its own on and off switch in the **Sound
Events** dialog, and **Toggle Sound Notifications** silences them all.

The **status line** is for anything you might want to go back and read.

Two commands let you check all of this. **Repeat Last Announcement** says the
last thing again. **Announcement Self-Test** sends a test message on every
channel and tells you which ones reached you. "Is my braille display getting
QUILL's messages?" stops being a guess.

### A status bar you can use

QUILL's status bar has parts for the word count, the selection, file
information, spelling, autosave, background tasks, notifications, read-aloud,
the Copy Tray, the document's format, the current section, the page, the
screen reader QUILL detected, and Radio while it is playing.

You can act on every one of them. Arrow to it and press Enter, or open its
context menu for more. The spelling part opens spelling. The Format part opens
the format switcher. The Radio part plays and pauses.

### Verbosity: how much QUILL says

People want very different amounts of speech, and so does one person at
different moments. QUILL has four verbosity profiles (Beginner, Normal, Expert
and Quiet), plus **Quiet Mode** and **Meeting Mode** for when you need QUILL to
stop talking right now.

You can also change the wording. A token-and-filter system lets you write your
own phrasing for any announcement. The Preview Lab lets you hear a change
before you keep it. Announcement History shows what QUILL has said. **Undo
Verbosity Change** takes back a setting you regret. And when a lot happens at
once, QUILL collapses it instead of burying you in speech. Safe Mode puts
verbosity back to a sensible default, so a bad profile can never leave you
unable to hear QUILL.

**Spoken Echo** (**Alt+Shift+E**) shows the last twenty announcements in a list
you can arrow through and copy from, for the message you half heard while your
screen reader was busy.

### The keyboard is the interface

Every feature has a home on a menu and a name in the command list. There are
more than seven hundred named commands, and you can reach every one three
ways: from the menu bar, from the Command Palette, and from a key you assign.

The menu bar has twelve menus in a default installation: File, Edit, View,
Insert, Format, Navigate, Search, Tools, AI, Window, QuillVille and Help.
Nothing hides in a toolbar without a menu item.

The **Command Palette** (**Ctrl+Shift+P**) finds any command by name:

- Words match in any order, so `url open` and `open url` both find **Open From
  URL**.
- You can search by key: type `ctrl+o` to find Open.
- Everyday words work too: `settings` finds Preferences, `quit` finds Exit,
  and `theme` finds dark mode.
- As you arrow through the results, you hear each command's key with its
  name, so the palette teaches you the faster way while it does the job.
- When a command is unavailable, the row says why, instead of a bare
  "(unavailable)".

The **Keymap Editor** (**Ctrl+Alt+Shift+Space**) changes any key. It can tell you
what a key does. Its Record Keys mode lets you press a combination instead of
spelling it out. Its diagnostics find duplicate, orphaned or dead keys, and
**Heal** fixes them. A whole set of keys can be saved and shared as a
**keyboard pack** (`.kqp`), a checked JSON file you can give someone else. The
**Dynamic Keyboard Reference** is built from the keys you actually have and
your active profile, and exports as HTML.

Many QUILL commands start with a prefix key called the **QUILL Key**, so they
never collide with your screen reader's own keys. **Change QUILL Key** moves
that prefix for every one of those commands at once, and warns you about
conflicts and combinations Windows keeps for itself before it makes the
change.

#### Global hotkeys

**Global Hotkeys** (**Tools > Global Hotkeys**) work from any program, not just
QUILL. Only a short list of safe commands can be global:

- Radio play/pause, stop, mute, and volume up and down
- New Sticky Note and the Sticky Notes Browser
- Posting to Mastodon, which opens the compose window and never sends by
  itself
- Show/hide to the tray

Nothing that edits a document, deletes anything or works out of sight can be
a global hotkey, whatever a settings file says. Every press tells you what
happened, even with QUILL minimized. The show/hide keys start out as
**Ctrl+Alt+Shift+Q** for QUILL, **Ctrl+Alt+Shift+R** for Quill Radio and
**Ctrl+Alt+Shift+F12** for Quill Cast. Quill Weather, Quill Converter, Quill
Media Player and Quill Inkwell start with none, so they never take a key
another app needs; choose one in that app's **File > Show and Hide Key...**,
which will not let you pick a key the family already uses. Global hotkeys are
Windows only, because macOS has nothing like them. The same commands are on
the menus and in the palette everywhere.

The **Keymap Editor** moved from Ctrl+Alt+Shift+R to **Ctrl+Alt+Shift+Space**
before release. Ctrl+Alt+Shift+R shows and hides Quill Radio from anywhere, so
while Quill Radio was running, it never reached QUILL. QUILL Lite's Keyboard
Manager moved to the same key.

### Help where you are

**F1** gives help on the control you are on. **What Can I Do Here?**
(**Ctrl+Alt+Shift+F1**) gives ideas for the place you are in. **Context
Help** (the QUILL Key followed by **Shift+H**) speaks the keys that matter
most where your focus is. Every command has a plain description and its key,
so nothing in the palette is a bare code name. Three commands are there for
the moments other programs go quiet: **Why Don't I See a Feature?**, **Why Is
This Unavailable?** and the Feature Profile health check.

#### Activity, and Repeat Last Result

**Help > Activity...** (**Shift+F9**) lists everything QUILL reported in this
session, newest first, one sentence per row: whether it worked, what it was,
and when. Each row offers what you can do about it: **Retry**, **Open
Folder**, **Copy Details** and **Clear List**.

- When a settings file could not be saved, you hear it once, with the reason:
  the disk is full, the folder is read only, or Windows would not allow it.
  Its row has Retry to save again and Open Folder to show you the disk. When a
  later save works, you hear that too.
- Background work that finishes after you close the window that started it
  shows up here instead of being lost.

**Repeat Last Result** (**F9**) says the newest result that mattered again:
the last thing QUILL told you, not the last thing your screen reader read. It
also names what Activity offers for it. Nothing in the list leaves your
computer, and no document text is ever in it. The same two keys work in QUILL
Lite, Quill Radio and QUILL Cast.

---

## Writing and Editing

### The document surface

QUILL opens many documents at once, each in its own tab.

- **Ctrl+Tab** and **Ctrl+Shift+Tab** move between them.
- **Alt+1** through **Alt+0** jump straight to a numbered document.
- **Ctrl+Shift+F4** closes every document except the one you are in.
- The Window menu lists them all.

Recent files, Save, Save All and session restore work the way you expect.
**Alt+Shift+1** to **Alt+Shift+9** reopen the nine documents you opened most
recently, and **Recent Documents...** (**Alt+Shift+0**, also at the foot of
**File > Open Recent**) shows the whole list in one window. You can open a
document, pin the ones you keep coming back to, remove a row, open the
containing folder, clear everything that is not pinned, and choose how many
documents to remember. QUILL Lite has the same window on the same key.

**Notebooks** gather a folder of related files into a project, with entries,
headings, bookmarks, sticky notes, saved versions and optional writing goals.
**Workspace Snapshots** save and restore your whole working setup, open
documents and tabs included, so you can put a project down and pick it up
exactly where you left it.

QUILL remembers where you were. Your cursor position is saved with every
autosave and every workspace snapshot, and when you reopen a file, you are
back at your last position.

### Selection and movement

Selecting text does not need a mouse. Commands start, extend, complete and
reselect a selection, and grow or shrink it by word, sentence, line,
paragraph or block. Press **F8** to start selecting and you hear two rising
notes; finish, and you hear them falling. You always know when selection mode
is on.

You can move through a long document by headings, paragraphs, blocks, links,
lists, tables, bookmarks, code blocks and search results.

- The **Outline Navigator** (**Ctrl+Shift+O**) shows the document's headings
  as one tree.
- **Go to Anything** (**Ctrl+Alt+Shift+A**) is one search box for commands
  and headings. For links, lists, tables, block quotes, bookmarks and code
  blocks, use Quick Nav, below.
- Back and Forward walk through the places you have been.
- Match Bracket, Next and Previous Token, and structure and region movement
  cover the rest.

**QUILL Quick Nav** is a browse mode like the one your screen reader uses on
web pages. Press the QUILL Key twice to turn it on. Then single letters move
you:

- **H** headings, **P** paragraphs, **S** sentences
- **A** links, **L** lists, **I** list items, **T** tables
- **Q** block quotes, **B** bookmarks, **C** the table of contents
- Tab for blocks

You choose whether it wraps around, and whether it answers with speech, sound,
both or nothing.

At the very top of a document you hear a high tick, and at the very end a low
thud, so you know when you have hit the edge instead of guessing from the
silence.

### Bookmarks, four kinds

- **Named bookmarks.** As many as you like, kept with the document. **Set
  Bookmark**, **Go To Bookmark** and **List Bookmarks** (**Alt+Shift+G**).
  **F2** and **Shift+F2** move to the next and previous one.
- **Named marks and a mark stack**, for the habit of setting a mark, going
  somewhere else, and popping back.
- **Nine numbered bookmarks.** **Ctrl+Shift+1** through **Ctrl+Shift+9** set
  the bookmark for that slot, **Ctrl+Shift+B** uses the next free slot, and
  **Ctrl+Alt+B** clears them all. No dialog and nothing to type. They are kept
  with the document like named bookmarks, under names such as "Quick 3".
- **One temporary bookmark.** **Set Temporary Bookmark** (**Ctrl+Alt+J**)
  drops a single unnamed marker at the cursor, with no dialog, and **Go to
  Temporary Bookmark** (**Ctrl+Shift+J**) takes you back. Setting it again
  moves it. QUILL forgets it when you close: it is for "come right back here",
  not for keeping. Both are in the Navigate menu's Bookmarks submenu.

The kept kinds stay with their words. Add or delete text above a bookmark and
it moves with its sentence, instead of pointing at a line number that now
means something else.

### Structured authoring

Headings, lists, links, tables, code blocks, block quotes, horizontal rules,
footnotes and a table of contents all have insert commands. Every one is
**format-aware**: the same command writes Markdown in a Markdown document and
HTML in an HTML document. If QUILL does not know a document's format yet, it
asks once, remembers your answer for that document, and never asks again.

- **Ctrl+Alt+1** through **Ctrl+Alt+6** set a heading level.
- **Ctrl+Shift+L** turns a bulleted list on and off. The QUILL Key followed by
  **Shift+L** does the same for a numbered list.
- **Alt+Shift+Up** and **Alt+Shift+Down** move a whole heading section past
  the one next to it.
- The status bar says where you are, such as "Section: Heading 2 (3 of 11)".

The **Heading Organizer** (**Alt+Shift+O**) shows the whole heading tree for
promoting, demoting, reordering and renaming sections. It can check for
skipped levels and, if you like, more than one H1. **Style Headings** sets the
font, size and alignment for one heading level or for all of them.

Lists have two tools of their own:

- The **List Manager** (the QUILL Key followed by **L**) rearranges a list you
  already have, as a tree: move, promote, demote, add, edit and delete.
- The **Structured List Studio** (**Ctrl+Alt+Shift+L**) builds a new list.
  Choose bulleted, numbered, checklist or definition, nest as you go, move
  whole branches, and watch the source it writes.

In Markdown, typing does what you expect. Enter continues a list item, Enter
on an empty item ends the list, and Tab and Shift+Tab nest and un-nest.

**Update Outline Numbering** writes numbers into your headings as real text,
plain or legal style. You can remove them or run it again, for documents that
need real section numbers.

### Finding and changing text

Find and replace covers plain search, wildcards, regular expressions, search
history and a report of every match.

- **Multi Replace** makes up to four find-and-replace changes in one pass.
- **Count Occurrences** tells you how many times something appears.
- **Search in Files** (**Ctrl+Alt+Shift+F**) and **Replace Across Files**
  (**Ctrl+Shift+R**) work across a folder.

#### The Regular Expression Helper

Regular expressions are hard to read aloud, so QUILL helps. The **Regular
Expression Helper** now has a **category tree of more than 100 recipes**:
cleanup, words, lines, numbers, dates, contact and web, Markdown, HTML,
punctuation, writing checks, OCR scan cleanup, code names, and
capture-and-replace changes that come with replace patterns ready to use.

Its **plain-language explain engine** reads any pattern to you step by step
("One or more digits. Optionally: a period..."), whether you typed it or
picked it. If a pattern is broken, it tells you in words, at the exact
character where it breaks. The preview reads each match as a sentence with its
line and column, and shows the result of a replace recipe. **Use in Find All
Matches** sends the pattern straight to search with regular expressions
already on, without the clipboard.

#### QUILL's own Find dialog

QUILL also has its **own accessible Find and Replace dialog**, made for screen
reader users. Turn on **Settings > Use QUILL's own Find dialog** (the setting
`find_use_quill_dialog`), and **Ctrl+F** and **Ctrl+H** open it instead of the
Windows one.

- **Extended mode** finds characters that are hard to type: `\n`, `\t`,
  `\xNN`, named characters, and a choice of forty special characters.
- The **match count is spoken as you type**.
- **Peek navigation** (**Ctrl+Up** and **Ctrl+Down**) walks through the
  matches while you stay in the search box, and reads the sentence around
  each one.
- You hear when the search wraps around.
- The Direction choice says its name, as it should.

It **ships off by default**. The Windows dialog stays the default, and stays
available, until testing with JAWS and NVDA is finished.

#### Working with lines

- Sort ascending, descending, by length, by number or by date. Reverse,
  shuffle, remove duplicates, quote and unquote. **Unquote Lines** is
  **Alt+Shift+.** (Alt, Shift and the period), in QUILL and QUILL Lite.
- **Number Lines (Advanced)** lets you set the starting number, the step,
  digits or Roman numerals, leading zeros, what follows the number, and the
  alignment.
- **Sort Lines by Date** understands dates written many ways: ISO dates,
  slashes and dots, and English month names. For a date like 03/04, it uses
  the day-month order of your region. Lines without a date it can read stay
  together at the bottom, in their original order.
- **Line Statistics** gives the count, total, average, median, mode and
  standard deviation when each line holds a number, such as a column of
  figures in a text file.

The **Calculator** (**Tools > Calculator**) works out scientific and
everyday-language sums with a safe parser that can never run other code. It
also totals, averages and finds the median and more for selected data, a
table column or a row.

### Typing less

- **Snippets** turn a trigger word into a template with blanks to fill,
  choices, the date and time, and set places for your cursor to stop. Snippet
  packs group them, and starter packs install from an ordinary list where you
  check the ones you want.
- The **Snippet Gallery** adds templates from extensions, each asking its own
  questions, including ready-made math formulas.
- **Abbreviations** expand a short trigger into longer text: boilerplate,
  signatures, notes, code or markup. You can turn them all off. Each one has
  its own settings: a category, which characters expand it (a space or
  punctuation, a space only, punctuation only, or never), whether it adds a
  space after punctuation, what your screen reader says when it expands, and
  whether it plays a sound. Capitals follow what you type: `btw` expands as
  written, `Btw` gets a capital, and `BTW` comes out all in capitals.
- **Fill-in fields** make an abbreviation ask you something first. Write
  `${field:Name}`, or `${field:Reply by=Friday}` to suggest an answer, and a
  small form opens with a labelled box for each field. A field used twice is
  asked once and filled in both places, so a name in the greeting also lands
  in the sign-off. Cancel, and what you typed stays exactly as it was.
- **Quick Insert** (**Insert > Quick Insert...**) finds an abbreviation by
  name when you have forgotten its trigger, most used first, and reads the
  full text as you arrow through. It is also the only way to use an
  abbreviation set never to expand on its own, which is a safe home for a long
  or risky one.
- **New Abbreviation from Clipboard** makes an abbreviation from whatever you
  just copied. You only type the trigger.
- **Emmet-style expansion** brings the HTML and CSS shorthand (children,
  siblings, climb-up, grouping, multiplication) to QUILL, with accessible
  extras such as `!a11y`, `skiplink` and `form:a11y`.
- **Smart Insert** has built-in abbreviations that expand as you type: `qbug`,
  `qmeet`, `qlog` and `qtodo`. A fifth, `qbrf`, makes a BRF test document. It
  has to run code to do that, and QUILL never runs code in the middle of a
  word, so you reach it another way: **Insert > Insert BRF Test Document**, or
  type `=brftest()` on a line of its own.
- **Smart text triggers** go further. Type `=meeting()`, `=todo(5)` or
  `=rand(3,4)` and QUILL inserts what it makes. They must fit on one line, and
  QUILL asks before a large insertion.
- **Word Prediction** (**Ctrl+Period**) suggests endings from the words
  already in your document, and from HTML and Markdown tags.
- **Insert > Markdown Tag** (**Ctrl+Alt+I**) is on the Insert menu only while
  you are in a Markdown document, and comes back as soon as you are. Pressed
  anywhere else, its key tells you that Markdown tags are for Markdown
  documents, instead of doing nothing.

### The clipboard, expanded

The **Copy Tray** has twelve numbered slots. Copy to a slot, paste from a
slot, and search the slots.

Behind it, the **Clip Library** keeps a searchable history of up to two
hundred things you copied. You can mark a clip as a favorite or put it in a
tray slot. You can rename a clip so you recognise it later, fix it if you
copied slightly the wrong thing, or save it as an abbreviation, which then
works everywhere. Mark several clips and **Combine Marked...** joins them in
order, with the separator you choose: a space, comma, full stop, vertical bar,
new line or blank line.

QUILL keeps only what you copy or keep *inside QUILL*. It does not watch the
Windows clipboard and keeps no history of what you copy in other programs. If
you want that, use a clipboard manager alongside QUILL. They do different
jobs.

Every tray slot and every numbered bookmark plays its own note on a shared
musical scale: soft marimba taps for the Copy Tray, brighter chirps for
bookmarks. After a while, slot seven is a pitch you know, and "copied to slot
seven" hardly needs saying.

The **Clipboard Collector** works with other programs. Turn it on, then copy
from a browser, an email, a terminal or anything else, and each item is added
to your open document and saved as it goes. It glances at the clipboard about
once a second, only does anything when the contents change, and collects each
item once.

**Magic Paste** looks at what is on the clipboard, recognizes a URL, a
Markdown block or a base64 image, and offers you a choice of how to insert it.
Its key is the QUILL Key followed by **Shift+V**, and you can change it in the
Keymap Editor.

### Notes on your work

**Sticky Notes** are timestamped, searchable and exportable. **Inline anchored
notes** (**Alt+Shift+I**) attach to a place in the text, follow your edits,
come back when you reopen the document, and have their own next, previous,
hear and edit commands.

**List Inline Notes** (**Alt+Shift+Enter**) shows every note in the document at
once, with its line and the text it is about, and lets you go to, edit, delete,
remove, copy or export them. A note whose text was deleted is listed last, so
it is never lost and never stuck. **Delete Inline Note** (**Alt+Shift+Delete**)
asks first, and the note window now shows the start of the text it is on.

In Markdown and HTML, a note can be written **into the file** as a hidden
comment, so the colleague or the AI assistant you hand the file to can read it.
Undo takes it back like any edit, the file stays valid, and published pages
leave it out. `quill --notes list`, `check` and `clear` read and tidy those
notes from the command line, and in Quick Nav, **N** and **Shift+N** move from
note to note. QUILL Lite has every one of these on the same keys.

**Toggle Task Done** (**Ctrl+Alt+Enter**) ticks a `- [ ]` task, or every task
in a selection, and tells you how many in the list are done. The preview shows
task lists as real check boxes.

These ideas come from **PlanCake**, by Andre of Oire Software. Thank you,
Andre.

The **Sticky Notes Browser** is the quick way back to any note. Start typing
and the list filters as you go, across titles and text, newest first. Down
Arrow moves into the results. Tab reaches a read-only preview, so you can read
a whole note without opening it. Enter opens it for editing. Give it a global
hotkey and it opens from anywhere in Windows, with QUILL's window brought back
first so you can see it.

### Comparing documents

**Compare Mode** shows the differences between two documents, from the
keyboard.

- **Ctrl+Alt+Shift+Period** and **Ctrl+Alt+Shift+Comma** move to the next and
  previous difference.
- **Ctrl+Alt+Shift+D** says the current one again.
- Word-level detail and a switch for whether spaces count are there too.

Each difference is described in words, down to the character, and each kind
of change has its own sound. From the command line, `--diff` opens two files
straight into Compare Mode, and `--goto` opens a file at a position.

### Folding without losing anything

QUILL can fold heading sections and fenced code blocks, and it does it
differently from other editors.

- **Toggle Fold** (**Ctrl+Shift+[**) folds or unfolds the section around the
  cursor and tells you what happened: "Folded: 14 lines under 'Chapter Two'."
- **Alt+Shift+]** and **Alt+Shift+[** move to the next and previous section
  you can fold, and tell you its name, whether it is folded, and how many
  lines it has.
- **List Folds** (**Ctrl+Shift+]**) lists every section you can fold, with its
  state and size.

In most editors, folding hides lines and the arrow keys skip over them, so a
screen reader user cannot tell whether text was folded, deleted or just
passed by. QUILL never does that. **The document text is never changed, and
moving by character, word and line is never interrupted.** Arrow through a
folded section and every word is still there. Folding changes where the jump
commands take you. It never makes text you could reach silently out of reach.

### Macros and repetition

**Macros** record a series of commands and play it back. **Repeat Next
Command** sets a count, so the next command or macro runs that many times.
**Restore Deleted Text** brings back any of the last three blocks a structured
delete removed, for when "delete paragraph" deleted the wrong paragraph.

### Preview

The **In-App Preview** and **Side-by-Side Preview** show Markdown and HTML as
they will look, and you move between the editor and the preview from the
keyboard. On any block in the preview, the context menu (the Applications
key, **Shift+F10** or a right-click) offers **Go to this location in the
editor**, which puts your cursor on that block's line in the source. The key
opens a menu instead of doing something straight away, which is what screen
reader users expect from it. There is also a browser preview that shows the
document as a web page, with MathJax for equations.

### Insert Emoji

Insert Special Character is for when you know the code point you want. Emoji
are the opposite: you don't know the code point, you may not remember the
exact name, and a grid of small pictures tells you nothing. Nearly every emoji
picker is built on that grid, which makes them useless without sight. QUILL's
is built the other way round.

**Insert > Insert Emoji** (**Alt+Period**) opens on every standard emoji
Unicode defines today, 3,781 of them, as of Unicode's 16.0 emoji release, in
Unicode's own nine categories:

| Category | Emoji |
| --- | --- |
| People and Body | 2,261 |
| Flags | 270 |
| Objects | 264 |
| Symbols | 224 |
| Travel and Places | 218 |
| Smileys and Emotion | 169 |
| Animals and Nature | 159 |
| Food and Drink | 131 |
| Activities | 85 |

People and Body is so large because every skin-tone and gesture variant
Unicode defines as its own emoji is in it.

There are two ways in. **Search** filters as you type, best matches first: the
emoji itself if you paste one, an old typed form such as `:)` or `<3`, the
official Unicode name or one of its keywords, and finally the emoji's written
description, so a half-remembered word like "melting" or "puddle" still finds
it. **Category** is for browsing.

As you arrow through, a description pane shows the category and subgroup, the
official name, the keywords, any typed form, and a real sentence or two about
what the emoji looks like: colors, shape, expression, pose. That last part is
what makes the picker usable. Above Unicode's nine groups sit two more:
**Favorites**, which you choose, and **Recent**, which fills itself with the
last thirty emoji you inserted.

QUILL wrote every one of those descriptions for this feature, ahead of time,
from Unicode's own names, categories and keywords. Nothing was copied from
another picker's website. The whole collection ships inside QUILL, and the
picker makes no network connection at all, in Safe Mode or anywhere else.

### Equations

**Insert Equation** (**Ctrl+Alt+=**) takes a LaTeX or MathML equation as text
and puts it at your cursor with the right delimiters, in the line or as its
own block. Select an equation you already wrote and it opens again for
editing, without the delimiters. Shortcuts in the style of Word's Math
AutoCorrect (`\alpha`, `\sqrt`) work as you type. **Explore Equation
Structure** steps through the parts of an equation (numerator, exponent,
radicand) instead of reading it as one long string.

Typing math as text works well by ear: it is all keyboard, you can review it
character by character, and screen readers that speak math can read it. The
preview and HTML export show it through MathJax. Word export writes real Word
equations you can edit, and they turn back into text when you reopen the
file. With the optional MathCAT engine installed, "read this part aloud"
speaks math the way NVDA does.

Insert Equation writes `\(...\)` around an equation in the line and `$$...$$`
around a block, the same marks the Math Equations Quillin uses, so the preview
and Word export both pick it up. A beta wrote single dollar signs, which
neither of them recognised. To update an equation from a beta, select it and
insert it again.

**Math in the books you read, too.** When you open an **EPUB** with equations
in MathML or LaTeX, QUILL turns each one into the same plain-language reading
and puts it in the text as "Math Equation: ...", so you hear the formula as
part of its sentence instead of skipping it or hearing raw markup. It uses
MathCAT when it is installed and QUILL's own reader otherwise, and it never
fails to open a book because of an equation it cannot read.

This feature was contributed by @salorajan.

---

## Spelling, Language, and Words

### Checking spelling

Press **F7** for the full Spelling Review. It walks you through the document
one misspelling at a time, with Change, Change All, Ignore Once, Ignore All,
Add to Dictionary, and Undo Last. Not sure a correction is right? Press
**Ctrl+R** in the dialog and QUILL reads the whole sentence around the word,
so you can hear it in context without leaving the review.

To check just one word, press **Alt+Shift+F7** for **Spell Check Word**. It
looks only at the word under the cursor. If the word is fine, QUILL says so
and leaves you where you were. If not, a small list offers the suggestions,
Add to Dictionary, and Ignore. **Ctrl+F7** jumps to the next misspelling in
the document, and if your hands learned Word, **Alt+F7** does the same.

Some documents make the same mistake over and over, such as a rough OCR scan
or one word autocorrect keeps getting wrong. Two ranked views help there:

- **Alt+Shift+R** opens the misspelling list with the most frequent word
  first, and a count in each entry: "teh (Ln 12, Col 4, 8 occurrences)".
- In the F7 review, tick **Review most-frequent words first** and the review
  takes the same order. Choose Change All on the top word, and the ranking is
  worked out again, so the next-biggest group of errors comes to the top.

**Alt+Shift+L** keeps the plain list in document order, if you would rather
start at the beginning.

### Spell check as you type

With spell check as you type turned on, finishing a word QUILL does not know
plays a soft spelling sound from your sound pack, not a bare system beep. It
is a sound, not speech, so it never talks over your screen reader.

It also knows when to stay quiet. Words inside web addresses, email
addresses, Markdown inline code, and fenced code blocks do not set it off,
because almost everything there would count as a misspelling. The full F7
review still checks the whole document. Only the sound holds back.

### The thesaurus

**The thesaurus finds the word you are on.** Press **Shift+F7** and a
two-pane picker opens for the word under the cursor, the word you selected,
or one you type. A thesaurus lists the base form of a word, *run* rather
than *running*, *happy* rather than *happier*. So QUILL finds the base form
for you and tells you: "running (as run)", or "verb, from run: sprinting,
dashing, ...". When you choose a replacement, QUILL puts it back in the form
your sentence needs, with the original's capitals: *sprinting* for
*running*, *More glad* for *Happier*.

Focus starts in the Senses list, with the part of speech first, so **n**
jumps to the nouns and **v** to the verbs. Tab moves to the words for the
selected sense. Some are labelled *broader:* or *opposite:* when they are not
plain replacements. Press Enter to put the word in. The selection collapses
afterwards, so your next keystroke cannot wipe it out.

**Say Word Summary** (**Ctrl+Alt+Shift+[**) speaks the headword, its meanings
for each part of speech, the first few replacements and the opposites,
without opening anything.

**Two submenus on any word.** Press the Applications key on a word. The menu
has *Thesaurus for "running"*, with the best replacements right there, every
other sense as a submenu, Opposites, Say Word Summary, and More in
Thesaurus. It also has *Dictionary for "running"*, which starts with Look Up
and, when AI is on, carries on with the AI dictionary.

### Look Up Word

**Look Up Word** (**Alt+F10**) is the dictionary without AI. Offline, it uses
the thesaurus, and nothing leaves this computer.

Tick **Use online sources** in the window and the word is sent to three free
services that need no account. Only the word goes, never the sentence or the
document.

- The Free Dictionary, for definitions with examples.
- Datamuse, for more synonyms, opposites, rhymes and related words.
- A short Wikipedia summary, with a link back to the article.

The offline answer appears straight away. The online one replaces it when it
arrives, and QUILL says a sentence to tell you. QUILL remembers the choice.
Untick it and you are offline again.

### The AI dictionary

**The AI dictionary** is a Dictionary submenu on the AI menu, and the second
half of the submenu on a word. It answers thirteen questions about the word
*as it is used in this sentence*:

- Define in Context
- Synonyms That Fit
- Simpler, More Formal and More Vivid Word
- Opposites
- Is This the Right Word?
- Use It in a Sentence
- Where It Comes From
- How to Say It
- Rhymes
- the Word Explorer, which answers all of them at once
- Find the Word For, the reverse dictionary

Each one sends the word and its sentence. The answer is written to be
listened to, and each choice says why it fits. Press Enter on a choice to
replace the word as one undo step, as long as the word is still where it
was. The AI dictionary runs on your own OpenAI key or your ChatGPT
subscription, never the free allowance. QUILL Lite has the same thirteen
items on the same keys.

### Proofreading and language

**Proofread before publish** can run a spelling pass for you on save, on
save-as, or on a Mastodon post before it goes out.

**Set Document Language** fixes the language of an unsaved document or a
file with an unusual extension. That language decides what Ctrl+B produces,
which comment syntax is used, and how the heading, table and list tools
behave. Automatic detection comes in hint, prompt, or automatic modes.

You can change QUILL's own display language under **Tools > Writing and
Language**. Italian is the first display language after English, and it
covers menus, dialogs and spoken messages.

---

## Reading and Speech

### Reading aloud

**Read Aloud** speaks the document, a section, or a selection. Start, pause,
stop and voice choice are all commands you can put on keys. It leaves out
Markdown punctuation as it reads, so you hear the words and not a string of
hash marks and asterisks. Exported audio gets the same treatment. A cleanup
pass also tidies typography and reads phone numbers, email addresses and URLs
the way a person would say them.

You can read with:

- **Windows SAPI 5** voices, in every language you have installed.
- **DECtalk**, for everyone who has been reading with it for thirty years.
- **eSpeak-NG**, which speaks a very wide range of languages.
- **Piper**, a fast neural voice that runs on your computer, Italian
  included.
- **Kokoro**, a higher-quality neural voice that runs on your computer, in
  English, Spanish, French, Hindi, Italian, and Brazilian Portuguese.
- The **macOS system voice**, the same engine VoiceOver uses.
- **Cloud voices** with your own key: OpenAI, Google Gemini, and ElevenLabs.
  Each shows a cost estimate before anything is spent, and can export MP3.

You can preview every voice before you choose it. When you install a new
engine from the Download Optional Components list, you can make it the
default right there.

The **SSML Builder** puts together emphasis, pauses, say-as instructions,
phonemes and prosody, and plays the result on SAPI 5 and eSpeak-NG. **Manage
Pronunciations** keeps pronunciation dictionaries, one for everything and one
per project, with a live preview. Use it for the names and terms every
synthesizer gets wrong.

**Read the document aloud in your browser** is an experimental option. It
builds an accessible reader page that uses your browser's own voices,
including Edge's Online (Natural) voices. It reads section by section, and
Pause remembers your place.

### Turning documents into audio

**Audiobook and Batch Speech** turns a whole folder of documents into audio
in one run.

- It makes chaptered audio with real MP3 chapter markers.
- It applies ACX loudness normalization.
- It can take turns between several voices, round-robin.
- A dry run tells you what it would do before it does it.
- Cancel (or Escape) stops cleanly. The file being made finishes normally, so
  you never get a half-written audio file, and the run stops before the next
  one.
- The diagnostics log shows the same chunk-by-chunk progress as the dialog.
- WAV files go in an **Audio Output** subfolder beside the source document,
  so the folder itself stays tidy. A recursive export gives each subfolder
  its own.

**Export to Translated Speech Audio** translates your document and then reads
it aloud in the languages you choose. It uses any AI provider you have set
up, or a local LibreTranslate, and shows one combined cost estimate first.

If you close QUILL while one of these exports is running, QUILL asks first.
It also offers **Window > Send to System Tray** so the export can keep going
quietly. Everyday background work, such as search and replace, dictation and
downloads, does not trigger the question. Only jobs that are hard to redo do.

### Speech to text

QUILL turns speech into text on your own computer.

- **whisper.cpp** is the engine that comes with QUILL.
- **Faster Whisper** uses your graphics card for speed.
- **Vosk** is light and runs on the processor alone.
- **NVIDIA Nemotron** (Nemotron Speech Streaming EN) is the fourth choice.
  It is NVIDIA's 600M streaming model, run int8 through sherpa-onnx, the
  same runtime Visual Studio Code uses for its own dictation on your
  computer. It understands English only, and it runs on the processor with
  no graphics card and no PyTorch. It is an optional install: the
  `quill[nemotron]` extra, or its entry in **Help > Download Optional
  Components**. Its model downloads from QUILL's own release files with a
  pinned checksum, and it is off in Safe Mode.

**Manage Speech Models** looks at your real memory and graphics card, warns
you when a model is too big for your computer, and recommends the best fit.
Downloads use a checksum-pinned progress dialog you can cancel.

- **Live Dictation** (**Ctrl+F11**) writes as you talk: each phrase lands at
  the cursor when you pause, with a soft tone, and is read back to you.
  **Shift+F11** lists the last twenty phrases, and **My Words and Phrases...**
  (**Alt+Shift+F10**) teaches it your names and corrections. Nothing leaves
  your computer and no recording is kept.
- **You can dictate in Spanish.** In **Dictation Settings** (**Alt+Shift+F6**),
  set **Dictation language** to Spanish. Your words come out in Spanish,
  accents and all, using a multilingual model that comes with QUILL, so there
  is nothing to download. The wake and stop phrases become "Quill dicta" and
  "deja de dictar", and Spanish punctuation words such as "coma" and "punto"
  work when automatic punctuation is off. Commands stay in English for now.
  This is new, and we would love to hear how it goes.
- **Better accuracy, if you want it.** Live Dictation works the moment you
  install. **Better Accuracy: Speech Models...** (**Alt+B** in Dictation
  Settings) offers the same local models VS Code offers -- NVIDIA's Nemotron
  3.5 ASR Streaming (our suggestion), Parakeet Unified and Parakeet TDT, and
  Whisper small and base -- plus the rest of the Whisper family and Moonshine
  base. Each downloads only when you choose it, after a question naming its
  source, size, licence and folder; it runs on the processor with no graphics
  card, resumes if you cancel, is checked before use, and is shared with QUILL
  Lite (inside the portable folder in a portable copy). The user guide's
  "Better accuracy: optional speech models" has the published accuracy of
  each.
- **Hold Ctrl+F11 to talk.** Hold the keys, speak, and let go: your last
  phrase is written and Live Dictation turns off. A quick press still toggles,
  and stopping never cuts off the phrase you are finishing. **Dictation On** in
  **Tools > Speech > Live Dictation** is checked while it writes, and the status
  bar says what it is doing.
- **See your words while you speak.** With Nemotron or OpenAI, the words heard
  so far appear in the status bar and on a braille display as you talk; the
  final words go in at the pause. Nemotron's questions now end with a question
  mark.
- **Your words go where you started speaking**, even if you move the cursor
  or switch tabs while a phrase is being recognised.
- **"Correct that"** reads Windows speech recognition's other guesses, and
  "choose two" swaps one in.
- **Talk to the AI.** **Ctrl+F11** in the AI Conversation window dictates your
  message; it is sent when you pause, the reply is read aloud, and the
  microphone waits while it is read.
- **OpenAI dictation, with your own key**, off until you choose it and agree
  to a plain question about what is sent. You pick the model from OpenAI's own
  current list. The local engines stay the default.
- **My Dictation Instructions** tell Tidy Dictated Text (**Ctrl+F3**) how you
  like your writing, and **More Dictation Settings...** (**Alt+A** in Dictation
  Settings) holds every new choice. All of it is shared with QUILL Lite.
- **Locked Dictation** is the reliable way to speak into a document.
  **Ctrl+F9** starts and stops, **Ctrl+Shift+F9** pauses and resumes, and
  **Alt+F9** tells you where things stand. Everything you dictate arrives as
  one edit you can undo.
- The **dictation safety net** saves your audio to a recovery folder before
  it is transcribed. In the History and Review window you can insert, copy,
  or discard a recovered recording. A failed transcription never costs you a
  dictation session.
- **Transcribe Audio or Video** works from a file instead of a microphone.
  You get plain text, Markdown, or HTML, labelled by speaker when diarization
  is installed. It handles a wide range of formats, and fetches ffmpeg when
  it needs it.
- **Generate Captions** writes timestamped SRT or VTT subtitle files.
- A **Watch Folder** does it all for you. Drop audio or video in, and QUILL
  transcribes it to text, SRT, VTT, or Markdown without being asked again.
- **Cloud transcription** is there if you turn it on: OpenAI Whisper, Groq
  Whisper, or ElevenLabs Scribe, which also labels speakers. It is for the
  times local accuracy is not enough and you are happy to send the audio.

### Voice commands

**Voice Command (Offline)** lets you run QUILL hands-free with a chosen set
of safe commands, recognized entirely on your computer. **Voice Conversation
Mode** lets you follow one command with another, and the **"Hey QUILL"** wake
word keeps it listening when you want it to. Every voice command also has an
ordinary key, so voice is a quicker path and never the only one.

### Teaching dictation your words

Dictation should not fight the words you use. QUILL reads a small plain file
called **`dictation.md`** in your data folder. It has three sections, all
optional:

- **Vocabulary** lists the names, jargon and acronyms you use, so dictation
  writes "wxPython" and "GitHub" instead of guessing.
- **Replacements** are your own fixes from what you say to what gets
  written, one per line. "New line" can insert a real line break, and "get
  hub" can become GitHub.
- **Commands** add your own spoken phrases for existing actions. They follow
  the same list of safe commands as the rest of voice.

It works everywhere QUILL transcribes dictation, and it does nothing at all
until you write one.

### Performance

Speech models are big. One setting unloads a model after it has sat idle for
the number of minutes you choose. A **low-resource mode** keeps QUILL usable
on modest hardware, and it turns itself on when a computer has very little
memory.

---

## Braille

QUILL treats braille as a document format and a way of reading in its own
right, not just a copy of print.

Turn it on with the **Braille Professional** profile in the startup wizard,
with **Help > Enable Braille Mode**, or from Manage Individual Features.

### Braille files, byte for byte

QUILL opens and saves `.brf`, `.brl`, `.pef` and `.ueb` files **keeping every
byte**. Form feeds, line endings and layout come back out exactly as they
went in. Open a file, save it, and you get an identical file.

The braille status cell tells a transcriber what they need to know, in one
place: `BRF Pg 12/87 | Ln 14/25 | Cell 31/40 | Print 7`. One detailed-status
command speaks all of it at once. When you open a braille file again, QUILL
puts you back exactly where you were and tells you the page, line and cell.

### The braille display starts in cell 1

Text in QUILL starts in **braille cell 1**, not cell 2. That fixes the old
offset that RichEdit controls share with Microsoft Word. When text is
selected, your display shows **dots 7-8**, so you can feel the selection.

Two checkboxes under **Preferences > Braille** control this. Both are on out
of the box:

- **Fix braille cell alignment and selection dots (recommended)** turns on
  the system-edit emulation that makes this work.
- **Hide editor border (required for braille cell alignment)**. The visible
  editor border pushes braille output away from cell 1, so the border has to
  go for the fix to work. If you uncheck it, QUILL warns you that braille
  cell alignment will break.

Both settings are for Windows only. After changing either one, restart QUILL
so the change applies everywhere.

**Report Editor Surface** is one command that tells you everything a braille
problem report needs: which editor surface is active, its window class,
whether the braille fix is on, whether the border is hidden, and whether
braille output is live and through which backend. Nothing from your document
is included. If braille ever looks wrong, run it first and paste what it
says into your message. "Braille starts in cell 2" plus that one sentence
gives us something we can look into straight away.

### Translation, without being quizzed

To back-translate a braille file in most programs, you have to know which
code it uses already. Pick the wrong one and you get nonsense with no
explanation.

**Back-Translate to Text (Auto-Detect Code)** takes that job off you. QUILL
takes a sample of the document or your selection, back-translates it through
every English braille code it knows, and checks which result reads most like
real English. Then it tells you: "Detected UEB Grade 2 (contracted)." It
tries UEB Grade 2, UEB Grade 1, Standard American Grade 2 (EBAE, legacy),
Standard American Grade 1 (EBAE, legacy), and 8-dot computer braille.

**Convert BRF File to Document** takes you from a braille file to something
you can read, edit and share, in one command. Pick any `.brf` or `.brl`.
QUILL finds the code, back-translates the whole file, and opens the result
as a clearly labelled draft. Save As then turns it into Markdown, HTML, Word,
or plain text. Braille files also work in the general converter: **File >
Convert File** lists `.brf` and `.brl` alongside every other document type.

Forward translation uses the optional **QUILL Braille Pack**. Its Translation
menu offers UEB Grade 1 and Grade 2, Standard American English (Legacy), and
a More Languages section that fills itself in with dozens of languages.
Translation works from every kind of install, even a source checkout,
because it can use the pack's own engine. Large files translate correctly
whatever their size.

### Proofreading braille

- **Print-page and running-head detection** finds print page numbers and
  running heads from BRF separators and margin numbers. It tells you how sure
  it is instead of just asserting.
- **Print-page navigation**: Go to Print Page, Next and Previous Print Page
  Change, Announce Running Head, and Include or Omit Running Head in the
  status readout.
- **Proofreading tracking**: mark pages as proofed or needing review, add
  notes, hear a spoken progress summary, jump to the next unfinished page,
  and export a proofing report.
- **Layout validation** flags lines and pages that are too long, missing page
  breaks, mixed line endings, stray non-braille characters, gaps in the
  numbering, and running heads that do not match. You can jump to the next or
  previous warning.
- **Read Layout Metrics**, **Go to Longest Line or Page**, and **Remove
  Trailing Spaces** find and fix lines and pages that are too wide.
- **Page Tools** insert and remove page breaks, recalculate the page map, and
  even out line endings.

---

## Documents and Formats

### What QUILL can open

QUILL opens plain text, Markdown, CommonMark, GitHub-flavored Markdown, HTML,
CSV and TSV, Word (`.docx`), RTF, OpenDocument, EPUB, PowerPoint,
spreadsheets, PDF, LaTeX, JSON, XML, TOML, YAML, Jupyter notebooks, SQLite
databases, text from Apple Pages, braille formats, and images through OCR.
Install Pandoc when you need it and the list grows, for opening and for
saving. Whenever a file is hard to read, a **Document Intake Report** tells
you honestly how well it went.

The PDF and spreadsheet readers come with every install, so a new copy of
QUILL opens a PDF or an `.xlsx` straight away. Word files open with headings
as headings, lists as lists, and tables as tables, in document order, not as
one flat line per paragraph.

A few reading improvements make the difference between a document you can
use and one you cannot:

- **PDF text repair on open** takes out hyphens split across lines, joins
  paragraphs back up, closes up spaced-out titles, and repairs ligatures.
- **Password-protected PDFs** just open. QUILL asks for the password, reads
  the file, and never stores, logs or writes the password anywhere. A wrong
  password says so and lets you try again.
- **A PDF's own bookmarks** (the outline Adobe Reader shows in its bookmarks
  pane) come into QUILL's Bookmarks Manager the first time you open the file.
  Anything you rename or delete afterwards stays that way.
- **EPUB heading navigation** shows the headings inside each chapter, so
  single-key heading navigation walks them. When a chapter has no headings,
  QUILL works them out from its structure.
- **PowerPoint import** turns slide titles into headings and bullet levels
  into nested lists, and brings tables and speaker notes along.

Your documents open as your documents. QUILL adds no banner or header to your
text. What it knows about how a file was read is in the intake report and in
what it says when the file opens.

### However a document arrives

A document can reach you as a file in File Explorer, a path in a chat, or a
link in an email. **File > Open from Clipboard** (**Ctrl+Alt+Shift+Enter**)
opens whichever of those you copied, and says so plainly when there is nothing
to open. **File > Open from URL...** asks before downloading anything, naming
the website and the size, and shows the download's progress with a Cancel
button; a link to a GitHub page opens the file itself. Files dragged onto the
window open too. These ideas come from **PlanCake**, by Andre of Oire Software.

### Every byte, and every change, kept

- **An older file keeps every byte.** A file that is not UTF-8 is read without
  replacing a single character, and saved back exactly as it was. QUILL tells
  you once, as it opens, when a file is not UTF-8.
- **Reopen with Encoding...**, in **File > File Format...** (**Ctrl+Alt+E**),
  reads a file again in the encoding you choose when its letters came out
  wrong. It then saves in that encoding, or in UTF-8 if you choose.
- **Save never writes over a change it has not seen.** If another program
  changed your file since you opened it or last saved it, even a moment ago,
  Save asks first: Save As, Reload from Disk, Overwrite or Cancel.

### Rich editing

QUILL edits clean plain text, and keeps the formatting beside it as hidden
codes. That is why search, spell check, AI commands, read aloud, bookmarks,
inline notes and braille all work the same however formatted a document is.

Open an `.rtf` file and the formatting is really there. Bold is bold.
Headings have real sizes. **Ctrl+B** applies real rich-text bold. **Describe
Formatting at Cursor** tells you what is under the cursor: "Arial, 14 point,
bold, centered."

The rule is simple: **QUILL speaks the language of the document you are
editing**. In Markdown, Ctrl+B wraps the selection in `**`. In HTML, it
produces `<strong>`. In RTF or Word, it applies real formatting. One command
does the right thing for whatever format you are in.

A `.docx` file opens for real rich editing and saves back as a real Word
document. QUILL is honest about the limits:

- A plain Word file with nothing QUILL cannot carry opens straight in rich
  mode.
- If a Word file has features QUILL cannot keep, it names them and asks what
  you want to do. You can open it for reading and plain editing (the safe
  choice, and the default), edit it as rich text knowing exactly what will
  not survive a save, or edit a copy and leave the original alone.
- The first rich save over a file like that makes a timestamped backup
  beside it first.

QUILL never quietly rewrites a complex Word file and hopes everything
survived.

Plain text stays plain. The first time you use a formatting command in a
`.txt` file, QUILL asks once whether to treat it as Markdown, convert it to
rich text, or keep it plain. It remembers your answer.

On macOS, rich mode works the first time you open QUILL, with nothing to
install. If rich text ever cannot load on a computer, the document opens as
editable text, and the status area tells you why.

**Illuminations** are for files that have to stay plain `.txt`. A
`.txt.illumination` file sits beside yours and stores the formatting (bold,
italic, font, color, alignment). Open the file again and the formatting comes
back exactly. Every other program still sees a plain text file.

### The Document Format switcher

**Format > Document Format** moves the document you are in between plain
text, Markdown, HTML, Rich Text, and Word, without opening another program.
It is also in the Command Palette and on the **Format** cell of the status
bar.

It is a real conversion every time, in every direction. Move a Markdown draft
into rich text and `# headings` become real headings. Switch to HTML and you
get real HTML, `<h1>` and `<strong>`, and switching back reads it in again.
Moving a rich document into Markdown first warns you by name about anything
that will not survive.

Your formatting goes with you: headings, bold, italic, underline,
strikethrough, superscript and subscript, font and size, colour and
highlight, bullet and numbered lists, links, code, block quotes, alignment,
line spacing, indents, spacing, named styles, page breaks, tables, images and
rules. Switch out and back as often as you like, and you end up with the
document you started with.

Plain text is the one case with two right answers, so QUILL asks. Plain text
cannot hold formatting, so the `#` and `**` in your document can either
**come off**, leaving only the words, or **stay as ordinary characters**. A
.txt file can hold them perfectly well, and plenty of people keep their notes
that way. Escape leaves the document as it was. Ordinary prose converts
without asking, because there is nothing to ask about.

Rich Text files use real Word styles. Headings use Word's own heading styles,
and Quote, Title, Subtitle and Caption use the names Word knows them by, so
they show up in Word's style box and style gallery as the real thing.

Changing format never quietly overwrites the old file. Your next save
suggests a name with the right extension, so `notes.md` becomes `notes.rtf`,
and the file on disk always says what is inside it.

### Reveal Codes

QUILL normally hides formatting codes so the text stays clean. **Reveal
Codes** (**Alt+F3**, or **View > Reveal Codes**) shows every one of them and
lets you hear them, whenever you want. If you miss it from WordPerfect, it is
back, built for screen readers.

The default **Flowed** view reads like your document, with the codes shown
in line: `[Bold On]Hello[Bold Off]`. You move through it the way you do in
the editor:

- Left and Right go one character at a time through text, but step over a
  whole code in one press. Cross `[Bold On]` and you hear "bold on", not a
  spelled-out bracket.
- Ctrl+Left and Ctrl+Right move by word.
- Up and Down move by line and read it.
- Home, End, Ctrl+Home and Ctrl+End take you to the ends.

QUILL names the pane once when you go in. After that you hear only the
character, word, line or code you land on, the same in JAWS and NVDA. If you
want QUILL to speak each code as well, turn on **Reveal Codes: Speak Codes
Aloud**.

To change the text between a pair of codes, press **F2** on it. You can only
edit that stretch of text. Enter puts the change back in the document,
Escape cancels, and the codes around it stay as they were. A stretch with a
tab or a code inside it is edited as one piece.

Reveal Codes and the editor always keep your place together, whether you use
arrows, word jumps, Home and End, Page Up and Down, a mouse click, or Find.
There is also a **Structured** view, a list with one labelled item per code,
for scanning. QUILL remembers your view and how much it says between
sessions.

To ask about one spot without opening the pane, use **Describe Formatting at
Cursor**, or **Describe Character at Cursor**. That one gives the Unicode
name, code point and category, and tells you about invisible characters.

### Converting between formats

**File > Convert File** converts to any format Pandoc supports. Choose
Convert File or Convert and Open. It remembers your last folder and format.
The **Pandoc Conversion Wizard** does the same thing step by step. The **Batch
Conversion wizard** converts a whole folder at once in four pages (intro and
tool check, folder and options, format and profile, review and start), with
a progress row for each file as it goes.

Seven conversion profiles cover the usual destinations: Clean Word Document,
Accessible HTML Page, EPUB Book, GitHub README, Print PDF, Instructor
Handout, and Plain Text for Screen Readers.

**File > Export > HTML...** (**Ctrl+Alt+Shift+End**) makes one web page you can
share: styles inside, no scripts, the document's language set, task lists as
check boxes and strikethrough kept. It is a copy; the document you are editing
stays as it is. QUILL Lite has the same command on the same key.

The main formats, for opening and saving, are Markdown, CommonMark,
GitHub-flavored Markdown, HTML, DOCX, ODT, RTF, plain text, CSV and TSV,
EPUB, and LaTeX. QUILL can also save PDF.

The User Guide has a section called "What carries over between formats".
In short:

- Everyday formatting (headings, emphasis, links, lists and tables) moves
  between Markdown, HTML and Word.
- Numbered lists keep their starting number.
- A link stays a real Word hyperlink after a trip through Word.
- A table saved to Word becomes a real, editable Word table, with a header
  row that repeats and that your screen reader reads as column headers.

A few things depend on the format. A table saved to RTF is written as
readable pipe text, not a native RTF table. Images embedded in Word are not
pulled into the text. Plain text never carries formatting.

**DAISY 2.02 text-only talking book export** (**File > Export > DAISY Talking
Book**) makes a talking book you can move through by heading, from any
document.

### Optical character recognition

**Import/Convert Document (OCR)** sends Word, PowerPoint, Excel, HTML, EPUB,
PDF and image files through a free converter on your computer first. For
scanned or image-only PDFs it then uses OCR on your computer (Tesseract), and
tells you how confident it is on each page. **Review Last OCR Result** gives
you a checklist of the lines it was unsure of, with a jump to each page, and
**Delete OCR Temporary Files** cleans up afterwards. You can also run OCR on
an image file, on the clipboard, or on part of the screen.

When OCR on your computer really cannot save a document, you can send it to
a cloud service with your own key. QUILL asks first, and it never happens by
itself.

### Headers, footers, and printing

The **Header and Footer Builder** offers ready-made presets or your own mix
of title, file name, date and page number, a different first page, and
numbers or Roman numerals. They are part of the saved document, not added at
print time. Save as `.docx` and the header is a real Word header, with a
page-number field Word keeps up to date. Save as `.rtf` and QUILL writes the
RTF equivalent. A custom starting page number and a different first page
both carry through. A blank header changes nothing, and a header can never
stop a save from working.

**Print Studio** (**File > Print Studio**) is a print preview you can hear
and read, instead of a picture of a page. It can print all, odd or even
pages, print in reverse order, and skip the first page.

A **page indicator** on the status bar gives exact page numbers for PDFs and
an estimated page count for text, Markdown and Word. You can set how many
words make a page.

### Text encoding

Old text files with odd characters are a real, everyday problem, and QUILL
has the tools for it:

- **Show Non-ASCII Characters** lists every one, says whether it can become
  Latin-1 or Windows-1252, and jumps to it in the text.
- **Convert Non-ASCII to HTML Entities** and **Decode HTML Entities**.
- **Re-encode As** UTF-8, UTF-8 with BOM, Latin-1, Windows-1252, or ASCII.
- **Analyze and Save Using Minimum Required Encoding**.
- **Remove Email Quote Markers**, **Strip Low or High ASCII Characters**,
  **Convert to Hex Dump**, OEM (DOS) to ANSI conversion both ways, and
  converting or removing line-drawing characters.
- RTF files say which code page they use, and QUILL reads it, so Cyrillic
  and other non-Western RTF comes out right instead of as noise.
- JSON, XML, TOML, YAML and notebook files that start with a byte order mark
  open normally and keep their line endings.

### Version history

**File > Restore Previous Version** keeps a plain-language history of each
document. Restore takes you back, and saves a copy of what you have now
first, so you can undo the restore. Open as Copy leaves the current file
alone. Identical versions are only kept once, and older ones are thinned out
over time so the history does not grow forever. In a notebook, **Manage
Versions** does the same for named versions, and tells you plainly when
there are none yet.

The **extracted-text overwrite guard** protects your originals. If you press
**Ctrl+S** on text that came from a PDF, EPUB, PowerPoint or spreadsheet,
QUILL opens Save As instead of overwriting the original file.

### Citations

QUILL formats citations in MLA 9, Chicago 17 and APA 7 from a labelled form.
You get an in-text citation, a bibliography entry, or both. For Markdown, you
choose footnotes or a bibliography.

### Remote files

QUILL opens and saves files over **FTP**, **SFTP**, **WebDAV**, **S3**,
**HTTPS** and **GitHub**. The Site Manager keeps your saved sites, and SSH
Quick Connect handles a one-off. For SSH, QUILL turns away a server key it
does not recognise. To have it accept a new key the first time and remember
it, turn on the trust-on-first-use setting yourself. It is a setting, not a
prompt you might click through.

### Publishing, read-only in 1.0

With the **Full Quill** profile, the File menu has a **Publish** submenu with
three items: **Publishing Connections**, **Verify Current Publishing
Connection**, and **Browse Publishing Content**. With them you can save a
WordPress site account, check that it still signs in, browse the site's posts
and pages, and open one in QUILL as an ordinary document to read or edit on
your computer.

That is all publishing does in 1.0. Sending content back to a site (making a
draft, publishing, updating a post, scheduling one) is a separate feature.
It is switched off in this release, and Settings cannot turn it on. It is
written and being reviewed, and it will come when it is ready. Site
passwords are kept in the Windows credential vault, not in a settings file,
and everything the read-only side sends goes through QUILL's checked network
layer. Other profiles leave the Publish submenu off the File menu. To add it,
go to Profiles and Features and turn on Publishing (Read-Only).

---

## The AI Suite

QUILL's AI is optional, off until you set it up, and quiet until you ask.
If you never set it up, nothing here bothers you and no menu nags you. If you
do, it is yours: your provider, your account, your key, or a model running on
your own computer with nothing leaving it. QUILL comes with no keys and takes
no cut.

Everything is on the **AI** menu at the top level, and all of it is turned
off in Safe Mode.

### Setting it up

The **AI Setup Wizard** asks one question at a time, in a Basic or an
Advanced mode. It ends with Test Connection, which either works or tells you
exactly why not. It supports Ollama (local or cloud), OpenAI, Claude, Google
Gemini, OpenRouter, and any custom OpenAI-compatible endpoint.

There is a free way in, and the wizard shows it up front. Run **Ollama** on
your computer and everything stays there, at no cost. Or choose OpenRouter:
the wizard picks a free model for you and marks every free model "Free" in
the list. Each provider that needs a key has a **Get API key** button that
takes you to the right page. If you choose Ollama, QUILL checks that a server
really answers before it counts it as set up, and the API key field is
dimmed for providers that do not need one.

Ollama does not have to be on this computer. Type an **Ollama server
address** on the Connect step, and the check, the model list and the finish
step all use it, so a server elsewhere on your network works. You never need
a command window to get a model, either. The Model step shows which
recommended models you already have and puts a **Pull model** button on the
rest, with live download progress.

AI on your own computer is a full option in its own right: Apple Foundation
Models on macOS, and llama.cpp with GGUF models on Windows.

The **AI Hub** holds all the AI settings, on eight tabs:

- **Provider** and **On-Device**: your connection settings.
- **Engines**: sign in to and set up the agent engines described under
  Agents below.
- **Audio Services**: transcription and speech.
- **Services**: document conversion and OCR. It says plainly that the free
  converter and the OCR engine on your computer always go first, and that
  the one paid cloud service uses your own key and asks before every upload.
- **Instructions**: your standing writing instructions.
- **Sessions**: your saved AI sessions.
- **Advanced**: consent and diagnostic settings.

The Hub finds a running Ollama server by itself and shows what each model
can really do (vision, tools), instead of guessing from its name.

### Ask Quill

**Ask Quill** is where you talk with the AI: one conversation that knows
which document you are in. It can answer questions and suggest changes, but
it can never make one.

Every AI feature in QUILL works the same way: **the AI proposes, you
dispose.** Every edit an AI suggests stops at a review dialog. Nothing
touches your document until you agree. When you do, all the changes land as
one undo step.

The review is made to be judged by ear:

- Changes are announced as what they are: "Changed 'quick' to 'rapid' at
  line 3."
- Edits next to each other are joined into one phrase, not read as pieces.
- The details pane shows the sentence before and after each change, so you
  get the same context a sighted reviewer gets from a highlight. The whole
  old and new lines are below it.
- A real rewrite with lots of scattered edits is shown as whole lines,
  because hearing the lines beats forty spoken word pairs.
- Changes that are only spacing are never announced as word edits.

### Asking out loud, and choosing how you are answered

You can ask Ask Quill a question by voice. **Ctrl+F9** starts recording and
Ctrl+F9 again stops it. QUILL turns what you said into text **on your own
computer** before sending it. Your recording never leaves the computer.

Choose how the answer comes back in **AI > Voice Reply Settings...**. The
choice applies to every reply:

- **Announce a short summary.** Short, spoken by your screen reader, offline
  and free. This is the default, so nothing changes unless you want it to.
- **Show as text only.** Nothing is spoken. Read the answer in the
  transcript.
- **Read aloud in QUILL's own voice.** The whole reply, in the offline voice
  you use for Read Aloud: Kokoro, Piper, eSpeak, DECtalk or SAPI. Offline and
  free.
- **Read aloud in an AI voice.** The whole reply, in a voice from **OpenAI**
  (11 voices) or **Google Gemini** (30).

When a reply is read aloud, you hear **all** of it. The length limit is for
keeping an *announcement* short, so it only applies to announcements. It
starts at 140 characters, and you can change it. Set it to 0 to have whole
replies announced too.

That length applies to **everything** Ask Quill announces: answers, error
messages, and the summary of an edit it wants to make. Errors and edit
suggestions are always announcements, whichever reply mode you pick, because
few people want a long error read out in full. They still keep to the length
you set.

When you choose an AI voice, you pick the provider, model and voice. The
voice list always matches the provider, so you cannot end up with an OpenAI
provider and a Gemini voice. **Preview this voice** reads a sample so you can
hear a voice before choosing it.

The AI voices are the only choice here that costs money and sends your
words away. The reply text goes to OpenAI or Google to be spoken, and you pay
per character. The dialog tells you so and estimates what a typical reply
costs. QUILL never picks an AI voice for you. If one cannot be used, for
example because there is no API key for that provider, QUILL reads the reply
in an offline voice and tells you why. You never lose an answer because a
voice was missing.

### Writing help

- **Rewrite**, **Summarize**, **Expand**, **Continue**, and **Fix Grammar**
  work with or without a selection. With none, they use the paragraph or the
  whole document.
- **Check Grammar with AI** and **AI Spell Check** give you a list of issues,
  each with the original wording, the suggested fix, and why. With no AI set
  up, they use the ordinary spell checker instead of failing.
- The **AI Thesaurus** gives synonyms with notes on tone and how formal they
  are, using the sentence around your cursor. It is on the AI menu and in the
  Command Palette, and has no key unless you give it one in the Keymap
  Editor.
- **Generate Table of Contents** builds one from the document's headings.
- **AI Translate Document or Selection** offers the languages your provider
  supports, or a local LibreTranslate that keeps the whole job on your
  computer.
- The **Prompt Library** holds named tools you run with one click: Generate
  FAQs, Draft a Speech, Summary Email, Social Media Post, Step-by-Step
  Instructions, Paraphrase, and the summarize, rewrite, tone and expand
  presets. Each works on your selection or the whole document, and you can
  edit any of them or turn it off.
- **Custom Instructions** replace the built-in instructions for any built-in
  task, so you tell the assistant once how you want it to behave.
- **Train Writing Style** teaches the assistant how you write.
- On the **on-device model**, the free offline choice, Rewrite, Summarize,
  Expand, Continue and Shorten give cleaner results. Small local models have
  habits you can predict, so QUILL shows the model a few examples of what not
  to do. It then checks the answer for hedging ("it seems", "arguably"),
  opinion words ("clearly", "obviously"), and filler openings ("In today's
  world", "It is important to note"), and tries once more without them. Fix
  Grammar and Improve Reading Order are left alone, so a word really in your
  text is never changed. Cloud providers answer exactly as before.
- On the on-device model, **Summarize now works in two passes**. The first
  pulls the plain facts out of your text. The second writes the summary from
  those facts, without seeing the original, which cuts down a lot on what
  small models make up. Cloud providers do not need this and use one pass.
- **Suggest Document Metadata** suggests a title, a summary, topic tags and a
  category, and lets you decide each one. You hear the field, what it says
  now, and what the AI suggests, then choose Accept, Accept and Next, Skip,
  or just copy the value. If a field already has something in it, QUILL asks
  before replacing it, and the safe answer is the default. Nothing is written
  until you choose Apply Accepted.

### Reading help

- **Document Q&A** is a back-and-forth conversation about the open
  document, which you can move through by heading. A document too big to send
  whole is trimmed from the middle, and QUILL tells you the size it is
  working from, so you know it is not answering from everything.
- **Improve Reading Order** fixes a document whose text comes out in the
  wrong order: a two-column PDF that reads as one jumbled stream, a page with
  sidebars, lines out of sequence. It joins the columns into one flow, mends
  lines broken mid-sentence, and works out headings, lists and tables. It
  keeps your exact words, and never summarizes or makes anything up.
  - Before anything is sent, QUILL tells you the provider, its address, and
    about how much text is going.
  - The result opens as a new, unsaved document. Your original is not
    touched.
  - It turns away documents over a page limit you set, so you cannot send a
    huge or costly one by accident.
  - With no cloud provider set up, it uses the on-device model that comes
    with QUILL, entirely on your computer.
- **Describe Image with AI** comes with twelve tested styles of description
  prompt, all editable, a "try a different prompt" action, and a place to
  keep your own. It reads HEIC and HEIF images.
- The **Insert Image** dialog will not insert an image until you give it
  real alt text or mark it "decorative". **Describe Image at Cursor** tells
  you the file name and alt text, or says MISSING. With a vision model
  connected, one button drafts alt text for you to check and edit. You always
  approve what goes in, and the button is not there in Safe Mode. When you
  insert into HTML, you can also set the width and height so the page does
  not jump as the image loads, keep the image responsive, and add a caption
  linked to it with `<figure>` and `<figcaption>`.

### Agents

QUILL can carry out tasks that take several steps, and you choose the engine
that runs them:

- **GitHub Copilot**, signing in with a device code.
- The **Claude Agent SDK** or the **OpenAI Agents SDK**, with your existing
  API keys.
- QUILL's own **Native** engine.

A dialog in QUILL lets you paste, save and remove those keys.

Agents from other companies work with text only, and their edits go through
the same preview and undo as everything else. Agent writing tasks (rewrite,
summarize, expand, build a table of contents) run in the background. You can
cancel them, and review a log of each step.

Sixteen ready-made agent personas come with QUILL: Accessibility Editor,
Citation and Link Fixer, Code Doctor, Data Cleaner, GitHub Maintainer,
Markdown Publisher, Math Tutor, Meeting Notes to Actions, Plain-Language
Rewriter, PRD Architect, QUILL Concierge, Release Notes Builder, Researcher,
Reviewer, Summarizer, and Writing Companion. The **AI Library** keeps
prompts, skills and agents in one place. A prompt you wrote once can become a
reusable skill, and then a full agent.

### The Listening Companion

The Listening Companion turns a recording into something you can use.
Transcribe it, with translation and speaker labels if you want them. Then
make Meeting Minutes, Action Items, an Executive Summary, Interview or Study
Notes, a Q&A, a Follow-Up Email, Key Quotes, a Decisions Log, or just a clean
draft. The **Action Builder** lets you describe what you want in your own
words, with no syntax to learn. A watch folder runs the whole thing on
anything you drop in.

### Honesty guarantees

Three promises hold for every AI feature:

- **QUILL never quietly changes what is answering you.** If a chat has to
  start on a different engine from the one you set up, because your provider
  could not be reached, QUILL says so as soon as the chat opens.
- **Fallback offers work in both directions, and never happen by
  themselves.** A failed cloud call points you to your on-device model. A
  failed on-device model points you to your cloud provider, and tells you
  plainly that switching would send your text to the cloud. QUILL never
  switches for you.
- **Connection problems are diagnosed, not generalized.** QUILL tells apart
  a rejected key, a key with no access to the model, rate limiting, a model
  still warming up, and a local server that is not running, and gives you the
  actual HTTP status. If a saved key cannot be read on this computer (say
  you moved a portable copy to a new machine), QUILL asks you to enter it
  again instead of failing with a puzzling error.

Prompt caching sends system prompts through each provider's own caching,
where there is one, which saves tokens on repeated work.

---

## Accessible Vault

The Accessible Vault turns a folder of plain-text notes into a personal
knowledge base you can move around by ear. Your notes stay ordinary files in
an ordinary folder. There is no special database, and no graph picture to look
at: everything is a list you can arrow through.

Open a vault on a folder of notes and QUILL indexes it and tells you what it
found: "Vault name: 312 notes, 480 links."

- **Wikilinks.** Write `[[Another Note]]`. **Follow Wikilink** jumps to the
  exact heading or block. If the note does not exist yet, it offers to create
  it, and if the name could mean more than one note, it asks which.
- **Show Backlinks** answers "what links here?" as a spoken list. Each entry is
  read with the sentence that mentions the note, and Enter opens that note at
  the mention itself.
- **Note Neighborhood** lists what sits around the current note: what it links
  to and what links to it.
- **Go to Note** is a type-ahead box. It narrows by title and tells you how many
  notes match as you type.
- **Search Vault** finds phrases and words, with regex and whole-word options,
  and reads each result as note, line and sentence.
- **Show Tags** lists your tags with a count for each, and rolls nested tags up
  under their parent.
- **Unlinked Mentions** finds places where a note's name appears without a
  link.
- **Embeds** pull one note into another: `![[Note]]`, `![[Note#Heading]]` and
  `![[Note#^block]]`. **Speak Embed at Cursor** reads one to you, and **Resolve
  Embed Inline** puts its text in place.
- **Insert Template** fills in `{{date}}`, `{{time}}` and `{{title}}`, asks you
  the question in `{{prompt:Question}}`, and leaves your cursor at `{{cursor}}`.
- **Daily notes**: Open Today's Note, and Previous and Next Daily Note.
- **Export Vault as Website** makes a self-contained, accessible website: one
  page per note, links and embeds working, and an index page.
- **Sync Vault** commits, pulls and pushes over your own git remote. If the
  same file changed in both places, it lists the conflicts by name and stops.
  It never overwrites anything.

---

## Story Studio

Story Studio is a binder for a long piece of writing: a novel, a thesis, a
manual.

**Tools > Story Studio** opens a tree you can walk with the keyboard. The
Manuscript branch holds your parts, chapters and scenes, taken from your
headings. Beside it are groups for Characters, Places, Plot threads, Research
and Brainstorm. A details form records a character's role, goal, motivation
and arc, a plot thread's status, and tags. All of it is saved as ordinary
front matter in the file itself.

**Compile manuscript** joins every manuscript file, in order, into one
document. From there, the usual **File > Export** sends it to Word, EPUB, PDF
or anything else.

A Story Studio project is just a folder of plain-text files, plus one small
file that remembers the order and the groups. Your book is never trapped
inside QUILL.

---

## Tables and CSV

**Table Studio** (experimental) opens a CSV or TSV file, or starts a new
table, in a grid made for screen readers. Left and Right Arrow say the column
heading as you move. **F2** edits a cell, Alt with the arrow keys moves a
whole row or column, and **Ctrl+Insert** adds a row. Where the optional native
UIA provider is installed, NVDA and JAWS get richer cell events.

When you are done, the table goes into your document as a Markdown or HTML
table with headings, or saves back out as CSV.

Inside a document, the table navigation commands move by cell: next,
previous, above, below, first, last, row start and row end. Word tables you
open for rich editing come through as real tables you can read and jump to
with single-key navigation, instead of disappearing.

---

## Git and GitHub

Version control is usually hard going with a screen reader. The text is full
of punctuation, differences are laid out for the eye, and the tools expect you
to watch two columns at once. You already trust QUILL with your writing, so
QUILL is where we made git and GitHub work by ear.

### Files on GitHub

QUILL opens files straight from a GitHub repository, lets you browse the
repository's tree, and saves a file back. Your token is kept in the system
credential store, and QUILL asks for your consent the first time. The
repository field takes `owner/repo`, a `github.com` address you paste in, or a
`git@github.com:` remote.

### The Items viewer

The GitHub Items viewer lists issues, pull requests, branches, commits,
workflows and workflow runs, all in one list you can arrow through.

- **Pinned repositories** keep the few you use most close at hand, so you are
  not typing `owner/repo` again. **Favorites** (**Ctrl+D**) bookmark one issue,
  pull request, branch or release, from any repository. They stay on your
  computer.
- **Full GitHub search syntax** (**Ctrl+F**) takes a real query, such as
  `label:bug is:open crash`, within the loaded repository.
- **Quick filter** (**Ctrl+Shift+F**) narrows the rows already loaded, live as
  you type, without going back to GitHub. Focus stays in the box you are typing
  in. It keeps quiet while you type and says the count once you stop, so it
  never talks over your screen reader's typing echo.
- **Local git awareness** fills in the repository for you when the document
  you are editing sits in a clone whose origin is on GitHub.
- **View Upstream** loads a fork's parent repository in place.
- **Columns** chooses which fields show for this view, and remembers your
  choice.

**Diff** on a pull request lets you browse its changed files. Instead of a
wall of plus and minus signs, each file goes through the same comparison as
**Compare Documents**, and you hear a numbered walk through the changes that
matter: "Difference 2 of 5. Text changed at line 41." A new file is read as
its content. A deleted file is announced as deleted. A binary or very large
file gives you its change counts. **Compare** on a branch does the same
between two branches, and you do not need to sign in, because it changes
nothing.

**Summarize** hands a long thread, even a hundred comments, to your AI and
gives you back a short summary in plain prose: what it is about, where it
stands, what is still open, and what seems to come next. It uses the same AI
connection, privacy settings and consent as the rest of QUILL. Nothing is
sent until you press it.

**Batch** works on several selected items at once: close, reopen or label
them. It is the one part of the viewer that changes things in bulk, so it has
firm limits. You must be signed in, and anonymous viewing stays read-only. The
confirmation names the exact action and the exact item numbers. If some items
fail, the rest still go through, and QUILL tells you which ones failed and
why.

**Actions** holds the commands that change one item: New Issue, New Pull
Request, Merge Pull Request, Delete Branch, Re-run Workflow, View Artifacts,
Reply to Thread, Edit This Comment and Delete This Comment. The comment
commands work with **Alt+N** and **Alt+P**: move to a comment, then act on
that one.

**View Artifacts** lists a workflow run's build artifacts with name, size and
expiry date. It downloads one or all of them to a folder you choose, with a
progress window you can cancel and a question before anything is overwritten.
Your GitHub token only ever goes to github.com. GitHub hands back a
short-lived download address on another server, and QUILL fetches that with no
token attached.

### Administering a repository

**Tools > Git and GitHub > GitHub** gathers the jobs that would otherwise send
you to a web browser:

- **Create Repository**, which offers right away to sync a local folder, so
  you can go from nothing to a folder pushing to GitHub without opening a
  browser.
- **Fork Repository**, **Rename Repository**, **Change Repository
  Visibility** and **Change Default Branch**.
- **Delete Branch** and **Configure Branch Protection**.
- **Commit Multiple Files**, which puts several local files in one commit.
  Save to GitHub, by contrast, saves the one document you have open.
- **Browse Organization Repositories**.
- **Create Release**, published or kept as a draft, with GitHub's automatic
  notes from merged pull requests if you want them.
- **Dispatch Workflow**.
- **Notifications**, a real inbox across all your repositories, not just the
  one loaded.
- **Security Alerts**, for open Dependabot alerts.

None of the commands that change things work without signing in. If you are
not signed in, QUILL offers to start sign-in right there. Four big actions ask
you to type the exact name or number before they go ahead: renaming a
repository, changing its visibility, deleting a branch and merging a pull
request. Every other change asks a question that names exactly what will
change.

Two more commands use the `gh` command-line tool you have installed. **Ask
Copilot for a Command** takes a description of what you want to do and
suggests a git or `gh` command. **Explain a Command** takes a command you do
not recognize and explains it in plain language. You can manage Codespaces
too. Codespaces use real compute and storage minutes, so their confirmation
says so in plain words.

No `git` or `gh` on your computer? **Help > Download Optional Components** has
a portable Git for Windows and the GitHub CLI for Windows and macOS, each
checked against its checksum. If you already have a copy installed, QUILL uses
yours.

A few GitHub areas are not in QUILL yet: **Discussions**, **Projects (v2)**,
**Packages**, and **transferring a repository to another owner**. Each needs
work we could not test properly for this release, so we left it out rather
than ship a guess. They will come when they can be built and checked.

### Local git

This part is not about GitHub. It is about `git` itself, and it may be the
part of QUILL I am proudest of. None of these commands contacts GitHub or any
other network service.

**Resolve Conflicts.** If you have used git, you have met the conflict markers
`<<<<<<<`, `=======` and `>>>>>>>`. A screen reader reads them as line noise.
QUILL works out what each conflicted file really says and walks you through
the conflicts one at a time: "Conflict 1 of 3: your version says X; their
version says Y." For each one, you keep yours, keep theirs, keep both, or type
something else. It goes through every conflict in every file, and you make
each decision yourself.

**Interactive Rebase.** `git rebase -i` normally opens a text file and expects
you to reorder lines and change words like `pick`, `squash`, `reword` and
`drop` without breaking anything. QUILL gives you a proper window instead: one
commit per row, the action chosen from a list, and Move Up and Move Down to
reorder. If a step runs into a conflict, the conflict walk-through opens by
itself, and the rebase carries on afterwards.

**The rest of the toolkit.**

- **Uncommitted Changes** stages and unstages through a comparison you can
  listen to, not a raw diff.
- **Switch Branch** stops uncommitted work from following you to the other
  branch by surprise.
- **Stash Changes** and **Manage Stashes** guide you through stashing.
- **Who Wrote This Line** is `git blame` for the line you are on, spoken.
- **Start Bisect** and **End Bisect** turn `git bisect` into a plain
  conversation: is this version good or bad?

**Worktrees.** Here is a problem few people ever name. When you switch
branches the usual way, git rewrites the files in your folder. The names and
paths stay the same, but the contents change. If you can see the screen, you
notice at once. With a screen reader, nothing tells you. The paragraph under
your review cursor now belongs to another branch, in a file that still has the
name of the one you opened, and you keep reading words that are no longer what
you thought.

A worktree fixes that. It is a second folder attached to the same repository,
with a different branch checked out in it. One history, one set of branches,
two folders. Nothing under your cursor ever changes, because the two folders
never share a file. Changing context becomes opening a different file, which
you choose and hear yourself do.

**Tools > Git and GitHub > Local Git > Worktrees** tells you how many there
are as it opens. Each row is one full sentence, such as "Linked worktree at
D:\usb\quill-spike, on branch spike, locked: on a USB drive", so you do not
have to arrow across columns.

- **New Worktree** asks where the folder goes and which branch it holds, or
  makes a brand-new branch with an optional starting point. Its folder box
  takes whatever you paste. QUILL checks first and tells you in a sentence if
  something is wrong: the folder already has files in it, the folder is inside
  the repository, or the branch is already open in another worktree, and if
  so, which folder.
- **Open in QUILL** opens the document you are reading, from the worktree you
  picked. If that file does not exist on that branch, it offers a file picker
  in the right folder.
- **Remove** deletes the folder, never the branch, and its question defaults
  to No. If git refuses because of uncommitted changes, QUILL says so plainly
  and asks you a second, separate question instead of forcing it.
- **Lock** and **Unlock** protect a worktree on a USB drive or network share,
  which git would otherwise think had gone. You can record a reason and hear
  it later.
- **Prune** clears the records of folders that really are gone, and tells you
  which ones it tidied, or that nothing needed doing.

Across all of local git, you never hear raw git error output. Every message is
a finished sentence written to be spoken.

### Synchronizing a folder

**Tools > Git and GitHub > GitHub > Sync Folder with GitHub** works with any
folder: notes, a writing project, source code, a whole body of work. If the
folder is already a git repository with a remote, QUILL commits, pulls and
pushes in the background. If it is not, QUILL tells you exactly what it will
do ("this runs `git init`, then adds the remote repository you provide as
origin") and changes nothing until you say yes. If the same file changed in
both places, it lists the conflicts by name and stops. It never settles a
conflict by quietly overwriting.

QUILL uses the git you installed and the credentials git already knows, such
as an SSH key or your system's git credential manager. It makes no second set
of credentials. It behaves just like a normal `git push` from a terminal.

There is a simpler kind of sync that needs no git at all. Point QUILL's data
location at a folder that OneDrive, Dropbox, Google Drive or iCloud already
syncs, and your settings, snippets, dictionaries and keymap travel between
computers with it. QUILL writes ordinary files, and the sync program carries
them. The setup wizard explains this, along with one limit: do not run QUILL
on two computers at once against the same synced data folder, because QUILL
cannot sort out changes made on both at the same time.

We thought about building our own QUILL sync service, with accounts and
online storage, and decided against it. Folder sync and git already do the
job.

[Tutorial 8: GitHub inside QUILL](../tutorials/08-github-inside-quill.md)
teaches all of this from start to finish.

---

## Quill Radio

Quill Radio is a full internet radio player. It is a standalone app with its
own window, menu bar and tray icon, for when you want the radio on without
opening an editor. From QUILL, it is on the **QuillVille** menu: choose **Open
Quill Radio**.

It shares its code and settings with the rest of the family, so a station you
favorite is there next time, in every app. Its menus carry everything a
listener needs: **Sound Enhancements** and the **radio output device**
chooser, the **Station Details** command on a favorite, **back up and
restore**, **Customize Features**, and **Start Quill Radio with Windows**.

### Finding something to listen to

**Browse Stations** searches [RadioBrowser](https://api.radio-browser.info), a
free, community-run directory that needs no key. Type a name, and narrow by
tag or genre and by country if you like. **Find Stations** searches
RadioBrowser, iHeart, TuneIn and SomaFM all at once, and also takes a website
address.

**Find Streams from a Website** reads one page you name and lists the streams
on it. It understands the players that hide the stream behind a "Listen Live"
button: Triton Digital / StreamTheWorld, and iHeart or TuneIn station pages.
Each one is turned into the real stream, not a page address that will not
play.

It also handles **SecureNet's player** (`securenetsystems.net/v5/...`), which
many American broadcasters use. That page does show its stream address, but
the address looks ordinary, such as
`https://ice66.securenetsystems.net/ROM`, with no `.mp3` on the end and no
`/stream` in the path, so it used to be thrown away with the page's other
links. Quill Radio now recognizes the player and lists the real stream first,
whether you point it at the player page or at a station's own site with the
player built in. A station saved from such a page also repairs itself the
first time it fails to play.

The browse tree also has sources that need no searching. It has twelve
branches, in this order:

- **Favorites**: your own saved stations, in nested folders you arrange, with
  search, reordering and a "find in this folder".
- **Popular Stations**: the directory's most-listened stations, for when you
  want something on and do not much mind what.
- **Radio Browser (by Genre)**: the community directory, browsed as genre
  folders.
- **Weather / NOAA**: a directory of real NWR transmitters you can browse and
  search by state, SAME code or call sign. It has three levels of offline
  fallback, so it works even when the directory cannot be refreshed.
- **ACB Media**: the American Council of the Blind's ten Live365 stations,
  built in so they are there before any network call. Their mission and ours
  overlap closely.
- **NFB Radio**: the National Federation of the Blind's NFB-NEWSLINE Radio
  Network stream, built in the same way and for the same reason. It is one
  long-running speech and talk stream, there before any network call.
- **Radio Reading Services**: twenty checked audio-reading services for blind
  and print-disabled listeners, built in for offline use, with a live refresh.
- **SomaFM**: the listener-supported independent channels, fetched live from
  somafm.com, on a branch of their own.
- **TuneIn**: browsed through TuneIn's own folders, not flattened into one
  list.
- **iHeart**: browse by genre or A to Z.
- **Community M3U (Music Genres)**: a playlist collection kept by the
  community, by musical genre.
- **Xiph / Icecast Directory**: the open Icecast directory, also by genre.

Whatever you select, a read-only details pane tells you what QUILL knows about
it: country, language, tags, codec and bitrate, community votes, homepage and
stream address. You know what you will hear before you press Play. **Station
Details** gives the same readout for any favorite.

Not every station is in a directory. **Add Custom Station** takes any stream
link, with an optional homepage and tags, and a **Test** button plays it before
you save. **Find Streams from a Website** fetches the one page you name and
lists every stream-like link on it (an `<audio>` tag, a `.pls` or `.m3u`
playlist, a Shoutcast or Icecast mount point), with a plain reason for each, a
Test to preview it, and **Use This Link** to carry the name and address into
Add Custom Station. It reads that one page instead of opening a browser
inside the app, because station pages nearly always list their stream as a
plain link, and a results list is easier to work with than a web page.

Two kinds of link get special handling.

- **Live365** station pages, player links and even a bare station id are
  turned into the real stream address. This is a simple text change. Nothing
  is looked up and nothing is sent anywhere. A link that is not Live365 is left
  alone.
- **YouTube** links, including YouTube Live, work like any other station.
  Paste one into Add Custom Station and you get a station with the same player,
  favorites, Record Now and scheduled recording. Quill Radio saves the page
  link, not the stream, because YouTube stream addresses expire within hours,
  so it finds the audio again each time the station plays or records.

That YouTube lookup uses **yt-dlp**, which QUILL never bundles. It installs
when you need it, after a one-time notice the first time you add a YouTube
station. The notice includes a plain reminder to record only what you have the
right to record. You are asked when you add the station, not when it plays,
so a recording set for 3 a.m. is never the first time QUILL reaches YouTube.
It is off entirely in Safe Mode. Finding the stream happens in the
background: you hear "Connecting" straight away, the window never freezes,
and if you press Stop or pick another station while it looks, the last
station you chose is the one that plays.

### Listening

The player keeps going when you close a window. Closing the station browser,
the custom-station window or the link finder never stops the music, so you can
listen while you carry on writing.

Playback controls: Play and Pause, Stop, Play Last Station, Jump to Live,
Rewind 30 seconds and Forward 30 seconds, volume up and down, mute, and a
volume boost. Two more are on the menus. **Sound Enhancements** is a
three-band equalizer and compressor, set once for everything or remembered
for each station. The **radio output device** chooser sends the music to a
different device from your screen reader.

Radio's volume is its own. It is separate from your Windows volume and from
your screen reader's speech volume, so you can keep the music low under your
speech without touching either. Your volume is remembered between sessions.

A **Sleep Timer** ends a listening session gently. Choose a preset or type
your own length of time. The radio fades to silence instead of cutting off
mid-sentence, then stops, and puts your volume back where it was, so the next
time you press Play it is not oddly quiet.

You can turn **Announce Track Titles** on or off. **What's Playing** says the
current track. **What's Playing (Review and Copy)** opens a read-only window
you can arrow through and copy from. **Copy What's Playing** puts it on the
clipboard. If a stream carries no titles, Quill Radio says so instead of going
silent.

When the app opens, focus is in your Favorite stations list: arrow to a
station, press Enter, and you are listening. The menu bar has a Station menu
(Browse Stations, Add Custom Station, Find Streams from a Website, and your
favorites listed right there for one-keystroke switching), a Playback menu
with a live now-playing line, and a Record menu. The Browse, Favorites,
Schedule and Weather windows share one menu bar and one Window menu, and
**Ctrl+Tab** moves between them. On the **QuillVille** menu, **Open Quill** is
there for when you decide you want the full editor after all.

### Recording

With FFmpeg installed (an optional component, installed when you need it),
**Record Now** saves whatever is playing straight to a file, from the menu or
the tray. **Schedule Recording** sets one up for later: once, daily or weekly
at a time you choose.

**Recording Settings** covers:

- format and bitrate
- the destination folder
- a filename pattern, with `{station}`, `{date}` and `{time}` tokens
- an optional temporary folder for recordings in progress, moved into place
  in one step when they finish
- a maximum length, so a recording you forgot about cannot quietly fill your
  disk

There are five recording formats. **MP3** and **OGG Vorbis** make smaller,
compressed files, and they are the two that use the bitrate setting. **FLAC**
and **WAV** lose nothing. **Raw stream** is the one worth knowing about: it
saves the broadcast exactly as it was sent, with no re-encoding, so nothing is
lost and nothing is added, and the file extension comes from the stream's own
codec. Choose Raw stream for archiving. The bitrate control hides itself,
because it would do nothing.

Recording copes with real life:

- A dropped connection reconnects and the recording carries on.
- Filenames are made unique, so nothing is overwritten.
- A serious error is told apart from a passing one.
- A scheduled recording starts anywhere within its window, not only at the
  exact second.
- A recording interrupted by a restart offers to resume, and one missed while
  the app was closed is reported the next time you open it.
- Stopping a recording lets FFmpeg finish the file properly, so it closes
  cleanly.
- The recordings list updates in place with the time so far, and finished
  recordings go to a default folder that is easy to find.

### Weather inside Radio

Quill Radio carries the full Weather menu described in the next section, so
the app you leave running all day can also watch for a tornado warning. That
menu lives in two places: here and in Quill Weather itself. The editor does
not have it.

### Housekeeping

- **Wake-Up Timer** starts a station at a time you choose.
- **Remove All**, in the Favorites manager, clears every favorite in one step.
  It asks first, and writes a backup you can restore.
- **Start Quill Radio with Windows** sets Quill Radio to start when you sign
  in, then tells you whether it worked, because a locked-down computer can
  refuse without saying so.
- **Back up and restore** writes a portable `.qrbackup` file with your
  favorites, settings, wake timer and recording schedule (and your recordings,
  if you like), and reads it back on another computer.
- **Customize Features** turns whole menu areas (Recording, Weather) on or
  off, so the app is as small as you want it.
- Radio keeps a log, with a level you can set, for when something needs
  looking into.

---

## Quill Weather

Quill Weather watches the United States National Weather Service and tells
you when something is happening where you are. It runs in the system tray on
its own. Quill Radio carries the same Weather menu, so if you already leave
the radio running, you already have everything below. The QUILL editor has no
Weather menu. To get weather alongside the editor, run Quill Weather in the
tray.

**Weather Now** (**Ctrl+Shift+W**) opens the Weather Center:

- current conditions
- an hour-by-hour forecast, as long as you choose, with temperature,
  conditions and chance of rain or snow
- a moon almanac (phase, illumination, moonrise and moonset), worked out on
  your own computer with no extra service

The local time at the place you looked up comes first, because "what time is
it there?" is usually the first thing you want to know. **Quick Weather**
(**Ctrl+Shift+Q**) is the short spoken version.

**Weather Guardian** matters most. It watches your location in the
background for watches, warnings and advisories, and speaks them. For a truly
severe event it interrupts, instead of waiting behind whatever else is being
said. During severe weather it checks more often, down to the National
Weather Service's own limit of every 30 seconds, then eases off again
afterwards. A Windows notification comes with each announcement. The live
watch and the background check share one record of what you have already been
told, so you never hear the same warning twice.

You control the **alert sounder**: on or off, your own `.wav` file with a
preview button, and how many times it repeats. **Test Alert** plays the whole
alert from start to finish, clearly marked as a test. It changes nothing and
needs no network, so you can hear how it will sound at 3 a.m. at a time that
suits you.

**Active Alerts** lists what is in effect right now. **Add Location** adds a
place to watch. **Start and Stop Weather Monitoring** (**Ctrl+Shift+M**) and
**Pause and Resume Alert Checks** let you decide whether it is running.
**Listen to Local NOAA Weather Radio** tunes in the nearest transmitter, and
**Update NOAA Weather Radio Directory** refreshes that list.

Quill Weather can **start with Windows**, start minimized to the tray, and
keep watching when you close its window. It can also set up a **per-user
Windows Scheduled Task**, so alerts are checked with no program running at
all, and a Windows notification your screen reader reads tells you what it
found. **File > Show and Hide Key...** lets you choose a key that shows and
hides it from anywhere; there is none until you choose one.

---

## Quill Inkwell

QUILL has always expanded abbreviations in its own editor. But as soon as you
went to a browser, a mail program or a form, the abbreviations you had built
up were gone.

Quill Inkwell fixes that. It sits in the system tray, listens for the
abbreviations you already have, and expands them wherever you can type. Type
`addr` and a space in a web form and your address appears. Type `sig.` at the
end of an email and your signature appears, with the full stop still there.

### One library, not two

This is what sets Inkwell apart from a separate text expander. Inkwell and
QUILL read and write **the same file**. Add an abbreviation in QUILL's
Abbreviation Manager and it works in your browser moments later. Add one in
Inkwell and QUILL's editor knows it too. There is nothing to import, export or
keep in step, because there is only one library. Every setting on an
abbreviation (its category, what expands it, what is spoken, whether it plays
a sound) goes with it.

Inside QUILL's own editor, QUILL does the expanding and Inkwell stays out of
the way. QUILL changes the document directly, which is faster and safer than
one program typing into another. You should not notice any difference: the
abbreviations, the settings and the results are the same either way.

### Using it

- **File > Show and Hide Key...** lets you choose a key that shows or hides
  the Inkwell window from anywhere. There is none until you choose one.
- **Ctrl+Alt+Shift+K** opens Quick Insert from anywhere, so an abbreviation
  you have not memorised is always two keystrokes away.
- **Ctrl+Alt+Shift+X** expands the word just before the cursor without
  waiting for a space. It is handy mid-word, at the end of a line, and for an
  abbreviation you have set never to expand on its own.

If an abbreviation expands when you did not want it to, press **Backspace
right away** and your abbreviation comes back. You have a few seconds, in the
window where it happened. After that, Backspace works as usual.

Expansions that ask you to fill something in work here too. The same fill-in
form appears, focus goes back to wherever you were typing, and cancelling
costs nothing, because nothing is erased until you accept.

### Where it will not type

Inkwell refuses to type in some places on purpose:

- password managers: 1Password, Bitwarden, KeePass and KeePassXC, LastPass,
  Dashlane, Keeper, NordPass, RoboForm and Enpass
- the Windows sign-in and lock screens, the credential prompt and the UAC
  dialog
- any programs you add to that list yourself

It decides by which window has focus, never by what you typed.

It also checks that whatever has focus really accepts text before it replaces
anything, so its backspaces never land in a list doing type-ahead, or on a web
page where Backspace means "go back".

One limit comes from Windows, not Inkwell: an ordinary program cannot see
keys typed into a program running as administrator, so nothing expands there.
Inkwell tells you the first time it happens, so it does not seem broken. If
you need expansion in such a program, start Inkwell as administrator too.

### What it does not do

Inkwell keeps **no clipboard history**. It reads the clipboard only at the
moment an expansion containing `${clipboard}` fires, and never stores what it
finds. Your clipboard is yours, and whatever clipboard manager you use keeps
its job.

### What it remembers while you type

To know where a word ends, Inkwell has to notice your typing. Here is exactly
what that means:

- It holds at most 64 characters, in memory only.
- Nothing is written to disk, added to a log or sent anywhere. There is no
  network code in the expansion path at all.
- The memory is emptied after every expansion, on Escape, on any arrow or
  editing key, on any Ctrl or Alt combination, whenever focus moves to another
  window, and whenever you pause expansion.
- Nothing decides what to keep based on *what* you typed. That is why the rule
  that keeps it out of password managers looks at the window, not the text.

**Ctrl+Shift+E** stops it, the tray menu stops it, and Safe Mode never starts
it.

---

## QUILL Lite, and one family

**QUILL Lite** is QUILL's editor on its own: a Notepad-sized program for when
you just want to open a file, change a line and save it. It installs beside
QUILL, keeps its own settings in its own folder, and is a separate download.
It is the same editor with everything else taken out. The two share the code
that does the editing, so a fix in one arrives in the other.

We keep it that way on purpose: **QUILL Lite may never be ahead of QUILL.** If
QUILL Lite needs something new, QUILL gets it in the same release. Otherwise
you could use QUILL for years and never know what you were missing.

For 1.0, that meant changes in both directions.

**QUILL gained what QUILL Lite already had.** The two now share one document
model. Spelling suggestions spell themselves out as you arrow through them,
which is the only way to tell "receive" from "recieve" by ear. There is a
Spelling Announcements window. And the formatting keys that come with the
editing control, such as `Ctrl+U`, no longer slip formatting into a Markdown
or plain document without marking it changed, telling you, or saving it.

**QUILL Lite gained what QUILL already had**, where it fits: Word's **F12**,
**Ctrl+F12** and **Ctrl+Shift+F12** for Save As, Open and Print.

**The keyboards came together.** Sixteen commands moved off QUILL's leader
key onto the plain keys QUILL Lite already used. Thirteen commands that only
had a key inside a keymap profile now have one by default. Every editor
command now has a key, or a written reason it does not. Eight keys still
differ on purpose, each for a reason we have written down and test. Where
Word, WordPad or Notepad use a key for something both editors do, Microsoft's
key wins, and both keymaps are tested against that rule.

**Nothing reloads under your hands.** When another program changes the file
you have open, QUILL asks: Reload from Disk, Keep Mine, or Open Disk Version in
a New Tab. The question has a "do not ask me again for .docx files" checkbox,
and **File > Forget Remembered File-Change Answers** (**Ctrl+Shift+F11**)
takes your answers back. A remembered Reload never throws away unsaved edits;
QUILL asks instead.

**Three things QUILL can now tell you about itself**, all on the View menu:

- **What Is This Document?** (**Alt+Shift+F1**) describes its shape, not its
  name: the length, then headings and list items, then anything that will
  stop you. Read-only comes last, because it is the one that changes what you
  do next.
- **What Changed?** (**Alt+Shift+F2**) tells you what the last command did to
  the text, even for commands like Sort Lines that work silently.
- **Undo and Say What Changed** (**Alt+Shift+F3**) tells you whether an undo
  reversed forty lines or a single character, and when you have reached the
  bottom of the undo list.

Only sizes are remembered for these, never your text.

**File > File Format** (**Ctrl+Alt+E**) is one window for encoding and line
endings, the same in both editors. It shows the format your file really has.
If your file uses something the lists do not offer, such as UTF-16
big-endian or old Mac CR line endings, a **keep as is** row keeps it that way,
so saving never quietly converts your file.

**Start from the setup you already have.** A **QUILL Lite** feature profile
gives QUILL the same nine menus as QUILL Lite and nothing else. The other
features are switched off, not hidden, so getting one back is one tick.
**Tools > Customize and Support > Bring My QUILL Lite Settings...**
(**Alt+Shift+F11**) brings your QUILL Lite abbreviations, dictionary, copy
tray, clip library and bookmarks into QUILL, and from then on the two editors
share them: a change in either is a change in both. It also copies your
preferences and changed keys across once. Before it does anything, it tells
you what it will do, including what it is leaving behind. Nothing already in
QUILL is replaced, and nothing happens unless you ask.

**No menu offers the same Alt letter twice.** When two items share a letter,
Windows does not press either. It moves between them and waits, so the letter
stops being a shortcut. That costs most for people who use menu letters
precisely so they do not have to hear a whole menu read out. We found 170 of
these across the family, from Tools > Customize offering "Export..." three
times to six in Cast's Help menu. All 170 are fixed, and a check keeps them
fixed.

QUILL Lite has its own user guide and release notes.

---

## Quillins: extending QUILL

Quillins are QUILL's extensions. A Quillin says up front, in its manifest,
exactly what it needs: to read text, write text, use the clipboard, fetch a
web address, read or write files, or change core settings. Each time it does
one of those things, you are asked at that moment, not once at install time.
A Quillin that uses the network must also list the exact sites it may reach.

Quillins can be written as simple declarations, or as separate handler
programs in Python or Node.js. JavaScript authors get a `@quill/api` package,
and a scaffold tool makes a starter manifest, extension file, README and
license.

A Quillin can add:

- commands and menu items
- settings pages, described in the manifest (control type, label, default and
  validation) and shown as accessible tabbed preferences
- status-bar cells
- snippet-gallery templates
- abbreviations and insert triggers
- subscriptions to fourteen document and lifecycle events, each with its own
  conditions
- timer events for scheduled background work
- file types that trigger it when a matching file opens
- category labels and dependency declarations

A set of Quillins comes with QUILL, turned on: Math Equations (contributed by
Robert Danaraj), BRF Tools, Smart Insert, Journal Stamp, Document Guardian,
Status Scribe, Insert Tools, Insert Character, Line Tools, Text Tools,
Markdown Helpers, and a Node.js word-count example that shows the JavaScript
route works from start to finish.

**Third-party Quillins are disabled by default** in a standard 1.0.0 build. A
fresh install never runs extension code it did not come with. If you turn them
on, the **Quillins Manager** enables, disables, reloads and removes them, and
the menu bar updates straight away, so a newly enabled Quillin shows up
without a restart.

The **Quillin Hub** is the community store. **Submit to Quillin Hub** checks
your Quillin on your own computer before anything goes over the network.
Published Quillins are signed, the Hub refuses anything unsigned, and the
store reads out a "Signed by" badge so you hear who published something before
you install it.

One limit to know about: a Quillin built on Node.js still needs an internet
connection the first time you use it, even in the Offline Edition. We know,
and it is on the list.

---

## The Offline Edition

Normally QUILL keeps its installer small and downloads its bigger optional
parts when you need them. The **Offline Edition** does the opposite: every
optional component is inside the installer and the portable download from the
start, so QUILL works fully the moment it is installed, with no internet
needed. It suits a computer that is never online, a locked-down work laptop,
or anywhere your first sign-in cannot reach the internet.

"Offline" means what it says, and we checked:

- **Kokoro** neural voices install and speak entirely from files on your
  computer, engine included.
- **whisper.cpp**, the speech-to-text engine QUILL uses by default, comes with
  its starter model already there. This mattered most: QUILL reaches for
  whisper.cpp on its own, so an offline edition that had to download a model
  before it could transcribe would not really be offline.
- **Faster Whisper**, **Vosk** and **MP3 chapter-marker support** all install
  with no connection, down to the supporting pieces that other packages leave
  to be downloaded.
- **Piper** comes with its engine, a check against a known fingerprint both
  when it is built and when it is installed, and a starter voice ready to speak
  (Lessac, US English, medium quality). More voices are in the online
  catalogue whenever you are connected and want them.

**Help > Download Optional Components** tells you plainly what you have. In
the Offline Edition each component shows as **Bundled**, or as **Not
included** for the few the offline build leaves out. You will not see a
Download button with nothing to download.

The regular, smaller installer and portable download are unchanged, and are
still what most people get.

The one gap left is the Node.js Quillin runtime mentioned above.

---

## Reliability, Recovery, and Safety

A writing tool that loses your work, or quietly does something other than what
it said, is worse than none, and even more so when you cannot glance at the
screen to catch it. A lot of QUILL 1.0 is about making sure that does not
happen.

### Your work is protected

- **Autosave** keeps snapshots of your documents all the time, formatting
  included, so crash recovery brings back your bold and headings as well as
  your words. Snapshots are written in one safe step (to a temporary file
  first, then renamed into place) and always in UTF-8, so a document in an
  unusual encoding can never break a save.
- **Document saves work the same safe way.** A power cut in the middle of a
  save cannot leave you with half a file.
- **Persistent undo** lasts beyond a single session.
- **Restore Backup** and **Restore Previous Version** cover the slower kinds of
  mistake.
- **If your screen reader stops, your work is already safe.** Losing your
  screen reader in the middle of work is one of the most disorienting things
  that can happen at a computer. QUILL watches for it. If the screen reader it
  found goes away and stays away for a short while (so simply restarting JAWS
  or NVDA does not count), QUILL saves a snapshot of every open document right
  away. Then it tells you what happened with whatever can still talk: another
  screen reader if one is running, or QUILL's own built-in voice. A note goes
  into Notifications too, so the explanation is waiting even if you missed it.
  QUILL keeps running the whole time, and tells you when it hears your screen
  reader come back.

### When something goes wrong

- If QUILL crashes, you get a **plain Win32 message box** your screen reader
  can read, even when QUILL cannot draw its normal windows.
- **QUILL only offers crash recovery when there is evidence of a crash**: an
  error, a critical, or a traceback in the log. If QUILL simply stopped, say
  from a forced shutdown or an ended process, you are not asked, because there
  is nothing to look into. The autosave snapshot is kept either way. Only the
  question changes.
- A **recovery diff preview** shows you a read-only piece of what would come
  back, before you restore it.
- **Crash reports** include the actual error and the log lines that led to the
  offer, so whoever reads one can see what happened. They never include your
  document text. Before they are written, they are cleaned of GitHub tokens,
  OpenAI keys, AWS credentials, Slack tokens and long strings that look like
  secrets.
- **Every kind of internal error has a short support code**, in the form
  `[QUILL-...]`. It goes into crash reports and turns "it said something went
  wrong" into something specific that support can look up. Every new kind of
  error gets one too.
- **Errors tell you what to do next.** More and more messages end with the
  next step, such as "Install Pandoc from Help > Download Optional Components
  to convert this format", or "Check the address, credentials, and connection
  under File > Manage Remote Sites." Voice and component downloads, Quillin
  problems, and remote transfers over SSH, FTP, S3 and WebDAV all do this. A
  "What to try next" section you can open appears when opening, exporting or
  importing a file fails.
- **A damaged settings file cannot stop you working.** If `settings.json` or
  `keymap.json` is damaged, QUILL sets it aside and uses the defaults, instead
  of crashing when it starts. Your settings carry a version number, are
  updated step by step when QUILL changes, and the previous version is backed
  up.

### Safety built in

- **Questions that delete or destroy always default to No.** Pressing Enter
  out of habit on "Delete this?" never does the damage, in any window of any
  app in the family. New windows are checked for this before they ship.
- **Every modal dialog opens the same way**, so the keys work the same
  everywhere, and all of them, hundreds of windows, are checked
  automatically.
- **Every place QUILL reaches the network is on a checked list.** No new one
  can be added without an entry on that list and your consent.
- **The Python snippet sandbox** blocks access to Python's hidden internals
  (dunder attributes), allows only a short list of imports, and limits time and
  memory.
- **External engines are on an allowlist** by program name, checked before
  anything is sent to them or read from them.
- **Update lists are checked for a valid signature**, and a missing or
  placeholder signature is refused. Updates are only looked for over HTTPS, on
  a short list of trusted sites. A portable copy gets a ZIP, applied without
  touching your `data` folder and with protection against harmful archives
  (zip-slip and zip-bomb guards). An installed copy gets the installer. QUILL
  never hands a Windows user a macOS download.
- **A signed safety-advisory system** can switch off one specific feature that
  is misbehaving, from a distance. When it does, you are told, it can be
  undone, it works offline, and you can override it on your own computer. A
  menu item switched off this way explains why, right there in the menu,
  instead of just being greyed out.

### Resetting and moving

**Settings** (**Ctrl+,**) opens on a **Find a setting** box: type a word or
two and arrow to the setting you meant, on whichever page it lives. The
**Administration** page can **Export settings...** to a file you carry to
another computer, leaving out the folders that only make sense on this one,
and **Import settings...** brings them back and tells you what the file did
and did not contain.

**Reset Everything to Factory Defaults** puts your settings, shortcuts, menu
changes and feature profile back as they were, after one confirmation.
**Import data from a previous QUILL install** brings settings, shortcuts and
documents over from an older copy.

**Work Personas** (**Tools > Work Personas**) are for people whose day has
two or three very different modes. Each one bundles a feature profile, a
working folder, favorite files and a keymap profile under a name. Start one
with `quill --persona NAME`, or from a shortcut QUILL makes for you.

---

## Everyday details that add up

Some things are too small for a section of their own and too useful to leave
out.

- **Favorite folders.** Recent folders tell you what you opened lately.
  Favorite folders are the ones that must always be easy to reach. **Add
  Favorite Folder** (**Ctrl+Shift+Grave** then **Shift+F**) adds the current
  document's folder, **Remove Favorite Folder...** (**Ctrl+Shift+Grave** then
  **Shift+X**) takes one off, and **Open From Favorite Folder...**
  (**Ctrl+Shift+Grave** then **G**) opens Quick Open across them. All three
  are on **File > Favorite Folders**.
- **Quick Open** puts you straight in a search box and filters as you type,
  across every favorite folder, with capital letters ignored. Each result
  says which folder it came from. By default it looks only at the top level of
  each folder, which keeps results instant and the list short. Check
  **Include subfolders** to go deeper. That search has a limit, so a very
  large folder cannot freeze the window.
- **Paste any path and it works.** The path box in the Open window accepts a
  path with the quotes File Explorer puts around it, a `file://` link with
  hidden characters in it, `%APPDATA%\Quill`, a `~`, or curly quotes. QUILL
  tidies it up first, so you stop hearing "path does not exist" for a path that
  exists.
- **Document Summary** (**Alt+I** on Windows) tells you the word, line and
  heading counts, when the document was last saved, and whether there is a
  recovery snapshot.
- **Speak-status commands** say the window title, the full file path, or a
  status summary whenever you ask.
- **A filename is suggested from your first line** when you save a new
  document. It never replaces a name you already gave a file, and you can turn
  it off.
- **Send as Email** hands your selection or document to your mail program.
  **Copy as Email Body** copies it ready to paste into a message.
- **Post to Mastodon** writes and sends posts, and manages accounts and lists,
  from inside QUILL. It can proofread your post for you first if you like.
- **Progress you can hear.** Long downloads and installs play a short blip
  every five percent, rising in pitch as the work nears the end, with a touch
  of harmony at each quarter and two notes when it finishes. A blip never talks
  over your screen reader, and you still hear the spoken milestones at 25, 50
  and 75 percent.
- **Keep the sound device awake.** Some USB and Bluetooth speakers cut off the
  first moment of sound after a quiet spell to save power. This setting keeps
  the device listening with a silent pulse.
- **Soft wrap and the tab-control toggles** are on the View menu. **Dark mode**
  is chosen in Settings, and QUILL notices system dark mode and high contrast
  on both Windows and Mac. The contrast-ratio announcement and the
  overwrite-mode toggle are in the command palette, and you can give them keys.
- **QUILL can be Thunderbird's external editor.** Install the External Editor
  Revived add-on in Thunderbird and point it at `quill.exe`. Press **Ctrl+E** in
  a compose window, write in QUILL, then save and close, and the text goes back
  into your message. The User Guide walks through it step by step.
- **The QUILL Developer Console** gives you Python and TypeScript consoles with
  session history, output capture and a `q.*` host API, for when you want to
  script the editor you write in. It is off in Safe Mode.
- **The QuillVille menu** is in every app in the family, for moving between
  QUILL, Quill Radio and Quill Weather.
- **Background watchers all work the same way.** The watch folder, weather
  monitoring and GitHub monitors share one set of choices: how often they
  check, whether they tick so you can hear them, and whether a result
  interrupts you. Set it once and it means the same thing everywhere.

---

## Getting help, and helping back

**Help > Get Help from Support...** (**Ctrl+Alt+F2**) is the direct line. It
used to be called **Report a Bug**. Choose what kind of message it is, type a
subject, and say what happened in your own words. QUILL fills in your screen
reader, its full version and your Windows version, so we can tell straight
away if you are on an older copy. Then it hands the whole message to your own
mail program, addressed to support@community-access.org. Nothing is sent until
you press Send there, and a person reads it and writes back. You do not need a
GitHub account, and there is no GitHub bug-report form any more. **Save
Diagnostics** writes a bundle you can attach, with secrets already removed.

**Help > About Quill** has a live list of contributors (with a copy kept for
when you are offline) and a **Golden Quills** tab thanking the people who
support the project with money.

QUILL is free, and it is made with the people who use it. Much of this release
exists because someone asked:

- The ranked spelling workflow and favorite folders came from a longtime
  Kurzweil 1000 user's side-by-side comparison.
- The Clipboard Collector came from a request for EdSharp's behavior.
- The Thunderbird integration came from someone who wanted to write email in
  QUILL.
- The braille cell-alignment fix became the default because braille readers
  tested it and told us.
- The Offline Edition became truly offline because someone checked the claim
  instead of trusting the label.

The GitHub integration owes its shape to
[GHManage](https://github.com/kellylford/GHManage), Kelly Ford's open-source,
screen-reader-first GitHub browser. It had many of these ideas first, and
QUILL learned from it.

If something surprises you, good or bad, tell us. A note that says "this works
perfectly" helps as much as one that says it does not.

Thank you for trying QUILL 1.0.0. I hope it becomes the place you like to
write, and I look forward to hearing what you make with it.
