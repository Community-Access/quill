# Chapter 8: What you hear

QUILL Lite talks to you through your screen reader, and plays small sounds
when things happen. This chapter explains what it says and what it leaves to
your screen reader, how to make it say less, a few keys that answer quick
questions, how to silence or change its sounds, and how to catch up on
something you missed while your attention was elsewhere.

## Speech

QUILL Lite talks through your screen reader, **NVDA or JAWS**. It has no voice
of its own, so you never get two voices talking over each other.

### What it says, and what it leaves to your screen reader

QUILL Lite tries to say as little as it can. Your screen reader already tells
you window titles, where focus has moved, the names of buttons and what you have
selected. QUILL Lite only tells you the things only it knows: that a save
happened, that a search went back to the top, that bold went on, that four
things were replaced.

### Hearing a message again

Everything QUILL Lite says also goes into the first part of the status bar. If
you missed something, press **F6** to hear it again. The guided tutorial *What
to press when you are lost* shows you this.

If no screen reader is running, QUILL Lite does not speak at all, but every
message is still in the status bar.

### If it says too much

If you hold a key down, QUILL Lite can talk faster than anybody can listen. To
calm it down, go to **Preferences > Shortest gap between spoken messages**. It
is a number of milliseconds. Anything QUILL Lite would say sooner than that
after its last message is skipped. Zero, the default, says everything as it
happens. You do not lose anything by raising it: the status bar still gets
every message, and **F6** reads it back.

### On a braille display

Everything QUILL Lite says also goes to a connected braille display, through
NVDA or JAWS, right after it is spoken. Dictation's live preview, the words
heard so far, goes to the display only.

**A burst settles instead of flickering.** When several different messages
arrive quickly, the first appears on the display at once, and the rest are
replaced, a moment later, by the newest one. Before, each message replaced the
last as fast as it arrived, so while you dictated, or while a quick run of
status changes went by, the display changed faster than a finger could read
the first cell. QUILL has worked this way for a long time; QUILL Lite now uses
the very same code.

For example, dictate "please send the minutes by Friday". Your display shows
the first words as they are heard, then, a fraction of a second after you
pause, the whole phrase, instead of a blur of half-phrases in between.

**Speech is not affected.** Every message is still spoken the moment it
happens; only the display waits. The status bar still records every message,
so **F6** reads back anything the display skipped over. If a message cannot be
spoken (no screen reader is running), it is not brailled either.

### What formatting is here?

Press **Ctrl+Shift+D** (**Format > Describe Formatting at Cursor**) to hear the
formatting where your cursor is. It is a quick way to check what a sighted
reader would see at a glance.

What you hear depends on the kind of document:

- In a **rich text** document you hear the real formatting, for example
  *"Arial, 14 point, bold, centred."*
- In a **Markdown** document it reads the markup around your cursor. Inside
  `**bold**` it says bold, and on a `##` line it says Heading 2.
- In a **plain text** document it tells you it is plain text, because there is
  no formatting to describe.

#### Two smaller questions

- **Ctrl+Shift+C** (**Describe Character**) names the character under the
  cursor. Use it to tell a hyphen from a dash or a minus sign, which most
  screen readers read the same way.
- **Ctrl+Alt+Shift+V** (**Describe Indent Depth**) tells you how far the
  current line is indented, and whether with tabs or spaces.

### How big is this document?

Press **Ctrl+Shift+G** (**View > Document Statistics**) to hear the size of the
whole document, for example *"1,240 words, 7,315 characters, 96 lines."*

The same numbers are in the status bar, but this is quicker than going there to
find them.

**Ctrl+Alt+W** (**Line Statistics**) does the same for just the line you are on,
or for what you have selected.

### What time is it?

Press **Alt+Shift+Space** (**Tools > Say Time and Date**) and QUILL Lite says
the time, the way a clock reads it: *"2:05 PM."* Press it twice, quickly,
within half a second, and you hear the date in full: *"Friday, November 6,
2026."* The first press is answered straight away, so you never wait for it.
It is quicker than finding the clock in the system tray, and you stay in your
document. The row has no access letter on the Tools menu; the key is the way
to reach it.

### How many documents are open?

Press **Ctrl+Shift+Space** (**Window > Say Windows Open**, or
**Alt+W**, then **S**) to hear how many documents you have open: *"3 documents
open."* Press it twice, quickly, and you hear their names, in order, with the
one you are in marked: *"3 documents: notes.txt (current), chapter 2.docx,
letter.md."* It is a fast check before you close QUILL Lite, without walking
the Window menu.

QUILL has both of these, on the same keys.

One more key of the same kind is about the clipboard: **Alt+Shift+Home**
(**Say Clipboard**) reads what you copied without pasting it. Chapter 5 has
the details.

## Sounds

QUILL Lite plays small sounds to let you know things happened. You can silence
them all at once, or change them one by one.

### Where QUILL Lite's sounds play, and turning them off

QUILL Lite makes short sounds of its own. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns QUILL Lite's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Tools > App Sounds** has a check mark that shows whether they are on.
- **Tools > Sound Scheme...** (**Ctrl+Alt+Shift+O**) opens the Sound Scheme window; its **App Sounds Play On...** button lets you pick where they play:
  - **System default**. This is where it starts. The sounds go where Windows sends sound.
  - **None (no sounds)**. QUILL Lite makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and QUILL Lite tells you once. When the device comes back, the sounds go back to it by themselves.

This changes QUILL Lite only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved. Until October 2026, Alt+Shift+M silenced QUILL and QUILL Lite together. Now each app has its own; to silence every QUILL app at once, turn off **Sound notifications** in QUILL's Settings.

If you only want to change one sound, use the Sound Scheme instead.

### Every sound, in a list you can hear

**Tools > Sound Scheme...** (**Ctrl+Alt+Shift+O**) lists every sound QUILL Lite
can make. As you arrow through the list, each one plays, so you can hear what it
is. If you would rather move through the list quietly, clear the checkbox under
the list.

Each row tells you the event, whether it is on, which sound file it plays, and
how long the sound is. The buttons work on the row you are on:

| Button | What it does |
|---|---|
| **Play** | Play this event's sound now, even if the event is switched off |
| **Switched on** | Silence this one event without changing which sound it has |
| **Browse...** | Use a WAV file of your own |
| **No Sound** | Remove the sound from this event entirely |
| **Use Default** | Put this one event back to the sound the scheme ships |

#### Saving and sharing your sounds

**Save As Scheme** saves your whole set of sounds under a name you choose. A
scheme is just a folder of sound files, so you can copy it, back it up, or give
it to a friend.

**Restore All Defaults** puts every sound back as it was and turns them all on.
The original sounds are never changed, so you can always get back to them with
one press.

QUILL uses the same Sound Scheme window and the same schemes, so a scheme you
make in one shows up in the other.

Besides QUILL's own sounds, the **Scheme** list offers **VS Code Signals**, the
accessibility signal sounds from Visual Studio Code, used under the MIT licence.
They cover errors, saving, dictation starting and stopping, and undo and redo.
Anything they have no sound for stays quiet, or is spoken where QUILL Lite
speaks instead. The choice is the family's: QUILL and the other QuillVille
apps play the same scheme, each from the next time it starts.

## Activity and Repeat Last Result

Sometimes QUILL Lite tells you something while your attention is elsewhere, and
you miss it. These two commands let you catch up.

### Activity (Shift+F9)

**Help > Activity...** (Shift+F9) is a list of everything QUILL Lite has told
you about in this session, newest first. That includes things like a settings
file that could not be saved, a save that worked after an earlier one failed,
or work that finished after you closed the window that started it. Each row is
one sentence: whether it worked, what it was, and when.

Press **Enter** on a row to take its first action. The buttons below the list
say what the selected row offers, and are dimmed when it offers nothing:

- **Retry** tries the same thing again. For a settings file that could not be
  saved, that means saving it again, so if your disk was full and you have since
  made room, one key fixes it.
- **Open Folder** opens the folder in File Explorer with the file selected, so
  you can check whether the disk is full or the folder is read only.
- **Copy Details** copies the selected result as text, ready to paste into a
  message to support.
- **Clear List** empties the list for this session.

Opening a large file, or one on a network drive, shows up here too. You see it
while it is still opening, and then as Opened or Could not open. So if a slow
file finished opening while you were busy elsewhere, you can find out how it
went.

All your document windows share one list. If a save failed while you were in a
different document, you will still find it in Activity from any window. The
list stays on your computer, and it never contains any of your document text.

### Repeat Last Result (F9)

**Help > Repeat Last Result** (F9) says the most recent important thing again.
That is the last thing QUILL Lite itself told you, not the last thing your
screen reader read. It also tells you what Activity can do about it. If nothing
has happened yet, it says so.

### When a settings file cannot be saved

QUILL Lite tells you once, and keeps your changes for the rest of the session.
In Activity, that row offers Retry and Open Folder. When a later save of the
same file works, QUILL Lite tells you that too, so you know the problem is
over.

## What you learned, and where to go next

QUILL Lite speaks through NVDA or JAWS and only tells you what your screen
reader cannot. Every message is kept in the status bar, so **F6** brings back
anything you missed. A few keys answer quick questions about formatting, a
character, indent depth and the size of your document. **Alt+Shift+M**
turns QUILL Lite's sounds off and on, and Sound Scheme on **Ctrl+Alt+Shift+O** lets you hear,
change or switch off each one and save your own set. **Shift+F9** opens
Activity, the list of everything QUILL Lite has told you this session, with
buttons to retry or look into a problem, and **F9** repeats the last important
message.

The tutorial *What to press when you are lost* shows you how to hear a
message again.

Next, Chapter 9, Writing by voice, shows you how to dictate instead of typing.

---

- Previous: [Chapter 7: Checking your writing](lite-guide-07-checking-your-writing.html)
- Next: [Chapter 9: Writing by voice](lite-guide-09-writing-by-voice.html)
- [Contents](../userguide.html)
