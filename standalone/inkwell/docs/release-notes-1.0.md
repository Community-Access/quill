# Quill Inkwell 1.0 Release Notes

Version 1.0.0 (build 2). This first public release is not yet published.

## A note on the shared runtime's licence

Installed Inkwell uses the shared QuillVille Runtime, which currently includes
PyMuPDF 1.28.2 under AGPL-3.0 through GLOW. Inkwell does not itself expose
GLOW. Release-specific source and legal review remain open; portable packages
must be checked separately.

Quill Inkwell expands abbreviations in every Windows program. Type a short
word, press space, and Inkwell types what you saved in its place: a phrase, an
email address, a signature, a paragraph, or a template with the cursor already
where you need it.

It is for anyone who types the same things again and again, and it was built
for screen reader users from the start. It is part of the QUILL family, and it
is free. Its abbreviations are the same ones QUILL's editor expands: there is
one list, shared by both.

## The short version

Inkwell runs quietly in the notification area. Type an abbreviation in your
browser, your email or a form, then a space or a punctuation mark, and it
expands. Press **Backspace** straight away if you did not want it. Nothing you
type is kept, and nothing is sent anywhere.

## Sharp at any display scaling

Quill Inkwell handles each monitor's scaling itself, so text stays sharp at 125, 150
and 200 percent and on monitors with different scaling, and windows and list
columns keep their proportions.

## What you can do with it

### Expand abbreviations anywhere you type

Inkwell works in browsers, email, chat, forms, office programs, code editors,
terminals and dialog boxes. An abbreviation can be anything you can type
without a space, such as `addr`, `sig` or `;;date`. The space or punctuation
you typed stays where it is, so `btw.` keeps its full stop.

A few common ones, such as `btw`, `imo` and `asap`, are built in, so there is
something to try straight away.

### One list with QUILL

Inkwell and QUILL read and write the same abbreviations. Add one in QUILL's
Abbreviation Manager and it works everywhere in Windows within moments. Add
one in Inkwell and QUILL's editor knows it. Neither program needs restarting.
Inside QUILL's own editor, QUILL does the expanding itself and Inkwell stays
out of the way, so a word is never expanded twice.

### Manage your list

**Abbreviations > Manage Abbreviations...** (**Ctrl+M**) lists everything.
Search it, filter it by category, and add, edit, turn on, turn off or delete
entries. The search finds words in any order. A list of ten thousand
abbreviations opens and searches as quickly as a list of ten.

**Abbreviations > New from Clipboard...** (**Ctrl+Shift+N**) is the fast way
to add one. Copy some text anywhere, press Ctrl+Shift+N, and the text is
already filled in. You only choose the abbreviation.

**Import...** and **Export...** in the manager save and load your whole list,
with every setting.

### Settings for each abbreviation

Each abbreviation decides for itself:

- whether it is on;
- whether only the exact spelling matches;
- its category;
- what expands it: a space or punctuation, a space only, punctuation only, or
  never;
- what is spoken when it expands: nothing, the abbreviation, or the text;
- whether it plays a sound;
- whether to add a space after the punctuation that expanded it.

For an abbreviation that is not case sensitive, your typing sets the case.
`btw` expands as you wrote it, `Btw` capitalises each word, and `BTW` puts it
all in capitals.

### Dates, the clipboard, and the cursor

An expansion can hold the date, the time, the day, the month, the year, your
Windows user name, or what is on the clipboard right now. `${cursor}` puts the
cursor at that spot after the text is typed. The user guide lists every one.

### Expansions that ask you something

Put a field in an expansion, such as `${field:Name}`, and Inkwell asks for it
before typing. A small form has one labelled box per field. A name used twice
is asked once and filled in both places. Escape cancels, and cancelling leaves
your abbreviation exactly as you typed it.

### Quick Insert

**Abbreviations > Quick Insert...** (**Ctrl+K**) opens a list of every
abbreviation you have turned on, with the ones you use most at the top. Type a
few letters, arrow to the one you want, and press Enter. The text is typed
into the program you were working in. Quick Insert is the only way to reach an
abbreviation set never to expand on its own. In Inkwell's window, the **Quick
Insert...** button is **Alt+I**.

### Expand on demand, and take one back

**Abbreviations > Expand the Word I Just Typed** (**Ctrl+Alt+E**) expands the
word before the cursor without waiting for a space. It works in the middle of
a word, at the end of a line, and for abbreviations set never to expand by
themselves.

If an abbreviation expands when you did not want it, press **Backspace**
straight away. Inkwell puts your abbreviation back. This works for a few
seconds, and only in the window where it expanded.

### Keys that work from any program

You can choose up to four keys that work in every program: one to show or hide
Inkwell's window, one for Quick Insert, one to expand the word you just typed,
and one to start and stop Dictate Anywhere. None of them exists until you
choose it, because a key like that is taken away from every other program. In
the File menu:

- **Show and Hide Key...** (**Ctrl+Alt+Shift+H**)
- **Quick Insert Key...** (**Ctrl+Alt+Shift+K**)
- **Expand Word Key...** (**Ctrl+Alt+Shift+E**)
- **Dictate Anywhere Key...** (**Ctrl+Alt+Shift+D**)

Type the key you want and press Enter. Inkwell says the key back. If another
QuillVille app or another program already uses it, Inkwell says so and your
old choice stays.

### Dictate Anywhere

Dictate Anywhere lets you talk instead of type, in any program. Choose its key
first, then put the cursor where the words should go, press your key and
speak. Each phrase is typed when you pause. Press the key again, or say "stop
dictation", to stop. In Inkwell's window, **Dictation > Dictate Anywhere**
(**Ctrl+D**) does the same.

It uses the same words you taught QUILL in My Words and Phrases, and the same
voice commands as QUILL and QUILL Lite. Say "scratch that" to erase the phrase
just typed. Say QUILL before a command, as in "QUILL scratch that", and it is
never typed. You can spell an address across pauses, insert snippets,
abbreviations and clips by voice, and correct the words dictation typed, with
commands such as "correct that" and "replace Tuesday with Wednesday".

If the focus moves while you dictate, Inkwell pauses and holds your words
instead of typing them in the wrong place. Then choose **Dictation > Resume**
(**Ctrl+R**), **Resume in This Field** (**Ctrl+Shift+R**) or **Discard Held
Words** (**Ctrl+Shift+D**).

Change engines and other choices in **Dictation > Dictation Settings...**
(**Ctrl+Alt+D**), the same window QUILL uses. Your dictation settings can be
shared with QUILL, QUILL Lite and QUILL Transcribe.

When QUILL Transcribe is running, pressing your Dictate Anywhere key passes
the work to it. Only one of the two dictates at a time.

### Everything else

- **Options > Preferences...** (**Ctrl+,**) has **App Sounds Play On...**, to
  choose where Inkwell's own sounds play. **Alt+Shift+M** turns those sounds
  off and on.
- **Help > Find a Setting or Command** (**Ctrl+Alt+Shift+S**) searches every
  menu at once. Type part of a name and press Enter on the row you want.
- **Help > What's New** (**Ctrl+Shift+F1**) opens Inkwell's changelog in your
  browser, on the same key as every other QuillVille app.
- The **QuillVille** menu opens the other apps in the family. For example,
  press **Alt+Q**, then R, to open Quill Radio. If an app is not installed,
  Inkwell offers to download it, and nothing downloads until you say yes.

## Getting it

There are two downloads. Choose one.

- **Quill-Inkwell-Setup-Shared-1.0.0.exe**, the installer. It installs the
  shared QuillVille runtime if your computer does not have it yet, then
  Inkwell, with a Start menu entry and an uninstaller. It does not need
  administrator rights.
- **Quill-Inkwell-Portable-1.0.0.zip**, the portable copy. Unpack it anywhere,
  such as a USB stick. It keeps your abbreviations and settings in its own
  `data` folder beside the program. A portable QUILL in the same place shares
  them, and nothing is left on the computer when you take the stick away.

Inkwell runs on 64-bit Windows 10 and Windows 11. Nothing downloads the first
time you use it.

**Options > Start Quill Inkwell with Windows** starts it hidden in the
notification area when you sign in, which is how most people run it. Closing
the window keeps expansion running. Turn off **Options > Close button keeps
expanding** if you want the close button to exit.

**For Dictate Anywhere, there is one thing to know.** To keep Inkwell small,
its downloads do not include the built-in speech models, Moonshine and
Whisper, or the speech part that runs them. Downloaded models, OpenAI and the
speech providers need that part too. On a computer with only Inkwell, you have
two choices:

1. Choose **Windows speech recognition** in Dictation Settings. It needs
   nothing extra, but you say the punctuation yourself.
2. Install QUILL Transcribe, which carries the built-in models. While it is
   running, your Dictate Anywhere key uses it.

## Essential keys

| What | Keys |
| --- | --- |
| Manage abbreviations | **Ctrl+M** |
| Quick Insert | **Ctrl+K** |
| New abbreviation from the clipboard | **Ctrl+Shift+N** |
| Expand the word I just typed | **Ctrl+Alt+E** |
| Turn expansion on or off | **Ctrl+Shift+E** |
| Take back the expansion that just fired | **Backspace**, straight away |
| Minimize to the tray | **Ctrl+W** |
| Choose your show and hide key | **Ctrl+Alt+Shift+H** |
| Choose your Quick Insert key | **Ctrl+Alt+Shift+K** |
| Choose your Expand Word key | **Ctrl+Alt+Shift+E** |
| Choose your Dictate Anywhere key | **Ctrl+Alt+Shift+D** |
| Dictate Anywhere, from Inkwell's window | **Ctrl+D** |
| Dictation Settings | **Ctrl+Alt+D** |
| Turn Inkwell's sounds off or on | **Alt+Shift+M** |
| Find a setting or command | **Ctrl+Alt+Shift+S** |
| Get help from support | **Ctrl+Alt+F2** |

Every dialog works the same way: Escape cancels, Enter presses the default
button, and every control has a name your screen reader reads. Press **F1** on
any window or control to hear what it is for.

## Privacy

Inkwell has to notice what you type to recognise an abbreviation. This is
exactly what that means.

- It holds at most 64 characters at a time, in memory only.
- Nothing you type is saved, logged or sent anywhere. Expansion has no network
  code at all.
- That memory is cleared after every expansion, on Escape, on arrow and other
  movement keys, on any Ctrl or Alt combination, when you switch windows, and
  when expansion is off.
- It never decides anything from what you typed. Where to expand is decided
  only from which window is in front.
- It never expands in password managers, the Windows sign-in and lock screens,
  the Windows credential prompt, or the administrator permission prompt. You
  can add programs of your own with **Options > Excluded Applications...**.
- An ordinary expansion never touches your clipboard. The clipboard is read
  only for an expansion that asks for it, and is never stored.
- **Ctrl+Shift+E** stops it. Safe Mode never starts it.

Dictate Anywhere treats your speech as the editors do. It stays on your
computer with Windows speech recognition and the built-in or downloaded
models. It goes to a company only if you choose OpenAI or a speech provider
yourself and say yes when asked, and No is the default. Nothing you say is
recorded or kept.

## Known limits

- **Programs running as administrator.** Windows does not let a normal program
  see what you type there, so nothing expands and dictation will not type
  there. Inkwell tells you the first time. To use it there, start Inkwell as
  administrator too.
- **Some programs drop fast typing.** If text arrives scrambled or cut short
  in one program, turn on **Options > Insert by pasting**. Inkwell then pastes
  the text and puts your clipboard back afterwards. The user guide explains
  how to do this for one program only.
- **Plain text only.** An expansion is typed as plain text. Formatted text is
  not supported yet.
- **One list for every program.** You cannot yet make an abbreviation that
  works only in one program.
- **Dictate Anywhere cannot read the other program's text.** Commands such as
  "select", "go to", "copy all" and correcting a word by name work only in
  QUILL's own documents. Corrections that retype words are refused in Word and
  Outlook; "scratch that" and the delete commands still work there.
- **Spanish dictation takes English commands.** Say "QUILL scratch that" in
  Spanish dictation too.
- **Windows only.** There is no Mac version.

## Not done yet

We would rather tell you what is unfinished than have you find out.

- **Testing in named programs is not finished.** Inkwell is meant to work
  wherever you can type. A recorded round of testing in particular programs,
  such as Notepad, Edge, Chrome, Firefox, Word and Outlook, with NVDA, JAWS and
  Narrator, is still to be done. If something does not expand where you
  expect, please tell us where.
- **More commands for other programs are planned.** Snippets, spelling, grammar
  review and changing text you have selected in another program are not in
  1.0.
- **Abbreviations from Quillins.** QUILL's editor expands abbreviations that
  Quillins add. Inkwell does not yet.
- **An optional companion for the Clipman clipboard manager** is planned. It
  will never be required.

Inkwell keeps no clipboard history and has no macros or scripting. That is on
purpose, not unfinished.

## Your version, and updates

**Help > About Quill Inkwell** says **1.0.0 (build 2)**. A fix that comes out
without a new version number is a newer build. **Help > Check for Updates...**
offers it, and only looks when you ask.

## Getting help

The Quill Inkwell User Guide explains everything here in full, including a
troubleshooting section for when nothing expands.

Support is run by Community Access. Write to
**support@community-access.org**, or use **Help > Get Help from Support...**
(**Ctrl+Alt+F2**). It writes the message in your own mail program, with
Inkwell's version filled in, and nothing is sent until you send it. A person
reads every message.
