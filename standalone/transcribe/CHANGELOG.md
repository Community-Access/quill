# Changelog -- QUILL Transcribe

All notable changes to QUILL Transcribe are recorded here. The fuller version
lives in `docs/CHANGELOG.md` (and its HTML and EPUB twins) and ships with the
app.

## Unreleased

- **Where QUILL Transcribe's own sounds play, and Alt+Shift+M to turn them off.** **Options > App Sounds Play On...** (Ctrl+Shift+S) offers System default, None (no sounds), or any sound card or headset by name. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and QUILL Transcribe says so once. **Alt+Shift+M** turns QUILL Transcribe's sounds off and back on where they were, and **Options > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.

- The start and stop key is Alt+Shift+Backslash from the start, and every key
  box has Record Key.
- With JAWS, no "c" with each phrase; with phrase feedback a tone or nothing,
  no "period" either. The same phrase said twice is written twice.
- Older Python 3.13 runtimes no app uses are removed by the installer.

## 1.0.0 - 2026-10-11

- The first release: dictation into the program you are using, locked to the
  field you started in, with QUILL's own local speech models, a tray menu,
  setup, and Transcribe a Recording.
