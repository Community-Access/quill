# Changelog -- QUILL Transcribe

All notable changes to QUILL Transcribe are recorded here. The fuller version
lives in `docs/CHANGELOG.md` (and its HTML and EPUB twins) and ships with the
app.

## Unreleased

- The start and stop key is Alt+Shift+Backslash from the start, and every key
  box has Record Key.
- With JAWS, no "c" with each phrase; with phrase feedback a tone or nothing,
  no "period" either. The same phrase said twice is written twice.
- Older Python 3.13 runtimes no app uses are removed by the installer.
- One microphone across QUILL (Locked Dictation too), QUILL Lite and QUILL
  Transcribe: a second start is refused with the name of the program listening
  and the key that stops it, and QUILL Lite's
  window is refused like QUILL's, with "press Ctrl+F11 to dictate here".
- The editors' dictation keys work here too: Ctrl+F11, Alt+Shift+F6,
  Alt+Shift+F10 (My Words and Phrases, new here), Ctrl+Shift+F11 (Switch
  Dictation Language, new here) and Shift+F5. Ctrl+D, Ctrl+, and Ctrl+O still work.
- A soft tick while a phrase is still being worked on, after the first second,
  and "Still working on that phrase." once a session after four. On by default
  here; More Dictation Settings turns it off. Words-only feedback gets the
  sentence without the tick; no feedback gets neither.
- Recent Phrases (Shift+F11): the last 20 phrases of this run, to type again or
  copy. Memory only.
- "insert snippet", "insert abbreviation" and "paste clip" work in any program.
- "What can I say" is a spoken answer while dictating, and Dictation Commands
  lists only what works in other programs, with your own phrases.

## 1.0.0 - 2026-10-11

- The first release: dictation into the program you are using, locked to the
  field you started in, with QUILL's own local speech models, a tray menu,
  setup, and Transcribe a Recording.
