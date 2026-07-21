# QUILL Audio Studio

Accessible, screen-reader-first audio production as a standalone Windows app, from the QUILL project.

QUILL Audio Studio is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.studio`) and runs the exact same audio feature code QUILL itself uses: the same waveform editing, chapter markers, TTS narration, loudness checks, and publishing. This repository holds only what exists because QUILL is not in the picture: the product wrapper (entry point), the installer, and this app's own documentation. Everything shared stays upstream, so QUILL Audio Studio tracks QUILL automatically.

## What it does

- Edit spoken-word audio (audiobooks, podcasts, narration) keyboard-first, with a screen reader in mind at every step.
- Add and navigate chapter markers; export chaptered MP3/M4B audiobooks.
- Narrate text with neural text-to-speech (Kokoro / Piper), fetched on demand.
- Run an ACX-style loudness/quality check so an audiobook meets the retailer's spec before you submit it.
- Convert and export common formats via bundled FFmpeg (MP3, M4A/M4B, OGG, Opus, FLAC).
- Live in the system tray; share settings and voices with QUILL, Quill Radio, and QUILL Cast (one data store in `%APPDATA%\Quill`).
- Check for its own updates from Help > Check for Updates.

## Install

Two flavors, both on this repository's Releases page:

- **`Quill-AudioStudio-Setup-<version>.exe`** -- the system install: its own directory, Start Menu entry, uninstaller. Choose per-user or per-machine at install time. Uses the shared Quill data in your Windows profile.
- **`Quill-AudioStudio-Portable-<version>.zip`** -- extract anywhere (a USB stick included) and run `QuillAudioStudio\QuillAudioStudio.exe`. The bundled `data` folder keeps your settings inside the app folder, so the whole thing travels -- exactly like QUILL portable.

FFmpeg is bundled. The neural TTS engine and any transcription engine are fetched on demand through QUILL's shared, SHA-verified component system (the assets-v1 mirrors); to ship a fully-offline Studio with TTS bundled, see the note in `quill-audio-studio.spec`.

Help > Check for Updates knows which flavor you run and downloads the matching artifact directly.

### A note on the SmartScreen warning (unsigned builds)

These releases are not yet code-signed, so Windows SmartScreen may warn the first time you run the installer or the portable exe. Choose **More info**, then **Run anyway**. The builds are produced directly from this repository's source by the maintainers; code signing is planned, and the warning will disappear once releases are signed.

## Run from source

```powershell
pip install ".[ui]"
python -m quill.apps.studio
# or, for quick dev testing against a local QUILL checkout:
.\run-quill-audio-studio.bat
```

## Build a release

```powershell
# One command, both artifacts (staged onedir folder -> portable zip + installer).
# Needs: the quill package + pyinstaller in the Python env, Inno Setup 6.3+,
# an ffmpeg.exe to bundle, and the issues-only feedback token file (the build
# FAILS without it rather than shipping a broken Report a Bug).
.\scripts\build_release.ps1 -TokenFile S:\token.txt -FfmpegDir C:\path\to\ffmpeg\bin
```

The PyInstaller spec is onedir on purpose: instant startup (no per-launch temp extraction), and one built folder feeds both the portable zip and the installer. It pulls the entire `quill` package -- code and data -- and excludes only the heavy speech/science stacks, which are fetched on demand.

## Documentation

- [User Guide](docs/userguide.md)
- [Release Notes](docs/release-notes-1.0.md)
- [Changelog](CHANGELOG.md)
- [Product Requirements](docs/prd.md)

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
