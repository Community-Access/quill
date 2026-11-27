"""Reading the other devices' Listening Places files, defensively.

Split from :mod:`quill.core.sync.listening_places` (GATE-11). The rules here are
the ones Cast and Earshot agreed to keep both sides robust (``ear.md`` C4 and
6.8): one sentence for every file that is skipped or corrected, a size cap, no
competition from a device silent for half a year, and no endless win for a
device whose clock is wrong.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from quill.core.sync.listening_places import DeviceFile, devices_dir, spoken_device

#: A device file larger than this is not parsed: 1,000 records are about 200 KB,
#: so ten times that is a damaged or foreign file, not a busy listener.
MAX_DEVICE_FILE_BYTES = 2 * 1024 * 1024

#: A device not heard from for this long no longer competes in the merge: its
#: old places would otherwise win against nothing for ever (ear.md 6.8, item 8).
STALE_DEVICE_DAYS = 180

#: A record stamped further ahead of this computer's clock than this comes from
#: a device whose clock is wrong (ear.md 6.8, item 1).
CLOCK_SKEW_LIMIT_HOURS = 24


def read_other_devices(
    remote_dir: Path | str,
    device_id: str,
    *,
    problems: list[str] | None = None,
    now: datetime | None = None,
) -> list[DeviceFile]:
    """Every device file except this device's own. Never raises.

    A folder that is not there, a file half-written by a cloud client, a file
    from a newer format: all of them are "nothing to read from that one", never
    an error. One unreadable file must not cost the rest.

    Each file that is skipped or corrected adds one sentence to *problems*, when
    given, so the sync report can say what happened instead of skipping in
    silence (``ear.md`` C4):

    - too large to be a device file (:data:`MAX_DEVICE_FILE_BYTES`);
    - not there yet (a cloud placeholder), or unreadable;
    - not ``listening-places/1``;
    - from a device silent for :data:`STALE_DEVICE_DAYS` days, which is ignored;
    - holding places stamped more than :data:`CLOCK_SKEW_LIMIT_HOURS` hours
      ahead of this computer: their time is taken as the file's own
      ``written_at`` (or now, if that is also ahead), so a fast clock cannot
      win every comparison until real time catches up.
    """
    said = problems if problems is not None else []
    folder = devices_dir(remote_dir)
    if not folder.is_dir():
        return []
    found: list[DeviceFile] = []
    try:
        entries = sorted(folder.glob("*.json"))
    except OSError:
        return []
    moment = now or datetime.now(UTC)
    now_text = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
    stale_before = _shift(moment, days=-STALE_DEVICE_DAYS)
    ahead_limit = _shift(moment, hours=CLOCK_SKEW_LIMIT_HOURS)
    for entry in entries:
        if entry.stem == device_id:
            continue
        try:
            if entry.stat().st_size > MAX_DEVICE_FILE_BYTES:
                said.append(f"{entry.name} in the sync folder is too large to be a place list.")
                continue
            data = json.loads(entry.read_text(encoding="utf-8"))
        except OSError:
            said.append(f"{entry.name} could not be read yet; it will be tried again next time.")
            continue
        except ValueError:
            said.append(f"{entry.name} is not a complete place list; it will be tried again.")
            continue
        parsed = DeviceFile.from_dict(data)
        if parsed is None:
            said.append(f"{entry.name} is not a Listening Places file this version can read.")
            continue
        name = spoken_device(parsed)
        if parsed.written_at and parsed.written_at < stale_before:
            said.append(
                f"{name} has not synced for over {STALE_DEVICE_DAYS} days, "
                "so its places were not used."
            )
            continue
        written = parsed.written_at
        fallback = written if written and written <= ahead_limit else now_text
        skewed = sum(1 for record in parsed.records if record.updated_at > ahead_limit)
        if skewed:
            from dataclasses import replace

            parsed.records = [
                replace(record, updated_at=fallback) if record.updated_at > ahead_limit else record
                for record in parsed.records
            ]
        if skewed:
            said.append(
                f"{name}'s clock looks wrong: {skewed} of its places were dated in the future, "
                "so they were treated as written when it last synced."
            )
        found.append(parsed)
    return found


def _shift(moment: datetime, *, days: int = 0, hours: int = 0) -> str:
    from datetime import timedelta

    return (moment + timedelta(days=days, hours=hours)).strftime("%Y-%m-%dT%H:%M:%SZ")
