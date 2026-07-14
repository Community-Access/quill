from __future__ import annotations

import os
import sys
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic

_VALID_MODES = {"appdata", "portable", "custom"}


def _has_portable_evidence(anchor: Path) -> bool:
    """Return True when *anchor* looks like a portable QUILL bundle.

    The portable bundle layout is now ``quill.exe`` at the anchor root
    plus a sibling ``data/`` folder the build script creates for the
    user. The ``data/`` folder is the L-9-equivalent evidence: it is a
    deliberate filesystem action by the user (or by the build, which
    only stages files in the bundle directory it controls), not an
    attacker-injectable env-var value.

    ``run-quill.cmd`` is also accepted as back-compat evidence so a
    beta-1 portable bundle (which had the .cmd but no ``data/`` folder)
    keeps working until the user upgrades to a bundle that ships the
    ``data/`` folder.
    """
    if not anchor.is_dir():
        return False
    has_exe = (anchor / "quill.exe").is_file()
    has_data = (anchor / "data").is_dir()
    if has_exe and has_data:
        return True
    has_cmd = (anchor / "run-quill.cmd").is_file()
    return has_cmd


def _resolve_app_root() -> Path | None:
    """Return the verified portable-install root, or None.

    Mirrors ``paths.py::new_install_marker_path()``'s anchor-resolution
    chain (duplicated rather than imported to avoid a circular import,
    since ``paths.py`` imports this module): ``QUILL_APP_ROOT`` (set
    unconditionally by the launcher at startup) is accepted as a hint,
    then we walk up from ``sys.executable`` for a Start-Menu-style
    launch straight into ``python\\pythonw.exe`` or the hoisted
    ``quill.exe`` at the bundle root.

    L-9: a bare env var value is never trusted on its own. A candidate
    is only accepted when ``_has_portable_evidence`` returns True --
    either ``quill.exe`` + ``data/`` (the new layout) or the legacy
    ``run-quill.cmd`` marker.
    """
    env_root = os.environ.get("QUILL_APP_ROOT")
    if env_root:
        candidate = Path(env_root).expanduser().resolve()
        if _has_portable_evidence(candidate):
            return candidate
    exe = Path(sys.executable).resolve()
    # Walk up to three levels: bundle root, bundle/python/ (where the
    # embedded runtime lives), and one more in case the launcher was
    # started via a wrapper that lives a level deeper than the bundle.
    parents: list[Path] = [exe.parent, exe.parent.parent]
    if exe.parent.parent != exe.parent:
        parents.append(exe.parent.parent.parent)
    for candidate in parents:
        if _has_portable_evidence(candidate):
            return candidate
    return None


def portable_root_dir() -> Path | None:
    """Return the candidate portable-mode data folder, or None.

    The ``data`` subfolder need not exist yet -- it is created on demand
    the first time the user opts into portable mode (the Setup Wizard's
    data-location page, or Preferences). Returning a path here only means
    "this is a verified portable bundle"; whether it is actually *used*
    still depends on the saved storage mode (see :func:`load_storage_mode`).
    """
    anchor = _resolve_app_root()
    if anchor is None:
        return None
    return (anchor / "data").resolve()


def storage_mode_path() -> Path | None:
    paths = storage_mode_paths()
    if not paths:
        return None
    return paths[0]


def storage_mode_paths() -> tuple[Path, ...]:
    """Where ``storage-mode.json`` itself is read from / written to.

    Always includes the appdata fallback, even when not running portable,
    so non-portable users can still save an explicit "appdata" or "custom"
    choice (#615) without a portable bundle being present.
    """
    fallback_path = _fallback_storage_mode_path()
    root = portable_root_dir()
    if root is None:
        return (fallback_path,)
    portable_path = root / "storage-mode.json"
    if _portable_path_is_writable(portable_path):
        return (portable_path, fallback_path)
    return (fallback_path, portable_path)


def _fallback_storage_mode_path() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata).expanduser().resolve() / "Quill" / "storage-mode.json"
    return Path.home() / ".quill" / "storage-mode.json"


def _portable_path_is_writable(path: Path) -> bool:
    candidate = path if path.exists() else path.parent
    while not candidate.exists() and candidate != candidate.parent:
        candidate = candidate.parent
    return os.access(candidate, os.W_OK)


def _read_storage_mode_document() -> dict | None:
    for path in storage_mode_paths():
        if not path.exists():
            continue
        raw = read_json(path, default={})
        if not isinstance(raw, dict):
            continue
        mode = raw.get("mode")
        if isinstance(mode, str) and mode in _VALID_MODES:
            return raw
    return None


def load_storage_mode() -> str | None:
    document = _read_storage_mode_document()
    if document is None:
        return None
    mode = document.get("mode")
    return mode if isinstance(mode, str) else None


def custom_path() -> Path | None:
    """Return the saved custom data directory when ``mode == "custom"``."""
    document = _read_storage_mode_document()
    if document is None or document.get("mode") != "custom":
        return None
    raw_path = document.get("path")
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    return Path(raw_path).expanduser().resolve()


def save_storage_mode(mode: str, *, path: Path | None = None) -> None:
    if mode not in _VALID_MODES:
        raise ValueError(f"Unknown storage mode: {mode}")
    if mode == "custom" and path is None:
        raise ValueError("Custom storage mode requires a path")
    document: dict[str, object] = {"mode": mode}
    if mode == "custom" and path is not None:
        document["path"] = str(path)
    paths = storage_mode_paths()
    if not paths:
        raise RuntimeError("Portable root is not configured")
    last_error: PermissionError | None = None
    for candidate in paths:
        try:
            write_json_atomic(candidate, document)
            return
        except PermissionError as error:
            last_error = error
    assert last_error is not None
    raise last_error
