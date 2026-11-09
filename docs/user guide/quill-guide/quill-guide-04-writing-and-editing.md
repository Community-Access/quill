# Chapter 4: Writing and editing

This chapter is about the work you do most: typing, fixing, moving text
around and putting things in. It starts with the keys you already know from
other Windows programs, then shows the extras QUILL adds, such as a tray of
twelve clipboards, abbreviations that type for you, and an emoji picker that
describes every emoji in words. Read the first few topics now. The rest will
keep until you want them.

## Writing and editing

Start with the commands you already know. They work in QUILL exactly as they
do everywhere else:

- `Ctrl+Z` to undo
- `Ctrl+Y` to redo
- `Ctrl+X`, `Ctrl+C` and `Ctrl+V` to cut, copy and paste
- `Ctrl+A` to select everything

Once those feel at home, QUILL has more to offer. You can put text away in a
numbered slot and paste it back with one chord, get back something you
deleted and drop it somewhere else, and run any command twenty times in a
row. Each has its own topic below.

### Ending a line without a new paragraph (Shift+Enter)

**Line Break** (`Shift+Enter`) ends the line **without starting a new
paragraph**, the same key Word uses. In Markdown a blank line between two
lines makes two paragraphs, while a line break makes two lines of one
paragraph. Use it for an address block, a verse, or a run of short lines that
should sit close together.

QUILL writes the break in the style set in **Settings > Editing >
Markdown line break style** (`markdown_hard_break_style`), and says which one
it used. The default is a **backslash** at the end of the line. The other
style, two spaces at the end of the line, cannot be seen on screen, is not
spoken by a screen reader, and is often removed by other programs when they
save. QUILL reads both styles, so a document written elsewhere with two
spaces still shows its breaks correctly here.

You can also choose it from the menu: **Insert > Line Break**. QUILL Lite has
the same command in the same place, on the same key.

## The Edit menu

The **Edit** menu holds the commands you use while writing. The standard
clipboard commands come first:

- Undo
- Redo
- Cut
- Copy
- Paste
- **Paste Text Only** (`Ctrl+Shift+V`), which pastes the words on the
  clipboard and leaves behind any fonts, colours or links that came with them.
  If something is selected, the pasted text replaces it.
- **Copy With Attribution** (`Alt+Shift+C`)
- The **Clipboard** submenu: **Say Clipboard** (`Alt+Shift+Home`), **Append
  Selection to Clipboard** (`Alt+Shift+End`), **Save Clipboard to File...**,
  **Clear Clipboard** and **Paste Copied Files...**. [Hearing and handling the
  clipboard](#hearing-and-handling-the-clipboard), later in this chapter, has
  the whole story.
- Select All

**Magic Paste** (press the QUILL key, then `Shift+V`) looks at what is on the
clipboard before it pastes, and tells you what it found: plain text, a web
address, Markdown, HTML or an image. Then it offers the ways that kind of
thing can go in. A web address can go in as a Markdown link, Markdown can
keep its formatting, HTML can come in as clean text or exactly as it is, and
an image can go in as a picture reference. Plain text is always one of the
choices. Arrow to the one you want and press **Paste**.

After those come the commands that know about selection and position:

- **Find...**, **Replace...**, **Find Next**, **Find Previous** and **Find All
  Matches**. The Replace dialog has a **Replace All** button, so bulk
  replacement happens in the same place.
- **Find in Open Documents...**, **Search in Files...** and **Replace Across
  Files...**, the three searches that reach beyond this document (Chapter 6
  covers them).
- **Word Prediction...** opens a list of word and tag suggestions (`Ctrl+.`).
  You hear how many there are and the first one. Up and Down say each one,
  Enter or Tab puts it in place of the part of the word you'd typed, and
  Escape closes the list without touching your text. It works in every
  profile. **Toggle Word Prediction As You Type**, in the Command Palette
  (Ctrl+Shift+P), opens the list on its own after two letters; that one is
  off unless you turn it on, and a profile can switch it off. In a code file
  the list offers the file's own names, each said with its kind, such as
  "count_words, function" (see the Developer Guide, chapter 11).
- **Extend Selection Mode** turns selection growth into a mode of its own.
- The **Selection** submenu: Select Word, Select Line, Select Paragraph,
  Select Block, Select to Start or End of Line, Select to Start or End of
  Document, and the mark commands: **Set Temporary Mark**, **Jump to Previous
  Mark**, **Swap Cursor and Mark** and **List Recent Marks**. Selecting text,
  later in this chapter, has the keys.
- **Search Tools**, with Count Occurrences, Multi Replace, the regular
  expression tools, and **Run Replace Job...** and **Manage Replace Jobs...**
  for find-and-replace lists you save and use again (Chapter 5 and Chapter 6
  cover them).
- **Paste HTML as Markdown** turns rich HTML from the clipboard into Markdown
  as it pastes.
- **Paste Markdown as HTML** does the opposite. It turns Markdown on the
  clipboard into a clean piece of HTML, using the same renderer as the live
  preview and HTML export, and inserts it at the cursor. It has no key at
  first; give it one in the Keymap Editor.
- **Follow Link**, on the **Navigate** menu, opens the link under the caret.
  `Ctrl+Enter` still does it when the caret is on a link; anywhere else that
  key now inserts a page break. Adding a link is on the **Insert** menu.
- The delete group, on **Format > Line**: **Delete to Line Start**, **Delete
  to Line End**, **Delete to Document Start**, **Delete to Document End** and
  **Delete Paragraph** remove text measured from the cursor. Edit > Restore
  Deleted Text, below, brings the last three back.

**Preferences...** and **Customize Menus...** are with the rest of QUILL's
settings, under **Tools > Customize and Support**.

### Find and Replace

By default `Ctrl+F` and `Ctrl+H` open the standard Windows Find and Replace
dialog. Turn on **Settings > Navigation and QUILL Key > Use QUILL's own Find dialog** and they open
QUILL's own accessible Find dialog instead. It does everything the Windows one
does, and adds these:

- **Extended mode (special characters).** Choose *Extended* in the Mode list
  to search for characters you cannot type: `\n` for a line break, `\t` for a
  tab, `\xNN` or `\uNNNN` by code, or `\N{EM DASH}` by name. The **Insert
  Special Character...** button offers forty named characters, such as the
  non-breaking space, curly quotes, the zero-width space and the soft hyphen.
  Those invisible characters can quietly spoil a document, and now you can
  find them by name. Replacements understand the same codes, so "replace every
  non-breaking space with a plain space" takes two fields.
- **A spoken match count as you type.** Pause for a moment and QUILL says
  "17 matches", so you know the search is right before you go.
- **Peek navigation.** `Ctrl+Down` and `Ctrl+Up` step through the matches
  while you stay in the search field. Each step speaks the match in its
  sentence and selects it in the editor, and you can keep typing at any
  moment. Look around first, then press Enter when the search is right.
- **Spoken match context.** Each match is read as the sentence around it
  ("line 40: ...the quick brown fox..."), not just a position. QUILL always
  tells you when the search wraps past the end of the document.
- **A Direction group with a name.** The Up and Down choice is a labelled
  group, so your screen reader says "Direction" when you reach it.
- **One dialog, always.** `Ctrl+F` while it is open takes you back to the
  search field. `Ctrl+H` switches it to Replace without opening another
  window. `Ctrl+L` jumps back to the search field from anywhere in the dialog.
  Escape closes it and returns you to your text. **Count** tells you how many
  matches there are without moving anywhere.

The setting is off when QUILL is installed, while the dialog is tested with
every screen reader. The Windows dialog is unchanged, and you can switch back
at any time. For now this dialog searches the current document only.
Searching folders or the Vault from it will come later.

Chapter 6, Moving around and finding things, has much more on searching.

## Selecting text

You can select the usual way, holding Shift while you move. QUILL also gives
you ways to select a whole unit at once, to mark where a selection starts and
finish it later, and to leave yourself marks to jump back to.

### Anchor selection with F8

With anchor selection you drop an invisible anchor, move anywhere you like,
and then select everything between the anchor and the cursor.

| Key | Command | What it does |
| --- | --- | --- |
| `F8` | Start selection | Sets an invisible anchor at the cursor. |
| `Ctrl+Alt+F8` | Toggle selection marker | Drops the anchor without moving the cursor, or picks it back up if you change your mind. |
| `Shift+F8` | Complete selection | Selects from the anchor to the cursor and says how much. |
| `Ctrl+Shift+F8` | Reselect | Brings back the last selection you made. |
| `Alt+Shift+F8` | Go to start of selection | Moves to the start of the selection without changing it. |
| `Ctrl+F8` | Copy all | Copies the whole document. |
| `Ctrl+Shift+A` | Unselect all | Drops the selection, leaving the cursor where it is. |
| `Alt+F8` | Read all | Reads the document from the beginning. |

### Selecting by structure

| Key | Command | What it does |
| --- | --- | --- |
| `Ctrl+Shift+W` | Select word | Selects the word the cursor is in. |
| `Ctrl+Space` | Select sentence | Selects the sentence the cursor is in. |
| `Ctrl+Alt+Space` | Select token | Selects the run of characters the cursor is in, whatever kind they are. On a word it is the same as Select Word; its real use is a run of punctuation, such as the `::` in a path, or the spaces at the start of a line. |
| `Ctrl+Shift+E` | Select line | Selects the whole line. |
| `Ctrl+Shift+H` | Select paragraph | Selects the paragraph at the cursor and says its size and word count. |
| `Ctrl+Alt+Shift+B` | Select block | Selects the indented block at the cursor. |
| `Ctrl+Shift+X` | Expand selection | Grows the selection one step: line, then paragraph, then block, then the whole document. |
| `Ctrl+Alt+Shift+X` | Shrink selection | Undoes the last expand step. |
| `Alt+Shift+F5` | Select section | Selects the section at the cursor with all its subsections, and says how many sections and lines that is. Cut and paste then move it anywhere. |

The ordinary selection keys are on the **Edit > Selection** menu too, so you
can find them there if you forget: **Select to Start of Line** (`Shift+Home`),
**Select to End of Line** (`Shift+End`), **Select to Start of Document**
(`Ctrl+Shift+Home`) and **Select to End of Document** (`Ctrl+Shift+End`).

Once something is selected, press `Ctrl+Alt+Q` for **Duplicate Selection**: it
puts a copy of the selection straight after itself, which saves a copy and a
paste when you are building a list of similar lines. With nothing selected, it
duplicates the line you are on. It is not on the menu bar; besides the key, it
is on the editor's right-click menu (press the Applications key) under
**Change Case**, and in the Command Palette.

You can also run any of these from the Command Palette, and change their keys
in the Keymap Editor.

### Extend Selection Mode

In Extend Selection Mode, the keys that normally move the cursor grow the
selection instead. Turn it on and off from the Selection menu, or with
`Alt+Shift+F9`. You can change the key in the Keymap Editor. While it is on,
**EXT** shows in the status bar.

### The mark ring

The mark ring is a short stack of temporary places to jump back to while you
work.

| Key | Command | What it does |
| --- | --- | --- |
| `Ctrl+Shift+M` | Set Temporary Mark | Puts a temporary mark at the cursor. |
| `Ctrl+M` | Jump to Previous Mark | Jumps to the latest mark and takes it off the ring. |
| `Ctrl+Alt+X` | Swap Cursor and Mark | Swaps the cursor with the top mark. |
| `Alt+M` | List Recent Marks | Shows every mark with its line and column. |

### Named marks and the review buffer

Named marks last for the whole session. Find them on **Edit > Selection**:

- **Set Named Mark** gives the cursor position a name and remembers it, and
  tells you the line and column.
- **Jump to Named Mark** shows a list of your marks with their positions.
  Choose one and you are there.
- **Review Buffer** opens the current selection in a read-only window, so
  you can read through it with your screen reader without any risk of
  changing it. You need a selection first. Its key is `Alt+Shift+U`.

Set Named Mark and Jump to Named Mark have no keys at first. Give them keys in
the Keymap Editor, or use the Selection menu.

## Getting text back, and doing it again

### Restore Deleted Text

Undo (`Ctrl+Z`) puts your last edit back exactly where it was. Sometimes you
want something else: you deleted a sentence, and now you want to put it
somewhere *else*. **Edit > Restore Deleted Text...** (`Ctrl+Alt+Shift+Z`)
remembers the last three pieces of text you removed with QUILL's delete
commands (delete to start or end of line, delete to start or end of document,
and delete paragraph). Pick one from the list and it goes in at the cursor.

- The list is newest first, with a short preview and the length of each, so
  you can tell them apart by ear.
- If only one deletion is remembered, it comes straight back with no list.
- To change its key, search for "Restore Deleted Text" in the Keymap Editor.

Fans of the classic WordPerfect Editor will know this as its "Cancel" buffer,
except that here you choose where the text lands.

### Repeat Next Command

When you need to do the same thing many times, such as moving down twenty
lines, deleting ten words, typing forty dashes or replaying a macro, you do
not have to press the key over and over. Choose **Edit > Repeat Next
Command...**, type how many times, and the *next* command you run happens
that many times. Then the count clears itself and editing carries on as
normal.

- It works with nearly any command, including moving, deleting, inserting and
  a recorded macro.
- The most it will repeat is 1000 times, so a slip of the finger cannot run
  away with you.
- It has no key at first. If you use it often, give it one in the Keymap
  Editor (**Tools > Customize and Support > Keymap Editor...**; search for
  "Repeat Next Command").

This is the "Repeat" command from the classic WordPerfect Editor.

## Hearing and handling the clipboard

You copy something in a web page, switch to QUILL, and then wonder: did that
copy actually work, and what exactly did I get? Until now the only way to find
out was to paste it somewhere and read it back. These four commands, on
**Edit > Clipboard**, let you hear the Windows clipboard, add to it, keep it
and empty it without pasting a thing. QUILL Lite has the same four, on the
same keys.

### Say Clipboard (Alt+Shift+Home)

Press `Alt+Shift+Home` and QUILL reads you what is on the clipboard. Like the
Copy Tray's paste keys, it does more if you press it again quickly. A quick
press is one within half a second of the last, and QUILL answers every press
straight away, so you never wait to find out whether a second press is coming.

- **Press once** to hear it. Short text is read in full. A long piece is read
  up to its first 2,000 characters, and then QUILL tells you how much is left:
  "and 4,312 more characters. Press three times quickly to read it all."
- **Press twice** to hear it spelled, letter by letter, so you can check a
  web address, a code or a name you are about to paste into a form. Capital
  letters are said as "cap". Spelling stops after the first 200 characters,
  because nobody wants to sit through more than that.
- **Press three times** to open a small read-only window, titled **Clipboard**,
  with everything in it. Read it line by line with the arrow keys, at your own
  pace; nothing you do there changes the clipboard. Press Escape, or the
  **Close** button, and you are back in your document, exactly where you were.

It tells you plainly when there is nothing to read:

- With nothing on the clipboard, you hear "The clipboard is empty".
- With a picture, or anything else that is not text, you hear "The clipboard
  holds something that is not text, such as a picture".
- With files you copied in File Explorer, you hear how many and their names:
  "2 files on the clipboard: report.docx, notes.txt". After ten names it says
  how many more there are. Press twice to hear each file's full path, folder
  and all, and three times to see the paths in the window, one to a line.

> **QUILLBee's tip:** Copied a confirmation code from an email? Press
> `Alt+Shift+Home` twice, quickly, and QUILL spells it out before you type it
> anywhere.

### Append Selection to Clipboard (Alt+Shift+End)

Copying replaces whatever was on the clipboard. Sometimes you want to add to
it instead: a name from here, an address from further down, a sentence from
the end. Select the next piece and press `Alt+Shift+End` (**Edit > Clipboard >
Append Selection to Clipboard**). The selection goes on the end of the text
already on the clipboard, on a new line of its own, and QUILL tells you where
things stand: "Appended 5 characters to the clipboard, which now holds 11
characters."

- No blank line is added between pieces. If the clipboard text already ends
  with a line break, the new piece goes straight after it.
- If the clipboard was empty, it simply ends up holding your selection.
- If nothing is selected, you hear "Select text first to append it to the
  clipboard", and the clipboard is left alone.
- If the clipboard holds files rather than text, your selection replaces them.

When you have gathered everything, paste it all at once with `Ctrl+V`, in
QUILL or in any other program.

### Save Clipboard to File...

**Edit > Clipboard > Save Clipboard to File...** puts the clipboard's text
straight into a file of its own, without making a new document first. A Save
window opens with a name already filled in, made from the date and time, such
as "clipboard 2026-11-06 1405.txt". Keep it or type your own, choose a folder,
and press Enter. QUILL saves it as UTF-8 text and says "Saved 1,204 characters
to clipboard 2026-11-06 1405.txt".

The file is written safely: QUILL writes a temporary copy first and only swaps
it in once it is complete, so a full disk or a sudden power cut cannot leave
you with half a file. If the clipboard holds files rather than text, you hear
"The clipboard holds files, not text, so there is nothing to save".

### Clear Clipboard

**Edit > Clipboard > Clear Clipboard** empties the Windows clipboard, for every
program, not just QUILL. You hear "Cleared the clipboard", or "The clipboard
was already empty" if there was nothing to clear. It is a good habit after you
copy a password or anything else private, so the next `Ctrl+V`, in whatever
program, cannot paste it somewhere it should not go.

### Paste Copied Files...

Copy a file in File Explorer, come back to QUILL and press `Ctrl+V`, and you
get nothing useful. **Edit > Clipboard > Paste Copied Files...** asks what you meant.
A small window says how many files are on the clipboard and names them, then
offers two choices in a list:

- **Each file's text** puts in what each file says, read the same way QUILL
  would open it: a Word document, a PDF or an RTF file comes in as its text,
  not as a screen of symbols. Two files are separated by a blank line.
- **Each file's full path** puts in one path per line, which is what you want
  for an email to IT or a note about where something lives.

Arrow to the one you want and press Enter. Escape pastes nothing. The text
goes in at the cursor, over anything you had selected, and `Ctrl+Z` takes it
all back in one step.

Some files are left out, and QUILL tells you which and why: a file over 5 MB
("big.log is 12 MB, over the 5 MB limit"), a folder, and anything that is not
text, such as a picture or a program. The rest are still pasted, and you hear
something like "Pasted the text of 2 files. Not pasted: photo.png is not a
text file". If there are no copied files on the clipboard at all, QUILL says
so and suggests `Ctrl+V` for ordinary text.

### Why some of these have no key

Save Clipboard to File, Clear Clipboard and Paste Copied Files are on the menu only.
When these commands were added, in November 2026, there was no key left that
was free in both QUILL and QUILL Lite, and all three are occasional commands. Clear Clipboard
has a second reason: a key you could press by accident would throw away
whatever you had just copied. If you want a key for either, give it one in the
Keymap Editor (**Tools > Customize and Support > Keymap Editor...**).

## Copy Tray

The Copy Tray is **twelve** clipboards of your own, each with a number. You
put text in a slot on purpose, and it stays there until you replace it or
clear it, even after you close and reopen QUILL. The Windows clipboard is
shared by every program and changes every time you copy. Copy Tray slots
belong to QUILL alone.

### Pasting and copying with a slot

**To paste from a slot, hold `Ctrl+Alt+Shift` and press a number key.**

| Key | What happens |
| --- | --- |
| `Ctrl+Alt+Shift+1` through `Ctrl+Alt+Shift+9` | Paste from slots 1 to 9 |
| `Ctrl+Alt+Shift+0` | Paste from slot 10 |
| `Ctrl+Alt+Shift+-` | Paste from slot 11 |
| `Ctrl+Alt+Shift+=` | Paste from slot 12 |

**To copy into a slot, press the QUILL key and then the same key with Shift:**

| Key | What happens |
| --- | --- |
| `Ctrl+Shift+Grave, Shift+1` through `Shift+9` | Copy the selection to slots 1 to 9 |
| `Ctrl+Shift+Grave, Shift+0` | Copy the selection to slot 10 |
| `Ctrl+Shift+Grave, Shift+-` | Copy the selection to slot 11 |
| `Ctrl+Shift+Grave, Shift+=` | Copy the selection to slot 12 |

A paste chord does more if you press it quickly more than once:

- **Press once** to paste the slot at the cursor.
- **Press twice** to peek. QUILL reads the slot to you without pasting it, so
  you can check what is there first.
- **Press three times** to open the Copy Tray dialog on that slot.

> **QUILLBee's tip:** Can't remember what is in slot 3? Press
> `Ctrl+Alt+Shift+3` twice, quickly. QUILL reads it to you and pastes nothing.

### Copy to Next Empty Slot, Copy to Tray Slot and Search Tray Slots

**Edit > Copy Tray > Copy to Next Empty Slot** (`Ctrl+Alt+Y`) copies the
selection to the first slot, from 1 to 12, that is empty and not pinned, and
tells you which: "Copied to slot 4 (first empty)." If all twelve slots are
full, QUILL tells you so and overwrites nothing.

**Edit > Copy Tray > Copy to Tray Slot...** (`Alt+Shift+Y`) lets you choose
the slot yourself, from a list. Each row says what is in that slot now, its
label if it has one, and whether it is pinned, so you know what you would be
replacing before you replace it. Arrow to the slot and press Enter. QUILL
says "Copied to tray slot 3", or "Replaced tray slot 3" if something was
there already.

**Edit > Copy Tray > Search Tray Slots...** opens a small search box. Type a
word or phrase and QUILL searches the text and labels of every slot and reads
you the matches. Press the slot's number to paste it, or Escape to cancel.

### Pinned slots

In the Copy Tray dialog you can pin any slot. A pinned slot:

- Is never filled by Copy to Next Empty Slot.
- Is read with "pinned" in front: "Slot 1 (pinned, signature)".
- Stays pinned after a restart (the pin is saved in `copy_tray.json`).

To pin or unpin a slot, open the Copy Tray dialog (`Ctrl+Alt+V`), choose the
slot, and press the Pin/Unpin button.

### The Copy Tray dialog

Open it with `Ctrl+Alt+V`, or **Edit > Copy Tray > Open Copy Tray...**. It
lists all twelve slots. Each row has the slot number, a label if you gave it
one, and a preview of the text. Move with the arrow keys. The buttons are:

- **Paste** puts the chosen slot's text at the cursor. Enter or a double-click
  on a row does the same.
- **Paste from Clipboard** stores what is on the Windows clipboard in the
  chosen slot.
- **Pin / Unpin** pins or unpins the chosen slot.
- **Save Changes** keeps edits you typed straight into the content area.
- **Clear Slot** empties the chosen slot.
- **Close** closes without pasting.

To empty every slot at once, choose **Edit > Copy Tray > Clear All Tray
Slots** (`Ctrl+Alt+Shift+Y`). QUILL asks first and tells you how many slots
have something in them, with **No** already chosen, because this cannot be
undone. If the tray is already empty, it just says so.

### Other ways to reach the tray

- **The Paste from Slot rows.** **Edit > Copy Tray** has twelve rows, from
  **Paste from Slot 1** to **Paste from Slot 12**. A slot that has something
  in it shows its label and a preview on its row: "1 signature, Hi, I wanted
  to follow...". Your screen reader reads both as you move through the
  submenu.
- **The status bar.** The `Slots: X/12` cell shows how many of the twelve
  slots are in use. Click it to open the Copy Tray dialog. If you cannot find
  it, add it in **Tools > Customize and Support > Status Bar Layout...**.
- **The system tray.** QUILL's icon in the system tray has a Copy Tray
  submenu listing every slot in use. Choose one to paste it into the active
  editor, without bringing QUILL to the front first.

### Copy Tray tips

- Put a signature, a disclaimer or a heading you use all the time in slot 1
  and pin it. One chord pastes it anywhere, and Copy to Next Empty Slot will
  never overwrite it.
- Label your slots for a research session: slot 1 "intro quote", slot 2
  "methodology note", slot 3 "source URL". Copy one piece into each as you
  read, then paste them in order as you write.
- Slots survive restarts, so you can keep a small set of pieces you reach for
  every day.
- You can change every Copy Tray key in the Keymap Editor (**Tools > Customize
  and Support > Keymap Editor...**).

## Clip Library

The twelve Copy Tray slots are for things you chose to keep. The **Clip
Library**, on the **Edit > Copy Tray** submenu, is a second, bigger store: a
searchable history of up to 200 clips.

- **Edit > Copy Tray > Keep Selection in Clip Library** (`Ctrl+Alt+M`)
  remembers the current selection. Keeping the same text again from the same
  place does nothing, because it is already there.
- **Edit > Copy Tray > Open Clip Library...** (`Ctrl+Alt+Shift+M`) opens the
  library.
  Search as you type, **Favorite** a clip so it is never pushed out as the
  history fills up, **Remove** one you no longer need, **Copy to Clipboard**,
  or **Promote to Copy Tray...** to give a clip a labelled slot of its own.
- **Rename...** gives a clip a short name, which is much easier to find later
  than its first few words. Leave the name empty to go back to a preview of
  the text.
- **Combine Marked...** joins several clips into one piece of text. Mark them
  with Ctrl or Shift (plain arrow keys still choose just one), choose what goes
  between them (space, comma, full stop, vertical bar, new line or blank line),
  and the joined text goes on the clipboard in the order the clips are listed.
- **Save as Abbreviation...** turns a clip into an abbreviation. QUILL and
  Quill Inkwell share one abbreviation library, so a clip saved this way can be
  typed in every program, not just here.

**Automatic capture.** Turn on **Settings > Editing > "Automatically keep
everything you copy in the Clip Library"** (off at first) and every copy you
make inside QUILL is kept for you, whether you used the menu, its key or a
right-click Copy. It only sees copies made in QUILL, never the system
clipboard in general, and never anything you copied before you turned it on.

**Format.** What Copy to Clipboard puts on the clipboard, and what Send as
Email and Copy as Email Body send, both follow one setting: **Settings >
Editing > "Kept and sent content format"** (plain text, Markdown or HTML).
Change it once and both follow.

**What the Clip Library is not.** It remembers what you keep or copy *inside
QUILL*. It does not watch the system clipboard, and it keeps no history of
what you copy in other programs. For a clipboard history across everything
you do, use a clipboard manager alongside QUILL. The two do different jobs.

## Copy With Source

`Alt+Shift+C` copies the selection and adds a note of where it came from in
the document. With nothing selected, QUILL copies the current line. This is
handy for notes, reviews and gathering evidence.

In a Markdown document you can choose what goes on the clipboard, under
**Settings > Editing > Markdown clipboard format**. **Plain text only** (the
default) copies the Markdown just as you wrote it. **HTML** or **Rich text**
adds a formatted copy as well, so when you paste into Word or an email the
headings, bold and links arrive formatted. Notepad and other plain-text
programs still get the plain text.

## Links

`Ctrl+K` adds a link written the right way for the document's format.
`Ctrl+Enter` with the caret on a link follows it. In Markdown and HTML this makes
citations and cross-references much less work.

## The Insert menu

The **Insert** menu puts structured content at the cursor. QUILL treats
Markdown and HTML as everyday writing formats, so the tag pickers sit here
next to the other inserts.

- **Insert Link...** adds a link in the right form for the document's format.
- The **Heading** submenu: Heading 1 through 6, **Decrease Level** and
  **Increase Level**, and **Style Headings...** (font, size and alignment) for
  the current level or all levels.
- **Body Text** (`Ctrl+Alt+0`).
- The **List** submenu: **Bullet**, **Numbered**, **Task**, **List
  Manager...** and **Structured List Studio...** (`Ctrl+Alt+Shift+L`).
- **Insert Code Block**, **Insert Footnote**, **Insert Table...**, **Insert
  Block Quote**, **Insert Horizontal Rule**, **Insert HTML Tag...** and
  **Insert Markdown Tag...**.
- **Date and Time** (`F5`) and the **Date and Time** submenu.
- **Insert Snippet...** and **Manage Snippets...** for reusable text with
  blanks to fill in.
- **Special Character...** (`Ctrl+Shift+F2`).
- **Line Break** (`Shift+Enter`), described under Writing and editing at the
  start of this chapter.
- **Insert Emoji...** (`Alt+.`).
- **File Content...** inserts the contents of another file at the cursor.
- **Insert Equation...** (`Ctrl+Alt+=`).

The topics below explain the ones that need more than a line.

### Headings and lists

**Heading N sets the level, it does not add one.** `Ctrl+Alt+2` on a line
that reads `### Notes` gives you `## Notes`, not `## ### Notes`. It works from
anywhere on the line, not just the start. With several lines selected, it
makes **all** of them headings in one change, so a single `Ctrl+Z` puts them
all back. Your screen reader says "Heading 2" either way, so it is good to
know QUILL gets this right.

**Body Text** (`Ctrl+Alt+0`) is the bottom rung of the `Ctrl+Alt+1` to `6`
heading ladder. It takes the heading marker off and leaves the words.

**Next Heading** is `Ctrl+Alt+H` and **Previous Heading** is
`Ctrl+Alt+Shift+H`. `Ctrl+Alt+L` opens the **Outline Navigator**, the same key
QUILL Lite uses for List Headings, so either habit works, and `Ctrl+Shift+O`
opens it too. **AI Thesaurus** no longer has a key of its own; reach it from
the AI menu or the Command Palette. The plain **Thesaurus** keeps Word's
`Shift+F7`.

Bullet lists are on `Ctrl+Shift+L` and numbered lists on
`Ctrl+Shift+Grave, Shift+L`.

### Format-aware inserts

Block quote, horizontal rule, table and image write Markdown in a Markdown
document and HTML in an HTML document. If the document's format is not set yet
(a new or plain document), QUILL asks **"Markdown or HTML?"** the first time,
then remembers your answer for that document and stops asking.

A table is the one insert that also has a rich text form: in a rich text
document **Insert Table** makes a real table, a grid your screen reader, Word
and WordPad all read as a table, not rows of `|` characters.
[Moving through a table cell by cell](quill-guide-06-moving-around-and-finding-things.html#moving-through-a-table-cell-by-cell)
covers reading and editing it.

Some have keys of their own:

- **Insert Table** is `Ctrl+Alt+T`.
- **Insert Block Quote** is the same command as **Quote Lines**
  (`Ctrl+Shift+Q`), because both wrote the same `> ` in Markdown.
  **Unquote Lines** (`Alt+Shift+.`, that is Alt, Shift and the period) takes
  the `> ` off again.
- **Insert Horizontal Rule** is `Ctrl+Alt+-`.

You can change all of them in the Keymap Editor.

**Insert Markdown Tag appears only in Markdown documents.** In a plain or
rich text document it is not on the menu at all, and if you press its key
there, QUILL just says "Markdown tags are for Markdown documents."
**Insert HTML Tag** is the same idea for HTML, except that it stays on the menu,
dimmed, in any document that is not HTML. **Navigate > Set Document
Language...** changes what kind of document you are in.

### Special Character (Ctrl+Shift+F2)

**Special Character...** opens a picker for the 357 characters a keyboard has
no key for. Search by name (`dash`, `euro`, `acute`, `arrow`) or by a word
people use even if Unicode does not (`gbp`, `copyright`, `eszett`). Or clear
the box and browse one of fifteen groups: whitespace, dashes, quotes,
invisibles, typography, legal and reference marks, currency, maths and units,
fractions, superscripts and ordinals, arrows, accented letters (small and
capital), Greek, and punctuation from other languages.

Each row shows the character, its name and its code point, and a description
pane changes as you arrow. **The search box is also the code-point box**:
`2014`, `U+2014` and `d8212` all find the em dash, and a code point that is in
no group still works, so the picker reaches every character Unicode has. When
you insert one, QUILL tells you what it was, in Describe Character's words,
because most of these characters cannot be seen on the page.

In both QUILL and QUILL Lite the picker is on **Insert > Special Character...**
(`Ctrl+Shift+F2`).
Both keys can be changed in the Keymap Editor.

### Insert Equation (Ctrl+Alt+=)

**Insert Equation...** (`Ctrl+Alt+=`) asks for a LaTeX or MathML equation in
up to two steps.

1. Type the formula in LaTeX, for example `E=mc^2` or
   `\frac{-b \pm \sqrt{b^2 - 4ac}}{2a}`, or paste a MathML fragment.
2. For LaTeX, choose whether it sits inline in the text (`\(...\)`) or as a
   block of its own (`$$...$$`).

If a LaTeX equation is already selected when you open Insert Equation, QUILL
takes off its delimiters and puts the bare formula in the box for you. MathML
(anything starting with `<math`) goes in exactly as typed, with no second
step. Browser Preview and HTML export show equations as MathML, which needs
nothing from the internet and which your screen reader can read. Math
Equations, later in this guide, has the formula gallery, symbol
abbreviations, exploring an equation part by part, and Word export.

### Word prediction and snippets

Word prediction and snippets are kept apart, so each has its own key.

1. Press `Ctrl+.` to open **Word Prediction** (also **Edit > Word
   Prediction...**).
2. Type, and matching words from your document, HTML tags and Markdown tags
   appear.
3. Arrow to the one you want and press Enter to insert it.

To set up and look after snippets:

- Press `Ctrl+Shift+Grave, S` for **Insert Snippet**.
- Press `Ctrl+Shift+Grave, Shift+S` for **Manage Snippets** (create, edit,
  delete, import, export, and starter packs).
- Open **More Preferences > Install Starter Snippet Packs** for sample sets for
  everyday writing, developer work, support and accessibility notes, and
  Mermaid diagrams.
- In **General Preferences**, turn **Word prediction and tag IntelliSense** or
  **Expand snippet triggers while typing** on or off as you like.

Snippets can have blanks such as `${input:name}`, `${choice:a|b}`, `${date}`,
`${time}` and `${cursor}`. When a snippet has blanks to fill, QUILL asks them
all at once, in one small form: a labelled box for each `${input:...}` and a
list for each `${choice:...}`, in the order the snippet uses them. Tab moves
between them, Enter on the last one inserts the snippet, and Escape inserts
nothing. It is the same form abbreviation fields use, below.

**Finding a snippet by name.** In **Insert Snippet**, type any part of a
snippet's name, trigger or text, spaces included, and the list narrows as you
type. The words can come in any order: `notes meeting` finds "Meeting notes
for Tuesday" and "Notes from the meeting". Snippets whose name starts with
what you typed come first. Press Down Arrow to move into the list, Enter to
insert the top match or the one you are on, and Escape to cancel. The
Abbreviations manager's search box and **Search Tray Slots** match words in any
order in the same way.

**Large libraries.** With thousands of snippets, the list shows the first 200
matches, and the line above it says how many matched in all, for example
"4,980 matches; showing the first 200. Type more to narrow them." Every
snippet is still reachable: type a little more of its name. QUILL also waits
until you pause typing before it refills a long list, so typing a whole name
fills it once instead of after every letter. Enter never acts on an
out-of-date list.

**Diagram snippets.** The **mermaid-diagrams** starter pack has eight Mermaid
diagrams for Markdown documents: a flowchart, a sequence diagram, a class
diagram, a state diagram, an entity relationship diagram, a Gantt chart, a
mind map and a timeline. Install it from **More Preferences > Install Starter
Snippet Packs**: arrow to mermaid-diagrams and press Enter. Then open **Insert
Snippet** (`Ctrl+Shift+Grave, S`) and type `mermaid`, or type a trigger such
as `;mmflowchart` or `;mmsequence` in your document. Every one asks you two
questions before anything else: the accessible title and the accessible
description. Say what the diagram is called and, in a sentence or two, what
it shows. They are written into the diagram as `accTitle` and `accDescr`,
which is what a screen reader gets when the diagram is shown as a picture in
a web page. The remaining questions fill in the first parts of the diagram,
and the cursor is left where you carry on typing. The Accessibility Tune-Up,
in the accessibility chapter, checks diagrams you write yourself.

**Typing a name in a list.** In lists you arrow through, such as Copy Tray,
Open Recent, bookmarks and most other pick-one lists, you can type the start of
a row's name, spaces included, to move to it. While you are typing a name,
Space is part of the name; after a pause of about a second, Space on its own
opens the selected row as before. Enter always opens the row and Escape always
closes the list.

### Date and time

**Date and Time** (`F5`) types the time and date at the caret and reads it
back to you. It uses Notepad's key and Notepad's layout (`14:07 16/09/2026`),
and QUILL Lite's too. It is built into QUILL, so it works in **Safe Mode**
as well.

**Insert > Date and Time** is also a submenu. The bundled Insert Tools
Quillin (`com.quill.bundled.insert-tools`) adds three items to it:

- **Insert Date** puts today's date at the cursor, in the format `${date}` uses.
- **Insert Time** puts the current time at the cursor, using `${time}`.
- **Insert Date and Time** puts both, with one space between them.

Those three are part of the Insert Tools Quillin, so they switch off with the
rest of it, and in Safe Mode. If you turn the Quillin off, the submenu stays
but its three items go. Turn it on or off in **Preferences > Quillins**, for
example if you would rather use date and time snippets of your own.

### Insert Emoji (Alt+.)

**Insert > Insert Emoji...** (`Alt+.`) opens the Accessible Emoji Picker. It
is for the opposite case from **Special Character...**: you do not know the
code, and you want help finding the right one. You can browse or search all
3,781 standard emoji by name, keyword, symbol or a typed smiley like `:)`, and
each has a real spoken description of what it looks like. There is no grid of
pictures anywhere in it. It is a category list and a list of named results,
like QUILL's other browse-and-search windows.

There are two ways to find an emoji.

- **Search** (the box at the top) looks, in this order, for: the emoji itself
  if you paste or type one in; an old typed smiley like `:)`, `:D` or `<3`;
  part of the official Unicode name or a keyword (for example "grin", "dog"
  or "heart"); and last, part of the emoji's description. So a half-remembered
  word like "melting" or "puddle" can still find the right one even when it is
  not a keyword.
- **Category** (the list on the left) follows Unicode's own groups, largest
  first:

  | Category | Emoji |
  | --- | --- |
  | People & Body | 2,261 |
  | Flags | 270 |
  | Objects | 264 |
  | Symbols | 224 |
  | Travel & Places | 218 |
  | Smileys & Emotion | 169 |
  | Animals & Nature | 159 |
  | Food & Drink | 131 |
  | Activities | 85 |

  Clearing the search box takes you back to the category you chose last.

As you arrow through the results, the **Description** pane shows the emoji's
category and subgroup, its official name, its keywords, any old typed smiley,
and one or two sentences about what it actually looks like: colours, shapes,
expression and pose, not just its name again. Press **Insert**, or Enter on a
result, to type the emoji at your cursor and close the picker. **Cancel** or
Escape closes it without inserting anything.

**Favorites and Recent** sit above the nine Unicode categories:

- **Favorites** lists the emoji you have starred. Choose any emoji, from a
  category, a search or Recent, and press **Add to Favorites**. Once it is a
  favourite the button reads **Remove from Favorites**.
- **Recent** fills itself with the last 30 emoji you inserted, newest first.

Taking an emoji out of Favorites, or letting it drop off Recent, only changes
those two lists. The emoji is still in the picker, under its category and in
search, as before.

All 3,781 emoji, with their categories, keywords, typed smileys and
descriptions, come in one file installed with QUILL. The picker never goes
online, in Safe Mode or otherwise. The PRD's Accessible Emoji Picker section
explains how the catalogue is kept up to date.

The full list, with every description, is in Appendix C, Every emoji QUILL can
insert.

## Abbreviation Expansion

Abbreviation Expansion types longer text for you, like TextExpander. You type
a short trigger word followed by a space, full stop, comma or other
punctuation, and QUILL quietly replaces the trigger with the full text. For
example, type `btw ` (with the space at the end) and QUILL changes it to
`by the way `.

**It is off by default**, so your text never changes as you type unless you
asked for it. Turn it on when you want it; QUILL remembers your choice.

### Turning it on and off

Any of these turns it on, and the same again turns it off:

- Press `Alt+Shift+A`, or choose **Insert > Toggle Abbreviation Expansion**.
- Click the **ABR: On / ABR: Off** cell in the status bar, if it is showing
  (add it in the status bar settings).
- Change **Abbreviation expansion** in **Settings > Editing**.

### The built-in abbreviations

QUILL comes with fifteen abbreviations for common shorthand. You can edit or
switch off any of them, and add your own.

| Abbreviation | Expansion |
| --- | --- |
| `afaik` | as far as I know |
| `afaict` | as far as I can tell |
| `asap` | as soon as possible |
| `atm` | at the moment |
| `btw` | by the way |
| `fwiw` | for what it's worth |
| `imo` | in my opinion |
| `imho` | in my humble opinion |
| `irl` | in real life |
| `omw` | on my way |
| `tbh` | to be honest |
| `tbc` | to be confirmed |
| `tbd` | to be determined |
| `ttyl` | talk to you later |
| `wrt` | with regard to |

### Managing your abbreviations

Open **Insert > Manage Abbreviations...** (`Ctrl+Shift+Grave, Shift+A`) to
add, edit and organise your abbreviations. Each one has:

- **Abbreviation**: the short trigger word, such as `btw`.
- **Expansion**: the full text that replaces it, such as `by the way`.
- **Description**: an optional note for yourself.
- **Case sensitive**: when checked, only the exact capitals match. Otherwise
  any capitalisation of the trigger works.
- **Enabled**: switch one off without deleting it.
- **Category**: any word you like (Work, Personal, Email) to group the list.
  There is a category filter beside the search box, and abbreviations with no
  category are listed under Uncategorised.
- **Expand after**: which keys set it off. A space or punctuation (the
  default), a space only, punctuation only, or never. **Never** means it only
  expands from Quick Insert, which suits a long expansion you would not want
  to appear by accident.
- **Speak**: what your screen reader says when it expands: nothing, the
  abbreviation, or the expanded text. You set this for each one, because a
  short one usually needs no announcement and a long template sometimes does.
- **Sound**: follow the main sound setting, always play, or never play.
- **Add a trailing space after punctuation**: adds a space after the
  punctuation that set it off, so `co.` gives `Company, ` and not
  `Company ,`. It makes no difference after a space, which already leaves one.

The **Search** box at the top of the manager filters the list as you type
any part of a trigger or its expansion. Switched-off abbreviations show
"(disabled)" after their name.

**Import** and **Export** read and write your library as a JSON file. Export
saves the whole library. Import adds a file's abbreviations to yours, skips
any it already has, and tells you how many it added.

### Other ways to use an abbreviation

- **Expand now.** Press `Ctrl+Shift+Grave, A` (or **Insert > Expand
  Abbreviation**) to expand the word just before the cursor without typing a
  space or punctuation. Useful in the middle of a word or at the very end of
  a document.
- **Quick Insert.** **Insert > Quick Insert...** opens a list of every
  switched-on abbreviation, with the ones you use most at the top and a
  preview of each expansion. Type a few letters, arrow down, press Enter, and
  the expansion goes in at the cursor. It is how you use an abbreviation you
  have not memorised, and the only way to reach one set to expand after
  Never. It has no key at first, but you can give it one in the keyboard
  settings, and it is in the Command Palette.
- **New Abbreviation from Clipboard.** **Insert > New Abbreviation from
  Clipboard...** opens a new abbreviation with the clipboard text already in
  the expansion, so all you add is the trigger. It is the quickest way to turn
  a signature, an address or a block of standard wording into an
  abbreviation.

### Abbreviations in every program, with Quill Inkwell

Your abbreviations also work in other programs through **Quill Inkwell**, a
small free companion app that sits in the system tray. It uses the very same
library file as QUILL. Add an abbreviation here and it works in your browser;
add one there and it works here. Open it from the QuillVille menu, and see
Quill Inkwell's own user guide for where it will and will not type.

**Abbreviations for certain programs only.** You can limit an abbreviation to
named programs, such as a signature to your mail program or a code snippet to
your code editor, by listing them in its **Applications** field. Leave the
field empty, as it is at first, and it works everywhere. This only matters in
Quill Inkwell, which types into whatever program you are in. Inside QUILL
there is only one program, so the field has no effect there. If Inkwell cannot
tell which program is in front, a limited abbreviation does **not** fire, so
it never types into the wrong place.

### Variables in expansions

An expansion can include these:

| Placeholder | Inserts |
| --- | --- |
| `${cursor}` | Puts the cursor here after expanding |
| `${date}` | Today's date (for example June 11, 2026) |
| `${time}` | The current time (for example 02:30 PM) |
| `${clipboard}` | The text on the system clipboard |
| `${datetime}` | The date and time together |
| `${day}` | Day of the month |
| `${month}` | Month name |
| `${year}` | Four-digit year |
| `${username}` | Your Windows user name |

### Fields that ask you something

A signature is the same every time. A letter or a bug report is the same
*except* for a name, a date or a reference number. Put a field in the
expansion and QUILL asks for it before inserting:

- `${field:Label}` asks for a value with that label. `${input:Label}` does
  the same thing, in the spelling snippets use, so a blank copied from a
  snippet still asks.
- `${field:Label=something}` offers a starting value you can keep or change.
- The same label used twice is asked once and filled in everywhere, so a name
  in the greeting also appears in the sign-off.
- `${choice:Label|first reminder|second reminder|final notice}` gives you a
  list to choose from instead of a box to type in. Use it whenever the answer
  is one of a few known ones: choosing is one arrow key, and you never have to
  spell "Second reminder" exactly right. The first option is the default.

A small form opens with one labelled control for each field, a box to type in
or a list to choose from, in the order they appear in the text. Tab moves
between them, Enter moves to the next one, Enter on the last one accepts, and
Escape cancels and leaves your text exactly as it was. `${cursor}` still
works alongside fields: the cursor lands where the template puts it once your
answers are in. Quill Inkwell shows the same form, so a template works the
same wherever you use it.

### Timing and sound

- **Multi-press window.** How quickly you must press a key twice or three
  times to count as a double or triple press is set in **Settings > Editing**
  as **Multi-press time window (ms)**. The default
  is 400 ms, and it can be anything from 100 to 1000 ms. Make it longer if you
  press keys slowly, or shorter if double presses happen by accident when you
  type fast.
- **Sound.** To hear a sound when an abbreviation expands, turn on **Play
  sound on abbreviation expansion** in **Settings > Editing**. You can point
  **Abbreviation expansion sound file**
  at a `.wav` file, or leave it empty for the standard system beep.

### Abbreviations from Quillins

Installed Quillins can add abbreviations of their own. You can switch each one
on or off on that Quillin's own preferences page: open **Preferences**
(`Ctrl+Comma`) and go to the Quillin by name. For the bundled Smart Insert
Quillin, they are on its **Abbreviations** tab. These are kept apart from
your own library and never saved into it, so removing a Quillin removes its
abbreviations too. Your own abbreviations always win over a Quillin's. If two
Quillins use the same trigger, the one loaded first wins. **They work in
other programs too**, through Quill Inkwell, so a Quillin full of medical
abbreviations or company wording is useful everywhere you type.

The bundled **Smart Insert** Quillin adds four abbreviations that expand as
you type:

| Trigger | Inserts |
| --- | --- |
| `qbug` | A bug report template (Title, Build, Screen reader, Windows version, Steps, Expected, Actual, Notes) |
| `qmeet` | A meeting notes template with today's date |
| `qlog` | A date and time stamp |
| `qtodo` | A three-item to-do checklist |

Only abbreviations with fixed text expand as you type. Ones that build their
text when used, such as Smart Insert's `qbrf`, do not fire from typing the
word. Use the matching smart trigger (`=brftest()`) or the Insert menu
command instead.

### Abbreviation tips

- Use `${cursor}` to put the cursor inside a template. For example, `sig`
  expanding to `Best regards,${cursor}Jeff` leaves the cursor just after the
  comma.
- Use case-sensitive abbreviations sparingly. Most triggers are lower case,
  and you rarely need it.
- Abbreviations expand before snippets. If a word is both, the abbreviation
  wins.
- Export your library now and then, as a backup and to copy it to another
  computer.

## AutoCorrect: fixing common misspellings as you type

AutoCorrect fixes the misspellings almost everybody makes, the moment you
finish the word. Type `teh` and a space, and QUILL changes it to `the `. Type
`recieve` and press `Enter`, and it becomes `receive` before the new line
starts. You hear the word-corrected sound and QUILL says "Corrected to the",
because your screen reader only echoes the space you typed and would otherwise
never tell you the word changed.

**It is off to begin with**, like everything else that changes your text
without being asked. Turn it on in **Settings > Editing > Correct common
misspellings as I type** (`Ctrl+,` opens Settings; type "misspell" in its
search box to jump there). QUILL remembers the choice.

### What it corrects

QUILL ships a list of about 350 common English misspellings, such as `teh`,
`recieve`, `seperate`, `definately`, `occured`, `untill`, `wierd` and
`adress`. Every one was checked against two English dictionaries (American
and British) before it went in: a word that is spelled correctly in either is
never on the list, and neither is a word that is also a real word or a name,
such as `calender` (a machine for pressing cloth) or `Sargent`.

QUILL keeps your capital letters. Some examples:

- `teh ` becomes `the `, and `Teh ` at the start of a sentence becomes
  `The `.
- `febuary ` becomes `February `, because the correction has its own capital.
- `(recieve, ` becomes `(receive, `. Brackets, quotes and punctuation around
  the word stay where they were.
- `TEH ` is left alone. A word typed all in capitals is far more often an
  abbreviation or an acronym than a mistake.

### What it never touches

AutoCorrect looks only at a whole word that a space or `Enter` has just ended.
It never changes:

- **Code and settings files.** Nothing is corrected in a file whose name
  marks it as code or configuration (`.py`, `.json`, `.yaml`, `.ini`, `.html`,
  `.csv` and the rest), the same list that keeps spell-check-as-you-type
  quiet in those files. Plain text (`.txt`), Markdown, rich text and new
  untitled documents are all corrected.
- **Web addresses, email addresses and paths.** A word with a full stop,
  slash, colon, `@`, digit or underscore inside it is never a misspelling, so
  `teh.example.com`, `adress@example.com` and `my_recieve_function` stay
  exactly as typed.
- **Code inside prose.** In a Markdown document, nothing inside backticks or
  inside a fenced code block is corrected.

### Taking a correction back

`Ctrl+Z` straight after a correction puts back exactly what you typed (the
correction and the space are one undo step). QUILL then leaves that word alone
in this window for the rest of the session: type the space again and the word
stays the way you wrote it, and the status line says "Kept teh as you typed
it". If you never want a correction again, turn it off in AutoCorrect Entries,
below.

### AutoCorrect Entries (Alt+Shift+9)

**Insert > AutoCorrect Entries...** (`Alt+Shift+9`) shows every correction,
the built-in ones and your own, one per row, read as a sentence: "teh becomes
the, built in". It is the same window, on the same key, in QUILL Lite.

- **Find** narrows the list as you type. Type `rec` and only the corrections
  with `rec` in the misspelling or the correction remain.
- **Corrections** is the list. `Enter` or `Space` on a row edits it.
- **Add...** makes a correction of your own. You type the word as you
  mistype it, what it should become, and whether case must match exactly.
  For example, add `qill` becoming `QUILL`, or `adn` becoming `and` if it is
  not already there. The word to correct must be letters only (an apostrophe
  inside is fine); what it becomes can be several words.
- **Edit...** changes the row you are on. Editing a built-in correction saves
  your version beside it, and the row then says "built in, changed by you".
- **Turn Off** stops the correction you are on without deleting it; the row
  then ends in "stopped", and the same button, now **Turn On**, starts it
  again. This is the answer when a correction keeps changing a word you meant.
- **Remove** deletes a correction of yours. On a built-in correction you
  changed or turned off, it puts it back the way QUILL shipped it. A built-in
  correction cannot be deleted, so Remove on one turns it off instead and
  tells you so.

Every button says what it did. Your changes are kept when you close the window
with **Close** or `Escape`.

### Where your corrections are kept

Your corrections are kept with your abbreviations, in the same
`abbreviations.json` file in QUILL's data folder, under the category
**AutoCorrect**. So **Back Up Settings** carries them, and you can see them in
**Manage Abbreviations** too (choose the AutoCorrect category). They are not
abbreviations, though: they never expand while only Abbreviation Expansion is
on, they do not appear in Quick Insert, and Quill Inkwell does not type them in
other programs. AutoCorrect works inside QUILL and QUILL Lite.

### Limits

- The built-in list is English only.
- A correction happens when a space or `Enter` ends the word. A word followed
  only by a full stop at the very end of your document is corrected when you
  type the space after the full stop.
- AutoCorrect fixes known misspellings, not every misspelling. Spell check
  (`F7`) and spell-check-as-you-type still find the rest.

## Insert Automation

Insert Automation ties abbreviations, smart text triggers, `.LOG` files and
append anchors together, all from the keyboard. Everything it does is
announced and can be undone, and it only acts on an exact match. Nothing runs
in the background, and nothing reads through your file unless you asked.

### Smart Text Triggers

A smart text trigger is a short command that starts with `=`, sits on a line
by itself, and expands when you press Enter. Because it starts with `=`, it
cannot go off by accident in the middle of a sentence.

The bundled **Smart Insert** Quillin comes with these:

| Trigger | Inserts |
| --- | --- |
| `=bug()` | A bug report template |
| `=meeting()` | Meeting notes with today's date |
| `=journal()` | A journal entry with today's date |
| `=todo()` or `=todo(5)` | A to-do checklist (5 items unless you give another number) |
| `=logentry()` | A time stamp at the cursor, in your Log Mode format |
| `=brftest()` | A predictable test document of several braille pages |
| `=rand(3,4)` | Three paragraphs of four readable sentences each |

**How to use one.** Type the trigger on a line by itself and press Enter. If
it matches, QUILL replaces the whole line with the new text and tells you what
it inserted. If it does not match, nothing happens and Enter works as usual.

**Large inserts.** If a trigger would produce more than a set amount of text
(50 paragraphs at first), QUILL asks before inserting anything. Change the
amount on the **General** tab of the **Smart Insert** page in More Preferences.

**Switching triggers on and off.** Every trigger can be switched on or off on
the **Smart Triggers** tab of that same Smart Insert page. A switched-off trigger's
`=name()` text is simply left on the line as you typed it.

### Log files that stamp themselves

If the first line of a text file is `.LOG`, QUILL treats it as a log with a
time stamp for each entry, just as Notepad has for decades.

When you open a `.LOG` file, QUILL:

1. Finds `.LOG` at the top of the file (within the first 4096 bytes).
2. Finds where the new entry belongs: a `QUILL-LOG-APPEND-HERE` anchor near
   the bottom of the file, or the end of the document if there is none.
3. Puts in a fresh time stamp.
4. Leaves the cursor just after it, so you can start typing.
5. Says "Log timestamp inserted. Type your entry."

QUILL never changes a read-only file. `.LOG` further down a file does nothing
on its own. A UTF-8 BOM before `.LOG` is fine.

**Time stamp format.** Choose it on the **Log Mode** tab of the Smart Insert page
in More Preferences:

- Long date and time (the default): `Sunday, June 14, 2026 9:42 PM`
- Short: `06/14/2026 09:42 PM`
- ISO 8601: `2026-06-14T21:42:00`
- Date only, Time only, or a custom `strftime` pattern

For example, set Timestamp format to Custom and enter `%Y-%m-%d %H:%M` to get
`2026-06-14 21:42`.

### Append Anchors

Any file can have a `QUILL-APPEND-HERE` line near the bottom. When QUILL adds
something that belongs at the end of the file, such as a log time stamp, a
template or a braille test block, it puts the new text just above the anchor
and leaves the anchor where it is for next time.

That gives you a fixed spot that keeps working. Footer notes, details or
closing instructions stay below the anchor, and new text always lands above
them.

A `.LOG` file can use the more specific `QUILL-LOG-APPEND-HERE` anchor to keep
log entries apart from other added text.

**To add an anchor,** type `QUILL-APPEND-HERE` on a line by itself near the
bottom of your file. That is all. QUILL finds it the next time it adds
something to that file.

## Look Up, Thesaurus and the Dictionary

Press the **Applications key** (or `Shift+F10`, or right-click) on any word
and the menu has two submenus named after that word.

- **Thesaurus for "running"** has the best replacements one key away, each
  further meaning as a submenu of its own, **Opposites**, **Say Word Summary**
  (what the thesaurus knows, spoken) and **More in Thesaurus...**.
- **Dictionary for "running"** starts with **Look Up "running"...** and, when
  AI is on, goes on with the thirteen AI dictionary items described under the
  AI menu.

If you have selected a single word, the menus use that word instead of the
one at the cursor.

### Thesaurus (Shift+F7)

**Thesaurus...** (`Shift+F7`, **Tools > Writing and Language**) opens a two-part window for
the word you are on, or asks you for one. It finds your word even when it is
not in its plain form. The thesaurus knows "run", not "running", and "happy",
not "happier", so QUILL works back to the plain word and tells you: in the
title ("running (as run)") and on each meaning ("verb, from run: sprinting,
dashing, ..."). It then gives each replacement back in the form your sentence
needs, with the same capitals: "sprinting" for "running", "More glad" for
"Happier", "sought" for "sought".

You start in the Senses list, with the part of speech first, so type **n** for
the nouns or **v** for the verbs. Tab moves to the words for the chosen
meaning: replacements, then *broader:* and *opposite:* words, each labelled.
Enter or **Replace** puts the chosen word in and drops the selection.

Press `Ctrl+Alt+Shift+[` for **Say Word Summary**: it reads you the plain word,
its meanings for each part of speech, the first few replacements and the
opposites, without opening anything. It has no menu item; besides the key, you
can find it as "Word Summary" in the Command Palette (**Tools > Command
Palette...**, `Ctrl+Shift+P`). QUILL Lite has the same thesaurus.

### Look Up Word (Alt+F10)

**Look Up Word...** (`Alt+F10`, **Tools > Writing and Language**) is the dictionary
without AI, in a window QUILL Lite shares. You start in the **Result**, a
read-only box you arrow through: the word, then a labelled section for each
kind of answer. Below it, **Words you can use** lists every synonym,
opposite, related word and rhyme, each saying which it is.

- Enter or **Replace Word** puts the chosen word in place of yours.
- **Copy** copies the chosen word, or the whole result.
- **Add to Dictionary** adds the word to your personal dictionary.

Offline, Look Up uses the thesaurus and nothing leaves this computer. The
**Use online sources** checkbox is off until you check it. When it is on, the
word, and only the word, never your sentence or document, goes to three free
services that need no account:

- the Free Dictionary, for definitions with examples
- Datamuse, for more synonyms, opposites, rhymes and related words
- **Wikipedia**, for a short summary with a link to the article (a word with
  no real article, or a page that only lists other meanings, shows no
  encyclopedia section)

The offline answer appears straight away and QUILL says "Looking up online".
When the online answer arrives it replaces the box, and QUILL tells you. Your
choice is remembered as `dictionary_online_lookups` in the settings file.
Uncheck the box and the next lookup is offline again.

Chapter 7, Spelling and words, has more on spelling and the dictionary.

## Sending your writing somewhere else

### Send as Email and Copy as Email Body

**File > Send as Email** opens your usual mail program with the selection, or
the whole document if nothing is selected, as the message. **File > Copy as
Email Body** prepares the same text and puts it on the clipboard instead. Use
that when your mail program cuts off or refuses a very long message. Both
follow the same format setting as the Clip Library. Copy as Email Body is also
on the QUILL key: press the QUILL key and then `C` (**Copy Selection For
Email**).

### Using QUILL as an external editor

Some programs, such as Thunderbird, can hand a draft to another editor and
take it back when you are done. QUILL opens one window per file and closes
when you close it, which is exactly what those programs expect, so QUILL
needs no special setup. For Thunderbird:

1. Install the **External Editor Revived** add-on in Thunderbird (Tools >
   Add-ons and Themes, then search for it). It also needs a small companion
   program, and its own setup page walks you through that.
2. In the add-on's settings, set the editor to QUILL's full path. On Windows
   this is usually
   `C:\Users\<you>\AppData\Local\Programs\QUILL for All\quill.exe`. Copy the
   exact path from the Target field of your QUILL shortcut.
3. Write a message and press the add-on's edit-externally key (`Ctrl+E` in
   Thunderbird, unless you changed it). Your draft opens in QUILL with
   everything QUILL offers: spell check, read aloud, AI tools and braille.
   Save (`Ctrl+S`) and close QUILL, and the text goes back into Thunderbird's
   message window.

The same steps work with any program that opens an editor on a file and reads
it back when the editor closes.

## AutoOutline numbered headings

**Format > Line > Update Outline Numbering** numbers every heading in your document
by its level, typed as real text at the start of the heading:

- **Numeric** (the default): `1`, `1.1`, `1.2`, `2`, `2.1`...
- **Legal**: `I`, `I.A`, `I.B`, `II`...

Choose the style in **Settings > Editing > "AutoOutline numbering
style."** Because the numbers are real text, they are read aloud, survive copy
and paste, and export with nothing to set up. Add, remove or move headings,
then run **Format > Line > Update Outline Numbering** again. It replaces the
old numbers instead of adding new ones in front. **Format > Line > Remove
Outline Numbering** takes them out again.

## Work Personas

A **Work Persona** is a named set of things you use together: a feature
profile, a working folder, some favourite files and, if you like, a keymap
profile. Make one for each part of your work, such as school, a freelance
client or a novel, and switch to it in one step.

Open **Tools > Work Personas...** to manage them.

1. Choose **New Persona**.
2. Type a name, pick a feature profile, browse to a working folder, add your
   favourite files and, if you want, choose a keymap profile.
3. Choose **Save**.

Then:

- **Apply Now** switches your feature profile, changes your working folder,
  reopens your favourite files and applies the keymap, all in the current
  session. Keymap changes take effect the next time you start QUILL.
- **Generate Shortcut...** makes a launcher you can double-click to open
  QUILL straight into that persona, even when QUILL is not running. On Windows
  it is a real shortcut where possible, or a `.bat` file otherwise. On macOS
  it is a `.command` file you open from Finder, which starts QUILL in
  Terminal.
- From a command prompt or another shortcut, `quill --persona "Persona Name"`
  does the same.

A persona is for one person's different kinds of work. It is not a separate
user account, and it does not replace Story Studio, Notebooks or the Copy
Tray, though a persona can point to any of them.

## Typing stays ahead of you

QUILL is built so that your next keystroke never has to wait. Between one
character and the next, it does only three things: updates your text,
refreshes the modified marker, and quietly sets the status line.

Everything else, such as the side preview, the spelling hint, word
prediction, getting browse mode ready, language detection, turning menu items
on and off, and autosave, waits until after your screen reader has been told
about the character. QUILL waits for a fifth of a second of quiet first, and
if you type faster than that it skips the work until you pause. So the faster
you type, the less QUILL does between keystrokes.

The status bar's word count, line and column, and progress cells also update
in those pauses, using the text QUILL already holds. And the abbreviation
feature only touches the Windows clipboard, which every program and your
screen reader share, at the moment an abbreviation that uses `${clipboard}`
expands.

This matters most with a screen reader. NVDA and JAWS speak the character you
typed when they get a signal from the same part of QUILL that does this work.
Anything done between keystrokes is heard as a delay before the character,
and if enough builds up, as keystrokes running together. A missing space
between words is usually the first sign. If you ever notice that in a very
large document, please report it rather than changing your screen reader
settings: it means something is slowing down typing that should not be.

## The Editing page in Settings

Most of the **Editing** page in Settings (`Ctrl+,`) is described where the
feature itself is. These are the rest:

- **Enable soft wrap** wraps long lines to the width of the window. It is on
  to begin with, and `Alt+Z` turns it on and off as you work.
- **Auto-fill numbered list markers** writes `1.`, `2.`, `3.` in front of
  every item when you insert a Markdown numbered list, instead of only the
  first. It is off to begin with, but QUILL does it anyway while you are in a
  Markdown document, and for five minutes after you turn a numbered list on.
- **Backspace after expansion** decides what `Backspace` does straight after
  an abbreviation expands: **Delete the expanded text** (the default) or
  **Revert to the typed abbreviation**.
- **Enable persistent undo** keeps a saved file's undo history from one
  session to the next. It is off to begin with; Chapter 13 has more.
- **How to open CSV files** is **Ask each time** (the default), **Plain
  text** or **Grid**.
- **How to open Word files** is **Ask each time** (the default), **Plain
  text** or **Structured**.
- **Autosave interval (seconds)** is how often QUILL autosaves the open
  document, from 5 to 600 seconds. The default is 30.
- **Autoformat straight quotes to curly** turns straight quotes into curly
  ones as you type. Off to begin with.
- **Autoformat double hyphen to dash** turns two hyphens into a dash as you
  type. Off to begin with.
- **Correct common misspellings as I type** turns on AutoCorrect, which
  changes `teh` to `the` when you type the space after it. Off to begin with;
  Chapter 4's AutoCorrect section has the details.
- **Continue lists in plain text** makes `Enter` continue a list in a plain
  text document the way it always does in Markdown. Off to begin with; see
  Typing in a list in Chapter 5.
- **Multi-press time window (ms)** is how long QUILL waits for a second or
  third press of the same key before it treats the first as a single press.
  It matters for the Copy Tray and Command Palette keys that do something
  different when pressed twice, and for Document Statistics (`Ctrl+Shift+G`),
  whose second press adds the full writing report. The default is 400. Fast typists may like
  300, and 500 gives you more time.

## What you learned, and where to go next

You now know the everyday editing keys, how to select by anchor, by structure
and with marks, and how to get deleted text back or repeat a command. You met
the Copy Tray and the Clip Library, the Insert menu with its special
characters, equations, snippets, dates and emoji, and abbreviations, smart
triggers and log files that do some of the typing for you.

To practise, open **Help > Tutorials...** (`Ctrl+Alt+F1`) and try "Select,
mark, and move text" and "Spelling, words, and the thesaurus" from the
Writing and editing track.

Next, Chapter 5, Formatting, structure and markup, shows how to give your
writing shape: headings, lists, tables and formatting.

---

- Previous: [Chapter 3: Opening, saving and converting files](quill-guide-03-opening-saving-and-converting-files.html)
- Next: [Chapter 5: Formatting, structure and markup](quill-guide-05-formatting-structure-and-markup.html)
- [Contents](../userguide.html)
