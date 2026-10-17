"""The drive a file is on, as reviewable text: what it is, how big, how full.

Todo item 46 (2026-10-17): the family's existing properties windows -- Quill
Radio's **Local Media Item Properties** and Quill Converter's **File
Properties** -- show one fact a line in a read-only box somebody can arrow
through and copy. Neither said anything about the drive the file lives on,
which is the question a person asks next when a recording will not save or a
conversion stops part-way: *is that drive full, and which drive is it?* This
module answers it in the same shape, a few labelled lines added to those
boxes, rather than as a file manager of its own:

    Drive: D:\\ (Music), local disk, NTFS
    Drive capacity: 931 GB (999,543,627,776 bytes)
    Drive used: 612 GB (657,129,013,248 bytes), 66 percent
    Drive free: 319 GB (342,414,614,528 bytes)

**Units** are the ones File Explorer shows -- powers of 1024, written KB, MB,
GB and TB -- so the numbers match what a sighted colleague reads off the same
drive, with the exact byte count beside them for anybody who needs it.

**What can go wrong is said, never raised.** A removable drive that has been
pulled out, a network share that has dropped, or a folder Windows will not let
QUILL look at each becomes one plain line ("Drive: not available. ..."), and
the rest of the properties still show: the drive is extra information, and a
problem reading it must not cost somebody the file's own details.

**Free** is the space *this* user can still write, which is what Windows
reports through ``GetDiskFreeSpaceEx`` (``shutil.disk_usage``) and is what
matters before a save; on a drive with quotas it can be less than the drive's
total free space.

wx-free and strict-typed. The Windows calls are ``GetVolumePathNameW``,
``GetVolumeInformationW`` and ``GetDriveTypeW``, read-only, local, and
reached through :func:`probe_volume`, which a test replaces.
"""

from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "DRIVE_KINDS",
    "VolumeInfo",
    "describe_volume",
    "format_capacity",
    "probe_volume",
    "volume_problem",
]

#: ``GetDriveTypeW`` results, as a person says them.
DRIVE_KINDS: dict[int, str] = {
    2: "removable drive",
    3: "local disk",
    4: "network drive",
    5: "CD or DVD drive",
    6: "RAM disk",
}

_UNITS = ("KB", "MB", "GB", "TB", "PB")


@dataclass(frozen=True, slots=True)
class VolumeInfo:
    """The drive (volume) a path is on."""

    root: str  # "C:\\", "\\\\server\\share\\", or "/" elsewhere
    label: str
    file_system: str
    kind: str  # one of DRIVE_KINDS' values, or "drive"
    total: int
    used: int
    free: int


def format_capacity(size_bytes: int) -> str:
    """A size the way File Explorer writes it, with the exact bytes beside it.

    Powers of 1024, three significant figures: ``931 GB``, ``12.3 GB``,
    ``1.50 TB``. Under one kilobyte it is just the bytes.
    """
    exact = max(0, int(size_bytes))
    if exact < 1024:
        return f"{exact:,} byte{'' if exact == 1 else 's'}"
    value = float(exact) / 1024
    index = 0
    while value >= 1024 and index < len(_UNITS) - 1:
        value /= 1024
        index += 1
    unit = _UNITS[index]
    if value >= 100:
        shown = f"{value:.0f}"
    elif value >= 10:
        shown = f"{value:.1f}"
    else:
        shown = f"{value:.2f}"
    return f"{shown} {unit} ({exact:,} bytes)"


def _windows_details(path: str) -> tuple[str, str, str, str]:
    """(root, label, file system, kind) from the Windows volume calls."""
    import ctypes

    kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
    buffer = ctypes.create_unicode_buffer(1024)
    if not kernel32.GetVolumePathNameW(path, buffer, len(buffer)):
        raise ctypes.WinError()  # type: ignore[attr-defined]
    root = buffer.value
    label = ctypes.create_unicode_buffer(261)
    system = ctypes.create_unicode_buffer(261)
    if not kernel32.GetVolumeInformationW(
        root, label, len(label), None, None, None, system, len(system)
    ):
        raise ctypes.WinError()  # type: ignore[attr-defined]
    kind = DRIVE_KINDS.get(int(kernel32.GetDriveTypeW(root)), "drive")
    return root, label.value, system.value, kind


def probe_volume(path: Path) -> VolumeInfo:
    """Read the volume *path* is on. Raises ``OSError`` when it cannot.

    The path need not exist: the nearest existing folder above it is asked,
    so a file that has just been deleted still reports its drive.
    """
    target = Path(path)
    probe = target
    while not probe.exists() and probe.parent != probe:
        probe = probe.parent
    if not probe.exists():
        # Not even the drive or share is there: never let Windows guess a
        # different volume for a root it cannot see.
        raise FileNotFoundError(2, "The drive or share is not there", str(probe))
    if sys.platform == "win32":
        root, label, file_system, kind = _windows_details(str(probe))
    else:  # pragma: no cover - the family ships on Windows; kept honest elsewhere
        root, label, file_system, kind = (probe.anchor or os.sep), "", "", "drive"
    usage = shutil.disk_usage(root)
    return VolumeInfo(
        root=root,
        label=label,
        file_system=file_system,
        kind=kind,
        total=int(usage.total),
        used=int(usage.used),
        free=int(usage.free),
    )


def volume_problem(error: OSError, *, network: bool = False) -> str:
    """Why the drive could not be read, in words, with what to try.

    *network* is whether the path was a network one (it starts with two
    backslashes), which turns "not found" into "could not be reached".
    """
    winerror = getattr(error, "winerror", None)
    if isinstance(error, PermissionError) or winerror == 5:
        return "Windows did not allow this drive to be read. You may not have permission."
    if winerror in (53, 64, 67, 1222, 1231) or network:
        return "The network location could not be reached. Check the connection and try again."
    if winerror in (21, 2, 3, 15) or isinstance(error, FileNotFoundError):
        return (
            "The drive could not be found or is not ready. It may have been "
            "removed or disconnected."
        )
    return f"The drive could not be read ({error.strerror or error})."


def describe_volume(path: Path, *, probe: Callable[[Path], VolumeInfo] = probe_volume) -> list[str]:
    """Labelled lines about the drive *path* is on, for a properties box.

    Never raises: a drive that cannot be read is one line saying why.
    """
    try:
        info = probe(Path(path))
    except OSError as error:
        network = str(path).startswith(("\\\\", "//"))
        return [f"Drive: not available. {volume_problem(error, network=network)}"]
    name = info.root.rstrip("\\/") or info.root
    if len(name) == 2 and name[1] == ":":
        name += "\\"
    identity = f"{name} ({info.label})" if info.label else name
    extras = ", ".join(part for part in (info.kind, info.file_system) if part)
    lines = [f"Drive: {identity}" + (f", {extras}" if extras else "")]
    if info.total > 0:
        percent = round(info.used * 100 / info.total)
        lines.append(f"Drive capacity: {format_capacity(info.total)}")
        lines.append(f"Drive used: {format_capacity(info.used)}, {percent} percent")
        lines.append(f"Drive free: {format_capacity(info.free)}")
    else:
        lines.append("Drive capacity: not reported by this drive.")
    return lines
