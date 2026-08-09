# Quill Radio for iOS -- Product Requirements

**Product:** Quill Radio for iOS (iPhone, iPad, Apple Watch, CarPlay)
**Ecosystem:** QUILL / QuillVille
**Language and stack:** Swift 6, SwiftUI + a thin UIKit layer where VoiceOver needs it, AVFoundation, AVAudioEngine, MediaPlayer, CarPlay, App Intents, WidgetKit, ActivityKit, CryptoKit
**Document status:** Product definition, implementation-ready
**Version:** 1.0
**Date:** August 8, 2026
**Windows counterpart:** `standalone/radio/docs/prd.md` (the authoritative feature spec for the shared radio domain)
**Shared platform spec:** `docs/Product Requirement Documents and Specifications/quillville-apple-platform-spec.md`
**Sibling iOS app:** `standalone/weather/docs/prd-ios.md`
**Product posture:** Accessibility-first, VoiceOver-first, keyboard-complete, local-first, directory-plural, no-account

---

## 1. Product statement

Quill Radio for iOS puts the whole of Quill Radio -- seven station directories,
a self-healing stream resolver, nested favorites, per-station sound, timers, and
recording -- into a pocket, and then does the thing a desktop app cannot: it goes
with you. Into the car. Onto a wrist. Into a Siri request made with the phone
still in a bag.

The desktop product's real achievement is not that it plays streams. It is that a
blind listener can **find** a station -- across RadioBrowser, TuneIn, iHeart,
SomaFM, ACB Media, Radio Reading Services, and NOAA Weather Radio -- get a
playable URL when the station's own website hides it behind a JavaScript player,
have that URL heal itself when the broadcaster moves it, and organize the result
into a tree that behaves the same way every time. That is the part that must
survive the port intact.

The measure of success: **a blind listener should be able to go from "I heard
about a station called X" to hearing it, entirely by voice or by VoiceOver, in
under thirty seconds, on a phone.** Nothing in the App Store does that today.

---

## 2. Architecture requirement: not a fork

- **R-1.** All portable logic lives in **QuillKit**, the Swift package shared
  with Quill Weather for iOS (see the platform spec). Directory clients, the
  stream resolver ladder, the favorites model, history, the recording model, the
  announcement policy, sync, and settings are QuillKit; the app target holds
  screens, intents, widgets, and the CarPlay scene.
- **R-2.** The domain layer is a **parity port** of `quill/core/radio/*` -- the
  41 wx-free, strict-typed modules that already exist precisely because someone
  anticipated this. Field names, JSON shapes, defaults, clamps, and the exact
  resolver ordering are preserved so a `radio_favorites.json` written on Windows
  loads on iOS and back again with no migration.
- **R-3.** Every user-visible string that is spoken or shown comes from the same
  narration layer Quill Weather uses (`QuillNarrate`), governed by the shared
  golden corpus. "Now playing", "Buffering", "Recording started", the reconnect
  wording, the DVR "two minutes behind live" phrasing -- all of it is spec'd
  once and matched byte for byte across platforms.
- **R-4.** Where iOS cannot do what Windows does, the product **says so plainly
  in the user guide and in the affected screen**. It does not silently ship a
  worse version of a promised feature. §13 is the honest list.
- **R-5.** Source layout: `standalone/radio-ios/` (app, widgets, watch app,
  CarPlay scene, intents, tests) and `apple/QuillKit/`. Both sit outside QUILL's
  Python CI gates, as `standalone/radio-mac/` does, and carry their own Swift CI.
- **R-6.** Data is shared, not copied: favorites, history, recordings index,
  schedules, wake timer, and settings live in one App Group container shared
  with Quill Weather for iOS -- the direct equivalent of the shared
  `%APPDATA%\Quill` store.

---

## 3. Scope

### 3.1 Finding stations

**F-1. Seven blended directories**, ported whole, each behind the audited
network chokepoint and each individually failure-tolerant so a down source never
blanks a result list:

| Source | Access | Notes |
|---|---|---|
| Radio Browser | Public API, keyless | Search with 200-per-page paging and a More Stations control; genre browse; country and tag facets; click-vote; by-uuid re-fetch for self-healing |
| TuneIn (RadioTime OPML) | `opml.radiotime.com`, `partnerId=RadioTime`, keyless | Search/Browse/Tune; resolve cap 10 per search |
| iHeart | Public sitemap index plus the keyless JSON content API | Genre browse; lazy per-station stream resolution; resolve cap 5 |
| SomaFM | Public directory, keyless | |
| ACB Media | Bundled directory | |
| Radio Reading Services | Bundled 20-service snapshot plus live refresh | The audio information services that read print aloud -- a first-class category, not a genre filter |
| NOAA Weather Radio (WeatherIndex) | Live API, then cache, then the bundled 1,035-transmitter snapshot | Works fully offline from the snapshot |

**F-2. Unified Find Stations** -- `merge_and_rank` ported exactly: de-dupe by
stream URL then by name plus country, exact matches first, every non-Radio-Browser
row labelled "via <source>", and `alt_sources` preserved so the Source facet
never hides a station under the wrong directory.

**F-3. Browse tree** -- the lazy hierarchical browser (source, then genre or
state, then A-Z or station) with per-node counts that match what expanding
actually shows.

**F-4. Find Streams -- the website scanner.** The whole resolver ladder ports,
because it is the feature that makes obscure stations reachable:
- Plain HTML scan with the bounded one-level "Listen / Live / Play / Tune in"
  link following.
- **Triton Digital / StreamTheWorld** JavaScript-player resolution: detect the
  player, read the callsign from the PWA's logo asset, resolve a real mount
  through the provisioning API, offer both MP3 and AAC.
- **SecureNet Cirrus** player resolution: host or `ice<N>` mount detection,
  `playSessionID` stripping, `/media` interstitial skipping, callsign casing
  from the mount. Parse-only, no network call of its own.
- **iHeart and TuneIn page** resolution.
- **Live365** pure-string link normalization to the canonical streaming URL.
- Test-play with a Test/Stop Test toggle before committing.

**F-5. Self-healing recovery** -- the confidence-ordered ladder on a playback
error: re-resolve a moved StreamTheWorld or `ice<N>` mount, refresh from the
directory by uuid, then (opt-in, default on) scan the station website. A single
unambiguous result auto-plays and rewrites the favorite; multiple candidates are
announced for the user to choose. One attempt per station per session.

**F-6. Custom stream URLs**, M3U/M3U8/PLS import with folder targeting and
duplicate handling, and export of favorites to extended M3U.

**F-7. Report Bad Station** -- the ported report builder, offered from any
station's actions, carrying station metadata only and never identity or paths.

### 3.2 Listening

**F-8. One transport control** (Play becomes Stop, never a dead button), mute,
and volume with **per-station memory** plus the persisted global level.

**F-9. Single-player rule** -- starting any stream silences sibling audio in
every QuillVille app on the device.

**F-10. What's Playing.** The three-tier title resolution ports:
1. ICY `StreamTitle` side-tap for progressive streams, parsed by the ported
   `now_playing` module -- including the `key="value"` broadcast-automation
   convention and the plain `Artist - Title` form.
2. The player's own timed metadata for HLS (`AVPlayerItemMetadataOutput`).
3. Same-host status endpoint fallback -- Icecast `/status-json.xsl`, SHOUTcast
   v2 `/stats?json=1`, v1 `/7.html`.

The user-set token template (`{title}`, `{artist}`, `{raw}`, `[optional]`
segments; default `{title}[ by {artist}]`) ports unchanged, as does the
reviewable, character-navigable Now Playing detail surface with copy, and the
rule that both the copy and the detail command **always terminate with a
result** -- a title-less stream still produces a surface naming the station.

**F-11. Track-change announcements are opt-in**, exactly as on Windows, so
ambient chatter never surprises anyone.

**F-12. Recently Played** (capped, de-duplicated), Play Last Station, and
resume-on-launch.

**F-13. Live DVR** -- pause and resume live radio, rewind and forward 30
seconds, and Back to Live, each announcing how far behind live the listener is.
Implemented over the HLS live window where the stream provides one, and over an
app-managed ring buffer for progressive streams.

**F-14. Buffering announcements** on a mid-stream stall, and a spoken, tiered
reconnect narrative rather than silence.

### 3.3 Organizing

**F-15. Favorites Manager** -- nested path-based folders, live rich search,
custom display names used everywhere, folder rename carrying descendants, folder
delete returning stations to the top level, and reordering. On iOS reordering is
available three ways: drag, the VoiceOver **Move up / Move down / Move above /
Move below** custom actions (A-6), and Full Keyboard Access.

**F-16. Sort orders** -- global (A-Z, Z-A, manual) with per-folder override, and
the load-bearing Windows rule that switching to manual **preserves the stored
order and never bakes the sorted view over it**.

**F-17. Station Details** -- the reviewable, copyable details surface for any
station from any list.

**F-18. Backup and restore** -- the `.qrbackup` bundle with its SHA manifest,
importable and exportable through the Files app, so a listener moving devices
carries everything. Path traversal guarded on import, identical to the Windows
implementation.

### 3.4 Sound

**F-19. Sound Enhancements**, per-station and global, with the resolution order
ported (per-favorite override, else the shared default):
- Three-band equalizer, bass/mid/treble, -12 to +12 dB.
- Compressor.
- Channel mode: stereo, mono downmix, left only, right only -- the
  single-sided-hearing feature, with the corrected 2.0.2 pan behavior (the whole
  stereo field to one output, not one source channel duplicated).
- Night mode loudness normalization.
- The OptiLab-derived broadcast modes: Podcast Leveler, Stream Polish, Smooth
  Limiter, with the Input trim and Auto-Adapt controls and the bypass that
  remembers the chosen mode.
- Quick presets (Small Speakers, Late Night).
- **Live preview**: every control takes effect on the playing stream
  immediately, debounced; Cancel reverts to the snapshot taken on open.

**F-20. Output routing** -- AirPlay and Bluetooth route selection through
`AVRoutePickerView`, spoken route changes, and a remembered preference. This is
the iOS analogue of the Windows Output Device picker.

### 3.5 Recording and time-shifting

**F-21. Record now** and **Record a different station**, for a duration, with
the ported settings: format, bitrate, destination, filename pattern with tokens,
and the maximum-duration safety cap.

**F-22. Concurrent recordings** -- the job-manager model ports: independent
jobs, per-job stop, Stop All, per-job reconnect state, a stable job id across a
reconnect, and the configurable concurrency cap with pending-and-retry rather
than a hard refusal.

**F-23. Raw/lossless capture** -- remux the server's packets without re-encoding
where the container allows, choosing the extension from the stream's own codec
and falling back to a universal lossless container. Sound Enhancements and
bitrate are correctly unavailable in this mode.

**F-24. Recordings list** -- live status with a growing size and a live elapsed
time, in-place diff refresh keyed by file path so VoiceOver is never yanked to
the top mid-read, plus Play, Stop, Share, Save to Files, and Remove.

**F-25. Auto-reconnect** with the ported fatal-versus-transient classification
(disk full and HTTP 404/410/451 are fatal; 403, 408, 5xx, and bare EOF
reconnect), the stderr-tail clearing rule so a recovered error cannot poison a
later verdict, and continuation parts that keep the original start timestamp.

**F-26. Crash resume** -- per-job resume markers, reconciliation of stray
temporary files on launch, and the ask/always/never resume choice with its
ten-minute grace window.

**F-27. Scheduled recordings** -- once, daily, weekly; edit in place; duplicate;
enable and disable without deleting; hours-plus-minutes duration entry; 12- or
24-hour time entry; per-entry time zone; the next-occurrence sort with the
stream host shown to disambiguate near-identical rows; and the window-based
"due from start through start plus duration" model with launch catch-up.

**iOS scope note.** Scheduled recording and the wake-up timer depend on the app
being alive at the scheduled moment, and iOS decides that, not the app. See §13
for exactly what is guaranteed, what is best-effort, and how the product tells
the user the truth about it. This is a scope reduction, and it is stated in the
feature's own screen, not buried.

### 3.6 Timers

**F-28. Sleep timer** with the shared fade-and-restore.
**F-29. Wake-up timer** -- once or daily at a set time, within the ported
five-minute firing window, "once" disabling itself. On iOS this becomes a
notification-driven alarm with a one-tap Play action (§13.2).

### 3.7 Shell

**F-30. Customize Features** -- switchable areas (Recording, Weather, Reading
Services, NOAA) that remove whole regions from the interface and from the
VoiceOver focus order.
**F-31. Verbose diagnostics** with a shareable log, and the ported coded errors.
**F-32. In-app documentation** -- user guide, release notes, and this PRD,
readable in the app with full VoiceOver support.
**F-33. QuillVille menu** -- the family navigation surface, listing every
QuillVille app with a link to open or install it.

### 3.8 Non-goals

- **YouTube as a station kind.** The Windows feature depends on yt-dlp
  installed on demand, which iOS cannot do and the App Store would not allow.
  The feature is explicitly absent, not degraded, and the user guide says why.
- Spotify. The Windows integration ships dark behind a feature flag; iOS does
  not carry it at 1.0.
- A general DSP effects rack. Sound Enhancements is a purpose-built three-band
  EQ, compressor, channel control, and loudness stage -- nothing more.
- Any station catalogue built from another product's private data files. Only
  open directories and public APIs, matching the ecosystem's standing rule.
- Advertising, analytics, tracking, an IDFA request, or any third-party runtime
  dependency.
- Re-broadcasting, sharing, or distributing recorded audio. Recording is
  personal time-shifting; the app has no share-to-the-world path for a recorded
  file, only a local save and a system share sheet the user drives.

---

## 4. Accessibility: VoiceOver as the primary interface

Requirements are normative. §5 of the Quill Weather iOS PRD defines the shared
contract (A-1 through A-27); this section states the parts that are specific to
a media application, and the shared ones bind here too.

### 4.1 Focus, structure, and the parity invariant

- **A-1.** What is displayed is what is spoken. There is no separate accessible
  version of any surface.
- **A-2.** Focus lands on the **favorites list** at launch, with the currently
  playing station selected. A focus dead zone is a defect.
- **A-3.** Every list row is one accessibility element with a complete,
  self-contained label -- station name, folder, and state -- so arrowing through
  favorites is a stream of meaningful sentences, never a stream of fragments.
  This is the ported `display_label` and `details_text` discipline.
- **A-4.** Real headings for source, genre, and folder nodes, so the Headings
  rotor navigates the browse tree.
- **A-5.** A hidden control is never a focus stop, and an empty detail region is
  removed from the accessibility tree rather than blanked.

### 4.2 VoiceOver Actions -- the core interaction model

- **A-6.** Actions live on the row, reached by swiping down, so nothing requires
  hunting for a button. Required action sets:
  - **Favorite station:** Play, Record now, Sound enhancements, Rename,
    Move up, Move down, Move above, Move below, Move to folder, Station details,
    Copy stream URL, Report bad station, Remove.
  - **Search or browse result:** Play, Test play, Add to favorites, Add to
    folder, Station details, Report bad station.
  - **Folder:** Play first station, Expand, Collapse, Rename, Sort, New
    subfolder, Delete folder.
  - **Recording row:** Play, Stop, Share, Save to Files, Rename, Remove.
  - **Schedule row:** Edit, Duplicate, Enable, Disable, Delete.
  - **Now Playing:** Play or Stop, Rewind 30, Forward 30, Back to live, What's
    playing, Copy title, Sound enhancements, Sleep timer, Record.
- **A-7.** Volume is an `.accessibilityAdjustableAction` on the Now Playing
  element -- swipe up and down changes volume without leaving the station. The
  volume boost range (to 150 percent for quiet stations) is exposed as an
  extension of the same adjustable, with the boost state spoken in the value.

### 4.3 Custom rotors and the "where am I" problem

- **A-8.** Custom rotors: **Folders**, **Sources**, **Stations**, **Recordings**,
  and **Now Playing**. The Now Playing rotor entry jumps to the transport from
  anywhere in the app -- the single most requested navigation shortcut in any
  media app.
- **A-9.** The ported **focusable status bar** becomes an accessibility-only
  summary element: one element whose value is the whole state sentence ("Playing
  WXYZ, volume 60, boost off, one recording, sleep timer 25 minutes remaining,
  47 favorites"), with the individual cells as its custom actions. F6 on Windows
  becomes a rotor stop and a keyboard shortcut on iOS.

### 4.4 Announcements and speech shaping

- **A-10.** Announcement priority: `.high` only for errors and for a weather
  alert forwarded from Quill Weather; `.default` for user-initiated results
  ("Recording started: WXYZ"); `.low` for track changes, buffering, and
  reconnects. Ambient state never interrupts a user who is reading.
- **A-11.** Identical announcements inside two seconds are suppressed, and
  bursts are coalesced -- the first message of a quiet period is immediate, and
  anything within the following 150 milliseconds settles to the newest. Errors
  are exempt from both rules.
- **A-12.** Track titles are **never truncated**. A long title is a long label.
- **A-13.** Call letters and stream hosts are spoken with
  `accessibilitySpeechSpellsOutCharacters` where character-by-character is
  clearer, and the ported abbreviation-widening applies to spoken metadata.
- **A-14.** A **Concise labels** setting swaps primary labels for the ported
  `compact_braille()` wording so a braille display line stays readable, with the
  full text in Custom Content. Same mechanism as Quill Weather (its A-14).

### 4.5 Gestures and system integration

- **A-15.** **Magic Tap** is Play/Stop, the iOS convention, from anywhere in the
  app and from the Lock Screen when Quill Radio owns the Now Playing session.
- **A-16.** **Escape** dismisses any sheet from any screen.
- **A-17.** Full Keyboard Access and hardware keyboard shortcuts mirroring the
  Windows accelerators where the platform permits: Command-P play/stop,
  Command-T what's playing, Command-Shift-D output device, Command-Shift-E new
  folder, Command-comma settings, Command-F find stations, Command-R record, and
  a Command-hold shortcuts overlay.
- **A-18.** Hardware media keys and headphone controls through
  `MPRemoteCommandCenter`, including the "skip" commands mapped to Rewind 30 and
  Forward 30 for DVR-capable streams.
- **A-19.** Dynamic Type to `AX5` with reflow and no truncation; Reduce Motion,
  Increase Contrast, and Differentiate Without Color honored; Switch Control,
  Voice Control, and Assistive Access supported, with an Assistive Access
  presentation that is favorites plus a transport and nothing else.
- **A-20.** Haptics for buffering, reconnect, recording start and stop, and
  timer fire -- always accompanying speech, never the only signal, always
  disableable.
- **A-21.** **Audio ducking discipline.** VoiceOver speech ducks the stream by a
  configurable amount rather than being drowned by it; this is set through the
  audio session and is verified in the scripted VoiceOver run at maximum volume.
  A screen reader a listener cannot hear over their own radio is a broken app.
- **A-22.** A VoiceOver user can complete first launch, find a station by name,
  play it, favorite it into a new folder, set a sleep timer, and start a
  recording without sighted assistance. Verified per release with the screen
  curtain on.

---

## 5. The playback engine

- **E-1. Two engines behind one protocol**, mirroring the Windows mpv/wx split
  and its silent cross-engine rescue:
  - **Engine A -- AVPlayer.** HLS, DASH-free adaptive streams, and anything
    Apple's stack handles natively. Best battery, best AirPlay, best CarPlay,
    native timed metadata.
  - **Engine B -- AVAudioEngine with a custom stream reader.** A URLSession
    byte stream feeding an `AVAudioConverter` into an `AVAudioEngine` graph.
    This is the engine that carries the ICY side-tap, the DVR ring buffer for
    progressive streams, and **all of Sound Enhancements** (`AVAudioUnitEQ`,
    `AVAudioUnitDistortion`-free dynamics via the dynamics processor audio unit,
    a mixer node for channel mode and boost).
- **E-2.** Engine selection is automatic and per-stream, with **one silent
  cross-engine rescue per play attempt in either direction**, exactly as on
  Windows. The chosen engine is inspectable in diagnostics and in Custom Content
  on the Now Playing element; it is never something the user must choose.
- **E-3.** Format coverage must be at least: MP3, AAC and HE-AAC, Ogg Vorbis,
  Opus, FLAC, and HLS. Ogg and Opus need a decoder the platform does not
  provide; the implementation ships a small, audited, statically linked decoder
  for those two codecs rather than dropping the SomaFM and Radio Reading Service
  streams that use them.
- **E-4.** Background audio via the `audio` background mode and an
  `AVAudioSession` in `.playback`, with correct interruption handling: a phone
  call pauses and resumes; a route change to a disconnected device pauses rather
  than blasting the speaker; a `.shouldResume` interruption end resumes.
- **E-5.** `MPNowPlayingInfoCenter` is kept accurate -- station name, current
  title and artist, artwork where the directory supplies it, and live-stream
  semantics -- because that is what Lock Screen, CarPlay, the watch, and
  VoiceOver's own now-playing surfaces all read.
- **E-6.** A stalled stream produces a spoken, tiered recovery narrative and the
  F-5 healing ladder, never an indefinite silence.

---

## 6. Beyond the app: system surfaces

- **W-1. CarPlay.** A full CarPlay audio app: favorites and folders as list
  templates, a Now Playing template with the transport and DVR controls, tabs
  for Favorites, Recently Played, and NOAA Weather Radio, and a "Play my last
  station" root action. CarPlay is the single strongest argument for this app
  existing on iOS.
- **W-2. App Intents and Siri.** `PlayStation`, `PlayLastStation`,
  `PlayFavorite(folder:)`, `StopPlayback`, `WhatIsPlaying`, `StartRecording`,
  `StopRecording`, `SetSleepTimer`, `PlayLocalNOAAWeatherRadio`. All are
  `AppShortcut`s with natural phrases ("Play my last station on Quill Radio",
  "What is playing on Quill Radio"), all expose favorites as an
  `AppEntity` with a dynamic query so Siri can match a station by its custom
  name, and all return spoken dialog from the shared narrator.
- **W-3. Widgets.** Favorites quick-play (interactive), Now Playing, and a
  Recording status widget. Lock Screen and StandBy families included. Every
  widget carries a complete accessibility label.
- **W-4. Control Center control** for play/stop and for "play my last station".
- **W-5. Live Activity and Dynamic Island** while playing or recording: station,
  current title, elapsed recording time, with transport controls and full
  VoiceOver labels.
- **W-6. Apple Watch app** -- favorites, transport, volume via the crown as an
  adjustable, now-playing complications, and playback control of the phone. A
  standalone-watch streaming mode is a later phase, not 1.0.
- **W-7. Spotlight and Shortcuts.** Favorites are indexed in Spotlight through
  `CSSearchableItem`, so typing a station name in system search plays it.
- **W-8. Action Button and Back Tap** are bound through the App Shortcut.

---

## 7. Sync -- favorites and settings that track either way

The full design is in the platform spec and in §11 of the Quill Weather iOS PRD;
the requirements binding on this app:

- **S-1.** Opt-in, end-to-end encrypted, zero-knowledge, over **QuillSync** --
  the engine that already exists at `quill/apps/beacon/quillsync/`. Three
  transports: an iCloud Drive folder (default, and the reason Windows-to-iPhone
  sync needs no QUILL server), any folder, or the QuillSync server.
- **S-2.** What syncs:

  | Scope | Syncs | Rationale |
  |---|---|---|
  | Favorites: stations, custom names, folder tree, per-station volume, per-station sound enhancements | Yes | The identification set. This is the whole point |
  | Folder sort orders and the global sort preference | Yes | |
  | Recently played history | Yes, capped and TTL'd | Cheap and genuinely useful across devices |
  | Global sound enhancement defaults, channel mode, night mode, OptiLab mode | Yes | |
  | Now-playing template, announcement preferences, concise labels | Yes | |
  | Recording settings: format, bitrate, filename pattern, duration cap, concurrency cap | Yes | |
  | Recording **destination path** | No -- device scope | Meaningless across platforms |
  | Recording schedules | Yes, with a per-device enable flag | The schedule is portable; whether *this* device acts on it is local |
  | Wake-up and sleep timer state | No -- device scope | |
  | Output device or AirPlay route, volume level, engine choice | No -- device scope | |
  | Recorded audio files | Never | Large, personal, and the `.qrbackup` bundle already covers deliberate transfer |

- **S-3.** Entity ids are `shared/...` and `device/<device-id>/...` partitioned;
  merge is field-level last-writer-wins with union merge on the folder tree and
  the favorites list; a station removed on one device and renamed on another is
  a one-tap, spoken conflict resolution.
- **S-4.** Favorite ids become UUIDs on both platforms, since two devices adding
  a favorite independently must not collide.
- **S-5.** The vault key lives in the Keychain, device-only, never synced, never
  sent anywhere. Wire-format parity with the Python implementation is verified
  by a cross-language fixture test in CI.
- **S-6.** Sync status is spoken, with an explicit "Sync now" and a plainly
  worded error that says what to do.

---

## 8. Cross-app behavior with Quill Weather

- **X-1.** Both apps share one App Group container, so a location saved in
  either is present in both immediately on the device.
- **X-2.** **NOAA Weather Radio hand-off.** Quill Weather finds the transmitter
  covering the user's location; Quill Radio plays it. This closes the desktop's
  documented limitation, where Quill Weather can find a transmitter but has no
  audio engine to play it. Reached by App Intent, from Quill Weather's alert
  surface, from Siri, and from CarPlay.
- **X-3.** **Alert ducking.** A `Critical` or `Urgent` weather alert ducks the
  stream, speaks, and restores the previous level. Nothing below `Urgent`
  interrupts audio. This is the cross-app application of the single-player rule.
- **X-4.** Quill Radio carries a Weather surface that reads the shared locations
  and shows current conditions and active alerts, using the shared narrator --
  the direct port of the Windows Weather menu inside Quill Radio. It does not
  duplicate Quill Weather; it offers to open it.
- **X-5.** Neither app requires the other, and each degrades to a described,
  working state alone.

---

## 9. Privacy, security, and network

- **N-1.** Every outbound request goes through one audited chokepoint: HTTPS
  only, system trust store, timeouts, and a `Quill Radio` User-Agent. Every call
  site is inventoried in the ecosystem network-egress audit alongside the
  Windows sites.
- **N-2.** The complete destination list is: the seven directories in F-1, the
  user-typed page for Find Streams plus at most one follow-on provider API call
  to resolve a stream, the playing stream itself, that stream server's own
  same-host status endpoint, and the sync transport if enabled. Nothing else.
- **N-3.** No telemetry, no analytics, no tracking. The Privacy Manifest
  declares no tracking domains. Diagnostics are generated on request, shown in
  full, redacted, and shared only by explicit action.
- **N-4.** **Offline Mode** -- the `QUILL_SAFE_MODE` analogue -- disables every
  network surface in one switch, leaving favorites, recordings, and the bundled
  NOAA and Reading Services snapshots fully usable.
- **N-5.** App Transport Security is left strict. Streams that are HTTP-only are
  refused with a clear spoken explanation and an offer to search for an HTTPS
  equivalent, rather than an ATS exception that weakens every connection.
- **N-6.** Persisted files use Data Protection; secrets use the Keychain.
- **N-7.** Errors are coded with the ported
  `QUILL-<DOMAIN>-<SUBSYSTEM>-<REASON>` scheme.

---

## 10. Distribution

- **P-1.** One universal app: iPhone, iPad, Apple Watch, CarPlay, and Mac
  (Catalyst or native, decided at implementation). App Store only.
- **P-2.** Free, no in-app purchase, no subscription, no account. Identical
  posture to the Windows product.
- **P-3.** MIT-licensed source in the monorepo under `standalone/radio-ios/`,
  with the shared package under `apple/QuillKit/`.
- **P-4.** Third-party notices, including the Ogg/Opus decoder (E-3) and the
  OptiLab attribution for the broadcast-processing chain shapes, ship in the app
  and in `docs/legal/THIRD_PARTY_NOTICES.md`.
- **P-5.** Versioning follows the QuillVille family convention; the iOS app
  starts at 1.0 and is documented in this folder's `CHANGELOG.md` at ship time,
  with the Windows changelog updated for any shared-package change.

---

## 11. Quality and the definition of done

- **Q-1.** The shared narration golden corpus passes in both the Swift and
  Python suites (see the Quill Weather iOS PRD Q-1).
- **Q-2.** `XCUIApplication.performAccessibilityAudit()` runs on every screen on
  every pull request; failures block the build.
- **Q-3.** A scripted VoiceOver run per release covering: first launch, find a
  station by name across sources, test-play, favorite into a new folder,
  reorder by custom action, set per-station sound, start and stop a recording,
  set and cancel a sleep timer, use every rotor, and drive the app entirely from
  CarPlay simulation.
- **Q-4.** Directory contract tests against recorded fixtures, plus a scheduled
  live suite to catch provider drift.
- **Q-5.** Stream-resolver regression suite: every Triton, SecureNet, iHeart,
  TuneIn, and Live365 case that has ever been reported is a fixture, and the
  resolver must still produce the same answer.
- **Q-6.** Long-play soak: eight hours of continuous playback with a scripted
  network interruption, verifying reconnect, DVR integrity, memory stability,
  and that no announcement is lost or duplicated.
- **Q-7.** Battery budget asserted with Instruments for one hour of background
  playback.
- **Q-8.** Done means all of the above pass, the privacy manifest matches the
  actual egress list, third-party notices are current, and the user guide,
  CHANGELOG, and this PRD are updated in the same change.

---

## 12. Phasing

**Phase 1 -- A radio you can actually find a station on.**
QuillKit foundation shared with Weather; the seven directories and unified
search; the favorites tree with folders and custom names; Engine A playback with
ICY and status-endpoint titles; the full VoiceOver contract including custom
actions and rotors; background audio and Lock Screen.
*Ships when a blind listener can find and play an obscure station on a phone.*

**Phase 2 -- The resolver and the sound.**
Find Streams with the full Triton, SecureNet, iHeart, TuneIn, and Live365
ladder; self-healing recovery; Engine B with Sound Enhancements, channel mode,
night mode, and the OptiLab modes; live preview; volume boost; DVR.
*Ships when the app can play stations no other app can find, and sound the way
the listener needs it to.*

**Phase 3 -- The car and the voice.**
CarPlay; App Intents and Siri; widgets; Control Center; Live Activity; Spotlight
indexing; Handoff.
*Ships when the phone can stay in a pocket.*

**Phase 4 -- Recording and time.**
Recording with concurrency, raw capture, auto-reconnect, crash resume, and the
recordings list; sleep and wake timers with the honest iOS scope from §13;
scheduled recordings.

**Phase 5 -- Everything tracks either way.**
QuillSync adoption with the three transports and the scope map; the Windows-side
adapter; backup and restore through Files.

**Phase 6 -- The rest.**
Apple Watch app and complications; iPad and Mac layouts; standalone watch
streaming; the Quill Weather NOAA hand-off in both directions; Radio Reading
Services enrichment.

---

## 13. What iOS cannot do, stated plainly

R-4 requires that these be visible in the product, not only in this document.

**13.1 Scheduled recording is best-effort, not guaranteed.**
Windows can wake a process at 3 a.m. and record. iOS cannot. A `BGProcessingTask`
is scheduled at the system's discretion and may not run. What the product
guarantees:
- A recording scheduled while the app is playing audio in the background **will**
  start, because the audio session keeps the app alive.
- A recording scheduled while the app is not running is attempted through a
  background task and, in parallel, a local notification fires at the scheduled
  time with a **Record now** action, so a listener who has the phone can start
  it with one tap.
- The scheduling screen states this in one sentence, and the app never reports a
  scheduled recording as "will record" when it can only promise "will try."
- The recommended configuration for a listener who depends on scheduled
  recording is stated in the user guide: keep Quill Radio playing, or use the
  Windows app for that recording. Telling the truth is better than a silent
  miss.

**13.2 The wake-up timer is a notification, not an alarm.**
iOS will not let an app start playing audio from a background timer. The wake-up
timer fires a Time Sensitive notification with a **Play** action. If the app is
already running with an active audio session, it starts playback directly. The
screen says which of the two applies.

**13.3 Sound Enhancements are unavailable on some HLS streams.**
Engine A cannot host the filter graph. Where a stream is HLS-only and Engine B
cannot read it, the sound controls are **disabled with a spoken explanation**
naming the reason, rather than shown as controls that silently do nothing.

**13.4 There is no system tray.**
Its roles are covered by widgets, Control Center, the Lock Screen, the Live
Activity, and CarPlay. The global show/hide hotkey has no iOS equivalent and is
replaced by the Action Button, Back Tap, and Siri.

**13.5 YouTube is absent.** See §3.8.

**13.6 Recording is personal time-shifting.**
The app records for the listener's own later use. It offers no re-broadcast, no
publishing, and no sharing surface beyond the system share sheet the user
drives. This posture is stated in the app, in the user guide, and in the App
Review notes.

---

## 14. Open questions to resolve before Phase 2 and Phase 4

1. **Ogg and Opus decoding.** Confirm the licensing and binary-size cost of the
   statically linked decoder (E-3), and confirm it against App Store review.
   Dropping SomaFM and several Radio Reading Services is not an acceptable
   alternative.
2. **ICY metadata on iOS.** Validate the `AVAssetResourceLoaderDelegate`
   side-tap approach against a representative set of Icecast and SHOUTcast
   servers before committing; the same-host status endpoint fallback must cover
   whatever it misses.
3. **DVR ring buffer sizing** for progressive streams -- the Windows engine
   offers roughly 45 minutes; determine what is reasonable on device given
   memory and disk, and make it a setting.
4. **App Review posture on recording.** Prepare the review notes and the
   demonstration script for §13.6 ahead of first submission.
5. **CarPlay entitlement.** The audio app category requires Apple approval;
   apply early, because it gates Phase 3.
6. **Background task budget** with concurrent recordings -- measure before
   promising a concurrency cap default above one on iOS.
7. **Directory rate limits at App Store scale.** Radio Browser, RadioTime, and
   the iHeart content API were sized for a desktop app's traffic. Confirm each
   one's terms and add client-side rate limiting and a shared cache before the
   install base makes it someone else's problem.

---

## 15. Relationship to the existing documents

- The Windows Quill Radio PRD (`standalone/radio/docs/prd.md`) remains the
  authoritative specification for the shared radio **domain**: the resolver
  ladder, the favorites model, the recording state machine, the sound-enhancement
  chain, and the settings keys. This document specifies the **iOS product**.
  Where the two disagree, the Windows PRD wins on domain semantics and this
  document wins on iOS delivery.
- Improvements discovered here -- UUID identifiers, rate limiting, the honest
  scheduled-recording wording -- flow back to the Windows product under R-4 of
  the Quill Weather iOS PRD's shared rule.
- `quillville-apple-platform-spec.md` owns QuillKit, QuillSync adoption, the
  narration golden corpus, the shared accessibility contract, and the Apple repo
  layout, and is shared with Quill Weather for iOS.
