"""Where QuillLite keeps its state on disk.

Deliberately **not** ``%APPDATA%\\Quill``. QuillLite is offered as an
alternative to QUILL, not as a client of it: a Notepad-scale editor that
silently adopted a writing environment's settings, recent files and recovery
store would be making a decision for the user that nobody asked it to make, and
uninstalling it could then cost them something QUILL owns. Two products, two
folders, and a user who wants one to know about the other moves the file
themselves.

Three locations, in the order they are consulted:

1. ``QUILL_LITE_DATA_DIR`` -- an explicit override, honoured everywhere. It is
   what the tests use for isolation and what a support answer can reach for.
2. The portable anchor. A portable bundle ships a ``data`` folder beside the
   executable and the wrapper exports ``QUILL_PORTABLE``/``QUILL_APP_ROOT``
   before any quill import runs; QuillLite then lives on the stick, beside a
   portable QUILL rather than inside it.
3. ``%LOCALAPPDATA%\\QuillLite`` -- the default. *Local*, not roaming: a
   recovery copy of an in-progress document and a window size are this
   machine's business, and roaming them costs a domain user login time for
   nothing.

Off Windows (where the rich surface is unavailable but the modules still
import, so the tests run anywhere) this falls back to ``XDG_DATA_HOME`` and
then to ``~/.quilllite``.
"""

from __future__ import annotations

import os
from pathlib import Path

from quill.core.lite import APP_NAME

__all__ = [
    "data_dir",
    "inbox_dir",
    "instance_marker_path",
    "recovery_dir",
    "settings_path",
]


def _override() -> Path | None:
    """The explicit ``QUILL_LITE_DATA_DIR``, expanded, or ``None``."""
    raw = os.environ.get("QUILL_LITE_DATA_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def _portable_root() -> Path | None:
    """The portable bundle's ``data`` folder, when this is a portable build."""
    if not os.environ.get("QUILL_PORTABLE"):
        return None
    try:
        from quill.core.storage_mode import portable_root_dir

        return portable_root_dir()
    except Exception:  # noqa: BLE001 - a missing anchor is not an error here
        return None


def _base_dir() -> Path:
    """The parent QuillLite's own folder is created under."""
    portable = _portable_root()
    if portable is not None:
        return portable
    local = os.environ.get("LOCALAPPDATA") or os.environ.get("XDG_DATA_HOME")
    if local:
        return Path(local)
    return Path.home()


def data_dir() -> Path:
    """QuillLite's data folder, created if it does not exist yet."""
    override = _override()
    root = override if override is not None else _base_dir() / APP_NAME
    root.mkdir(parents=True, exist_ok=True)
    return root


def settings_path() -> Path:
    """``settings.json`` -- ten fields, and nothing QUILL reads."""
    return data_dir() / "settings.json"


def recovery_dir() -> Path:
    """One folder of recovery slots: a content file and a meta file per window."""
    path = data_dir() / "recovery"
    path.mkdir(parents=True, exist_ok=True)
    return path


def inbox_dir() -> Path:
    """Where a second launch drops the files it wants the first one to open."""
    path = data_dir() / "inbox"
    path.mkdir(parents=True, exist_ok=True)
    return path


def instance_marker_path() -> Path:
    """The running instance's process id, so a handover can raise its window.

    Windows will not let a background process steal focus; the *running* one has
    to allow it, and ``AllowSetForegroundWindow`` needs the pid to allow. Without
    this file a second launch would open the file correctly into a window the
    user then has to go and find.
    """
    return data_dir() / "running.pid"
