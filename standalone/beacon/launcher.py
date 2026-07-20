"""PyInstaller entry point for the one-file QuillBeacon build.

Mirrors ``quill_cast/launcher.py`` and ``quill_radio/launcher.py``: anchor the
frozen build's environment so the local store and bundled assets are found
next to the exe, then hand off to the app.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill_beacon imports run.

    Portable mode: the portable zip ships a ``data`` folder next to
    QuillBeacon.exe. When it is there, export QUILLBEACON_DATA so the whole
    local store lives on the stick. The installed copy ships no ``data``
    folder, so it keeps using the platform app-data directory. Never
    overrides an explicitly set environment.
    """
    if os.environ.get("QUILLBEACON_DATA") or os.environ.get("QUILL_APP_ROOT"):
        return
    if not getattr(sys, "frozen", False):
        return
    anchor = Path(sys.executable).resolve().parent
    if (anchor / "data").is_dir():
        os.environ["QUILLBEACON_DATA"] = str(anchor / "data")


def main() -> int:
    _export_app_root()
    from quill_beacon import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())