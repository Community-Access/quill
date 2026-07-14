# Persistence and migration contract

How QUILL stores user state so that upgrades "just work" release to release:
customizations are preserved, new and changed defaults arrive automatically,
and a bad migration is always recoverable. This is the design contract every
persisted store follows; read it before adding a new store or changing an
existing one's on-disk shape.

## The three rules

1. **Defaults live in code.** The default value of every setting, keybinding,
   and feature flag is defined in the code, never baked into the user's file.
2. **Disk stores only the delta.** A user's file contains *only* the fields they
   changed from the default, plus a schema/epoch version stamp.
3. **Load migrates and protects.** On load, a file that predates the current
   shape is backed up and rewritten to the canonical shape exactly once.

Why a delta and not a full snapshot? Because the delta is what makes upgrades
safe:

- **New setting added in a release** -> it is absent from old files, so every
  user picks up its default automatically. ("New settings migrate in as we add
  features.")
- **Default value changed** -> users who never overrode that field have no entry
  for it, so they get the new default. (A full snapshot would pin every field to
  its value at save time, so a changed default would never reach an existing
  user. That was a real bug; see "History" below.)
- **User customization** -> it is the only thing written, so it survives upgrades
  verbatim.

## The stores

| Store | File | Stamp | Backed by |
|---|---|---|---|
| Settings | `settings.json` | `schema_version` (2) | `settings_migration.py` + `versioned_store.py` |
| Keymap | `keymap.json` | `_defaults_epoch` (1) | `keymap.py` (`merge_keymaps`, `load_keymap`) |
| Feature flags | `features.json` | `schema_version` (1) | `features.py` (overrides only) |

All three keep only the user's overrides. New stores must do the same.

## Shared building blocks

- **`quill/core/versioned_store.py`** - `load_with_migration(path, *, store_name,
  parse, serialize, is_legacy, default)`. The reusable load -> migrate -> backup
  -> resave dance. A store supplies four small callables and gets the whole
  contract for free. (Settings uses this; keymap/features can adopt it.)
- **`quill/core/migration_backup.py`** - `backup_before_migration(name, raw, *,
  version_tag)`. Snapshots a pre-migration document to
  `migration-backups/<name>-v<old>-<timestamp>.json` (keeps the most recent few)
  so a one-time conversion is always recoverable. Shared by all stores.

## Recipe: add a new persisted store

1. Define the domain object with its defaults in code.
2. Write `parse(raw) -> obj` (read any historical shape, validate field-by-field,
   refill missing fields with code defaults) and `serialize(obj) -> dict` (write
   only fields that differ from the default, plus a version stamp).
3. Write `is_legacy(raw) -> bool` (does this file predate the current version?).
4. In the loader, call
   `versioned_store.load_with_migration(path, store_name="...", parse=...,
   serialize=..., is_legacy=..., default=...)`.

That's it: forward-compatible defaults, one-time legacy conversion, and a
pre-migration backup all come for free.

## Recipe: change a default

Just change it in code. Every user who has not overridden that field gets the new
value on the next launch. No migration entry is needed.

## Recipe: force a change onto users who DID override it

Some default changes matter enough to push even to users who already customized
the field -- the canonical case is restoring **Find** to `Ctrl+F`. Use a
**recommended update** (`quill/core/recommended_updates.py`):

- Append a `RecommendedKeymapUpdate` with a brand-new, never-reused `id`.
- It is applied **at most once per user** (the id is recorded in
  `settings.applied_recommended_updates`), then never force-touched again, so the
  user stays free to rebind afterward.
- It is **opt-out**: users who prefer to keep their own choices set
  `apply_recommended_keymap_updates = False` in Settings, and nothing is forced.

The same mechanism exists for **settings** (`RecommendedSettingsUpdate` +
`apply_recommended_settings_updates`): because an upgraded settings file from an
older build is a full snapshot, a changed default would otherwise stay pinned, so
an important settings-default change can be force-set once the same way. Both are
applied at startup by `MainFrame._apply_recommended_keymap_updates()` after
settings and keymap load, share the `apply_recommended_keymap_updates` opt-out,
and record applied ids in `settings.applied_recommended_updates`.

## Recipe: rename / retype / split a field (schema bump)

When a change cannot be expressed as a default change (a field is renamed,
retyped, or split), bump the store's version and transform the old shape inside
`parse` (or a dedicated ordered migration step). Because `is_legacy` now reports
the old file as legacy, it is backed up before the rewrite automatically.

## Safety properties

- **No data loss.** Documents, autosaves, backups, and recovery data are never
  touched by migration; only the small config files are rewritten, and always
  after a backup.
- **Corruption tolerant.** A bad value in one field falls back to that field's
  default without discarding the rest (settings validate field-by-field). A whole
  file that is *unparseable* is **quarantined** before reset: the loader catches
  the decode error, copies the original to `migration-backups/<name>-corrupt-*`,
  and returns defaults -- so a corrupt config never crashes startup and is always
  recoverable (`migration_backup.backup_corrupt_file`, used by `load_keymap` and
  `versioned_store.load_with_migration`).
- **Best-effort persistence.** A read-only or locked data dir never blocks
  startup; valid state is already in memory and the rewrite retries next launch.
- **Backward tolerant.** An older build opening a newer delta file ignores
  override keys it does not recognize rather than crashing.

## Enforcement (the gate)

`quill/tools/persistence_audit.py` (and `tests/unit/tools/test_persistence_audit.py`)
make the contract self-sustaining: an AST scan finds every `write_json_atomic`
call site, and the test fails if any is **unclassified** in `_REVIEWED_PERSISTENCE`.
So a new persisted store cannot be added without consciously tagging it
`versioned`, `framework`, `secret`, `export`, `content`, `cache`, `marker`, or
`needs-versioning`. The `needs-versioning` tag is the tracked backlog of real
config stores that should still adopt the contract; **today it is empty** -- every
config store carries a `schema_version` (dict stores stamp the key; bare-list /
map / raw-dict stores wrap in a `{"schema_version", ...}` envelope with
back-compatible reads). Run `python -m quill.tools.persistence_audit` to check.

Note that a `schema_version` stamp is the *posture*, not necessarily an active
migration: most config stores are at v1 with no migration needed yet (old,
unstamped files still load), exactly like `features.json`. The stamp is what
makes a *future* shape change expressible.

Underpinning all of this, `storage.read_json` is **corruption-tolerant**: a
present-but-unparseable file returns the caller's default (and logs) instead of
raising, so one bad config file can never crash a load path -- and the critical
stores (settings, keymap) additionally quarantine the bad file first.

## Installer interaction

The Windows installer does a clean payload replace (wipes the first-party
`quill` package before laying down the new one) to prevent version-skew import
crashes, but it does **not** delete user config -- the migration contract above
is what keeps config safe across releases. See
`scripts/build_windows_distribution.py` (the `[InstallDelete]` section).

## History

- `schema_version` 1 (settings): nested `{schema_version, groups}` **full
  snapshot** of every field -- pinned changed defaults, so they never reached
  existing users.
- `schema_version` 2 (settings): nested `groups` hold only the **delta** from
  `Settings()` defaults. Legacy v1 files are backed up and converted on load.
- Keymap moved from a full snapshot to a delta + `_defaults_epoch` for the same
  reason.
