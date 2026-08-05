"""Quill Media Player standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.player``) and
runs the exact same accessible player QUILL hosts -- same transport, chapters,
resume, bookmarks, and Go to Position. This package is only the product wrapper:
it anchors QUILL_APP_ROOT for the frozen build (so the bundled ffmpeg/engines in
``tools`` next to the exe are found) and hands off to the app.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill imports run.

    Mirrors QUILL's own launcher and the sibling standalone apps:

    - Portable mode: the portable zip ships a ``data`` folder next to
      QuillMediaPlayer.exe. When present, export QUILL_APP_ROOT and
      QUILL_PORTABLE so the shared data store lives on the stick.
    - Engines: ``{QUILL_APP_ROOT}/tools`` is where the installer and the
      portable zip place bundled ffmpeg and libmpv.

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
    elif (anchor / "tools").is_dir():
        os.environ["QUILL_APP_ROOT"] = str(anchor)


def main() -> int:
    _export_app_root()
    from quill.apps.player import main as run

    return run()


__all__ = ["main"]
