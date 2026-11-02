"""Where one scheduled recording is saved (quill-radio #21).

A schedule may name its own folder -- the Saturday jazz show in one place, the
news in another -- instead of the recordings folder from Recording Settings.
Empty means that default, so every schedule saved before this existed keeps
recording exactly where it did.

wx-free, strict-typed.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import replace
from pathlib import Path

from quill.core.radio.recording import RecordingSettings


def settings_for_folder(settings: RecordingSettings, folder: str) -> RecordingSettings:
    """*settings* with *folder* as the destination, or unchanged when it is empty."""
    folder = folder.strip()
    if not folder:
        return settings
    return replace(settings, destination_root=folder)


def folder_problem(folder: str) -> str | None:
    """Why a recording could not be saved in *folder*, or ``None`` if it can.

    Empty is fine (it means the default folder). Otherwise the folder must be a
    full path; it is created if missing, and a file is written and removed to
    prove it is writable -- a permission check alone misses a read-only share
    or a full drive. The message is a plain sentence for the status line.
    """
    folder = folder.strip()
    if not folder:
        return None
    path = Path(os.path.expandvars(folder)).expanduser()
    if not path.is_absolute():
        return "Type the full path of the folder, starting with a drive letter, or choose Browse."
    if path.exists() and not path.is_dir():
        return f"{path} is a file, not a folder. Choose a folder to save recordings in."
    try:
        path.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryFile(dir=path):
            pass
    except OSError:
        return (
            f"Recordings cannot be saved in {path}. It cannot be written to; "
            "choose another folder, or leave it empty to use the default."
        )
    return None
