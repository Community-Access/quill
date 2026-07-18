"""Reusable load/migrate/backup/resave for QUILL's versioned persistence stores.

This is the scalable backbone of the release-to-release persistence contract.
Every user-state file (settings today; keymap and feature flags as they adopt
it; any future store) follows the same three rules:

1. Defaults live in code.
2. Disk stores only the user's *delta* from those defaults, stamped with a
   schema/epoch version.
3. On load, a file that predates the current shape is backed up and rewritten
   to the canonical shape once, so changed/added defaults reach existing users
   while their customizations are preserved.

Rather than re-implement that dance per store, a store supplies four small
callables and gets the whole contract -- including the recoverable
pre-migration backup -- for free. Adding a new store is then: define defaults,
write ``parse``/``serialize``, declare ``is_legacy``, and call
:func:`load_with_migration`. Bumping a schema is: change ``serialize`` (and any
field-rename step inside ``parse``) and raise the version; legacy files migrate
and back up automatically.

Pure model code -- no ``wx`` imports.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from quill.core.migration_backup import backup_before_migration, backup_corrupt_file
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)


def _version_tag(raw: dict[str, object]) -> str:
    """The on-disk schema version being migrated away from, for backup naming."""
    version = raw.get("schema_version")
    if isinstance(version, int):
        return str(version)
    epoch = raw.get("_defaults_epoch")
    if isinstance(epoch, int):
        return str(epoch)
    return "legacy"


def load_with_migration[T](
    path: Path,
    *,
    store_name: str,
    parse: Callable[[dict[str, object]], T],
    serialize: Callable[[T], dict[str, object]],
    is_legacy: Callable[[dict[str, object]], bool],
    default: Callable[[], T],
    reconcile_unknown: Callable[[dict[str, object], dict[str, object]], dict[str, object]]
    | None = None,
    is_future: Callable[[dict[str, object]], bool] | None = None,
) -> T:
    """Load ``path`` as a versioned-delta store, migrating + backing up if needed.

    Parameters mirror the contract:

    * ``parse`` turns a raw on-disk dict (any historical shape) into the
      validated domain object, refilling anything missing with code defaults.
    * ``serialize`` turns the domain object into the canonical on-disk dict (the
      delta + version stamp). ``serialize(parse(raw))`` is the "what the file
      should look like now" form.
    * ``is_legacy`` reports whether ``raw`` predates the current schema, i.e. a
      real migration (not just a cosmetic rewrite) is happening and the original
      is worth backing up.
    * ``default`` builds the all-defaults object for a missing or unreadable
      file -- which is intentionally *not* created on disk on read.
    * ``reconcile_unknown`` (optional) preserves the multi-vintage shared-store
      contract: given ``(raw, desired)`` for a *non-legacy* file, it returns
      ``desired`` augmented with any content this binary does not recognize but
      a newer sibling app wrote (e.g. a setting field this older build lacks),
      carried forward verbatim so the rewrite does not silently drop it. Called
      only when ``is_legacy(raw)`` is False (a real migration is authoritative).
    * ``is_future`` (optional) reports that ``raw`` was written by a *newer*
      schema than this binary understands. Such a file is read for in-memory use
      but never rewritten -- an older app must not downgrade a newer app's file.

    When the on-disk form already equals the canonical form, nothing is written
    (no churn). Otherwise the file is rewritten to the canonical form; if it was
    legacy, the original is snapshotted first via
    :func:`quill.core.migration_backup.backup_before_migration`. Persistence is
    best-effort: a read-only or locked file never blocks startup -- the valid
    object is already in memory and cleanup retries next launch.
    """
    if not path.exists():
        return default()
    try:
        raw = read_json(path, default=None)
    except (ValueError, OSError):
        raw = None
    if not isinstance(raw, dict):
        # A file that exists but does not parse (malformed JSON or the wrong
        # top-level type) is corrupt: quarantine it before falling back to
        # defaults (which the next save would overwrite), so the user's original
        # is always recoverable -- and so a bad file never crashes startup.
        backup_corrupt_file(store_name, path)
        return default()
    obj = parse(raw)
    if is_future is not None and is_future(raw):
        # A file written by a newer schema than this build understands: use what
        # we can in memory, but never rewrite it -- downgrading it would strip
        # the newer app's data. It stays intact for the app that owns it.
        return obj
    desired = serialize(obj)
    legacy = is_legacy(raw)
    if reconcile_unknown is not None and not legacy:
        # Same-schema file that a newer sibling app may have extended (a setting
        # this older build has no field for). Carry those unknown entries forward
        # so the rewrite preserves them instead of dropping them.
        desired = reconcile_unknown(raw, desired)
    if raw != desired:
        if legacy:
            backup_before_migration(store_name, raw, version_tag=_version_tag(raw))
        try:
            write_json_atomic(path, desired)
        except OSError as exc:
            logger.debug("Could not persist migrated %s to %s: %s", store_name, path, exc)
    return obj


__all__ = ["load_with_migration"]
