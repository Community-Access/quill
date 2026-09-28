# Quill Converter -- Product Requirements

Version 1.0.0 -- status: released September 28, 2026 (first public release)

## 1. Product statement

Quill Converter is the Universal Converter shipped as its own small Windows app,
for people who need to change an audio or video file's format and do not want
to load a writing environment -- or hand their file to a website -- to do it. It
converts sound to sound, video to sound and video to video, can improve the
sound on the way through, and lets the listener hear the result before
committing. It is screen-reader-first, keyboard-complete, offline, and
deliberately focused on conversion.

## 2. Architecture requirement: not a fork

- R-1. All feature code lives in the upstream `quill` package: the wx-free
  engine (`quill.core.audio.convert`, `.formats`, `.presets`, `.dsp`,
  `.effect_recipes`, `.assemble`, `.media_probe`, `.cover_art`,
  `.ffmpeg_errors`, `.url_import`, `.chapter_plan`) and settings
  (`quill.core.converter_settings`); the shared choice tables and URL
  orchestration (`quill.ui.audio_studio.convert_audio_dialog`); the Audio
  Studio's Chapter Workbench (`quill.ui.audio_studio.chapter_workbench`),
  reused rather than rebuilt; the app's own windows
  (`quill.ui.converter_dialogs`); and the app itself in five modules --
  `quill.apps.converter` (the window), `quill.apps.converter_menu` (the menu
  bar and Help menu), `quill.apps.converter_actions` (what the commands do),
  `quill.apps.converter_chapters` (Join, Split by Chapters and the Chapter
  Workbench) and `quill.apps.converter_advanced` (the Advanced section). This
  folder is the product wrapper only -- launcher, tile icon, build
  and installer plumbing, and documents.
- R-2. **One converter, surfaced several ways.** The standalone app, QUILL's
  Audio Studio menu item, the Explorer verbs, and the headless `quill convert`
  command are all doors onto the same engine. A behaviour fixed once is fixed
  everywhere; no surface reimplements a feature.
- R-3. Data is shared where it should be: settings, keymap and logs live in the
  family's data folder. The Converter's own remembered choices are one file,
  `converter.json`, written atomically and read forgivingly (a damaged value
  falls back to its default rather than stopping the app from opening).
- R-4. The app frame is hosted on the shared `AppShellFrame`, which supplies
  announcements, the status bar, the accessible modal-dialog path, the tray,
  the QuillVille menu, F1 help, and the per-app update check.
- R-5. Every long job -- a batch, a Join, a preview render, File Properties'
  probe -- runs off the UI thread and reports back through `wx.CallAfter`.

## 3. Users

- A screen reader user with a file in the wrong format and a player that will
  not take it -- the primary case.
- A podcaster or audiobook producer batching a folder into a delivery format at
  a loudness target, joining chapter files into an M4B, splitting one, or
  giving a long recording chapters it never had.
- Someone taking the sound out of a video, or making a video smaller or playable
  on another device, without losing a described-audio track.
- A listener who wants a recording clearer, louder or quieter at night, and
  knows the problem but not the name of the effect that fixes it.
- A power user or script author who wants the same conversion without a window
  (`quill convert`).

## 4. Functional surface

In scope for 1.0.0:

- **Queue.** A mixed file and folder queue. Folders are scanned for known audio
  and video extensions, sub-folders included, and the output mirrors the source
  tree. Duplicates are ignored. Delete, Remove, Remove from Queue and Clear
  Queue take rows out; Alt+Up and Alt+Down reorder; File Properties describes
  the highlighted file in plain words (length, size, container, bit rate, tags,
  each track, cover art, chapters).
- **Getting files in.** Add Files, Add Folder, Paste Files (files copied in
  File Explorer; a text box keeps its own paste), drag and drop, positional
  command-line paths, the installer's **Convert with Quill Converter** Explorer
  verb, QUILL's own **Convert with Quill** verb, and Convert from URL. A second
  launch hands its files to the running window, so a multi-file Explorer
  selection lands in one queue.
- **Inputs.** 82 extensions: 52 sound (everyday, lossless and archival, film and
  broadcast, telephony, older and specialist, tracker music) and 30 video.
  `.ts` is read but not registered for the Explorer verb (TypeScript clash).
- **Outputs.** 34 formats -- 25 sound and 9 video (MP4 H.264, MP4 H.265, MKV,
  WebM VP9, MOV, AVI Xvid, WMV, MPEG-2, Ogg Theora) -- each with a
  plain-language label, and filtered at startup to what the resolved FFmpeg can
  genuinely encode.
- **Format constraints.** A requested sample rate a format cannot take is moved
  to the nearest it accepts (AC-3, E-AC-3, MP2, Opus, WebM audio, Speex, AMR);
  AMR is forced to mono; lossless formats ignore a bit rate; AIFF and AU are
  written big-endian; 32-bit WAV, Wave64 and CAF are real float.
- **Video.** Video to a sound format keeps the sound; video to a video format
  keeps the picture. Five video presets named for the result (Same quality;
  up to 1080p; up to 720p; up to 480p; Change the container only). MP4, MKV,
  MOV and WebM keep every audio track; MKV keeps subtitles. A sound file queued
  for a video format is skipped with a spoken reason. Video encodes run one at
  a time.
- **Presets.** Ten sound presets and five video presets, each announced with a
  description of what it is good for. The chosen output format always overrides
  the preset's own. The last sound and video preset are remembered separately.
- **Effects.** Named recipes on the main window, each named for the problem it
  solves, plus Custom. The Custom Effects dialog exposes every switch (rumble,
  hum, noise, long silences, de-ess, voice clarity, bass, treble, dialogue
  boost, compressor, speech leveling, night mode leveler, peak limiter), a
  loudness target (-16, -20, -14, -23 LUFS), gain, speed, fades, and keep from /
  keep until. Effects apply to the sound of video conversions; Change the
  container only skips them and says so.
- **Preview.** Fifteen seconds of the highlighted or first file, rendered
  through the chosen format and effects and decoded back, starting a quarter of
  the way in (at most 30 seconds); Preview Original plays the same window
  untouched. Pressing again stops.
- **Chapters.** A headline feature: chapter marks are content, not metadata
  that may or may not survive. A Chapter marks choice on the main window
  (`quill.core.audio.chapter_plan.CHAPTER_SOURCES`) says where each file's
  chapters come from: keep its own (default); a chapter list beside it
  (`name.chapters.txt` of `0:00 Title` lines, `name.cue`,
  `name.chapters.json` Podcasting 2.0, `name.labels.txt` Audacity labels, or
  `name.txt` when it parses as a chapter list); found at pauses (two seconds
  of quiet, chapters at least 20 seconds); every 5, 10, 15, 30 or 60 minutes
  (Part 1, Part 2...; a last piece under a minute joins the one before); or
  removed. A missing list or a failed scan falls back to the file's own
  chapters.
- **Where chapters land.** FFmpeg writes them natively into MP3 (ID3 CHAP and
  CTOC), the MP4 family (M4A, M4B, ALAC, M4R, MP4, MOV), Matroska and WebM,
  Opus, and WMA/WMV. Ogg Vorbis, FLAC, Speex and Ogg video get `CHAPTERnnn`
  comments written with mutagen. Every other format gets a `.cue` sheet of
  the same name beside the output. Nothing is silently lost. Keep from / keep until clips the chapters to the kept
  window and shifts them to zero.
- **Chapter Workbench.** Queue > Chapter Workbench (and a main-window button)
  opens the highlighted MP3, M4B or M4A in the Audio Studio's Chapter
  Workbench: libmpv playback with exact seeking, rename, split at the
  playhead, set start to the playhead, merge, find at silences, import and
  export chapter lists (Audacity labels, CUE, timestamps, Podcasting 2.0 JSON,
  CSV), the five Book details fields and All tags... (the Tag Editor), Save
  (MP3 in place, tags only; M4B or M4A in place when only tags changed, Save
  As, lossless, when chapters changed) and
  split into files. Other formats are pointed at the chapter-list route or a
  conversion to M4B or MP3 first. Preview ignores chapters.
- **Edit Tags** (Queue > Edit Tags..., Ctrl+T). Audio Studio's Tag Editor,
  shared: every modelled tag (26 fields over four pages) plus a cover-art
  page, for
  MP3, M4A, M4B and MP4, written in place without re-encoding and without
  touching chapter frames. Other formats are refused in words: an ID3 block
  written onto FLAC or WAV would damage it.
- **Join into One File.** The queue, in order, into one sound file, with a
  chapter per source in every format that holds chapters (MP3 included), and
  as comments or a `.cue` sheet for the rest; sources of different shapes are
  normalized first so they join cleanly.
- **Split by Chapters.** One file per chapter, into a folder named after the
  source, numbered, titled and tagged. It follows the Chapter marks choice, so it
  can cut every N minutes, at pauses, or exactly where a chapter list says.
- **Destination and conflicts.** Default destination is a `Converted` folder
  beside the first queued item. The default never overwrites (auto-numbering);
  Advanced Options offers number / skip / replace.
- **Advanced Options.** View > Advanced Options, a check item, shows or hides
  an Advanced section in the main window (the Windows way to show more of a
  window, rather than a second window with its own Convert button): bit rate
  (size and quality), sample rate, channels, bit depth, the conflict policy, Exact
  OptiLab broadcast polish where the adapter is present, and "Look in
  subfolders too". Each starts on its neutral choice, shapes the same Convert
  as the rest of the page, and is remembered, as is whether the section is
  shown.
- **Convert from URL.** Prompt, then read the link off the UI thread without
  downloading (`url_collections.read_link`: video, playlist with count, or
  channel with the sections that exist). A video: background download through
  the bundled yt-dlp and deno (the shared URL orchestration). A playlist or
  channel: the Download a Playlist or Channel window (scope, how many, section,
  published within, skip already downloaded), then one Converter job with
  progress, Stop and a report; files numbered in order, tagged album + track,
  a per-link download archive, pauses on long runs. Everything joins the main
  window's queue, converted by the same Convert as everything else. Refused in
  Safe Mode.
- **Running a batch.** Off the UI thread, multi-worker for sound and one at a
  time for video. Convert becomes Stop; Stop kills the encode in progress
  (its temp file is removed), starts nothing after it, and the report lists
  every stopped file as skipped. A Join stops mid-file too and saves nothing
  (it writes to a temp folder first). H.264 and H.265 run on the graphics
  chip's encoder when one works (`quill/core/audio/video_accel.py`: probed once
  per session, a failed real encode falls back to the processor and disables
  the card for the session). Progress is measured
  inside each file from FFmpeg's `-progress` output
  (`quill/core/audio/ffmpeg_live.py`), combined across the batch by
  `batch_progress.py`, spoken every 25 percent and mirrored, with an estimate
  of the time left, in the status bar and tray tooltip at most once a second
  ("Converting Book.m4b: 42 percent, about 3 minutes left"; "Converted 3 of
  10, 47 percent overall"). A progress bar ("Progress:", a `wx.Gauge` named
  "Conversion progress") under the action buttons shows the same fraction; it
  is not in the Tab order, because the status bar carries the same words.
- **Results.** A summary that names failures; a Conversion Report with the
  settings, destination, time taken and a plain-language reason per failure
  (then FFmpeg's own last line), with Copy All; Open Output Folder and Open
  Output Folder When Done. Cover art is carried into MP3, M4A/M4B/M4R, FLAC and
  Ogg/Opus/Speex copies where FFmpeg drops it.
- **Remembered choices.** Format, presets, effect, custom effects, keep from /
  keep until, the Chapter marks choice, the Advanced Options (and whether they are
  shown) and output folder persist between runs.
- **Menus.** File, Queue, View, Convert, QuillVille, Help and Window.
- **Tray.** Minimize to tray (Ctrl+W), the shared tray menu, and a system-wide
  show/hide chord (Ctrl+Alt+Shift+C) claimed best-effort.
- **Family.** The shared QuillVille menu lists the released siblings, and the
  siblings list Quill Converter.
- **Help.** The family Help menu, on Quill Radio's and QUILL Lite's keys: F1
  help for the window and control, User Guide, Release Notes, Changelog,
  Product Requirements, Keyboard Shortcuts (a read-only list of every key), Get
  Help from Support, Get FFmpeg (repair), Check for Updates, and About.
- **Support.** Email only, to support@community-access.org, through Get Help
  from Support (Ctrl+Alt+F2), which composes the message in the user's own mail
  program. No GitHub path and no token.

Out of scope, by decision:

- Recording. That is Audio Studio and QUILL Cast territory. (Chapter, tag and
  cover-art editing are in scope only through reused Audio Studio surfaces --
  the Chapter Workbench and the Tag Editor; the Converter builds no editor of
  its own. The rest of Audio Studio -- the audiobook-from-a-folder journey, the
  ACX check, captions, documents to speech, publishing -- is for later.)
- Saving user-defined named presets in 1.0. Custom Effects is one remembered
  custom recipe.
- Video effects (picture filters, cropping, rotation) and subtitle burn-in.
- Joining video files.
- Converting copy-protected (DRM) files.
- Transcription, translation and text-to-speech. Different products.
- Any cloud or upload path. Conversion is local, always.

## 5. Accessibility contract

- A-1. Focus lands on the **Files to convert** list at launch. A bare-frame
  focus dead zone is a defect.
- A-2. Every interactive control carries an accessible name, set explicitly
  where the visible label is a separate static text, and an access key unique
  within its window (GATE-14). OK, Cancel and Close carry none.
- A-3. Every action announces its outcome through the shared announcement
  service, and the status bar carries the same text as the visual floor. A
  silent state change is a defect; announcing what the screen reader already
  says (GATE-13) is too.
- A-4. Nothing is conveyed by colour alone; queue rows, progress and failures
  are words, and failures are explained in plain language.
- A-5. Full keyboard operation. Every enabled menu item shows its key, no key is
  claimed twice, and Keyboard Shortcuts lists them all in one read-only window.
- A-6. All modal dialogs go through the shared accessible modal path with a real
  affirmative/cancel pair and Escape that works.
- A-7. A progressive reveal (the Advanced section, shown from View > Advanced
  Options) moves focus to the first revealed control.
- A-8. Long work never owns the window, and stays reviewable from the tray
  tooltip while minimized.
- A-9. Every window answers F1 with an authored purpose and the focused
  control's own help (GATE-CONVERTER-HELP): the main window (the Chapters
  choice, the Advanced section and the progress bar included), Chapter
  Workbench, Tag Editor, Convert from URL, Custom Effects, File Properties,
  Conversion Report and Keyboard Shortcuts.
- A-10. Reports and descriptions are shown in a read-only multi-line text box,
  the one surface every screen reader reviews line by line without a special
  mode.

## 6. Privacy and network requirements

- N-1. Conversion is entirely local. Nothing is uploaded, ever.
- N-2. Exactly three outbound paths exist, all user-initiated: **Check for
  Updates** (this app's own releases), **Convert from URL**, and **Get FFmpeg**
  (repair, when the bundled copy is missing).
- N-3. yt-dlp is bundled; Convert from URL downloads only the address the user
  pasted, sends no account or credential to the site, and reminds the user to
  download only what they have the right to use.
- N-4. Convert from URL is refused in Safe Mode.
- N-5. Support messages leave only through the user's own mail program, and
  only when the user sends them.

## 7. Packaging requirements

- P-1. Two artifacts: `Quill-Converter-Setup-Shared-1.0.0.exe` (Inno Setup 7;
  installs the shared QuillVille runtime if absent, then the native launcher,
  docs and uninstaller) and `Quill-Converter-Portable-1.0.0.zip`. Both are
  built by `standalone/converter/scripts/build_release.ps1`.
- P-2. Nothing downloads at install time or on first use: FFmpeg and ffprobe
  (pinned, SHA-256-verified), libmpv (the Chapter Workbench's player), yt-dlp,
  mutagen and, when a C++ toolchain is
  available at build time, the OptiLab Core adapter ship inside both artifacts.
- P-3. Portable mode: the `data` folder beside the program holds settings, logs
  and `converter.json`, so nothing touches the host machine.
- P-4. The installer's "Convert with Quill Converter" Explorer checkbox (a
  native checkbox, not an Inno `[Tasks]` entry) is checked by default, registers per user (HKCU) for every extension in
  `quill.core.shell_verbs.MEDIA_EXTENSIONS`, and is removed on uninstall. The
  registry block is generated by `scripts/build_converter_verb_iss.py`.
- P-5. Uninstalling never deletes the shared data folder -- another family app
  may still be using it.
- P-6. Single instance, via the shared IPC slot. A second launch hands its paths
  to the running window and exits.
- P-7. The update check resolves this app's own release asset and offers the
  matching download, installer or portable.
- P-8. No GitHub token is generated or embedded in any artifact.

## 8. Non-goals

macOS and Linux standalone builds (the tray pattern this app leans on does not
exist there in the same form), watched folders, telemetry of any kind, and any
feature that would require uploading a user's media anywhere.

See `docs/CHANGELOG.md` for the versioned history and `docs/userguide.md` for
the user-facing documentation.
