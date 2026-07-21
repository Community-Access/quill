"""PyInstaller entry point for the QuillBeacon onedir build.

Mirrors the radio/cast launchers: anchor the frozen build's environment so the
local store is found next to the exe in portable mode, then hand off to the app
that lives in the shared quill package (``quill.apps.beacon``).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's data directory before quill imports run.

    Portable mode: the portable zip ships a ``data`` folder next to
    QuillBeacon.exe. When it is there, export QUILLBEACON_DATA so the whole
    local store lives on the stick (``quill.apps.beacon.paths.data_dir`` reads
    it). The installed copy ships no ``data`` folder, so it keeps using the
    platform app-data directory (%APPDATA%\\QuillBeacon). Never overrides an
    explicitly set environment.
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
    from quill.apps.beacon import main as run

    return run()


if __name__ == "__main__":
    raise SystemExit(main())
