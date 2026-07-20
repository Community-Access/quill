# Quill Radio -- Product Requirements

Version 2.0

## 1. Product statement

Quill Radio is QUILL's internet radio, shipped as its own small Windows app for people who want the radio on without loading a full writing environment. It is screen-reader-first, keyboard-complete, and deliberately small -- and by 1.0 it is a complete radio product: organization, recording resilience, timers, and appliance-grade startup.

## 2. Architecture requirement: not a fork

- R-1. All feature code lives in the upstream `quill` package (`quill.apps.radio`, `RadioMixin`, `AppShellFrame`, `quill/core/radio/*`, `quill/ui/radio/*`). This repository contains only the product wrapper (entry point, icon, installer, docs). Nothing here reimplements a feature.
- R-2. The app stays in sync with QUILL by construction: the wrapper depends on `quill` from the upstream repository, and the one-file build pulls the entire package. Divergence is only permitted for content that exists because QUILL is not in the picture.
- R-3. Data is shared, not copied: favorites (folders, custom names, per-station volumes), recently-played history, recordings, schedules, the wake-up timer, and settings live in the same `%APPDATA%\Quill` store QUILL uses.
- R-4. Keystrokes are the app's own (menu accelerators), kept separate from QUILL's keymap so nothing collides with editor shortcuts.

## 3. Scope (all reused from upstream; all shipped in 1.0)

**Listening**
- Station browser over four blended directories -- RadioBrowser, SomaFM, iHeart, TuneIn -- with a Source facet, genre/country dropdown filters, test-play, and favorite; bundled ACB Media directory; custom stream URLs; website stream finder with a Test/Stop Test toggle.
- iHeart and TuneIn directory sources + Unified Find Stations (upstream `core/radio/iheart.py`, `core/radio/tunein.py`, `core/radio/directory_search.py`; #1116, #1117, #1132). iHeart is indexed from its public XML sitemap (`www.iheart.com/sitemap.xml` -> the `livestations` sub-sitemap, two HTTPS GETs) and each station's real stream (iHeart-native HLS or a StreamTheWorld redirect) is resolved lazily from its own page on demand; the sitemap index is cached once per Browse Stations session with a Refresh button, and a name search resolves up to `IHEART_RESOLVE_CAP = 5` matches. TuneIn goes through RadioTime's open OPML API (`opml.radiotime.com` -- `Search.ashx`/`Browse.ashx`/`Tune.ashx?partnerId=RadioTime`, no key/auth; a bad guide id self-validates to "nothing found"), resolving up to `TUNEIN_RESOLVE_CAP = 10` per search. `directory_search.merge_and_rank` blends all four sources into one de-duped (by stream URL, then name+country), exact-match-first list; each non-RadioBrowser row is labeled "via <source>". The Browse Stations dialog adds a Source facet dropdown (All sources / RadioBrowser / iHeart / TuneIn / SomaFM / ACB Media / Website) and turns the tag/country free-text into a genre editable combo and a country dropdown auto-filled from the directory (choosing one fires the search). Find Streams also resolves iHeart/TuneIn station pages directly (`link_finder` `_PORTAL_HOSTS`, `_tunein_candidates`; #1131, #1105, #1087). All failure-tolerant (a down source never blanks the list), egress via each client's single reviewed `_fetch`, off in Safe Mode via `refuse_in_safe_mode`. This reverses the earlier "TuneIn deliberately left out" non-goal (upstream QUILL PRD §5.84f), approved 2026-07-17; TuneIn uses RadioTime's public API, not a competitor-data scrape.
- JavaScript-player resolution in the website stream finder (upstream `core/radio/triton.py`): Triton Digital / StreamTheWorld players (the `player.listenlive.co` network and thousands of broadcast stations) compute their stream URL in JavaScript, so it never appears in the page HTML and a plain-HTML scan finds nothing. Quill Radio detects the player, reads the station callsign from the Triton PWA's own logo asset name, and resolves it to a real playable mount through Triton's JS-free provisioning API (`playerservices.streamtheworld.com`), offering both the MP3 and AAC streams. Gated to pages that actually are Triton players and to a callsign the API validates, so it never surfaces a wrong stream; the response is parsed through the hardened `core/safe_xml` wrapper. One added egress, inventoried in QUILL's network-egress audit (§N-1), reached only from the same explicit Scan button and disabled in Safe Mode.
- One transport control (Play becomes Stop), mute, volume with per-station memory, single-player rule (starting any stream silences sibling media, radio or podcast, in every app).
- What's Playing (Ctrl+T) with a clean, configurable announcement (upstream `core/radio/now_playing.py`, #1068): parses the `key="value"` broadcast-automation metadata some stations pack into their ICY StreamTitle (and the plain "Artist - Title" convention) into title/artist fields, and renders them through a user-set token template (`{title}`/`{artist}`/`{raw}` with `[optional]` segments) stored in `RadioHistory.now_playing_template` and edited in Preferences (Ctrl+,). Default `{title}[ by {artist}]`. 2.0.1 adds review/copy: `radio.whats_playing_details` opens a read-only, selectable, character-reviewable dialog with a Copy button, and `radio.copy_whats_playing` copies the clean text straight to the clipboard (#1134).
- What's Playing server status-endpoint fallback (upstream `core/radio/station_status.py`, #1111, #1112): when the ICY side-tap and the playback engine's own `media-title` both come up empty (common on HLS), Quill Radio reads the current title from the stream server's own public now-playing status endpoint -- Icecast `/status-json.xsl`, SHOUTcast v2 `/stats?json=1`, or v1 `/7.html` -- on the same host it is already streaming from. Same-host only, off in Safe Mode.
- Paged station search (upstream `radio_browser.search_stations` offset + the Browse Stations dialog, #1064): 200 most-listened-first results per request (was 50) plus a More Stations button that pages the RadioBrowser directory beyond the first page; a finished search states when more exist and suggests narrowing.
- Self-healing stream recovery (upstream `core/radio/recovery.py`, #1065): on a playback error, a confidence-ordered ladder runs off-thread -- re-resolve a moved StreamTheWorld mount, refresh the URL from the directory, then (opt-in, `RadioHistory.recover_from_website`, default on, off in Safe Mode) scan the station's website with the shared Triton + "Listen Live" link-following scanner. A single unambiguous result auto-plays and self-heals the favorite; multiple candidates are announced for the user to pick in Find Streams. One attempt per station per session; all egress via the already-reviewed sites. `link_finder` also now follows a bounded allowlist of listen/live/play/tune-in `<a>` links one level deep, benefiting the manual Find Streams too.
- Recently Played (capped, de-duplicated), Play Last Station, optional resume-on-launch.
- What's Playing: ICY track titles on demand and optional announce-on-change (off by default).
- Stream fallback: a directory station whose stream errors is re-fetched by uuid and retried once, self-healing the saved favorite.

**Organization**
- Favorites Manager: nested path-based folders, live rich search, Move Up/Down, Mark-and-Move (Move Above/Below adopting the destination folder), station rename (custom display names used everywhere), folder rename carrying descendants, folder delete that returns stations to the top level.

**Recording**
- Record now; Record Station (a different station than the one playing, for N minutes); scheduled recordings (once/daily/weekly).
- Concurrent recording (2.0.2, upstream `quill/core/radio/*`, `ui/radio/*`): the recorder holds any number of independent recordings, not one. `RadioRecorder` became a manager of `{job_id: RecordingJob}` -- each job owns its own ffmpeg process, recent-stderr tail (no cross-contamination of the fatal/transient verdict), reconnect counter, user-stopped flag, Windows kill-on-close handle, and resume marker; `active_jobs()`/`job(id)`/`active_count` replace the old scalar `current_*` getters (kept as back-compat), `stop(job_id)` / `stop_all()` replace the single `stop()`, and the state-changed callback carries the `job_id`. `RecordingSettings.max_concurrent_recordings` caps concurrency (0 = unlimited, the default); at the cap `start()` raises `RecordingLimitError` (a `RecordingError` subclass) and the scheduler holds the entry pending via `on_busy` and retries within its window -- the old "already in progress" hard refusal and its fragile string-match in the scheduler are gone, so overlapping scheduled shows all record. A reconnect reuses the same `job_id` (and the original `started_at`/`scheduled_end`) so a recording's row and marker keep a stable identity across a drop. Record Now targets the listened station (`_radio_playing_job_id`): stop it if it is recording, else start a new job; Record Station's single-recording guard is removed. UI: the Recordings window lists one row per active recording with per-row **Stop Recording** (by job id) and **Stop All Recordings** (shown at >=2), mirrored in the Record menu and the tray/status menu (`radio.stop_all_recordings`); the status bar / tray read "(N recording)". Crash-resume is multi-marker: `recording_resume.py` writes one `<job_id>.json` per recording under a markers directory (migrating a legacy single-marker file), and launch offers a single `ResumeRecordingDialog` for one interrupted recording or a batched `ResumeRecordingsBatchDialog` for several. Everything lands in the shared `quill` package; nothing is vendored into the wrapper.
- Schedule management (upstream `ui/radio/schedule_recording_dialog.py`, #1106): Edit an entry in place, Duplicate it, and Enable/disable it without deleting (a disabled entry renders "(disabled)" and does not fire); 12-hour or 24-hour time entry (`parse_time_of_day`, "7:30 PM" or "19:30"); and a per-entry time-zone dropdown ("(local time)" plus all zoneinfo zones) so an entry fires at the correct absolute moment and the list shows zone-labeled times.
- Recordings list: live status (Recording with growing size / Recorded / Scheduled), Play, Stop Recording, Open in Folder, Remove. Refresh is an in-place diff keyed by file path (no-op when unchanged; selection/focus/scroll preserved), not a rebuild; the active row shows a live elapsed time and scheduled rows show their zone-labeled times; the tray tooltip carries "(recording)".
- Auto-reconnect: ffmpeg HTTP reconnect flags plus process-level retry into numbered part files; enabled/attempts/spacing configurable; user stops and duration-cap finishes never retry.
- Settings: format (mp3/ogg/flac/wav, plus a raw stream-copy mode), bitrate, destination, filename pattern with tokens, max-duration safety cap.
- Raw/lossless capture (upstream `core/radio/recording.py`, listener request): a "Raw stream -- exactly as sent, no re-encoding (lossless)" format (`format="copy"`) stream-copies the server's audio packets with ffmpeg's `-c:a copy` -- no decode, no re-encode -- so the saved file is bit-for-bit the original broadcast, the most faithful capture for a listener who wants to do their own lossless editing/conversion. Bitrate and Sound Enhancements are meaningless with no re-encode and are dropped. The output container follows the stream's own codec, chosen from a one-time bounded `ffprobe` of the first audio stream (mp3->`.mp3`, aac->`.aac`, vorbis->`.ogg`, opus->`.opus`, flac->`.flac`, ...), falling back to Matroska audio (`.mka`) for anything unrecognized -- a universal lossless copy container; a missing/failed probe degrades to `.mka` rather than blocking the recording, and the resolved extension is reused across auto-reconnect continuation files.
- Recording reliability (upstream `quill/core/radio/*`, 2.0.0; R1-R4): a reported round of recording bugs closed in four phases, delivered in the 2.0.0 release. (R1) the Recordings list is an in-place diff keyed by file path -- a screen reader is no longer yanked to the top mid-read; the active recording is counted from the recorder itself (a temp-folder recording is no longer invisible), a firing schedule is no longer double-counted, completed one-time entries drop out of the scheduled count, and the active row shows a live elapsed time. (R2) the scheduler uses a next-due-timestamp window model (an entry is due from `start` through `start + duration`, so a late arrival starts with the remaining minutes and launch catch-up is free); `last_fired` is stamped by entry id only on a successful start, `once` entries auto-disable after firing, a same-minute conflict defers via `on_busy`, and the scheduler thread is lock-guarded and can no longer die silently. (R3, new feature) resume across restart: an `ActiveRecordingMarker` is written at start and cleared on a clean stop (a crash leaves it); on launch, `reconcile_temp_strays` moves finished temp orphans to the destination and leaves a still-writing file untouched, then per `RadioHistory.recording_resume_choice` (`ask`|`always`|`never`, default `ask`) Quill Radio offers to resume for the remaining minutes within a 10-minute grace via an accessible dialog (Resume/Skip/Don't-ask-again; a corrupt marker is discarded). (R4) pipeline hardening: a reconnect records only the remaining time to `_scheduled_end` (not a fresh full duration); `uniquify()` replaces the unconditional `-y` overwrite and continuation parts keep the original start timestamp; a drop is classified fatal (disk full / HTTP 404/410/451 only, narrowed in 2.0.1 so a transient 403/408/5xx/network drop reconnects) vs transient before any reconnect attempt is spent, with the stderr tail cleared on a reconnect/progress signal so a recovered-from error cannot poison a later verdict; and on Windows ffmpeg runs in a job object with `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` so a crashed host takes the child down, with the stop wait moved off the UI thread. Everything lands in the shared `quill` package; nothing is vendored into the wrapper.

**Timers**
- Sleep timer (shared radio/podcasts fade-and-restore).
- Wake-up timer: once or daily at HH:MM; fires only within a 5-minute window (never retro-fires); "once" disables itself; requires the app running (tray counts); honest about that in the UI.

**Shell**
- System tray with full controls and the app's own icon; Send to Tray (Ctrl+W) and Exit; hardware media keys (play/pause, stop) system-wide while running, never stolen from an app that already owns them, released on exit.
- Command Palette scoped to the app's registry; Redeem Unlock Code (shared store); in-app update check that downloads the installer with spoken progress and offers Install now; About.
- Unlock-gated Audio Description Project menu when `future.adp_assistant` is unlocked.
- Diagnostics (upstream `core/radio/radio_logging.py`, `RadioHistory.debug_mode`/`log_dir`; #1130, #1124, #1122): a Verbose logging (debug-mode) checkbox in Preferences applied live via `set_radio_debug` (no restart), and a settable Log folder; recording stderr is captured into the log so a failed capture leaves a trail.

Out of scope by decision: QUILL's editor, AI, speech transcription, braille, and TTS stacks (not installed); a custom update engine beyond download-and-run.

## 4. Accessibility requirements

- A-1. Every interactive element has an accessible name; upstream inventory gates audit the shared surfaces.
- A-2. Focus lands on the favorites list at launch; focus dead zones are defects.
- A-3. All dialogs route through the shared dialog contract (modal ids, focus placement, region announcements) and are registered in the dialog inventory.
- A-4. Every action announces its outcome; silent state changes are defects. Track-title announcements are opt-in so ambient chatter never surprises anyone.
- A-5. Full keyboard operation including manager reordering and the tray menu; Delete/F2/Enter conventions consistent across lists.

## 5. Packaging requirements

- P-1. PyInstaller onedir build with the app's own icon; Inno Setup installer with its own AppId installing to {autopf}\Quill Radio, per-user by default.
- P-2. Everything bundled, nothing downloaded at install or runtime: the onedir build carries the whole quill package and data; ffmpeg installs to {app}\tools\ffmpeg and libmpv (the mpv playback engine, with its GPL license texts and source-offer note) to {app}\tools\mpv, both found via the wrapper exporting QUILL_APP_ROOT. A portable zip ships the same onedir build plus a `data\` folder that switches storage to travel with the app.
- P-3. Uninstall never deletes `%APPDATA%\Quill` -- QUILL or QUILL Cast may still use it.
- P-4. Release artifacts: `Quill-Radio-Setup-<version>.exe`, tagged `v<version>`, which Help > Check for Updates compares against and downloads.

## 6. Network requirements

- N-1. Every outbound surface is inventoried in QUILL's network-egress audit: RadioBrowser and SomaFM (search/tags/countries/click-votes/byuuid fallback); iHeart (`www.iheart.com` public sitemap index + on-demand station-page GETs to resolve a stream); TuneIn via RadioTime's OPML directory (`opml.radiotime.com` search/browse/tune, `partnerId=RadioTime`, no key); the user-typed page for Find Streams (plus, for a Triton/StreamTheWorld player page or an iHeart/TuneIn page, one follow-on call to that provider's public API to resolve the stream); the playing stream itself for ICY titles and, as a same-host last-resort for What's Playing, that stream server's own Icecast/SHOUTcast status endpoint; and this repository's GitHub releases for the update check. Playback (mpv) and the metadata/status requests send a "Quill Radio" User-Agent. No telemetry of any kind. (Sound Enhancements' local relay, §8, is loopback-only and never reaches the network itself -- it filters the same stream this section already covers.)
- N-2. Safe Mode disables the radio's network surfaces along with the feature.

## 7. Non-goals

macOS/Linux standalone builds (upstream QUILL covers macOS; the tray pattern does not exist there), auto-updating in place, telemetry. A full DSP effects rack (reverb, tempo/pitch, spatial audio) -- Sound Enhancements (§8) is a small, purpose-built three-band EQ and compressor, not a general effects rack.

## 8. Since 1.0

- **2.1.1 (upstream `quill/core/radio/wxindex*.py`, `core/radio/reading_services.py`, `core/radio/directory_search.py`, `ui/radio/browse_tree_dialog.py`, `ui/main_frame_weather.py`, `apps/radio.py`).**
  - *NOAA Weather Radio via WeatherIndex.* The Browse "Weather / NOAA" source drops the fuzzy RadioBrowser name search (`radio_browser.noaa_weather_stations`, removed) for the authoritative **WeatherIndex** directory (api.wxindex.org): a lazy State -> Station tree (call sign, frequency, place), SAME-code / callsign / "County, ST" routing in unified search (`directory_search.wxindex_search_stations`), and Weather menu > **Listen to your Local NOAA Weather Radio**, resolved from the saved Weather location's county and coordinates (`wxindex.local_stations`: county/SAME match first, nearest covering transmitter fallback). A three-tier resolver -- live API (Safe-Mode-blocked, in the network-egress audit) -> app-data cache (`<app_data>/radio/wxindex-cache/`) -> bundled snapshot `quill/data/noaa_directory.json` (1,035 transmitters across every state and territory; regenerated by `scripts/snapshot_wxindex.py`) -- keeps every capability working offline and outliving the API. Weather menu > **Update NOAA Weather Radio Directory** force-pulls the directory into the cache tier on demand; the bundled snapshot is the permanent floor and is never overwritten. Stations adapt to `RadioStation` (`wxindex.to_radio_station`), so Favorites, recording, and scheduling work unchanged. Partially delivers the §18 NWR stream capability (directory + streams; alert interruption and generated audio remain future work). Detailed in §18.5.
  - *Radio Reading Services.* A new "Radio Reading Services" Browse category and unified-search blend (`directory_search.reading_services_search_stations`) for the audio information services that read print aloud for blind and print-disabled listeners. 20 vetted services ship as a bundled snapshot (`quill/data/reading_services.json`); Station > **Update Radio Reading Services** refreshes live from RadioBrowser through a cache -> live -> snapshot resolver mirroring wxindex (Safe-Mode-guarded). Detailed in §18.6-18.7.
  - *iHeart in Browse.* iHeart, previously search-only (upstream §8, 2.0.0), gains a Browse Stations branch: genre folders, each an A-Z sub-directory, all lazy (`ui/radio/browse_tree_dialog.py`). The XML sitemap the search path uses carries no genre, so browse reads iHeart's free, keyless JSON content API (`us.api.iheart.com`: `/content/genre`, `/content/liveStations?genreId=`), where each row embeds its own stream -- one GET per genre, no per-station page fetch. New core: `iheart.parse_genres`/`parse_genre_stations`/`fetch_genres`/`fetch_genre_stations`, routed through the existing reviewed `iheart._fetch` egress site (rationale expanded to cover the content API). Safe-Mode-guarded.
  - *Unified-search Source filter de-dup fix.* A station carried by more than one directory (e.g. a SomaFM channel RadioBrowser also lists) was de-duplicated to a single result, so the Source facet could hide it under the wrong directory. `directory_search.merge_and_rank` now records every absorbed duplicate's source on a transient, identity-neutral `RadioStation.alt_sources`, and the facet matches the full set via `directory_search.station_source_labels`; the result row still badges the winning source.
- **2.0.2 (upstream `quill/core/radio/*`, `quill/apps/radio.py`, `quill/ui/radio/*`).**
  - *Channel mode Left/Right one-ear fix.* 2.0.1's `pan=stereo|c0=c0|c1=c0` duplicated a single source channel to both outputs; corrected to send the whole stereo field to one output and silence the other (`pan=stereo|c0=0.5*c0+0.5*c1|c1=0*c0`, and the mirror for right) in `core/audio_enhance.py`.
  - *Favorites sort order.* `RadioHistory.favorites_sort` (az/za/manual, default az) + per-folder `folder_sort_orders`; non-mutating `RadioFavoritesStore.favorites_in_display_order` / `folders_in_display_order` so the manual order survives. Applied to the main tree, the Favorites Manager (Move buttons disabled for sorted folders), and the Station-menu submenu; re-sorts on add. Preferences choice for the default; a folder context-menu override.
  - *M3U/M3U8 station import.* Pure `core/radio/playlist_import.parse_m3u` + `split_new_and_duplicates`; Station > Import Stations from Playlist... with folder targeting/creation at any depth and a skip-vs-import-all duplicate prompt.
- **2.0.1 fast-follow (upstream `quill/core/radio/*`, `quill/ui/radio/*`).** From the first round of live feedback:
  - *Recording reconnect classification narrowed.* `_FATAL_STDERR_RE` (`core/radio/recording.py`) now matches only genuinely-terminal outcomes (disk full; HTTP 404/410/451); a transient 403 (rotating CDN token), 408/409, 5xx, or bare EOF reconnects within the attempt budget. The stderr tail is cleared on a reconnect/progress signal (`_RECOVERY_STDERR_RE`) so an error ffmpeg recovered from can't poison a later drop's verdict -- fixing "recording stops after ~1 minute" reports.
  - *Recording-started announcement.* Record Now / Record Station announce "Recording started: <station>" (`main_frame_radio.radio_record_toggle` / `open_record_station_dialog`).
  - *What's Playing review/copy (#1134).* New `radio.whats_playing_details` (a read-only, selectable, char-reviewable `NowPlayingDialog` with Copy) and `radio.copy_whats_playing` (`_copy_to_clipboard`); no new setting.
  - *Channel mode.* `RadioHistory.channel_mode` and `FavoriteStation.channel_mode` (stereo/mono/left/right) replace the `mono_enabled` bool (migrated on load). `audio_enhance` gains left/right pan filters (`pan=stereo|c0=c0|c1=c0` / `...|c0=c1|c1=c1`); the Sound Enhancements dialog's mono checkbox becomes a Channel-mode RadioBox. Global default AND per-station override (resolved with the EQ via `_radio_resolve_enhancement`); night mode stays global.
  - *Recording-playback volume.* A `Ctrl+Up/Down` char-hook on the (modal) Recordings dialog drives the shared controller's volume, so a played-back recording is adjustable like a live stream.
- **Recordings reliability overhaul (2.0.0, upstream `quill/core/radio/*`; R1-R4).** The headline of 2.0.0: a reported round of recording bugs closed and the one missing piece added -- a recording that survives a restart. Resume across restart with an ask-on-launch dialog and a 10-minute grace window; window-based scheduling with launch catch-up; a flicker-free, place-keeping Recordings list with honest counts and a live elapsed time; and pipeline hardening against dropped connections, dead streams, and a crashed host. Detailed as delivered scope in §3 (Recording). Everything lands in the shared `quill` package; nothing is vendored into the wrapper.
- **iHeart and TuneIn directories + Unified Find Stations (2.0.0, upstream `core/radio/iheart.py`, `core/radio/tunein.py`, `core/radio/directory_search.py`; #1116, #1117, #1132).** Two of the largest internet-radio directories added as keyless, account-free station sources blended into Browse Stations, with a Source facet, genre/country dropdown filters, "via <source>" result labels, a Refresh button for the cached iHeart index, and iHeart/TuneIn page resolution in Find Streams. Detailed as delivered scope in §3 (Listening). Reverses the earlier TuneIn non-goal (upstream QUILL PRD §5.84f), approved 2026-07-17.
- **Schedule management (2.0.0, upstream `ui/radio/schedule_recording_dialog.py`, #1106).** Edit, Duplicate, and Enable/disable for schedule entries; 12-or-24-hour time entry; per-entry time zones with zone-labeled list times. Detailed in §3 (Recording).
- **What's Playing server status-endpoint fallback (2.0.0, upstream `core/radio/station_status.py`, #1111, #1112).** A same-host last resort reading the stream server's own Icecast/SHOUTcast now-playing status page when ICY and the engine title channel are both empty. Detailed in §3 (Listening).
- **Diagnostics (2.0.0, upstream `core/radio/radio_logging.py`; #1130, #1124, #1122).** A live Verbose logging (debug-mode) checkbox and a settable Log folder in Preferences, with recording stderr captured to the log. Detailed in §3 (Shell).
- **The mpv playback engine (1.1.0, upstream `quill/ui/radio/mpv_radio_engine.py` + `player_controller.py`, #1076).** A second, preferred audio backend: libmpv, live-stream-aware (readiness from `core-idle`, not the duration a live stream never reports), bundled at `{app}\tools\mpv`. `RadioHistory.playback_engine` = auto (mpv when present) / wx ("Windows Media (classic)", the byte-for-byte pre-1.1 escape hatch) / mpv; one silent cross-engine rescue per play attempt in either direction. Combined stream-format coverage is effectively complete: MP3, AAC and HE-AAC (AAC+), Ogg Vorbis, Opus, FLAC streams, and HLS (m3u8) -- Ogg Vorbis/Opus/HLS were undecodable by WMP. The engine delivers: **Radio output device** (Preferences; `RadioHistory.output_device`; screen reader and app sounds stay on the system default; unplugged devices remembered, spoken fallback when unusable); **live DVR** (a seekable ~45-minute demuxer cache: pause/resume live radio, Rewind/Forward 30 Seconds, Back to Live, each announcing how far behind live); **Volume Boost** (up to 150% for quiet stations; the 0-100 scale, per-station volumes, and mute untouched); **engine-native What's Playing fallback** (mpv `media-title` when the ICY side-tap gets nothing or the stream is HLS); and **"Buffering..." announcements** on mid-stream stalls.
- **OptiLab broadcast polish (2.0.2, upstream `core/audio_enhance.py`, `ui/sound_enhance_dialog.py`).** One-touch broadcast-processing modes in Sound Enhancements, adapted from OptiLab Core by dgl1984 (github.com/dgl1984/optilab, Apache-2.0). OptiLab is a GUI-only plugin (JSFX/CLAP/Winamp DSP) with no library API and a Windows-64-only binary, so rather than hosting the binary the modes reproduce the *shape* of its three chains -- Podcast Leveler (HPF -> speechnorm -> acompressor -> 65 Hz tame -> alimiter), Stream Polish (dynaudnorm -> acompressor -> presence -> alimiter), Smooth Limiter (acompressor -> alimiter) -- as ffmpeg filter chains appended last in `build_filter_graph` (their lookahead limiter guards the output), so they ride the same three delivery paths (mpv-native live, relay, recordings) and work cross-platform. Controls map OptiLab's onto ffmpeg: Mode picks the chain, Input is a front-end `volume` trim (0 dB default, per product choice), Auto-Adapt (0-100%) leans the leveling/density more assertive. A bypass checkbox (`optilab_enabled`) keeps the chosen mode remembered while off. Stored on `RadioHistory` and, as of 2.0.2, also per-station on `FavoriteStation`, carried by `RadioPlayerController.set_sound_options`/`preview_enhancements` and resolved per stream by `ResolvedEnhancement`. A faithful adaptation, not a bit-for-bit port; credited in release notes, the About box, and the third-party notices.
- **Live Sound Enhancements preview + fully per-station (2.0.2, upstream `ui/sound_enhance_dialog.py`, `ui/radio/player_controller.py`).** Every control in the Sound Enhancements dialog previews live on the playing stream via an `on_live_change` callback (debounced ~180 ms) into `RadioPlayerController.preview_enhancements` (one apply for the whole set, so a wx drag reconnects once, not per field; mpv applies natively). OK keeps; Cancel/Escape reverts to the snapshot captured on open (the Reset button's own restore is exempted). And all listener-level settings -- previously EQ/compressor/channel per-station but night mode + OptiLab global-only -- are now per-station as well as global: `FavoriteStation` gained `night_mode_enabled`/`optilab_*`, `set_enhancement` and the `ResolvedEnhancement` NamedTuple carry the full set, `play_station` applies all of it per stream, and `open_sound_enhancements` saves the whole dialog to the favorite override (when a favorite plays) or the shared `RadioHistory` default (otherwise). Reset to Default and Reset All Stations both restore the shared default including night mode and OptiLab.
- **Sound Enhancements** (Playback > Sound Enhancements...): a three-band equalizer (Bass/Mid/Treble sliders, -12 to +12 dB) and a compressor, applied live via an ffmpeg filter graph relayed to the playback engine over a loopback-only local HTTP server -- or, on the mpv engine (1.1.0), natively inside the player with no relay and with changes heard live, no reconnect. Off by default. 1.1.0 adds two listener-level (deliberately global, not per-station) options riding the same shared graph everywhere including recordings: **mono downmix** (single-sided hearing / one earbud -- hard-panned content never disappears) and **night mode** (real-time loudness normalization lifting quiet passages), plus the Small Speakers and Late Night quick presets. A "Quick preset" shortcut sets all three sliders at once. Remembered per favorite station (a whole-record override on `FavoriteStation`, mirroring QUILL Cast's per-podcast override) as well as a shared default in `RadioHistory`; `RadioPlayerController` resolves which applies via an injected callback at the top of every `play_station`. Recording Settings' "Apply Sound Enhancements to recordings" (off by default) optionally records the filtered audio too.
- **SomaFM**, a second free, keyless station directory, blended into Browse Stations search alongside RadioBrowser.
- **Exit/Minimize to Tray confirmation**: closing the window asks Exit, Minimize to Tray, or Cancel (with a one-time "Don't ask me again"), instead of always exiting immediately and silently stopping an in-progress recording. Adjustable in Preferences.
- **Quieter dialogs and a real "up to date" answer**: dialog-transition announcements are now off by default (Preferences), and a manual Check for Updates that finds nothing newer shows a dialog instead of only announcing it.
- **In-app documentation**: Help > User Guide / Release Notes / Product Requirements open the bundled docs in your browser.

See `CHANGELOG.md` for the full, versioned history.

## 9. QUILL Weather -- full product requirements

The following is the complete QUILL Weather product-requirements document. The Weather menu shipped in 2.1.0 implements its text-only first slice; the sections below describe the full roadmap.

## QUILL Weather
### Product Requirements Document

**Working title:** QUILL Weather  
**Ecosystem:** QUILL / QuillVille  
**Document status:** Product definition and implementation-ready working draft  
**Version:** 1.0  
**Date:** July 19, 2026  
**Primary platforms:** Windows first; macOS next; iOS considered in later phases  
**Product posture:** Accessibility-first, screen-reader-first, keyboard-first, local-first, provider-based, safety-conscious

---

## 1. Executive Summary

QUILL Weather transforms official weather data into an immediate, understandable, highly configurable, and delightfully accessible weather experience.

It is not merely a weather screen. It is a persistent **Weather Guardian**, an accessible **Weather Center**, a flexible **audio weather channel generator**, a location-aware **Alert Center**, and a deeply configurable **Voice Studio** built on the QUILL speech framework.

A user should be able to:

1. Add a home, work, family, travel, event, or temporary location in seconds.
2. Hear current conditions immediately.
3. Receive watches, warnings, advisories, updates, and cancellations as soon as QUILL receives them.
4. Continue receiving alerts while the main QUILL window is closed, provided QUILL Weather Guardian is running.
5. Assign different voices, engines, rates, volumes, earcons, verbosity levels, and interruption rules to different weather feeds and alert scenarios.
6. Build continuous generated audio channels from authoritative weather data.
7. Listen to a live community NOAA Weather Radio stream when one is available.
8. Understand where every piece of weather information came from, when it was issued, when it was last checked, and whether it may be stale.
9. Use every major feature without sight, without a mouse, and without needing to interpret a visual map.

The initial primary data provider will be the United States National Weather Service at `api.weather.gov`. The NWS API provides forecasts, hourly forecasts, observations, alerts, zones, stations, and grid data as open government data. It is cache-aware, supports conditional requests, and requires an identifying User-Agent. NWS recommends requesting alert updates no more frequently than every 30 seconds.

For faster alerts, a later QUILL Alert Relay can subscribe to the NOAA Weather Wire Service Open Interface. NWS describes NWWS as its fastest method for receiving text alerts and weather products, generally within 10 seconds of issuance. The relay will reconcile those pushed products with the public NWS alerts API and deliver normalized updates to subscribed QUILL clients.

QUILL Weather must never imply that it replaces Wireless Emergency Alerts, a physical NOAA Weather Radio, local emergency instructions, or other official safety channels. It is an additional accessible delivery and interpretation tool.

---

## 2. Product Vision

### 2.1 Vision statement

> Weather should never be hidden behind a map, buried in a dashboard, delayed by an inaccessible workflow, or spoken in a voice the user cannot understand.

QUILL Weather meets people where they are. It provides as much or as little weather information as the user wants, in the voice they choose, for the places and people they care about.

### 2.2 Product promise

QUILL Weather makes five promises:

#### Everything can be reached

Every location, alert, forecast period, setting, history item, source status, and audio control is keyboard accessible and represented through native or predictably accessible controls.

#### Important state is never hidden

An alert’s status, severity, urgency, certainty, effective time, expiration, affected area, source, update history, and delivery state are available as text and speech. Color, icon, animation, and screen position are never the only means of conveying meaning.

#### Official information remains official

QUILL preserves the source alert, its identifiers, its lifecycle, and its authoritative text. QUILL may organize or deterministically summarize information, but it will not silently rewrite emergency instructions.

#### The user controls the voice

Different weather content can use different QUILL speech providers, voices, rates, pitches, volumes, pronunciation dictionaries, earcons, and interruption behaviors.

#### Fast does not mean careless

QUILL prioritizes alert speed while using deduplication, update reconciliation, source freshness, delivery logging, and transparent fallback behavior.

---

## 3. Goals

### 3.1 Primary goals

1. Provide fast access to official current conditions, forecasts, and alerts.
2. Keep monitoring selected locations while QUILL Weather Guardian is running.
3. Deliver new, updated, escalated, downgraded, extended, and cancelled alerts without forcing the user to open the main window.
4. Allow unlimited saved locations, subject only to practical local storage and service limits.
5. Support location groups and multi-location weather feeds.
6. Generate highly configurable spoken weather channels from structured data.
7. Provide per-feed, per-content, per-location, and per-alert speech scenarios.
8. Integrate naturally with the existing QUILL speech provider and voice framework.
9. Preserve raw provider data and normalize it into a stable internal weather model.
10. Work without a QUILL account in local mode.
11. Use QuilleSync optionally for encrypted synchronization of saved locations, feed definitions, voice mappings, alert rules, and preferences.
12. Support live NOAA Weather Radio stream catalog entries without making live audio a prerequisite for weather or alert availability.
13. Provide strong diagnostics and a human-readable event history.

### 3.2 Success measures

QUILL Weather will be considered successful when:

- A new user can add a location and hear current conditions within 30 seconds of launching the feature.
- A returning user can hear the primary location’s current conditions within 3 seconds when fresh cached data is available.
- The alert monitor operates while the main window is closed.
- A new alert is announced within one polling cycle in local API mode.
- A relay-delivered alert is normally announced within 15 seconds of relay receipt.
- Alert updates do not produce duplicate announcements unless the user has chosen repeat behavior.
- Every alert action can be completed with a keyboard and screen reader.
- Voice routing works independently for routine weather, watches, warnings, emergency instructions, and system status.
- Source freshness and failure states are always understandable.
- No emergency alert content is replaced by an unmarked generative summary.

---

## 4. Non-Goals

The initial product will not:

1. Claim to be a certified emergency warning receiver.
2. Replace Wireless Emergency Alerts, local emergency management, a physical NOAA Weather Radio, or instructions from public safety officials.
3. Activate the Emergency Alert System.
4. Generate meteorological predictions independent of official providers.
5. Use generative AI to rewrite life-safety instructions as the only presented version.
6. Promise a live NOAA audio stream for every city or transmitter.
7. Require an account, subscription, or cloud relay for basic weather access.
8. Require visual map interaction.
9. Attempt to provide global forecast coverage in the first release.
10. Store continuous precise-location history by default.
11. Treat all provider values as equally current or equally reliable.
12. Infer missing observations or alert instructions and present the inference as source data.

---

## 5. Product Components

### 5.1 QUILL Weather Center

The main accessible weather workspace.

Primary sections:

- Weather Now
- Active Alerts
- Forecast Timeline
- Hourly Conditions
- Weather Details
- Saved Locations
- Location Groups
- Weather Feeds
- NOAA Weather Radio Explorer
- Alert History
- Voice Studio
- Settings
- Source and System Status
- Diagnostics

The Weather Center will use a simple semantic structure with predictable headings, lists, property views, and command menus. Users can choose a compact view or detailed view.

### 5.2 Weather Guardian

A lightweight background process responsible for:

- Alert monitoring
- Forecast refresh scheduling
- Tray presence
- OS notifications
- Speech and earcon delivery
- Feed refreshes
- Relay connectivity
- Network recovery
- Stale-data detection
- Alert lifecycle reconciliation
- Delivery history

Weather Guardian starts with the user only when explicitly enabled. It does not require administrator privileges.

Closing the Weather Center does not close Weather Guardian. Exiting Weather Guardian requires an explicit Exit Monitoring command.

### 5.3 Weather Channels

A Weather Channel is a generated audio feed assembled from selected structured content.

Example channel:

1. Channel identification
2. Active critical alerts
3. Current conditions
4. Next six hours
5. Today and tonight
6. Extended forecast
7. Hazardous weather outlook
8. NOAA Weather Radio transmitter information
9. Last-update status
10. Repeat after a configured interval

Channels can be played on demand or continuously. New alerts can interrupt or queue according to the channel’s alert policy.

### 5.4 Alert Center

A complete, searchable history and current-state view for all monitored locations.

It distinguishes:

- New alert
- Updated alert
- Escalated alert
- Downgraded alert
- Extended alert
- Area changed
- Instructions changed
- Corrected alert
- Cancelled alert
- Expired alert
- Test message
- Unknown lifecycle event

The Alert Center preserves alert revisions and clearly identifies what changed.

### 5.5 Voice Studio

The configuration surface for weather speech scenarios.

Voice Studio allows the user to assign voices and behaviors by:

- Feed
- Location
- Location group
- Content type
- Alert event
- Alert severity
- Alert urgency
- Alert certainty
- Alert lifecycle event
- Language
- Time of day
- Foreground or background state
- Headphones or speakers, where supported
- Routine, important, urgent, or critical priority

### 5.6 NOAA Weather Radio Explorer

A searchable transmitter and stream catalog containing:

- Call sign
- Transmitter city and state
- Frequency
- Counties served
- SAME codes
- Coverage notes
- Operational status
- NWS office
- Community audio stream, when available
- Stream provider
- Stream last verified time
- Stream health
- Official or community provenance
- Receiver-node information, when applicable

QUILL must clearly differentiate:

- Official NWR transmitter metadata
- Official NWS data
- Community-operated audio streams
- QUILL-generated weather audio

---

## 6. Core User Experiences

### 6.1 First launch

On first launch, QUILL Weather asks one accessible question:

> Which location would you like to use first?

Available methods:

- Enter city and state
- Enter ZIP code
- Enter an address
- Use current location
- Enter latitude and longitude
- Search by county
- Search by NOAA Weather Radio call sign
- Skip and explore sample data

The user reviews resolved choices before saving. QUILL announces ambiguities such as multiple cities with the same name.

After selection, QUILL immediately presents:

- Location name
- Current conditions
- Active alert count
- Next forecast period
- Data source
- Last update time

The user is then offered an optional, clearly explained choice to enable Weather Guardian at sign-in.

### 6.2 Quick Weather

A configurable global command speaks:

- Location
- Temperature
- Feels-like temperature, when meaningful
- Current condition
- Wind
- Active alert count
- Next meaningful forecast change
- Data age

Example:

> Phoenix. 108 degrees, feels like 112. Mostly sunny. Southwest wind 8 miles per hour. One Excessive Heat Warning is active. Conditions were updated 6 minutes ago.

The quick response must be deterministic and configurable.

### 6.3 Active alert arrival

When a new alert arrives:

1. Weather Guardian validates and normalizes it.
2. The alert is matched against monitored locations and alert rules.
3. QUILL deduplicates it against existing revisions.
4. QUILL determines its priority scenario.
5. The configured earcon plays.
6. The configured voice announces the headline.
7. An accessible OS notification appears when enabled.
8. The system tray state changes.
9. The Alert Center records receipt and delivery.
10. The user can open details, repeat, acknowledge, snooze allowed repeats, or move directly to instructions.

Example spoken sequence:

> Weather Warning. Tornado Warning for Pima County, including the Tucson area, until 4:45 PM. Take shelter now. Press the configured Alert Details command for the complete official message.

For warnings where the official message contains instructions, the user must be able to hear those instructions immediately without navigating through unrelated details.

### 6.4 Alert update

An update must not be treated as a duplicate merely because the event name is unchanged.

QUILL compares:

- Headline
- Severity
- Urgency
- Certainty
- Effective, onset, expiration, and end times
- Area description
- Geometry and geocodes
- Description
- Instruction
- Response type
- Event codes
- References
- Parameters
- Sender and issuing office

The announcement can say:

> Update to the Tornado Warning for Pima County. The warning now expires at 5:15 PM. The affected area has expanded eastward. Instructions remain unchanged.

A user can choose:

- Headline only
- Changes only
- Changes plus instructions
- Entire updated alert
- Silent log for low-priority updates

### 6.5 All-clear behavior

When an alert is cancelled or expires:

- The Alert Center updates immediately.
- The tray state is recalculated.
- The user’s configured all-clear scenario runs.
- QUILL never says “all clear” unless the source explicitly supports that interpretation.
- Default wording is factual:

> The Severe Thunderstorm Warning for Maricopa County has expired. Two other advisories remain active.

### 6.6 Continuous weather channel

A user starts “Home Weather Radio.”

QUILL generates a continuous audio experience using a selected program clock. Routine content repeats at user-defined intervals, but only changed content needs to be spoken on every cycle.

A new warning can:

- Interrupt immediately
- Finish the current sentence, then interrupt
- Finish the current segment, then interrupt
- Queue behind current content
- Announce headline only and offer details

Critical alerts default to immediate interruption, but the user retains control.

### 6.7 Multi-location monitoring

A user creates a group named “Family” containing:

- Home
- Keri
- David
- Brian

The group can use:

- One shared voice profile
- A unique location-identification voice
- A critical-alert voice
- Different quiet-hour rules
- A combined scan feed

Example:

> Family Weather Scan. Phoenix has one warning. Tucson has no active alerts. Austin has a Heat Advisory.

### 6.8 Travel mode

Travel mode can monitor:

- The current OS-provided location
- A destination
- Saved locations
- A configurable corridor or set of waypoints in a later release

Current location is sampled only with permission. Precise location history is not retained unless the user explicitly enables it.

---

## 7. Location Model

### 7.1 Location types

QUILL supports:

- Fixed point
- Address
- City
- ZIP code
- County
- NWS forecast zone
- Fire weather zone
- Marine zone
- State or territory
- Current location
- Temporary location
- NOAA Weather Radio transmitter
- Custom latitude and longitude
- Location group

### 7.2 Location record

Each saved location includes:

```json
{
  "id": "loc_uuid",
  "display_name": "Home",
  "resolved_name": "Phoenix, Arizona",
  "latitude": 33.4484,
  "longitude": -112.0740,
  "timezone": "America/Phoenix",
  "country": "US",
  "state": "AZ",
  "county_name": "Maricopa",
  "county_zone": "AZC013",
  "forecast_zone": "AZZ543",
  "fire_zone": null,
  "marine_zone": null,
  "nws_office": "PSR",
  "grid_x": 159,
  "grid_y": 57,
  "forecast_url": "...",
  "hourly_forecast_url": "...",
  "grid_data_url": "...",
  "observation_station_ids": [],
  "nwr_transmitters": [],
  "source_resolved_at": "2026-07-19T17:00:00Z",
  "privacy_classification": "precise",
  "sync_enabled": false
}
```

Actual provider URLs are stored as provider-owned metadata and can be refreshed.

### 7.3 Location resolution

The NWS API requires latitude and longitude for point metadata and does not provide general address geocoding. QUILL therefore uses a pluggable Geocoder Provider interface.

Resolution sequence:

1. Use exact coordinates when supplied.
2. Use OS location services when requested.
3. Use the configured geocoder for addresses, cities, and ZIP codes.
4. Present ambiguous results for user selection.
5. Resolve coordinates through the NWS `/points/{lat},{lon}` endpoint.
6. Cache point-to-grid metadata because it changes infrequently.
7. Discover forecast URLs, zones, office, grid, and nearby stations.
8. Resolve NWR transmitter coverage separately.

### 7.4 Location privacy

- No current-location access without explicit permission.
- No continuous location history by default.
- Saved precise coordinates are classified as sensitive application data.
- Local protection uses operating-system secure storage where appropriate.
- QuilleSync synchronization is optional.
- A future encrypted sync design must avoid exposing precise locations to the sync operator.
- Users can sync a coarse county or zone instead of an exact point.
- Removing a location offers to remove its weather history and cached coordinate metadata.

---

## 8. Weather Feed Model

### 8.1 Feed definition

A feed is a named weather experience containing one or more locations and one or more content segments.

Example feed types:

- Quick Weather
- Home Weather Radio
- Morning Briefing
- Evening Outlook
- Family Alert Scan
- Travel Watch
- Severe Weather Only
- Marine Weather
- Fire Weather
- NOAA Radio Stream
- Custom

### 8.2 Feed record

```json
{
  "id": "feed_uuid",
  "name": "Home Weather Radio",
  "locations": ["loc_home"],
  "segments": [
    "identity",
    "critical_alerts",
    "current_conditions",
    "next_six_hours",
    "today_tonight",
    "extended_forecast",
    "hazardous_outlook",
    "source_status"
  ],
  "repeat_interval_minutes": 15,
  "speak_only_changes_after_first_cycle": true,
  "alert_interruption_policy": "critical_immediate",
  "voice_profile_id": "voice_home_radio",
  "output_device_id": "default",
  "live_stream_fallback_policy": "generated_audio",
  "enabled": true
}
```

### 8.3 Content segments

Supported segment types include:

- Feed identification
- Location identification
- Active alert summary
- Critical alert details
- Current conditions
- Observation details
- Feels-like conditions
- Today
- Tonight
- Next period
- Next 3, 6, 12, or 24 hours
- Hourly precipitation timeline
- Temperature trend
- Wind trend
- Visibility
- Humidity and dew point
- Sunrise and sunset, through an appropriate provider
- Extended forecast
- Hazardous weather outlook
- Text products
- Marine forecast
- Fire weather forecast
- Air quality, through an appropriate provider
- NWR transmitter details
- Live stream
- Source and freshness status
- Custom deterministic template

Every segment exposes:

- Source
- Issue/update time
- Valid time range
- Data age
- Missing-field behavior
- Speech template
- Voice scenario
- Repeat policy
- Change detection policy

---

## 9. Voice and Speech Scenario Framework

### 9.1 Design principle

The QUILL speech framework is not merely a text-to-speech output switch. For QUILL Weather it becomes a **scenario router**.

A scenario answers:

- What is being spoken?
- Why is it being spoken?
- For which feed and location?
- How important is it?
- Which provider and voice should speak it?
- At what rate, pitch, volume, and language?
- Which pronunciation rules apply?
- What should it interrupt?
- Should an earcon play?
- Should the full source text or a concise deterministic version be spoken?
- Can it repeat?
- What happens if the selected voice is unavailable?

### 9.2 Speech scopes

Rules can be assigned at these levels, from broadest to most specific:

1. Global QUILL default
2. QUILL Weather default
3. Output device
4. Feed
5. Location group
6. Location
7. Content type
8. Alert priority
9. Alert event type
10. Alert lifecycle event
11. Language
12. Temporary session override

The most specific enabled rule wins. The resolved rule is inspectable.

### 9.3 Voice scenario record

```json
{
  "id": "scenario_uuid",
  "name": "Critical Warning Voice",
  "match": {
    "content_domain": "alert",
    "severity": ["Extreme", "Severe"],
    "urgency": ["Immediate", "Expected"],
    "event_types": ["Tornado Warning", "Flash Flood Warning"],
    "feed_ids": ["*"],
    "location_ids": ["*"]
  },
  "speech": {
    "provider_id": "sapi5",
    "voice_id": "Microsoft David Desktop",
    "rate": -1,
    "pitch": 0,
    "volume": 100,
    "language": "en-US",
    "pronunciation_dictionary_id": "weather_terms",
    "number_style": "natural",
    "time_style": "local_explicit",
    "units_style": "spoken_full"
  },
  "presentation": {
    "earcon_id": "warning_critical",
    "earcon_before": true,
    "earcon_after": false,
    "priority": "critical",
    "interruption": "immediate",
    "duck_other_audio_percent": 80,
    "repeat_policy": "until_acknowledged_or_changed",
    "repeat_interval_minutes": 5,
    "maximum_repeats": 3
  },
  "fallbacks": [
    "weather_default_voice",
    "system_default_voice",
    "screen_reader_announcement"
  ]
}
```

### 9.4 Recommended built-in scenarios

QUILL ships with editable defaults:

- Routine Conditions
- Forecast Narrator
- Watch Announcement
- Warning Announcement
- Immediate Life-Safety Warning
- Alert Update
- Alert Cancellation or Expiration
- Location Identification
- Source and Freshness Status
- System Error
- Live Stream Identification
- Spanish Alert
- Test Alert

### 9.5 Per-feed voices

A user can make each generated feed sound distinct.

Example:

- Home Weather Radio: Piper voice A
- Family Alert Scan: SAPI voice B
- Travel Watch: eSpeak NG voice C
- Tornado and Flash Flood Warnings: high-clarity SAPI voice D
- System and source errors: QUILL system voice
- Spanish CAP content: Spanish-capable provider voice

A feed may also use multiple voices internally:

- Announcer voice for headings
- Forecast voice for routine content
- Warning voice for urgent content
- Location voice for each city
- Status voice for source and freshness messages

### 9.6 Speech rendering rules

The renderer must correctly handle:

- Temperature symbols
- Units
- Decimal values
- Percentages
- Wind directions
- Cardinal and intercardinal abbreviations
- Time zones
- UTC versus local time
- SAME and NWS codes
- Call signs
- County and parish names
- Highway names
- Coordinates
- Acronyms
- Meteorological abbreviations
- VTEC codes in expert mode
- Repeated punctuation
- URLs, which are omitted from routine speech unless requested

Examples:

- `WSW 8 mph` becomes “west southwest wind at 8 miles per hour.”
- `40%` becomes “a 40 percent chance.”
- `AZC013` is normally spoken as “Maricopa County,” with the code available in details.
- `KPHX` can be spoken as “K P H X” or “Phoenix Sky Harbor,” based on context.

### 9.7 Pronunciation dictionaries

Weather Voice Studio supports:

- Global dictionary
- Provider-specific dictionary
- Voice-specific dictionary
- Location dictionary
- Feed dictionary
- Alert dictionary

Users can correct local names without modifying source text.

### 9.8 Voice failure behavior

If a selected voice or engine fails:

1. Try the configured fallback voice.
2. Try the QUILL Weather default voice.
3. Try the system default voice.
4. Send an accessible screen-reader or OS notification.
5. Log the failure.
6. Never silently discard a critical alert.

---

## 10. Alert Architecture

### 10.1 Alert sources

#### Initial source: NWS Alerts API

Default endpoint patterns include:

- Active alerts for a point
- Active alerts for a county or forecast zone
- Active alerts for a state
- Individual alert retrieval
- Alert type metadata

The default local polling interval is 30 seconds, matching NWS guidance not to request alert updates more frequently.

#### Optional fast source: QUILL Alert Relay

The relay can receive NOAA Weather Wire Service products through NWWS-OI, which requires NWS-issued credentials and an XMPP client. The relay:

- Receives pushed products
- Parses CAP and text products
- Normalizes alert messages
- Matches zone subscriptions
- Pushes updates to clients
- Reconciles against the NWS API
- Falls back to public API polling
- Reports relay status and latency

#### Future source: FEMA IPAWS

A future provider may add FEMA IPAWS for non-weather and broader all-hazards alerts, subject to access requirements, agreements, testing, and explicit provenance.

### 10.2 Local-first and relay modes

#### Local mode

- No account required
- Client communicates directly with official NWS endpoints
- Alert polling no more frequent than every 30 seconds
- Uses conditional requests and provider caching guidance
- Best privacy
- Slight polling delay

#### Relay-assisted mode

- Optional
- Uses coarse zones or opaque subscriptions where possible
- Receives server-pushed alert changes
- Falls back locally if relay is unavailable
- Does not require the relay to store exact addresses
- Shows connection and last-message status

#### Hybrid mode

Recommended default after the relay is production ready:

- Relay for speed
- NWS API for verification and reconciliation
- Local cache for continuity
- Independent periodic checks to detect missed messages

### 10.3 Alert normalization

The normalized alert model must preserve at least:

```json
{
  "provider": "nws",
  "source_id": "official-alert-id",
  "status": "Actual",
  "message_type": "Alert",
  "scope": "Public",
  "sent": "...",
  "effective": "...",
  "onset": "...",
  "expires": "...",
  "ends": "...",
  "event": "Flash Flood Warning",
  "sender": "...",
  "sender_name": "...",
  "headline": "...",
  "description": "...",
  "instruction": "...",
  "response": "Shelter",
  "urgency": "Immediate",
  "severity": "Severe",
  "certainty": "Observed",
  "area_description": "...",
  "geometry": {},
  "geocodes": {},
  "affected_zones": [],
  "references": [],
  "parameters": {},
  "language": "en-US",
  "raw_payload_hash": "...",
  "received_at": "...",
  "normalized_at": "..."
}
```

Raw payloads are retained according to the user’s history setting so developers and users can verify interpretation.

### 10.4 Alert matching

An alert can match a location through:

- Direct point query result
- Point-in-polygon calculation
- County or zone code
- Forecast zone
- Fire zone
- Marine zone
- State or territory
- NWR SAME code
- Explicit user rule

Where geometry and zone matching disagree, QUILL records the discrepancy and follows a configurable conservative policy. Default behavior favors notifying the user rather than suppressing a potentially relevant warning.

### 10.5 Alert lifecycle and deduplication

QUILL uses:

- Official alert ID
- Message type
- References
- Event code
- Sender
- Sent time
- Payload hash
- Geometry/geocode changes
- Expiration changes

A revision graph links all related alert versions.

A repeated provider response with no meaningful change is not reannounced unless the user selected periodic reminders.

### 10.6 Alert priority model

QUILL does not reduce urgency, severity, and certainty to a single hidden number. It preserves all three.

For delivery, QUILL computes a transparent priority tier:

- Critical
- Urgent
- Important
- Advisory
- Informational
- Test

Users can inspect why a tier was selected.

The default mapping considers:

- Event type
- Severity
- Urgency
- Certainty
- Response type
- Observed versus forecast condition
- User rules
- Location role
- Time of day
- Lifecycle event

### 10.7 Notification actions

An accessible notification can offer:

- Hear headline
- Hear official instructions
- Hear full alert
- Open Alert Center
- Acknowledge
- Repeat
- Snooze reminders
- Copy official text
- View source details
- Switch to affected location
- Start the related weather feed

### 10.8 Quiet hours and interruption safety

Users can configure:

- Routine quiet hours
- Advisory quiet hours
- Watch quiet hours
- Warning behavior
- Critical override
- Headphone-only behavior
- Earcon-only behavior
- Notification-only behavior
- Repeat limits

Default behavior:

- Routine weather respects quiet hours.
- Advisories are logged and optionally notified.
- Watches use the configured important-alert policy.
- Severe and extreme immediate alerts are allowed to interrupt.
- The user can change every default.

A “Silence all critical alerts” action requires explicit confirmation, states the consequence, and can be time-limited.

### 10.9 Authoritative text and summaries

For life-safety alerts:

1. The official headline and instructions are always available.
2. QUILL can create a deterministic “changes only” summary.
3. Optional plain-language assistance must be labeled as a QUILL interpretation.
4. Generative AI may not replace, suppress, or alter official instructions.
5. The user can always access the raw source message.

---

## 11. Weather Data Architecture

### 11.1 Primary NWS data flow

For each point location:

1. Resolve latitude and longitude.
2. Request NWS point metadata.
3. Cache office, grid, zones, and provider URLs.
4. Retrieve forecast periods.
5. Retrieve hourly forecast periods.
6. Retrieve gridpoint data for detailed time-series values.
7. Retrieve nearby stations.
8. Select observations using freshness and availability rules.
9. Retrieve active alerts.
10. Retrieve optional text products.
11. Normalize all values.
12. store source time, receipt time, and freshness.
13. Render views and speech.

### 11.2 Provider interfaces

```text
WeatherProvider
  get_capabilities()
  resolve_point_metadata()
  get_forecast()
  get_hourly_forecast()
  get_grid_data()
  get_observation_stations()
  get_latest_observations()
  get_alerts()
  get_alert()
  get_zones()
  get_text_products()
  get_source_status()

GeocoderProvider
  search()
  reverse_geocode()
  normalize_result()

AlertPushProvider
  connect()
  subscribe()
  unsubscribe()
  receive()
  acknowledge_cursor()
  get_status()

NwrMetadataProvider
  search_transmitters()
  get_county_coverage()
  get_transmitter_status()
  get_same_codes()

WeatherAudioStreamProvider
  search_streams()
  resolve_stream()
  verify_health()
  get_provenance()
```

Providers register capabilities through stable contribution points. Provider provenance is available in text and speech.

### 11.3 Normalized weather model

QUILL stores:

- Raw source value
- Source unit
- Normalized SI value
- Display value
- Display unit
- Valid time interval
- Source update time
- QUILL receipt time
- Quality or status metadata
- Provider identity
- Missing or null reason, when known

### 11.4 Time-series understanding

NWS gridpoint data may represent values across ISO 8601 time intervals rather than one record per hour. QUILL’s interval engine must:

- Expand intervals only when needed
- Preserve original valid intervals
- Avoid creating false precision
- Merge identical adjacent values for speech
- Select the value valid at a requested time
- Handle gaps explicitly
- Convert to the location’s time zone
- handle daylight-saving transitions
- distinguish issue time from valid time

### 11.5 Units

QUILL supports:

- Fahrenheit and Celsius
- Miles per hour, kilometers per hour, knots, and meters per second
- Inches, millimeters, and centimeters
- Miles, kilometers, feet, and meters
- Inches of mercury, millibars/hectopascals, and pascals

The user can set units globally, by feed, or by content type.

The source value is never destroyed when converted.

### 11.6 Observations

Observation station selection considers:

- Distance
- Data freshness
- Missing values
- Station availability
- Quality-control status when exposed
- User preference
- Airport or station identity

QUILL states the observation source and age.

It must distinguish:

- Reported observation
- Forecast value
- Derived display value
- Missing value

### 11.7 Freshness and staleness

Every view and speech response can expose:

- Issued time
- Updated time
- Valid time
- Retrieved time
- Age
- Next refresh
- Source status

Default stale thresholds are content-specific.

Example:

> Current conditions were last observed 47 minutes ago and may be stale. The forecast was updated 18 minutes ago.

QUILL must not hide stale data behind a generic “updated” label.

### 11.8 Caching

QUILL honors:

- Cache-Control
- Last-Modified
- ETag, when available
- If-Modified-Since
- If-None-Match
- Retry-After

The client avoids cache-busting query parameters.

Point-to-grid mapping is cached long-term and refreshed on provider errors, source changes, or a scheduled maintenance interval.

### 11.9 Failure and fallback

When a request fails:

1. Keep the last successful data.
2. Mark it stale.
3. Attempt a bounded retry with exponential backoff and jitter.
4. Use a secondary provider only when configured.
5. Announce source changes when they affect meaning.
6. Never merge conflicting provider values without attribution.
7. Keep alert monitoring prioritized over routine refreshes.
8. Record errors in diagnostics.

---

## 12. System Tray and Background Experience

### 12.1 Tray states

The tray item has an accessible name reflecting state:

- QUILL Weather: no active alerts
- QUILL Weather: 2 active alerts, highest priority warning
- QUILL Weather: critical alert
- QUILL Weather: data stale
- QUILL Weather: offline
- QUILL Weather: monitoring paused
- QUILL Weather: relay disconnected, local monitoring active

Visual icons may differ, but text state is authoritative.

### 12.2 Tray menu

Keyboard-accessible commands:

- Speak Quick Weather
- Active Alerts
- Repeat Last Alert
- Open Official Instructions
- Open Weather Center
- Start or Stop Current Weather Feed
- Choose Location
- Choose Location Group
- Mute Routine Speech
- Snooze Non-Critical Notifications
- Pause Monitoring
- Source Status
- Last Successful Update
- Settings
- Exit Monitoring

Destructive or safety-relevant commands include confirmation and a clear status announcement.

### 12.3 Accessible notifications

Notifications must:

- Use plain, concise titles
- Identify location
- Identify alert type
- State expiration when relevant
- Expose useful actions
- Avoid icon-only meaning
- Avoid rapidly replacing an unread notification
- Link to the exact alert revision
- remain represented in Alert History

### 12.4 Global commands

Global commands are opt-in and configurable.

Suggested defaults:

- Speak Quick Weather
- Open Active Alerts
- Repeat Last Weather Message
- Silence Current Speech
- Open Weather Center

QUILL checks for conflicts and allows reassignment.

### 12.5 Startup and shutdown

Settings include:

- Start Weather Guardian at sign-in
- Start minimized to tray
- Restore last feed
- Speak startup status
- Check alerts immediately
- Continue monitoring after Weather Center closes
- Confirm before exiting monitoring
- Resume pending alert speech after restart

---

## 13. Settings

### 13.1 General

- Primary location
- Default location group
- Start at sign-in
- Start minimized
- Default Weather Center section
- Compact or detailed mode
- Time format
- Unit system
- Language
- Data retention
- History retention
- Offline cache size
- Diagnostic logging level

### 13.2 Location

Per location:

- Friendly name
- Location role
- Monitoring enabled
- Forecast enabled
- Alerts enabled
- Alert radius or zone policy
- Time zone override
- Observation station preference
- NWR transmitter preference
- Sync behavior
- Privacy precision
- Quiet hours
- Voice profile
- Alert profile

### 13.3 Alerts

- Polling interval, constrained by provider rules
- Relay enabled
- Local fallback enabled
- Event filters
- Severity filters
- Urgency filters
- Certainty filters
- Test alert behavior
- Update announcement style
- Repeat intervals
- Acknowledgment behavior
- Expiration behavior
- Quiet hours
- Critical override
- OS notifications
- Speech
- Earcons
- Tray flashing or animation, when accessible
- Alert history retention

### 13.4 Speech

- Default provider
- Default voice
- Per-feed voices
- Per-location voices
- Per-alert voices
- Rate
- Pitch
- Volume
- Units speaking style
- Time speaking style
- Wind speaking style
- Alert verbosity
- Routine verbosity
- Heading announcements
- Earcons
- Audio ducking
- Interruption policy
- Pronunciation dictionaries
- Fallback chain
- Output device
- Screen-reader-only mode
- Self-voicing mode
- Combined mode

### 13.5 Feeds

- Segment selection
- Segment order
- Repeat interval
- Changes-only mode
- Alert interruption
- Voice profile
- Location sequence
- Silence between segments
- Intro and closing
- Source identification
- Freshness announcement
- Live stream preference
- Generated fallback
- Playback speed
- Output device
- Resume behavior

### 13.6 Privacy and sync

- Local-only mode
- QuilleSync enabled
- Items to sync
- Exact versus coarse location sync
- Current-location use
- Location history
- Clear history
- Export settings
- Delete cloud copy
- Relay subscription privacy

### 13.7 Advanced

- Provider selection
- Provider priority
- Raw data inspector
- Request diagnostics
- Cache controls
- NWWS relay status
- Alert matching strategy
- Conservative matching
- Station selection
- Geocoder provider
- Developer mode
- Simulated alert testing
- Import/export

---

## 14. Accessibility Requirements

### 14.1 Foundational requirements

- Full keyboard operation
- Predictable tab order
- Native controls whenever practical
- Correct accessible names, roles, states, values, and descriptions
- No unlabeled controls
- No custom-drawn control without a complete accessibility implementation
- No color-only, icon-only, position-only, or sound-only meaning
- Screen-reader browse and focus behavior tested
- High contrast support
- Text scaling
- Reduced motion
- Accessible error recovery
- Logical headings and landmarks
- Reviewable, selectable alert and forecast text

### 14.2 Screen-reader behavior

- Routine background refreshes do not constantly interrupt the user.
- New alert announcements use an explicit priority model.
- Changes in alert count are announced only when meaningful.
- Focus is never stolen merely because data refreshed.
- Opening a notification places focus on the alert heading.
- Alert instructions have a direct command and heading.
- Tables provide useful row and column context.
- Charts always have equivalent lists, summaries, and data tables.
- Maps are optional visual enhancements, not required navigation surfaces.

### 14.3 Keyboard behavior

Every context menu is reachable through keyboard commands and Shift+F10 where applicable.

List items support:

- Arrow navigation
- First-letter navigation
- Search
- Sort
- Filter
- Details
- Context menu
- Multi-select where meaningful

### 14.4 Audio accessibility

- Earcons are optional and never the sole signal.
- Speech can be repeated.
- Speech can be paused or stopped without dismissing the alert.
- Critical alert text remains available if audio fails.
- Volume can be configured separately from routine QUILL speech where the platform allows.
- Headphone removal does not silently lose alerts; a fallback rule applies.
- Audio ducking is configurable.
- Every continuous feed has a Stop command that is always available.

### 14.5 Cognitive accessibility

- Compact summaries
- Plain labels
- Consistent alert structure
- Changes-only views
- Optional definitions
- No unnecessary meteorological codes in default mode
- One-action access to official instructions
- Time expressed with context, such as “until 4:45 PM today”
- Clear distinction between current, forecast, and historical information

---

## 15. Safety, Trust, and Integrity

### 15.1 Safety notice

QUILL Weather displays a concise notice during onboarding and in About:

> QUILL Weather is an additional accessible weather information tool. Delivery can be delayed or interrupted by network, device, provider, or software failures. Do not rely on QUILL Weather as your only source of emergency information.

### 15.2 Source attribution

Every weather object has:

- Provider
- Issuing organization
- Source identifier
- Issue/update time
- Retrieval time
- Validity
- Original text or raw data access

Generated audio identifies itself as QUILL-generated weather using official data.

### 15.3 No silent transformation

QUILL does not silently:

- Shorten official instructions
- Change an alert’s severity
- Replace source wording with AI wording
- Merge two conflicting alerts
- Convert an expiration into an all-clear
- Hide a stale source
- suppress a warning because a visual geometry calculation failed

### 15.4 Test and exercise alerts

Test alerts are clearly identified through:

- Spoken prefix
- Text prefix
- Unique earcon
- Notification title
- History classification

Users can choose to announce, log, or ignore provider-designated tests, but development simulation mode cannot impersonate an actual alert without a persistent simulation label.

---

## 16. Data Storage

### 16.1 Local database

SQLite is recommended for:

- Locations
- Location groups
- Feeds
- Feed segments
- Voice scenarios
- Alert rules
- Alert revisions
- Delivery history
- Acknowledgments
- Provider metadata
- Observation and forecast cache
- NWR metadata
- Stream health
- Diagnostic events

### 16.2 Suggested entities

- `locations`
- `location_groups`
- `location_group_members`
- `provider_point_metadata`
- `weather_snapshots`
- `forecast_periods`
- `time_series_values`
- `observation_stations`
- `observations`
- `alerts`
- `alert_revisions`
- `alert_location_matches`
- `alert_deliveries`
- `alert_acknowledgments`
- `feeds`
- `feed_segments`
- `voice_profiles`
- `voice_scenarios`
- `pronunciation_entries`
- `nwr_transmitters`
- `nwr_coverage`
- `weather_streams`
- `stream_health_checks`
- `source_status_events`
- `settings`

### 16.3 Retention

Defaults:

- Active alert revisions: retained while active
- Expired alert history: 30 days
- Delivery logs: 30 days
- Forecast cache: provider-driven plus bounded history
- Observations: 7 days
- Raw payloads: 7 days or user-selected
- Location history: off
- Diagnostics: 14 days

All are configurable within safe storage limits.

---

## 17. QUILL Alert Relay

### 17.1 Purpose

The relay exists to improve speed, scalability, and resilience—not to make local weather dependent on the cloud.

### 17.2 Responsibilities

- Maintain NWWS-OI connection
- Receive CAP and related NWS products
- Parse and validate
- Deduplicate
- Normalize
- Maintain revision graph
- Index by zones, states, offices, and event types
- Push to subscribed clients
- Reconcile with NWS API
- Expose relay health
- Record end-to-end latency
- Avoid retaining precise client coordinates
- Apply backpressure and retry
- Support multiple relay regions later

### 17.3 Subscription privacy

Clients preferably subscribe using:

- County zone IDs
- Forecast zone IDs
- Fire zones
- Marine zones
- State codes
- Opaque server-derived subscription sets

Exact addresses are not sent.

For point-specific polygon matching, options are:

1. Match locally after receiving relevant coarse-zone alerts.
2. Send a short-lived encrypted or coarse point token.
3. Use privacy-preserving regional subscriptions.

The first option is the preferred initial design.

### 17.4 Client connection

Recommended protocol:

- Secure WebSocket for live updates
- HTTPS reconciliation endpoint
- Monotonic event cursor
- Resume after disconnect
- Heartbeats
- Signed message envelope
- Schema version
- Compression
- Rate limiting
- Anonymous client mode
- Optional authenticated QuilleSync mode

### 17.5 Reliability

The client continuously knows:

- Relay connected or disconnected
- Last heartbeat
- Last alert received
- Local fallback status
- Last successful official API check
- Current subscription set

A relay failure automatically activates local polling if enabled.

---

## 18. NOAA Weather Radio and Community Audio

### 18.1 Metadata

QUILL imports and normalizes official transmitter information:

- Station call sign
- Transmitter location
- Frequency
- State
- NWS office
- County coverage
- SAME code
- Partial-county information
- Power, when available
- Status: normal, degraded, or out of service
- Last metadata refresh

### 18.2 Stream catalog

A stream record includes:

```json
{
  "id": "stream_uuid",
  "call_sign": "WXL30",
  "transmitter_name": "Phoenix",
  "stream_url": "...",
  "provider_name": "Community Receiver Operator",
  "provider_type": "community",
  "official_noaa_stream": false,
  "codec": "MP3",
  "bitrate": 32,
  "last_verified": "...",
  "health": "online",
  "terms": "...",
  "redistribution_allowed": true
}
```

### 18.3 Stream rules

- Do not scrape or redistribute streams contrary to provider terms.
- Verify stream health.
- Clearly identify community sources.
- Never use stream silence as the only alert detector.
- The structured alert engine remains independent.
- Allow a warning to interrupt the live stream.
- Offer generated weather audio when the live stream is unavailable.

### 18.4 Receiver network

A later QUILL Community Receiver program may provide:

- Documented receiver hardware
- RTL-SDR or radio line-in support
- Secure stream publishing
- Receiver status
- Silence detection
- Audio-quality checks
- Volunteer attribution
- Geographic gap analysis
- Automated failover among receivers

### 18.5 Delivered implementation: WeatherIndex integration (Quill Radio 2.1.1)

The NWR directory-and-streams portion of this section shipped in Quill Radio
2.1.1, powered by the **WeatherIndex API** (`https://api.wxindex.org`) -- a
curated, no-auth JSON directory of NWR transmitters plus internet re-stream
URLs, organized by state, county/SAME, and NWS Weather Forecast Office.

- **Data layer** (`quill/core/radio/wxindex.py`, wx-free): `list_states`,
  `stations_for_state`, `search_stations(county/state/same/callsign)`,
  `station_detail`, `local_stations(lat, lon, county)`, and
  `to_radio_station` adapting each transmitter to the existing playable model,
  so Favorites, recording, and scheduling required no new code. `WxStation`
  carries call sign, frequency, state, county/SAME coverage, WFO, coordinates,
  and the ordered re-stream feed URLs (best first) -- the metadata set of §18.1
  as far as the upstream directory provides it.
- **Resilience**: a three-tier resolver -- live API (short timeout, HTTPS-only,
  Safe-Mode-blocked, registered in the network-egress audit), app-data cache of
  the last successful pull, bundled snapshot
  (`quill/data/noaa_directory.json`, 1,035 transmitters, regenerated by
  `scripts/snapshot_wxindex.py`) -- so browse, search, and local-station
  resolution work fully offline and survive the API disappearing. A corrupt or
  missing snapshot logs and yields an empty directory rather than raising.
- **Surfaces**: Browse's Weather / NOAA branch is a lazy State -> Station tree;
  unified search routes SAME codes (6 digits), call signs, and "County, ST" /
  state names to the directory; Weather menu > Listen to your Local NOAA
  Weather Radio resolves the saved Weather location (county/SAME match first,
  nearest covering transmitter by coordinates as fallback); Weather menu >
  Update NOAA Weather Radio Directory refreshes the cache tier on demand,
  never overwriting the bundled floor.
- **Still future** (per §18.3-18.4 and §26 phases): alert interruption of the
  live stream, generated weather audio as a stream fallback, stream-health
  verification, and the community receiver network.

### 18.6 Radio Reading Services (delivered in Quill Radio 2.1.1)

Radio reading services -- the audio information services affiliated with IAAIS
(the International Association of Audio Information Services) that read
newspapers, magazines, and local print aloud for people who are blind or
print-disabled -- are a natural companion to community NWR audio and shipped
alongside it:

- A **Radio Reading Services** Browse category and a unified-search blend
  (name, tag, or state match), implemented in
  `quill/core/radio/reading_services.py` and `directory_search.py`.
- **20 vetted services bundled** in `quill/data/reading_services.json` (WRBH
  88.3 Reading Radio, Sun Sounds of Arizona, CRIS Radio / The Chicago
  Lighthouse, Connecticut Radio Information System, KPBS and WKAR reading
  services, WUFT RRS, Down East RRS, Recording Library of West Texas, Audible
  Local Ledger, Owl Radio, Voice Corps, 95alive, ACB Media 1-5, NFB Radio
  Network, and the American Council of the Blind stream), so the category
  works offline.
- **Refresh**: Station > Update Radio Reading Services pulls live from the
  community Radio Browser directory through a cache -> live -> snapshot
  resolver that mirrors the wxindex one; reading-service keyword queries
  ("radio reading", "reading service", "audio information", ...) are filtered
  to stations whose name or tags match a reading-service term and that carry a
  playable stream URL, de-duplicated by stream. Safe Mode refuses the live
  pull and falls back to cache or snapshot.

### 18.7 Reading-service discovery methodology and rights review

The bundled list was built with a discovery pass, kept here as the method for
future refreshes of the curated set:

- **Sources.** The IAAIS national service locator (iaais.org/find-a-service)
  enumerates United States state pages and candidate services but exposes no
  public JSON API; the **Radio Browser API** (docs.radio-browser.info)
  supplies station UUIDs, resolved stream URLs, homepage, state, codec,
  bitrate, health status, tags, language, and popularity, and asks clients to
  use a descriptive User-Agent and discover/fail over among API mirrors
  (which the in-app client honors).
- **Matching.** Each IAAIS-derived service was queried against Radio Browser
  by full name, normalized name, a generic-terms-stripped name, and broader
  reading-service keyword searches. Candidates were scored on station-name
  similarity, distinctive-word overlap, website-domain and stream-domain
  agreement, state agreement, reading-service keywords, and Radio Browser
  health, then tiered: high confidence (82-100), medium (65-81.99), low
  (48-64.99), unlikely (below 48). Every tier -- including high confidence --
  went through human review before a service entered the bundled list.
- **Rights.** A Radio Browser match only establishes that a public directory
  knows the stream. It does not by itself prove the service permits
  redistribution, proxying, recording, revealing a restricted URL, or
  bypassing listener qualification (some reading services restrict listening
  to qualified print-disabled users). The curated set therefore carries only
  publicly listed streams, and per-service review covers redistribution
  permission, official-player-only status, and authentication requirements
  before inclusion. The stream rules of §18.3 apply to reading-service
  streams exactly as to NWR streams.

---

## 19. User Interface Information Architecture

### 19.1 Weather Now

Recommended reading order:

1. Location
2. Active alert summary
3. Temperature and condition
4. Feels-like condition
5. Wind
6. Observation age and station
7. Next meaningful forecast
8. Quick actions

### 19.2 Active Alerts list

Default sort:

1. Critical priority
2. Urgency
3. Severity
4. Most recently updated
5. Location

Each item speaks:

> Tornado Warning. Pima County. Immediate, extreme, observed. Updated 2 minutes ago. Expires at 4:45 PM.

### 19.3 Alert details

Headings:

- Alert headline
- What changed
- Official instructions
- Description
- Affected areas
- Timing
- Severity, urgency, and certainty
- Locations you monitor
- Source
- Revision history
- Delivery history
- Raw message

### 19.4 Forecast timeline

Accessible list alternatives:

- Period-by-period
- Hour-by-hour
- Meaningful changes
- Temperature trend
- Precipitation windows
- Wind windows
- Hazard windows

A visual chart may be included but never replaces the list.

### 19.5 Settings search

All settings are searchable by plain language.

Example search terms:

- tornado voice
- quiet hours
- home location
- alert repeat
- system tray
- Celsius
- NOAA radio
- current location privacy
- provider status

Search results explain the setting path and current value.

---

## 20. Commands and Extensibility

Suggested command IDs:

```text
weather.openCenter
weather.speakQuick
weather.openAlerts
weather.repeatLastMessage
weather.stopSpeech
weather.startFeed
weather.stopFeed
weather.switchLocation
weather.addLocation
weather.openAlertInstructions
weather.acknowledgeAlert
weather.openVoiceStudio
weather.openSourceStatus
weather.refresh
weather.pauseMonitoring
weather.resumeMonitoring
```

Extension-contributed commands use the QUILL extension naming convention, such as:

```text
ext.vendor.weatherCommand
```

Extensions may contribute:

- Weather providers
- Geocoders
- Air-quality providers
- Audio stream catalogs
- Feed segments
- Speech templates
- Pronunciation packs
- Alert classification rules
- Exporters

An extension cannot silently suppress critical alerts. Any suppression capability requires explicit user authorization and is visible in diagnostics.

---

## 21. Diagnostics and Supportability

### 21.1 User-facing status

Source Status answers:

- Is Weather Guardian running?
- Is the network available?
- Is the NWS API responding?
- Is the Alert Relay connected?
- When was each location last checked?
- When was the last alert received?
- Is any data stale?
- Is the selected voice available?
- Is a feed playing?
- Are notifications permitted by the OS?

### 21.2 Diagnostic package

The user can create a privacy-reviewed support bundle containing:

- App version
- Platform version
- Provider versions
- Redacted request timeline
- HTTP status codes
- Cache behavior
- Alert lifecycle events
- Voice resolution results
- Relay state
- Stream health
- Accessibility settings relevant to reproduction

Precise coordinates, addresses, alert text, and account identifiers are excluded by default and require explicit inclusion.

### 21.3 Raw data inspector

Expert users and developers can inspect:

- Raw JSON or CAP
- Normalized object
- Provider headers
- Cache metadata
- Rule match trace
- Voice scenario resolution
- Delivery decision
- Location-match explanation

The inspector is fully accessible and supports copying selected sections.

---

## 22. Performance Requirements

- Fresh cached Quick Weather response: target under 3 seconds.
- Initial uncached location resolution and weather: target under 10 seconds under normal network conditions, excluding geocoder delays.
- Main Weather Center initial usable state: target under 2 seconds with cached content.
- Alert processing after receipt: target under 1 second.
- Speech start for critical alert after processing: target under 2 seconds.
- Tray command response: target under 500 milliseconds.
- Background idle CPU: negligible under normal conditions.
- Memory use: bounded and documented.
- Local database operations must not block the UI thread.
- Provider requests, parsing, audio generation, and stream health checks run asynchronously.
- Alert processing has priority over routine forecast work.

---

## 23. Security Requirements

- HTTPS for all remote providers.
- Validate TLS certificates.
- Validate and bound all remote payloads.
- Treat provider text as untrusted content for rendering.
- No HTML execution from alert content.
- No arbitrary command execution from feed templates.
- Protect local secrets with OS secure storage.
- Relay messages are authenticated and schema validated.
- Stream URLs are validated before use.
- Redirects are bounded.
- Diagnostic exports are redacted.
- Dependencies are pinned and monitored.
- No API credentials embedded in the open-source client.
- NWWS credentials remain on the relay, never in distributed clients.
- QuilleSync encryption keys are not stored in plaintext.

---

## 24. Testing Strategy

### 24.1 Unit tests

- Unit conversion
- Time-zone conversion
- DST transitions
- Interval expansion
- Alert deduplication
- Revision linking
- Geometry matching
- Zone matching
- Priority classification
- Voice-rule resolution
- Speech rendering
- Pronunciation
- Cache behavior
- Retry behavior
- Stale thresholds

### 24.2 Contract tests

Saved fixtures for:

- Point metadata
- Forecast
- Hourly forecast
- Grid data
- Stations
- Observations
- CAP alerts
- Alert updates
- Cancellations
- Missing fields
- Null values
- Malformed payloads
- Provider errors

### 24.3 Alert simulation laboratory

A built-in developer and QA laboratory can simulate:

- Tornado Warning
- Flash Flood Warning
- Severe Thunderstorm Watch
- Heat Advisory
- Red Flag Warning
- Marine Warning
- Alert update
- Area expansion
- Expiration extension
- Cancellation
- Test message
- Duplicate delivery
- Relay disconnect
- API outage
- Voice failure
- Audio device change

Every simulation is unmistakably marked as a simulation.

### 24.4 Accessibility tests

Test with:

- JAWS
- NVDA
- Narrator
- VoiceOver on macOS
- Keyboard only
- High contrast
- 200% and greater text scaling
- Reduced motion
- Multiple speech providers
- Screen-reader-only mode
- Self-voicing mode

### 24.5 Real-world tests

- Multiple locations in one county
- Locations near county borders
- Partial-county alerting
- Locations covered by out-of-state NWR transmitters
- Mountain and rural areas
- Marine zones
- Network interruption
- Sleep and resume
- Clock and time-zone change
- Long-running tray session
- System restart with active alerts
- Multiple simultaneous alerts
- Alert flood during a major event

---

## 25. Acceptance Criteria

### 25.1 Location and forecast

- User can add a location entirely by keyboard.
- Ambiguous search results are understandable.
- NWS point metadata is cached.
- Current, hourly, and period forecasts are available.
- Data source and freshness are exposed.
- Missing data is identified rather than invented.

### 25.2 Background monitoring

- Weather Guardian can run without the Weather Center open.
- User can enable startup without administrator access.
- Tray state has an accurate accessible name.
- Monitoring failure is announced and logged.
- Local API fallback works when relay mode fails.

### 25.3 Alerts

- Active alerts can be queried for every monitored location.
- Default API polling does not exceed NWS guidance.
- New and updated alerts are distinguished.
- Alert revisions are linked.
- Instructions are available in one action.
- Critical alert speech has a fallback.
- Expiration does not produce a false “all clear.”
- Acknowledgment does not delete the alert.
- Test alerts are unmistakable.

### 25.4 Speech

- User can assign a voice per feed.
- User can assign a voice per alert priority.
- User can assign location identification voices.
- Missing voice falls back safely.
- Speech can be repeated and stopped.
- Stopping speech does not dismiss the alert.
- Official text remains accessible.
- Units and abbreviations are spoken naturally.

### 25.5 Accessibility

- No critical function requires a mouse.
- No alert meaning depends only on color, icon, or sound.
- Data refresh does not steal focus.
- Every chart has a text equivalent.
- Alert history is searchable and filterable.
- Settings are searchable.
- Accessible names and states pass automated and manual inspection.

---

## 26. Delivery Phases

### Phase 0: Architecture and prototypes

- Normalized weather schema
- NWS provider prototype
- Location resolution prototype
- Alert lifecycle prototype
- QUILL speech scenario prototype
- Accessible tray prototype
- Alert simulation laboratory
- Threat and privacy review

### Phase 1: Windows minimum lovable product

- Weather Center
- Saved locations
- Current conditions
- Forecast and hourly forecast
- Direct NWS alert polling
- Weather Guardian
- System tray
- Accessible notifications
- Quick Weather command
- Active Alert Center
- Basic per-content voices
- Data freshness and diagnostics
- Local-only operation

### Phase 2: Weather Channels and Voice Studio

- Feed builder
- Continuous generated audio
- Per-feed and per-location voices
- Earcons
- Pronunciation dictionaries
- Advanced interruption rules
- Location groups
- Morning/evening briefings
- Changes-only announcements
- Import/export

### Phase 3: QUILL Alert Relay

- NWWS-OI integration
- Secure push
- Zone subscriptions
- Local reconciliation
- Relay status
- Latency metrics
- Failover
- Privacy validation
- Production monitoring

### Phase 4: NWR Explorer and community audio

- Official transmitter metadata
- County and SAME mapping
- Transmitter status
- Curated stream catalog
- Stream verification
- Generated fallback
- Alert interruption over live audio
- Community receiver toolkit design

### Phase 5: QuilleSync and macOS

- Encrypted settings sync
- Saved location and feed sync
- Voice mapping portability
- macOS Weather Guardian
- macOS status menu
- VoiceOver testing
- Cross-device acknowledgment policy

### Phase 6: Expanded services

Potential future additions:

- Air quality
- Sunrise and sunset
- Lightning
- Radar data and accessible radar interpretation
- River gauges
- Tropical products
- Space weather
- Earthquake and tsunami providers
- FEMA IPAWS
- iOS companion
- Route and corridor monitoring
- Community receiver network

Each addition must preserve provider provenance and accessibility.

---

## 27. Product Risks and Mitigations

### Risk: Users assume QUILL is guaranteed life-safety delivery

**Mitigation:** Clear safety notice, source-status visibility, failure announcements, no claims of certification, and encouragement to use multiple official channels.

### Risk: Duplicate or noisy alerts

**Mitigation:** Revision graph, deterministic change comparison, acknowledgment, changes-only announcements, and configurable repeat rules.

### Risk: Over-customization suppresses important warnings

**Mitigation:** Transparent rule trace, critical-silence confirmation, safety review, reset-to-safe-defaults command, and diagnostics showing suppressed events.

### Risk: NWS API outage or rate limiting

**Mitigation:** Conditional requests, centralized relay for scale, backoff, cache, local fallback, stale-state communication, and provider abstraction.

### Risk: Voice provider failure

**Mitigation:** Multi-step fallback chain, screen-reader/OS notification fallback, and delivery logging.

### Risk: Incorrect location matching

**Mitigation:** Combine point, geometry, and zone methods; conservative default; match explanation; testing near boundaries; user-selected county/zone override.

### Risk: Community stream disappears

**Mitigation:** Health checks, multiple streams, generated audio fallback, and independent structured alert monitoring.

### Risk: Generative summaries change meaning

**Mitigation:** No generative rewrite as the authoritative alert; official text always primary; deterministic summaries; explicit labels.

### Risk: Precise location privacy

**Mitigation:** local-first storage, no default history, optional coarse subscriptions, encrypted sync, redacted diagnostics, and explicit permissions.

---

## 28. Recommended Technical Shape

### 28.1 Client modules

```text
quill_weather/
  providers/
    nws/
    geocoding/
    nwr/
    streams/
  domain/
    locations/
    forecasts/
    observations/
    alerts/
    feeds/
    speech/
  services/
    weather_guardian/
    alert_monitor/
    feed_engine/
    cache/
    sync/
    notifications/
  ui/
    weather_center/
    alert_center/
    location_manager/
    feed_builder/
    voice_studio/
    settings/
    diagnostics/
  platform/
    windows/
    macos/
  storage/
  tests/
```

### 28.2 Threading and process model

- UI process remains responsive.
- Weather Guardian can run as a separate user process.
- Database writes are serialized safely.
- Provider calls use asynchronous workers.
- Alert intake has a high-priority queue.
- Speech uses a serialized, priority-aware dispatcher.
- Critical speech can preempt routine feed speech.
- Crashes do not corrupt alert state or settings.
- Restart recovery checks active alerts immediately.

### 28.3 Speech dispatcher priorities

1. Emergency stop and user control
2. Critical alert
3. Urgent alert update
4. User-requested speech
5. Watch or important alert
6. Advisory
7. Routine weather feed
8. Background status

The user can modify the mapping, but the dispatcher always exposes the active queue and allows immediate stop.

---

## 29. Example Built-In Profiles

### 29.1 Calm and complete

- Speaks all watches and warnings
- Reads official instructions
- Uses one clear voice
- Routine brief every 30 minutes
- No repeat after acknowledgment
- Critical alerts interrupt

### 29.2 Minimal

- Critical and urgent alerts only
- Headline plus instructions
- No routine speech
- Tray and notifications remain active

### 29.3 Weather radio

- Continuous generated channel
- Forecast cycles every 10 minutes
- Alert interruption
- Station-style identification
- Separate alert voice
- Optional community NWR stream

### 29.4 Family guardian

- Multiple locations
- Location spoken first
- Warnings repeat until acknowledged
- Watches announce once
- Combined location scan
- Distinct voice per family location

### 29.5 Screen-reader integrated

- Uses screen-reader announcement path where possible
- No duplicate self-voicing
- Earcons optional
- Opens alert details in accessible text
- Speech provider used only for continuous feeds

---

## 30. Example Spoken Output

### Quick Weather

> Home, Phoenix. 108 degrees and mostly sunny. It feels like 112. Southwest wind at 8 miles per hour. An Excessive Heat Warning is active until 8 PM Monday. The observation is 6 minutes old.

### New warning

> Critical weather alert for Home. Flash Flood Warning. Immediate, severe, and observed. In effect until 6:30 PM. Move to higher ground now. Do not drive through flooded roadways. Press the Alert Details command to hear the complete official message.

### Update

> Update for Home. The Flash Flood Warning has been extended until 7:15 PM. The affected area now includes northern Maricopa County. Official instructions are unchanged.

### Stale data

> Weather data for Travel Location may be stale. QUILL last reached the National Weather Service 38 minutes ago. Alert monitoring is retrying.

### Relay fallback

> QUILL Alert Relay is unavailable. Direct National Weather Service alert monitoring remains active and checks every 30 seconds.

---

## 31. Research Basis and Official Sources

The initial design is grounded in these official NWS capabilities and constraints:

1. The NWS API provides forecasts, alerts, observations, and other weather data as open data without usage fees, subject to reasonable rate limits.  
   https://www.weather.gov/documentation/services-web-api

2. NWS forecast lookup begins with latitude and longitude through `/points/{lat},{lon}`, which returns forecast, hourly forecast, and gridpoint metadata. The point mapping can be cached.  
   https://weather-gov.github.io/api/general-faqs

3. The NWS alerts service supports JSON-LD, CAP v1.2, and Atom. NWS recommends requesting new alerts no more frequently than every 30 seconds.  
   https://www.weather.gov/documentation/services-web-alerts

4. NWS CAP fields such as urgency, severity, and certainty are specifically intended to support decision tools and synthesized voice applications.  
   https://www.weather.gov/documentation/services-web-alerts

5. NOAA Weather Wire Service is described by NWS as its fastest method of receiving text alerts and weather information, within approximately 10 seconds of issuance. NWWS-OI requires NWS-issued credentials and an XMPP client.  
   https://www.weather.gov/nwws/faq

6. NOAA Weather Radio is a nationwide network of more than 1,000 transmitters broadcasting continuous official information on seven VHF frequencies. It is fundamentally a radio transmitter service and requires a compatible receiver.  
   https://www.weather.gov/nwr

7. Official NWR station search and county coverage information includes call signs, frequencies, SAME codes, and transmitter coverage.  
   https://www.weather.gov/nwr/station_search  
   https://www.weather.gov/nwr/county_coverage

---

## 32. Final Product Statement

QUILL Weather should feel like a trusted weather desk that belongs to the user.

It should be fast without being frantic, detailed without being overwhelming, configurable without becoming inaccessible, and powerful without hiding what it is doing.

The product’s defining achievement will not simply be that it speaks the weather. It will be that it understands the structure, timing, source, priority, location, and lifecycle of weather information—and then gives every user direct control over how that information reaches them.

QUILL Weather will turn official data into an accessible living service:

- A Weather Center when the user wants to explore
- A Weather Guardian when the user needs protection
- A Weather Channel when the user wants to listen
- An Alert Center when every second and every word matters
- A Voice Studio when one voice is not enough
- A QuillVille service built around inclusion, clarity, choice, and trust
