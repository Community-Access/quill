# Quill Radio -- Product Requirements

Version 3.0.0

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
- Networks browse section, quick-play favorites, and browse position memory (this release; `quill/core/radio/networks.py`, `quill/ui/radio/browse_tree_dialog.py`, `quill/ui/radio/browse_position.py`, `quill/ui/main_frame_radio.py`, `quill/core/keymap.py`, #1384). A **Networks** branch in Browse Stations groups well-known broadcasters (public broadcasters worldwide, US news/talk, US public radio, sports, music) as one-click nodes, each a curated `radio_browser.search_stations` query so it adds **no new egress site**; syndication services with no single stream of their own (Westwood One, NBC News Radio, ABC News Radio) open an affiliate name-search, labelled as such. CBS News Radio is deliberately excluded (the syndicated service ends 2026-05-22). Ten `radio.play_favorite_1..10` commands play the first ten favorites directly (default `Ctrl+Alt+Shift+1..0` since the plain number keys are already bound; rebindable, on the Command Palette). Browse Stations remembers the top-level source last selected and reopens there instead of collapsed. The equalizer target is already met by the existing Sound Enhancements (3-band EQ + presets + compressor/mono/night mode, applied via mpv's native `af`).
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
- Global show/hide-to-tray hotkey (2.2.0, upstream `ui/app_shell.py`, `ui/tray_hotkey.py`, `apps/radio.py`): a system-wide chord toggles the main window between shown and hidden-to-tray from any app, even without focus, over the same Windows `RegisterHotKey` mechanism the hardware media keys use. Best-effort registration -- if another app already owns the chord it is skipped silently (no error), with the tray icon and the Alt+F4-to-tray preference as the always-present fallbacks; playback/recording continue while hidden. One unique chord per family app so they never collide -- Quill Radio Ctrl+Alt+Shift+R, QUILL Ctrl+Alt+Shift+Q, Quill Weather Ctrl+Alt+Shift+W. Windows-only. Detailed in §8.
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
- A-6. The main window exposes a focusable, arrow-navigable status bar (F6 to enter, a second F6 or Escape to leave) whose cells announce live state and act on Enter, with a per-cell context menu -- a keyboard- and screen-reader-first alternative to a passive, sighted-only status line. It is user-hideable (View > Show Status Bar).
- A-7. View-menu visibility toggles (Show Station Details, Show Status Bar) persist across sessions and are honored by every surface that owns the affected control; a hidden control is never a focus stop.
- A-8. A low-vision text-size control (View > Text Size) scales the main window's fonts (favorites tree, transport buttons, now-playing line, status bar) and persists; reordering and every list action remain fully keyboard-operable at every size.
- A-9. Long-running background audio (playback, recording) keeps the machine awake so it does not stop unattended; the behavior is user-controllable and defaults on, and never inhibits display sleep (audio-only need).
- A-10. The shared-runtime download is accessible wherever it appears. Any download of the QuillVille Runtime -- from an installer or from the app's own first launch -- presents a progress bar that reports correctly to NVDA, JAWS, and Narrator and announces progress as a percentage; a silent or screen-reader-invisible download is a defect.
- A-11. **Every menu item shows a keyboard route, and no key is claimed twice.** Every enabled item -- top level, submenu, and dynamic rows such as Recently Played -- carries an accelerator in its label, because walking a menu to discover there is no shortcut is a cost paid on every visit, and a key claimed by two items means one of them silently never fires. Items backed by a registered command render through `_menu_label`, so the label shows what is *actually* bound and follows a rebinding in Keyboard Shortcuts; per-app defaults live in `keymap.APP_KEYMAPS` (app keys, not editor keys -- Ctrl+B is Browse Stations here and Bold in QUILL). Only a disabled status readout is exempt. Enforced from the built menu bar by `tests/unit/ui/test_menu_accelerators.py`, which also rejects any key wx cannot bind. Measured before the rule landed: 49 of 115 items had no accelerator, seven keys were claimed twice, and two advertised keys (`Ctrl+Shift+Plus`/`Minus`) were being discarded by wx outright.
- A-12. **A Close button closes.** Surfaces that can run modeless (Browse Stations, Find Stations, Manage Favorites, Schedule Recording) bind theirs through `dialog_contract.bind_close_button`: `wx.Dialog` handles `ID_CANCEL` for free and `wx.Frame` does not, so the window model's conversion left four Close buttons doing nothing, with only Escape working. A control that looks like the way out and is not is worse than no control.
- A-13. **Every control on a window has an Alt key, and it is a letter the menu bar has not claimed.** A button mnemonic on a frame competes with the menu bar's: when the transport button claimed Alt+S / Alt+P those keys opened the Station and Playback menus instead of stopping the radio (#1208), and the fix at the time removed the button's mnemonic entirely -- trading a broken key for no key. Two buttons kept colliding ones until 2026-08-16 (Add to Fa&vorites vs &View; &Record vs &Record), both silently dead. The rule is a *free* letter, never no letter: P&lay/S&top (Alt+L / Alt+T), Add to &Favorites, Rec&ord, &Browse Stations, plus Ctrl+Alt+P as an unconditional stop beside Ctrl+P's toggle. Status-bar cells are exempt -- they are a read-out reached with F6 and arrows (A-6), and spending six letters on them would starve the actions that need them. Enforced by `tests/unit/ui/test_button_mnemonics.py`, which checks both halves (a key exists; the menu bar does not answer it first).

## 5. Packaging requirements

- P-1. Native launcher, not a stamped interpreter. The per-app entry-point exe (`QuillRadio.exe`) is a tiny, genuinely-compiled-from-C native launcher (`quill/native/launcher/*`), not a renamed/rcedit-stamped `pythonw.exe`. This closes the ACB-reported AV false positive: the old stamped-`pythonw.exe` pattern is the textbook signature for a repackaged/backdoored Python, and the honest fix is to stop producing that shape. The launcher is a process-spawn shim (resolve a Python runtime, `exec` `<python> -m quill.apps.radio`); it does not link `python313.dll`, so it is decoupled from Python's ABI and is signtool-ready when signing lands. The legacy stamped-`pythonw.exe` remains as a best-effort build fallback for one more release (build machines without MSVC/cmake) and as a runtime-resolution fallback for in-place upgrades. Design record: `docs/design/native-launcher-2026-07-24.md`.
- P-2. Shared QuillVille Runtime, install-once-per-user. Every QuillVille app (main QUILL, Quill Radio, Quill Weather, QUILL Audio Studio) shares one Python engine -- the QuillVille Runtime -- installed once at `%LOCALAPPDATA%\QuillVille\Runtime\<major>\` and reused by all of them, so a second app starts instantly with nothing large to fetch. The native launcher's resolver (`quill/native/launcher/runtime_resolve.c`) prefers the shared runtime, then a private embedded runtime beside the launcher, then the legacy `pythonw.exe`; it never crashes and shows a product-specific error dialog if none resolve. The runtime is reference-counted at `%APPDATA%\Quill\runtime.state.json` (owned by `installer/shared-runtime.iss`): install-if-absent on setup, and removed on uninstall only when the last referencing app is gone. ffmpeg and libmpv (the mpv playback engine, with its GPL license texts and source-offer note) stage into the runtime's `tools\` and are found via `QUILL_APP_ROOT`.
- P-3. Four distribution editions, one per download need. Two full and two light:
  - *Full portable zip* (`Quill-Radio-Portable-<version>.zip`, approximately 311 MB): fully self-contained, no install, no runtime network use, runs from a USB stick. Carries a genuine unmodified embeddable Python plus bundled ffmpeg/mpv, and a `data\` folder that switches storage to travel with the app (`quill/core/storage_mode.py` recognizes `QuillRadio.exe` as portable evidence).
  - *Companion edition* (`Quill-Radio-Companion-<version>.zip`, approximately 3 MB): the native launcher plus docs only, running on the shared runtime. On first launch, if the runtime is absent, it offers to download and install it once (approximately 230 MB) behind the accessible progress UI (A-10).
  - *Full installer* (`Quill-Radio-Setup-Shared-<version>.exe`): installs the shared runtime (if absent) plus the app; Inno Setup, its own AppId, `{autopf}\Quill Radio`, per-user by default.
  - *Thin ("Lite") installer*: a small installer that downloads the shared runtime only when it is not already present.
- P-4. Runtime download is always accessible (A-10). Every fetch of the shared runtime -- whether triggered by an installer or by the app's own first launch -- surfaces a progress bar that reads correctly under NVDA, JAWS, and Narrator, announcing progress as a percentage.
- P-5. Uninstall never deletes `%APPDATA%\Quill` -- QUILL, Quill Weather, or QUILL Cast may still use it; the shared runtime is likewise left in place while any other QuillVille app references it.
- P-6. Release artifacts: `Quill-Radio-Portable-<version>.zip`, `Quill-Radio-Companion-<version>.zip`, `Quill-Radio-Setup-Shared-<version>.exe`, and the thin ("Lite") installer, tagged `v<version>`, which Help > Check for Updates compares against and downloads (the installer for an installed copy, the portable zip for a portable one).

## 6. Network requirements

- N-1. Every outbound surface is inventoried in QUILL's network-egress audit: RadioBrowser and SomaFM (search/tags/countries/click-votes/byuuid fallback); iHeart (`www.iheart.com` public sitemap index + on-demand station-page GETs to resolve a stream); TuneIn via RadioTime's OPML directory (`opml.radiotime.com` search/browse/tune, `partnerId=RadioTime`, no key); the user-typed page for Find Streams (plus, for a Triton/StreamTheWorld player page or an iHeart/TuneIn page, one follow-on call to that provider's public API to resolve the stream); the playing stream itself for ICY titles and, as a same-host last-resort for What's Playing, that stream server's own Icecast/SHOUTcast status endpoint; and this repository's GitHub releases for the update check. Playback (mpv) and the metadata/status requests send a "Quill Radio" User-Agent. No telemetry of any kind. (Sound Enhancements' local relay, §8, is loopback-only and never reaches the network itself -- it filters the same stream this section already covers.)
- N-2. Safe Mode disables the radio's network surfaces along with the feature, **per branch** rather than as one app-wide switch: `browse_sources.LOCAL_SOURCES` names the branches that need no network at all (Favorites, ACB Media, NFB Radio, the Networks catalogue), and every other branch refuses out loud with its own words rather than showing an empty folder.
- N-3. **The cost rule.** No integration may create a recurring financial obligation -- no paid API subscription, per-request or per-stream charge, commercial SDK licence, required premium or paid developer account, revenue share, paid proxy, or paid metadata service -- for BITS, for Quill Radio, or for the listener, for anything a listener needs. Optional provider functionality that independently costs money must never be required for the core integration.
- N-4. **The access rule, which is stricter than the cost rule and is what actually governed the 3.0 sources.** A source must need **no API key, no account, no developer registration, and no business relationship**. This is why Apple Podcasts is the podcast directory and Podcast Index is not (2026-08-13): Podcast Index's key is free, and a free key is still a key to configure, to support, and to explain to somebody at the worst possible moment.
- N-5. **No provider is load-bearing.** Every source can be switched off and the app is whole without it; a source that is off is never contacted, so the toggles govern egress rather than display. If a provider changes its terms, its adapter can be disabled through configuration, Quill Radio keeps working, no automatic paid upgrade can occur, and no listener can unexpectedly incur a charge.
- N-6. **Release gate.** Before every release, each provider integration is re-checked against N-3 and N-4. A provider whose required API, SDK, playback mechanism, directory access, or basic listener functionality has acquired a mandatory recurring cost is removed or disabled rather than shipped.
- N-7. **Provenance is not optional.** Every result names the provider it came from, in the row text and not only in a details pane -- including a row whose data is joined from two sources, which is why the Wikidata branch labels its rows "from Wikidata" while Radio Browser still supplies the stream.
- N-8. **Caching, in three tiers plus the browse cache.** Short for searches and trending, medium for item metadata, persistent for favorites, history and resume positions; `core/radio/directory_cache.py` adds the browse-level tier (fresh -> live -> stale, with a reportable age). Audio itself is never cached unless a download was explicitly requested. The Internet Archive adapter's cache is not optional -- the Archive's automated-access policy asks for caching, a descriptive User-Agent, restrained concurrency, and `Retry-After` on HTTP 429, and all four are honoured.

## 6a. Accessibility rules every browse branch inherits

Standing requirements, not a description of finished work: a new source in the
Browse Stations tree meets all of these or it does not ship. They were learned
one at a time from real faults, which is why each says what goes wrong rather
than only what to do.

Most of these the dialog already honours. They are written down so the nine new providers inherit them rather than each rediscovering them.

- **The count is announced on expand, and the cursor does not move.** Already the rule (#1188). A source that supplies `child_count` announces *before* the fetch as well.
- **A folder that is empty says why**, and distinguishes "this genre has no stations" from "this source could not be reached". The current `_add_children` announces a count of zero; that is not enough, and a source that is down must not read as a source that is empty.
- **A lazily-resolved leaf says what will happen before it happens.** A Mixcloud leaf says it opens in your browser. A TuneIn or Apple leaf says it resolves first. Nothing surprises the listener after Enter.
- **Loading is announced once, on the node, never on a timer**, and a slow branch does not block the tree. Already true.
- **Every bound is spoken.** Find-in-folder already reports when a depth, result, or fetch budget cut a search short. The **More...** node is the same principle applied to pagination: a truncated tree must never look complete.
- **Refresh works on every branch**, and says what it refreshed.
- **Safe Mode refuses out loud, per branch.** Local branches -- Favorites, ACB Media, NFB Radio -- keep working, which is the current behaviour and worth preserving deliberately.
- **A provider that is switched off is not in the tree at all**, and makes no request. Same rule as `search_sources.py`: the toggles govern egress, not display.
- **Browse-position memory survives the new sources.** `browse_position.py` keys on the tree path; opaque `node_id`s must be stable across sessions for this to keep working, which is a real constraint on providers that might be tempted to embed a cursor or a timestamp in an id. They must not.

---

## 7. Non-goals

macOS/Linux standalone builds (upstream QUILL covers macOS; the tray pattern does not exist there), auto-updating in place, telemetry. A full DSP effects rack (reverb, tempo/pitch, spatial audio) -- Sound Enhancements (§8) is a small, purpose-built three-band EQ and compressor, not a general effects rack.

**YouTube search and browse (decided 2026-08-12).** yt-dlp's `ytsearch:` works, needs no key, and is **against YouTube's Terms of Service**. The sanctioned route is the Data API v3, which needs a key and carries a quota. Radio's other directories (RadioBrowser, SomaFM) are open APIs built to be consumed this way; YouTube is not, and the difference is the whole argument. **No search branch** -- paste a link or a playlist. Revisit only via the Data API with the *listener's own* key, which is the shape the Spotify integration already uses.

**Commercial and relationship-gated directories (closed 2026-08-14).** Quill
Radio will not pursue, license, or integrate a station directory that requires a
commercial agreement, a paid tier, a partner approval, or a per-application
developer key. That closes the whole pile that had been kept open as a "worth an
email" list: **airable**, **vTuner**, **myTuner**, **Radioplayer**,
**Radio.net**, **Online Radio Box**, **Streema**, and the **SHOUTcast** developer
directory. **Broadcastify** was already out on its own terms (as of June 2026 the
feed-catalog API is USD 2,500 per month and they decline to license new
consumer-facing scanner applications).

Three reasons, and the third is the one that settles it:

1. **N-3 and N-4.** A recurring cost is forbidden outright, and even a *free*
   key is a key to configure, to support, and to explain to somebody at the worst
   possible moment. That is the same reasoning that put Podcast Index out.
2. **The premise expired.** vTuner's selling point was its Location / Genre /
   Language / Quality classification -- and Quill Radio 3.0 builds Country,
   State, Language, Genre, Quality, Trending and Recently-Changed browse from
   data it already fetches, for nothing. A commercial catalogue moved from "the
   thing that unlocks browse" to "a second opinion on a catalogue we can already
   browse", which is a very weak reason to accept anybody's terms.
3. **It is a standing dependency on somebody else's goodwill.** Every branch in
   the tree today can be switched off and the app is whole; none of them can be
   revoked. A licensed catalogue can be, and building the discovery experience of
   an accessibility product on something revocable is the wrong trade at any
   price.

The SHOUTcast API request sent on 2026-08-12 is abandoned rather than awaited,
and the two commitments made in it (a spoken source label, and per-source
recording suppression on request) lapse with it -- nothing was ever built on
them. **SHOUTcast streams remain fully supported**; it is only the directory that
is out, and `My Servers` browses an individual SHOUTcast or Icecast server with
no directory involved at all. **Radio Garden** stays out as a directory for the
same reason (undocumented API, no terms); its appeal is largely covered by the
Wikidata axes and Browse by Country.

Reopening any of this needs a new reason, not a new email.

**A watch link carrying `&list=` is not a playlist.** The listener asked for that video. Quietly expanding it into fifty stations would be a nasty surprise, and "it was technically in the URL" is not consent. Add-from-playlist is its own explicit command.

## 8. Since 1.0

- **YouTube subscriptions import, and the account question answered (3.0.0; `core/radio/youtube_takeout.py`, `ui/radio/youtube_takeout_ui.py`).** A listener asked whether Quill Radio could sign in with a YouTube account and synchronise their history. Both were researched against Google's own documentation and both are **no**: the [Developer Policies](https://developers.google.com/youtube/terms/developer-policies) forbid a third-party client from *"separat[ing], isolat[ing], or modify[ing] the audio or video components"* (which audio-only playback is), from background players, and from downloading or offline storage -- with **no Premium exception** -- and watch history was removed from third-party reach years ago (`playlistItems.list` answers `watchHistoryNotAccessible`; Watch Later likewise). The answerable part of the question was "do not make me paste forty channel addresses", and it is answered **without an account**: Google Takeout's `subscriptions.csv` (Channel ID, Channel URL, Channel title) imports straight into the existing `ChannelStore`. **The OAuth route was considered and refused, and the reason is the requirement**: signing a listener's real Google account into an app that also runs yt-dlp extraction puts the *account* at risk rather than merely the feature; it would additionally require every listener to create a Google Cloud project (seven console steps, since QUILL ships no shared identity) and add a credential to store, refresh and protect. The file route authenticates nothing, stores no credential, makes no API call -- so none of YouTube's API terms bind us -- and works offline and in Safe Mode. Verified while deciding: our extraction passes no cookies and no credentials, so playback is anonymous today and this keeps it so. The parser is deliberately tolerant (missing, reordered or localized header; BOM; quoted commas; a lost URL column falling back to the channel id; junk rows skipped individually), because one mangled row must not cost the other ninety-nine. One-shot by design: no background sync, and re-importing skips what is already followed. 11 tests.
- **An update offers back the edition you are running (3.0.0; `core/install_edition.py`, `core/updates.py`, `ui/app_shell.py`, the `.iss` markers).** Reported twice -- #1100 ("what was downloaded was the portable version rather than the full installer") and again 2026-08-16 ("whenever i update it shows me the portable"). #1100 was closed after fixing one axis, and the complaint outlived it because **three** faults produce the same symptom. (1) `_running_portable_build` looked for `unins000.exe` beside `sys.executable`; on the shared QuillVille Runtime that is `%LOCALAPPDATA%\QuillVille\Runtime\QuillVilleRuntime.exe`, installed `uninsneveruninstall`, so no uninstaller sits beside it and *every* installed listener answered "portable" -- the root cause both reports describe. (2) `_pick_asset` chose among four published assets by file extension, so an installed listener got whichever `.exe` GitHub listed first (the 2.6 MB thin setup even when running the 240 MB full edition) and a Companion listener got an `.exe` that cannot install a zip-based copy. (3) The uninstaller test knew only the literal `unins000`, while Inno writes `unins001`, `unins002`... when a copy is installed over an existing one. The fix gives the app a real identity: each installer stages a `quill-edition.txt` marker, detection falls back to folder shape for installs that predate it, and the uninstaller is matched by pattern; an install that cannot be told apart resolves to the thin installer, which shares the full one's AppId and upgrades either. 15 tests, including one asserting each published asset matches exactly **one** edition, so "first `.exe` wins" cannot return. Two more repairs on the same path, the first the most serious defect found that day: **`shared-runtime.iss` installed the runtime where the launcher never looks.** `runtime_resolve.c` probes `Runtime\<major>\quillville-runtime.json` -- versioned, because the design keys runtimes by major so a future Python lands alongside rather than on top -- while the fragment installed to the unversioned `Runtime\`, so a clean install could not start: "Quill Radio could not find a Python runtime". `RuntimeDir()` now derives the major from `RuntimeVersion`; the thin installers had been probing the correct versioned path all along and keep it; and `tests/unit/structure/test_shared_runtime_installer.py` pins launcher and installers to each other, so either side moving alone fails the build. Found by running an installed copy, not by reading either file -- each was reasonable alone. Second: the fragment skipped the payload copy whenever the CPython version matched, so an update installed cleanly and left the old code in place.
- **Directories say when they are down, instead of looking empty (3.0.0; `core/radio/browse_failure.py`, `core/radio/directory_cache.py`, `core/radio/internet_archive.py`, `core/media/librivox.py`, `ui/radio/browse_feedback.py`).** The empty-versus-broken distinction the browse contract promises was leaking in two places. Every source wraps transport failures in its own coded error and the classifier matched only the outermost type, so LibriVox being unreachable for a day (Cloudflare 522 after a ~19.5 s hold) reported "no data in the folder" on every shelf; it now walks the `__cause__`/`__context__` chain. And the Internet Archive answers a failed search with **HTTP 200** plus `{"error": "[BACKEND_ERROR] ..."}`, which parsed to zero docs -- Radio Programs reported itself empty, and because that empty payload was a truthy dict it was **cached**, outliving the outage; the error body now raises (`service_unreachable`), empty listings are never cached, and `directory_cache` records a swallowed refresh failure so `browse` can still tell empty from broken without the cache layer having to raise into a tree. LibriVox browse also drops from the 20 s book-download budget to 8 s, and a branch names itself while loading and speaks up if it passes three seconds, because slow and hung are the same experience in silence.
- **AudioPub as a Community Audio source, v1 = Discover only (3.0.0; `core/radio/audiopub.py`, handlers in `core/radio/browse_libraries.py`).** AudioPub (audiopub.site) is an open-source (AGPL-3.0) platform whose agreement says uploads are publicly streamable and downloadable. Its own client code implements one JSON endpoint -- `GET /quickfeed/api?page=N`, 50 items per page, deliberately randomized server-side -- so v1 is exactly that: a **Discover** shelf (a random fifty, different every time, with a "More to discover" row), each row playable with a timeline and carrying its creator and play count. Two boundaries, both deliberate: (1) the software being open source does not make the *audio* freely licensed -- uploaders keep their rights, so AudioPub is live-only, excluded from the station catalog, and the Status view says why; (2) newest/popular/search/live-streams all exist server-side but have no public API, and the plan of record is to **ask the AudioPub developer to bless a small read-only API** for them rather than screen-scrape an internal one that can change. Live Now (Icecast at live.audiopub.site:8000, mount = user id) is the most interesting v2 branch once blessed -- playback is infrastructure Quill Radio already speaks.
- **Find became branch-smart, and the tree learned to read ahead (3.0.0; `core/radio/branch_find.py`, `ui/radio/browse_prefetch.py`, scoped filters on `catalog.store.search`).** *Find in this folder* used to answer one way everywhere: crawl the subtree and match labels -- which anchored on Podcasts meant crawling chart pages and never asking Apple's search engine (how a show as findable as Double Tap came back "no matches", reported 2026-08-16). Find now routes to the fastest honest channel for the anchor: the Podcasts branch asks the real iTunes Search API and answers with show *folders* that expand into episodes; a catalog-served Radio Browser axis answers from the local FTS index, scoped to the anchored country/state/language/genre/codec -- instant and offline; LibriVox, the Internet Archive, Project Gutenberg, SomaFM, TuneIn, iHeart, NOAA, Audius, Mixcloud and ccMixter each route to their own search engine (books and Archive items as drillable folders, TuneIn rows stream-resolved); only engine-less branches keep the bounded crawl, and an unreachable directory reports itself rather than posing as "no matches". Ctrl+F focuses the box from anywhere in the window. Every answer states its origin out loud ("Searched the whole podcast directory", "From your catalog"). The Find box moved **above** the tree -- one Shift+Tab away -- and the tree got **predictive prefetch**: highlighting a collapsed folder starts its fetch immediately and a just-opened folder's first child folders fetch behind it, so expands the listener was about to make open instantly. Prefetch is driven only by where the cursor actually is: hidden sources stay uncontacted, Safe Mode fetches nothing. Related fix: a Find Stations result that is a *work* rather than a stream (an Apple show, a LibriVox book) used to hand the player an empty URL and silently do nothing; Play now resolves it off-thread and starts the show's latest episode or the book's first section, announced by name.
- **Browse as a contract, not a window (3.0.0; upstream `core/radio/browse_nodes.py`, `core/radio/browse_sources.py`, `core/radio/browse_visibility.py`, `core/radio/directory_cache.py`, `ui/radio/browse_tree_dialog.py`).** The Browse Stations window knew the shape of all thirteen sources in it: adding iHeart had cost three internal node-kind strings and edits in six places, and *Find in this folder* carried a **second** copy of the same knowledge, hand-synchronised -- so a source added to the display and forgotten there was silently unsearchable, with no error to notice. `BrowseNode` is now the whole contract (folder / leaf / action, plus `note` and an optional `child_count`), every source answers exactly one question -- *what is inside this folder* -- through one registry (`ROOT_SOURCES` plus one handler), and the dialog knows only that a row is something to open or something to play. Adding a source is one registry entry and one function, both testable with no wx at all. The window ended **199 lines smaller while the tree it serves grew from thirteen root branches to twenty-eight**, and its GATE-11 budget was ratcheted down to hold that: a change that puts a source-specific branch back inside it fails the build. Three behaviours came with the refactor: an empty branch distinguishes "this genre has no stations" from "that directory could not be reached" (they used to be indistinguishable, which is how a listener concludes a working source is broken); a folder announces its size with its name where the source can say cheaply; and `directory_cache` adds the fourth cache tier (fresh -> live -> stale) so a level survives a session, a failed refresh keeps what was there rather than blanking a working branch, and a cached answer reports its own age instead of implying it is current. `LOCAL_SOURCES` is what Safe Mode reads, per branch, rather than a single app-wide switch.
- **Nine new browse branches, none of them needing a key (3.0.0; upstream `core/radio/radio_browser.py`, `core/podcasts/apple_podcasts.py`, `core/radio/internet_archive.py`, `core/media/librivox.py`, `core/radio/gutendex.py`, `core/radio/free_music.py`, `core/radio/wikidata.py`).** The access rule is the organising principle: no API key, no account, no developer registration, no business relationship.
  - *Four axes the directory already published.* **By Country** -> state/region (the `/json/states/{country}/` **trailing slash is required** -- without it the API answers "this country has no states" rather than an error, which is a fault no unit test would have caught), **By Language**, **Trending Now** (`topclick`, genuinely distinct from `topvote` behind Popular Stations), and **Recently Added or Changed**. No new egress host: this is data Quill Radio was already downloading to fill two dropdowns.
  - *Apple Podcasts, keyless.* Storefront -> genre tree -> subgenre -> charts -> lazy `lookup` -> `feedUrl`. Genre tree cached a week, charts six hours, feed URLs a month; one chart request serves every genre in a storefront. **A chart row is tagged with its leaf genre and never its ancestors**, so filtering the US top 100 by Arts returned zero -- `genre_id_set` expands a genre to its subtree. Apple is discovery only: a show resolves to the publisher's own RSS and everything after that (episodes, audio, transcripts) comes from the feed, so the branch is switchable off at no cost to playback. **Podcast Index is out** -- decision 2026-08-13, reversing the earlier plan: it needs a free key, which means a key to configure, to support, and to explain to somebody at the worst moment, and transcripts never came from a directory in the first place.
  - *Internet Archive.* The collection tree walked to any depth (every item declares its parents, so one query shape walks all of it), `Retry-After` honoured on HTTP 429 per the Archive's automated-access rules, a **More...** node that states how many rows it is hiding rather than silently showing the first hundred of eight thousand, and rights metadata shown only where the item publishes it.
  - *LibriVox, Project Gutenberg, Audius, Mixcloud, ccMixter.* LibriVox: Recently Added, By Genre (43), By Author A-Z (~7,000); **no By Title**, because the catalogue supports no title filter in any form -- four were tried and all answer 404 or 400 while author works from the same address, and an axis that quietly finds nothing is worse than one not offered. Gutenberg: the 1,124 records carrying human-read audio, by topic and language. Audius: trending overall and within 27 genres, gated tracks dropped rather than listed and refused at play time. **Mixcloud is Mode A only** -- metadata browse, and activating a show opens it in the listener's browser; no stream extraction, and the row says so *before* activation, per Mixcloud's widget terms. ccMixter: by tag, each row carrying its own licence.
  - *Explore (Wikidata).* By City and By Format (P131/P415) plus On the Dial by FM band, matched conservatively against Radio Browser, which still supplies every stream. Labelled "from Wikidata" because the join is Quill Radio's, not either source's. **A place and a format are asked of Radio Browser directly** and topped up with Wikidata's call-sign matches: the reverse order takes Wikidata's capped, unordered slice as the universe, and Arizona opened to nothing while forty-eight of its stations were playable (reported 2026-08-16). **By Network was removed and By Format moved off P2360** in the same pass -- P449 is recorded for two US radio stations and P2360 for none, so neither folder could ever list anything; same reasoning as the RadioDNS non-goal below, and found by opening every axis in one sweep rather than waiting for a report. **By Owner (P127) was removed 2026-08-17**, and it is the rule the axis set now follows: *an axis stays only if Radio Browser can answer it directly*. Ownership is not a field Radio Browser carries, so an owner folder had no lead query and fell back to call-sign matching alone -- it counted correctly and then opened to nothing, or to a fraction of the named company, about three times in four. Empty-before-opening (By Network) and empty-at-the-leaf (By Owner) are the same defect at two depths.
  - *My Servers and YouTube Channels, and the action-row contract they needed.* `core/radio/my_servers.py` enumerates Icecast (`/status-json.xsl`) and SHOUTcast (`/stat`, `/7.html`) mounts with now-playing text on each; `core/radio/youtube_channels.py` pages a channel's uploads and playlists with no Google account. Both are branches you add to yourself, which needed the one node kind nothing had ever handled: `BrowseNode.is_action` existed and `browse_tree_dialog` ignored it, so "Add a Server..." and "Add a Channel..." were rows that did nothing on Enter -- precisely the failure `bounded_playback_ui`'s house rule exists to prevent. Dispatch is now `ui/radio/browse_actions.py`, one registry entry per action, so the window still learns nothing source-specific and the next "Add..." row costs a function. Three rules the actions share: the address is **probed before it is stored** (`my_servers.probe`, or the same shallow listing request the branch itself would make), and one that answers with nothing is refused rather than kept as a dead row; the probe runs on the task manager, never the UI thread, because a small box on a slow link can take the full twelve-second timeout; and Safe Mode refuses out loud, per action, before anything is asked. **`my_servers` is the one deliberate plain-`http` exception in the app**: a large share of small Icecast boxes are http on a high port and always have been, refusing them would refuse the whole audience the branch exists for, the address is one the listener typed, only a GET is sent, and no credential is ever attached. Written down rather than quietly made.
  - *Song Details (upstream `ui/radio/song_facts.py`).* `core/radio/musicbrainz.py` had been written and called by nothing; it is now the **Song Details** button in the Song History window -- release, year and length for the selected song, which is the difference between a list of titles and a history somebody can act on. Deliberately a button: automatic enrichment would issue a network request per row and spend a listener's connection on curiosity they never expressed. On the task manager, self-rate-limited to MusicBrainz's one request per second (the module keeps the interval itself rather than trusting callers), and **degrading to "nothing more is known"** rather than to an HTTP message -- somebody asking what album a song is from is not served by a status code. Injected into the dialog as a callable, matching the existing Background lookup, so the window keeps one injection style.
  - *RadioDNS is a non-goal (2026-08-14), and the module was **removed** rather than left as dead code.* It resolves a broadcaster's own service document from the **broadcast** parameters -- frequency, PI code, ECC -- and Quill Radio has no source of PI codes; wiring it would have meant a form asking a listener for a value nobody has, which is the same failure as an axis that quietly finds nothing. Its egress entry went with it, and `dnspython` was dropped from the dependencies, nothing else needing it.
- **Playlist formats, and the M3U8 ambiguity (3.0.0; upstream `core/radio/playlist_formats.py`, `core/radio/playlist_export.py`).** PLS, XSPF and ASX join M3U on import, and favorites export to all four -- each asserted to round-trip through its own parser rather than merely to serialise. ASX is read twice, strictly and then forgivingly, because in the wild it is frequently not valid XML at all. XSPF and ASX go through `safe_xml`, so a billion-laughs playlist is refused rather than opened. `classify_m3u` settles the real bug: an `.m3u8` is either a station list or an HLS manifest, the two share an extension *and* a first line, and handing the second to the importer produced a list of two-second "stations" -- content wins over extension, because a server naming a live stream `.m3u` is common, and every sniff outcome is speakable.
- **Where you stopped, for anything with an end (3.0.0; upstream `core/radio/resume.py`, `ui/radio/resume_playback.py`).** Deliberately separate from `core/media/positions.py`, which Cast and the Media Player use: that store keys on a *file* by name and size, and nothing Quill Radio plays here is a file. These key on the stream URL, normalised so a session token or a changed scheme still finds the place. A position under `MIN_RESUME_MS` is not a position and saving one *clears* the entry; within `END_MARGIN_MS` of the end counts as finished and clears it too; every failure degrades to "no saved position" and never reaches the player. Which rows have a timeline at all is `RadioStation.is_recording`, declared by the source that produced the row -- a live station has no position worth remembering. Extracted to its own module rather than grown inside `player_controller.py`, which is at its GATE-11 ceiling.
- **Timed transcript cues (3.0.0; upstream `core/podcasts/transcripts.py`).** `TranscriptCue`, `parse_transcript_cues`, `cues_to_text` and a binary-search `cue_at`, over WebVTT, SRT, Podcasting 2.0 JSON and YouTube `json3` -- the last arriving free with every YouTube resolve and previously discarded. `parse_transcript` is redefined as the timed form with timings removed, so there is one reader rather than two that drift; Cast's existing tests are the regression gate and pass untouched. This is the foundation for follow-playback, jump-to-line and spoken positions; the reading surface itself is not built.
- **Three silent faults (3.0.0; upstream `core/radio/xiph.py`, `core/radio/tunein.py`).** Xiph's genre index had outgrown the page-size cap and was being truncated mid-file, losing 412 genres and a *different* number on every refresh, in perfect silence -- the reader is deliberately forgiving of mangled markup, which is right for a website tweak and exactly wrong for a size limit. Truncation now raises; the cap fits the page. The same list was also being sorted alphabetically, destroying the directory's own popularity order (it opened on `00`, `00s`, `100.1`); source order is kept, obvious non-genres are filtered, and the branch offers the top 120. TuneIn's stream choice was a *filter* (first thing that is not TuneIn's own un-followable redirect) rather than a *ranking*, so it could hand back `http://` while an `https://` sat beside it; it now ranks not-a-redirect first, then encrypted over unencrypted, while still preferring a plain address that plays over an encrypted one that does not.
- **The download queue, its filing rules, and books that play back (3.0.0; upstream `core/radio/download_queue.py`, `core/radio/download_prefs.py`, `core/radio/downloaded_books.py`, `ui/radio/download_runner.py`, `ui/radio/download_queue_dialog.py`, `ui/radio/download_menu.py`, `ui/radio/book_playback.py`, `ui/radio/track_end.py`).** Saving one file needs no queue; saving a forty-chapter book while listening to something else is the real shape. **One transfer at a time, in the order asked** -- not a pool: every source here is a free library on donations, parallel fetches are a worse citizen for no audible gain, and order is what makes a part-finished book a *playable prefix*. The pump is re-entrant-safe by construction (each completion schedules the next from the UI thread's own callback), so there is no lock because there is no concurrency to guard. **View > Downloads... (Ctrl+Shift+J)** is the monitor; finished rows persist until cleared, because "did that actually download?" is the question asked most and a self-tidying list cannot answer it. Cancel/remove/clear-finished/clear-all all preserve what is on disk; the running row cannot be removed from under its own transfer. Closing the window honours `keep_going_in_background` and **states the outcome either way** -- silence in both directions is equally surprising.
  - *Filing is a design decision, not a preference dump.* `plan_destination` puts a podcast under its show and a book in its own folder, and adds an **author** folder only once a second book by that author exists -- an author folder holding one book is a folder you open and immediately leave, and the right answer depends on what is already on disk, which is why the function is given the library it files into. `safe_segment` handles Windows reserved names and trailing dots, since a silently-renamed folder merges two books into one.
  - *A downloaded book is read back off the disk, not indexed.* `downloaded_books` sorts naturally (2 before 10 -- a book that plays its tenth chapter second is worse than one that will not play), admits only audio (the licence note beside a CC track is not a chapter), and understands both filing shapes. The folder **is** the record: no database, no startup scan, so a chapter moved by hand simply changes the book. `book_playback.handle_finished` auto-advances, announcing position-first ("4 of 40"), and says when a book ends rather than leaving silence that is indistinguishable from a fault. It plays each chapter as an **ordinary station**, so resume, Sound Enhancements, the Winamp keys and Continue Listening all apply without earning them twice. `track_end.py` is the GATE-11 extraction that made room and is better for it: an end-of-playback is three different events (dropped live stream / chapter finishing / recording genuinely ending) and the order they are asked in *is* the logic.
- **Continue Listening spans local files (3.0.0; upstream `core/media/local_paths.py`, `core/media/continue_listening.py`).** `PositionStore` keys on file *contents* so a place survives moving, renaming and a different OS -- which is why it stores no path, and why local files could never appear in a resume list. A **local-only sidecar** records where each media id was last seen. Deliberately not a field on the synced record: a path is a fact about one machine, putting one in a travelling record leaks a folder layout to every device, and two machines disagreeing about a location is two correct answers rather than a conflict to merge. A stale hint is skipped rather than offered-and-failed; the position itself is untouched and is recovered the next time the file plays. Classified `cache` in the persistence audit, which is exactly what it is.
- **Download, and the rights rule that governs it (3.0.0; upstream `core/radio/downloadable.py`, `core/radio/media_download.py`, `ui/radio/download_command.py`, `ui/radio/browse_tree_menu.py`).** Quill Radio surfaced a great deal of freely-licensed material it could play and not save. The feature is small; the **policy** is the design. `downloadable.can_download` is a pure, unit-tested predicate over an **affirmative allow-list** (LibriVox, Project Gutenberg, Internet Archive, ccMixter, podcast enclosures), so an unrecognised source is refused rather than guessed at -- N-7's provenance discipline applied to writing files instead of reading them. Four refusals carry their own sentence, because a missing menu item is indistinguishable from a bug and the reasons differ in kind: **live** (no file exists; named Record Station as the command that does apply), **Spotify** (DRM), **YouTube** (a decision the PRD already records, restated rather than silently enforced), **Audius** (downloadability is the artist's choice and is absent from the listing, so no guess is made). The check runs at the transfer boundary as well as in the menu, so no path reaches the network without it. `media_download` fetches in bounded chunks with a `.part` file and a Range header, so a long transfer resumes and a cancel lands **inside** a file rather than between files; `download_book` walks chapters **in order** (a part-finished book is a playable prefix), isolates a failure to one chapter, and reports progress in chapters rather than bytes. A Creative Commons licence is written beside the audio -- saving the work and discarding its terms strips the one thing the licence exists to carry. One new reviewed egress entry; no new hosts, since every address comes from a directory the browse tree already reached. `browse_tree_menu.py` is the GATE-11 extraction that made room for the menu item, and `network_egress_entries.py` is the extraction that made room for the audit entry.
- **Federated search across the libraries (3.0.0; upstream `core/radio/federated_search.py`, `ui/radio/library_search.py`, `ui/radio/search_paging.py`).** 3.0 grew fifteen browse branches while Find Stations searched the same eight radio directories, so a listener could *walk* to a LibriVox book by author and could not *find* it by typing the title. Now LibriVox, Internet Archive, Project Gutenberg and Apple Podcasts are queried alongside the directories. **Not a new window**: rows land in the existing results list carrying their own `RadioStation.source`, which the Source column already renders and the Source dropdown already filters, and the existing cross-directory merge de-duplicates them unchanged -- a second search surface would be a second thing to learn for no gain. **No new egress hosts**: `internet_archive.search` adds a query shape to the scrape endpoint the tree already uses, and `gutendex.audiobooks` gained a `query` parameter that maps to Gutendex's own `search`. Four rules. **No cross-provider ranking** -- each source's own order is preserved within its group, because a relevance score comparing a LibriVox chapter with an Archive recording is a research project pretending to be a feature and a wrong one is worse than an honest concatenation. **One task per source**, so a slow library never holds up the others or the stations, with results appended as they land and the listener's cursor preserved mid-read (`_show_category_for_library_results`). **One announcement, when the last source reports** -- the pending counter exists solely to make "last" knowable, because a list that announces itself five times cannot be read. And **a source that cannot be searched says so** -- `search=None` plus a written reason, named once in the summary, since "no results from Mixcloud" and "Mixcloud cannot be searched" are different facts and only one means try different words. **No source is in that state.** Audius, Mixcloud and ccMixter shipped declared unsearchable ("trending only", "categories", "tags") and all three publish a keyword search; verified against the live services 2026-08-14 and wired the same day (`free_music.audius_search` / `mixcloud_search` / `ccmixter_search`, `/v1/tracks/search`, `/search/?type=cloudcast`, and `api/query` with `search=` instead of `tags=`). The parsers needed no change at all, because a search result and a trending result are the same object from the same service -- which is the measure of how small the gap was, and of how easily a shelf becomes a believed limit. **Mixcloud stays Mode A**: search changes how a row is found and nothing about what it is, so no stream URL is extracted and the row still opens the show's page in the browser, labelled before Enter. The unsearchable machinery is kept for the next source that genuinely lacks a search; having nowhere honest to record that is what let three wrong claims stand for a release.
- **Video, and the accessibility specification it is built against (3.0.0; upstream `core/radio/video_formats.py`, `core/radio/caption_style.py`, `ui/radio/video_window.py`, `ui/radio/video_commands.py`, `ui/radio/video_output.py`, `ui/radio/mpv_video_mixin.py`, `ui/radio/caption_settings_dialog.py`, `apps/radio_video_menu.py`).** Quill Radio could play a YouTube link and could not show it -- video was off in three separate places, none of them a bug, all of them the right first version. The consequence had become wrong: a lecture with slides or a livestream with an on-screen crawl was a partial product, **low-vision listeners were excluded from a feature nominally for them**, and a blind listener could not share what they were hearing with a sighted person in the room.
  - *The design, in one sentence.* **Video is a view onto playback, never a mode of playback.** `attach_video` sets mpv's `wid` to the panel's handle and flips `vid` from `no` to `auto`; `None` reverses both. mpv accepts both at runtime, so **showing and hiding the picture never restarts the stream and never costs the listener their place** -- which is the property that makes video safe to offer at all. Never opening the window leaves 3.0's behaviour byte for byte.
  - *Two URLs, not a merge.* YouTube serves adaptive video and audio separately. Having yt-dlp merge them means downloading the whole video before a frame plays -- not streaming, and impossible for a live broadcast. `pick_video_stream` therefore chooses a **video-only** format (tallest to `MAX_HEIGHT = 1080`, then bitrate, then frame rate; combined formats are skipped, since the single-URL path already handles them and pairing one with a separate audio file would play the programme twice) and the audio is handed to mpv's `audio-files`. This is what mpv's own `ytdl_hook` does internally. A live HLS manifest carries both, so the existing path is unchanged and `pick_video_stream` answers with nothing.
  - *The surface, which is where video players fail.* An mpv-rendered child window is, to assistive technology, an unnamed handle containing nothing. The panel carries an accessible **name** (the video's title, updated silently on change -- it is for somebody navigating there, not an announcement for somebody listening), a **description** stating what it is and where the controls are, is in the tab order **exactly once** with no trap, and **never takes focus by itself** except deliberately once, on open. A top-level `wx.Frame` rather than a docked panel: the main window's tab order is screen-reader-tested and must not be perturbed, a frame can be moved to a second monitor, and one window with one Close is unambiguous. **No on-screen buttons** -- every command is a menu item, a palette entry and a rebindable key, because duplicating them into an unlabelled strip is how video players become inaccessible. The status line is **not a live region**; a self-announcing position display is the commonest way a media player becomes unusable. **The close handler opens no modal**, which is a repository-specific hazard already hit once on wxMSW.
  - *Section 508 503.4 shapes the menu.* Captions and Audio-and-Described-Audio are Playback items beside Volume because the rule requires user controls for captions and for audio description at the same menu level as volume. Read as a design instruction rather than a checkbox, it produces a better menu for free.
  - *Captions (503.4.1, WCAG 1.4.3 and 1.4.4).* External caption file via `sub-add`; `CaptionStyle` -> `mpv_properties` is the only place that knows mpv's caption properties. **Opaque background by default** -- caption text sits over arbitrary moving pictures, so no colour can be guaranteed to contrast with what is behind it, and a solid box is the only honest answer. Sizes are percentages of the player's own default (so they scale with the window) up to **300%**, because 1.4.4 asks for 200% and a floor is not a target. Three text colours and three backgrounds rather than a colour picker: a free choice invites a combination that fails silently. Every stored value is clamped, because a settings file is somebody else's input. An **automatic** caption track is announced as automatic, once.
  - *Photosensitivity (WCAG 2.3.1), answered honestly.* A stream cannot be analysed for flashing before it plays, so the claim is not made. Instead: video never starts on its own, the picture can be **dimmed** through mpv's `brightness`, and **hiding it is one keystroke from anywhere in the app** -- escape from an unpleasant image must not require finding the right window first.
  - *Keyboard only (WCAG 2.1.1, 2.1.2).* Every capability has a command, resize and full screen included; no new command takes a bare letter or number, which would collide with station-list type-ahead; full screen has two documented exits and **speaks both on entry**, because a way out that is true but unstated is not usable.
  - *Deliberately not built.* **No YouTube web player or IFrame API** -- it would bring a WebView, its accessibility, its adverts and its tracking into an app whose house position (recorded in `link_finder.py`) is to prefer the user's real browser for anything accessibility-sensitive. **No video downloading**: the resolve stays `download=False` and recording still captures audio. **Video is not the default** and never becomes it.
  - *Consent.* `YOUTUBE_CONSENT` promised only "the audio stream behind the page", which stopped being the whole truth; it now says audio *or* video and states the rights reminder more firmly. The consent **flag does not reset** -- somebody who consented to YouTube has consented to YouTube, and asking twice for a superset is friction rather than ethics -- so the change is stated plainly in the release notes for everyone who already agreed.
- **Described audio (3.0.0; upstream `core/radio/audio_tracks.py`, `ui/radio/audio_track_dialog.py`, `ui/radio/track_selection.py`, `apps/radio_video_menu.py`).** **The product's reason for existing, and the strongest single differentiator in the app.** A described audio track is a second narration saying what a sighted viewer can see. Broadcasters publish them; YouTube carries them on a growing number of videos; and the desktop-player state of the art is an audio-track menu reading "Track 1 / Track 2 / Track 3", which for a blind listener is not a control but a puzzle solved by playing each in turn. **Playback > Audio and Described Audio... (Ctrl+Shift+A)** and **Play Described Audio (Ctrl+Alt+D)**. `tracks_from_info` reads the renditions yt-dlp already reports on every resolve (audio-only, deduplicated, URL kept); `is_described` is a **pure, unit-tested** predicate, generous about form and strict about meaning -- "English (Audio Description)", "descriptive", "eng-desc", "English AD", and the BCP 47 `x-description` / `x-desc` / `x-ad` subtags -- so the heuristic can improve as publishers change their labelling without touching a line of UI. `describe_track` **names** each rendition ("English (described)") and drops yt-dlp's own quality notes (`medium`, `DRC`), which describe the encoding and not the content. Four product decisions: the described track is listed **first with the cursor on it** and its availability stated *above* the list, because that is the one fact the listener opened the window to learn; it is **ordered, never filtered**, so somebody who did not ask for description is never surprised by it; **selection keeps the position** (`track_selection.play_audio_track` reads `position_ms` before the reload and restores it through `_pending_resume_ms`, because a rendition is a separate URL rather than a channel of one stream, and losing an hour of a film to enable description would defeat the feature exactly where it matters); and **absence is reported with what the video does have** (`summarise`), never as a disabled command -- "no described audio" alone leaves the listener unable to tell a video's omission from an app's limitation. **And the feature announces itself** (`track_selection.announce_described_if_new`, called from `_on_radio_state_changed`): a video carrying a described track says so **once**, keyed on the station so a repeat is impossible within a session, naming the key. This is the part that decides whether the feature reaches anybody -- a command you must already know about only serves the people who least need it, and essentially nobody expects a desktop radio player to offer described audio. `_selected_audio_track` is cleared on every `play_station`, so a choice made for one video never silently carries to the next.
- **Transcripts, end to end (3.0.0; upstream `quill/ui/transcript_reader.py`, `ui/radio/transcript_command.py`, `apps/radio_video_menu.py`, `core/podcasts/transcripts.py`).** **Playback > Transcript... (Ctrl+Shift+T)** on a finished video. The caption track was already being captured by every YouTube resolve and discarded; `PlayerController.caption_track()` exposes it and `fetch_transcript_cues` parses YouTube's `json3` through the same cue reader Cast uses. The window is **shared with Quill Cast**, not Radio's own -- two transcript readers would drift apart the day after the second was written -- and it is a read-only `wx.TextCtrl` rather than a custom list, so arrow keys, word and line movement, selection, the review cursor and Find all behave exactly as they do everywhere else. `line_starts` and `cue_index_for_offset` map character offsets to cues and back, which is what lets Enter seek correctly however the caret got there. **Follow the audio is off by default** (while somebody is reading, playback must not move their caret) and silent while on (a position per line would be unusable); every position is spoken as words through `spoken_duration`; Save As keeps the timings via `cues_to_vtt` / `cues_to_srt`, both asserted to round-trip through the parser rather than merely to serialise; and an **automatic** caption track is announced as automatic in the heading, because a machine transcript presented as a human one is exactly the confident wrong answer rule A-10 exists to prevent. Four refusals, each with words: a live stream has no transcript, a video with no published captions says so, Safe Mode refuses before any request, and an unparseable file is reported. The fetch is on the task manager, never the UI thread. `apps/radio_video_menu.py` is the GATE-11 extraction that made room for the menu item, and it returns its id refs so `radio.py` can still pin them.
- **A dropped live stream reconnects, in two layers (3.0.0; upstream `ui/radio/mpv_radio_engine.py`, `ui/radio/live_reconnect.py`, `ui/radio/player_controller.py`, `core/radio/iheart.py`).** Reported against KFI Los Angeles: "plays for about 20 seconds and then stopping", plus a second station replaying its last five seconds. Root cause, confirmed by live capture: iHeart's `secure_hls_stream` answers 302 to a **per-listener** host carrying `rj-ttl=5` and a session cookie, and the media playlist behind it holds three segments at `EXT-X-TARGETDURATION:10` -- a thirty-second window refilled every ten seconds. A single failed playlist refresh or segment fetch therefore drains the buffer and ends the stream twenty to thirty seconds later, which is the reported symptom exactly; the replayed five seconds is the same fault caught a step earlier, where a silently re-established connection re-serves what it already sent. The code gap was total: `MpvRadioEngine` set **no ffmpeg reconnect options**, so one transient read error was terminal, and `_on_finished` treated EOF on a live station as the end of the stream. The one retry path that existed, `_attempt_engine_fallback`, is gated on `CONNECTING` and never fires mid-stream. Three parts. (1) `stream-lavf-o` now carries `reconnect=1,reconnect_streamed=1,reconnect_on_network_error=1,reconnect_delay_max=30` -- `reconnect_streamed` is the load-bearing one, since without it ffmpeg refuses to reconnect a non-seekable stream, which describes every live station -- and `_NETWORK_TIMEOUT_SECONDS` rose 15 -> 30, which was tight against a playlist that only advances every ten seconds. (2) `ui/radio/live_reconnect.py` (extracted, not grown inside the controller, which was at its GATE-11 ceiling) retries a dropped **live** station `MAX_ATTEMPTS = 3` times at 2 s / 5 s / 15 s, announcing each attempt with its number and the outcome either way; a **bounded** source is excluded via `is_seekable`, because a recording reaching its end has ended and reconnecting would replay it; a retry whose `_play_token` has moved on is dropped, so Stop or another station cancels it; and "Reconnected" is said only from `_on_loaded`, never from the scheduling side, so no success is claimed that was not observed. The one wx call it needs is `PlayerController._schedule_later`, injected, which keeps the module wx-free and lets tests drive the retry synchronously. (3) `_STREAM_KEYS` now prefers `secure_shoutcast_stream` over `secure_hls_stream`: one long HTTP body, no segment window, no per-refresh token, no per-listener session to lose. Parts 1 and 2 harden every station; part 3 removes the failure mode for iHeart specifically. **Also verified and recorded:** a separate report of "KNBR does not play in Quill" was **not a bug** -- the URL supplied was the station's homepage, whose player is built in JavaScript, and `link_finder.py` deliberately never runs JavaScript, so finding nothing there is correct behaviour. The playable feed resolves through Triton's provisioning API (`station=KNBRAM`).
- **TuneIn stream choice prefers progressive over HLS, host-scoped (3.0.0; upstream `core/radio/tunein.py`).** The same failure mode as `iheart._STREAM_KEYS`, reached through a different directory. Reported against **96.5 The Fan, Kansas City** -- the Chiefs flagship, TuneIn guide id `s28141`, absent from Radio Browser entirely and not addressable through the Triton provisioning endpoint under any call-letter mount tried, which is why the first pass could not identify it. `Tune.ashx` returns two addresses for it: an HLS manifest on `live.amperwave.net` and a progressive MP3 on `ais-sa40.cdnstream1.com`, and rank-first took the manifest. **The restriction is the design.** Those two hosts are different companies, and the MP3's own query string carries `aw_0_1st.stationId=s324671`, `class=music` and a music `genre_id` where the station is sports -- so it is very possibly not the same programme at all, and a blind progressive preference could hand a listener a different broadcaster. That is a materially worse failure than a dropout, which the engine's reconnect options and `ui/radio/live_reconnect` already cover. So `best_stream` demotes HLS **only when a progressive URL on the same host is available**, which is exactly the shape of the iHeart case (`.../zc177` beside `.../zc177/hls.m3u8`) and a strong signal of one stream in two deliveries. `_is_hls` matches the path only, because TuneIn's URLs carry heavy tracking query strings and matching those would demote ordinary MP3s. Probed 2026-08-14: both forms captured clean here (60.0 s, 59/59 unique one-second windows on the HLS form; 25.0 s clean on the MP3), confirming the fault is timing- and route-dependent rather than reproducible on demand.
- **A capture that recorded nothing is a failure, not a recording (3.0.0; upstream `core/radio/recording_outcome.py`, `core/radio/recording.py`, `ui/main_frame_radio.py`).** Reported alongside the dropout above (John, 2026-08-14, against 96.5 The Fan Kansas City): Record gave no confirmation of a start or a stop and left an empty recordings folder. Two defects met. ffmpeg writes the output container the instant it opens the file, **so file existence was never evidence that any audio arrived** -- and `_monitor` fired `on_state_changed(False, landed, ...)` for a job that produced zero bytes, which the frame announces as "Recording saved: <name>". `recording_outcome.py` now owns the whole "how did this capture end" verdict: `captured_nothing` (missing, or under `MIN_USEFUL_CAPTURE_BYTES` = 8 KiB -- deliberately generous, since deleting audio somebody wanted is far worse than keeping a very short file), `empty_capture_reason` (read from ffmpeg's own last stderr lines, most recent match first, falling back to an honest admission rather than a guess), `discard_empty_capture`, and the `FATAL_STDERR_RE` / `RECOVERY_STDERR_RE` classifiers that moved with them because they answer the same question. `RadioRecorder` gained `on_capture_failed(station, reason)` -- **separate from `on_state_changed` on purpose**, because the two say opposite things: one reports a file that exists, the other reports that there is none -- and the frame speaks it on `RADIO_STREAM_ERROR`, never the saved cue. A listener-stopped capture is exempt: stopping two seconds in is a choice, not a fault. GATE-11 was held by extraction throughout: `recording_outcome.py` is new, `probe_capture_extension` moved to `recording_commands.py` (beside the probe command it runs and the parser it feeds), and `ui/radio/recording_markers.py` took the resume-marker helpers out of `main_frame_radio.py`.
- **A probe per service (3.0.0; `S:\radio-probes\`).** Quill Radio depends on eighteen services it does not control, and the historical way to learn one had moved was that something stopped working for somebody. Thirty-seven probes, each asserting something specific ("that station id came back with a playable address", not "the server answered"). Writing them found three real faults before release -- the Apple genre filter, the Radio Browser states endpoint, and a bulk endpoint whose answer changed with the fields requested -- two of which would have looked like "that feature just doesn't find anything".
- **YouTube metadata and playlists (2.2.0; upstream `core/radio/youtube.py`, `tools/network_egress_audit.py`).**
  - *The metadata was already being paid for.* `_default_resolver` called `extract_info` and kept four fields -- `stream_url`, `page_url`, `title`, `is_live` -- out of a response that also carried duration, the uploader's own chapter markers, subtitle and automatic-caption tracks, uploader, and description. All of it is now captured on the same request, so the cost is zero: no extra fetch, no extra latency. The parsing is split into pure functions (`stream_from_info`, `parse_chapters`, `pick_caption_track`, `playlist_entries_from_info`) so every field is testable against a fixture dict without touching YouTube; 22 tests do exactly that, and the pipeline was additionally verified end-to-end against a real 12-chapter video. Caption selection prefers a human-written track over an automatic one, accepts only *timed* formats (a plain-text dump carries no positions, making it useless for both seeking and the podcast chapter segmenter), and refuses a non-HTTPS URL. `duration_ms` is 0 for a live broadcast, which is not a failure but the honest answer: a broadcast has no timeline.
  - *Playlists, listed flat.* `resolve_youtube_playlist` uses `extract_flat="in_playlist"`, so a fifty-video playlist costs one request rather than fifty, and no entry's audio is resolved until that entry is played -- which then goes through the normal resolver with its re-resolve-on-every-play rule, because YouTube's stream addresses expire. A new reviewed egress site. A watch link carrying `&list=` is deliberately **not** treated as a playlist: the listener asked for that video, and silently expanding it into fifty stations would be a surprise, so only a genuine `/playlist` address expands.
  - *Deliberately not built: search and browse.* yt-dlp's `ytsearch:` works without a key and is against YouTube's Terms of Service; the sanctioned route is the Data API v3, which needs a key and carries a quota. Radio's other directories (RadioBrowser, SomaFM, Xiph) are open APIs built to be consumed this way -- YouTube is not, and the same rights posture that keeps the Live365 rewrite a pure string transform applies here. Decision 2026-08-12: no search branch; paste a link or a playlist. If it is revisited, it should be through the Data API with the listener's own client credentials, the shape Spotify already uses.
  - *A finished video is not a station -- delivered.* Seek, absolute position and 0.25-4x speed live in `ui/audio/mpv_engine.py`; `MpvRadioEngine` stubbed all three because live radio has no timeline. The obstacle was ordering, not capability: `_select_engine()` runs before `_resolve_playback_url()`, while live-versus-finished is only known after the resolve. The answer was **not** the engine swap first sketched here -- rebuilding the play path to choose an engine later would have meant restructuring the most sensitive code in the radio stack for a capability the engine could simply be *told about*. `MpvRadioEngine.set_bounded()` instead receives the fact immediately after the load (`_declare_source_shape`), inside the existing one-play-token discipline, and gates `seek`/`length_ms`/`set_rate` on it; everything that is not a resolved, finished video is untouched. On top of that: the uploader's chapters, `Play Faster/Slower/Normal`, `Where Am I?`, and `Go to Position...` (Ctrl+Shift+J), which reuses the Media Player's accessible H/M/S dialog rather than a second prompt. **The last gap closed was the transport keys themselves:** Rewind/Forward 30 Seconds still ran the live-DVR cache seek for a finished video and announced a distance behind a live edge that does not exist -- a fabricated measurement. `_radio_seek_bounded` now picks the operation the source deserves, which is also what finally reaches `bounded_playback_ui.skip_back`/`skip_forward` (written for exactly this, previously with no caller). No scrub *slider* was added: this is a keyboard-and-speech surface, and Go to Position plus the skip keys are the accessible form of the same capability.
- **Song History and one volume for every station (2.2.0; upstream `core/radio/song_history.py`, `ui/radio/song_history_dialog.py`, `ui/radio/song_history_commands.py`, `ui/radio/volume_commands.py`, `core/radio/favorites.py`, `core/commands.py`).**
  - *Song history (Playback > Song History, Ctrl+Shift+H).* `core/radio/song_history.py` is a wx-free, strict-typed per-station log recorded at `_radio_apply_track_title` -- the single choke point every route to a title (ICY, the engine, the station's status endpoint) already funnels through, and where the "this is a new song" signal already exists, so the thirty-second poll gains a memory without gaining a timer. Four rules keep the log readable and are directly unit-tested: a repeat of the song already at the front folds into that entry with a `play_count` rather than appearing six times per track; each station is capped independently (`MAX_PER_STATION`) so one station left playing all day cannot evict another's afternoon; stations are capped separately, least-recently-active dropped first; and titles that are the station's own name, "Live", or an advert marker are rejected as noise. Recording is wrapped so it can never raise -- it runs immediately before the What's Playing announcement, and anything thrown would silence it -- and both the enabled flag and Safe Mode are read through `getattr`, so a host predating the preference degrades to logging rather than crashing the announcement path. The dialog offers Copy, Send to Clip Library (via the existing `ClipLibrary`/`Fragment` API), and **Background**: one provider-neutral `ProviderChatBackend` call off the UI thread whose answer is always prefixed with `BACKGROUND_DISCLAIMER`, because model-written text sits inches from the station's own metadata in the same window. Refused in Safe Mode, and the prompt explicitly instructs the model to admit when it does not know the song. Persistence is classified `cache` in the persistence audit: an observed log with no default whose meaning could silently change. Off switch: `RadioHistory.song_history_enabled`.
  - *One volume for every station (Playback > Use One Volume for All Stations).* `RadioHistory.use_global_volume` (default off, so behaviour is unchanged until switched on) makes `volume_percent` the single level `_radio_resolve_volume` returns for every station, deliberately outranking a favorite's own remembered level -- which is the entire point, since that level winning outright is what left twenty favorites with twenty places to turn the volume down. `_radio_track_history_and_volume` stops writing a per-station copy while it is on, or it would quietly rebuild the very levels the setting bypasses. Per-station levels are **kept, never erased**, so switching back off restores them exactly; `forget_station_volumes` is the deliberate, confirm-first way to be rid of them and uses the new `RadioFavoritesStore.clear_volume` rather than `set_volume(-1)` -- the latter clamps to 0-100 and would set every station to *silent* instead of clearing it. Both behaviours are pinned by tests.
  - *Toggle state in the Command Palette (#1383).* The palette lists `Command.title` verbatim and has no checkmark, so "Announce Track Titles On/Off" read identically whichever way the switch was set. New `CommandRegistry.set_title` retitles a command in place (keeping handler, keybinding and feature id), and the track-title and global-volume toggles now carry "(currently On)"/"(currently Off)" and retitle themselves as they flip. The global-volume menu checkmark is synced the same way, since the palette and a rebound chord reach the handler without wx updating the item.
- **Since 2.2.0 (upstream `core/radio/youtube.py`, `core/radio/live365.py`, `core/radio/playlist_export.py`, `core/radio/bad_station_report.py`, `core/radio/directory_registry.py`, `core/radio/local_clock.py`, `ui/radio/youtube_playback.py`, `ui/radio/youtube_ui.py`, `ui/radio/playlist_export_ui.py`, `ui/radio/output_device_ui.py`, `core/radio/history.py`, `ui/radio/now_playing_commands.py`, `platform/windows/braille_output.py`, `core/announce/*`).** Two new station *kinds*, a volume that persists, and the announcement surface finally reaching braille.
  - *YouTube as a station kind (#1268).* A YouTube page URL (watch, `youtu.be`, `music.youtube.com`, `/live/`, `/shorts/`, `/embed/`) is accepted by Add Custom Station and stored **as the page URL**, never as a resolved media URL, because YouTube signs its media URLs with a few-hour expiry. `resolve_youtube_stream` re-resolves on **every** play and every recording start, which is what makes a scheduled recording survive to a later day; a resolved URL is never persisted. yt-dlp is the resolver and is **never bundled** -- it installs on demand after a one-time consent + rights notice recorded in `RadioHistory.youtube_consented`, deliberately gated at *add* time rather than play time so an unattended scheduled recording is never the first network reach. Resolution runs off the UI thread ("Connecting" first, no freeze) and a late result is discarded if the listener has since stopped or switched. Refused in Safe Mode; the single egress hand-off is in `_default_resolver` and is inventoried in the network-egress audit. The resolver is injectable, so tests never touch the network.
  - *Live365 link normalization.* `live365.normalize_live365_url` rewrites a station page (`live365.com/station/<slug>-<id>`), a player page (`player.live365.com/<id>`), a plain-http stream with a player-hint fragment, or a bare `a#####` id to the canonical `https://streaming.live365.com/<id>`. A **pure string transform**: the id is already present in every such link, so there is no network call, no scraping, no use of Live365's auth-gated directory API, and therefore nothing new to gate in Safe Mode or add to the egress audit. A bare slug with no id is left untouched (resolving it would require the auth-gated API, which is a deliberate non-goal), and a non-Live365 URL passes through byte-for-byte.
  - *SecureNet Cirrus player resolution (upstream `core/radio/securenet.py`).* SecureNet hosts the player for a large number of US broadcasters at `…securenetsystems.net/v5/<CALLSIGN>`. Unlike Triton, the real stream **is** a literal string in the page — and the scan still discarded it: the mount is a bare Icecast path (`https://ice66.securenetsystems.net/ROM`) with no extension and no `/stream`-style hint, indistinguishable by *shape* from an ordinary page link. Reported 2026-08-07 (Radio Once More returned two useless candidates; Radio Once More 2 returned none). `securenet.page_is_securenet_player` matches by host, or by an `ice<N>` mount in the body so a broadcaster embedding the player on their own domain still resolves; `stream_urls_from_page` strips per-visit `playSessionID` query strings, collapses duplicates, and skips the shared `/media` interstitial mount; `callsign_from_page` prefers the mount's casing over the pasted link's. The ice-server number is not derivable from the callsign (ROM is on `ice66`, WARL on `ice25`), so it is read, never computed, and a page carrying no mount reports nothing rather than guessing an address that will not play. `link_finder` offers these ahead of shape-matched candidates. `recovery._is_resolved_player_mount` additionally counts a lone `ice<N>` mount as an unambiguous heal — matching the existing StreamTheWorld rule — so a station saved from a player page self-repairs instead of stalling on "3 possible streams"; the match is deliberately on the `ice<N>` host and not the domain, since the player front-ends (`radio.`, `streamdb<N>web.`) share it and a player page links to itself. Parse-only: no network call of its own, so no new egress entry, and it works in Safe Mode.
  - *Volume persistence and focus-independent volume keys (#1263).* `RadioHistory.volume_percent` (-1 = unset) persists the last level the listener set; a favorite's own remembered level still takes precedence. The save is disk-only, so it no longer reloads the favorites tree or re-announces the station. Ctrl+Up/Ctrl+Down move from a menu accelerator (which Win32 does not deliver reliably outside the tree) into the frame char hook, so they fire from any focus except inside a text control, where Ctrl+arrow keeps its editing meaning.
  - *What's Playing commands always terminate with a result (#1282).* `radio.copy_whats_playing` and `radio.whats_playing_details` treated a missing title as "nothing is playing" (the normal state for the first seconds of a stream, for a refused ICY tap, and for every station with track announcements off), swallowed the async fallback's failure path, and mis-read `AppShellFrame._copy_to_clipboard`'s `None` return as failure where `MainFrame` returns a bool. All three are fixed: with a station on, both commands fetch first, then act; a title-less stream still opens a window naming the station; a failed fetch is reported; the copy confirmation names what it copied.
  - *Braille as a first-class announcement channel (#1283).* Announcements are routed to the braille display at the same choke point as speech (`platform/windows/braille_output.py` over Prism `Backend.braille()` and accessible_output2's JAWS `BrailleString` / NVDA `nvdaController_brailleMessage`). Three invariants: braille never costs speech (any failure degrades to spoke-not-brailled, never silence); nothing is truncated (both readers pan, and clipping would drop the end of a track title); an identical message inside 2 s does not re-flash. A burst coalescer in `ui/announce_wiring.py` writes the first message of a quiet period instantly and settles anything within the following 150 ms to the newest, with errors exempt. Preferences > Accessibility > **Show announcements in braille**. Quill Radio also adopts the shared announcement service, gaining `app.repeat_last_announcement` and `app.announcement_self_test` (registered on `AppShellFrame`, so no companion app can ship without them) plus its own sound cues.
  - *Export Favorites to Playlist (#1249).* `playlist_export.export_m3u` -- the wx-free writer counterpart to `playlist_import.parse_m3u` -- serializes favorites to extended M3U using each favorite's `display_label`, skipping entries with no stream URL, and round-trips through `parse_m3u`. M3U is flat, so folder structure is not represented (matching import's discard). Station-menu wiring in `ui/radio/playlist_export_ui.py`.
  - *Output Device quick picker (#1253).* Playback > **Output Device... (Ctrl+Shift+D)** over the existing `mpv_radio_engine` device enumeration and the same `history.output_device` persistence Preferences uses, so the two paths cannot drift. Kept in `ui/radio/output_device_ui.py` so `apps/radio.py` stays within its size budget.
  - *Report Bad Station (#1218).* `bad_station_report.build_bad_station_report` turns a `RadioStation` into a `(summary, body)` pair for the existing Report a Bug flow, offered from the station context menu in both `BrowseTreeDialog` and `StationBrowserDialog` and dispatched by `AppShellFrame.report_bad_station`. Motivated by directories hiding stations their own checker believes are dead (`hidebroken=true`), which leaves the listener the only party able to flag a station that plays for the directory and fails for them. The body carries station metadata only -- never identity or paths -- so it is safe to place on the clipboard or in a browser issue form. Pure and wx-free, so the wording is unit-tested.
  - *OS-live local clock for recording filenames (#1223).* `local_clock.local_now` reads Windows `GetLocalTime` instead of `datetime.now()`, whose local timezone the C runtime resolves once per process with no `tzset` on Windows to refresh it. A timezone change or DST rollover during a long-running session now shows up in new filenames without a restart; non-Windows and any failure fall back to `datetime.now()`.
  - *Quillin-contributed station directories.* `core/radio/directory_registry.py` is a process-wide registry of `radio.directory` providers populated by `QuillinAppHost` from enabled Quillin contributions and consulted by `directory_search.directory_provider_stations` during the Find Stations fan-out. A provider is a `(query) -> list[dict]` callable returning `{"name", "url", "source"}` rows from its own storage or a bundled list and makes **no network call of its own**, so the registry introduces no new egress site. Quillins are off in Safe Mode; third-party Quillins remain disabled.
  - *Scheduled-recordings list ordering (#1220).* The schedule list sorts by next occurrence rather than entry order, shows each entry's stream host in brackets to disambiguate near-identical rows, and moves focus to the added/saved entry while clearing the form, so the Add button no longer reads as "press me again to add another".
- **Distribution overhaul: the QuillVille Runtime, the native launcher, and light editions (2.2.0; `quill/native/launcher/*`, `quill/core/runtime_marker.py`, `quill/core/storage_mode.py`, `installer/shared-runtime.iss`, `installer/quill-radio.iss` (promoted 2026-07-24 from the validation-only `quill-radio-shared.iss`, since deleted), `scripts/build_native_launcher.py`, `standalone/radio/scripts/build_release.ps1`). The headline of how Quill Radio is delivered.**
  - *Shared runtime, install-once-per-user.* All four shipping QuillVille apps share one Python engine at `%LOCALAPPDATA%\QuillVille\Runtime\3.13\`, installed once and reference-counted at `%APPDATA%\Quill\runtime.state.json`; a second app starts instantly and the runtime is removed only when the last referencing app is uninstalled. See P-2.
  - *Native C launcher replaces the stamped `pythonw.exe`.* `QuillRadio.exe` is a tiny native process-spawn shim resolving the shared runtime (then a private embedded runtime, then legacy `pythonw.exe`) and `exec`-ing `-m quill.apps.radio`. Fixes the ACB-reported AV false positive by no longer producing the repackaged-Python shape; signtool-ready for when signing lands. See P-1.
  - *Two new light editions.* A ~3 MB **Companion** zip (app + docs on the shared runtime, first-launch runtime fetch) and a thin **"Lite" installer** join the ~311 MB full portable zip and the full shared-runtime installer. See P-3.
  - *Accessible runtime download (A-10).* The runtime fetch shows an NVDA/JAWS/Narrator-readable progress bar announcing percent, whether an installer or the app's own first launch triggers it. See P-4.
- **2.2.0 (upstream `quill/core/radio/backup.py`, `ui/radio/backup_ui.py`, `apps/radio.py`, `ui/main_frame_radio.py`, `core/radio/radio_browser.py`, `core/radio/wxindex.py`, `core/radio/favorites.py`, `ui/window_manager.py`, `ui/window_menu.py`, `ui/dialog_contract.py`, `ui/app_shell.py`, `ui/tray_hotkey.py`). Everything since 2.1.2; 2.2.0 was never shipped as a separate build.**
  - *Modeless multi-window model (menu-bar-loss root fix).* The heavy surfaces -- Browse Stations (`BrowseTreeDialog`), Search Stations (`StationBrowserDialog`), Manage Favorites (`FavoritesManagerDialog`), Schedule Recording (`ScheduleRecordingDialog`), and the Weather Center (`WeatherCenterDialog`) -- convert from `wx.Dialog` to modeless `wx.Frame`s, each carrying the shared menu bar, fixing the reported "menu bar disappears" defect (a `wx.Dialog` cannot host a menu bar) and removing the modal lock-out of the main window. A pure `WindowRegistry` (`ui/window_manager.py`) holds open order + numbering + cyclic next/previous (unit-tested, wx-free); the wx `WindowManager` (`ui/window_menu.py`) installs a dynamic **&Window** menu (numbered 1-9 in open order), the Ctrl+Tab / Ctrl+Shift+Tab / Ctrl+1..9 accelerators, and register-on-show / unregister-and-activate-previous on close, with "Entered ..."/"Exited ..." cues and primary-control focus via `dialog_contract.show_modeless_surface`. Each surface takes an optional `windows=` param: present (standalone Quill Radio) -> modeless frame; absent (embedded QUILL) -> the classic modal dialog, so one class serves both hosts. Design record: `docs/design/2026-07-20-radio-window-model.md`.
  - *Backup / restore (import & export).* `core/radio/backup.py` bundles the state files (favorites, history/settings, wake timer, recording schedule) and, on request, the recorded audio into a single SHA-manifested `.qrbackup` zip; `restore_backup` validates it, accepts only the known state filenames, is zip-slip-guarded, and reloads the running app. Station-menu UI in `ui/radio/backup_ui.py` (worker-threaded, native file dialogs). Directly serves R-3 device migration.
  - *Now Playing window on Ctrl+T (#1134 wiring).* Ctrl+T ("What's Playing?") now opens the reviewable `NowPlayingDialog` (arrow/copy the title+artist) instead of only speaking it; the window existed but had no menu item or key. Fetch-and-speak fallback when no title is cached.
  - *Per-favorite Station Details.* Favorites context menu -> Station Details... shows `RadioStation.details_text` in the same reviewable window the search results use.
  - *Radio Browser clarity + genre browse (#1194).* The Search source facet reads "Radio Browser" (two words) and the derived label is spelled the human way everywhere; a first-class "Radio Browser (by Genre)" node joins the Browse tree via `radio_browser.fetch_genres/genre_display/fetch_genre_stations` over the existing tag/search API.
  - *View menu.* A new top-level **View** menu (`apps/radio.py`) with two persisted visibility toggles. *Show Station Details* (`RadioHistory.show_station_details`, default on) shows/hides the read-only details pane in Browse and Search Stations, threaded to `BrowseTreeDialog`/`StationBrowserDialog` via a `show_details` param that `root.Hide`s the control (and its label) so a hidden pane is never a focus stop. *Show Status Bar* (`RadioHistory.show_status_bar`, default on) shows/hides the main-window status bar.
  - *Focusable status bar (A-6).* A self-contained `ui/radio/status_bar.py` (`RadioStatusBar`) builds an arrow-navigable status strip along the bottom of the main window -- cells for Now Playing, Volume (Volume Boost indicator), Recording, Sleep timer, Favorites count, and time. F6 enters it (a second F6 / Escape returns focus to the favorites tree), Left/Right/Home/End navigate, Enter/Space activates (reusing the existing `radio_*` actions and `_build_radio_status_bar_menu`), and each cell has a context menu. The bar refreshes on every `_refresh_statusbar`; `apps/radio.py` only wires it (build, View toggle, F6 char-hook branch), so the same bar can serve embedded QUILL radio later.
  - *More View items.* A Sort Favorites submenu (radio items over `RadioHistory.favorites_sort`), Expand All / Collapse All Folders on the favorites tree, and a Text Size submenu (Normal/Large/Larger) driving `RadioHistory.ui_font_scale` (clamped [1.0, 2.0]) applied to the tree, buttons, now-playing line, and status bar via `_apply_text_size` / `RadioStatusBar.set_font` (A-8).
  - *Favorites Manager Move buttons work from a sorted view.* Move Up/Down/Above/Below in `FavoritesManagerDialog` were disabled unless the folder was already manual; they now switch to manual on the first move (`_switch_to_manual_if_needed`, which flips the sort only) and move within the preserved stored order, mirroring the main list's Alt+Shift+Up/Down. The stored list is NOT baked to the sorted view -- doing so silently destroyed a hand-arranged order (#1186); the reload reveals the preserved order. The host persists the switch via `_radio_switch_favorites_to_manual` (new `on_switch_to_manual` callback).
  - *Keep-awake while playing/recording (A-9).* `platform/keep_awake.set_keep_awake` (Windows `SetThreadExecutionState`, `ES_CONTINUOUS | ES_SYSTEM_REQUIRED`; no-op elsewhere) holds off system standby while a station plays or a recording runs, released when neither is active. `_update_sleep_inhibitor` reads live playback + recorder state and `RadioHistory.prevent_sleep` (default on; Preferences checkbox) on every state change. Display sleep is deliberately not inhibited.
  - *Global show/hide-to-tray hotkey.* A system-wide hotkey toggles the main window between shown and hidden-to-tray from any application, even when Quill Radio does not have focus, over the same Windows `RegisterHotKey` path the hardware media keys already use. `app_shell._register_tray_hotkey` claims the chord on show and `app_shell.toggle_window_to_tray` hides the window (announcing "hidden to the tray", playback/recording left running) or restores-and-focuses it (announcing "shown"); the wx-free chord parser is shared in `ui/tray_hotkey.py`, and `apps/radio.py` supplies Quill Radio's chord. Registration is best-effort: a chord another app already owns is left to that app and skipped silently (no error, no crash), so the tray icon and the "Alt+F4 minimizes to the system tray" preference remain the reliable show/hide fallbacks. Each family app registers a distinct chord so they never collide -- Quill Radio **Ctrl+Alt+Shift+R**, QUILL Ctrl+Alt+Shift+Q, Quill Weather Ctrl+Alt+Shift+W. Windows-only (no-op elsewhere).
  - *The QuillVille menu (`core/app_launcher.py`, `ui/quillville_menu.py`).* A top-level **QuillVille** menu (Alt+Q) carried identically by Quill Radio, QUILL, and Quill Weather, listing every family member so cross-app navigation lives in one predictable place in every app. Functional menus keep descriptive names a screen reader can find by first letter (the Weather menu stays "Weather"); QuillVille is the family-navigation menu, which is what a brand name should label. The launcher runs a sibling's own exe in a frozen build or `python -m quill.apps.<app>` from source; because every app is single-instance, launching one already running brings it forward. Quill Radio's Weather menu also offers **Open the Quill Weather App**.
  - *Customize Features (`core/app_features.py`, `ui/app_features_dialog.py`).* **View > Customize Features...** lists the app's switchable areas -- Quill Radio's **Recording** and **Weather** menus -- each with a description; unchecking one omits the whole menu and every command beneath it on the next launch (`_app_area_enabled` guards the menu-bar build). Shared model and dialog reused by Quill Weather, defaulting every area on so a newly-added area is enabled until turned off. The tray menu also gains Play/Pause, Stop, and the sibling-app launchers.
  - *Start Quill Radio with Windows (`platform/windows/radio_startup.py`).* A Station-menu check item adding/removing a per-user autostart entry -- the same no-elevation mechanism QUILL uses. Pairs with Resume Last Station on Launch for a sign-in appliance.
  - *Weather Guardian and the weather suite in Quill Radio (`core/weather/monitor.py`, `core/weather/astronomy.py`, `platform/alert_sound.py`, `ui/main_frame_weather.py`).* Background NWS alert monitoring (Ctrl+Shift+M) speaking each newly-issued alert, with forced interrupting speech at Urgent and above, tray toasts, tray-resident operation, auto-resume on launch, a severe-weather poll mode down to the NWS 30-second courtesy floor, and Pause/Resume distinct from Stop; a configurable alert sounder (off / custom `.wav` / 1-10 repeats, with a Play preview) and a **Test Alert** that exercises the whole path without touching the network or the monitor's real state; plus an hourly forecast pane, a locally-computed moon almanac (phase, illumination, moonrise/moonset -- no extra network call), and the location's own local time leading Weather Now and Quick Weather. The full design of record now lives in the Quill Weather PRD (§9).
  - *Destructive confirmations default to No.* Remove Favorite, Delete Folder, Remove Recording, Remove All Favorites, and Reset Sound Enhancements move to `wx.YES_NO | wx.NO_DEFAULT`, so Enter is always the safe answer. `quill/tools/dialog_button_contract.py` fails the build on a new destructive Yes-default.
  - *Fixes.* A global key hook could fire before (or after) the surfaces it inspected existed, raising `AttributeError` most visibly while starting Quill Radio, which has no editor; all three surface checks are `getattr`-guarded with a regression test (#1203). Alt+Shift+Up/Down reorder from a sorted view switches to manual and preserves the stored order (it does NOT bake the visible order over it -- baking silently destroyed a hand-arranged list, #1186; the reload reveals the preserved order and the move happens within it); explicit Exit (menu/tray) quits for real instead of bouncing to the tray under minimize-on-close (#1193); keyboard focus lands inside the window after show so Alt reaches the menu bar on launch (#1193); NOAA state folders count from the same directory tier the leaves come from, so "(N items)" always matches what expanding shows (`wxindex.states_with_playable_feeds`). A later feedback round also fixed: the transport button dropped its colliding Alt+S/Alt+P mnemonic so Ctrl+P is the reliable Stop/Play key (#1208); New Folder Ctrl+Shift+E handled in the app char hook so it fires from the favorites tree (#1211); Add to Favorites for TuneIn resolves the stream on demand (#1210); adding a custom station refreshes the favorites tree immediately (#1205); a **Remove All** favorites action with confirmation + rolling-backup recovery (`RadioFavoritesStore.clear`, `remove_all_favorites`, #1201); the Browse directory cache is bypassed when the bundled snapshot is newer so an in-place update surfaces new listings (`wxindex._directory_stations`, #1207); and the mpv engine is hard-terminated on exit so audio never outlives the app (`MpvRadioEngine.terminate`, #1195). Two more feature requests: Schedule Recording takes duration as hours (0-24) + minutes (0-59) instead of a single minutes box, computed to the unchanged `duration_minutes` total with a `< 1` guard in `build_schedule_entry` (#1213); and a `wx.Slider` **Volume** control sits in the main-window Tab order (arrow-adjustable), wired to `RadioPlayerController.set_volume` and kept in step with Ctrl+Up/Down and per-station memory via `_sync_volume_slider` in `_refresh_statusbar` (#1214).
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
- **A play queue for the Recordings list (2.2.0; upstream `core/radio/play_queue.py`, `ui/radio/recordings_queue.py`).** `winamp_keys.py` deliberately left `R` (shuffle), `S` (repeat) and `Ctrl+V` (stop after current) unbound, because all three describe a play queue the recordings list did not have and a key that only appears to work is worse than one that is not offered. `PlayQueue` is that queue: wx-free, strict-typed, and normative on three points. **Shuffle is a fixed permutation, regenerated only when the set of rows changes** -- "random next" would replay items before others had played at all and, decisively for this audience, would leave `Z` unable to return to what was just heard; the list also refreshes on a two-second timer, so `set_rows_if_changed` compares as a *set* to stop the order being reshuffled underneath the listener. **Repeat-one applies to a natural end, not to Next**, or Next reads as broken. **Stop-after-current outranks repeat, clears itself when it fires, and is not persisted** -- a one-shot surviving a restart would halt playback for a reason nobody could remember requesting. Shuffle and repeat persist on `RadioHistory` (`recordings_shuffle`, `recordings_repeat`, normalized on load so a mode from a later build cannot strand the queue). Auto-advance is driven from the dialog's existing refresh timer rather than the controller's single `on_state_changed`, which belongs to the app frame and which a modal dialog would have to hand back on every exit path, including the exceptional ones.
- **Recordings reliability overhaul (2.0.0, upstream `quill/core/radio/*`; R1-R4).** The headline of 2.0.0: a reported round of recording bugs closed and the one missing piece added -- a recording that survives a restart. Resume across restart with an ask-on-launch dialog and a 10-minute grace window; window-based scheduling with launch catch-up; a flicker-free, place-keeping Recordings list with honest counts and a live elapsed time; and pipeline hardening against dropped connections, dead streams, and a crashed host. Detailed as delivered scope in §3 (Recording). Everything lands in the shared `quill` package; nothing is vendored into the wrapper.
- **iHeart and TuneIn directories + Unified Find Stations (2.0.0, upstream `core/radio/iheart.py`, `core/radio/tunein.py`, `core/radio/directory_search.py`; #1116, #1117, #1132).** Two of the largest internet-radio directories added as keyless, account-free station sources blended into Browse Stations, with a Source facet, genre/country dropdown filters, "via <source>" result labels, a Refresh button for the cached iHeart index, and iHeart/TuneIn page resolution in Find Streams. Detailed as delivered scope in §3 (Listening). Reverses the earlier TuneIn non-goal (upstream QUILL PRD §5.84f), approved 2026-07-17.
- **Schedule management (2.0.0, upstream `ui/radio/schedule_recording_dialog.py`, #1106).** Edit, Duplicate, and Enable/disable for schedule entries; 12-or-24-hour time entry; per-entry time zones with zone-labeled list times. Detailed in §3 (Recording).
- **What's Playing server status-endpoint fallback (2.0.0, upstream `core/radio/station_status.py`, #1111, #1112).** A same-host last resort reading the stream server's own Icecast/SHOUTcast now-playing status page when ICY and the engine title channel are both empty. Detailed in §3 (Listening).
- **Diagnostics (2.0.0, upstream `core/radio/radio_logging.py`; #1130, #1124, #1122).** A live Verbose logging (debug-mode) checkbox and a settable Log folder in Preferences, with recording stderr captured to the log. Detailed in §3 (Shell).
- **The mpv playback engine (1.1.0, upstream `quill/ui/radio/mpv_radio_engine.py` + `player_controller.py`, #1076).** A second, preferred audio backend: libmpv, live-stream-aware (readiness from `core-idle`, not the duration a live stream never reports), bundled at `{app}\tools\mpv`. `RadioHistory.playback_engine` = auto (mpv when present) / wx ("Windows Media (classic)", the byte-for-byte pre-1.1 escape hatch) / mpv; one silent cross-engine rescue per play attempt in either direction. Combined stream-format coverage is effectively complete: MP3, AAC and HE-AAC (AAC+), Ogg Vorbis, Opus, FLAC streams, and HLS (m3u8) -- Ogg Vorbis/Opus/HLS were undecodable by WMP. The engine delivers: **Radio output device** (Preferences; `RadioHistory.output_device`; screen reader and app sounds stay on the system default; unplugged devices remembered, spoken fallback when unusable); **live DVR** (a seekable ~45-minute demuxer cache: pause/resume live radio, Rewind/Forward 30 Seconds, Back to Live, each announcing how far behind live); **Volume Boost** (up to 150% for quiet stations; the 0-100 scale, per-station volumes, and mute untouched); **engine-native What's Playing fallback** (mpv `media-title` when the ICY side-tap gets nothing or the stream is HLS); and **"Buffering..." announcements** on mid-stream stalls.
- **OptiLab broadcast polish (2.0.2, upstream `core/audio_enhance.py`, `ui/sound_enhance_dialog.py`).** One-touch broadcast-processing modes in Sound Enhancements, adapted from OptiLab Core by Lanes Audio / dgl1984 (github.com/dgl1984/optilab; Apache-2.0 with the Commons Clause from upstream v1.3.0). **Correction (2026-08-13):** this entry originally justified the adaptation by calling OptiLab "a GUI-only plugin with no library API and a Windows-64-only binary". All three claims were false -- upstream's native/API.md documents `optilab-core`, a framework-independent C++17 static library shipped since v1.2.0, and only the CLAP and Winamp *wrapper* targets are platform-gated. The adaptation below is still what ships for the built-in chain, and it is a reasonable design (it needs no native component and previews live), but it was never the only option available. See the exact-processing entry that follows. The modes reproduce the *shape* of its three chains -- Podcast Leveler (HPF -> speechnorm -> acompressor -> 65 Hz tame -> alimiter), Stream Polish (dynaudnorm -> acompressor -> presence -> alimiter), Smooth Limiter (acompressor -> alimiter) -- as ffmpeg filter chains appended last in `build_filter_graph` (their lookahead limiter guards the output), so they ride the same three delivery paths (mpv-native live, relay, recordings) and work cross-platform. Controls map OptiLab's onto ffmpeg: Mode picks the chain, Input is a front-end `volume` trim (0 dB default, per product choice), Auto-Adapt (0-100%) leans the leveling/density more assertive. A bypass checkbox (`optilab_enabled`) keeps the chosen mode remembered while off. Stored on `RadioHistory` and, as of 2.0.2, also per-station on `FavoriteStation`, carried by `RadioPlayerController.set_sound_options`/`preview_enhancements` and resolved per stream by `ResolvedEnhancement`. A faithful adaptation, not a bit-for-bit port; credited in release notes, the About box, and the third-party notices.
- **Exact OptiLab processing (2026-08-13; `quill/native/optilab/`, `quill/core/audio/exact_optilab.py`, `quill/core/optilab_adapter.py`, `scripts/build_native_optilab.py`).** The three broadcast-polish modes above are a faithful *adaptation* of **OptiLab Core by Lanes Audio / dgl1984**, rebuilt as ffmpeg filter chains. The engine itself is now vendored unmodified at v1.4.0 under `quill/native/optilab/upstream/` (with its LICENSE and NOTICE) and linked into an adapter QUILL owns -- upstream is explicit that its C++ API is "not a stable C ABI" and that consumers should "wrap this C++ class in a small adapter owned by your project", so QUILL does, and that adapter contains no DSP. It is a **process**, not a Python extension, for the same reason ffmpeg is: the offline audio paths already drive an external program through `safe_subprocess` with an argv list and never a shell. **One setting, three states** (`RadioHistory.optilab_exact` / `optilab_exact_live`, per-station overridable, both off by default): off, saved files, or saved files and live. **Saved files** (`RadioRecorder` post-pass and `core/audio/convert.py`) are the recommended state -- a finished recording is processed *after* it finishes and after any dropped-and-resumed parts are joined, writing a temp file that replaces the original only on success, so no failure mode can cost somebody a recording; a raw capture is never post-processed, because re-encoding it is precisely what raw capture exists to avoid. **Live** routes the stream through `EnhanceRelay`'s three-process form (decode | engine | encode | loopback URL) on *both* engines, mpv included, and clears mpv's native filter graph so the audio is never processed twice. It is opt-in because it costs what the mpv-native path exists to provide: a slower start, an MP3 re-encode generation, more CPU, and a reconnect on every settings change (the engine is prepared with a mode and a sample rate at start-up and cannot be re-parameterised mid-stream). The rejected alternatives are recorded in `quill/native/optilab/README.md`: a custom libavfilter, an in-process extension over an ABI upstream does not offer, and an mpv CLAP host (mpv has none). Whichever state is chosen, the OptiLab *filters* leave the graph whenever the real engine will run. Honest differences, stated rather than implied: the chain has none of upstream's gated AGC, six-band density, adaptive bass and top control, stereo processing or hybrid final stage; its Podcast and Limiter ceilings are -1.5 and -2.0 dBFS where upstream delivers to -0.1; its Input default is 0 dB where upstream's `inputDriveDb` is 3.5; and the limiter feedback loop (easing the lift while final limiting runs heavy) cannot be expressed in a feed-forward graph at all -- which is the one difference that can be claimed with confidence. Entirely optional: with no adapter built `available()` is False, every surface says why in words, and every caller stays on the chain. Licence **Apache-2.0 with the Commons Clause v1.0**; upstream's NOTICE separately grants royalty-free commercial use of OptiLab Core as a tool for processing or broadcasting audio, and both LICENSE and NOTICE ship beside the executable in the installer and the portable bundle.
- **Live Sound Enhancements preview + fully per-station (2.0.2, upstream `ui/sound_enhance_dialog.py`, `ui/radio/player_controller.py`).** Every control in the Sound Enhancements dialog previews live on the playing stream via an `on_live_change` callback (debounced ~180 ms) into `RadioPlayerController.preview_enhancements` (one apply for the whole set, so a wx drag reconnects once, not per field; mpv applies natively). OK keeps; Cancel/Escape reverts to the snapshot captured on open (the Reset button's own restore is exempted). And all listener-level settings -- previously EQ/compressor/channel per-station but night mode + OptiLab global-only -- are now per-station as well as global: `FavoriteStation` gained `night_mode_enabled`/`optilab_*`, `set_enhancement` and the `ResolvedEnhancement` NamedTuple carry the full set, `play_station` applies all of it per stream, and `open_sound_enhancements` saves the whole dialog to the favorite override (when a favorite plays) or the shared `RadioHistory` default (otherwise). Reset to Default and Reset All Stations both restore the shared default including night mode and OptiLab.
- **Sound Enhancements** (Playback > Sound Enhancements...): a three-band equalizer (Bass/Mid/Treble sliders, -12 to +12 dB) and a compressor, applied live via an ffmpeg filter graph relayed to the playback engine over a loopback-only local HTTP server -- or, on the mpv engine (1.1.0), natively inside the player with no relay and with changes heard live, no reconnect. Off by default. 1.1.0 adds two listener-level (deliberately global, not per-station) options riding the same shared graph everywhere including recordings: **mono downmix** (single-sided hearing / one earbud -- hard-panned content never disappears) and **night mode** (real-time loudness normalization lifting quiet passages), plus the Small Speakers and Late Night quick presets. A "Quick preset" shortcut sets all three sliders at once. Remembered per favorite station (a whole-record override on `FavoriteStation`, mirroring QUILL Cast's per-podcast override) as well as a shared default in `RadioHistory`; `RadioPlayerController` resolves which applies via an injected callback at the top of every `play_station`. Recording Settings' "Apply Sound Enhancements to recordings" (off by default) optionally records the filtered audio too.
- **SomaFM**, a second free, keyless station directory, blended into Browse Stations search alongside RadioBrowser.
- **Exit/Minimize to Tray confirmation**: closing the window asks Exit, Minimize to Tray, or Cancel (with a one-time "Don't ask me again"), instead of always exiting immediately and silently stopping an in-progress recording. Adjustable in Preferences.
- **Quieter dialogs and a real "up to date" answer**: dialog-transition announcements are now off by default (Preferences), and a manual Check for Updates that finds nothing newer shows a dialog instead of only announcing it.
- **In-app documentation**: Help > User Guide / Release Notes / Product Requirements open the bundled docs in your browser.

See `CHANGELOG.md` for the full, versioned history.

## 9. Weather -- now its own product

The weather feature set (Weather Center, Weather Guardian alert monitoring, the
alert model, voice/speech plans, and the roadmap) has its own home now that
Quill Weather is a standalone app: see **`../../weather/docs/prd.md`**.

Weather remains available inside Quill Radio via the **Weather** menu when the
Weather feature is enabled (View > Customize Features...), and that menu offers
**Open the Quill Weather App** to hand off to the standalone watcher. The two are
separate, independently-distributed apps that run side by side.

## 10. Spotify integration (experimental)

Quill Radio (music) and QUILL Cast (podcasts) can play directly from Spotify. The
capability is **experimental and ships in the app**. It is gated behind the
`future.spotify` feature flag in `quill/core/feature_catalog.py` -- no longer
`locked_off`, and no longer behind an unlock code, since that mechanism was
withdrawn. The flag remains so a listener who does not want Spotify can switch it
off in Manage Individual Features and have its menu items disappear. Nothing
reaches Spotify's servers until an account is deliberately connected, behind a
one-time network-access consent, and the whole feature is refused in Safe Mode.
This section is the design of record and the honest statement of what is left
before general availability. As with every radio feature (R-1), all
of it lives in the shared `quill` package -- `quill/core/spotify/*` and
`quill/ui/spotify/*` -- and nothing is vendored into this wrapper.

### 10.1 Design

- **Sign-in: OAuth 2.0 Authorization Code with PKCE, no client secret**
  (`quill/core/spotify/auth.py`). A desktop app cannot keep a secret, so QUILL
  generates a high-entropy `code_verifier`, sends only its SHA-256 challenge to
  `accounts.spotify.com/authorize`, and proves possession of the verifier when it
  redeems the code at `accounts.spotify.com/api/token`. A random `state` guards
  against a cross-site redirect. The two token exchanges (code redemption and
  refresh) funnel through the single reviewed egress site `auth._token_request`.
- **Loopback redirect receiver** (`quill/core/spotify/auth_callback.py`). PKCE's
  redirect lands in the user's browser at a loopback address, so QUILL runs a
  one-shot local HTTP server that binds `http://127.0.0.1:43217/callback` *before*
  the browser opens (so the port is held when Spotify redirects back), validates
  the echoed `state`, reads the authorization `code`, and stops. It only receives
  a connection from the local browser -- no outbound egress of its own. The fixed
  port is what the user registers as the redirect URI on their Spotify app.
- **Web API wrapper** (`quill/core/spotify/client.py`). Search, the signed-in
  profile, saved shows/episodes/tracks, and playlists -- the Radio/Cast browse
  surfaces -- all go through the single reviewed egress site `client._request`:
  HTTPS-only to `api.spotify.com` over a verified TLS context, Bearer token in the
  header (never the URL), with lazy, lock-guarded token refresh.
- **Playback: a WebView Web Playback SDK engine coexisting with mpv/wx behind the
  AudioEngine protocol** (`quill/ui/spotify/web_player.py`, `SpotifyWebEngine`).
  Spotify Premium audio is DRM-protected and only Spotify's own Web Playback SDK
  may play it, inside a browser. QUILL hosts that SDK in a hidden
  `wx.html2.WebView` (Edge/WebView2 on Windows) and drives it through the same
  method surface (`play`/`pause`/`stop`/`seek`/`set_volume`/`is_playing`/
  `position_ms`/`length_ms`/`close`) the mpv and Windows Media engines expose, so
  a controller treats a `spotify:` URI like any other source. The engine and its
  page are cleanly split so the state machine is unit-tested with synthetic
  messages -- no browser, no network, no account. There is deliberately **no**
  cross-engine fallback for a `spotify:` URI: only this engine can play one.
- **Engine routing** (`quill/ui/radio/player_controller.py`,
  `quill/ui/podcasts/player_controller.py`). A `spotify:` station or
  `spotify:episode:` is detected up front and routed to the Web Playback engine,
  created lazily on first use; the normal cross-engine rescue never applies to it.
  Playback snapshots from the SDK are reflected into the shared playback state, so
  the status-bar mini-player, the tray, and the per-command Global Hotkeys behave
  exactly as for a normal station or episode. Leaving Spotify closes the hidden
  WebView and returns to the stream engines; shutdown tears the WebView down.
- **Token vault and Client ID** (`quill/core/spotify/token_store.py`,
  `session.py`). The access/refresh tokens and the user's Client ID live only in
  the OS credential vault (the same unified store the AI keys use), never in a
  plain file or log. `SpotifySession` hands the Web Playback engine a currently
  valid access token, refreshing transparently a minute before expiry.
- **Consent, feature flag, Safe Mode, and egress gating**
  (`quill/core/spotify/consent.py`). Because connecting reaches Spotify's servers,
  sign-in is gated on a one-time network-access consent flag *in addition to* the
  `future.spotify` flag and Safe-Mode refusal. Every egress site is inventoried in
  `quill/tools/network_egress_audit.py`: `accounts.spotify.com` and
  `api.spotify.com` for sign-in and the Web API, plus the SDK's own in-WebView
  traffic to `sdk.scdn.co`, `open.spotify.com`, and Spotify's DRM CDN, which the
  AST egress scanner cannot see and which is therefore documented manually there.

### 10.2 Enablement checklist

Playing from Spotify requires all three of the following. Missing any one means
playback never starts.

| Requirement | Detail |
| --- | --- |
| Spotify Premium account | The Web Playback SDK only streams audio for Premium; the requested scopes (`streaming`, `user-read-email`, `user-read-private`) are Premium-only. A free account can browse but not play. |
| User-supplied Spotify Client ID | Registered at the Spotify Developer Dashboard, with the redirect URI set to exactly `http://127.0.0.1:43217/callback`. No client secret -- PKCE. |
| Windows with the Edge WebView2 runtime | The only sanctioned playback path is the WebView-hosted SDK; QUILL already warms WebView2 at startup. |

Whenever the feature is on and the app is out of Safe Mode, the standalone frames
(`quill/apps/radio.py`, `quill/apps/podcasts.py`) add **Connect to Spotify...**
and **Browse Spotify...** (Radio) / **Browse Spotify Podcasts...** (Cast) to the
Help menu; the accessible dialogs are `quill/ui/spotify/connect_dialog.py` and
`quill/ui/spotify/browse_dialog.py`.

### 10.3 What remains before general availability

The offline-testable core and the wx state machine are done and unit-tested, but
the following cannot be exercised without a real Premium account and Client ID and
are explicitly open:

- **End-to-end verification with a real Premium account + Client ID.** The browser
  OAuth round-trip, actual SDK audio playback, the in-WebView token-refresh
  handshake, and Spotify Connect device transfer are not exercisable offline and
  have not been run against live Spotify.
- **A product decision on the Client ID model.** Whether to ship a public/bundled
  Client ID or keep the current bring-your-own-Client-ID approach is unresolved.
- **Wiring the RSS-match action to a button.** The best-effort "find a downloadable
  public version of this Spotify episode via an RSS match" capability exists in the
  core (`quill/core/spotify/rss_match.py`, `find_public_enclosure`), but it is not
  yet surfaced as a menu item or button in QUILL Cast. It reuses the existing
  reviewed podcast-directory and feed-reader egress sites (it adds no new egress),
  is Safe-Mode-guarded, and only ever returns the publisher's own public
  enclosure -- never Spotify audio.

## 11. The Station Catalog - PRD and strategic plan (merged)

Formerly `docs/station-catalog.md` (and before that the repo-root `ideas.md`); merged here 2026-08-15 so the radio
PRD is one document. Internal section numbers (2b, 5.5, 6.5...) are
preserved because code comments, changelogs and tests cite them.

Status: plan of record, and as of 2026-08-15 **largely built** - Phases 1-3
shipped together as the station-catalog feature branch (see the Delivery
log at the end). Owner: Jeff. This document graduated here from a root
working note the same day.

One sentence: Quill Radio ships the station directories inside the app as a
fast local catalog, keeps that catalog current from live data automatically and
on demand, lets the listener turn every automatic behavior off, and never -
under any circumstance - touches a station the listener added or saved.

---

### 1. Why this, and why now

Browsing today is lazy: every branch of Browse Stations fetches from its
source when expanded, softened by `directory_cache` (fresh -> live -> stale).
That design shipped 3.0.0 well, but it has three costs the listener feels:

- **First expansion waits on the network.** "By Country" on a slow connection
  is a spinner, and on no connection it is an apology.
- **The app's completeness depends on someone else's uptime.** A directory
  outage makes Quill Radio look broken, even though nothing local changed.
- **Search can only be as fast as the slowest source it asks.**

The fix is not more caching of the same shape. It is inverting the default:
**the local catalog is the source of truth for browsing; the network is the
source of truth for freshness.** The app reads locally in milliseconds and
reconciles with live data in the background - a shape this codebase already
proved twice, in miniature: the NOAA `wxindex` bundled snapshot with a refresh
tier, and the Radio Reading Services directory with its manual update command.
This plan makes that the architecture for every source that permits it.

### 2. What exists today (grounded inventory)

Read before designing anything; all of this is on main.

- `quill/core/radio/browse_sources.py` - one `browse(node_id)` contract, 28
  root branches, per-source handlers, wx-free and tested without UI.
- `quill/core/radio/directory_cache.py` - fresh -> live -> stale tiers; a
  failed refresh keeps what was there; cached answers report their age.
- `wxindex` - bundled NOAA snapshot + refreshed cache: the seed precedent.
- Reading services - bundled list + "Update Radio Reading Services..." menu
  command: the manual-refresh precedent.
- Bundled already: networks catalog, ACB Media, NFB Radio, community M3U.
- Live-only today: Radio Browser axes, iHeart, TuneIn tree, Xiph, SomaFM,
  Apple Podcasts, the libraries (Archive/LibriVox/Gutenberg), free music.
- User-owned stores, each its own file with atomic writes: favorites
  (`radio_favorites.json`, with timestamped backups under
  `backups/radio-favorites/`), My Servers, YouTube channels, schedule.
- `core/radio/radiodns.py` + the approved `dnspython` dependency - identity
  enrichment hook, currently underused.
- House rules that constrain the design: wx-free strict-typed core; all JSON
  via `write_json_atomic`; every egress site in the network audit; Safe Mode
  refuses network per branch; browse-visibility rule ("a source that is off is
  never contacted"); GATE-11 module budgets; GATE-EC coded errors.

### 2b. Phase 0 findings - measured, 2026-08-15

Phase 0 ran early: the real exports were pulled once and the store was
prototyped against them (`local/catalog-proto/`). Numbers below are from this
machine; every design amendment they forced is applied in the sections that
follow.

#### The data

- Radio Browser full working-station dump: **62,377 stations, 77.7 MB raw
  JSON**, fetched in 25 s across 7 paginated requests (`hidebroken=true`,
  10k per page, 0.5 s politeness gaps). `/json/stations` without pagination
  silently caps at 1,000 rows - paging is mandatory, not optional.
- `stationuuid` coverage: **100 percent**. Key rule 1 covers the entire
  source.
- **7,135 normalized stream URLs are shared by more than one station**
  (18,007 rows) *within Radio Browser alone* - relays, network feeds, and
  multi-listed streams. A same-URL merge rule would wrongly collapse
  thousands of real stations. Merge policy amended below.
- **The Xiph directory is serving empty data right now**: `yp.xml` returns a
  bare empty directory element and the beta `/genres` page is a 3 KB shell
  with no genre links. Not a parser bug - the source itself is empty today.
  Two consequences: Xiph cannot seed until it recovers, and the refresh
  engine gains a rule it was always going to need - **a full fetch that
  returns zero rows for a source that previously had thousands is an outage,
  never truth**; the catalog keeps what it has and marks the source stale.
- SomaFM channels.json: 51 KB. Trivial.
- **iHeart terms read (Terms of Use, last updated 2025-03-12): bulk caching
  is off the table.** Section 23 prohibits, verbatim, "reproduce, download,
  license, publish, **enter into a database**, display, modify, create
  derivative works from, transmit, post, **distribute**" - and a seeded
  catalog shipped in the installer is precisely "enter into a database" plus
  "distribute". Section 5 separately bars obtaining material "through any
  means not intentionally made available", and Section 14 grants only a
  "limited, revocable, license... for your private, non-commercial use".
  Decision: **iHeart is Class B permanently, by policy, not by gap** -
  live-drill browsing with the existing short-lived `directory_cache`, same
  posture 3.0.0 already ships. It is never seeded, never persisted into the
  catalog database, and - a rule this reading forced - **Layer 4
  write-through applies to Class A sources only**, so an iHeart row fetched
  live is never upserted into the catalog either. A transient session cache
  for the listener's own browsing is a materially different act from
  redistributing listings in a shipped database, and the design now keeps
  that line bright.

#### Apple Podcasts (iTunes) - why it is not measured for seeding

Asked and answered rather than silently skipped. The Podcasts (Apple) branch
rides the iTunes/Apple Marketing endpoints (`apple_podcasts.py`: genre tree,
per-storefront charts, show lookup), and it is deliberately **not** a seeding
candidate, for three reasons that stack:

- **It is a content catalog, not a station directory.** The unit is a show
  that resolves to its own RSS feed; the full corpus is millions of feeds
  and unbundleable by nature. What the app actually browses - charts and
  genre lists per storefront - is a ranking, and a shipped ranking is stale
  by definition (the same reasoning that keeps Radio Browser's
  popular/trending live-first).
- **Terms.** Apple's marketing/search API posture permits client lookup and
  search with short-lived caching, not entering listings into a
  redistributed database - the same line the iHeart reading drew, applied
  consistently: Class B, session cache only, never written through.
- **It is already fast enough live**, measured today: the full genre tree in
  0.8 s, a 100-show storefront chart in 1.7 s, both behind
  `directory_cache`. There is no user-felt problem for the catalog to solve
  here.

So Apple stays exactly where Section 4 puts it: Class B, live-drill, with the
existing honest empty-state when unreachable.

#### The complete source sweep - every source, measured 2026-08-15

Every source in the app was exercised live, not just the seeding candidates.
Counts are what one fetch returns through our own modules unless noted.

| Source | Measured | Bulk feasible? | Class | Note |
| --- | --- | --- | --- | --- |
| Radio Browser | 62,377 stations, 77.7 MB raw | Yes (paginated) | A | The seed's backbone |
| SomaFM | 46 channels, 51 KB | Yes | A | Trivial |
| Xiph | 0 today; ~500 genres on Aug 13-14 | Yes when up | A | Flapping - ruling below |
| NOAA wxindex | 40 states with feeds | Already bundled | A | Existing snapshot joins the store |
| Community M3U | 95 genres (~1,900 stations in first 5) | Already bundled | A | |
| Networks / ACB / NFB / Reading | 6 groups / 10 / 1 / 21 | Already bundled | A | Curated, highest trust |
| iHeart | 18 genres, 317 markets | Barred by terms | B | Section 2b terms reading |
| TuneIn | 7 root categories | Barred by policy | B | Remote drill tree |
| Apple Podcasts | 19 genres in 0.8 s; 100-show chart in 1.7 s | Barred by terms; rankings anyway | B | |
| Internet Archive | oldtimeradio 8,853; librivoxaudio 21,747; 78rpm 310,899; netlabels 80,423; audio_music 522,283 items | No - millions of items | B | Numbers close the question |
| LibriVox | ~22-24k books total; limit=1000 paging works (1,000 books = 1.31 MB, 1.9 s; API 404s past the end) | **Yes** (~30 MB raw, est. 3-4 MB compressed) | B today, **A2 candidate** | Public-domain data; see below |
| Project Gutenberg audio | **1,124 records total** (gutendex count, audio/mpeg) | **Yes** (one fetch) | B today, **A2 candidate** | Tiny |
| Wikidata axes | 400 stations per axis in 2.1 s | Yes (CC0) | B | Small derived joins; cache suffices |
| Audius / Mixcloud / ccMixter | 59 trending / 38 categories / 16 tags | Rankings and charts | B | Stale by definition if seeded |

**Class A2 - the library seed - is ADOPTED (2026-08-15), not parked.** The
directive is to cache everything legally allowed, and LibriVox (~22-24k
public-domain books, cleanly pageable) and Gutenberg audio (1,124 records)
qualify without a caveat: finite, freely redistributable, together an
estimated 3-4 MB compressed, inside the seed budget's reserve. They ship in
the seed as their own tables (books and sections are not stations; forcing
them into the stations schema would bend both), land in **Phase 3** right
after the station machinery proves itself, and make the two audiobook
branches browsable offline and instant. Wikidata's axis joins (CC0, 400 rows
per axis) also become a seeded enrichment table rather than a live cache.
Internet Archive stays live-drill permanently - the measured
half-million-item collections end that discussion - and Apple, iHeart, and
TuneIn stay out on terms, which is the directive's other half.

#### The Xiph outage, diagnosed (2026-08-15)

Troubleshot rather than shrugged at. Findings, in order:

- Every fetch path is empty **server-side**: `/genres`, `/codecs`,
  `/search?search_term=jazz` all return the same 3 KB page shell with zero
  content links, and `yp.xml` returns a bare 23-byte empty directory
  element.
- **Not user-agent filtering**: byte-identical responses to a real browser
  UA and to QUILL's own UA, on every path.
- **Not our parser**: the same `xiph.py` code measured ~500 genres from this
  site on 2026-08-13/14 during the 3.0 truncation fix; fixtures from those
  runs still parse.
- **Intermittent by history**: Wayback snapshots of `/genres` from 2026-07-09
  and 2026-07-21 are *also* content-free shells, while our mid-August runs
  saw full data - so the beta backend has been flapping for weeks, serving
  either everything or nothing.
- Every other source in the app answered a live health sweep today
  (Radio Browser, SomaFM, M3U, iHeart, TuneIn, networks, reading services,
  NOAA, Gutenberg, LibriVox, Archive, Apple). Xiph is the only outage.

Consequences, all already in this plan: the empty-answer-is-an-outage rule
(5.6) exists precisely for this; the `directory_cache` stale tier would have
bridged it in the app had the local caches not been cleared today; and under
the catalog design this whole class of outage becomes invisible - the
listener browses the last-known-good Xiph data while the source is marked
stale with its age. Worth doing besides: report the flapping backend
upstream to Xiph, since the site presents no status page.

**Ruling on "pull it out of the package" (2026-08-15): Xiph is not
unrecoverable - it served ~500 genres to this codebase two days ago - so it
stays in the code, and the tripwire has been EXECUTED rather than deferred:**
`default_on=False` shipped the same day (PR #1401). New profiles do not see
the branch; anyone who enables it in Choose Browse Sources keeps it; the
honest empty-state still explains the outage for those who look; reversal is
one line when the backend holds steady. Removal outright happens only if the
source stays dead for sixty days (from 2026-08-15), at which point it exits
`ROOT_SOURCES`, the seed builder, and the docs together.
#### The store (built from the real dump)

- SQLite with the PRD schema plus FTS5: **26.4 MB** after VACUUM for the full
  62k stations. Import plus FTS build: 5.8 s (off-thread, once per full
  refresh).
- Compressed seed: **6.4 MB** at lzma preset 6 (21 s to compress at build
  time), 5.7 MB at preset 9. Decompress on first run: **1.2 s**. The 20 MB
  budget was generous by three times - **amended to 10 MB hard**.
- Query medians (n=30):
  - point lookup by key: 0.01 ms
  - FTS "jazz": 1.2 ms; FTS prefix "bb": 0.5 ms
  - states of a country: 2.9 ms
  - stations by country ordered by votes: 41 ms bare, **0.53 ms** with a
    `(country, votes DESC)` covering index. The index ships in the schema.
  - countries GROUP BY: 7-13 ms (acceptable; can become a cached table if
    the root branch ever needs better)
- The JSON alternative, measured and rejected with numbers: loading the raw
  dump takes **9.0 s and peaks at 217 MB of memory**; even once in memory, a
  by-country filter costs 23 ms - slower than the indexed SQLite query
  reading from disk.
- Refresh memory amendment: parse and insert **per page** (10k rows), never
  the whole dump at once; paging caps refresh peak in the tens of megabytes
  where whole-dump loading measured 217 MB.

#### The read path, end to end

Catalog rows were materialized through the real `BrowseNode`/`RadioStation`
types the tree consumes:

- all 240 country folders, **each carrying its station count**, in 7.3 ms -
  a per-folder count the live path cannot afford at all, and exactly what the
  "folder announces its size" rule wants;
- 2,000 fully constructed playable US station leaves in 41.7 ms, where the
  cost is dataclass construction, not SQLite. Branches page far below 2,000
  rows, so the 50 ms budget holds with a wide margin.

#### Windows swap semantics (the trap the prototype caught)

`os.replace` over a database an open SQLite connection holds **fails with
PermissionError on Windows** - so the first draft's "stage then swap the .db"
design cannot work while any reader exists. Verified fix, also prototyped:
**generation files plus a pointer**. Refresh writes `catalog.<n>.db`, then
atomically replaces a tiny `CURRENT` pointer file that readers consult on
open; old generations are deleted once unreferenced (next launch at the
latest). The pointer replace succeeded with the old generation still open.
Section 5.1 is amended accordingly.

### 3. Goals and non-goals

#### Goals

1. Browse Stations answers from local data instantly - target under 50 ms per
   branch - for every source class that permits bulk data.
2. The full supported directories ship inside the app as a compressed,
   versioned seed, refreshed at release-build time, so first launch is
   complete with no network at all.
3. The catalog updates from live data three ways: on startup (toggleable),
   on a timer (interval configurable, off-able), and on demand (menu command
   with a spoken summary).
4. Every automatic behavior has an off switch, and off means off: no fetch,
   no probe, no "just checking".
5. Custom and saved stations are structurally incapable of being damaged by
   any catalog operation. Not "carefully avoided" - stored elsewhere.
6. The listener can always answer: how old is my catalog, what changed last
   time, and which sources are healthy.
7. **Cache everything that is legally allowed, and nothing that is not.**
   The standing directive (Jeff, 2026-08-15): every source whose license or
   terms permit local storage joins the catalog; every source whose terms bar
   it stays live-drill with a session cache only - and the boundary between
   the two is visible in the product, not buried in this document.
8. **The listener can always tell what is local and what is live** - per
   branch, in the UX, without noise (Section 6.5).

#### Non-goals (this program)

- No telemetry, no usage upload, no server of ours. All reconciliation is
  client-side against the sources' own endpoints.
- No recommendations engine. "Similar stations" and taste modeling are a
  later, separate conversation.
- No SHOUTcast dependency. The stance from 3.0 stands: opportunistic,
  optional, never load-bearing.
- No scraping of sources whose terms do not permit bulk retrieval. TuneIn's
  tree remains live-drill; Apple charts remain live; that is a compliance
  posture, not a technical gap.
- The libraries (Archive, LibriVox, Gutenberg, Apple Podcasts) are content
  catalogs, not station directories; they keep today's lazy + cached model.

### 4. Source classes - the load-bearing distinction

Every source gets exactly one class, declared in code, and the class decides
everything downstream: whether it is bundled, how it refreshes, what the
refresh may touch.

#### Class A - bundled and refreshed (the catalog proper)

Bulk retrieval is permitted and practical. Shipped in the seed, refreshed
live, served locally.

- Radio Browser (full export; countries/states/languages/tags/codecs axes,
  popular/trending rankings snapshotted for offline fallback)
- Xiph / Icecast directory (yp listing)
- SomaFM (channels.json)
- (iHeart was a candidate here; the terms read moved it to Class B
  permanently - see Section 2b.)
- NOAA wxindex, community M3U, networks, ACB, NFB, reading services (already
  bundled; they join the catalog store so one machine serves all of them)

#### Class B - live-drill (cached, never bundled)

Remote trees or terms-limited APIs. Today's behavior, unchanged:
`directory_cache` in front, lazy expansion. TuneIn, **iHeart (by policy -
its terms bar entering listings into a database or distributing them; see
Section 2b)**, Apple Podcasts, the libraries, free music
(Audius/Mixcloud/ccMixter), Wikidata, YouTube listings.

#### Class C - user-owned (protected, never refreshed)

Favorites, custom stations, My Servers, YouTube channels the listener added,
imported playlists. These live in their existing stores, are never written by
any catalog code path, and are overlaid at read time (Section 8).

### 5. Architecture

#### 5.1 The store: SQLite, not JSON

The catalog is a single SQLite database per profile:

    %APPDATA%\Quill\radio-catalog\catalog.db

Why SQLite over the house JSON pattern: measured, not asserted (Section 2b).
The full directory in SQLite answers an indexed browse query in **0.5 ms**;
the same data as JSON costs a 9-second, 217 MB load before the first answer.
The persistence rules hold in spirit via **generation files plus a pointer**:
refresh builds `catalog.<n>.db` completely, then atomically replaces a tiny
`CURRENT` pointer file naming it. Readers resolve the pointer on open. This
shape is forced by a measured Windows fact: `os.replace` over a database an
open connection holds raises PermissionError, so the classic stage-and-swap
of the .db itself cannot coexist with readers. Old generations are removed
once unreferenced (next launch at the latest). A crashed refresh leaves a
garbage numbered file and an untouched pointer - always consistent.

Crucially: **the catalog is derived data.** It can be deleted, rebuilt from
the seed, or discarded on schema change with zero loss, because nothing the
listener owns is in it. That single property removes the entire class of
migration risk that makes databases scary.

#### 5.2 Schema (DDL sketch)

    CREATE TABLE catalog_meta(
      key   TEXT PRIMARY KEY,       -- schema_version, seed_version,
      value TEXT NOT NULL           -- seed_built_at, imported_at, app_version
    );

    CREATE TABLE sources(
      id             TEXT PRIMARY KEY,   -- 'radio_browser', 'xiph', ...
      class          TEXT NOT NULL,      -- 'bundled' | 'live' | 'user'
      last_refresh   TEXT,               -- ISO UTC
      last_status    TEXT,               -- 'ok'|'stale'|'rate_limited'|'error'
      last_error     TEXT NOT NULL DEFAULT '',
      station_count  INTEGER NOT NULL DEFAULT 0,
      content_hash   TEXT NOT NULL DEFAULT ''   -- change detection
    );

    CREATE TABLE stations(
      key              TEXT PRIMARY KEY, -- canonical key, Section 5.4
      name             TEXT NOT NULL,
      stream_url       TEXT NOT NULL,
      homepage         TEXT NOT NULL DEFAULT '',
      country          TEXT NOT NULL DEFAULT '',
      state            TEXT NOT NULL DEFAULT '',
      language         TEXT NOT NULL DEFAULT '',
      tags             TEXT NOT NULL DEFAULT '',  -- normalized, comma-joined
      codec            TEXT NOT NULL DEFAULT '',
      bitrate          INTEGER NOT NULL DEFAULT 0,
      votes            INTEGER NOT NULL DEFAULT 0, -- ranking snapshot
      source_id        TEXT NOT NULL REFERENCES sources(id),
      source_record_id TEXT NOT NULL DEFAULT '',
      first_seen       TEXT NOT NULL,
      last_seen        TEXT NOT NULL,
      vanished_at      TEXT,             -- tombstone; Section 5.6
      extra            TEXT NOT NULL DEFAULT '{}'  -- source-specific JSON
    );
    CREATE INDEX idx_st_geo  ON stations(country, state);
    CREATE INDEX idx_st_lang ON stations(language);
    CREATE INDEX idx_st_src  ON stations(source_id);

    CREATE VIRTUAL TABLE stations_fts USING fts5(
      name, tags, country, language, content='stations', content_rowid='rowid'
    );

    CREATE TABLE merges(          -- provenance when two sources are one station
      canonical_key TEXT NOT NULL,
      member_key    TEXT NOT NULL,
      reason        TEXT NOT NULL,     -- 'same_url'|'radiodns'|'uuid'
      PRIMARY KEY(canonical_key, member_key)
    );

#### 5.3 New modules (house conventions; every one wx-free unless named ui/)

- `quill/core/radio/catalog/store.py` - open/query/atomic-swap/rebuild; the
  only module that touches SQLite.
- `quill/core/radio/catalog/keys.py` - canonical keying + URL normalization.
  Pure. **Must use the same key rule favorites already use**
  (`station_uuid or stream_url`) so overlay joins are exact.
- `quill/core/radio/catalog/merge.py` - cross-source dedupe + provenance.
  Pure functions over record lists; deterministic; heavily tested.
- `quill/core/radio/catalog/refresh.py` - orchestration: which sources are
  due, staggering, delta-vs-full, staging writes, swap. Fetchers injected so
  tests never touch the network.
- `quill/core/radio/catalog/summary.py` - the diff model and its spoken
  sentences. Pure.
- `quill/core/radio/catalog/seed.py` - locate the bundled seed, verify its
  hash, import to the profile on first run / app update.
- `quill/ui/radio/catalog_ui.py` - glue: minute-tick wiring, menu command,
  announcements, settings plumbing (host-taking functions, like
  `schedule_wake_ui`).
- `quill/ui/radio/catalog_summary_dialog.py` - the review dialog (house
  ListBox pattern; rows speak whole sentences).
- `scripts/build_radio_catalog.py` - the release-time seed builder.

Errors: `CatalogError(CodedError)` with `QUILL-RADIO-CATALOG-*` codes
(`-CORRUPT`, `-SEED-MISSING`, `-REFRESH-FAILED`, `-SWAP-FAILED`).

#### 5.4 Canonical keys and merge rules

Key precedence, first match wins:

1. Radio Browser `station_uuid` (stable, source-issued).
2. Normalized stream URL: lowercase scheme+host, strip default ports, strip
   known junk query params, keep path. One pure function in `keys.py`,
   shared with nothing rewritten - favorites' existing key logic is the
   reference behavior.
3. RadioDNS service identity, when `radiodns.py` resolves one - as a merge
   *link* between records, never as a primary key.

Merge policy (deliberately modest for Phase 1):

- Same key across sources -> one canonical row; the higher-trust source wins
  field-by-field only where the other is empty; all member identities kept in
  `merges` with a reason.
- **A shared stream URL alone never merges.** Measured: 7,135 URLs are shared
  by multiple distinct stations within Radio Browser alone (relays and
  network feeds). URL-based merging additionally requires a case-insensitive
  name match; anything less collapses real stations.
- Trust order: user (never merged, always overlay) > bundled curated (ACB,
  NFB, networks, reading services) > Radio Browser > Xiph > iHeart.
- Ambiguity (same name+country, different URLs) is NOT merged. Two rows and
  honesty beat one row and a guess. Fuzzy matching is Phase 4 material, if
  ever.

#### 5.5 The seed: building and shipping the whole directory

`scripts/build_radio_catalog.py`:

1. Runs the same Class-A fetchers the app uses (they are wx-free precisely so
   this is possible), against live endpoints, with polite pacing.
2. Normalizes, merges, writes a fresh `seed.db`.
3. Compresses with `lzma` (stdlib; no new dependency) to `seed.db.xz`,
   records SHA-256 + build date in a sidecar manifest.
4. Emits a size report and **fails the build if the seed exceeds budget**
   (Section 12) - a silently ballooning installer is a regression.

Wired into `standalone/radio/scripts/build_release.ps1` exactly like docs
rendering: a step before PyInstaller, with `-SkipCatalog` for dev builds, and
the seed staged into `quill/data/radio-catalog/`. Both editions carry it
(portable payload and shared runtime); the installer therefore works fully
offline on first run.

First-run import: `seed.py` extracts to staging, verifies the hash, swaps in.
App update with a newer seed: if the profile catalog's `seed_version` lineage
is older than the shipped seed, import the new seed and let the next live
refresh replay any newer deltas. Simple, and correct because the catalog is
derived data.

#### 5.6 The refresh engine

Layers, mirroring what shipped for scheduling elsewhere in the app:

- **Layer 0 - release build.** Every release ships a seed built that day.
- **Layer 1 - startup refresh** (setting: on by default, one checkbox to turn
  off). Runs on the task manager after the window is up, never blocking
  launch; skipped in Safe Mode; skipped when the catalog is younger than a
  floor (6 hours) so a restart loop never hammers anyone's API.
- **Layer 2 - periodic refresh** (setting: interval in hours, default 24;
  0 = off). Driven from the existing radio minute-tick - no new timer.
  Staggered per source (one source per tick window) so refresh is a trickle,
  not a burst.
- **Layer 3 - manual.** Station menu: "Update Station Catalog..." - refresh
  all due sources now, announce the summary, offer the review dialog. Also
  per-source refresh from the (Phase 3) catalog status view.
- **Layer 4 - opportunistic write-through, Class A sources only.** When a
  live fetch of a Class-A source happens anyway (a stream re-resolve,
  federated search), the slice it returns upserts into the catalog.
  Freshness for free, zero extra requests. Class B results are **never**
  written through - for TuneIn and iHeart that is a terms obligation
  (their listings may not be entered into a persistent database), and for
  the rest it keeps the rule simple enough to audit: the catalog contains
  Class A rows, only.

Mechanics:

- Delta where the source supports it (Radio Browser publishes change feeds);
  full fetch + `content_hash` comparison where it does not; a full fetch
  whose hash is unchanged writes nothing and counts as "no changes".
- All fetches through the existing `http_client` identity, respecting
  Retry-After, with per-source failure isolation: one source down = one
  source stale, never a failed refresh.
- **An empty answer from a previously populated source is an outage, not
  truth** (learned from Xiph serving a bare directory today): the fetch is
  recorded as failed, the catalog keeps what it has, and the source is
  marked stale with its age.
- Bulk fetches are parsed and upserted **per page** (10k rows), never as one
  whole-dump load - measured whole-dump peak was 217 MB; paging caps it in
  the tens.
- Removal is a tombstone (`vanished_at`), not a delete; rows vanish from
  browse immediately but are kept 14 days so a source hiccup that drops half
  its records for an afternoon does not thrash the catalog. After the grace
  window they are purged.
- **The browse-visibility rule extends to refresh:** a source the listener
  has hidden is not refreshed. Off means never contacted - same sentence,
  same guarantee.

#### 5.7 The read path: how browsing gets fast

No UI changes at all in Phase 1 - the speed appears under the existing
contract. Inside `browse_sources`, each Class-A handler gains a catalog-first
branch:

    countries      -> SELECT country, COUNT(*) ... GROUP BY country
    states         -> SELECT state ... WHERE country=?
    stations-by-X  -> indexed SELECT, ordered, instant
    genres/tags    -> SELECT from the normalized tag column
    popular        -> votes-ordered snapshot when offline; live when online
                      (rankings are the one thing that should stay live-first)

Fallback ladder per branch: catalog (if enabled and present) -> live fetch
(which also write-throughs) -> `directory_cache` stale tier -> the existing
honest empty-state messages. `last_error_was_network` semantics unchanged.

Find Stations gains an FTS lane: local matches appear instantly as the first
group, live-source groups append as they arrive - same UI, same source
column, no second surface. Search-as-you-type against FTS must stay under
30 ms.

#### 5.8 RadioDNS and identity enrichment, baked in

`core/radio/radiodns.py` and its approved `dnspython` dependency shipped in
3.0.0 and are underused. Under the catalog they stop being a live lookup and
become **build-time enrichment**:

- The seed builder joins Wikidata's axis data (which carries broadcast
  frequency and country - the inputs RadioDNS resolution needs) against the
  station rows, performs the SRV/CNAME resolution **once, at build time, on
  the build machine**, and writes the resolved service identities into an
  `identities` table. The app then merges by identity with a plain local
  join - zero DNS traffic from any listener's machine.
- Refresh re-resolves only rows whose inputs changed, on the same staggered
  cadence as everything else, and only when the catalog and refresh are
  enabled.
- Coverage honesty: this enriches the minority of stations that publish
  broadcast parameters. It is a merge-quality upgrade, not a feature the UI
  advertises; where it fires, two provider rows quietly become one, which is
  the whole point.
- RadioDNS **SPI service documents** (`SI.xml` - stations, logos, and stream
  links that broadcasters publish themselves, an open standard built for
  exactly this kind of consumption) are the natural next enrichment and are
  listed in Appendix A for adoption.

### 6. User-facing behavior

#### 6.1 Settings (all in RadioHistory + the Preferences dialog)

- `catalog_enabled` (default on) - master switch. Off restores today's
  behavior exactly: live browsing, `directory_cache`, nothing read from or
  written to the catalog, no refresh of any layer.
- `catalog_refresh_on_startup` (default on) - Layer 1 toggle.
- `catalog_refresh_hours` (default 24; 0 = off) - Layer 2 interval.
- Per-source participation is NOT a new setting: it is the existing Choose
  Browse Sources selection. One list, one rule, already shipped.

Checkbox copy follows the house voice, for example: "Keep the station catalog
updated automatically" / "Check for station updates when Quill Radio starts".

#### 6.2 The summary, spoken and reviewable

After any refresh (manual always; automatic only when something changed):

    "Station catalog updated. 174 new, 62 repaired streams, 431 details
    updated, 12 removed. Two sources could not be reached."

Whole words, counts first, sources-by-name only in the review dialog. The
dialog is the house ListBox pattern: one row per category, Enter expands to
the per-source detail, read-only, Escape closes. "No changes" is announced
for manual refresh and stays silent for automatic ones - an automatic process
that talks when nothing happened is noise.

#### 6.3 Status, on demand

View menu: "Station Catalog Status..." (Phase 3) - catalog age, station
count, per-source last-refresh and health, seed version, and three buttons:
Update Now, Update This Source, Rebuild From Shipped Snapshot.

#### 6.4 Offline and Safe Mode

- Offline: everything Class A browses and searches normally from the catalog;
  Class B branches show their existing could-not-reach messages. The app is
  never empty.
- Safe Mode: no refresh of any layer, ever. Reading the local catalog is
  permitted - it is local data, exactly like favorites.

#### 6.5 Telling the listener what is local and what is live

The directive: the cached/live boundary must be visible in the experience,
not just in this document. The rule for doing it without noise: **say it
where the listener is already reading detail, never on every row.**

- **The details panel** (already on every browse surface) gains one closing
  line per branch: *"Answers from your catalog, updated 2 hours ago."* or
  *"Asks the internet each time; nothing is stored."* Words, never a
  timestamp; the age is spoken the way Continue Listening speaks positions.
- **Choose Browse Sources** rows gain the same fact in their description -
  "On. LibriVox Audiobooks. Public-domain audiobooks, by chapter. Stored on
  this computer." versus "... Live from TuneIn." - so the place you decide
  about a source is the place you learn how it behaves.
- **Station Catalog Status** (6.3) is the complete answer: every source, its
  class in plain words ("stored and kept current" / "live only" / "yours"),
  its age, its health, and *why* a live-only source is live-only - one
  sentence each, "iHeart's terms do not allow storing its listings", because
  the honest reason reads better than an unexplained gap.
- **The magical touch, kept quiet:** the first time a branch answers from
  the catalog with the network down, one announcement - *"You are offline.
  Browsing from your catalog, updated this morning."* - once per session,
  never per branch. The app quietly being fine when the internet is not is
  the whole feature; one sentence is how it takes credit without bragging.
- Never a per-row badge, never a per-row suffix: 62,000 rows that each end
  in "cached" is 62,000 interruptions for a fact that belongs to the branch.

### 7. What "fast" means (budgets, enforced)

- Open catalog + first branch query: < 50 ms on the dev machine, enforced by
  a perf-marked test (RUN_PERF lane, like the existing budgets).
- FTS search keystroke: < 30 ms.
- Startup cost when refresh is off: zero added network, < 10 ms added CPU
  (open is lazy - the store opens on first browse, not on launch).
- Refresh memory: streaming parse, never a whole-directory list in RAM;
  peak budget 150 MB during a full Radio Browser import.
- UI thread: zero catalog I/O ever; store reads run on the task manager and
  return via the existing call-ui-safely path... with one exception: point
  reads under 5 ms (a single keyed SELECT) may run inline, measured, because
  a CallAfter round-trip would cost more than the read.

### 8. Protection of user stations (invariants, not intentions)

1. **Separate files.** User data stays in its existing stores. The catalog
   database contains zero user-owned rows. There is no code path from
   `catalog/refresh.py` to any user store - enforced by an import-boundary
   test (refresh modules may not import favorites/my_servers/youtube_channels
   stores).
2. **Overlay at read time.** When a browse row's canonical key matches a
   favorite, the favorite's name and edits win in display, and the row is
   marked saved. The catalog row is untouched.
3. **Vanish never cascades.** A station disappearing from a source never
   changes a favorite that points at it - favorites already serialize their
   own full station record, and that stays the rule.
4. **Rebuild is safe by construction.** "Rebuild From Shipped Snapshot"
   deletes only `radio-catalog/`. A test asserts the favorites, My Servers,
   YouTube channels, and schedule files are byte-identical across a rebuild.
5. **Imports are user data.** A playlist import lands in favorites (Class C),
   never in the catalog, so no refresh can ever "correct" it.
6. The existing timestamped favorites backups continue independently.

### 9. Accessibility requirements (gates, not aspirations)

- Every new dialog through `_show_modal_dialog` + `apply_modal_ids`; ListBox
  activation via `apply_listbox_activation` (GATE-13); rows speak state
  first; dialog and accessible-name inventories regenerated.
- Counts and ages in words ("about two hours old"), never bare timecodes.
- Automatic refresh announces only outcomes that changed something; manual
  refresh always answers.
- The empty/broken distinction survives: catalog-served branches still say
  "nothing in X" vs "X could not be reached" correctly, because the fallback
  ladder preserves the failure flags.

### 10. Compliance and egress

- Every new endpoint (bulk exports, delta feeds) gets a reviewed entry in the
  network egress audit before it is called.
- The seed builder runs at release time from the build machine - it is not
  app egress, but it is documented in the audit's build-tools section anyway.
- iHeart terms were read 2026-08-15 (Section 2b): Class B permanently;
  never seeded, never written through, live-drill with session caching only.
- TuneIn: policy unchanged - live-drill only, never bulk, never seeded.
- Attribution: sources that request credit (Radio Browser) get it in the
  About/docs, and provenance is visible per-station in the details panel.

### 11. Failure handling (the degradation matrix)

| Failure | Behavior |
| --- | --- |
| Catalog file corrupt | Coded error logged once; auto-rebuild from seed; browse falls to live for that session; one calm announcement |
| Seed missing/hash mismatch (tampered or truncated install) | Catalog disabled with a status message; live browsing unaffected; never import an unverified seed |
| One source down during refresh | Source marked stale with its age; every other source refreshes; summary names it |
| Rate limited | Honor Retry-After; back off that source for the day; count it in the summary as "waiting", not "failed" |
| Disk full mid-refresh | Staging write fails; swap never happens; existing catalog intact; announced once |
| Refresh interrupted (sleep, shutdown) | Staging discarded on next start; catalog is whatever was last swapped in - always consistent |

### 12. Packaging and size budget

- Seed budget: **10 MB compressed, hard-failed in the build** if exceeded.
  Measured (Section 2b): the full 62,377-station Radio Browser catalog with
  FTS compresses to **6.4 MB**; SomaFM is noise; Xiph is currently empty;
  iHeart is out by policy. The realistic seed is roughly 7 MB - the budget
  has a comfortable third in reserve.
- If the measured seed lands over budget: split the seed and move the bulk to
  the existing assets-on-demand release mechanism (the pattern speech engines
  already use), keeping a minimal in-package seed (curated sources + top-N
  per country) so first-launch is still complete-feeling offline.
- The catalog directory is excluded from any sync mechanism (it is derived,
  per-machine data, same reasoning as `local_paths`).

### 13. Testing strategy

- Pure units: keys (URL normalization table-driven), merge (every rule and
  every refusal-to-merge), summary sentences, due/stagger arithmetic with an
  injected clock.
- Store: tmp-dir SQLite round-trips; swap atomicity (kill between stage and
  swap -> old catalog intact); tombstone grace; FTS query shapes.
- Refresh: fake fetchers (success/empty/hash-unchanged/rate-limited/raise);
  assert per-source isolation and that a hidden source is never fetched.
- Read-path parity: for each converted branch, catalog-served rows ==
  live-served rows for the same fixture data (shape and ordering), so the UI
  cannot tell which path answered.
- Invariant tests from Section 8 (import boundary, rebuild byte-identity).
- Perf lane: the 50 ms / 30 ms budgets as RUN_PERF tests.
- The conftest real-profile write guard already protects the developer's own
  catalog during all of this.

### 14. Phased delivery (PR-sized, in order)

#### Phase 0 - measure before promising - DONE 2026-08-15

Findings are Section 2b; the prototype lives in `local/catalog-proto/`
(fetchers, the built 26 MB catalog, the 6.4 MB seed, the benchmark scripts).
Outcomes folded into this document: 10 MB seed budget, pointer-based swap,
URL-merge tightening, empty-source outage rule, per-page refresh parsing,
the `(country, votes DESC)` covering index, and mandatory pagination for the
Radio Browser dump. The iHeart terms read closed Phase 0 entirely: iHeart is
Class B by policy (Section 2b). Nothing remains open in this phase.

#### Phase 1 - the catalog exists and browsing is instant (2-3 PRs)

1. `catalog/` core: store, keys, merge, seed import, coded errors + tests.
2. Seed builder script + release-script wiring + size gate + egress entries.
3. Catalog-first read path for Radio Browser axes, Xiph, SomaFM (+ iHeart if
   cleared), behind `catalog_enabled`; parity + perf tests; the master
   checkbox in Preferences.

Exit criteria: fresh install, network cable pulled, every Class-A branch
browses instantly; suite green; installer size within budget.

#### Phase 2 - it stays fresh, and says so (2 PRs)

4. Refresh engine: startup toggle, interval, staggering, tombstones,
   write-through; the two new Preferences checkboxes; minute-tick wiring.
5. "Update Station Catalog..." command, summary model, spoken summary,
   review dialog; inventories regenerated.

Exit criteria: John's machine can sit for a week and the catalog is current;
turning both toggles off produces zero background requests (verified by the
egress-silent test lane).

#### Phase 3 - visibility, search, and the adopted extensions (2-3 PRs)

6. FTS lane in Find Stations (instant local group first).
7. Catalog Status view: age, health, per-source refresh, rebuild button;
   "what's new since last update" as a browse branch that reads the diff;
   the cached-vs-live UX of Section 6.5 (details-panel line, Choose Browse
   Sources descriptions, the once-per-session offline sentence).
8. **The library seed (Class A2, adopted):** Gutenberg audio seeded and
   served locally. LibriVox measured out of the v1 seed (see the delivery
   log: 194,501 section rows = 60 MB against the whole 10 MB budget); its
   branches stay live, and seeding it behind a compact section format is
   the named follow-up.
9. **RadioDNS enrichment at build time** (5.8): the identities table and the
   Wikidata frequency join in the seed builder.

#### Phase 4 - explicitly deferred until the above is proven

- FMSTREAM as a new Class-A source (terms check first).
- RadioDNS-driven merge links in the merge engine.
- Trust badges in station details; "most improved"; nearby/local mix.
- Fuzzy dedupe. Only with a corpus of real duplicates to test against.

### 15. Risks

| Risk | Mitigation |
| --- | --- |
| Seed bloats the installers | Hard size gate in the build; assets-on-demand split ready as the relief valve |
| A source changes its export format | Per-source isolation + hash short-circuit; worst case one stale source, never a broken app |
| SQLite on network/portable drives misbehaves with WAL | Portable edition detection already exists; fall back to journal mode DELETE on portable media; swap semantics unchanged |
| Merge collapses two real stations into one | Refusal-to-merge on ambiguity; provenance table makes any merge inspectable and reversible on rebuild |
| Scope creep toward the delight features before the engine is solid | Phase gates above; Phase 4 items are named and parked, not smuggled |

### 16. Open questions for Jeff

1. (Closed 2026-08-15: iHeart terms read; Class B permanently. See 2b.)
2. Default periodic interval: 24 hours is proposed; 12 felt eager for a
   directory that changes slowly. Preference?
3. Should popular/trending fall back to the snapshot when offline (proposed:
   yes, labeled "as of <age>"), or hide rather than show stale rankings?
4. Seed in both editions, or portable-only with the installer relying on
   first-run refresh? (Proposed: both; offline-first is the story.)

### Appendix A - freely available sources for Jeff to consider

Filtered hard by the standing rule: **if hoops are required - keys,
registrations, partner agreements, terms that bar storage - forget it.**
Everything below was checked on 2026-08-15; the two marked *verified live*
were fetched and measured today.

#### Include - no hoops, storage permitted

- **laut.fm** (*verified live*): open keyless JSON API, `api.laut.fm` -
  measured today at **15,956 stations, 36.8 MB, one request, no key**.
  German community/web-radio platform; API is explicitly public. A genuine
  Class A candidate on Radio Browser's scale, with unusually clean metadata.
  Effort: one adapter, one seed table. The strongest add on this list.
- **RadioDNS SPI documents (SI.xml)**: broadcasters self-publish station
  lists, logos, and stream links in an open standard *designed* to be
  consumed and cached. No key, no agreement - the standard exists so clients
  do exactly this. Effort: an SPI parser plus the 5.8 enrichment hook.
  Coverage is broadcaster-by-broadcaster (strong in Europe), so it enriches
  rather than fills the tree.
- **Openverse audio** (WordPress Foundation): CC-licensed audio catalog with
  an open anonymous API (rate-limited, keyless at the tier the app would
  use). A library-shelf source rather than radio; every record carries its
  license, which fits the ccMixter licence-travels-with-the-file pattern.
  Effort: moderate; consider only if a "CC music shelf" is wanted.

#### Consider with one caution each

- **FMSTREAM (fmstream.org)**: **ignored for now (Jeff, 2026-08-15).**
  Large directory, no API, terms silent rather than permissive - and silent
  is not yes. Revisit only with a clear answer from the maintainer.
- **Podcast Index** (*verified live*): the full database is a genuinely
  free, keyless public download - measured today at **1.8 GB** - but the
  size makes it an on-demand asset at best (the assets-v1 pattern), never a
  seed, and Cast is its natural home rather than Radio. Parked unless the
  Radio/Cast boundary changes.
- **Environment Canada Weatheradio**: the NOAA-shape counterpart for Canada;
  public data, but the internet re-streams are third-party and would need
  the same feed-by-feed vetting `wxindex` did for NOAA. Effort: a wxindex
  sibling; worth it if Canadian listeners ask.
- **Lit2Go** (University of South Florida): free public-domain audiobooks
  with attribution terms; no API, so ingestion is page-walking - modest
  hoops, honest ones. Only worth it if the A2 shelf proves popular.

#### Excluded by the no-hoops rule - listed so the reasoning is visible

- **Jamendo** (free but mandatory API key), **Free Music Archive** (API
  discontinued; terms of the successor unclear), **radio.garden**
  (unofficial API, terms not open), **Dirble** (dead), **vTuner/Streema/
  radio-locator** (commercial/proprietary), **SHOUTcast** (partner-gated;
  the 3.0 stance stands), **BBC and public-broadcaster direct streams**
  (geo/terms per broadcaster; RadioDNS SPI is the legitimate path to the
  same stations).

### Delivery log

- 2026-08-15: Phases 1-3 built in one pass on `feat/station-catalog`:
  `quill/core/radio/catalog/` (store with pointer-swapped generations, keys,
  refresh with the empty-guard and tombstones, seed import, spoken
  summaries, the read path), the `browse()` chokepoint integration, the
  Find Stations instant lane, three Preferences (master switch, startup
  check, interval defaulting 24 hours), Station > Update Station Catalog,
  View > Station Catalog Status (the complete cached-versus-live answer),
  the once-per-session offline sentence, the seed builder with its hard
  10 MB gate wired into the release script, the Gutenberg audio shelf, and
  17 core tests pinning every measured rule.
- **LibriVox is not in the v1 seed - the budget gate said so.** The full
  shelf built: 8,978+ books carrying 194,501 section rows, a 70.3 MB
  database compressing to 11.8 MB - over the 10 MB gate on chapter listings
  alone (their API also caps `extended=1` pages at 800; `fetch_book_page`
  uses 500 and stays for the follow-up). Decision: LibriVox branches keep
  answering live exactly as 3.0 served them; seeding them behind a compact
  section format is the named follow-up. The Status view says so honestly.
- **Found while wiring Layer 1:** the startup refresh never fired in a
  public-shaped run because the editor's `core.radio` release gate (#1347)
  also killed `_init_radio`'s active block inside Quill Radio itself -
  scheduler, wake task, missed reports, palette included. Fixed via
  `FeatureManager.grant_product_features` (the app claims its own feature at
  startup; in-memory, safety locks still apply), same treatment for Quill
  Cast. The catalog's startup import is verified end-to-end in a real app
  loop: seed imported, `CURRENT` + generation present, age 0.
- FMSTREAM: ignored for now (Jeff, 2026-08-15).

### 17. Decision log

- 2026-08-15 (directive): cache-everything-legal adopted as Goal 7; Class A2
  (LibriVox + Gutenberg audio) promoted from parked to Phase 3; Wikidata
  becomes a seeded CC0 enrichment table; cached-vs-live made a first-class
  UX requirement (6.5); RadioDNS moved from live lookup to build-time
  enrichment (5.8); Xiph default_on=False executed same day (PR #1401);
  Appendix A added with verified candidates (laut.fm 15,956 stations
  keyless; Podcast Index dump 1.8 GB, parked on size) and the no-hoops
  exclusion list.
- 2026-08-15 (sweep): every source measured (table in 2b). LibriVox and
  Gutenberg audio identified as Class A2 library-seed candidates for Phase 4
  (~22-24k + 1,124 records, est. 3-4 MB compressed); Internet Archive
  confirmed live-drill by the numbers (collections to 522k items). Xiph ruled
  intermittent, not dead: kept with a release-cut tripwire (auto-hide via
  `default_on=False` while empty; removal only after sixty dead days).
- 2026-08-15 (latest): iHeart Terms of Use read (updated 2025-03-12).
  Section 23's "enter into a database... distribute" bars seeding or
  persisting iHeart listings; iHeart set to Class B permanently, and Layer 4
  write-through narrowed to Class A sources only so the catalog database
  provably contains nothing terms-encumbered.
- 2026-08-15 (later, from the prototype): swap design changed to generation
  files plus a pointer after `os.replace` over an open database failed on
  Windows; seed budget halved to 10 MB on a measured 6.4 MB; URL-only merging
  rejected on measured evidence (7,135 shared URLs); empty-source outage rule
  added after finding the live Xiph directory empty; the JSON store
  alternative rejected with measurements (9 s and 217 MB versus 0.5 ms).
- 2026-08-15: SQLite chosen over sharded JSON for the catalog store; derived-
  data principle adopted (rebuildable, never authoritative for user data);
  TuneIn confirmed excluded from bulk; user-data protection expressed as
  import-boundary + byte-identity tests rather than code review vigilance;
  the earlier rubber-duck note this file held is superseded by this plan
  (its delight items live in Phase 4, its "what not to do" list is absorbed
  into Non-goals and Invariants).
