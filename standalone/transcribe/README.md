# QUILL Transcribe

Say it, and it is typed into the program you are using. QUILL Transcribe is an
accessible, screen-reader-first dictation app for Windows from Community Access:
an email in Outlook, a form in your browser, a note in Notepad, a document in
Word. It lives in the system tray, uses QUILL's own speech models on your
computer, writes only into the field you started in, and pauses rather than
typing somewhere else when the focus moves.

Version 1.0.0 (build 2), released on 2026-11-01 (the first public release;
not yet published as of 2026-10-17). See `docs/userguide.md`,
`docs/release-notes-1.0.md` and `docs/CHANGELOG.md`.

## Downloads

- `QUILL-Transcribe-Setup-Shared-1.0.0.exe` -- the installer (recommended).
  Installs the shared QuillVille runtime if it is absent, then the app with its
  speech models. For the current user only; no administrator rights needed.
- `QUILL-Transcribe-Portable-1.0.0.zip` -- unpack anywhere; settings stay in its
  own `data` folder next to the app.

Neither download fetches anything on first use. Both include the built-in
Moonshine (the default) and Whisper speech models, Whisper's multilingual model
for Spanish, and the sherpa-onnx engine that runs them. Larger models (141 MB
to 1.8 GB, tiered Lightweight, Balanced or High accuracy) download only when
you ask, from Model > Model Library (Ctrl+L). OpenAI and twelve speech
providers can be used with your own account, after a question whose default
is No. The user guide's "Models" chapter explains how to choose.

## This folder

The app itself lives in the shared `quill` package (`quill/apps/transcribe*.py`,
with its speech code in `quill/core/windows_dictation/`). This folder carries
only the launcher, the installer, the icon and these documents.

Build both downloads with `scripts\build_release.ps1`.
