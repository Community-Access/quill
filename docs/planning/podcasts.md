# Podcasts in QUILL — Design Spec

- Status: Phase 1 shipped (0.9.0 Beta 3) — brainstormed 2026-07-13; Phase 2-5 (§20) remain planned, not yet built.
- Sources: `docs/planning/radio.md` §3 (the original, lighter sketch this supersedes), the ACB Link research from that same session (its ~37-show OPML subscription list was the concrete example for the OPML shape), QUILL's existing Audio Studio/publish stack (`core/speech/audiobook.py`, `core/speech/audio_edit.py`, `core/publish/*`), and a live Q&A session with Jeff.
- Companion feature: Internet Radio (already shipped, PR #987). Podcasts follows the same architectural instincts — reviewed egress per external call, atomic JSON persistence, dedicated background work instead of ad hoc threads, reuse over reinvention — but is a substantially larger feature, closer in size to Radio-plus-Audio-Studio than to Radio alone.

## 1. Data model

```
PodcastFolder                        # organizes SHOWS; a show lives in exactly
  id, name                           # one folder (or none = top level).
  parent_folder_id: str | None       # arbitrarily deep nesting (adjacency list;
                                      # no fixed depth limit).

InboxFolder                          # a SECOND, independent nested tree, only
  id, name                           # for organizing episodes inside the Inbox
  parent_folder_id: str | None       # (see §9). Unrelated to PodcastFolder.

PodcastShow
  id, title, feed_url: str | None    # None only for is_local shows
  homepage, artwork_url
  is_local: bool                     # true = imported from local files (§12)
  folder_id: str | None              # library placement (PodcastFolder)
  is_favorite: bool                  # §10
  paused: bool                       # subscription paused (§2): no feed
                                      # refresh, no new episodes, no
                                      # auto-download -- show and its full
                                      # existing catalog/history stay in the
                                      # library exactly as they are
  route_to_inbox: bool               # §9
  inbox_default_folder_id: str | None  # "remembered" auto-file target (§9)
  settings: PodcastSettings | None   # None = inherit the global defaults

PodcastEpisode
  guid, title, audio_url, published, duration_seconds, description
  chapters_url: str | None           # Podcasting 2.0 <podcast:chapters>
  transcript_url: str | None         # Podcasting 2.0 <podcast:transcript>
  transcript_type: str | None        # text/vtt, application/json, text/srt, ...
  downloaded_path: str | None        # local file, once downloaded
  mode_override: "stream" | "download" | None   # None = follow the show setting
  played: bool
  position_ms: int                   # resume position (§8)
  inbox_folder_id: str | None        # only meaningful if the owning show
                                      # routes to the Inbox (§9)

PodcastSettings                      # one global record; a show only stores
  playback_mode: "stream" | "download"   # the fields it overrides
  retention: "keep_all" | "keep_last_n" | "delete_after_play"
  retention_count: int               # used only when retention == keep_last_n
  speed: float                       # 0.5-3.0x, default 1.0
  always_sync_full_catalog: bool     # §14 -- backfill the whole feed, not just new
  auto_trim_silence: bool            # §15
  normalize_loudness: bool           # §15
  download_root: Path                # global only, not per-show (§13)
  skip_forward_s: int                # global only (§5), default 30
  skip_back_s: int                   # global only (§5), default 15
  volume_boost: float                # global only (§5), live-playback gain

PlayQueue                            # cross-show, ordered (§11)
  entries: [(show_id, episode_guid), ...]
```

## 2. Discovery, subscription, manual add

- **Discovery**: iTunes Search API (`itunes.apple.com/search?media=podcast`) — free, keyless, same reviewed-egress pattern as `core/radio/radio_browser.py` (a new `core/podcasts/itunes_search.py::_http_json`, HTTPS-only, Safe-Mode gated, registered in `network_egress_audit.py`).
- **Add by Feed URL...** — paste any RSS URL directly, same shape as Radio's Add Custom Station. Covers shows iTunes doesn't index and self-hosted feeds.
- **Subscribing**: fetch the feed and parse it with **`feedparser`** (a new, small, pure-Python dependency — MIT-licensed, no C extensions) rather than hand-rolled `ElementTree`. Real-world podcast feeds are messier than the simple HTML link-scanning `link_finder.py` handles (malformed XML, encoding quirks, mixed RSS/Atom/iTunes/Podcasting-2.0 namespaces), and getting "rich episode data" — `itunes:duration`, `itunes:image`, `itunes:episode`/`season`, `itunes:explicit`, `itunes:summary`, plus the `podcast:chapters`/`podcast:transcript` tags — reliably needs a real feed parser's tolerance and namespace handling, not a second hand-rolled XML walker. `feedparser` is the standard choice for exactly this in the Python ecosystem. Add as a normal (always-installed) dependency in `pyproject.toml`, not an on-demand optional component — it's pure Python and tiny, unlike the heavier optional pieces (Pandoc, speech engines) QUILL downloads on demand.
- **Private feeds**: HTTP Basic auth, credentials in the OS credential store via the same pattern as `core/publish/destinations.py` (never plaintext, unlike FastPlay's SQLite columns).
- **Duplicate detection**: subscribing to (or OPML-importing) a feed URL that's already subscribed updates/merges rather than creating a second show.
- **Defensive feed parsing** (two real-world edge cases worth guarding against explicitly): a single episode with a bad future-dated `<pubDate>` must not poison the "what's new since last check" high-water mark and silently blackhole every subsequent real episode; and if a feed republishes an old episode under its same GUID with a newer date, it should only resurface in New Episodes/Inbox if it was untouched backlog — anything already played/started/queued/cleared stays exactly as it was, never resurrected by a feed's own misbehavior.
- **Pause / Resume Subscription**: stops feed refresh and auto-download for a show entirely while keeping it, its full episode catalog, and all history exactly as-is in the library — distinct from `playback_mode` (which governs *how* an actively-syncing show's episodes are obtained, not whether it syncs at all).
- **Unsubscribe** removes a show from the library; reachable from the context menu and via the **Delete** key when a show is focused in the tree/list (with the same confirmation as the context menu action — Delete is a shortcut to the same guarded action, not a silent bypass of it).

## 3. OPML import/export

- Exports the **library only**: every non-local show, nested inside `<outline text="Folder Name">` elements that mirror the `PodcastFolder` tree exactly (a folder-in-a-folder becomes a nested `<outline>`).
- Import reconstructs that same folder tree from the nesting, creating any folder that doesn't already exist by name, and merges into existing subscriptions rather than duplicating.
- **Excluded from OPML, both directions**: local/imported podcasts (§12, no feed URL to export) and the Inbox and its folder tree (§9, a local curation layer with no OPML equivalent).

## 4. Downloads

- A dedicated `PodcastDownloadQueue` — its own background worker thread (not the shared `QuillTaskManager` pool), modest concurrency cap (~3 at a time, matching FastPlay's own choice), so a backlog of podcast downloads never competes with or slows down other QUILL background work (AI calls, transcription, etc.).
- Files land at `<podcast storage location>/<show-slug>/<episode-file>.<ext>` plus a `chapters.json` sidecar when the feed doesn't already point at one — mirrors the audiobook-build sidecar convention in `core/speech/audiobook.py`.
- **Storage location is a global setting** (`PodcastSettings.download_root`), defaulting to `<data_dir>/podcasts` but pointable anywhere, same pattern as QUILL's existing data-location setting.
- **Auto-download**: a show set to `playback_mode: "download"` auto-queues new episodes as soon as a feed refresh finds them (periodic + on-launch refresh). Streaming-mode shows never auto-download. A per-episode `mode_override` lets any single episode go against its show's default in either direction (e.g. keep one episode of a normally-streamed show offline for a flight).
- **Pause / Resume Downloads** — two genuinely independent controls, not one setting wearing two hats:
  1. **Pause All Downloads / Resume All Downloads** (global, status bar/queue-view control): stops the worker from *starting* any new transfer. Anything already mid-transfer when this is pressed keeps running to completion — this toggle only affects what starts next, not what's already in flight.
  2. **Pause This Download / Resume This Download** (per-item, in the queue view and the episode context menu): immediately halts that one transfer's byte stream mid-flight, wherever it currently is — queued-but-not-started (trivially, just don't start it) or actively downloading (stop reading from the connection right now, don't wait for it to finish). Either way the partial bytes already written stay on disk. Resuming that item issues an HTTP `Range` request to continue from that exact byte offset when the server supports it (most podcast hosts do), falling back to a clean restart-from-scratch on hosts that don't support ranged requests rather than failing outright.
  Both controls compose normally: All-Paused doesn't erase a per-item Pause's state, and resuming one specific item while All Downloads is still paused simply re-queues it to run once All Downloads resumes.
- **Retention** runs after each successful download: `keep_last_n` prunes the oldest kept episode(s) past the count; `delete_after_play` removes the local file once an episode is marked played (by finishing playback or by an explicit "Mark as Played"); `keep_all` never prunes.
- **Always Sync** (`always_sync_full_catalog`, per show): in addition to the routine "check for episodes newer than what I have" refresh every show gets, a show with this on also backfills every older episode the live feed still exposes into the local catalog — and downloads them too, if that show is in download mode. Note for implementation: this is in tension with `keep_last_n` (backfilling the whole catalog while immediately pruning to N fights itself), so the settings UI should nudge toward `keep_all` when Always Sync is on rather than silently contradict itself.
- **Auto-trim silence** (optional, per show): trims dead air from a downloaded episode's start/end using the exact same silence-trim function (`core/speech/audio_edit.py`) the audiobook builder already uses.
- **Loudness normalization** (optional, per show): levels out volume using the same ACX loudness-normalization ffmpeg pass the audiobook builder already runs.

## 5. Playback

- Downloaded episodes reuse Audio Studio's existing chapter-aware `PlayerPanel` (Play/Pause/Stop/Prev/Next chapter, position slider, speed, chapter-crossing announcements) — no new transport UI.
- Streaming (not-yet-downloaded) episodes play the same way, straight from the enclosure URL, through the same engine — unlike Radio, this works fine with the duration-gated mpv backend too, since a podcast episode is a bounded file with real `Content-Length`/duration, not an infinite live stream.
- **Configurable playback speed**: **0.5x-3.0x in 0.1x steps**, exposed on the PlayerPanel's existing speed control (`set_rate`, already part of the audio engine protocol — no new engine work) plus dedicated Speed Up/Speed Down hotkeys. Two-level setting, same global-default-with-per-show-override pattern as everything else in `PodcastSettings`: `PodcastSettings.speed` is the global default every show starts at; adjusting speed while an episode is playing updates *that show's* remembered speed (not the global default), so a normally-fast-talking show and a normally-slow one can each keep their own comfortable rate without fighting each other every time you switch between them. A **Reset to Global Default** action on the per-show settings clears the override.
- **Configurable skip intervals** (global setting, e.g. default 30s forward / 15s back): the Prev/Next-style skip buttons/hotkeys use these instead of one fixed value.
- **Volume boost**: a separate live-playback gain control (distinct from the download-time loudness normalization in §4) for pushing quiet audio louder on the fly, without reprocessing the file.
- **Sleep timer**: stop after N minutes, or at the end of the current episode/chapter — a control on the PlayerPanel/status bar, no new playback engine work. Radio should get the same control for parity (tracked in `docs/planning/radio.md`'s follow-ups, not part of this spec's build).
- **Audio backend dependency, addressed directly**: both this feature and Radio ultimately depend on `wx.media`, which ships with wxPython itself — not an optional/downloadable component, always present on a normal QUILL install. mpv (gapless/exact-seek) is a pure enhancement layered on top when the on-demand `engine-packs/mpv` component is installed, with automatic fallback to `wx.media` already built into `create_engine()`. So there is no real "component might be missing" gap for basic playback on a supported OS. The one genuine edge case (a stripped Windows install with no Media Player component at all) is handled with a **startup capability check**: if constructing any audio engine fails outright, `Tools > Media` (both Radio and Podcasts entries) is disabled with an explanatory message, rather than presenting a feature that only fails when you try to use it.

## 6. Chapters

- Read the Podcasting 2.0 `chapters.json` link when present (works even while streaming, before download) — the read-side companion to the same sidecar format `core/speech/audiobook.py::write_book_sidecars` already writes.
- Falls back to ID3 chapter frames (CHAP/CTOC) read via `mutagen` once a file is downloaded, for the many shows that only embed chapters in the file itself.
- **View Chapters...** lists title/start-time/duration per chapter; selecting one jumps playback there.

## 7. Transcripts & export

- If the feed carries a `<podcast:transcript>` link: **Save Transcript As...** (to a file) and **Open Transcript in Editor** (opens as a new QUILL document — the transcript is never overwritten, matching how the Listening Companion already handles results).
- If absent (the common case today): **Transcribe Episode...** routes the downloaded audio through QUILL's existing transcription engines (whatever's installed/configured — Whisper, faster-whisper, Vosk, cloud providers), the same `core/ai/transcription.py` path the Listening Companion already uses. Requires the episode downloaded first (offers to download if it isn't).
- Either way, the resulting transcript can chain straight into **Transcript Actions** (Executive Summary, Show Notes, Key Quotes, etc.) — the real "why QUILL and not a standalone podcast app" story.
- **Export...** on one or more selected episodes copies the downloaded audio file(s) to a folder you choose; offers to download first if an episode isn't downloaded yet. Exported files are named from the real show/episode title ("Show Name - Episode Title.mp3"), never QUILL's internal filename.

## 8. Resume position & cross-device sync

QUILL Sync (shipped Beta 3) is "point your data directory at a Dropbox/OneDrive/Google Drive folder" — QUILL just writes JSON there, the sync client does the rest, no bespoke sync engine to build. The design work here is entirely about making sure the *right* things are small, JSON, and keyed correctly:

- **The episode catalog is durable, not an ephemeral re-fetch.** Each show's known-episode list is persisted locally (small text metadata only) and merged on every feed refresh, never wholesale-replaced — an episode is never silently dropped from your catalog just because it scrolled off the live feed. This is what makes "see the same state on a different machine" possible at all.
- **Resume position and played state are keyed by `(feed_url, episode_guid)`**, never by `downloaded_path` — so a position recorded on a machine that has the file downloaded is still meaningful on a machine that doesn't; QUILL offers to stream or download starting from that point.
- **What travels through the sync folder**: subscriptions, library folders, per-show settings, the episode catalog metadata, played/position/queued/favorited state. **What never does**: the audio files themselves (too large) and anything local-only (§12).
- Honest limit: "loading older episodes" is bounded by what the source feed actually exposes. Some hosts paginate their full archive, most don't. QUILL keeps everything it's ever seen forever once seen, but can't invent episodes a feed has genuinely stopped listing anywhere.

## 9. Organization: library folders vs. the Inbox vs. Favorites

Three independent ways to organize, deliberately not unified into one tree:

- **Library folders** (`PodcastFolder`) organize *shows*. A show lives in exactly one folder (or none), arbitrarily nested. This is "where the show is filed."
- **The Inbox** (`InboxFolder`, a second, independent nested tree) organizes *episodes*, cutting across library folders entirely. A show marked `route_to_inbox` has all its new episodes appear in the Inbox regardless of its library folder. Inside the Inbox, episodes can be manually filed into Inbox-only folders unrelated to the library structure. The first time you manually move an episode from a given show into an Inbox folder, QUILL remembers that folder for that show (`inbox_default_folder_id`) and auto-files future episodes from it there — "last manual placement wins," with a **Forget Remembered Folder** action to go back to manual filing. Inbox and its folders are excluded from OPML export (§3) and are pure local curation.
- **Favorites** is not a folder at all — a boolean flag (`is_favorite`) on a show, surfaced as a pinned virtual node (§10) so favoriting never forces a choice between "properly filed" and "starred."

## 10. Virtual views

Three pinned nodes at the top of the library folder tree, alongside the real folders:

- **Favorites** — every show with `is_favorite`, regardless of real folder.
- **New Episodes** — every unplayed episode across all subscriptions, newest first (an inbox-style aggregate; distinct from the curated Inbox in §9). Surfaces through QUILL's existing notification system (`core/notifications.py`) the same way other background-produced events already do — **off by default, opt-in per show** ("notify me about new episodes of this show"), and never a nag: exactly one notification per new episode, never a digest/reminder/inactivity ping. This mirrors the discipline Earshot's research surfaced as worth copying literally: notifications inform, they don't pester.
- **Continue Listening** — in-progress episodes (partial `position_ms`, not yet played) across all shows, most-recently-listened first. Pairs directly with §8's resume-position data; no new state needed to populate it.

## 11. Play Queue

- Cross-show, ordered list (`PlayQueue`) — **Play Next** / **Add to Queue** on any episode; plays through in sequence.
- Reordering is two-tier: **Move Up / Move Down** for single-slot nudges, plus **Mark for Move** on one item followed by **Move Marked Item Above/Below** on a target item for long-distance moves without repeated nudging — matches QUILL's existing accessible-reordering pattern (e.g. Interactive Rebase's commit list).
- **Remove from Queue** / **Clear Queue**.

## 12. Local (imported) podcasts

- **Add Local Podcast...** — pick one or more audio files (mp3/wav/m4b/m4a), or a whole folder of them. QUILL copies them into the podcast storage location under a new show, one episode per file, title guessed from the filename (reusing `core/speech/audiobook.py::title_from_filename`). A file's own chapters (an m4b's, or an mp3's ID3 chapters) populate that episode's chapter list exactly like a downloaded feed episode's would — no new chapter machinery.
- `is_local: true`, `feed_url: None`. Not exported to OPML (§3). **Not synced**: since QUILL Sync works by pointing the entire configured data directory at a synced folder, "not synced" has to be structural, not a promise — local-podcast records need to live in a path that is never inside that user-configured (possibly-synced) data directory, so it's impossible for them to end up in Dropbox/OneDrive by construction. Exact path TBD at implementation time (likely alongside any other existing genuinely-machine-local QUILL state, if a precedent exists).
- **Watched folder** (Downcast-inspired): optionally point a local podcast at a watched folder (reusing QUILL's existing watch-folder infrastructure, `core/watch_audiobook.py`'s pattern) so any audio file dropped there automatically becomes a new episode of that local show — no manual re-import needed for an ongoing local source (e.g. a folder your own recording workflow already drops files into).

## 13. Episode notes/annotations

- Attach a timestamped note to a moment in an episode, reusing QUILL's existing Sticky Notes / Inline Notes system rather than building a parallel one.
- A **My Notes in this Episode** list on the episode view jumps to any note's timestamp.
- The most QUILL-native idea in this spec — no mainstream podcast app does this, and it directly follows from QUILL already being a notes-and-writing tool, not just a player.

## 14. Sorting & filtering

A View/Sort toolbar above both the show list and the episode list, remembered between sessions (same pattern GitHub Items' Columns... already uses):

- **Shows**: sort by Title A-Z, Date Subscribed, Latest Episode Date, Unplayed Count. Filter: All / Favorites Only / Has Unplayed Episodes.
- **Episodes**: sort by Publish Date (newest/oldest), Title A-Z, Duration. Filter: All / Unplayed / Played / Downloaded / Not Downloaded.
- **Local search**: context-aware by default — searching from the episode list searches only that show's episodes, searching from the show list searches only shows, etc. — plus an always-visible **Search Everywhere** action that broadens to every subscription/episode/transcript/note at once, grouped by type. Avoids the common failure mode where a scoped search silently misses something because you searched from the wrong screen. Separate from the iTunes discovery search used for finding new shows.

## 15. Rich context menus

- **Show**: Play/Pause (acts on whatever's currently playing from this show, or starts the latest episode if nothing is), Play Latest Episode, Stop, Move to Folder..., Edit Settings... (mode/retention/speed/Always-Sync/trim/normalize overrides), Toggle Favorite, Toggle Route to Inbox, Forget Remembered Inbox Folder, Pause/Resume Subscription, Unsubscribe (also: **Delete** key), Open Homepage, multi-select bulk variants (mark all played, move several to a folder at once, pause/resume several at once).
- **Folder** (library or Inbox): New Subfolder..., Rename, Move..., Delete (asks what happens to shows/episodes inside — move to parent or Uncategorized), Export as OPML... (library folders only).
- **Episode**: Play/Pause, Stop, Play/Stream, Download, Pause Download / Resume Download (only enabled while this episode is queued or actively downloading — see §4's two independent pause controls), Remove Download, Mark Played/Unplayed, Play Next / Add to Queue, View Chapters..., View/Add Notes..., Transcribe Episode... / View Transcript, Save Transcript As..., Open Transcript in Editor, Export..., Show Notes (description), Copy Episode Link, multi-select bulk variants (download all selected, export all selected, mark all selected played/unplayed).
- **Queue item**: Play Now, Play/Pause, Remove from Queue, Mark for Move, Move Marked Item Above/Below, Move Up, Move Down (§11).

## 16. UI surfaces summary

- **Podcast Manager** (`Tools > Media > Podcasts...`, extending the submenu Radio already created) — a folder tree (`wx.TreeCtrl`, the one place in this feature a real tree fits, since folders genuinely nest) on the left, episode/show list with the sort/filter toolbar on the right.
- **Add Podcast**: search (iTunes), Add by Feed URL..., Import OPML..., Add Local Podcast... all reachable from one place.
- **Preferences > Podcasts**: the global defaults (mode, retention, count, speed, storage location, auto-trim, normalize).
- **Command palette**: `podcasts.open_manager`, `podcasts.add_by_url`, `podcasts.import_opml`, `podcasts.export_opml`, `podcasts.add_local`, following the same `try_register` + `feature_id="core.podcasts"` pattern Radio used.
- **Status bar + hotkeys**: play/pause/stop mirroring Radio's pattern, plus the sleep-timer control, for background listening while writing. Speed Up/Speed Down hotkeys adjust the current show's remembered speed live.
- **System tray**: extends the tray section Radio already created with a Podcasts block — Play/Pause, Stop, and both download controls (**Pause All Downloads / Resume All Downloads**, plus **Pause/Resume** for whichever single download is currently active) — so you can manage downloads without restoring the window.

## 17. Accessibility engineering notes (from the Earshot research)

- **Name every dismiss action explicitly.** A modal/dialog's close control should announce what closing it does ("Dismiss folder queue sheet"), not a bare generic "Close" — already QUILL convention, worth holding to deliberately here given how many new dialogs this spec adds (§16).
- **Don't wrap a whole panel's contents in one auto-focused container.** Focus should land on a heading, with the panel's actual controls individually navigable — an eagerly-summarized container can look fine visually and read terribly. Test every new dialog in this spec individually with a screen reader rather than assuming one dialog's pattern generalizes to the next.
- **Trust native controls over hand-rolled semantics.** Prefer real wx controls (checkbox, radio, slider) over custom-drawn equivalents with manually-attached accessible roles — the native control gets the role/state right for free.
- **Give list rows a meaningful preview, not just a title.** An episode row in the Inbox/Queue/show list should read a short show-notes preview after the title, so browsing the list tells you what an episode is about without drilling in — directly applicable to the show/episode lists in §16.
- **Destination screens should announce themselves on open** (e.g. opening chapters announces "Chapters" and exposes that as a heading), so navigating somewhere is audibly confirmed, not just visually apparent.
- **Every reorderable list needs a non-drag path.** The Play Queue's Move Up/Down + Mark-for-Move design (§11) already satisfies this by construction — no drag gesture required anywhere in this spec.
- **Long operations get live-region progress announcements**, not silent progress bars — applies to OPML import (§3), downloads (§4), and transcription (§7).

## 18. Architecture sketch

```
quill/core/podcasts/
  models.py             # the real dataclasses from §1 (PodcastFolder, Show,
                        # Episode, Settings)
  itunes_search.py     # discovery client -- mirrors core/radio/radio_browser.py
  feed_reader.py         # RSS/Atom parsing via feedparser (§2), chapters/
                         # transcript tag extraction
  opml.py               # import/export, folder-tree <-> nested <outline>
  subscriptions.py      # atomic-JSON store: shows, folders, settings, catalog,
                         # resume/played state -- the syncable half (§8)
  local_store.py        # atomic-JSON store for is_local shows -- the
                         # deliberately non-synced half (§12)
  download_queue.py     # PodcastDownloadQueue, its own thread (§4)
  inbox.py              # InboxFolder tree + routing/remembered-folder logic (§9)
  queue.py              # PlayQueue (§11)

quill/ui/podcasts/
  manager_dialog.py      # the Podcast Manager (§16)
  add_podcast_dialog.py  # search/URL/OPML/local-import entry points
  settings_dialog.py     # per-show settings override
  episode_notes_panel.py # §13

quill/ui/main_frame_podcasts.py   # mixin: menu, commands, keymap, status bar,
                                   # tray -- follows main_frame_radio.py exactly
```

## 19. Explicitly out of scope (this spec)

- Skip-intro/outro beyond the optional silence-trim already in §4 (no dedicated "detect and skip the sponsor read" feature).
- Video podcasts (audio only, matching QUILL's existing audio-only scope everywhere else) — confirmed again during a later pass over Overcast/Downcast/Castro/Apple Podcasts; none of their ideas change this.
- Social features (comments, sharing to other users, public playlists).
- A bespoke QUILL-hosted sync service — sync is entirely QUILL Sync's existing folder mechanism (§8), never a new server.
- **Considered from the Earshot research and explicitly declined for this spec** (not oversights — real ideas, deliberately left out): a whole listening-stats/analytics feature area (time listened, time saved, streaks, year-in-review, CSV export), and reorderable user-configurable "Quick Actions" that redefine the default per-content-type action — both would be sizable scope additions on top of an already-large spec; either could become its own follow-up spec later if wanted.
- Queue/Inbox freshness expiration with a "Recently Expired" undo buffer — considered, not added; file-retention policy (§4) covers the "don't keep everything forever" need for downloaded files, and this spec's Inbox (§9) has no separate staleness-expiry mechanism of its own.
- Mono audio mode — considered, not added.
- **Considered from a pass over Overcast/Downcast/Castro/Apple Podcasts, explicitly declined**: Overcast-style **Smart Speed** (continuously detecting and skipping silence *during live playback*, not just trimming dead air at an episode's start/end) — a real, different, and meaningfully bigger feature than the download-time silence-trim already in §4 (needs real-time audio analysis while playing, not a one-time ffmpeg pass); **rule-based smart playlists** (e.g. "all unplayed episodes from these three shows, newest first, auto-updating") beyond the manual Play Queue in §11; and an AI-based noise-reduction/"enhance" filter for poor-quality recordings (Apple Podcasts' Enhance Recording). All three are real ideas worth a future spec of their own, not silently folded into this one this late.

## 20. Suggested phasing

Everything above (through §17) is in scope; this is a build order, not a cut list.

1. **Phase 1 — core loop**: data model, iTunes search + Add by Feed URL, RSS parsing, dedicated-thread download queue (incl. pause/resume, §4), library folders (nested), OPML import/export, playback via the reused PlayerPanel, configurable speed.
2. **Phase 2**: chapters, skip intervals, transcripts + export, resume position and the durable/synced episode catalog.
3. **Phase 3**: Favorites/New Episodes/Continue Listening virtual views, sorting/filtering (incl. Search Everywhere), rich context menus, local search.
4. **Phase 4**: Play Queue (reorderable), the Inbox (separate tree + remembered routing), local/imported podcasts, watched-folder auto-import.
5. **Phase 5**: sleep timer, auto-trim silence, loudness normalization, volume boost, episode notes/annotations, Always Sync.

**Phase 1, as shipped — two deviations from the sketch above, both deliberate.**
Playback does *not* reuse the embeddable `PlayerPanel`: that panel is owned
by whatever dialog holds it, which would tie playback lifetime to the
Podcast Manager dialog and violate the single-active-playback rule ("if I
start playing another episode it should stop and start the new episode
automatically, no two things playing at once"). Playback instead uses a new
`quill/ui/podcasts/player_controller.py` (`PodcastPlayerController`),
mirroring `core/radio/player_controller.py`'s shape exactly: one instance,
owned by `MainFrame` for the process's lifetime, that every dialog drives
but none of them own. Rich context menus (§15) and configurable per-show
speed (§5) — both listed as Phase 3/Phase 1 items respectively above — were
pulled forward and shipped in this same Phase 1 pass rather than split
out, since the underlying UI surfaces (the episode list, the tree, the
player row) already existed and the marginal cost of wiring them in was
small. `local_store.py`, `inbox.py`, and `queue.py` from §18's sketch are
not yet built — they land with Phases 3-4 as planned.
