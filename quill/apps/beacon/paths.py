"""Platform data-directory resolution for QuillBeacon (wx-free).

A single source of truth for where the local store and per-user files live, so
the GUI (``app.py``), the sync CLI (``sync_ui.py``), and the headless CLI
(``cli.py``) all agree. Importing this module must not pull in wx.

Override with the ``QUILLBEACON_DATA`` (or ``QUILL_APP_ROOT``) environment
variable; otherwise the platform's per-user application-data directory is used.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def data_dir() -> Path:
    """Return the QuillBeacon data directory, creating it if needed."""
    base = os.environ.get("QUILLBEACON_DATA") or os.environ.get("QUILL_APP_ROOT")
    if base:
        p = Path(base) / "QuillBeacon"
    elif sys.platform.startswith("win"):
        p = Path(os.environ.get("APPDATA", str(Path.home()))) / "QuillBeacon"
    elif sys.platform == "darwin":
        p = Path.home() / "Library" / "Application Support" / "QuillBeacon"
    else:
        p = Path.home() / ".local" / "share" / "QuillBeacon"
    p.mkdir(parents=True, exist_ok=True)
    return p
