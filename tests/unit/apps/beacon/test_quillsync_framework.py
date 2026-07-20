"""Framework-level tests for the generic quillsync core (PRD 45, 46).

These prove the engine is record-agnostic -- it syncs a non-Beacon store
(a trivial settings store) with no domain coupling -- and that
``ServerTransport`` adapts the reference server's bulk push/pull contract to
the per-item ``Transport`` interface. This is the contract Quill, Quill Radio,
and Quill Cast adapters will implement in their own repos.
"""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon.quillsync import (
    FolderTransport,
    ServerTransport,
    SyncEngine,
    derive_vault_key,
)
from quill.apps.beacon.quillsync.merge import union_lists


class _SettingsStore:
    """A minimal non-Beacon RecordStore: opaque dict records keyed by id."""

    def __init__(self) -> None:
        self.data: dict[str, dict] = {}

    def get_record(self, entity_id: str) -> dict | None:
        return self.data.get(entity_id)

    def put_record(self, entity_id: str, record: dict) -> None:
        self.data[entity_id] = record

    def delete_record(self, entity_id: str) -> None:
        self.data.pop(entity_id, None)


def _settings_merge(local, remote):
    """Remote-wins with list-union for the 'recent' list."""
    if local is None:
        return remote, []
    merged = dict(remote)
    merged["recent"] = union_lists(local.get("recent", []), remote.get("recent", []))
    return merged, []


class GenericEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = derive_vault_key("shared")
        self.s1, self.s2 = _SettingsStore(), _SettingsStore()
        self.e1 = SyncEngine(
            self.s1,
            self.vault,
            device="d1",
            data_dir=Path(self.tmp) / "d1",
            merge_fn=_settings_merge,
            entity_type="settings",
        )
        self.e2 = SyncEngine(
            self.s2,
            self.vault,
            device="d2",
            data_dir=Path(self.tmp) / "d2",
            merge_fn=_settings_merge,
            entity_type="settings",
        )
        self.transport = FolderTransport(Path(self.tmp) / "remote")

    def test_generic_push_pull(self):
        self.s1.put_record("voice", {"voice": "kokoro", "recent": ["a"]})
        self.e1.commit("set voice", ["voice"])
        self.e1.push(self.transport)
        applied, conflicts = self.e2.pull(self.transport)
        self.assertEqual(applied, 1)
        self.assertEqual(conflicts, [])
        self.assertEqual(self.s2.get_record("voice")["voice"], "kokoro")

    def test_generic_tombstone(self):
        self.s1.put_record("voice", {"voice": "kokoro"})
        self.e1.commit("set", ["voice"])
        self.e1.push(self.transport)
        self.e2.pull(self.transport)
        self.s1.delete_record("voice")
        self.e1.commit("remove voice", ["voice"])
        self.e1.push(self.transport)
        self.e2.pull(self.transport)
        self.assertIsNone(self.s2.get_record("voice"))

    def test_generic_list_union_merge(self):
        self.s1.put_record("voice", {"voice": "kokoro", "recent": ["a"]})
        self.e1.commit("set", ["voice"])
        self.e1.push(self.transport)
        self.e2.pull(self.transport)
        self.s1.put_record("voice", {"voice": "kokoro", "recent": ["a", "b"]})
        self.e1.commit("add b", ["voice"])
        self.s2.put_record("voice", {"voice": "kokoro", "recent": ["a", "c"]})
        self.e2.commit("add c", ["voice"])
        self.e2.push(self.transport)
        self.e1.pull(self.transport)
        self.assertEqual(set(self.s1.get_record("voice")["recent"]), {"a", "b", "c"})


class _FakeServerClient:
    """Mimics quill.apps.beacon.server_client.ServerClient's push/pull shape over an in-memory
    store, so ServerTransport is tested without network or the requests dep."""

    def __init__(self) -> None:
        self.commits: dict[str, dict] = {}
        self.objects: dict[str, bytes] = {}

    def push(self, commits, objects):
        for h, b in (objects or {}).items():
            self.objects.setdefault(h, b)
        new = 0
        for c in commits:
            if c["commit_id"] not in self.commits:
                self.commits[c["commit_id"]] = c
                new += 1
        return {"ok": True, "new_commits": new}

    def pull(self, have):
        commits = [c for cid, c in self.commits.items() if cid not in set(have)]
        objects = {}
        for c in commits:
            for e in c.get("entries", []):
                if e.get("tombstone"):
                    continue
                h = e.get("blob_hash")
                if h and h not in objects and h in self.objects:
                    objects[h] = self.objects[h]
        return {"commits": commits, "objects": objects}

    def hints(self):
        return {"new": len(self.commits)}


class ServerTransportTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.vault = derive_vault_key("shared")
        self.s1, self.s2 = _SettingsStore(), _SettingsStore()
        self.c1 = _FakeServerClient()
        self.e1 = SyncEngine(
            self.s1,
            self.vault,
            device="d1",
            data_dir=Path(self.tmp) / "d1",
            merge_fn=_settings_merge,
            entity_type="settings",
        )
        self.e2 = SyncEngine(
            self.s2,
            self.vault,
            device="d2",
            data_dir=Path(self.tmp) / "d2",
            merge_fn=_settings_merge,
            entity_type="settings",
        )

    def test_server_transport_roundtrip(self):
        self.s1.put_record("voice", {"voice": "kokoro"})
        self.e1.commit("set", ["voice"])
        t1 = ServerTransport(self.c1)
        self.assertEqual(self.e1.push(t1), 1)
        # dev2 pulls via a second transport over the same fake server
        t2 = ServerTransport(self.c1)
        applied, conflicts = self.e2.pull(t2)
        self.assertEqual(applied, 1)
        self.assertEqual(conflicts, [])
        self.assertEqual(self.s2.get_record("voice")["voice"], "kokoro")


if __name__ == "__main__":
    unittest.main()
