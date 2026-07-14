"""Locate ``git`` and ``gh`` executables: system PATH first, QUILL-managed
vendor copy second, following the packaging plan in
``docs/planning/github.md`` section 2.

Design:

- **Prefer the system's own copy.** Most development machines already have
  `git`; using it directly avoids a duplicate install and any version-drift
  reasoning. The bundled copy (fetched on demand via
  ``quill.core.release_assets``, same mechanism as Pandoc/Vosk/Kokoro/the
  braille pack) exists specifically for the user who has never installed
  either -- exactly the person the local-git accessibility work in
  ``quill.core.local_git`` is for.
- **A narrow subprocess allowlist**, mirroring the reasoning behind
  ``quill.core.ai.external_engine``'s ``_ENGINE_EXECUTABLE_BASENAMES`` but
  scoped to this module's own boundary: a tampered settings file (or a
  vendor directory an attacker could write to) must never turn a git-
  integration feature into an arbitrary-executable launcher.
- No network calls here. This module only *locates* binaries; fetching a
  missing one is ``release_assets.fetch_component``'s job, triggered by an
  explicit user action in Help > Download Optional Components.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

from quill.core.paths import app_data_dir

#: Basenames this module will ever treat as a legitimate git/gh executable.
#: Enforced by :func:`validate_executable` before any resolved path is handed
#: to a subprocess call -- the one place every local-git and gh-bridge call
#: site should route through.
_GIT_EXECUTABLE_BASENAMES = frozenset({
    "git",
    "git.exe",
    "gh",
    "gh.exe",
})


class GitBinaryError(RuntimeError):
    """Raised when a resolved or configured executable fails validation."""


def _vendor_dir() -> Path:
    """Where QUILL's own bundled git/gh land, mirroring the braille pack's
    ``app_data_dir() / "vendor" / <name>`` convention."""
    return app_data_dir() / "vendor" / "git"


def vendor_dir() -> Path:
    """Public accessor for the shared git/gh vendor directory, for the
    ``release_assets.fetch_component`` download target and the Download
    Optional Components removal path (``quill.core.optional_components``)."""
    return _vendor_dir()


def validate_executable(path: Path) -> Path:
    """Raise :class:`GitBinaryError` unless *path*'s basename is an allowed
    git/gh executable name. Callers use this right before building a
    subprocess command line, so a corrupted or tampered path can never
    silently become "run whatever this string points at"."""
    if path.name not in _GIT_EXECUTABLE_BASENAMES:
        raise GitBinaryError(f"Refusing to run {path}: not a recognized git/gh executable name.")
    return path


def _vendor_candidate(basename: str) -> Path:
    exe = f"{basename}.exe" if sys.platform == "win32" else basename
    if basename == "git":
        # MinGit's git.exe lives at <vendor_dir>/cmd/git.exe, alongside
        # sibling etc/, mingw64/, usr/ folders it needs at runtime -- see the
        # "git-windows" ASSETS entry in quill.core.release_assets for why the
        # fetched layout is nested rather than flat.
        return _vendor_dir() / "cmd" / exe
    return _vendor_dir() / exe


def resolve_git() -> Path | None:
    """Return a usable ``git`` executable: system ``PATH`` first, then the
    QUILL-managed vendor copy. ``None`` if neither is present."""
    on_path = shutil.which("git")
    if on_path:
        return validate_executable(Path(on_path))
    candidate = _vendor_candidate("git")
    if candidate.exists():
        return validate_executable(candidate)
    return None


def resolve_gh() -> Path | None:
    """Return a usable ``gh`` executable: system ``PATH`` first, then the
    QUILL-managed vendor copy. ``None`` if neither is present."""
    on_path = shutil.which("gh")
    if on_path:
        return validate_executable(Path(on_path))
    candidate = _vendor_candidate("gh")
    if candidate.exists():
        return validate_executable(candidate)
    return None


def git_available() -> bool:
    return resolve_git() is not None


def gh_available() -> bool:
    return resolve_gh() is not None


__all__ = [
    "GitBinaryError",
    "gh_available",
    "git_available",
    "resolve_gh",
    "resolve_git",
    "validate_executable",
    "vendor_dir",
]
