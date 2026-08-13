# QUILL Audio Studio 2.2.0 - Release Notes

Built, not yet released.

## Why the version jumps from 1.0.0 to 2.2.0

There is no Audio Studio 2.0 or 2.1. On 2026-07-21 the Studio's build was rebuilt from the shared template every Quill app now uses, and it took the family's version number with it - the same 2.2.0 that Quill Weather (2026-07-23) and Quill Radio (2026-07-24) carry. The number is shared because the apps now install and run on one shared runtime; the releases stay independent, so each app still updates on its own schedule.

This build has not been published. Audio Studio is not yet offered in the cross-app menu and there is no 2.2.0 download page. What follows is what is in the build, waiting on the release.

## Install Python once, and every Quill app starts instantly

The single biggest change is how the Studio is delivered. Every Quill app - QUILL, Quill Radio, Quill Weather, and QUILL Audio Studio - now shares one Python engine, the **QuillVille Runtime**, installed once per user and reused by all of them. Install it a single time with any Quill app, and every app you add afterward launches immediately instead of downloading its own copy of everything. The runtime is reference-counted: it is removed only when the last app that needs it is uninstalled, so removing one app never leaves another unable to start.

That unlocks two feather-light ways to get the Studio, alongside the fully self-contained editions:

- **Companion edition** (about 2 to 3 MB) - just the app and its documentation. The first time you launch it, if the runtime is not already on your machine, it offers to download and install it (about 230 MB, once). After that, this app and every other Quill app start instantly.
- **Thin installer** (the "Lite" setup) - a small installer that downloads the shared runtime only if it is not already present, then installs the app.

The fully self-contained editions are still there: the **full portable** zip (about 675 MB) runs from a USB stick with no installation and no internet, carrying a genuine, unmodified copy of Python plus the offline speech and text-to-speech engines, and the **full installer** installs the shared runtime, if it is not already present, plus the app. The installer now also offers a choice of setup: Full, Compact (the program without the bundled documentation), or Custom.

Every runtime download - whether an installer started it or the app did on its own first launch - shows a **fully accessible progress bar** that works with NVDA, JAWS, and Narrator and announces progress as a percentage. There is no silent wait where you cannot tell whether anything is happening.

The Studio's launcher is now a genuine, tiny native program, and the bundled Python is the official unmodified build. Earlier versions used a renamed and modified copy of Python's own launcher, a pattern some antivirus tools flagged as a false positive. That pattern is gone, so the Quill apps are far less likely to be flagged. Releases are still not code-signed, so SmartScreen may caution on first run.

## Update in one click

When an update is available, choose **Download**, then **Install and restart now**. The Studio applies the update itself - extracting the new portable files over your folder, or running the installer quietly - and relaunches, keeping every setting, voice, and book position. No closing the app, unzipping, and swapping folders by hand.

**Help > Check for Updates...** now looks at the shared Quill project releases and picks out Audio Studio's own download for the flavor you run. Each app updates on its own schedule from that one place, so an update to Quill Radio is never mistaken for an update to the Studio.

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

## Built from QUILL's own source

The Studio used to be assembled from a copy of QUILL's audio code kept in a separate repository and re-synced by hand. It is now built directly from QUILL itself. Nothing changes in what you see, but the standalone Studio and QUILL's built-in Audio Studio can no longer drift apart, and a fix made upstream is in the next Studio build with nothing to copy across.

Two smaller results of the same work: Piper voices now download from the project's own signed mirror rather than a third-party model host, so a voice download no longer depends on an outside service being reachable from your network; and the shared components each app needs (ffmpeg, for the Studio) are counted, so uninstalling one Quill app can never take away something another app still needs. The build also leaves out the large libraries the Studio never loads, making both the installer and the portable zip meaningfully lighter.

## An icon of its own

Until now QUILL Audio Studio shipped a **byte-identical copy** of Quill Radio's blue broadcast-wave icon -- not a similar drawing, the same file. So did Quill Inkwell and Quill Weather. On a desktop with more than one Quill app installed, four different products wore one face in the taskbar, in Alt+Tab, in the Start menu and in the notification area, which for a tray-resident app is where it lives its whole life. Nobody chose that; each new app was built from the last one's template, and an icon is easy not to notice.

Every app in the family now has its own. They are still recognisably a set -- one rounded tile shape, one gold accent -- but each has its own colour and its own picture. The Studio's is a three-bar waveform on a dark slate tile: editing audio rather than broadcasting it, and the only glyph in the family built from repetition.

The drawing was made for the size that actually matters. At 16 by 16 pixels -- the notification area, and the small icons in a file list -- a first attempt with five bars merged into a solid slab. There are three, with real gaps between them, because gaps are what make a waveform read as bars rather than as a block.

## Fixed

**Kokoro narration no longer stops mid-run on a portable copy.** A long, dense passage could overrun the neural model's input window; the Studio then fell back to a heavyweight code path a portable copy does not carry, and announced "Kokoro voices need one more component" - for a component you had already installed, 29 chapters into a run. The Studio now re-splits that one passage at safe boundaries and carries on, so a portable narration completes. The per-passage size limit is capped below the model's window everywhere it is used, translated editions included, and when a passage genuinely cannot be synthesized the message names the real cause and where the report is, instead of pointing at a download you do not need.

## Known limitations

- **Not released yet.** This version is built but unpublished, and Audio Studio is not offered in the cross-app menu.
- **Releases are not code-signed.** Windows SmartScreen warns on first run; choose "More info" then "Run anyway".
- **Windows-first; macOS supported.** SAPI 5 and DECtalk are Windows engines, and stored secrets use the Windows Credential Manager; elsewhere those fields work per-session but are not persisted.
- **Add-ons are not available here yet.** Quillins - QUILL's small, sandboxed add-ons - run in QUILL, Quill Radio, and QUILL Cast. Audio Studio does not yet offer them.
