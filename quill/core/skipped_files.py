"""Why a file was left out, in words a listener can act on.

A backup, an export or a restore that touches many files used to end with a
count: "11 skipped". A count with no names is the sentence that makes somebody
about to reset their computer ask whether their favorites just went missing --
which is exactly the report that prompted this module (2026-10-04, a Quill
Radio listener whose recordings and backups live in OneDrive).

So every file left out carries a **name** and a **reason**, and the reasons are
a short fixed vocabulary, each one paired with what to do about it:

* **Stored only in OneDrive.** Windows' Files On-Demand leaves a placeholder on
  the disk: the name and size are there, the bytes are in the cloud. Reading
  the file asks Windows to download it, so a backup that *reads* rather than
  skipping is the cure -- this reason is for the case where that download did
  not happen (OneDrive not running, offline, or not enough free space).
* **In use by another program.** A sharing violation: OneDrive mid-upload, a
  player holding the file open.
* **Path too long.** Past Windows' classic 260-character limit.
* **Could not be read.** Anything else, with the system's own words kept for
  the log rather than read aloud.
* **Already there.** Deliberately left alone -- not a failure.

Pure and wx-free. The file-attribute check takes an injectable ``stat`` so the
tests can fake a cloud placeholder without a real OneDrive.
"""

from __future__ import annotations

import errno
import os
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CLOUD_ONLY_ATTRIBUTES",
    "REASON_ALREADY_THERE",
    "REASON_CLOUD_ONLY",
    "REASON_IN_USE",
    "REASON_NOT_ON_THIS_COMPUTER",
    "REASON_NO_SPACE_TO_DOWNLOAD",
    "REASON_TOO_LONG",
    "REASON_UNREADABLE",
    "SkippedFile",
    "classify_error",
    "is_cloud_only",
    "report_lines",
    "what_to_do",
]

#: FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN |
#: FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS: any of these on a file means its
#: bytes are not on this disk yet. ``os.stat`` reads attributes without
#: triggering the download, which is what makes asking safe.
FILE_ATTRIBUTE_OFFLINE = 0x1000
FILE_ATTRIBUTE_RECALL_ON_OPEN = 0x40000
FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS = 0x400000
CLOUD_ONLY_ATTRIBUTES = (
    FILE_ATTRIBUTE_OFFLINE | FILE_ATTRIBUTE_RECALL_ON_OPEN | FILE_ATTRIBUTE_RECALL_ON_DATA_ACCESS
)

REASON_CLOUD_ONLY = "stored only in OneDrive, not downloaded to this computer"
REASON_NO_SPACE_TO_DOWNLOAD = (
    "stored only in OneDrive, and there is not enough free space on this computer to download it"
)
REASON_IN_USE = "in use by another program"
REASON_TOO_LONG = "its folder path is too long for Windows"
REASON_UNREADABLE = "could not be read"
REASON_ALREADY_THERE = "already in your recordings folder"
REASON_NOT_ON_THIS_COMPUTER = "not on this computer yet, so there was nothing to carry"

#: What to do, keyed by reason. Said once under the list, not per row.
_ADVICE: dict[str, str] = {
    REASON_CLOUD_ONLY: (
        "Open File Explorer, right-click the folder that holds them, choose "
        "Always keep on this device, wait for OneDrive to finish, then try again."
    ),
    REASON_NO_SPACE_TO_DOWNLOAD: (
        "Free some space on this computer, or copy those files somewhere else "
        "yourself; they are still safe in OneDrive."
    ),
    REASON_IN_USE: (
        "Close the program using them, or wait for OneDrive to finish syncing, then try again."
    ),
    REASON_TOO_LONG: "Move or rename them into a folder with a shorter path, then try again.",
    REASON_UNREADABLE: "Check that the files open in another program, then try again.",
}

#: The Windows sharing / lock violations.
_IN_USE_WINERRORS = frozenset({32, 33})
#: ERROR_FILENAME_EXCED_RANGE.
_TOO_LONG_WINERRORS = frozenset({206})
#: The ERROR_CLOUD_FILE_* block (362 provider not running ... 397) plus
#: ERROR_CLOUD_FILE_UNSUCCESSFUL's neighbours. A range, because every one of
#: them means the same thing to a listener: OneDrive did not hand the file over.
_CLOUD_WINERRORS = frozenset(range(358, 400))
_CLASSIC_MAX_PATH = 260


@dataclass(frozen=True, slots=True)
class SkippedFile:
    """One file left out, and why."""

    name: str
    reason: str
    #: The system's own words, for the log; never read aloud.
    detail: str = ""

    def line(self) -> str:
        return f"{self.name}: {self.reason}"

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "reason": self.reason}


def _attributes(path: Path, stat: Callable[[Path], os.stat_result] | None) -> int:
    try:
        result = stat(path) if stat is not None else os.stat(path)
    except OSError:
        return 0
    return int(getattr(result, "st_file_attributes", 0) or 0)


def is_cloud_only(path: Path, *, stat: Callable[[Path], os.stat_result] | None = None) -> bool:
    """Whether *path* is a Files On-Demand placeholder whose bytes are in the cloud."""
    return bool(_attributes(path, stat) & CLOUD_ONLY_ATTRIBUTES)


def classify_error(
    error: OSError,
    path: Path,
    *,
    stat: Callable[[Path], os.stat_result] | None = None,
) -> str:
    """The plain reason a read of *path* failed with *error*."""
    winerror = int(getattr(error, "winerror", 0) or 0)
    if winerror in _CLOUD_WINERRORS:
        return REASON_CLOUD_ONLY
    if winerror in _IN_USE_WINERRORS:
        return REASON_IN_USE
    if (
        winerror in _TOO_LONG_WINERRORS
        or error.errno == errno.ENAMETOOLONG
        or len(str(path)) >= _CLASSIC_MAX_PATH
    ):
        return REASON_TOO_LONG
    if is_cloud_only(path, stat=stat):
        return REASON_CLOUD_ONLY
    return REASON_UNREADABLE


def what_to_do(skipped: Iterable[SkippedFile]) -> list[str]:
    """One sentence of advice per distinct reason, in a stable order."""
    seen: list[str] = []
    for item in skipped:
        advice = _ADVICE.get(item.reason)
        if advice and advice not in seen:
            seen.append(advice)
    return seen


def report_lines(skipped: Iterable[SkippedFile]) -> list[str]:
    """Every skipped file as ``name: reason``, grouped by reason."""
    rows = list(skipped)
    order: list[str] = []
    for item in rows:
        if item.reason not in order:
            order.append(item.reason)
    return [item.line() for reason in order for item in rows if item.reason == reason]
