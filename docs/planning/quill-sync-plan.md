# QUILL Sync: Local-First, Provider-Neutral, Accessibility-First Sync and Versioning

**Status:** Plan of record, 2026-07-04. No code exists yet; this document is the
design the implementation phases will be cut from.
**Owner:** QUILL core.
**One-line vision:** Sign in once. Choose what to sync. QUILL handles the rest.
Conflicts are readable. Nothing is hidden behind an inaccessible cloud-provider UI.

---

## 1. The principle that governs everything

QUILL is not becoming a Dropbox app, a GitHub app, or a OneDrive app. QUILL
Sync is QUILL infrastructure: a local-first sync engine with provider adapters
behind it. Users never learn the storage backend's concepts (repos, commits,
delta tokens, cursors, app folders). They learn QUILL concepts: **settings,
snippets, workspaces, backups, conflicts, devices, and restore points.**

Most sync tools are visual, vague, and terrifying when something goes wrong.
QUILL Sync is calm, verbal, reversible, and deeply understandable. That is the
whole product.

Design laws, in priority order:

1. **Local first.** Every write lands in the local QUILL data folder before any
   network is touched. Sync is a background replication of state that already
   exists locally. Offline is not an error state; it is the default state that
   networking occasionally improves.
2. **Nothing silent.** Every sync outcome — uploaded, downloaded, skipped,
   conflicted, failed — is observable in the Sync Center, the Safety Log, and
   (per verbosity settings) the announcement channel. No toast-only design, no
   color-only status, no mystery icons.
3. **Reversible by construction.** Sync never destroys the only copy of
   anything. Deletes are tombstones. Overwrites capture a restore point first.
   "Disconnect and keep local data" always works.
4. **Least privilege.** App-folder scopes wherever the provider offers them.
   Tokens live in the OS credential vault, never in files. Every network call
   site is registered in the egress audit. Safe Mode disables sync outright.
5. **The user never has to understand the backend.** If a screen or message
   requires knowing what a cursor, delta token, SHA, or remote is, the design
   has failed.

## 2. Requirements

### 2.1 Functional requirements

- FR-1: Sync Tier-1 QUILL data (section 5) between two or more devices through
  a chosen backend, with no user knowledge of the backend's concepts.
- FR-2: Work fully offline; queue changes and reconcile on reconnect.
- FR-3: Detect conflicts deterministically (version vectors, never wall-clock
  guessing) and resolve them only through explicit, accessible flows.
- FR-4: Record a restore point before any overwrite (sync-driven or
  local-save-driven) of a synced item; expose "Restore previous version."
- FR-5: Tombstone deletes; propagate them; never hard-delete the last copy
  without an explicit, separately-confirmed user action.
- FR-6: Provide a Sync Center with live status, last-sync time, provider,
  device name, scope list, and the six actions (sync now, review conflicts,
  choose what syncs, export backup, view safety log, disconnect).
- FR-7: Keep a Safety Log of every sync action, exportable as plain text.
- FR-8: First-run wizard with the three plain-language questions (scope,
  destination, conflict policy) and a "what QUILL can access" disclosure.
- FR-9: Export the complete sync payload as a ZIP at any time; import it on a
  fresh install ("restore from backup" without any provider).
- FR-10: Per-device identity with a human-editable device name used in every
  conflict sentence and log line.
- FR-11: Disconnect in two explicit flavors: keep local data (default) or
  remove synced copies locally; both leave the provider copy untouched.
- FR-12 (Tier 2): Designate workspace folders; sync text-class documents with
  the same guarantees; binary files keep-both only.

### 2.2 Non-functional requirements

- NFR-1 **Accessibility:** every surface passes the dialog gates; all state
  changes reach the announcement/sound/status-bar channels per user verbosity;
  full keyboard operability; braille-friendly (short, front-loaded status
  strings); no color-only or icon-only meaning. Screen-reader scripts (JAWS +
  NVDA) are exit criteria for every phase.
- NFR-2 **Data safety:** kill -9 at any point corrupts nothing (journal +
  atomic writes + WAL); the convergence property suite (section 11) is green
  every release; zero classes of silent loss.
- NFR-3 **Performance:** steady-state idle cost ~0 (event/timer driven, no
  busy polling); initial Tier-1 scan under 2 seconds for a typical profile;
  UI thread never blocks on sync I/O (everything through QuillTaskManager,
  results via wx.CallAfter); background sync must not perceptibly delay typing,
  speech, or braille output.
- NFR-4 **Privacy:** no telemetry; the Safety Log is local; crash reports pass
  through the existing redaction scrubber so tokens, account names, and paths
  never leave the machine unredacted; API keys never sync.
- NFR-5 **Honesty:** every failure state has one owner message written in this
  plan or the copy deck, and every message says what QUILL will do next.
- NFR-6 **Compatibility:** sync schema is versioned; an older QUILL reading a
  newer sync store degrades to read-only-with-explanation, never corruption
  (section 13).
- NFR-7 **i18n:** every user-facing string goes through the gettext pipeline;
  conflict sentences are template-based so translators keep the grammar.
- NFR-8 **Footprint:** Phase 1-3 add zero new runtime dependencies (section 4);
  version store bounded by the retention policy's size cap.

## 3. What QUILL already has (build on it, do not duplicate it)

This plan deliberately reuses existing, tested infrastructure. The sync engine
is smaller than it looks because most of the hard parts already exist:

| Existing piece | Where | Role in QUILL Sync |
| --- | --- | --- |
| Atomic JSON writes | `core.storage.write_json_atomic` | All local sync-state side files; the "never half-written" guarantee |
| Credential vault + DPAPI | `platform/windows/credential_manager.py`, `dpapi.py` | OAuth token storage for every adapter |
| Egress audit gate | `quill/tools/network_egress_audit.py` | Every adapter call site gets an audit entry; CI enforces it |
| Background task pool | `stability/task_manager.py` (QuillTaskManager) | All sync I/O off the UI thread; `wx.CallAfter` for UI updates |
| Safe Mode | `QUILL_SAFE_MODE` gating pattern | Sync fully disabled in Safe Mode, like AI and watch folders |
| Redaction scrubber | `stability/redaction.py` | Tokens/accounts/paths scrubbed from any diagnostic bundle |
| Announcements + sounds + verbosity | announce engine, `core/sound_events.py`, verbosity system | The accessible notification channel; sync adds events, not a new channel |
| Settings registry + export | `core/settings.py`, `settings_specs.py`, SHARE-1 export | The schema-validated, per-key-describable settings model that makes field-level settings merge possible |
| Backups + autosave + persistent undo | `backup_document`, `core/autosave.py`, persistent undo store | The starting point for document restore points |
| Vault Git sync | Vault "Sync Vault" (commit/pull/push, conflicts listed) | Prior art for explicit, accessible conflict listing; the GitHub adapter generalizes it |
| Remote transports | `quill/io/` sftp, ftp, http, webdav, s3 | Proof of the transport-adapter pattern; WebDAV/SFTP sync backends later reuse these |
| Shareable artifact family | Quillin Hub types (quillins, sound packs, keyboard packs, verbosity packs, dictionaries, agents, skills) | The exact same artifact taxonomy defines what Tier-1 sync carries |
| Accessible dialog contract | `_show_modal_dialog`, `apply_modal_ids`, dialog gates | Sync Center and conflict dialogs are ordinary QUILL dialogs, gate-audited |
| Compare mode | existing document compare | The "Compare in QUILL" conflict view for text files |
| External change watcher | FEAT-19 watcher + prime-on-save pattern | The template for "my own sync write is not an external change" |
| QUILL Companion plan | PRD / companion workstream | The Phase 6 account/phone layer lands inside that program, not as a second one |

## 4. Dependencies

### 4.1 Runtime dependencies (the goal: zero new ones through Phase 3)

- **SQLite:** stdlib `sqlite3`. No package. WAL mode; single-writer engine.
- **Hashing:** stdlib `hashlib` (SHA-256).
- **HTTP:** the audited HTTP plumbing already in the tree (requests is already
  a transitive dependency). Adapters speak raw REST; provider SDKs are
  explicitly avoided unless a phase proves a concrete need, because every SDK
  is an unaudited egress surface, a supply-chain surface, and installer weight.
- **Microsoft auth:** `msal` is already installed (it ships today via the
  Microsoft 365 integration chain), so the OneDrive adapter adds nothing.
- **Dropbox:** raw REST (`/2/files/*`, `/2/files/list_folder*`) — nothing new.
- **Google:** OAuth installed-app loopback flow implemented directly (a
  localhost redirect listener + token exchange over the audited HTTP layer);
  no `google-api-python-client`, no `google-auth`, unless Phase 4 review says
  otherwise.
- **GitHub:** raw REST Contents/Git-Data APIs with the user's fine-grained
  token — nothing new; PyGithub exists in the tree but the adapter prefers the
  same thin audited-REST style as the others.

### 4.2 Project/infrastructure dependencies (owner action required, long lead)

These are the items that block phases regardless of code readiness — start
them early:

- **Azure app registration** (OneDrive): public-client app, delegated
  `Files.ReadWrite.AppFolder` + `offline_access`; publisher verification for
  a clean consent screen. Lead time: days.
- **Dropbox app registration:** App-Folder access type. Dropbox apps start in
  development status (limited users) and need **production approval** to
  exceed the small-user cap. Lead time: days to weeks.
- **Google Cloud project + OAuth consent verification:** `drive.appdata` is a
  sensitive scope; Google's app **verification review** is mandatory before
  non-test users can consent, and it can take weeks and requires a privacy
  policy URL and demo video. This is the single longest external lead time in
  the plan — file it at Phase 2 time even though Google ships in Phase 4.
- **GitHub:** none (user-supplied fine-grained token; no app registration).
- **Redirect URI strategy** for all OAuth: loopback (`http://127.0.0.1:<port>`)
  per RFC 8252 native-app guidance; no embedded web views (screen-reader-hostile
  and disallowed by Google). The system browser does the sign-in; QUILL
  announces "Your browser opened to sign in to OneDrive. QUILL is waiting."
- **Provider terms and branding:** each adapter's release checklist includes
  API ToS review and brand-usage rules (name providers in plain text; no logo
  misuse implying endorsement).

### 4.3 Internal dependencies

- Verbosity + sound events (new `SoundEvent`s: SYNC_STARTED, SYNC_COMPLETE,
  SYNC_ATTENTION, SYNC_CONFLICT — retunable in sound packs like all others).
- Settings registry (new specs; every new setting speakable).
- Keymap (new assignable commands; defaults listed in 9.4).
- Quillin Hub (Quillin re-install prompts on new devices; pack formats).
- i18n catalog; docs pipeline (this file's own HTML/EPUB artifacts included).

## 5. Architecture: three layers

### Layer 1: the Local Sync Engine (`quill/core/sync/`)

Pure domain logic. wx-free, strict-typed, fully unit-testable — the same
discipline as `quill/core` everywhere else.

**The object model.** Every synced thing is a `SyncItem`:

```text
id              stable QUILL-assigned identity (survives renames)
type            settings | profile | snippet | abbreviation | dictionary |
                template | soundpack | keyboard_pack | verbosity_pack |
                quillin_config | ai_prefs | feature_flags | workspace_file
path            logical QUILL path ("snippets/email-replies.json")
local_path      absolute path on this device
provider_path   opaque adapter-owned locator (never shown to users)
content_hash    SHA-256 of content, the change detector
modified_time   local mtime (UTC)
created_time    UTC
device_id       stable per-install id + human device name ("Work Laptop")
version_id      monotonically increasing per-item counter + origin device
deleted         tombstone flag (tombstones sync; nothing vanishes silently)
encrypted       whether the payload is E2E encrypted at rest on the provider
sync_status     in_sync | pending_upload | pending_download | conflict | error
last_error      speakable string, empty when healthy
```

**Sync state store: SQLite.** This is a deliberate, documented exception to
the JSON-atomic-write rule: sync state is high-churn, needs transactions,
indexed lookups by hash and path, and a journal that survives crashes
mid-batch. One database, `sync/state.db`, under the QUILL data dir. WAL mode.
Everything user-facing (the Safety Log export, backups) still renders to plain
text and JSON; SQLite is an engine internal, never a user-visible format.

**Versioning model.** A content-addressed blob store (`sync/versions/` keyed by
content hash) holds prior versions of synced items. Every overwrite —
whether caused by sync or by a local save to a synced item — records a restore
point first. Retention policy: keep every version from the last 7 days, then
daily for 30 days, then weekly to a size cap (default 200 MB, settable). This
generalizes `backup_document` rather than replacing it: documents keep their
existing backup behavior; synced items gain a uniform "Restore previous
version" surface on top.

**Conflict detection.** Per-item `(device_id, version_counter)` pairs — a
lightweight version vector. A change is a fast-forward when the incoming
version descends from the local one; otherwise it is a conflict. Wall-clock
time is displayed to humans ("changed at 9:14 AM on Work Laptop") but never
used to decide a winner. There is no silent last-writer-wins anywhere in the
engine; "prefer newest" exists only as an explicit user-chosen policy.

**The journal.** Every engine action appends a Safety Log record: what
changed, which device changed it, when, and whether it uploaded, downloaded,
skipped, or conflicted. The log is plain text, exportable, and rotates by
size. This is the "support artifact" and the user's audit trail in one.

**Scheduling model.** Event-driven, not polling: a debounced local watcher
(reusing the FEAT-19 watcher machinery, primed so QUILL's own writes are not
"external changes"), plus provider change signals (Graph delta on a timer,
Dropbox longpoll, Drive changes on a timer), plus manual "Sync now," plus a
low-frequency safety-net timer (default every 15 minutes when connected).
Exponential backoff with jitter on provider errors and rate limits; backoff
state is visible in the Sync Center ("Retrying in 4 minutes"), never hidden.

**Engine API surface (names indicative, signatures settled in Phase 1):**

- `scan()` — hash local items, enqueue pending uploads
- `pull()` / `push()` — exchange with the active adapter via its change feed
- `resolve(item, decision)` — apply a conflict decision (mine | theirs |
  both | merged payload)
- `restore(item, version_id)` — restore point recovery
- `status()` — the Sync Center's single source of truth

### Layer 2: provider adapters (`quill/core/sync/adapters/`)

One small interface; each adapter translates provider events into the same
internal engine events. The engine never branches on provider identity.

```text
class SyncAdapter (contract):
    capabilities()      -> app_folder | delta_feed | ranges | atomic_replace
    connect() / disconnect()
    account_summary()   -> speakable "what QUILL can access" description
    list_changes(token) -> (changes, next_token)     # normalized
    download(item) / upload(item) / delete(item)     # tombstone-aware
```

| Adapter | Change detection | Access model | Ships in |
| --- | --- | --- | --- |
| Local Folder | filesystem scan + hashes | a folder the user picks | Phase 1 |
| OneDrive | Microsoft Graph delta queries | App Folder (`Files.ReadWrite.AppFolder`) | Phase 2 |
| Dropbox | `list_folder` cursors + longpoll | Dropbox App Folder | Phase 3 |
| Google Drive | Changes API + start page tokens | appData folder (settings) or visible folder (workspaces) | Phase 4 |
| GitHub | tree/file SHAs, Contents API | fine-grained token, one repo | Phase 5, advanced |
| WebDAV / SFTP / self-hosted | ETag / mtime+size probing via existing `quill/io` transports | user-supplied server | later |

Adapter notes, by provider:

- **OneDrive first.** Built into Windows, dominant in work and school, Graph
  delta queries are exactly the change feed a sync engine wants, and the App
  Folder scope means QUILL asks for its own folder, not the user's drive. The
  honest caveats go in the UI: the app folder counts against quota, and the
  user can delete it from OneDrive's own UI (the engine treats that as "remote
  reset," not data loss, because local is the source of truth). Work/school
  tenants can block third-party consent; the failure message says exactly that
  and suggests the personal-account or local-folder path.
- **Dropbox second.** The simplest mental model (files in a visible folder),
  App Folder scoping, mature cursor/longpoll change detection. Treated as
  storage only — QUILL never depends on the Dropbox desktop client or tray UI.
- **Google Drive third.** appData is ideal for settings-class data and wrong
  for user-facing documents (hidden by design). The adapter therefore has two
  modes, chosen per scope: appData for Tier-1 data, a visible "QUILL" folder
  for workspaces. The Sync Center says which is in use in plain words, and the
  "Export backup" button exists precisely because appData is invisible.
- **GitHub is a power-user mode, never the default.** Every file update is a
  repository operation, and the concept load (repos, tokens, branches, rate
  limits) is exactly what mainstream users must never meet. But for
  developers it is superb: version this writing project, sync a profile to a
  repo, publish or install snippet packs, sync Quillins from a repo. The Vault
  Git sync feature is the prototype; GitHub-adapter workspaces generalize it.
  Fine-grained tokens with Contents-write scope only; stored in the vault.
- **Local Folder is not a toy.** It is the engine's proving ground *and* a
  real product: point it at a thumb drive, a network share, or a folder that
  OneDrive/Syncthing/Drive's own desktop client already mirrors, and users get
  provider sync with zero OAuth. It ships first and stays forever.

### Layer 3: QUILL Cloud / account layer (later, and only with a reason)

Not storage-first. It exists when — and only when — a concrete need arrives:
device registry across providers, push notifications, encrypted key recovery,
snippet-pack sharing, "send to my other device," and the phone companion.
This layer lands inside the existing QUILL Companion program rather than as a
parallel effort. Nothing in Layers 1-2 depends on it.

## 6. What syncs, in tiers

### Tier 1 (first): high-value, low-risk QUILL data

Every entry maps to a storage surface QUILL already owns, which is what makes
Tier 1 cheap and safe:

| Sync scope | Existing storage it rides on |
| --- | --- |
| Settings | schema-validated settings JSON (sensitive keys excluded or E2E-encrypted; DPAPI-bound values never leave the machine) |
| Feature profiles / flags | the feature-profile export format (SHARE-1) |
| Snippets | snippet store |
| Abbreviations | abbreviation library (user library only; Quillin-contributed ones re-materialize from their Quillins) |
| Dictionaries + custom spelling words | spell-check dictionaries and user word lists |
| Templates | template files |
| Sound packs | the Hub sound-pack artifact format |
| Keyboard customizations | keymap + keyboard-pack (.kqp) export |
| Verbosity packs | verbosity system data |
| Quillin configuration | per-Quillin settings (configs sync; Quillin *code* installs from the Hub, so a new device gets "install these 3 Quillins?" as an accessible prompt, not silent code sync) |
| AI Hub service preferences | provider/model/engine prefs — **never API keys**; keys stay in the credential vault per device, and the new device says plainly "sign in to OpenRouter on this device to finish" |
| Accessibility preferences | settings subset, called out separately in "Choose what syncs" because it is the first thing a user wants on a new machine |
| Recent folders | paths only, never the files behind them |

Formats stay portable and human-readable on the provider: `settings.json`,
`profiles/*.json`, `snippets/*.json`, `abbreviations/*.json`,
`dictionaries/*.dic`, `templates/*`, `soundpacks/*` — a person can open their
sync folder in any file manager and recognize everything.

**Per-key sync policy in the settings registry.** Each `SettingSpec` gains a
sync class: `sync` (default for preferences), `local_only` (paths, window
geometry, device-specific hardware choices like audio devices and SAPI voice
ids — a synced voice that does not exist on the other machine must degrade,
not error), or `secret` (never leaves the vault). The wizard's "Choose what
syncs" reads these classes, so the choice list stays truthful automatically as
settings are added.

### Tier 2 (later): document workspaces

A user designates a folder as a **QUILL Workspace**. QUILL syncs Markdown,
text, HTML, BRF, scripts, and project folders inside it. Binary files are
supported but conservative: hashed whole, never merged, conflicts always
keep-both. A Vault is a natural workspace (one checkbox: "Sync this vault");
so is a Story Studio project folder. Workspaces wait until the engine has
survived a full release cycle on Tier-1 data — full document sync on day one
is the trap this plan exists to avoid.

## 7. Document versioning (the half of this that is not sync)

**Status: SHIPPED early, in 0.9.0 Beta 1** — this section was implemented ahead
of the rest of Phase 1 as `quill/core/restore_points.py` +
`quill/ui/main_frame_restore_points.py` (File > Restore Previous Version, the
`restore_points_enabled` / `restore_points_max_mb` settings, PRD 5.39a). The
sync engine's later phases build on that store as designed here.

Versioning works entirely offline and is valuable with no provider connected
at all:

- **Restore points.** Every save of a synced item (and every sync-driven
  overwrite) records a content-addressed version. `File > Restore Previous
  Version...` lists versions the way backups are listed today: "Yesterday at
  4:12 PM, this device, 2,341 words," Enter to preview, explicit button to
  restore (which itself records a restore point first — restoring is never
  destructive either).
- **Retention** as in section 5; the policy is one plain-language setting.
- **Relationship to existing features.** `backup_document` and autosave keep
  doing their jobs; persistent undo remains the in-session safety net. Restore
  points are the cross-session, cross-device layer above both. One user guide
  page explains all three in one breath, because users should not have to
  taxonomize their own safety nets.

## 8. Filesystem and platform design considerations

The unglamorous list that decides whether sync is trustworthy:

- **Windows realities:** case-insensitive filenames (two logical paths
  differing only by case are the *same* item — enforce at the logical-path
  layer); reserved device names (CON, PRN, AUX, NUL, COM1-9, LPT1-9) rejected
  in logical paths with a speakable message; long paths handled via the
  `\\?\` opt-in QUILL already uses for data dirs; NTFS alternate data streams
  are not synced.
- **macOS realities:** Unicode normalization — APFS/HFS store NFD while
  everything else speaks NFC; all logical paths normalize to NFC before
  hashing and comparison, or the same file ping-pongs forever. Keychain
  replaces Credential Manager behind the same credential interface.
- **Timestamps:** all stored times are UTC; display is local. Timestamps are
  informational only (FR-3), so clock skew can never corrupt state — it can
  only make a displayed time look odd.
- **Single-instance discipline:** the engine takes an exclusive lock file
  next to `state.db`; a second QUILL instance (or a crashed one's leftover
  lock, detected by PID liveness) degrades to "sync paused in this window,"
  spoken, not raced.
- **Own-write suppression:** every local write the engine performs primes the
  external-change watcher (the FEAT-19 pattern) so sync never reports its own
  writes as external edits, and the editor never re-prompts on them.
- **Antivirus/locked files:** transient sharing violations retry with
  backoff; a persistently locked file becomes a per-item `error` with the
  filename spoken, never a wedged queue.
- **Portable builds:** the portable data dir is sync-capable; the Local
  Folder adapter is the natural pairing (QUILL-on-a-stick with versioning).
- **Metered connections:** honor the OS metered-connection signal with a
  setting ("Pause sync on metered connections," default on for uploads over
  1 MB); state shows as "Paused (metered connection)."
- **Proxies:** whatever the existing HTTP plumbing honors applies to
  adapters automatically; no adapter-private networking stacks.
- **Large files (Tier 2):** chunked/resumable uploads where the provider
  supports them (Graph upload sessions, Dropbox upload sessions); a per-file
  size guardrail with a speakable "stays local" message (default 100 MB,
  settable).

## 9. The accessibility-first experience

### 9.1 The Sync Center (`Tools > QUILL Sync Center`)

One dialog, keyboard-first, gate-audited like every QUILL dialog:

- Status line, always one of: "Up to date," "Syncing," "Needs attention,"
  "Offline," "Paused," "Conflict found." Words, not icons; a sound event and
  optional announcement accompany transitions.
- Last successful sync time, current provider, current device name (editable
  here), what is being synced (a readable list, not a tree of checkboxes).
- Buttons: **Sync now**, **Review conflicts**, **Choose what syncs**,
  **Export backup**, **View safety log**, **Disconnect provider**.
- Disconnect always asks one question with two honest answers: "keep local
  data" (default) or "also remove synced copies from this device."

A status-bar cell mirrors the status line (Enter opens the Center), and the
existing Status Page gets sync task rows like any background work.

### 9.2 First-run wizard

Three plain-language questions, in this order:

1. **"What do you want to sync?"** Settings only / Settings and snippets /
   Settings, snippets, and workspaces / Everything I choose manually.
2. **"Where should QUILL store your sync data?"** OneDrive (recommended for
   Windows and work or school) / Dropbox (recommended for simple personal
   file sync) / Google Drive / GitHub (advanced) / A local folder. Each
   option's description says, in one sentence, what QUILL will be able to
   access — before sign-in, not after.
3. **"How should conflicts be handled?"** Ask me every time / **Keep both
   copies and tell me (default)** / Prefer this device / Prefer the newest
   copy.

Sign-in happens in the system browser (RFC 8252 loopback; never an embedded
web view — those are screen-reader-hostile and Google forbids them anyway).
QUILL announces "Your browser opened to sign in to OneDrive. QUILL is
waiting," and completion returns focus to the wizard with a spoken result.
After sign-in, a **"What QUILL can access"** screen states the granted scope
in plain words ("QUILL can see only its own folder in your OneDrive, named
Apps/QUILL. It cannot see your other files.") with Disconnect right there.

### 9.3 Conflict resolution — the part everyone else gets wrong

QUILL never says only "Conflict detected." The sentence pattern is fixed:

> "The snippet file 'Email Replies' was changed on Work Laptop at 9:14 AM and
> on Home Desktop at 9:21 AM. Review both versions, keep both, or choose one."

Four resolvers, chosen by item type:

- **Text files:** Compare in QUILL (the existing compare surface), read
  changed sections, jump by change, copy from either side, then Keep mine /
  Keep theirs / Save both / Merge manually.
- **Settings:** field-level, in human language, powered by the fact that
  every setting has a spec with a speakable label: "Your Home Desktop changed
  the default font size from 12 to 14. Your Work Laptop changed it from 12 to
  13. Which value should QUILL use?" Non-conflicting fields merge silently
  and are listed in the Safety Log.
- **Collections** (snippets, abbreviations, dictionary words): item-level.
  Two devices adding different snippets is not a conflict at all; only the
  same item edited both places asks a question, phrased like the settings one.
- **Binary files:** always keep both ("Email Replies (from Home Desktop)"),
  say so, never attempt a merge.

"Save both" is the universal escape hatch and the default policy. A conflict
queue (not a modal ambush) lives behind "Review conflicts"; nothing blocks
editing while conflicts wait.

### 9.4 Commands, keys, and menus

- Commands (palette + keymap-assignable, empty defaults except where noted):
  `sync.open_center` (suggested Alt+Shift+S), `sync.sync_now`,
  `sync.review_conflicts`, `sync.export_backup`, `sync.restore_version`
  (also under File for the active document).
- Menu: `Tools > QUILL Sync Center...`; `File > Restore Previous Version...`.
- Status bar cell opt-in via the existing Status Bar preferences.

### 9.5 Notifications and copy deck

Through the channels QUILL already has — status bar text, optional sound
event, optional speech announcement honoring verbosity, braille-friendly
status strings (short, meaning first). The copy below is the spec:

- "QUILL Sync complete. Three settings updated."
- "QUILL Sync paused. OneDrive needs you to sign in again."
- "Conflict found in Snippets. Press Alt+Shift+S to review."
- "Sync is waiting for the network. Your changes are safe on this computer."
- "Sync is retrying in four minutes. Nothing is lost."

No silent failure: an error state produces exactly one notification plus a
persistent "Needs attention" status until acted on (no repeating nag). All
strings gettext-wrapped; conflict sentences are parameterized templates.

### 9.6 The Sync Safety Log

Every record: what changed, which device, when, and the outcome (uploaded /
downloaded / skipped / conflicted / failed, with the speakable reason).
Plain-text export for support, one button. This log is also what "QUILL, what
did sync just do?" reads from.

## 10. Failure modes and their owner messages

Every row is an exit criterion for the phase that ships it:

| Failure | Engine behavior | What the user hears |
| --- | --- | --- |
| Token expired / revoked | pause provider, keep queueing locally | "Sync paused. OneDrive needs you to sign in again." |
| Provider outage / 5xx | backoff with jitter, visible retry timer | "Sync is retrying in four minutes. Nothing is lost." |
| Rate limited | honor Retry-After, same as outage | same as outage |
| Quota full | pause uploads, downloads continue | "OneDrive is full. QUILL keeps your changes on this computer until space is free." |
| Remote app folder deleted | treat as remote reset; re-seed from local after one confirmation | "Your QUILL folder on OneDrive is gone. QUILL still has everything locally. Re-create it?" |
| Tenant/admin consent blocked | fail at sign-in with the real reason | "Your work account does not allow QUILL to connect. A local folder or a personal account still works." |
| Local file locked (AV, editor) | retry, then per-item error | "Sync could not read 'notes.md' because another program has it open." |
| Same account, two devices syncing at once | version vectors make this the normal case, not a failure | (nothing — this is the designed situation) |
| Crash mid-sync | journal replay on next start | "QUILL finished a sync that was interrupted." (only if anything was pending) |
| Sync store from a newer QUILL | read-only + explanation | "This sync data was written by a newer QUILL. Update this computer to sync again." |
| Hash mismatch after download | discard, re-fetch, then per-item error | "Sync could not verify 'settings.json' and will try again." |

## 11. Testing strategy

- **Engine:** pure unit tests (wx-free) for hashing, version vectors,
  tombstones, retention, journal replay after simulated crash; property-style
  tests that random interleaved edits on N fake devices always converge with
  zero silent losses.
- **Adapter contract:** one shared test suite every adapter must pass (the
  fake adapter, Local Folder, then each cloud adapter against a sandbox
  account) — the same pattern as the live AI provider regression suite, CI-safe
  and skipped without credentials.
- **Failure drills:** scripted scenarios for every row of section 10 —
  mid-upload kill, token revocation, quota exhaustion, remote folder deletion —
  each must leave the journal replayable and user data intact.
- **Accessibility:** dialog gates cover the new dialogs automatically; a
  manual screen-reader script per phase (JAWS, NVDA, the full conflict-review
  flow end to end by ear, braille status reading) mirrors the save-as
  spot-check practice. The wizard and Sync Center get the axe-style checks the
  accessibility rules require for UI work.
- **Performance:** a benchmark fixture (1,000 Tier-1 items) with budgets for
  initial scan, steady-state CPU, and memory, run in CI on the smoke tier.

## 12. Security and privacy

Minimum bar (Phase 1-2, non-negotiable):

- OAuth tokens in the Windows Credential Manager via the existing wrapper
  (Keychain on macOS); never in files, never in settings JSON.
- Least-privilege scopes: App Folder on OneDrive and Dropbox, appData on
  Drive, single-repo fine-grained token on GitHub.
- Every adapter call site registered in the network egress audit; the gate
  fails CI on any unregistered call.
- Sync disabled entirely in Safe Mode; no first network call before the
  wizard's explicit consent (the existing consent-before-egress law).
- Sensitive settings (anything DPAPI-bound today) either excluded from sync
  or E2E-encrypted; API keys never sync, period.
- Diagnostic bundles route through the redaction scrubber; the Safety Log
  export redacts account identifiers by default with a "include account
  details" checkbox for support cases.
- Clear "what QUILL can access" screen; one-button disconnect.

Better (its own later phase, opt-in): end-to-end encryption of the sync
payload with a passphrase, so providers store only blobs. Honest caveat baked
into the design: **encryption recovery is an accessibility hazard.** The
passphrase flow must be speakable, re-promptable, and paired with a recovery
phrase the wizard reads back and requires confirming; "I lost my passphrase"
must have a documented, truthful answer ("your provider copy is unreadable;
your local data is untouched; here is how to re-sync fresh"). If that UX
cannot be made calm, E2E ships later rather than confusingly.

## 13. Compatibility and schema evolution

- `schema_version` lives in both `state.db` and a `manifest.json` at the root
  of the provider payload.
- Rules: same major — sync freely; newer minor writes, older minor reads —
  allowed (unknown fields preserved, never stripped); older QUILL meeting a
  newer major — read-only with the section-10 message, no writes, no
  corruption.
- Migrations run forward-only on the local store with a pre-migration backup
  ZIP written automatically.
- The manifest also records device registry (id, name, last-seen) so the Sync
  Center can list "computers using this sync data" without any cloud account.

## 14. Phone access

Sequenced honestly, because cloud sync alone is not a phone story:

- **Phase A (free, immediate):** synced data is human-readable on providers'
  own mobile apps — Markdown, TXT, readable JSON exports, snippets as plain
  text. Costs nothing beyond the portable-format discipline already chosen.
- **Phase B: QUILL mobile web companion.** A small accessible web app: view
  and copy snippets, read documents, edit plain text and Markdown, view sync
  status, "send this to my QUILL desktop." This is where the QUILL Cloud
  account layer earns its existence, and it lands inside the QUILL Companion
  program alongside the Hub infrastructure.
- **Phase C: native mobile app,** only after the model is proven.

## 15. Staged implementation plan

Each phase produces working, testable software; no phase depends on a later
one. Documentation (user guide, PRD, CHANGELOG, release notes) updates as
each phase ships, per the incremental-docs rule.

**Phase 1 — Local Sync Foundation.** `quill/core/sync/` engine + SQLite state
+ version store + Local Folder adapter + Sync Center + Safety Log + restore
points + first-run wizard (local-folder path only) + export/import backup ZIP
+ the settings-spec sync classes. Exit criteria: two QUILL installs pointed at
one shared folder converge; every conflict class (text, settings field,
collection item, binary) resolves through the accessible flows; kill -9
mid-sync corrupts nothing; the whole engine is unit-tested with a scriptable
fake adapter; the screen-reader script passes.

**Phase 2 — OneDrive App Folder.** Azure registration + msal OAuth
(vault-stored, loopback flow), Graph delta queries, Tier-1 scopes only.
Egress audit entries, "what QUILL can access" screen, re-auth flow. Exit
criteria: Tier-1 data round-trips between two machines; token revocation,
tenant-blocked consent, quota-full, and remote-folder-deletion drills all
produce their section-10 messages and recover.

**Phase 3 — Dropbox App Folder.** Cursor/longpoll change feed; production
approval filed early. Proves the adapter contract with a second real
provider; any engine change this phase forces is an adapter-contract bug to
fix, not a special case to add.

**Phase 4 — Google Drive.** appData mode for Tier-1, visible-folder mode
reserved for workspaces; the wizard explains the hidden-folder trade-off in
one sentence with Export backup presented alongside. Google verification
must already be underway (filed at Phase 2 time).

**Phase 5 — GitHub advanced mode + Tier-2 workspaces.** Workspaces ship here,
on the by-now-hardened engine: designate a workspace, sync documents, Vault
and Story Studio integration, chunked uploads, size guardrails. GitHub
adapter for power users: profile-to-repo, versioned writing projects, snippet
packs, Quillins-from-repo. Clearly labeled "advanced" everywhere.

**Phase 6 — QUILL Cloud / Companion.** Account layer, device registry push,
phone web companion, encrypted recovery, "send to my other device" — inside
the QUILL Companion program, and only with the Phase B reason list actually
in front of us.

## 16. Repo invariants this work must honor

- `quill/core/sync` is wx-free and joins the strict mypy scope.
- New modules stay under the 600-line default budget; no main_frame growth
  beyond thin command/dialog wiring (a mixin, not main_frame.py).
- All UI through `_show_modal_dialog` and the dialog contract; new dialogs
  enter the dialog inventory.
- Every outbound call in the egress audit; consent before first network use.
- Feature-flagged (`future.sync` pattern) until Phase 2 is judged stable;
  fully absent in Safe Mode.
- Settings additions go through `settings.py` + `settings_specs.py` with
  speakable descriptions; new sounds are real SoundEvents; new strings are in
  the i18n catalog; new commands are keymap-assignable.

## 17. Risk register

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Google OAuth verification delays Phase 4 | High | File verification at Phase 2 time; Drive is deliberately not the first provider |
| Tenant admins block OneDrive consent at work | Medium | Honest failure message + local-folder fallback is always present |
| Sync bugs erode the trust the product is about | Medium | Local-first design, restore points, drills as exit criteria, Tier-1-before-documents sequencing |
| E2E encryption recovery confuses users | Medium | Ship later, behind its own phase gate, only with a passing screen-reader script |
| Scope creep toward "full Dropbox replacement" | Medium | Tier boundaries in this doc; workspaces wait a full release cycle |
| Version store disk growth | Low | Retention policy with size cap + one plain-language setting |
| Provider API/ToS changes | Low | Thin raw-REST adapters are small to update; contract tests catch drift |

## 18. Success criteria

- A blind user sets up sync on a second machine, alone, in under five
  minutes, and can state afterward what synced, where it lives, and how to
  turn it off — in their own words.
- Zero classes of silent data loss in the drill suite, every release.
- A conflict is something users resolve in QUILL in under a minute, not
  something they fear. The support question changes from "what happened to my
  file?" to "which version do I want?" — asked *by the product, out loud.*
