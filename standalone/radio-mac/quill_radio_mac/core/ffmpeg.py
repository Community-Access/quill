"""Discovery of the ``ffmpeg`` / ``ffprobe`` executables that power radio
stream recording (``core.recording``) and its raw-capture codec probe.

Adapted for this port from upstream ``quill.core.speech.ffmpeg`` (a
Windows-first search: a QUILL-managed ``tools/ffmpeg`` folder, then
``PATH``). This module keeps that "QUILL-managed locations first, then
PATH" shape but adds the stops a macOS install actually needs: Homebrew
puts ffmpeg in ``/opt/homebrew/bin`` (Apple Silicon) or ``/usr/local/bin``
(Intel), and neither is reliably on ``PATH`` for a GUI app launched from
Finder/Dock rather than a login shell.

Search order (first hit wins). Every stop except ``PATH`` is a
*directory* that is checked for both ``ffmpeg`` and ``ffprobe`` (one
setting covers both tools, mirroring how the bundle/engine-pack
directories already work upstream):

1. ``QUILL_FFMPEG`` -- an explicit directory override (tests, dev runs,
   or a user who keeps a specific build). Expanded for ``~``.
2. ``{QUILL_APP_ROOT}/tools/ffmpeg`` -- a bundle-adjacent copy, when the
   launcher exports ``QUILL_APP_ROOT`` (mirrors the Windows portable
   build layout upstream already uses).
3. ``<data>/engine-packs/ffmpeg`` -- a copy a future "Download FFmpeg"
   action could install into this app's data directory.
4. ``PATH`` via :func:`shutil.which`.
5. ``/opt/homebrew/bin`` then ``/usr/local/bin`` -- Homebrew's two
   install prefixes, checked last as a GUI-launch fallback.

At each directory stop, the bare name (``ffmpeg``) is checked; when
``os.name == "nt"`` (this core-logic suite also runs on Windows) the
``.exe`` variant is checked too, so the search logic itself is exercised
identically on both platforms even though only macOS ever hits the
Homebrew fallback in practice. Only a resolved basename on the narrow
allowlist below is ever returned, so a same-named-but-unexpected
executable earlier on a search path can never be launched.

No bundling: this app does not ship ffmpeg (its GPL/LGPL licensing makes
redistribution out of scope), the same non-redistributor stance upstream
takes -- :data:`INSTALL_HINT` points the user at Homebrew instead of a
downloader.

Threading contract: pure functions over ``os.environ`` and the
filesystem. :func:`find_ffmpeg` and :func:`find_ffprobe` are
``lru_cache``d (resolved once per process, like upstream), so they are
safe to call from any thread, including the recorder's background
thread; tests that need a fresh resolution monkeypatch the cached
function itself rather than clearing the cache (the same pattern
upstream's own ffmpeg tests use).

macOS notes: this is the platform the search order above was written
for. It also runs correctly on Windows (via the ``.exe`` branch) so the
cross-platform core test suite can exercise it without a Mac.
"""

from __future__ import annotations

import os
import shutil
from functools import lru_cache
from pathlib import Path

from quill_radio_mac.core.paths import app_data_dir

#: Only these basenames may ever be returned by :func:`_resolve_tool` --
#: a safety allowlist so a same-named executable found on a search path
#: (e.g. a malicious ``ffmpeg`` shim) is never silently accepted.
_ALLOWED_FFMPEG = frozenset({"ffmpeg", "ffmpeg.exe"})
_ALLOWED_FFPROBE = frozenset({"ffprobe", "ffprobe.exe"})

#: Homebrew's two install prefixes (Apple Silicon, Intel) -- checked last,
#: after PATH, as a fallback for a GUI app launched without a shell PATH.
_HOMEBREW_DIRS: tuple[Path, ...] = (Path("/opt/homebrew/bin"), Path("/usr/local/bin"))

#: How to obtain ffmpeg, surfaced in "not installed" errors/announcements.
INSTALL_HINT = "Install FFmpeg with Homebrew: brew install ffmpeg"


def ffmpeg_search_dirs() -> list[Path]:
    """QUILL-managed directories to check for ffmpeg/ffprobe before PATH.

    Covers the first three directory-based stops from the module
    docstring's search order (``QUILL_FFMPEG``, the bundle dir, and the
    data-dir engine pack). PATH and the Homebrew fallback directories are
    handled separately in :func:`_resolve_tool`.
    """
    dirs: list[Path] = []
    override = os.environ.get("QUILL_FFMPEG", "").strip()
    if override:
        dirs.append(Path(override).expanduser())
    app_root = os.environ.get("QUILL_APP_ROOT", "").strip()
    if app_root:
        dirs.append(Path(app_root).expanduser() / "tools" / "ffmpeg")
    dirs.append(app_data_dir() / "engine-packs" / "ffmpeg")
    return dirs


def _candidate_names(name: str) -> tuple[str, ...]:
    """Bare ``name``, plus its ``.exe`` variant when ``os.name == "nt"``."""
    return (name, f"{name}.exe") if os.name == "nt" else (name,)


def _find_in_dir(directory: Path, name: str, allowed: frozenset[str]) -> str | None:
    """Return the allowed executable named ``name`` directly inside
    ``directory``, or ``None`` if it is not there."""
    for exe in _candidate_names(name):
        candidate = directory / exe
        if candidate.is_file() and candidate.name.lower() in allowed:
            return str(candidate)
    return None


def _resolve_tool(name: str, allowed: frozenset[str]) -> str | None:
    """The full search order shared by :func:`find_ffmpeg` and
    :func:`find_ffprobe`: QUILL-managed dirs, then PATH, then Homebrew."""
    for directory in ffmpeg_search_dirs():
        found = _find_in_dir(directory, name, allowed)
        if found is not None:
            return found
    which = shutil.which(name)
    if which and Path(which).name.lower() in allowed:
        return which
    for directory in _HOMEBREW_DIRS:
        found = _find_in_dir(directory, name, allowed)
        if found is not None:
            return found
    return None


@lru_cache(maxsize=1)
def find_ffmpeg() -> str | None:
    """Path to an allowed ffmpeg executable, or ``None`` if not installed."""
    return _resolve_tool("ffmpeg", _ALLOWED_FFMPEG)


@lru_cache(maxsize=1)
def find_ffprobe() -> str | None:
    """Path to an allowed ffprobe executable, or ``None`` if not installed."""
    return _resolve_tool("ffprobe", _ALLOWED_FFPROBE)


def ffmpeg_available() -> bool:
    """True when this app can record a live stream to a local file."""
    return find_ffmpeg() is not None
