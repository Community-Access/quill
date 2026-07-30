# QUILL Audio Studio -- Product Requirements

Version 1.0.0

## 1. Product overview and mission

QUILL Audio Studio is a standalone Windows desktop application for audiobook
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

The wizard, Chapter Workbench, batch narration pipeline, and publish surfaces
are the exact same code QUILL ships. This app supplies what a standalone
product needs around them: a home window, menu bar, status bar, system tray,
preferences, voice preview, background-task host, and an installer.

## 2. Relationship to QUILL

QUILL Audio Studio lives in its own self-contained repository (S:\QUILL-AS).
Unlike Quill Radio and QUILL Cast (thin wrappers over an installed QUILL), it
vendors its dependency closure from QUILL into the `quillas` package so it
builds and runs without the monorepo.

- REL-1. All Audio Studio feature code must be vendored from the upstream
  QUILL repository by `scripts/vendor_from_quill.py`, which copies a seed set
  (core/speech, core/publish, core/schemas, ui/audio_studio, stability,
  platform, assets, and named ui/core modules) and then chases imports via AST
  until the closure is complete, rewriting `quill.*` imports to `quillas.*`.
- REL-2. Vendored files must never be hand-edited; re-running the vendor
  script overwrites them. Only the declared hand-written files
  (`quillas/__init__.py`, `quillas/__main__.py`, `quillas/apps/studio.py` and
  other app-shell modules outside the vendor set) may diverge.
- REL-3. Behavior parity with QUILL's built-in Audio Studio (QUILL PRD
  sections 5.25d and 5.25e) is a requirement, not a goal. Feature changes land
  upstream in QUILL first and reach this app through a vendor sync. This repo
  must not grow a second pipeline or forked wizard behavior.
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

## 4. Functional requirements

### 4.1 Home window and library

- AS-1. The app must present a home window with a named activity line, three
  journey buttons (Narrate Documents, Build From Recordings, Edit a Book), and
  a "Your books" list that takes focus on launch.
- AS-2. The books list must show the recent-audiobook MRU, most recent first,
  flagging entries whose file is missing. Enter or double-click opens the
  selected book in the Chapter Workbench; Delete removes the entry from the
  list without touching the file (and says so).
- AS-3. The menu bar must provide: Studio (Open Audio Studio Ctrl+N, the three
  journeys, Open Book File Ctrl+O, Open Job File, Preferences Ctrl+Comma,
  Exit), Book Tools (Publish a Finished Book, Make a Podcast Feed From a
  Folder, ACX Compliance Check), Voices (Speech Hub, Manage Speech Models,
  Download Optional Components, Get FFmpeg), AI (Set Up AI), and Help (User
  Guide, PRD, Release Notes, Command Palette Ctrl+Shift+P, Check for Updates,
  Report a Bug, About).
- AS-4. All menu actions must also be registered as commands reachable from
  the command palette.
- AS-5. The status bar must reflect readiness ("Ready - N books in your
  library") when idle and must be owned by the running task while background
  work is in flight.
- AS-6. Opening a book that no longer exists at its recorded path must show a
  warning naming the path and refresh the library list.
- AS-76. The home-window library must be a tree (Favorites, In Progress,
  Recently Played, Inbox, plus any folders the user creates), built from
  `quillas/core/audio_studio/library.py`, with each book row tagged by path
  so selection resolves to a concrete book. The tree must preserve the
  selected book across a reload.
- AS-77. The library tree must offer a keyboard-complete context menu on each
  book and folder: Open, Reveal in Folder, Favorite (toggle), Move to Folder,
  New Folder, and Remove (the file itself is untouched; Remove says so).
- AS-78. Favorites, In Progress (books with a saved, unfinished listening
  position), Recently Played, and Inbox (everything else) must be derived
  from the library and history stores without duplicate book entries.

### 4.2 The Studio wizard (shared by both build journeys)

- AS-7. The wizard's start page must offer the three journeys as a radio box
  plus a "Load a job file..." button. The last-used journey
  (`audio_studio_last_journey`, shared setting) must be pre-selected and must
  be persisted on every journey change.
- AS-8. Page flow must adapt to the journey: documents = Start > What to read
  > Voices > Chapters > Output > Book > Summary; audio = Start > Recordings
  folder > Book > Summary; edit = Start > Open a book, with the final button
  relabeled "Open in Workbench".
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
  from `book_prefs` (`quillas/core/audio_studio/book_prefs.py`) and persist
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
  executables (DECtalk, Piper, eSpeak), ffmpeg, and other optional components
  install through the shared component downloader into the shared data store.
- AS-49. Voice preview must always try to make sound: play the bundled
  pre-recorded sample when one ships; otherwise, if the engine is installed,
  synthesize the standard preview phrase live in the background; otherwise say
  "Download this voice to hear a preview." Every preview must speak the same
  phrase so before/after-download comparisons are direct.
- AS-50. Starting a new preview must supersede the old one: in-flight
  synthesis results are discarded by generation check and playback is cut.
- AS-51. Choosing "Export to audio" from the Speech Hub must open the Audio
  Studio wizard (documents journey).

### 4.8 AI features and Safe Mode

- AS-52. AI setup must run through the shared AI setup wizard (providers,
  keys, free-model paths). API keys must be stored in the Windows Credential
  Manager / DPAPI, never in plain settings files.
- AS-53. AI-powered features are exactly: chapter title proposals (AS-40),
  translated editions (AS-14), and cloud TTS voices (ElevenLabs and
  provider-backed voices). Each must be consent-gated and cost-surfaced where
  money is involved.
- AS-54. Translation must retry with bounded exponential backoff, cache
  repeated strings, and halt a language entirely on persistent failure rather
  than emit half-translated audio.
- AS-55. Safe Mode (`QUILL_SAFE_MODE=1` or `--safe-mode`, plus the shipped
  safe-mode launcher) must disable AI setup, AI chapter titles, and all
  publishing surfaces, each refusal announced in a plain sentence.

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
- AS-66. The tray icon must always be present, offering Open Audio Studio and
  "Resume: <most recent book>", both restoring the window first. Sending the
  app to the tray must announce that it is still running.
- AS-67. Alt+F4-to-tray, when enabled, must intercept before Windows closes
  the window so a long narration run keeps going; the titlebar X and Exit must
  keep the configured close action.
- AS-68. "Ask when work is running" must prompt only when protected work is
  actually running (listing the running jobs, defaulting to No/keep open); an
  idle window must just close. A second close during the prompt must not stack
  a second dialog.
- AS-69. On real exit the app must stop any preview, shut down the task
  manager without waiting, unregister media keys, and remove the tray icon.
- AS-70. Update checks must query the app's own GitHub releases
  (Community-Access/quill-audio-studio): manually from Help at any time, and
  automatically on launch only when enabled, only when due, deferred until
  after the window is up, and silent when there is no update.
- AS-71. Help must open the packaged User Guide, PRD, and Release Notes, and
  Report a Bug must submit through the shared feedback channel tagged with
  this app's name and version.
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
  `quillas/core/audio_studio/play_queue.py`: an ordered, editable list of
  books (add, remove, clear, set next) that persists to disk.
- AS-87. When the current book finishes and the Workbench is then closed,
  the shell must advance to the next queue entry whose file still exists,
  opening it in the Workbench and announcing the change; an empty queue or a
  missing next file ends playback quietly.
- AS-88. The Sleep Timer and Play Queue dialogs must expose an accessible
  name on every focusable control and route through the shared modal contract
  like every other Studio dialog.

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
  configured AI/cloud-TTS/translation calls (cost-confirmed when paid). No
  other outbound calls. Book building, chapter editing, ACX checks, local and
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
  quillas.apps.studio:main` (gui-script), package `quill-audio-studio`
  version 1.0.0, Python 3.12+.
- P-2. Release builds must be PyInstaller onedir (`QuillAudioStudio.exe`,
  windowed, no UPX), with the heavy ML runtimes (faster-whisper, vosk,
  kokoro-onnx, onnxruntime, torch) excluded from the bundle -- they install on
  demand into the shared engine-packs store.
- P-3. One onedir build must feed both artifacts: an Inno Setup installer
  (`QUILL-Audio-Studio-Setup-1.0.0.exe`, per-user default install, x64,
  Windows 10+, Start-menu and optional desktop shortcuts, packaged docs) and a
  portable zip (`QUILL-Audio-Studio-Portable-1.0.0.zip`).
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
- P-8. A safe-mode launcher (`run-quill-audio-studio-safe-mode.bat` /
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
- P-11. The Studio must ship in four editions:
  - Full portable (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`, roughly
    675 MB): fully self-contained, runs from a USB stick with no installation
    and no internet, bundling a genuine, unmodified copy of Python plus the
    offline speech and text-to-speech engines (whisper.cpp, DECtalk, eSpeak-NG,
    Piper, and neural Kokoro).
  - Companion edition (`QUILL-Audio-Studio-Companion-<version>.zip`, roughly
    2 to 3 MB): the app and its docs only, running on the shared QuillVille
    Runtime. On first launch, if the runtime is absent, it must offer to
    download and install it (about 230 MB, once) before running.
  - Full installer (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`): installs
    the shared runtime, if not already present, plus the app.
  - Thin installer (the `-Lite` setup): a small installer that downloads the
    shared runtime only if it is not already present, then installs the app.
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
- Direct platform publishing (WordPress and similar) -- deferred upstream to
  QUILL 2.0; when it lands there, it arrives here by vendor sync.
- A second pipeline. Any narration or assembly behavior that diverges from
  QUILL's Audio Studio is a bug, not a feature.

## 8. Future directions

- Watch-folder auto rebuild surfaced in the UI: `core/watch_audiobook.py` is
  vendored but has no Studio surface yet.
- Recognize `QuillAudioStudio.exe` in the shared portable-evidence check
  (`storage_mode._has_portable_evidence` currently lists only the other Quill
  app executables; the launcher's env export covers the gap today).
- A dedicated voice-casting manager (save and reuse named casting rule sets
  across projects, beyond the per-run rules on the Voices page).
- Toast/notification center: the runner already passes notification flags that
  the standalone host currently drops; a small notification surface would let
  finished overnight runs be reviewed later.

---

Change history lives in CHANGELOG.md. Upstream behavior of record: QUILL PRD
sections 5.25d (Batch Document-to-Speech) and 5.25e (Build Audiobook from
Folder / ChapterForge surface).
