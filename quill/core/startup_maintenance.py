"""One-time, epoch-gated startup cleanups that give upgraders a clean slate.

Existing testers can carry a backlog of regenerable diagnostic clutter from
earlier runs -- old log files and crash reports, sometimes from a half-applied
upgrade. To "meet people where they are", QUILL clears that clutter **once** on
the first launch after the cleanup ships, so the app starts fresh instead of
greeting the user with a pile of past problems.

Design (mirrors the recommended-updates / schema-epoch pattern, so it scales):

* :data:`MAINTENANCE_EPOCH` is the current cleanup generation. Bump it to ship a
  new one-time cleanup in a future release.
* A tiny marker file records the last epoch completed, so a cleanup runs at most
  once per user per epoch.
* Only **regenerable diagnostic artifacts** are touched -- ``logs/``,
  ``crash-reports/``, ``diagnostics/``. User documents, autosaves, backups,
  recovery data, sessions, and settings are never removed.

Must run **early in** ``quill.__main__.main()`` -- after the data-location and
legacy-import migrations have resolved the real data dir, but **before**
``configure_logging`` opens the active log file -- so clearing ``logs/`` is safe.
Pure model code; no ``wx`` imports.
"""

from __future__ import annotations

import logging
from pathlib import Path

from quill.core.paths import app_data_dir
from quill.core.storage import read_json, write_json_atomic

logger = logging.getLogger(__name__)

#: Current cleanup generation. Bump to trigger a fresh one-time cleanup.
MAINTENANCE_EPOCH = 1

_MARKER_NAME = "startup-maintenance.json"

#: Subdirectories whose *contents* are cleared by the epoch-1 cleanup. These hold
#: only regenerable diagnostics -- never user work.
_EPOCH1_CLEARED_DIRS = ("logs", "crash-reports", "diagnostics")


def _completed_epoch(marker: Path) -> int:
    raw = read_json(marker, default={})
    if isinstance(raw, dict) and isinstance(raw.get("epoch"), int):
        return int(raw["epoch"])
    return 0


def _clear_dir_contents(directory: Path) -> None:
    """Best-effort: remove files (and empty subdirs) under *directory*, keep it.

    A locked or in-use file is skipped rather than raising -- startup must never
    fail over diagnostic cleanup.
    """
    if not directory.is_dir():
        return
    for entry in sorted(directory.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if entry.is_file() or entry.is_symlink():
                entry.unlink()
            elif entry.is_dir():
                entry.rmdir()
        except OSError:
            continue


def run_pending_startup_maintenance() -> None:
    """Run one-time cleanups newer than the recorded epoch, then record it.

    Idempotent and best-effort: if the marker already records the current epoch,
    nothing happens; any filesystem error is logged and swallowed so a launch is
    never blocked. Safe on a fresh install (the dirs are empty, so it just stamps
    the marker).
    """
    data_dir = app_data_dir()
    marker = data_dir / _MARKER_NAME
    if _completed_epoch(marker) >= MAINTENANCE_EPOCH:
        return
    # Epoch 1: clear the diagnostic backlog from the early beta (stale crash
    # reports and logs, including those left by half-applied upgrades).
    for name in _EPOCH1_CLEARED_DIRS:
        _clear_dir_contents(data_dir / name)
    try:
        write_json_atomic(marker, {"epoch": MAINTENANCE_EPOCH})
    except OSError as exc:
        # If we cannot record completion, the cleanup simply runs again next
        # launch -- harmless, since it only clears regenerable diagnostics.
        logger.debug("Could not record startup-maintenance epoch: %s", exc)


__all__ = ["MAINTENANCE_EPOCH", "run_pending_startup_maintenance"]
