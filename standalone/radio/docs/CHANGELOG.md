# Changelog

All notable changes to Quill Radio are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Quill Radio runs the same radio code as QUILL from the shared `quill` package, so features and fixes land in both at once; this repository carries only the wrapper, installer, icon, and docs.

## [3.0.0] - 2026-08-15

Major: Browse Stations becomes a browsable directory rather than a list of
sources, podcasts arrive keylessly, transcripts gain timings, and three
long-standing silent faults are fixed. See `docs/release-notes-3.0.md`.

### Added

- **Scheduled recordings keep the computer awake, and can wake it**
  (`core/radio/schedule_wake.py`, `platform/windows/recording_wake_task.py`,
  `ui/radio/schedule_wake_ui.py`). A schedule is a thread inside a running app,
  so a sleeping machine is never asked and the recording starts whenever it
  next wakes -- reported from the field as an 11:00 recording announcing itself
  at 11:03. The scheduling window now states the requirement, standby is held
  off for `IMMINENT_MINUTES` (5) before a recording is due, and a per-user Task
  Scheduler entry with `WakeToRun` wakes the machine `WAKE_LEAD_MINUTES` (2)
  beforehand. Two Preferences checkboxes, both default on and deliberately
  separate. Best effort throughout: a blocked `schtasks` costs the wake, not
  the app.

- **Choose Browse Sources... (Station menu)** -- hide any branch of Browse
  Stations. A branch that is off is not in the tree at all and is never
  contacted (the Search Sources rule); rows speak their own state; hiding
  everything leaves one row saying the way back; and "never set" is kept
  distinct from "chosen", so branches added later appear on their own.
- **Download Preferences... (Station menu; also a button in View > Downloads)**
  -- the downloads folder, per-show and per-book folders, author grouping once
  an author has more than one work, keep-downloads-going on close, and an
  ask-me-where mode that asks once per book and cancels the enqueue out loud
  if declined. A live sentence answers "what will happen to the next thing I
  save?".

- **Browse by Country, then State or region** -- a top-level branch over data
  Radio Browser always exposed and Quill Radio only used to fill a dropdown. A
  country with no regional breakdown lists its stations directly.
- **Browse by Language** -- the same data on the axis that is hardest to find
  elsewhere.
- **Trending Now** -- ranked by what is being listened to today, as distinct from
  Popular Stations, which ranks by votes cast once.
- **Recently Added or Changed** -- new and just-repaired stations.
- **Podcasts (Apple)** -- storefront, then Apple's full genre tree, then charts,
  then a show's episodes. No key, no account, no registration at any step. A show
  resolves to its own RSS feed and Apple is not involved after that.
- **Internet Archive** -- the collection tree walked to any depth, with a
  **More...** node that names how many rows it is hiding, `Retry-After` honoured
  on HTTP 429, and rights metadata shown only when the item publishes it.
- **LibriVox** -- Recently Added, By Genre (43), By Author (A-Z over ~7,000).
  No By Title: the API supports no title filter in any form.
- **Project Gutenberg** audiobooks by topic and language.
- **Audius** trending, overall and within 27 genres; gated tracks dropped.
- **Mixcloud** (Mode A, metadata only) -- 28 music and 10 talk categories; rows
  state that they open in the browser before activation.
- **ccMixter** by tag, with each row's licence shown on the row.
- **My Servers** -- add a broadcaster's own Icecast or SHOUTcast address and
  browse its mounts, each carrying what is playing on it right now.
  `browse_actions.py` probes the address before storing it (`my_servers.probe`)
  and reports the mount count; an address that answers with nothing is **not**
  stored. Plain `http` on a high port is accepted here deliberately -- a great
  many small Icecast boxes are exactly that, the address is one the listener
  typed, only a GET is sent, and no credential is ever attached.
- **YouTube Channels** -- follow a channel with no Google account. Adding one
  makes the same shallow request opening the branch would, so a channel that
  cannot be read is caught before it is stored; channels open into Uploads plus
  published playlists, paged with a **More...** node.
- **Action rows in the browse tree now act.** `BrowseNode.is_action` existed and
  `browse_tree_dialog` did not handle it, so "Add a Server..." and "Add a
  Channel..." were rows that did nothing on Enter -- the exact failure the house
  rule in `bounded_playback_ui` exists to prevent. Dispatch lives in
  `ui/radio/browse_actions.py`, one registry entry per action, so the window
  still learns nothing source-specific. Both actions run their network check on
  the task manager, never the UI thread, and refuse out loud in Safe Mode.
- **Explore (Wikidata)** -- By City, By Owner, By Network, By Format and On the
  Dial (FM band). Wikidata supplies the organisation, Radio Browser still
  supplies every stream, and each row is labelled "from Wikidata" because the
  join between the two is ours rather than either source's.
- **Your place is kept in anything with an end** (`core/radio/resume.py`,
  `ui/radio/resume_playback.py`) -- a LibriVox chapter, an Archive episode, a
  podcast. Keyed on the normalised stream URL, since nothing here is a file. A
  position under the floor is not a position and saving one clears the entry;
  finishing clears it too; every failure degrades to "no saved position" rather
  than reaching the player. Live stations are excluded by
  `RadioStation.is_recording`, because tuning in *is* your position.
- **PLS, XSPF and ASX playlists open**, and favorites export to all four formats
  (M3U, PLS, XSPF, ASX), each round-tripping through its own reader.
- **Federated search over the libraries** (`core/radio/federated_search.py`,
  `ui/radio/library_search.py`). Find Stations now also queries LibriVox,
  Internet Archive, Project Gutenberg and Apple Podcasts, each on its own task,
  appending into the existing results list with its own `source` so the Source
  column and filter work unchanged -- no second surface. `internet_archive.search`
  and a `query` parameter on `gutendex.audiobooks` reuse the endpoints and
  reviewed egress sites the browse tree already had; no new host. Deliberately no
  cross-provider ranking: each source's own order is preserved within its group.
  Sources that cannot answer free text (Audius, Mixcloud, ccMixter) are declared
  `search=None` with a reason and reported by name. One announcement when the
  last source reports, never per arrival.
- **Song Details** (`ui/radio/song_facts.py`) wires `core/radio/musicbrainz.py`,
  which had been written and called by nothing, into the Song History window:
  release, year and length for the selected song. Opt-in (a button, never
  automatic -- a per-row network request would spend somebody's connection on
  curiosity they did not express), on the task manager, self-rate-limited to
  MusicBrainz's one request per second, and degrading to "nothing more is known"
  rather than to an HTTP message.
- **Video** (`core/radio/video_formats.py`, `core/radio/caption_style.py`,
  `ui/radio/video_window.py`, `ui/radio/video_commands.py`,
  `ui/radio/video_output.py`, `ui/radio/mpv_video_mixin.py`,
  `ui/radio/caption_settings_dialog.py`). **Show Video (Ctrl+Shift+V)** attaches
  mpv to a `wx.Panel`'s handle *while playing* -- `wid` plus `vid=auto`, and back
  to `vid=no` on hide -- so showing and hiding the picture never restarts the
  stream and never loses the position. YouTube serves adaptive video and audio
  separately, so `pick_video_stream` chooses a **video-only** format (capped at
  1080p) and the audio rides alongside through mpv's `audio-files`, which is what
  avoids downloading and merging the whole file first; a combined format is
  skipped, and a live HLS stream already carries its own picture. The surface
  carries an accessible name and description, is in the tab order once, and never
  self-focuses; the status line is not a live region. Captions load via `sub-add`
  with `CaptionStyle` -> mpv properties, defaulting to **opaque** white-on-black
  (contrast against arbitrary video cannot be guaranteed otherwise) and scaling to
  300%. `Ctrl+Shift+I` reports size, rate, codec and whether captions and
  described audio exist; snapshots write `screenshot-to-file ... video`, without
  subtitles. Brightness control is the honest answer to a photosensitivity
  requirement no player can satisfy by inspection. `YOUTUBE_CONSENT` rewritten to
  cover video; the consent **flag** deliberately does not reset.
- **Described audio** (`core/radio/audio_tracks.py`,
  `ui/radio/audio_track_dialog.py`, `ui/radio/track_selection.py`). Every
  YouTube resolve reports each audio rendition with a language code and a label;
  `tracks_from_info` reads them, `is_described` decides which is descriptive
  (generously about form -- "English (Audio Description)", "descriptive",
  "eng-desc", "English AD", `en-x-description` -- and strictly about meaning),
  and `describe_track` names each one instead of numbering it.
  **Playback > Audio and Described Audio... (Ctrl+Shift+A)** lists them with the
  described track first, the cursor on it, and the availability stated above the
  list; **Play Described Audio (Ctrl+Alt+D)** switches straight to it. A
  rendition is a separate URL, so selection is a reload -- and the position is
  carried across, since losing your place an hour into a film to enable
  description would defeat the feature. Absence is reported with what the video
  *does* have, never as a greyed-out command. Detection is pure and unit-tested,
  so the heuristic can improve without touching the UI.
- **Timed transcript cues, and the reader that uses them.** WebVTT, SubRip,
  Podcasting 2.0 JSON and YouTube `json3` parse into timed lines
  (`TranscriptCue`, `parse_transcript_cues`, `cue_at`, `cues_to_vtt`,
  `cues_to_srt`, `fetch_transcript_cues`), and `quill/ui/transcript_reader.py`
  is the window: follow playback, Enter to play from a line, Find with the
  position spoken, Copy, Save As in text/VTT/SRT, Open in QUILL. Shared with
  Quill Cast rather than owned by either app. Radio reaches it from **Playback >
  Transcript... (Ctrl+Shift+T)** via `PlayerController.caption_track()`, which
  picks up the caption track every YouTube resolve was already fetching and
  discarding. Follow is off by default and silent while on; positions go through
  `spoken_duration`; the writers are asserted to round-trip through the parser;
  an automatic track is labelled automatic.
- **Browse levels are cached between sessions**, with the age of a cached answer
  available so it can be spoken rather than implied.
- **A probe suite for every external service** (37 probes, `S:\radio-probes`),
  each asserting a specific capability rather than a status code.

### Changed

- **Browse sources moved behind one contract**
  (`quill/core/radio/browse_sources.py`). The Browse window no longer knows the
  shape of any source; it renders folders and leaves. Adding a source is one
  registry entry and one handler, not a node kind plus edits in six places.
  `browse_tree_dialog.py` is 199 lines smaller while the tree it serves grew
  from thirteen root branches to twenty-eight, and its GATE-11 budget was
  **ratcheted down** to match.
- **An empty branch distinguishes "nothing here" from "could not be reached"**,
  and Safe Mode says so per branch rather than showing an empty folder.
- **A folder announces its child count before it is opened** where the source
  supplies one cheaply.
- **Xiph genres are offered in the directory's own use order** (most-used first),
  filtered to plausible genres, and bounded to the top 120 rather than ~3,400
  free-text strings.
- **`browse_tree_helpers` moved from `quill/ui/radio/` to `quill/core/radio/`**
  as `browse_helpers`, since the (core) browse registry needs it and core must
  not import from the UI layer.
- **The NOAA Weather Radio user agent is derived from the package version**
  instead of a hard-coded `2.1.1` that had been stale for two releases.

### Fixed

- **The described-audio picker listed one track as three, and then three as
  one.** `audio_tracks.tracks_from_info` first identified a track by
  `format_note`, which carries a quality tier (`low`, `medium`, `high`), so an
  ordinary video's several bitrates became several unchoosable rows all reading
  "English". Keying instead on yt-dlp's `audio_track` id with a language
  fallback was worse: yt-dlp does not populate `audio_track` for YouTube at all,
  and a video's original and descriptive renditions share a language code, so
  two tracks would have collapsed into one and the described track would have
  been discarded silently. `format_note` is now parsed (`track_name_from_note`)
  -- tiers and the `(default)` marker stripped, the track's own name kept -- and
  identity is language plus name. A row never repeats its language, and a
  regional tag survives only when it is the one thing distinguishing two rows.
  Unit-tested against the shapes YouTube really returns, plus an opt-in live
  test over fourteen real videos
  (`QUILL_YT_LIVE=1 pytest tests/integration/test_youtube_audio_tracks_live.py`).

- **Descriptive and dubbed renditions YouTube withholds from desktop players
  are now reached.** The web player response names a video's alternate audio
  renditions -- "English descriptive", twenty-four dubbed languages -- but
  serves them URL-less (SABR streaming), so yt-dlp discards them and every
  video claimed one track. The resolver now also asks as YouTube's iOS player
  client (`player_client: ["default", "ios"]`, `formats: ["missing_pot"]`),
  which gets the same renditions with direct, playable URLs; verified live on
  all eight known descriptive-track videos at no added resolve time. Fallout
  fixed along the way: the iOS client's `MISSING POT` stamp read as a phantom
  second track until stripped; the repeat-strip mangled unmapped language
  labels at a mid-word boundary ("Tamil" -> "ta (mil)"); and Tamil, Telugu,
  Malayalam, Punjabi, Marathi, and Bangla joined the language-name table, with
  unmapped codes now deferring to the track's own label.

- **`http.client.HTTPException` was not caught** by the new fetchers. It is not
  an `OSError` subclass, so ccMixter's oversized HTTP header (it emits one at
  page sizes of 20 or more) escaped as an unhandled type and the branch went
  silently empty instead of reporting that it could not load. ccMixter's page
  size is now capped at the 15 that works.

- **The Xiph genre index was silently truncated**, losing 412 genres and
  reporting a different count on every refresh: the page had outgrown the read
  limit and the forgiving parser hid it. The limit now fits, and an oversized
  page raises rather than dropping entries.
- **Xiph genres were sorted alphabetically**, discarding the directory's
  popularity order and opening the list on `00`, `00s`, `100.1` and `104.5`.
- **A single failed read ended a live stream** (reported against KFI Los
  Angeles). iHeart's HLS form is a three-segment, thirty-second window behind a
  per-listener redirect whose token lives five seconds and is refreshed every
  ten, so one missed refresh drained the buffer and the audio ran out twenty to
  thirty seconds later -- and `mpv_radio_engine` set **no ffmpeg reconnect
  options at all**, while `player_controller._on_finished` treated EOF on a live
  station as "the stream ended" and stopped. The only retry path that existed
  (`_attempt_engine_fallback`) is reachable only while `CONNECTING`. Three
  changes: `stream-lavf-o` now carries
  `reconnect=1,reconnect_streamed=1,reconnect_on_network_error=1,reconnect_delay_max=30`
  (`reconnect_streamed` is the one that matters -- without it ffmpeg refuses to
  reconnect a non-seekable stream, which is every live station); a new
  `ui/radio/live_reconnect.py` retries a dropped **live** station three times at
  2 s / 5 s / 15 s, announcing each attempt and the outcome, excluding bounded
  sources and dropping any retry whose play token has moved on; and
  `_NETWORK_TIMEOUT_SECONDS` rose from 15 to 30, which was tight for a playlist
  that only advances every ten seconds.
- **iHeart stations now prefer the progressive stream over HLS.**
  `iheart._STREAM_KEYS` puts `secure_shoutcast_stream` first: one long HTTP body,
  no segment window, no per-refresh token, no per-listener session to lose. It
  removes the failure mode above rather than recovering from it, and it captured
  60 seconds clean under probe (59/59 unique one-second PCM hashes) where the
  HLS form is the one that fails intermittently in the field. HLS remains the
  fallback for stations that publish nothing else.
- **A capture that recorded nothing was reported as a completed recording.**
  ffmpeg creates the output container before the first audio frame, so file
  existence was never evidence of a capture, and `_monitor` announced
  "Recording saved" (or, when the file was never created, nothing legible at
  all) for a job that produced zero bytes. New `core/radio/recording_outcome.py`
  owns the verdict -- `captured_nothing`, `empty_capture_reason`,
  `discard_empty_capture`, plus the fatal/recovery classifiers that moved with
  them -- and `RadioRecorder` gained an `on_capture_failed(station, reason)`
  callback, deliberately separate from `on_state_changed` because the two say
  opposite things: one reports a file that exists and the other reports that
  there is none. The empty file is removed and the failure is spoken on the
  error cue.
- **TuneIn preferred an HLS manifest over a progressive stream from the same
  host**, which is the iHeart dropout arriving through a different directory
  (96.5 The Fan Kansas City, guide id `s28141`). `best_stream` now demotes HLS
  -- but **host-scoped**, and the scoping is the point: for that station TuneIn
  returns the manifest on `live.amperwave.net` and an MP3 on
  `ais-sa40.cdnstream1.com`, whose own query string carries a *different*
  station id and `class=music` where the station is sports. A blind preference
  could hand somebody another broadcaster entirely; where the hosts differ, the
  engine's reconnect options and `live_reconnect` handle it instead. `_is_hls`
  matches on the path only, since TuneIn URLs carry heavy tracking query
  strings.
- **TuneIn could select an unencrypted stream when an encrypted one was
  offered.** Stream choice is now ranked -- not-a-redirect first, then HTTPS --
  instead of taking whichever survived a filter first.
- **`/json/states/<country>` needs its trailing slash**; without it the directory
  answers with an empty list rather than an error, which reads as "this country
  has no states".
- **Apple chart rows are tagged with their leaf genre**, so filtering a chart by
  a top-level genre matched nothing until the filter was widened to the genre's
  whole subtree.

### Security

- **XSPF and ASX playlists are parsed with entity expansion disabled**, so a
  crafted playlist cannot be used for a billion-laughs expansion.


- **Quill Radio's icon is its own again.** Quill Inkwell, Quill Audio Studio and Quill Weather were all shipping byte-identical copies of Quill Radio's broadcast-wave icon, so four products shared one face in the taskbar, in Alt+Tab and in the tray. Every app in the family now has a purpose-drawn icon: one shared tile shape and one shared amber accent, but a distinct silhouette and a distinct colour each. Radio keeps its waves, redrawn to survive tray size -- at 16x16 the old three thin arcs merged into a smear, so there are now two, thicker and further apart.
- **Exact OptiLab processing.** Quill Radio's broadcast-polish modes have always been a faithful *adaptation* of **OptiLab Core by Lanes Audio / dgl1984** (https://github.com/dgl1984/optilab), rebuilt as ffmpeg filter chains so they work everywhere -- live, relayed and recorded -- and preview the moment you move a control. That adaptation has one honest limit: OptiLab eases its lift and pulls back bass help *while* its final limiter is working hard, and a filter chain cannot do that, because no stage in it can see how hard a later stage is working. Quill Radio can now run the real OptiLab engine instead, when the optional component is included in your build. One setting, three states, both off by default: **off** (the built-in chain everywhere), **when saving** (recordings and converted files -- the recommended one, and it costs nothing, because a recording is processed after it finishes and the original is replaced only once a good copy exists), or **when saving and while listening** (which relays the stream through the engine, so the station starts slower, uses more CPU, and needs a brief reconnect on every settings change -- stated in the option rather than discovered afterwards). The built-in filters always leave the graph when the real engine runs, so nothing is processed twice; if the component is absent the option says so and nothing else changes. With thanks to dgl1984; licensed Apache-2.0 with the Commons Clause.

### Known incomplete

Written down rather than left to be found, because "not mentioned" and "not
built" look identical from the outside.

- **RadioDNS is a non-goal, and its module has been removed** rather than left
  as dead code. It resolves a broadcaster's own service document from the
  *broadcast* parameters -- frequency plus PI code plus ECC -- and Quill Radio
  has no source of PI codes. Wiring it would have meant a form asking a listener
  for a value nobody has, which is the same failure as an axis that quietly
  finds nothing. `dnspython` went with it, since nothing else needed it.


### Also in 3.0.0: everything from 2.2.0 (landed 2026-07-24, never published)

2.2.0 was built and never published, so its entries ship for the first time in
3.0.0. They are kept under their own sub-headings below rather than merged into
the lists above, so the record of what landed when survives the version skip.

#### The 2.2.0 work, in full
2.2.0 was never published, so everything that had accumulated under "Unreleased" is part of it rather than a release after it. It is a large one: the app is delivered differently (a shared runtime and two light downloads), it learns two whole new kinds of station -- YouTube and Live365 -- it remembers the songs each station played, your volume finally stays where you put it, and every message the app speaks now also reaches a braille display.

#### Added

- **A play queue for the Recordings list, which unlocks the last three Winamp keys.** **R** (shuffle), **S** (repeat) and **Ctrl+V** (stop after current) were deliberately left unbound when the rest of the Winamp map landed, because all three describe a play queue the recordings list did not have -- and a key that only looks like it worked is worse than a key that is not offered. It has one now. Shuffle is a **fixed order** rather than a fresh roll each time, so every recording plays once before any repeats and **Z** reliably goes back to the one you just heard; "pick at random each time" can do neither. Repeat cycles off, all recordings, this recording, and repeat-one applies when a recording *ends on its own* -- pressing **B** still moves on, because a Next that refused to move would look broken. Stop-after-current outranks repeat, clears itself the moment it fires, and is deliberately not remembered between sessions: a stop that survived a restart would halt playback for a reason nobody could remember asking for. A recording that reaches its end is now followed by whatever the queue says is next. Shuffle and repeat are remembered.
- **Go to Position... (Ctrl+Shift+J) for a finished video.** Skipping thirty seconds at a time gets you near; this gets you exact. It reuses the same accessible Hours / Minutes / Seconds dialog the Quill Media Player uses -- three labelled spin controls as the primary input, plus a timecode field for `1:23:45` -- rather than growing a second, lesser prompt, and it clamps to the video's length and says so if you asked for a point past the end.

- **One volume for every station (Playback > Use One Volume for All Stations).** Quill Radio remembers a volume per favorite, and that per-station level won outright -- so with twenty favorites there was no way to turn them all down; you had to play each station and adjust it. Switch this on and a single level answers for every station, so Volume Up/Down turn *everything* up or down. Turning it on adopts whatever you are hearing right now, so nothing lurches. Per-station levels are kept rather than erased, so turning it back off restores every station's own level exactly as it was; **Forget Every Station's Own Volume...** clears them deliberately, after confirming and never as a side effect. Off by default, so nothing changes until you ask for it. The menu checkmark follows the setting however you change it -- menu, Command Palette, or a rebound chord.
- **Song History: what each station played earlier (Playback > Song History, Ctrl+Shift+H).** What's Playing speaks the current track and forgets it; this is the memory behind it. A per-station list of every title change the existing thirty-second poll observed, newest first, each entry reading as a whole sentence ("Your Song by Elton John, heard 10:04, played twice"). From a selected song: **Copy**, **Send to Clip Library**, and **Background** -- a short note on the song from whichever AI provider is configured, always introduced as written by an AI model rather than by the station, and never available in Safe Mode. Up to 200 songs per station, and one station's listening never evicts another's. A repeat of the song already at the front folds into that entry with a play count instead of filling the list, and stations that broadcast their own name, "Live", or an advert marker are left out. **Clear...** empties one station or all of them, and **Keep a song history for each station** in Preferences turns the whole thing off.
- **Browse by network: the BBC, NPR, and broadcasters worldwide.** Browse Stations gains a **Networks** branch that gathers well-known broadcasters into one-click lists, grouped by type: public broadcasters (BBC, CBC, ABC Australia, RTÉ, RNZ, NHK, Deutsche Welle, Deutschlandfunk, Radio France, and more), US news and talk (NPR, Fox News Radio, CNN, Bloomberg), US public radio, sports, and music. Each list is drawn live from the Radio Browser directory, so there is nothing new to keep up to date and no new place your searches go. Syndication services that have no single stream of their own -- Westwood One, NBC News Radio, ABC News Radio -- open a search across their local affiliate stations instead, and the label says so. (#1384)
- **Quick-play your favorites.** Ten commands -- *Play Favorite 1* through *Play Favorite 10* -- play the first ten stations in your favorites list directly, without opening anything. They default to **Ctrl+Alt+Shift+1** through **Ctrl+Alt+Shift+0** (the plain number keys are already used by window switching, headings, and the copy tray), and like every command they are rebindable in **Keyboard Shortcuts** -- set them to Alt+1 through Alt+0 if you prefer -- and appear on the Command Palette.
- **Browse Stations remembers where you were.** Play a station and reopen the browse tree, and it lands on the source you were last in -- Networks, TuneIn, iHeart, wherever -- instead of collapsed at the top with everything closed.
- **YouTube plays and records like any other station.** Paste a YouTube link into **Add Custom Station** -- an ordinary video link, a `youtu.be` short link, or a channel's live page -- and it becomes a station: it plays through the same player, sits in Favorites, records with Record Now, and can be captured by a scheduled recording. Quill Radio saves the *page* address, never a stream address, and re-finds the audio each time you play or record, so a recording you schedule today still works next week. Off in Safe Mode. A private, removed, region-blocked, or not-yet-live video says so in plain words. (#1268)
- **YouTube works out of the box: the `yt-dlp` helper is built in.** Finding the audio behind a YouTube link needs `yt-dlp`, and it ships inside the app -- your first YouTube link simply plays, with no download and no consent prompt standing between you and the thing you asked for. It costs about 3 MB in the installer, and it is bundled only in the apps that can use it -- Quill Radio, Audio Studio, and Audio Converter -- so Weather, Cast, Social, Beacon, and Inkwell do not carry it. **Station > Update YouTube Support...** fetches a newer build when YouTube changes how it serves audio, so nobody is stuck waiting for the next Quill Radio release; an update installed that way takes precedence over the built-in copy from then on. (Making that precedence real took a small import-priority shim: inside a frozen build a bundled module would otherwise always win over an updated one, because PyInstaller's importer is consulted before the search path is.)
- **Paste a Live365 link and it just plays.** The Live365 link you actually have is almost never the stream -- it is the station page or the web player, both of them web pages that used to save as a station that could never play. Add Custom Station now recognizes any Live365 station page, player link, or bare station id and rewrites it to that station's real stream address, telling you it did. It is a pure text rewrite: no network lookup, nothing sent anywhere, and a link that isn't Live365 is passed through exactly as you typed it.
- **Export Favorites to Playlist (Station menu).** Save your stations to an M3U playlist you can hand to any media player, share, or keep as a plain-text backup outside Quill Radio. It is the twin of Import Stations from Playlist, and the two round-trip. Together with **Remove All...** in the Favorites Manager (confirmation plus rolling-backup recovery, #1201), this completes the requested "export, re-order the list elsewhere, clear it, and import it back" journey. (#1249, #1382)
- **A YouTube station knows what it is playing.** Finding the audio behind a link is one request, and that request answers with far more than an audio address. Quill Radio keeps all of it: the video's **length**, its **uploader**, its **description**, the **chapters the uploader published**, and whether a **caption track** exists -- none of it costing an extra moment or an extra connection. A live broadcast honestly reports no length, because it has no timeline.
- **A finished video has a timeline, so you can move around it.** This is what a live broadcast can never offer, and it is where a YouTube station stops being radio that happens to come from YouTube and starts being a player. On the **Playback** menu, working on any finished video: **Chapters...** (Ctrl+Shift+C) opens the uploader's own chapter list, each entry read as a whole sentence with the one playing now marked, and Enter jumps to it; **Next Chapter** (Ctrl+Alt+Right) and **Previous Chapter** (Ctrl+Alt+Left, which restarts the current chapter first); **Forward / Back 30 Seconds** (Ctrl+Shift+Right / Ctrl+Shift+Left); **Play Faster / Slower / Normal Speed** (Ctrl+Alt+Up / Ctrl+Alt+Down / Ctrl+Alt+0), stepping through round, speakable values from 0.25x to 4x and remembered for the next video; and **Where Am I?** (Ctrl+Shift+P), which speaks position, length, and the chapter you are in. Every one of them **says why when it declines** -- point any at a live stream and you hear "This is a live stream, so there is no timeline to move along", because a control that silently does nothing is worse than one that is not offered: you cannot tell it from a broken app. Times are spoken in words ("5 minutes 31 seconds") rather than as "5:31", which read aloud is an ambiguous pair of numbers.
- **Add from YouTube Playlist (Station menu).** Paste a `youtube.com/playlist?list=...` link -- prefilled from your clipboard if it is already there -- and Quill Radio lists the videos in the uploader's own running order, never re-sorted. Each row reads as a whole sentence ("3. Introducing layers, 5 minutes 31 seconds, 3Blue1Brown"), so a screen reader tells you everything about a video without arrowing across columns. Select what you want (Shift or Ctrl for several) and choose **Add Selected**, or take the lot with **Add All**; each becomes an ordinary station you can play, favorite, and record. It reports how many it added and how many were already in your favorites, so "Add All" on fifty videos never looks like a button that did nothing. Listing is deliberately shallow -- one request for the whole playlist rather than one per video -- and no video's audio is fetched until you play it. A *watch* link that happens to carry a `list=` is still just that one video: you asked for the video, and turning it into fifty stations without being asked would be a nasty surprise. The window is headed with the playlist's own name, read from the same request that fetched the list. Adding a playlist is an import, not a subscription or a play queue: the videos become ordinary favorites in your list (not a folder of their own), nothing plays through them in order, and nothing re-checks the playlist later -- run the command again on the same link to pick up videos added since, and duplicates are skipped.
- **Broadcast polish follows OptiLab Core 1.4.0.** Stream Polish's Auto-Adapt is restaged to match the upstream release: each stage now fades in over its own part of the slider using OptiLab's own smoothstep curve, instead of everything rising together on one straight line. The practical change is that turning Auto-Adapt up no longer drives every stage harder -- the leveler *eases off* as you raise it, and a separate slow lift supplies the loudness, which is what removes the edge-case volume jumps at the top of the range. That lift only responds to real program material now: silence, low-level noise and rumble no longer build gain. High frequencies get firmer control as the slider rises rather than the old flat presence boost, the limiter's lookahead lengthens toward the top, and the chain delivers to OptiLab's -0.1 dBFS target. Podcast Leveler and Smooth Limiter are unchanged -- 1.4.0's work is specific to Stream Polish. Adapted with thanks from OptiLab Core by dgl1984 (Apache-2.0).
- **Sound Enhancements answers Ctrl+E.** The three-band equalizer, compressor, channel mode, night mode, and broadcast polish have all been here since 1.0.2, but the dialog had no keyboard shortcut -- you went through the Playback menu or the Command Palette every time. It now opens with **Ctrl+E** in Quill Radio. (Inside full QUILL it stays on the Command Palette and is rebindable, since that chord family is spoken for there.)
- **Output Device on the Playback menu (Ctrl+Shift+D).** Switch the radio to another sound card or USB headset in one keystroke instead of opening Preferences. It changes the device immediately and remembers the choice, exactly like the Preferences setting it shortcuts. (#1253)
- **Report Bad Station.** A station that plays for the directory but not for you is something only you can flag. **Report Bad Station...** on any station's context menu (in Browse Stations and Search Stations) opens the normal Report a Bug flow pre-filled with that station's details -- name, stream, source, country -- so the report is complete on the first try. It carries station information only; never your name, email, or file paths. (#1218)
- **Repeat Last Announcement, and an Announcement Self-Test.** Speech is gone the moment it finishes; **Repeat Last Announcement** (Command Palette) brings the last thing Quill Radio said back. **Announcement Self-Test...** announces a phrase and then tells you which channels actually delivered it and through which backend, so "braille is broken" and "no display is connected" stop looking the same. Quill Radio also gains its own sound cues, all of which can be turned off or replaced from a sound pack.
- **Quillins in Quill Radio.** Quill Radio can run Quillins -- QUILL's small, sandboxed, permission-gated add-ons -- from its own Quillins menu. A Quillin declares which apps it is for, so only add-ons written for the radio appear. One thing a radio Quillin can do is contribute an extra station directory, which then shows up alongside RadioBrowser and the others when you search. Off in Safe Mode; third-party Quillins stay disabled in this release.
- **An interrupted recording ends up as one file.** When a stream drops mid-recording, Quill Radio reconnects and continues into a "(part 2)" file -- and now, when the recording finishes, it stitches the pieces back into a single recording under the name you expected. A show that dropped twice no longer leaves you three files to find and play in order. The join is a straight copy, so nothing is re-encoded and even a long capture takes seconds, and it is done in an order that cannot lose your audio: the joined file is written, verified, and only then put in place, and the parts are removed only once that has demonstrably worked. Anything that goes wrong -- a missing part, parts in different formats, an FFmpeg error -- leaves every part exactly where it is. You are told either way: "Joined 3 parts into one recording", or "Kept 3 separate parts" and the reason.
- **Spotify says up front what a free account can do.** Signing in now tells you which kind of account you have, instead of leaving you to discover it when a track refuses to start. The distinction is about *where* audio plays, not whether you may listen: **a free account can search Spotify and browse your library and playlists here**, and plays what it finds in the Spotify app, where the advertising that funds the free tier lives. Spotify does not license other applications to stream free-tier audio -- both routes another app could use are Premium-only in Spotify's own words ("The Web Playback SDK requires a Spotify Premium subscription"; "This API only works for users who have Spotify Premium") -- so a track started inside Quill Radio will not sound on a free account. Signing in free is still worthwhile for the finding, which is the part that is genuinely awkward with a screen reader. The user guide and release notes now carry the full setup step by step: how to get a Client ID from the Spotify Developer Dashboard, the exact redirect address to register, that the Client secret is **not** needed, and where in Quill Radio to paste the Client ID.
- **Spotify moved from the Help menu to the Station menu.** **Connect to Spotify...** and **Browse Spotify...** now sit on **Station**, below Find Streams from a Website. Spotify is somewhere you get stations *from* -- the same kind of thing as Browse Stations and Search Stations -- so Help was never where anyone would look for it.
- **Search YouTube from Find Stations.** Type a search and YouTube videos appear beside the radio directories, each an ordinary station you can play, favorite and record. No API key, no account, no setup: it uses the yt-dlp already bundled for YouTube links, via its keyless `ytsearch` extraction -- the same route FreeTube, NewPipe and Invidious take. The alternative, YouTube's official Data API, would put a Google Cloud project and a pasted API key in front of a search box, which is a wall, not a feature. The trade-off is honest and documented: extraction breaks when YouTube changes its site, which is precisely what **Station > Update YouTube Support...** exists to fix without waiting for a release. Flat, like the playlist listing it reuses -- one request for the result set, and no video's audio is fetched until you play it. Rows read "title, uploader" and carry the durable page URL, never a stream URL. Off in Safe Mode, and a failed search never blanks the other sources.
- **Choose what Find Stations searches (Station > Search Sources...).** Eight sources is wonderful when hunting and noise when you already know what you want, so any of them -- Radio Browser, TuneIn, iHeart, SomaFM, NOAA Weather Radio, Radio Reading Service, Spotify, YouTube -- can be switched off. A source that is off is **never contacted**: this gates the search fan-out itself rather than filtering results that were fetched anyway, so switching sources off genuinely makes searching faster and stops that source's network traffic. Deliberately not a checkbox list -- checkbox state in a wx list is announced inconsistently across NVDA, JAWS and Narrator -- so every row states its own condition ("On. YouTube. Videos, added as stations you can play and record.") and a button flips the focused row, announcing the outcome. Both the source selection and the Source filter in the results list are remembered across sessions; Reset to Default turns everything back on. Turning everything off is preserved as a real choice rather than being quietly re-enabled.
- **Spotify results in Find Stations.** Searching Spotify works on every account tier -- only playback is Premium-gated -- so Spotify results now blend into **Find Stations** alongside the radio directories once you have connected an account. One search returns stations, shows, and tracks together instead of asking you to remember which of two search boxes holds which kind of thing. Songs read as "title, artist" and shows as "show, publisher", because a list of bare titles is unusable when several share a name; results are interleaved by type so one prolific category cannot crowd out the others. Every row is labelled **Spotify** in the Source column and under a new **Spotify** entry in the Source filter. On a Spotify row, Shift+F10 offers **Open in Spotify** -- named that rather than "Open Website" because on a free account it is not a footnote about a home page, it is how you play the thing; Premium subscribers can just press Enter. If you have never connected Spotify, no Spotify rows appear and Find Stations behaves exactly as before. Off in Safe Mode, and a slow or unreachable Spotify never delays or blanks the other sources.
- **Spotify (experimental).** Quill Radio can play from Spotify through Spotify's own playback engine. It is marked experimental and ships in the app: no unlock code is involved any more. It still asks a great deal before it will do anything -- a paid Spotify Premium account, your own Spotify Client ID, and the Edge WebView2 runtime -- and nothing reaches Spotify until you deliberately connect an account, behind a one-time network-access consent and refused in Safe Mode. Spotify audio is copy-protected, so a Spotify selection cannot be recorded. Turn **Spotify** off in Manage Individual Features to hide it entirely.

- **Winamp's classic keys work in the Recordings player.** If you came to Windows audio through Winamp, its classic-skin main-window keys are still in your fingers -- and the Recordings window answered to exactly two of them (Ctrl+Up and Ctrl+Down for volume). The whole transport set is now live on the keys you already know: **X** play, **C** pause and unpause, **V** stop, **Shift+V** stop (Winamp's fade-out; this player has no fade, so it stops cleanly rather than pretending), **B** next recording, **Z** previous, **Left/Right** back and forward 5 seconds, **Shift+Left/Shift+Right** 30 seconds, **T** to swap between elapsed and remaining time, **J** to jump to a recording by typing part of its name, **Ctrl+J** to jump to a time (`90`, `1:30`, or `1:02:03`), and **L** to open. Every one of them announces what it did, so a key that did not land is never mistaken for one that did. Two deliberate differences from Winamp, both documented: **Ctrl+T** stays What's Playing, which is worth more in a radio app, so the elapsed/remaining toggle sits on plain **T**; and **Up/Down** keep moving through the list, which is what Winamp itself does in its Playlist Editor -- and this list is a playlist editor by any other name. Seeking needs a timeline, so on a live stream (or the classic Windows Media engine) the seek keys say why they cannot move instead of doing nothing, and a letter typed into a text field is never swallowed. Turn the letter keys off with **Winamp-style playback keys in the Recordings player** in Preferences if you would rather use them for list typeahead; volume is unaffected either way. Shuffle, repeat, and stop-after-current are deliberately absent: all three describe a play queue the recordings list does not have yet, and a key that only looks like it worked is worse than no key. (#1344)

#### Changed

- **Announcements now reach your braille display.** Everything Quill Radio speaks -- What's Playing, a finished refresh, a recording starting -- is now also written to a connected braille display, not only spoken. Nothing is truncated, an identical message inside two seconds does not steal the display twice, and braille never costs speech: an unplugged display or a reader that refuses the call degrades to "spoke but did not braille", never to silence. Turn it off with **Show announcements in braille** in Preferences > Accessibility. A *burst* of different messages no longer flickers across the display either -- the first message of a quiet period writes instantly and anything landing within the next 150 ms settles to the newest, with errors always writing through at once. (#1283)
- **The scheduled-recordings list is ordered by when each recording next occurs**, soonest first, rather than the order you entered them, and each row shows the stream's host in brackets so two similar entries -- or a duplicate still pointing at the original station -- are easy to tell apart. (#1220)

#### Fixed

- **Seeking a finished YouTube video no longer reports a live edge that does not exist.** **Rewind / Forward 30 Seconds** always ran the *live-stream* seek, which moves within mpv's rolling buffer and announces how far behind live you now are. On a finished video there is no live edge to be behind, so the number it spoke was invented. The keys now pick the operation the source actually deserves: a video moves along its own timeline and says "3 minutes 10 seconds of 18 minutes 40 seconds"; a live stream is completely unchanged. (This is also what finally reaches the video skip commands, which had been written for exactly this and had no caller at all.)
- **Show this file in Explorer really does select the file.** The Recordings list's **Open in Folder** passed Windows Explorer its `/select,` switch and the path as two separate arguments; Explorer wants them as one, and given two it quietly drops the switch and opens Documents instead. A window appeared, so it looked like it had worked -- and nothing told a screen-reader user that the wrong folder had opened. There is one tested implementation of this now, shared with QUILL and QUILL Cast.

- **The Command Palette now says which way every toggle is currently set.** Two people asked for this about **Announce Track Titles**: the palette lists a command's name and offers no checkmark, so the entry read the same whichever way the switch actually was -- which is the one thing you opened the palette to find out. It now reads **"Announce Track Titles (currently On)"** or **"(currently Off)"** and re-titles itself the moment you toggle it. That was never one entry's problem, though, so the fix was generalised: every on/off command in the palette now carries its own state, refreshed each time the palette opens. (#1383)
- **Quill Radio remembers your volume, and Ctrl+Up/Down works from anywhere.** The player started every session at 100% unless the station was a favorite with its own remembered level, so a non-favorite station came back at full blast on the next launch. The last level you set is now saved and restored (a favorite's own level still wins), and saving it no longer reloads the favorites list or re-announces the station. Separately, **Ctrl+Up** and **Ctrl+Down** only worked while the favorites tree had focus; they now work from any focus in the window -- except inside a text field, where Ctrl+arrow still edits text. (#1263)
- **"Copy What's Playing" and "What's Playing - Review and Copy" always answer you.** With a station playing, both commands could come back having done nothing at all -- no window, no copy, no message -- while with nothing playing they spoke a sensible message, which made the bug look inverted. Now, if a station is on, both fetch the title first ("Checking what's playing..."), then copy it or open the review window; a stream that sends no titles says so and still opens a window naming the station; a failed lookup is reported instead of silently swallowed; and the copy confirmation names what it copied. (#1282)
- **A recording that stops recording is now noticed, even when nothing reports a problem.** A stalled stream can leave FFmpeg alive and apparently healthy while the file stops growing, so the recording looked fine and captured nothing. Quill Radio now watches the recording file's size as a second, independent check: if it has not gained a byte across four checks in a row -- about a minute -- the recording is treated exactly like a dropped connection, so it reconnects and continues or stops and saves what it captured. The existing checks (FFmpeg's own read timeout, and watching for FFmpeg exiting) are unchanged; this one sits alongside them. It is patient enough that a slow network or a station's own rebuffering is never mistaken for a dead one, and it is never applied to a recording you have just asked to stop.
- **Recording filenames follow the computer's current time zone.** Change the computer's time zone (or ride a daylight-saving shift) while Quill Radio is running and new recordings are named with the new local time straight away -- no restart. Filenames used to keep stamping the zone that was in force when the app launched. (#1223)

#### Earlier work in 2.2.0 (landed 2026-07-24)

These entries were written when this material was expected to ship as its own
release. It never was, so they belong to 2.2.0 alongside everything above.

The headline of this release is how Quill Radio is delivered: a shared runtime installed once per user, two brand-new light downloads, an accessible runtime download, and a native launcher that no longer looks like repackaged Python to antivirus tools. It also gains a family switcher, a way to trim the app to just what you use, and a weather watch that speaks warnings as they are issued.

#### Added

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

#### Changed

- **Native launcher replaces the stamped `pythonw.exe`.** `QuillRadio.exe` is now a tiny, genuinely-compiled native program that starts the app on a real, unmodified Python. The full portable zip (`Quill-Radio-Portable-<version>.zip`, about 311 MB) remains fully self-contained with its own genuine Python and bundled ffmpeg and mpv. The full installer is now `Quill-Radio-Setup-Shared-<version>.exe` and installs the shared runtime (if absent) plus the app.
- The heavy surfaces (Browse Stations, Search Stations, Manage Favorites, Schedule Recording, Weather Center) are now modeless windows that each carry the full menu bar, fixing the reported "menu bar disappears" behavior and the modal lock-out of the main window. A Window menu and Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1-9 move between them.
- **Every destructive question now defaults to No.** Remove Favorite, Delete Folder, Remove Recording, Remove All Favorites, and Reset Sound Enhancements all used to open with Yes as the default button, so pressing Enter reflexively destroyed the thing. Enter is now always the safe answer and you choose Yes deliberately. A build check keeps it that way.

#### Fixed

- **Launching Quill Radio no longer crashes on a stray keystroke.** A key pressed at the wrong moment during launch could take the app down before its window appeared. (#1203)
- **Custom stations show up in Favorites the moment you add one (#1205).** Adding a custom station saved it, but the favorites list did not visibly update, so it looked as though nothing had happened.
- **Browse Stations picks up new listings after an in-place update (#1207).** The previous version's station-directory cache, still inside its freshness window, could keep showing the old listings; the newer bundled directory now wins (a directory you refreshed yourself still wins over both).
- **New Folder (Ctrl+Shift+E) works from the favorites tree (#1211).** The shortcut was advertised, but a focused favorites tree swallowed it before it could fire.
- **Audio no longer keeps playing after you exit (#1195).** On the real exit path the mpv playback engine only soft-stopped and left its final teardown to a window event, so audio could outlive the app. (Ctrl+W and the window X still minimize to the tray by design and keep playing -- use Exit to quit.)
- **Song information shows for more stations (#1215).** Some stations -- notably HLS streams -- put the current track where Quill Radio was not looking, so the now-playing title came up empty. It now reads both places.
- Favorites keep the hand-arranged order you gave them when you move an item from a sorted view. Explicit Exit quits for real. Keyboard focus lands inside the window on launch so Alt reaches the menu bar. The transport button no longer claims Alt+S/Alt+P, so Ctrl+P is the reliable Stop/Play key (#1208). Add to Favorites resolves a TuneIn stream on demand (#1210). Remove All favorites with confirmation and rolling-backup recovery (#1201).

#### Security

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
