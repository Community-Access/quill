# QuillSync Integration Plan -- Quill, Quill Radio, Quill Cast, iOS

Status: planning. No code changes in the `quill`, `quill-radio`, or
`quill-cast` repos. No iOS build. This document specifies the adapter each
companion app would write against the `quillsync` framework that lives in this
repo (PRD 46), so the integration is ready to land in those repos when we
choose to.

## 0. The framework that already exists here

Built in this repo (PRD 46.1):

- `quillsync/` -- generic, record-agnostic sync core: `crypto`, `protocol`
  (`RecordStore`, `MergeFn`, `Commit`, `Conflict`), `transports`
  (`FolderTransport`, `ServerTransport`), `engine` (`SyncEngine`), `merge`
  (`union_lists`, `three_way_note`).
- `server/` -- reference hosted server: magic-link auth (PRD 45.9),
  push/pull/hints, per-account encrypted object store, `server/client.py`.
- `quill_beacon/sync.py` -- the Beacon adapter (`BeaconRecordStore` +
  `beacon_merge`), the reference implementation of the contract below.

The contract every app implements (PRD 46.2):

```
RecordStore:
    get_record(entity_id) -> dict | None   # None = deleted/trashed -> tombstone
    put_record(entity_id, record: dict)
    delete_record(entity_id)

MergeFn:
    (local: dict | None, remote: dict) -> (merged: dict, conflicts: list[Conflict])

SyncEngine(adapter, vault, *, device, data_dir, merge_fn, entity_type)
    .commit(message, entity_ids) -> Commit
    .push(transport) -> int
    .pull(transport) -> (applied: int, conflicts: list[Conflict])
```

The app never imports a Beacon model. It hands the framework opaque dicts and
a merge function; the framework handles encryption, commit log, transport, and
conflict surfacing.

## 0.5 Authentication and user experience -- client-based, no web interface

**Decision: there is no web UI.** Sync is configured and authenticated inside
each desktop companion app. The hosted server is an API + an email sender, not
a website. This is an accessibility and trust decision: blind and low-vision
users should never be bounced to a browser tab to complete a sign-in, and no
account data should live behind a web page we then have to make accessible.

### Magic links via Postmark, verified in the client (cross-ref PRD 45.9)

Auth is passwordless magic-link, delivered by **Postmark** (PRD 45.9). The
difference from a typical web magic-link flow is where the link lands:

1. **Request (in-app).** The user opens *Sync Settings* inside the companion
   app (Radio is first; see section 5) and enters their email in one labeled
   field. The app POSTs `{"email": ...}` to the server's `/auth/request`.
2. **Issue (server + Postmark).** The server mints a single-use, short-lived
   token, stores its hash, and asks Postmark to email a link. The link uses a
   **custom URL scheme**, not an HTTPS web page:
   `quillsync://verify?token=...&device=...`. The email is plain-text-first
   with the link on its own line (PRD 45.9 accessibility of the email).
3. **Verify (in-app, no browser).** The user activates the link in their mail
   client. The OS hands it to the registered companion app (the custom-scheme
   handler), which reads the token and calls the server's
   `GET /auth/verify?token=...&device=...`. The server returns a per-device
   bearer token as JSON. The app stores it. **No web page is ever rendered.**
4. **Device registration (in-app).** The app names the device ("Jeff's
   laptop") and the token is scoped to this app's namespace (PRD 46.4).

The server's `/auth/verify` endpoint returns JSON for the client to consume;
it is not a page a person reads. A hosted HTTPS verify URL is kept only as a
fallback for environments where custom schemes are unavailable (e.g., a
headless server box), and even then it shows a single "open the app" line, not
a form.

### Why this satisfies the constraints

- **No web interface to build or make accessible.** The entire auth UX is one
  in-app dialog (email field + "Send sign-in link" button) plus the mail
  client the user already uses. SEC-009 is met by making the auth screen a
  single labeled field and a button, never a captcha or a password.
- **Postmark retained.** Postmark is still the email transport (PRD 45.9),
  behind the `Mailer` interface so it can swap to SES/Mailgun/SMTP. The only
  change is the link's scheme (`quillsync://` instead of `https://`).
- **Client owns the vault key.** Account access (the device token) never
  equals content access: the vault key is still passphrase-derived and lives
  only on the client (PRD 45.3). The server holds wrapped DEKs and ciphertext,
  never plaintext or keys.
- **Custom-scheme registration.** Each companion app registers a handler for
  `quillsync://` (or its own `quillradio://`/`quillbeacon://` scheme) at
  install time. The NSIS/Inno installer (PRD 44 packaging) writes the
  `HKEY_CLASSES_ROOT\quillsync` key on Windows; the `.app` bundle registers
  it in `Info.plist` on macOS; the `.desktop` file sets `x-scheme-handler`
  on Linux. This is the only install-time addition the auth flow requires.

### What this means for each repo

- **This repo (framework + server):** the reference server already returns
  JSON from `/auth/verify` and already sends the link via Postmark
  (`server/mailer.py`, `server/app.py`). The one change is the link scheme:
  `SyncServer.request_magic_link` builds a `quillsync://` link (parameterized
  by `verify_base`) instead of an HTTPS URL. No web templates exist or are
  added.
- **Companion apps (Radio first, then Beacon/Quill/Cast):** each adds an
  in-app *Sync Settings* dialog (email field + button + status), a
  custom-scheme handler that calls `/auth/verify`, and the install-time scheme
  registration. No repo adds a web UI.

## 1. Quill (the editor) -- settings-as-a-repo + Vault sync

Source: `s:\quill\docs\planning\plan.md` section 2 (QUILL Sync). Quill already
stores everything as schema-validated, atomically-written JSON (settings,
keymaps, abbreviations, Quillin manifests) and Vault content as files. That is
exactly the shape `quillsync` was built for.

### Scopes (smallest first, per plan.md)

1. **Preferences scope.** Settings, keymap, abbreviations, voice/verbosity,
   Quillin install list (manifests re-fetched, not blobs). Small, low-conflict,
   immediately valuable: "sit down at any machine and it is your QUILL."
2. **Vault scope.** Notes, links, tags. Text merges via `three_way_note`;
   conflicts surface as an accessible two-version review flow, never inline
   markers.
3. **Opt-in extras.** AI conversation history, reading positions, Story Studio
   binder state.

### Adapter Quill would add (in the quill repo)

- `quill/sync/adapter.py`:
  - `SettingsRecordStore(RecordStore)`: one entity per settings file
    (`entity_id = "settings/keymap"`, etc.). `get_record` reads the
    atomically-written JSON and returns `{"scope": "keymap", "body": <json>}`;
    `put_record` writes via the existing `write_json_atomic`; `delete_record`
    removes the file. Scopes marked local-only (Windows credential-manager
    entries) are never returned by `get_record`, so they never sync.
  - `VaultRecordStore(RecordStore)`: one entity per Vault note (`entity_id =
    note_id`). `get_record` returns `{"title", "body", "tags", "updated"}`;
    `put_record` writes the note file; `delete_record` moves to Vault trash.
- `quill/sync/merge.py`:
  - `settings_merge`: remote-wins per key with a per-key override allowlist
    (audio devices and braille displays are per-machine overlays and stay
    local, per plan.md's "work/home profile" model). Built on `union_lists`
    for list-valued keys.
  - `vault_note_merge`: `three_way_note` for the body, `union_lists` for tags.
- `quill/sync/__main__.py`: vault key from passphrase (recovery kit via PRD
  23.4), `FolderTransport` or `ServerTransport`, a `sync now` command wired
  into the existing keymap.

### Security (non-negotiable, per plan.md)

- E2E encryption before anything leaves the machine; the sync payload is
  encrypted with the passphrase-derived vault key, so a compromised remote
  leaks nothing.
- Secrets never sync in plaintext; some (credential-manager entries) never sync
  at all. The sync manifest marks scopes syncable / encrypted-syncable /
  local-only.
- Every outbound call goes through Quill's existing network egress audit; sync
  is off until the user turns it on (consent-first).

### Branch-like profiles

plan.md's "work" and "home" profiles map to per-device overlays: each device
commits its machine-specific settings (audio device, braille display) under a
device-scoped entity id, while shared settings (abbreviations, AI setup) use
the shared id and merge. The adapter handles this by partitioning entity ids
into `shared/` and `device/<device_id>/` namespaces; only `shared/` merges
across devices.

### What this repo provides vs. what Quill adds

- This repo provides: `quillsync` engine/crypto/transports/merge, the reference
  server, and the Beacon adapter as the worked example.
- Quill adds: its two `RecordStore` adapters, its two `MergeFn`s, the
  passphrase/recovery plumbing, and the keymap command. No changes to this
  repo are required for Quill to integrate.

## 2. Quill Radio -- stations, favorites, recordings (pilot sync surface)

Quill Radio (`s:\quill-radio`) already has a wx-free core (`quill/core/radio/`)
with favorites, recording schedulers, and station catalogs. Those stores are
the sync substrate. **Radio is the pilot sync surface** (section 5): the first
companion app to integrate `quillsync`, and the app on which the client-based
auth UX (section 0.5) is proved end-to-end. Radio's *Sync Settings* dialog is
the reference implementation of the no-web-UI magic-link flow that Beacon,
Quill, and Cast then reuse.

### Scopes

1. **Favorites + custom stations.** The user's station list and favorites
   order. Small, high value: the same radio on every machine.
2. **Recording schedules.** Time-based recording rules sync so a recording
   set up on the desktop runs on the laptop too.
3. **Recording history (opt-in).** What was recorded and where it was saved;
   optional because file paths are machine-specific.

### Adapter Quill Radio would add (in the quill-radio repo)

- `quill_radio/sync/adapter.py`:
  - `StationRecordStore`: `entity_id = station_id`; `get_record` returns
    `{"name", "url", "stream_type", "favorite": bool, "order": int, "tags"}`
    from the existing favorites store; `put_record` writes back; `delete_record`
    removes the favorite.
  - `ScheduleRecordStore`: `entity_id = schedule_id`; record is the recording
    rule (station, cron-like time, output template). Paths are templated, not
    absolute, so they resolve per machine.
- `quill_radio/sync/merge.py`:
  - `station_merge`: `union_lists` for tags; favorite = OR; order kept local
    (per-machine order is an overlay, like Quill's audio device). Conflicts on
    URL changes (same station, new URL) surface for review rather than
    silently replacing.
  - `schedule_merge`: remote-wins for rule edits; `union_lists` for tags.

### Why this is low-risk

The radio core is already wx-free and parent-agnostic (per
`s:\quill\docs\planning\apps.md`). The sync adapter is a thin read/write shim
over the existing favorites and schedule stores; it adds no new UI and no new
core logic. The standalone `Quill Radio` app (apps.md pilot) gets sync for free
once the adapter exists, because the adapter sits on the core, not the frame.

## 3. Quill Cast -- episodes and publishing state

Quill Cast (`s:\quill-cast`) manages podcast publishing: episode metadata,
feed state, publishing pipeline outputs (DAISY, EPUB, WordPress, audio).

### Scopes

1. **Episode metadata + show config.** Titles, summaries, chapter marks,
   show-level config. The editorial state of a podcast, synced across the
   machines that produce it.
2. **Publishing state.** What has been published where (WordPress post id,
   feed entry guid, publish timestamp) so two machines do not double-publish.
3. **Pipeline outputs (opt-in, manifest-only).** Manifests of generated
   artifacts (sha256 + filename), not the blobs themselves; blobs are large and
   machine-local, so only their manifest syncs (mirrors Quill's "manifests
   re-fetched, not blobs" rule).

### Adapter Quill Cast would add (in the quill-cast repo)

- `quill_cast/sync/adapter.py`:
  - `EpisodeRecordStore`: `entity_id = episode_id`; record is the episode
    metadata + chapter marks + publishing state. `delete_record` moves to
    trash (never hard-deletes a published episode).
  - `ShowRecordStore`: show-level config (feed URL, categories, cover art
    ref).
- `quill_cast/sync/merge.py`:
  - `episode_merge`: `three_way_note` for the summary/show notes; `union_lists`
    for tags and categories; publishing state is a last-write-wins per platform
    with a "already published" guard so pull never re-publishes.
  - `show_merge`: remote-wins for config, with a review conflict if the feed
    URL changed on two devices.

### Publishing safety

The "already published" guard is the critical merge rule: a publish action
sets `published[platform] = {id, ts}` and that field is monotonic -- once
true/ set, it never reverts on merge. This prevents the classic split-brain
double-publish when two machines sync after both thinking they published.

## 4. iOS (Quill Pocket) -- plan only, no build

Per the user's constraint, iOS is planned here, not built. Source:
`s:\quill\docs\planning\plan.md` section 1 (QUILL Pocket).

### What Pocket is

The phone is the capture device, the reader, and the voice; the desktop is the
writing desk. Pocket is VoiceOver-first, works offline, and syncs
opportunistically over the same `quillsync` framework.

### How Pocket integrates with the framework

- SwiftUI app + Share Extension + App Intents (Action Button / Shortcuts /
  share sheet) for capture.
- A Swift `RecordStore` adapter speaking the same opaque-record contract, over
  `ServerTransport` (HTTP to the reference server). The adapter is the only
  iOS-side code that knows the sync contract; the rest of Pocket is native.
- E2E encryption is done in Swift (CryptoKit AES-GCM + scrypt-equivalent KDF)
  so the wire format is identical to the Python client. The vault key is
  derived from the user's passphrase in the Keychain and restored via the
  recovery kit (PRD 23.4).

### Scopes ( Pocket uses Quill's scopes, not Beacon's)

1. Capture: voice memos (transcribed on-device or via the user's AI key),
   camera OCR, share-sheet text -> land in the Vault inbox, already tagged.
2. Read: manuscripts, Vault notes, imported documents with per-document
   position sync (a position entity in the Vault scope).
3. Light editing: notes and small revisions, not the full command surface.

### Why this is a plan doc, not a build

Replicating 27k lines of desktop main_frame on a phone would produce a bad
phone app. Pocket gets a clean VoiceOver-native editor for notes and small
revisions; the heavy drafting stays on the desktop. The sync framework does
the handoff. Build is deferred per the user's directive; this section exists
so the framework's contract is confirmed to extend cleanly to iOS.

## 5. Sequencing across repos (Radio is the pilot sync surface)

1. **Beacon ships the framework + `BeaconRecordStore`** (done here). Beacon
   itself syncs over the framework, proving the engine and the folder/server
   transports on real data.
2. **Quill Radio -- the pilot sync surface.** Radio is the first *companion*
   app to integrate, and the surface on which the client-based auth UX
   (section 0.5) is proved end-to-end. It is the smallest, cleanest app
   (`apps.md` pilot candidate): a wx-free core, a thin standalone shell, and a
   low-conflict data set (favorites + stations). Landing Radio first proves
   the cross-app contract *and* the no-web-UI magic-link flow on the app
   least likely to surface a hard merge or a hard auth edge case.
3. **Quill scope 1 (preferences).** With the contract proven on Radio, Quill
   settings-as-a-repo lands in the quill repo. The auth flow is reused
   verbatim -- only the adapter and scopes differ.
4. **Quill scope 2 (Vault).** The hard three-way merge problems, solved on
   desktop where debugging is easiest.
5. **Quill Cast** episode metadata + the publishing guard.
6. **iOS Pocket v1** (capture + read + Vault browse), riding the proven sync
   -- build deferred per the user's directive, plan ready. iOS uses the same
   client-based auth (the mail client hands the `quillsync://` link to the
   Pocket app, which calls `/auth/verify`); no Safari web UI is added.

## 6. What stays in each repo

Each companion app owns its adapter, its merge functions, and its passphrase/
recovery plumbing. This repo owns the framework, the reference server, and the
Beacon adapter. No repo imports another's domain model; they share only the
`quillsync` contract and the server's JSON wire format.