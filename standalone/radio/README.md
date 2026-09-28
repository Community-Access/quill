# Quill Radio

Accessible, screen-reader-first internet radio for Windows, from the QUILL project by Community Access.

Version 3.0.2, released 2026-09-28.

Quill Radio is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.radio`) and runs the same radio code QUILL itself uses: the same station browser, favorites, recorder, scheduler and dialogs. This folder (`standalone/radio` in the QUILL repository) holds only what exists because QUILL is not in the picture: the packaging wrapper (entry point), the installer, and this app's own documentation. Everything shared lives in the `quill` package, so Quill Radio tracks QUILL automatically.

## What it does

- Opens with keyboard focus on your favorite stations. Arrow to one and press Enter; that is the whole loop.
- Browse Stations (Ctrl+B): one tree of every source -- the station directory by country, language, genre and what is trending, NOAA Weather Radio, radio reading services, podcasts, audiobooks, archives and television. No account or sign-in anywhere.
- A station catalog on your own computer, so browsing and searching answer at once, even offline.
- Search Stations (Ctrl+F) that understands frequencies, call signs and places, and scans a station's own web site for its stream when no directory has it.
- Rewind live radio (Ctrl+Shift+Left) and go back to live (Ctrl+Shift+L); pause and resume podcasts, recordings and files (Ctrl+Space).
- Record what is playing (Ctrl+R), record several stations at once, and schedule recordings for later (Ctrl+Shift+S).
- Every window reaches the player: volume, mute, stop and the rest work from any Quill Radio window.
- Sound Enhancements (Ctrl+E): equalizer presets, a compressor, mono and one-ear modes, night mode and broadcast polish, applied live.
- Lives in the system tray, with a system-wide show and hide key (Ctrl+Alt+Shift+R) and the keyboard's media keys.
- F1 help on every control, 41 guided tutorials (Ctrl+Alt+F1), and a Command Palette (Ctrl+Shift+P).
- Shares favorites, settings and recordings with QUILL and QUILL Cast when installed (one data store in `%APPDATA%\Quill`). A portable copy keeps its own.

Deliberately not included: QUILL's editor, AI writing tools, transcription, braille and speech-synthesis stacks. This is the radio, and just the radio.

## Install

Downloads are on the [QUILL Releases page](https://github.com/Community-Access/quill/releases/tag/quill-radio-v3.0.2), under the tag `quill-radio-v3.0.2`. There are two:

- **`Quill-Radio-Setup-Shared-3.0.2.exe`** -- the installer, and the right choice for most people. It installs the shared **QuillVille Runtime** if it is not already on the computer, then the app, with a Start Menu entry and an uninstaller. Your settings, favorites and recordings live in the shared Quill data folder in your Windows profile, so QUILL and QUILL Cast see them too.
- **`Quill-Radio-Portable-3.0.2.zip`** -- the portable copy. It is fully self-contained, with its own genuine Python and the bundled FFmpeg and mpv. Unpack it anywhere, a USB stick included, and run `QuillRadio\QuillRadio.exe`. Nothing downloads when it runs.

A portable copy writes nothing to the computer it runs on, from the very first launch, with no setting to find first. Settings, favorites, history, logs and caches live in the `data` folder beside `QuillRadio.exe`; recordings and downloads go to `Recordings` and `Downloads` folders beside it. Start with Windows and the wake-for-recording task are unavailable, because both would write to the host. Delete the `data` folder and it becomes an ordinary copy that uses this computer's profile.

QUILL, Quill Radio, Quill Weather and QUILL Audio Studio share one QuillVille Runtime, installed once per user and reference-counted, so it is removed only when the last app that needs it is uninstalled.

Pre-release builds of 3.0 also offered a thin "Lite" installer and a small Companion zip. Both are retired. If you have either, nothing is lost: the installer upgrades a thin install in place and keeps your data, and Check for Updates on a Companion copy offers the installer.

### Updates

**Help > Check for Updates...** (Ctrl+Alt+U) offers the download that matches your copy: the portable zip to a portable copy, the installer to everything else. The Update Available window puts the release's What's New notes in a read-only box that focus lands on, with **Update** (Enter) and **Close** (Escape). A check you ask for that finds nothing says "You are up to date". A quiet check once a day at launch speaks only when an update exists; turn it off in Preferences (Ctrl+,).

### Code signing and SmartScreen

Release builds are code-signed: the installer, its uninstaller and the app carry an Authenticode signature. While a new release builds reputation, or if you run an unsigned development build, Windows SmartScreen may still show a caution. Choose **More info**, check the publisher, then choose **Run anyway**.

## Run from source

```powershell
pip install .
quill-radio
# or, with the quill package already installed:
python -m quill.apps.radio
# or, for quick dev testing against a local QUILL checkout:
.\run-quill-radio.bat
```

## Build a release

```powershell
# One command builds both downloads from one onedir build:
#   dist\QuillRadio\                         the staged app folder
#   dist\Quill-Radio-Portable-<ver>.zip      the portable copy
#   dist\Quill-Radio-Setup-Shared-<ver>.exe  the installer
# The Python interpreter, Inno Setup (ISCC) and FFmpeg are found from the
# checkout; pass -Python, -Iscc or -FfmpegDir to override. No GitHub or
# feedback token is needed (2026-09-26): all feedback goes by email to
# support@community-access.org. -Sign turns on Authenticode signing
# (docs/code-signing.md). A release also rebuilds the station catalog seed;
# -SkipCatalog is for development builds only.
.\scripts\build_release.ps1 -Sign
```

The PyInstaller spec is onedir on purpose: instant startup (no per-launch temp extraction), and one built folder feeds both the portable zip and the installer. It pulls the entire `quill` package -- code and data -- and excludes only the stacks Radio never touches (transcription and neural TTS engines). The build fails if the shared runtime it packages does not contain `quill.apps.radio`, and it removes any retired Lite or Companion files for this version from `dist`.

## Documentation

- [User Guide](docs/userguide.md) -- every feature, step by step (Help > User Guide, Ctrl+F1)
- [Tutorials](docs/tutorials.md) -- the guided lessons, generated from the ones
  the app itself teaches (Help > Tutorials..., Ctrl+Alt+F1)
- [Release Notes (3.0)](docs/release-notes-3.0.md) -- also
  [2.0](docs/release-notes-2.0.md), [1.0 and 1.1](docs/release-notes-1.0.md)
- [Changelog](CHANGELOG.md)
- [Product Requirements](docs/prd.md)

## Support

Quill Radio is made by Community Access. Write to support@community-access.org, or use **Help > Get Help from Support...** (Ctrl+Alt+F2) inside the app, which fills in the version for you. A person reads every message.

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
