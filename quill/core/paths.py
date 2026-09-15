from __future__ import annotations

import os
import sys
from collections.abc import Callable
from pathlib import Path

from quill.core import storage_mode
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


def safe_dialog_filename(name: str, *, suffix: str = "", fallback: str = "Untitled") -> str:
    """A filename safe to hand a native Save panel as ``defaultFile`` (#1345).

    A macOS ``SystemError: ActivateEvent returned a result with an exception
    set`` was reported while a notebook was being created from a folder whose
    name began with an emoji: the suggested filename went straight into the
    native save panel, and the underlying ``wxAssertionError`` ("nIndex <
    m_nCount", arrstr.h) came out of native code during that panel's
    activation. Emoji, control characters and the reserved path characters are
    stripped here so a folder name can never be what reaches the panel raw.

    The *display* name is never touched -- only the filename suggestion, which
    the user can edit anyway.
    """
    cleaned = []
    for char in str(name):
        code = ord(char)
        if code < 0x20 or code == 0x7F:  # control characters
            continue
        if char in '<>:"/\\|?*':  # reserved on Windows, awkward everywhere
            continue
        if code > 0xFFFF or 0x2190 <= code <= 0x2BFF or 0xFE00 <= code <= 0xFE0F:
            # Astral-plane characters (all emoji live there), the symbol and
            # arrow blocks, and variation selectors.
            continue
        cleaned.append(char)
    result = "".join(cleaned).strip(" .")
    if not result:
        result = fallback
    return f"{result}{suffix}"


#: Set by an app whose own data does NOT live in QUILL's folder -- QuillLite is
#: the only one today. ``None`` means "this app is QUILL, or shares its store".
_RUNNING_APP_DATA_DIR: Callable[[], Path] | None = None


def use_running_app_data_dir(provider: Callable[[], Path] | None) -> None:
    """Declare where the *running* app keeps its data. Called once, at startup.

    See :func:`running_app_data_dir` for what this is for and why it is not
    simply an override of :func:`app_data_dir`.
    """
    global _RUNNING_APP_DATA_DIR
    _RUNNING_APP_DATA_DIR = provider


def running_app_data_dir() -> Path:
    r"""Where the app that is running keeps its own files.

    **Not the same question as** :func:`app_data_dir`, which answers "where is
    QUILL's data folder" -- the shared store QUILL, Inkwell and the QuillVille
    apps all use, and which QuillLite reaches on purpose in exactly three
    places (share QUILL's dictionary, share QUILL's abbreviations, list QUILL's
    sound schemes). Those say "QUILL's data directory" in their docstrings and
    must keep meaning it.

    This one is for a *cache or private store the running app needs somewhere*
    -- the comtypes generated-wrapper cache and the managed Hunspell folder.
    Both used :func:`app_data_dir`, and for QuillLite that was the wrong folder:
    one ``--check`` on a machine that had never seen QUILL created
    ``%APPDATA%\Quill\comtypes_gen`` and ``%APPDATA%\Quill\spell``, because
    the native Rich Edit surface goes through comtypes and the spell checker
    goes through the managed dir. ``quill/core/lite/paths.py`` opens by saying
    QuillLite is "deliberately **not** ``%APPDATA%\Quill``", and
    ``core/lite/settings.py`` that "a machine that has never had QUILL
    installed must not grow a Quill data folder because somebody opened a text
    file". It grew one on first launch (verified 2026-09-15).

    Defaults to :func:`app_data_dir`, so every app that has not declared
    otherwise is unaffected.
    """
    provider = _RUNNING_APP_DATA_DIR
    if provider is not None:
        try:
            return provider()
        except Exception:  # noqa: BLE001 - a bad provider must not lose the cache
            pass
    return app_data_dir()


def app_data_dir() -> Path:
    override = os.environ.get("QUILL_DATA_DIR")
    if override and _DEV_BUILD:
        resolved = Path(override).expanduser().resolve()
        if _is_constrained_to_home(resolved):
            return resolved
    # Release build: ignore the env var entirely.
    mode = load_storage_mode()
    if mode == "custom":
        custom = storage_mode.custom_path()
        if custom is not None:
            return custom
        # Saved custom path is unavailable (e.g. cleared externally); fall
        # through to the appdata default below rather than raising.
    portable_root = portable_root_dir()
    # ``mode is None`` means the user has never chosen, and in a *verified*
    # portable bundle the answer to a question nobody asked is portable.
    # Until 2026-09-09 it was %APPDATA%: extract the zip, run it, and QUILL
    # created a folder on the host machine's hard drive -- which is precisely
    # the thing somebody running from a USB stick chose the portable build to
    # avoid, and they had no way to know it had happened. The user guide has
    # said "portable mode is a property of the bundle, not of the running
    # environment" the whole time; this makes that true.
    #
    # An explicit "appdata" or "custom" still wins, because that is a choice
    # rather than a default, and ``portable_root`` is None for every
    # non-portable install, so nothing else moves.
    if portable_root is not None and mode in {"portable", None}:
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


def machine_local_dir() -> Path:
    """Where machine-local, regenerable data (caches) belongs.

    The same directory as :func:`app_data_dir` -- except when the data folder
    is a *custom* location. Custom folders exist to be synced between machines
    (the Setup Wizard's own tip is to pick a Dropbox/OneDrive/Google Drive
    folder), and syncing the station catalog or the directory caches is pure
    churn: megabytes of regenerable bytes that legitimately differ per
    machine, re-uploaded on every refresh. Those stay in this machine's
    default profile location instead, under ``machine-cache``.

    Portable mode deliberately keeps everything on the stick -- self-contained
    is the point there -- and appdata mode is already machine-local, so both
    resolve to :func:`app_data_dir` unchanged. The dev override
    (``QUILL_DATA_DIR``) also resolves to :func:`app_data_dir`, so tests stay
    isolated in one directory.
    """
    override = os.environ.get("QUILL_DATA_DIR")
    if override and _DEV_BUILD:
        return app_data_dir()
    if load_storage_mode() == "custom" and storage_mode.custom_path() is not None:
        appdata = os.environ.get("APPDATA")
        base = Path(appdata) / "Quill" if appdata else Path.home() / ".quill"
        return base / "machine-cache"
    return app_data_dir()


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

    from quill.core.storage_mode import _has_portable_evidence

    marker_name = "quill-new-install.txt"

    # Primary: QUILL_APP_ROOT exported by the launcher at startup. The
    # launcher sets it whenever a portable anchor is detected.
    app_root_env = os.environ.get("QUILL_APP_ROOT")
    if app_root_env:
        candidate = Path(app_root_env).expanduser().resolve()
        if _has_portable_evidence(candidate):
            return candidate / marker_name

    # Fallback: Start Menu shortcut calls quill.exe (or pythonw.exe for
    # legacy bundles) directly; the exe lives at the bundle root or at
    # {app}\python\, so the install root is one or two levels up.
    exe = Path(sys.executable).resolve()
    parents: list[Path] = [exe.parent, exe.parent.parent]
    if exe.parent.parent != exe.parent:
        parents.append(exe.parent.parent.parent)
    for candidate in parents:
        if _has_portable_evidence(candidate):
            return candidate / marker_name

    return None


def ensure_app_directories() -> None:
    root = app_data_dir()
    for relative in ("", "logs", "diagnostics", "backups", "autosave", "sessions"):
        (root / relative).mkdir(parents=True, exist_ok=True)
