# Changelog -- QUILL Transcribe

All notable changes to QUILL Transcribe are recorded here. The fuller version
lives in `docs/CHANGELOG.md` (and its HTML and EPUB twins) and ships with the
app.

## 1.0.0 - 2026-11-01

Testing rebuild: **1.0.0 (build 3)**. The packages have not been published
yet. 1.0.0 is the first public release, planned for 1 November 2026, so
everything here is new in it, including what the first test builds already
did. This is the short list, grouped by area in the same order as
`docs/CHANGELOG.md`, which has the detail.

### Since build 3 (2026-10-31)

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which currently carries PyMuPDF 1.28.2 under AGPL-3.0 through the shared
  GLOW dependency; Transcribe does not itself expose GLOW. Release-specific
  source and legal review are required before the next public release.
  Portable contents must be checked separately. See Licences and Notices and
  the PyMuPDF distribution review.
- **Sharp text at any display scaling** (2026-10-31). QUILL Transcribe now handles
  each monitor's scaling itself instead of letting Windows stretch it, so
  text stays sharp at 125, 150 and 200 percent and on monitors with
  different scaling, and windows and list columns keep their proportions.
  Setting the environment variable `QUILL_DPI_UNAWARE` to `1` turns this off,
  for diagnosing a display problem (#1702).
- **Pygments in the notices** (2026-10-31). The shared runtime now bundles
  Pygments, which QUILL and QUILL Lite use to read code and web pages for
  spell check, so QUILL Transcribe's third-party notices list it.

### Dictating into other programs

- The first release: dictation into the program you are using, locked to the
  field you started in, paused and held when the focus moves, with QUILL's own
  local speech models, a tray menu, setup, and Transcribe a Recording.
  Password fields, programs running as administrator and QUILL's own windows
  are refused with a sentence that says why.
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

### Models, microphone and speech providers

- Choose Model and Choose Microphone; the model you chose is the one that runs.
- Recommended for this computer, with tiers (Lightweight, Balanced, High
  accuracy), from tests on real speech; Switch to Recommended Model and an
  offer to delete the old model's files; five English-only models removed;
  twelve speech providers with your own account; a full "Models" chapter in
  the user guide.

### Practice and lessons

- Practice Dictation (Ctrl+Shift+P), the recognition test, and five tutorials
  (Ctrl+Alt+F1).

### Recordings

- Transcribe a Recording translates Spanish into English (Alt+E), and Review
  Transcript can type the transcript into a field (Alt+F).

### Setup, the window, the tray and sounds

- **Options > App Sounds Play On...** (Ctrl+Shift+S) and Alt+Shift+M to turn
  QUILL Transcribe's sounds off. Alt+W opens the Window menu again; Discard Held
  Words is Alt+C.

### QUILL Transcribe and the QuillVille family

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

### Help, updates and release channels

- **Help > What's New** (Ctrl+Shift+F1, new in build 3) opens the changelog in
  your browser.
- Help > Release Channel... (Alt+H, L): Stable, Beta or Dev.

### Installing and Safe Mode

- Runs on Python 3.14; older Python 3.13 runtimes no app uses are removed by
  the installer.
- Safe Mode listens to nothing, registers no keys and downloads nothing.
