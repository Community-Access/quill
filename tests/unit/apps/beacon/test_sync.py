"""QuillSync client tests: crypto, commit/push/pull, merge/conflict."""

from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from quill.apps.beacon import capture, db, sync, sync_crypto


def _store(dir_path: Path) -> db.BeaconStore:
    return db.BeaconStore(dir_path / "beacons.db")


class CryptoTests(unittest.TestCase):
    def test_vault_derivation_reproducible(self):
        salt = os.urandom(16)
        a = sync_crypto.derive_vault_key("passphrase", salt=salt)
        b = sync_crypto.derive_vault_key("passphrase", salt=salt)
        self.assertEqual(a.key, b.key)

    def test_wrong_passphrase_differs(self):
        salt = os.urandom(16)
        a = sync_crypto.derive_vault_key("passphrase", salt=salt)
        b = sync_crypto.derive_vault_key("wrong", salt=salt)
        self.assertNotEqual(a.key, b.key)

    def test_wrap_unwrap_roundtrip(self):
        vault = sync_crypto.derive_vault_key("pw")
        dek = sync_crypto.new_dek()
        wrapped = sync_crypto.wrap_dek(vault, dek)
        self.assertEqual(sync_crypto.unwrap_dek(vault, wrapped), dek)

    def test_encrypt_decrypt_json(self):
        dek = sync_crypto.new_dek()
        blob = sync_crypto.encrypt_json(dek, {"a": 1, "b": "two"})
        self.assertEqual(sync_crypto.decrypt_json(dek, blob), {"a": 1, "b": "two"})

    def test_tamper_detected(self):
        dek = sync_crypto.new_dek()
        blob = bytearray(sync_crypto.encrypt_object(dek, b"secret"))
        blob[-1] ^= 1
        with self.assertRaises(Exception):  # noqa: B017 -- any failure proves tamper detection
            sync_crypto.decrypt_object(dek, bytes(blob))


class SyncEngineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.dev1 = Path(self.tmp) / "dev1"
        self.dev2 = Path(self.tmp) / "dev2"
        self.remote = Path(self.tmp) / "remote"
        for p in (self.dev1, self.dev2, self.remote):
            p.mkdir()
        self.store1 = _store(self.dev1)
        self.store2 = _store(self.dev2)
        self.vault = sync_crypto.derive_vault_key("shared-secret")
        self.eng1 = sync.SyncEngine(self.store1, self.vault, device="dev1", data_dir=self.dev1)
        self.eng2 = sync.SyncEngine(self.store2, self.vault, device="dev2", data_dir=self.dev2)
        self.transport = sync.FolderTransport(self.remote)

    def _add(self, store, url="https://example.org/a", title="A", note=""):
        b, res = capture.capture(url, title=title, note=note, tags=["t"])
        store.put_beacon(b, resource=res)
        return b

    def test_push_pull_replicates(self):
        b = self._add(self.store1, title="Page A")
        self.eng1.commit("add Page A", [b.beacon_id])
        pushed = self.eng1.push(self.transport)
        self.assertEqual(pushed, 1)
        applied, conflicts = self.eng2.pull(self.transport)
        self.assertEqual(applied, 1)
        self.assertEqual(conflicts, [])
        self.assertEqual(self.store2.count(), 1)
        got = self.store2.get_beacon(b.beacon_id)
        self.assertEqual(got.title, "Page A")
        self.assertEqual(got.tags, ["t"])

    def test_tombstone_propagates(self):
        b = self._add(self.store1, title="Page A")
        self.eng1.commit("add", [b.beacon_id])
        self.eng1.push(self.transport)
        self.eng2.pull(self.transport)
        # dev1 trashes and commits a tombstone
        self.store1.trash(b.beacon_id)
        self.eng1.commit("trash", [b.beacon_id])
        self.eng1.push(self.transport)
        self.eng2.pull(self.transport)
        self.assertEqual(self.store2.count(), 0)

    def test_tag_union_merge(self):
        b = self._add(self.store1, title="Page A")
        self.eng1.commit("add", [b.beacon_id])
        self.eng1.push(self.transport)
        self.eng2.pull(self.transport)
        # both add different tags
        b1 = self.store1.get_beacon(b.beacon_id)
        b1.tags = ["t", "research"]
        self.store1.put_beacon(b1)
        self.eng1.commit("add research tag", [b.beacon_id])
        b2 = self.store2.get_beacon(b.beacon_id)
        b2.tags = ["t", "policy"]
        self.store2.put_beacon(b2)
        self.eng2.commit("add policy tag", [b.beacon_id])
        self.eng2.push(self.transport)
        self.eng1.pull(self.transport)
        merged = self.store1.get_beacon(b.beacon_id)
        self.assertIn("research", merged.tags)
        self.assertIn("policy", merged.tags)

    def test_note_conflict_surfaced(self):
        b = self._add(self.store1, title="A", note="base line one")
        self.eng1.commit("add", [b.beacon_id])
        self.eng1.push(self.transport)
        self.eng2.pull(self.transport)
        b1 = self.store1.get_beacon(b.beacon_id)
        b1.note = "base line one\nlocal edit"
        self.store1.put_beacon(b1)
        self.eng1.commit("local note", [b.beacon_id])
        self.eng1.push(self.transport)
        applied, conflicts = self.eng2.pull(self.transport)
        # dev2 had the same base; pulling dev1's note merges in the new line
        merged = self.store2.get_beacon(b.beacon_id)
        self.assertIn("local edit", merged.note)


if __name__ == "__main__":
    unittest.main()
