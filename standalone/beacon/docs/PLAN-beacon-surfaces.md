# QuillBeacon -- Integration Plan Across All Surfaces

Where QuillBeacon lives, where it could live, and how each surface connects.
This is the builder's view of Beacon as a hub that many surfaces feed and read.
For the QuillSync framework integration into the companion apps (Quill, Radio,
Cast, iOS), see `Docs/PLAN-quillsync-integration.md`; this document is about
Beacon's own surfaces and the contracts between them.

## 0. Beacon's role

QuillBeacon is the "find your way back to anything" hub. Other surfaces either
**feed** it (capture a place into the library) or **read** it (resolve a saved
place back to its exact location). Beacon owns the library, the ULD, the
search grammar, and the sync root. Every other surface is a thin edge that
talks to Beacon over a small, stable contract -- never by reaching into its
database.

The contracts are deliberately tiny so a surface can be built without Beacon
present and vice versa. Each contract below states: direction (feed/read),
transport, auth, fail-safe behavior, and what is in vs. out of scope here.

## 1. Surface inventory

| Surface | Status | Direction | Contract |
|---|---|---|---|
| Desktop app (this repo) | Built | Both | Native; the reference |
| Browser extension (Chromium) | Built | Feed | Capture bridge HTTP |
| Browser extension (Firefox) | Built | Feed | Capture bridge HTTP |
| Capture bridge (localhost) | Built | Feed | HTTP, bearer token |
| QuillSync server (reference) | Built | Read/sync | HTTP JSON, magic-link auth |
| CLI | Built | Read/feed | `python -m quill_beacon.sync_ui` (verify) and `quill_beacon.cli` (capture/search/export) |
| System tray / status center | Built | Read | In-app |
| External media player | Built | Read | Subprocess handoff |
| Quill (editor) | Planned | Feed + read | Native messaging + sync scope |
| Quill Radio | Planned | Feed + read | Sync scope + capture |
| Quill Cast | Planned | Read | Sync scope (publish state) |
| iOS (Quill Pocket) | Planned | Feed | Sync scope; plan only |
| Web (read-only publish) | Built | Read | Static HTML + localhost preview, publish token |
| OS integrations (future) | Possible | Feed | Share sheet, quick action |

## 2. Desktop app (this repo) -- the reference surface

Status: built. The desktop app is the canonical surface and the integration
reference for every other surface. It owns the `BeaconStore`, the ULD resolver,
the search engine, the QuillSync root, and the accessible shell.

What it provides to other surfaces:
- The capture bridge (section 3) for browser extensions.
- The QuillSync root and server (section 4) for companion-app sync.
- The CLI (section 5) for automation and headless verify.
- The `quillsync://verify` scheme handler (section 5) for magic-link handoff.

In scope here: everything. Out of scope: changes in other repos (plan only).

Second-pass completions (all in-repo, tested): an attachments UI (Edit >
Attachments), a trails step-through view (sidebar + TrailStepDialog), a Smart
Collections manager (Tools > Smart Collections Manager), bulk add-to-collection
and bulk remove-tag, on-demand health revalidation (Tools > Revalidate Health,
injectable fetcher, no network by default), an optional auto-sync timer
(Sync > Auto Sync, off by default), cross-device vault pairing (Sync Settings
> Pair Device), server hints in the Status Center, incremental sync commits
(schema v2: `beacons.updated`/`dirty` + `beacon_tombstones`), and a conflict
review flow in Sync History (Use Local / Remote / Merged).

Third-pass completions (all in-repo, tested): a headless CLI
(`quill_beacon.cli`: `capture`/`search`/`export` subcommands, wx-free, sharing
the same on-disk store), a native messaging host fallback for the capture
bridge (`quill_beacon.native_messaging`: stdio protocol reusing
`CaptureBridge.handle_capture`/`handle_batch`, cross-platform host-manifest
registration, extension fallback in both extensions' `background.js`), a
configurable external player (`external_player.PlayerSettings`: custom path +
per-type player preference, Tools > External Player..., honored by
`_on_play_external`), and editing existing collections via the Collection
Editor (Tools > Collection Editor..., Ctrl+Shift+C: edits the selected
collection in place by `collection_id`, creates when nothing is selected).

## 3. Browser extensions -- feed surface

Status: built (Chromium MV3 and Firefox MV3). The extensions gather context
from a page -- whole page, selection, nearest heading, link, or media time --
and POST it to the capture bridge.

Contract:
- Transport: HTTP to `127.0.0.1:<port>` (port discovered from
  `bridge_port.txt` in the data dir; default 8752).
- Auth: bearer token (the bridge token), checked with `secrets.compare_digest`.
  Origin/scheme check: only `chrome-extension://`, `moz-extension://`, and the
  loopback are accepted.
- Endpoints: `GET /health` (public), `GET /collections`, `GET /token`,
  `POST /capture`, `POST /capture-batch`, `OPTIONS` (CORS preflight).
- Fail-safe: if the bridge is down, the extension tells the user plainly and
  saves nothing. It never silently drops a capture. The bridge has its own
  `BeaconStore` connection (`check_same_thread=False`, `busy_timeout=5000`) so
  the HTTP thread never touches the app's connection.

Integration points for later:
- Native messaging host fallback: built. When the loopback bridge is blocked,
  the extension falls back to `chrome.runtime.connectNative` talking to
  `quill_beacon.native_messaging` (host name
  `com.communityaccess.quillbeacon`). The browser enforces which extension may
  reach the host via the manifest's `allowed_origins`/`allowed_extensions`, so
  the host trusts the stdio channel and does not re-check the bearer token.
  Register with `python -m quill_beacon.native_messaging register [--browser
  chrome|edge|firefox|all]`.
- Auto-discovery of the port and token via a well-known file the user approves
  once, instead of manual paste.

## 4. QuillSync server -- sync and read surface

Status: built (reference server on stdlib `http.server`; production target is
FastAPI + PostgreSQL + S3 + Redis per PRD 45.5). The server stores encrypted
blobs and an opaque commit graph; it never sees plaintext.

Contract (PRD 45.5, 45.9):
- Auth: magic link via Postmark, verified in the client. Custom scheme
  `quillsync://verify?token=...&device=...` opens the companion app, not a web
  page. `GET /auth/verify` returns JSON the client consumes.
- Sync: `POST /sync/push` (commits + objects), `POST /sync/pull` (have -> new),
  `GET /sync/hints` (opaque new-commit count).
- Fail-safe: `PostmarkMailer` fails closed without an API key; `LoggingMailer`
  is the dev default and prints the link. The client wraps every server call so
  a failure returns an error and never corrupts the local library.

Integration points for later:
- Per-app scopes so signing in to Radio does not expose Beacon's library
  (cross-ref `PLAN-quillsync-integration.md` section 0.5).
- Push hints to drive a "N new on the server" badge in the status center.

## 5. CLI and custom-scheme handoff -- automation surface

Status: built. Two paths:
- `python -m quill_beacon.sync_ui verify --server URL --token T --device D`
  exchanges a magic-link token for a device token and saves it to config. This
  is the terminal path for environments where OS scheme registration is not
  available, and for CI.
- `quillsync://verify?...` passed as argv: `run()` checks `sys.argv` and hands
  the link to `handle_verify_url`, which calls `/auth/verify` and registers the
  device. This is the OS-registered-scheme path.

Scheme registration: `quill_beacon/scheme_register.py` registers/unregisters the
`quillsync://` scheme so the OS launches the app for a verify link -- Windows
(`HKCU\Software\Classes\quillsync`, no admin), Linux (a `~/.local/share/
applications` `.desktop` handler), macOS (bundle `Info.plist` at build time).
Fail-safe dict returns; CLI
`python -m quill_beacon.scheme_register register|unregister|status`. It is
installer-adjacent: invoked by an installer/wizard/user, not at app startup.

Fail-safe: any verify error is announced, never raised; a bad token does not
change config.

Integration points for later:
- A `capture`/`search`/`export` CLI: built as `quill_beacon.cli` (console
  script `quill-beacon-cli`). `capture <url> [--title --note --tags
  --collection]` feeds the library (reads stdin when the URL is `-`);
  `search <terms> [--collection --tag --type --sort --limit --json]` reads;
  `export <json|html|markdown|csv|opml|m3u|text> [--path --collection]`
  exports the whole library or one collection. It is wx-free and points at the
  same store via `paths.data_dir()` (override with `QUILLBEACON_DATA`).

## 6. System tray and status center -- in-app read surface

Status: built. The tray icon (show/hide, quick capture, sync now, status
center, exit) and minimize-to-tray keep long-running capture/sync available
without a visible window. The status center aggregates capture-bridge, sync,
and library-health rows via a `status_provider` callable so it stays a view.

Fail-safe: if the platform has no `TaskBarIcon`, the tray is simply not
created; nothing else changes. The icon uses a standard art provider bitmap so
no bundled assets are required.

## 7. External media player -- read surface

Status: built. `external_player.launch` hands a media URL (with resume time) to
VLC or mpv, falling back to the system default handler. The command builder is
pure and testable; the launcher is fail-safe (missing player -> default handler,
never an exception). Only the media URL the user already saved leaves the
machine, to a local process.

Integration points for later:
- A user-configurable player path and per-type player preference: built as
  `external_player.PlayerSettings` (persisted to `player_settings.json`).
  `default_player`, a `custom_path` per player for installs not on PATH, and a
  `per_type` map (e.g. radio in one player, podcasts in another) are honored by
  `build_command`/`launch` and edited via Tools > External Player....
- Saving the external player's exit position back as a time-point (requires a
  player that reports position; out of scope for the handoff itself).

## 8. Quill (the editor) -- planned feed + read surface

Direction: feed (capture a cursor/selection/heading from Quill into Beacon) and
read (resolve a saved place back into the editor at the exact location).

Contract (planned, built in the quill repo):
- Feed: a Quill command "Save place in Beacon" sends a ULD (heading path +
  text quote + positional) to Beacon via the capture bridge or a native
  messaging host. Beacon stores it as a `documentLocation` Beacon.
- Read: Beacon's ULD resolver can target Quill by a `native_locator` that names
  the Quill document id + offset; Quill exposes a "reveal at offset" command.
- Sync: Quill's settings/Vault sync over QuillSync, separate scope from
  Beacon's library (cross-ref `PLAN-quillsync-integration.md` section 1).

Fail-safe: if Quill is not running, capture still saves the ULD; resolution
falls through to the structural/text-quote layers and marks `needs_review`.

In scope here: the ULD `native_locator` shape for a Quill document and the
resolver hook. Out of scope: any change in the quill repo.

## 9. Quill Radio -- planned feed + read surface

Direction: feed (a "now playing" station/program becomes a Beacon) and read
(a saved radio Beacon opens in Radio at the right stream/program).

Contract (planned, built in the quill-radio repo):
- Feed: Radio posts the current station + program metadata to the capture
  bridge as a `radioProgram`/`radioStation` Beacon, reusing
  `radio.capture_program`.
- Read: Beacon's "open" hands a radio Beacon to Radio (or the external player)
  with the saved stream URL and alternates.
- Sync: Radio's stations/favorites/recordings sync over QuillSync, separate
  scope. Radio is the pilot sync surface (cross-ref
  `PLAN-quillsync-integration.md` section 5).

Fail-safe: if Radio is absent, a radio Beacon still opens in the external
player with alternates.

In scope here: the `radio.*` helpers and the `radioProgram`/`radioStation`
model. Out of scope: changes in the quill-radio repo.

## 10. Quill Cast -- planned read surface

Direction: read (a podcast Beacon opens in Cast's editor at the right episode;
publish state syncs so two machines never double-publish).

Contract (planned, built in the quill-cast repo):
- Read: Beacon resolves a `podcastEpisode`/`podcastChapter` Beacon to a Cast
  episode via `provider_ids` on the Resource.
- Sync: Cast's episode-notes and published-where state sync over QuillSync,
  separate scope (cross-ref `PLAN-quillsync-integration.md` section 3).

Fail-safe: if Cast is absent, the episode opens in the built-in or external
player.

In scope here: the podcast/chapter model and chapter normalization. Out of
scope: changes in the quill-cast repo.

## 11. iOS (Quill Pocket) -- planned feed surface

Direction: feed (capture an idea by voice or camera on the phone; it lands in
the desktop library, tagged and ready).

Contract (planned only, no build per PRD 35 Phase 4):
- Feed: Pocket writes captures into a QuillSync scope that Beacon pulls. The
  capture is a Beacon with a `capture_source` of `pocket` and optional audio
  attachment (manifest only; the blob stays local to the device or syncs via a
  separate large-object channel, never the encrypted commit graph).
- Auth: Pocket uses the same magic-link, per-device-token flow, its own scope.

Fail-safe: Pocket never needs the desktop running; sync lands the capture when
both are online.

In scope here: the `Attachment` model and the `capture_source` taxonomy. Out of
scope: the iOS app itself.

## 12. Web -- read-only surface

Status: built. A read-only public web view of a user's explicitly-published
collection. Not a sign-in surface and not a capture surface.

Contract:
- Transport: static render of the selected collection to a self-contained,
  accessible HTML page on disk under `published/<slug>/` in the data dir, plus a
  token-gated localhost preview served from the capture bridge
  (`GET /published/` index and `GET /published/<token>/` page). The bridge binds
  127.0.0.1, so the preview is local-only; the static files are the portable
  artifact the user can host anywhere.
- Auth: no auth beyond the publish token, which travels in the preview URL path
  so the link is shareable. No bearer token header is required for published
  routes (they mirror the public `/health` route).
- Fail-safe: nothing the web can do can modify the library; publishing is an
  explicit, reversible user action (Tools > Publish Collection, Ctrl+Shift+W,
  acting on the currently-selected sidebar collection). Unpublish removes only
  the generated files and never touches the database or sync state. The
  `Collection.sharing` field is not mutated by publish/unpublish.
- Accessibility: the rendered page is semantic HTML5 with a skip link, a single
  `<h1>`, `<article>`/`<h2>` per beacon, link text that is the resource title
  (never a bare URL), a plain-text fallback when a beacon has no resolvable URI,
  and a `prefers-reduced-motion` media query. A structural accessibility test in
  `tests/test_publish.py` gates the in-repo output, and an axe-core CI workflow
  (`.github/workflows/a11y.yml`) renders a fixture through the real renderer and
  fails the build on any WCAG 2A/AA violation.

In scope here: the publish module, the bridge routes, the dialog, and the tests.

## 13. OS integrations (possible future) -- feed surface

Direction: feed. OS share-sheet and quick-action integrations so a user can
"share to QuillBeacon" from any app that exposes a URL or text.

Contract (possible):
- Reuse the capture bridge or a native messaging host; the OS integration is a
  thin launcher that POSTs the shared payload.
- Fail-safe: identical to the browser extension -- if Beacon is not running,
  the share fails plainly and saves nothing.

Not in scope here: noted as a possibility only.

## 14. Contract stability

Every surface talks to Beacon over one of four stable contracts: the capture
bridge (feed), the QuillSync server (sync/read), the CLI/scheme (automation),
or the ULD `native_locator` (read into a host app). Beacon's internal schema
may evolve; the contracts must not. New Beacon fields ride inside the opaque
sync record or the capture payload without breaking a surface that ignores
unknown fields.

## 15. Sequencing

1. Desktop, bridge, extensions, server, CLI, tray, status center, external
   player -- done in this repo.
2. Quill Radio sync (pilot) -- next, in the quill-radio repo, against the
   server and framework built here.
3. Quill and Quill Cast sync -- after Radio proves the pilot.
4. iOS (Quill Pocket) -- plan only until Phase 4.
5. Web and OS integrations -- possible, not committed.

## 16. What stays in this repo

Beacon's library, ULD, search, sync root, server, extensions, and all the
in-app surfaces in sections 2-7 and 11's model. Everything else is an
integration point whose code lives in its own repo, planned here.