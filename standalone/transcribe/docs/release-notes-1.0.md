# QUILL Transcribe 1.0 Release Notes

Version 1.0.0 (build 2), released November 1, 2026.

QUILL Transcribe is new. It types what you say into the program you are using,
with the same speech models and dictation you know from QUILL and QUILL Lite.

## The short version

Choose your model, press your key in the field you want, and speak. Your words
go into that field and nowhere else. Your speech stays on your computer unless
you choose an internet model yourself.

## New in this release

Everything in QUILL Transcribe is new, but if you tried a test build, these
are the things that arrived since. The full list, grouped by area, is in the
changelog (`CHANGELOG` in the docs folder); each part of the user guide named
here explains one in full.

**Starting and stopping.** The start and stop key is **Alt+Shift+Backslash**
from the start, chosen in **File > Start and Stop Key...**
(**Ctrl+Alt+Shift+D**), and every key box has **Record Key**. Hold the key
to talk, or say the wake phrase "Quill dictate" (both off until you turn
them on). Three more keys you can choose ask for Dictation Status, resume, or
discard held words from the program you are in. A list of programs
dictation never types into is in More Dictation Settings (**Alt+N**).

**What you hear.** Your screen reader no longer says "c" or "period" after
each phrase. A soft tick plays while a slow phrase is worked on. The words
heard so far appear on a braille display, and **Dictation Status**
(**Alt+F9**) says what dictation is doing in one sentence. Emoji are typed
whole.

**Commands and correcting.** Say "QUILL" before a command so it is never
typed ("QUILL scratch that"), or press **F11** and say it. Spell an address
across pauses, say a Markdown link, and insert snippets, abbreviations and
clips by voice. "Correct that", "replace Tuesday with Wednesday" and
"delete last sentence" work in other programs on the words QUILL
Transcribe typed itself. Dictation profiles (**Ctrl+Shift+F**), a dictation
style, and "QUILL review that" (**Shift+F4**) are there when you want
them. See "Commands while dictating into other programs".

**Your words and settings.** Your dictation settings can be shared with
QUILL, QUILL Lite and Quill Inkwell (**Alt+Q** in More Dictation
Settings). My Words and Phrases (**Alt+Shift+F10**) imports and exports.
**Recent Phrases** (**Shift+F11**) keeps what could not be typed until you
type or discard it, and a dictation history is kept only if you turn it on.

**Models.** **Recommended for this computer** says which model suits your
computer and why, every model has a tier, and twelve speech providers can be
used with your own account. See "Models".

**Advice tested on real speech.** The recommendation now rests on tests with
recordings of real people, not a synthetic voice. For English on a computer
with 8 GB of memory and four cores it names NVIDIA Parakeet Unified 0.6B,
which got 3.2 percent of words wrong on audiobooks no model was trained on,
against 6.5 for the built-in Moonshine. For Spanish on 8 GB it names NVIDIA
Parakeet TDT 0.6B v3: 4.4 percent wrong, against 30.5 for the built-in
Whisper. On 4 GB the built-in models are still the advice. Moonshine base no
longer drops phrases longer than about eight and a half seconds, and no
longer loses a word where a long phrase is cut: the pieces overlap by half a
second. See "How we chose: tested on real speech".

**A better Spanish model, said once.** The first time you dictate in Spanish
on a computer that can run Parakeet TDT v3 (in practice, 8 GB of memory and
four cores), while your Spanish would go to the built-in Whisper, you hear
one sentence. For example: "For Spanish, NVIDIA Parakeet TDT 0.6B v3 gets
about 6 percent of words wrong, against 29 for the built-in model. It is a
670 MB download in the model list." Nothing is downloaded or changed. You
hear it once across every QuillVille program, and a computer with 4 GB hears
nothing. See "Dictating in Spanish".

**Removed: five English-only models.** Distil-Whisper small.en, Whisper
small.en, Distil-Whisper medium.en, Whisper medium.en and Distil-Whisper
large-v3 are no longer offered. Whisper base.en and every Whisper model
without ".en" in its name stay. On real recordings, NVIDIA Parakeet Unified
0.6B got 3.2 percent of words wrong on the held-out audiobooks, against 3.6
to 6.3 for these five. It also ran faster on one processor thread, in the
same or a smaller memory tier. If one of them was your model, it becomes Parakeet
Unified if you have already downloaded it, and otherwise the built-in model.
Nothing is downloaded, and you are told once, the next time dictation starts.
The downloaded files are not deleted: they stay in
`%LOCALAPPDATA%\QuillVille\Dictation\models` (in a portable copy,
`data\dictation\models` inside the portable folder), in a folder named
`whisper-small.en-int8`, `whisper-distil-small.en-int8`,
`whisper-medium.en-int8`, `whisper-distil-medium.en-int8` or
`whisper-distil-large-v3-int8`. Delete that folder to free the space. To use
Parakeet Unified, open the Model Library (**Ctrl+L**), download it, and press
**Use for Dictation** (**Alt+U**). See "Models removed in October 2026".

**Practice.** **Practice Dictation** (**Ctrl+Shift+P**) has a field of its
own and a recognition test, and **Help > Tutorials...** (**Ctrl+Alt+F1**)
has five lessons. See "Practice and lessons".

**Recordings and sounds.** Transcribe a Recording can translate Spanish into
English (**Alt+E**), and Review Transcript can type the transcript into a
field (**Alt+F**). **Options > App Sounds Play On...** (**Ctrl+Shift+S**)
chooses where QUILL Transcribe's sounds play, and **Alt+Shift+M** turns them
off. In the window, **Alt+W** opens the Window menu and **Discard Held
Words** is **Alt+C**.

## What is in 1.0

### Dictation into any program

Put the cursor where you want to write, press your start and stop key, and
speak. Each phrase is typed when you pause. Press the key again, or say "stop
dictation", to stop.

The start and stop key is **Alt+Shift+Backslash** unless you change it. To
change it, choose File > Start and Stop Key... (Ctrl+Alt+Shift+D): type the
key, or press **Record Key...** and press it. If you empty the box, the tray
menu starts and stops dictation instead: choose Start Dictation, switch to the
field you want, and dictation starts there.

### Quiet with your screen reader

Your screen reader echoes what is typed, and because a phrase arrives faster
than it can speak, you would hear only the last character: "period" after
every sentence. When your phrase feedback is a tone or nothing, QUILL
Transcribe presses Ctrl on its own straight after the words, which every
screen reader takes as "stop talking". When you have chosen to hear phrases
read back, you hear everything, punctuation included.

### Paused, never misplaced

If you move to another field or program while dictating, QUILL Transcribe stops
typing and tells you. What you say next is held, not typed anywhere. Go back and
choose Resume to have it typed where you started, choose Resume in This Field to
write where you are now, or discard it.

### The model you chose

The built-in Moonshine is chosen for you and works with nothing downloaded and
no internet; the built-in Whisper is there too, and both know Spanish (Moonshine
through Whisper's multilingual model). Choose Model (Ctrl+M) shows every model
with what matters: whether it runs on your computer or sends your speech over
the internet, its tier (Lightweight, Balanced or High accuracy), which
languages it knows, and whether it is downloaded. **Recommended for this
computer** names the model that suits your computer, and why, from our tests
with real recordings. Ten larger models, from 141 MB to 1.8 GB, download
from the Model Library (Ctrl+L) only when you ask.

The one you choose is the one that runs. If it cannot run, you are told, and
nothing else is quietly used instead. Use the Built-in Model This Time (Ctrl+B)
is there when you want to keep going anyway.

### Your own account, if you want it

OpenAI, with your own key, and twelve speech companies, from Microsoft Azure
to IBM Watson, can do the listening instead. Set them up in Dictation Settings
(Speech Providers...); keys go to Windows Credential Manager. Nothing is sent
until you say yes, and No is the default. Choose Model does not list the
providers yet: choose them in Dictation Settings.

### Set up in one page

The first time it opens, QUILL Transcribe asks for a microphone, with a quick
test, a model, a key if you want one, and whether to start with Windows. Skip
changes nothing.

### Recordings too

Transcribe a Recording turns an audio or video file into text in the
background. Review the transcript, then copy it, save it, or open it in QUILL.

### With Quill Inkwell

Only one program dictates at a time. While QUILL Transcribe runs, Inkwell's
Dictate Anywhere key is passed to it. The first time it runs, QUILL Transcribe
brings over the settings and key you chose for Dictate Anywhere in Inkwell.

### Dictate Here in Quill Cast and Quill Radio

Quill Cast and Quill Radio have no speech engine of their own. Their Edit >
Dictate Here (Ctrl+F11) asks QUILL Transcribe to dictate into the box you are
in, starting it in the tray if it is not running.

## Good to know

- QUILL Transcribe never reads what is already in the other program.
- It will not type into password fields, into programs running as
  administrator, into QUILL's own windows, or into a program on your list of
  programs dictation never types into (More Dictation Settings, Alt+N), and it
  says why.
- Dictation speaks English or Spanish. In Spanish, commands stay in English for
  now.
- Nothing is recorded until you start, and recordings of your voice are never
  kept. Words that could not be typed are kept, sealed for your Windows
  account, until you write or discard them; a history of what you said is kept
  only if you turn it on.
- F1 on any window or control says what it is for.

Questions and problems: Get Help from Support in the Help menu, or
support@community-access.org.
