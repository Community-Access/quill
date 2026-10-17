# QUILL Transcribe 1.0 Release Notes

Released November 1, 2026.

QUILL Transcribe is new. It types what you say into the program you are using,
with the same speech models and dictation you know from QUILL and QUILL Lite.

## The short version

Choose your model, press your key in the field you want, and speak. Your words
go into that field and nowhere else. Your speech stays on your computer unless
you choose an internet model yourself.

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
computer** names the model that suits your computer, and why. Fifteen larger
models, from 141 MB to 1.8 GB, download from the Model Library (Ctrl+L) only
when you ask.

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
