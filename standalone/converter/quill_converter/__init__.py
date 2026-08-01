"""Quill Converter standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.converter``)
and runs the exact same wx-free conversion engine QUILL and Audio Studio use --
same presets, same Advanced DSP catalog, same bundled FFmpeg. This package is
only the product wrapper: it anchors QUILL_APP_ROOT for the frozen build (so the
bundled ffmpeg in ``tools\\ffmpeg`` next to the exe is found) and hands off to
the app.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill imports run.

    Two jobs, mirroring the sibling product launchers:

    - Portable mode: the portable zip ships a ``data`` folder next to
      QuillConverter.exe. When it's there, export QUILL_APP_ROOT and
      QUILL_PORTABLE so settings, conversion presets, and the job history live
      on the stick. The installed copy ships no ``data`` folder, so it keeps
      using %APPDATA%\\Quill.
    - ffmpeg: ``quill.core.speech.ffmpeg.ffmpeg_search_dirs`` checks
      ``{QUILL_APP_ROOT}/tools/ffmpeg`` first, which is exactly where both the
      installer and the portable zip place the bundled ffmpeg/ffprobe. The
      converter is useless without them, so this is not optional polish.

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
    elif (anchor / "tools" / "ffmpeg").is_dir():
        os.environ["QUILL_APP_ROOT"] = str(anchor)


def main() -> int:
    _export_app_root()
    from quill.apps.converter import main as run

    return run()


__all__ = ["main"]
