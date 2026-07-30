"""The shared Python runtime's version marker.

A shared-runtime install (the QuillVille Runtime -- one CPython + wxPython +
the shared packages, reused by every app; see
``docs/design/2026-07-21-quillville-installer-and-shared-runtime-program.md``)
drops a small JSON marker in its folder so an installer can tell, without
running anything, whether the correct runtime is already present and therefore
skip re-installing it. This module writes the marker at build time and reads it
back; the reference counting (who still needs it) lives in
:mod:`quill.core.runtime_refs`.

The marker is intentionally trivial JSON so an Inno Setup ``Check:`` function can
parse it with plain string operations during install, before any Python runs.
"""

from __future__ import annotations

import platform
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_MARKER_NAME = "quillville-runtime.json"


def runtime_version() -> str:
    """This interpreter's version as ``"major.minor.micro"`` (e.g. ``3.13.1``)."""
    return platform.python_version()


def marker_path(runtime_dir: Path) -> Path:
    return runtime_dir / _MARKER_NAME


def write_marker(runtime_dir: Path, *, python_version: str, build_id: str) -> None:
    """Stamp *runtime_dir* with the runtime version + build id (called at build time)."""
    write_json_atomic(
        marker_path(runtime_dir),
        {"python": str(python_version), "build": str(build_id)},
    )


def read_marker(runtime_dir: Path) -> dict[str, str] | None:
    """Return the marker dict for *runtime_dir*, or None if it is absent/unreadable."""
    raw = read_json(marker_path(runtime_dir), None)
    if not isinstance(raw, dict):
        return None
    python = raw.get("python")
    build = raw.get("build")
    if not isinstance(python, str):
        return None
    return {"python": python, "build": str(build) if isinstance(build, str) else ""}


def installed_version(runtime_dir: Path) -> str | None:
    """The Python version already installed in *runtime_dir*, or None."""
    marker = read_marker(runtime_dir)
    return marker["python"] if marker is not None else None


def installed_build(runtime_dir: Path) -> str | None:
    """The build id already installed in *runtime_dir*, or None.

    Returns None both when the marker is absent and when it predates build
    tracking (empty ``build`` field), so callers can treat "no known build" as
    "older than any real build" -- see :func:`needs_install`.
    """
    marker = read_marker(runtime_dir)
    if marker is None:
        return None
    return marker["build"] or None


def needs_install(
    runtime_dir: Path,
    required_version: str,
    required_build: str | None = None,
) -> bool:
    """True when *runtime_dir* does not already hold the wanted shared runtime.

    The installer's skip test: install the shared runtime only when this returns
    True. It reinstalls when either

    * the installed CPython version differs from *required_version* -- the folder
      is keyed by ``major.minor`` so two minors coexist rather than overwrite
      (see the program spec); or
    * *required_build* is given and the installed payload is **older** than it.
      Same CPython, but the bundled ``quill`` app code/data has moved on. This is
      the #1217 case: a sibling app (or an earlier build) had already dropped a
      same-Python runtime, so the version-only gate skipped the copy and the app
      kept running stale code -- Quill Radio's Reading Services folder collapsed
      to just the live tier (~7 entries) because the bundled catalog never
      shipped. Build ids are ISO dates (``yyyy-mm-dd``), so a plain string
      compare orders them.

    A newer-or-equal installed build is left in place, so installing an older app
    beside a newer one never downgrades the shared runtime.
    """
    if installed_version(runtime_dir) != str(required_version):
        return True
    if required_build:
        return (installed_build(runtime_dir) or "") < str(required_build)
    return False
