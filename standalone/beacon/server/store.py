"""QuillSync hosted server -- data store (PRD 45.5).

A runnable reference server using stdlib only (sqlite + http.server), so it
can be developed and tested without external infrastructure. PRD 45.5 names
the production stack (FastAPI + PostgreSQL + S3-compatible object storage +
Redis); this module is the same shape, backed by sqlite and the filesystem so
the contract is provable locally.

The server stores only encrypted blobs and an opaque commit graph. It cannot
read private content (PRD 23.3, 45.3). Search stays local.
"""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path
from typing import Any

SCHEMA = """
CREATE TABLE IF NOT EXISTS accounts (
    email TEXT PRIMARY KEY,
    created INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS devices (
    device_id TEXT PRIMARY KEY,
    account_email TEXT NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL,
    revoked INTEGER NOT NULL DEFAULT 0,
    FOREIGN KEY (account_email) REFERENCES accounts(email)
);

CREATE TABLE IF NOT EXISTS magic_tokens (
    token_hash TEXT PRIMARY KEY,
    email TEXT NOT NULL,
    device_hint TEXT,
    created INTEGER NOT NULL,
    expires INTEGER NOT NULL,
    used INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS commits (
    commit_id TEXT PRIMARY KEY,
    account_email TEXT NOT NULL,
    parent TEXT,
    message TEXT NOT NULL DEFAULT '',
    created INTEGER NOT NULL,
    device TEXT NOT NULL DEFAULT '',
    manifest TEXT NOT NULL DEFAULT '[]',
    FOREIGN KEY (account_email) REFERENCES accounts(email)
);
CREATE INDEX IF NOT EXISTS idx_commits_account ON commits(account_email);

CREATE TABLE IF NOT EXISTS objects (
    blob_hash TEXT PRIMARY KEY,
    account_email TEXT NOT NULL,
    data BLOB NOT NULL,
    size INTEGER NOT NULL,
    created INTEGER NOT NULL,
    FOREIGN KEY (account_email) REFERENCES accounts(email)
);
"""


class ServerStore:
    """SQLite-backed server store. One row per account/device/commit/object."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False: the HTTP server handles requests on a worker
        # thread, while the store may be created on the main thread. The
        # reference HTTPServer is single-threaded per request, so no extra
        # locking is needed for correctness.
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    def close(self) -> None:
        self.conn.close()

    # -- accounts / devices ---------------------------------------------------

    def ensure_account(self, email: str) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO accounts(email, created) VALUES(?, ?)",
            (email.lower(), int(time.time())),
        )
        self.conn.commit()

    def issue_magic_token(self, email: str, *, ttl: int = 900, device_hint: str = "") -> str:
        """Create a single-use magic-link token. Returns the raw token (to send).

        Only the token HASH is stored (PRD 45.9). The raw token leaves the
        server immediately via the mailer and is never persisted.
        """
        import hashlib

        raw = os.urandom(24).hex()
        token_hash = hashlib.sha256(raw.encode()).hexdigest()
        now = int(time.time())
        self.conn.execute(
            "INSERT INTO magic_tokens(token_hash, email, device_hint, created, expires, used) "
            "VALUES(?, ?, ?, ?, ?, 0)",
            (token_hash, email.lower(), device_hint, now, now + ttl),
        )
        self.conn.commit()
        return raw

    def verify_magic_token(self, raw_token: str) -> str | None:
        """Consume a magic token. Returns the account email, or None if invalid."""
        import hashlib

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        row = self.conn.execute(
            "SELECT * FROM magic_tokens WHERE token_hash=?", (token_hash,)
        ).fetchone()
        if not row or row["used"] or row["expires"] < int(time.time()):
            return None
        self.conn.execute("UPDATE magic_tokens SET used=1 WHERE token_hash=?", (token_hash,))
        self.ensure_account(row["email"])
        self.conn.commit()
        return row["email"]

    def register_device(self, email: str, name: str, raw_token: str) -> dict:
        import hashlib

        device_id = os.urandom(8).hex()
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        self.conn.execute(
            "INSERT INTO devices(device_id, account_email, token_hash, name, created) "
            "VALUES(?, ?, ?, ?, ?)",
            (device_id, email.lower(), token_hash, name, int(time.time())),
        )
        self.conn.commit()
        return {"device_id": device_id, "device_token": raw_token}

    def auth_device(self, raw_token: str) -> str | None:
        """Return the account email for a valid device token, else None."""
        import hashlib

        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        row = self.conn.execute(
            "SELECT account_email FROM devices WHERE token_hash=? AND revoked=0",
            (token_hash,),
        ).fetchone()
        return row["account_email"] if row else None

    def revoke_device(self, device_id: str) -> None:
        self.conn.execute("UPDATE devices SET revoked=1 WHERE device_id=?", (device_id,))
        self.conn.commit()

    # -- commits / objects ----------------------------------------------------

    def put_commit(self, account: str, commit: dict) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO commits(commit_id, account_email, parent, message, "
            "created, device, manifest) VALUES(?, ?, ?, ?, ?, ?, ?)",
            (commit["commit_id"], account.lower(), commit.get("parent"),
             commit.get("message", ""), commit.get("created", 0),
             commit.get("device", ""), json.dumps(commit.get("entries", []))),
        )
        self.conn.commit()

    def has_commit(self, account: str, commit_id: str) -> bool:
        row = self.conn.execute(
            "SELECT 1 FROM commits WHERE account_email=? AND commit_id=?",
            (account.lower(), commit_id),
        ).fetchone()
        return row is not None

    def put_object(self, account: str, blob_hash: str, data: bytes) -> None:
        self.conn.execute(
            "INSERT OR IGNORE INTO objects(blob_hash, account_email, data, size, created) "
            "VALUES(?, ?, ?, ?, ?)",
            (blob_hash, account.lower(), data, len(data), int(time.time())),
        )
        self.conn.commit()

    def get_object(self, account: str, blob_hash: str) -> bytes | None:
        row = self.conn.execute(
            "SELECT data FROM objects WHERE account_email=? AND blob_hash=?",
            (account.lower(), blob_hash),
        ).fetchone()
        return row["data"] if row else None

    def commits_since(self, account: str, have: set[str]) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM commits WHERE account_email=? ORDER BY created",
            (account.lower(),),
        ).fetchall()
        out = []
        for r in rows:
            if r["commit_id"] in have:
                continue
            out.append({
                "commit_id": r["commit_id"], "parent": r["parent"],
                "message": r["message"], "created": r["created"],
                "device": r["device"], "entries": json.loads(r["manifest"]),
            })
        return out