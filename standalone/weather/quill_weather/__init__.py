"""Quill Weather standalone launcher.

The application itself lives in the ``quill`` package (``quill.apps.weather``)
and runs the exact same weather feature code QUILL and Quill Radio use -- same
National Weather Service client, same Weather Center, same Weather Guardian
alert monitoring. This package is only the product wrapper: it anchors
QUILL_APP_ROOT for the frozen build and hands off to the app.

Quill Weather and Quill Radio are versioned together (2.2.0): they ship the same
weather code and were released as a pair, but they are separate, independently
distributed and independently updated apps that can launch each other.
"""

import os
import sys
from pathlib import Path


def _export_app_root() -> None:
    """Anchor the frozen build's environment before quill imports run.

    Mirrors Quill Radio's launcher:

    - Portable mode: a portable zip ships a ``data`` folder next to
      QuillWeather.exe. When present, export QUILL_APP_ROOT and
      QUILL_PORTABLE so the shared data store (weather locations, settings,
      the alert-monitor config) lives on the stick. The installed copy ships
      no ``data`` folder, so it keeps using %APPDATA%\\Quill -- and therefore
      shares saved locations with QUILL and Quill Radio on the same machine.

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
    from quill.apps.weather import main as run

    return run()


__all__ = ["main"]
