"""Application data directory resolution for Quill Radio for Mac.

Rewritten for this port from upstream ``quill.core.paths``, which is
Windows-first (``%APPDATA%`` plus a storage-mode store) and gates the
``QUILL_DATA_DIR`` override behind a dev-build flag. This standalone app
keeps the same environment variable names but resolves in a simpler,
fully documented order:

1. ``QUILL_DATA_DIR`` -- explicit override, used as-is (expanded for
   ``~``). Handy for tests, dev runs, and users who want their data
   somewhere specific.
2. ``QUILL_PORTABLE=1`` -- portable mode: a ``data`` directory beside the
   app. The root is ``QUILL_APP_ROOT`` when the launcher exports it,
   otherwise the directory containing the running executable.
3. Platform default:
   - darwin: ``~/Library/Application Support/Quill``
   - win32:  ``%APPDATA%\\Quill`` (kept so development and the test suite
     work on Windows)
   - anything else: ``~/.local/share/Quill``

The folder is named ``Quill`` on every platform, matching the Windows
app, so a data folder copied from a Windows machine (favorites, history,
recording settings, recordings) works unchanged on the Mac.

``app_data_dir()`` creates the directory on every call, so callers can
write into it immediately without their own ``mkdir`` dance.

Threading contract: pure functions over ``os.environ`` and the
filesystem; safe to call from any thread.

macOS notes: ``~/Library/Application Support`` is the Apple-sanctioned
location for app data; it always exists for a real user account, so the
``mkdir(parents=True)`` only ever creates the ``Quill`` leaf (and, in
tests, the monkeypatched fake home tree).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _resolve_data_dir() -> Path:
    """Resolve the data directory without creating it (pure logic).

    Split from :func:`app_data_dir` so the resolution order is testable
    and readable in one place. Reads ``sys.platform`` and ``Path.home()``
    at call time (not import time) so tests can monkeypatch both.
    """
    override = os.environ.get("QUILL_DATA_DIR")
    if override:
        return Path(override).expanduser()

    if os.environ.get("QUILL_PORTABLE") == "1":
        app_root = os.environ.get("QUILL_APP_ROOT")
        if app_root:
            return Path(app_root).expanduser() / "data"
        return Path(sys.executable).parent / "data"

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Quill"

    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Quill"
        raise RuntimeError(
            "Could not determine the Quill data directory: APPDATA is not set. "
            "Please set QUILL_DATA_DIR or APPDATA in your environment."
        )

    return Path.home() / ".local" / "share" / "Quill"


def app_data_dir() -> Path:
    """Return the application data directory, creating it if needed.

    See the module docstring for the resolution order. Every persistence
    module (favorites, history, recording settings, schedules, wake
    timer) roots its JSON files here, and ``radio_recordings`` lives
    directly beneath it.
    """
    directory = _resolve_data_dir()
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def recordings_dir() -> Path:
    """Return ``app_data_dir()/radio_recordings``, creating it if needed.

    The recorder writes finished captures here and the recordings
    manager dialog scans it; the name matches the Windows app exactly so
    a migrated data folder keeps its recordings visible.
    """
    directory = app_data_dir() / "radio_recordings"
    directory.mkdir(parents=True, exist_ok=True)
    return directory
