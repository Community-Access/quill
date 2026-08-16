"""Which edition of the app is running, so an update offers *that* one back.

Reported by a user, 2026-08-16: "fix the installer upgrade so it doesn't show
the wrong installer." They are right, and the fault was structural. A release
publishes four assets -- a full installer, a thin "Lite" installer, a portable
zip and an app-only Companion zip -- and the updater chose between them by
file extension alone. Every installed user therefore got whichever ``.exe``
GitHub happened to list first, so someone who installed the full edition was
handed the 2.6 MB thin installer and a Companion user was handed an ``.exe``
they cannot use at all. #1100 fixed *one* axis of this (portable versus
installed) and left the other, which is why the complaint outlived the fix.

Extension is not identity. This module answers the actual question, in order
of how much the evidence is worth:

1. **A marker the installer wrote** (``quill-edition.txt`` beside the app).
   Exact, because the thing that installed the app is the only thing that
   knows which installer it was.
2. **The shape of the folder**, for installs that predate the marker and for
   the zips: a portable bundle carries its own ``data`` folder, an Inno
   install always drops ``unins000``, and a Companion bundle has neither.

An install that predates the marker and cannot be told apart resolves to
:data:`INSTALLER_LITE` on purpose: the thin installer carries the same AppId
as the full one, so it upgrades either, and it fetches the shared runtime only
when the runtime is genuinely absent. It is the smallest download that is
correct for every installed listener -- provided its runtime check works,
which is a sibling fix in the same release.

wx-free and side-effect free: it only reads.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: The four things a release publishes, and what a listener is running.
PORTABLE = "portable"
COMPANION = "companion"
INSTALLER_FULL = "installer-full"
INSTALLER_LITE = "installer-lite"

#: Written into the app folder by each installer / staged into each zip.
MARKER_NAME = "quill-edition.txt"

_VALID = frozenset({PORTABLE, COMPANION, INSTALLER_FULL, INSTALLER_LITE})


def app_root() -> Path | None:
    """The folder the app was installed or unpacked into, or None.

    ``QUILL_APP_ROOT`` is exported by every frozen launcher; a source checkout
    has no edition at all, which is why this may answer None.
    """
    env_root = os.environ.get("QUILL_APP_ROOT")
    if env_root:
        try:
            candidate = Path(env_root).expanduser().resolve()
        except (OSError, ValueError):
            candidate = None
        if candidate is not None and candidate.is_dir():
            return candidate
    if not getattr(sys, "frozen", False):
        return None
    try:
        return Path(sys.executable).resolve().parent
    except (OSError, ValueError):
        return None


def read_marker(root: Path) -> str:
    """The edition recorded by whatever installed this copy, or ""."""
    try:
        text = (root / MARKER_NAME).read_text(encoding="utf-8").strip().lower()
    except OSError:
        return ""
    return text if text in _VALID else ""


def is_inno_install(root: Path) -> bool:
    """Whether an Inno Setup uninstaller sits beside the app.

    Matched by *pattern*, not by the literal ``unins000``. Inno numbers them:
    when ``unins000.exe`` already exists it writes ``unins001``, ``unins002``
    and so on, which happens whenever a copy is installed over an existing one
    without uninstalling first. Checking only ``unins000`` therefore reads
    those installs as portable -- and a portable-looking install is offered
    the portable .zip on every update, which is exactly what two users
    reported ("what was downloaded was the portable version rather than the
    full installer", #1100; and again on 2026-08-16).
    """
    try:
        return any(root.glob("unins*.exe")) or any(root.glob("unins*.dat"))
    except OSError:
        return False


def detect(root: Path | None = None) -> str:
    """Which edition is running, or "" when this is not a packaged build."""
    if root is None:
        root = app_root()
    if root is None:
        return ""
    marker = read_marker(root)
    if marker:
        return marker
    # No marker: an install from before this shipped, or a hand-unpacked zip.
    if is_inno_install(root):
        return INSTALLER_LITE  # the installer that correctly upgrades either
    if (root / "data").is_dir():
        return PORTABLE  # the portable bundle carries its own data folder
    return COMPANION


def matches_asset(edition: str, asset_name: str) -> bool:
    """Whether *asset_name* is the download for *edition* (pure).

    Names are matched on what the build scripts actually produce:
    ``Quill-Radio-Setup-Shared-3.0.0.exe``, ``Quill-Radio-Lite-Setup-3.0.0.exe``,
    ``Quill-Radio-Portable-3.0.0.zip``, ``Quill-Radio-Companion-3.0.0.zip``.
    """
    name = asset_name.lower()
    if edition == PORTABLE:
        return name.endswith(".zip") and "portable" in name
    if edition == COMPANION:
        return name.endswith(".zip") and "companion" in name
    if edition == INSTALLER_LITE:
        return name.endswith(".exe") and "lite" in name
    if edition == INSTALLER_FULL:
        return name.endswith(".exe") and "lite" not in name
    return False
