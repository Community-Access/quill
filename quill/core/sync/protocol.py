"""Record-agnostic sync protocol (PRD 45).

The QuillSync framework is generic over an application's data: it never imports
a domain model. An application adapts its store to the :class:`RecordStore`
protocol -- three methods over opaque JSON-able record dicts -- and supplies a
:class:`MergeFn` that knows how to combine two versions of its own records.

This is the integration point every QUILL companion app (Beacon, Quill, Quill
Radio, Quill Cast) implements. The framework lives in this repo; each app's
adapter lives in its own repo (PRD 46.2).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass
class ManifestEntry:
    """One entity in a commit: either a tombstone or an encrypted blob ref."""

    entity_id: str
    entity_type: str  # e.g. "beacon", "settings", "station"
    tombstone: bool
    blob_hash: str
    wrapped_dek: str  # base64

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, d: dict) -> ManifestEntry:
        return cls(**d)


@dataclass
class Commit:
    """An immutable, encrypted snapshot of the entities that changed."""

    commit_id: str
    parent: str | None
    message: str
    created: int
    device: str
    entries: list[ManifestEntry] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "commit_id": self.commit_id,
            "parent": self.parent,
            "message": self.message,
            "created": self.created,
            "device": self.device,
            "entries": [e.to_dict() for e in self.entries],
        }

    @classmethod
    def from_dict(cls, d: dict) -> Commit:
        return cls(
            commit_id=d["commit_id"],
            parent=d.get("parent"),
            message=d.get("message", ""),
            created=d.get("created", 0),
            device=d.get("device", ""),
            entries=[ManifestEntry.from_dict(e) for e in d.get("entries", [])],
        )


@dataclass
class Conflict:
    """A two-version conflict for accessible review (PRD 23.5, 45.6).

    Generic over entity type; ``entity_id`` is the application's own id.
    """

    entity_id: str
    field: str
    local: str
    remote: str
    merged: str
    message: str


@runtime_checkable
class RecordStore(Protocol):
    """The contract an application store implements to be syncable.

    Records are opaque JSON-able dicts the framework never inspects (except to
    encrypt/decrypt). Returning ``None`` from ``get_record`` means the entity
    does not exist locally OR is in a deleted/trashed state that should sync
    as a tombstone (PRD 23.5).
    """

    def get_record(self, entity_id: str) -> dict | None: ...

    def put_record(self, entity_id: str, record: dict) -> None: ...

    def delete_record(self, entity_id: str) -> None: ...


#: Merge two versions of a record. ``local`` is None when the entity is new.
#: Returns the merged record plus a list of conflicts for accessible review.
MergeFn = Callable[[dict | None, dict], "tuple[dict, list[Conflict]]"]


def default_merge(local: dict | None, remote: dict) -> tuple[dict, list[Conflict]]:
    """Remote-wins merge with no conflicts. The simplest correct policy.

    Adapters that need field-level or three-way merge supply their own
    :data:`MergeFn`; this is the fallback so a bare store is immediately
    syncable.
    """
    return remote, []
