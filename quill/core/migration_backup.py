"""Pre-migration backups for QUILL's versioned persistence stores.

Shared safety net for the release-to-release persistence contract (settings,
keymap, and feature stores all keep only a *delta* of the user's overrides plus
a schema/epoch stamp, so defaults flow forward automatically). Before a loader
rewrites a pre-current-schema file into the current shape, it snapshots the
original here, so the one-time conversion is always recoverable: a user (or we,
in support) can restore the most recent backup if a migration ever misbehaves.

Used by the settings store today (see ``quill.core.settings.load_settings``);
the keymap and feature stores adopt it as their own migrations land. Pure model
code -- no ``wx`` imports.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from quill.core.paths import app_data_dir
from quill.core.storage import write_json_atomic

logger = logging.getLogger(__name__)

#: All stores share one backup directory under the data dir.
BACKUP_DIRNAME = "migration-backups"

#: How many backups to retain per store (oldest are pruned).
_KEEP = 5

#: Store names migrated (and backed up) during this process, for the UI to
#: surface once after startup. In-process only: the loaders run in the same
#: process as the UI, so a simple list is enough and avoids another file.
_recent_migrations: list[str] = []


def pop_recent_migrations() -> list[str]:
    """Return and clear the store names migrated this launch (consume-once)."""
    names = list(_recent_migrations)
    _recent_migrations.clear()
    return names


def migration_backups_dir() -> Path:
    return app_data_dir() / BACKUP_DIRNAME


def backup_before_migration(name: str, raw: dict[str, Any], *, version_tag: str) -> None:
    """Snapshot a pre-migration document so its conversion stays reversible.

    Writes ``raw`` to ``migration-backups/<name>-v<version_tag>-<timestamp>.json``
    and prunes to the most recent :data:`_KEEP` backups for that ``name``.

    ``name`` is the store's short id (e.g. ``"settings"``); ``version_tag`` is
    the on-disk schema version being migrated away from (e.g. ``"1"`` or
    ``"legacy"`` when unstamped), so backups are self-describing.

    Best-effort: a read-only or locked data dir must never block startup -- the
    caller already holds valid in-memory state -- so failures are logged and
    swallowed.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backups_dir = migration_backups_dir()
    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
        write_json_atomic(backups_dir / f"{name}-v{version_tag}-{stamp}.json", raw)
        _prune(backups_dir, f"{name}-")
    except OSError as exc:
        logger.debug("Could not back up %s before migration: %s", name, exc)
    # Record even if the backup write failed: a migration still happened and the
    # UI should be able to tell the user (the in-memory state is already valid).
    if name not in _recent_migrations:
        _recent_migrations.append(name)


def backup_corrupt_file(name: str, path: Path) -> None:
    """Quarantine an existing-but-unparseable store before it is reset to defaults.

    When a config file is present but cannot be read as a valid document, the
    loader falls back to defaults -- which would otherwise overwrite the bad file
    on the next save and lose whatever the user had. Copy its raw bytes to
    ``migration-backups/<name>-corrupt-<timestamp>.json`` first so the original
    is always recoverable. Best-effort: never blocks startup.
    """
    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S-%f")
    backups_dir = migration_backups_dir()
    try:
        data = path.read_bytes()
    except OSError:
        return
    try:
        backups_dir.mkdir(parents=True, exist_ok=True)
        (backups_dir / f"{name}-corrupt-{stamp}.json").write_bytes(data)
        _prune(backups_dir, f"{name}-")
    except OSError as exc:
        logger.debug("Could not back up corrupt %s file: %s", name, exc)
    if name not in _recent_migrations:
        _recent_migrations.append(name)


def _prune(backups_dir: Path, prefix: str) -> None:
    backups = sorted(backups_dir.glob(f"{prefix}*.json"), key=lambda p: p.stat().st_mtime)
    for stale in backups[:-_KEEP]:
        try:
            stale.unlink()
        except OSError:
            pass


__all__ = [
    "BACKUP_DIRNAME",
    "backup_before_migration",
    "backup_corrupt_file",
    "migration_backups_dir",
    "pop_recent_migrations",
]
