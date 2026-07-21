# Changelog

All notable changes to QUILL Audio Studio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Update in one click -- Audio Studio installs it and restarts itself.** When an update is available, choose Download, then **Install and restart now**: Audio Studio applies the update (extracting the new portable files over your folder, or running the installer silently) and relaunches automatically, keeping all your settings and data. No more closing the app, unzipping, and swapping folders by hand. Shared across every Quill app.

## [1.0.0] - 2026-07-18

First release: the QUILL editor's Audio Studio as a self-contained standalone app for Windows and macOS, screen-reader-first throughout.

### Added

- Standalone app frame (`quillas.apps.studio`): home window with the three journey buttons and a "Your books" library, menu bar, status bar with spoken 25/50/75 percent run milestones, system tray (Open Audio Studio, Resume last book), Ctrl+Shift+P command palette, and in-app update checks against this repo's GitHub releases.
- The Audio Studio wizard with three journeys: Narrate Documents (source/filters, engine + voice with previews, round-robin rotation, voice casting rules, translated editions, chapter shaping with title preview, output and diagnostics, book details with Open Library / MusicBrainz lookup, plain-sentence summary), Build From Recordings (folder of audio to one chaptered master, library mode, silence trimming, pre-build chapter review), and Edit a Book.
- The Chapter Workbench: chapter-aware player (mpv engine with wx.media fallback, resume positions, pitch-preserved speed, "Where am I?"), split at playhead, set start to playhead, merge, rename, restore, silence-based chapter proposals, AI-proposed chapter titles (local transcription, text-only to the configured AI, reviewable), ACX check, chapter list import/export in five formats, split into per-chapter files, in-place MP3 saves and lossless M4B Save As.
- The listening layer: the home-window "Your books" library is a tree (Favorites, In Progress, Recently Played, Inbox, plus your own folders) that populates as you open books, with a keyboard-complete context menu (Open, Reveal in Folder, Favorite, Move to Folder, New Folder, Remove) built on `quillas/ui/audio_studio/library_tree.py` over `quillas/core/audio_studio/library.py`; Resume on launch (Studio menu, opt-in) that reopens the most recently played book at its saved position, silently skipping if the file is gone; a Recently Played submenu (Studio menu); media keys while a Workbench is open (Play/Pause, Stop, Next chapter, Previous chapter route to the active player, unregistered on exit); per-book volume and mute (each book remembers its own level and mute state, Ctrl+M toggles mute); a Sleep Timer (Book Tools menu) that stops playback after N minutes or at the end of the current chapter, with a cancellable watcher; and a Play Queue (Book Tools menu) that auto-advances to the next book when the current one finishes and the Workbench is closed. `open_book_in_workbench` threads optional host callbacks (`on_player_ready`, `on_finished`, `on_volume`, `on_mute`, `on_closed`) to the player so the shell drives media keys, per-book prefs, history, and queue auto-advance.
- Voice engines with on-demand downloads: Windows SAPI 5, DECtalk, Piper, Kokoro, eSpeak-NG, macOS say; ElevenLabs (installs on demand) and OpenAI/Gemini/ElevenLabs cloud voices with user-supplied keys. Speech Hub, Manage Speech Models, Pronunciation Dictionaries, Download Optional Components (with Test/Remove), and Get FFmpeg in the Voices menu. A "Generating preview, please wait" spoken cue for slow live previews (on by default).
- AI menu with the Set Up AI wizard (cloud provider with your own key, or local via Ollama) powering AI chapter titles, translated editions, and cloud narration voices.
- Book Tools menu: Publish a Finished Book (local RSS feed, folder show feed with accessible show notes, SFTP upload with Credential Manager storage, Auphonic mastering), Make a Podcast Feed From a Folder, ACX Compliance Check with plain-language recommendations, plus Sleep Timer, Play Queue, and Mute Playback.
- `.quilljob` job files: save an exact run from the summary page; re-run it from Studio > Open Job File or the wizard's first page.
- Preferences (Ctrl+Comma): automatic update checks, Alt+F4-to-tray (opt-in), spoken run milestones, and the close-window policy (Ask when work is running / Exit / Minimize to Tray), stored app-locally so shared QUILL settings stay untouched.
- Save-a-diagnostics-bundle offer after a component-install failure: a redacted zip support can read.
- Safe Mode (`QUILL_SAFE_MODE=1` or `--safe-mode`): disables AI, publishing, and component downloads.
- Shared data store with QUILL, Quill Radio, and QUILL Cast (`%APPDATA%\Quill`), with full portable mode via a `data` folder next to the exe containing a `storage-mode.json` marker (`{"mode": "portable"}`).
- Packaging: PyInstaller onedir build (`quill-audio-studio.spec`, `launcher.py`), Inno Setup installer (`installer/quill-audio-studio.iss`), portable zip, bundled ffmpeg and mpv; vendoring tooling (`scripts/vendor_from_quill.py`, `scripts/vendor_tests.py`) to re-sync from the QUILL monorepo; vendored unit test suite.
