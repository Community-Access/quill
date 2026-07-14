"""Detect and install the optional QUILL Braille Pack (#243 / BR-020).

The pack bundles liblouis plus the English UEB tables and powers the Translation
submenu (BR-022). It is entirely optional: when absent, the Translation submenu
is hidden so users never see disabled items. Detection is non-invasive (PATH,
bundled binding, or a python module) and never imports liblouis in-process.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

# Names that, if present, indicate a usable liblouis install shipped with the
# pack: the CLI tools on PATH, or the python binding importable.
_PACK_EXECUTABLES = ("lou_translate", "louis")
_PACK_MODULES = ("louis", "lou_translate")

# Footprint unbundle: the pack (~68 MB of translation tables) is no longer
# shipped in the installer. It is fetched on demand from QUILL's pinned,
# SHA-256-verified assets-v1 release into this app-data directory. The resolvers
# below prefer a bundled copy (upgraders keep theirs) but also find the download.
_RELEASE_COMPONENT = "braille"


def managed_braille_dir() -> Path:
    """The app-data directory the downloaded braille pack is extracted into."""
    from quill.core.paths import app_data_dir

    return app_data_dir() / "vendor" / "braille-pack"


def _find_install_root() -> Path | None:
    """Return the Quill install root when running from a bundled install.

    The Start Menu shortcut calls pythonw.exe -m quill directly (bypassing
    run-quill.cmd and its QUILL_APP_ROOT export). pythonw.exe lives at
    {app}\\python\\pythonw.exe, so walk up two levels to reach {app}. Confirm
    it is actually a Quill install directory by checking for run-quill.cmd.
    """
    exe = Path(sys.executable)
    for candidate in (exe.parent, exe.parent.parent):
        if (candidate / "run-quill.cmd").exists():
            return candidate
    return None


def is_braille_pack_installed() -> bool:
    """Return True when a liblouis-backed braille pack is available."""
    import os

    pack_rel = Path("vendor") / "braille-pack" / "lou_translate.exe"

    # Primary: QUILL_APP_ROOT is set by run-quill.cmd for .cmd launches.
    app_root_env = os.environ.get("QUILL_APP_ROOT")
    if app_root_env:
        if (Path(app_root_env) / pack_rel).exists():
            return True

    # Fallback: Start Menu shortcut calls pythonw.exe directly; infer root
    # from the executable path so the bundled pack is still found.
    install_root = _find_install_root()
    if install_root is not None:
        if (install_root / pack_rel).exists():
            return True

    # On-demand download location (footprint unbundle).
    if (managed_braille_dir() / "lou_translate.exe").exists():
        return True

    if any(shutil.which(name) for name in _PACK_EXECUTABLES):
        return True
    if any(name in sys.modules for name in _PACK_MODULES):
        return True
    for module in _PACK_MODULES:
        try:
            if importlib.util.find_spec(module) is not None:
                return True
        except (ImportError, ValueError):
            continue
    return False


def braille_pack_version() -> str | None:
    """Return the installed liblouis version string, or None when not installed.

    liblouis is never imported in-process (BR-020) -- there is no Python
    ``louis`` module to ask. The version is read from the pack's own
    manifest.json, written by build_braille_pack.py at build time (the same
    file get_brf_profiles() reads brf_profiles.json alongside).
    """
    if not is_braille_pack_installed():
        return None
    for path in _pack_file_candidates("manifest.json"):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except Exception:  # noqa: BLE001
                continue
            version = data.get("liblouis_version")
            return str(version) if version else "unknown"
    return "unknown"


def _pack_file_candidates(filename: str) -> list[Path]:
    """Search-ordered candidate paths for *filename* alongside the pack.

    1. ``{QUILL_APP_ROOT}/vendor/braille-pack/`` — set by run-quill.cmd in the
       installer build; covers both portable and installed modes.
    2. the managed app-data pack dir (``managed_braille_dir()``) — where the
       on-demand download extracts to (footprint unbundle).
    3. ``<repo-root>/liblouis/vendor/braille/pack/`` — dev source tree.
    4. ``<repo-root>/vendor/braille-pack/`` — portable staging path.
    """
    import os

    candidates: list[Path] = []

    app_root_env = os.environ.get("QUILL_APP_ROOT")
    if app_root_env:
        candidates.append(Path(app_root_env) / "vendor" / "braille-pack" / filename)

    # On-demand download location (footprint unbundle).
    candidates.append(managed_braille_dir() / filename)

    repo_root = Path(__file__).resolve().parents[2]
    candidates += [
        repo_root / "liblouis" / "vendor" / "braille" / "pack" / filename,
        repo_root / "vendor" / "braille-pack" / filename,
    ]
    return candidates


def get_brf_profiles() -> list[dict]:
    """Return the list of BRF profiles from the installed pack's brf_profiles.json.

    Searches the vendor braille pack directory for brf_profiles.json. Returns
    an empty list when the pack is not installed or the file cannot be read.
    """
    for path in _pack_file_candidates("brf_profiles.json"):
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                return list(data.get("profiles", []))
            except Exception:  # noqa: BLE001
                continue
    return []


def install_braille_pack(
    progress: Callable[[float, str], None] | None = None,
    *,
    should_cancel: Callable[[], bool] | None = None,
) -> Path:
    """Download and verify the braille pack on demand (footprint unbundle).

    Fetches QUILL's pinned, SHA-256-verified pack from the assets-v1 release
    (via :func:`quill.core.release_assets.fetch_component`) and extracts it into
    :func:`managed_braille_dir`. Returns the install directory. Raises
    ``ReleaseAssetError`` (Safe Mode, network, checksum) or ``DownloadCancelled``
    -- the same contract as the other on-demand components -- so the UI can
    degrade cleanly. GATE-9: the network egress lives in ``release_assets``.
    """
    from quill.core.release_assets import fetch_component

    return fetch_component(
        _RELEASE_COMPONENT,
        managed_braille_dir(),
        progress=progress,
        should_cancel=should_cancel,
        label="Downloading the braille pack...",
    )
