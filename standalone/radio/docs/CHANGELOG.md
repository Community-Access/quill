# Changelog

All notable changes to Quill Radio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Quill Radio runs the same radio code as QUILL from the shared `quill` package, so features and fixes land in both at once; this repository carries only the wrapper, installer, icon, and docs.

## [2.2.0] - 2026-07-24

The headline of this release is how Quill Radio is delivered: a shared runtime installed once per user, two brand-new light downloads, an accessible runtime download, and a native launcher that no longer looks like repackaged Python to antivirus tools.

### Added

- **The QuillVille Runtime -- shared, install-once-per-user.** Quill Radio, QUILL, Quill Weather, and QUILL Audio Studio now share one Python engine, the QuillVille Runtime, installed once and reused by every app. Install any one app and every app you add afterward starts instantly. The runtime is reference-counted and removed only when the last app that needs it is uninstalled.
- **Companion edition (new download), about 3 MB.** `Quill-Radio-Companion-<version>.zip` contains only the app and its docs and runs on the shared runtime. On first launch, if the runtime is not already installed, Quill Radio offers to download and install it once (about 230 MB) with a fully accessible progress bar; after that, this and every other QuillVille app start instantly.
- **Thin ("Lite") installer (new download).** A small installer that installs the app and downloads the shared runtime only if it is not already present.
- **Accessible runtime download everywhere.** Whenever the shared runtime is downloaded -- by an installer or by the app's own first launch -- the progress bar reads correctly under NVDA, JAWS, and Narrator and announces progress as a percentage.
- **Backup and restore.** Station > Back Up Stations and Settings and Restore from Backup save favorites, settings, wake timer, recording schedule, and optionally recorded audio into a single `.qrbackup` file and bring it all back on a new machine.
- **View menu with a focusable status bar.** Show Station Details, Show Status Bar, Sort Favorites, Expand/Collapse All Folders, and Text Size (Normal/Large/Larger). The status bar is arrow-navigable (F6), acts on Enter, and offers a per-cell context menu.
- **Global show/hide-to-tray hotkey (Ctrl+Alt+Shift+R).** A system-wide chord toggles the main window to and from the tray from any app; playback and recording continue while hidden. Skipped silently if another app already owns the chord.
- **Now Playing window on Ctrl+T** with a character-reviewable, copyable title and artist, plus per-favorite Station Details. Radio Browser genre browsing and clearer source labels. Keep-the-computer-awake while playing or recording. Schedule Recording duration as hours plus minutes. A Volume slider in the main-window Tab order.

### Changed

- **Native launcher replaces the stamped `pythonw.exe`.** `QuillRadio.exe` is now a tiny, genuinely-compiled native program that starts the app on a real, unmodified Python. The full portable zip (`Quill-Radio-Portable-<version>.zip`, about 311 MB) remains fully self-contained with its own genuine Python and bundled ffmpeg and mpv. The full installer is now `Quill-Radio-Setup-Shared-<version>.exe` and installs the shared runtime (if absent) plus the app.
- The heavy surfaces (Browse Stations, Search Stations, Manage Favorites, Schedule Recording, Weather Center) are now modeless windows that each carry the full menu bar, fixing the reported "menu bar disappears" behavior and the modal lock-out of the main window. A Window menu and Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1-9 move between them.

### Fixed

- Favorites keep the hand-arranged order you gave them when you move an item from a sorted view. Explicit Exit quits for real. Keyboard focus lands inside the window on launch so Alt reaches the menu bar. The transport button no longer claims Alt+S/Alt+P, so Ctrl+P is the reliable Stop/Play key. Add to Favorites resolves a TuneIn stream on demand. Remove All favorites with confirmation and rolling-backup recovery.

### Security

- **Friendlier to antivirus.** Earlier versions used a renamed and modified copy of Python's `pythonw.exe` as the launcher, a pattern some antivirus tools flagged as a false positive. That pattern is completely gone: the launcher is a genuine native program and the bundled Python is the official unmodified build. Releases are not yet code-signed (SmartScreen may caution on first run); signing is planned.

## [2.1.2]

### Fixed

- One-click updating works again (the update installer no longer rejects a legitimately app-sized download as a "decompression bomb").
- Favorites keep their order across the upgrade: a pre-2.0.2 favorites file is read as Unsorted rather than snapped to A-Z.
- A shared Speech Hub crash on an older build is fixed and regression-locked.

## [2.1.1]

### Added

- NOAA Weather Radio from the authoritative WeatherIndex directory: a State-to-Station browse tree, SAME code / call sign / "County, ST" search routing, and Listen to your Local NOAA Weather Radio from your saved location. Works offline via a bundled snapshot of 1,035 transmitters.
- Radio Reading Services: a Browse category and search blend for the audio information services that read print aloud for blind and print-disabled listeners; 20 vetted services bundled, refreshable on demand.
- iHeart browsing by genre and A-Z sub-directory in Browse Stations.

### Fixed

- The Source filter no longer hides a station carried by more than one directory.

## [2.1.0]

### Added

- A top-level Weather menu (National Weather Service, Open-Meteo, OpenStreetMap) reading current conditions, forecast, alerts, and an extended outlook as arrow-navigable, copyable text.
- Browse Stations as its own search-free window: one tree of every source (Favorites, Popular, Weather/NOAA, ACB Media, NFB Radio, SomaFM, TuneIn, Community M3U, Xiph/Icecast) with lazy loading.
- One-click updating: Download, then Install and restart now, keeping favorites, recordings, and settings.
- Reorder favorites from the keyboard (Alt+Shift+Up / Alt+Shift+Down) in manual order.

### Fixed

- Quill Radio no longer opens a second copy of itself. The Record button reads Stop Recording while recording. Volume changes are quiet with a screen reader. The Country and Tag lists stay put while arrowing.

## [2.0.2]

### Added

- Record as many stations at once as you want, with an optional Maximum simultaneous recordings cap; overlapping scheduled shows all record. Stop Recording and Stop All Recordings.
- Live Sound Enhancements preview, with every setting remembered per station as well as shared.
- OptiLab broadcast polish (Podcast Leveler, Stream Polish, Smooth Limiter), adapted with credit from OptiLab Core by dgl1984 (Apache-2.0).
- Favorites sort order (Ascending, Descending, Unsorted) with per-folder overrides. M3U/M3U8 playlist import.

### Fixed

- Channel mode Left/Right now plays in one ear only.

## [2.0.1]

### Fixed

- A recording no longer stops after a minute on a transient hiccup; only a genuinely terminal failure (full disk, HTTP 404/410/451) stops a recording.

### Added

- A clear "Recording started" announcement. Review-and-copy What's Playing. Channel mode (Stereo, Mono, Left only, Right only). Adjust a recording's playback volume with Ctrl+Up / Ctrl+Down.

## [2.0.0]

### Added

- Recordings you can trust: a recording in progress survives a restart and Quill Radio asks before resuming; scheduled recordings fire reliably throughout their window; the Recordings list stops flickering and keeps your place; the recording pipeline hardens against dropped connections, dead streams, and a crashed host.
- iHeart and TuneIn join station search, blended into one results list with a Source facet and genre/country dropdowns.
- Schedule management: Edit, Duplicate, Enable/disable, 12-or-24-hour time entry, and per-entry time zones.
- What's Playing reads a stream server's own Icecast/SHOUTcast status page as a same-host last resort.
- Verbose logging and a settable log folder.

## [1.1.0]

### Added

- The mpv playback engine, used automatically, with the classic Windows Media engine one Preferences setting away.
- Every stream format in real-world use: MP3, AAC and HE-AAC (AAC+), Ogg Vorbis, Opus, FLAC streams, and HLS (m3u8).
- A second sound card for the radio, live pause and rewind of the stream, and Volume Boost.
- Sound Enhancements as a full listening toolkit: three-band EQ, compressor, mono downmix, night mode, per-station memories.
- Alt+F4-to-tray, self-healing stream recovery from a station's website, JavaScript-player (Triton/StreamTheWorld) resolution, and paged station search (up to 200 results).

## [1.0.2]

### Added

- A real three-band equalizer and per-station Sound Enhancements. A second station directory (SomaFM). Automatic Check for Updates. A Preferences dialog. In-app documentation in the Help menu.

### Fixed

- Volume keys work from the Favorites tree, and volume stays put across play/pause.

## [1.0.0]

First release: QUILL's internet radio as its own small, screen-reader-first Windows app -- a favorites tree with focus at launch, spoken feedback for every action, a system tray, recording with scheduling, sleep and wake-up timers, and a shared data store with QUILL (`%APPDATA%\Quill`).
