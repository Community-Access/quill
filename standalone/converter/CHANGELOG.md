# Changelog

All notable changes to Quill Converter are documented here in summary. The
itemized list is `docs/CHANGELOG.md`, which is the one the app's Help menu
opens (Help > What's New, Ctrl+Shift+F1); `docs/release-notes-1.0.md` is the narrative version.

Quill Converter is the product wrapper; the application code lives in the
`quill` package, so the entries below are drawn from the history of
`quill/apps/converter.py`, `converter_menu.py`, `converter_actions.py`,
`converter_chapters.py` and `converter_advanced.py`,
`quill/ui/converter_dialogs.py`, the shared conversion engine under
`quill/core/audio/`, the shared Convert Audio dialog, and this folder.

## 1.0.0 - 2026-09-28

The first public release. The app was first built in July 2026 as an audio
converter (an entry here once dated it 2026-07-31); that build was never
published as an installer, and everything in it is part of 1.0.0.

Since build 2:

- **Shared-runtime licensing.** Installed editions use the QuillVille Runtime,
  which currently carries PyMuPDF 1.28.2 under AGPL-3.0 through the shared
  GLOW dependency; Converter does not itself expose GLOW. Release-specific source
  and legal review are required before the next public release. Portable
  contents must be checked separately. See Licences and Notices and the
  PyMuPDF distribution review.
- **Sharp text at any display scaling** (2026-10-31). Quill Converter now handles
  each monitor's scaling itself instead of letting Windows stretch it, so
  text stays sharp at 125, 150 and 200 percent and on monitors with
  different scaling, and windows and list columns keep their proportions.
  Setting the environment variable `QUILL_DPI_UNAWARE` to `1` turns this off,
  for diagnosing a display problem (#1702). User guide: "Text looks blurry, or a window is the wrong size".
- **Pygments in the notices** (2026-10-31). The shared runtime now bundles
  Pygments, which QUILL and QUILL Lite use to read code and web pages for
  spell check, so Quill Converter's third-party notices list it.

Build 2:

- **Also in build 2:** Process with Auphonic (Ctrl+Shift+A) and Auphonic Work
  Waiting (Ctrl+Alt+A); File Properties (Alt+Enter) ends with the drive's
  details and free space; Help > Changelog is now **Help > What's New** on the
  same key, Ctrl+Shift+F1; QUILL Transcribe on the QuillVille menu (Alt+U, then
  T, or Ctrl+Alt+Shift+F11); the user guide says where transcription lives;
  FFmpeg's licence files are checked on every build; and every release build
  checks its version against what is published. Itemized in
  `docs/CHANGELOG.md`.
- **Where Quill Converter's own sounds play, and Alt+Shift+M to turn them off.** **File > Preferences > App Sounds Play On...** offers System default, None (no sounds), or any sound card or headset by name. After a change one sound plays on the new card, so you hear where it went. If that card is unplugged the sounds play on the system default until it is back, and Quill Converter says so once. **Alt+Shift+M** turns Quill Converter's sounds off and back on where they were, and **File > App Sounds** shows a check mark while they are on. Each QUILL app keeps its own choice; "Share these choices with my other Quill apps" keeps them in step. Your screen reader is never moved. Asked for on QUILLVille by Rick Lewis.

- **Found before release (2026-10-05):** no show and hide key until you choose
  one in File > Show and Hide Key... (Ctrl+Alt+Shift+H), which refuses a key
  another QuillVille app uses; Find a Setting or Command (Ctrl+Alt+Shift+S);
  build numbers (About says 1.0.0 (build 1), file version 1.0.0.1); the
  installer and the portable copy write `quill-app-version.ini`, so About and
  Check for Updates name the Converter you installed rather than the shared
  runtime's code; web requests name Quill Converter; a portable copy starts
  from a folder with a space in its name; Stable is always code-signed and
  Beta and Dev never; no AI, kept so by a test; and the user guide is in
  chapters.
- **Two downloads**, both with everything bundled and nothing downloaded on
  first use: `Quill-Converter-Setup-Shared-1.0.0.exe` (Inno Setup 7; installs
  the shared QuillVille runtime if it is absent) and
  `Quill-Converter-Portable-1.0.0.zip` (settings in its own `data` folder).
  FFmpeg and ffprobe, libmpv, yt-dlp, mutagen and, when built, the OptiLab
  Core adapter are inside both.
- **Edit Tags** (Ctrl+T): Audio Studio's Tag Editor, built in -- every tag and
  the cover art of an MP3, M4A, M4B or MP4.
- **Chapters through every conversion.** A Chapters choice (keep, a chapter
  list beside the file, at pauses, every N minutes, or none); chapters land
  inside every format that holds them and in a `.cue` beside the rest; a
  Chapter Workbench (Ctrl+H) edits them at the playhead.
- **Advanced Options in the main window**, shown or hidden with View >
  Advanced Options (Ctrl+Alt+V), replacing the separate Convert Audio dialog.
- **An installer a screen reader can read.** Every choice in it -- the desktop
  icon, the File Explorer entry, launching when done -- is a real Windows
  checkbox that says whether it is checked (the family's installers moved to
  this on 2026-09-26; Inno Setup's own task list always read "not checked").
- **File Explorer right-click.** An installer checkbox, checked by default, adds
  "Convert with Quill Converter" for every audio and video type the app reads,
  per user, removed on uninstall. Many files selected at once arrive in one
  queue.
- **When Quill Converter cannot start, it says so.** The launcher keeps a
  launch log of what the app's engine reports and, when the engine exits with
  an error, opens one plain message: "Quill Converter did not start", the
  reason in words, where the log is, and the support address. Opening
  `QuillConverter.exe` from inside the zip is recognised. Shared launcher
  code (2026-09-28, first in Quill Radio 3.0.4); itemized in `docs/CHANGELOG.md`.
- **Formats.** 25 sound and 9 video output formats, each labeled with what it
  is for; 82 input types. Format constraints (sample rates, mono-only AMR,
  bit rates on lossless formats) are handled rather than failing. AIFF and AU
  are written big-endian (AIFF output was broken); 32-bit WAV is real float.
- **Video.** Video to sound keeps the sound; video to video keeps the picture,
  with five video presets including Change the container only. Every audio
  track is kept in MP4, MKV, MOV and WebM; MKV keeps subtitles.
- **Effects.** Named effect recipes on the main window, a Custom Effects dialog
  (Ctrl+E) with every switch, loudness targets, gain, speed, fades and keep
  from / keep until. Effects apply to the sound of video conversions too.
- **Preview** (Ctrl+P) and **Preview Original** (Ctrl+Shift+P): fifteen seconds
  exactly as the result will sound, and the same fifteen seconds untouched.
- **Join into One File** (Ctrl+J), with a chapter per source in every format
  that holds chapters, MP3 included; **Split by Chapters** (Ctrl+Shift+S),
  following the Chapters choice.
- **Queue and reports.** Paste and drag and drop, reorder, clear, File
  Properties (Alt+Enter), Convert that becomes Stop, progress every 25 percent,
  a Conversion Report (Ctrl+R) with plain-language failure reasons, Open
  Output Folder, cover art carried across, and choices remembered between runs.
- **Help menu** matching Quill Radio and QUILL Lite, a Keyboard Shortcuts list
  (Ctrl+Alt+K), and support by email only: Help > Get Help from Support
  (Ctrl+Alt+F2) writes to support@community-access.org.
- **In the family.** Quill Converter is on the QuillVille menu of the other
  apps, and QUILL's own "Convert with Quill" Explorer entry is available in
  public builds.
- **The tile icon moved to the family generator.** Quill Converter's icon was
  already generated rather than hand-drawn -- it had its own
  `assets/make_quill_converter_icon.py` -- which made it the only app in the
  family whose icon could be reviewed in source. That idea was right and has
  been generalised: `scripts/build_app_icons.py` at the repository root now
  draws every app's icon from one design system, and Converter's private
  generator has been retired. The drawing is unchanged in concept (two arrows
  passing in opposite directions, on a violet tile); what changed is that no two
  apps can now drift apart, or collide, because a test asserts that no two
  render the same face.
- **Carried from the July build:** the tray-resident single-instance window
  and its Ctrl+Alt+Shift+C show/hide key, folder scanning with the source
  layout mirrored, a conflict policy that never overwrites unless asked, ten
  sound presets, exact encoder settings, Convert from URL
  (yt-dlp now bundled rather than installed on demand), and the headless
  `quill convert` command.

See `docs/CHANGELOG.md` for the full itemized list.
