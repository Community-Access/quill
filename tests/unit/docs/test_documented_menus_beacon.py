"""GATE-DOCMENU for Quill Beacon: what its changelog and guide promise is on its menus.

Builds the real :class:`~quill.apps.beacon.app.BeaconFrame` menu bar in memory,
over an empty data folder, and reads ``standalone/beacon/CHANGELOG.md`` and the
guide a user is given (``standalone/beacon/docs/USER-GUIDE-QuillSync.md``)
against it with the shared reader in ``menu_claims``. The PRD and the two PLAN
documents are design records, not things a listener follows with the app open,
and no other app's gate reads its PRD either.

Beacon is a plain ``wx.Frame``, not an ``AppShellFrame``, so
``_app_menu_bar.real_menu_bar`` cannot build it; this test closes the same
machine doors by hand instead, which is why it needs no ``machine_global`` mark:

* the localhost capture bridge (a listening socket) is not started;
* no tray icon is put in the notification area;
* the auto-sync timer is not created, and nothing deferred runs
  (``CallAfter`` / ``CallLater``);
* the announcer keeps its status-bar half and never reaches the screen
  reader, and the app-sound router is not pointed at any sound card.

None of that changes which menu rows exist: every row is appended in
``BeaconFrame._build_menu``, which runs unchanged.
"""

from __future__ import annotations

import pytest

from tests.unit.docs.menu_claims import (
    ROOT,
    check_documents,
    chord_identity,
    items_from_wx_menu_bar,
)

wx = pytest.importorskip("wx")

DOCS = [
    ROOT / "standalone" / "beacon" / "CHANGELOG.md",
    ROOT / "standalone" / "beacon" / "docs" / "USER-GUIDE-QuillSync.md",
]

#: Finding key -> why it is allowed. Empty: every finding so far was a document
#: to correct.
ALLOW: dict[str, str] = {}

#: Keys Quill Beacon binds with no menu row of its own, on purpose.
EXTRA_KEYS: dict[str, str] = {}


def _beacon_menu_items(monkeypatch: pytest.MonkeyPatch, data_dir) -> list:  # type: ignore[no-untyped-def]
    import quill.apps.beacon.app as beacon_app
    from quill.apps.beacon.announce import Announcer

    class _StatusBarOnly(Announcer):
        """The status-bar half of Beacon's announcer; nothing is spoken."""

        def _speak(self, *_args, **_kwargs) -> None:  # type: ignore[no-untyped-def]
            return None

    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    monkeypatch.setenv("QUILLBEACON_DATA", str(data_dir))
    monkeypatch.setattr(beacon_app, "Announcer", _StatusBarOnly)
    monkeypatch.setattr(beacon_app, "init_app_sound", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.app_sounds, "apply", lambda *_a, **_k: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_capture_bridge", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_start_tray", lambda self: None)
    monkeypatch.setattr(beacon_app.BeaconFrame, "_setup_auto_sync", lambda self: None)
    monkeypatch.setattr(wx, "CallAfter", lambda *_a, **_k: None)
    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
    app = wx.App.Get() or wx.App(False)
    frame = beacon_app.BeaconFrame()
    try:
        return items_from_wx_menu_bar(frame.GetMenuBar())
    finally:
        frame.store.close()
        frame.Destroy()
        del app


def test_beacon_documents_promise_only_what_the_menus_show(
    quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _beacon_menu_items(monkeypatch, quill_data_dir)
    tops = {item.path[0] for item in items if len(item.path) == 1}
    assert {"&File", "&Edit", "&View", "&Media", "&Tools", "&Sync", "&Assist", "&Help"} <= tops, (
        tops
    )
    # One key, one row: a key shown twice means one of the pair never fires.
    keys = [chord_identity(item.key) for item in items if item.key]
    assert sorted({k for k in keys if keys.count(k) > 1}) == []
    findings, used = check_documents(DOCS, items, ALLOW, extra_keys=EXTRA_KEYS)
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
