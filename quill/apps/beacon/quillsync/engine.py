"""Generic QuillSync engine (PRD 45): git-like, E2E encrypted, BYO remote.

A commit is an immutable, encrypted snapshot of the entities that changed,
linked to a parent commit. Push copies local commits to a remote; pull applies
remote commits not yet local, in parent order. Merge is delegated to the
application's :class:`~quillsync.protocol.MergeFn`, so the framework stays
record-agnostic -- Beacon, Quill settings, Quill Radio stations, and Quill Cast
episodes all use the same engine with their own adapter and merge function.

Pure logic over a :class:`~quillsync.protocol.RecordStore`; wx-free and
unit-testable. Nothing here touches the network or any domain model.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from quill.apps.beacon.quillsync import crypto
from quill.apps.beacon.quillsync.protocol import (
    Commit,
    Conflict,
    ManifestEntry,
    MergeFn,
    RecordStore,
    default_merge,
)
from quill.apps.beacon.quillsync.transports import Transport


class SyncEngine:
    """Local-first sync over a RecordStore with a vault key."""

    def __init__(
        self,
        store: RecordStore,
        vault: crypto.VaultKey,
        *,
        device: str,
        data_dir: str | Path,
        merge_fn: MergeFn | None = None,
        entity_type: str = "record",
    ) -> None:
        self.store = store
        self.vault = vault
        self.device = device
        self.entity_type = entity_type
        self.merge_fn = merge_fn or default_merge
        self.data_dir = Path(data_dir)
        (self.data_dir / "sync" / "objects").mkdir(parents=True, exist_ok=True)
        self.log_path = self.data_dir / "sync" / "log.jsonl"

    # -- local commit log ----------------------------------------------------

    def _read_log(self) -> list[Commit]:
        if not self.log_path.exists():
            return []
        out = []
        for line in self.log_path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                out.append(Commit.from_dict(json.loads(line)))
        return out

    def _append_log(self, commit: Commit) -> None:
        with self.log_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(commit.to_dict()) + "\n")

    def head(self) -> str | None:
        log = self._read_log()
        return log[-1].commit_id if log else None

    def _local_object_path(self, blob_hash: str) -> Path:
        return self.data_dir / "sync" / "objects" / blob_hash

    # -- commit --------------------------------------------------------------

    def commit(self, message: str, entity_ids: list[str]) -> Commit:
        """Snapshot the given entities into an encrypted commit.

        An entity whose ``get_record`` returns None is sent as a tombstone, so
        a delete/trash on one device propagates as recoverable Trash on others
        (PRD 23.5) rather than an instant destroy.
        """
        entries: list[ManifestEntry] = []
        for eid in entity_ids:
            record = self.store.get_record(eid)
            if record is None:
                entries.append(ManifestEntry(eid, self.entity_type, True, "", ""))
                continue
            dek = crypto.new_dek()
            blob = crypto.encrypt_json(dek, record)
            blob_hash = crypto.object_hash(blob)
            self._local_object_path(blob_hash).write_bytes(blob)
            entries.append(
                ManifestEntry(
                    eid,
                    self.entity_type,
                    False,
                    blob_hash,
                    crypto._b64(crypto.wrap_dek(self.vault, dek)),
                )
            )
        commit = Commit(
            commit_id=_new_id("cmt"),
            parent=self.head(),
            message=message,
            created=_now_ms(),
            device=self.device,
            entries=entries,
        )
        self._append_log(commit)
        return commit

    # -- push / pull ----------------------------------------------------------

    def push(self, transport: Transport) -> int:
        """Copy local commits (and their blobs) not on the remote. Returns count."""
        pushed = 0
        for commit in self._read_log():
            if transport.has_commit(commit.commit_id):
                continue
            for e in commit.entries:
                if e.tombstone:
                    continue
                if not transport.has_object(e.blob_hash):
                    blob = self._local_object_path(e.blob_hash).read_bytes()
                    transport.write_object(e.blob_hash, blob)
            transport.write_commit(commit)
            pushed += 1
        return pushed

    def pull(self, transport: Transport) -> tuple[int, list[Conflict]]:
        """Apply remote commits not local, in parent order. Returns (count, conflicts)."""
        local_ids = {c.commit_id for c in self._read_log()}
        remote_ids = set(transport.list_commit_ids())
        new_ids = remote_ids - local_ids
        ordered = self._order_commits(transport, new_ids)
        conflicts: list[Conflict] = []
        applied = 0
        for cid in ordered:
            commit = transport.read_commit(cid)
            if commit is None:
                continue
            for entry in commit.entries:
                conflicts.extend(self._apply_entry(transport, entry))
            self._append_log(commit)
            applied += 1
        return applied, conflicts

    def _order_commits(self, transport: Transport, ids: set[str]) -> list[str]:
        # Walk each new commit's parent chain until we hit a known commit.
        ordered: list[str] = []
        visited: set[str] = set()

        def visit(cid: str) -> None:
            if cid in visited or cid not in ids:
                return
            commit = transport.read_commit(cid)
            if commit and commit.parent and commit.parent in ids:
                visit(commit.parent)
            visited.add(cid)
            ordered.append(cid)

        for cid in sorted(ids):
            visit(cid)
        return ordered

    def _apply_entry(self, transport: Transport, entry: ManifestEntry) -> list[Conflict]:
        if entry.tombstone:
            self.store.delete_record(entry.entity_id)
            return []
        blob = transport.read_object(entry.blob_hash)
        dek = crypto.unwrap_dek(self.vault, crypto._unb64(entry.wrapped_dek))
        remote_record = crypto.decrypt_json(dek, blob)
        local_record = self.store.get_record(entry.entity_id)
        merged, conflicts = self.merge_fn(local_record, remote_record)
        self.store.put_record(entry.entity_id, merged)
        return conflicts


def _now_ms() -> int:
    return int(time.time() * 1000)


def _new_id(prefix: str) -> str:
    return f"{prefix}_{os.urandom(8).hex()}"
