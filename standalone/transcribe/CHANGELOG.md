# Changelog -- QUILL Transcribe

All notable changes to QUILL Transcribe are recorded here. The fuller version
lives in `docs/CHANGELOG.md` (and its HTML and EPUB twins) and ships with the
app.

## Unreleased

Version 1.0.0 (build 2), released on 1 November 2026: the first public
release. Everything here ships in it. This is the short list, grouped by area
in the same order as `docs/CHANGELOG.md`, which has the detail.

### Release and the QuillVille family

- Released on 1 November 2026, and from then on the QuillVille menu and tray
  menus of the other apps (Alt+Q, then T; Alt+U, then T in Quill Converter),
  with a download offer that asks first. Its own QuillVille menu opens the
  others on Ctrl+Alt+Shift+F7 to F11.
- Quill Cast's and Quill Radio's **Edit > Dictate Here** (Ctrl+F11) dictates
  into the box you are in through QUILL Transcribe, in every copy.
- One microphone across QUILL (Locked Dictation too), QUILL Lite, QUILL
  Transcribe and Quill Inkwell: a second start is refused with the name of the
  program listening and the key that stops it. QUILL Lite's window is refused
  like QUILL's, with "press Ctrl+F11 to dictate here".

### Starting, stopping and where it types

- The start and stop key is Alt+Shift+Backslash from the start, chosen in
  **File > Start and Stop Key...** (Ctrl+Alt+Shift+D), and every key box has
  Record Key. Three more optional keys: Dictation Status, Resume and Discard
  Held Words.
- Hold the key to talk, and the wake phrase "Quill dictate", both off until you
  turn them on.
- Programs dictation never types into (More Dictation Settings, Alt+N).
- A user guide section on the programs it has been tested with.

### What you hear, and what is typed

- Your screen reader no longer says "c" with each phrase; with phrase feedback a tone or nothing,
  no "period" either. The same phrase said twice is written twice.
- A soft tick while a phrase is still being worked on, after the first second,
  and "Still working on that phrase." once a session after four.
- A calmer spoken preview, dictation on your braille display, and Dictation
  Status (Alt+F9).
- Emoji and rarer characters are typed whole.

### Commands, spelling and correcting

- The command word ("QUILL scratch that"), command mode, the Command Key and
  Speak a Command (F11).
- Spell an address across pauses; a Markdown link by voice.
- "insert snippet", "insert abbreviation" and "paste clip" work in any program,
  with snippet blanks asked for by voice.
- "What can I say" is a spoken answer while dictating.
- Correcting in another program ("correct that", "replace ... with ...",
  "change that to", "delete last sentence"), with a second opinion from the
  other built-in engine.
- Dictation profiles (Ctrl+Shift+F), bold and italic by voice, fixing it when
  you correct yourself, and a dictation style.

### Review and polish

- Review Dictation (Shift+F4, "QUILL review that"), and polishing with AI only
  when you ask.

### Your words, settings and history

- Dictation settings shared with the family (Alt+Q in More Dictation
  Settings); the word list's new home; Import and Export in My Words and
  Phrases; backslashes in your phrases kept.
- The editors' dictation keys work here: Ctrl+F11, Alt+Shift+F6, Alt+Shift+F10
  (My Words and Phrases, new here), Ctrl+Shift+F11 (Switch Dictation Language,
  new here) and Shift+F5. Ctrl+D, Ctrl+, and Ctrl+O still work.
- Recent Phrases (Shift+F11), words that could not be typed kept until you
  type or discard them, and a dictation history that is off unless you turn
  it on.

### Models and speech providers

- Recommended for this computer, with tiers (Lightweight, Balanced, High
  accuracy); twelve speech providers with your own account; a full "Models"
  chapter in the user guide.

### Practice and lessons

- Practice Dictation (Ctrl+Shift+P), the recognition test, and five tutorials
  (Ctrl+Alt+F1).

### Recordings

- Transcribe a Recording translates Spanish into English (Alt+E), and Review
  Transcript can type the transcript into a field (Alt+F).

### Sounds and the window

- **Options > App Sounds Play On...** (Ctrl+Shift+S) and Alt+Shift+M to turn
  QUILL Transcribe's sounds off. Alt+W opens the Window menu again; Discard Held
  Words is Alt+C.

### Installing

- Runs on Python 3.14; older Python 3.13 runtimes no app uses are removed by
  the installer.

## 1.0.0 - 2026-11-01

- The first release: dictation into the program you are using, locked to the
  field you started in, with QUILL's own local speech models, a tray menu,
  setup, and Transcribe a Recording.
