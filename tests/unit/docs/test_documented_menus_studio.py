"""GATE-DOCMENU for QUILL Audio Studio: what its documents promise, its menus keep.

Built from the real :class:`~quill.apps.studio.StudioAppFrame` over an empty data
folder with the release gate closed (``_app_menu_bar``). Every menu path the
changelog and the guide write must exist, and every command they name beside a
key must be on that key in the menus.

The 2026-10-16 pass found **App Sounds Play On...** written as a submenu of
Preferences ("Studio > Preferences > App Sounds Play On..."); it is a button in
the Preferences window. It also found the guide's keyboard reference giving the
Voices menu Alt+V, which opens View; that table is not a shape this gate reads,
so it was fixed by hand.
"""

from __future__ import annotations

import pytest

from tests.unit.docs._app_menu_bar import real_menu_bar
from tests.unit.docs.menu_claims import ROOT, check_documents

DOCS = [
    ROOT / "standalone" / "studio" / "docs" / "CHANGELOG.md",
    ROOT / "standalone" / "studio" / "docs" / "userguide.md",
]

#: Findings allowed on purpose, each with its reason. Empty: fix the document.
ALLOW: dict[str, str] = {}


def test_studio_documents_promise_only_what_its_menus_show(
    quill_data_dir, monkeypatch, request
) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("wx")
    with real_menu_bar(monkeypatch, request, "quill.apps.studio", "StudioAppFrame") as items:
        tops = {item.path[0] for item in items}
        assert {"&Studio", "Vo&ices", "&View"} <= tops, tops
        findings, used = check_documents(DOCS, items, ALLOW)
    assert findings == []
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
