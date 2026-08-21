"""One sync pass over the plain, shared Listening Places folder.

:mod:`quill.core.sync.places` carries positions between two copies of QUILL,
encrypted, over its own ``quillsync`` subfolder. This is the **interchange**
pass: the same folder, a published plain-JSON format, and a second app on the
other end.

Both can be on at once and they do not interfere -- they read and write
different subfolders of the folder the listener chose, and each keeps the same
local stores as its source of truth.

WHAT THIS PASS DOES, IN ORDER
-----------------------------
1. Read every device file that is not this device's own.
2. Take, per id, the record with the newest ``updated_at`` across all of them.
3. Apply the wins to the local stores -- Cast's episode positions, and the
   content-keyed positions for local files and books.
4. Rewrite this device's own file from the now-updated local state, and skip
   the write entirely when nothing changed.

**Reading happens only where it cannot interrupt anything** -- at startup and
on an explicit Sync Now. Never on a timer, never on a file-change notification,
and never on a playback path. The reason is what a pulled position does: if a
read lands mid-session and finds the desktop moved you to 52 minutes in the
episode you are listening to at 40, every available behaviour is bad. Moving
the playhead under somebody is unacceptable, and it is worse for a screen
reader user, who gets no visual cue that anything happened. Restricting reads
to the two moments when nothing is playing removes the whole problem rather
than managing it.

**Writing follows activity** and is the caller's business: this function is one
pass, and the caller decides when a pass happens.

wx-free, strict-typed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core.sync.listening_places import (
    Disagreement,
    PlaceRecord,
    merge_records,
    read_other_devices,
    remote_view,
    write_device_file,
)

__all__ = ["InterchangeReport", "sync_interchange"]

#: What goes in the ``app`` field of this device's file, so somebody reading
#: the folder can tell which app wrote what.
APP_NAME = "quill-cast"


@dataclass(slots=True)
class InterchangeReport:
    """What one pass did, in numbers and in one sentence."""

    applied: int = 0
    written: bool = False
    sent: int = 0
    disagreements: list[Disagreement] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)

    @property
    def changed(self) -> bool:
        return bool(self.applied or self.written)

    def summary(self) -> str:
        """One sentence, and it says nothing happened when nothing did.

        "Sync finished" after a sync that moved nothing is the message that
        teaches people to ignore the message.
        """
        if self.problems and not self.changed:
            return self.problems[0]
        if not self.changed:
            return "Everything was already up to date."
        parts: list[str] = []
        if self.applied:
            parts.append(f"brought back {self.applied} place{'' if self.applied == 1 else 's'}")
        if self.written:
            parts.append(f"shared {self.sent} place{'' if self.sent == 1 else 's'} from here")
        said = f"Sync {' and '.join(parts)}."
        if self.disagreements:
            count = len(self.disagreements)
            said += (
                f" {count} place{'' if count == 1 else 's'} disagreed between devices; "
                "the most recent was kept."
            )
        if self.problems:
            said += f" {self.problems[0]}"
        return said


def sync_interchange(
    *,
    data_dir: Path | str,
    remote_dir: Path | str,
    device_id: str,
    device_label: str,
    include_labels: bool = True,
    library: Any = None,
    save_library: Any = None,
) -> InterchangeReport:
    """Read every other device, apply what is newer, rewrite this device's file.

    *library* and *save_library* are injected so this stays testable without a
    data directory; left out, the shared podcast library is loaded and saved
    the way every other Cast caller does it.
    """
    report = InterchangeReport()
    root = Path(remote_dir)
    if not root.is_dir():
        # Checked first: a cloud folder that has been renamed, unshared, or is
        # simply not mounted yet would otherwise report "everything was already
        # up to date", which is the most misleading thing this could say.
        report.problems.append(
            "The sync folder is not there. Check that it still exists and that "
            "the drive or cloud folder holding it is available. Your place is "
            "still saved on this device."
        )
        return report

    from quill.core.podcasts import position_sync

    if library is None:
        try:
            from quill.core.podcasts.subscriptions import load_library

            library = load_library(Path(data_dir))
        except Exception as error:  # noqa: BLE001 - a sentence, never a traceback
            report.problems.append(f"The podcast library could not be read: {error}")
            return report

    try:
        others = read_other_devices(root, device_id)
    except Exception as error:  # noqa: BLE001
        report.problems.append(f"Could not read the sync folder: {error}")
        return report

    local = {record.id: record for record in position_sync.collect_records(library)}
    incoming = remote_view(others)
    merged, disagreements = merge_records(local, incoming)
    report.disagreements = disagreements

    applied = 0
    for entity_id, record in merged.items():
        if entity_id in local and local[entity_id].updated_at >= record.updated_at:
            continue
        if position_sync.apply_record(library, record):
            applied += 1
    report.applied = applied

    if applied:
        try:
            if save_library is not None:
                save_library(library)
            else:
                from quill.core.podcasts.subscriptions import save_library as _save

                _save(Path(data_dir), library)
        except Exception as error:  # noqa: BLE001
            report.problems.append(f"Those places could not be saved: {error}")

    outgoing = _outgoing_records(library, data_dir, include_labels=include_labels)
    report.sent = len(outgoing)
    try:
        report.written = write_device_file(
            root,
            device_id=device_id,
            device_label=device_label,
            app=_app_version(),
            records=outgoing,
            include_labels=include_labels,
        )
    except Exception as error:  # noqa: BLE001
        report.problems.append(f"Could not write to the sync folder: {error}")
    return report


def _outgoing_records(
    library: Any, data_dir: Path | str, *, include_labels: bool
) -> list[PlaceRecord]:
    """This device's whole view: podcast episodes, plus books and local files.

    Both, because the folder is one mailbox and the promise made to the listener
    is "my place follows me", not "my podcast place follows me". The two come
    from different local stores and land in one file under two id namespaces,
    which is exactly what the namespaces are for.
    """
    from quill.core.podcasts import position_sync

    records = position_sync.collect_records(library, include_labels=include_labels)
    records.extend(_file_records(data_dir, include_labels=include_labels))
    return records


def _file_records(data_dir: Path | str, *, include_labels: bool) -> list[PlaceRecord]:
    """The content-keyed positions -- audiobooks, imported audio -- as records."""
    try:
        from quill.core.media.positions import ListeningPosition, PositionStore

        store = PositionStore(Path(data_dir))
        rows: list[PlaceRecord] = []
        for entity_id in store.entity_ids():
            raw = store.get_record(entity_id)
            position = ListeningPosition.from_dict(raw) if raw is not None else None
            if position is None or not position.position_ms:
                continue
            rows.append(
                PlaceRecord(
                    id=f"file:{position.media_id}",
                    position_ms=position.position_ms,
                    duration_ms=position.duration_ms,
                    played=False,
                    updated_at=_as_z(position.updated_at),
                    label=position.label if include_labels else "",
                )
            )
        return rows
    except Exception:  # noqa: BLE001 - a store that will not read contributes nothing
        return []


def _as_z(stamp: str) -> str:
    """A local ISO timestamp as RFC 3339 UTC with a trailing ``Z``.

    The position store writes ``datetime.now(UTC).isoformat()``, which ends
    ``+00:00``. Plain string comparison is the merge rule, so the two spellings
    of the same instant must not be allowed to sort against each other.
    """
    from datetime import datetime

    try:
        parsed = datetime.fromisoformat(stamp)
    except (TypeError, ValueError):
        return stamp
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _app_version() -> str:
    try:
        from quill import __version__

        return f"{APP_NAME}/{__version__}"
    except Exception:  # noqa: BLE001
        return APP_NAME
