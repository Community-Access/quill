# Quill Converter Changelog

All notable changes to Quill Converter are recorded here, newest first. The
release notes (`release-notes-1.0.md`) tell the same story as a narrative; this
file is the itemized list.

Quill Converter runs the same conversion code as QUILL from the shared `quill`
package -- the app in `quill/apps/converter.py`, `converter_menu.py`,
`converter_actions.py`, `converter_chapters.py` and `converter_advanced.py`,
its windows in `quill/ui/converter_dialogs.py`, and the
engine under `quill/core/audio/` -- so a fix to the engine lands in QUILL's
Audio Studio at the same time. The `standalone/converter` folder carries only
the launcher, installer, icon and these documents.

## 1.0.0 -- 2026-09-28

The first public release. The app was first built in July 2026 as an audio
converter; that build was never published as an installer, and everything it
had is included here.

### 1.0 in brief

- **Two downloads.** `Quill-Converter-Setup-Shared-1.0.0.exe` (the installer,
  Inno Setup 7, installs the shared QuillVille runtime if it is absent) and
  `Quill-Converter-Portable-1.0.0.zip` (unpack anywhere; settings stay in its
  own `data` folder).
- **Nothing downloads on first use.** FFmpeg and ffprobe, libmpv, yt-dlp,
  mutagen and, when built, the OptiLab Core adapter are inside both downloads.
- **Sound and video.** 25 sound formats and 9 video formats out, 82 file types
  in.
- **Effects you can hear first.** Named effect recipes, Custom Effects, and a
  fifteen-second Preview beside Hear Original.
- **Chapters through every conversion.** Keep them, write your own beside the
  file, find them at pauses or every few minutes, or remove them; they land
  inside every format that holds them, and in a `.cue` sheet beside the rest.
  The Chapter Workbench edits them at the playhead.
- **Join and split.** Join into One File with a chapter per source; Split by
  Chapters, cutting wherever the Chapter marks choice says.
- **Advanced Options in the main window**, shown and hidden from the View menu.
- **Right-click to convert** from File Explorer, many files at once.

### Formats

- 34 output formats: 25 sound (MP3, M4A, M4B, Opus, Ogg Vorbis, FLAC, WAV, AAC,
  AIFF, Apple Lossless, WMA, CAF, AC-3, E-AC-3, MP2, WavPack, TTA, MKA, WebM
  audio, M4R, Speex, AMR narrowband, AMR wideband, AU, Wave64) and 9 video (MP4
  H.264, MP4 H.265/HEVC, MKV, WebM VP9, MOV, AVI Xvid, WMV, MPEG-2, Ogg
  Theora).
- Every format is labeled with what it is for, for example "M4B audiobook --
  remembers your place in book players".
- Reads 82 file types: 52 sound (everyday, lossless and archival, film and
  broadcast, phone and telephony, older and specialist, and tracker music) and
  30 video.
- The format list is still filtered to what the bundled FFmpeg can actually
  write, so a batch never fails for a missing encoder.
- Format constraints are handled instead of failing: a format that only
  accepts certain sample rates (AC-3, E-AC-3, MP2, Opus, WebM audio, Speex,
  AMR) gets the nearest one it accepts; AMR is forced to mono; lossless formats
  ignore a bit rate.
- The format catalogue moved to `quill/core/audio/formats.py`, one table per
  question.

### Video

- Converting a video to a sound format keeps its sound; to a video format keeps
  it a video.
- Video presets named for the result: Same quality (recommended), Phones and
  the web up to 1080p, Smaller file up to 720p, Smallest file up to 480p, and
  Change the container only (fastest, copies the streams; effects cannot
  apply, and you are told so).
- MP4, MKV, MOV and WebM keep every audio track, such as a described-audio
  track or a second language. MKV keeps subtitle tracks.
- A sound file queued for a video format is skipped, and the summary says why.
- Video files are encoded one at a time, since each encoder already uses every
  core.
- The sound format and the video format each remember their own last preset.

### Effects and preview

- A new Effects choice on the main window with named recipes: No effects, Clean
  up speech, Podcast ready, Audiobook ACX ready, Clearer voice for listening,
  Louder dialogue for films and TV, Night listening, Music streaming loudness,
  Broadcast standard EBU R128, Remove electrical hum, Reduce background noise,
  Remove long silences, Bass boost, and Custom.
- Custom Effects (Ctrl+E): every switch on one page -- rumble, hum, noise,
  remove long silences, de-ess, voice clarity, bass, treble, dialogue boost,
  compress, speech leveling, night mode leveler, peak limiter -- plus a
  loudness target (-16 podcast, -20 ACX, -14 music, -23 EBU R128), gain,
  playback speed, fade in and out, and keep from / keep until. It opens seeded
  with the current recipe.
- New processing in the shared catalogue: hum removal, noise reduction,
  de-essing, voice clarity, bass and treble boost, dialogue boost, speech
  leveling, and music and broadcast loudness targets.
- Effects apply to the sound of video conversions too.
- Preview (Ctrl+P) plays fifteen seconds of the highlighted or first file
  exactly as it will sound after conversion -- encoded in the chosen format with
  the chosen effects, then decoded. Preview Original (Ctrl+Shift+P, the Hear
  Original button) plays the same fifteen seconds untouched. Both start a
  quarter of the way in, at most 30 seconds, and pressing again stops.

### Chapters

- A new Chapter marks choice on the main window (Alt+K) says where the converted
  files' chapters come from: Keep each file's own chapters (the default); Use
  the chapter list beside each file; Find chapters at the pauses (a pause of
  two seconds or more, chapters at least 20 seconds long); A chapter every 5,
  10, 15, 30 or 60 minutes (Part 1, Part 2...; a last piece under a minute
  joins the one before); or Remove all chapters. It is remembered.
- Chapter lists you write yourself, for any format: beside the source, with
  the same name, `name.chapters.txt` (lines such as `0:00 Welcome`,
  `1:30 Questions`, `1:02:05 Summary`), `name.cue`, `name.chapters.json`
  (Podcasting 2.0), `name.labels.txt` (Audacity labels), or `name.txt` when it
  parses as a chapter list (a transcript is ignored). A file with no list keeps
  its own chapters.
- Where chapters land: FFmpeg writes them inside MP3 (ID3 CHAP and CTOC), M4B,
  M4A, Apple Lossless, M4R, MP4, MOV, MKV, MKA, WebM, WebM audio, Opus and
  WMA/WMV. Ogg Vorbis, FLAC, Speex and Ogg video get CHAPTER001 /
  CHAPTER001NAME comments, written with mutagen. Every other format (WAV,
  AIFF, WavPack, AC-3, the AAC stream, MP2 and the rest) gets a `.cue` sheet
  with the same name beside the converted file.
- Keep from / Keep until trim the chapters to the kept part and shift them to
  start at zero.
- Chapter Workbench (Queue > Chapter Workbench..., Ctrl+H, or the Chapter
  Workbench button) opens the highlighted MP3, M4B or M4A in the Audio
  Studio's Chapter Workbench: a player, rename, split at the playhead, set a
  start to the playhead, merge, find chapters at silences, import and export
  chapter lists (Audacity labels, CUE, timestamps, Podcasting 2.0 JSON, CSV),
  the five Book details fields plus All tags... (the Tag Editor), Save (MP3 in
  place, tags only; an M4B or M4A in place when only tags changed, as a new
  file, lossless, when chapters did) and
  split into files. Other formats are told the chapter-list route, or to
  convert to M4B or MP3 first.
- libmpv, the mpv playback engine, is bundled in the installer and the
  portable zip as the Workbench's player, for exact seeking.
- Preview and Preview Original ignore chapters.

### Join and split

- Join into One File (Ctrl+J): the whole queue, in order, into one sound file,
  with one chapter per source, named from its title tag or a tidied file name
  ("01 - Intro" becomes "Intro"). The chapters go inside every format that
  holds them -- now including MP3 -- and into Ogg/FLAC comments or a `.cue`
  sheet for the rest. Files of different sample rates and channel counts join
  cleanly.
- Split by Chapters (Ctrl+Shift+S): one file per chapter, into a folder named
  after the source inside the output folder, named "01 - Chapter title" and
  tagged with the title and track number. It follows the Chapter marks choice: "A
  chapter every 30 minutes" cuts a long recording into 30-minute files, "Find
  chapters at the pauses" cuts at the pauses, and a chapter list beside the
  file cuts exactly where it says.

### Queue and reports

- **Edit Tags (Queue > Edit Tags..., Ctrl+T).** The Audio Studio's Tag
  Editor, shared into Quill Converter: every tag of an MP3, M4A, M4B or MP4 over
  five pages, and the cover art, written into the file without touching the
  sound or the chapters. Other formats are refused in words rather than risk
  damage.
- Paste files copied in File Explorer with Ctrl+V (a text box still pastes
  text), and drag and drop onto the queue.
- Reorder with Alt+Up and Alt+Down; Remove from Queue (Ctrl+Delete); Clear
  Queue (Ctrl+Shift+Delete).
- File Properties (Alt+Enter): length, size, container, bit rate, tags, each
  video, audio and subtitle track, cover art, and chapters, read by ffprobe.
- Convert (Ctrl+Enter or the Convert button) becomes Stop while running. Stop
  is immediate: the file being encoded is stopped too and its unfinished
  output removed (FFmpeg writes to a temp file that only a finished encode
  moves into place). Before this, a stop only took effect between files, and
  in a batch of sound files it never took effect at all, because every file
  had already been handed to a worker. The report lists stopped files as
  skipped. A Join still stops before its next source.
- Progress is counted inside each file from FFmpeg's own progress report, not
  only by files finished, so a one-file batch of a long audiobook or film is
  no longer silent until it ends. It is announced at 25, 50 and 75 percent;
  the status bar and tray tooltip update about once a second with the
  percentage and, once it can be estimated, the time left ("Converting
  Book.m4b: 42 percent, about 3 minutes left"; "Converted 3 of 10, 47 percent
  overall").
- A progress bar ("Progress:", named "Conversion progress") sits under the
  action buttons and fills with the same count. It is not in the Tab order; the
  status bar says the same in words.
- Convert from URL puts the downloaded file into the main window's queue,
  ready for Ctrl+Enter with the choices already on the window. With no Output
  folder set, its converted copy goes to Downloads\Converted rather than into
  the temporary folder the download sits in.
- Conversion Report (Ctrl+R) lists every file with the settings used, a
  plain-language reason for each failure, and any note on a converted file
  (where its chapters went, captions left out), with a Copy All button.
- Failures are explained in plain words -- no track of the needed kind, file
  not found, damaged file, access refused, drive full, tracks that cannot be
  copied into the container, settings the encoder refused, copy protection, an
  unreadable codec, no sound track -- followed by FFmpeg's own last line.
- Open Output Folder (Ctrl+Shift+F) and Open Output Folder When Done
  (Ctrl+Shift+W, a check item).
- Cover art is carried into the converted copy where FFmpeg drops it: MP3,
  M4A, M4B, M4R, FLAC, Ogg, Opus and Speex.
- Format, presets, effects, custom effects, keep from and keep until, the
  Chapter marks choice, the Advanced Options and the output folder are remembered
  between runs, in `converter.json` in the data folder.
- View > Advanced Options (Ctrl+Alt+V), a check item, shows or hides an
  Advanced section in the main window and moves focus to its first control;
  whether it is shown is remembered. It holds Bit rate (size and quality), Sample rate,
  Channels, Bit depth, If a file already exists (number the new one, skip or
  replace), Broadcast polish (OptiLab Core: Podcast Leveler, Stream Polish,
  Smooth Limiter; disabled when the build lacks it) and "Look in subfolders
  too" (on by default). Each starts on its neutral choice. This replaces the
  Advanced button and the Advanced Options command that opened the Audio
  Studio's Convert Audio dialog, a second window with its own queue and its
  own Convert button.
- Menus are now File, Queue, View, Convert, QuillVille, Help and Window, and
  every item shows its key.

### Help menu and support

- The Help menu matches Quill Radio's and QUILL Lite's: Help for This Window
  (F1), User Guide (Ctrl+F1), Release Notes (Shift+F1), Changelog
  (Ctrl+Shift+F1), Product Requirements (Alt+Shift+F1), Keyboard Shortcuts
  (Ctrl+Alt+K), Get Help from Support (Ctrl+Alt+F2), Get FFmpeg (Ctrl+Alt+F),
  Check for Updates (Ctrl+Alt+U) and About (Alt+F1).
- Keyboard Shortcuts is a read-only list of every key in the app.
- Get Help from Support writes to support@community-access.org through your
  own mail program. There is no GitHub token and no GitHub path.
- F1 help for the new windows: Custom Effects, File Properties, Conversion
  Report, Keyboard Shortcuts and the Tag Editor.

### Installer and portable

- The installer's choices -- a desktop icon (off by default), the File
  Explorer entry (on) and launching when done (off) -- are real Windows
  checkboxes that announce checked and not
  checked, like every family installer since 2026-09-26.
- The installer (Inno Setup 7) installs the shared QuillVille runtime if it is
  absent, then the app, with Start Menu entries and the documents.
- The File Explorer checkbox, checked by default, adds "Convert with Quill Converter" to
  the File Explorer right-click menu for every audio and video type the app
  reads, per user, removed on uninstall. `.ts` is left off because it is
  commonly a TypeScript file.
- Selecting many files in Explorer and choosing the entry queues them all in
  one window: a second launch hands its files to the running one.
- The portable zip keeps settings in its own `data` folder next to the app.
- FFmpeg and ffprobe, libmpv, yt-dlp, mutagen and, when built, the OptiLab
  Core adapter are bundled in both; nothing downloads on first use.
- Check for Updates offers the matching download, installer or portable.
- Quill Converter is listed on the QuillVille menu of the other apps, and
  QUILL's own "Convert with Quill" Explorer entry is available in public
  builds.
- The tile icon is drawn by the family generator, `scripts/build_app_icons.py`,
  which replaced Converter's own private generator.

### Fixes

- AIFF and AU output are written big-endian, as those formats require; AIFF
  output failed before.
- WAV, Wave64 and CAF at 32-bit are real 32-bit floating point.
- A preset or Advanced setting a format cannot accept no longer fails the file
  half way through a batch.
- Several files chosen at once in File Explorer all arrive in one queue, and
  a second launch brings the running window forward instead of doing nothing.
- Loudness effects no longer hand FFmpeg's internal 192 kHz on to the output:
  WMA refused it, and FLAC stored it. A loudness target now writes 48 kHz
  unless you choose a rate.
- A video with no sound track, converted to a sound format, fails with the
  reason in words; before, FFmpeg quietly put the video itself inside the
  .m4a.
- MP2 (on its own, or inside an MPEG-2 video) is written at an MPEG-1 rate, so
  a 22 kHz source no longer fails at the default 192 kbps.
- A film whose captions cannot go into MKV (DivX bitmaps, broadcast
  teletext) converts without them and says so, instead of failing. A Flash
  video whose sound declares an unnamed channel layout converts.
- File Properties shows the title and artist of Ogg, Opus and Speex files,
  which keep their tags on the sound track rather than the file.
- Check for Updates offers Quill Converter's own downloads. With no asset
  prefix it would have fallen back to the newest release of any family app.

### From the July build

Carried into 1.0.0 unchanged in spirit:

- A tray-resident, single-instance window with focus on the queue at launch,
  and Ctrl+Alt+Shift+C to show or hide it from anywhere.
- Folder scanning with the source folder layout mirrored in the output, and a
  conflict policy that never overwrites unless asked.
- Ten one-click sound presets: Just convert, MP3 320, 192 and 128, Podcast,
  Audiobook (M4B), Voice memo, Web voice (Opus), Archival (FLAC) and
  Hearing-aid mono.
- Exact bit rate, sample rate, channels and bit depth, each starting on "leave
  the preset alone" -- now in the main window's Advanced section rather than
  a separate dialog.
- Convert from URL, now with yt-dlp bundled rather than installed on demand.
  Unavailable in Safe Mode.
- The headless `quill convert` command over the same engine.
