# Chapter 12: Making QUILL yours

QUILL comes ready to use, but no two people work the same way. This chapter
is about shaping it to fit you: how much of QUILL you see, which keys do what,
what the status bar tells you, and what happens when you start it in the
morning. Start with profiles and keys, because they make the biggest
difference for the least effort. After that come everyday preferences, the
power tools, Quillins (extensions that add new commands), QUILL on a Mac, and
how to use QUILL in another language or help translate it.

## Profiles, Keyboard Packs, and Customization

You can change a great deal in QUILL, and it tries to keep those changes
tidy. A profile decides which parts of QUILL you see, a keyboard pack decides
which keys you already know, and the Keymap Editor lets you change any single
key. All three live under **Tools > Customize and Support**.

### Feature profiles

A feature profile decides which groups of features are on, quiet or off. It
lets QUILL stay calm when you are new to it, without taking anything away from
you once you want more.

#### Choosing a profile

A profile is a starting point, not a cage. You can switch any time from
**Profiles and Features...**, and you can fine-tune single features afterwards
without losing the rest of the profile's choices.

The first-run Personalise QUILL wizard offers seven profiles as starting
points, each with a plain-English preview of what you get. The full set of
ten lives in **Profiles and Features...**, along with the QUILL Lite profile.
That includes profiles the wizard does not show, such as Reader and Student,
Office and Admin, and Low Vision.

- **Essential.** The calmest editor QUILL can be. Just text, files and the
  basics, with everything else a quiet opt-in away.
- **Casual Writer.** Everyday writing, formatting and cleanup, with the more
  powerful features close by when you reach for them. For papers, citations
  and a table
  of contents, see Author or Student below.
- **Author or Student.** Long-form writing with a table of contents,
  footnotes, and MLA, Chicago or APA citations, for papers, theses and class
  assignments. Choose footnote-style or full academic citations with
  **Format > Markdown > Select Citation Style...**.
- **Reader and Student.** Reading, highlights, references and light writing,
  for working through someone else's material more than producing your own.
- **Office and Admin.** Reliable file work, sessions, cleanup and printing for
  everyday office documents.
- **Developer.** Regular expressions, cleanup, inspection and
  document-analysis tools, right up front, and the only profile apart from
  Full Quill with the coding tools: project tasks with an AI, commands and
  tests, the Developer Console, and Git and GitHub. See "Project tasks: coding
  with an AI" in Chapter 10.
- **Low Vision.** Higher contrast, larger reading aids and friendly inspection
  tools.
- **Braille and Screen Reader Power User.** Navigation that suits a screen
  reader, with the advanced text tools within easy reach instead of buried.
- **Accessibility Professional.** Reading, inspection, trust and accessibility
  diagnostics, for checking other people's documents.
- **Full Quill.** Everything visible, including advanced and experimental
  paths, for people who would rather see it all than wonder why something is
  missing.
- **QUILL Lite.** QUILL with QUILL Lite's nine menus and nothing else: a
  plain-text editor with rich text, spelling, the line tools and the
  clipboard, without the writing environment around them. Choose it if you
  are coming from the small editor and want QUILL to be the shape you already
  know.

> **QUILLBee's shortcut:** You can switch profiles from anywhere. Press
> `Alt+Shift+P`, pick one, and you are done.

#### The QUILL Lite profile

The QUILL Lite profile does two things the others do not.

- It **switches features off rather than hiding them**. Everything it takes
  away is still in **Customize Features** and the command palette, so getting
  one thing back is a single checkbox, not a reinstall.
- It sets `Ctrl+N` to make a plain text document, because that is what
  QUILL Lite makes.

**Bring my QUILL Lite settings.** The first time you choose the profile, QUILL
offers to start from your QUILL Lite setup. You can also do it any time with
**Tools > Customize and Support > Bring My QUILL Lite Settings...**
(`Alt+Shift+F11`), even if you only want your QUILL Lite abbreviations and not
its menus. Before it does anything, QUILL tells you what it will bring, with
counts, and what it will leave behind.

What comes across follows one simple rule: **content is shared and
preferences are copied.**

- Your abbreviations, personal dictionary, copy tray, clip library and
  bookmarks are merged into QUILL's folder, and QUILL Lite is pointed at the
  same copy. From then on, an abbreviation you add in either editor is in
  both.
- Wrap, autosave, spell-check-while-typing and the other editor preferences
  are copied once. After that each editor keeps its own, so they can drift
  apart.
- Keys you have rebound come across the same way. A QUILL Lite command that
  QUILL does not have is left behind instead of guessed at.
- **Nothing already in QUILL is replaced.** Where both have an entry, QUILL's
  wins, because it is the one you have been using most recently.

#### Managing profiles

Use **Profiles and Features...** to:

- switch profiles
- quick-switch profiles from anywhere with `Alt+Shift+P`
- compare profiles
- undo the last profile change
- reset to Essential
- import and export profile data
- create custom profiles
- update a custom profile from your current feature, settings and keymap state
- delete custom profiles

When you make a custom profile, you choose how it starts:

- **Inherit parent profile** starts from the built-in profile you selected.
- **Bare-bones start** inherits nothing, and starts with only the locked core
  safety features turned on.

### Fine-tuning individual features

Sometimes a profile is almost right, and you just want to add or remove one or
two things. **Help > Feature Profiles > Manage Individual Features** lets you
do that on top of your active profile, without making a whole new profile.

The dialog has a checkbox for each feature you can turn on or off. A **Show**
radio button at the top chooses between **All features** and **Disabled
features only**. The disabled-only view lists just the features that are not
on yet, so you can find the one you want without scrolling past everything
that is already running.

As you arrow to a checkbox, a read-only description at the bottom of the
dialog tells you what the feature does and what it depends on. Turning a
feature on also turns on the features it needs. Turning one off also turns off
the features that need it, and QUILL tells you what changed in the status bar.

In the disabled-only view, a feature you turn on drops out of the list
straight away, and focus moves to the next disabled item, so you keep your
place.

### Keyboard packs

A keyboard pack sets up QUILL's keys to match an editor you already know, so
QUILL feels familiar from day one. The packs are:

- Quill Default
- Quill Writer
- Quill Navigation
- Quill Review
- Windows Notepad
- Notepad++
- VS Code
- Microsoft Word

Choose a pack in **Profiles and Features...**. If you later change shortcuts
by hand or import a keymap of your own, the pack's name changes to **Custom**
so you know it is no longer the stock pack.

### Keymap editor

Use the Keymap Editor (**Tools > Customize and Support > Keymap Editor...**)
when you want to change the key for one command. If the key you choose is
already in use, QUILL warns you before it reassigns anything.

#### Rebinding QUILL Quick Nav keys

QUILL Quick Nav, the single-letter movement mode, has its own entries in the
Keymap Editor:

- `QUILL Quick Nav: Link`
- `QUILL Quick Nav: List`
- `QUILL Quick Nav: List Item`
- `QUILL Quick Nav: Table`
- `QUILL Quick Nav: Block Quote`
- `QUILL Quick Nav: Bookmark`
- `QUILL Quick Nav: Code Block`
- `QUILL Quick Nav: Table of Contents`
- `QUILL Quick Nav: Paragraph`
- `QUILL Quick Nav: Sentence`
- `QUILL Quick Nav: Heading`
- `QUILL Quick Nav: Block`

Here is an example that moves two of them:

1. Open **Tools > Customize and Support > Keymap Editor...**.
2. Choose `QUILL Quick Nav: Link`.
3. Enter `K` if you want link jumps on `K` instead of `A`.
4. Choose `QUILL Quick Nav: Code Block`.
5. Enter the grave accent key if you prefer it to the apostrophe.

Two things to know:

- The Keymap Editor will not let you save a conflict.
- Quick Nav keys only work while QUILL Quick Nav mode is on.

### Recommended shortcut updates

Once in a while a shortcut needs correcting for everyone. For example, Find
went back to `Ctrl+F` after some early builds had moved it to a QUILL key
chord. QUILL makes a correction like this **once** and never touches that key
again, so you are always free to change it back in the Keymap Editor.

If you would rather QUILL never changed your shortcuts at all, turn off
**Apply recommended keyboard-shortcut updates** in Settings. Your keys then
stay exactly as you set them, through every update.

### Reset everything to factory defaults

To start over completely, choose
**Tools > Customize and Support > Reset Everything to Factory Defaults...**.
QUILL asks you to confirm first, and the answer starts on "No". Then it puts
your settings, keyboard shortcuts, menu customizations and feature profile
back the way they came, all in one step. Your documents, autosaves and backups
are never touched.

There are smaller resets too: **Reset Keymap** puts back only your shortcuts,
and **Reset to Factory Defaults** inside Settings puts back only your
settings.

## General preferences

Most everyday preferences are in the Settings dialog: **Tools > Customize and
Support > Preferences...**, or press `Ctrl+Comma`. A few quick toggles are on
the View menu as well.

### Settings you can change today

These are the settings people most often want to change:

- theme behavior, including dark mode
- soft wrap
- recent files limit
- system tray mode
- persistent undo
- spell check as you type
- **spell check a document before saving.** When this is on, saving opens the
  Spelling Review (`F7`) first, so you can correct the document before it is
  written. Off by default.
- line-number visibility
- whether QUILL starts with no document open
- **suggest a filename from the first line.** When this is on, saving an
  untitled document fills in the Save dialog with a name taken from the first
  line. It works in every format, and leading markup such as a Markdown
  heading, quote or list bullet is left out. Off by default.
- read-aloud voice selection
- active feature profile
- active keyboard pack
- custom keybindings through the keymap editor
- status-bar order and status-bar visibility
- **reopen last session's documents** (`restore_session`). On by default, the
  way Notepad 11 and QUILL Lite both behave. The list of what was open is kept
  in `session_files`. A file you open from Explorer or the command line always
  wins, and opens *instead* of the session, not on top of it. **Whether it
  asks first** is `session_restore_ask`; see
  [Reopening last session](#reopening-last-session).
- **line endings for new documents** (`default_line_ending`). Windows (CR LF)
  by default, which is what Notepad, WordPad, Word and QUILL Lite all write.
  Set it to Unix (LF) if you prefer. A file you *open* always keeps the line
  endings it already had; this only decides what a brand-new document starts
  with.
- **the format a new document starts in** (`default_new_document_format`).
  Markdown, plain text or HTML. **File > New Rich Text Document**
  (`Alt+Shift+T`) and **New Plain Text Document** (`Ctrl+Alt+N`) always start
  that kind of document, whatever the setting says, and `quill --rich` and
  `quill --plain` do the same from a command line.

Some of these are on the View menu for quick toggling. The preference-style
ones are in the **Settings** dialog
(**Tools > Customize and Support > Preferences...**). Others are in
**Profiles and Features...**, **Status Bar Layout...**, **Keymap Editor...**
and the other customization commands under **Tools > Customize and Support**.

### Status bar settings

If the status bar says too much, or not enough, change it with **Status Bar
Layout...**. You can reorder the items and choose which ones stay visible.

### Reopening last session

QUILL remembers the saved documents you had open and offers them back the next
time you start. With one document, opening it straight away is what you want.
With four, you would have four tabs to sort through before you could start, so
QUILL shows a chooser instead. It appears **when it matters**:

| Last time you had | What happens |
| --- | --- |
| one or two documents, both still there | they open |
| three or more | the chooser |
| any document whose file has moved or gone | the chooser |

The chooser lists what was open, with a checkbox on each row. Everything that
can be opened starts checked, so pressing **Enter** opens all of it, and
unchecking two means "not those". A row whose file has gone says so and cannot
be checked.

- **Open Checked** opens the checked rows and leaves the list alone.
- **Open All** opens everything still on disk, checked or not.
- **Not Now** opens nothing and changes nothing; the same documents are
  offered next time. Escape does the same.
- **Forget Checked** takes the checked rows off the list so they stop being
  offered. **Clear the List** does that to all of them. Neither one touches a
  file. Forgetting only changes what QUILL offers you, not what is on your
  disk, and the window says so under the buttons.
- **Never Ask Again** opens the checked documents and sets QUILL to reopen
  without asking from then on.
- **Ask Me Next Time** undoes that, so you are asked again when it matters,
  like a new install. Only one of the pair is available at a time. The other
  is greyed out, not hidden, so landing on it tells you which way the setting
  is.

Afterwards you hear what happened, for example "Reopened all 3 documents",
"Reopened 1 of 2", or "Forgot 2 documents. 1 still remembered. The files
themselves are untouched."

**File > Reopen Last Session...** (`Alt+Shift+F12`) opens the same window
whenever you want it. That is why Not Now is safe to press: you have put the
answer off, not lost it, and you can tidy the list without waiting for a
restart. If you pressed Never Ask Again and want the window back, open it this
way and press Ask Me Next Time.

The `session_restore_ask` setting holds your choice: **always**,
**when_it_matters** (the default) or **never**. It is separate from
`restore_session`, which decides whether last session is reopened at all.
QUILL Lite has the same window on the same key, and the same setting under
the same name.

### Starting QUILL automatically

**Settings > General** has a **Start QUILL when Windows starts** checkbox,
right next to **Enable background mode**. Check it and QUILL starts the next
time you sign in to Windows. There is no elevation prompt, and nothing an
installer or antivirus tool would find unusual: it uses the same per-user
startup entry most everyday Windows apps use.

Checking it also turns on **Enable background mode**, because a QUILL that
starts quietly at sign-in needs a tray icon for you to bring the window back
from. Unchecking **Start QUILL when Windows starts** removes the startup entry
cleanly, and leaves **Enable background mode** as you set it.

### Task recipes and working modes

Some jobs mean changing several settings at once: getting ready to dictate,
or keeping background checks from talking over you. **More Preferences >
Task Recipes and Working Modes** does that in one step, and always shows you
exactly what it will change first.

1. Press the QUILL key and then `O` to open More Preferences (it is also
   **Tools > Customize and Support > More Preferences...**), and choose **Task
   Recipes and Working Modes**.
2. Arrow through the list. **What it changes**, below the list, says setting
   by setting what each one would change from and to.
3. Press **Apply**.

**Recipes** change their settings once:

- **Quiet background work** stops podcast, watch folder, weather and GitHub
  checks from ticking or interrupting speech. They still run.
- **Prepare for dictation** turns on Windows dictation's announcements, its
  sounds, automatic punctuation and sensible spacing.
- **Make the editor easier to see** chooses the dark theme and larger text.
- **Tell me more while I write** says formatting as you move and indent
  depth, and gives Reveal Codes its detailed descriptions.

**Put Back** undoes the last recipe you applied in the window.

**Working modes** stay on until you turn them off, and turning one off puts
every setting back exactly as it was:

- **Focus** is for writing without interruption: no spelling marks as you
  type, no formatting called out, no start-up tips, quiet background work.
- **Review** is for reading a draft through: spelling checked as you go,
  formatting called out, and Reveal Codes in detail.

Check **Turn a working mode on for this session only** before turning one on,
and QUILL turns it off again the next time it starts. Working modes are not
the same as feature profiles (Profiles and Features), which decide which parts
of QUILL you see at all. Every change a recipe or mode makes is an ordinary
setting you could also change by hand.

### Finding a setting

Settings has a lot of pages, so you never have to remember where something
lives. At the top of the dialog is a **Find a setting** box. Type a word or
two from a setting's name or its help, such as "autosave" or "title bar", and
a list of **Matching settings** appears under it. After a short pause QUILL
tells you how many there are. Press `Down Arrow` to move into the list, and
`Enter` to go straight to the setting on its own page. Finding a setting never
changes it. A setting you cannot change right now says "(disabled)" after its
name.

`Ctrl+F` brings you back to the box from anywhere in the dialog. `Escape` in
the box clears what you typed, and a second `Escape` closes Settings.

**OK** saves your changes and closes Settings, **Cancel** forgets them, and
**Apply** saves them and leaves Settings open. Apply is unavailable until you
have changed something.

### More on the General page

- **Title bar path** shows just the file name in the title bar (the default)
  or the full path.
- **Unsaved-change title style** is how the title bar marks a document with
  unsaved changes: **Text** adds "[modified]" (the default), **Asterisk** adds
  a star, and **Asterisk and text** adds both.
- **Preview browser** chooses which of your browsers opens HTML previews.
- **Open preview beside the editor** shows a Markdown or HTML document's
  preview in a pane beside the editor as soon as you open it. Plain text is
  left alone. On to begin with.
- **Interface language** is the language of menus, dialogs and messages,
  written as a short code such as `fr` or `es`. Leave it blank to follow
  Windows. **Tools > Writing and Language > Change Display Language...** sets
  it for you from a list.
- **Confirm destructive actions** asks before your unsaved changes are thrown
  away, for example when you reload a file from disk. On to begin with.
- **Default document folder** is where the Open and Save As windows start;
  **Choose Default Folder...** picks it. Once you have opened or saved
  something, QUILL starts where you last were for the rest of that session.
  Left blank, it starts in Documents.
- **Default new-document format** is **Markdown** (the default), **Plain
  text** or **HTML**, as described above.
- **Open a blank document at startup** hands you an empty Untitled document
  when nothing else is opening. Turn it off if you always open an existing
  file. Files you named, a restored session and recovered work still open.
- **Store QUILL's data** says where QUILL keeps your settings, snippets,
  dictionaries and keyboard shortcuts: **In my user profile (recommended)**,
  **Next to QUILL, on this portable drive** (only in a portable copy), or
  **Custom folder**, chosen with **Choose Folder...**. When you change it,
  QUILL offers to restart, and the change takes effect when it starts again.
- **Windows and your files** is covered in Chapter 3, under Making QUILL your
  text editor.

### The Administration page

The **Administration** page holds updates, safety and the settings file
itself:

- **Check for updates on startup** and **Release channel** are covered in
  Chapter 15.
- **Enable Developer Console** makes the Python and TypeScript consoles
  available under **Tools > Advanced > Developer Console**. Appendix A
  explains them. Some feature profiles turn it off.
- **TypeScript console execution timeout (seconds)** is how long a TypeScript
  console command may run before QUILL stops it, from 5 to 300 seconds. The
  default is 30.
- **Trust SSH hosts on first connection** is covered in Chapter 3, under
  Editing a file over SSH.
- **Apply recommended keyboard-shortcut updates** lets QUILL apply an
  important shortcut correction once when you upgrade, such as putting Find
  back on `Ctrl+F`. You can still change it afterwards.
- **Upgrade notice** is how QUILL tells you it has updated your settings or
  shortcuts after an upgrade: **Silent**, **Brief announcement** or
  **Summary with Undo**. A backup is always saved first.

Below the settings are five buttons:

- **Export settings...** saves your settings to a QUILL settings file
  (`.qsf`). Folders and file locations that belong to this computer are left
  out, and QUILL tells you how many.
- **Import settings...** reads a settings file back. Settings closes, the
  imported settings take effect at once, and QUILL tells you what the file
  did and did not contain.
- **Reset to Factory Defaults** puts every setting back the way it was when
  QUILL was installed. It asks first, and it cannot be undone.
- **Export profile...** and **Import profile...** save and load your feature
  profile, the choice of which parts of QUILL you see, as a QUILL profile
  file (`.qpf`).

## The Customize and Support menu

**Tools > Customize and Support** keeps every configuration and support
command in one place, which is where you, and anyone helping you, will look
for them. It used to be two separate menus, Support and Customize.

- **Preferences...**
- **Customize Menus...**
- **Bring My QUILL Lite Settings...**
- **Profiles and Features...**
- **Status Bar Layout...**
- **Export and Back Up...** / **Import or Restore...**
- **Keymap Editor...** / **Export Keymap...** / **Import Keymap...** /
  **Reset Keymap**
- **Reset Everything to Factory Defaults...**
- **Show Notifications**
- **Save Diagnostics...**
- **Open Logs Folder** / **View Startup Logs...** / **Open Diagnostics
  Folder**
- **Check for Updates**

To write to us, use **Help > Get Help from Support...**. It lives in the
Help menu, not here.

## Power tools

The **Advanced** submenu (**Tools > Advanced**) holds the automation
utilities, developer tools and power switches for how the editor behaves. You
can use QUILL for years without opening it, but it is worth knowing what is
there.

### Editor utilities

- **Toggle Read-Only Guard** (`Ctrl+Alt+Backspace`) stops accidental edits to a
  document you are reviewing, and is remembered for that file. Bookmarks and
  notes keep working. Chapter 8, Reading without changing anything, has the
  details.
- **Toggle Clipboard Collector** and **Collect Clipboard Now** gather
  clipboard entries into a running log in the open document. This works
  system-wide, the way EdSharp did: while the collector is on, anything you
  copy in *any* application, such as your browser, mail or a terminal, is
  added (each distinct copy once). If the document already has a file name,
  QUILL saves it quietly after each piece and you hear one sentence,
  "Collected and saved." An untitled document is never saved and no Save As
  window opens; it is marked as changed, and you save it when you are ready.
  If a save cannot happen (a full disk, a read-only folder, a file another
  program has changed), QUILL says so and keeps collecting. To have collected
  text wait for you to save instead, clear **Save the document after every
  clip the clipboard collector adds** in **Settings > Editing**. **Alt+Shift+S**
  turns the collector on and off. QUILL Lite has the same collector and the
  same setting, on the same key, in the Clipboard submenu of its Edit menu.
- **Toggle Key Describer** says the names of keys instead of doing what they
  do. It is handy for writing down keystrokes.
- **Toggle Indentation Announcements** and **Infer Indentation...** tell you
  when the indentation level changes as you move.

### Macros

- **Start Recording** and **Stop Recording** capture a sequence of editing
  commands.
- **Play Last Macro** plays back the last one you recorded.
- **Manage Macros...** lets you name, edit and organize saved macros.

Macros are ideal for repetitive cleanup: record it once, then replay it as
many times as you need.

### Authoring utilities

- **Regular Expression Helper...** is the guided home for regular
  expressions, so you never have to face a wall of punctuation alone.
  - A **category tree** holds more than a hundred ready recipes: cleanup
    (multiple spaces, smart quotes, zero-width characters), words and phrases,
    lines, numbers, dates, email and web addresses, Markdown and HTML
    structure, punctuation and dialogue, writing and editing checks, OCR and
    scan cleanup, code identifiers, and capture-and-replace transformations
    with ready replace templates.
  - Pick a recipe and three things happen at once. The pattern goes into the
    pattern box. A **plain-language explanation** appears ("One or more
    digits. Optionally: a period..."). And a **preview** runs against sample
    text taken from your selection, reading every match as a sentence ("Match
    3: line 4, column 7: foo@bar.com"), with replace previews for the
    transformation recipes.
  - The explanation is live. Type or paste **any** pattern and QUILL explains
    it step by step. A broken pattern is explained in words, with the exact
    character position ("Unclosed group: the open-parenthesis at character 4
    has no matching close").
  - When the pattern is right, **Use in Find All Matches** takes it straight
    into the search, with regex mode on and no trip through the clipboard.
    **Copy Pattern** is there for everywhere else.
- **Pandoc Conversion Wizard...** converts supported source files into
  Markdown, HTML or plain text, which opens straight away as a QUILL tab.
- **External Tools and Format Support...** explains what each supported
  helper program adds, whether QUILL can already see it, and the easiest way
  to set it up.
- **YAML Structure Editor...** inspects and edits YAML front matter and
  structure files.

### Document Intake

- **Document Intake Report...** tells you how good an extraction was, and
  whether the source probably had structure that did not survive.
- **Review Extraction Quality...** walks you through the quality signals one
  by one.
- **Report Bad Extraction...** flags a source for manual cleanup or another
  extraction.

These matter when QUILL is reading an imported format for you. They help you
answer questions like: Is this document safe to quote from directly? Does it
need manual cleanup?

An imported document opens with its own text and nothing else. QUILL never
writes a heading such as "PDF Extract", or the name of the engine, into the
file you are reading. Everything about *how* it was read (format, engine,
pages, quality score, which reader each PDF page's text came from, and the
pages that may read poorly, with the reason for each) is in the **Document
Intake Report**, and the short version is announced when the file opens. For a
Word, Excel or PowerPoint file the report also says which reader read it, how
many sheets or slides it has, which sheet was cut short if one was, and, in
the rare case QUILL's own reader could not read the file and MarkItDown did,
why ("QUILL's own reader: not used." followed by the reason). For example, a
Word file whose only content is a scanned picture opens with "Read by:
MarkItDown" if MarkItDown found text in it, and the next line says QUILL's own
reader found no text to read.

### Shell Integration

- **Install Shell Integration...** adds QUILL to the Windows Explorer context
  menu and registers it as a protocol handler.
- **Remove Shell Integration** takes those entries out again.

The **Integration and Context Menu** page in Settings chooses what appears on
that right-click menu:

- **Show QUILL in the file-manager right-click menu** is the main switch. Off
  to begin with.
- **Offer “Open in QUILL”** adds Open in QUILL for text documents. On to
  begin with.
- **Offer “OCR with QUILL”** adds a command that turns an image or PDF into
  text. On to begin with.
- **Offer “OCR with QUILL (structured Markdown)”** adds the AI-assisted
  version, which returns headings and lists as Markdown. It needs AI turned
  on. Off to begin with.
- **Offer “Read aloud in QUILL”** opens a file and starts reading it aloud.
  Off to begin with.
- **Offer “Convert with QUILL”** opens an audio or video file in Quill
  Converter so you can change its format. Off to begin with.
- **File types offered to QUILL** chooses which files get QUILL on their
  right-click menu: images only, images and PDFs, or images, PDFs and text
  documents (the default). Audio and video files have their own Convert
  switch above.

Your choices take effect as soon as you press OK, with no need to install
shell integration again.

## Quillins

Quillins are extensions. They add commands, snippets, menus, abbreviations,
smart triggers, settings pages, status bar cells and document event handlers
to QUILL, without a full restart.

Each Quillin runs in its own worker process. That keeps faults apart: a
Quillin that goes wrong cannot crash QUILL or damage your document. It is not
a security sandbox, though. The worker is an ordinary Python interpreter, so
what really keeps you safe is code review and the Author Covenant. QUILL draws
every Quillin's controls itself, using standard widgets that work well with a
screen reader.

### Bundled Quillins

QUILL comes with seventeen trusted Quillins of its own, all turned on:

- **Smart Insert** (`com.quill.smartinsert`): abbreviations and smart text
  triggers for everyday templates. It adds the `qbug`, `qmeet`, `qlog` and
  `qtodo` abbreviations, and the `=bug()`, `=meeting()`, `=journal()`,
  `=todo()`, `=logentry()`, `=brftest()` and `=rand()` smart triggers. Its
  dynamic `qbrf` abbreviation is reached through `=brftest()` instead.
  Settings are under **More Preferences > Smart Insert**.
- **BRF Tools** (`com.quill.brftools`): preferences for braille translation
  defaults, page handling, status bar display and diagnostics. It needs the
  QUILL Braille Pack. Settings are under **More Preferences > BRF Tools**.
- **Journal Stamp** (`com.quill.journalstamp`): inserts a date header when you
  create a new journal document, tells you your word count (and daily goal
  progress) after every save, and announces session restores. It listens to
  `quillin.enabled` to log when it starts and to `settings.changed` to pick up
  new preferences straight away. Settings are under
  **More Preferences > Journal Stamp**.
- **Document Guardian** (`com.quill.docguardian`): warns before you close a
  short or unfinished document, can stamp an `Updated:` line before each
  save, and can speak the file name and size after each save. It uses the
  `quillin.enabled`, `quillin.disabled` and `quill.shutdown` events. Settings
  are under **More Preferences > Document Guardian**, which has Close Guard, Save
  Stamp, Save Confirmation and Lifecycle Announcements tabs. The Lifecycle
  Announcements tab decides whether QUILL speaks a cue when the Quillin is
  turned on or off. It is off by default, so your first run stays quiet.
- **Status Scribe** (`com.quill.statusscribe`): adds a live word, character
  and sentence count to the status bar. The count updates after every save
  and when you switch tabs. It uses the `ui.log` capability to write messages
  to the Developer Console. Settings are under
  **More Preferences > Status Scribe**.
- **Text Tools**: advanced text changes such as line numbering, hard-wrap,
  regex match counting and block filtering.
- **Insert Tools**: date, time, and date-and-time snippets in the
  **Insert > Date and Time** submenu.
- **Line Tools**: line operations that work from where your cursor is.
- **Markdown Helpers**: help with Markdown syntax.
- **Insert Character**: a searchable picker for Unicode symbols.
- **Word Count (Node)**: a word count that runs on the Node.js Quillin
  runtime, to show that Quillins can be written in JavaScript as well as
  Python.
- **AI Writing Prompts**: extra entries for the prompt library.
- **AI Writing Skills**: ready-made `.sqp` skill files for rewriting, pulling
  out meeting notes, and research drafts.
- **Math Equations**: inserts LaTeX or MathML equations at the cursor with
  **Insert > Insert Equation...** (`Ctrl+Alt+=`). Math Equations is covered
  earlier in this guide.
- **ElevenLabs Scribe Transcription**, **Groq Whisper Transcription** and
  **OpenAI Whisper Transcription**: add those cloud services as optional
  transcription providers (ElevenLabs can also tell speakers apart). Audio is
  only uploaded when you choose to transcribe with that provider and have set
  up its API key. Never offline, and never without your consent.

### Quillin preferences

Every enabled Quillin that has settings gets its own entry at the bottom of
More Preferences (the QUILL key and then `O`, or **Tools > Customize and
Support > More Preferences...**). `Ctrl+,` opens Settings itself; More Preferences is the list
of everything Settings does not hold. Move to the Quillin by name and press
Enter to open its settings.

**Settings tabs.** A Quillin with several groups of settings puts them on
tabs. Use the Left and Right Arrow keys to move between tabs, and Tab to reach
the controls on a tab. Changing tabs does not lose anything you have changed;
everything is applied when you press Save.

**Labels.** Every labeled control (combo box, text field, number spinner) is
placed right after its `StaticText` label, so JAWS and NVDA read the right
label when you Tab to it. Checkboxes (`wx.CheckBox`) carry their own label.

**Reset controls.** Every preference page has Reset options:

- **Reset this setting** puts that one setting back to the Quillin's default.
- **Reset this section** puts back every setting in the section.
- **Reset this Quillin** puts back all of the Quillin's settings.

**Where settings are kept.** Each Quillin's settings are saved safely to
`%APPDATA%\Quill\quillin_settings\<quillin-id>.json`. Turning a Quillin off
hides its preference page but keeps its settings. When you uninstall one,
QUILL asks whether to keep or delete them.

### The Quillins Manager

Open it from **Tools > Quillins > Manage Quillins...**. In the Manager you can:

- See every installed Quillin and whether it is enabled, disabled, or invalid
  (with the error).
- Select a Quillin to hear its details: name, version, author, description,
  categories, the oldest QUILL version it needs, the capabilities it asks
  for, the network hosts it may reach, and whether each of its event
  subscriptions is on or off.
- **Enable** or **Disable** a Quillin without removing it. The change happens
  straight away.
- **Configure Events...** opens a list of the selected Quillin's document
  events, with a checkbox next to each. Check one to turn that handler on,
  uncheck it to stop it. Your choice is saved straight away and kept across
  restarts.
- **Reload** reads all Quillins from disk again without restarting. Use it
  after editing a bundled Quillin while you develop.
- **Remove** uninstalls a Quillin, after you confirm. Its folder is deleted
  from disk.
- **Install from Folder** lets you pick a local folder that contains a
  Quillin. QUILL checks its `manifest.json`, copies the folder into your own
  extensions folder, and turns it on. This will be the way to install
  Quillins from other people once that is opened up.

The details pane lists every capability a Quillin asks for (for example
`fs.read`, `net`, `settings.own.read` or `settings.own.write`), any
`net_allowed_hosts` limits, and whether each event subscription is on. Look
at the capabilities before you turn on a Quillin from a source you do not
know.

If a Quillin cannot load, the details pane tells you why: it needs a newer
QUILL (`min_quill_version`), something it depends on is missing (`requires`),
or there is a mistake in its manifest.

The details pane also has a **Signature** line for every Quillin: `verified`
when a signature file beside the manifest matches the publisher key,
`invalid` when there is one that does not match, or `unsigned` when there is
none. It is read with the rest of the details, so you can hear whether a
publisher vouches for a Quillin before you turn it on. The PyNaCl library this
check needs comes with QUILL. The signing protocol is described in
`docs/signing.md`.

### Document events

Quillins can listen for things happening to your documents and act on them
automatically, with nothing for you to do. There are fourteen events:

| Event | When it fires |
| --- | --- |
| `document.opened` | A file was opened from disk |
| `document.activated` | You switched to this tab |
| `document.before_save` | Right before saving |
| `document.after_save` | After a successful save |
| `document.before_close` | Before a tab closes |
| `document.after_close` | After a tab closes |
| `document.created` | A new blank document was created |
| `document.loaded_from_session` | A document was restored from a crash |
| `smart_trigger.entered` | A smart trigger was activated |
| `abbreviation.expanded` | An abbreviation was expanded |
| `quillin.enabled` | This Quillin was just enabled or QUILL started with it on |
| `quillin.disabled` | This Quillin was disabled in the Manager |
| `quill.shutdown` | QUILL is about to close |
| `settings.changed` | A setting owned by this Quillin changed |

A Quillin can limit an event to certain file extensions, paths or content.
A journal Quillin can stick to `**/journal/**` paths, and a `.LOG` handler can
insist that the file starts with `.LOG`.

Each event subscription has an `enabled_by_default` field. When the author
sets it to `false`, that handler starts switched off, which suits optional or
chatty behaviour. You can turn any event on or off for each Quillin in
**Quillins Manager > Configure Events...**.

Handlers use `api.announce()` to speak their results, and must not hold up
the editor while they work.

### The Quillin Hub

The **Quillin Hub** is where you can share what you make with the community,
and not only Quillins. It takes seven kinds of file:

- **Quillin extensions** (a zipped folder with `manifest.json`)
- **AI agents** (a single `.md` or `.json` agent file)
- **Verbosity packs** (`.qvp.json`)
- **Sound packs** (`.qsp`)
- **Keyboard packs** (`.kqp`)
- **AI skill packs** (`.sqp`)
- **Pronunciation dictionaries** (`.json`)

To check your work before you send it:

1. Choose **Tools > Quillins > Submit to Quillin Hub...**.
2. Pick your file. For a Quillin extension, pick its `manifest.json`; QUILL
   checks the whole folder.
3. Listen to the result. QUILL works out what kind of file it is and runs the
   same checks the Hub runs, on your own computer, with nothing uploaded.

**Passed** means your work clears every check QUILL applies to its own
bundled files. **Needs work** lists each error and warning so you know what to
fix. The **Signature** line says `verified` if there is a signature file next
to yours, `invalid` if there is one but it does not match, or `unsigned` if
there is none. The Hub turns down unsigned submissions, so the "Open the
Quillin Hub" button only appears when your file passes and is signed. Sign it
with `python -m quill.tools.signing sign <artifact>` and run the check again.
The check makes no network connection; only the "Open the Quillin Hub" button
opens anything.

Publishing happens through GitHub pull requests, so every submission is
reviewed in the open. The Hub runs the same checks again, looks over any
extension code for security and for honesty about the capabilities it asks
for, reads your manifest so you never retype your name, version or
description, and checks the publisher signature on every signature file sent
with the submission.

### Authoring Quillins

If you write code, Quillins are built screen-reader-first. Each one must ask
for the smallest set of permissions it needs, and anything sensitive (such as
writing to a file or changing a setting) asks you for consent when it
happens.

A Quillin can add:

- **Commands**: Python or Node.js handlers, or simple declared snippets.
- **Menus**: items in the normal QUILL menu bar.
- **Hotkeys**: keys that respect the QUILL key chord prefix.
- **Abbreviations**: short typed words that expand after a delimiter.
- **Smart triggers**: `=name()` commands typed on the current line.
- **Sound events and sound packs**: its own earcons for its own events.
- **Preferences**: settings pages with tabs, sections, checked controls,
  search keywords and their own storage.
- **Document events**: handlers that run when a document opens, saves,
  closes or is restored, or when the Quillin is enabled or disabled, or QUILL
  shuts down.
- **Status bar cells**: live cells that QUILL refreshes and shows in the
  status bar. Needs the `ui.status` capability.
- **Categories**: one or more labels (`writing`, `accessibility`, `braille`,
  `productivity` and more) for filtering in the Manager.
- **Dependencies (`requires`)**: another Quillin that must be installed first.
  QUILL checks this when it finds the Quillin.
- **Network host allowlist (`net_allowed_hosts`)**: with the `net`
  capability, a list of host names or wildcard patterns it may connect to.
  QUILL blocks any other host, even if you have granted general `net`
  consent.
- **Minimum version (`min_quill_version`)**: the oldest QUILL release it
  supports. An older QUILL refuses to load it.

The full authoring reference is `docs/quillins/quillins.md`. PRD section 5.83a
("The Quillin Hub - community distribution for every shareable artifact") is
the developer guide to every file you can share (Quillins, agents, verbosity
packs, sound packs, keyboard packs, skill packs and pronunciation
dictionaries) and how to check and submit each one. One checker covers them
all: `python -m quill.tools.artifact_validate <path>`.

## QUILL on macOS

QUILL runs on **macOS** as well as Windows, and the aim is for both to do the
same things. Here is what is different, or worth knowing, on a Mac.

### Speech and VoiceOver

- **VoiceOver first, with QUILL's own voice as a fallback.** On macOS, QUILL
  sends its announcements to **VoiceOver** and never talks over it. Headings,
  regions and result messages behave as they do with NVDA and JAWS on
  Windows. If you run QUILL on a Mac *without* VoiceOver, it speaks the same
  announcements with the Mac's own speech synthesizer, just as QUILL on
  Windows uses SAPI when no screen reader is running.
- **Read Aloud and earcons work on macOS.** Live Read Aloud plays through
  `afplay`, so Piper, Kokoro, ElevenLabs and the system voices all speak, and
  the earcon volume slider works too.
- **The accessible WebView** behind the chat, the Markdown and HTML preview,
  the About box and the update dialogs reads correctly with VoiceOver, as it
  does with NVDA and JAWS on Windows.

### Keys on a Mac

- **Function keys and the Fn key.** Many of QUILL's shortcuts use the F keys
  (`F3` for Find Next, `F7` for spell check, `F8` for selection, `F6` for
  moving between regions). On a stock MacBook those keys do system things
  (brightness, Mission Control, media) unless you hold **Fn**, or turn on
  **Use F1, F2, etc. keys as standard function keys** in
  **System Settings > Keyboard**. So you do not have to, Find Next and Find
  Previous also work on the usual Mac keys, `Cmd+G` and `Cmd+Shift+G`, with no
  Fn. You can change any key in the Keymap Editor.
- **Mac-specific defaults.** A few Windows keys would clash with macOS system
  shortcuts, so they are different on a Mac: **Replace** is `Cmd+Alt+F` (not
  `Cmd+H`, which is Hide), **Pop Mark** is `Cmd+Alt+M` (not `Cmd+M`, which is
  Minimize), and **Select Chunk** is `Cmd+Alt+Space` (not `Cmd+Space`, which
  is Spotlight). These may still change. If one clashes with something on
  your Mac, change it in the Keymap Editor and tell us through
  Help > Get Help from Support.
- **Back / Forward Location on macOS** uses `Cmd+[` and `Cmd+]`, so it does
  not clash with VoiceOver's word-by-word reading on `Option+Left` and
  `Option+Right`. Windows keeps `Alt+Left` and `Alt+Right`.
- **Keymap profiles respect your platform.** The built-in keymap profiles
  leave the platform's own keys for quitting, back and forward, and switching
  documents alone, so on a Mac you get the right Cmd keys instead of Windows
  ones.
- **Help menu registered as system Help.** The Help menu is the macOS system
  Help menu, so the usual `Cmd+?` Help shortcut works.

### Menus, files and the rest

- **A real macOS Window menu.** The Window menu (Next, Previous, Close Other,
  Send to Tray) is the macOS Window menu, so it sits in its usual place just
  left of Help, together with the standard Mac items: Minimize (`Cmd+M`),
  Zoom, Bring All to Front and the list of open windows.
- **Standard Mac behaviors.** Preferences and About are where a Mac puts them:
  **QUILL > Settings** and **QUILL > About Quill**. Preferences is the
  standard macOS menu entry, so it appears in the QUILL app menu as you would
  expect.
- **Tray status messages say "menu bar" on macOS.** When QUILL goes to the
  background, comes back, or switches tray mode, the message names what you
  actually have: "menu bar" on macOS, where it is a menu-bar status item, and
  "system tray" on Windows.
- **Setting QUILL as your default editor takes effect immediately.** After
  registering the file types (through `duti` if you have it; install it with
  `brew install duti`), QUILL refreshes the Mac's LaunchServices database, so
  Finder opens your files in QUILL straight away instead of after a restart.
- **The default-folder hint shows a Mac path on macOS.** In Settings, the
  empty default-folder box suggests
  `e.g. /Users/YourName/Documents (blank = last used)`.
- **macOS-safe launch paths.** Opening a file, showing its folder, launching
  an installer or playing a voice sample all use the Mac's own way of doing
  it.
- **Your secrets stay off the command line.** API keys, SSH passphrases and
  other secrets QUILL keeps for you go into the macOS Keychain through the
  native Security framework, so the value never appears on a command line
  where other programs could see it. On a Mac without that native link, QUILL
  falls back to the `security` CLI and warns you the first time, because that
  way does put the value on the command line.
- **On-device AI.** Ask QUILL uses **Apple Foundation Models** (Apple
  Intelligence) on a Mac that supports it, with no model to download and
  nothing sent to the cloud. The GGUF and llama.cpp model picker is hidden on
  a Mac because Apple's model is used instead. You can still connect Ollama or
  a cloud service if you prefer.
- **Signed and notarized.** Release Mac builds are signed with a Developer ID
  certificate and notarized by Apple, so Gatekeeper opens them without
  warnings. QUILL comes as a `.app` (and a disk image).

## Translation and Community Localization

QUILL can show its menus and dialogs, and speak its messages, in other
languages. The translations come from people in the community, the same way
NVDA's do, and you are welcome to help.

### Switching QUILL's display language

Once a translation is installed, you can switch the language QUILL uses for
its menus, dialogs and spoken messages:

1. Open **Tools > Writing and Language > Change Display Language...**.
2. Choose a language from the list, or **System default** to follow your
   operating system. Only languages with a finished translation (an `.mo`
   file) are listed, so you never pick one that has nothing to show.
3. QUILL saves your choice and uses it for new spoken messages straight away.
   Restart QUILL so every menu and dialog reloads in that language.

The first community translation is **Italian**, by Elena Brescacin: menus,
dialogs and spoken messages, with anything not yet translated shown in
English. QUILL keeps growing, and the translation grows with it. Pick
*Italiano* from the list and QUILL speaks Italian straight away, with every
menu following after a restart. More languages appear in the list as
community translations arrive.

### How the translation pipeline works

QUILL uses the standard GNU gettext pipeline (`POT > PO > MO`) for every
string you see or hear, the same model NV Access uses for NVDA. If you have
translated NVDA, JAWS scripts or other accessibility software before, it will
feel familiar.

1. **Strings are marked in the source code** with `_()` for ordinary strings,
   `ngettext()` for plural forms, and `lazy_gettext()` for strings that must
   be translated when they are shown, not when the program loads.
2. **The POT file** (`quill/locale/quill.pot`) is the master template, made
   automatically by `pybabel extract`. It holds every translatable string in
   QUILL.
3. **PO files** (`quill/locale/<lang>/LC_MESSAGES/quill.po`) hold the actual
   translations for each language. This is where translators work.
4. **MO files** are compiled from the PO files by `pybabel compile`. They are
   the files QUILL loads when it runs.
5. **QUILL picks the language** when it starts, from your `language` setting
   (a BCP 47 tag such as `fr`, `es` or `pt-BR`). If it is blank, QUILL
   follows the operating system's language.

Speech strings, the text a screen reader will say instead of text shown on
screen, are marked with a `# SPEECH:` comment in the source code. When you
translate one, keep the natural spoken rhythm as well as the meaning.

### Contributing translations

To contribute a translation:

1. **Fork the QUILL repository** and create a branch named `l10n/<lang>` (for
   example `l10n/fr`).
2. **Copy `quill.pot` into your language folder** as
   `quill/locale/fr/LC_MESSAGES/quill.po`.
3. **Translate each `msgid` into a `msgstr`.** Leave `msgstr` empty for
   anything you have not translated yet; English is used instead.
4. **Run the translation check** to make sure the placeholders are intact and
   see how complete it is: `python -m quill.tools.check_translation`
5. **Open a pull request.** The Translation Coordinator reviews it and merges
   it when it is approved.

**Tools that help:**

- [Poedit](https://poedit.net/): a free, accessible PO file editor with spell
  check.
- [Virtaal](https://virtaal.translatehouse.org/): a lighter alternative.
- Crowdin (once QUILL's project is live): translation in the browser, with a
  review queue.

**Do not translate:**

- Placeholder tokens such as `{name}`, `%(count)s` and `{path}`. Leave them
  exactly as they are in the `msgid`.
- ARIA role names such as `"dialog"`, `"button"` and `"listbox"`. They are
  passed to the accessibility system unchanged.
- Internal command names such as `"file.open"` and `"glow.audit"`. Nobody
  sees them.
- File extensions and format names: `.docx`, `EPUB`, `PDF`.

### Translation roles and responsibilities

QUILL uses four roles, following NV Access community practice:

| Role | Responsibilities |
|------|----------------|
| **Translator** | Translate strings from English into the target language. |
| **Proofreader** | Review translations for accuracy, tone, and natural language flow. |
| **Language Coordinator** | Own quality for one language; approve or request changes from translators and proofreaders. |
| **Translation Coordinator** | Oversee the whole translation project, manage Crowdin, coordinate string freeze, credit contributors. |

To become a translator or proofreader, open a GitHub issue with the label
`translation` and say which language you would like to work on.

### Speech string guidelines

Strings meant for a screen reader are marked `# SPEECH:` in the source code.
When you translate them:

- **Put spoken clarity before literal accuracy.** A string that sounds right
  read aloud matters more than one that is grammatically perfect but awkward
  to hear.
- **Match the rhythm.** Keep short speech strings short. People hear these
  dozens of times a session, so every extra word costs them time.
- **Keep the emphasis.** Where the English uses word order to show what
  matters most (for example, the key word comes first), try to do the same.
- **Test with a screen reader.** If you can, listen to your strings with NVDA
  or JAWS before you send them.
- **Ask if you are unsure.** Open a GitHub issue tagged `translation` and
  `speech` if you are not sure how a speech string should be adapted.

Strings are frozen before each release candidate. No new strings are added
after the freeze, and translators have a two-week window to finish their
language before the release is built.

## What you learned, and where to go next

You can now choose a feature profile and fine-tune single features, pick a
keyboard pack, change any key in the Keymap Editor, and put everything back
with a factory reset. You know the everyday preferences, how to find any
setting by typing a word or two, how to carry your settings to another
computer, how QUILL reopens your last session and starts with Windows, and
how task recipes and working modes change several settings at once. You also
met the power tools,
Quillins, QUILL on a Mac, and how to change or help translate QUILL's
language.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try "The QUILL
key" and "Make QUILL the size you need". For a longer walk-through, read
[Own the keyboard](https://www.quillforall.org/tutorials/02-own-the-keyboard.html)
on the website.

Next, Chapter 13, Keeping your work safe, shows how QUILL protects your
documents and what to do when something goes wrong.

---

- Previous: [Chapter 11: Accessibility, speech and braille](quill-guide-11-accessibility-speech-and-braille.html)
- Next: [Chapter 13: Keeping your work safe](quill-guide-13-keeping-your-work-safe.html)
- [Contents](../userguide.html)
