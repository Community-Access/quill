# QUILL Studio 2.0.0 - Release Notes

Built, not yet released.

## Since build 2: speech engines, licensing and the chapter sound

QUILL no longer downloads or distributes DECtalk while its redistribution
terms are unclear. New Studio portable staging excludes it; separately
installed copies remain supported. Earlier packages still need review.
Windows OCR and Media projections move to PyWinRT 4.0.3 and Windows SDK
10.0.28000.2705; the Windows Media engine also releases device references and
event handlers at shutdown.

Installed Studio uses the shared QuillVille Runtime, which currently includes
PyMuPDF 1.28.2 under AGPL-3.0 through GLOW. Studio does not itself expose GLOW.
Release-specific source and legal review remain open; portable packages must
be checked separately. The default chapter transition is now an original
synthesized page-turn-like sound; you can still choose your own.

The expanded Studio editing, Converter round-trip and AI transcription
workflows in the planning PRD are proposed, not part of this release claim.

## QUILL Studio 2.0.0 follows Audio Studio 1.0.0

QUILL Studio 2.0.0 follows Audio Studio 1.0.0. The previously unpublished 2.2.0 build is renumbered to 2.0.0 with the QUILL Studio rename. Studio continues to use the shared QuillVille Runtime; each app has its own release version.

This build has not been published. QUILL Studio is not yet offered in the cross-app menu and there is no 2.0.0 download page. What follows is what is in the build, waiting on the release.

## A new name: QUILL Studio

QUILL Audio Studio is now **QUILL Studio**. The window, the tray, the wizard, the installer and the shortcuts use the new name. Nothing else moves: an installed copy upgrades in place, your books, voices, settings and shared data stay where they are, and the old command-line name still works.

## Screenshots, global hotkeys, and a Screenshot Inspector (AI optional)

A new **Capture** menu adds screenshot capture tools directly in Studio. These features are available without enabling AI; AI inspection is an optional extra for describing or discussing what is in an image.

Highlights:

- **Capture menu and command palette coverage.** Every capture action is available from the menu bar and **Help > Command Palette...** (Ctrl+Shift+P).
- **A shorter window list with an escape hatch.** Capture screen lists top-level task windows by title (similar to Alt+Tab) so the picker is readable. Enable "Show all windows (advanced)" when you need tool windows, and use "Window properties..." for process IDs and other identifiers. If you only see Desktop/Display targets, update: a preview build had a regression that hid windows from the picker.
- **Wizard entry point.** **Studio > Open Studio Wizard...** (Ctrl+N) includes a Capture journey so you can start a screenshot run from one place.
- **Minimize-to-tray on demand.** **Studio > Minimize to Tray** (Ctrl+Alt+T) hides the window in the system tray without exiting.
- **Library window instead of a book-centric home.** The home window stays intentionally quiet; open **View > Library Window...** (Ctrl+Alt+Y) to browse and manage books.
- **Preferences close is silent.** Leaving Preferences updates the status line but does not speak "Preferences saved".

## Record a demonstration: screen, camera and sound, checked before and after

**Capture > Record a demonstration...** (Ctrl+Alt+Shift+V) records what you are showing and only what you choose to let people hear. It is built for a presenter who cannot see the screen: you set it up from lists and check boxes, hear one summary before you start, and are told afterwards what is really in the file.

- **Any combination.** Two check boxes, Include the screen picture and Include the camera picture, and a list of sound sources. Record the screen, the screen with your camera in a corner, the camera alone, or sound only. Sound-only recordings are saved as M4A, MP3, WAV, FLAC or Opus. A video with no sound gets a silent soundtrack by default, because some websites refuse a video without one.
- **What to record.** A named window, one display or the whole desktop, at 15, 24, 30 or 60 frames a second, optionally scaled to 1080p or 720p, with or without the mouse pointer, after a spoken countdown.
- **Your screen reader stays private.** Each program's sound is recorded directly from that program, so a demonstrated browser is recorded without your screen reader. System sound can be recorded with the screen reader left out. Screen reader speech is a separate source that starts left out and asks before it goes in.
- **Every sound is your choice.** The program you are demonstrating, system sound, any other program, everything on one sound card, your microphone and your screen reader, each in or out with its own level from minus 60 to plus 12 decibels. The microphone starts left out every time. Each source can also be kept as its own WAV file for editing later.
- **The camera, with face framing.** Put your camera in any corner at the size you choose. Check camera framing (Ctrl+Alt+Shift+C) tells you as you move whether your face is in view and which way to move, using face detection built into Windows that runs on your computer. During a recording Studio can tell you when your face leaves the picture.
- **Keep awake and Do Not Disturb.** Both are on by default while you record, so the computer does not sleep and no notification slides into the picture or the sound. Both are put back exactly as they were afterwards, even after a crash.
- **One spoken check before you start.** Check takes a trial picture, records three seconds to see whether the computer keeps up, opens each sound source, and looks at the camera, FFmpeg, the folder, free space, the battery and any waiting Windows Update restart. It says what will be recorded, which sounds are in, which are left out, and every problem, as Stop or Warn. It catches a microphone that Windows privacy settings have silenced.
- **A quick test.** Record a quick test makes a 5-second to 10-minute rehearsal with exactly these settings, checks it and plays it, then deletes it.
- **Control from anywhere.** Pause, markers, microphone mute, a spoken status, a status window that never takes focus, an emergency stop and discard, from the Capture menu, the tray icon's menu, or system-wide keys you assign.
- **Problems are said once and marked.** A window closing, a program or your screen reader quitting, a microphone unplugged, a display change, the camera stopping, or the disk running low are announced once and marked in the recording. A different microphone is never swapped in.
- **The finished file is checked independently.** After Stop the file is reopened and checked: its streams, length, frame count, clean decoding at the start, middle and end, black stretches, and that each sound source is really there. You hear one sentence, and the result is Verified, Needs review or Failed. A readable report and a JSON report are saved beside the video.
- **Nothing is lost.** Studio records in short pieces. If Studio or the computer stops, Recover unfinished recordings (Ctrl+Alt+Shift+L) finishes and checks what was recorded.
- **Captions and a transcript.** The result window makes SRT and VTT captions and a plain transcript on your computer, with the speech recognition you already use. Nothing is sent anywhere.

## The Studio Mixer

**Capture > Studio Mixer...** (Ctrl+Alt+Shift+M) is one window for the sound you hear. The Programs tab lists every program playing sound: mute it with Space, set its volume from 0 to 100 percent, or move it to another sound card, as Windows Settings does, for example a browser to the speakers while your screen reader stays in your headset. The Devices tab sets the default and communications devices, and a microphone's recording level and mute.

## ASIO sound cards

Professional audio interfaces with an ASIO driver can be used as microphones with the lowest delay. Open Studio > Preferences, turn on Use ASIO sound cards, and restart Studio. It is off by default.

## Make a picture with AI

**Capture > New picture with AI...** (Ctrl+Alt+Shift+J) makes a picture from your description with OpenAI or Google Gemini, wide for YouTube, square for a cover, or tall for Shorts. Ask for changes in words; every version is kept. Each picture is then described to you by a separate look from your vision model, so you hear what was actually drawn, including any text exactly as written. Nothing is sent until you approve, and AI Off and Safe Mode stop it.

## A picture and sound as a YouTube video

**Capture > Make a YouTube video from a picture and sound...** (Ctrl+Alt+Shift+Y) turns a recording or any audio file into a video YouTube accepts, with your picture for the whole length. Choose YouTube, square, vertical or the picture's own size, a slow zoom, and a sound wave along the bottom. A recording's markers become YouTube chapters. A text file beside the video holds the title and the description with chapter times, ready to paste into YouTube.

## Ask AI about a video

**Capture > Ask AI questions about a video...** (Ctrl+Alt+Shift+K) asks about the whole video or a stretch you choose. Studio lays out 4 to 16 frames as one picture with each frame's time on it, adds the transcript of that stretch when there are captions, and opens the same conversation window as the Screenshot Inspector. Answers cite the frame times they rely on. Nothing is sent until you approve.

## Broadcast live to Icecast or SHOUTcast

**Capture > Broadcast live...** (Ctrl+Alt+Shift+G) streams a show to your own Icecast or SHOUTcast server.

- **Plain-word quality.** Speech, Talk and music, or Music, or Custom for the format (MP3, AAC, Ogg Vorbis, Ogg Opus or FLAC), bit rate, stereo or mono, and sample rate. Loudness can keep the stream even at talk, music or broadcast level.
- **You choose what listeners hear.** The microphone, system sound without the screen reader, the screen reader's speech, and every program, each in or out with its own level, separate from any recording. Everything starts left out. Studio's own sounds never reach listeners.
- **Show details.** Title, description, genre, website, public listing, and a Now playing title you can change while live.
- **Safe controls.** Mute everything public (Ctrl+Alt+Shift+Z) gives listeners silence at once without disconnecting; Stop broadcasting is Ctrl+Alt+Shift+E. Both can be system-wide keys.
- **Check and test first.** Check says where the stream goes, what is in it, and every problem, including an upload speed too slow for the quality. Test the connection checks the address and password with two seconds of silence, privately.
- **Keeps going.** A dropped connection is announced once and retried automatically. An optional FLAC copy of the show is saved on your computer throughout; you decide each time.
- **Your password stays private.** It is kept in Windows Credential Manager, never in settings or logs.

## Lessons from Quick Describe, with thanks to Kelly Ford

Kelly Ford's Quick Describe, a free, open-source app that describes the screen with Windows' own AI, shares what it learned the hard way, and Studio took several of those lessons. The Recording status window can now stay visible to magnifiers and screen sharing. Ask AI about a video draws fewer frames bigger, labels their times clearly, and tells the AI to say when text is too small rather than guess. A face detector that stops answering is replaced, and gives up out loud rather than going quiet. "Automatic screenshot AI is paused" is said once, not with every screenshot. Diagnostic bundles leave out your user name. Thank you, Kelly, for the ideas and for all you give to the community.

## Sharp at any display scaling, and named controls

QUILL Studio handles each monitor's scaling itself, so text stays sharp at 125, 150 and 200 percent and on monitors with different scaling. Controls that had no label, in Convert Audio, the wizard's summary and the translated speech export, now have a spoken name.

## Not yet verified

These features are built and tested with real FFmpeg runs and with stand-in servers and services, but the following have not yet been done: recordings with a real microphone and camera, face detection with a person in front of the camera, JAWS, NVDA, Narrator and braille passes, a real Icecast or SHOUTcast server, and a real AI picture request. A window recording records the window's area of the screen, so a covering window is recorded and a moved window is not followed.

## Chapters for any recording

**Studio > Find Chapters in a Recording...** (Ctrl+Shift+R) picks any MP3, M4A or M4B -- a lecture or a meeting as much as a book -- and opens the Chapter Workbench on it with **Propose chapters from silences** already started. Proposals are titled "Proposed chapter 1, 2...", so a guess is never mistaken for a real title. If the recording has chapters of its own you are asked whether to keep them and add only new boundaries (the default) or replace them; nothing is replaced silently. Press the button again (it reads **Stop proposing chapters**) to stop a scan.

## Sliders that go the way you expect, and Slider Keys to choose

Up and Page Up raise the player's Position and Volume sliders and Down and Page Down lower them, in every Quill app. Home and End go with them: Home is the top of a volume slider, 100 percent, and End the bottom. If you would rather have the keys a standard Windows slider uses, open **Studio > Preferences...** (Ctrl+,) and choose the **Slider Keys...** button: **Up is more** (the default) or **As Windows sliders** (Down, Page Down and End raise it). It is one choice for every Quill app at once. Right is always more and Left less, and each key press tells your screen reader the new value. Ctrl+Up and Ctrl+Down, the volume keys that work from anywhere in the apps that have them, are not changed.

## The Studio's own sounds, where you want them

The **App Sounds Play On...** button in **Studio > Preferences...** (Ctrl+,) sends the Studio's own sounds to the system default, to any sound card or headset by name, or nowhere. **Alt+Shift+M** turns them off and back on where they were, and **Studio > App Sounds** shows a check mark while they are on. Your screen reader is never moved.

## What's New, and a guide that matches the menus

**Help > What's New** (Ctrl+Shift+F1) opens the Studio's changelog in your browser, on the same key as every other Quill app. The user guide has a new section on the speech-recognition engines (Whisper.cpp, the QUILL speech models such as Parakeet and Nemotron, and Faster Whisper) and how to download them, and its keyboard reference now matches the menus: Alt+V is the View menu and Alt+I the Voices menu.

## Install Python once, and every Quill app starts instantly

The single biggest change is how the Studio is delivered. Every Quill app - QUILL, Quill Radio, Quill Weather, and QUILL Audio Studio - now shares one Python engine, the **QuillVille Runtime**, installed once per user and reused by all of them. Install it a single time with any Quill app, and every app you add afterward launches immediately instead of downloading its own copy of everything. The runtime is reference-counted: it is removed only when the last app that needs it is uninstalled, so removing one app never leaves another unable to start.

The Studio comes as two downloads. The **portable** zip (about 675 MB) runs from a USB stick with no installation and no internet, carrying a genuine, unmodified copy of Python plus the offline speech and text-to-speech engines. The **installer** installs the shared runtime, if it is not already present, plus the app. The installer now also offers a choice of setup: Full, Compact (the program without the bundled documentation), or Custom.

Earlier test builds also came as a small "Lite" installer and a "Companion" zip. Those are gone. Take the installer in place of the Lite installer, or the portable zip in place of the Companion zip.

The Studio's launcher is now a genuine, tiny native program, and the bundled Python is the official unmodified build. Earlier versions used a renamed and modified copy of Python's own launcher, a pattern some antivirus tools flagged as a false positive. That pattern is gone, so the Quill apps are far less likely to be flagged. Releases are still not code-signed, so SmartScreen may caution on first run.

## Update in one click

When an update is available, choose **Download**, then **Install and restart now**. The Studio applies the update itself - extracting the new portable files over your folder, or running the installer quietly - and relaunches, keeping every setting, voice, and book position. No closing the app, unzipping, and swapping folders by hand.

**Help > Check for Updates...** now looks at the shared Quill project releases and picks out the Studio's own download for the flavor you run. Each app updates on its own schedule from that one place, so an update to Quill Radio is never mistaken for an update to the Studio.

## A status bar you can actually read

The Studio's status bar used to be a strip of text a screen reader could not review. It is now arrow-navigable, exactly like the one in QUILL and Quill Radio: press **F6** to move focus into it, Left and Right to move between cells, Enter to act on the one you are on, and Escape or a second F6 to leave. The cells are Activity, Progress, Sleep timer, Your books, and Time, so "what is going on right now" is always one key away.

The Progress cell carries a live narration or build run - the percentage, how many files are done, and the current step - and the Studio writes the same text into its system-tray tooltip. An overnight narration therefore stays reviewable with the window tucked into the tray, instead of going quiet the moment you minimize it. **View > Show Status Bar** turns the bar on or off and remembers your choice.

## Converting audio, without leaving the Studio

**Voices > Convert Audio...** changes audio files between formats - MP3, M4A/M4B, Opus, Ogg, FLAC, WAV, AAC and more - and pulls the audio track out of video files (MP4, MKV, MOV, WebM and the rest) along the way. It converts through the ffmpeg the Studio already bundles, so there is nothing new to install, nothing is uploaded, and it works in Safe Mode.

Build a queue of files and whole folders, pick a destination, and choose one of ten presets: Just convert (no processing), MP3 at 320, 192 or 128 kbps, Podcast, Audiobook M4B, Voice memo, Web voice (Opus), Archival (FLAC), and Hearing-aid mono. The format list only ever offers what your ffmpeg can genuinely encode, so a long batch cannot die half way for a missing encoder. Conversion runs in the background with several files at once, a real Cancel, and a spoken summary at the end that **names the files that failed** rather than quietly reporting success. Progress appears in the status bar's Progress cell and the tray tooltip, the same as a narration run.

An Advanced panel is there when you want it, and neutral when you do not: loudness normalization to audiobook (ACX) or podcast level, gain, a high-pass filter, silence trimming, pitch-preserving tempo, a compressor, a night-mode leveler, fade in and fade out, and a safety limiter.

**Voices > Convert from URL...** takes a link - YouTube and the many other sites the downloader supports - fetches the audio, and drops it straight into the converter. The downloader is never bundled: it installs on demand after a one-time consent and rights notice, and the whole feature is unavailable in Safe Mode.

## Announcements reach your braille display

A braille user reported that messages the app speaks never appeared in braille. The diagnosis was blunter than the report: nothing had ever been sent to a braille display at all - not by this app, not by any of them. A whole output channel was missing.

Braille is now written at the same point as speech, so every message the Studio makes is covered at once. Three rules govern it:

- **Braille never costs speech.** An unplugged display, a screen reader that rejects the call, a bridge without the capability - all of them degrade to "spoke but did not braille", never to silence.
- **Nothing is truncated.** Clipping a message to the display width would drop the end of the very thing you asked for, and both readers let you pan a flash message anyway.
- **The display is not stolen twice.** An identical message inside two seconds is skipped, because a flash message physically replaces whatever is under your fingers. A burst of different messages no longer flickers past faster than cell one can be read: the first message of a quiet period writes instantly, and anything landing in the next fraction of a second settles to the newest instead of each shoving the last aside. Errors are exempt and always write through at once.

Behind that, speech, braille, sound, and the status line are now delivered by one shared announcement service - the same one QUILL uses - so a channel added anywhere appears in every app. Announcements are recorded as they go, so a message that passed while you were reading something else is not simply gone.

New shared accessibility settings control the braille style (the full spoken string, or a compact position-first form), how long an identical braille message is held back, whether an error sticks on the display instead of flashing past, whether the companion apps play sound cues, whether a cue stands in for speech while Quiet Mode is on, and which severities interrupt speech. The Studio's own Preferences dialog stays the short list it has always been; these live in the settings store the Studio shares with QUILL, so setting them in QUILL applies here too.

## A transcription engine that cannot make things up

Whisper — the engine most offline transcription runs on, the Studio's
included — has one famous flaw: fed silence, it sometimes *invents* text. A
pause in a recording can come back as a phantom "thank you" or a subtitle
credit that nobody said, because under the hood Whisper is a language model
guessing at what silence "should" say.

The Studio now offers **Parakeet 3**, an NVIDIA model that works the other way
round: it only writes down words it actually heard, so silence produces
nothing — which matters for exactly the material a studio transcribes, long
recordings full of pauses. It covers 25 languages and detects which one is
being spoken, runs on any CPU with no graphics card and no heavy libraries,
and downloads (about 650 MB, checksum-verified from QUILL's own mirror) from
the same model manager as every other engine. Every engine and model in that
manager now also states its capabilities in plain language — "detects the
spoken language; never invents text from silence" — *before* you download,
so choosing is no longer guesswork.

Alongside it, a silence pre-pass now trims the quiet lead-in and tail from
captured audio before any engine hears it, and your custom vocabulary (names,
product words, jargon) is fuzzy-matched into finished transcripts so a name
the engine mangles still comes back spelled your way.

## Built from QUILL's own source

The Studio used to be assembled from a copy of QUILL's audio code kept in a separate repository and re-synced by hand. It is now built directly from QUILL itself. Nothing changes in what you see, but the standalone Studio and QUILL's built-in Audio Studio can no longer drift apart, and a fix made upstream is in the next Studio build with nothing to copy across.

Two smaller results of the same work: Piper voices now download from the project's own signed mirror rather than a third-party model host, so a voice download no longer depends on an outside service being reachable from your network; and the shared components each app needs (ffmpeg, for the Studio) are counted, so uninstalling one Quill app can never take away something another app still needs. The build also leaves out the large libraries the Studio never loads, making both the installer and the portable zip meaningfully lighter.

## An icon of its own

Until now QUILL Audio Studio shipped a **byte-identical copy** of Quill Radio's blue broadcast-wave icon -- not a similar drawing, the same file. So did Quill Inkwell and Quill Weather. On a desktop with more than one Quill app installed, four different products wore one face in the taskbar, in Alt+Tab, in the Start menu and in the notification area, which for a tray-resident app is where it lives its whole life. Nobody chose that; each new app was built from the last one's template, and an icon is easy not to notice.

Every app in the family now has its own. They are still recognisably a set -- one rounded tile shape, one gold accent -- but each has its own colour and its own picture. The Studio's is a three-bar waveform on a dark slate tile: editing audio rather than broadcasting it, and the only glyph in the family built from repetition.

The drawing was made for the size that actually matters. At 16 by 16 pixels -- the notification area, and the small icons in a file list -- a first attempt with five bars merged into a solid slab. There are three, with real gaps between them, because gaps are what make a waveform read as bars rather than as a block.

## Fixed

**Alt+B opens the Book Tools menu again.** The main window's Build From Recordings button also claimed Alt+B, so Alt+B started a new book. The button is now **Build From Recordings...** on Alt+R, and Alt+B opens Book Tools.

**Edit a Book opens again.** It stopped with an error before its window appeared. It opens, and Ctrl+Shift+T (Sleep Timer) and Ctrl+Shift+Q (Play Queue) now work inside it.

**Resume Last Book on Launch is Ctrl+Alt+F10.** It was Ctrl+Alt+Shift+R, Quill Radio's system-wide show and hide key, so with Radio running the menu key never fired.

**Kokoro narration no longer stops mid-run on a portable copy.** A long, dense passage could overrun the neural model's input window; the Studio then fell back to a heavyweight code path a portable copy does not carry, and announced "Kokoro voices need one more component" - for a component you had already installed, 29 chapters into a run. The Studio now re-splits that one passage at safe boundaries and carries on, so a portable narration completes. The per-passage size limit is capped below the model's window everywhere it is used, translated editions included, and when a passage genuinely cannot be synthesized the message names the real cause and where the report is, instead of pointing at a download you do not need.

## Known limitations

- **Not released yet.** This version is built but unpublished, and Audio Studio is not offered in the cross-app menu.
- **Releases are not code-signed.** Windows SmartScreen warns on first run; choose "More info" then "Run anyway".
- **Windows-first; macOS supported.** SAPI 5 and DECtalk are Windows engines, and stored secrets use the Windows Credential Manager; elsewhere those fields work per-session but are not persisted.
- **Recording, broadcasting and AI pictures are not yet verified live.** See "Not yet verified" above.
- **Add-ons are not available here yet.** Quillins - QUILL's small, sandboxed add-ons - run in QUILL, Quill Radio, and QUILL Cast. Audio Studio does not yet offer them.
