# Internet Radio in QUILL — Plan + Build Log

- Status: **In progress** — building on branch `worktree-radio-internet-stations`, worktree `.claude/worktrees/radio-internet-stations`
- Created: 2026-07-12
- Sources: research pass over `S:\code\fastplay` (C++ Win32 accessible media player); `S:\code\acb_link_desktop` (BITS/ACB's official wxPython radio+podcast app) for ideas and the ACB Media station list; QUILL's existing Audio Studio / publish stack.
- Decision, final: RadioBrowser only for station discovery. **TuneIn, iHeartRadio, and YouTube are explicitly out of scope and will not be built** — both radio backends are undocumented reverse-engineered commercial APIs with no public terms, and YouTube reopens a deliberate call already made in `requirements.txt` to keep yt-dlp/youtube-transcript-api out of QUILL's installed surface. Do not resurrect these; if this line is ever revisited, it needs a fresh decision, not a reading of old research notes.

## 1. What shipped (or is shipping) in this pass

**Core (`quill/core/radio/`, wx-free):**
- `models.py` — `RadioStation` dataclass shared by every source (RadioBrowser, ACB Media, custom, saved favorites).
- `radio_browser.py` — RadioBrowser client (free, keyless, community-run station directory): search, tags, countries, click-vote registration. Resolves a mirror host once per session instead of hardcoding one. Safe Mode gated (`refuse_in_safe_mode`), reviewed egress site `core/radio/radio_browser.py::_http_json`.
- `acb_media.py` — the American Council of the Blind's ten "ACB Media" Live365 streams, bundled as a static list (not fetched live — see the module docstring for why: no egress surface needed, never breaks if `link.acb.org` is briefly down, and a sibling ACB player was found to have two contradictory in-code station lists during research, a bug this static/verified approach avoids). Always available as a first-class category in the station browser, not just a search result — genuinely on-mission for an accessibility-first app.
- `link_finder.py` — "Find Streams from a Website": fetches one user-typed page and parses it (stdlib `html.parser`, no embedded browser — see module docstring) for `<audio>`/`<source>` tags and stream-shaped links, plus a title/favicon guess for pre-filling a new custom station. Reviewed egress site `core/radio/link_finder.py::_fetch_html`.
- `favorites.py` — saved stations (from any source) as atomic JSON, the standard QUILL settings-surface pattern. Each favorite carries an optional `folder` field, unused by radio today but there on purpose so podcasts (see §3) can grow folders out of the same shape later instead of inventing a second one.

**UI (`quill/ui/radio/`):**
- `player_controller.py` — the one playback engine for the whole app, owned by `MainFrame` for its lifetime. **Deliberately uses the wx.media (WMP) backend only, never libmpv** — `MpvAudioEngine`'s poll loop only considers a stream "loaded" once `duration > 0`, which a live stream never reports, so play/pause would silently never work through that backend. `WxMediaEngine` has no such gate problem. Giving radio a working mpv path is a real, separately-scoped follow-up, not something to improvise by touching the shared Audio Studio engine. This one shared controller is *why* "listen in the background while editing" needs no new non-modal-panel architecture: the station browser dialog is an ordinary modal picker (like the emoji picker) — closing it doesn't stop playback, because playback lives in the controller, not the dialog. That resolves what an earlier draft of this doc flagged as an open design tension.
- `station_browser_dialog.py`, `add_station_dialog.py`, `link_finder_dialog.py` — see §2.
- Status bar mini-player cell and system tray radio section (both non-modal by nature, both drive the same controller) — see §2.

**Menu, commands, hotkeys:** `Tools > Media > Internet Radio` submenu; commands registered in `CommandRegistry` (so they're in the Command Palette, unlike the Audio Studio menu item, which was found during research to bypass the registry); in-app QUILL-key chord hotkeys for play/pause, stop, mute (see §2 for the "why in-app, not OS-global" call).

## 2. UI surfaces

- **Station Browser** (`Tools > Media > Internet Radio > Browse Stations...`) — a category list (Favorites, ACB Media, Search Results) for instant/local browsing plus a search row (name + optional tag/country fields, an explicit Search button since it's a network call) for RadioBrowser, in the spirit of the emoji picker's search+category-list approach (not a literal `wx.TreeCtrl` — the emoji picker itself uses two flat lists, not a tree, so this follows the real established pattern rather than the "tree-view" phrasing literally). Results list + read-only details panel + a volume slider/mute button (Internet Radio's own volume, separate from system/screen-reader volume). Play / Add to Favorites / Add Custom Station / Find Streams from a Website / Close buttons; every control gets a full `SetName`.
- **Add Custom Station** — Name / Stream URL / Homepage / Tags, a Test button (plays through the same controller before you commit to saving), Save to Favorites. Supports "a wide variety of links" per the ask — any http(s) stream URL, including ones RadioBrowser doesn't carry.
- **Find Streams from a Website** — type a site's address, Scan fetches and parses that one page for candidate stream links, each with a plain-language reason ("audio tag", "stream-shaped link"), Test to preview, "Use This Link..." opens Add Custom Station pre-filled with the guessed name/URL/favicon. This is the scoped, accessible version of "open a browser and find the stream for me" — see `link_finder.py`'s docstring for why it's a fetch-and-parse rather than a full embedded interactive browser (QUILL has no general-purpose accessible WebView for arbitrary-site navigation, and `core/browser_reader.py` shows a deliberate house pattern of preferring the user's real browser over an embedded one for exactly this kind of accessibility-sensitive task). If real JS-rendered-page scanning is ever wanted, that's a separately-scoped follow-on.
- **Status bar mini-player** — a `radio_player` status bar cell (station + state), click toggles play/pause, right-click/context menu offers Play/Pause, Stop, Mute, a Favorite Stations quick-switch submenu, and Open Internet Radio — all the generic per-cell wiring (keyboard nav, focus announcement, Hide/Settings) comes free from the existing status bar mixin.
- **System tray** — extends the existing `wx.adv.TaskBarIcon` right-click menu (already used for Copy Tray / Sticky Notes) with a "rich" radio section: Now Playing label, Play/Pause, Stop, Mute, a Favorite Stations submenu, Open Internet Radio; tray tooltip reflects the current station.
- **Hotkeys** — in-app QUILL-key chords for play/pause, stop, mute, scoped to "QUILL has focus" like almost everything else in the keymap system. QUILL has exactly one precedent for a true OS-level global hotkey (`RegisterHotKey`, sticky notes, Windows-only) and it's used sparingly by design; radio's hotkeys follow the normal in-app pattern instead, consistent with "quick hotkeys ... from the editor." A true system-wide (app-not-focused) hotkey is a small, separately-decidable addition later if wanted, not the default here.

## 3. Podcasts (future, richer plan needed — do not build yet)

Explicitly deferred until after radio ships, per direct instruction. Requirements captured here so they aren't lost, plus small forward-compatible stubs in code (pure dataclasses only, not wired to any UI, command, or menu — CLAUDE.md's "no half-finished implementations" rule means nothing user-facing should half-exist):

- **Folders of shows.** Create folders, put subscribed podcasts into folders, each show containing its episodes — a real hierarchy, not the flat favorites list radio uses today. `core/radio/favorites.py`'s `folder` field is a first small step toward this, not the design itself.
- **OPML import/export** for podcast subscriptions (FastPlay and ACB Link both support this; ACB Link's `link.opml` is a real-world example of the shape to parse).
- **Generate a playlist from a folder** — turn "everything in this folder" (or "every unplayed episode in this folder") into a playable queue.
- Discovery/reader design questions (iTunes Search API for discovery, stdlib `xml.etree.ElementTree` for RSS reading, credentials for private feeds via the OS credential store per `core/publish/destinations.py`'s pattern, chaining a downloaded episode into the Listening Companion for transcribe+summarize as a QUILL-unique differentiator) are still the right starting points from the original research pass, but need a proper brainstorming/design pass of their own — folders, OPML, and playlists-from-folders change the data model enough (a real tree, not a flat list) that it deserves its own spec rather than an extension of this doc.

## 4. Recording, scheduling, and ACB Media calendar (planned next, not built in this pass)

Per direct instruction: "Leave Radio, recording, scheduling and ACB Media streams as the primary focus for now" — these three are the *next* things to build after this pass, ahead of podcasts (§3). Researched from `S:\code\acb_link_desktop`, which has all three today; the plan below borrows the good ideas and deliberately upgrades past its rough edges (see caveats per item).

### 4.1 Recording the current stream

ACB Link's `StreamRecorder` (`acb_link/media_player.py`) uses `requests`' streaming `iter_content` to write the live stream to disk in a background thread, independent of playback — you can record without listening, or listen without recording. For QUILL:

- **Formats**: record to MP3/WAV/OGG at minimum, reusing `core/speech/ffmpeg.py`'s existing transcode wrapper (QUILL already runs ffmpeg for audiobook/podcast production — no new dependency) rather than ACB Link's raw byte-for-byte dump, so "save into multiple formats" is a real transcode step, not just renaming a raw MP3 stream to `.wav`.
- **Where it lives**: a small `core/radio/recorder.py` (wx-free) driving ffmpeg as a subprocess against the currently-playing `stream_url`, following the same `safe_subprocess` conventions as the rest of QUILL's ffmpeg call sites. UI: a Record toggle next to Play/Pause in the station browser, status bar cell, and tray menu (mirroring how Play/Pause/Stop/Mute already appear in all three places).
- **Filing convention**: land recordings in a QUILL-managed subfolder (mirroring the audiobook-build output convention) named from station + timestamp, not a bare dump into the working directory.
- **Caveat learned from ACB Link**: its recorder and its `STREAMS` data model live in genuinely different, inconsistently-typed places (see §"a real bug" in the research notes preserved in this session's transcript) — keep the recorder reading from the *same* `RadioStation`/favorites model the browser and player already use, not a second parallel station representation.

### 4.2 Scheduled recording (and scheduled playback)

ACB Link's `scheduler.py` uses the OS's own scheduler (Windows Task Scheduler / macOS `launchd`) so a recording can start even if ACB Link itself isn't running. That is real added complexity (writing/removing OS scheduled tasks, needing the app or a helper process to actually run at trigger time) beyond anything QUILL does today.

- **Phase A (in-app only, simplest, do this first)**: a schedule is just "while QUILL is running, start recording station X at time T for duration D" — an in-app `wx.Timer`-driven check against a small persisted schedule list (`core/radio/schedule.py`, atomic JSON like favorites). No OS integration, no risk of a stray scheduled task surviving an uninstall. This covers the common case (you leave QUILL running) and ships fast.
- **Phase B (OS-level "even if QUILL is closed", real follow-up, not default)**: only if there's real demand — needs a design pass of its own for how a scheduled trigger actually launches something that can record without the full GUI (a headless CLI entry point?), and an uninstall story that reliably removes any OS-level task QUILL created. Do not build this without that separate design pass; it's meaningfully riskier than Phase A (OS Task Scheduler/launchd integration, cross-platform, needs to survive uninstall cleanly).
- **UI**: a "Schedule Recording..." dialog off the station browser (station, start time, duration, output format) and a "Scheduled Recordings" list to review/cancel upcoming ones — same list-based, fully keyboard/screen-reader pattern as everything else in this feature, not ACB Link's calendar-grid style.

### 4.3 ACB Media calendar feeds

ACB Link pulls `https://link.acb.org/categories.xml`-family feeds (events, affiliate/SIG info) as part of its broader "everything ACB" surface (see the ACB Link research notes: streams.xml, link.opml, states.xml, sigs.xml, publications.xml, categories.xml, acbsites.xml — all served as simple XML dumps from the same `link.acb.org` host, refreshed weekly with a SHA256 change-check). The specific ask here is the **events/meetings calendar** feed:

- **Scope for QUILL**: a read-only "ACB Media Events" view (or an .ics/iCal export) surfaced from the same place the ACB Media station category lives, so a QUILL user gets "here's what's on/coming up on ACB Media" without leaving the app. This is a *new* egress site (`link.acb.org`, likely `categories.xml` or a dedicated events feed — confirm the exact URL before implementing, since the research pass only confirmed `streams.xml`/`link.opml` concretely) and needs its own `network_egress_audit.py` entry, HTTPS-only, Safe-Mode gated, following `radio_browser.py`'s pattern.
- **Parsing**: same custom lightweight XML shape ACB Link's `StreamsParser` uses (`<ACBRadioStreams><Stream .../></ACBRadioStreams>`-style) — expect the events feed to be similarly simple, parse with stdlib `xml.etree.ElementTree` like `link_finder.py` already does, not a heavier XML/OPML library.
- **Explicitly not doing (this pass or the next)**: the rest of ACB Link's "everything ACB" surface — affiliate directories, publications, SIG info, a full web-server tab, voice control. The calendar/events feed is the one piece directly relevant to "ACB Media streams as primary focus"; the rest is a different, much larger scope decision for another day.

## 5. Explicitly out of scope

- TuneIn / iHeartRadio backends (undocumented commercial APIs).
- YouTube audio in any form (search or playback) — `requirements.txt` already made this call.
- DSP effects rack (reverb/echo/EQ/compressor/tempo-pitch/center-cancel/3D spatial audio) — a media-player feature, not a writing-tool-with-audio-production feature.
- SQLite as a new storage engine — everything here is atomic JSON via `core.storage.write_json_atomic`, QUILL's existing convention.
- A full embedded interactive browser for link discovery (see §2's Find Streams from a Website entry).

## 6. Open follow-ups (not blocking this pass)

- A working mpv backend for live streams (needs its own live-stream-aware polling logic, validated against real streams — see `player_controller.py`'s docstring).
- ICY "now playing" metadata capture/announcement for radio (nice accessibility touch, low effort once playback exists, not built in this pass).
- Optional true OS-level global hotkeys for transport control while QUILL isn't focused (the sticky-note `RegisterHotKey` precedent is Windows-only; a cross-platform story would be needed).
- A live-refresh fetcher for the ACB Media list (currently static/hand-maintained; see `acb_media.py`'s docstring for the pattern to follow if this is ever wanted).
