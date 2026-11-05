# Chapter 11: Making QUILL Lite yours

QUILL Lite comes ready to use, and you never have to change a thing. But it is
yours, and this chapter shows you how to shape it. You will find every
everyday setting in one window, make QUILL Lite as small as Notepad or as full
as you like with a profile, and change the key for any command. Nothing here
is one-way, and you can always put things back.

## Settings

All of QUILL Lite's everyday settings are in one window.

### Opening Preferences

Press **Ctrl+,** to open **Tools > Preferences**. It is one long column of
controls, with **OK** and **Cancel** at the bottom.

- **Tab** moves down the column, and **Shift+Tab** moves back up.
- **F1** on any control tells you what that one control does.
- **Nothing you change is saved until you press OK.** So Escape is always safe.

### Finding a setting

A **Find a setting** box at the top searches the
names of the settings, what your screen reader calls them, and their help text.

1. Type a word, such as "spelling".
2. Press **Down** to reach Matching settings.
3. Arrow to the one you want and press **Enter**. Focus moves to that control.

**Ctrl+F** takes you back to the search box. In the search, Enter moves you to a
setting; it does not save. Escape clears what you typed first, and closes the
window if the box is already empty. Searching never changes a setting for you,
and OK and Cancel work just as before.

### Choosing the default document folder

**Default document folder** chooses where Open and Save As start when you are
working in a new document. Leave it blank to use your Windows **Documents**
folder, or type a path or use **Choose default folder...** to pick another
existing folder. A document you already saved continues to use its own folder.

### If your settings could not be saved

Sometimes Windows will not let QUILL Lite save your settings, for example if the
disk is full. If that happens:

- Your new settings still work until you close QUILL Lite.
- QUILL Lite tells you, and the warning stays in the status bar's Message cell.
  Press **F6** to read it again.
- Free up some space, or fix access to the settings folder, then open
  Preferences again. QUILL Lite tries again by itself. You do not need to change
  anything or press OK.

When it works, the warning goes away. QUILL Lite also tries to save whenever you
change a setting and when you exit normally. This warning is only about your
settings. It does not mean your document was not saved.

### Every setting, in order

Here is each control in the order you meet it.

#### Profile

**Profile** is the same four-choice box that Customize Features has, with the
same description underneath. See [Making QUILL Lite smaller (or
larger)](#making-quill-lite-smaller-or-larger), later in this chapter.

#### New documents are

**New documents are:** **Plain text** or **Rich text**. This only decides what
**Ctrl+N** makes. **New Plain Text Document** (**Ctrl+Alt+N**) and **New Rich
Text Document** (**Alt+Shift+T**) always make what their names say.

If you choose the **Notepad** or **WordPad** profile, this control changes to
match, right in front of you. So you can see what the profile chose and change
it before you press OK.

#### Theme

**Theme:** **Dark** or **Follow the system**. **Follow the system is the
default.** It uses the colours you have already chosen in Windows, so if you
have a high-contrast or dark setting there, QUILL Lite follows it. Choose
**Dark** if you want QUILL Lite dark whatever Windows is set to.

The theme only changes the screen. The colours never go into your files, so
nobody you send a document to will get grey text.

You can also switch dark mode straight from the View menu with **Alt+Shift+D**.
It says "Dark mode on" or "Dark mode off".

If you chose dark in an earlier version, you keep dark.

#### Startup and recovery

**Reopen the documents I had open last time** is on. Turn it off and QUILL Lite
starts with only what you open yourself. This is not the same as recovering
unsaved work after a crash, which happens either way.

**Offer untitled unsaved work back after a crash** is on. An untitled document
has never been saved to a file, so this copy is the only one there is. Turn it
off if you use QUILL Lite as a scratchpad and would rather it forgot.

**Start with a blank document** is on, just like Notepad and WordPad. If you
always open an existing file, turn it off, so you are not handed an empty
Untitled to close every time. Files you open by double-clicking, last session's
documents and recovered work all still appear. QUILL has the same setting under
**General**.

#### Sharing with QUILL

**Share QUILL's abbreviation library** is off. Turn it on and QUILL Lite uses
QUILL for All's list of short forms instead of its own, so a short form you add
in either program works in both. It does nothing if QUILL is not installed.

**Share QUILL's dictionary of taught words** is off. It works the same way for
spelling: a word you teach in either editor is known to both.

#### Clipboard and updates

**Keep everything I copy in the clip library** is off. Turn it on and every
Ctrl+C is saved in the clip library by itself, not just the ones you keep with
**Ctrl+Alt+M**. It is handy, but the library will fill up on its own.

**Look for updates when QUILL Lite starts** is on. It looks once a day and only
speaks up if there is something new. **Ctrl+Alt+U** checks whenever you like.

#### Spelling and autocorrect

**Check spelling as I type** is on. It is the same switch as **Tools > Spelling >
Check While Typing** (**Ctrl+Alt+F7**), which is quicker to reach while you are
writing.

**Curl quotes as I type** is off. It turns a straight quote into a matching
curly one.

**Turn two hyphens into an em dash** is off. When you type the second hyphen of
`--`, both become one long dash.

Both of these also need **Autocorrect while typing** switched on in Customize
Features. Neither ever runs in a plain text, source code or settings document.

**Correct common misspellings as I type** is off. It changes `teh` to `the`
when you type the space after it. It also needs **Autocorrect while typing** in
Customize Features, and unlike the two above it does run in plain text, because
a misspelling is as wrong in a `.txt` file as anywhere. It never runs in source
code or settings files. *Correcting misspellings as you type*, below, has the
details.

**Continue lists in plain text** is off. With it on, **Enter** in a plain text
list starts the next item, as it always does in Markdown. Chapter 6 has the
details, under *Pressing Enter in a list*.

#### What you hear

**When a command does something, give me:** **a sound**, **the action spoken**,
**both**, or **nothing**. This is how QUILL Lite tells you that a cut, copy,
paste, undo or new selection worked. A sound is the default. Spoken words are
easier while you are still learning the sounds.

Two things happen whatever you choose. If your sound pack has no sound for a
command, QUILL Lite speaks instead of staying silent. And if a command could not
do what you asked, QUILL Lite **always says so in words**.

**When a search misses:** has the same four choices, set separately. You often
press F3 several times in a row, and hearing "Not found" spoken each time gets
tiring fast, so many people pick the sound here. The words are always in the
status bar too.

**Say a heading's level:** **before the text** or **after the text**. Before
means QUILL Lite says it all in one go, like "Heading 2, Installing". You will
still hear it after a jump, such as Ctrl+Home or landing on a search result.
After means your screen reader reads the line and QUILL Lite adds the level
afterwards, which is quieter when you are reading line by line.

#### Searching and wrapping

**Searching carries on from the other end** is on. When Find Next reaches the
end, it starts again at the top and tells you so. Turn it off and it stops and
tells you which end you are at. Then you know the word is not missing, you are
just at the bottom.

**Wrap long lines to the window** is on. Turn it off and long lines run past the
right edge of the window. **Alt+Z** on the View menu is the same switch.

#### Timing

**Shortest gap between spoken messages (ms):** from 0 to 2000. The default is 0,
which says everything as it happens. A bigger number skips anything QUILL Lite
would say too soon after the last thing. That helps if holding a key down makes
your screen reader talk too much. You do not lose anything: every message still
goes to the status bar, and **F6** reads it back.

**Copy unsaved work aside every (seconds):** from 15 to 600, and 30 by default.
This is how often a changed document is copied to the recovery folder. The copy
is kept beside your file, never on top of it, and it is removed as soon as you
save.

#### Editor font

**Editor font:** a read-only box showing the font and size, and a **Change
Font...** button that opens the font chooser. When you pick a font, the box
updates and QUILL Lite says the new font out loud. The same chooser is on
**Ctrl+Alt+F** (**Format > Editor Font**), where Notepad has always kept it. It
stays on the Format menu even if you switch rich text off.

#### AI help

**Use QUILL's free AI help** is off. This one works straight away, without
waiting for OK. Checking it shows you the whole agreement right then and saves
your answer. Unchecking it takes your agreement back right then. If you decline
the agreement, the check mark goes away again and QUILL Lite tells you so. See
[Chapter 10, AI help](lite-guide-10-ai-help.html#chapter-10-ai-help).

#### When another program changes the file

**Watch the open file for external changes** is on. **Reload automatically
when you have no unsaved edits** is off. **Ask before discarding unsaved edits
on a conflict** is on. **External-change debounce (milliseconds)** is 750.
**Forget remembered file-change answers** takes back every "Do not ask me again"
answer when you press OK. What each one does is in [When another program
changes your file](lite-guide-03-opening-saving-and-printing.html#when-another-program-changes-your-file), in Chapter 3.

### What is not in here, and where it is instead

Some switches are on a key instead, because you change them while you are
working:

| Not in Preferences | Where it is |
|---|---|
| Dark mode | **View > Dark Mode** (**Alt+Shift+D**) |
| Word wrap | **View > Word Wrap** (**Alt+Z**) |
| Announce Headings, Announce Lists | **View** (**Ctrl+Alt+F3**, **Ctrl+Alt+F5**) |
| Overwrite mode, Tab key behaviour, the status bar | **View** |
| App sounds on or off | **Tools > App Sounds** (**Alt+Shift+M**) |
| Which sound each event makes | **Tools > Sound Scheme** (**Ctrl+Alt+Shift+O**) |
| Which of the 24 areas exist at all | **Tools > Customize Features** (**Ctrl+Alt+F10**) |
| What any key does | **Tools > Keyboard Manager** (**Ctrl+Alt+Shift+Space**) |
| The twelve spelling announcement settings | **Tools > Spelling > Announcements** (**Ctrl+Alt+Shift+F7**) |
| Whether you are asked about last session | The **Reopen Last Session** window itself (**Alt+Shift+F12**) |

People often look for that last one in Preferences. It lives in the window that
asks the question. See [Reopening what you had
open](lite-guide-03-opening-saving-and-printing.html#reopening-what-you-had-open), in Chapter 3.

### Taking your settings with you

**Tools > Back Up Settings...** (**Ctrl+Alt+F11**) saves your settings to a
`.qsf` file. **Tools > Restore Settings...** (**Ctrl+Alt+F12**) reads one back,
for example on a new computer.

The backup holds your preferences. It leaves out the things that only make
sense on this computer: your recent files, the documents QUILL Lite reopens at
startup, the window size, and when it last checked for an update. The backup
tells you how many file locations it left out.

When you restore, QUILL Lite tells you what happened: how many settings came
across, how many are new since the backup was made (those keep their usual
values), and how many it did not recognise. If the file has nothing QUILL Lite
recognises at all, nothing is changed, so picking the wrong file cannot reset
your editor.

QUILL has the same thing, as buttons in its Preferences window. The two use
the same kind of file, but each one only reads its own backups.

## Making QUILL Lite smaller (or larger)

QUILL Lite has a lot in it. You may not want all of it, and you do not have to
keep it. **Tools > Customize Features** (**Ctrl+Alt+F10**) lets you switch whole
parts of the app off.

When you switch something off, it leaves the menus and its keys stop working.
It is really gone, not just hidden. So a smaller QUILL Lite is one with fewer
things to arrow past and fewer keys to press by accident.

### Profiles: five ways to say it in one word

You do not have to go through the checkboxes one by one. The **Profile** box at
the top of the window offers five ready-made choices. **Choosing one sets every
checkbox below it straight away.** There is no second button to press.

Nothing is saved until you press **Save**. So you can try a profile, look at
what it would do, and change your mind.

#### Hearing what a profile does

Under the Profile box is a **read-only description you can read line by line**.
It tells you two things. First, what the profile is. Then what it would do to
your copy of QUILL Lite: how many of the 24 areas it keeps and which ones, which
ones it removes, and anything else it changes. Notepad, for example, also makes
**Ctrl+N** create a plain text document. Press **F1** on the Profile box to hear
the same thing.

When you choose a profile, QUILL Lite says a short version, like this: "Notepad
profile: 3 of 24 features on. New documents will be plain text. Nothing is saved
until you press Save." Your screen reader already reads the profile's name, and
the longer description is there for you to read at your own pace.

#### Changing your mind

**Custom puts everything back.** If you arrow onto a profile you did not mean,
choose **Custom**. Every checkbox goes back to how it was when you opened the
window.

You will also hear the box say Custom as soon as you check or uncheck anything
yourself. That is not a warning. Picking your own is exactly what the list is
for.

After you choose a profile, the checkboxes are still ordinary checkboxes. You
can change any of them. If you have changed a few and want to start the profile
over, press **Use Profile**.

#### The same profiles in Preferences

**The same five profiles are in Preferences** too, at the top, with the same
description underneath. So if you think of "make this like Notepad" as a
setting, you will find it where your other settings are. The 22 separate
checkboxes are only in Customize Features.

#### The five profiles at a glance

Here is each one at a glance, and then in more detail.

| Profile | Areas on | Ctrl+N makes |
|---|---|---|
| **Recommended** | 19 of 24 | plain text (unchanged) |
| **Everything** | 23 of 24 | plain text (unchanged) |
| **Developer** | 20 of 24 | plain text (unchanged) |
| **WordPad** | 6 of 24 | **rich text** |
| **Notepad** | 3 of 24 | **plain text** |

#### Recommended

**This is what you get when you first install QUILL Lite.** It keeps nineteen
of the 24 areas: rich text, headings, Markdown and HTML, bookmarks, the line
tools, the clipboard history, printing, abbreviations, the Selection submenu,
spell check, the dictionary and thesaurus, Matches, Go Back and Go Forward, the
Command Palette, Describe Character, text size, dictation, WordPress and
Forms.

**Off:** autocorrect, timestamped backups, Go To Anything, AI help and coding.
The first four are not switched off because they are poor. They are off
because you should choose them yourself:

- Autocorrect can change the quotes in a settings file and break it.
- Backups slowly fill a folder on your computer.
- Go To Anything is one more way to jump around, and the command palette, the
  headings list and the bookmark list already do that.
- AI help sends the text you ask about over the internet, and only you should
  decide to do that.

Coding, the fifth, belongs to the Developer profile below.

**Choose this** when you have been experimenting and want to get back to where
you started.

#### Everything

**23 of the 24 areas on**: every writing area, including the four above.
Coding stays off, because coding is what the Developer profile is for. That includes **AI help**, which
is the one area that sends anything off your computer, so only choose this
profile if you are happy with that.

With Everything on:

- Autocorrect can straighten your quotes and turn two hyphens into a long dash.
  It does nothing else. It never capitalises sentences.
- Every save keeps a dated copy in your data folder.
- Go To Anything joins the command palette and the two lists.

**Choose this** if you would rather have it all and switch things off as they
get in your way.

#### Developer

**Everything in Recommended, plus Coding.** Twenty of the 24 areas: the
seventeen Recommended keeps and the Coding area, which no other profile has.
Coding gives you project tasks with an AI, reviewed changes across files,
commands and tests that ask first, Undo Last Agent Turn and coach mode. See
[Coding: project tasks, in the Developer profile](lite-guide-10-ai-help.html#coding-project-tasks-in-the-developer-profile)
in Chapter 10.

**Off:** autocorrect, timestamped backups, Go To Anything and AI help, as in
Recommended. Project tasks need an AI connection, so turn on AI help too when
you want to use them.

**Ctrl+N** is unchanged.

**Choose this** if you write code and want an AI to help with it, and you want
every change it makes shown to you first.

#### WordPad

**Everything WordPad could do.** Rich text you can format, print and spell
check: bold, italic, underline, headings, alignment, bullets, indenting and line
spacing, plus Find and Replace, printing and text size, and the Command
Palette. Six of the 24 areas.

**Off**, all eighteen of the others. These are the writing tools around the
formatting, and coding:

- No line tools (Edit > Lines) and no Change Case.
- No clipboard history or Copy Tray.
- No bookmarks, no abbreviations, and no Selection submenu.
- No Matches list, no Find in Open Documents or Search in Files, no Back and
  Forward, and no Go To Anything.
- No Describe Character and no dictation.
- No dictionary or thesaurus (WordPad never had one).
- No autocorrect and no backups.
- **No Markdown or HTML.** Ctrl+B in a `.md` file goes back to meaning rich text
  bold, and QUILL Lite tells you so.
- **No AI help** and no coding.
- **No WordPress** and **no Forms**.

**Ctrl+N makes a rich text document.** So choosing WordPad changes a setting as
well as the checkboxes: new documents start as rich text.

**One thing real WordPad did not have:** the spell checker. It stays, because a
word processor without one would just be a nuisance.

**Choose this** for letters, notes and anything you want to look nice.

#### Notepad

**The smallest QUILL Lite can be.** Many people come to QUILL Lite to replace
Notepad, and this is the profile for them. It keeps three of the 24 areas:
**printing**, **text size** and the **Command Palette**.

**Off**, all twenty of the others: the Format menu and everything under it,
headings, Markdown and HTML, bookmarks, the line tools, Change Case, the
clipboard history, abbreviations, the Selection submenu, spell check, the
dictionary and thesaurus, Matches (and with it Find in Open Documents and
Search in Files), Back and Forward, Go To Anything,
Describe Character, dictation, autocorrect, backups, AI help, WordPress,
Forms and coding.
Nothing that Notepad does not have, apart from the palette.

**Why every profile keeps the Command Palette:** it is how you find a
command when you do not know its key or its menu. Press **Ctrl+Shift+P** and
type part of a name. Every command and every menu item is in it, including
your open windows and your recent files, each with its key beside it.

**Ctrl+N makes a plain text document**, and the Save As dialog stops offering
you formats you have switched off.

**Some things stay, because Notepad has always had them:** Find, Find Next,
Replace, Go To Line, Select All, Insert Date and Time, Word Wrap, the font
picker, the status bar and Undo. **Tools > File Encoding and Line Endings**
stays too. That is a big part of why people replace Notepad: so a file saves
back exactly the way it arrived.

**Choose this** for settings files, logs, quick notes, and anything that must
stay plain text with no hidden formatting.

#### Moving between them

You can always go back. Choose **Notepad** and then **Everything**, and it all
comes back, including the Format menu and its keys. The only thing a profile
does not undo is a setting you changed by hand afterwards. A profile only
changes the things it says it changes.

Two things stay whichever profile you choose: **Tools > Preferences** and
**Customize Features** itself. Otherwise you could switch off the very window
you need to switch things back on.

### Searching the list

There are 23 checkboxes, which is a lot to Tab through. Type in the search box
below the Profile box and the list narrows as you type.

It searches what an area does as well as its name. Type "curly quotes" and you
find Autocorrect. Type "dictionary" and you find Spell check. The line under the
box tells you how many are left. Press **Down** from the box to go straight into
the list.

### The 24 areas

| Area | What goes | Starts |
|---|---|---|
| **Rich text and the Format menu** | Bold, headings, alignment, bullets, spacing | on |
| **Heading navigation** | Next and previous heading, the headings list | on |
| **Markdown and HTML** | The two tag pickers, Document Language, and markup Bold | on |
| **Bookmarks** | All nine, and the list | on |
| **Line tools and change case** | Edit > Lines, Tools > Change Case | on |
| **Copy Tray and the clip library** | Edit > Clipboard (Cut, Copy, Paste and Copy All stay) | on |
| **Printing** | Print and Page Setup | on |
| **Abbreviations** | Short forms, and the list that manages them | on |
| **Spell check** | Tools > Spelling, and checking as you type | on |
| **Dictionary and thesaurus** | Look Up, Thesaurus, Say Word Summary, and the two submenus on any word | on |
| **The Selection submenu** | F8 selecting, whole-structure selecting, marks | on |
| **Matches** | The Matches submenu (All Matches, Count Occurrences), and Find in Open Documents, Search in Files and Replace Across Files on Edit (Find itself stays) | on |
| **Go Back and Go Forward** | The trail of places you jumped from | on |
| **The Command Palette** | Ctrl+Shift+P, the search box for commands | on |
| **Describe Character** | What the character under the cursor actually is | on |
| **Text size** | Bigger, smaller, and reset | on |
| **Dictation** | Tools > Dictation: speaking into the document, and choosing the microphone | on |
| **WordPress** | File > WordPress: your sites' pages, posts, pictures, comments, categories and tags | on |
| **Forms** | File > New Form, and the form rows in Insert, View, Format and Tools > Forms | on |
| **Autocorrect while typing** | Curly quotes and long dashes (it does not capitalise sentences) | **off** |
| **Timestamped backups** | A dated copy kept every time you save | **off** |
| **Go To Anything** | One box that searches everything at once | **off** |
| **AI help (sends your text to QUILL's servers)** | Tools > AI: summarize, rewrite, proofread, explain, and questions about a document | **off** |

The last four start switched off. They are still in this list, so you can find
them and switch them on whenever you like.

#### Why autocorrect, backups and Go To Anything start off

Curly quotes look lovely in a letter but can break a settings file. Backups
slowly fill a folder. And Go To Anything does a job that the command search,
the headings list and the bookmark list already share between them.

#### Switching on AI help

**AI help is off for a different reason.** Using it sends the passage you ask
about over the internet, and that is your choice to make, nobody else's. Its row
in Customize Features tells you exactly what you are agreeing to before you
switch it on. While the area is off, it has no menu, no keys, no sign-in saved
on your computer, and makes no connection of any kind.

**Switching it on is only the first step.** Before anything is sent, QUILL Lite
shows you the whole agreement: what is sent, what QUILL keeps, what it does not
keep, what OpenAI does with it, and how to say no. Nothing happens until you
accept.

If you switch the area on and then decline the agreement, the AI menu stays but
nothing in it will send anything. QUILL Lite does not quietly switch the area
back off for you.

You can reach the same agreement in **three places**. Use whichever you find
first:

- **Tools > AI > Accounts and Usage > Privacy Agreement...** (**Ctrl+Alt+Shift+K**). Read it, accept
  it, or take it back. Taking it back also signs this computer out.
- **Preferences**, where a check box says *Use QUILL's free AI help*. Checking it
  shows the agreement. Unchecking it takes your agreement back.
- **Customize Features**, where switching the area on asks you straight away.

All three share one answer, so they always agree. If the agreement ever changes
in a way that matters, such as what is sent or what is kept, you will be asked
again.

#### How autocorrect works

**Autocorrect has three rules, and switching the area on does not turn any of
them on.** The area decides whether autocorrect exists at all. Three check boxes
in **Tools > Preferences** decide which rules run:

- **Curl quotes as I type**
- **Turn two hyphens into an em dash**
- **Correct common misspellings as I type**

All three start off. So after you switch the area on, you also need to check the
rule you want. They are separate because plenty of people want the long dash but
not the curly quotes, or the spelling fixes and nothing else.

The two typography rules never run in a plain text, source code or settings
document, whatever the boxes say. A curly quote in a `.json` file would break
it. Misspelling correction runs in plain text, Markdown and rich text, and never
in source code or settings files.

There is no fourth rule. QUILL Lite does **not** capitalise the start of a
sentence, and never has.

#### Correcting misspellings as you type

With the rule on, QUILL Lite fixes the misspellings almost everybody makes the
moment you finish the word. Type `teh` and a space and it becomes `the `; type
`recieve` and press **Enter** and it becomes `receive` before the new line
starts. You hear the word-corrected sound and "Corrected to the", because your
screen reader only echoes the space and would never tell you the word changed.

The built-in list has about 350 common English misspellings, such as `teh`,
`seperate`, `definately`, `occured`, `untill` and `wierd`. Every one was checked
against American and British dictionaries before it went in, so a word you
spelled correctly is never on it. Your capitals are kept: `Teh` becomes `The`,
and `febuary` becomes `February`. Brackets, quotes and punctuation round the
word stay where they were, so `(recieve,` becomes `(receive,`.

It never touches:

- a word typed all in capitals, such as `TEH`, which is far more often an
  acronym than a mistake;
- web addresses, email addresses and paths, or any word with a full stop,
  slash, colon, `@`, digit or underscore inside it, so `teh.example.com` and
  `adress@example.com` stay as typed;
- anything inside backticks or a fenced code block in Markdown;
- source code and settings files, by their name, the same list that keeps
  spell-check-as-you-type quiet in them.

**Taking one back.** **Ctrl+Z** straight after a correction puts back exactly
what you typed, as one undo step. QUILL Lite then leaves that word alone in this
document for the rest of the session: type the space again and the word stays,
and the status bar says "Kept teh as you typed it".

#### AutoCorrect Entries (Alt+Shift+9)

**Tools > AutoCorrect Entries...** (**Alt+Shift+9**) shows every correction, the
built-in ones and yours, one per row: "teh becomes the, built in". It is QUILL's
window, on QUILL's key, so it works the same in both.

- **Find** narrows the list as you type.
- **Corrections** is the list. **Enter** or **Space** on a row edits it.
- **Add...** makes a correction of your own: the word as you mistype it, what it
  should become, and whether case must match exactly. For example, `qill`
  becoming `QUILL`. The word must be letters only (an apostrophe inside is
  fine); what it becomes may be several words.
- **Edit...** changes the row you are on. Editing a built-in one keeps your
  version beside it, and the row says "built in, changed by you".
- **Turn Off** stops the correction you are on without deleting it, and the row
  ends in "stopped". The same button, now **Turn On**, starts it again. Use this
  when a correction keeps changing a word you meant.
- **Remove** deletes one of yours. On a built-in one you changed or turned off,
  it puts it back as it shipped. A built-in correction cannot be deleted, so
  Remove on one turns it off instead and tells you so.

Every button says what it did, and your changes are kept when you close the
window.

Your corrections are kept in your abbreviation list, under the category
**AutoCorrect**: QUILL Lite's own list, or QUILL's if Preferences says share
it, in which case QUILL and QUILL Lite share your corrections too. Turning
**Abbreviations** off in Customize Features does not turn your corrections off.
The window needs the **Autocorrect while typing** area switched on, like the
rule itself.

**Limits.** The built-in list is English only. A correction happens when a
space or **Enter** ends the word. AutoCorrect fixes known misspellings, not
every misspelling; **F7** and the spell check as you type still find the rest.

#### What can never be switched off

Three things always stay. **Tools > Preferences** and **Customize Features**
stay, so you can always get back to your settings. And **File Encoding and Line
Endings** stays, because saving a file back exactly as it arrived is at the
heart of QUILL Lite.

## Changing what a key does

You can change the key for any command in QUILL Lite. Open **Tools > Keyboard
Manager...** (**Ctrl+Alt+Shift+Space**).

1. The list shows every command and its key. Type part of a command's name to
   find it.
2. Press **Enter** on the command you want.
3. Press the new key.
4. Press **Save** when you are done.

### Finding out what a key already does

Want to know whether a key is free? Press **Record a Key**, then press the key.
QUILL Lite tells you what it does now, for example "Ctrl+S is File > Save", or
tells you it is free. That is much quicker than reading through two hundred
rows.

### When a key is taken

If you choose a key another command already uses, QUILL Lite tells you which
command has it and asks if you want to take it. If you say yes, that other
command is left with no key until you give it one. That way two commands never
share a key, which would leave one of them never working.

### When another program has the key

Some programs take a key for the whole of Windows. Google Drive takes
**Ctrl+Alt+G**, for example, and there are others. When that happens, the key
never reaches QUILL Lite, even while you are typing in it. The command is fine;
the key just goes to the other program.

QUILL Lite warns you about this. Record a Key says the key is "already claimed
by another application running on this computer", and the Keyboard Manager says
so if you pick one. It is only a warning, so you can keep the key if you want
it. It may work again when that other program is closed.

Windows does not tell QUILL Lite which program has the key, so it cannot tell
you either.

### What cannot be changed

- **The Insert key cannot be used.** Your screen reader needs it, and you would
  need it to get your key back.
- **A key on its own**, without Ctrl, Alt or Shift, cannot be used either. It
  would just type itself.

### Putting things back

- **Reset to Default** puts the command you are on back to its original key.
- **Reset Everything** does that for every command, after asking you first.
- Nothing is saved until you press **Save**. Press **Escape** to leave with your
  keys just as they were.

**Check for Problems** looks over all your keys at once. It tells you about a
key used twice, a key QUILL Lite cannot read, or a key Windows will accept but
never actually send to a menu, which would leave it doing nothing.

Only the keys you changed are saved. That way, if a later version of QUILL Lite
improves a key you never touched, you still get the improvement.

## Making QUILL Lite your text editor

When you open a text file from File Explorer or your desktop, Windows opens it
in Notepad. You can have it open in QUILL Lite instead. There are two ways, and
you can use either one or both. Both are in Preferences (**Ctrl+,**), under
**Windows and your files**, with a line that tells you which program opens in
place of Notepad right now.

### Choosing QUILL Lite in Default apps

Windows lets you choose which app opens each kind of file. QUILL Lite cannot
make that choice for you, but it can take you straight to the right place.

1. Open Preferences (**Ctrl+,**) and, under **Windows and your files**, press
   **Make QUILL Lite My Text Editor...**.
2. Read the short message, then press **OK**.
3. Windows Settings opens on the Default apps page for QUILL Lite. It lists
   file types such as .txt, .md and .rtf, each with the app that opens it now.
4. Choose **.txt**, pick **QUILL Lite** in the list that appears, and choose
   **Set default**.
5. Do the same for any other type you want QUILL Lite to open. Leave the rest
   as they are.
6. Close Settings with **Alt+F4**.

From now on, pressing Enter on a .txt file opens it in QUILL Lite. QUILL Lite
is also in the **Open with** list when you press the Applications key on a
file.

On Windows 10, Settings opens on the general Default apps page instead. Choose
**Choose default apps by file type**, find .txt, and pick QUILL Lite.

To change your mind, go back to the same page and pick Notepad, or any other
app, for that type.

### Opening QUILL Lite instead of Notepad

Some programs open Notepad by name, and so does typing "notepad" in the Run
box. Default apps does not change those. If you would like QUILL Lite to open
every time anything asks for Notepad, check **Open QUILL Lite instead of
Notepad** in Preferences, under **Windows and your files**. It is off until you
turn it on.

Three things to know first:

- It changes Notepad for everyone who uses this computer, not just for you.
- Windows asks for administrator approval. If your account is not an
  administrator, somebody with an administrator password will need to approve
  it.
- To undo it, clear the same checkbox and press OK. The checkbox always shows
  whether it is on right now.

To turn it on:

1. Open Preferences (**Ctrl+,**) and, under **Windows and your files**, check
   **Open QUILL Lite instead of Notepad**. Then press **OK**.
2. Read the message and choose **Yes**.
3. Approve the Windows prompt that follows.
4. QUILL Lite tells you when it is done.

On Windows 11 there is one more step. The newer Notepad has a shortcut of its
own, called an app execution alias, that can still open it. QUILL Lite offers
to open the page where you turn that off. Choose **Yes**, find **Notepad** in
the list, and turn it off. To get there yourself, open Settings, then Apps,
then Advanced app settings, then App execution aliases.

When QUILL Lite opens in place of Notepad, you get the file Notepad was asked
to open, or a new blank plain text document if there was none. If a program
asked Notepad to print a file, QUILL Lite opens it instead, and **Ctrl+P**
prints it.

If you uninstall QUILL Lite while this is on, the uninstaller puts Notepad back
for you. If you use a portable copy, turn it off before you delete the folder.

## What you learned, and where to go next

Preferences (**Ctrl+,**) holds your everyday settings in one column, and
nothing is saved until you press OK. Press F1 on any control when you are
unsure what it does. A few quick switches live on the View and Tools menus
instead, and **Ctrl+Alt+F11** and **Ctrl+Alt+F12** back up and restore your
settings.

Customize Features (**Ctrl+Alt+F10**) makes QUILL Lite as small as Notepad or
as full as you like, in one step with a profile or one checkbox at a time.
Nothing is saved until you press Save, and nothing is one-way. The Keyboard
Manager (**Ctrl+Alt+Shift+Space**) changes any key, Record a Key tells you what a
key does now, you are warned when a key is taken, and you can always put
things back. The Keyboard reference at the end of this guide lists every key
QUILL Lite ships with.

In Preferences, under Windows and your files, Make QUILL Lite My Text Editor
takes you to the Windows page where you choose QUILL Lite for .txt and other
types, and Open QUILL Lite instead of Notepad catches everything that still asks
for Notepad by name.

If you are curious about AI help, the tutorial *Asking a question about a
document* walks you through switching it on.

Next, Chapter 12, Your files, updates and QUILL for All, explains where QUILL
Lite keeps things and how to get new versions.

---

- Previous: [Chapter 10: AI help](lite-guide-10-ai-help.html)
- Next: [Chapter 12: Your files, updates and QUILL for All](lite-guide-12-your-files-updates-and-quill-for-all.html)
- [Contents](../userguide.html)
