# QUILL Audio Studio

Accessible, screen-reader-first audio production as a standalone Windows app, from the QUILL project.

QUILL Audio Studio is not a fork. The whole application lives in the [quill](https://github.com/Community-Access/quill) package (`quill.apps.studio`) and runs the exact same audio feature code QUILL itself uses: the same waveform editing, chapter markers, TTS narration, loudness checks, and publishing. This folder holds only what exists because QUILL is not in the picture: the product wrapper (entry point), the installer, and this app's own documentation. Everything shared stays upstream, so QUILL Audio Studio tracks QUILL automatically.

## What it does

- Edit spoken-word audio (audiobooks, podcasts, narration) keyboard-first, with a screen reader in mind at every step.
- Add and navigate chapter markers; export chaptered MP3/M4B audiobooks.
- Narrate text with neural text-to-speech (Kokoro / Piper), fetched on demand.
- Run an ACX-style loudness/quality check so an audiobook meets the retailer's spec before you submit it.
- Convert and export common formats via bundled FFmpeg (MP3, M4A/M4B, OGG, Opus, FLAC), including a batch converter with presets, advanced DSP, and audio import from a link.
- Transcribe audio or video to `.srt` / `.vtt` captions offline.
- Speak, braille, cue and display every announcement through the shared announcement service, with an arrow-navigable status bar (F6) that keeps a long run reviewable from the tray.
- Live in the system tray; share settings and voices with QUILL, Quill Radio, and QUILL Cast (one data store in `%APPDATA%\Quill`).
- Check for its own updates from Help > Check for Updates.

## Install

Audio Studio is built at 2.2.0 -- the shared QuillVille family version -- but has **not been publicly released yet**, so there is no download page for it. When it ships it will be published, like every QuillVille app, from the [quill](https://github.com/Community-Access/quill) Releases page, where each app recognizes its own downloads:

- **`QUILL-Audio-Studio-Setup-Shared-<version>.exe`** -- the system install: its own directory, Start Menu entry, uninstaller. Choose per-user or per-machine at install time. Installs the shared QuillVille Runtime if it is not already present, plus the app. Uses the shared Quill data in your Windows profile.
- **`QUILL-Audio-Studio-Lite-Setup-<version>.exe`** -- the thin installer: downloads the shared runtime only if it is missing, then installs the app.
- **`QUILL-Audio-Studio-Portable-Lean-<version>.zip`** -- extract anywhere (a USB stick included) and run `QuillAudioStudio\QuillAudioStudio.exe`. Fully self-contained: a genuine, unmodified CPython plus the offline speech engines, ffmpeg, and mpv. The bundled `data` folder keeps your settings inside the app folder, so the whole thing travels -- exactly like QUILL portable.
- **`QUILL-Audio-Studio-Companion-<version>.zip`** -- the feather-light edition (a few MB): the app and its docs only, running on the shared QuillVille Runtime, which it offers to download once on first launch.

FFmpeg is bundled. The neural TTS engine and any transcription engine are fetched on demand through QUILL's shared, SHA-verified component system (the assets-v1 mirrors); to ship a fully-offline Studio with TTS bundled, see the note in `quill-audio-studio.spec`.

Help > Check for Updates knows which flavor you run, resolves Audio Studio's own artifact from the shared releases page, and can install it and restart the app for you in one step.

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
# One command, both artifacts (staged portable folder -> portable zip + installer).
# Needs: the quill package in the Python env, Inno Setup 6.3+, an ffmpeg.exe to
# bundle, and the issues-only feedback token file (the build FAILS without it
# rather than shipping a broken Report a Bug).
.\scripts\build_release.ps1 -TokenFile S:\token.txt -FfmpegDir C:\path\to\ffmpeg\bin
```

The portable bundle is a genuine, unmodified CPython embeddable runtime with a small native launcher -- not a PyInstaller onedir, and not a renamed `pythonw.exe`, the pattern antivirus tools used to flag. One staged folder feeds both the portable zip and the installer. It pulls the entire `quill` package -- code and data -- and excludes the heavy speech/science stacks, which are fetched on demand.

## Documentation

- [User Guide](docs/userguide.md)
- [Release Notes 2.2](docs/release-notes-2.2.md) -- the current build
- [Release Notes 1.0](docs/release-notes-1.0.md) -- the first release
- [Changelog](CHANGELOG.md)
- [Product Requirements](docs/prd.md)

## License

MIT, same as QUILL. See [LICENSE](LICENSE).
