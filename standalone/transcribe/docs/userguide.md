# QUILL Transcribe User Guide

QUILL Transcribe types what you say into the program you are using. Write an
email in Outlook, fill in a form in Edge, Chrome or Firefox, add a note in
Notepad or a paragraph in Word, all by speaking, without leaving the program.

It uses the same speech models and the same dictation as QUILL and QUILL Lite.
If you already dictate in QUILL, the words, punctuation and commands you know
work here too.

Version 1.0.0.

## What it promises

- **Your words go where you started.** Dictation writes into the field that had
  the focus when you started it, and only that field. If you move somewhere
  else, dictation pauses and keeps your words until you say where they go.
- **It never reads the other program.** QUILL Transcribe types into the field.
  It does not read what is already there, what the page says, or what is in
  your email.
- **Your speech stays on your computer.** The built-in models run on this
  computer. Your speech only goes over the internet if you choose an internet
  model yourself, and you are asked first.
- **The model you choose is the model it uses.** It never switches models on
  its own.
- **Nothing listens until you start.** The microphone opens when you start
  dictation and closes when you stop.

## Getting started

### The first time

The first time QUILL Transcribe opens, it shows **Set Up QUILL Transcribe**.
It has one page:

1. **About QUILL Transcribe** - a short description to read with the arrow keys.
2. **Microphone** - the Windows default, or a microphone you name. Press
   **Test Microphone** to record four seconds and hear how loud it was and what
   it heard. The test stays on your computer and nothing is kept.
3. **Speech model** - the models already on this computer. Moonshine is a good
   place to start: it is quick and adds punctuation for you.
4. **Start and stop key** - the key that starts and stops dictation from any
   program. It is **Alt+Shift+Backslash** (`Alt+Shift+\`) unless you change it.
   Type another, for example Ctrl+Alt+PageDown, or press **Record Key** (Alt+C)
   and then press the combination you want: it is written into the box for you.
   Leave the box empty for no key. A key another QuillVille app already uses is
   refused with the name of the app that uses it. If a key does something else
   when you press it in Record Key, another program already uses it: type it, or
   choose another.
5. **Start QUILL Transcribe when I sign in to Windows** - off unless you check
   it. When it is on, QUILL Transcribe opens in the tray. It still does not
   listen until you start dictation.

Press **Finish** to keep your choices or **Skip** to change nothing. You can
open setup again at any time from the Help menu (Ctrl+Alt+S).

### The tray

QUILL Transcribe lives in the notification area, the system tray. To reach it
from the keyboard, press Windows+B, find QUILL Transcribe with the arrow keys,
and press the Applications key or Shift+F10 for its menu.

The menu starts with two lines you can read but not press: what dictation is
doing, and which model it uses. Then:

- **Start Dictation** or **Stop Dictation**
- **Resume**, **Resume in This Field** and **Discard Held Words**, when dictation is paused
- **Choose Model**, **Choose Microphone**, **Dictation Settings** and **Model Library**
- **Transcribe a Recording**
- **User Guide** and **Check for Updates**
- **Show QUILL Transcribe** and **Exit QUILL Transcribe**

The tray icon's name also says what dictation is doing, for example
"QUILL Transcribe - Listening".

If Windows has no notification area for QUILL Transcribe, its window stays open
instead, and closing it puts it on the taskbar. QUILL Transcribe says so when it
starts.

### The window

Press Enter on **Show QUILL Transcribe** in the tray menu, or your show and
hide key if you chose one. The window shows:

- **State** - Ready, Listening, Hearing you, Paused, or Waiting for you to
  switch to a field.
- **Start Dictation** - the button changes to Stop Dictation while dictation is on.
- **Resume**, **Resume in This Field** and **Discard Held Words** - for when dictation is paused.
- **Model and microphone** - the model, microphone and key in use.
- **What happens next** - what starting dictation will do, or why it paused or
  could not start.
- **Choose Model**, **Choose Microphone** and **Dictation Settings**.

Closing the window keeps QUILL Transcribe running in the tray. To quit, choose
**Exit** in the File menu (Ctrl+Q) or **Exit QUILL Transcribe** in the tray menu.

## Dictating

### With your key

1. Go to the field you want to write in: the body of an email, a box on a web
   page, a document.
2. Press your start and stop key. You hear the dictation tone and "Dictation on".
3. Speak. When you pause, what you said is typed where the cursor is.
4. Press the key again, or say "stop dictation", to stop. Anything you were
   still saying is written first.

### From the tray or the window

When you start from the tray or the window, QUILL Transcribe has the focus, and
it never types into itself. So it waits: QUILL Transcribe says "Switch to the
field you want", and dictation starts as soon as you are back in another
program. Alt+Tab, or Escape out of the tray menu, takes you there. If no other
program comes forward within 20 seconds, it gives up and says so. Choosing the
same command again while it waits cancels it.

### What you hear

You hear a tone when dictation starts and stops, and after each phrase. Your
screen reader already reads what is typed, so QUILL Transcribe does not read the
words back unless you ask it to in **Dictation Settings**.

With a large model there can be a few seconds between your pause and the text.
So that the wait is not silent, QUILL Transcribe plays a soft tick once a second
while a phrase is still being worked on. There is no tick for a phrase that
arrives within a second. The first time in a session that a phrase takes four
seconds, you also hear "Still working on that phrase." The ticks stop as soon as
the text arrives, or if recognition fails. While a tick plays, the microphone is
not listened to for a moment, as with every QUILL sound, so the tick is never
typed as speech. To turn the tick off, open **Dictation Settings**, choose
**More Dictation Settings**, and clear **Tick while a phrase is being worked
on**. It is on by default here and off in QUILL and QUILL Lite.

**What you hear after each phrase** in Dictation Settings decides the tick
too. Set to nothing, there is no tick and no sentence. Set to words only, there
is no tick; you hear "Still working on that phrase." when a phrase has taken
four seconds, each time that happens. If your sound pack has no tick sound, you
hear the sentence at four seconds instead of the ticks, each time.

It speaks when something happens that your screen reader cannot tell you: that
dictation paused, that it could not start and why, that a phrase may be
incomplete.

## When the focus moves: paused, not lost

If you move to another field, another program or another window while
dictating, QUILL Transcribe stops typing. It does not follow you. You hear
"Dictation paused" and the reason.

While it is paused, it keeps listening and holds what you say. Nothing is
typed anywhere. Then you choose:

- **Resume** (Ctrl+R in the window) - go back to the field you started in
  first. The held words are typed there and dictation carries on.
- **Resume in This Field** (Ctrl+Shift+R) - make the field you are in now the
  one dictation writes into. It gets the same safety checks as a fresh start.
  If you choose it from the tray or the window, it waits for you to switch to
  the field, as starting does. Choose it again to cancel the wait; your words
  stay held.
- **Discard Held Words** (Ctrl+Shift+D) - throw away what was held. Dictation
  stays paused until you resume or stop.

While paused, "scratch that" takes back the last held phrase, and "stop
dictation" stops. If you stop or exit while words are held, you are told how
many were not written, and exiting asks before throwing them away.

Up to 50 phrases are held. Held words are kept only in memory and only until
you resume, discard, stop or exit.

## Where it will not type

QUILL Transcribe refuses, with a sentence saying why, when:

- the field is a password field;
- the program is running as administrator and QUILL Transcribe is not, because
  Windows does not allow it;
- the focus is in QUILL Transcribe itself, or in a QUILL or QUILL Lite window.
  You hear "This is a QUILL window: press Ctrl+F11 to dictate here." Both
  editors dictate into their own documents with Ctrl+F11;
- the program is on your list of programs dictation never types into. You hear,
  for example, "Dictation does not type into KeePass. Move to another
  program." The list starts with the common password managers and the Windows
  sign-in, lock and administrator prompts. Change it in **More Dictation
  Settings**, with **Programs Dictation Never Types Into...** (Alt+N).
  Programs are matched by file name, like keepass.exe, never by a window title,
  and words already held stay held;
- the chosen model or microphone is not available.

While you use the OpenAI engine, the state line ends "Speech goes to OpenAI.",
because that is the one engine that sends your voice off this computer.

If Windows does not take all of a phrase, QUILL Transcribe stops and says part
of it may be missing. Check the field before you carry on. It never says a
phrase went in when it is not sure.

## Commands while dictating into other programs

These work in any program:

- "stop dictation"
- "scratch that" - removes the last phrase, but only while you are still in the
  same field
- spelling: "start spelling" and "stop spelling"
- capitals and spacing: "caps on", "all caps on", "no space on" and their "off" forms
- "switch to Spanish" and "switch to English"
- punctuation and layout: "comma", "period", "new line", "new paragraph" and the rest
- your snippets, abbreviations and clips: "insert snippet" and the snippet's
  name, "insert abbreviation" and the abbreviation, "paste clip" and a number
  from one to twelve. They come from the same lists QUILL uses, and are typed
  as one phrase, so "scratch that" takes all of it back
- "what can I say" for a short spoken answer

Two limits on snippets and abbreviations here. A snippet's blanks are typed as
their names in square brackets, like [title], and you are not asked to fill
them in. And where a snippet or an abbreviation would put the cursor in the
middle, the cursor stays at the end, because QUILL Transcribe cannot move it
inside another program's text without reading it.

Commands that need to read the text, such as "select that", "correct that" or
"copy all", only work in QUILL's own documents. In another program you hear
"That works in QUILL's own documents" and nothing changes.

### What can I say

Saying "what can I say" while you dictate does not open a window, because a
window would take the focus and pause dictation. Instead you hear: "In another
program, you can say scratch that, new line, start spelling, insert snippet
and its name, or stop dictation. For the full list, open Dictation Commands
from the Dictation menu, Ctrl+Shift+C."

**Dictation Commands** (Ctrl+Shift+C, in the Dictation menu) lists exactly
what works in other programs, and nothing that does not, followed by your own
words and phrases from My Words and Phrases.

## Models

### Choosing a model

Open **Choose Model** (Ctrl+M). Every model is listed with:

- whether it runs **on this computer** or **sends your speech over the internet**;
- the languages it knows;
- whether it is downloaded yet.

The box below the list says more about the one you are on: its size, who
publishes it and its licence. Press **Use This Model** to choose it. It stays
your model until you choose another.

A model that is not downloaded is listed so you know it exists, but you cannot
use it until it is downloaded. Choose **Model Library** to download it.

### The Model Library

**Model Library** (Ctrl+L) is the same one QUILL uses. Each download shows its
size first, is your choice, can be cancelled, and is checked before it is used.
A download that did not finish is never marked ready. Models downloaded here
are shared with QUILL and QUILL Lite, so you only download a model once.

### When your model cannot run

If your chosen model is missing or will not load, QUILL Transcribe does not
quietly use another one. It says which model could not run and what to do.

To dictate anyway, choose **Use the Built-in Model This Time** in the Dictation
menu (Ctrl+B). It uses Moonshine for one session and says so. Your chosen model
stays your choice, and the next session tries it again.

### OpenAI

If you have saved an OpenAI key in QUILL's Use My Own AI Key, OpenAI appears in
the list. It is never chosen for you. The first time you choose it, QUILL
Transcribe tells you exactly what is sent and where, and nothing is sent unless
you agree. No is the default.

## Settings

### Microphone

**Choose Microphone** (Ctrl+Shift+M) lists your microphones. The Windows
default follows whatever Windows is set to. A named microphone stays chosen even
if the default changes.

### Dictation Settings

**Dictation Settings** (Alt+Shift+F6, the key QUILL and QUILL Lite use; Ctrl+,
still works) is the same window QUILL and QUILL Lite use: language,
punctuation, filler words, how long a pause ends a phrase, what you hear after
each phrase, and your dictation word list. QUILL Transcribe keeps its own copy
of these settings, so changing them here does not change QUILL's. Two of them
are always off here: the wake phrase, because it would start typing into
whatever program is in front, and holding the key to talk, because Windows
reports when a system-wide key is pressed but not when it is let go.

**More Dictation Settings** in that window has **Tick while a phrase is being
worked on**, on by default in QUILL Transcribe (see What you hear).

### Your words, the language, and your last phrases

- **Recent Phrases** (Shift+F11, in the Dictation menu) lists the last 20
  phrases you dictated, newest first, in the same window as QUILL and QUILL
  Lite. **Insert Again** types the phrase into the program you go back to:
  QUILL Transcribe says "Switch to the field you want. The phrase is typed
  there.", and types it, with the same checks as dictation, as soon as you are
  back in another program. **Copy** puts it on the clipboard and says "Copied"
  and the phrase. The list is kept in memory only, for as long as QUILL
  Transcribe runs; nothing is saved to disk, and it is empty again next time.
- **My Words and Phrases** (Alt+Shift+F10, in the Dictation menu) is the same
  window as in QUILL and QUILL Lite, over the same word list as QUILL, so a
  word you teach one is known to the other. QUILL Lite shares it once you
  check **Use the shared word list** in its own My Words and Phrases window.
  **Export...** saves the list to a Markdown or CSV file, and **Import...**
  adds the new entries from one after showing you what it will add; nothing
  you have is replaced. You hear the counts, such as "Imported 12 words, 3
  already there."
- **Switch Dictation Language** (Ctrl+Shift+F11, in the Dictation menu) changes
  between English and Spanish and keeps the choice for next time. You hear
  "Español." or "English." If dictation is on, the next phrase is heard in the
  new language. Saying "switch to Spanish" or "switch to English" does the same.

### The same keys as QUILL and QUILL Lite

Where QUILL Transcribe has the same dictation command as the editors, it has the
same key: Ctrl+F11 starts and stops, Alt+Shift+F6 opens Dictation Settings,
Alt+Shift+F10 opens My Words and Phrases, Ctrl+Shift+F11 switches the language,
Shift+F11 opens Recent Phrases, and Shift+F5 transcribes a recording. The keys
from version 1.0 (Ctrl+D, Ctrl+, and Ctrl+O) still work. These work in the
QUILL Transcribe window; from other programs, use your start and stop key.

Three of the editors' dictation commands are not in QUILL Transcribe, because
they work on a document and QUILL Transcribe has none: Live Transcript,
Dictation Context and Tidy Dictated Text. Dictation
Status (Alt+F9) is not needed: the State field and the tray icon's name say what
dictation is doing.

If you choose **Dictate in Other Programs** in QUILL or QUILL Lite while QUILL
Transcribe is running, your editor's dictation settings are handed to QUILL
Transcribe.

### Keys

There are two keys you can choose, both in the File menu, and neither is set
until you choose it:

- **Start and Stop Key** (Ctrl+Alt+Shift+D) - chooses the key that starts and
  stops dictation from any program: Alt+Shift+Backslash unless you change it.
  Type the key, or press **Record Key** and press it.
- **Show and Hide Key** (Ctrl+Alt+Shift+H) - shows and hides the QUILL
  Transcribe window from any program.

Type the key, or leave the box empty for none. If the family already uses the
key, you are told which app uses it. If another program has already taken it,
Windows says so, but Windows does not say which program, so neither can QUILL
Transcribe.

### Options

- **Start QUILL Transcribe with Windows** (Ctrl+Alt+W) - opens it in the tray when you sign in.
- **Start minimized to the tray** (Ctrl+Alt+M).
- **Close button keeps QUILL Transcribe running** (Ctrl+Alt+C) - on by default.

## Transcribing a recording

**Transcribe a Recording** (Shift+F5 in the window, as in QUILL and QUILL Lite;
Ctrl+O still works) turns an audio or video file
into text with the same models, using the same window as QUILL. Choose the file
and the model; it is transcribed in the background while you carry on.

When it finishes, you hear how long the recording was and how many words came
out. Open **Notifications** (Ctrl+Shift+N) and press Enter on the transcript to
review it. The **Review Transcript** window shows it read-only, with:

- **Copy All** - puts the whole transcript on the clipboard;
- **Save As** - saves it as a text file where you choose;
- **Open in QUILL** - opens it in QUILL to edit.

Nothing is copied or saved unless you choose it.

## Quill Inkwell and QUILL Transcribe

Quill Inkwell also has Dictate Anywhere. Only one of the two dictates at a time:

- While QUILL Transcribe is running, it owns dictation. Pressing Inkwell's
  Dictate Anywhere key passes the press to QUILL Transcribe, so you get QUILL
  Transcribe's dictation, with its pause when the focus moves.
- When QUILL Transcribe is not running, Inkwell dictates as it always has.
- If Inkwell is in the middle of dictating when you start QUILL Transcribe, QUILL
  Transcribe waits until Inkwell stops.

The first time QUILL Transcribe runs, it brings over the Dictate Anywhere
settings and key you chose in Inkwell. Inkwell's own settings are not changed.

## One microphone: QUILL, QUILL Lite and QUILL Transcribe

Only one program listens at a time, so the same words are never written twice.
The microphone belongs to whichever of QUILL, QUILL Lite, QUILL Transcribe and
Quill Inkwell started dictating first, for as long as it is dictating. QUILL
Transcribe waiting in the tray does not hold it.

- If QUILL or QUILL Lite is dictating when you press your start and stop key,
  QUILL Transcribe does not start, and says who is and the key that stops it,
  for example "QUILL Lite is dictating. Press Ctrl+F11 in QUILL Lite to stop
  it, then try again." QUILL's Locked Dictation (Ctrl+F9) counts too.
- If QUILL Transcribe is listening when you press Ctrl+F11 in QUILL or QUILL
  Lite, the editor does not start a second microphone. It names your start and
  stop key: "QUILL Transcribe is listening. Press Alt+Shift+Backslash to stop
  it, then try again." With no key chosen, it says "Stop it from its tray icon"
  instead.

The microphone is let go when dictation stops, when it stops because something
went wrong, when the window closes, and when the program exits for any reason.

## Where QUILL Transcribe's own sounds play

QUILL Transcribe makes short sounds of its own, such as the ones that mark dictation starting and stopping. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns QUILL Transcribe's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Options > App Sounds** has a check mark that shows whether they are on.
- **Options > App Sounds Play On... (Ctrl+Shift+S)** lets you pick where they play:
  - **System default**. This is where it starts. The sounds go where Windows sends sound.
  - **None (no sounds)**. QUILL Transcribe makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and QUILL Transcribe tells you once. When the device comes back, the sounds go back to it by themselves.

This changes QUILL Transcribe only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved.

## Safe Mode

In Safe Mode, QUILL Transcribe does not listen, registers no keys, downloads no
models and sends nothing over the internet. The window and tray menu still open
so you can look at your settings.

## Privacy

- Nothing is recorded before you start dictation.
- Recordings and transcripts of your dictation are not kept. Held words live in
  memory only until you resume, discard, stop or exit.
- QUILL Transcribe never writes what you said, or what is in other programs, to
  its logs.
- There is no usage tracking of any kind.
- Uninstalling QUILL Transcribe leaves your downloaded models, your dictation
  word list and your settings in place, because QUILL and the other apps use
  them too.

## Keyboard shortcuts

In the QUILL Transcribe window:

| Command | Key |
|---|---|
| Start or stop dictation | Ctrl+F11 (or Ctrl+D) |
| Resume | Ctrl+R |
| Resume in this field | Ctrl+Shift+R |
| Discard held words | Ctrl+Shift+D |
| Use the built-in model this time | Ctrl+B |
| Recent phrases | Shift+F11 |
| Switch dictation language | Ctrl+Shift+F11 |
| My words and phrases | Alt+Shift+F10 |
| Dictation commands | Ctrl+Shift+C |
| Choose model | Ctrl+M |
| Choose microphone | Ctrl+Shift+M |
| Model library | Ctrl+L |
| Dictation settings | Alt+Shift+F6 (or Ctrl+,) |
| Transcribe a recording | Shift+F5 (or Ctrl+O) |
| Notifications | Ctrl+Shift+N |
| Minimize to tray | Ctrl+W |
| Exit | Ctrl+Q |
| User guide | Ctrl+F1 |
| Set up QUILL Transcribe | Ctrl+Alt+S |
| Check for updates | Ctrl+Alt+U |
| About QUILL Transcribe | Ctrl+Alt+I |

From any program, only these: your start and stop key (Alt+Shift+Backslash
unless you changed it), and your show and hide key if you chose one.

F1 anywhere in QUILL Transcribe says what the window is for and what the
control you are on does.

## Getting help

Choose **Get Help from Support** in the Help menu (Ctrl+Alt+F2), or write to
support@community-access.org.
