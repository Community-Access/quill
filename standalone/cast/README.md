# QUILL Cast

Accessible, screen-reader-first podcasts as a standalone Windows app, from the QUILL project.

QUILL Cast is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.podcasts`) and runs the exact same podcast feature code QUILL itself uses: the same Podcast Manager, pinned views, Inbox, Play Queue, download engine, and dialogs. This repository holds only what exists because QUILL is not in the picture: the product wrapper (entry point), the installer, and this app's own documentation. Everything shared stays upstream, so QUILL Cast tracks QUILL automatically.

## What it does

- **Your library, on the main page**: the same pinned views (Favorites, New Episodes, Continue Listening, Inbox) and nested folders the Manager shows, with a full context menu and one state-aware Play/Pause/Stop button. Enter on a show plays its next unplayed episode directly.
- Subscribe by search, feed URL, or OPML import; export your subscriptions any time.
- Private feeds: subscribe to username/password-protected shows (Patreon supporter feeds, premium and members-only feeds) -- prompted automatically when a feed needs a sign-in, managed later via Feed Credentials... on the show's context menu. Passwords live in Windows Credential Manager (or DPAPI-encrypted in the portable data folder), are only ever sent to the feed's own host, and never appear in OPML exports.
- The full Podcast Manager: pinned Favorites / New Episodes / Continue Listening views, an Inbox that triages episodes into your own folders, and Search Everywhere across shows, episodes, notes, and fetched transcripts.
- A cross-show Play Queue that survives restarts, reorders entirely from the keyboard, and now has its own top-level menu item and Command Palette entry.
- Resume Last Episode on Launch, a Recently Played submenu, and Mute/Unmute.
- Optional Sound Enhancements: an equalizer preset, a compressor, and Smart Speed (live silence trimming) -- full seek/scrub-bar support while enhanced (needs FFmpeg).
- Feed-provided transcripts (Podcasting 2.0), episode notes that timestamp the moment, chapters, sleep-timer-safe volume boost.
- Local podcasts: turn your own audio files into shows, with optional watched folders.
- Subscribe to ACB Media Podcasts in one command.
- Downloads with pause/resume all, auto-reconnect on a dropped connection (configurable attempts/wait), Always Sync for shows you want complete.
- Live in the system tray; share settings, subscriptions, and downloads with QUILL and Quill Radio (one data store in `%APPDATA%\Quill`).
- Check for its own updates from Help > Check for Updates; Help > Get FFmpeg restores the bundled ffmpeg if it ever goes missing.

Deliberately not included: QUILL's editor, AI, speech transcription engines, braille, and speech-synthesis stacks. Feed-provided transcripts are plain downloads and work fully; nothing here generates transcripts from audio.

## Install

Download `QUILL-Cast-Setup-<version>.exe` from this repository's Releases page and run it, or grab the portable zip and extract it anywhere -- its `data` folder keeps your whole library on the stick. Everything is bundled: ffmpeg ships alongside the app for audio processing, and neither flavor performs any downloads. The installer puts the app in its own directory and never touches an existing QUILL install.

## Run from source

```powershell
pip install .
quill-cast
# or, with the quill package already installed:
python -m quill.apps.podcasts
# or, for quick dev testing against a local QUILL checkout:
.\run-quill-cast.bat
```

## Build

```powershell
# Every release artifact from one onedir build -- the staged app folder,
# a portable zip, and the installer (needs Inno Setup 6.3+, an ffmpeg.exe
# to bundle, and the feedback token file; everything ships bundled, nothing
# is downloaded at install or runtime):
.\scripts\build_release.ps1 -FfmpegDir C:\path\to\ffmpeg\bin
```

The PyInstaller spec pulls the entire `quill` package -- code and data -- into an onedir build (`dist\QUILLCast\`), and excludes only the stacks Cast never touches (speech transcription and neural TTS engines; feed-provided transcripts are plain downloads and work fully). Onedir, not onefile: one built folder feeds both the portable zip and the installer, and the app starts instantly instead of re-extracting to a temp folder on every launch.

## Documentation

- [User Guide](docs/userguide.md)
- [Release Notes](docs/release-notes-1.0.md)
- [Changelog](CHANGELOG.md)
- [Product Requirements](docs/prd.md)

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
