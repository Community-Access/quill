"""Tests for the in-client SyncController (PRD 45, 45.9, 46.2).

These exercise the fail-safe, no-network paths: config persistence, vault
unlock/setup, folder-transport sync end to end, snapshots, history, and
rollback. Server paths are covered by mocking the server client where needed.
"""

from unittest.mock import patch

from quill.apps.beacon.db import BeaconStore
from quill.apps.beacon.model import Beacon, Resource
from quill.apps.beacon.sync_ui import SyncConfig, SyncController


def _store_and_ctrl(tmp_path):
    store = BeaconStore(str(tmp_path / "beacons.db"))
    ctrl = SyncController(store, tmp_path)
    return store, ctrl


def _seed(store, title="A"):
    res = Resource(title=title, type="web", primary_uri=f"https://x/{title}")
    b = Beacon(resource_id=res.resource_id, title=title, in_inbox=False)
    store.put_beacon(b, resource=res)
    return b


def test_config_defaults_off(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    assert ctrl.config.transport == "off"
    assert not ctrl.config.is_configured()
    assert not ctrl.is_unlocked()


def test_config_persistence_roundtrip(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    cfg = SyncConfig(transport="folder", folder=str(tmp_path / "remote"), device="laptop")
    ctrl.save_config(cfg)
    ctrl2 = SyncController(_s, tmp_path)
    assert ctrl2.config.transport == "folder"
    assert ctrl2.config.folder == str(tmp_path / "remote")
    assert ctrl2.config.is_configured()


def test_vault_setup_and_unlock(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.setup_vault("correct horse battery staple")
    assert ctrl.has_vault()
    assert ctrl.is_unlocked()
    ctrl.lock()
    assert not ctrl.is_unlocked()
    ctrl.unlock("correct horse battery staple")
    assert ctrl.is_unlocked()


def test_unlock_without_vault_errors(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    try:
        ctrl.unlock("x")
        raise AssertionError("expected RuntimeError")
    except RuntimeError:
        pass


def test_sync_now_off_returns_error(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.sync_now()
    assert "error" in res


def test_sync_now_folder_end_to_end(tmp_path):
    # Two devices sharing a folder remote.
    remote = tmp_path / "remote"
    s1 = BeaconStore(str(tmp_path / "d1.db"))
    c1 = SyncController(s1, tmp_path / "d1dir")
    c1.save_config(SyncConfig(transport="folder", folder=str(remote), device="d1"))
    c1.setup_vault("pass")
    _seed(s1, "Alpha")

    s2 = BeaconStore(str(tmp_path / "d2.db"))
    c2 = SyncController(s2, tmp_path / "d2dir")
    c2.save_config(SyncConfig(transport="folder", folder=str(remote), device="d2"))
    c2.setup_vault("pass")  # same passphrase -> same vault? No: different salt.

    # Note: different salts mean different vault keys, so cross-device decrypt
    # would fail. For this test we re-key c2 to c1's salt so they share a vault.
    c2.config.salt_b64 = c1.config.salt_b64
    c2.save_config(c2.config)
    c2.unlock("pass")

    r1 = c1.sync_now()
    assert r1.get("ok"), r1
    r2 = c2.sync_now()
    assert r2.get("ok"), r2
    assert r2["pulled"] >= 1
    titles = [b.title for b in s2.list_beacons()]
    assert "Alpha" in titles


def test_sync_makes_snapshot(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(tmp_path / "r"), device="d"))
    ctrl.setup_vault("p")
    _seed(s, "X")
    res = ctrl.sync_now()
    assert res.get("ok")
    backups = ctrl.list_backups()
    assert len(backups) >= 1
    assert backups[0]["name"] == res["backup"]


def test_rollback_restores_state(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(tmp_path / "r"), device="d"))
    ctrl.setup_vault("p")
    _seed(s, "Before")
    res = ctrl.sync_now()
    backup = res["backup"]
    # Make a change after the sync.
    _seed(s, "After")
    assert "After" in [b.title for b in s.list_beacons()]
    # Rollback: close, restore, reopen.
    s.close()
    assert ctrl.restore_backup(backup)
    s2 = BeaconStore(str(tmp_path / "beacons.db"))
    titles = [b.title for b in s2.list_beacons()]
    assert "Before" in titles
    assert "After" not in titles


def test_restore_backup_rejects_traversal(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    assert ctrl.restore_backup("../../etc/evil") is False
    assert ctrl.restore_backup("nonexistent.db") is False


def test_history_empty_then_populated(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    assert ctrl.history() == []
    ctrl.save_config(SyncConfig(transport="folder", folder=str(tmp_path / "r"), device="d"))
    ctrl.setup_vault("p")
    _seed(s, "H")
    ctrl.sync_now()
    h = ctrl.history()
    assert len(h) >= 1
    assert h[-1]["message"] == "sync"


def test_request_magic_link_no_server(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.request_magic_link("a@b.com")
    assert "error" in res


def test_verify_magic_link_mocked(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="server", server_url="http://x", device="d"))

    def fake_verify(base_url, token, device="device", session=None):
        return {"device_id": "dev1", "device_token": "tok123", "account": "user@example.com"}

    with patch(
        "quill.apps.beacon.server_client.ServerClient.verify_magic_link", staticmethod(fake_verify)
    ):
        res = ctrl.verify_magic_link("tok", "d")
    assert res["device_token"] == "tok123"
    assert ctrl.config.device_token == "tok123"
    assert ctrl.config.account == "user@example.com"


# -- conflict review (PRD 23.5, 45.6) ----------------------------------------


class _FakeConflict:
    def __init__(self, eid, field, local, remote, merged, message="note conflict"):
        self.entity_id = eid
        self.field = field
        self.local = local
        self.remote = remote
        self.merged = merged
        self.message = message


def test_persist_and_list_conflicts(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    b = _seed(s, "C")
    cf = _FakeConflict(b.beacon_id, "note", "old note", "new note", "old note\nnew note")
    ctrl._persist_conflicts([cf])
    listed = ctrl.list_conflicts(resolved=False)
    assert len(listed) == 1
    assert listed[0]["entity_id"] == b.beacon_id
    assert listed[0]["local"] == "old note"


def test_persist_dedupes_unresolved(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    b = _seed(s, "C")
    cf = _FakeConflict(b.beacon_id, "note", "a", "b", "a\nb")
    ctrl._persist_conflicts([cf])
    ctrl._persist_conflicts([cf])  # same entity/field, still unresolved
    assert len(ctrl.list_conflicts()) == 1


def test_resolve_conflict_applies_choice(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    b = _seed(s, "C")
    s.get_beacon(b.beacon_id)  # ensure exists
    ctrl._persist_conflicts([
        _FakeConflict(b.beacon_id, "note", "local note", "remote note", "merged note")
    ])
    cid = ctrl.list_conflicts()[0]["id"]
    res = ctrl.resolve_conflict(cid, "remote")
    assert res["ok"]
    assert s.get_beacon(b.beacon_id).note == "remote note"
    # Marked resolved -> no longer in unresolved list.
    assert ctrl.list_conflicts(resolved=False) == []
    assert len(ctrl.list_conflicts(resolved=True)) == 1


def test_resolve_conflict_bad_choice(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.resolve_conflict("cf_0", "garbage")
    assert "error" in res


def test_resolve_conflict_missing(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.resolve_conflict("cf_99", "local")
    assert "error" in res


# -- cross-device vault pairing (PRD 45.7) -----------------------------------


def test_export_pairing_requires_vault(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.export_vault_pairing()
    assert "error" in res


def test_pairing_roundtrip_shares_vault(tmp_path):
    # Device A sets up a vault; device B imports A's salt and unlocks with the
    # same passphrase -> both derive the same vault key.
    sA, cA = _store_and_ctrl(tmp_path / "A")
    cA.setup_vault("shared secret")
    code = cA.export_vault_pairing()["pairing_code"]
    assert code == cA.config.salt_b64

    sB, cB = _store_and_ctrl(tmp_path / "B")
    res = cB.import_vault_pairing(code)
    assert res["ok"]
    assert cB.config.salt_b64 == cA.config.salt_b64
    cB.unlock("shared secret")
    assert cB.is_unlocked()
    # Same salt + same passphrase -> same key bytes.
    assert cB._vault.key == cA._vault.key


def test_import_pairing_rejects_garbage(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    res = ctrl.import_vault_pairing("not!! valid!! b64@@")
    assert "error" in res
    res = ctrl.import_vault_pairing("   ")
    assert "error" in res


# -- server hints (PRD 45.5) --------------------------------------------------


def test_fetch_hints_off_returns_error(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    assert "error" in ctrl.fetch_hints()


def test_fetch_hints_mocked(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(
        SyncConfig(transport="server", server_url="http://x", device="d", device_token="tok")
    )

    def fake_hints(self):
        return {"new": 3}

    with patch("quill.apps.beacon.server_client.ServerClient.hints", fake_hints):
        res = ctrl.fetch_hints()
    assert res == {"new": 3}


def test_fetch_hints_unreachable_is_safe(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(
        SyncConfig(transport="server", server_url="http://x", device="d", device_token="tok")
    )

    def boom(self):
        raise RuntimeError("connection refused")

    with patch("quill.apps.beacon.server_client.ServerClient.hints", boom):
        res = ctrl.fetch_hints()
    assert "error" in res


# -- incremental sync commits (PRD 45.8) -------------------------------------


def _folder_ctrl(store, tmp_path, name, remote):
    c = SyncController(store, tmp_path / name)
    c.save_config(SyncConfig(transport="folder", folder=str(remote), device=name))
    c.setup_vault("pass")
    return c


def test_incremental_first_sync_commits_all(tmp_path):
    remote = tmp_path / "remote"
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(remote), device="d"))
    ctrl.setup_vault("pass")
    _seed(s, "A")
    _seed(s, "B")
    _seed(s, "C")
    res = ctrl.sync_now()
    assert res.get("ok"), res
    assert res["committed"] == 3
    # All dirty flags cleared after commit.
    assert s.dirty_beacon_ids() == []


def test_incremental_second_sync_commits_nothing(tmp_path):
    remote = tmp_path / "remote"
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(remote), device="d"))
    ctrl.setup_vault("pass")
    _seed(s, "A")
    _seed(s, "B")
    ctrl.sync_now()
    res = ctrl.sync_now()
    assert res.get("ok"), res
    assert res["committed"] == 0


def test_incremental_edits_commit_only_changed(tmp_path):
    remote = tmp_path / "remote"
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(remote), device="d"))
    ctrl.setup_vault("pass")
    b1 = _seed(s, "A")
    _seed(s, "B")
    ctrl.sync_now()
    # Edit only b1.
    b1.note = "changed"
    s.put_beacon(b1)
    assert s.dirty_beacon_ids() == [b1.beacon_id]
    res = ctrl.sync_now()
    assert res["committed"] == 1


def test_incremental_permanent_delete_tombstones(tmp_path):
    remote = tmp_path / "remote"
    s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.save_config(SyncConfig(transport="folder", folder=str(remote), device="d"))
    ctrl.setup_vault("pass")
    b1 = _seed(s, "A")
    _seed(s, "B")
    ctrl.sync_now()
    s.delete_permanent(b1.beacon_id)
    assert s.tombstone_ids() == [b1.beacon_id]
    res = ctrl.sync_now()
    assert res["committed"] == 1
    # Tombstone cleared once committed.
    assert s.tombstone_ids() == []


def test_incremental_delete_propagates_to_second_device(tmp_path):
    remote = tmp_path / "remote"
    s1 = BeaconStore(str(tmp_path / "d1.db"))
    c1 = _folder_ctrl(s1, tmp_path, "d1dir", remote)
    b = _seed(s1, "Alpha")
    c1.sync_now()

    s2 = BeaconStore(str(tmp_path / "d2.db"))
    c2 = _folder_ctrl(s2, tmp_path, "d2dir", remote)
    c2.config.salt_b64 = c1.config.salt_b64
    c2.save_config(c2.config)
    c2.unlock("pass")
    c2.sync_now()
    assert "Alpha" in [x.title for x in s2.list_beacons()]

    # Delete on d1, sync, then d2 pulls the tombstone.
    s1.delete_permanent(b.beacon_id)
    c1.sync_now()
    c2.sync_now()
    assert "Alpha" not in [x.title for x in s2.list_beacons()]


def test_put_beacon_touch_false_no_dirty(tmp_path):
    s, ctrl = _store_and_ctrl(tmp_path)
    b = _seed(s, "A")
    s.clear_dirty([b.beacon_id])
    b.note = "remote apply"
    b.dirty = 0  # mirror the sync apply path (put_record forces dirty=0)
    s.put_beacon(b, touch=False)
    assert s.dirty_beacon_ids() == []


def test_migrate_v1_to_v2_adds_columns(tmp_path):
    """A library created under schema v1 migrates to v2 on open."""
    import sqlite3

    from quill.apps.beacon.db import BeaconStore

    db_path = str(tmp_path / "v1.db")
    raw = sqlite3.connect(db_path)
    raw.executescript("""
        CREATE TABLE schema_meta (key TEXT PRIMARY KEY, value TEXT);
        INSERT INTO schema_meta VALUES('version','1');
        CREATE TABLE beacons (
            beacon_id TEXT PRIMARY KEY, resource_id TEXT NOT NULL,
            title TEXT NOT NULL DEFAULT '', note TEXT NOT NULL DEFAULT '',
            favorite INTEGER NOT NULL DEFAULT 0, in_inbox INTEGER NOT NULL DEFAULT 1,
            archived INTEGER NOT NULL DEFAULT 0, trashed INTEGER NOT NULL DEFAULT 0,
            date_added INTEGER NOT NULL, last_opened INTEGER,
            open_count INTEGER NOT NULL DEFAULT 0, privacy TEXT NOT NULL DEFAULT 'private',
            health TEXT NOT NULL DEFAULT 'available', capture_source TEXT NOT NULL DEFAULT 'manual',
            version INTEGER NOT NULL DEFAULT 1
        );
        INSERT INTO beacons(beacon_id, resource_id, title, date_added)
            VALUES('bcn_old','res_old','Legacy',1700000000);
    """)
    raw.commit()
    raw.close()
    s = BeaconStore(db_path)
    cols = {r["name"] for r in s.conn.execute("PRAGMA table_info(beacons)")}
    assert "updated" in cols and "dirty" in cols
    # backfilled updated from date_added, dirty defaults to 0.
    row = s.conn.execute("SELECT updated, dirty FROM beacons WHERE beacon_id='bcn_old'").fetchone()
    assert row["updated"] == 1700000000
    assert row["dirty"] == 0
    # tombstones table exists.
    s.conn.execute("SELECT COUNT(*) FROM beacon_tombstones").fetchone()
    s.close()


# -- auto-sync config (PRD 45.10; off by default) ---------------------------


def test_auto_sync_default_off(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    assert ctrl.config.auto_sync_seconds == 0


def test_auto_sync_persists(tmp_path):
    _s, ctrl = _store_and_ctrl(tmp_path)
    ctrl.config.auto_sync_seconds = 900
    ctrl.save_config(ctrl.config)
    ctrl2 = SyncController(_s, tmp_path)
    assert ctrl2.config.auto_sync_seconds == 900


def test_auto_sync_from_dict_coerces(tmp_path):
    cfg = SyncConfig.from_dict({"auto_sync_seconds": "600"})
    assert cfg.auto_sync_seconds == 600
    cfg2 = SyncConfig.from_dict({})
    assert cfg2.auto_sync_seconds == 0
