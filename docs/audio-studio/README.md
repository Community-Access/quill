# QUILL Audio Studio

Accessible, screen-reader-first audiobook and audio production as a standalone Windows and macOS desktop app - the QUILL editor's Audio Studio, extracted into its own self-contained product.

Turn a folder of documents into a chaptered audiobook read by any voice (or a whole cast), stitch a folder of recordings into one chaptered master, and fix a finished book entirely by ear in the Chapter Workbench - then check it against ACX and publish it as a podcast feed, over SFTP, or through Auphonic. Every surface is keyboard-first and announced through your screen reader.

## Features

- **Three journeys** in one guided wizard: Narrate Documents (.docx/.md/.html/.txt to speech audio or an M4B/MP3 audiobook), Build From Recordings (a folder of audio to one chaptered master), and Edit a Book (the Chapter Workbench).
- **Voice engines**: Windows SAPI 5, DECtalk, Piper and Kokoro (neural, fully offline), eSpeak-NG, macOS `say`; ElevenLabs plus OpenAI/Gemini/ElevenLabs multilingual cloud voices with your own API key. Engines and models download on demand; every voice previews with the same comparable phrase.
- **Casting and translation**: round-robin voice rotation, glob-based casting rules per chapter, and translated editions via a configured AI provider or local LibreTranslate.
- **Production honesty**: audition mode, dry runs, incremental rebuilds, ACX loudness normalization, fades and tempo, spoken opening/closing credits, spoken progress milestones, and portable `.quilljob` recipe files.
- **Chapter Workbench**: chapter-aware player (resume positions, 0.75x-2x pitch-preserved speed, "Where am I?"), split-at-playhead surgery, silence-based chapter proposals, AI-proposed chapter titles (local transcription, text-only to your AI, always reviewable), tags and cover, chapter list import/export (Audacity, CUE, timestamps, Podcasting 2.0 JSON, CSV), split into per-chapter files.
- **Publishing**: local RSS feed, whole-folder show feed with accessible show notes, SFTP upload (credentials in the Windows Credential Manager, strict host keys), and Auphonic mastering - each explicit, consented, cancellable, and announced.
- **Listening layer**: the home window's Your-books library is a tree (Favorites, In Progress, Recently Played, Inbox, plus your own folders) that fills in as you open books; resume-on-launch, a Recently Played list, media keys, per-book volume and mute (Ctrl+M), a sleep timer (including stop-at-end-of-chapter), and a play queue that opens the next book for you.
- **App comforts**: system tray with Resume-last-book, opt-in Alt+F4-to-tray, Ctrl+Shift+P command palette, in-app update checks, Safe Mode.

## Quick start

From source (Python 3.12+):

```powershell
pip install -e ".[ui]"
python -m quillas
```

Or just run `run-quill-audio-studio.bat`, which finds a suitable environment (this repo's `.venv`, a sibling `S:\QUILL\.venv`, or `python` on PATH). `run-quill-audio-studio-safe-mode.bat` launches with AI, publishing, and downloads disabled.

Optional extras:

- `pip install -e ".[ui,kokoro]"` - the Kokoro neural TTS runtime (models download on demand in-app).
- `pip install -e ".[ui,ssh]"` - SFTP publishing (paramiko).
- `pip install -e ".[ui,dev]"` - pytest and ruff for development.

End-user documentation lives in `docs/userguide.md` (also opened in-app via Help > User Guide).

## Repo layout

- `quillas/` - the application package: the complete Audio Studio dependency closure vendored from the QUILL monorepo (with `quill.*` imports rewritten to `quillas.*`), plus the standalone app shell. `quillas/apps/studio.py` is the app frame and entry point; `quillas/ui/audio_studio/` is the wizard, Chapter Workbench, player, and publish surfaces.
- `scripts/vendor_from_quill.py` - re-syncs the vendored closure from `S:/QUILL` (copies seed packages/modules, rewrites imports, chases the import graph). Re-runnable; never touches hand-written files.
- `scripts/vendor_tests.py` - vendors the matching test suite the same way.
- `tests/` - the vendored unit tests plus the audio corpus; run with `pytest -q`.
- `launcher.py` and `quill-audio-studio.spec` - the PyInstaller entry script (portable-mode detection, bundled-tools anchoring) and onedir build spec.
- `installer/quill-audio-studio.iss` - the Inno Setup script for the installer; `scripts/build_release.ps1` stages ffmpeg/libmpv/docs into `dist/QuillAudioStudio` and drives both the installer and the portable zip.
- `assets/` - the app icon.

## Building releases

`scripts/build_release.ps1` builds the PyInstaller onedir bundle, stages the bundled tools and rendered docs, then produces the installer (via ISCC on `installer/quill-audio-studio.iss`) and the portable zip. The installed copy uses the shared `%APPDATA%\Quill` store; the portable zip ships a `data` folder next to the exe that keeps everything self-contained.

## Relationship to QUILL, Quill Radio, and QUILL Cast

- **QUILL** (`Community-Access/quill`) is the upstream: the Studio's wizard, Workbench, batch pipeline, and publish code are the same code QUILL ships, vendored here so this repo builds and runs without the monorepo. `scripts/vendor_from_quill.py` keeps the copy honest.
- **Quill Radio** and **QUILL Cast** are sibling standalone apps built on the same `AppShellFrame` shell (tray, palette, updates, bug reporting). Unlike them - thin wrappers that depend on the `quill` package - this repo is self-contained.
- All four apps share one data store (`%APPDATA%\Quill`, or the portable `data` folder): settings, voices, downloaded engines, and your book library are configured once and available everywhere.

## License

MIT - see `LICENSE`.
