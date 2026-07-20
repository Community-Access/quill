# FAMILY-DATA.md — the QuillVille shared data contract

Status: initial ownership map, 2026-07-20. This is the file the QUILL PRD
§35.3 requires: every file the family writes under the shared data directory,
its schema owner, its readers, and its release-to-release posture. It is the
map the store has lacked; keep it in step with `quill/tools/persistence_audit.py`
(the gate that classifies every `write_json_atomic` site) — that gate is the
enforcement, this document is the human-readable contract.

## The shared directory

All Windows apps read and write **`%APPDATA%\Quill`** (macOS:
`~/Library/Application Support/Quill`), resolved through the
`QUILL_DATA_DIR` / `QUILL_PORTABLE` / `QUILL_APP_ROOT` environment contract.
Portable builds keep a `data\` folder beside the executable with a
`storage-mode.json` marker. Every app in the family points at the same store —
that shared store, not a shared binary, is what makes the apps a family.

## Posture classifications

Mirrors `persistence_audit.py::_CLASSIFICATIONS`:

- **versioned** — schema/epoch stamped, with a migration path (the contract).
- **framework** — the persistence/migration machinery itself.
- **content** — user-created data; additive, self-describing; a corrupt file
  degrades to empty. No changed-default risk.
- **cache** — regenerable recency/usage/log; loss is harmless.
- **marker** — a small boolean/state flag, trivially defaulted.
- **secret** — via the OS credential store; no JSON-schema concern.
- **export** — user-initiated output to a chosen file; not a store.
- **needs-versioning** — real user *config* that should adopt the versioned
  contract but has not yet. The tracked backlog, not a free pass.

## Shared contract files (read/written by multiple apps)

| Store | File (under %APPDATA%\Quill) | Owner | Readers | Posture |
| --- | --- | --- | --- | --- |
| App settings | `settings.json` | `core/settings.py` | all apps | versioned |
| Keymap | `keymap.json` | `core/keymap.py` | all apps | versioned |
| Feature flags | (features store) | `core/features.py` | all apps | versioned |
| Storage-mode marker | `data/storage-mode.json` | `core/storage_mode.py` | all apps | framework |
| Feature kill-switch cache | (safety lock) | `core/safety/feature_lock.py` | all apps | cache |

**Rule (Tier 1, mandatory):** on rewrite, preserve unknown fields; rewrite on
load only when genuinely legacy; stamp `last_written_by` (app + version). This
is what stops a newer app from silently downgrading an older app's data. Until
that lands, concurrent QUILL + Radio/Cast sessions are last-writer-wins on these
files — a known, documented risk.

## Per-app stores (namespaced; an app owns its own)

### Quill Radio (`core/radio/*`)
| Store | Owner | Posture |
| --- | --- | --- |
| Favorites (folders, custom names, per-station volume) | `favorites.py::save_favorites` | content |
| History / recently played | `history.py::save_history` | content |
| Recording settings | `recording.py::save_recording_settings` | content |
| Recording schedule | `recording_schedule.py::save_schedule` | content |
| Active-recording resume marker | `recording_resume.py::save_marker` | marker |
| Wake timer | `wake_timer.py::save_wake_setting` | content |

### Quill Cast (`core/podcasts/*`)
| Store | Owner | Posture |
| --- | --- | --- |
| Subscriptions | `subscriptions.py::save_library` | content |
| History | `history.py::save_history` | content |
| Episode notes | `episode_notes.py::save_episode_notes` | content |

### Audio Studio (`core/audio_studio/*`, `apps/studio.py`)
| Store | Owner | Posture |
| --- | --- | --- |
| Book library (folders/favorites) | `library.py::save_library` | content |
| Per-book prefs (volume/mute) | `book_prefs.py::save_prefs` | content |
| Recently played | `history.py::save_history` | content |
| Play queue | `play_queue.py::save_queue` | content |
| Sleep timer | `sleep_timer.py::save_sleep_setting` | content |
| App-shell prefs (close action, …) | `apps/studio.py::_save_app_prefs` | needs-versioning |

### Publishing (shared by Cast/Studio)
| Store | Owner | Posture |
| --- | --- | --- |
| SFTP/publish destinations | `core/publish/destinations.py` | content |
| Feed-folder show config | `core/publish/feed_folder.py` | content |
| Publish secrets | `core/publishing.py::save_publishing_secret` | secret |

### QUILL Beacon (independent today)
Beacon keeps its **own** store (`%APPDATA%\QuillBeacon`, SQLite + FTS5), not the
shared contract. When it converges to `quill/apps/beacon.py` its beacons remain
an **app-private** SQLite index in a per-app namespace; only the cross-app data
it wants to share (places via QuillSync) joins the shared contract.

## Rules

1. **Shared contract files are JSON** under the hardened versioned-store rules.
   **App-private indexes may be SQLite** in a per-app namespace (Beacon's
   engine; a future Audio Studio library index).
2. **Never widen a shared file's schema without the versioned contract** —
   preserve-unknown-fields makes cross-app coexistence safe; a schema bump is a
   suite-major event (PRD §35.4).
3. **Adding any `write_json_atomic` site fails the persistence gate until it is
   classified here and in `persistence_audit.py`.** That is the enforcement that
   keeps this document honest.
4. **Secrets never go in JSON** — they use the OS credential store (`secret`).

## Backlog (needs-versioning)

Real config not yet on the versioned contract: Weather settings
(`core/weather/settings.py`), Audio Studio app-shell prefs
(`apps/studio.py::_save_app_prefs`). These should route through
`versioned_store` before the QuillVille 1 suite freezes its contract.
