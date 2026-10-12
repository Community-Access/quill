"""QUILL Transcribe standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.transcribe``)
and runs the same dictation QUILL, QUILL Lite and Quill Inkwell use -- the same
controller, speech engines, models and words. This package is only the product
wrapper: it anchors QUILL_APP_ROOT for the frozen build and hands off to the app.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill imports run.

    Portable mode: a portable zip ships a ``data`` folder next to
    QuillTranscribe.exe. When present, export QUILL_APP_ROOT and QUILL_PORTABLE
    so its settings and the family's dictation word list live on the stick. The
    installed copy ships no ``data`` folder, so it keeps using the family's data
    folder -- and so shares dictation words with QUILL and Inkwell.

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
    from quill.apps.transcribe import main as run

    return run()


__all__ = ["main"]
