# QUILL 0.7.0 Beta 2 Release Notes

Beta 2 is the release where QUILL really starts to *talk with you* — and listen.
You can now decide exactly how much QUILL says and when, transcribe and caption
audio entirely on your own computer, dictate and even run commands by voice
offline, save accessible talking books, and work through a real braille
proofreading workflow. Around those headline features sit a smoother upgrade, a
cleaner startup with no console window for both installed and portable copies,
stronger macOS and screen-reader support, and a long list of reliability fixes.

Everything new here follows the same promises: it is **optional**, it is
**screen-reader-first**, and your content stays **on your machine** unless you
explicitly choose otherwise. QUILL launches, edits, and saves with all of it
turned off.

## At a glance

- **Verbosity controls.** Choose how quiet or talkative QUILL is, per action,
  with Quiet and Meeting modes for shared rooms.
- **Private, offline speech.** Transcribe audio/video, make SRT/VTT captions,
  dictate into your document, and run commands by voice — all on-device, nothing
  uploaded.
- **DAISY talking-book export.** Save any document as a DAISY 2.02 text-only
  talking book for Victor Reader Stream, Plextalk, APH players, and DAISY apps.
- **Braille proofreading workflow.** Restore-your-place, a proofing tracker,
  layout validation, and selection-aware back-translation.
- **A smoother upgrade** that carries your compatible settings and shortcuts
  forward automatically, and a **cleaner startup** — no console window flashing,
  for both installed and portable copies.
- **Stronger macOS + screen-reader behavior**, and many crash, focus, and
  file-fidelity fixes.

---

## Control what QUILL says: the Verbosity system

QUILL now lets you decide how much it announces and when — from full, friendly
context for every action down to near silence — without fighting your screen
reader. Open **Verbosity Preferences** from the command palette
(`Ctrl+Shift+P`, then type "verbosity").

- **Four profiles.** Pick a level: **Beginner** (full context for everything),
  **Normal** (informative, the default), **Expert** (routine confirmations are
  suppressed, but errors always speak), or **Quiet** (speech and earcons off,
  leaving braille and the on-screen status bar). Switching profiles is announced
  so you hear the change.
- **Quiet Mode and Meeting Mode.** `QUILL key + Q` toggles Quiet Mode and
  `QUILL key + Shift + Q` toggles Meeting Mode for a call or a shared room. The
  status bar keeps updating, a `[Q]` or `[M]` indicator shows the mode, and
  `Ctrl+Shift+Z` undoes the last verbosity change.
- **Channels you control.** Speech, Braille, and Sound can each be turned on or
  off; the **Visual** status bar is always on and cannot be disabled, so you
  never lose the on-screen status of an action.
- **Make it say exactly what you want.** Advanced users can edit what each action
  announces using simple tokens like `{line}` and filters like `${ordinal:line}`,
  with live validation and a preview before you commit. Save wordings to a
  template **library**, **import/export** your setup as a file, or install a
  community **QUILL Verbosity Pack** — all data-only, never code.
- **Understand and tune it.** A **Preview Lab** lets you hear how a profile sounds
  against everyday scenarios; an **announcement History** lets you replay, copy,
  or ask **"why did QUILL say that?"**; and **Safe Mode** instantly restores the
  built-in announcements if a custom setup ever misbehaves — without deleting your
  work.

QUILL speaks *alongside* your screen reader, never instead of it, so it does not
duplicate the typing echo, speech rate, or punctuation level your screen reader
already controls.

## Speak and listen: private, offline speech

QUILL has a privacy-first speech engine that runs entirely on your computer,
under **Tools > Speech > Whisperer**. It needs **no AI account, key, or
provider** — you do not have to turn on Artificial Intelligence to use any of it
(that is why it no longer lives under the AI menu). The engine ships with QUILL
(choose the *offline
speech engine (whisper.cpp)* installer component, or drop it into
`tools\speech\whispercpp` in a portable copy) — no separate install, no PATH
editing. Then download a model from **Manage Speech Models** (sizes and
trade-offs are shown; the Small model is a good start; downloads come over a
secure connection and are disabled in Safe Mode).

### Manage models with confidence
**Manage Speech Models** now guides you to a model that fits your computer and
gets out of your way while it downloads.

- **Machine-aware guidance.** The dialog opens with a summary of your machine
  (RAM, and whether a GPU was found). Each model shows roughly how much memory it
  needs, flags models that are too big for your RAM, marks the best fit as
  **"Recommended for your computer,"** and warns when a large model has no GPU to
  accelerate it.
- **Downloads run in the background with a real percentage.** A download no longer
  freezes QUILL — it runs while you keep working, shows a percentage you can
  **Cancel** at any time (cancelling cleans up the partial file), and announces
  progress for screen-reader users. QUILL also warns about low disk space before
  starting.
- **Deleting a model is now obvious.** After you pick a model, choose **Download**
  or **Remove** explicitly, instead of the action being inferred for you.
- **A startup freeze is fixed.** Opening any Whisperer command no longer stalls
  the app while the optional Faster Whisper engine loads.
- **Open models, no account, nothing to accept.** The speech models QUILL offers
  are open-source (**MIT-licensed**) and free — there is **no Hugging Face account
  or sign-in required**, no license to click through, and no gated models. Each
  model shows its license and links its model card before anything downloads, and
  the files are stored only on your computer.
- **Verified, reproducible downloads.** Models are fetched from a pinned version
  and checked against a known checksum, so a silent re-upload can't change a model
  underneath you. (This also fixed the speaker-detection model, whose download
  link had gone stale — it works again.)
- **Optional token, with guidance, if you want higher limits.** A token is never
  required, but if you download many models and hit Hugging Face's rate limits you
  can add a free access token under **Tools > Speech > Whisperer > Hugging Face
  Token...**. First time, QUILL walks you through it — the steps to create a free
  "Read" token, with a one-click offer to open the Hugging Face token page in your
  browser — then you paste it (entered masked, stored in Windows Credential
  Manager, never in a settings file). A rate-limit error now points you here
  instead of showing a raw failure.

### Transcribe audio and video
**Transcribe Audio or Video (Offline)...** turns a recording into text on your
own machine — no cloud account, and your audio is never uploaded. Choose the
output format (**plain text, Markdown, or HTML**); it opens as an editable draft
while QUILL works in the background. With the speaker-detection model installed,
transcripts label **who is speaking when** ("Speaker 1", "Speaker 2", ...).

**Open almost any file.** QUILL now accepts a wide range of audio and video
formats — MP3, M4A, AAC, FLAC, OGG, Opus, WMA, WAV, MP4, M4V, MOV, MKV, WebM,
and AVI. When **ffmpeg** is available on your computer, QUILL converts the file
automatically before transcribing, so you no longer have to prepare a WAV first.
(Without ffmpeg, the offline Whisper engine still reads 16 kHz mono WAV files;
the Faster Whisper engine reads the other formats on its own.) QUILL does not
bundle ffmpeg, but it can fetch it for you: **Tools > Speech > Whisperer >
Download FFmpeg...** downloads the official build and sets it up — or install it
yourself once with `winget install Gyan.FFmpeg`.

### Captions
**Generate Captions (Offline)...** transcribes a file with timestamps and saves
it as **SRT** or **VTT** subtitles you can review and ship.

### Transcribe a whole folder automatically
Watch Folder automation can now transcribe for you. Point a watch profile at a
folder, choose the **Transcribe audio (Whisperer)** action, and every audio or
video file you drop in is transcribed **on your machine** and saved next to it —
nothing is uploaded. Pick the **Transcript format** per profile: plain **Text**,
**SubRip (.srt)**, **WebVTT (.vtt)**, or **Markdown**. The caption formats carry
timestamps and fall back to plain text when the engine returns no timed segments,
so you never get an empty caption file. If no speech model is installed yet, the
profile tells you where to get one. This automation always uses the on-device
engine — it never uploads your audio.

### Add a cloud transcription provider (optional)
Prefer a cloud service for its accuracy? You can now add one as an **extension**.
Install the bundled **OpenAI Whisper Transcription** Quillin and set an OpenAI API
key in AI Hub, and "OpenAI Whisper" appears as a provider in **Manage Speech
Models**. Cloud transcription is strictly **opt-in and never silent**: audio is
uploaded only when you explicitly transcribe a file with that provider, never
offline and never in Safe Mode — and the folder automation above never uses it.
Extensions that add a provider ship no code and request no network permission;
QUILL itself performs the upload through its audited network path, so the
extension never sees your audio or your key.

### Dictate into your document
**Dictate (Offline)** lets you speak directly into the editor. Press the command
(or `QUILL key + Shift + D`) to start — you hear a start tone and "Dictation
listening" in the status bar — then press again to stop; QUILL inserts what you
said at the cursor as a single undoable edit. **Dictation Microphone...** picks
which microphone to use.

### Run commands by voice (new)
**Voice Command (Offline)** lets you drive QUILL hands-free. Run it, say a
command — "save", "bold", "next heading", "word count", "command palette" — and
run it again to act. Recognition is on-device, and voice can only invoke a
curated, **safe set of commands**, so a misheard phrase can never trigger
something destructive. It is off by default (turn it on in Settings) and always
disabled in Safe Mode. Say "cancel" or "never mind" to dismiss without acting.

### Choose your engine
The bundled **whisper.cpp** engine needs nothing extra. On capable machines you
can opt into **Faster Whisper**, a higher-throughput engine that uses your **GPU**
when one is available, by installing QUILL's optional `fasterwhisper` dependency;
**Manage Speech Models** then offers a **Speech Engine** chooser, and your choice
is used for transcription, captions, and dictation. (For speaker labels, use the
whisper.cpp speaker-detection model.)

## Read and proof braille

Braille Mode gained a real proofreading and quality workflow, and it never
changes your braille file — progress and notes live in a small companion file
beside it.

- **QUILL remembers your place.** Reopen a `.brf`, `.brl`, `.pef`, or `.ueb`
  file and your cursor returns to where you left off, announced precisely — for
  example, "BRF file opened. 87 braille pages detected. Last position: braille
  page 12, line 14, cell 31."
- **Track proofreading.** A **Braille > Proofing** menu lets you mark a page
  proofed or needs-review, add notes, hear a spoken progress summary, jump to
  pages that still need work, and export a plain-text proofing report.
- **Validate layout.** A **Braille > Validation** menu flags common problems —
  over-long lines or pages, missing page breaks, mixed line endings, stray
  non-braille characters, malformed page indicators, numbering gaps, inconsistent
  running heads, and Unicode-vs-NABCC mismatches — then steps you through each
  finding with spoken position and detail. It only reads your file.
- **Recover source text.** **Braille > Translation > Back-Translate (draft)**
  back-translates a selected passage (or the whole file) to draft text, so you
  can check the source wording of a paragraph. Requires the optional QUILL
  Braille Pack.
- **Continuation pages read correctly.** Print-page continuation labels such as
  `7a` are now reported in full instead of being shortened to `7`.

## Save accessible talking books (DAISY)

**File > Export > DAISY Talking Book** saves your document as a **DAISY 2.02
text-only talking book** — the accessible format read by DAISY software and by
hardware players such as the Victor Reader Stream, Plextalk, and APH units.

- It exports what is on screen, so you do not have to save first.
- A DAISY book is a *folder* (the name you choose), holding the three files a
  player expects; QUILL asks before writing into a folder that already has files.
- Your headings become the player's navigation points; a document with no
  headings gets a title heading so navigation still works.
- The book is text-only, so a player reads it with its own text-to-speech — and
  because it is a standard DAISY book, you can open the folder in a tool like APH
  Book Wizard Producer to add recorded or synthesized audio later.

---

## Write in any language: Document Language and auto-detection

QUILL now lets a document be edited *as* a language even when its file name says
otherwise — so a plain `.txt`, an unsaved buffer, or a snippet you pasted can get
real HTML, Markdown, or code editing.

- **Set the language and get its characteristics.** **Ctrl+Shift+L** (also
  **Navigate > Set Document Language...**, the new **Format > Document Language**
  list, or Enter on the status-bar **Language** segment) pins a language for the
  current document. Once set, **Bold/Italic** insert the right markup,
  the heading/table/list/tag menu items light up, **comment toggling** uses that
  language's syntax, and heading navigation, the outline, link insertion, and
  live preview all follow it. The status bar shows **(set)** when you chose the
  language yourself. Recognised languages now include HTML, Markdown, CSS,
  Python, JavaScript, TypeScript, C, C++, **C#**, **PHP**, Go, Rust, Kotlin,
  Shell, YAML, JSON, TOML, and SQL.
- **It is an editing aid, not a rename.** Setting HTML on a `.txt` does not change
  the file; QUILL reminds you to use **Save As** to write it as `.html`. The
  choice is per-tab and resets when you close the file. **Auto-detect from file**
  clears the override.
- **Optional automatic detection (off by default).** Turn on **Settings >
  Editing > Auto-detect document language** to have QUILL recognise the language
  when you paste or type code into a plain `.txt`/untitled document. Choose how
  assertive it is: **Hint** (status bar only), **Suggest and announce** (you
  confirm), or **Switch automatically**. Detection is cautious — it acts only
  when confident, never guesses on ordinary prose, learns lightly from the
  languages you use, and **never** overrides a real extension or a language you
  set. Unlike editors that switch silently or show a visual-only hint, QUILL
  keeps a screen-reader user informed in every mode. Braille content is never
  affected — it has its own Braille Mode.

---

## A smoother upgrade

When you upgrade from QUILL 0.5.0 or Beta 1, QUILL checks your saved settings and
keyboard shortcuts as it starts and carries forward everything that still works.
If an older choice points at a command that no longer exists, has an empty
shortcut, or conflicts with another command, QUILL quietly drops just that entry
and uses the current default — so a feature never silently appears "broken."

- **Familiar shortcuts come back.** Bindings that drifted during 0.7.0
  development (for example `Ctrl+F` for Find, plus Send to System Tray, Read
  Aloud, and Dictation) are repaired automatically.
- **Your customizations are respected.** QUILL starts from the current defaults
  and layers your compatible changes on top; importing someone's profile brings
  in only their real customizations and leaves your unrelated shortcuts alone.
- **Nothing extra to run.** Beta 2 handles the common upgrade needs on its own. A
  fuller migration utility (for larger format changes, older-beta profiles and
  Quillins, and a reviewable record of what changed) is still planned.

## How QUILL starts: installer and portable

QUILL now starts the same clean way whether you used the **Windows installer** or
the **portable** edition: both run through `quill.exe`, a proper windowed
launcher. However you open QUILL — pressing Enter on the Start-menu or desktop
shortcut after an install, or opening `quill.exe` in a portable folder — you get
the same behaviour described here.

- **No more console window flashing at startup.** The old `run-quill.cmd` batch
  launcher is gone, replaced by the windowed `quill.exe`. That removes the brief
  black command window some people saw when QUILL started — for **both installed
  and portable** copies. Upgrading also replaces any old Start-menu or desktop
  shortcut that still pointed at the batch file, so the flash does not return.
- **Honest identity.** The launcher reports itself as **QUILL for All** with the
  real version and **Community Access** as the publisher, so a screen reader's
  "what is this window / what version" commands say something useful instead of
  "Python." On upgrade, a stale shortcut pointing at the old launcher is replaced.
- **Choose where QUILL stores your data.** A first-run **Where QUILL stores your
  data** page offers the recommended AppData location, a spot beside a portable
  bundle, or a folder you choose; change it later under **Preferences > General**
  and QUILL moves your data there safely on the next restart. A folder counts as
  portable only when it contains both `quill.exe` **and** a sibling `data/`
  folder — real evidence on disk, so a stray setting can never redirect where your
  work lives.
- **Zero-setup and backward-compatible.** New portable bundles ship an empty
  `data/` folder so they work from the first launch; older Beta 1 bundles that
  still include `run-quill.cmd` keep working. AI keys (DPAPI-encrypted) travel
  with a verified portable bundle automatically.

## Accessibility and screen-reader refinements

- **Setup starts on the heading**, and its text is readable. Each Setup Wizard
  page focuses its heading first, so you hear the page's purpose before its
  controls; the explanatory text sits in a **read-only field you can arrow
  through line by line**, exactly like the About window, for both Windows screen
  readers and VoiceOver; and the buttons read plainly as **Back** and **Next**
  (no "less than Back").
- **A cleaner first launch.** On a fresh install the Setup Wizard opens before any
  Untitled document, so a screen reader doesn't announce a stray tab first; a
  blank document is created after setup.
- **macOS / VoiceOver.** VoiceOver now identifies the editor as a real editable
  text area; the Report a Bug fields have proper names and the window is
  non-modal (switch back to your document while writing it); and the Help menu is
  recognized as the system Help menu (`Cmd+?` works).

## More natural keyboard behavior

- **Typing `R` or `S` types `R` or `S`.** Friendly single-letter shortcut hints
  no longer get mistaken for system shortcuts, so your letters stay in your
  document. Modifier shortcuts like `Ctrl+R` are unaffected.
- **macOS standards.** `Cmd+Q` quits; word movement (`Option+Left/Right`) works
  normally; Back/Forward Location use `Cmd+[` and `Cmd+]`. Quote/Unquote Lines
  moved to `Ctrl+Shift+Q` / `Ctrl+Shift+K`. Older bindings are repaired on
  startup.
- **Closing an unsaved document.** The prompt uses the standard Yes/No/Cancel:
  press `Y` to save, `N` to discard, or `Esc` to cancel — or Tab to the buttons.

## Opening and saving files faithfully

### Plain-text fidelity
- **No stray byte-order mark.** A UTF-8 BOM is kept out of the editable text (so
  it can't sit under your cursor or be read aloud) and re-added on save if the
  original had one.
- **Round-trip exactness.** Open and save and you get the same file back: Windows
  `CRLF` line endings stay `CRLF`, and runs of blank lines (and Markdown-looking
  lines) are preserved verbatim. Use **File > Save As Plain Text** when you
  *want* to flatten formatting.

### Simple File Open dialog
An opt-in, keyboard-friendly picker (turn on **Settings > General > Use simple
file open dialog**), reached from the same **File > Open...** / `Ctrl+O`:
folders first with a `[dir]` prefix, a small **Filter** dropdown, `Ctrl+L` to
focus the path, `Enter` to open or descend, `Backspace` to go up, `Ctrl+H` for
hidden files, a **Recent** popup, and a **Use Windows Dialog** button for the
native picker when you need it. Accessible error messages keep the dialog open so
you can fix a path and retry.

## Setup and AI Hub reliability

- The **Open AI Hub** button works on a brand-new profile, and the Hub's tabs,
  provider choices, instructions, and image styles all load correctly — from the
  Setup Wizard or the Tools menu.
- A new profile no longer triggers a startup typing failure.
- The Setup Wizard no longer reopens on every launch after an elevated install
  into a protected folder: QUILL remembers that setup is done even when it cannot
  delete the marker file.

## Stability and crash reporting

Several crashes and rough edges are fixed: **Check for Updates** and **Check for
GLOW Updates** open correctly; choosing **Don't Save** after `Ctrl+F4` no longer
crashes; closing the last document is safe from a late caret event; **saving
settings** (OK, Reset to Factory Defaults, or importing) applies theme,
spell-check, soft-wrap, and title-style cleanly; a Quillin reporting status no
longer crashes the app; the Developer Console reports the real document name;
**Quill Eraser** opens its review dialog correctly; and a fresh install with the
Setup Wizard pending no longer crashes on startup.

When an unexpected error does close QUILL, a new **crash-report dialog** (on by
default during the beta) shows a **redacted preview** of what would be sent —
recent commands, the document name and encoding, platform and screen-reader info,
and the last traceback frames, with personal data and credential-shaped strings
scrubbed first. You choose: **Send** (to the public issue tracker, only with a
configured token), **Copy to clipboard**, or **Don't send** (the default; Escape
triggers it). A local copy is always saved to your crash-reports folder, and you
can turn the dialog off in **Settings > General**.

Everyday housekeeping also improved: the User Guide and other static pages stay
put instead of refreshing every second (the live Browser Preview still follows
your edits); **Open Log Folder**, **View Startup Logs**, and **Open Diagnostics
Folder** use the right file manager per platform; the macOS app menu says **Hide
QUILL** / **Quit QUILL**; and macOS explains honestly that system-tray mode is
unavailable there rather than pretending to run.

## What is coming next

QUILL's roadmap is tracked openly, and every workstream is targeted to ship.
**Landed in this beta:** the verbosity system; the offline speech suite
(transcription, captions, dictation, speaker labels, voice commands, and the
optional Faster Whisper engine); DAISY talking-book export; and the braille
proofing, validation, restore-your-place, and back-translation workflow.

**Coming next:** broader publishing options (including direct publishing to
external platforms and chaptered audiobook export), a unified agentic AI hub, and
deeper accessibility-checking tools — all optional and screen-reader-first.

## What you need to do

For most people, nothing special:

1. Install or start QUILL 0.7.0 Beta 2.
2. Let QUILL check and carry forward your compatible settings at startup.
3. Keep working with your familiar files and preferences.

**Optional extras, only if you want them:**

- **Offline speech engine.** The on-device transcription engine (whisper.cpp)
  ships with the Windows installer — choose the *offline speech engine
  (whisper.cpp)* component during setup (it is included in a Full install). In a
  portable copy you can drop it into `tools\speech\whispercpp`. Then download a
  model from **Tools > Speech > Whisperer > Manage Speech Models**.
- **ffmpeg, for transcribing anything but WAV.** To transcribe or caption MP3,
  M4A, MP4, MOV, MKV, and other formats you need **ffmpeg**. The easiest way is
  **Tools > Speech > Whisperer > Download FFmpeg...**, which fetches the official
  build and sets it up for you; or install it yourself (for example,
  `winget install Gyan.FFmpeg`) and QUILL finds it on your PATH. QUILL does not
  bundle ffmpeg — it uses the copy on your computer — so without it the offline
  engine reads only 16 kHz mono WAV files. No ffmpeg is needed for typing,
  editing, or
  any non-speech feature.
- **Faster Whisper (advanced, GPU).** On capable machines you can install the
  optional `faster-whisper` package to add a higher-throughput engine; QUILL then
  offers a Speech Engine chooser.

None of these are required to launch, edit, or save — QUILL runs fully without
them.

**Installing from source (developers).** If you install with `pip` rather than the
Windows installer and the on-device AI extra, note that `llama-cpp-python` has
prebuilt CPU wheels but no Windows wheel on PyPI itself. If `pip` starts a slow
source build, force the wheel with `pip install --only-binary=llama-cpp-python ...`
(QUILL's requirements already point at the CPU wheel index). Installer users are
unaffected.

You should not need to edit `keymap.json` or rebuild your preferences by hand.
Because this is a beta, please keep telling us anything that feels confusing,
inaccessible, unreliable, or harder than it should be — your feedback shapes what
ships next.
