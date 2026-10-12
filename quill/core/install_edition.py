"""Which edition of the app is running, so an update offers *that* one back.

Every app in the family ships exactly two downloads (owner decision,
2026-10-11): the **portable** zip, which runs from any folder and keeps its
settings in a ``data`` folder beside the app, and the **installer**, which
puts the app on the machine for everyone who uses it. The thin "Lite"
installer and the runtime-less Companion zip are gone.

The question still matters, because the two are not interchangeable: a
portable user handed the installer gets an app in Program Files they never
asked for, and an installed user handed the zip gets a second copy that
updates nothing. Reported by a user on 2026-08-16 ("fix the installer upgrade
so it doesn't show the wrong installer") and in #1100 before that.

The answer comes from, in order of how much the evidence is worth:

1. **A marker the installer wrote** (``quill-edition.txt`` beside the app).
   Exact, because the thing that installed the app is the only thing that
   knows which installer it was.
2. **The shape of the folder**, for installs that predate the marker and for
   the zip: an Inno install always drops an ``unins*`` uninstaller, and a
   portable bundle carries its own ``data`` folder. Anything else -- an
   installed app whose ``QUILL_APP_ROOT`` is the shared runtime's folder, say
   -- is the installer, because that is the one download that upgrades it.

A marker left behind by a retired edition still reads sensibly: an old thin
install is an Inno install and takes the installer, and an old Companion
folder takes the portable zip, its nearest living relative.

wx-free and side-effect free: it only reads.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: The two things a release publishes, and what a listener is running.
PORTABLE = "portable"
INSTALLER_FULL = "installer-full"

#: Every edition a running copy can report.
EDITIONS = (PORTABLE, INSTALLER_FULL)

#: Written into the app folder by each installer / staged into each zip.
MARKER_NAME = "quill-edition.txt"

#: Markers written by editions that no longer ship, and what replaces each.
_RETIRED_MARKERS = {"installer-lite": INSTALLER_FULL, "companion": PORTABLE}


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
    if text in EDITIONS:
        return text
    return _RETIRED_MARKERS.get(text, "")


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
        return INSTALLER_FULL
    if (root / "data").is_dir():
        return PORTABLE  # the portable bundle carries its own data folder
    return INSTALLER_FULL


def matches_asset(edition: str, asset_name: str, *, app_prefix: str = "") -> bool:
    """Whether *asset_name* is the download for *edition* (pure).

    Names are matched on what the build scripts produce:
    ``Quill-Beacon-Setup-Shared-3.0.0.exe`` (the installer) and
    ``Quill-Beacon-Portable-3.0.0.zip`` (the portable zip). Older releases also
    carry a thin ``...-Lite-Setup-...exe`` and a ``...-Companion-...zip``;
    neither matches anything, so going back to an old release never offers one.

    *app_prefix* is the app's own asset basename, stripped before matching, and
    it is not optional in spirit: "lite" is a word, and an app whose **name**
    contains it cannot be told apart without it.
    ``QuillLite-Setup-Shared-1.0.0.exe`` contains "lite", so without the prefix
    the installer reads as a retired thin one and matches nothing.
    """
    name = asset_name.lower()
    prefix = app_prefix.lower()
    if prefix and name.startswith(prefix):
        name = name[len(prefix) :].lstrip("-_. ")
    if edition == PORTABLE:
        return name.endswith(".zip") and "portable" in name and "companion" not in name
    if edition == INSTALLER_FULL:
        return name.endswith(".exe") and "lite" not in name
    return False
