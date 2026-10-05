"""Bring an earlier copy's favorites into a new portable Quill Radio.

Quill Radio 2.x kept its data in this computer's profile (``%APPDATA%\\Quill``)
even when it ran from the portable zip. A 3.0 portable copy keeps everything in
its own ``data`` folder and writes nothing to the computer -- so somebody who
updates a 2.x portable copy would open 3.0 to an empty favorites tree, with
every station they saved still sitting one folder away.

This module answers two questions, both pure filesystem work with no wx:

* :func:`find_earlier_data` -- is there anything worth offering? Only when this
  run keeps its data in a portable bundle, the bundle has no favorites of its
  own yet, the profile has at least one, and the listener has not already
  answered.
* :func:`copy_earlier_data` -- copy the Radio files across. The profile is only
  ever *read*: the portable rule is about writing, and the earlier copy must be
  left exactly as it was. A file the bundle already has is never overwritten.

The answer, yes or no, is remembered in the bundle so the question is asked
once.
"""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from quill.core.radio.backup import RADIO_DATA_FILES
from quill.core.radio.favorites import load_favorites

__all__ = [
    "COPIED_FILES",
    "EarlierData",
    "copy_earlier_data",
    "find_earlier_data",
    "host_profile_dir",
    "remember_answer",
]

#: Everything a listener would call "my Radio setup": the backup's state files
#: plus reminders and download preferences.
COPIED_FILES: tuple[str, ...] = tuple(
    dict.fromkeys((*RADIO_DATA_FILES, "radio-reminders.json", "radio_downloads.json"))
)

_MARKER = "portable-migration.json"


@dataclass(frozen=True, slots=True)
class EarlierData:
    """What an earlier copy left in this computer's profile."""

    source: Path
    favorites: int


def host_profile_dir(environ: dict[str, str] | None = None) -> Path | None:
    """Where Quill Radio 2.x kept its data on this computer, if anywhere."""
    appdata = (environ if environ is not None else os.environ).get("APPDATA", "")
    if not appdata:
        return None
    folder = Path(appdata) / "Quill"
    return folder if folder.is_dir() else None


def _favorite_count(folder: Path) -> int:
    try:
        return len(load_favorites(folder).favorites)
    except (OSError, ValueError):
        return 0


def find_earlier_data(bundle_data: Path, profile: Path | None) -> EarlierData | None:
    """The earlier copy's data worth offering, or ``None``. Reads only."""
    if profile is None or (bundle_data / _MARKER).exists():
        return None
    try:
        if profile.resolve() == bundle_data.resolve():
            return None
    except OSError:
        return None
    if _favorite_count(bundle_data):
        return None  # this copy already has favorites of its own
    count = _favorite_count(profile)
    return EarlierData(source=profile, favorites=count) if count else None


def copy_earlier_data(earlier: EarlierData, bundle_data: Path) -> tuple[str, ...]:
    """Copy the Radio files the bundle does not have yet. Returns their names.

    Each file lands under a temporary name and is then renamed into place, so an
    interrupted copy never leaves half a favorites file behind.
    """
    bundle_data.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in COPIED_FILES:
        source = earlier.source / name
        target = bundle_data / name
        if not source.is_file() or (target.exists() and not _replaceable(target)):
            continue
        partial = target.with_name(target.name + ".copying")
        shutil.copyfile(source, partial)
        os.replace(partial, target)
        copied.append(name)
    return tuple(copied)


def _replaceable(target: Path) -> bool:
    """A favorites file with no favorites in it may be replaced.

    The offer is made *because* the bundle has no favorites, and a 3.0.0 bundle
    that had been opened once had a favorites file with none in it -- so
    "never overwrite what the bundle has" skipped the one file the listener
    said Yes to, and the answer was remembered as done (Jeff, C:\\qr,
    2026-09-28: "it prompted me to copy favorites over but it never did").
    Anything else the bundle has is still left alone.
    """
    if target.name != "radio_favorites.json":
        return False
    try:
        return not load_favorites(target.parent).favorites
    except Exception:  # noqa: BLE001 - an unreadable file is not something to keep
        return True


def remember_answer(bundle_data: Path, *, copied: bool) -> None:
    """Record the answer in the bundle, so the question is asked only once."""
    from quill.core.storage import write_json_atomic

    bundle_data.mkdir(parents=True, exist_ok=True)
    write_json_atomic(bundle_data / _MARKER, {"asked": True, "copied": copied})
