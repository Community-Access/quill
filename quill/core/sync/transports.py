"""Sync transports (PRD 45.2): BYO folder now, BYO git and hosted server hooks.

A transport is the remote a :class:`~quillsync.engine.SyncEngine` pushes to and
pulls from. It stores immutable commits and content-addressed encrypted blobs;
it never sees plaintext (E2E encryption happens in the engine before any blob
leaves the machine, PRD 45.3).

The folder transport (tier 2) is implemented here in full. The git-remote tier
(1) and the hosted server tier (3) are the same commit format over a different
backend; :class:`ServerTransport` adapts the reference server's HTTP API.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from quill.core.sync.protocol import Commit


class Transport:
    """Abstract transport: commits + content-addressed blobs."""

    def has_commit(self, commit_id: str) -> bool:
        raise NotImplementedError

    def write_commit(self, commit: Commit) -> None:
        raise NotImplementedError

    def read_commit(self, commit_id: str) -> Commit | None:
        raise NotImplementedError

    def list_commit_ids(self) -> list[str]:
        raise NotImplementedError

    def has_object(self, blob_hash: str) -> bool:
        raise NotImplementedError

    def write_object(self, blob_hash: str, data: bytes) -> None:
        raise NotImplementedError

    def read_object(self, blob_hash: str) -> bytes:
        raise NotImplementedError


class FolderTransport(Transport):
    """BYO folder remote (PRD 45.2 tier 2). Commits and objects on disk.

    Point this at an iCloud/OneDrive/Dropbox/Syncthing folder. The commit
    format is plain JSON; blobs are raw encrypted bytes content-addressed by
    sha256. No git required.
    """

    def __init__(self, remote_dir: str | Path) -> None:
        self.root = Path(remote_dir)
        (self.root / "commits").mkdir(parents=True, exist_ok=True)
        (self.root / "objects").mkdir(parents=True, exist_ok=True)

    def has_commit(self, commit_id: str) -> bool:
        return (self.root / "commits" / f"{commit_id}.json").exists()

    def write_commit(self, commit: Commit) -> None:
        path = self.root / "commits" / f"{commit.commit_id}.json"
        path.write_text(json.dumps(commit.to_dict(), indent=2), encoding="utf-8")

    def read_commit(self, commit_id: str) -> Commit | None:
        path = self.root / "commits" / f"{commit_id}.json"
        if not path.exists():
            return None
        return Commit.from_dict(json.loads(path.read_text(encoding="utf-8")))

    def list_commit_ids(self) -> list[str]:
        return sorted(p.stem for p in (self.root / "commits").glob("*.json"))

    def has_object(self, blob_hash: str) -> bool:
        return (self.root / "objects" / blob_hash).exists()

    def write_object(self, blob_hash: str, data: bytes) -> None:
        path = self.root / "objects" / blob_hash
        if not path.exists():
            path.write_bytes(data)

    def read_object(self, blob_hash: str) -> bytes:
        return (self.root / "objects" / blob_hash).read_bytes()


class ServerTransport(Transport):
    """Hosted server remote (PRD 45.2 tier 3) over the reference HTTP API.

    The server exposes a *bulk* push/pull contract (POST /sync/push with a
    batch of commits+objects; POST /sync/pull with the ids the client already
    has). This class adapts that bulk contract to the per-item
    :class:`Transport` interface the engine expects, so an application swaps
    ``FolderTransport`` for ``ServerTransport`` with no other changes.

    ``client`` is any object implementing the ``server.client.ServerClient``
    shape (``push``, ``pull``, ``hints``); quillsync itself never imports
    ``requests``, so the framework stays pure and the network boundary stays
    in the application's client.
    """

    def __init__(self, client: Any) -> None:
        self.client = client
        self._commits: dict[str, Commit] = {}
        self._objects: dict[str, bytes] = {}
        self._pending_objects: dict[str, bytes] = {}
        self._fetched = False

    # -- read side: bulk pull, cache, serve per-item -------------------------

    def _fetch(self) -> None:
        # Pull every commit the server has (have=[]). The engine filters out
        # ids it already knows, so over-fetching is safe for a reference.
        data = self.client.pull([])
        self._commits = {}
        for c in data.get("commits") or []:
            commit = Commit.from_dict(c)
            self._commits[commit.commit_id] = commit
        self._objects = dict(data.get("objects") or {})
        self._fetched = True

    def _ensure_fetched(self) -> None:
        if not self._fetched:
            self._fetch()

    def list_commit_ids(self) -> list[str]:
        self._fetch()
        return list(self._commits.keys())

    def has_commit(self, commit_id: str) -> bool:
        self._ensure_fetched()
        return commit_id in self._commits

    def read_commit(self, commit_id: str) -> Commit | None:
        self._ensure_fetched()
        return self._commits.get(commit_id)

    def has_object(self, blob_hash: str) -> bool:
        self._ensure_fetched()
        return blob_hash in self._objects

    def read_object(self, blob_hash: str) -> bytes:
        self._ensure_fetched()
        return self._objects[blob_hash]

    # -- write side: buffer objects, flush one commit at a time --------------

    def write_object(self, blob_hash: str, data: bytes) -> None:
        if not self.has_object(blob_hash):
            self._pending_objects[blob_hash] = data

    def write_commit(self, commit: Commit) -> None:
        # Push this commit together with any blobs buffered for it. The server
        # accepts a batch, so a single push per commit is the natural unit.
        self.client.push([commit.to_dict()], self._pending_objects)
        self._objects.update(self._pending_objects)
        self._commits[commit.commit_id] = commit
        self._pending_objects = {}
