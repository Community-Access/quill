"""The folders a running app was installed or unpacked into.

Documents, icons and anything else an installer or a portable zip puts beside
the program live in *the app's* folder -- beside ``QuillRadio.exe`` -- which,
since the shared runtime (2026-08-17), is no longer the folder of the running
Python:

* **Installed:** ``sys.executable`` is ``QuillVilleRuntime.exe`` in
  ``%LOCALAPPDATA%\\QuillVille\\Runtime\\<version>``, which holds no documents.
* **Portable:** ``sys.executable`` is the bundle's ``pythonw.exe``, and the
  build is not "frozen" at all, so a lookup gated on ``sys.frozen`` never ran.

Both found no documents, so Help > User Guide did nothing in either edition of
Quill Radio 3.0 (reported 2026-09-28). The native launcher exports its own
folder as ``QUILL_LAUNCHER_DIR`` before it starts the app; that is the answer,
and the running Python's folder is the fallback (a portable bundle keeps both
in one place, and a frozen single-app build is its own program).

wx-free and strict-typed.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

__all__ = ["app_folders"]


def app_folders(
    *, env: Mapping[str, str] | None = None, executable: str | None = None
) -> list[Path]:
    """Where the app's own files may be, most specific first, without repeats."""
    environ = os.environ if env is None else env
    exe = sys.executable if executable is None else executable
    folders: list[Path] = []
    launcher = (environ.get("QUILL_LAUNCHER_DIR") or "").strip()
    if launcher:
        folders.append(Path(launcher))
    if exe:
        folders.append(Path(exe).resolve().parent)
    unique: list[Path] = []
    for folder in folders:
        if folder not in unique:
            unique.append(folder)
    return unique
