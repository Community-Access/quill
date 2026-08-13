"""In-client sync controller for QuillBeacon (PRD 45, 45.9, 46.2).

Wraps the QuillSync engine + transports into the operations the Beacon shell
needs, with fail-safe behavior everywhere:

- Sync is off until configured and unlocked. Nothing leaves the machine by
  default.
- The vault key is derived from a passphrase the user enters each session; the
  passphrase is never stored. Only the scrypt salt is persisted.
- Every network/server call is wrapped so a failure returns an error dict and
  never corrupts the local library. A failed push leaves the local commit
  unpushed (retried next sync); a failed pull applies nothing.
- Before each sync the controller snapshots the database, so a user can roll
  back to how things were before a given sync (PRD 18.5 history/rollback).

The controller is wx-free and unit-testable; the shell supplies dialogs and
refresh callbacks. Network lives behind ``ServerClient`` (requests), imported
lazily so the module loads without it.
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

from quill.apps.beacon import sync_crypto as crypto
from quill.apps.beacon.sync import FolderTransport, SyncEngine

CONFIG_NAME = "sync_config.json"
BACKUP_DIR = "sync_backups"
CONFLICTS_NAME = "sync_conflicts.json"


class SyncConfig:
    """Persisted sync configuration. The passphrase is never stored."""

    def __init__(
        self,
        *,
        transport: str = "off",  # off | folder | server
        folder: str = "",
        server_url: str = "",
        device: str = "",
        account: str = "",
        device_token: str = "",
        salt_b64: str = "",
        auto_sync_seconds: int = 0,
    ) -> None:
        self.transport = transport
        self.folder = folder
        self.server_url = server_url
        self.device = device
        self.account = account
        self.device_token = device_token
        self.salt_b64 = salt_b64
        self.auto_sync_seconds = auto_sync_seconds

    def to_dict(self) -> dict[str, Any]:
        return {
            "transport": self.transport,
            "folder": self.folder,
            "server_url": self.server_url,
            "device": self.device,
            "account": self.account,
            "device_token": self.device_token,
            "salt_b64": self.salt_b64,
            "auto_sync_seconds": self.auto_sync_seconds,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> SyncConfig:
        return cls(
            transport=d.get("transport", "off"),
            folder=d.get("folder", ""),
            server_url=d.get("server_url", ""),
            device=d.get("device", ""),
            account=d.get("account", ""),
            device_token=d.get("device_token", ""),
            salt_b64=d.get("salt_b64", ""),
            auto_sync_seconds=int(d.get("auto_sync_seconds", 0) or 0),
        )

    def is_configured(self) -> bool:
        if self.transport == "folder":
            return bool(self.folder)
        if self.transport == "server":
            return bool(self.server_url and self.device_token)
        return False


class SyncController:
    """Owns config, vault unlock, snapshots, and sync operations."""

    def __init__(self, store, data_dir: str | Path) -> None:
        self.store = store
        self.data_dir = Path(data_dir)
        self.config_path = self.data_dir / CONFIG_NAME
        self.backup_dir = self.data_dir / BACKUP_DIR
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.conflicts_path = self.data_dir / CONFLICTS_NAME
        self.config = self._load_config()
        self._vault: crypto.VaultKey | None = None
        # Capture the live DB file path while the connection is open, so
        # snapshot/rollback still work after the store is closed.
        self._db_file = self._db_path()

    # -- config persistence --------------------------------------------------

    def _load_config(self) -> SyncConfig:
        if not self.config_path.exists():
            return SyncConfig()
        try:
            return SyncConfig.from_dict(json.loads(self.config_path.read_text(encoding="utf-8")))
        except Exception:
            return SyncConfig()

    def save_config(self, cfg: SyncConfig) -> None:
        self.config = cfg
        self.config_path.write_text(json.dumps(cfg.to_dict(), indent=2), encoding="utf-8")

    # -- vault ---------------------------------------------------------------

    def has_vault(self) -> bool:
        return bool(self.config.salt_b64)

    def is_unlocked(self) -> bool:
        return self._vault is not None

    def setup_vault(self, passphrase: str) -> crypto.VaultKey:
        """Create a new vault (new salt). For a first-time setup or re-key."""
        if not passphrase:
            raise ValueError("Passphrase required")
        self._vault = crypto.derive_vault_key(passphrase)
        self.config.salt_b64 = crypto._b64(self._vault.salt)
        self.save_config(self.config)
        return self._vault

    def unlock(self, passphrase: str) -> crypto.VaultKey:
        """Derive the vault key from the stored salt + passphrase."""
        if not self.config.salt_b64:
            raise RuntimeError("No vault configured; set up sync first")
        salt = crypto._unb64(self.config.salt_b64)
        self._vault = crypto.derive_vault_key(passphrase, salt=salt)
        return self._vault

    def lock(self) -> None:
        self._vault = None

    # -- cross-device pairing (PRD 45.7) -------------------------------------

    def export_vault_pairing(self) -> dict:
        """Return the shareable vault pairing code (the salt).

        The salt is the only thing a second device needs to derive the same
        vault key; the passphrase is entered separately on each device and is
        never transferred. Fail-safe: returns an error dict if no vault exists.
        """
        if not self.has_vault():
            return {"error": "Set up the vault on this device first"}
        return {"pairing_code": self.config.salt_b64}

    def import_vault_pairing(self, pairing_code: str) -> dict:
        """Adopt a vault salt exported from another device.

        After importing, the user unlocks with the same passphrase used on the
        originating device. The existing vault, if any, is replaced -- records
        encrypted under the old key will no longer decrypt, so this is intended
        for a fresh device or a deliberate re-pair. Fail-safe: never raises.
        """
        code = (pairing_code or "").strip()
        if not code:
            return {"error": "Paste a pairing code"}
        try:
            crypto._unb64(code)  # validate it decodes
        except Exception:
            return {"error": "That does not look like a valid pairing code"}
        self.config.salt_b64 = code
        self._vault = None  # force a fresh unlock under the new salt
        self.save_config(self.config)
        return {"ok": True}

    # -- transport -----------------------------------------------------------

    def build_transport(self):
        cfg = self.config
        if cfg.transport == "folder":
            return FolderTransport(cfg.folder)
        if cfg.transport == "server":
            client = self._make_server_client(cfg)
            from quill.core.sync.transports import ServerTransport

            return ServerTransport(client)
        raise RuntimeError("Sync is off; nothing to transport")

    def _make_server_client(self, cfg: SyncConfig):
        try:
            from quill.apps.beacon.server_client import ServerClient
        except ImportError as ex:
            raise RuntimeError("server client unavailable (requests not installed)") from ex
        return ServerClient(cfg.server_url, cfg.device_token)

    # -- magic-link auth (PRD 45.9) ------------------------------------------

    def request_magic_link(self, email: str) -> dict:
        """Ask the server to email a sign-in link. Fail-safe: never raises."""
        if not self.config.server_url:
            return {"error": "Set a server URL first"}
        try:
            from quill.apps.beacon.server_client import ServerClient
        except ImportError:
            return {"error": "requests library not installed; cannot reach server"}
        try:
            return ServerClient.request_magic_link(self.config.server_url, email)
        except Exception as ex:
            return {"error": f"could not request link: {ex}"}

    def fetch_hints(self) -> dict:
        """Ask the server how many new commits are waiting (PRD 45.5).

        Fail-safe: returns an error dict (never raises) when sync is off, the
        device is not signed in, the requests library is missing, or the server
        is unreachable. On success returns ``{"new": N}``.
        """
        if self.config.transport != "server" or not self.config.device_token:
            return {"error": "Not signed in to a server"}
        try:
            client = self._make_server_client(self.config)
            return client.hints()
        except Exception as ex:
            return {"error": f"could not reach server: {ex}"}

    def verify_magic_link(self, token: str, device: str) -> dict:
        """Exchange a magic-link token for a device token. Fail-safe."""
        if not self.config.server_url:
            return {"error": "Set a server URL first"}
        try:
            from quill.apps.beacon.server_client import ServerClient
        except ImportError:
            return {"error": "requests library not installed; cannot reach server"}
        try:
            res = ServerClient.verify_magic_link(self.config.server_url, token, device)
        except Exception as ex:
            return {"error": f"verify failed: {ex}"}
        if "device_token" in res:
            self.config.device_token = res["device_token"]
            self.config.account = res.get("account", self.config.account)
            self.save_config(self.config)
        return res

    # -- sync now ------------------------------------------------------------

    def _all_beacon_ids(self) -> list[str]:
        rows = self.store.conn.execute("SELECT beacon_id FROM beacons").fetchall()
        return [r["beacon_id"] for r in rows]

    def _snapshot(self) -> str:
        """Copy the live DB to a timestamped backup before a sync.

        Checkpoints the WAL first so all committed data is in the main .db
        file, then copies only that file. (BeaconStore runs in WAL mode; a
        naive copy of the .db alone could miss recently committed rows still
        in the -wal file.)
        """
        ts = _now_ms()
        name = f"sync_{ts}.db"
        db_file = self._db_path()
        if db_file and Path(db_file).exists():
            try:
                self.store.conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            except Exception:
                pass  # best-effort; copy whatever is on disk
            shutil.copy2(db_file, self.backup_dir / name)
        return name

    def _db_path(self) -> str:
        # Prefer the cached path (works after the store is closed); fall back
        # to a live query for the first capture in __init__.
        cached = getattr(self, "_db_file", "")
        if cached:
            return cached
        if self.store is None:
            return ""
        try:
            for r in self.store.conn.execute("PRAGMA database_list").fetchall():
                if r["name"] == "main":
                    return r["file"] or ""
        except Exception:
            return ""
        return ""

    def sync_now(self) -> dict:
        """Commit, push, pull. Returns a summary dict; never raises."""
        if not self.config.is_configured():
            return {"error": "Sync is not configured"}
        if not self.is_unlocked():
            return {"error": "Unlock the vault first"}
        try:
            backup = self._snapshot()
        except Exception as ex:
            return {"error": f"snapshot failed: {ex}"}
        try:
            engine = SyncEngine(
                self.store,
                self._vault,
                device=self.config.device or "beacon",
                data_dir=self.data_dir,
            )
            committed, commit_count = self._commit_changes(engine)
            transport = self.build_transport()
            pushed = engine.push(transport)
            pulled, conflicts = engine.pull(transport)
            if conflicts:
                self._persist_conflicts(conflicts)
            return {
                "ok": True,
                "pushed": pushed,
                "pulled": pulled,
                "committed": commit_count,
                "conflicts": conflicts,
                "backup": backup,
            }
        except Exception as ex:
            return {"error": f"sync failed (local state intact): {ex}", "backup": backup}

    def _commit_changes(self, engine) -> tuple[list[str], int]:
        """Commit only what changed since the last sync (PRD 45.8).

        The first sync (no local commits yet) takes a full snapshot of every
        beacon so other devices get the whole library. After that only dirty
        beacons (any local edit) plus pending tombstones (permanent deletes)
        are committed, and their dirty/tombstone markers are cleared once the
        commit is safely in the local log -- a later failed push still retries
        from the log, so no change is lost.
        """
        dirty = self.store.dirty_beacon_ids()
        tombstones = self.store.tombstone_ids()
        if not self._has_local_commits():
            # Initial full snapshot so a fresh device shares everything.
            ids = self._all_beacon_ids() + tombstones
        else:
            ids = dirty + tombstones
        if not ids:
            return [], 0
        engine.commit("sync", ids)
        self.store.clear_dirty(dirty)
        self.store.clear_tombstones(tombstones)
        return ids, len(ids)

    def _has_local_commits(self) -> bool:
        log_path = self.data_dir / "sync" / "log.jsonl"
        try:
            return log_path.exists() and log_path.stat().st_size > 0
        except Exception:
            return False

    # -- history + rollback --------------------------------------------------

    def history(self) -> list[dict]:
        """Summarize the local commit log (PRD 18.5)."""
        log_path = self.data_dir / "sync" / "log.jsonl"
        if not log_path.exists():
            return []
        from quill.core.sync.protocol import Commit

        out = []
        for line in log_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                c = Commit.from_dict(json.loads(line))
            except Exception:
                continue
            out.append({
                "commit_id": c.commit_id,
                "created": c.created,
                "message": c.message,
                "device": c.device,
                "entries": len(c.entries),
            })
        return out

    # -- conflict review (PRD 23.5, 45.6) -----------------------------------

    def _persist_conflicts(self, conflicts) -> None:
        """Append new unresolved conflicts, deduped by entity_id + field.

        Conflicts carry the local/remote/merged note strings (the only field
        beacon_merge surfaces a conflict for). Resolution is picking which
        note wins; no vault is needed because the records are already decrypted.
        """
        existing = self._read_conflicts()
        seen = {(c["entity_id"], c["field"], c.get("resolved", False)) for c in existing}
        idx = len(existing)
        for cf in conflicts:
            key = (cf.entity_id, cf.field, False)
            if key in seen:
                continue
            existing.append({
                "id": f"cf_{idx}",
                "entity_id": cf.entity_id,
                "field": cf.field,
                "local": cf.local,
                "remote": cf.remote,
                "merged": cf.merged,
                "message": cf.message,
                "resolved": False,
                "resolution": None,
                "created": _now_ms(),
            })
            seen.add(key)
            idx += 1
        self.conflicts_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    def _read_conflicts(self) -> list[dict]:
        if not self.conflicts_path.exists():
            return []
        try:
            data = json.loads(self.conflicts_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def list_conflicts(self, *, resolved: bool = False) -> list[dict]:
        return [c for c in self._read_conflicts() if c.get("resolved", False) == resolved]

    def resolve_conflict(self, conflict_id: str, choice: str) -> dict:
        """Apply the user's choice (local/remote/merged) and mark resolved.

        The beacon was already merged by the pull; resolution overwrites the
        note with the chosen version. Returns a result dict; never raises.
        """
        if choice not in ("local", "remote", "merged"):
            return {"error": "choice must be local, remote, or merged"}
        conflicts = self._read_conflicts()
        target = next((c for c in conflicts if c["id"] == conflict_id), None)
        if target is None:
            return {"error": "conflict not found"}
        if target.get("resolved"):
            return {"ok": True, "already": True}
        try:
            b = self.store.get_beacon(target["entity_id"])
            if b is None:
                return {"error": "beacon no longer exists"}
            b.note = target[choice]
            self.store.put_beacon(b)
        except Exception as ex:
            return {"error": f"could not apply: {ex}"}
        target["resolved"] = True
        target["resolution"] = choice
        self.conflicts_path.write_text(json.dumps(conflicts, indent=2), encoding="utf-8")
        return {"ok": True, "resolution": choice}

    def list_backups(self) -> list[dict]:
        out = []
        for p in sorted(self.backup_dir.glob("sync_*.db"), reverse=True):
            name = p.name
            try:
                ts = int(name[len("sync_") : -len(".db")])
            except ValueError:
                ts = 0
            out.append({"name": name, "created": ts, "size": p.stat().st_size})
        return out

    def restore_backup(self, name: str) -> bool:
        """Copy a backup over the live DB file. Caller must close the store first.

        ``name`` is validated against the backup directory to prevent path
        traversal -- only an existing backup file may be restored.
        """
        src = self.backup_dir / name
        try:
            src = src.resolve()
            base = self.backup_dir.resolve()
            if base not in src.parents and src != base:
                return False
        except (ValueError, OSError):
            return False
        if not src.exists() or not src.is_file():
            return False
        db_file = self._db_path()
        if not db_file:
            return False
        shutil.copy2(src, db_file)
        return True


def _now_ms() -> int:
    import time

    return int(time.time() * 1000)


def _default_data_dir() -> Path:
    """Compute the data dir without importing wx (for the CLI verify path)."""
    from quill.apps.beacon import paths

    return paths.data_dir()


def main(argv: list[str] | None = None) -> int:
    """CLI entry: exchange a magic-link token for a device token (PRD 45.9).

    Supports the ``quillsync://verify`` custom-scheme flow from a terminal for
    environments where OS scheme registration is not available, and for CI. The
    companion app's normal path is the OS-registered scheme handler.
    """
    import argparse

    parser = argparse.ArgumentParser(prog="quill.apps.beacon.sync_ui")
    sub = parser.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("verify", help="Exchange a magic-link token for a device token")
    v.add_argument("--server", required=True, help="Server base URL")
    v.add_argument("--token", required=True, help="Magic-link token")
    v.add_argument("--device", default="device", help="Device name")
    v.add_argument("--data-dir", default="", help="QuillBeacon data directory")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir) if args.data_dir else _default_data_dir()
    cfg_path = data_dir / CONFIG_NAME
    cfg = SyncConfig.from_dict(
        json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
    )
    cfg.server_url = args.server
    ctrl = SyncController.__new__(SyncController)
    ctrl.data_dir = data_dir
    ctrl.config_path = cfg_path
    ctrl.backup_dir = data_dir / BACKUP_DIR
    ctrl.backup_dir.mkdir(parents=True, exist_ok=True)
    ctrl.config = cfg
    ctrl._vault = None
    ctrl.store = None
    res = ctrl.verify_magic_link(args.token, args.device)
    if "error" in res:
        print(f"verify failed: {res['error']}")
        return 1
    print(f"verified; device token saved for {res.get('account', cfg.account)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
