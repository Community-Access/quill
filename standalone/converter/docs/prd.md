# Quill Converter -- Product Requirements

Version 1.0

## 1. Product statement

Quill Converter is the Universal Audio Converter shipped as its own small
Windows app, for people who need to change an audio file's format and do not
want to load a writing environment -- or hand their file to a website -- to do
it. It is screen-reader-first, keyboard-complete, offline, and deliberately
single-purpose.

## 2. Architecture requirement: not a fork

- R-1. All feature code lives in the upstream `quill` package: the wx-free
  engine (`quill.core.audio.convert`, `.presets`, `.dsp`, `.url_import`), the
  shared dialog and orchestration (`quill.ui.audio_studio.convert_audio_dialog`),
  and the app frame (`quill.apps.converter`). This folder is the product
  wrapper only -- entry point, tile icon, build and installer plumbing.
- R-2. **One converter, surfaced several ways.** The standalone app, QUILL's
  Audio Studio menu item, the Explorer verb, and the headless `quill convert`
  command are all doors onto the same engine and the same dialog. A behaviour
  fixed once is fixed everywhere; no surface reimplements a feature.
- R-3. Data is shared, not copied: settings, keymap, unlock state and logs live
  in the same store QUILL uses, so a preference set in one app holds in the
  others.
- R-4. The app frame is hosted on the shared `AppShellFrame`, which supplies
  announcements, the status bar, the accessible modal-dialog path, the tray,
  the QuillVille menu, and the per-app update check. The app supplies only its
  own menus, its own panel, and a background-task runner that meets the shared
  progress contract.

## 3. Users

- A screen reader user with a file in the wrong format and a player that will
  not take it -- the primary case.
- A podcaster or audiobook producer batching a folder into a delivery format at
  a loudness target.
- Someone converting a video's audio track out to MP3.
- A power user or script author who wants the same conversion without a window
  (`quill convert`).

## 4. Functional surface

In scope for 1.0:

- **Queue.** A mixed file and folder queue. Folders are scanned for known audio
  and video extensions and the output mirrors the source tree. Duplicates are
  ignored. Delete or a Remove button takes a row out.
- **Getting files in.** Add Files (multi-select picker), Add Folder, positional
  command-line paths, the Windows Explorer **Convert with Quill** verb (off by
  default, opt-in per user), and Convert from URL. Drag and drop is
  out of scope; every route must be keyboard-reachable.
- **Output.** MP3, M4A, M4B, Opus, OGG, FLAC, WAV, AAC, AIFF, ALAC, WMA, CAF --
  filtered at startup to the formats the resolved FFmpeg can genuinely encode.
  WAV, AIFF and CAF are always offered; with no FFmpeg at all, WAV only.
- **Presets.** Ten built-in one-click recipes, each announced with a
  plain-language description of what it is good for. The chosen output format
  always overrides the preset's own.
- **Destination and conflicts.** Default destination is a `Converted` folder
  beside the source. The main window never overwrites (auto-numbering instead);
  the Advanced dialog exposes Rename / Skip / Overwrite.
- **Advanced.** The full Convert Audio dialog: include-sub-folders, conflict
  policy, and a revealable panel for bit rate, sample rate, channels, bit depth,
  loudness normalization (audiobook and podcast targets), gain, tempo, fade in,
  fade out, high-pass, silence trim, compressor and leveler. Every control
  defaults to a neutral "leave the preset alone" value.
- **Convert from URL.** Prompt, one-time consent with a rights notice, on-demand
  yt-dlp install, background download with progress, then the Convert Audio
  dialog seeded with the downloaded file.
- **Running a batch.** Off the UI thread, multi-worker, with progress reported
  through the shared task callback so the status bar, the tray tooltip and the
  spoken milestones update together. The run ends with a summary that names
  failures rather than reporting a blanket success.
- **Tray.** Tray icon with Show / Open / Exit, minimize-to-tray on Ctrl+W, and a
  system-wide show/hide chord (Ctrl+Alt+Shift+C) claimed best-effort.
- **Family.** The shared QuillVille menu, listing the released sibling apps.
- **Help.** Check for Updates against this app's own release assets, and About.

Out of scope, by decision:

- Video output of any kind. Video files are inputs only, and only their audio
  track is taken.
- Tagging, cover art, chapter editing, splitting, joining, and recording. Those
  are Audio Studio and QUILL Cast territory.
- Saving user-defined presets in 1.0. Advanced settings apply to the run in
  front of you.
- Transcription, translation, and text-to-speech. Different products.
- Any cloud or upload path. Conversion is local, always.

## 5. Accessibility contract

- A-1. Focus lands on the **Files to convert** list at launch. A bare-frame
  focus dead zone is a defect.
- A-2. Every interactive control carries an accessible name, set explicitly
  where the visible label is a separate static text. Labels are created before
  the control they describe, so reading order matches tab order.
- A-3. Every action announces its outcome through the shared announcement
  service -- speech through the user's screen reader plus the braille display --
  and the status bar always carries the same text as the visual floor. A silent
  state change is a defect.
- A-4. Nothing is conveyed by colour alone; queue rows and progress are words.
- A-5. Full keyboard operation. Delete removes a queue row; access keys reach
  every button and field; the tray is reachable from the keyboard.
- A-6. All modal dialogs go through the shared accessible modal path with a real
  affirmative/cancel pair and Escape that works. The Convert Audio dialog's
  affirmative is labelled **Convert**.
- A-7. A progressive reveal (the Advanced panel) moves focus to the first
  revealed control, so the change is announced rather than being a silent
  resize.
- A-8. Long work never owns the window: batches run off the UI thread and stay
  reviewable from the tray tooltip while minimized.

## 6. Privacy and network requirements

- N-1. Conversion is entirely local. Nothing is uploaded, ever.
- N-2. Exactly two outbound paths exist: **Check for Updates** (this app's own
  releases) and **Convert from URL**. Both are user-initiated.
- N-3. yt-dlp is never bundled. It is installed only after an explicit one-time
  consent that states what it does, roughly how large it is, where it comes
  from, and that the user must only download what they have the right to use.
  No account or credential of the user's is sent to the site.
- N-4. Convert from URL is refused in Safe Mode.

## 7. Packaging requirements

- P-1. The released launcher is the native QuillVille launcher, spawning
  `pythonw.exe -m quill.apps.converter`, built by the shared portable builder
  with the app's own tile icon.
- P-2. FFmpeg ships with the app; nothing is downloaded at install time.
- P-3. Portable mode: a `data` folder beside the program makes settings, logs
  and keymap travel with the bundle instead of touching the host machine.
- P-4. Uninstalling never deletes the shared `%APPDATA%\Quill` store -- another
  family app may still be using it.
- P-5. Single instance, via the shared IPC slot. Launching a second copy does
  not open a second window.
- P-6. The update check resolves this app's own release asset, so every
  QuillVille app updates independently of the others.

## 8. Non-goals

macOS and Linux standalone builds (the tray pattern this app leans on does not
exist there in the same form), background or automatic conversion, watched
folders, telemetry of any kind, and any feature that would require uploading a
user's audio anywhere.

See `CHANGELOG.md` for the versioned history and `docs/userguide.md` for the
user-facing documentation.
