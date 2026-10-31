# QUILL Studio -- Product Requirements

Version 2.0.0 (QUILL Studio; see CHANGELOG.md)

Unreleased runtime update: Windows OCR and Media use the shared PyWinRT 4.0.3
runtime and Windows SDK 10.0.28000.2705 projections; Windows Media releases
device references and event handlers on shutdown. DECtalk is not distributed
or downloaded by QUILL and must be installed separately. Broader production,
Converter round-trip and AI transcription work is proposed in the consolidated
Studio planning PRD, not represented by this document as delivered.

**Distribution licensing:** Installed Studio editions use the QuillVille
Runtime, which currently carries PyMuPDF 1.28.2 under AGPL-3.0 through
GLOW, although Studio does not expose GLOW. Release-specific source and legal
review are required before the next public release; inspect portable builds
separately. See the PyMuPDF distribution review and Licences and Notices.

## 1. Product overview and mission

QUILL Studio is a standalone Windows desktop application for audiobook
and audio production, extracted from the QUILL editor's Audio Studio. Its
mission: audio production that meets blind and low-vision creators where they
are. Every step -- narrating a manuscript, assembling recordings into a
chaptered book, fixing chapter markers, measuring against ACX, publishing a
feed -- is fully operable with a keyboard and a screen reader, with progress
you can hear.

The product is one studio with three journeys:

1. Narrate Documents -- turn a folder of documents (.docx, .md, .html, .txt)
   into speech audio or a finished chaptered audiobook.
2. Build From Recordings -- combine a folder of pre-recorded audio files into
   one chaptered M4B or MP3 master.
3. Edit a Book -- open a finished audiobook in the Chapter Workbench: play it,
   fix chapters and tags, run the ACX check, publish.

Since 2.0.0 the studio also captures, inspects, edits and verifies
screenshots (section 4.14): a named window, a display, the whole desktop, a
guided portion of one of them, or one accessible element inside a window, each
saved with a verification report that separates what was measured from what an
AI only suggested. Recording video is not yet part of the product; it is
specified as the next thing to build in the QUILL Studio planning PRD
(`docs/planning/QUILL-Studio-PRD.md`, section 7A).

The wizard, Chapter Workbench, batch narration pipeline, and publish surfaces
are the exact same code QUILL ships. This app supplies what a standalone
product needs around them: a home window, menu bar, status bar, system tray,
preferences, voice preview, background-task host, and an installer.

## 2. Relationship to QUILL

QUILL Studio is built from the QUILL repository itself. The whole
application lives in the `quill` package (`quill.apps.studio`); this directory
is the product wrapper only -- entry point, installer, assets, and these docs.
Superseded: the Studio was originally assembled in a separate repository
(S:\QUILL-AS) that vendored its dependency closure into a `quillas` package and
re-synced by hand. That vendoring was retired on 2026-07-20 when the app was
reverse-vendored into `quill.apps.studio`; requirements REL-1 and REL-2 below
record the rule that replaced it.

- REL-1. All Audio Studio feature code must live in the shared `quill`
  package, not in a copy. The product wrapper may contain only the entry
  point, packaging, assets, and documentation; a feature added here instead of
  upstream is a defect.
- REL-2. There must be no vendored or hand-synced duplicate of QUILL's audio
  code. A build of this product is a build of the current `quill` package, so
  the standalone Studio and QUILL's built-in Audio Studio cannot drift.
- REL-3. Behavior parity with QUILL's built-in Audio Studio (QUILL PRD
  sections 5.25d and 5.25e) is a requirement, not a goal. Feature changes land
  in the shared package and reach this app on its next build. There must not be
  a second pipeline or forked wizard behavior.
- REL-4. The app must use the shared `%APPDATA%\Quill` data store, the same
  store used by QUILL, Quill Radio, and QUILL Cast. Speech defaults (engine,
  voices, rates, chapter sounder) live in the shared settings.json: a voice
  configured here is the voice QUILL reads aloud with, and vice versa.
- REL-5. App-local preferences (window behavior, update checks) must live in
  their own file (`audio-studio-app.json` in the data dir) so the shared
  settings.json stays exactly what QUILL wrote.
- REL-6. Downloaded speech engines, voices, and engine packs
  (`%APPDATA%\Quill\engine-packs`, Piper voices, Kokoro models, ffmpeg
  component installs) must be shared with the other Quill apps -- downloaded
  once, used by all.

## 3. Users and accessibility requirements

Primary users are blind and low-vision authors, narrators, and podcasters
working with JAWS or NVDA on Windows. Accessibility is a functional
requirement, not a layer.

- A-1. Every interactive control must have an accessible name, including the
  inner text controls of composite spinners.
- A-2. Every function must be reachable by keyboard. There must be no
  mouse-only paths. Menus, buttons, and wizard navigation carry mnemonics; the
  library list acts on Enter (open) and Delete (remove).
- A-3. All modal dialogs must go through the host's `_show_modal_dialog`
  contract (`apply_modal_ids` keyboard contract); never a bare `ShowModal()`.
- A-4. Wizard page changes must be announced ("Step 2 of 7: What should I
  read?") and focus must move to the new page.
- A-5. Long runs must be followable by ear: status-bar progress mirrored from
  the worker, plus optional spoken milestones at 25, 50, and 75 percent
  (preference-controlled, on by default).
- A-6. Every wizard page must open with a one-sentence purpose line before any
  control, so screen-reader users get context first.
- A-7. Playback must announce position on demand ("Where am I?" speaks chapter
  N of M, elapsed and remaining in the chapter and the book) and announce each
  chapter once as playback crosses into it.
- A-8. Outcomes -- run completion, save, publish, download, error -- must be
  announced in plain sentences through the screen-reader bridge, and errors
  must surface as dialogs on the UI thread, never silently.
- A-9. Announcements must be delivered by the shared announcement service, not
  by a private speech call, so every channel the service carries -- speech,
  braille, sound, and the visual status slot -- reaches this app, and a channel
  added upstream appears here without app-side work.
- A-10. Announcements must reach a connected braille display by default, under
  three invariants: braille must never cost speech (any braille failure is
  recorded for diagnostics and degrades to speech-only, never to silence); a
  message must never be truncated to the display width; and the display must
  not be stolen twice -- an identical message inside the dedupe window is
  skipped, and a burst of differing messages settles to the newest rather than
  each overwriting the last, with errors always written through immediately.
- A-11. Announcement behaviour must be user-configurable from the shared
  settings store (braille on/off, braille style, dedupe window, sticky errors,
  app sound cues, cue-instead-of-speech under Quiet Mode, and which severities
  interrupt), and diagnostics must report whether braille was both supported
  and active, so "braille is broken" and "no display is connected" are
  distinguishable in a support bundle.

## 4. Functional requirements

### 4.1 Home window and library

- AS-1. The app must present a home window that is intentionally quiet: a named
  activity line, a status bar, and a menu bar. Books must not be front-and-center
  in the home window by default.
- AS-2. A separate Library Window (View > Library Window) must provide the
  "Your books" tree with the recent-audiobook MRU, most recent first, flagging
  missing files. Enter opens the selected book in the Chapter Workbench; Delete
  removes it from the library without touching the file (and says so).
- AS-3. The menu bar must provide: Studio (Open Studio Wizard Ctrl+N, the three
  journeys, Open Book File Ctrl+O, Open Job File, Resume on launch, Recently
  Played, Minimize to Tray Ctrl+Alt+T, Preferences Ctrl+Comma, Exit), View (Show
  Status Bar, Library Window Ctrl+Alt+Y), Capture (Capture screen, Open saved
  screenshot, Screenshot Inspector, Cancel pending capture, Screenshot active
  window now, Screenshot full desktop now, Repeat last selected target,
  Screenshot global hotkeys; see AS-93), Book Tools (Publish a Finished Book, Make a
  Podcast Feed From a Folder, ACX Compliance Check, Sleep Timer, Mute Playback
  Ctrl+M, Play Queue), Voices (Speech Hub, Manage Speech Models, Pronunciation
  Dictionaries, Generate Captions, Convert Audio, Convert from URL, Download
  Optional Components, Get FFmpeg), AI (Set Up AI), and Help (User Guide, PRD,
  Release Notes, Command Palette Ctrl+Shift+P, Check for Updates, Report a Bug,
  View Log, Save Diagnostics, About).
- AS-4. All menu actions must also be registered as commands reachable from
  the command palette.
- AS-5. The status bar must reflect readiness ("Ready - N books in your
  library") when idle and must be owned by the running task while background
  work is in flight.
- AS-85. The status bar must be reviewable, not merely visible: F6 moves focus
  into it, Left/Right move between cells, Enter activates the focused cell, a
  per-cell context menu is available, and Escape or a second F6 returns focus
  to the window. Cells are Activity, Progress, Sleep timer, Your books, and
  Time. View > Show Status Bar must toggle it and the choice must persist in
  the app-local prefs.
- AS-86. A running narration or build must drive the Progress cell (percent,
  files, current step) and the same text must be written to the system-tray
  tooltip, so a run minimized to the tray stays reviewable.
- AS-6. Opening a book that no longer exists at its recorded path must show a
  warning naming the path and refresh the library list.
- AS-76. The home-window library must be a tree (Favorites, In Progress,
  Recently Played, Inbox, plus any folders the user creates), built from
  `quill/core/audio_studio/library.py`, with each book row tagged by path
  so selection resolves to a concrete book. The tree must preserve the
  selected book across a reload.
- AS-77. The library tree must offer a keyboard-complete context menu on each
  book and folder: Open, Reveal in Folder, Favorite (toggle), Move to Folder,
  New Folder, and Remove (the file itself is untouched; Remove says so).
- AS-78. Favorites, In Progress (books with a saved, unfinished listening
  position), Recently Played, and Inbox (everything else) must be derived
  from the library and history stores without duplicate book entries.

### 4.2 The Studio wizard (shared by both build journeys)

- AS-7. The wizard's start page must offer the three journeys, plus a fourth
  entry, "Capture a screenshot (verify, OCR, and optional AI inspection)", as a
  radio box plus a "Load a job file..." button. The last-used journey
  (`audio_studio_last_journey`, shared setting) must be pre-selected and must
  be persisted on every journey change.
- AS-8. Page flow must adapt to the journey: documents = Start > What to read
  > Voices > Chapters > Output > Book > Summary; audio = Start > Recordings
  folder > Book > Summary; edit = Start > Open a book, with the final button
  relabeled "Open in Workbench"; capture = Start only, with the final button
  relabeled "Open Capture Screen", which closes the wizard and opens the
  Capture screen dialog (AS-94).
- AS-9. Navigation must provide Back, Next, Skip to summary (fast-forward that
  stops at the first invalid page), Start, Cancel, and a "Step N of M" label.
  Next and Start must validate pages and report the failure message.
- AS-10. Wizard defaults must be the user's global speech settings overlaid by
  the source folder's project profile, with precedence this-run > project
  profile > global settings > built-in defaults.

### 4.3 Narrate Documents journey

- AS-11. The source page must offer: source folder (with MRU combo and
  Browse), include subfolders, file-type checkboxes (.docx, .md, .html/.htm,
  .txt), include and exclude glob filters, a max-file-size cap (MB, 0 = no
  limit), and a "Count documents" probe that reports document and word counts
  off-thread and announces the result.
- AS-12. The voices page must offer: engine choice (unavailable engines
  labeled "(not installed)"), voice choice with a Preview button, rate 80-450
  WPM, and Kokoro speed 0.5-2.0.
- AS-13. The voices page must support round-robin voice rotation (an ordered
  list of voices, one per article/heading, with move up/down/remove) and voice
  casting rules (pattern -> voice, where a pattern is a case-insensitive glob
  against the section title or `#N` for section number; first match wins;
  cast rules override rotation).
- AS-14. The voices page must support translated editions: one or more
  (language, engine, voice) targets, translated by either the configured AI
  provider (cloud) or a local LibreTranslate server. Each translation is
  exported as a sibling file named "<stem> (<Language>)<ext>".
- AS-15. The chapters page must offer: chapter mode (one chaptered file per
  document, or separate file per article), chapter heading level (every
  heading, level 1, levels 1-2, levels 1-3), a "Preview chapter titles" probe
  (first 20, off-thread), speak headings aloud, combine empty headings into
  the next article, a transition sounder with volume, and article gap,
  sentence gap, and trailing-pad milliseconds.
- AS-16. The output page must offer: output format (MP3, M4B, WAV),
  existing-file policy (skip/resume, overwrite, rename), normalize loudness to
  ACX, reuse unchanged audio (incremental rebuild), dry run (writes
  `<doc>.preview.txt`, no audio), save the exact spoken text
  (`<doc>.spoken.txt` sidecar), audition (first document only), and a
  temporary-files folder override.
- AS-17. The book page must offer: assemble into one audiobook, title, author,
  narrator, genre, year, a consented "Look up book details" (Open Library +
  MusicBrainz; only title and author are sent; cover download is separately
  consented), cover image, book format (M4B or MP3), normalize the book to ACX
  loudness, fade-in/fade-out milliseconds, book tempo 0.5-2.0
  (pitch-preserving), spoken opening/closing credits, review chapters before
  building, and an explicit output path synced to the chosen format.
- AS-18. The summary page must restate the whole run in plain sentences and
  offer "Save a job file...".

### 4.4 Execution pipeline (batch runs)

- AS-19. Starting a run must, in order: remember the source folder in the MRU,
  persist the voice/engine choices to shared settings, auto-save the project
  profile into the source folder, then run the batch.
- AS-20. Progress must be shown in a non-modal, minimizable, screen-reader
  announced progress dialog; percent is weighted by word counts, with
  per-chunk movement inside large documents, mirrored to the status bar.
- AS-21. Cancellation must be cooperative: the current file always finishes
  (no partial or corrupt output); the run stops between documents and reports
  "Cancelled after N of M".
- AS-22. Per-file failures must be counted and logged but must never abort the
  run. Voices that fail must enter a persisted voice blacklist and be skipped
  by rotation on later runs.
- AS-23. Runs that would spend money (cloud translation or cloud TTS) must
  show an estimated cost and require confirmation before starting. Local-only
  runs must never be interrupted by a cost prompt.
- AS-24. Incremental rebuild must reuse unchanged outputs (content plus all
  shaping settings fingerprinted in `<folder>/.quill/speech-cache.json`) when
  reuse is on, policy is overwrite, chapter mode is single, and the run is not
  a dry run or audition.
- AS-25. Every run must write a timestamped conversion log in the output
  folder and clean up its temporary folder (`quill-batch-<timestamp>`) when
  done.
- AS-26. Book assembly must support Library mode (every immediate subfolder
  becomes its own audiobook, unattended) and spoken credits chapters, and must
  open the chapter review editor before building when review is requested or
  when the sources are purely pre-recorded audio. Cancelling review keeps the
  synthesized audio and skips only the book.
- AS-27. Run completion must be summarized in one announced sentence (done,
  chapters, skipped, errors, book result). Long text must be chunked per
  engine (Kokoro 1000, Piper 4000, others 8000 characters).

### 4.5 Build From Recordings journey

- AS-28. The recordings page must offer: source folder (shared MRU), include
  subfolders, Library mode, and "Trim leading and trailing silence from each
  recording". Accepted inputs: MP3, M4A/M4B, WAV, FLAC, Opus, OGG (and AAC).
- AS-29. This journey must force book assembly on and default to chapter
  review (except in Library mode); the Book page hides the narration-only
  options (credits) it cannot honor.
- AS-30. Files must be ordered by natural sort; chapter titles must derive
  from filenames (track-number prefixes stripped, underscores to spaces,
  purely numeric names becoming "Chapter N").
- AS-31. Cover art must be auto-discovered in the folder (cover/folder/front/
  albumart/album/artwork stems; jpg/jpeg/png), overridable on the Book page.
- AS-32. A pre-flight check must warn (not block) when sources mix sample
  rates, channel counts, or codecs; the build re-encodes to a uniform master.
- AS-33. Output must be a chaptered M4B (AAC 96k, native MP4 chapter atoms,
  cover as attached picture) or MP3 (LAME VBR q4, ID3v2.3 CHAP/CTOC chapters);
  FLAC/Opus are deliberately not offered as book formats (no chapter markers).
- AS-34. Every built book must be verified (chapter count, positive duration,
  monotonic starts) and must ship two sidecars: a human-readable
  `<book>.chapters.txt` and a Podcasting 2.0 `<book>.chapters.json`.

### 4.6 Chapter Workbench (Edit a Book)

- AS-35. The Workbench must open MP3, M4B, and M4A books; a file with no
  chapter markers must open as a single chapter spanning the file so it can be
  split. Opened books must join the home-window library MRU.
- AS-36. The embedded player must provide Play/Pause, Stop, Previous chapter,
  Next chapter, Rewind, Forward (10-second step), Where am I?, speed choice
  (0.75x, 1x, 1.25x, 1.5x, 2x, pitch preserved), a position slider, and a
  volume slider -- all named and keyboard-operable.
- AS-37. The Workbench must resume from the saved listening position on open
  ("Resuming where you left off") and save the playhead on close. Previous
  chapter within 3 seconds of a chapter start must go to the prior chapter.
- AS-38. Chapter surgery must include: rename, split at playhead (minimum
  1-second parts), set chapter start to playhead, merge into previous, and
  Restore original (from the snapshot taken at open). Audio bytes are never
  altered by chapter surgery.
- AS-39. "Propose chapters from silences" must run ffmpeg silence detection
  with adjustable noise floor (-60..-10 dB, default -30) and minimum silence
  (0.1..5.0 s, default 0.8), place boundaries at silence midpoints, enforce a
  5-second minimum chapter, and always land as a reviewable proposal -- never
  applied blind.
- AS-40. "Propose AI titles" must be present only when AI is configured and
  not in Safe Mode. It must show a consent dialog first, transcribe each
  chapter's first minute locally (audio never leaves the machine), send only
  the transcribed text to the AI, cap titles at 8 words, apply only changed
  titles, and remain undoable via Restore original.
- AS-41. "Check against ACX" must measure integrated loudness, true peak, and
  noise floor via ffmpeg loudnorm analysis, judge them against the ACX window
  (-20 +/-3 LUFS integrated, -3 dBFS max true peak, -60 dBFS max noise
  floor), announce the verdict, and show per-metric results with plain
  recommendations on failure.
- AS-42. Chapter lists must import from Audacity labels, timestamp lists, CUE
  sheets, and Podcasting 2.0 JSON (auto-detected), and export to those four
  formats plus CSV.
- AS-43. "Split into files" must write one audio file per chapter into a
  chosen folder.
- AS-44. Tag editing must cover book title, author, narrator, genre, and year.
  Saving an MP3 must rewrite tags and chapters in place without touching audio
  bytes; an M4B must Save As a new file via a lossless stream-copy re-mux (the
  in-place Save button is disabled for M4B and says why).
- AS-45. Publish must refuse until chapter and tag edits are saved.
- AS-79. The Workbench player must expose a Mute toggle (Ctrl+M from the
  shell) that caches the pre-mute volume, sets volume to zero while muted,
  restores it on unmute, updates the button label, and announces the state.
- AS-80. The Workbench player must apply per-book volume and mute on open
  from `book_prefs` (`quill/core/audio_studio/book_prefs.py`) and persist
  volume and mute changes back to that store, so each book remembers its own
  level across launches.
- AS-81. While a Workbench is open, the app shell must route the media
  Play/Pause, Stop, Next chapter, and Previous chapter keys (Windows
  RegisterHotKey) to the active player; with no Workbench open the handlers
  are silent no-ops. Media keys must be unregistered on exit.
- AS-82. `open_book_in_workbench` and the Workbench dialog must thread
  optional host callbacks (`on_player_ready`, `on_finished`, `on_volume`,
  `on_mute`, `on_closed`) down to the player so the shell can drive media
  keys, per-book prefs, history position-stamping, and queue auto-advance.
  Embedded QUILL passes none; the standalone shell wires all of them.

### 4.7 Voices and engines

- AS-46. Offline engines: Windows SAPI 5 (always available), DECtalk, Piper
  (neural), Kokoro (neural), eSpeak-NG, and the macOS system voice on macOS.
  Online engine: ElevenLabs (available when a key is stored and the client is
  installed). Availability must be probed, and unavailable engines must be
  visibly labeled, never hidden.
- AS-47. The Speech Hub must present voices and engines across offline/online
  read-aloud and offline/online dictation tabs, let the user select engine,
  voice, and per-engine pace/pitch/volume, and persist selections to the
  shared settings (so QUILL uses them too).
- AS-48. Neural engines and voices must be download-on-demand, never bundled:
  Piper voices download from the pinned voice catalog (offline bundle first
  when present, then the catalog URL, with .part temp files and atomic
  replace, cancelable progress, and cleanup on failure); Kokoro models, engine
  executables (Piper, eSpeak), ffmpeg, and other optional components install
  through the shared component downloader into the shared data store. DECtalk
  is supported only when installed separately and is not distributed by QUILL.
- AS-49. Voice preview must always try to make sound: play the bundled
  pre-recorded sample when one ships; otherwise, if the engine is installed,
  synthesize the standard preview phrase live in the background; otherwise say
  "Download this voice to hear a preview." Every preview must speak the same
  phrase so before/after-download comparisons are direct.
- AS-50. Starting a new preview must supersede the old one: in-flight
  synthesis results are discarded by generation check and playback is cut.
- AS-51. Choosing "Export to audio" from the Speech Hub must open the Audio
  Studio wizard (documents journey).
- AS-87. Generate Captions (Offline) must transcribe a chosen audio or video
  file to `.srt` or `.vtt` entirely on the local machine, using the shared
  speech-recognition models, and must offer to install a model when none is
  present. No audio may leave the machine.
- AS-88. Convert Audio must offer a mixed file/folder queue, an output format,
  a preset, a destination, and an on-conflict choice (Rename / Skip /
  Overwrite). It must run off the UI thread with multiple workers, a
  determinate progress dialog, a working Cancel, and a spoken summary that
  names failed files rather than reporting a clean run. The offered output
  formats must be probed from the available ffmpeg, never assumed, so a batch
  cannot fail part-way for a missing encoder. It is fully local and must
  therefore remain available in Safe Mode.
- AS-89. The converter's Advanced panel must expose loudness normalization
  (audiobook/ACX or podcast), gain, high-pass, silence trimming,
  pitch-preserving tempo, compressor, leveler, fade in, fade out, and a
  limiter, all neutral by default, and must reveal them without changing the
  Basic flow.
- AS-90. Convert from URL must obtain one-time consent covering both the
  on-demand downloader install and the user's rights to the audio, before any
  network contact, and must be unavailable in Safe Mode.
- AS-91. Converter progress must be reported through the same task-progress
  channel as a narration run, so it reaches the status bar's Progress cell and
  the tray tooltip.

### 4.8 AI features and Safe Mode

- AS-52. AI setup must run through the shared AI setup wizard (providers,
  keys, free-model paths). API keys must be stored in the Windows Credential
  Manager / DPAPI, never in plain settings files.
- AS-53. AI-powered features are exactly: chapter title proposals (AS-40),
  translated editions (AS-14), cloud TTS voices (ElevenLabs and
  provider-backed voices), and screenshot inspection (AS-105 to AS-107). Each
  must be consent-gated and cost-surfaced where money is involved; where a
  price cannot be estimated (screenshot inspection), the consent prompt must
  say so rather than show a guess.
- AS-54. Translation must retry with bounded exponential backoff, cache
  repeated strings, and halt a language entirely on persistent failure rather
  than emit half-translated audio.
- AS-55. Safe Mode (`QUILL_SAFE_MODE=1` or `--safe-mode`, plus the shipped
  safe-mode launcher) must disable AI setup, AI chapter titles, screenshot AI
  (manual and automatic), system-wide screenshot hotkeys, and all publishing
  surfaces, each refusal announced in a plain sentence. Screenshot capture,
  local OCR, editing and verification stay available in Safe Mode.

### 4.9 Publishing

- AS-56. Publish a Finished Book must offer three consent-gated destinations
  for an already-saved book: a local podcast feed, SFTP upload, and Auphonic
  mastering.
- AS-57. Local feed: "Write feed file" must write a self-contained RSS 2.0
  (+ iTunes + Podcasting 2.0) `.rss` next to the book, built from its tags,
  probed duration, and `.chapters.json` sidecar, with no network access. A
  blank media URL may be derived from a saved SFTP destination's public URL.
- AS-58. SFTP: destinations (name, host, port, user, remote folder, public
  URL) must be savable and reusable; passwords must be stored only in the
  Windows Credential Manager; uploads must show cancelable byte progress; host
  keys must follow the shared SSH policy (reject unknown hosts unless
  trust-first-use is enabled in settings).
- AS-59. Auphonic: the API token must live in the Credential Manager; the
  dialog must verify the account and list presets (showing remaining credits),
  require consent before upload, poll production status with cancel support
  (up to about 30 minutes), and download results beside the book as
  "<stem> (Auphonic)".
- AS-60. Make a Podcast Feed From a Folder must manage a folder as a show:
  per-folder config in `<folder>/.quill/feed.json`, oldest-first episode
  numbering, per-episode titles and descriptions, "Write feed.rss now"
  (requires a media URL base), and a show-notes page. All folder-feed work is
  local file IO; uploading remains the SFTP destination's job.
- AS-61. The standalone ACX Compliance Check (Book Tools menu) must measure
  any audio file against the ACX window in the background and report the three
  metrics with pass/fail and recommendations; if ffmpeg is missing it must
  point the user at Voices > Get FFmpeg instead of failing.

### 4.10 Job files and project profiles

- AS-62. A job file (`.quilljob`) must capture every field of a run as
  hand-editable UTF-8 JSON with a format marker and version, written
  atomically. Loading must be tolerant: unknown keys ignored, missing keys
  keep defaults, malformed files rejected with a speakable error.
- AS-63. Jobs must be savable from the wizard summary and loadable from both
  the wizard start page and Studio > Open Job File; both paths must land in
  the wizard with every page pre-filled and behave identically from there
  (including re-load loops).
- AS-64. A project profile (`<folder>/.quill/speech-project.json`, version 2,
  schema-validated) must be applied when the wizard opens on that folder and
  auto-remembered on Start, covering synthesizer, output, chapters,
  translation, credits, and library mode. Older profile versions must load
  with defaults filled in.

### 4.11 Preferences, tray, close behavior, and updates

- AS-65. Preferences must offer: check for updates on launch (default on),
  Alt+F4 minimizes to tray (default off), speak progress milestones (default
  on), and the close action (Ask when work is running / Exit / Minimize to
  Tray, default Ask). They must persist to the app-local prefs file, written
  atomically, with unreadable prefs falling back to defaults rather than
  crashing.
- AS-66. The tray icon must always be present, offering the screenshot items
  of AS-112, Open Studio Wizard and "Resume: <most recent book>", each
  restoring the window first. Studio > Minimize to Tray (Ctrl+Alt+T) must send
  the app to the tray on demand, and sending the app to the tray must announce
  that it is still running.
- AS-67. Alt+F4-to-tray, when enabled, must intercept before Windows closes
  the window so a long narration run keeps going; the titlebar X and Exit must
  keep the configured close action.
- AS-68. "Ask when work is running" must prompt only when protected work is
  actually running (listing the running jobs, defaulting to No/keep open); an
  idle window must just close. A second close during the prompt must not stack
  a second dialog.
- AS-69. On real exit the app must stop any preview, shut down the task
  manager without waiting, unregister media keys, and remove the tray icon.
- AS-70. Update checks must query the shared QUILL project's GitHub releases
  (Community-Access/quill) and resolve **this app's own** release asset for the
  running flavor (installer for an installed copy, portable zip for a portable
  one), so each QuillVille app updates independently from one publishing point
  and an update to a sibling app is never offered here. Checks must be
  available manually from Help at any time, and automatically on launch only
  when enabled, only when due, deferred until after the window is up, and
  silent when there is no update.
- AS-71. Help must open the packaged User Guide, PRD, and Release Notes, offer
  View Log and Save Diagnostics (a redacted bundle), and Report a Bug must
  submit through the shared feedback channel tagged with this app's name and
  version.
- AS-92. An available update must be installable in one step: after Download,
  "Install and restart now" applies it (extracting portable files over the
  install folder, or running the installer silently) and relaunches the app,
  preserving all settings and data.
- AS-83. The Studio menu must offer a Resume on launch opt-in (check item)
  that, when set, reopens the most recently played book at its saved
  listening position on the next launch, silently skipping if the file no
  longer exists. The choice must persist across launches.
- AS-84. The Studio menu must offer a Recently Played submenu, rebuilt on
  open, listing the most recently played books from `history.py`; choosing
  one opens it in the Workbench.

### 4.12 Background work and close protection

- AS-72. All long work (runs, previews, downloads, ACX measures, saves,
  uploads, diagnostics) must run off the UI thread through the frame's
  background-task host, with results and errors delivered to the UI thread.
- AS-73. Tasks that represent real, hard-to-redo work (an export run) must
  register as close-protected so the close prompt can name them; finishing or
  failing must unregister them, refresh the status bar, and reload the
  library.
- AS-74. Task failure must set a failure status and show an error dialog
  naming the task; it must never crash the app.
- AS-75. After a component-install failure the app must offer to save a
  redacted diagnostics bundle (zip) so support has something to read.

### 4.13 Book Tools extras (sleep timer, play queue)

- AS-85. Book Tools must offer a Sleep Timer that, once started, stops
  playback after a chosen delay in minutes or at the end of the current
  chapter, announces that playback stopped, and can be cancelled. The
  setting must persist from `sleep_timer.py` and a `SleepTimerWatcher` must
  fire the stop on the UI thread.
- AS-86. Book Tools must offer a Play Queue dialog backed by
  `quill/core/audio_studio/play_queue.py`: an ordered, editable list of
  books (add, remove, clear, set next) that persists to disk.
- AS-87. When the current book finishes and the Workbench is then closed,
  the shell must advance to the next queue entry whose file still exists,
  opening it in the Workbench and announcing the change; an empty queue or a
  missing next file ends playback quietly.
- AS-88. The Sleep Timer and Play Queue dialogs must expose an accessible
  name on every focusable control and route through the shared modal contract
  like every other Studio dialog.

### 4.14 Screen capture, inspection and screenshot evidence (2.0.0)

Shipped in the 2.0.0 build (built, not yet released): commits `4b385a57`,
`e8a15444`, `5cc0023f` (merged as `8d2e1c49`) and the picker refinements
`51df692c` to `fbddf261`. The code is the Studio adapter
`quill/apps/studio_capture.py` over shared modules: `quill/core/studio_capture.py`
(targets, verification, reports), `quill/core/studio_capture_ai.py`,
`quill/core/screenshot_project.py`, `quill/core/screenshot_sequences.py`,
`quill/core/screenshot_workspaces.py`, `quill/core/screenshot_note.py`,
`quill/platform/windows/studio_capture.py`, `screenshot_window.py`,
`screenshot_uia.py` and `screenshot_scroll.py`, and the dialogs
`quill/ui/studio_capture_*.py`. These requirements describe source behaviour;
screen-reader, braille, mixed-DPI and installed-upgrade acceptance are still
open (`docs/design/quill-studio-capture-milestone.md`).

- AS-93. A Capture menu must offer eight commands, each also in the command
  palette, with these default in-app chords from `APP_KEYMAPS["studio"]`
  (labels render whatever is actually bound): Capture screen...
  (Ctrl+Alt+Shift+S), Open saved screenshot... (Ctrl+Alt+Shift+O), Screenshot
  Inspector... (Ctrl+Alt+Shift+I), Cancel pending capture (Ctrl+Alt+Shift+X),
  Screenshot active window now (Ctrl+Alt+Shift+F5), Screenshot full desktop now
  (Ctrl+Alt+Shift+F6), Repeat last selected target (Ctrl+Alt+Shift+F4), and
  Screenshot global hotkeys... (Ctrl+Alt+Shift+H). These are in-app keys;
  system-wide keys are AS-111.
- AS-94. Capture screen must list, in one Target choice: the full desktop (all
  displays), each display by number with its size and origin (primary marked),
  each named top-level task window, "Active window after the delay", and
  "Guided region". The window list must by default show roughly what Alt+Tab
  shows (no tool windows, no owned windows unless they are app windows, no
  cloaked windows); an advanced "Show all windows" check box must list every
  visible titled window. Refresh windows and displays must keep the selected
  target by identity (kind, window handle, process, display device); a target
  that disappeared must stay selected and be labelled "Unavailable target",
  never silently replaced.
- AS-95. Window targets must be labelled for listening: the title reduced to
  its first meaningful part, the application's own name stripped from it and
  repeated once in parentheses in a friendly form (for example "Microsoft
  Edge" rather than msedge.exe), at most 80 characters. Process IDs and handles
  must not be read in the list.
- AS-96. Advanced options must be hidden behind a "Show advanced options"
  check box. They hold Show all windows, Window properties..., and Choose a
  specific window element.... Window properties must show the selected named
  window's title, application, process ID, window handle (decimal and hex),
  class name, bounds and executable, and copy the same text to the clipboard
  for a bug report; it is enabled only for a named window.
- AS-97. Choose a specific window element must read the selected window's UI
  Automation tree in the background, read-only (no control is invoked),
  bounded to 1,000 elements and 8 seconds, cancellable, excluding password
  controls, their descendants and offscreen elements. The user filters by name
  or role and picks one; the element becomes a capture target. Before capture
  it must be found again by its runtime ID, and capture must fail, not
  substitute, if the element moved, changed name, disappeared or its window
  changed.
- AS-98. Guided region must need no pixel input: choose a window or display as
  the source, then Whole source (the default), Top half, Bottom half, Left
  half, Right half, or Middle quarter. An "Enter exact coordinates (advanced)"
  check box must offer left, top, width and height in physical desktop pixels
  (negative left and top allowed for displays left of or above the primary),
  prefilled from the guided choice and validated to lie within the desktop. A
  read-only "Capture plan and guidance" field must say what will be included,
  what may be cut off, and that geometry cannot prove the intended content is
  complete.
- AS-99. Capture must use physical-pixel coordinates (per-thread DPI
  awareness, restored afterward). A named window or element must be rendered
  from its own window by handle (PrintWindow), never by sampling the desktop
  behind it; displays, the desktop and screen-area regions are grabbed as a
  rectangle and their dimensions checked. Immediately before and after the
  capture the target must be re-resolved and must fail with a spoken reason,
  never broaden, when: the window closed, is minimized or hung, its process or
  title changed, a display disconnected or the display layout changed, or a
  region's source window moved or resized. No capture ever falls back to the
  full desktop.
- AS-100. Capture screen must offer a delay of 2 to 60 seconds (default 5) and,
  under "More capture options", an optional spoken countdown. Only one capture
  may be pending; a second request is refused with a spoken reason. Cancel
  pending capture (menu, tray, or global key) must cancel a waiting capture and
  say that one already under way may finish. Completing a capture must not
  move focus away from the application being captured; the outcome goes to the
  status bar.
- AS-101. More capture options must offer Several screenshots (1 to 30
  captures, 1 to 60 seconds apart) and Scrolling page. Scrolling page needs a
  named window and a limit of 2 to 30; it must move the window's scrollable
  element through UI Automation's scroll pattern, capture each position, join
  the images only where their overlap matches, restore the original scroll
  position, and mark a result that hit its limit, could not be joined, or could
  not restore scrolling as needing review (spoken). Both modes must write a
  manifest that records an interrupted run as Incomplete with the files it did
  capture.
- AS-102. Capture setups must be savable by name (up to 100 setups, names up to
  100 characters) holding target, delay, count, interval and mode only; the
  output folder and any AI permission must never be saved. Loading must read an
  explicit schema (unknown or out-of-range values rejected), and a saved window
  is rechecked like any other target (AS-99).
- AS-103. Every screenshot must be saved as a uniquely named PNG (existing
  files never overwritten) in the chosen absolute folder (default
  `studio-captures` in the data folder), then reopened, fully decoded, measured
  and SHA-256 hashed from the same bytes. Beside it Studio must write
  `<name>.verification.json` (schema version, evidence, the checks performed,
  and the checks not performed: target identity, privacy, completeness, visual
  correctness) and a readable `<name>.verification.md`. Metadata must record the
  backend, coordinate units, capture time, window DPI and scale factor where
  available, and whether every pixel was the same colour, reported as evidence
  of possibly protected content, not as proof.
- AS-104. Open saved screenshot must accept a PNG, verify it as in AS-103, and
  restore the original target, time, metadata and unverified observations from
  its verification report only when the hashes match.
- AS-105. The Screenshot Inspector must work on the last or an opened
  screenshot: Read text locally (offline OCR, with confidence only when the
  engine reports it), Ask AI, Save report, Export description
  (`<name>.description.txt`), Copy image, and Edit a copy. It must offer seven
  screenshot prompt styles (overview, controls, text and errors, framing
  problems, possible sensitive information, alt text, charts) alongside the
  shared image prompt library and the user's own prompts, editable
  instructions, and a free question. Follow-up questions must use the same
  image, verified by hash, and the prior conversation; they never recapture.
  A file-checks pane must show the source evidence.
- AS-106. Each Ask AI request must first ask for approval naming the provider,
  model and endpoint, stating that the image may hold private information,
  that no redaction was applied, and that the price cannot be estimated. It
  uses the shared AI connection, credentials and vision transport (no separate
  provider settings) and sends a private temporary copy whose hash matches the
  reviewed image, deleted afterwards. AI Off, Safe Mode, or no connected
  provider must refuse with a spoken reason while capture and OCR continue.
  AI text is saved only as unverified observations.
- AS-107. Automatic inspection of future captures must be off by default and
  turned on only with its own approval, bound to the approved provider, model
  and endpoint. A changed connection, AI Off or Safe Mode must pause it (said
  once), and permission must be rechecked immediately before each upload.
- AS-108. Edit a copy must open a nondestructive screenshot editor whose text
  "Edit plan and results" field is the full alternative to the visual preview.
  Operations: Keep only this area (crop), Hide private information (solid
  black redaction, flattened on export), Add a numbered box, Point with an
  arrow, Highlight an area, Spotlight an area, Add a note. Areas are chosen by
  name (whole image, halves, middle, quarters), by recognised text ("Find text
  to select" adds OCR lines as anchors), or by four percentages. Under More
  options: an ordered object list, remove, move and grow or shrink by 1
  percent, resize 10 to 400 percent, visual preview at 25 to 400 percent, pixel
  comparison with another image (changed pixels, share and bounding box,
  never a judgment), save and open a layered project (`.screenshot.json`), and
  export to PNG, JPEG or WEBP without the source's hidden metadata. Undo and
  redo cover every edit; a project holds at most 200 edits; an invalid edit is
  rejected without losing the previous state; the original file is never
  changed, and a changed original is refused before export.
- AS-109. Export evidence bundle must write a ZIP holding the rendered image,
  `evidence.json` (export hash, parent hash, goal, steps to reproduce, review
  state, waiver, public annotation list), `description.md` and
  `description.html`; the original image and its paths are excluded so a
  redaction cannot be undone from the bundle. Two review check boxes (private
  information, intended content) are human acknowledgments, cleared by any
  later edit. Strict evidence export must refuse until both are checked or a
  waiver reason is written, and the waiver goes into the bundle.
- AS-110. Add a spoken note must record from the user's chosen microphone only
  on an explicit Start, through the shared microphone lock (another QUILL
  recording refuses it), stop at two minutes, recognise the speech locally
  with an installed speech model, reject a recording of pure digital silence,
  delete the audio afterwards, and write `<name>.note.json` tied to the
  screenshot's hash with "Recognition unverified". The text is edited and
  acknowledged before it becomes the screenshot's description. Nothing is sent
  to AI.
- AS-111. System-wide screenshot hotkeys must be opt-in with no defaults, set
  in Screenshot global hotkeys... through QUILL's shared hotkey manager and
  limited to four commands: screenshot the active window, screenshot the full
  desktop, screenshot the last selected target, and cancel a pending
  screenshot. Saving must preserve other apps' global bindings; a chord another
  program holds must be reported as not registered; registrations are removed
  on exit; Safe Mode disables them. A global capture must not restore Studio
  before choosing the active window.
- AS-112. The tray menu must begin with Take a screenshot..., Review
  screenshot..., and Cancel pending screenshot, each showing its bound chord
  and restoring the window before acting.
- AS-113. Every capture, inspector, editor, element and note control must carry
  authored inline F1 help (`quill/core/audio_studio/surface_help.py`, audited
  by `quill/tools/studio_help_audit.py`), every dialog must use the shared
  modal contract, and a long operation in the editor, inspector or note dialog
  must refuse a second press with a spoken line rather than disable the
  focused button. Known exception in 2.0.0: Window properties (AS-96) is a
  `wx.MessageDialog` shown with a bare `ShowModal()` from inside Capture
  screen; it should move to the host's modal contract.

## 5. Non-functional requirements

- N-1. Threading: the UI thread owns all wx widgets. Worker threads must never
  touch widgets; every cross-thread UI update goes through `wx.CallAfter`.
  The mpv engine must poll state from a wx timer rather than letting mpv event
  threads touch wx.
- N-2. Persistence: all JSON writes (settings, prefs, profiles, jobs, caches,
  feed configs) must be atomic (temp file + `os.replace`).
- N-3. Network egress is limited to: pinned assets-v1 / catalog component and
  voice downloads (Ed25519-signed where supported), the app's own GitHub
  update check, and explicit user actions -- consented metadata lookup,
  consented cover fetch, user-initiated SFTP/Auphonic publishing, and
  configured AI/cloud-TTS/translation calls (cost-confirmed when paid),
  including screenshot inspection only after per-request approval or the
  separately approved automatic mode (AS-106, AS-107). No other outbound calls;
  capture, OCR, editing, notes and evidence bundles are entirely local. Book building, chapter editing, ACX checks, local and
  folder feeds are entirely local.
- N-4. Privacy: passwords, API keys, and tokens live only in the Windows
  Credential Manager / DPAPI; nothing secret on disk. AI chapter titling sends
  transcribed text only, never audio. Diagnostics bundles are redacted.
- N-5. External processes (ffmpeg, ffprobe, engine executables) must run
  through the hardened safe-subprocess wrapper (no console windows, bounded
  timeouts: 600 s for probes/detection, 1800 s for builds and re-muxes).
- N-6. Performance: a multi-hour book build must remain responsive -- progress
  streamed, window minimizable to the tray, cancellation honored between
  files. Repeat runs must be fast via the incremental synth cache. MP3 tag
  saves must be instant (tags only, audio untouched); M4B saves must be
  stream-copy, not re-encode.
- N-7. The app must start and function with no engines downloaded: SAPI 5
  narration, book building, Workbench editing, and local feeds must all work
  out of the box (ffmpeg is bundled; see P-4).

## 6. Packaging and distribution

- P-1. The Python entry point must be `quill-audio-studio =
  quill_audio_studio:main` (gui-script), a thin wrapper over
  `quill.apps.studio`; package `quill-audio-studio`, Python 3.13+. The
  packaging version is 2.0.0. Studio uses the shared QuillVille Runtime,
  with its own application version and release schedule.
- P-2. Release builds must exclude the heavy ML runtimes (faster-whisper,
  vosk, kokoro-onnx, onnxruntime, torch) and the large libraries the Studio
  never loads -- they install on demand into the shared engine-packs store, and
  excluding the rest keeps both the installer and the portable zip small.
- P-3. One build must feed both artifacts: an Inno Setup installer
  (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`, per-user default install,
  x64, Windows 10+, Start-menu and optional desktop shortcuts, packaged docs)
  and a portable zip (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`). The
  installer must offer Full, Compact (no bundled documentation), and Custom
  setup types; the shared runtime and the app itself are fixed components and
  only the documentation is optional.
- P-4. ffmpeg and ffprobe must be bundled at `tools\ffmpeg` (with license
  text); the build must fail without them. libmpv should be bundled at
  `tools\mpv` (GPL, with license text) for the gapless Workbench player;
  builds may skip it, in which case playback falls back to the Windows Media
  engine.
- P-5. The portable zip must carry a `data\` folder containing a
  `storage-mode.json` marker (`{"mode": "portable"}`) so all data travels with
  the stick; the installed copy must ship no `data\` folder and use the shared
  `%APPDATA%\Quill` store.
- P-6. The uninstaller must never delete or prompt to delete `%APPDATA%\Quill`
  -- that store is shared with QUILL, Quill Radio, and QUILL Cast, and the
  full QUILL uninstaller owns it. Uninstall removes only the install folder.
- P-7. The installed docs (User Guide, Release Notes, this PRD) must ship as
  both Markdown and rendered HTML, wired to Help menu items and the installer
  shortcut.
- P-8. A safe-mode launcher (`run-quill-studio-safe-mode.bat` /
  `--safe-mode`) must ship alongside the normal launcher.

### 6.1 The QuillVille Runtime and shared-runtime editions

- P-9. All QuillVille apps (QUILL, Quill Radio, Quill Weather, and QUILL
  Audio Studio) must be able to share one Python runtime -- the QuillVille
  Runtime -- installed once per user and reused by every app. Once any app has
  installed the runtime, every other app must be able to start against it
  without downloading Python again.
- P-10. The QuillVille Runtime must be reference-counted: each installed app
  that depends on it increments the count, uninstalling an app decrements it,
  and the runtime is removed only when the last dependent app is uninstalled.
  Uninstalling one app must never strand another.
- P-11. The Studio must ship in exactly two editions, like every app in the
  family (owner decision, 2026-10-11):
  - Installer (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`): installs
    the shared runtime, if not already present, plus the app.
  - Portable (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`, roughly
    675 MB): fully self-contained, runs from a USB stick with no installation
    and no internet, bundling a genuine, unmodified copy of Python plus the
    offline speech and text-to-speech engines (whisper.cpp, eSpeak-NG,
    Piper, and neural Kokoro).
  The thin `-Lite` installer and the runtime-less Companion zip are retired.
- P-12. Every QuillVille Runtime download -- whether triggered by an installer
  or by an app's own first launch -- must show a fully accessible progress bar
  that works with NVDA, JAWS, and Narrator, announcing progress as a
  percentage. There must be no silent or screen-reader-invisible wait during a
  runtime download.
- P-13. The app launcher must be a genuine, tiny native executable, and any
  bundled Python must be the official, unmodified build. The previous pattern
  of shipping a renamed or modified copy of Python's `pythonw.exe` as the
  launcher -- a frequent antivirus false-positive trigger -- must not be used.

## 7. Out of scope / non-goals

- Document editing. This app narrates documents; writing them is QUILL's job.
- Radio and podcast listening. Live-stream playback is Quill Radio; podcast
  subscription playback is QUILL Cast. This app only builds and publishes.
- Linux. Windows is primary and macOS is supported by the codebase; Linux is
  not a target.
- Bundling neural voices or ML runtimes in the installer. Engines and voices
  are download-on-demand, always.
- Screen or video recording, audio mixing and routing, and live broadcasting
  in 2.0.0. They are planned, not shipped; see the QUILL Studio planning PRD
  (`docs/planning/QUILL-Studio-PRD.md`), whose section 7A specifies the
  recorded demonstration as the next feature.
- Direct platform publishing (WordPress and similar) -- deferred upstream to
  QUILL 2.0; when it lands there, it arrives here on the next build.
- A second pipeline. Any narration or assembly behavior that diverges from
  QUILL's Audio Studio is a bug, not a feature.

## 7a. Chapters for any recording (2026-10-16)

Todo item 42. **Studio > Find Chapters in a Recording...** (**Ctrl+Shift+R**)
picks any MP3, M4A or M4B and opens the Chapter Workbench on it with Propose
chapters from silences already started, so a lecture or a meeting gets
chapters without being thought of as an audiobook. The proposals are titled
"Proposed chapter N"; a recording with chapters of its own asks Keep mine, add
proposals (the default) or Replace with the proposal; the button reads Stop
proposing chapters while the scan runs, and stopping or closing discards the
answer. Edit a Book's Sleep Timer (Ctrl+Shift+T) and Play Queue (Ctrl+Shift+Q)
now work inside the Workbench: Studio passed them to a function that did not
accept them, so Edit a Book failed before the Workbench opened.

## 8. Future directions

- The QUILL Studio planning PRD (`docs/planning/QUILL-Studio-PRD.md`) holds
  everything planned beyond this document: audio routing, recording,
  demonstrations, video editing, live shows and the Verification Center. Its
  next item is the recorded demonstration (a window or the desktop, with
  chosen sounds, saved as one video file; section 7A there). When a planned
  requirement ships it moves here and the planning PRD keeps one line pointing
  at it.
- Watch-folder auto rebuild surfaced in the UI: the shared
  `core/watch_audiobook.py` has no Studio surface yet.
- Quillins in Audio Studio. QUILL, Quill Radio, and QUILL Cast host Quillins;
  the Studio does not yet build a Quillins menu or an app host, so a
  `studio.pipeline` contribution (the bundled `studio-normalizer` sample) has
  no way to load here. Composing the app-Quillins mixin into the Studio shell
  is the remaining work.
- Recognize `QuillAudioStudio.exe` in the shared portable-evidence check
  (`storage_mode._has_portable_evidence` currently lists only the other Quill
  app executables; the launcher's env export covers the gap today).
- A dedicated voice-casting manager (save and reuse named casting rule sets
  across projects, beyond the per-run rules on the Voices page).
- Toast/notification center: the runner already passes notification flags that
  the standalone host currently drops; a small notification surface would let
  finished overnight runs be reviewed later. (The shared announcement service
  now records announcements, so the history exists; the surface does not.)
- Repeat Last Announcement and the Announcement Self-Test. Both commands are
  implemented on the shared app shell but no companion app calls
  `register_announcement_commands()`, so neither is reachable from the Studio's
  command palette yet. They are deliberately left undocumented for users until
  they are wired up.

---

Change history lives in CHANGELOG.md. Upstream behavior of record: QUILL PRD
sections 5.25d (Batch Document-to-Speech) and 5.25e (Build Audiobook from
Folder / ChapterForge surface).
