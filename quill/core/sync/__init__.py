"""QuillSync framework: a generic, record-agnostic sync core (PRD 45, 46).

This package is the shared sync layer for every QUILL companion app. It has no
dependency on any app's domain model -- it speaks only the
:class:`~quill.core.sync.protocol.RecordStore` protocol and opaque JSON-able
record dicts.

**Moved here from ``quill/apps/beacon/quillsync/`` on 2026-08-13**, before the
second adopter rather than after the fourth. A framework three other products
are meant to build on cannot live inside one of them: it made every future
adapter import from an app package, and ``core/media/positions.py`` was already
reaching up into ``apps/`` for a ``Conflict`` type, which is the layering smell
that the move removes. Its new home also puts it permanently in ``mypy``'s
strict scope, where a shared framework belongs.

Companion apps integrate by writing an adapter:

- ``BeaconRecordStore`` (``quill/apps/beacon/sync.py``) was the first, and is
  still the only complete one (PRD 46.2).
- Quill, Quill Radio, and Quill Cast each write their own against this
  protocol. ``core/media/positions.PositionStore`` already satisfies it, and
  ``merge_positions`` already satisfies ``MergeFn`` -- what is missing is the
  transport wiring, not the records (PRD 46.3).

Public API:
    from quill.core.sync import SyncEngine, FolderTransport, ServerTransport
    from quill.core.sync import RecordStore, MergeFn, Commit, Conflict, ManifestEntry
    from quill.core.sync import derive_vault_key, union_lists, three_way_note
"""

from __future__ import annotations

from quill.core.sync import crypto
from quill.core.sync.engine import SyncEngine
from quill.core.sync.merge import three_way_note, union_lists
from quill.core.sync.protocol import (
    Commit,
    Conflict,
    ManifestEntry,
    MergeFn,
    RecordStore,
    default_merge,
)
from quill.core.sync.transports import FolderTransport, ServerTransport, Transport

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
