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

- [User Guide](userguide.md)
- [Release Notes 2.2](release-notes-2.2.md) -- the current build
- [Release Notes 1.0](release-notes-1.0.md) -- the first release
- [Changelog](CHANGELOG.md)
- [Product Requirements](prd.md)

---

## Relocated from the public QUILL docs (1.0.0 consolidation)

> **Not part of the public QUILL 1.0 product.** The standalone Audio Studio app
> is one of the five companion apps gated behind `RELEASED_APPS`
> (`quill/core/app_launcher.py`) for QUILL 1.0.0; its QuillVille launcher is
> hidden in a public build.
>
> The *editor-embedded* audio tooling is **not** gated and stays fully documented
> in QUILL's public user guide and PRD: **Tools > Speech > Audiobook & Batch
> Speech...** (`tools.speech_batch_export`), the Chapter Workbench it opens,
> **Export to Translated Speech Audio**, and the Universal Audio Converter
> dialog. Only the standalone app's own material was relocated here, during the
> 1.0.0 documentation consolidation. Nothing was deleted.
>
> Sign-off note: the embedded wizard's menu label was changed from
> "Audio Studio..." to "Audiobook & Batch Speech..." precisely to remove the name
> clash with this app (`docs/planning/signoff/QUILL-1.0.0-SIGNOFF.md`, section G).

### From `QUILL-PRD.md` 35.1 -- the Audio Studio family entry

_The PRD's family inventory now lists only the publicly released apps and points
here for the gated ones._

- **Audio Studio** (`quill/apps/studio.py`) -- the audiobook/narration studio.
  Reverse-vendored from the former standalone `quill-audio-studio` repo
  (Option D); targets a clean **1.0.0**. Held back from the public QUILL 1.0.0
  release via `RELEASED_APPS`.

The consolidation roadmap that stays in the PRD (`35.5`) carries this app's two
remaining steps: the Audio Studio reverse-vendor (`quill/apps/studio.py`, Phase A
landed under the GATE suite, then the thin-wrapper cutover and closure deletion),
and the packaging toolkit -- one parameterized spec/installer/build script
consumed by QUILL, Radio, Cast, and Audio Studio, retiring the four forks. `35.3`
also reserves SQLite for app-private indexes such as a future Audio Studio
library index.

### From `QUILL-PRD.md` 5.25e -- what the standalone shell wires up

_The PRD keeps the shared-module half of this bullet (the embedded Chapter
Workbench uses the same code); the standalone-only half is below._

`open_book_in_workbench` and `ChapterWorkbenchDialog` thread optional host
callbacks -- `on_player_ready(player, path)`, `on_finished(path)`,
`on_volume(path, pct)`, `on_mute(path, muted)`, `on_closed(path, position_ms,
chapter)` -- down to `PlayerPanel`. Embedded QUILL passes none (fully backward
compatible -- its single call site is unchanged), and the **standalone QUILL-AS
Studio shell** wires them to route media keys (Play/Pause, Stop, Next/Previous
chapter via `RegisterHotKey`), persist per-book volume/mute, stamp Recently
Played history, and auto-advance the play queue on finish-then-close. The wx-free
stores in `quill/core/audio_studio/` -- `library.py` (book entries + user
folders), `history.py` (Recently Played), `play_queue.py` (ordered queue +
`next_entry`), `sleep_timer.py` (`SleepTimerSetting` + `SleepTimerWatcher`) --
and the shared UI (`library_tree.py`, `play_queue_dialog.py`,
`sleep_timer_dialog.py`) are all vendored into QUILL-AS.

### From `QUILL-PRD.md` 5.89e -- the standalone-apps non-goal

_The PRD's standalone companion-app section is now Quill Radio only._

**Non-goals (v1).** No single-instance enforcement; no Audio Studio standalone
app yet -- the phased plan, including those, lives in `docs/planning/apps.md`.

### From `docs/user guide/userguide.md` -- the shared-announcement mentions

_The public user guide's announcement and earcon sections now name only the
publicly released apps._

- **The four announcement channels.** The same announcement service carries
  speech, braille, sound and status in Audio Studio as well as in QUILL, Quill
  Radio and Quill Weather, so an announcement behaves the same wherever you are.
- **Sound cues in the companion apps.** The accessibility setting that turns on
  earcons in the companion apps covers Audio Studio along with the rest.

## License

MIT, same as QUILL.
