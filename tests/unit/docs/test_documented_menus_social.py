"""GATE-DOCMENU for QUILL Social: what its changelog and guides promise is on its menus.

Builds the real :class:`quill_social.ui.app.SocialFrame` menu bar in memory,
over an empty data folder (a new install: one workspace and the demo
account), and reads the documents a listener is handed against it with the
shared reader in ``menu_claims``: ``standalone/social/CHANGELOG.md``, the user
guide and the keyboard reference -- the last two are what **Help > User
Guide** and **Help > Keyboard Reference** open. The PRD working draft is a
design record, and no other app's gate reads its PRD either.

QUILL Social's code is the one app that still lives under ``standalone/``
(``standalone/social/quill_social``). The shared venv may also carry an
installed copy of the package; this test imports the worktree's own source,
because that is the code the documents beside it describe, and puts any
previously imported copy back afterwards.

``SocialFrame`` is a plain ``wx.Frame``, not an ``AppShellFrame``, so
``_app_menu_bar.real_menu_bar`` cannot build it. The machine doors are closed
by hand instead, which is why this needs no ``machine_global`` mark: the
announcer gets no speech engine (it would otherwise reach the screen reader
directly), nothing deferred runs (``CallAfter`` / ``CallLater``), credentials
go to an in-memory store rather than the Windows vault, and the scheduler
timer the frame starts is stopped before the frame is destroyed. The demo
account's timeline is local; nothing touches the network.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from tests.unit.docs.menu_claims import (
    ROOT,
    check_documents,
    chord_identity,
    items_from_wx_menu_bar,
)
from tests.wx_session import patch_call_after, shared_wx_app

wx = pytest.importorskip("wx")

SOCIAL = ROOT / "standalone" / "social"
DOCS = [
    SOCIAL / "CHANGELOG.md",
    SOCIAL / "docs" / "USER_GUIDE.md",
    SOCIAL / "docs" / "KEYMAP_SPEC.md",
]

#: Finding key -> why it is allowed. Empty: every finding so far was a document
#: to correct.
ALLOW: dict[str, str] = {}

#: Keys QUILL Social binds with no menu row of its own, on purpose.
EXTRA_KEYS: dict[str, str] = {}


@pytest.fixture
def worktree_quill_social(monkeypatch: pytest.MonkeyPatch):  # type: ignore[no-untyped-def]
    """Import ``quill_social`` from this tree, and restore whatever was there."""
    saved = {n: m for n, m in sys.modules.items() if n.split(".")[0] == "quill_social"}
    for name in saved:
        del sys.modules[name]
    monkeypatch.syspath_prepend(str(SOCIAL))
    try:
        yield
    finally:
        for name in [n for n in sys.modules if n.split(".")[0] == "quill_social"]:
            del sys.modules[name]
        sys.modules.update(saved)


def _social_menu_items(monkeypatch: pytest.MonkeyPatch, data_dir) -> list:  # type: ignore[no-untyped-def]
    import quill_social.ui.app as social_app
    from quill_social.security.credentials import InMemoryCredentialStore
    from quill_social.ui.announce import Announcer

    assert SOCIAL in Path(social_app.__file__).resolve().parents
    monkeypatch.setenv("QUILLSOCIAL_DATA", str(data_dir))
    monkeypatch.setattr(Announcer, "_make_speaker", lambda self: None)
    monkeypatch.setattr(social_app, "_make_credential_store", InMemoryCredentialStore)
    patch_call_after(monkeypatch, lambda *_a, **_k: None)
    monkeypatch.setattr(wx, "CallLater", lambda *_a, **_k: None)
    app = wx.App.Get() or shared_wx_app()
    frame = social_app.SocialFrame()
    try:
        return items_from_wx_menu_bar(frame.GetMenuBar())
    finally:
        frame._closing = True
        frame._sched_timer.Stop()
        frame.store.close()
        frame.Destroy()
        del app


def test_social_documents_promise_only_what_the_menus_show(
    worktree_quill_social, quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    items = _social_menu_items(monkeypatch, quill_data_dir)
    tops = {item.path[0] for item in items if len(item.path) == 1}
    expected = {"&File", "&Compose", "&Item", "Fee&ds", "&Listen", "&Studio", "&Tools", "&Help"}
    assert expected <= tops, tops
    # One key, one row: Find Text and Favourite both showed Ctrl+F until
    # 2026-10-17, and only Favourite ever answered it.
    keys = [chord_identity(item.key) for item in items if item.key]
    assert sorted({k for k in keys if keys.count(k) > 1}) == []
    findings, used = check_documents(DOCS, items, ALLOW, extra_keys=EXTRA_KEYS)
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
