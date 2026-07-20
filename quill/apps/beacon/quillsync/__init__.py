"""QuillSync framework: a generic, record-agnostic sync core (PRD 45, 46).

This package is the shared sync layer for every QUILL companion app. It lives
in the QuillBeacon repo as the canonical home (PRD 46.1) but has no dependency
on Beacon's domain model -- it speaks only the :class:`~quillsync.protocol
.RecordStore` protocol and opaque JSON-able record dicts.

Companion apps integrate by writing an adapter in their own repo:

- ``BeaconRecordStore`` lives here (Beacon is the exception; it gets the full
  build in this repo, PRD 46.2).
- Quill, Quill Radio, and Quill Cast each write their own adapter against this
  protocol. Those adapters are planned, not built here (PRD 46.3).

Public API:
    from quill.apps.beacon.quillsync import SyncEngine, FolderTransport, ServerTransport
    from quill.apps.beacon.quillsync import RecordStore, MergeFn, Commit, Conflict, ManifestEntry
    from quill.apps.beacon.quillsync import derive_vault_key, union_lists, three_way_note
"""

from __future__ import annotations

from quill.apps.beacon.quillsync import crypto
from quill.apps.beacon.quillsync.engine import SyncEngine
from quill.apps.beacon.quillsync.merge import three_way_note, union_lists
from quill.apps.beacon.quillsync.protocol import (
    Commit,
    Conflict,
    ManifestEntry,
    MergeFn,
    RecordStore,
    default_merge,
)
from quill.apps.beacon.quillsync.transports import FolderTransport, ServerTransport, Transport

__version__ = "0.1.0"

__all__ = [
    "SyncEngine",
    "FolderTransport",
    "ServerTransport",
    "Transport",
    "RecordStore",
    "MergeFn",
    "Commit",
    "Conflict",
    "ManifestEntry",
    "default_merge",
    "union_lists",
    "three_way_note",
    "crypto",
    "derive_vault_key",
]

# Crypto is also re-exported at package level for convenience.
derive_vault_key = crypto.derive_vault_key
