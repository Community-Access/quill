"""Listening Places: your place, in a plain file another app can read.

The interchange half of "carry my place between machines". :mod:`places` already
carries positions between two copies of QUILL, encrypted, over a folder. This
module carries them between **different apps** -- QUILL Cast on the desktop and
Earshot on iOS -- over the same kind of folder, in a published format neither
app owns.

Spec: ``listening-places/1``. The proposal it implements is
``S:\\code\\earshot\\sync.md``; the sections cited below are its sections.

FOUR PROPERTIES, AND EACH ONE RULES OUT A FAILURE
-------------------------------------------------
**No account, no server, no signup.** The user picks a folder they already sync
-- Dropbox, OneDrive, Google Drive, iCloud Drive, Nextcloud, Syncthing, a
network share, a stick. QUILL runs nothing and holds nobody's listening
history.

**One writer per file** (6.1). Each device writes exactly one file and reads
everyone else's. Cloud drives resolve simultaneous edits to one file by leaving
``positions (Jeff's conflicted copy).json`` lying around, which is the single
worst failure mode on offer. If no two devices ever write the same file, that
failure cannot happen -- and the design scales past two devices for free.

**Last write wins, not furthest position** (6.4). If you deliberately jumped
back twenty minutes to re-hear something and then opened the episode on the
laptop, the furthest position is exactly the wrong answer.

**Identity from content, never from a path** (6.3). ``D:\\Audio\\book.mp3`` and
an iOS container path are the same audiobook and will never agree on a key. An
episode is keyed on its RSS GUID, which is stable across the FeedBurner
redirect one app subscribed through and the final host the other did; a file is
keyed on its size and the digest of its two ends.

WHAT THIS DELIBERATELY IS NOT
-----------------------------
**Not encrypted** -- this is tier A (6.6). Everything readable in the folder is
hashed: a third party with access learns how many things are listened to,
roughly how long each is and when, and nothing about *what* unless the optional
label is left on. Tier B, the encrypted vault with the eight-word recovery
phrase, already exists in :mod:`quill.core.sync.crypto` and is a separate
switch. The strong recommendation in the proposal is to ship tier A first and
never gate the feature on tier B, because a feature nobody can set up syncs
nothing.

**Not real-time.** Propagation takes as long as the cloud client takes. The
promise is that your place is right when you pick up the other device.

**Not subscriptions.** Positions and played state only. Subscriptions cannot be
hashed -- the whole point of a feed record is a URL the other app can fetch --
so they carry a different exposure, belong behind their own switch, and are
phase 3 (6.7).

wx-free, strict-typed, no network. Nothing here is ever called on a playback
path.
"""

from __future__ import annotations

import hashlib
import json
import re
import secrets
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

__all__ = [
    "FOLDER_NAME",
    "FORMAT_ID",
    "DeviceFile",
    "PlaceRecord",
    "episode_id",
    "file_id",
    "merge_records",
    "new_device_id",
    "read_other_devices",
    "stream_id",
    "write_device_file",
]

#: The format string every file carries. Stable whatever either app calls the
#: feature in its own menus.
FORMAT_ID = "listening-places/1"

#: The subfolder created inside whatever folder the user chose.
FOLDER_NAME = "Listening Places"

#: One paragraph, so somebody who stumbles on this in Dropbox six months later
#: is not mystified (6.1).
README_TEXT = """\
Listening Places
================

This folder is how your audio apps remember where you got to, across your
devices, without an account and without anybody's server.

Each device writes exactly one file in "devices" and reads the others. Nothing
here is audio -- these are only positions, a few hundred kilobytes at most. The
ids are hashed, so this folder does not list what you listen to in readable
form.

You can delete this folder at any time. Nothing breaks: every app still knows
your place on the device you are using. It just stops being shared.

Format: listening-places/1
"""

#: How far apart two positions must be before the difference is worth
#: mentioning (6.4). Below five minutes it is the same place, and saying so
#: teaches people to ignore the message.
CONFLICT_GAP_MS = 5 * 60 * 1000

#: A device file is capped so it cannot grow without bound; the oldest fall off
#: (6.1). One thousand records is roughly 250 KB of JSON.
MAX_RECORDS = 1000

#: How much of each end of a local file feeds its identity digest.
_SAMPLE_BYTES = 64 * 1024

_DEVICE_ID_RE = re.compile(r"^[0-9a-f]{8}$")


def _now() -> str:
    """RFC 3339 UTC with a trailing Z, so plain string comparison sorts (6.2)."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def new_device_id() -> str:
    """A random id for this device, generated once at setup.

    Random rather than the device's name, so a shared Dropbox folder's listing
    does not announce "Jeff's iPhone" to everybody who can see it (6.1).
    """
    return secrets.token_hex(4)


# -- identity (6.3) ----------------------------------------------------------


def _short(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def episode_id(guid: str, audio_url: str = "") -> str:
    """``episode:<hash>`` for anything from a feed.

    Keyed on the GUID **alone**, not on feed URL plus GUID. Two apps disagree
    about a feed's URL far more often than one expects -- one subscribed through
    a FeedBurner redirect and the other through the final host, one has http and
    the other https, one carries a tracking prefix. GUIDs are required to be
    unique by the RSS spec and survive all of that. The enclosure URL is the
    fallback for the feeds that publish no GUID at all.

    The hash is not for security. It is so a plain-text file in a shared folder
    does not list every podcast somebody follows in readable form, and so ids
    are fixed-length and filename-safe.
    """
    key = (guid or "").strip() or (audio_url or "").strip()
    return f"episode:{_short(key)}" if key else ""


def file_id(path: Path) -> str:
    """``file:<size>-<digest>`` for local audio -- the same key on every platform.

    Delegates to :func:`quill.core.media.positions.media_identity`, which is
    already in production and is what makes the cloud-file case work: the same
    MP3 in ``Dropbox/Audiobooks`` produces the same id on iOS and on Windows,
    wherever each platform mounts it and whatever either called the file.
    """
    from quill.core.media.positions import media_identity

    identity = media_identity(path)
    return f"file:{identity}" if identity else ""


def stream_id(stream_url: str) -> str:
    """``stream:<hash>`` -- reserved for Quill Radio's recordings.

    Listed so the namespace cannot be claimed for something else later. An app
    that does not understand a namespace ignores those records rather than
    choking on them, which is what lets the format grow.
    """
    key = (stream_url or "").strip().lower()
    return f"stream:{_short(key)}" if key else ""


# -- the record (6.2) --------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlaceRecord:
    """One place: what it is, where you got to, and when that was decided."""

    id: str
    position_ms: int = 0
    duration_ms: int = 0
    played: bool = False
    updated_at: str = ""
    #: Human-readable only, never part of the identity. It exists so a conflict
    #: can say "you and your phone disagree about Episode 214" rather than
    #: reading out a hash -- and it is the one field that leaks, so a
    #: privacy-minded listener can turn it off.
    label: str = ""
    #: Carried for disambiguation and debugging. Not part of the key.
    feed: str = ""
    #: A tombstone: "I removed this", as distinct from "I have never heard of
    #: this". It carries no other fields.
    deleted: bool = False

    @property
    def kind(self) -> str:
        return self.id.split(":", 1)[0] if ":" in self.id else ""

    def to_dict(self, *, include_label: bool = True) -> dict[str, object]:
        if self.deleted:
            return {"id": self.id, "deleted": True, "updated_at": self.updated_at}
        row: dict[str, object] = {
            "id": self.id,
            "kind": self.kind,
            "position_ms": int(self.position_ms),
            "duration_ms": int(self.duration_ms),
            "played": bool(self.played),
            "updated_at": self.updated_at,
        }
        if include_label and self.label:
            row["label"] = self.label
        if self.feed:
            row["feed"] = self.feed
        return row

    @classmethod
    def from_dict(cls, data: object) -> PlaceRecord | None:
        if not isinstance(data, dict):
            return None
        entity_id = str(data.get("id", "")).strip()
        if not entity_id or ":" not in entity_id:
            return None
        return cls(
            id=entity_id,
            position_ms=max(0, _as_int(data.get("position_ms"))),
            duration_ms=max(0, _as_int(data.get("duration_ms"))),
            played=bool(data.get("played", False)),
            updated_at=str(data.get("updated_at", "")),
            label=str(data.get("label", "")),
            feed=str(data.get("feed", "")),
            deleted=bool(data.get("deleted", False)),
        )


def _as_int(value: object) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, (float, str)):
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return 0
    return 0


@dataclass(slots=True)
class DeviceFile:
    """One device's file: who wrote it, when, and what it knows."""

    device: str
    device_label: str = ""
    app: str = ""
    written_at: str = ""
    records: list[PlaceRecord] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: object) -> DeviceFile | None:
        if not isinstance(data, dict):
            return None
        if str(data.get("format", "")) != FORMAT_ID:
            # A file from a later version of the format. Ignored rather than
            # guessed at: a half-understood record is worse than none.
            return None
        raw = data.get("records")
        rows = [PlaceRecord.from_dict(row) for row in raw] if isinstance(raw, list) else []
        return cls(
            device=str(data.get("device", "")),
            device_label=str(data.get("device_label", "")),
            app=str(data.get("app", "")),
            written_at=str(data.get("written_at", "")),
            records=[row for row in rows if row is not None],
        )


# -- the folder (6.1) --------------------------------------------------------


def places_dir(remote_dir: Path | str) -> Path:
    return Path(remote_dir) / FOLDER_NAME


def devices_dir(remote_dir: Path | str) -> Path:
    return places_dir(remote_dir) / "devices"


def device_file_path(remote_dir: Path | str, device_id: str) -> Path:
    return devices_dir(remote_dir) / f"{device_id}.json"


def write_device_file(
    remote_dir: Path | str,
    *,
    device_id: str,
    device_label: str,
    app: str,
    records: list[PlaceRecord],
    include_labels: bool = True,
    now: str = "",
) -> bool:
    """Write this device's file. Returns whether anything was actually written.

    **Skips the write when the content has not changed** (6.4). Without that
    check, a machine left open all day re-uploads an identical file to
    somebody's cloud folder over and over, which costs bandwidth, drains a
    battery, burns a metered connection, and makes the folder's modification
    times useless to anybody trying to see what happened.

    The check hashes the records rather than the whole file, because
    ``written_at`` changes on every call by definition and would defeat it.
    """
    kept = sorted(records, key=lambda row: row.updated_at, reverse=True)[:MAX_RECORDS]
    rows = [row.to_dict(include_label=include_labels) for row in kept]
    fingerprint = hashlib.sha256(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    target = device_file_path(remote_dir, device_id)
    if _previous_fingerprint(target) == fingerprint:
        return False

    payload = {
        "format": FORMAT_ID,
        "device": device_id,
        "device_label": device_label,
        "app": app,
        "written_at": now or _now(),
        "records": rows,
    }
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        _ensure_readme(remote_dir)
        from quill.core.storage import write_json_atomic

        write_json_atomic(target, payload)
        _remember_fingerprint(target, fingerprint)
    except OSError:
        return False
    return True


def _fingerprint_path(target: Path) -> Path:
    return target.with_suffix(".fingerprint")


def _previous_fingerprint(target: Path) -> str:
    try:
        return _fingerprint_path(target).read_text(encoding="utf-8").strip()
    except OSError:
        return ""


def _remember_fingerprint(target: Path, fingerprint: str) -> None:
    try:
        _fingerprint_path(target).write_text(fingerprint, encoding="utf-8")
    except OSError:
        # An unwritable marker means writing every time: wasteful, correct, and
        # never a reason to refuse to sync.
        return


def _ensure_readme(remote_dir: Path | str) -> None:
    readme = places_dir(remote_dir) / "README.txt"
    if readme.exists():
        return
    try:
        readme.parent.mkdir(parents=True, exist_ok=True)
        readme.write_text(README_TEXT, encoding="utf-8")
    except OSError:
        return


def read_other_devices(remote_dir: Path | str, device_id: str) -> list[DeviceFile]:
    """Every device file except this device's own. Never raises.

    A folder that is not there, a file half-written by a cloud client, a file
    from a newer format: all of them are "nothing to read from that one", never
    an error. One unreadable file must not cost the rest.
    """
    folder = devices_dir(remote_dir)
    if not folder.is_dir():
        return []
    found: list[DeviceFile] = []
    try:
        entries = sorted(folder.glob("*.json"))
    except OSError:
        return []
    for entry in entries:
        if entry.stem == device_id:
            continue
        try:
            data = json.loads(entry.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        parsed = DeviceFile.from_dict(data)
        if parsed is not None:
            found.append(parsed)
    return found


# -- merging (6.4, 6.5) ------------------------------------------------------


def remote_view(files: list[DeviceFile]) -> dict[str, PlaceRecord]:
    """For each id, the record with the greatest ``updated_at`` across devices."""
    best: dict[str, PlaceRecord] = {}
    for device_file in files:
        for record in device_file.records:
            current = best.get(record.id)
            if current is None or record.updated_at > current.updated_at:
                best[record.id] = record
    return best


@dataclass(frozen=True, slots=True)
class Disagreement:
    """Two devices that remembered genuinely different places."""

    id: str
    label: str
    local_ms: int
    remote_ms: int
    kept_ms: int

    def spoken(self) -> str:
        from quill.core.media.timecode import format_spoken

        return (
            f"Two devices remembered different places in {self.label or 'this recording'}. "
            f"This device had {format_spoken(self.local_ms)}. "
            f"The other had {format_spoken(self.remote_ms)}. "
            "The most recent one was kept."
        )


def merge_records(
    local: dict[str, PlaceRecord], remote: dict[str, PlaceRecord]
) -> tuple[dict[str, PlaceRecord], list[Disagreement]]:
    """Apply the remote view to the local one. Last write wins on ``updated_at``.

    Ties and missing timestamps resolve to the remote, which keeps behaviour
    predictable when data is incomplete. A disagreement is reported only when
    the two positions are at least :data:`CONFLICT_GAP_MS` apart: reopening an
    episode on a second device and finding the position eight seconds off is
    not news.
    """
    merged = dict(local)
    disagreements: list[Disagreement] = []
    for entity_id, incoming in remote.items():
        current = merged.get(entity_id)
        if current is None:
            merged[entity_id] = incoming
            continue
        if current.updated_at > incoming.updated_at:
            continue
        if abs(current.position_ms - incoming.position_ms) >= CONFLICT_GAP_MS:
            disagreements.append(
                Disagreement(
                    id=entity_id,
                    label=current.label or incoming.label,
                    local_ms=current.position_ms,
                    remote_ms=incoming.position_ms,
                    kept_ms=incoming.position_ms,
                )
            )
        merged[entity_id] = incoming
    return merged, disagreements


def guard_clock_skew(record: PlaceRecord, seen_at: str) -> PlaceRecord:
    """Never write a timestamp older than the newest already seen for this id (6.5).

    Two devices whose clocks are a few minutes apart make bad merge decisions.
    Full vector clocks are overkill for a listening position; this one cheap
    guard fixes the case people actually notice, which is a device with a slow
    clock repeatedly losing to its own stale data. Documented as a bounded
    limitation rather than solved: positions are not money.
    """
    if not seen_at or record.updated_at > seen_at:
        return record
    return PlaceRecord(
        id=record.id,
        position_ms=record.position_ms,
        duration_ms=record.duration_ms,
        played=record.played,
        updated_at=_bump(seen_at),
        label=record.label,
        feed=record.feed,
        deleted=record.deleted,
    )


def _bump(stamp: str) -> str:
    """*stamp* plus one second, keeping the RFC 3339 UTC shape."""
    try:
        parsed = datetime.strptime(stamp, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=UTC)
    except ValueError:
        return _now()
    return datetime.fromtimestamp(parsed.timestamp() + 1, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_device_id(value: str) -> bool:
    return bool(_DEVICE_ID_RE.match(value or ""))
