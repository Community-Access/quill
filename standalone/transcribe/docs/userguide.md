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
3. **Speech model** - the models already on this computer, each with its tier
   (see "Choosing a model"). Moonshine is a good place to start: it is quick
   and adds punctuation for you. Below it, **Recommended for this computer**
   (Alt+P) is one line naming the model that suits your computer and why. It
   is only advice: the model in the box above is the one you get.
4. **Start and stop key** - the key that starts and stops dictation from any
   program. It is **Alt+Shift+Backslash** (`Alt+Shift+\`) unless you change it.
   Type another, for example Ctrl+Alt+PageDown, or press **Record Key** (Alt+C)
   and then press the combination you want: it is written into the box for you.
   Leave the box empty for no key. A key another QuillVille app already uses is
   refused with the name of the app that uses it. If a key does something else
   when you press it in Record Key, another program already uses it: type it, or
   choose another.
5. **Command key** - optional, and empty unless you choose one. Press it in
   the field you are dictating into and the next thing you say is a command,
   as if you had said QUILL first (see "The command word"). Type a key, or
   press **Record Command Key** (Alt+N) and press it. It must not be the start
   and stop key.
6. **Start QUILL Transcribe when I sign in to Windows** - off unless you check
   it. When it is on, QUILL Transcribe opens in the tray. It still does not
   listen until you start dictation.

Press **Finish** to keep your choices or **Skip** to change nothing. You can
open setup again at any time from the Help menu (Ctrl+Alt+S).

### The tray

QUILL Transcribe lives in the notification area, the system tray. To reach it
from the keyboard, press Windows+B, find QUILL Transcribe with the arrow keys,
and press the Applications key or Shift+F10 for its menu.

The menu starts with three lines you can read but not press: what dictation is
doing, which model it uses, and which dictation profile is in use. Then:

- **Start Dictation** or **Stop Dictation**
- **Resume**, **Resume in This Field** and **Discard Held Words**, when dictation is paused
- **Choose Model**, **Choose Microphone**, **Dictation Settings**, **Dictation Profile** and **Model Library**
- **Transcribe a Recording**
- **User Guide** and **Check for Updates**
- **Show QUILL Transcribe** and **Exit QUILL Transcribe**

The tray icon's name also says what dictation is doing, for example
"QUILL Transcribe - Listening". With a profile other than Standard it says that
too: "QUILL Transcribe - Listening - Email profile".

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
- **Model and microphone** - the model, microphone, dictation profile (and
  whether it is locked) and keys in use.
- **What happens next** - what starting dictation will do, or why it paused or
  could not start.
- **Choose Model**, **Choose Microphone** and **Dictation Settings**.

Closing the window keeps QUILL Transcribe running in the tray. To quit, choose
**Exit** in the File menu (Ctrl+Q) or **Exit QUILL Transcribe** in the tray menu.

## Practice and lessons

New to dictation, or to a new microphone or model? Practise in QUILL
Transcribe's own window first. Nothing you say there goes into another program.

### Practice Dictation

Open **Practice Dictation** from the Dictation menu (Ctrl+Shift+P). The window
has, in Tab order:

- **Sentence to read aloud** - a sentence for the recognition test.
- **Practice field** - QUILL Transcribe's own field. The focus starts here.
- **Result** - the last recognition test's score.
- **Start Dictation Here** (Alt+H) - starts dictation in the practice field, or
  stops it. Ctrl+F11 does the same while you are in this window.
- **Read This Sentence** (Alt+T) - the recognition test, below.
- **Score the Field** (Alt+S) - scores everything in the practice field
  against the sentence.
- **Next Sentence** (Alt+N) - shows another of eight sentences.
- **Close** (Escape) - stops dictation in the field and closes the window.

Everywhere else, starting dictation from QUILL Transcribe's own window waits
for you to switch to another program, because the window itself is never
dictated into. The practice field is the one exception: Start Dictation Here
writes into it straight away. The same checks as any start still apply (Safe
Mode, the microphone, your model), and if dictation is already on in another
program you are asked to stop it first.

Everything works in the practice field as it does elsewhere: punctuation by
voice, "QUILL scratch that", "QUILL caps on", snippets, Review Dictation, and
your profile. Formatting profiles (Document, Email) treat the field as plain
text, as they would Notepad. When dictation stops, by any route, it goes back
to working in other programs as usual.

**Example.** Press Ctrl+Shift+P, then Alt+H. You hear "Dictation on". Say
"this is my first dictation period" and pause. You hear your words read back,
and the practice field holds "This is my first dictation."

### The recognition test

Press **Read This Sentence** (Alt+T). The practice field is cleared, dictation
starts in it if it was off, and the status bar shows the sentence. Read the
sentence aloud at your usual pace, then pause. The first thing written is
compared with the sentence word for word, and you hear the result once; it
also stays in the Result field. For example:

- "All 9 words right. Recognition is working well."
- "78 percent right: 2 differences in 9 words. Not heard as said: jumps, lazy.
  Try speaking a little slower, moving closer to the microphone, or a larger
  model in Choose Model."

Capitals and punctuation do not count; the test is about the words. Below 80
percent you are given the three suggestions above. If you said the sentence
in two breaths, only the first part is scored; press **Score the Field**
(Alt+S) to score everything in the field instead. The score uses the same
word-error count as QUILL's dictation benchmark, so it means the same thing.

Limits: the sentences are in English, and the test checks your microphone,
model and voice together. It cannot tell which of the three to change.

### Tutorials

**Tutorials** in the Help menu (Ctrl+Alt+F1) opens five short lessons in the
same Tutorials window as QUILL and QUILL Lite:

1. Your first dictation, in the Practice window.
2. Pause and resume in another program.
3. Commands with the command word.
4. Snippets and clips by voice.
5. Review before it is typed.

Each step says what to do, why, and what you should hear. Where a step names a
command, **Try it** runs it for you. The same lessons are in the tutorial book,
`tutorials.html` beside this guide.

## Dictating

### With your key

1. Go to the field you want to write in: the body of an email, a box on a web
   page, a document.
2. Press your start and stop key. You hear the dictation tone and "Dictation on".
3. Speak. When you pause, what you said is typed where the cursor is.
4. Press the key again, or say "stop dictation", to stop. Anything you were
   still saying is written first.

### Holding the key to talk

If you would rather hold a key while you speak, as with a walkie-talkie, open
**Dictation Settings**, choose **More Dictation Settings**, and check **Hold
the dictation key to talk** (Alt+H). It is off until you turn it on, and it is
the same setting QUILL and QUILL Lite have for Ctrl+F11. Then:

- Hold your start and stop key and talk. When you let go, dictation stops,
  keeping your last phrase.
- What you say while the key is down is typed the moment you let go, not
  before. Your start and stop key has Alt or Ctrl in it, and letters typed
  while one of those is held would reach the other program as shortcuts.
- A quick press still turns dictation on, and the next press turns it off.

Keys with Ctrl in them make most screen readers stop talking while they are
held, so a key with Alt, such as the default Alt+Shift+Backslash, works best
for holding.

### Starting with your voice: the wake phrase

You can start dictation by saying the wake phrase, "Quill dictate" unless you
change it, instead of pressing a key. Open **Dictation Settings** and check
**Listen for the wake phrase while dictation is off** (Alt+H in that window);
the **Wake phrase** box (Alt+W) is where you change the words. It is off until
you turn it on, and when you turn it on you hear "Listening for your wake
phrase whenever another program is in front."

While it is on:

- The microphone stays open whenever another program is in front, and the
  State field and the tray say **Listening for your wake phrase**. Nothing it
  hears is written, kept or sent anywhere until it hears the wake phrase at the
  start of what you say.
- Say "Quill dictate" in the field you want, and dictation starts there.
  Anything you say after the wake phrase in the same breath is typed: "Quill
  dictate dear Sam comma" writes "Dear Sam,".
- When you stop, it goes back to listening for the wake phrase, and says so.
- It does not listen while QUILL Transcribe's own window, QUILL or QUILL Lite
  is in front (they have their own dictation), or while a program on your
  never-type list is in front, such as a password manager.

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

**On a braille display**, while you are working in the other program, you see
the words heard so far ("Hearing: dear Sam") with a model that shows them
while you speak, and the changes dictation shows without saying them: Command
mode, Waiting for a command, and Listening for your wake phrase. These go to
the display only and are not spoken. To hear the words so far as well, choose
**Show it, and say new words quietly** for **While you speak, the words heard
so far** in More Dictation Settings.

**Dictation Status** (Alt+F9 in the window, as in QUILL and QUILL Lite) says in
one sentence what dictation is doing, the program it is writing into, the model,
and how many phrases are held, for example "Dictation is paused in OUTLOOK,
using Moonshine Tiny, with 2 phrases held." To ask from another program, choose
a Dictation Status Key (see Keys).

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

Up to 50 phrases are held. Held words are also kept on this computer, sealed
for your Windows account, so a crash, a sleep or exiting loses nothing. Resume
and Discard Held Words delete them. If you stop or exit while words are held,
they stay for next time: stopping says "They are kept in Recent Phrases", and
the next start says how many are waiting. A phrase Windows stopped typing
part-way through is kept the same way.

To resume or discard without coming back to QUILL Transcribe's window, choose a
**Resume Key** and a **Discard Held Words Key** in the File menu (see Keys).
Pressed in the field you started in, the Resume Key types the held words there
and carries on; the Discard Held Words Key throws them away.

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

## Programs it has been tested with

QUILL Transcribe types into almost any program with a text field, but we only
promise what we have tested. The table below comes from a test that types the
same short dictation, phrase by phrase, into each program and then reads the
program's text back to check every phrase arrived exactly. It runs on a real
Windows computer, not on our build servers, so a program that was not
installed there is listed as untested, which does not mean it fails.

- **Supported**: at least 95 out of every 100 phrases arrived exactly.
- **Best effort**: at least half did. Dictation works, but check what was
  typed.
- **Unsupported**: fewer than half did.
- **Untested**: not tried yet on that version.

Programs update often, so each row says when it was checked and when it is
due to be checked again. If a program you use behaves differently from its
row, tell us which version you have.

<!-- compatibility:start -->
| Program | Version | Result | Phrases exact | Checked | Review by | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Notepad | 11.2607.14.0 | Untested | - | 2026-10-15 | 2027-01-13 | The test run was interrupted before it finished, so nothing was measured yet. |
| WordPad | - | Untested | - | 2026-10-15 | 2027-01-13 | WordPad was removed from Windows 11 in version 24H2. |
| Microsoft Word | 16.0.20430.20146 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |
| Microsoft Outlook | 16.0.20430.20146 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |
| Microsoft Edge | 155.0.4283.45 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |
| Google Chrome | 155.0.8059.84 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |
| Mozilla Firefox | 157.0.1.583 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |
| Visual Studio Code | 1.142.0.0 | Untested | - | 2026-10-15 | 2027-01-13 | Installed on the test computer, not run yet. |

Each tested program was sent the same 12 phrases. A phrase counts as
exact when the program's text, read back afterwards, grew by exactly that
phrase. A program's own formatting, such as Word's curly quotes, and its
own line ending are not counted as changes.
<!-- compatibility:end -->

## Commands while dictating into other programs

### The command word

In QUILL Transcribe a command starts with the command word, **QUILL**:
"QUILL scratch that", "QUILL caps on", "QUILL start spelling". Said on its own,
"scratch that" is typed as words, because a command typed into an email by
mistake is much harder to take back than one in a document. Only the stop
phrase, "stop dictation", works without the word, and "stop spelling" while
you are spelling. This is called strict mode,
and it is on in QUILL Transcribe; QUILL and QUILL Lite leave it off.

- QUILL counts only as the first word after a pause. "I told Quill about it"
  is typed as words.
- Whatever follows "QUILL" is never typed. If it is not a command, you hear
  the error sound and "Not a command. Say it again, or say QUILL type that to
  write it." Saying **"QUILL type that"** types those words after all, once.
- To type the word itself, say **"literal QUILL"**.
- Say **"QUILL"** on its own and pause, and the next thing you say is a
  command. A short rising tone tells you it was heard.
- **"QUILL command mode"** takes several commands in a row without the word.
  You hear the tone and "Command mode", and the State field and the tray icon's
  name say Command mode. Say **"dictation mode"** to go back. With no command
  for eight seconds it ends by itself with a falling tone, and what you say
  next is typed.
- The **Command Key**, if you chose one, does the same from the field you are
  in: press it, then say the command. Press it twice for command mode, and
  once more to go back. If dictation is off, it starts dictation in that field
  first. In the QUILL Transcribe window, **Speak a Command** (F11, the key QUILL
  and QUILL Lite use) does the same.

The command word, strict mode, and how long command mode waits are in
**More Dictation Settings** (see "Dictation Settings").

### What works in another program

These work in any program, after the command word:

- "stop dictation" (with or without the word)
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
- correcting the words dictation itself typed: "correct that" and "choose one"
  to "choose three", "capitalize that", "all caps that", "no caps that",
  "replace" some words "with" new ones, "change that to" and new words, "delete
  last sentence" and "delete previous paragraph". See "Correcting in another
  program" below

A snippet with blanks asks for each one before anything is typed. Say "QUILL
insert snippet bug report" and you hear the snippet's name, how many blanks it
has, and the first blank's name, like "Summary?". Say the answer; spoken
punctuation works in it. For a choice you hear the options, "Choose NVDA, JAWS
or Narrator.": say one, or "choose two". Say "skip" to leave a blank empty,
"scratch that" to answer the one before again, or "cancel" to type nothing.
The command word is allowed before an answer but not needed. When the last
blank is answered, the whole snippet is typed as one phrase, so "QUILL scratch
that" takes all of it back. A date or time in a snippet comes from this
computer's clock.

One limit: where a snippet or an abbreviation would put the cursor in the
middle, the cursor stays at the end, because QUILL Transcribe cannot move it
inside another program's text without reading it. For the same reason, "QUILL
read that" reads back what dictation typed, all of it, but "read last
sentence" and the other commands that read a document work only in QUILL.

Commands that need to read the other program's text, such as "select that",
"go to", "correct" and a word, or "copy all", only work in QUILL's own
documents. In another program you hear "That works in QUILL's own documents"
and nothing changes.

### Correcting in another program

QUILL Transcribe never reads the other program's text. What it can do is
remember the words it typed there itself, since the focus last moved, and
change those: it takes them back with Backspace and types the corrected words,
starting from the first letter that changes.

- **"QUILL correct that"**, then **"QUILL choose two"**: with Moonshine,
  Whisper or a downloaded model, the other built-in engine listens to your
  last phrase again, and you hear both answers, for example "1: the whether is
  nice. 2: the weather is nice. Say choose and the number." With Windows speech
  recognition you hear its own other guesses. The phrase is retyped with the
  one you choose.
- **"QUILL replace Tuesday with Wednesday"** looks only in the phrase you
  dictated last. If you said "see you on Tuesday at noon", Backspace takes back
  "Tuesday at noon" and "Wednesday at noon" is typed. If the words are not in
  that phrase, you hear "Not found." and nothing changes.
- **"QUILL change that to see you Friday"** puts the new words in place of the
  last phrase, keeping its capital and closing full stop.
- **"QUILL all caps that"**, **"QUILL capitalize that"** and **"QUILL no caps
  that"** change the capitals of the last phrase.
- **"QUILL delete last sentence"** and **"QUILL delete previous paragraph"**
  take back the end of what dictation typed, never anything before it.

With strict mode off, you can say these without QUILL.

To keep your own typing safe, a correction is refused, with one sentence, and
nothing is sent, when:

- **the focus has moved** since dictation typed the words: "The focus has moved
  since dictation typed those words, so they were left alone."
- **you have typed, clicked or moved the mouse** since then, because the cursor
  may no longer be where dictation left it: "You have typed or clicked since
  dictation typed those words, so they were left alone. Change them with the
  keyboard, or say them again." Windows tells QUILL Transcribe only *when* a key
  or the mouse was last used, never which key. Reading keys count too, so if
  you arrow back to check a word, change it with the keyboard instead.
- **the program is Word or Outlook**, for the commands that retype words.
  Those programs change words as you type them (AutoCorrect), so the count of
  letters to take back could be wrong: "Word can change words as they are
  typed, so dictation does not retype them there. Say scratch that and say it
  again." "Scratch that" and the two delete commands still work there, because
  they only take words away.

Whatever a correction replaced goes into **Recent Phrases** (Shift+F11),
marked "(before correction)", so you can type it again with Insert Again.

### What can I say

Saying "what can I say" while you dictate does not open a window, because a
window would take the focus and pause dictation. Instead you hear: "In another
program, you can say QUILL scratch that, new line, QUILL start spelling, QUILL
insert snippet and its name, or stop dictation. For the full list, open
Dictation Commands from the Dictation menu, Ctrl+Shift+C." With strict mode
off, the commands are said without QUILL.

**Dictation Commands** (Ctrl+Shift+C, in the Dictation menu) lists exactly
what works in other programs, and nothing that does not, followed by your own
words and phrases from My Words and Phrases.

## Review before it is typed

Sometimes you want to hear and check what you said before it goes into the
email. Say **"QUILL review that"**: the last phrase is backspaced away again
(or, if dictation was paused, the words it was holding are taken) and opened in
the **Review Dictation** window. Nothing more is typed into the other program
until you insert it.

- **Read the words** with the arrow keys. They are in an ordinary text box, so
  your screen reader reads them by line, word and character, and a braille
  display shows them. Type to change them, or keep talking: while the window is
  open, what you say is written into it, and the program you were in is left
  alone. This is an expected pause, so you do not hear "Dictation paused".
- **Ask the AI to change them**: say **"QUILL make it shorter"**, **"QUILL
  more formal"** or **"QUILL fix the grammar only"**, or type the instruction
  in **Ask the AI to change it** (Alt+K) and press Enter. You hear "Working",
  then what changed, in two sentences at most, such as "Changed next Thursday
  to Friday. Removed um, so." QUILL Transcribe works that out by comparing the
  words itself, never from the AI's own account. **Talk about it** (Alt+A)
  makes everything you say an instruction, without the command word.
- **Insert** (Ctrl+Enter, or say **"QUILL insert it"**) goes back to the field
  you were dictating into and types the words there once, with the same checks
  as every phrase: the same field, no password field, nothing on the list of
  programs it never types into. If the field cannot be typed into, nothing is
  typed, you are told why, and the words are in Recent Phrases (Shift+F11) for
  Insert Again. "QUILL scratch that" takes the inserted words back out.

The window's other keys: Ctrl+R reads all the words ("QUILL read it back"),
Ctrl+D says again what changed ("QUILL what changed"), Ctrl+Z undoes the AI's
last change ("QUILL undo that change"), Ctrl+Shift+Z goes back to exactly what
you said ("QUILL back to what I said"), and Escape stops a request on its way
or discards the words ("QUILL discard it"). From the QUILL Transcribe window,
**Review Dictation** (Shift+F4, in the Dictation menu, the key QUILL and QUILL
Lite use) opens it too, empty if there is nothing to take.

**The AI.** QUILL Transcribe has no AI menu of its own. It uses what you set up
in QUILL: your ChatGPT subscription (Use My ChatGPT Subscription) or your own
key (Use My Own AI Key). Without either, or in Safe Mode, AI is off: "QUILL
review that" says "AI is off. Your words were written as you said them." and
leaves the phrase typed, and the window still opens from Shift+F4 to edit and
insert by hand. The first time, QUILL Transcribe asks before anything is sent
and names who receives it; No is the default and sends nothing. Only the words
in the window and your instruction are sent, with My Dictation Instructions if
you wrote any; nothing is ever read from the other program. Each change you ask
for is one request.

To send everything you say to the review window first, turn on **Send
dictation to review first** (Alt+V) in More Dictation Settings.

### Polishing what you said, only when you ask

**Polish** tidies punctuation, capital letters and small slips without
rewording anything, before the words are typed into the other program. It is
one request you ask for each time, it is off until you turn it on, and it never
runs by itself.

1. Open **Dictation Settings** (Alt+Shift+F6), press **More Dictation
   Settings**, and check **Allow polishing my dictation with AI when I ask**
   (Alt+G). Press OK in both windows.
2. Dictate into your email as usual. When you want the last phrase polished,
   say **"QUILL polish that"** (or "QUILL polish it"). The phrase is backspaced
   away and opened in Review Dictation, then the polish request is made there.
   If Review Dictation is already open, the words in it are polished.
3. In the Review Dictation window you can also press **Polish** (Ctrl+P). The
   button is there only while polishing is allowed.
4. You hear "Polishing", then what changed. Read the words, then **Insert**
   (Ctrl+Enter, or "QUILL insert it") types them into the field once, or Undo
   Change (Ctrl+Z) takes the polish back.

The AI is asked to fix punctuation, capital letters, spelling and obvious
grammar slips only, and to keep your words, meaning, order and tone. It uses
the same AI and the same first-time question as the rest of the review: nothing
is sent until you say yes, and only the words in the window go. With AI off the
Polish button is greyed out, and with polishing not allowed "QUILL polish that"
says "Polish my dictation is off" and sends nothing.

### Correcting yourself as you talk

With **Fix it when I correct myself, like Thursday, no, Friday** (Alt+X)
checked in Dictation Settings, QUILL Transcribe types only what you meant when
you correct yourself in the middle of a sentence:

| You say | QUILL Transcribe types |
|---|---|
| meet on Thursday, no, Friday at noon | meet on Friday at noon |
| in June, no I mean July | in July |
| I have two no three cats | I have three cats |
| call me at 5, sorry, 6 | call me at 6 |
| send it to Ana, sorry, Maria (both names in My Words) | send it to Maria |

The marking words are "no", "I mean", "no I mean", "sorry" and "scratch that
word", and a correction is made only between two days, two months, two numbers
or two names from the Vocabulary list in My Words and Phrases. Everything else
is typed as you said it: "no, I don't think so" and "Is it Thursday? No,
Friday." stay as they are. The fix happens on this computer before anything is
typed, with no AI. It is off until you turn it on.

**Dictation style** (Alt+Y), in the same window, sets these choices together:
**Verbatim** (every word as you say it), **Clean** (no filler words, and your
corrections fixed) or, only when AI is set up in QUILL, **Polished** (Clean,
plus Send dictation to review first and Allow polishing my dictation with AI).
Choosing Polished sends nothing by itself. Change a check box yourself and the
style shows **Your own mix of the settings below**.

**Remembering a correction.** When you fix the same word the same way twice
with "QUILL correct that" and then "QUILL choose two" (see "Correcting in
another program"), QUILL Transcribe offers to add it to My Words and Phrases,
so it comes out right next time. The question is spoken, never shown in a
window that would take the focus from your field: "Add a correction: Ann
becomes Anne? Say QUILL yes to add it, or QUILL no." Answer within 30 seconds.
Yes adds it to the Corrections list, which you can change in My Words and
Phrases (Alt+Shift+F10); No, silence or anything else adds nothing. Each pair
is offered once each time QUILL Transcribe runs, and only a word or a short
phrase of up to four words.

## Profiles: the kind of writing you are doing

A dictation profile changes dictation for one kind of writing, without you
changing several settings each time. There are seven:

| Profile | Fillers | Punctuation | Pause | Headings, bold and italic |
|---|---|---|---|---|
| Standard | As your settings say | As your settings say | As your settings say | Markdown marks |
| Email | Removed | Added | As your settings say | Formatted where the document holds formatting; elsewhere nothing, and you are told why |
| Document | As your settings say | As your settings say | As your settings say | Formatted, the same way |
| Markdown | As your settings say | As your settings say | As your settings say | Markdown marks, in any program |
| Chat | Removed | As your settings say | As your settings say | Plain text |
| Coding | Removed | Not added: you say every mark | Long | Markdown marks |
| Verbatim | Kept | As your settings say | As your settings say | Plain text |

Standard is where everybody starts, and is your Dictation Settings exactly as
they are.

### Choosing a profile

- **Dictation Profile** in the Dictation menu (Ctrl+Shift+F), or in the tray
  menu, lists the seven with a sentence about the one you are on, and has the
  **Lock the profile** check box (Alt+L). OK uses it from your next phrase.
- **By voice**, after the command word: "QUILL email mode", "QUILL markdown
  mode", "QUILL standard mode", and so on ("email profile" works too). You
  hear "Email profile." and the choice is kept.
- **More Dictation Settings** in Dictation Settings has the same choice
  (Alt+A) and lock (Alt+B).

**Lock Profile** (Dictation menu, Ctrl+Shift+L) stops a spoken profile name
from switching profiles: you hear "Lock Profile is on, so the profile stays
Email." You can still choose one from the menu. QUILL Transcribe never switches
profiles on its own, for example by which program you are in.

The profile in use shows in the window's Model and microphone field, the
tray's third line, the tray icon's name and Dictation Status.

### Headings, bold and italic in other programs

QUILL Transcribe never reads the other program's text, so:

- In **Markdown** and **Coding**, "heading two" at the start of a phrase types
  "## " before your words, and "QUILL bold that" retypes the phrase you just
  dictated with two asterisks either side, as one step that "QUILL scratch
  that" takes back. "QUILL italic that" uses one asterisk.
- In **Document** and **Email**, other programs cannot be formatted by
  keystrokes QUILL Transcribe can trust, so "heading two" starts a new line,
  writes your words and says "Headings work in QUILL documents or the
  Markdown profile." Bold and italic say the same about themselves.
- In **Chat** and **Verbatim**, "heading two" starts a new line with your words
  and nothing else, and bold and italic say "This profile writes plain text, so
  nothing was formatted."

**Example.** In an email, choose the Email profile, then say "um thanks for
the notes" and pause. "Thanks for the notes." is typed: the filler is gone and
the full stop added.

**Profiles and the Dictation style.** While a profile other than Standard is
on, its own choice about filler words wins over the **Dictation style** in
Dictation Settings: Verbatim keeps fillers even if the style is Clean, and
Email, Chat and Coding remove them even if the style is Verbatim. A profile
never changes **Fix it when I correct myself** or polishing. Standard leaves
your style exactly as it is.

The settings are stored as `windows_dictation_profile` and
`windows_dictation_profile_locked`, under the same names as QUILL's and QUILL
Lite's, in QUILL Transcribe's own copy of the dictation settings.

## Models

### Choosing a model

Open **Choose Model** (Ctrl+M). Every model is listed with:

- whether it runs **on this computer** or **sends your speech over the internet**;
- its tier: **Lightweight**, **Balanced** or **High accuracy**;
- the languages it knows;
- whether it is downloaded yet.

The box below the list says more about the one you are on: its size, what
its tier means, who publishes it and its licence. Press **Use This Model** to
choose it. It stays your model until you choose another.

The tiers say how much work a model is for your computer:

- **Lightweight**: keeps up comfortably even on a modest computer. The
  built-in Moonshine and Whisper, and Moonshine base.
- **Balanced**: more work than the built-in models; keeps up on a computer
  with four or more cores. Parakeet and Whisper base.
- **High accuracy**: the fewest mistakes, for the most work; needs a capable
  computer, or patience. Nemotron, and Whisper small and larger.

**Recommended for this computer** (Alt+C) is a read-only box below that. It
names the model that suits your computer and your dictation language, and
says why: whether it keeps up, about how soon your words appear after you
pause, and how big the download is, or that it is already installed. The
figures are estimates, measured with a synthetic voice. It is only advice:
QUILL Transcribe never changes your model by itself. The Model Library has
the same advice, with a **What matters most** choice (the quickest response,
or the fewest mistakes) and a **Show Recommended Model** button.

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

### Speech providers: your own account

QUILL Transcribe can also use a speech company you already have an account
with: Azure, Google, Amazon, Deepgram, AssemblyAI, Speechmatics, ElevenLabs,
Gladia, Rev.ai, Groq, Mistral or IBM Watson. Open **Dictation Settings**
(Alt+Shift+F6) and choose **Speech Providers...** (Alt+V): pick the company,
fill in what it needs, **Test Connection** (Alt+T), then the Save button (Alt+S).
Keys go to Windows Credential Manager, never into settings; the region and
other details are kept in QUILL Transcribe's own settings. Then choose the company as the model in
Dictation Settings. As with OpenAI, you are told exactly what is sent and
where, nothing is sent unless you agree, and No is the default. If the company
cannot be reached, dictation stops with one sentence and your model stays
your choice; **Use the Built-in Model This Time** (Ctrl+B) is there if you need
to keep going.

## Settings

### Microphone

**Choose Microphone** (Ctrl+Shift+M) lists your microphones. The Windows
default follows whatever Windows is set to. A named microphone stays chosen even
if the default changes.

### Dictation Settings

**Dictation Settings** (Alt+Shift+F6, the key QUILL and QUILL Lite use; Ctrl+,
still works) is the same window QUILL and QUILL Lite use: language,
punctuation, filler words, the dictation style and fixing it when you correct
yourself (see Correcting yourself as you talk), how long a pause ends a phrase,
what you hear after each phrase, and your dictation word list. **Share dictation settings with every QuillVille program**
(Alt+Q, in More Dictation Settings) decides whether they are shared: when it
is checked, what you save here is used by QUILL, QUILL Lite and Quill Inkwell
too, and what you save in any of them is used here within a second. See
Sharing dictation settings with the family, below. The wake
phrase and holding the key to talk work here too, both off until you turn them
on (see Holding the key to talk, and Starting with your voice).

**More Dictation Settings** in that window has **Tick while a phrase is being
worked on**, on by default in QUILL Transcribe (see What you hear). Its
**Commands** group has the **Command word** (Alt+C; QUILL unless you change it,
and empty for none, so only the Command Key gives commands), **Commands only
after the command word (strict mode)** (Alt+E; on in QUILL Transcribe), and
**Seconds command mode waits for a command** (Alt+D; 8, from 5 to 30). A
common word, or one of your own words in My Words and Phrases, cannot be the
command word, and you are told why.

### Sharing dictation settings with the family

When **Share dictation settings with every QuillVille program** is checked, QUILL,
QUILL Lite, QUILL Transcribe and Quill Inkwell use one set of dictation
settings.

- **What is shared:** the model and engine, the language, the microphone,
  automatic punctuation, the pause, filler words, the wake phrase, the command
  word, review first, the never-type list and the other dictation choices.
- **What stays QUILL Transcribe's own:** its keys and tray, the working tick
  and strict mode (both on here), what you hear after each phrase, and every
  permission to send your speech to a company.
- **When:** saving Dictation Settings with OK, or changing the language,
  shares at once. A change saved in QUILL or QUILL Lite is used here within a
  second, without a word from QUILL Transcribe: it is your own change.
- **To begin with:** checked for a new install; unchecked if you had already
  changed your dictation settings, so nothing you chose is replaced. Check it
  when you want to join in.
- **Nothing is lost:** the first time QUILL Transcribe takes settings from the
  family, its own are saved as `before-sharing-transcribe.json` in
  `%LOCALAPPDATA%\QuillVille\Dictation`. If two programs save at once, the
  last one saved wins. If the shared copy cannot be saved, you hear "Saved
  here, but the other QuillVille programs will not see this change", and why.

For example: in QUILL, choose a different model in Dictation Settings and
press OK. The next phrase you dictate into Outlook with QUILL Transcribe uses
that model.

### Your words, the language, and your last phrases

- **Recent Phrases** (Shift+F11, in the Dictation menu) lists the last 20
  phrases you dictated, newest first, in the same window as QUILL and QUILL
  Lite. **Insert Again** types the phrase into the program you go back to:
  QUILL Transcribe says "Switch to the field you want. The phrase is typed
  there.", and types it, with the same checks as dictation, as soon as you are
  back in another program. **Copy** puts it on the clipboard and says "Copied"
  and the phrase. This run's phrases are kept in memory only. After them come
  the words kept from before: "Not written" (held while paused, or typing that
  stopped), "Review not finished", and, with **Keep a dictation history** on,
  "Earlier" phrases. Insert Again types one and then deletes it from the
  computer; **Discard** (Alt+D) deletes it unwritten; **Clear History**
  (Alt+H) deletes the history after asking, with No as the answer unless you
  choose Yes.
  When a correction changed a phrase, the words it replaced are in the list
  too, marked "(before correction)"; Insert Again and Copy leave the label out.
- **Keep a dictation history** (Alt+Y in More Dictation Settings) is Off unless
  you choose One day, Seven days or Thirty days. Only the text is kept, never
  the sound, sealed for your Windows account. Turning it off deletes it.
- **My Words and Phrases** (Alt+Shift+F10, in the Dictation menu) is the same
  window as in QUILL and QUILL Lite, over the same word list as QUILL, so a
  word you teach one is known to the other. The list lives in
  `%LOCALAPPDATA%\QuillVille\Dictation`; the first time it is needed after
  the update it is copied there from QUILL's data folder, and the old file is
  left as it was, as a backup. QUILL Lite shares it once you
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
Shift+F11 opens Recent Phrases, F11 is Speak a Command, Shift+F4 is Review
Dictation, Alt+F9 is Dictation Status, and Shift+F5 transcribes a recording. The keys
from version 1.0 (Ctrl+D, Ctrl+, and Ctrl+O) still work. These work in the
QUILL Transcribe window; from other programs, use your start and stop key.

Three of the editors' dictation commands are not in QUILL Transcribe, because
they work on a document and QUILL Transcribe has none: Live Transcript,
Dictation Context and Tidy Dictated Text.

If you choose **Dictate in Other Programs** in QUILL or QUILL Lite while QUILL
Transcribe is running, your editor's dictation settings are handed to QUILL
Transcribe.

### Keys

There are six keys you can choose, all in the File menu. Only the start and
stop key has one to begin with; the others are not set, and nothing is taken
from other programs, until you choose them:

- **Start and Stop Key** (Ctrl+Alt+Shift+D) - chooses the key that starts and
  stops dictation from any program: Alt+Shift+Backslash unless you change it.
  Type the key, or press **Record Key** and press it.
- **Command Key** (Ctrl+Alt+Shift+K) - chooses the key that makes the next
  thing you say a command, from any program (see "The command word").
- **Show and Hide Key** (Ctrl+Alt+Shift+H) - shows and hides the QUILL
  Transcribe window from any program.
- **Dictation Status Key** (Ctrl+Alt+Shift+A) - says Dictation Status's one
  sentence from any program.
- **Resume Key** (Ctrl+Alt+Shift+U) - when dictation is paused, types the held
  words into the field you started in and carries on.
- **Discard Held Words Key** (Ctrl+Alt+Shift+Y) - when dictation is paused,
  throws the held words away.

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

For a recording in Spanish, check **Translate into English** (Alt+E) and the
transcript is written in English instead. It needs a model that translates: the
built-in Whisper, or a multilingual Whisper you downloaded (not the ones marked
English). With any other model, or for an English recording, the box is
unavailable.

When it finishes, you hear how long the recording was and how many words came
out. Open **Notifications** (Ctrl+Shift+N) and press Enter on the transcript to
review it. The **Review Transcript** window shows it read-only, with:

- **Type into a Field** - types the transcript, or only the part you
  selected, into another program. QUILL Transcribe says "Switch to the field
  you want. The phrase is typed there.", and types it once you are there, with
  the same checks as dictation;
- **Copy All** - puts the whole transcript on the clipboard;
- **Save As** - saves it as a text file where you choose;
- **Open in QUILL** - opens it in QUILL to edit.

Nothing is typed, copied or saved unless you choose it.

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

## Dictate Here from Quill Cast and Quill Radio

Quill Cast and Quill Radio have no speech engine of their own. Their **Edit >
Dictate Here** (Ctrl+F11) asks QUILL Transcribe to dictate into the field you
are in, such as Cast's Add Podcast box or Radio's Search Stations box.

- If QUILL Transcribe is running, it starts dictating there, just as if you had
  pressed your start and stop key, and you hear its usual "Dictation on".
- If it is not running, it starts in the tray and begins dictating when it is
  ready; Cast or Radio says "Starting QUILL Transcribe. Dictation starts here
  when it is ready." The first time, when QUILL Transcribe opens its window to
  set up, it does not start dictating; finish setting up, go back to the field
  and press Ctrl+F11 again.
- If Quill Inkwell is dictating, you hear that Inkwell is dictating, and
  nothing starts.

Your words, commands and never-type list all work as usual, because it is
QUILL Transcribe doing the dictating. Stop with your start and stop key, or say
"stop dictation".

## One microphone: QUILL, QUILL Lite and QUILL Transcribe

Only one program listens at a time, so the same words are never written twice.
The microphone belongs to whichever of QUILL, QUILL Lite, QUILL Transcribe and
Quill Inkwell started dictating first, for as long as it is dictating. QUILL
Transcribe waiting in the tray does not hold it, unless the wake phrase is on:
then it holds the microphone while it listens for the wake phrase, and lets go
whenever QUILL or QUILL Lite comes to the front.

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
- Recordings of your dictation are never kept. Words that were not written
  (held while paused, or typing that stopped part-way) are kept on this
  computer, sealed for your Windows account, until you write or discard them
  in Recent Phrases.
- The text of what you dictate is kept only if you turn on **Keep a dictation
  history**, for one, seven or thirty days; Clear History deletes it, and
  turning it off deletes it too. It is off unless you choose it.
- Words waiting in Review Dictation are kept in a file in QUILL's data folder
  while the window is open, so a crash does not lose them, and the file is
  deleted when you insert or discard them. Close keeps them for next time.
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
| Dictation status | Alt+F9 |
| Speak a command | F11 |
| Review dictation | Shift+F4 |
| Recent phrases | Shift+F11 |
| Switch dictation language | Ctrl+Shift+F11 |
| My words and phrases | Alt+Shift+F10 |
| Dictation commands | Ctrl+Shift+C |
| Dictation profile | Ctrl+Shift+F |
| Lock profile | Ctrl+Shift+L |
| Practice dictation | Ctrl+Shift+P |
| Choose model | Ctrl+M |
| Choose microphone | Ctrl+Shift+M |
| Model library | Ctrl+L |
| Dictation settings | Alt+Shift+F6 (or Ctrl+,) |
| Transcribe a recording | Shift+F5 (or Ctrl+O) |
| Notifications | Ctrl+Shift+N |
| Minimize to tray | Ctrl+W |
| Exit | Ctrl+Q |
| User guide | Ctrl+F1 |
| Tutorials | Ctrl+Alt+F1 |
| Set up QUILL Transcribe | Ctrl+Alt+S |
| Check for updates | Ctrl+Alt+U |
| About QUILL Transcribe | Ctrl+Alt+I |

In the Practice Dictation window, Ctrl+F11 starts or stops dictation in the
practice field, and Escape closes it.

From any program, only these: your start and stop key (Alt+Shift+Backslash
unless you changed it), and your Command Key, show and hide key, Dictation
Status Key, Resume Key and Discard Held Words Key if you chose them.

F1 anywhere in QUILL Transcribe says what the window is for and what the
control you are on does.

## Getting help

Choose **Get Help from Support** in the Help menu (Ctrl+Alt+F2), or write to
support@community-access.org.
