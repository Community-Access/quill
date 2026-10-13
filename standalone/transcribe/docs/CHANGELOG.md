# QUILL Transcribe Changelog

All notable changes to QUILL Transcribe are recorded here, newest first. The
release notes (`release-notes-1.0.md`) tell the same story as a narrative; this
file is the itemized list.

## Unreleased

### Dictating into other programs

- The start and stop key is **Alt+Shift+Backslash** from the start. Change it
  or empty it in Dictation > Start and Stop Key.
- Record Key, beside every key box: press the combination you want and it is
  written out for you. Typing the key still works.
- No more "c" before or after each phrase with JAWS: words are typed as the
  keys of your keyboard layout rather than as Unicode keystrokes.
- With phrase feedback set to a tone or to nothing, the screen reader no longer
  says "period" (or the last character) after every phrase: QUILL Transcribe
  presses Ctrl, which every screen reader takes as "stop talking", straight
  after the words. With the read-back on, you still hear everything.
- Saying the same phrase twice writes it twice. It was taken for the screen
  reader's echo and dropped.
- **Runs on Python 3.14, and older runtimes are cleaned up.** The shared QuillVille
  runtime this build installs is Python 3.14. The installer then removes older
  runtimes (Python 3.13) that no installed QuillVille app uses any more; one that
  an app or a shortcut still points to is left alone. Portable copies carry their
  own Python and change nothing outside their folder.

## 1.0.0 - 2026-10-11

The first release.

### Dictating into other programs

- Start and stop dictation with a key you choose, from the tray menu, or from
  the window. No key is registered until you choose one.
- Words are typed into the field that had the focus when dictation started,
  and only that field.
- When the focus moves, dictation pauses and holds what you say. Resume writes
  the held words back where you started; Resume in This Field moves dictation to
  the field you are in, after the same checks as a new start; Discard Held
  Words throws them away.
- Starting from the tray or the window waits until you are back in another
  program, and gives up after 20 seconds.
- Password fields, programs running as administrator, and QUILL's own windows
  are refused with a sentence that says why.
- A phrase Windows did not fully take is reported as possibly incomplete, never
  as written.
- The same commands, punctuation, spelling, capitals and spacing modes and
  word list as dictation in QUILL. Commands that need to read the other
  program's text are refused politely.

### Models and microphone

- Choose Model lists every model, marked as on this computer or over the
  internet, with its languages, size, source, licence and whether it is
  downloaded.
- The chosen model is the one that runs. A missing model, or one that will not
  load, stops the start and says so; Use the Built-in Model This Time uses
  Moonshine for one session, on purpose.
- OpenAI appears only with a saved OpenAI key, and asks before any speech is
  sent.
- The Model Library and Dictation Settings are the same windows QUILL uses.
- Choose Microphone, and a four-second microphone test in setup that stays on
  this computer.

### The app

- Set Up QUILL Transcribe: microphone, model, key, and starting with Windows,
  all on one page; Skip changes nothing.
- A tray menu that says what dictation is doing and which model it uses, and
  does everything the window does.
- A calm window: state, model and microphone, what happens next.
- Transcribe a Recording, with a read-only Review Transcript window to copy,
  save or open the result in QUILL.
- While QUILL Transcribe runs, Quill Inkwell's Dictate Anywhere key is passed
  to it, so only one program dictates at a time. The first run brings over
  Inkwell's Dictate Anywhere settings and key, without changing Inkwell.
- QUILL and QUILL Lite's Dictate in Other Programs hands your editor's
  dictation settings to QUILL Transcribe while it runs.
- F1 help on every window and control.
- Safe Mode listens to nothing, registers no keys and downloads nothing.
