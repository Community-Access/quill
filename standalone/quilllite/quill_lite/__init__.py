"""QUILL Lite standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.lite``) and
shares QUILL's editor surface, its RTF safety scanner, its dialog contract, its
F1 context-help engine and its announcement path. This package is only the
product wrapper: it anchors ``QUILL_APP_ROOT`` for the frozen build and hands
off to the app.

One detail differs from every sibling wrapper, and it is deliberate. Inkwell
keeps using ``%APPDATA%\\Quill`` on purpose, because its whole value is that its
abbreviations are *the same* abbreviations QUILL expands. QUILL Lite is the
opposite case: it is offered as an alternative to QUILL rather than as a
companion to it, so its settings, its recent files and its recovered work live
in ``%LOCALAPPDATA%\\QuillLite`` and nothing it does creates or touches a QUILL
data folder. A machine that has never had QUILL installed must not grow one
because somebody opened a text file.

What portable mode still does is put that folder on the stick: a portable bundle
ships a ``data`` folder beside ``QuillLite.exe``, and
:mod:`quill.core.lite.paths` puts QUILL Lite's own directory inside it.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before any quill import runs.

    Portable mode: a portable zip ships a ``data`` folder next to
    QuillLite.exe. When it is there, export ``QUILL_APP_ROOT`` and
    ``QUILL_PORTABLE`` so QUILL Lite's data folder lands on the stick beside a
    portable QUILL rather than in this machine's profile. The installed copy
    ships no ``data`` folder and therefore keeps using
    ``%LOCALAPPDATA%\\QuillLite``.

    Never overrides an explicitly set environment, so a support instruction or
    a test can always win.
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
    from quill.apps.lite import main as run

    return run()


__all__ = ["main"]
