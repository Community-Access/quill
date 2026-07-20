# Quill Radio

Accessible, screen-reader-first internet radio as a standalone Windows app, from the QUILL project.

Quill Radio is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.radio`) and runs the exact same radio feature code QUILL itself uses: the same station browser, favorites, recorder, scheduler, and dialogs. This repository holds only what exists because QUILL is not in the picture: the product wrapper (entry point), the installer, and this app's own documentation. Everything shared stays upstream, so Quill Radio tracks QUILL automatically.

## What it does

- Browse thousands of internet radio stations, keyboard-first, with a screen reader in mind at every step.
- Keep favorite stations one Enter press away; the favorites list has focus the moment the app opens.
- Record what you are hearing, or schedule a recording for later.
- Optional Sound Enhancements: an equalizer preset and a compressor, applied live (needs FFmpeg).
- Live in the system tray: close to tray, control playback from the tray menu.
- Share settings, favorites, and recordings with QUILL and QUILL Cast (one data store in `%APPDATA%\Quill`).
- Check for its own updates from Help > Check for Updates.

Deliberately not included: QUILL's editor, AI, transcription, braille, and speech-synthesis stacks. This is the radio, and just the radio.

## Install

Two flavors, both on this repository's Releases page, both fully bundled (ffmpeg included, no downloads ever):

- **`Quill-Radio-Setup-<version>.exe`** -- the system install: its own directory, Start Menu entry, uninstaller. Uses the shared Quill data in your Windows profile.
- **`Quill-Radio-Portable-<version>.zip`** -- extract anywhere (a USB stick included) and run `QuillRadio\QuillRadio.exe`. The bundled `data` folder keeps your favorites, history, and settings inside the app folder, so the whole thing travels -- exactly like QUILL portable.

Help > Check for Updates knows which flavor you run and downloads the matching artifact directly.

### A note on the SmartScreen warning (unsigned builds)

These releases are not yet code-signed, so Windows SmartScreen may warn the first time you run the installer or the portable exe. Choose **More info**, then **Run anyway**. The builds are produced directly from this repository's source by the maintainers; code signing is planned, and the warning will disappear once releases are signed.

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
# One command, three artifacts (staged onedir folder, portable zip, installer).
# Needs: the quill package + pyinstaller in the Python env, Inno Setup 6.3+,
# an ffmpeg.exe to bundle, and the issues-only feedback token file (the build
# FAILS without it rather than shipping a broken Report a Bug).
.\scripts\build_release.ps1 -TokenFile S:\token.txt -FfmpegDir C:\path\to\ffmpeg\bin
```

The PyInstaller spec is onedir on purpose: instant startup (no per-launch temp extraction), and one built folder feeds both the portable zip and the installer. It pulls the entire `quill` package -- code and data -- and excludes only the stacks Radio never touches (transcription and neural TTS engines).

## Documentation

- [User Guide](docs/userguide.md)
- [Release Notes (2.0)](docs/release-notes-2.0.md) -- also [1.0 and 1.1](docs/release-notes-1.0.md)
- [Changelog](CHANGELOG.md)
- [Product Requirements](docs/prd.md)

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
