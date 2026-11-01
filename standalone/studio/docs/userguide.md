# QUILL Studio User Guide

Version 2.0.0

## Upcoming Preferences Search

Preferences gains **Find a setting** in the next maintenance update. Type a
term from a setting's label or help, press Down for matching settings, then Enter
to focus one. Control+F returns to search; Escape clears a search before closing.
Search navigates only: OK still saves, Cancel still cancels, and values are not
indexed. Disabled settings stay disabled.

(QUILL Studio 2.0.0 follows Audio Studio 1.0.0. The previously unpublished 2.2.0 build is renumbered for this release.)

QUILL Studio is audiobook and audio production the way a screen reader user would design it: a small home window with a menu bar, a wizard that asks one question at a time and announces every step, a chapter editor you drive entirely by ear, and spoken progress for every long run. It runs the exact same Audio Studio code that ships inside the QUILL editor and shares QUILL's data store, so a voice you configure here reads aloud in QUILL too, and nothing you set up is ever stranded.

Three journeys cover the whole workshop:

- **Narrate Documents** - point at a folder of Word, Markdown, HTML, or text files and get speech audio, or one chaptered audiobook.
- **Build From Recordings** - point at a folder of audio you already recorded and get one chaptered master, each file a chapter.
- **Edit a Book** - open any finished MP3 or M4B in the Chapter Workbench: listen, fix chapters by ear, edit tags, run the ACX check, publish.

## Installing and running

### The QuillVille Runtime: install Python once, use it everywhere

Every QuillVille app - QUILL, Quill Radio, Quill Weather, and QUILL Studio - now shares one Python runtime, called the **QuillVille Runtime**. It is installed once per user and reused by all of them. Install it a single time (with any Quill app), and every app you add afterward launches instantly, because the shared runtime is already there.

The runtime is reference-counted: it is removed only when the last app that needs it is uninstalled, so removing one app never leaves the others unable to start.

The Studio comes as two downloads. Pick the one that fits how you work:

- **Installer** (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`) - installs the shared runtime, if it is not already present, plus the app. See "The installer" below.
- **Portable** (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`, about 675 MB) - fully self-contained. It runs from a USB stick with no installation and no internet, carrying a genuine, unmodified copy of Python plus bundled offline speech and text-to-speech engines (whisper.cpp, eSpeak-NG, Piper, and neural Kokoro). DECtalk is not distributed with QUILL.

Earlier test builds also came as a small "Lite" installer and a "Companion" zip. Those are gone. If you have one, take the installer in place of the Lite installer, or the portable zip in place of the Companion zip. Help > Check for Updates offers the right one for you.

### The installer

Run the installer (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`). It makes sure the shared QuillVille Runtime is present (installing it only if it is not) and then installs the Studio to its own folder with a Start Menu group (including a User Guide shortcut) and an uninstaller. Your data lives in the shared Quill store in your Windows profile (`%APPDATA%\Quill`), the same store QUILL, Quill Radio, and QUILL Cast use. Uninstalling never deletes that shared data, and never removes the shared runtime while another Quill app still needs it.

Windows SmartScreen may warn on first run because this release is not code-signed; choose "More info" then "Run anyway".

### The portable zip

Extract the full portable zip (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`) anywhere - even a USB stick - and run `QuillAudioStudio\QuillAudioStudio.exe`. This edition needs no runtime download: it bundles its own genuine, unmodified copy of Python and the offline speech engines, so it runs with no installation and no internet. The portable switch is a `data` folder next to the exe that contains a `storage-mode.json` marker file holding `{"mode": "portable"}`. When that folder and marker are present, all settings, voices, downloaded engines, and your book list live inside the app folder, so the whole studio travels with you. The portable zip ships this marker already in place; the installed copy ships no `data` folder and uses the shared `%APPDATA%\Quill` store instead.

Both packaged flavors bundle ffmpeg and the mpv player engine in a `tools` folder next to the exe, so audiobook building and high-fidelity playback work out of the box.

### Downloading the QuillVille Runtime

The installer and the portable zip both carry everything the Studio needs, so you should never see this. If the shared runtime has gone missing from an installed copy - removed by hand, say - the Studio offers to download it again, about 230 MB, one time. This download always shows a **fully accessible progress bar** that works with NVDA, JAWS, and Narrator, whether the download was triggered by the installer or by the app's own first launch. Progress is announced as a percentage, so you always know how far along it is and never face a silent wait. Once the runtime is installed, this app and every other QuillVille app start instantly, and you are never asked to download it again unless every Quill app has been removed.

### A note on antivirus

The Studio's launcher is now a genuine, tiny native program, and the bundled Python is the official unmodified build. Earlier versions used a renamed and modified copy of Python's `pythonw.exe` as the launcher, which some antivirus tools flagged as a false positive. That pattern is completely gone, so the Quill apps are far less likely to be flagged. If an antivirus tool ever does flag a Quill app, it is a false positive; the downloads come from the project's official releases.

### Running from source

From a checkout of the repository:

- `pip install -e ".[ui]"` then `python -m quill.apps.studio`, or
- run `run-quill-studio.bat`, which finds a Python environment for you (this repo's `.venv`, then a sibling QUILL checkout's `.venv`, then whatever `python` is on PATH).

`run-quill-studio-safe-mode.bat` launches with Safe Mode on (see "Safe Mode" below).

## The home window

The Studio opens as a plain window with a menu bar. Most work happens in modal
surfaces (the Studio Wizard, the Chapter Workbench, and focused dialogs),
which you launch from the menus. The home window stays intentionally quiet
so your books are not front-and-center unless you choose to open one.

From top to bottom:

- **Studio activity** (read-only text): what the Studio is doing right now — "Ready", or live progress during a run.
- **Status bar** (optional): an arrow-navigable summary you can reach with **F6**.

Start points:

- **Studio > Open Studio Wizard...** (Ctrl+N) to narrate documents, build from recordings, edit a book, or start a screenshot capture.
- **Capture** menu for screenshots, inspector, and global hotkeys (AI is not required).

### The status bar

The status bar reads "Ready - use the menu bar to begin" when idle. During a long run it carries per-file progress, and by default the Studio also speaks the 25, 50, and 75 percent milestones so you can follow an overnight narration from another window (turn this off in Preferences).

You can read the bar rather than wait for it to speak. Press **F6** to move focus into it, then **Left** and **Right** to move between its cells:

- **Activity** - what the Studio is doing right now.
- **Progress** - a live narration or build run: the percentage, how many files are done, and the current step.
- **Sleep timer** - the timer's state, when one is set.
- **Your books** - how many books are in your library (informational; the home window does not show a book list by default).
- **Time** - the current time.

Press **Enter** to act on the cell you are on, use the context menu (Application key, or Shift+F10) for what that cell offers, and press **Escape** or F6 again to leave the bar and return to the window. **View > Show Status Bar** hides or shows it, and the Studio remembers your choice.

The Progress text is also written into the system-tray tooltip, so a long run is still reviewable when the window is minimized to the tray.

### The library window

The home window does not show your books by default. Open **View > Library Window...** (Ctrl+Alt+Y) to browse your library in a dedicated window.

The library fills in as you work: every book you open in the Chapter Workbench joins it, and you can shape it yourself with Favorites and folders. Books are grouped into four built-in collections and any folders you create:

- **Favorites** - books you have marked as a favorite.
- **In Progress** - books with a saved listening position you have not finished.
- **Recently Played** - the books you have opened most recently.
- **Inbox** - everything else.

In the Library Window, expand and collapse the groups with Left and Right. Press **Enter** on a book to open it in the Chapter Workbench. The context menu (Application key, or Shift+F10) is keyboard-complete on both books and folders: **Open**, **Reveal in Folder**, **Favorite** (toggle), **Move to Folder**, **New Folder**, and **Remove**. **Reveal in Folder** opens your operating system's file manager (Windows File Explorer, or the macOS Finder) with the book file selected, so you can find it on disk. **Remove** takes the book out of your library but never touches the file on disk, and says so. The tree remembers which book you had selected when the library reloads.

## The Studio wizard

**Studio > Open Studio Wizard...** (Ctrl+N) opens the wizard. Its first page asks the one question that matters - what would you like to make? - and the following steps adapt to your answer. The wizard remembers which journey you used last and pre-selects it.

Wizard mechanics, the same on every page:

- Every page change is announced: "Step 2 of 7: What should I read?".
- **Back** and **Next** move between steps. Each page validates before you leave it, with a plain-language message if something is missing.
- **Skip to summary** fast-forwards past pages that are already complete - a repeat run with saved settings is a few keystrokes. If a page objects, the wizard stops there and tells you why.
- **Start** on the summary page begins the run. In the Edit journey the button reads **Open in Workbench** instead.
- **Load a job file...** on the first page re-opens the wizard pre-filled from a saved `.quilljob` (see "Job files").

The menu items **Narrate Documents...**, **Build From Recordings...**, and **Edit a Book...** are shortcuts into the same wizard (Edit a Book goes straight to a file picker and then the Workbench).

## Journey 1: Narrate Documents

Seven steps: Start, What should I read?, Who should read it?, How should chapters work?, Output and diagnostics, Tell me about the book, Review and start.

### What should I read?

- **Source folder** - a combo box seeded with your recent source folders, plus a **Browse...** button. **Include subfolders** widens discovery.
- **File types to include** - Word (`.docx`), Markdown (`.md`), HTML (`.html`, `.htm`), plain text (`.txt`). Check any combination.
- **Include / Exclude files matching** - optional glob filters, semicolon- or comma-separated.
- **Skip files larger than (MB)** - a size cap so one accidental 400 MB export cannot hijack a run (0 = no limit).
- **Count documents** - counts the matching files and their words off-thread and announces the settled number: "12 document(s) found, about 84,000 words." The count also refreshes automatically when you browse to a folder or arrive on the page.

### Who should read it?

- **Engine** - Windows (SAPI 5), DECtalk, Piper (neural, offline), Kokoro (neural, offline), eSpeak-NG (many languages); on a Mac, the macOS system voice as well. An engine that is not installed yet is labeled "(not installed)" - see "Voices" below. DECtalk must be installed separately.
- **Voice** and **Preview voice** - hear the chosen voice before committing. Previews play a bundled sample when one ships, or synthesize live with the real engine when it is installed.
- **Rate (WPM)** and **Kokoro speed** - pace controls.
- **Round-robin voices** (optional) - build an ordered rotation; article 1 gets voice 1, article 2 voice 2, wrapping around. **Add voice**, **Move Up**, **Move Down**, **Remove**. The rotation uses voices of the selected engine; switching engines clears it.
- **Voice casting** (optional) - explicit assignment layered over the rotation. Add a rule: a pattern plus the voice that should read every matching chapter. Patterns match the heading title as a glob (`Chapter *`, `*interview*`) or a section number (`#1` for the opener). The first matching rule wins; unmatched chapters fall through to the rotation or the single voice. This is how dialogue-heavy fiction gets cast deliberately.
- **Also export in other languages (translated)** - add language + voice pairs to produce translated editions alongside the original. Voices are offered local-first (eSpeak, installed system voices), then the premium multilingual cloud voices (OpenAI, Gemini, ElevenLabs), which need the matching provider API key at run time. Choose **Translate with**: your configured AI provider (cloud) or LibreTranslate (local).

### How should chapters work?

- **Chapter mode** - one single chaptered file, or a separate file per article.
- **Chapters start at heading level** - every heading, level 1 only, levels 1-2, or levels 1-3; deeper headings fold into the chapter above. **Preview chapter titles** lists the first twenty titles this choice would carve from your actual documents, so you can tune the level before synthesizing anything.
- **Speak each heading aloud**, **Combine empty headings into the next article** (a "Part One" heading with no body joins the next chapter's title instead of becoming an empty chapter).
- **Play a transition sounder between headings** with its own volume, plus configurable pauses between articles and sentences and an anti-clipping trailing pad per section.

### Output and diagnostics

- **Output format** - MP3 (with chapter markers), M4B audiobook (native chapters), or WAV. MP3 lands next to the document it came from; WAV, which produces much larger files, goes into an **Audio Output** subfolder beside the document instead, and a recursive run through nested folders gives each subfolder its own.
- **If an audio file already exists** - Skip (a cheap resume), Overwrite, or Rename (keep both).
- **Normalize loudness to audiobook (ACX) level** - re-level every file to audiobook loudness.
- **Reuse unchanged audio from the last run** (on by default) - the incremental rebuild. The Studio fingerprints each document's text plus every audio-shaping setting; on a re-run, only what changed is re-synthesized. Draft with a fast voice, then swap in your best voice for the final pass and everything rebuilds automatically.
- **Dry run** - write a preview text file of exactly what would be spoken, without synthesizing. Proofread before paying for slow synthesis.
- **Save the text sent to speech** - one sidecar per document.
- **Audition** - convert only the first document, so you can judge voice, pace, and mastering in minutes before an overnight run.
- **Temporary files folder** - blank uses the system temp.

### Tell me about the book

- **Assemble the results into one audiobook** - optional in this journey (leave it off for plain speech-audio files).
- **Book title, Author, Narrator, Genre, Year** - the tags that travel with the book in every player.
- **Look up book details...** - type the title and the Studio searches Open Library and MusicBrainz (free public catalogs; it asks before the first contact, and only the title and author you typed are sent). The match you pick fills author, genre, and year, and if it has a cover image you are offered a `cover.jpg` download next to your audio.
- **Cover image** - auto-detected from the folder, or browse to one.
- **Book format** - M4B (native chapters) or MP3 (chapter markers).
- **Normalize the book to ACX (Audible) loudness**, **fade in / fade out** per chapter, and **book tempo** (pitch-preserving).
- **Add spoken opening and closing credits** - the book introduces itself ("Title. Written by... Narrated by...") in the run's own voice.
- **Review chapters before building** - pause after synthesis to rename, reorder, or merge chapters before the master is assembled.
- **Save the book as** - blank saves next to the sources.

### Review and start

The summary reads every choice back in plain sentences; press **Back** to change any of it. **Save a job file...** pins this exact run to a portable `.quilljob` (see "Job files"). Press **Start** and the run begins in the background: per-file progress in the status bar, spoken milestones at 25, 50, and 75 percent, and the finished book lands in Your books. **Cancel** (or Escape) stops a run cleanly - the file being synthesized right now finishes first, so you are never left with a half-written audio file, and nothing new is started after it. The diagnostics log records the same chunk-by-chunk detail the progress dialog shows, so reading the log after a run tells you as much as watching it did.

## Journey 2: Build From Recordings

Four steps: Start, Where are the recordings?, Tell me about the book, Review and start.

- **Folder of audio files** - MP3, M4A/M4B, WAV, FLAC, Opus, and OGG files are accepted. Each file becomes one chapter, in natural filename order, with the title taken from the file name. Files that look like previous builds are set aside automatically.
- **Include subfolders** widens discovery.
- **Library mode** - every subfolder becomes its own audiobook, titled after the folder, built unattended in one run. Point it at a folder of book folders and come back to a shelf of masters.
- **Trim leading and trailing silence from each recording** - per-file polish before the merge.
- The book page is the same as in the documents journey (tags, cover, lookup, M4B or MP3, ACX loudness, fades, tempo), except assembly is always on and spoken credits are not offered (there is no narration voice to speak them).
- Outside library mode you always **review the chapter list before the book is built**: rename, reorder, merge, remove, or import titles, then confirm the merge.

## Journey 3: The Chapter Workbench

Open a book three ways: **Edit a Book...** (a file picker), **Studio > Open Book File...** (Ctrl+O), or press **Enter** on a book in Your books. A chaptered MP3, M4B, or M4A opens with its chapters; a file with no chapter markers opens as one big chapter, ready to carve.

### Chapters for a lecture, a meeting or any recording

The Workbench is not only for audiobooks. **Studio > Find Chapters in a Recording...** (**Ctrl+Shift+R**) asks for any MP3, M4A or M4B -- a two-hour lecture, a recorded meeting, a talk somebody sent you -- opens the Workbench on it, and starts **Propose chapters from silences** straight away.

1. Pick the recording and press Open.
2. Choose how quiet counts as silence (-30 decibels suits most speech; -40 a noisy room) and how long a pause must last (0.8 seconds catches a speaker drawing breath between topics; 2 or 3 seconds only the real breaks), and press OK.
3. The scan runs in the background; you can keep listening. Each new chapter starts in the middle of a silence and is titled **Proposed chapter 1**, **Proposed chapter 2** and so on, so a guess never passes for a name somebody chose.
4. Review them: Enter plays one, **Hear boundary** plays the moments around its start, **Set start to playhead**, **Split at playhead** and the nudge buttons move a boundary, **Merge into previous** removes one, and **Rename** names it.
5. **Save** writes the chapters (an MP3 in place, touching only its tags; an M4B as a new file), or **Export chapters...** writes a chapter file. Open the recording again and the chapters are there.

If the recording already has chapters of its own, you are asked first: **Keep mine, add proposals** (the default) keeps every chapter you had and adds a proposed one only where a silence is at least ten seconds from yours; **Replace with the proposal** swaps the list; Cancel changes nothing. While the scan runs the button reads **Stop proposing chapters**; press it, or close the Workbench, and the list stays exactly as it was. **Restore original** takes back a whole proposal. A long recording is given time in proportion to its length, so an all-day recording is scanned to the end. FFmpeg is needed; without it you are told so.

**Sleep Timer** (Ctrl+Shift+T) and **Play Queue** (Ctrl+Shift+Q) now work inside the Workbench too, so you can set one while a book plays there.

### The chapter list

Each row reads in full: "3. The Long Road - starts 1:02:03, runs 12:40". Press **Enter** on a chapter to hear it. Selecting a chapter loads its title into the **Chapter title** field - type a new one and press Enter (or the **Rename** button).

### The player

The built-in player anchors everything. All controls are buttons with access keys, fully reachable with Tab and screen-reader-friendly:

- **Play / Pause** (one button whose label follows the state) and **Stop**.
- **Previous chapter** and **Next chapter** - within the first three seconds of a chapter, Previous means the one before.
- **Rewind** and **Forward** - ten-second skips, position spoken after each.
- **Where am I?** - the full audible glance: "Chapter 4 of 24: The Long Road. 3:12 into the chapter, 9:28 left in it. 1:02:03 of 7:41:00 in the book, 6:38:57 remaining."
- **Speed** - 0.75x to 2x, pitch preserved.
- A **Position** slider that speaks human time, and a **Volume** slider.
- A **Mute** button (and **Ctrl+M** from the shell) - caches your current volume, drops to zero while muted, and restores it when you unmute. The button label follows the state and the change is announced.
- The current chapter is announced as playback crosses into it, and the player **remembers where you stopped** in each book and resumes there next time.

The player also **remembers your volume and mute choice per book** - turn one book down to 40% and mute another, close them, and each reopens at the level you left it.

Playback uses the bundled mpv engine when it is available (gapless audio, exact seeking, instant chapter jumps even on eight-hour books) and quietly falls back to the Windows media engine when it is not - a broken engine can never take playback away.

While a Workbench is open, your **media keys** drive the active player: Play/Pause, Stop, Next chapter, and Previous chapter work from any window. With no Workbench open they are silent. (Media keys are a Windows feature.)

#### Which way the slider keys go (Slider Keys)

On the **Volume** slider, the arrow keys follow the family's **Slider Keys** choice, made in **Preferences** (Ctrl+Comma) with the **Slider Keys...** button:

- **Up is more** (the default): Up, Page Up and Home raise the volume, and Home is the top, 100 percent. Down, Page Down and End lower it, and End is 0.
- **As Windows sliders**: the keys of a standard Windows slider. Down, Page Down and End raise it (End is 100 percent); Up, Page Up and Home lower it (Home is 0).

Right is always more and Left always less. It is one choice for every Quill app with a volume slider -- QUILL Studio, Quill Radio, QUILL Cast and Quill Media Player -- so changing it here changes it there at the next key press. Each key press also tells your screen reader the new value. Ctrl+Up and Ctrl+Down, the volume keys that work from anywhere in the apps that have them, are not changed.

### Chapter surgery

All by ear:

1. Play until you hear where a boundary belongs, and pause there.
2. **Split at playhead** - the chapter is cut in two exactly at the playhead. This is the fix for a book whose chapters landed in the wrong places.
3. **Set start to playhead** - retime an existing boundary: select the chapter, park the playhead where it should start, press. The timeline always stays contiguous.
4. **Merge into previous** and **Restore original** (one press undoes every edit) round it out.

### Analysis helpers

Both propose, never impose - proposals land in the list for review, and **Restore original** undoes them.

- **Propose chapters from silences...** - scans the recording with ffmpeg for silences and proposes boundaries at the silence midpoints. A small dialog asks for the noise threshold (dB, default -30) and minimum silence length (seconds, default 0.8). The one-long-recording story is complete: open a single 80-minute file, press one button, review, save.
- **Propose AI titles...** - names a folder of "track07"-style chapters by listening to them. The opening minute of each chapter is transcribed on your machine by the local speech model (the audio never leaves your computer); only that text goes to your configured AI, which proposes a short title per chapter. Needs a configured AI (AI > Set Up AI...) and is unavailable in Safe Mode. The Studio asks before starting and tells you exactly what will be sent.
- **Check against ACX** - measures the book against Audible's ACX submission window (integrated loudness, true peak, noise floor) and shows a verdict dialog with a plain-language recommendation for each failing criterion. The verdict is also announced, so you hear it even if you dismiss the dialog with Escape.

### Import, export, and split

- **Import chapters...** replaces the whole list from Audacity labels, a CUE sheet, timestamp lines, Podcasting 2.0 JSON, or CSV.
- **Export chapters...** writes the list in any of the same five formats.
- **Split into files...** goes the other way: one audio file per chapter into a folder you pick - instant podcast episodes, or tracks for players without chapter support.

### Book details and saving

Title (album), author, narrator, genre, and year are edited right in the dialog.

Saving is honest about physics:

- An **MP3** saves **in place** with **Save** - only the tags are rewritten; the audio is untouched. **Save As...** writes an edited copy instead.
- An **M4B** cannot be rewritten in place; the Save button is disabled and **Save As...** performs a lossless re-mux (no re-encode, no quality loss) into a new file.

Long saves run in the background so the window stays responsive.

### Publish...

Opens the Publish dialog for this book - save your chapter edits first. See "Publishing" below.

## Voices

### Engines

- **Windows (SAPI 5)** - every voice installed on your PC, in any language; zero downloads.
- **DECtalk** - the classic formant synthesizer, usable if you have installed it separately. QUILL does not distribute it or its preview samples.
- **Piper** - neural voices that run entirely offline; download individual voices from a catalog.
- **Kokoro** - modern neural voices, entirely on your machine, in several languages; a one-time model download.
- **eSpeak-NG** - compact and fast, speaks a very large number of languages.
- **macOS (system voice)** - on a Mac, the system `say` voices.
- **Cloud voices** - ElevenLabs on the Speech Hub's online tab, and OpenAI / Gemini / ElevenLabs multilingual voices as translation-target voices. All require your own API key and are never used without it.

### The Speech Hub

**Voices > Speech Hub (Voices and Engines)...** (Ctrl+Shift+H) is the one place to see and set everything: offline voices on one tab, cloud voices on another, and the speech-recognition (dictation/transcription) engines and models alongside. Pick an engine and voice, adjust rate, volume, or speed, preview, and **Set as Default**. Voices you configure here are shared with QUILL - and the hub's "export to audio" action opens the Studio Wizard, because in this app that is what export means.

### Pronunciation dictionaries

**Voices > Pronunciation Dictionaries...** opens the same manager QUILL uses to teach the speech engines how to say tricky words - names, acronyms, invented terms. Each entry maps what is written to how it should be spoken, and dictionaries apply as a silent text transform to both narration runs and live Read Aloud. Because this is shared QUILL data, a correction you make here is honoured everywhere the shared store is used.

### Voice previews

Every preview speaks the same standard phrase, so voices are directly comparable. When a bundled sample ships for a voice, the preview plays instantly - even before the engine is downloaded. When no sample ships but the engine is installed, the Studio synthesizes the phrase live with the real voice; if that synthesis is taking a moment, you hear "Generating preview, please wait" so silence never leaves you guessing. If neither a sample nor an installed engine is available, the status line says "Download this voice to hear a preview." Starting a new preview always stops the previous one; previews never overlap.

### Generate captions from audio or video

**Voices > Generate Captions (Offline)...** transcribes an audio or video file into a `.srt` or `.vtt` caption file entirely on your own machine - nothing is uploaded. Point it at a recording, a finished chapter, or a video, and it writes captions alongside. Press **Ctrl+Shift+C** to start it. It uses the same speech-recognition engine and models as the Studio's other transcription work, so if no model is installed yet it offers to open Manage Speech Models first. The next section explains the engines and walks through an example.

### Speech recognition: the engines that listen

Narration is the Studio speaking. A few features need the opposite: the Studio listening to a recording and writing down what was said. Two features do that, both on your own computer: **Generate Captions (Offline)** (Ctrl+Shift+C), and the Workbench's **Propose AI titles...**, which writes down the first minute of each chapter. The Studio has no dictation and no voice commands; for typing by voice, use QUILL Transcribe.

The listening is done by a speech-recognition engine and a model, which is the file of speech knowledge the engine uses. There are three engines to choose from:

- **Whisper.cpp** - the recommended default: light and fast, and works on any computer. The engine is a small download (about 8 MB) from QUILL's own verified release, fetched the first time you need it if your copy does not have it yet. Its models then download in Manage Speech Models: Tiny (75 MB), Base (145 MB), Small (465 MB, a good place to start), a Small English model that can tell speakers apart, and larger ones. Bigger models make fewer mistakes and take longer.
- **QUILL speech models (Parakeet, Nemotron and more)** - the same models QUILL Transcribe, QUILL Lite and QUILL's live dictation use. A model you downloaded for any of them is already here, and is never downloaded twice. NVIDIA Parakeet understands 25 European languages and never invents text from silence, which matters on a long recording with pauses.
- **Faster Whisper** - the most accurate, a larger download that uses more memory, and the only engine that can use a graphics card. It installs on demand, and is offered only where this copy of the Studio can install it.

Every engine keeps the audio on your computer. Nothing is uploaded, and the Studio does not use online speech services for captions. Vosk, an engine older guides mentioned, is no longer offered for speech recognition.

#### Choosing an engine and downloading a model

1. Press **Ctrl+Shift+M** (Voices > Manage Speech Models...). It opens the Speech Hub on its offline speech-recognition tab.
2. Choose an engine, then a model. Each model row says its size and what it can do, such as "detects the spoken language; never invents text from silence", before you download anything.
3. Download it. Progress is announced, and Cancel works.

If you would rather be walked through it, **Voices > Download Optional Components...** (Ctrl+Alt+Shift+D) has a row called **Dictation (offline speech)**. Choose it and you are offered the three engines in the order above, recommended first, then a model. **Test** on that row proves the engine works once it is installed.

The Studio shares its speech settings with QUILL, so an engine you choose in either one is used by both. If the engine you chose is not ready, the Studio uses Whisper.cpp instead, so captions still work.

#### Example: captions for a finished chapter

1. Press **Ctrl+Shift+C** (Voices > Generate Captions (Offline)...).
2. If no model is installed yet, the Studio asks "No offline speech model is installed yet. Open Manage Speech Models to download one?" Choose Yes, download Whisper.cpp's Small model, close the window, and press Ctrl+Shift+C again.
3. Choose the audio or video file, such as chapter 3 of your book.
4. Wait while it works. The Studio tells you how it is getting on, and says when it has finished.
5. Choose the caption format, **SubRip captions (.srt)** or **WebVTT captions (.vtt)**, then choose where to save. The file is named after the recording to begin with.

#### Limits

- Generate Captions and model downloads are off in Safe Mode.
- The audio never leaves your computer. For Propose AI titles, the written-down text of each chapter's opening is sent to the AI you set up, and the Studio asks first.
- Speech recognition makes mistakes, more of them with music, noise or several people talking at once. Read the captions through before you publish them.

### Convert audio between formats

**Voices > Convert Audio...** changes audio files between formats and pulls the audio track out of video files. It uses the ffmpeg the Studio already bundles, so there is nothing extra to install, nothing leaves your machine, and it works in Safe Mode.

- **Build a queue.** Add individual files, whole folders, or both. Delete removes the row you are on, and each row says in words what will happen to it.
- **Pick a format and a preset.** Output formats include MP3, M4A/M4B, Opus, Ogg, FLAC, WAV, and AAC; sources can be MP3, WAV, FLAC, Ogg, Opus, M4A/M4B, AAC, WMA, AIFF, and more, plus MP4, MKV, MOV, WebM, AVI and other video containers. The list only ever offers formats your ffmpeg can genuinely encode, so a long batch cannot fail half way for a missing encoder. Ten presets cover the usual jobs: Just convert (no processing), MP3 at 320, 192 or 128 kbps, Podcast, Audiobook (M4B), Voice memo, Web voice (Opus), Archival (FLAC, lossless), and Hearing-aid mono.
- **Choose what happens to existing files** - Rename (auto-number, never overwrites), Skip, or Overwrite.
- **Advanced processing**, all off or neutral unless you ask for it: loudness normalization to audiobook (ACX, -20 LUFS) or podcast and streaming level (-16 LUFS), gain, a high-pass filter, silence trimming, pitch-preserving tempo, a compressor, a night-mode leveler, fade in and fade out, and a safety limiter.

The run happens in the background with several files at once, so the window stays responsive, and **Cancel** works. Progress appears in the status bar's Progress cell and the tray tooltip, and the spoken summary at the end **names any files that failed** rather than reporting success for all of them.

**Voices > Convert from URL...** takes a link - YouTube and the many other sites the downloader supports - fetches its audio, and hands it to the converter. The downloader is not bundled: the first time you use this, the Studio explains what it is about to install and asks, and it reminds you that you are responsible for having the right to the audio you download. Unavailable in Safe Mode.

### Downloading voices, engines, and components

Everything heavy downloads on demand, with progress and a working Cancel:

- The Speech Hub offers **Download Voice** for Piper voices and the Kokoro model pack, and engine downloads for Piper and eSpeak-NG right where you would use them. DECtalk must be installed separately.
- **Voices > Manage Speech Models...** (Ctrl+Shift+M) manages the speech-recognition engines and models used by Generate Captions and AI chapter titles: Whisper.cpp, the QUILL speech models and Faster Whisper. See "Speech recognition: the engines that listen" above.
- **Voices > Download Optional Components...** (Ctrl+Alt+Shift+D) is the hub for everything else: see what is installed versus available, download, **Test** it in place, or **Remove** it. The audio pack here bundles the mpv player engine and ffmpeg in one download.
- **Voices > Get FFmpeg...** is the safety net for ffmpeg alone - the tool behind compressed formats, audiobook assembly, loudness measurement, and silence detection. Both packaged flavors already bundle it.

If a component install fails, the Studio offers to **save a diagnostics bundle** - a small, redacted zip you can send to support so the failure can be read without exposing anything private.

All downloads are disabled in Safe Mode.

## AI features

### Set Up AI

**AI > Set Up AI...** runs a short, jargon-free wizard: choose how AI should run - a cloud provider with your own key (paste it, test it) or a local model via Ollama (nothing leaves your machine) - and you land ready to go. Nothing is applied until you confirm, and you can cancel at any point with nothing lost.

One configured provider powers three things in this app:

- **AI chapter titles** - the Workbench's "Propose AI titles..." (local transcription first; only text goes to the AI).
- **Translated editions** - "Translate with: AI provider" on the voices page. LibreTranslate remains the local, no-AI alternative.
- **Cloud narration voices** - the OpenAI / Gemini / ElevenLabs voices offered as translation targets, each using its provider's key.

All AI features are unavailable in Safe Mode.

## Publishing

### Publish a Finished Book

**Book Tools > Publish a Finished Book...** asks for the book file (pre-selecting the book highlighted in Your books) and opens the Publish dialog. The Workbench's **Publish...** button opens the same dialog for the book you are editing. Three explicit, consent-first paths:

- **Podcast feed** - writes a complete `.rss` file next to the book from its tags and the public URL you give; generation itself never touches the network. Upload the feed and the audio anywhere, then subscribe to the feed's public URL in any podcast app. Chapter navigation rides the `chapters.json` sidecar for Podcasting 2.0 apps.
- **SFTP upload** - save a destination (name, host, port, username, remote folder, and the public URL base that mirrors it) and upload the book plus its companion files through the app's own SSH machinery, with strict host-key policy. The password is kept in the Windows Credential Manager, never in settings. Progress speaks whole-percent steps ("Uploading book.m4b: 42%") and Cancel is real: files already completed stay on the server.
- **Auphonic** - professional post-production in your own Auphonic account. Paste your API token (kept in the credential manager), press **Check account and load presets** to hear whose account it is, your credit balance, and your saved presets; then **Send to Auphonic...** uploads, waits, and downloads the results into a folder next to the book. Cancelling before the upload finishes means no production starts; cancelling later leaves the production running in your account and skips the download - the app announces which happened.

### Make a Podcast Feed From a Folder

**Book Tools > Make a Podcast Feed From a Folder...** runs a whole show from one folder. Every MP3, M4B, or M4A master becomes an episode (oldest file = episode 1), with its title from its tags or your per-episode override and your per-episode description, edited in an accessible list. The show settings (title, author, description, media URL base, feed URL, cover URL) persist in the folder itself, so after each new build one press of **Write feed.rss now** regenerates the complete feed. **Write show notes page** produces an accessible `show-notes.html` beside it. Everything here is local file IO; uploading is the SFTP destination's job.

All publishing is unavailable in Safe Mode.

### ACX Compliance Check

**Book Tools > ACX Compliance Check...** measures any audio file - not just books built here - against the ACX submission window: integrated loudness (target -20 LUFS plus or minus 3), true peak (max -3 dBFS), and noise floor (max -60 dBFS). A passing file is told so plainly; a failing one gets a concrete recommendation per criterion ("make the recording 5.8 dB quieter"). The measurement runs in the background and needs ffmpeg; if ffmpeg is missing the app points you at **Voices > Get FFmpeg...** first.

## Job files

A `.quilljob` file pins an entire run - folder, voices, rotation and casting, chapters, output, mastering, and book details - in a small, portable, hand-editable text file.

- **Save**: on the wizard's summary page, press **Save a job file...**
- **Load**: **Studio > Open Job File...**, or **Load a job file...** on the wizard's first page. The wizard reopens with every page pre-filled from the job; review and press Start.

Keep one job file per project, or edit one in any text editor between runs. Loading a job from the Studio menu behaves exactly like loading it in the wizard - just one dialog sooner.

## Book Tools

Two listening aids live on the **Book Tools** menu:

- **Sleep Timer...** - stop playback after a number of minutes you choose, or at the end of the current chapter. The Studio announces when playback stops, and you can cancel the timer before it fires. Your last setting is remembered.
- **Play Queue...** - line up an ordered list of books. Add, remove, clear, and set which one is next. When the book you are listening to finishes and you close the Workbench, the Studio opens the next entry in the queue and announces the change; an empty queue, or a next file that has gone missing, ends playback quietly.

**Mute** (Ctrl+M) is also on the Book Tools menu - same as the Mute button in the player.

## The Studio menu

Two items on the **Studio** menu track your listening across launches:

- **Resume Last Book on Launch** (Ctrl+Alt+F10, a check item, off by default) - when set, launching the Studio reopens the most recently played book at its saved position. If that file no longer exists, it stays closed silently.
- **Recently Played** (a submenu, rebuilt each time you open it) - the books you have played most recently. Pick one to open it in the Workbench.

## Preferences

**Studio > Preferences...** (Ctrl+Comma):

- **Check for updates automatically on launch** - a quiet daily check; see "Checking for updates".
- **Alt+F4 minimizes to the system tray** (off by default) - when on, Alt+F4 tucks the Studio into the tray with any narration run still going, instead of closing the window. The titlebar X and Studio > Exit keep the "When closing the window" behavior.
- **Speak progress milestones during long runs** (on by default) - announce 25, 50, and 75 percent during a narration or build run.
- **When closing the window** - Ask when work is running / Exit / Minimize to Tray. "Ask" only prompts while an export is still going; an idle window just closes. The prompt names the work that would be lost and defaults to keeping the Studio open.

These preferences are stored in a small app-local file, so the shared settings QUILL wrote stay exactly as QUILL wrote them. Speech settings (engine, voices, rates) deliberately stay in the shared store - configure a voice here and QUILL reads aloud with it too.

## Where the Studio's own sounds play

The Studio makes short sounds of its own, such as the ones that mark a narration run starting and finishing. You choose where they play, and you can turn them off.

- **Alt+Shift+M** turns the Studio's sounds off. Press it again and they come back, on the same sound card as before. You hear a short sound as they go off, and another where they now play when they come back on, and both are spoken too. **Studio > App Sounds** has a check mark that shows whether they are on.
- **App Sounds Play On...**, a button in the Preferences window, lets you pick where they play. Open **Studio > Preferences...** (Ctrl+,), press Tab until you reach the button, and press Space. It is a button rather than a menu row, so it has no key of its own. The choices are:
  - **System default**. This is where it starts. The sounds go where Windows sends sound.
  - **None (no sounds)**. The Studio makes no sounds at all. Everything it tells you is still spoken.
  - **Any sound card or headset in the list.** The sounds get a device of their own.

After you choose, one sound plays on the new device, so you know straight away where it went.

If the device you chose is unplugged or asleep, you still hear every sound, on the system default, and the Studio tells you once. When the device comes back, the sounds go back to it by themselves.

This changes the Studio only. Your other QUILL apps keep their own choice, unless you have checked "Share these choices with my other Quill apps", which copies a change here to the others that share. Your screen reader is never moved.

## The system tray

QUILL Studio's icon is three white-and-gold waveform bars on a dark slate tile. If you have used an earlier build, this is new: the Studio used to share Quill Radio's blue broadcast-wave icon, so on a desktop with more than one QuillVille app installed several of them looked identical. Every app in the family now has its own - the same rounded tile shape and the same gold accent throughout, but its own colour and its own picture each.

While minimized to the tray the Studio keeps running - a long narration continues with the window tucked away. Use **Studio > Minimize to Tray** (Ctrl+Alt+T) to send the window there without closing it. Right-click (or keyboard-invoke) the tray icon for:

- **Open Studio Wizard...** - restore the window and open the wizard.
- **Resume: <your latest book>** - restore the window and open your most recent book in the Chapter Workbench.

Double-click the tray icon to bring the window back.

## Announcements: how the Studio tells you things

Everything the Studio announces - "Ready", a run milestone, a finished conversion, a warning - goes out on four channels at once, so you hear or feel it in whichever way you actually work:

- **Speech**, through your screen reader.
- **Braille**, on your display. This works with JAWS and NVDA and is on by default. Three rules keep it useful: braille never costs you speech (an unplugged display or a reader that refuses the message means the Studio still speaks and simply does not braille - never silence); nothing is truncated, so the end of a message is never clipped off; and the display is not stolen twice by the same message, since a flash message replaces whatever is under your fingers. An identical message inside two seconds is skipped, and a burst of different messages settles to the newest rather than each shoving the last aside - except errors, which always come through immediately.
- **Sound**, for the short cues that confirm an action.
- **The status line**, which you can read at your own pace with F6 (see "The status bar").

Announcements are also recorded as they happen, so a message that went past while you were reading something else is not simply gone.

These settings are shared with QUILL rather than repeated in the Studio's own Preferences, so set them once in QUILL's Preferences (Accessibility) and they apply here too: whether to show announcements in braille, the braille style (the full spoken wording, or a compact position-first form), how long an identical braille message is held back, whether an error stays on the display instead of flashing past, whether the companion apps play sound cues, whether a cue stands in for speech while Quiet Mode is on, and which severities interrupt speech.

## Checking for updates

**Help > Check for Updates...** compares your version with the newest Quill release, works out which download matches the flavor you run (the installer for an installed copy, the portable zip for a portable one), and fetches it with spoken progress. Then choose **Install and restart now** and the Studio does the rest itself: it applies the update - unpacking the new portable files over your folder, or running the installer quietly - and relaunches, keeping every setting, voice, and saved listening position. There is nothing to unzip and no folder to swap by hand.

Help > About shows your version with a build number, such as 2.0.0 (build 2). The build number tells you which build of a version you have: when a fix comes out without a new version number, it is a newer build, and Check for Updates offers it.

All the Quill apps are published from one place, and each one recognizes its own download, so an update to Quill Radio is never offered to the Studio and each app updates on its own schedule. The automatic startup check (on by default, throttled to once a day) is silent unless it actually finds something.

## The Command Palette

**Help > Command Palette...** (Ctrl+Shift+P) lists every Studio command in one searchable list: the three journeys, Open Job File, Publish, the podcast feed, the ACX check, Sleep Timer, Mute Playback, Play Queue, the Speech Hub, Pronunciation Dictionaries, Generate Captions, Convert Audio, Convert from URL, model and component downloads, AI setup, Preferences, and Check for Updates. Type a few letters, arrow to the command, press Enter.

## Quillins

**Quillins** are QUILL's small, sandboxed, permission-gated add-ons. They run in QUILL, Quill Radio, and QUILL Cast today; **The Studio does not offer a Quillins menu yet.** The groundwork is in place - an add-on can declare that it contributes an extra step to the Studio's audio processing, such as a loudness pass at the mastering stage, and a sample add-on demonstrates exactly that - but the Studio does not load add-ons in this version. When it does, they will be off in Safe Mode like everywhere else.

## Keyboard reference

| Action | Key |
| --- | --- |
| Open Studio Wizard... | Ctrl+N |
| Minimize to Tray | Ctrl+Alt+T |
| Open Library Window | Ctrl+Alt+Y |
| Open Book File | Ctrl+O |
| Preferences | Ctrl+Comma |
| Command Palette | Ctrl+Shift+P |
| Move focus to the status bar (and back out) | F6 |
| Open selected book (Library Window) | Enter |
| Remove selected book from library (Library Window) | Delete |
| Play selected chapter (Workbench list) | Enter |
| Rename chapter (Workbench title field) | Enter |
| Mute (player / shell) | Ctrl+M |
| Media Play/Pause (when a Workbench is open) | Media key |
| Media Stop (when a Workbench is open) | Media key |
| Media Next chapter (when a Workbench is open) | Media key |
| Media Previous chapter (when a Workbench is open) | Media key |
| Studio menu | Alt+S |
| Book Tools menu | Alt+B |
| Voices menu | Alt+I |
| AI menu | Alt+A |
| View menu | Alt+V |
| Help menu | Alt+H |
| What's New (the changelog, in your browser) | Ctrl+Shift+F1 |
| Build From Recordings button (main window) | Alt+R |
| Your books list (main window) | Alt+Y |
| Capture menu (screenshots, recording, mixer, broadcasting) | Alt+C |
| Record a demonstration, or stop and save | Ctrl+Alt+Shift+V |
| Studio Mixer | Ctrl+Alt+Shift+M |
| Broadcast live | Ctrl+Alt+Shift+G |
| Mute everything public (while live) | Ctrl+Alt+Shift+Z |

Every button and field in the wizard, the Workbench, and the dialogs also has an access key (underlined letter), reachable with Alt plus that letter while the surface has focus.

## Safe Mode

Set the environment variable `QUILL_SAFE_MODE=1` or pass `--safe-mode` (or use `run-quill-studio-safe-mode.bat`). Safe Mode disables AI features, publishing, and component downloads; everything local - narration with installed engines, the Workbench, saving - keeps working. Use it to isolate a problem or to run on a machine where network features are unwelcome.

## Sharing data with QUILL

The Studio reads and writes the same data store as QUILL, Quill Radio, and QUILL Cast: `%APPDATA%\Quill` for an installed copy, or the `data` folder next to the exe (marked by a `storage-mode.json` file holding `{"mode": "portable"}`) for a portable one. Shared between the apps:

- Speech settings: engine, voices, rates, chapter sound.
- Installed engines and models: a separately installed DECtalk, Piper voices, Kokoro, eSpeak-NG, speech-recognition models, and the mpv engine.
- Your books list, recent source folders, and per-book listening positions.
- AI provider configuration and service keys (keys live in the Windows Credential Manager).

Only the handful of window-behavior preferences above are app-local. Uninstalling the Studio never deletes the shared data.

## Getting help

Support is run by **Community Access**, and the address is
**support@community-access.org**. A person reads it, and replies come back by
email.

The quickest way there is **Help > Get Help from Support...** (Ctrl+Alt+F2),
which every app in the family answers with the same form: what kind of message
this is, a subject, what happened, and -- if you want an answer -- an email
address to reply to. What you expected and how to reproduce it are optional,
and worth more than anything else when you can give them.

Press Send and your **own mail program opens with the whole message already
written**, addressed to support, with QUILL Studio's name and version and your Windows
version filled in at the bottom. Nothing is sent until you send it there, so you
can read it over, add anything, or change your mind.

If this machine has no mail program set up -- webmail only, say -- the app puts
the whole message on your clipboard and tells you the address, so nothing you
typed is lost. And writing to **support@community-access.org** yourself always
works just as well: there is no form you have to use. Say which app you were
using and what happened.

## What's New

**Help > What's New** (Ctrl+Shift+F1) opens QUILL Studio's changelog in your browser: everything that has changed, newest first, grouped by subject so you can move through it by heading. Every app in the QuillVille family has the same command.

## Licences and notices

QUILL Studio is free and released under the MIT License. It also includes software,
data and sounds from other projects, each under its own licence.

To read them, open the Help menu, choose About QUILL Studio, and then choose the
Licences and Notices button. The list opens as a plain text file, with one
heading for each component: what it is, its licence, who holds the copyright
and what the licence asks of us. The full licence texts are at the end.

The same file, THIRD-PARTY-NOTICES.txt, and QUILL Studio's own licence, LICENSE.txt,
are also in the folder where QUILL Studio is installed or unpacked, so you can open
them without starting the app.

## Thanks

Several things in Studio's recording and screenshot features come from lessons Kelly Ford shared in [Quick Describe](https://github.com/TheIdeaPlace/QuickDescribe), a free, open-source app that describes the screen with Windows' own AI. Among them: keeping the Recording status window visible to magnifiers, drawing fewer video frames bigger so the AI guesses less, replacing a face detector that stops answering, saying a lasting limitation once rather than with every result, and keeping your user name out of diagnostic bundles. Thank you, Kelly, for the ideas and for all you give to the community.

## Troubleshooting

Two Help items are worth knowing before anything else goes wrong. **Help > View Log...** opens the Studio's own log, so you can read what happened during a run instead of guessing. **Help > Save Diagnostics...** writes a small, redacted zip - the log plus what the Studio can tell about your machine and settings, with anything private scrubbed - which is exactly what to attach to a bug report. **Help > Get Help from Support...** (Ctrl+Alt+F2) writes to a person for you, already tagged with this app's name and version.

- **"The ACX check measures loudness with FFmpeg, which looks missing."** Choose **Voices > Get FFmpeg...** The same applies if compressed output formats fall back to WAV, audiobook assembly fails, or silence detection cannot run - all of those are ffmpeg's jobs. The packaged installer and portable zip bundle ffmpeg; this mostly affects source checkouts.
- **An engine shows "(not installed)" in the wizard.** Open **Voices > Speech Hub** and use the download button for Piper, eSpeak-NG, or Kokoro, or use **Voices > Download Optional Components...**. DECtalk is not distributed by QUILL and must be installed separately.
- **The Preview voice button says "Download this voice to hear a preview."** No bundled sample ships for that voice and its engine is not installed yet; download the engine or voice first.
- **A Piper voice is selected but will not speak.** The voice model has not been downloaded; the Speech Hub's Download Voice button fetches it.
- **A book in Your books is marked "(missing)".** The file was moved or renamed. Open it from its new location with Ctrl+O (the list updates), or press Delete to drop the stale entry.
- **The Save button is disabled in the Workbench.** The book is an M4B; use **Save As...** - M4B chapter data cannot be rewritten in place, so the Workbench re-muxes losslessly to a new file.
- **"Propose AI titles" says it needs a configured AI provider.** Run **AI > Set Up AI...** first - or you are in Safe Mode, where every AI surface is disabled.
- **A translated edition was skipped.** The cloud voice you chose for that language has no API key configured; the run notes the skip and continues rather than stopping.
- **Closing the window warns about work in progress.** A narration or build run is still going. Choose No to keep the Studio open, or minimize to the tray and let it finish; the "When closing the window" preference sets a fixed answer.
- **Windows SmartScreen blocks the installer.** The release is not code-signed; choose "More info" then "Run anyway".
- **Text looks blurry, or a window is the wrong size.** QUILL Studio scales itself for each monitor. Text stays sharp at 125, 150 or 200
  percent, and when you move a window to a monitor with different scaling;
  windows and list columns keep their proportions. If a window looks wrong at
  your scaling, you can turn this off to see whether it is the cause. Search
  Windows for "Edit environment variables for your account", add a variable
  named `QUILL_DPI_UNAWARE` with the value `1`, and start QUILL Studio again.
  Windows then stretches it the old way, so text is blurrier. Delete the
  variable to put scaling back, and tell support what you saw.


## Screenshots and the Screenshot Inspector (unreleased)

The new Capture menu keeps screenshot work separate from your book library. It does not record sound or change your audio devices.

Choose **Capture screen** to select a named visible window, one display, the full desktop, an active window after a delay, or a guided region. For the easiest first capture, choose the whole named window: no size settings are needed. Guided regions use familiar portions of a window or display; exact coordinates are optional advanced settings. Displays left of or above your primary display can have negative coordinates. Minimized windows must be restored first.

By default, the window list aims to stay short by listing top-level task windows (similar to what Alt+Tab shows). Use **Show all windows (advanced)** when you need tool windows or helper dialogs that are not normally listed. If you need more than a window title to decide, use **Window properties...** for the selected window. If the window list shows only Desktop/Display targets, update: a preview build had a regression that hid named windows.

Refresh windows and displays when the list is stale; a missing target remains unavailable rather than silently becoming a desktop screenshot.

Choose an absolute save folder and a delay, then activate **Start capture**. For the active-window option, switch to the intended application during that delay. A selected named window is captured directly. **Cancel pending capture** cancels a capture that has not started. A capture already in progress may finish.

**Screenshot active window now** and **Screenshot full desktop now** are immediate actions. **Repeat last selected target** uses the target, folder and delay you chose in Capture screen. It asks you to choose a target first when none has been selected this session.

Screenshots are saved as uniquely named PNG files, with a JSON verification report and readable Markdown report. File decoding, dimensions and the file hash are objective checks. They do not prove that the intended content is visible or private. Protected content can still be blank. **Screenshot Inspector** opens the latest screenshot; **Open saved screenshot** opens a saved PNG for review.

### Guided regions: no pixel calculations required

Choose **Guided region** from Target. In **Region source**, choose the window or display containing the material. In **Capture portion**, start with **Whole source (recommended; keeps all visible context)**. Studio calculates the screen position and size.

For a smaller area, choose **Top half**, **Bottom half**, **Left half**, **Right half**, or **Middle quarter**. These describe portions of the source rectangle, not recognized controls. For example, the top half may include a dialog heading while excluding its buttons. If you do not know which part contains your content, keep Whole source or capture the whole named window instead.

Read **Capture plan and guidance** before Start capture. It explains the source, exclusions, possible clipping, and next review steps. Guidance is selectable text, and changed selections are announced. The content area scrolls while Start capture and Cancel remain outside it. Use Tab to visit labeled controls; native choice controls use arrow keys.

A guided region captures an area of the desktop. Overlapping windows and notifications can appear in it. Direct named-window capture is the better choice when you need the whole application window. Keep a guided region's source still during the delay. If it moves, resizes, disappears or changes process, refresh and choose again; Studio will not silently switch sources.

**Enter exact coordinates (advanced)** is optional. Enabling it starts with the current guided portion's values. Left and Top locate its upper-left corner; Width and Height measure its size in physical screen dots. A screen left of or above your primary display can have negative Left or Top. Studio rejects values beyond the desktop, but valid numbers alone cannot prove that text is readable or the intended dialog is complete.

After capture, use local OCR to check expected text. If you approve AI sharing, choose the framing preset and ask “Is the whole dialog visible, including its buttons?”, “Is any text cut off?”, or “What should I change before sharing?” AI gives uncertain advice; no setting guarantees semantic correctness.

### Screenshot commands and default in-app shortcuts

These shortcuts operate inside Studio. System-wide screenshot keys are separate, opt-in assignments; the Capture menu displays the current in-app bindings.

| Action | Default in-app shortcut |
|---|---|
| Capture screen: choose source and delay | Ctrl+Alt+Shift+S |
| Open saved screenshot | Ctrl+Alt+Shift+O |
| Screenshot Inspector | Ctrl+Alt+Shift+I |
| Cancel pending capture | Ctrl+Alt+Shift+X |
| Screenshot active window now | Ctrl+Alt+Shift+F5 |
| Screenshot full desktop now | Ctrl+Alt+Shift+F6 |
| Repeat last selected target | Ctrl+Alt+Shift+F4 |
| Capture global hotkeys configuration | Ctrl+Alt+Shift+H |

Immediate full-desktop capture includes every display. Repeat uses the last source/folder/delay selected in this session; there is no repeat recipe after a fresh launch until you select one. A previously approved automatic-AI setting also applies to screenshots triggered by global keys.

### Global screenshot hotkeys

Open **Capture > Capture global hotkeys**. Select active-window capture, full-desktop capture, repeat-last-target or cancellation, choose Assign and press your preferred combination, then Save. Clear removes a binding. These keys work while Studio is in the tray or another application has focus, provided Windows grants the registration. No global screenshot key is taken by default. An unavailable combination is reported so you can choose another. Safe Mode leaves them inactive. Test your chosen keys with your screen reader and other applications.

### Local OCR and image-grounded AI chat

The Inspector shows the exact image source, hash, file checks and a selectable conversation. **Read text locally** runs the existing offline OCR service. Confidence is reported only when the engine supplies it; OCR availability and recognition accuracy vary.

Choose a **Prompt style**. Screenshot-specific presets cover orientation, controls, text/errors/tables, capture problems, possible sensitive information, alt text and charts. The shared image styles and your custom prompts are available too. **Editable prompt instructions** lets you add detail or replace the preset, and **Your question or additional instructions** accepts a separate question. **Manage prompts** adds, edits or removes reusable prompts in the shared library.

**Configured AI providers.** Screenshot AI uses QUILL's shared AI connection settings, model selection, provider-specific credentials and vision transport: OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama (local or cloud), and compatible custom endpoints. Select the provider and an image-capable model through the shared AI setup. Studio does not require Ollama or maintain a separate provider configuration. Provider/model image support still applies; a text-only model cannot inspect screenshots. Changing the connection pauses previously approved automatic uploads.

Choose **Ask AI** to approve sending the complete screenshot to the named provider, model and endpoint. Private information is not automatically redacted. A privacy-review prompt is a review of an image already sent to that provider, not a guarantee that sharing was safe. AI Off and Safe Mode block AI; local capture and verification continue to work.

The reply appears in the same conversation. Ask follow-ups about that image without capturing again. The image bytes are checked against the original hash before each request. Editing the saved image causes inspection to fail rather than silently answering about a different artifact. You can keep typing while a reply is pending, but a second request waits until the first finishes.

**Save report** exports objective evidence and clearly labeled unverified observations. **Export description** saves a text description and conversation, and **Copy image** copies the PNG to the clipboard. Closing the Inspector cancels unsent chat work; a request already sent may still finish. AI and OCR observations need review even when the file checks pass.

### Optional automatic AI

**Automatically inspect future captures with AI** is off by default. Enabling it asks for separate approval to send every future user-triggered Studio screenshot, including full-desktop captures, to the selected connection. **Use for automatic AI** saves the current prompt instructions for those requests.

Changing the provider, model or endpoint pauses automatic analysis until you approve the new connection. AI Off and Safe Mode override this setting. Clearing the checkbox stops future and queued unsent automatic requests; it cannot recall a request already sent. Capturing remains an explicit user action. The result is available in Screenshot Inspector and the report.

Screenshots do not yet offer scrolling capture, UIA-element selection or annotation and redaction editing. Video recording with sound is in "Record a demonstration" below. Release acceptance still requires JAWS, NVDA, Narrator, braille, mixed-DPI and installed/portable testing.

### Worked example: an error dialog for a support request

1. Open the application and error dialog you want to document. Avoid showing passwords, private messages or unrelated personal material.
2. Open Capture screen and choose that named window. If a dialog has its own window entry, choose its title. Use Refresh windows and displays if it is missing; restore minimized windows first.
3. Keep the whole window for the first attempt. Choose an absolute save folder and enough delay to return to the application, then Start capture.
4. Open Screenshot Inspector. Review the source name and file evidence. Read text locally and check that the expected error code and message appear. Missing OCR text might mean recognition failed; it does not by itself prove that the capture is wrong.
5. If you want AI help, choose the text/errors preset, add “Preserve the exact error code; mark uncertain characters,” and enter your question. Ask AI presents the configured destination before sending. Declining leaves the screenshot saved locally.
6. Ask a follow-up such as “Are any buttons or message lines clipped?” The same image is used again. Capture a new image when the application changes; a follow-up does not inspect the live desktop.
7. Save report and Export description. Copy image only when ready to paste it into the intended destination. Review the exported text and image before sharing. The evidence report labels AI/OCR observations as unverified.

### Worked example: use your configured AI provider

Use **AI > Set Up AI** and QUILL's shared connection controls to choose OpenAI, Google Gemini, Anthropic Claude, OpenRouter, Ollama or a compatible custom service. Configure the endpoint, credential and an image-capable model there. The Screenshot Inspector uses that active shared connection; it does not have a separate provider selector or separate key store. Switching providers in shared settings affects other QUILL features that use the same connection.

Open a saved PNG or make a new screenshot. Choose a prompt, edit its instructions, type a question and activate Ask AI. Check the provider, effective model and endpoint in the consent message. Local OCR works independently of a cloud key. A provider being configured does not prove that every one of its models accepts images. Provider errors should be resolved through the shared connection/model settings, rather than by sending the image to another service without approval.

### Customize a reusable prompt and keep the conversation grounded

Choose a built-in style for a starting point. Add your purpose in Editable prompt instructions, for example: “I am writing a bug report. Separate the exact visible error text from your explanation. Describe positions as top/bottom/left/right; do not invent keyboard shortcuts.” Add a separate question such as “What information should I include in my report?”

Edits in the prompt field apply to that request. Use Manage prompts to add or edit a reusable custom prompt in the shared image-prompt library. Choosing another style fills the editor with that style, so save reusable wording through Manage prompts before changing styles. Use for automatic AI explicitly saves the current instructions for future automatic requests; editing a manual question does not grant automatic-sharing consent.

Follow-ups include earlier observations about the current image. A provider may misunderstand the text or layout. Ask it to identify uncertainties and verify important strings locally. Replacing or editing the PNG changes its hash; reopen it as a new review artifact instead of continuing under the old verification.

### What the evidence proves

The PNG is the saved screenshot. The same-named verification JSON is machine-readable; the verification Markdown is readable text. A description export contains file evidence and recorded observations. Full decode, dimensions and SHA-256 establish that the saved image is decodable and identify its bytes. They do not establish privacy, completeness, visual quality, accessibility or that the intended dialog is visible. “Uniform pixels” can indicate an empty-looking result; it cannot identify every protected or failed capture.

AI and OCR findings are separate from objective checks. AI does not automatically fix, redact, annotate or publish an image. This milestone exports PNG; JPEG conversion, editable annotation layers and comprehensive evidence bundles are still pending.

### Screenshot troubleshooting

- **The window is not listed.** Restore it, then Refresh windows and displays. If it still cannot be captured, read the failure rather than choosing a broader source accidentally. Protected or GPU-rendered content can remain blank.
- **The guided region moved or changed.** Keep the source still, refresh and choose it again. Repeat last selected target retains the prior recipe; it does not authorize capturing a newly positioned region silently.
- **The plan says a region cannot be captured.** Choose Whole source or the whole named window. Advanced users can correct the bounds. A window partly beyond the desktop may be unsuitable as a desktop region.
- **The image is clipped or contains an overlay.** Capture the whole named window, dismiss the unrelated overlay, or deliberately select a different source and capture again. A half-region is not a content-aware crop.
- **OCR is unavailable or inaccurate.** Check the shared offline OCR support and try clearer/larger source text. Confidence is not supplied by every engine. Optional image-capable AI can help, but requires sharing approval and is not proof.
- **AI fails.** Check AI Off, Safe Mode, the shared endpoint/key/model and whether the model accepts images. The PNG remains available even when AI fails. No provider is silently substituted.
- **Automatic AI has paused.** The approved provider, model or endpoint may have changed. Review the new destination and explicitly approve it. Turning automatic mode off stops future/unsent work; it cannot recall a sent request.
- **A global hotkey does nothing.** Confirm it was assigned and Windows reported registration success. Safe Mode leaves global keys inactive. Another application or screen reader may own the combination; choose and test another.

### Completion status and next steps

The full screenshot PRD is not complete. UIA control selection, content-aware regions, scrolling/sequence capture, comparison, named workspaces, keyboard crop/zoom, annotation/redaction and Capture and Dictate remain. Actual JAWS/NVDA/Narrator/braille usability, mixed-DPI hardware, live-provider privacy and installer/portable acceptance also remain. The requirement coverage audit, `docs/design/quill-studio-screenshot-coverage.md` in QUILL's source, lists each one. Video demonstrations with sound, the Studio Mixer, picture making, YouTube videos, asking AI about a video and live broadcasting each have their own section below.

## Record a demonstration (unreleased)

This records what you are showing and what you choose to let people hear, as one MP4 video you can post or send, or as a sound file when there is no picture. It is built for a presenter who cannot see the screen: everything is set up from lists and check boxes, you hear one summary before you start, and afterwards you are told what is actually in the file, not what Studio meant to put there.

Open **Capture > Record a demonstration...** (Ctrl+Alt+Shift+V). The window goes from top to bottom in the order you decide things: what to record, which sounds go in, the camera, the picture and the file, and then Check.

### The short version

1. Open the program you want to demonstrate.
2. Press Ctrl+Alt+Shift+V. Choose that program under **Target**.
3. In **Sound sources**, put in what people should hear: usually the program's own sound and your microphone. Your screen reader is left out unless you put it in.
4. Press **Check** and listen to the summary. Fix anything it calls Stop.
5. Press **Start recording**. Studio counts down, hides itself, and records.
6. Press Ctrl+Alt+Shift+V (or a system-wide key you assigned) to stop. You hear what was saved and whether it checked out.

### What to record

Two check boxes decide the picture, and the Sound sources list decides the sound. Any mix works:

| You want | Include the screen picture | Include the camera picture | Sound sources |
|---|---|---|---|
| A software demonstration | On | Off | Program sound, microphone |
| A demonstration with your face in a corner | On | On | Program sound, microphone |
| A talking-head video | Off | On (Camera only) | Microphone |
| A podcast or voice-over | Off | Off | Microphone, any programs |
| A silent screen video | On | Off | Nothing |

- Both pictures off gives a sound-only file. Choose the kind under **Sound-only file format**: M4A for most uses, MP3 to play anywhere, WAV or FLAC to keep every detail, or Opus for the smallest speech files.
- A picture with no sound source: **Give a video with no sound a silent soundtrack** is on by default, because some websites refuse a video without one. Turn it off for no soundtrack at all.
- If nothing at all is chosen, the check says so and recording cannot start.

**Target** is a named window, one display or the full desktop, from the same list Capture screen uses. It applies only when the screen picture is on. A named window is selected first when there is one. A window recording records that window's area of the screen, so anything that covers it, such as a notification, is recorded too, and if you move the window the recording does not follow it. If that matters, record the display instead. **Refresh windows and displays** brings the list up to date after you open or close a program.

### Which sounds go in

**Sound sources** is a list. Each row says either "In the recording" or "Left out", and Space switches the row you are on. Nothing on this list changes what you hear; it only decides what is recorded.

- **The program's own sound** (for example "msedge sound") is in by default when you chose a window. It is that program's sound and nothing else, so your screen reader is not in it. Windows records it directly from the program, so it does not matter which sound card the program plays on, or whether you have muted it for yourself.
- **System sound** is everything your computer plays. It starts left out. With **Leave the screen reader out of system sound** checked, which is the default, Studio records everything except your screen reader. Studio's own sounds are switched off while it records the system and come back when you stop.
- **Microphone** starts left out, every time. Studio never remembers that it was on, so you never record your voice by accident. Choose which microphone under **Microphone device**, and under **Microphone channels** whether to record input 1, input 2 or both inputs mixed; use one input when your interface has the microphone plugged into only that one. If another QUILL app is dictating, the check tells you which one.
- **Screen reader speech** (for example "JAWS speech") starts left out. Putting it in asks you to confirm, because everything your screen reader says while you record ends up in the file. While it is in, Studio stops talking to you through it except to report a failure; confirmations become sounds instead.
- **Add a program's sound...** adds any other program that is playing sound, such as a media player, as a row of its own. The same list ends with **Everything playing on** each sound card, to record all a card plays, such as your headphones. If your screen reader speaks on that card, its speech is recorded too, and the check says so. **Remove program** takes a row off again.

**Level of the selected source** sets how loud that row is in the recording, from minus 60 to plus 12 decibels. A level of 0 leaves it as it is. Lower a loud program by 6 to 10 decibels so your voice stays on top.

**Professional audio interfaces (ASIO).** See "ASIO sound cards" below. Once it is on, your interface's inputs appear under **Microphone device** with "(ASIO)" after the name.

### The camera

Check **Include the camera picture** to record your camera as well. Choose the camera, which corner it goes in (or **Camera only**, which records the camera instead of the screen picture), and how big it is.

**Check camera framing...** (Ctrl+Alt+Shift+C, or the button in this window) opens the camera and tells you, as you move, whether your face is in view: "No face in view", "Face in view, centred", or which way to go, such as "move a little to your left", "move back from the camera" or "tilt the camera down or sit up taller". Directions are from your side of the camera. If they send you the wrong way, your camera gives a mirror image: check **The camera gives a mirror image**. Face detection is the one built into Windows and runs on this computer. Nothing is recorded, saved or sent anywhere while you check.

With **Tell me when my face leaves the camera view** checked, Studio says so during the recording, and again when you are back. If your screen reader's speech is being recorded, Studio adds a marker instead of speaking, so the announcement does not end up in the video.

If the face detector stops answering, Studio starts a fresh one. After three failures in a row it says "Face detection stopped answering, so framing advice has stopped": close the camera check and open it again, or restart the computer if it keeps happening.

Tips for good framing: sit an arm's length from the camera, put a light in front of you rather than behind you, and run the framing check with the same lighting you will record in.

### The picture and the file

- **Frame rate** is 30 frames a second unless you choose 15, 24 or 60. 30 suits software demonstrations; 60 makes fast movement smoother but makes bigger files and works the computer harder.
- **Maximum picture size** can scale a large screen down to 1080p or 720p. Smaller pictures make smaller files and help a slower computer keep up.
- **Include the mouse pointer** is on by default.
- **Countdown** is how many seconds Studio counts aloud before it starts, so you have time to move to the program you are demonstrating.
- **Save in** is your Videos folder, in a QUILL Studio folder, unless you choose another one. The name is "Demo -", the target, and the date and time. An existing file is never replaced.
- **Also keep each sound source as its own WAV file** keeps a separate file per source beside the video, so the microphone and the program can be edited separately later.

### Keeping the computer awake and notifications quiet

**Keep the computer awake while recording** and **Turn on Do Not Disturb while recording** are both on unless you turn them off. The first stops sleep, the screen turning off and the screen saver. The second silences Windows notifications so none slides into the picture or the sound. When you stop, both go back to exactly how they were: if Do Not Disturb was already on, it stays on. If Studio or the computer stops in the middle, Do Not Disturb is put back the next time Studio starts. If Windows does not let Studio change Do Not Disturb, the check tells you, so you can turn it on yourself from the Windows notification centre.

Studio keeps its own windows out of the recording. Windows does that by hiding them from capture, which can also hide them from a magnifier and from screen sharing. If you use a magnifier, or share your screen during a recording, check **Let magnifiers and screen sharing see the Recording status window**. The window is then recorded too if it is inside what you record, so put it on another display or outside the window you record. The check reminds you when this is on.

### Check, then start

Press **Check**. It takes a few seconds: Studio takes a trial picture, records three seconds of the screen at your settings to see whether the computer keeps up, opens each sound source briefly, looks for the camera, and checks FFmpeg, the folder and its free space, whether the computer is on battery, and whether Windows Update is waiting to restart it.

The result lands in the **Check result** field and your screen reader reads it once. It says what will be recorded, which sounds are in and which are left out (always naming your screen reader), where the file goes, and then every problem:

- **Stop** means it cannot record until you fix it, for example no folder, no FFmpeg, or nothing chosen to record.
- **Warn** means it can, but something might spoil it. Examples: a microphone that is delivering pure digital silence because Windows privacy settings are blocking it; the trial recording dropped frames; the computer is on battery; a Windows Update restart is waiting; free space runs out in a stated number of minutes; your screen reader may be on a sound card you chose to record.

When nothing says Stop, press Enter in the result field, or **Start recording**. If you change anything after the check, Studio asks you to check again.

**Record a quick test** records with exactly these settings to a temporary file, for as long as **Test length, seconds** says (5 seconds to 10 minutes, so a longer test is a full rehearsal), checks it the same way as a real recording, and lets you play it. The test file is deleted when you close its window.

### Before a long recording

An hour-long demonstration is a big investment. Before you start one:

1. Plug the computer in. The check warns on battery and says how many minutes it thinks are left.
2. Restart first if the check says Windows Update is waiting. An update restart in the middle ends the recording.
3. Make sure the check's free-space estimate is well over your planned length. Studio warns two minutes before space runs out and stops and saves before it does, but it cannot make more room.
4. Record a quick test of two or three minutes with the real programs, microphone and camera, and play it back. Listen for your voice level against the program's sound.
5. If the trial dropped frames, lower **Frame rate** or **Maximum picture size**, close other heavy programs, and check again.
6. Assign system-wide keys (see "While you record") so you can pause, mark and stop without coming back to Studio.
7. Add a marker (Ctrl+Alt+Shift+B) at each new topic. Markers become YouTube chapters later and make the recording easy to navigate.

### While you record

Studio hides itself, keeps its own windows out of the picture, puts "Recording" at the front of its title, and shows a small **Recording status** window that does not take focus. Focus stays in the program you are demonstrating.

| Action | In Studio | Notes |
|---|---|---|
| Record a demonstration, or stop and save | Ctrl+Alt+Shift+V | |
| Pause or resume | Ctrl+Alt+Shift+P | A pause is a gap in the file, not a frozen picture |
| Add a marker | Ctrl+Alt+Shift+B | Saved beside the video as a markers file |
| Mute or unmute the microphone in the recording | Ctrl+Alt+Shift+U | The microphone stays open; the muted stretch is marked |
| Recording status | Ctrl+Alt+Shift+T | Elapsed time, sounds in, screen reader in or out, dropped frames, space left |
| Show the Recording status window | Ctrl+Alt+Shift+W | |
| Emergency stop and save | Ctrl+Alt+Shift+End | A second stop key, in case one is swallowed |
| Discard this recording | Ctrl+Alt+Shift+Delete | Asks before deleting anything |
| Recover unfinished recordings | Ctrl+Alt+Shift+L | |

Those keys work while Studio has focus. While you are demonstrating, focus is somewhere else, so assign system-wide keys: **Assign keys** in the Record a demonstration window, or **Capture > Capture global hotkeys...**. None is assigned for you, because a system-wide key takes that key away from every other program. Until you assign some, use the tray icon's menu, which has Stop and save, Pause, Add a marker, Recording status and the status window, and acts without bringing Studio back into the picture.

If something goes wrong while you record, you hear it once and it is marked at that moment:

- The window you are recording closes: the recording stops and saves what it has.
- A program or your screen reader quits: Studio notices within two seconds, and that sound is silent until the same program starts again, when you hear that it is back.
- Your screen reader restarts while it is left out of system sound: system sound is muted at once, so the new screen reader is never recorded, and comes back once the new one is left out too.
- A sound card you are recording is unplugged or changes format: silent until the same card comes back, and then reopened.
- A microphone is unplugged: silent until the same microphone comes back. A different microphone is never swapped in.
- Sound stops arriving, or a microphone overflows: you hear it the first time, and the check report counts every time.
- The display changes: the recording pauses.
- The camera stops or falls behind.
- The disk runs low: a warning at two minutes left, then a stop and save before it runs out.

### When you stop

Studio joins the pieces, mixes the sounds at your levels, adds the camera picture, and then checks the finished file on its own, without trusting anything it measured while recording: one picture stream and one sound stream, the right length and frame count, clean decoding at the start, middle and end, no long black stretches, and each sound source actually present. You hear one sentence, for example "Demonstration saved, 2 minutes 41 seconds, 1920 by 1080 at 30 frames a second. Picture and sound checked. msedge sound and Microphone present; screen reader left out."

The result is **Verified** when every check passed, **Needs review** when it plays but something may be spoiled, or **Failed** when a stream is missing or it does not decode, in which case the recorded pieces are kept so nothing is lost.

The result window lists every check, and has buttons to:

- play the file, open its folder, or copy its path;
- **Inspect a frame...** in the Screenshot Inspector;
- **Ask AI about this video...** (see "Ask AI about a video");
- **Make captions and a transcript**: Studio transcribes the speech on this computer with the speech recognition you already use for captions, and saves SRT and VTT captions and a plain transcript beside the file. Nothing is sent anywhere;
- **Make a video with a picture...**, for a sound-only recording (see "Make a YouTube video from a picture and sound").

### What is saved

Beside each recording:

- the video (MP4) or sound file;
- a readable report and a JSON report of the checks;
- a markers file, when you added markers;
- one WAV file per sound source, when you asked for them;
- captions (SRT and VTT) and a transcript, when you made them.

### Recovering an unfinished recording

If Studio or the computer stops in the middle of a recording, nothing is lost up to that point: Studio records in short pieces as it goes. The next time Studio starts it says so on the status line. Choose **Capture > Recover unfinished recordings** (Ctrl+Alt+Shift+L) to finish and check them; each becomes an ordinary recording with the same checks.

### Worked example: a screen reader demonstration for a blog post

You want to show how to fill in a web form with your screen reader, with your voice explaining and the screen reader audible.

1. Open the form in your browser.
2. In Record a demonstration, choose the browser window under **Target**.
3. In **Sound sources**: leave the browser sound in, put **Microphone** in, and put your screen reader's speech in, confirming when asked. Set the browser to minus 6 decibels.
4. Turn the camera off. Leave **Keep the computer awake** and **Do Not Disturb** on.
5. **Assign keys** for stop and marker, for example Ctrl+Alt+Shift+F11 and Ctrl+Alt+Shift+F12, so they work from the browser.
6. **Check**, then **Record a quick test** of 20 seconds and play it. Your voice and the screen reader should both be clear.
7. Start recording, demonstrate, add a marker at each step of the form, and stop.
8. In the result window, choose **Make captions and a transcript**, then post the video with its captions file.

### Worked example: a podcast episode with no picture

1. Turn off both **Include the screen picture** and **Include the camera picture**.
2. Choose **Sound-only file format**: MP3 for a podcast feed.
3. Put **Microphone** in. If a guest calls in on Zoom or Teams, add that program's sound with **Add a program's sound...**, so you record the guest without your screen reader or other programs.
4. Check, record, and stop. The result is an MP3 beside its report.
5. To put it on YouTube, choose **Make a video with a picture...** in the result window.

### Recording troubleshooting

- **The check says the microphone is silent.** Windows privacy settings may be blocking microphone access for desktop apps. Open Windows Settings, Privacy and security, Microphone, and allow desktop apps. Or another program has the microphone in exclusive mode; close it.
- **The check says frames were dropped.** Lower the frame rate or picture size, close heavy programs, and plug in the computer.
- **My screen reader is in the recording and I did not want it.** Check which rows are in. "Everything playing on" a sound card includes your screen reader if it speaks on that card; use the program's own sound or System sound with "Leave the screen reader out" instead.
- **A covering window is in the video.** A window recording records the window's area of the screen. Bring the window to the front, turn on Do Not Disturb, or record the whole display.
- **My stop key does nothing.** Studio's own keys work only while Studio has focus. Assign system-wide keys, or use the tray icon's menu.
- **The result says Needs review.** Open the result window's list of checks: it says which check did not pass, such as a long black stretch or a sound source that was silent throughout.
- **Do Not Disturb did not turn on.** Some Windows editions and policies do not allow it. Turn it on yourself before you start.

### What this does not do yet

A window recording follows the window's area of the screen rather than the window itself, so a covering window is recorded and moving the window is not followed. There is no trimming or editing, no click highlighting, and no virtual camera. Real screen-reader, braille and hardware acceptance runs are still to be done.

## The Studio Mixer (unreleased)

**Capture > Studio Mixer...** (Ctrl+Alt+Shift+M, or **Mixer: sounds you hear** in the Record a demonstration window) changes what *you* hear, not just what is recorded. It does what the Windows volume mixer and sound settings do, in one window you can use entirely from the keyboard. It has two tabs; Ctrl+Tab moves between them.

### Programs

The list has every program playing sound, with whether you hear it, how loud it is, whether it is playing now, and which sound card it plays on.

- **Space** mutes or unmutes the program you are on.
- **Volume** sets it from 0 to 100 percent: Up and Down move by 1, Page Up and Page Down by 10.
- **Sound card** moves the program to another card, exactly as Windows Settings does. Choose **Windows default** to send it back. Windows remembers these choices for the next time the program runs.

A program has to be playing, or have played, to appear and to be moved: Windows only knows about a program's sound once it has made some.

### Devices

The list has your playback and recording devices.

- **Make default** makes the selected device the one Windows uses for most sound.
- **Make communications device** makes it the one calls use, such as Zoom and Teams.
- For a microphone, **Recording level** and **Mute this input** set how it records for every program.

### Worked example: your screen reader in the headset, everything else on the speakers

1. Set your headset as the Windows default so your screen reader uses it.
2. Open the Studio Mixer and, on Programs, select your browser.
3. Under **Sound card**, choose your speakers. The browser now plays on the speakers while your screen reader stays in your headset.
4. Lower the browser's **Volume** if it is too loud.

A program muted in the mixer is silent for you and in any recording of the system sound. A recording of that program's own sound still has it, because that is taken directly from the program.

## ASIO sound cards (unreleased)

If you have a professional audio interface with an ASIO driver, Studio can record from its inputs with the lowest delay.

1. Open **Studio > Preferences...** (Ctrl+,).
2. Turn on **Use ASIO sound cards**.
3. Restart Studio.

The interface's inputs then appear under **Microphone device** in Record a demonstration, listed first, with "(ASIO)" after the name. Most ASIO drivers let only one program use the interface at a time, so close other audio programs first. The setting is off by default because a faulty ASIO driver can stall the program that loads it. If Studio misbehaves after you turn it on, turn it off again and restart Studio.

## Make a picture with AI (unreleased)

**Capture > New picture with AI...** (Ctrl+Alt+Shift+J) makes a picture from your description, such as a cover for a podcast or the picture for a YouTube video. You describe it in words and change it in words; you never have to see it.

It uses the AI provider you set up in **AI > Set Up AI**, when that provider makes pictures: OpenAI or Google Gemini. Other providers are told plainly that they cannot.

### Making the first picture

1. In **Describe the picture, or the change you want**, describe the whole picture: the subject, the style, the colours, and any words on it exactly as they should be written.
2. Choose **Shape**: wide for a YouTube video (16 by 9), square for a cover or social post, or tall for Shorts or a phone (9 by 16).
3. Press **Make the picture**. Studio asks first, naming the provider, model and address the description goes to, and that charges may apply.

The picture is saved in a "QUILL Studio Pictures" folder beside your recordings folder. Then your vision model looks at it separately and describes it: subject, layout, colours, any text exactly as written, and anything odd. You hear that description, not the generator's claim about what it drew, so a misspelt title or an extra hand is reported to you.

### Changing it

Type only the change, such as "make the background darker" or "add the title QUILL Talk at the top in large white letters", and press **Make the change**. Every earlier request is kept, so the change is applied to the picture you have rather than starting again.

Every version stays in **Versions**; choose one to hear its description again in **Description of the chosen version**. **Make a video with this picture...** opens the YouTube video window with that picture. **Open folder** opens the pictures folder. A text file beside each picture holds what you asked for and its description.

### Privacy and cost

Your description is sent to the provider you approved; nothing is sent until you press the button and approve. Picture making is charged by most providers per picture. AI off and Safe Mode both stop picture making.

### Worked example: a podcast cover

1. Describe: "A square podcast cover. A vintage microphone in warm gold light on a deep blue background. The words QUILL Talk in large white letters across the top."
2. Shape: Square. Make the picture.
3. Listen to the description. If it says the words read "QUIL Talk", type "the title must read QUILL Talk, spelled Q U I L L" and make the change.
4. When the description matches what you want, choose **Make a video with this picture...** to pair it with your episode.

## Make a YouTube video from a picture and sound (unreleased)

**Capture > Make a YouTube video from a picture and sound...** (Ctrl+Alt+Shift+Y) turns a recording or any audio file into a video YouTube accepts, showing a picture for the whole length. The sound goes in exactly as it is.

To record new sound first, use Record a demonstration with the screen and the camera turned off. When that finishes, its result window has **Make a video with a picture...**, which opens this window with the sound already filled in.

- **Picture** and **Sound**: type a path or use the Browse buttons. The picture can be PNG, JPEG, WebP or BMP, and defaults to your last screenshot. It is fitted to the video, never stretched; any space left over is black.
- **Shape**: YouTube video (1920 by 1080), square (1080 by 1080) for social posts, vertical (1080 by 1920) for Shorts, or the picture's own size.
- **A slow zoom on the picture** makes the picture move gently closer through the video, so it does not look frozen.
- **Show a sound wave along the bottom** adds a white wave that moves with the sound, so viewers can see that sound is playing.
- **Use the recording's markers as chapters** is available when the sound came from a recording with markers. YouTube shows chapters only when there are at least three, ten seconds or more apart, starting at 0:00, so Studio keeps the ones that qualify and adds a "Start" chapter at 0:00 when needed.
- **Title** and **Description** are what viewers see.

Press **Make the video**. The video is saved beside the sound as "name - video.mp4" and checked the same way as a recording. A text file beside it ("name - video.youtube.txt") holds the title and the description with chapter timestamps, ready to paste into YouTube's upload page.

### Uploading to YouTube

1. On YouTube, choose Create, then Upload videos, and choose the "name - video.mp4" file.
2. Open "name - video.youtube.txt". Paste its title into the title field and the rest into the description. The chapter times in the description become YouTube chapters.
3. If you made captions for the recording, upload the SRT file under Subtitles.

Studio never uploads anything itself.

## Ask AI about a video (unreleased)

**Capture > Ask AI questions about a video...** (Ctrl+Alt+Shift+K), or **Ask AI about this video...** in a recording's result window, lets you ask what is on screen in a video: whether a dialog appeared, whether the text was readable, what a viewer sees at a given moment.

1. **Video**: the file to ask about; **Browse...** to choose one.
2. Choose **The whole video**, or **A stretch of it** and set **From** and **To** in minutes and seconds, written like 1:05.
3. **Number of frames**: how many pictures to take across that stretch: 4, 6, 9, 12 or 16. Fewer frames are drawn bigger, so the AI can read small text better: 4 frames are each 960 pixels wide, 16 are 512. More frames see more moments, but each is smaller.
4. **Include the transcript of that stretch**, when captions exist beside the video, adds what was said in the same stretch.
5. Press **Prepare the question**.

Studio takes the frames at even times across the stretch, lays them out as one picture with each frame's time written on it, and opens the same conversation window as the Screenshot Inspector, with a question already describing the picture. Ask your own question, and follow-ups after it. Nothing is sent until you approve it, using your usual AI connection, and Safe Mode blocks it as it blocks screenshot AI. Answers cite the times of the frames they rely on, so you can go to that point in the video.

The AI sees only the frames, not the moving video, so something that appears and disappears between two frames can be missed. Ask about a shorter stretch to look more closely. The AI is told to quote text only where it can read it clearly and to say when it is too small, rather than guess; check anything important against the transcript or a frame in the Screenshot Inspector.

### Worked example: did the error message show?

1. After recording, choose **Ask AI about this video...** in the result window.
2. Choose **A stretch of it**, from 2:10 to 2:40, with 12 frames.
3. Ask: "Is an error dialog visible in any frame? If so, quote its text and give the frame time."
4. Follow up: "Is any text cut off or too small to read?"

## Broadcast live to Icecast or SHOUTcast (unreleased)

**Capture > Broadcast live...** (Ctrl+Alt+Shift+G) streams a show to your own Icecast or SHOUTcast server, the kind internet radio stations use. You decide exactly what listeners hear, separately from what you hear and from any recording.

You need a server: one you run, or one from a streaming host. Your host gives you the address, port, mount or stream number, and the source password.

### Server

- **Server type**: Icecast or SHOUTcast.
- **Server address**: such as stream.example.org, without http.
- **Port**: as your host gave it, often 8000.
- **Mount (Icecast)**: such as /live. **Stream number (SHOUTcast)**: usually 1.
- **User name (Icecast)**: usually source.
- **Password**: the source password. Studio keeps it in Windows Credential Manager, never in its settings or logs, and fills it in next time.
- **Use a secure connection** only if your server offers it.

### About the show

**Show title**, **Description**, **Genre** and **Website** are what listeners' players and directories show. **List this stream in public directories** asks the server to list it; leave it off for a private stream.

### Sound quality

**Sound quality** offers plain-word presets:

| Preset | Sound | Upload needed |
|---|---|---|
| Speech: smallest, clear voices | MP3, 64 kilobits a second, mono | About 64 kilobits a second |
| Talk and music: a good balance | MP3, 128 kilobits a second, stereo | About 128 kilobits a second |
| Music: best sound | MP3, 192 kilobits a second, stereo | About 192 kilobits a second |
| Custom: choose everything | Your choice | Depends on your choice |

**Custom** unlocks **Format** (MP3, AAC, Ogg Vorbis, Ogg Opus or FLAC; SHOUTcast takes MP3 and AAC), **Bit rate** (16 to 320 kilobits a second), **Channels** (stereo or mono) and **Sample rate** (22,050 to 48,000 hertz).

**Loudness** can keep the stream sounding even, with a limiter against distortion:

- Off: send the mix exactly as it is.
- Even, for talk (minus 16 LUFS), the usual podcast level.
- Even, for music (minus 14 LUFS), the usual music-service level.
- Broadcast standard (minus 23 LUFS), the European broadcast level.

### What goes into the stream

**What goes into the stream** is a list like the recording one: your microphone, system sound without the screen reader, the screen reader's speech, and every program playing sound. Space puts a sound in or leaves it out. **Level in the stream, decibels** sets each one's level, separately from any recording. Everything starts left out, and the screen reader asks first. Studio's own sounds can never reach listeners.

### A saved copy

**Save a copy of the show on this computer** keeps a FLAC copy in **Folder for the saved copy**, even through a dropped connection. It is off by default: you decide each time, and the check reminds you when no copy is being saved.

### Check, test and go live

Press **Check**: you hear where the stream goes, what is in it, and every problem. A **Stop** blocks going live, for example no password stored or nothing in the stream. A **Warn** does not, for example the microphone not being in the stream, the screen reader being in it, or a quality needing more upload speed than your connection measured.

**Test the connection** sends two seconds of silence privately to check the address and password, without going live.

When nothing says Stop, press Enter or **Go live**. While live, the computer is kept awake and Do Not Disturb is on, and both are put back afterwards.

### While you are live

The **Live broadcast** window, which does not take focus, shows the **Status**: how long you have been live, whether you are connected, and how many times the stream has reconnected.

- **Now playing** and **Update the title** change the title listeners see, such as the name of the current segment.
- **Mute everything public** (Ctrl+Alt+Shift+Z) gives listeners silence at once without disconnecting. Press it again to bring the sound back. Use it for a cough, a phone call, or anything you do not want broadcast.
- **Stop broadcasting** (Ctrl+Alt+Shift+E) ends the show.

Both keys work while Studio has focus. Give them system-wide keys in **Capture > Capture global hotkeys...** so they work from any program; Mute everything public is the one to have under your fingers.

If the connection drops, Studio says so once and keeps trying: after 2 seconds, then waiting twice as long each time up to 30 seconds, for up to 10 tries. The saved copy keeps recording throughout. If it cannot reconnect, it says so and stops the stream; the saved copy continues until you stop.

### Worked example: a weekly talk show

1. Server: Icecast, your host's address, port 8000, mount /live, user name source, and the password. Press **Test the connection**.
2. Show title "Tech Talk Tuesday", genre "Talk". Sound quality: Talk and music. Loudness: Even, for talk.
3. In the stream: your microphone at 0, and your media player at minus 8 for music beds. Leave your screen reader out.
4. Turn on **Save a copy of the show on this computer** so you can post it as a podcast later.
5. Assign a system-wide key for Mute everything public.
6. **Check**, then **Go live**. Update **Now playing** at each segment, and stop at the end.
7. Use the saved FLAC copy with **Make a YouTube video from a picture and sound** to post the show afterwards.

### Broadcasting troubleshooting

- **Test the connection fails.** Check the address (no http), port, mount or stream number, and password with your host. Some hosts give a separate source port for SHOUTcast.
- **Listeners hear silence.** Check that something is in the stream, and that Mute everything public is off.
- **Listeners hear your screen reader.** Take it out of the stream list. System sound without the screen reader leaves it out automatically.
- **The stream keeps dropping.** Choose a lower quality. The check warns when a quality needs more than about 70 percent of your measured upload speed.
- **The password is not remembered.** Windows Credential Manager may be unavailable; enter it each time.

