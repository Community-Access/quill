"""Reclaim shared-runtime slots for a Python no installed app runs on any more.

Moving the shared runtime to a new Python minor (3.13 -> 3.14, 2026-10-11)
leaves the old slot behind: each updated app moves its reference to the new
slot, and an app's uninstaller only ever removes the slot its own ini names, so
nothing removes ``Runtime\\3.13`` (about 335 MB) once every app has moved on.
Every app installer runs :func:`reclaim` (``runtime_cli reclaim-old-slots``)
right after registering, so the last app to move is the one that frees it.

**Release channels leave slots behind too** (2026-10-15). An app that moves
from Beta back to Stable is reinstalled into ``Runtime\\3.14`` and its reference
moves with it, but nothing removed ``Runtime\\3.14-beta`` -- the uninstaller
only runs on uninstall -- so the "about 335 MB comes back" the risk window
promises never came back. So a **Beta or Dev slot of the current Python** is a
candidate too (:func:`abandoned_channel_slots`), under exactly the same tests.
The slot being installed into, the current Python's Stable slot, and any slot
of a newer Python are never candidates.

**Only when nothing can still need it.** A candidate is kept while any of
these hold:

* :func:`quill.core.runtime_refs.slot_referenced` -- an app is registered
  against it (apps register at every launch, not only at install);
* an installed app's ``quill-app-version.ini`` names it in ``[runtime] slot=``;
* it is a Stable slot and some installed app's ini has no ``slot=`` at all.
  Installers write ``slot=`` since release channels (2026-10); an app installed
  before that and never updated runs on the Python its launcher was built for,
  which is older than the current one, so every older Stable slot stays.

* a Start menu, Desktop or Startup shortcut, or a ``Run`` entry, launches from
  it. The earliest installers had no ini and pointed their shortcuts straight
  at ``Runtime\\3.13\\QuillVilleRuntime.exe -m quill.apps.radio``; the runtime
  carries the app's code, so such a shortcut still works -- found on a real
  machine whose Radio 3.0.0 install folder was long gone (2026-10-12);
* it is a Stable slot and a Community Access install folder exists with
  neither an ini nor a private runtime of its own.

An app with its own private runtime (``python.exe`` or ``_internal\\python.exe``
beside its ini) uses no shared slot and is ignored. Removing a runtime an app
still needs would stop that app starting, so every doubt keeps the slot.

wx-free; Windows registry reads are confined to :func:`installed_app_dirs`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable, Iterable
from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path

from quill.core.runtime_refs import slot_referenced
from quill.core.updater.channels import STABLE
from quill.core.updater.runtime_slots import channel_of_slot, is_valid_slot

__all__ = [
    "InstallScan",
    "abandoned_channel_slots",
    "ReclaimResult",
    "launch_references",
    "older_slots",
    "reclaim",
    "runtime_root",
    "scan_installs",
    "slots_launched_by",
    "slots_named_by_installs",
]

_PUBLISHER = "Community Access"

#: The Inno uninstall keys of the runtime installers for the two 3.13 slots;
#: later slots use ``<base>-<slot>_is1`` (``quillville-runtime.iss``).
_RUNTIME_APPID_BASE = "{6D6B0E7C-51A4-4B5E-9E0D-2F8B4C0A9137}"
_LEGACY_UNINSTALL_KEYS = {
    "3.13": "{6D6B0E7C-51A4-4B5E-9E0D-2F8B4C0A9137}_is1",
    "3.13-beta": "{6D6B0E7C-51A4-4B5E-9E0D-2F8B4C0A9138}_is1",
}
_UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall"
_UNINSTALLER_WAIT_S = 60.0


@dataclass(frozen=True, slots=True)
class ReclaimResult:
    """What happened to one older slot: ``removed`` or ``kept``, and why."""

    slot: str
    action: str
    reason: str


def runtime_root() -> Path:
    """``%LOCALAPPDATA%\\QuillVille\\Runtime``, where every slot lives."""
    return Path(os.environ.get("LOCALAPPDATA", "")) / "QuillVille" / "Runtime"


def _minor(slot: str) -> tuple[int, int] | None:
    if not is_valid_slot(slot):
        return None
    major, minor = slot.split("-", 1)[0].split(".")
    return int(major), int(minor)


def older_slots(root: Path, current_slot: str) -> list[str]:
    """Slot folders under *root* for a Python older than *current_slot*'s."""
    current = _minor(current_slot)
    if current is None:
        return []
    try:
        names = [entry.name for entry in root.iterdir() if entry.is_dir()]
    except OSError:
        return []
    return sorted(name for name in names if (m := _minor(name)) is not None and m < current)


def abandoned_channel_slots(root: Path, current_slot: str) -> list[str]:
    """Beta and Dev slot folders for *current_slot*'s Python, other than *current_slot*.

    Installing Quill Radio back onto Stable (``3.14``) makes ``3.14-beta`` a
    candidate; installing it onto Beta makes ``3.14-dev`` one. Whether a
    candidate is really unused is :func:`reclaim`'s question.
    """
    current = _minor(current_slot)
    if current is None:
        return []
    try:
        names = [entry.name for entry in root.iterdir() if entry.is_dir()]
    except OSError:
        return []
    return sorted(
        name
        for name in names
        if name != current_slot and _minor(name) == current and channel_of_slot(name) != STABLE
    )


def _has_private_runtime(app_dir: Path) -> bool:
    return (app_dir / "python.exe").is_file() or (app_dir / "_internal" / "python.exe").is_file()


def slots_named_by_installs(app_dirs: Iterable[Path]) -> tuple[set[str], bool]:
    """The slots installed apps' inis name, and whether any ini names none.

    An ini that cannot be read counts as naming none: the safe answer.
    """
    named: set[str] = set()
    unknown = False
    for app_dir in app_dirs:
        ini_path = app_dir / "quill-app-version.ini"
        if not ini_path.is_file() or _has_private_runtime(app_dir):
            continue
        parser = ConfigParser(interpolation=None)
        try:
            parser.read(ini_path, encoding="utf-8-sig")
            slot = parser.get("runtime", "slot", fallback="").strip()
        except Exception:  # noqa: BLE001 - unreadable means "assume the old slot"
            slot = ""
        if is_valid_slot(slot):
            named.add(slot)
        else:
            unknown = True
    return named, unknown


@dataclass(frozen=True, slots=True)
class InstallScan:
    """Installed apps with an ini, and whether any install exists without one."""

    app_dirs: list[Path]
    unknown_install: bool


def _uninstall_entries() -> list[tuple[str, str]]:
    """``(InstallLocation, Publisher)`` of every Uninstall entry, all hives."""
    if sys.platform != "win32":
        return []
    import winreg

    hives = (
        (winreg.HKEY_CURRENT_USER, 0),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_64KEY),
        (winreg.HKEY_LOCAL_MACHINE, winreg.KEY_WOW64_32KEY),
    )
    entries: list[tuple[str, str]] = []
    for hive, view in hives:
        try:
            root = winreg.OpenKey(hive, _UNINSTALL, 0, winreg.KEY_READ | view)
        except OSError:
            continue
        with root:
            index = 0
            while True:
                try:
                    name = winreg.EnumKey(root, index)
                except OSError:
                    break
                index += 1
                values: list[str] = []
                try:
                    with winreg.OpenKey(root, name) as entry:
                        for value_name in ("InstallLocation", "Publisher"):
                            try:
                                values.append(str(winreg.QueryValueEx(entry, value_name)[0]))
                            except OSError:
                                values.append("")
                except OSError:
                    continue
                entries.append((values[0], values[1]))
    return entries


def scan_installs(entries: Iterable[tuple[str, str]] | None = None) -> InstallScan:
    """Which installed apps carry an ini, and whether a Community Access install
    folder exists with neither an ini nor a private runtime (assume it is old)."""
    found: dict[str, Path] = {}
    unknown = False
    for location, publisher in _uninstall_entries() if entries is None else entries:
        text = location.strip().strip('"')
        if not text:
            continue
        path = Path(text)
        if (path / "quill-app-version.ini").is_file():
            found[str(path).lower()] = path
        elif publisher.strip() == _PUBLISHER and path.is_dir() and not _has_private_runtime(path):
            unknown = True
    return InstallScan(list(found.values()), unknown)


def launch_references() -> list[bytes]:
    """The raw bytes of everything that can launch an app at a click or login:
    Start menu, Desktop and Startup shortcuts, and ``Run`` values. Searched for a
    slot's path, so no shortcut parsing (or COM) is needed."""
    blobs: list[bytes] = []
    folders = [
        Path(os.environ.get("APPDATA", "")) / "Microsoft" / "Windows" / "Start Menu",
        Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft" / "Windows" / "Start Menu",
        Path(os.environ.get("USERPROFILE", "")) / "Desktop",
        Path(os.environ.get("PUBLIC", "")) / "Desktop",
    ]
    for folder in folders:
        if not str(folder) or not folder.is_dir():
            continue
        for link in folder.rglob("*.lnk"):
            try:
                blobs.append(link.read_bytes())
            except OSError:
                continue
    if sys.platform == "win32":
        import winreg

        for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
            try:
                key = winreg.OpenKey(hive, r"Software\Microsoft\Windows\CurrentVersion\Run")
            except OSError:
                continue
            with key:
                index = 0
                while True:
                    try:
                        _name, value, _kind = winreg.EnumValue(key, index)
                    except OSError:
                        break
                    index += 1
                    blobs.append(str(value).encode("utf-16-le"))
    return blobs


def slots_launched_by(root: Path, slots: Iterable[str], blobs: Iterable[bytes]) -> set[str]:
    """The *slots* whose folder a shortcut or ``Run`` value points into.

    A ``.lnk`` stores its target in ANSI and/or UTF-16, so both are searched,
    case-insensitively, with a trailing separator so ``3.13`` never matches
    ``3.13-beta``.
    """
    needles = {
        slot: [
            f"{root / slot}\\".lower().encode(encoding, "ignore")
            for encoding in ("mbcs" if sys.platform == "win32" else "latin-1", "utf-16-le")
        ]
        for slot in slots
    }
    hits: set[str] = set()
    for blob in blobs:
        lowered = blob.lower()
        for slot, patterns in needles.items():
            if any(pattern in lowered for pattern in patterns):
                hits.add(slot)
    return hits


def _forget_uninstall_entry(slot: str, slot_dir: Path) -> None:
    """Drop the slot's Programs and Features entry once its folder is gone."""
    if sys.platform != "win32":
        return
    import winreg

    key = _LEGACY_UNINSTALL_KEYS.get(slot, f"{_RUNTIME_APPID_BASE}-{slot}_is1")
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, f"{_UNINSTALL}\\{key}") as entry:
            location, _kind = winreg.QueryValueEx(entry, "InstallLocation")
        if Path(str(location).strip().strip('"')).resolve() != slot_dir.resolve():
            return  # not this folder's entry; leave it alone
        winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{_UNINSTALL}\\{key}")
    except OSError:
        pass


def _remove_slot(slot_dir: Path, slot: str) -> bool:
    """Its own uninstaller first (so its Programs and Features entry goes), then
    whatever is left. True when the folder is gone."""
    uninstaller = slot_dir / "unins000.exe"
    if uninstaller.is_file():
        try:
            subprocess.run(
                [str(uninstaller), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"],
                check=False,
                timeout=_UNINSTALLER_WAIT_S,
            )
        except (OSError, subprocess.SubprocessError):
            pass
        # Inno's uninstaller hands the work to a copy of itself and exits.
        deadline = time.monotonic() + _UNINSTALLER_WAIT_S
        while slot_dir.exists() and time.monotonic() < deadline:
            time.sleep(1.0)
    shutil.rmtree(slot_dir, ignore_errors=True)
    gone = not slot_dir.exists()
    if gone:
        _forget_uninstall_entry(slot, slot_dir)
    return gone


def reclaim(
    data_dir: Path,
    root: Path,
    current_slot: str,
    installs: InstallScan,
    launch_blobs: Iterable[bytes],
    *,
    remove: Callable[[Path, str], bool] = _remove_slot,
) -> list[ReclaimResult]:
    """Remove every older-Python slot, and every Beta or Dev slot this Python's
    apps have left, that nothing can still need; say what happened."""
    named, unknown = slots_named_by_installs(installs.app_dirs)
    unknown = unknown or installs.unknown_install
    candidates = older_slots(root, current_slot) + abandoned_channel_slots(root, current_slot)
    launched = slots_launched_by(root, candidates, launch_blobs)
    results: list[ReclaimResult] = []
    for slot in candidates:
        if slot_referenced(data_dir, slot):
            results.append(ReclaimResult(slot, "kept", "an app is registered on it"))
        elif slot in named:
            results.append(ReclaimResult(slot, "kept", "an installed app's ini names it"))
        elif slot in launched:
            results.append(ReclaimResult(slot, "kept", "a shortcut or startup entry runs from it"))
        elif unknown and channel_of_slot(slot) == STABLE:
            results.append(
                ReclaimResult(slot, "kept", "an installed app predates slot= and may use it")
            )
        elif remove(root / slot, slot):
            results.append(ReclaimResult(slot, "removed", "no installed app uses it"))
        else:
            results.append(ReclaimResult(slot, "kept", "could not remove it (files in use?)"))
    return results
