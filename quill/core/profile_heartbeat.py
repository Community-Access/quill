"""Who is using this data folder right now -- the two-machines guard.

A custom data folder's whole purpose is to be synced between machines
(Dropbox, OneDrive, Google Drive...), and the one rule the sync clients
cannot enforce for us is "one machine at a time": two apps writing the same
profile from two PCs produce conflicted-copy files and silently split
histories. This is the lightweight tripwire: every app stamps this file at
launch (and refreshes it occasionally while running), and a launch that
finds a *different* machine's fresh stamp says so out loud before the user
spends an afternoon writing into a profile that is about to be overwritten.

Deliberately advisory -- a warning, never a lock. Sync latency means a stale
stamp can be wrong in both directions, and locking a blind user out of
their own data on the word of a sync client would be far worse than the
conflict it prevents. The stamp is small and changes at most every
:data:`REFRESH_SECONDS`, so the sync cost is a few bytes, not churn.

wx-free, strict-typed. Loss of the file is harmless (persistence class:
marker).
"""

from __future__ import annotations

import os
import platform
import time
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_FILE_NAME = "profile-heartbeat.json"

#: How often a running app bothers to re-stamp. Long enough that a synced
#: folder is not uploading constantly; short enough that "fresh" means
#: something.
REFRESH_SECONDS = 10 * 60

#: A foreign stamp younger than this reads as "in use over there".
FRESH_SECONDS = 15 * 60


def _path(data_dir: Path) -> Path:
    return data_dir / _FILE_NAME


def _machine_name() -> str:
    try:
        return platform.node() or "another computer"
    except Exception:  # noqa: BLE001 - a hostname lookup must never break startup
        return "another computer"


def note_profile_use(data_dir: Path) -> None:
    """Stamp this machine's use of the profile. Best effort; never raises."""
    try:
        write_json_atomic(
            _path(data_dir),
            {"machine": _machine_name(), "pid": os.getpid(), "at": time.time()},
        )
    except Exception:  # noqa: BLE001
        return


def refresh_profile_use(data_dir: Path) -> None:
    """Re-stamp, but only when the last stamp is old enough to matter.

    Call freely from a periodic tick; it writes at most every
    :data:`REFRESH_SECONDS`, so a synced folder is not uploaded once a
    minute for a timestamp.
    """
    try:
        document = read_json(_path(data_dir), default={})
        if isinstance(document, dict) and document.get("machine") == _machine_name():
            age = time.time() - float(document.get("at") or 0.0)
            if age < REFRESH_SECONDS:
                return
        note_profile_use(data_dir)
    except Exception:  # noqa: BLE001
        return


def startup_profile_guard(data_dir: Path) -> str:
    """The launch sequence in one call: warn about a foreign fresh stamp,
    then stamp this machine. Returns the warning to announce, or ``""``."""
    warning = foreign_use_warning(data_dir)
    note_profile_use(data_dir)
    return warning


def foreign_use_warning(data_dir: Path, *, fresh_seconds: float = FRESH_SECONDS) -> str:
    """A spoken warning when another machine stamped this profile recently,
    or ``""``. Check *before* :func:`note_profile_use` overwrites the stamp.
    """
    try:
        document = read_json(_path(data_dir), default=None)
        if not isinstance(document, dict):
            return ""
        machine = str(document.get("machine") or "")
        if not machine or machine == _machine_name():
            return ""
        age = time.time() - float(document.get("at") or 0.0)
        if age < 0 or age >= fresh_seconds:
            return ""
        minutes = max(1, int(age // 60))
        plural = "s" if minutes != 1 else ""
        return (
            f"Heads up: this data folder was in use on {machine} "
            f"{minutes} minute{plural} ago. Using it from two computers at "
            "once can lose changes -- close Quill there first."
        )
    except Exception:  # noqa: BLE001
        return ""
