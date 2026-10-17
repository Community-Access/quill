"""GATE-DOCMENU for Quill Inkwell: what its changelog and guide promise is on its menus.

Builds the real Quill Inkwell menu bar in memory, with the empty data folder a
new install starts from, and reads ``standalone/inkwell/docs/CHANGELOG.md`` and
``userguide.md`` against it with the shared reader in ``menu_claims``.

Not ``machine_global``: the frame is built in Safe Mode, which never installs
the keyboard hook, and a new install has no show/hide, Quick Insert, Expand
Word or Dictate Anywhere key, so nothing is registered system-wide -- the same
way ``tests/unit/apps/test_inkwell_preference_persistence.py`` builds it.
"""

from __future__ import annotations

import pytest

from tests.unit.docs.menu_claims import ROOT, check_documents, items_from_wx_menu_bar

wx = pytest.importorskip("wx")

DOCS = ROOT / "standalone" / "inkwell" / "docs"

#: Finding key -> why it is allowed. Empty: every finding so far was a document
#: to correct.
ALLOW: dict[str, str] = {}

#: Keys Quill Inkwell binds with no menu row of its own, on purpose.
EXTRA_KEYS: dict[str, str] = {}


def test_inkwell_documents_promise_only_what_the_menus_show(
    quill_data_dir, monkeypatch: pytest.MonkeyPatch
) -> None:
    # A released build's menus: QUILL_DEV_BUILD=1 would add the gated apps to
    # the QuillVille menu, which a new user never sees.
    monkeypatch.delenv("QUILL_DEV_BUILD", raising=False)
    from quill.apps.inkwell import QuillInkwellFrame

    app = wx.App(False)
    frame = QuillInkwellFrame(safe_mode=True)
    try:
        items = items_from_wx_menu_bar(frame.frame.GetMenuBar())
    finally:
        frame._preference_saver.flush()
        frame._task_manager.shutdown(wait=True)
        timer = getattr(frame, "_ipc_timer", None)
        if timer is not None:
            timer.Stop()
        frame._remove_tray_icon()
        frame.frame.Destroy()
        app.Destroy()
    findings, used = check_documents(
        [DOCS / "CHANGELOG.md", DOCS / "userguide.md"], items, ALLOW, extra_keys=EXTRA_KEYS
    )
    assert findings == [], "\n".join(findings)
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
