"""Platform data-directory resolution for QUILL Social (wx-free).

A single source of truth for where the local store and per-user files live, so
the GUI (``ui/app.py``), the headless CLI (``cli.py``), and the services all
agree. Importing this module must not pull in wx.

Override with the ``QUILLSOCIAL_DATA`` (or ``QUILL_APP_ROOT``) environment
variable; otherwise the platform's per-user application-data directory is used.
Mirrors ``quill_beacon.paths`` and ``quill.core.paths``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_DIRNAME = "QuillSocial"


def data_dir() -> Path:
    """Return the QUILL Social data directory, creating it if needed."""
    base = os.environ.get("QUILLSOCIAL_DATA") or os.environ.get("QUILL_APP_ROOT")
    if base:
        p = Path(base) / APP_DIRNAME
    elif sys.platform.startswith("win"):
        p = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_DIRNAME
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / APP_DIRNAME
    else:
        p = Path.home() / ".local" / "share" / APP_DIRNAME
    p.mkdir(parents=True, exist_ok=True)
    return p


def db_path() -> Path:
    """Path to the primary SQLite store."""
    return data_dir() / "social.db"
