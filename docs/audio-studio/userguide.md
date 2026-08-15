# QUILL Audio Studio User Guide

Version 2.2.0

(There is no Audio Studio 2.0 or 2.1: the Studio adopted the shared Quill family version number when it moved onto the shared runtime, so it went straight from 1.0.0 to 2.2.0. See the release notes for the full story.)

QUILL Audio Studio is audiobook and audio production the way a screen reader user would design it: a small home window whose book list has focus the instant it opens, a wizard that asks one question at a time and announces every step, a chapter editor you drive entirely by ear, and spoken progress for every long run. It runs the exact same Audio Studio code that ships inside the QUILL editor and shares QUILL's data store, so a voice you configure here reads aloud in QUILL too, and nothing you set up is ever stranded.

Three journeys cover the whole workshop:

- **Narrate Documents** - point at a folder of Word, Markdown, HTML, or text files and get speech audio, or one chaptered audiobook.
- **Build From Recordings** - point at a folder of audio you already recorded and get one chaptered master, each file a chapter.
- **Edit a Book** - open any finished MP3 or M4B in the Chapter Workbench: listen, fix chapters by ear, edit tags, run the ACX check, publish.

## Installing and running

### The QuillVille Runtime: install Python once, use it everywhere

Every QuillVille app - QUILL, Quill Radio, Quill Weather, and QUILL Audio Studio - now shares one Python runtime, called the **QuillVille Runtime**. It is installed once per user and reused by all of them. Install it a single time (with any Quill app), and every app you add afterward launches instantly, because the shared runtime is already there.

The runtime is reference-counted: it is removed only when the last app that needs it is uninstalled, so removing one app never leaves the others unable to start.

You choose how much of that runtime to download when you get the Studio. Four editions are offered:

- **Full portable** (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`, about 675 MB) - fully self-contained. It runs from a USB stick with no installation and no internet, carrying a genuine, unmodified copy of Python plus the bundled offline speech and text-to-speech engines (whisper.cpp, DECtalk, eSpeak-NG, Piper, and neural Kokoro). Best when you want everything in one folder with nothing to install.
- **Companion edition** (`QUILL-Audio-Studio-Companion-<version>.zip`, about 2 to 3 MB) - feather-light. It contains only the app and its docs, and runs on the shared QuillVille Runtime. The first time you launch it, if the runtime is not already installed, it offers to download and install it (about 230 MB, once) with a fully accessible progress bar. After that, this app and every other QuillVille app start instantly. Best once you already run, or plan to run, more than one Quill app.
- **Full installer** (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`) - installs the shared runtime, if it is not already present, plus the app. See "The installer" below.
- **Thin installer** (the `-Lite` setup) - a tiny installer that downloads the shared runtime only if it is not already present, then installs the app.

Whenever the runtime is downloaded - by an installer or by an app's own first launch - it shows a fully accessible progress bar that works with NVDA, JAWS, and Narrator, announcing progress as a percentage. See "Downloading the QuillVille Runtime" below.

### The installer

Run the full installer (`QUILL-Audio-Studio-Setup-Shared-<version>.exe`) or the thin `-Lite` installer. Either one makes sure the shared QuillVille Runtime is present (installing or downloading it only if it is not) and then installs the Studio to its own folder with a Start Menu group (including a User Guide shortcut) and an uninstaller. Your data lives in the shared Quill store in your Windows profile (`%APPDATA%\Quill`), the same store QUILL, Quill Radio, and QUILL Cast use. Uninstalling never deletes that shared data, and never removes the shared runtime while another Quill app still needs it.

Windows SmartScreen may warn on first run because this release is not code-signed; choose "More info" then "Run anyway".

### The portable zip

Extract the full portable zip (`QUILL-Audio-Studio-Portable-Lean-<version>.zip`) anywhere - even a USB stick - and run `QuillAudioStudio\QuillAudioStudio.exe`. This edition needs no runtime download: it bundles its own genuine, unmodified copy of Python and the offline speech engines, so it runs with no installation and no internet. The portable switch is a `data` folder next to the exe that contains a `storage-mode.json` marker file holding `{"mode": "portable"}`. When that folder and marker are present, all settings, voices, downloaded engines, and your book list live inside the app folder, so the whole studio travels with you. The portable zip ships this marker already in place; the installed copy ships no `data` folder and uses the shared `%APPDATA%\Quill` store instead.

Both packaged flavors bundle ffmpeg and the mpv player engine in a `tools` folder next to the exe, so audiobook building and high-fidelity playback work out of the box.

### Downloading the QuillVille Runtime

When you run the Companion edition or the thin installer and the shared runtime is not yet on your machine, the Studio offers to download it - about 230 MB, one time. This download always shows a **fully accessible progress bar** that works with NVDA, JAWS, and Narrator, whether the download was triggered by the installer or by the app's own first launch. Progress is announced as a percentage, so you always know how far along it is and never face a silent wait. Once the runtime is installed, this app and every other QuillVille app start instantly, and you are never asked to download it again unless every Quill app has been removed.

### A note on antivirus

The Studio's launcher is now a genuine, tiny native program, and the bundled Python is the official unmodified build. Earlier versions used a renamed and modified copy of Python's `pythonw.exe` as the launcher, which some antivirus tools flagged as a false positive. That pattern is completely gone, so the Quill apps are far less likely to be flagged. If an antivirus tool ever does flag a Quill app, it is a false positive; the downloads come from the project's official releases.

### Running from source

From a checkout of the repository:

- `pip install -e ".[ui]"` then `python -m quill.apps.studio`, or
- run `run-quill-audio-studio.bat`, which finds a Python environment for you (this repo's `.venv`, then a sibling QUILL checkout's `.venv`, then whatever `python` is on PATH).

`run-quill-audio-studio-safe-mode.bat` launches with Safe Mode on (see "Safe Mode" below).

## The home window

The window opens with keyboard focus on your books list. From top to bottom:

- **Studio activity** (read-only text): what the Studio is doing right now - "Ready", or live progress during a run. The same text is mirrored in the status bar.
- Three buttons, one per journey: **Narrate Documents...**, **Build From Recordings...**, **Edit a Book...**
- **Your books**: your audiobooks, organized as a tree (see below). Press **Enter** to open the selected book in the Chapter Workbench. A book whose file has been moved or renamed is marked "(missing)".

### The status bar

The status bar reads "Ready - N books in your library" when idle. During a long run it carries per-file progress, and by default the Studio also speaks the 25, 50, and 75 percent milestones so you can follow an overnight narration from another window (turn this off in Preferences).

You can read the bar rather than wait for it to speak. Press **F6** to move focus into it, then **Left** and **Right** to move between its cells:

- **Activity** - what the Studio is doing right now.
- **Progress** - a live narration or build run: the percentage, how many files are done, and the current step.
- **Sleep timer** - the timer's state, when one is set.
- **Your books** - how many books are in your library.
- **Time** - the current time.

Press **Enter** to act on the cell you are on, use the context menu (Application key, or Shift+F10) for what that cell offers, and press **Escape** or F6 again to leave the bar and return to the window. **View > Show Status Bar** hides or shows it, and the Studio remembers your choice.

The Progress text is also written into the system-tray tooltip, so a long run is still reviewable when the window is minimized to the tray.

### The library tree

The library fills in as you work: every book you open in the Chapter Workbench joins it, and you can shape it yourself with Favorites and folders. Books are grouped into four built-in collections and any folders you create:

- **Favorites** - books you have marked as a favorite.
- **In Progress** - books with a saved listening position you have not finished.
- **Recently Played** - the books you have opened most recently.
- **Inbox** - everything else.

Expand and collapse the groups with Left and Right. Press **Enter** on a book to open it in the Chapter Workbench. The context menu (Application key, or Shift+F10) is keyboard-complete on both books and folders: **Open**, **Reveal in Folder**, **Favorite** (toggle), **Move to Folder**, **New Folder**, and **Remove**. **Reveal in Folder** opens your operating system's file manager (Windows File Explorer, or the macOS Finder) with the book file selected, so you can find it on disk. **Remove** takes the book out of your library but never touches the file on disk, and says so. The tree remembers which book you had selected when the library reloads.

## The Studio wizard

**Studio > Open Audio Studio...** (Ctrl+N) opens the wizard. Its first page asks the one question that matters - what would you like to make? - and the following steps adapt to your answer. The wizard remembers which journey you used last and pre-selects it.

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
- **File types to include** - Word (`.docx`), Markdown (`.md`), HTML (`.html`, `.htm`), plain text (`.txt`). Tick any combination.
- **Include / Exclude files matching** - optional glob filters, semicolon- or comma-separated.
- **Skip files larger than (MB)** - a size cap so one accidental 400 MB export cannot hijack a run (0 = no limit).
- **Count documents** - counts the matching files and their words off-thread and announces the settled number: "12 document(s) found, about 84,000 words." The count also refreshes automatically when you browse to a folder or arrive on the page.

### Who should read it?

- **Engine** - Windows (SAPI 5), DECtalk, Piper (neural, offline), Kokoro (neural, offline), eSpeak-NG (many languages); on a Mac, the macOS system voice as well. An engine that is not installed yet is labeled "(not installed)" - see "Voices" below for downloading it.
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

## Copy Sections

**Voices > Copy Sections...** takes pieces out of an audio file and collects them
into a new one. It is for the job that always used to mean doing the same thing
six times: pulling the four quotes you want out of a long interview, or the songs
you actually want out of a four-hour recording of a broadcast.

Play the file, and as you listen:

- **Mark Start** when a piece begins and **Mark End** when it stops. Either can
  be set first, and either can be moved as often as you like -- a mark is a
  position, not a commitment, and nothing is written until you ask for a file.
- **Preview Marked** plays from your start mark so you can hear whether you got
  it right before keeping it.
- **Add to List** collects it, and clears the marks so you can go and find the
  next one.

The list is what will be saved, in the order shown -- **Move Up** and **Move
Down** change that order, **Play This One** replays any collected piece, and
**Remove** drops one. Each row reads as a whole sentence, so there are no columns
to arrow across.

Then either **Save as New File...**, or **Add to an Existing File...** to put
what you collected onto the end of a file you already have. That second one is
the reason for collecting at all: the fourth quote from the third interview joins
the three already in the file.

**Your original file is never changed.** Not on marking, not on preview, not on
save -- everything is written somewhere else. And if a save fails part way
through, the file you were saving into is left exactly as it was rather than half
written.

There is no waveform display, deliberately. A waveform is a picture of the audio
for people who can see it; listening to the marked range tells you the same thing
and tells it more reliably.

## Voices

### Engines

- **Windows (SAPI 5)** - every voice installed on your PC, in any language; zero downloads.
- **DECtalk** - the classic formant synthesizer, downloadable on demand.
- **Piper** - neural voices that run entirely offline; download individual voices from a catalog.
- **Kokoro** - modern neural voices, entirely on your machine, in several languages; a one-time model download.
- **eSpeak-NG** - compact and fast, speaks a very large number of languages.
- **macOS (system voice)** - on a Mac, the system `say` voices.
- **Cloud voices** - ElevenLabs on the Speech Hub's online tab, and OpenAI / Gemini / ElevenLabs multilingual voices as translation-target voices. All require your own API key and are never used without it.

### The Speech Hub

**Voices > Speech Hub (Voices and Engines)...** is the one place to see and set everything: offline voices on one tab, cloud voices on another, and the speech-recognition (dictation/transcription) engines and models alongside. Pick an engine and voice, adjust rate, volume, or speed, preview, and **Set as Default**. Voices you configure here are shared with QUILL - and the hub's "export to audio" action opens the Audio Studio wizard, because in this app that is what export means.

### Pronunciation dictionaries

**Voices > Pronunciation Dictionaries...** opens the same manager QUILL uses to teach the speech engines how to say tricky words - names, acronyms, invented terms. Each entry maps what is written to how it should be spoken, and dictionaries apply as a silent text transform to both narration runs and live Read Aloud. Because this is shared QUILL data, a correction you make here is honoured everywhere the shared store is used.

### Voice previews

Every preview speaks the same standard phrase, so voices are directly comparable. When a bundled sample ships for a voice, the preview plays instantly - even before the engine is downloaded. When no sample ships but the engine is installed, the Studio synthesizes the phrase live with the real voice; if that synthesis is taking a moment, you hear "Generating preview, please wait" so silence never leaves you guessing. If neither a sample nor an installed engine is available, the status line says "Download this voice to hear a preview." Starting a new preview always stops the previous one; previews never overlap.

### Generate captions from audio or video

**Voices > Generate Captions (Offline)...** transcribes an audio or video file into a `.srt` or `.vtt` caption file entirely on your own machine - nothing is uploaded. Point it at a recording, a finished chapter, or a video, and it writes captions alongside. It uses the same speech-recognition models as the Studio's other transcription work, so if none is installed yet it offers to fetch one first (see "Downloading voices, engines, and components").

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

- The Speech Hub offers **Download Voice** for Piper voices and the Kokoro model pack, and engine downloads for DECtalk, Piper, and eSpeak-NG right where you would use them.
- **Voices > Manage Speech Models...** manages the speech-recognition models (used by transcription-backed features such as AI chapter titles), matched to your machine's memory and GPU.
- **Voices > Download Optional Components...** is the hub for everything else: see what is installed versus available, download, **Test** it in place, or **Remove** it. The audio pack here bundles the mpv player engine and ffmpeg in one download.
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

- **Resume on launch** (a check item, off by default) - when set, launching the Studio reopens the most recently played book at its saved position. If that file no longer exists, it stays closed silently.
- **Recently Played** (a submenu, rebuilt each time you open it) - the books you have played most recently. Pick one to open it in the Workbench.

## Preferences

**Studio > Preferences...** (Ctrl+Comma):

- **Check for updates automatically on launch** - a quiet daily check; see "Checking for updates".
- **Alt+F4 minimizes to the system tray** (off by default) - when on, Alt+F4 tucks the Studio into the tray with any narration run still going, instead of closing the window. The titlebar X and Studio > Exit keep the "When closing the window" behavior.
- **Speak progress milestones during long runs** (on by default) - announce 25, 50, and 75 percent during a narration or build run.
- **When closing the window** - Ask when work is running / Exit / Minimize to Tray. "Ask" only prompts while an export is still going; an idle window just closes. The prompt names the work that would be lost and defaults to keeping the Studio open.

These preferences are stored in a small app-local file, so the shared settings QUILL wrote stay exactly as QUILL wrote them. Speech settings (engine, voices, rates) deliberately stay in the shared store - configure a voice here and QUILL reads aloud with it too.

## The system tray

QUILL Audio Studio's icon is three white-and-gold waveform bars on a dark slate tile. If you have used an earlier build, this is new: the Studio used to share Quill Radio's blue broadcast-wave icon, so on a desktop with more than one QuillVille app installed several of them looked identical. Every app in the family now has its own - the same rounded tile shape and the same gold accent throughout, but its own colour and its own picture each.

While minimized to the tray the Studio keeps running - a long narration continues with the window tucked away. Right-click (or keyboard-invoke) the tray icon for:

- **Open Audio Studio...** - restore the window and open the wizard.
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

All the Quill apps are published from one place, and each one recognizes its own download, so an update to Quill Radio is never offered to the Studio and each app updates on its own schedule. The automatic startup check (on by default, throttled to once a day) is silent unless it actually finds something.

## The Command Palette

**Help > Command Palette...** (Ctrl+Shift+P) lists every Studio command in one searchable list: the three journeys, Open Job File, Publish, the podcast feed, the ACX check, Sleep Timer, Mute Playback, Play Queue, the Speech Hub, Pronunciation Dictionaries, Generate Captions, Convert Audio, Convert from URL, model and component downloads, AI setup, Preferences, and Check for Updates. Type a few letters, arrow to the command, press Enter.

## Quillins

**Quillins** are QUILL's small, sandboxed, permission-gated add-ons. They run in QUILL, Quill Radio, and QUILL Cast today; **Audio Studio does not offer a Quillins menu yet.** The groundwork is in place - an add-on can declare that it contributes an extra step to the Studio's audio processing, such as a loudness pass at the mastering stage, and a sample add-on demonstrates exactly that - but the Studio does not load add-ons in this version. When it does, they will be off in Safe Mode like everywhere else.

## Keyboard reference

| Action | Key |
| --- | --- |
| Open Audio Studio (the wizard) | Ctrl+N |
| Open Book File | Ctrl+O |
| Preferences | Ctrl+Comma |
| Command Palette | Ctrl+Shift+P |
| Move focus to the status bar (and back out) | F6 |
| Open selected book (in Your books) | Enter |
| Remove selected book from the list | Delete |
| Play selected chapter (Workbench list) | Enter |
| Rename chapter (Workbench title field) | Enter |
| Mute (player / shell) | Ctrl+M |
| Media Play/Pause (when a Workbench is open) | Media key |
| Media Stop (when a Workbench is open) | Media key |
| Media Next chapter (when a Workbench is open) | Media key |
| Media Previous chapter (when a Workbench is open) | Media key |
| Studio menu | Alt+S |
| Book Tools menu | Alt+B |
| Voices menu | Alt+V |
| AI menu | Alt+A |
| Help menu | Alt+H |

Every button and field in the wizard, the Workbench, and the dialogs also has an access key (underlined letter), reachable with Alt plus that letter while the surface has focus.

## Safe Mode

Set the environment variable `QUILL_SAFE_MODE=1` or pass `--safe-mode` (or use `run-quill-audio-studio-safe-mode.bat`). Safe Mode disables AI features, publishing, and component downloads; everything local - narration with installed engines, the Workbench, saving - keeps working. Use it to isolate a problem or to run on a machine where network features are unwelcome.

## Sharing data with QUILL

The Studio reads and writes the same data store as QUILL, Quill Radio, and QUILL Cast: `%APPDATA%\Quill` for an installed copy, or the `data` folder next to the exe (marked by a `storage-mode.json` file holding `{"mode": "portable"}`) for a portable one. Shared between the apps:

- Speech settings: engine, voices, rates, chapter sound.
- Downloaded engines and models: DECtalk, Piper voices, Kokoro, eSpeak-NG, speech-recognition models, the mpv engine.
- Your books list, recent source folders, and per-book listening positions.
- AI provider configuration and service keys (keys live in the Windows Credential Manager).

Only the handful of window-behavior preferences above are app-local. Uninstalling the Studio never deletes the shared data.

## Troubleshooting

Two Help items are worth knowing before anything else goes wrong. **Help > View Log...** opens the Studio's own log, so you can read what happened during a run instead of guessing. **Help > Save Diagnostics...** writes a small, redacted zip - the log plus what the Studio can tell about your machine and settings, with anything private scrubbed - which is exactly what to attach to a bug report. **Help > Report a Bug...** files one for you, already tagged with this app's name and version.

- **"The ACX check measures loudness with FFmpeg, which looks missing."** Choose **Voices > Get FFmpeg...** The same applies if compressed output formats fall back to WAV, audiobook assembly fails, or silence detection cannot run - all of those are ffmpeg's jobs. The packaged installer and portable zip bundle ffmpeg; this mostly affects source checkouts.
- **An engine shows "(not installed)" in the wizard.** Open **Voices > Speech Hub** and use the download button on that engine's tab, or **Voices > Download Optional Components...** DECtalk, Piper, eSpeak-NG, and the Kokoro models all install on demand.
- **The Preview voice button says "Download this voice to hear a preview."** No bundled sample ships for that voice and its engine is not installed yet; download the engine or voice first.
- **A Piper voice is selected but will not speak.** The voice model has not been downloaded; the Speech Hub's Download Voice button fetches it.
- **A book in Your books is marked "(missing)".** The file was moved or renamed. Open it from its new location with Ctrl+O (the list updates), or press Delete to drop the stale entry.
- **The Save button is disabled in the Workbench.** The book is an M4B; use **Save As...** - M4B chapter data cannot be rewritten in place, so the Workbench re-muxes losslessly to a new file.
- **"Propose AI titles" says it needs a configured AI provider.** Run **AI > Set Up AI...** first - or you are in Safe Mode, where every AI surface is disabled.
- **A translated edition was skipped.** The cloud voice you chose for that language has no API key configured; the run notes the skip and continues rather than stopping.
- **Closing the window warns about work in progress.** A narration or build run is still going. Choose No to keep the Studio open, or minimize to the tray and let it finish; the "When closing the window" preference sets a fixed answer.
- **Windows SmartScreen blocks the installer.** The release is not code-signed; choose "More info" then "Run anyway".
