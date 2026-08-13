"""Quill Inkwell standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.inkwell``)
and shares QUILL's abbreviation library, dialog conventions, announcement
service, and sound events. This package is only the product wrapper: it anchors
QUILL_APP_ROOT for the frozen build and hands off to the app.

One detail matters more here than in the other family apps. Inkwell's whole
value is that its abbreviations are *the same* abbreviations QUILL expands, so
an installed copy deliberately keeps using ``%APPDATA%\\Quill``. Only a portable
build (a ``data`` folder next to the executable) moves the library onto the
stick, where it is then shared with a portable QUILL sitting beside it.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill imports run.

    Portable mode: a portable zip ships a ``data`` folder next to
    QuillInkwell.exe. When present, export QUILL_APP_ROOT and QUILL_PORTABLE so
    the shared data store -- including ``abbreviations.json`` -- lives on the
    stick. The installed copy ships no ``data`` folder, so it keeps using
    %APPDATA%\\Quill and therefore shares one abbreviation library with QUILL
    and every sibling app on the machine.

    Never overrides an explicitly set environment.
    """
    if os.environ.get("QUILL_APP_ROOT") or os.environ.get("QUILL_PORTABLE"):
        return
    if not getattr(sys, "frozen", False):
        return
    anchor = Path(sys.executable).resolve().parent
    if (anchor / "data").is_dir():
        os.environ["QUILL_APP_ROOT"] = str(anchor)
        os.environ["QUILL_PORTABLE"] = "1"


def main() -> int:
    _export_app_root()
    from quill.apps.inkwell import main as run

    return run()


__all__ = ["main"]
