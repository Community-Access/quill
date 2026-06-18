from __future__ import annotations

import os
import sys
from pathlib import Path

from quill.core.storage_mode import load_storage_mode, portable_root_dir

# H-1-core: ``QUILL_DATA_DIR`` is documented as a *dev-only* override. In
# release builds we ignore it entirely, so a tampered environment cannot
# redirect the user's settings, undo, recovery, or AI session files to an
# attacker-controlled directory. Development builds (CI, local testing)
# opt in by exporting ``QUILL_DEV_BUILD=1`` in the environment, or by
# setting the module-private ``_DEV_BUILD`` flag below to ``True``.
_DEV_BUILD = os.environ.get("QUILL_DEV_BUILD") == "1" or False  # dev override opt-in


def _is_constrained_to_home(candidate: Path) -> bool:
    """H-1-core: the dev override is accepted only when it stays under $HOME.

    ``Path.resolve()`` follows symlinks, so a malicious
    ``QUILL_DATA_DIR=/home/user/.config/Quill`` that is a symlink into
    ``/etc`` will fail the check. ``is_relative_to`` is new in Python 3.9
    and QUILL's PRD pins 3.12.
    """
    try:
        home = Path.home().resolve()
    except OSError:
        return False
    try:
        return candidate.is_relative_to(home)
    except (OSError, ValueError):
        return False


def app_data_dir() -> Path:
    override = os.environ.get("QUILL_DATA_DIR")
    if override and _DEV_BUILD:
        resolved = Path(override).expanduser().resolve()
        if _is_constrained_to_home(resolved):
            return resolved
    # Release build: ignore the env var entirely.
    portable_root = portable_root_dir()
    if portable_root is not None:
        mode = load_storage_mode()
        if mode == "portable":
            return portable_root
        if mode == "appdata":
            appdata = os.environ.get("APPDATA")
            if appdata:
                return Path(appdata) / "Quill"
            if sys.platform == "win32":
                raise RuntimeError(
                    "Could not determine the Quill data directory: APPDATA is not set. "
                    "Please set QUILL_DATA_DIR (dev) or APPDATA in your environment."
                )
            return Path.home() / ".quill"

    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "Quill"

    if sys.platform == "win32":
        raise RuntimeError(
            "Could not determine the Quill data directory: APPDATA is not set. "
            "Please set QUILL_DATA_DIR (dev) or APPDATA in your environment."
        )
    return Path.home() / ".quill"


def new_install_marker_path() -> Path | None:
    """Return the path of the installer's new-install marker file, or None.

    The installer writes quill-new-install.txt to {app} on every install
    (including upgrades). Startup consumes it to reset setup_wizard_completed
    so the first-run wizard re-runs after a reinstall, even when %APPDATA%
    settings from a prior install say the wizard already completed.

    Returns None when the install root cannot be determined (e.g., a dev run
    without a bundled install directory) so the caller can safely skip the
    check without touching anything.
    """
    import os

    marker_name = "quill-new-install.txt"

    # Primary: QUILL_APP_ROOT exported by run-quill.cmd.
    app_root_env = os.environ.get("QUILL_APP_ROOT")
    if app_root_env:
        return Path(app_root_env) / marker_name

    # Fallback: Start Menu shortcut calls pythonw.exe directly; pythonw.exe
    # lives at {app}\python\, so the install root is one or two levels up.
    exe = Path(sys.executable)
    for candidate in (exe.parent, exe.parent.parent):
        if (candidate / "run-quill.cmd").exists():
            return candidate / marker_name

    return None


def ensure_app_directories() -> None:
    root = app_data_dir()
    for relative in ("", "logs", "diagnostics", "backups", "autosave", "sessions"):
        (root / relative).mkdir(parents=True, exist_ok=True)
