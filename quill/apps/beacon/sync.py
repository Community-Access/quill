"""Beacon adapter over the generic QuillSync framework (PRD 45, 46.2).

This module is the Beacon-specific integration point. It wraps a
:class:`~quill.apps.beacon.db.BeaconStore` as a :class:`~quillsync.protocol
.RecordStore` (opaque record dicts the framework encrypts without inspecting)
and supplies a Beacon :class:`~quillsync.protocol.MergeFn` that does
field-level union for tags/collections and three-way line merge for notes,
surfacing conflicts for accessible review (PRD 23.5, 45.6).

The generic engine, crypto, transports, and merge primitives live in the
:mod:`quillsync` package and are re-exported here so existing callers and
tests keep working: ``SyncEngine``, ``FolderTransport``, ``Commit``,
``Conflict``, ``ManifestEntry``.
"""

from __future__ import annotations

from pathlib import Path

from quill.apps.beacon import db as dbmod
from quill.apps.beacon import sync_crypto as crypto  # re-export surface
from quill.apps.beacon.model import Beacon, Location, Resource
from quill.apps.beacon.quillsync import (
    Commit,
    Conflict,
    FolderTransport,
    ManifestEntry,
)
from quill.apps.beacon.quillsync import (
    SyncEngine as _Engine,
)
from quill.apps.beacon.quillsync import merge as merge_mod

__all__ = [
    "SyncEngine",
    "FolderTransport",
    "Commit",
    "Conflict",
    "ManifestEntry",
    "BeaconRecordStore",
    "beacon_merge",
]


class BeaconRecordStore:
    """Adapt a :class:`BeaconStore` to the QuillSync :class:`RecordStore`.

    A record is the portable, JSON-able shape of one beacon: its row, its
    resource row, its locations, and its tag/collection names. Trashed beacons
    return ``None`` so the engine emits a tombstone (PRD 23.5).
    """

    def __init__(self, store: dbmod.BeaconStore) -> None:
        self.store = store

    def get_record(self, beacon_id: str) -> dict | None:
        b = self.store.get_beacon(beacon_id)
        if not b or b.trashed:
            return None
        res = self.store.get_resource(b.resource_id) if b.resource_id else None
        row = b.to_row()
        # ``dirty`` is a device-local "needs commit" flag; it must not leak to
        # other devices or every pull would make them re-commit (ping-pong).
        row["dirty"] = 0
        return {
            "beacon": row,
            "resource": res.to_row() if res else None,
            "locations": [loc.to_row() for loc in b.locations],
            "tags": b.tags,
            "collections": b.collections,
        }

    def put_record(self, beacon_id: str, record: dict) -> None:
        beacon = Beacon.from_row(record["beacon"])
        beacon.tags = record.get("tags", [])
        beacon.collections = record.get("collections", [])
        beacon.locations = [Location.from_row(r) for r in record.get("locations", [])]
        # Applied records are never "dirty" -- they came from elsewhere, so they
        # should not trigger a re-commit on the next sync.
        beacon.dirty = 0
        res = Resource.from_row(record["resource"]) if record.get("resource") else None
        if res is not None:
            self.store.put_resource(res)
            beacon.resource_id = beacon.resource_id or res.resource_id
        self.store.put_beacon(beacon, resource=None, touch=False)

    def delete_record(self, beacon_id: str) -> None:
        self.store.trash(beacon_id)


def beacon_merge(local: dict | None, remote: dict) -> tuple[dict, list[Conflict]]:
    """Beacon merge policy: union tags/collections, three-way note merge.

    Reproduces the field-level behavior the Beacon UI expects: tags and
    collections are a union (order-preserving, deduped); favorite is OR-ed;
    the remote title and resource win when non-empty; the note is merged
    line-by-line with conflicts surfaced for review, never inline markers the
    user must parse (PRD 23.5, 45.6).
    """
    remote_beacon = Beacon.from_row(remote["beacon"])
    remote_beacon.tags = remote.get("tags", [])
    remote_beacon.collections = remote.get("collections", [])
    remote_beacon.locations = [Location.from_row(r) for r in remote.get("locations", [])]

    if local is None:
        return remote, []

    local_beacon = Beacon.from_row(local["beacon"])
    local_beacon.tags = local.get("tags", [])
    local_beacon.collections = local.get("collections", [])

    merged = Beacon.from_row(local["beacon"])
    merged.tags = merge_mod.union_lists(local_beacon.tags, remote_beacon.tags)
    merged.collections = merge_mod.union_lists(local_beacon.collections, remote_beacon.collections)
    merged.favorite = bool(local_beacon.favorite or remote_beacon.favorite)
    merged.title = remote_beacon.title or local_beacon.title
    merged.resource_id = remote_beacon.resource_id or local_beacon.resource_id

    merged_note, conflict = merge_mod.three_way_note(
        local_beacon.note,
        remote_beacon.note,
        entity_id=merged.beacon_id,
        field="note",
    )
    merged.note = merged_note

    record = {
        "beacon": merged.to_row(),
        "resource": remote.get("resource") or local.get("resource"),
        # Keep the local locations on merge (matches prior behavior: the
        # existing beacon's locations are the source of truth locally).
        "locations": local.get("locations", []),
        "tags": merged.tags,
        "collections": merged.collections,
    }
    conflicts = [conflict] if conflict else []
    return record, conflicts


class SyncEngine(_Engine):
    """Beacon sync engine: a :class:`quillsync.SyncEngine` over BeaconStore.

    Accepts a :class:`BeaconStore` directly (the historical signature) and
    wires in the Beacon record adapter and merge policy.
    """

    def __init__(
        self, store: dbmod.BeaconStore, vault: crypto.VaultKey, *, device: str, data_dir: str | Path
    ) -> None:
        super().__init__(
            BeaconRecordStore(store),
            vault,
            device=device,
            data_dir=data_dir,
            merge_fn=beacon_merge,
            entity_type="beacon",
        )
        # ``self.store`` is the RecordStore adapter the base engine uses; keep
        # the raw BeaconStore handle for callers that want the domain store.
        self.beacon_store = store
