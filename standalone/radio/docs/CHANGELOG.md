# Changelog

All notable changes to Quill Radio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Quill Radio runs the same radio code as QUILL from the shared `quill` package, so features and fixes land in both at once; this repository carries only the wrapper, installer, icon, and docs.

## [Unreleased]

Work landed since 2.2.0 and not yet released. Quill Radio learns two whole new kinds of station -- YouTube and Live365 -- your volume finally stays where you put it, and every message the app speaks now also reaches a braille display.

### Added

- **YouTube plays and records like any other station.** Paste a YouTube link into **Add Custom Station** -- an ordinary video link, a `youtu.be` short link, or a channel's live page -- and it becomes a station: it plays through the same player, sits in Favorites, records with Record Now, and can be captured by a scheduled recording. Quill Radio saves the *page* address, never a stream address, and re-finds the audio each time you play or record, so a recording you schedule today still works next week. It needs the small `yt-dlp` helper, which is never bundled: it installs on demand (about 3 MB) after a one-time consent and rights notice shown when you add your first YouTube station -- asked then, not while a recording is firing at 3am. Off in Safe Mode. A private, removed, region-blocked, or not-yet-live video says so in plain words. (#1268)
- **Paste a Live365 link and it just plays.** The Live365 link you actually have is almost never the stream -- it is the station page or the web player, both of them web pages that used to save as a station that could never play. Add Custom Station now recognizes any Live365 station page, player link, or bare station id and rewrites it to that station's real stream address, telling you it did. It is a pure text rewrite: no network lookup, nothing sent anywhere, and a link that isn't Live365 is passed through exactly as you typed it.
- **Export Favorites to Playlist (Station menu).** Save your stations to an M3U playlist you can hand to any media player, share, or keep as a plain-text backup outside Quill Radio. It is the twin of Import Stations from Playlist, and the two round-trip. (#1249)
- **Output Device on the Playback menu (Ctrl+Shift+D).** Switch the radio to another sound card or USB headset in one keystroke instead of opening Preferences. It changes the device immediately and remembers the choice, exactly like the Preferences setting it shortcuts. (#1253)
- **Report Bad Station.** A station that plays for the directory but not for you is something only you can flag. **Report Bad Station...** on any station's context menu (in Browse Stations and Search Stations) opens the normal Report a Bug flow pre-filled with that station's details -- name, stream, source, country -- so the report is complete on the first try. It carries station information only; never your name, email, or file paths. (#1218)
- **Repeat Last Announcement, and an Announcement Self-Test.** Speech is gone the moment it finishes; **Repeat Last Announcement** (Command Palette) brings the last thing Quill Radio said back. **Announcement Self-Test...** announces a phrase and then tells you which channels actually delivered it and through which backend, so "braille is broken" and "no display is connected" stop looking the same. Quill Radio also gains its own sound cues, all of which can be turned off or replaced from a sound pack.
- **Quillins in Quill Radio.** Quill Radio can run Quillins -- QUILL's small, sandboxed, permission-gated add-ons -- from its own Quillins menu. A Quillin declares which apps it is for, so only add-ons written for the radio appear. One thing a radio Quillin can do is contribute an extra station directory, which then shows up alongside RadioBrowser and the others when you search. Off in Safe Mode; third-party Quillins stay disabled in this release.
- **Spotify (experimental, and off unless you deliberately turn it on).** Quill Radio can play from Spotify through Spotify's own playback engine. It ships dark: on a normal install there are no Spotify menu items, no settings, and nothing reaching Spotify. Lighting it up needs an unlock code, a paid Spotify Premium account, your own Spotify Client ID, and the Edge WebView2 runtime. Spotify audio is copy-protected, so a Spotify selection cannot be recorded.

### Changed

- **Announcements now reach your braille display.** Everything Quill Radio speaks -- What's Playing, a finished refresh, a recording starting -- is now also written to a connected braille display, not only spoken. Nothing is truncated, an identical message inside two seconds does not steal the display twice, and braille never costs speech: an unplugged display or a reader that refuses the call degrades to "spoke but did not braille", never to silence. Turn it off with **Show announcements in braille** in Preferences > Accessibility. A *burst* of different messages no longer flickers across the display either -- the first message of a quiet period writes instantly and anything landing within the next 150 ms settles to the newest, with errors always writing through at once. (#1283)
- **The scheduled-recordings list is ordered by when each recording next occurs**, soonest first, rather than the order you entered them, and each row shows the stream's host in brackets so two similar entries -- or a duplicate still pointing at the original station -- are easy to tell apart. (#1220)

### Fixed

- **Quill Radio remembers your volume, and Ctrl+Up/Down works from anywhere.** The player started every session at 100% unless the station was a favorite with its own remembered level, so a non-favorite station came back at full blast on the next launch. The last level you set is now saved and restored (a favorite's own level still wins), and saving it no longer reloads the favorites list or re-announces the station. Separately, **Ctrl+Up** and **Ctrl+Down** only worked while the favorites tree had focus; they now work from any focus in the window -- except inside a text field, where Ctrl+arrow still edits text. (#1263)
- **"Copy What's Playing" and "What's Playing - Review and Copy" always answer you.** With a station playing, both commands could come back having done nothing at all -- no window, no copy, no message -- while with nothing playing they spoke a sensible message, which made the bug look inverted. Now, if a station is on, both fetch the title first ("Checking what's playing..."), then copy it or open the review window; a stream that sends no titles says so and still opens a window naming the station; a failed lookup is reported instead of silently swallowed; and the copy confirmation names what it copied. (#1282)
- **Recording filenames follow the computer's current time zone.** Change the computer's time zone (or ride a daylight-saving shift) while Quill Radio is running and new recordings are named with the new local time straight away -- no restart. Filenames used to keep stamping the zone that was in force when the app launched. (#1223)

## [2.2.0] - 2026-07-24

The headline of this release is how Quill Radio is delivered: a shared runtime installed once per user, two brand-new light downloads, an accessible runtime download, and a native launcher that no longer looks like repackaged Python to antivirus tools. It also gains a family switcher, a way to trim the app to just what you use, and a weather watch that speaks warnings as they are issued.

### Added

- **The QuillVille Runtime -- shared, install-once-per-user.** Quill Radio, QUILL, Quill Weather, and QUILL Audio Studio now share one Python engine, the QuillVille Runtime, installed once and reused by every app. Install any one app and every app you add afterward starts instantly. The runtime is reference-counted and removed only when the last app that needs it is uninstalled.
- **Companion edition (new download), about 3 MB.** `Quill-Radio-Companion-<version>.zip` contains only the app and its docs and runs on the shared runtime. On first launch, if the runtime is not already installed, Quill Radio offers to download and install it once (about 230 MB) with a fully accessible progress bar; after that, this and every other QuillVille app start instantly.
- **Thin ("Lite") installer (new download).** A small installer that installs the app and downloads the shared runtime only if it is not already present.
- **Accessible runtime download everywhere.** Whenever the shared runtime is downloaded -- by an installer or by the app's own first launch -- the progress bar reads correctly under NVDA, JAWS, and Narrator and announces progress as a percentage.
- **Backup and restore.** Station > Back Up Stations and Settings and Restore from Backup save favorites, settings, wake timer, recording schedule, and optionally recorded audio into a single `.qrbackup` file and bring it all back on a new machine.
- **View menu with a focusable status bar.** Show Station Details, Show Status Bar, Sort Favorites, Expand/Collapse All Folders, and Text Size (Normal/Large/Larger). The status bar is arrow-navigable (F6), acts on Enter, and offers a per-cell context menu.
- **Global show/hide-to-tray hotkey (Ctrl+Alt+Shift+R).** A system-wide chord toggles the main window to and from the tray from any app; playback and recording continue while hidden. Skipped silently if another app already owns the chord.
- **The QuillVille menu (Alt+Q) -- one cross-app switcher in every app.** Quill Radio, QUILL, and Quill Weather each carry the same top-level QuillVille menu listing every family member, so you can jump to any of them from the same place everywhere. Opening an app that is already running just brings it forward.
- **Customize Features (View menu) -- turn whole areas of Quill Radio on or off.** **View > Customize Features...** lists the app's switchable areas -- the **Recording** and **Weather** menus -- each with a description. Uncheck one and its whole menu (and every command under it) is left out the next time the app opens, so you can trim Quill Radio to just what you use. Everything is on until you turn it off.
- **Start Quill Radio with Windows.** A new **Station > Start Quill Radio with Windows** checkbox adds (or removes) a per-user autostart entry so the radio is running at sign-in. No administrator rights needed.
- **Weather Guardian -- background alert monitoring that speaks warnings as they arrive.** **Weather > Start/Stop Weather Monitoring** (Ctrl+Shift+M) watches one US location's active watches, warnings, and advisories on a timer and speaks each newly-issued alert as it appears -- with forced, interrupting speech for tornado and flash-flood-level events -- then announces when they all clear. It keeps running while the window is minimized to the tray, resumes on launch, and shows a tray toast for each new alert. A severe-weather mode automatically tightens the poll while any alert is active and relaxes back afterwards. **Pause/Resume Alert Checks** snoozes the watch without turning it off.
- **An alert sounder you control.** New alerts play a distinctive bundled chime. In Weather > Settings you can turn the sound off entirely (alerts are still shown and spoken), choose your own `.wav` with a **Play** button to hear it before saving, and set how many times it plays per alert (1-10). **Weather > Test Alert** demonstrates the whole experience -- spoken text, sound, tray toast, and dialog -- clearly marked as a TEST, touching neither the network nor the real monitor state.
- **More weather to read:** an **hourly forecast** pane (temperature, conditions, and chance of precipitation for each upcoming hour, length configurable), a **moon almanac** (named phase, percent illuminated, moonrise and moonset, computed locally with no extra network call), and the **current local time at the searched location** leading Weather Now and Quick Weather, so checking another city's weather also tells you what time it is there. Each is a toggle in Weather > Settings.
- **Now Playing window on Ctrl+T** with a character-reviewable, copyable title and artist, plus per-favorite Station Details. Radio Browser genre browsing and clearer source labels. Keep-the-computer-awake while playing or recording. Schedule Recording duration as hours plus minutes. A Volume slider in the main-window Tab order.

### Changed

- **Native launcher replaces the stamped `pythonw.exe`.** `QuillRadio.exe` is now a tiny, genuinely-compiled native program that starts the app on a real, unmodified Python. The full portable zip (`Quill-Radio-Portable-<version>.zip`, about 311 MB) remains fully self-contained with its own genuine Python and bundled ffmpeg and mpv. The full installer is now `Quill-Radio-Setup-Shared-<version>.exe` and installs the shared runtime (if absent) plus the app.
- The heavy surfaces (Browse Stations, Search Stations, Manage Favorites, Schedule Recording, Weather Center) are now modeless windows that each carry the full menu bar, fixing the reported "menu bar disappears" behavior and the modal lock-out of the main window. A Window menu and Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1-9 move between them.
- **Every destructive question now defaults to No.** Remove Favorite, Delete Folder, Remove Recording, Remove All Favorites, and Reset Sound Enhancements all used to open with Yes as the default button, so pressing Enter reflexively destroyed the thing. Enter is now always the safe answer and you choose Yes deliberately. A build check keeps it that way.

### Fixed

- **Launching Quill Radio no longer crashes on a stray keystroke.** A key pressed at the wrong moment during launch could take the app down before its window appeared. (#1203)
- **Custom stations show up in Favorites the moment you add one (#1205).** Adding a custom station saved it, but the favorites list did not visibly update, so it looked as though nothing had happened.
- **Browse Stations picks up new listings after an in-place update (#1207).** The previous version's station-directory cache, still inside its freshness window, could keep showing the old listings; the newer bundled directory now wins (a directory you refreshed yourself still wins over both).
- **New Folder (Ctrl+Shift+E) works from the favorites tree (#1211).** The shortcut was advertised, but a focused favorites tree swallowed it before it could fire.
- **Audio no longer keeps playing after you exit (#1195).** On the real exit path the mpv playback engine only soft-stopped and left its final teardown to a window event, so audio could outlive the app. (Ctrl+W and the window X still minimize to the tray by design and keep playing -- use Exit to quit.)
- **Song information shows for more stations (#1215).** Some stations -- notably HLS streams -- put the current track where Quill Radio was not looking, so the now-playing title came up empty. It now reads both places.
- Favorites keep the hand-arranged order you gave them when you move an item from a sorted view. Explicit Exit quits for real. Keyboard focus lands inside the window on launch so Alt reaches the menu bar. The transport button no longer claims Alt+S/Alt+P, so Ctrl+P is the reliable Stop/Play key (#1208). Add to Favorites resolves a TuneIn stream on demand (#1210). Remove All favorites with confirmation and rolling-backup recovery (#1201).

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
- **Find in this folder** -- a search box in Browse Stations that searches from the folder you are on downward only (one genre, one state, one source), so results stay short instead of searching every directory. Type a name, press Enter, and matches appear as a flat list under that folder; **Clear** puts you back where you started.

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
- **Quill Radio tells you about recordings it missed while it was closed.** The scheduler only records while the app is running, so a scheduled recording whose time passed while Quill Radio was shut used to vanish silently. On launch it now says what it missed -- naming up to three and collapsing the rest to a count -- and stays quiet when nothing was missed.
- **Recordings go somewhere you can find them.** New recordings land in **~/Music/Quill Radio Recordings** (falling back to your home folder) instead of a buried AppData path. The Recordings list also stops rebuilding under you: the live refresh pauses while the list has keyboard focus and resumes when you move off it.
- **An optional temporary folder while a recording is in progress.** Recording Settings gains **Temporary folder (while recording)**: set it and a recording is written there and moved to your destination the moment it finishes, so a half-written file never appears in your recordings folder and a fast scratch disk can absorb the write churn. Leave it blank to record straight to the destination, as before. If the move ever fails the finished file is left safely in the temp folder rather than lost.
- **Find Streams recognizes iHeart and TuneIn station pages.** Pasting one into Find Streams from a Website now resolves the real playable stream instead of handing back a page address that will not play. (#1087)
- Verbose logging and a settable log folder -- plus the detail worth logging: the recorder's own error output, which playback engine was chosen for a station and why, how each recording ended and where its file landed, and a full trail from stream discovery (each page scanned, each candidate link kept and why, and which call sign resolved to how many playable streams). Every logged address is scrubbed first in case a stream link carries a token.
- Quill Radio identifies itself on the wire, so a station operator sees a named, honest client rather than an anonymous one.
- Move Up / Move Down in the Favorites Manager announces the station the entry now sits next to, so you always know where it landed, and the favorites tree follows your desktop's own window and text colours (and Windows High Contrast) instead of a default that could render near-invisibly.

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
