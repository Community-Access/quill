# Chapter 2: Finding your way around

This chapter is a walk around QUILL. You will learn how to get help on whatever
you are on, how to run any command by name, how the QUILL key opens up the rest
of QUILL, and what lives where in the window and the menus. Read it once from
top to bottom, then come back to it whenever you wonder where something is.

## Getting around QUILL

QUILL is built so you never have to memorise an action to reach it. Three things
carry most of the load: `F1` for help on what you are on, the Command Palette
for running anything by name, and the QUILL key for the bigger features.

### Help on the focused control (F1)

Press `F1` on anything that can take focus, whether that is a field in a dialog,
a button, a menu item or the editor itself, and a small help window opens. It
tells you what the control does and which keys work there. All of the text sits
in one read-only field, so your screen reader reads the whole thing as soon as
the window opens.

The help keys are:

- `F1` help on the focused control.
- `Ctrl+Shift+F1` open the full User Guide.
- `Ctrl+Alt+Shift+F1` open **What Can I Say Here?**, ideas for the document you
  have open.
- `Ctrl+F1` the Key Cheatsheet, a list of shortcuts.
- `Shift+F1` About QUILL.

Chapter 15, Help, updates and support, covers context-sensitive help in full.

F1 works the same way in every QuillVille app: Radio, Cast, the Media Player,
Audio Studio, Inkwell, Weather, the Converter and Beacon. It answers two
questions at once. First it says what the *window* you are in is for, in a
sentence or two written for that window. Then it describes the *control* under
your cursor: what it wants, what format it expects, what its default is and what
changing it affects. A field that asks for a number of seconds says so, and says
which number it starts at.

Some controls already explain themselves by name, such as "Reload the
highlighted source from the internet". For those, F1 gives you the name plus a
line on how to work that kind of control ("A list: Up and Down move between
rows, Enter acts on the row, and Shift+F10 lists everything else you can do to
it"). Nothing answers F1 with silence.

If you would rather read it all in one place, every help sentence in the family
is collected in [the F1 help reference](../../f1-help-reference.md). The default
keyboard shortcuts have a companion document, [the keyboard
reference](../../keyboard-reference.md). Both are made from the app itself, so they
always match what QUILL really does.

### The Command Palette (Ctrl+Shift+P)

`Ctrl+Shift+P` opens the Command Palette, a list of every command in QUILL that
you can search. Type any part of a command's name to narrow the list, then press
Enter to run it. It is the quickest way to any action when you do not know its
key or where it lives in the menus. Searching for `guide`, `spell`, `compare` or
`glow` is good practice. You can also open it from
**Tools > Command Palette...**.

Your search can be looser than the exact name:

- Words can come in any order. `url open` and `open url` both find
  **Open From URL...**.
- A shortcut works as a search. `ctrl+o` finds Open.
- Everyday words are understood. `settings` finds **Preferences...**, and `quit`
  finds **Exit**.

As you arrow through the results, QUILL says each command's shortcut along with
its name. Before long you will find you reach for the key and not the palette.

**Everything in the menus is in the palette.** That includes the rows that
change as you work: your recent files, your open documents, and the lists of
templates, sound packs and voices. Each one is named by the menus it sits in,
so a recent file is listed under File and Open Recent, with its number and
name. Typing the name of
anything you can see in a menu finds it. If it is dimmed in the menu right now,
the palette tells you so rather than doing nothing.

Every on/off command in the palette says which way it is set right now, for
example **Toggle Soft Wrap (currently On)** and
**Toggle Dark Mode (currently Off)**. The same goes for find wrap, the tab
control, persistent undo, spell check as you type, word prediction, overwrite
mode, extend-selection mode, tab insert mode, abbreviation expansion and more. A
menu can show a check mark, but a list in the palette cannot, so the state goes
in the name. You never have to flip a switch just to find out which way it was.

When a command cannot run right now, the palette tells you why. A command
switched off by a safety update reads as "(unavailable: Turned off by a safety
update: ...)", and trying to run it says the reason again.

The palette learns from you, too. The commands you use most rise towards the top
of the list.

#### Palette search modes

Start your search with one of these characters to change how the palette looks:

- Normal search, or `>`, searches all commands.
- `:` searches command IDs.
- `?` favours commands that have a key.
- `~` puts recently used commands first.

### Say or Type a Command (F11)

Press **F11** and type what you want, in your own words, then press Enter.
"Save", "go to line 120", "how many words", "make this bold" and "next
heading please" all work. You do not need the command's exact name, and a
small typo is forgiven. **Tools > Say or Type a Command...** opens the same
box.

It only ever does what this window can do right now. If you ask for something
that is switched off here, it says why, and it does not do the next nearest
thing instead. If it is in another app, it says which one. If it cannot work
out what you mean, it says so, and "what can I say" gets you ideas.

A few more things to know:

- **When it is not sure,** it shows a short Did You Mean list, each command with
  its key. Arrow to the one you meant and press Enter, or choose Something else
  to type it another way.
- **Anything that closes, clears or stops something asks first.** Close
  Document and Clear Bookmarks are two. Press Enter to go ahead or Escape to
  leave it.
- **Some things are never done from a sentence:** exiting, signing in,
  sending, publishing, deleting and changing settings. Ask for one and you are
  told where it is, so you can do it yourself from its menu or its key.
- **"Undo that" and "do that again"** work on what the box last did. "A lot
  bigger" does three steps at once, and "undo that" takes all three back.
- **What can I say here?** Type "what can I say", or choose **Help > What Can I
  Say Here?** (**Ctrl+Alt+Shift+F1**). You get a list of everything this window
  can do right now, by menu, with one way of saying each and its key. Press
  Enter on one to do it. "What can I say about bookmarks" shows only those.
- **F11 never starts, stops or pauses dictation.** Dictation keeps
  **Ctrl+F11**. The dictation command that used to be on F11 is now **Next
  Phrase Is a Dictation Command**, on the Dictation menu, with no key.

The matcher that understands you is free, works without an internet
connection, and keeps everything you type on your computer. The page "What you
can say in each app" (`command-catalogue.html` in the documentation folder)
lists every command it understands in QUILL, QUILL Lite and Quill Radio, with
examples.

#### When the matcher is not sure: Jev, or your own AI

The first time the matcher could use some help, QUILL asks you once what it
may do. There are three equal answers:

- **Use Jev.** Jev is TypeSafe's decision model. A request the matcher cannot
  settle is sent to it, and it picks one of this window's commands, or none.
  If this computer is signed in to QUILL's free AI, the request goes through
  Community Access's service, which holds the key, so you do not need one of
  your own. If you stored your own TypeSafe key, QUILL asks TypeSafe directly.
  When Jev cannot answer, your own AI is asked next, if you have one.
- **Use My Own AI Instead.** The request goes to the AI you chose in Choose
  Your AI (**Ctrl+4**), when it is one of your own: your ChatGPT plan, GitHub
  Copilot, Codex or your own key. It is asked one question, to pick one of
  this window's commands or none, and nothing goes to Jev. QUILL's free AI is
  never asked this question.
- **Match on This Computer Only.** Nothing is ever sent. Escape gives the same
  answer.

What is sent is the words you typed or said, the app's name and the ids of the
commands this window can do right now. Never document text, file names,
stations, places or accounts. Community Access's service keeps counts, never
what you typed. TypeSafe keep the requests they receive, and say they do not
train on them.

What you hear and what happens:

- **"Asking your AI."** while your own AI thinks. If it takes more than eight
  seconds, the matcher's answer stands.
- **Nothing runs on a guess.** Jev's pick runs only when it is clearly sure.
  Your AI's pick runs only when it agrees with the matcher's best guess and the
  command is safe. Otherwise you get the Did You Mean list, and anything that
  closes, clears or stops something still asks first.
- **One line, once, when help is not available,** because you are offline, a
  daily limit is reached or credit is spent. For example: "Jev's daily limit
  is reached, so I'm asking your AI." After that the matcher carries on by
  itself.
- **Nothing is sent in Safe Mode.**

Your answer is kept for every later request. The question's own window says
you can change it at any time, but there is no setting for it yet; that is
being fixed (issue 1819 on GitHub).

### The QUILL key

The **QUILL key** is `Ctrl+Shift+Grave`. The grave key is the back-tick key,
just above Tab. Press it, then one more key, and you reach most of QUILL's
bigger features without leaving the keyboard.

Everywhere QUILL shows one of these keys, in menus, in
**About > Keyboard Reference**, in the QUILL Key Help dialog, on the cheat sheet
and in the status bar, it writes it as `QUILL Key + <key>`: `QUILL Key + S`,
`QUILL Key + Shift+O` and so on. When you type one into the Keymap Editor you
write it as `Ctrl+Shift+Grave, <key>`. Both mean the same thing.

The QUILL key works in two ways.

1. **Prefix Mode (One-shot).** Press it once and QUILL waits a moment for your
   next key. That key runs a command, such as `G` to open a file from a
   favorite folder or `M` to
   paste rich text as Markdown, and then QUILL goes back to normal.
2. **Browse Mode (Locked).** Press the QUILL key twice in a row and QUILL locks
   **Quick Nav (Browse) mode** on. Now single letters move you through the
   document: `H` for headings, `P` for paragraphs, `S` for sentences and more.
   It stays on until you press `Esc`.

Every one of these chords can be changed in the Keymap Editor, which the next
topic covers. The full cheat sheet is one key away: `QUILL Key + ?`.

#### The QUILL key chords

These are the chords QUILL starts with.

- `QUILL Key + N` Quick Nav (browse) mode for your next move. If
  **Sticky browse mode** (the `browse_mode_sticky` setting) is on, it stays
  locked until `Esc`. Otherwise it ends when the QUILL key times out.
- `QUILL Key` pressed twice locks Quick Nav on until `Esc`, whatever that
  setting says. This is the way most people use it: the first press gets QUILL
  ready, the second locks browse mode.
- `QUILL Key + G` opens **Open From Favorite Folder...**. (Go to Anything is
  `Ctrl+Alt+Shift+A`, and the Quick Nav landmark list is `Ctrl+Shift+Z`.)
- `QUILL Key + M` pastes the rich HTML on the clipboard as Markdown at the
  cursor.
- `QUILL Key + V` opens the browser preview of the current document.
- `QUILL Key + A` opens selection actions when text is selected. With nothing
  selected, it expands an abbreviation by hand in the middle of a word.
- `QUILL Key + Shift+A` opens the abbreviation manager.
- `QUILL Key + Shift+1` to `Shift+9`, then `Shift+0`, `Shift+-` and `Shift+=`
  copy the selection to slots 1 to 12 of the Copy Tray.
- `QUILL Key + ?` shows the QUILL key cheat sheet.
- `QUILL Key + Esc` cancels the QUILL key without running anything.

A few things that once had a QUILL key chord have moved:

- Opening from, saving to and managing remote sites (FTP, SFTP, HTTPS, WebDAV,
  S3 and GitHub) have no key to start with. Find them under
  **File > Open from Remote**, or give them a key of your own. (These were
  `QUILL Key + Shift+O`, `QUILL Key + W` and `QUILL Key + Shift+M`.)
- Turning abbreviation expansion on or off is `Alt+Shift+A`.
- The Copy Tray dialog is `Ctrl+Alt+V`.
- Switching the Tab key between indenting and typing a tab character is
  `Ctrl+Alt+Shift+I`.

#### Hearing the QUILL key

When you press the QUILL key, QUILL plays a short double ping that sounds like
nothing else, so you know it is ready before any speech arrives. The sound is in
every sound pack that comes with QUILL, and you can switch it off on its own in
**Tools > Reading and Dictation > Sound Scheme...** (this used to be called
Sound Events).

#### The QUILL key on keyboards that are not US English

Only a US layout calls the grave key a backtick. On a German layout the same
key types `^`, on French it types `²`, and on many Nordic layouts it types `§`.
QUILL does not care what the key types. It looks for the key by where it sits
on the keyboard: the key just above Tab, to the left of `1`. So on any layout,
the QUILL key is Control, Shift and that key, and you never need to switch to a
US layout to use it.

On Windows, QUILL recognises the key from the keyboard's own hardware code,
which is the same on every layout.

On macOS, QUILL reads the Mac's key code, which also names a position rather
than a character. On the keyboards sold in Germany, the UK and most of Europe
(Apple calls them ISO keyboards), the key above Tab and the extra key beside
the left Shift key (`<` on a German keyboard) both count as the grave key, so
whichever of the two your Mac reports, `Control+Shift` with it is the QUILL key.
You hear the same double ping as on a US keyboard.

Use the physical **Control** key for the QUILL key on macOS, not Cmd.
`Cmd+Shift+Grave` is macOS's own shortcut for cycling windows, and QUILL never
sees it. If you would rather use Cmd, change that system shortcut first in
**System Settings > Keyboard > Keyboard Shortcuts > Mission Control**.

If the QUILL key still does nothing on your keyboard, you can move it. Open the
Keymap Editor (**Tools > Customize and Support > Keymap Editor...**,
`Ctrl+Alt+Shift+Space`), press the **Change QUILL Key...** button and type the
chord you want. Every QUILL key chord moves with it, so `QUILL Key + G` is
still `G` after your new key. Then write to support with your keyboard layout
and your Mac or PC model, so the key can be made to work for the next person.

#### Moving a QUILL key chord

1. Open the Keymap Editor, from
   **Tools > Customize and Support > Keymap Editor...** (`Ctrl+Alt+Shift+Space`).
2. Find the command you want to move.
3. Type the new chord in the form `Ctrl+Shift+Grave, X`, putting the key you
   want in place of `X`.

The Keymap Editor stores chords in that `Ctrl+Shift+Grave, X` form, and menus
and the cheat sheet show them as `QUILL Key + X`. If the chord you pick is
already in use, QUILL tells you before anything is overwritten.

## The Keyboard Manager

The Keymap Editor, also called the Keyboard Manager, is where you see and change
every key in QUILL. Open it from
**Tools > Customize and Support > Keymap Editor...** (`Ctrl+Alt+Shift+Space`), or
from the Keymap Editor entry in More Preferences (the QUILL key, then `O`). It is made to be quick
and safe to use, however you think about shortcuts.

- **Search two ways from one box.** Type part of a command's name to narrow the
  list. Or type a *shortcut*, such as `ctrl+alt+m`, `Control + Shift + K`, or
  even a QUILL key chord like `quill, s`. The editor then tells you which
  command that key belongs to, or that it is "unassigned and available". You
  never have to remember whether a key is free. Just ask.
- **Forgiving spelling.** Write the modifiers however you like: `control`,
  `ctrl` or `ctl`, in any order (`shift+ctrl+k` is the same as `ctrl+shift+k`)
  and in any case. QUILL tidies up what you type before saving it. A Mac-style
  `Cmd` stays separate from `Ctrl` and is never mixed up with it.
- **Record Keys.** Would you rather press the keys than spell them? Choose
  **Record Keys**, press the chord, and QUILL fills it in for you.
- **Clear warnings when a key is taken.** If you choose a key that another
  command already has, QUILL tells you that command's name and offers to move
  the key over, taking it off the other command. Nothing is replaced behind your
  back.
- **Diagnostics and repair.** **Run Diagnostics** checks your whole keymap. It
  reports duplicate shortcuts, keys for commands that no longer exist, bindings
  it cannot read, and any key that is "assigned but inert", meaning the editor
  cannot actually use it. For the problems it can fix, one press of **Heal**
  removes the bad entries and reapplies your keymap, so the menus and the
  shortcuts agree again.

## The Main Window

QUILL's main window is kept simple: a menu bar across the top, the editor in the
middle and a status bar along the bottom. When you have several documents open
you can also show a row of tabs, which the Windows and tabs topic, later in this
chapter, covers.

### The menu bar

The menus run across the top of the window in the order you know from Windows
and Office: File, Edit, View, Insert, Format, Navigate, Tools, AI, Window,
QuillVille and Help. There used to be a Search menu as well. Its commands now
live on the **Edit** menu: the folder searches as rows of Edit itself, and the
rest under **Edit > Search Tools**.

Every menu and every menu item can be reached from the keyboard. Press `Alt`
with the menu's underlined letter: `Alt+F` for File, `Alt+E` for Edit, `Alt+V`
for View, `Alt+T` for Tools, `Alt+W` for Window and `Alt+H` for Help.

The menus cover everything. If QUILL can do something, there is almost always a
menu item for it. The menus topic, later in this chapter, says what each one
holds.

### The editor

The editor is the heart of QUILL. It is where you write, where text taken from
other files lands, and where reports and comparison summaries open, as ordinary
documents you can read and edit like any other.

The editor handles:

- plain text writing
- Markdown-aware writing
- HTML-aware writing
- moving by the structure of the document
- selection helpers
- cleaning up text
- spelling and the thesaurus
- inserting and following links
- reviewing changes after a comparison

### The status bar

The status bar is something you can work in, not just a strip of text to read.

Press `F6` to move into it. Once you are there, you can move between its cells
and press Enter on one, and most cells open a related window. `Shift+F6` takes
you back to the editor. Depending on your layout and what you are doing, the
status bar can show:

- the current message
- line and column
- word count
- insert or overwrite mode
- tab mode (whether the Tab key indents the line or types a tab character)
- selection size
- encoding
- line endings
- spell-check state
- background tasks
- notifications
- read-aloud state
- autosave timing
- the current search term
- the file path, or that the file is unsaved

You can reorder the cells or hide some of them in
**Tools > Customize and Support > Status Bar Layout...**. **Restore Defaults**
there puts every cell back the way it started.

Open the context menu on a status cell (right-click, `Shift+F10` or the
Applications key) to **Activate** it, **Hide this item**, or open
**Status bar settings...**. On the **Notifications** cell (or the
**Background Tasks** cell) the menu also has **Clear All Notifications**, which
empties the notification list in one go without opening the dialog.

The status bar never says the same thing twice. When the title bar is set to
show the full path, QUILL hides the file path cell. The current message cell
hides itself too, whenever its text is exactly the same as another cell you can
see.

To hide or show the whole status bar, use **View > Status Bar**, described in
View and display, later in this chapter.

### Moving between regions (F6)

`F6` and `Shift+F6` move you between the main parts of the window. If you write,
check and move around entirely from the keyboard, this soon becomes second
nature.

When **Show Tab Control** is on (in the View menu) and at least one document is
open, the row of document tabs joins the `F6` cycle as **Document Tabs**, so you
can reach the tabs from the keyboard instead of skipping past them. The order is
the editor, then Document Tabs, then the preview (when you have it open beside
the editor), then the status bar. On the tab row, Left and Right Arrow move
between tabs, and Enter, Space or Tab takes you back to the editor on the
document you chose.

### The Tab key, indent or tab character

Out of the box, the **Tab** key indents. It adds one level of indentation at the
start of the current line, or of every line you have selected, and **Shift+Tab**
takes one level away. On a Markdown list item, Tab and Shift+Tab move the item
in and out a level. QUILL speaks each of these, so you hear that the line moved
even though the cursor stays where it was.

When you indent with Tab, or outdent with Shift+Tab, QUILL says how deep the
line now sits, for example "4 spaces", "8 spaces" or "1 tab". If you would
rather just hear "Indented lines", turn off
**Announce indentation depth on Tab** in Preferences, under **Accessibility**.

Two settings decide what an indent is made of, both in Preferences:

- **Indent size** is the number of spaces per indent level, from 1 to 8. The
  default is 4.
- **Indent with tabs** makes QUILL insert tab characters instead of spaces.

Whichever you choose, the spoken depth follows it.

If you would rather Tab typed a real tab character at the cursor, the way it
does in a plain text editor, switch **Tab Mode** with `Ctrl+Alt+Shift+I`, or
with **Format > Tab Key Inserts Tab Character**, which is checked while the mode
is on. QUILL says the new mode when you switch, and the **Tab Mode** cell in the
status bar shows **Indent** or **Tab char**. Even while Tab types a tab
character, Shift+Tab still outdents, so you can take back a stray indent without
leaving the mode. Tab Mode lasts until you close QUILL.

## The menus

Here is what each menu holds and which chapter tells you more. They are listed
in the order they sit on the menu bar.

### File

File is where documents begin and end: new, open, save and save as, recent files
and favourite folders, opening from a web address or over SSH and remote sites,
snapshots, publishing, and importing and exporting other formats. Chapter 3,
Opening, saving and converting files, covers all of it.

### Edit

Edit holds the everyday editing commands, along with selection tools, the Copy
Tray, and what used to be the Search menu: **Edit > Search in Files...**,
**Edit > Replace Across Files...** and the **Edit > Search Tools** submenu.
Chapter 4, Writing and editing, covers editing and selection, and Chapter 6,
Moving around and finding things, covers searching.

### View

View changes how your document is shown without changing what is in it: soft
wrap, the tab row, the status bar, text size, previews and Reveal Codes. It is
covered later in this chapter, under View and display.

### Insert

Insert puts things into your document: headings, lists, the date and time, links
and special characters. Chapter 4, Writing and editing, covers it.

### Format

Format holds font, size, alignment, colour and paragraph settings, along with
changing case, working on lines, sorting, whitespace, HTML and Markdown, and the
document's language. Chapter 5, Formatting, structure and markup, covers it.

### Navigate

Navigate gathers the ways to move around a document: go to line, go to heading,
go to an entry in a notebook, the Heading Organizer, the Outline Navigator, back
and forward through places you have been, and next and previous by structure. It
also has bookmarks, folding and sticky notes. When you need to get around a long
document, start here. Chapter 6, Moving around and finding things, covers it.

### Tools

Tools is QUILL's workshop, for jobs that are more than plain editing. The
Command Palette is here, along with spelling and writing tools (Chapter 7,
Spelling and words), reading, comparison and inspection tools (Chapter 8,
Reading, reviewing and listening), speech and dictation (Chapter 9, Dictation
and transcription), and braille and accessibility (Chapter 11, Accessibility,
speech and braille). **Tools > Customize and Support** is where you make QUILL
your own (Chapter 12, Making QUILL yours), and Story Studio, the Vault and Git
are covered in Chapter 14, Projects, notes and the QuillVille family.

### AI

AI holds the optional assistant: proofreading, changing the selected text,
translation, reading aloud, transcribing audio and more. Nothing in it runs
unless you choose it. Chapter 10, AI, when you want it, covers it.

### Window

Window lists your open documents and lets you move between them, open a new tab,
close the others, or send QUILL to the system tray. It is covered later in this
chapter, under Windows and tabs.

### QuillVille

QuillVille (`Alt+Q`) opens the other apps in the QUILL family. Each row has
its own letter, so `Alt+Q` and then one letter opens an app with nothing held
down, and each has a key of its own:

- **Open Quill Radio** (`Ctrl+Alt+Shift+F7`)
- **Open Quill Weather** (`Ctrl+Alt+Shift+F8`)
- **Open Quill Converter** (`Ctrl+Alt+Shift+F9`), which changes audio and
  video files from one format to another
- **Open Quill Inkwell** (`Ctrl+Alt+Shift+F10`)

The menu lists only the apps that have been released, and the keys are handed
out in the order the menu lists them, starting at `Ctrl+Alt+Shift+F7`. Quill
Cast and Audio Studio are not released yet, so they are not on this menu; when
one is, it joins the list and the keys of the rows below it move down by one.
The menu always shows each row's current key beside it, so press **Alt+Q** and
listen rather than relying on memory. (Once Quill Cast is running, its own
show-and-hide key, `Ctrl+Alt+Shift+F12`, brings it forward from any program.)

- **Open Quill Radio** (`Alt+Q`, `R`, or `Ctrl+Alt+Shift+F7`)
- **Open Quill Weather** (`Alt+Q`, `W`, or `Ctrl+Alt+Shift+F8`)
- **Open Quill Converter** (`Alt+Q`, `V`, or `Ctrl+Alt+Shift+F9`), which
  changes audio and video files from one format to another
- **Open Quill Inkwell** (`Alt+Q`, `I`, or `Ctrl+Alt+Shift+F10`), which
  expands your abbreviations in every program
- **Open QUILL Transcribe** (`Alt+Q`, `T`, or `Ctrl+Alt+Shift+F11`), which
  types what you say into any program. It is released on 1 November 2026.

For example, to start dictating into an email, press `Ctrl+Alt+Shift+F11`.
QUILL Transcribe opens (or comes to the front if it is already running), and
its own start and stop key, Alt+Shift+Backslash unless you changed it, then
works in your email program. Inside QUILL you do not need it: `Ctrl+F11`
dictates into the document you are in.

Those five are every row this menu shows. Quill Cast and Audio Studio join it
when they are released; Cast will keep `Ctrl+Alt+Shift+F12`, the key that
shows and hides it from any program. Every row is a command you can give a
different key in **Tools > Customize and Support > Keymap Editor...**
(`Ctrl+Alt+Shift+Space`): search for
"QuillVille: Open".

If an app is not on your computer yet, QUILL offers to download it for you.
Nothing is downloaded until you say yes. QUILL Transcribe has nothing to
download until 1 November 2026; before then QUILL says it could not fetch it
and offers to open the download page instead. Chapter 14, Projects, notes and the QuillVille family, says more.

### Help

Help has help on the control you are on, **What Can I Say Here?**, the tutorials,
the User Guide, the keyboard reference, **Personalise QUILL...**, feature
profiles, checking for updates and ways to get support. Chapter 15, Help,
updates and support, covers it.

## Windows and tabs

QUILL lets you have many documents open at once. Each one gets its own tab, and
QUILL opens things it makes for you as tabs too. The welcome guide, the keyboard
reference and a comparison summary all open as ordinary tabs, right beside the
work that produced them.

### Tabs and document switching

- `Ctrl+Tab` and `Ctrl+Shift+Tab` move to the next and previous document.
- `Ctrl+W` closes the document you are in.
- The context menu on a tab lets you close that tab, close the other tabs, or
  close the tabs to its right.
- The same menu can show a saved document in File Explorer.

To see the row of tabs, turn on **Show Tab Control** in the View menu
(`QUILL Key + Shift+T`).

### The Window menu

The **Window** menu is small but handy.

- **New Tab** (`Ctrl+T`) opens a new, empty document tab.
- **Next Document** (`Ctrl+Tab`, also `Ctrl+F6`; on macOS `Cmd+Shift+]`) moves
  to the next open document.
- **Previous Document** (`Ctrl+Shift+Tab`, also `Ctrl+Shift+F6`; on macOS
  `Cmd+Shift+[`) moves to the previous open document. macOS keeps `Cmd+Tab` for
  its own App Switcher, so on a Mac QUILL uses the same tab keys as Safari and
  Xcode.
- **Close Other Documents** (`Ctrl+Shift+F4`) closes every document except the
  one you are in.
- **Say Windows Open** (`Ctrl+Shift+Space`) tells you how many documents
  are open: "3 documents open". Press it twice, quickly, to hear their names in
  tab order, with the one you are in marked "(current)". Chapter 6 has more.
- **Send to System Tray** (`QUILL Key + T`) tucks QUILL into the notification
  area without closing it.
- After those come your open documents, numbered, such as
  **1: notes.txt (Alt+1) (active)** and **2: other.md (Alt+2)**. Press `Alt+W`
  to open the Window menu, then the number, to go straight to that document. The
  one you are in is marked active. The list keeps up as you open and close
  files, and an untitled document takes its new name the moment you save it.

You can also jump straight to a document by its position without opening the
menu. **Go to Document 1** to **Go to Document 10** are `Alt+1` to `Alt+9`, and
`Alt+0` for the tenth. If no document is open in that position, QUILL says so
and leaves you where you are. You can change these keys in the Keymap Editor,
like any other.

> **QUILLBee's shortcut:** Juggling notes, extracted files and previews? Keep
> your main document first in the row, and `Alt+1` will always bring you home.

## View and display

The **View** menu changes how QUILL shows your document on screen. Nothing on it
changes what is in the document.

- **Toggle Soft Wrap** (`Alt+Z`) wraps long lines to fit the window without
  changing the file.
- **Show Tab Control** shows or hides the row of document tabs.
- **Status Bar** (`Alt+Shift+B`) shows or hides the **whole** status bar. It is
  the same switch on the same key as in Notepad and QUILL Lite. It is a
  different thing from choosing which cells the bar carries (right-click the
  bar, or **Tools > Customize and Support > Status Bar Layout...**): a bar with every
  cell hidden still takes up a row of the window. The setting is
  **`show_status_bar`** (**Show status bar**). It is on to start with, and QUILL
  remembers your choice. QUILL says which way it went, because your screen
  reader will not tell you a bar has left the window.
- **Increase Text Size** (`Ctrl+=`), **Decrease Text Size** (`Ctrl+-`) and
  **Reset Text Size** (`Ctrl+0`) change how big the editor's text is without
  leaving the document. They are the same three keys as in Notepad and QUILL
  Lite. Chapter 11, Accessibility, speech and braille, has more on the size and
  face of the text.
- **Preview...** (`Alt+Shift+V`), **Preview Side by Side**, **Focus Preview**
  (`Alt+F6`) and **Browser Preview...** (`QUILL Key + V`) show your document
  rendered, the way a reader would see it.
- **Auto Side-by-Side Preview** opens a live preview beside the editor
  automatically.
- **Announce Headings** and **Announce Lists** choose whether QUILL tells you
  when you move onto a heading or a list.
- **What Is This Document?**, **What Changed?** and
  **Undo and Say What Changed** tell you the things a screen reader cannot work
  out for itself.
- **Show Entries Panel** and **Reveal Codes** (`Alt+F3`) show more of the
  document's structure and formatting.

Two switches that used to be on this menu are now in Preferences (`Ctrl+,`):
**Wrap Find Searches** decides whether Find carries on from the top when it
reaches the end, and **Start With No Document Open** makes QUILL open to an
empty workspace instead of a starter document.

Other settings that once lived here are in Preferences too, where they are saved
in one place: the theme and dark mode, system tray mode, how the title bar shows
the path, how the title marks unsaved changes, persistent undo, spell check as
you type, and word prediction as you type. You reach them from
**Tools > Customize and Support > Preferences...**.

### Live preview while you type

Open the side-by-side preview with **Preview Side by Side**, or turn on Auto
Side-by-Side Preview. `Alt+F6` jumps straight into it, and while it is open it
joins the `F6` cycle too.

As you edit, the preview updates quietly in place. The new content is swapped in
without reloading the page, so your braille display and screen reader are not
interrupted, nothing is read again from the top, and you keep your place. This
is the live preview to use if you read with a screen reader or braille.

The **Browser Preview** in your web browser can also follow your edits. A real
browser has to reload the whole page to do that, so QUILL refreshes it only when
you pause typing, not on every key. Each time, it puts you back at the section
you are editing, or where you had scrolled to, instead of at the top.

### Jump from the preview back to the editor

Reading the side preview, and want to change what you just heard? Go to a block
(a heading, paragraph, list item, quote, table or code block) and open its
context menu with the **Applications key**, **Shift+F10** or a right-click.
Choose **Go to this location in the editor**. The cursor moves to that block in
your document, focus goes with it, and QUILL tells you where you landed.

Pressing **Enter** on a block does the same, when your screen reader passes the
key through. The context menu is the dependable way, though: in browse mode
there is no way to ask where the virtual cursor is, but a context menu always
belongs to the exact spot you are on. The jump is offered when the preview
matches your document word for word. A preview that expands Vault links does not
offer it, because the places would no longer line up.

## What you learned, and where to go next

You know three ways to reach anything in QUILL: `F1` for help on what you are
on, the Command Palette (`Ctrl+Shift+P`) for any command by name, and the QUILL
key (`Ctrl+Shift+Grave`) for the bigger features and Quick Nav. You have been
round the window with `F6`, heard what each menu holds, moved between documents
and tabs, and seen how View changes what is on screen.

For a guided go at the same ground, open **Help > Tutorials...**
(`Ctrl+Alt+F1`). In the Your first hour track, "Do anything by name", "The QUILL
key" and "Getting unstuck" match this chapter, and "Make QUILL the size you
need", in Living with it, covers text size. On the website, [Own the
keyboard](https://www.quillforall.org/tutorials/02-own-the-keyboard.html) goes
deeper into keys and the Keymap Editor.

Next, Chapter 3, Opening, saving and converting files, shows you how to bring
documents in and send them out in the format you need.

---

- Previous: [Chapter 1: Your first session](quill-guide-01-your-first-session.html)
- Next: [Chapter 3: Opening, saving and converting files](quill-guide-03-opening-saving-and-converting-files.html)
- [Contents](../userguide.html)
