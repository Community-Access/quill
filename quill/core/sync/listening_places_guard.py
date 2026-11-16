"""This device's Listening Places file is replaced only if it is still ours.

The folder is shared with other programs: a cloud client, a restore from a
backup, somebody copying the folder between machines, Earshot on a Mac. The
writer used to put its file down over whatever was at its path, and when the
write failed it returned the same ``False`` that means "nothing changed", so
the listener was never told their place had stopped travelling.

Earshot hardened its writer the same way in 1.2.5 (earshot.md E3): replace the
file only when it still holds what this device last wrote, leave anything else
untouched and say why, and say when a write fails. Both apps now behave the
same way in the same folder.

**What counts as still ours.** The file holds the rows this device last wrote
(the fingerprint beside it matches), or, when there is no fingerprint yet --
the first write after an update, or a marker that could not be saved -- it is a
``listening-places/1`` file naming this device. Anything else is somebody
else's file, and it is left exactly as it is.

wx-free, strict-typed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from quill.core.error_codes import CodedError

__all__ = ["ListeningPlacesWriteError", "problem_with_own_file", "rows_fingerprint"]


class ListeningPlacesWriteError(CodedError):
    """This device's Listening Places file was not written; the message says why."""

    code = "QUILL-SYNC-PLACES-NOT-WRITTEN"


def rows_fingerprint(rows: list[dict[str, object]]) -> str:
    """The hash the writer remembers: the rows only, never ``written_at``."""
    return hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def problem_with_own_file(
    target: Path, *, device_id: str, format_id: str, previous_fingerprint: str
) -> str:
    """Why *target* must not be replaced, or ``""`` when it is safe to write."""
    if not target.exists():
        return ""
    moved_away = (
        f"This computer's Listening Places file ({target.name}) changed in its "
        "folder since it was last written here, so it was left untouched. If "
        "that was not you, move the file out of the devices folder and a fresh "
        "one will be written."
    )
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return moved_away
    if not isinstance(data, dict) or str(data.get("format", "")) != format_id:
        return moved_away
    if str(data.get("device", "")) != device_id:
        return moved_away
    rows = data.get("records")
    if not isinstance(rows, list):
        return moved_away
    if previous_fingerprint and rows_fingerprint(rows) != previous_fingerprint:
        return moved_away
    return ""
