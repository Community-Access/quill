"""GATE-DOCMENU for Quill Media Player: what its guide promises, its menus keep.

Built from the real :class:`~quill.apps.player.QuillMediaPlayerFrame` over an
empty data folder with the release gate closed (``_app_menu_bar``). The player
has no changelog yet, so the guide is the one document read: every menu path it
writes must exist, and every command it names beside a key must be on that key.

The 2026-10-16 pass rewrote much of the guide by hand, because most of what it
promised was not in the shapes this gate reads: a menu bar of ten menus (the
app has seven), single-letter keys nothing binds (``[``, ``]``, M, W), a tray
menu of playback commands (it has Show and Exit), and "no settings window"
beside a File > Preferences... (Ctrl+,) that exists. Keep new promises in the
gate's shapes -- **Menu > Item** and **Name** (**Key**) -- so the next drift is
caught here instead.
"""

from __future__ import annotations

import pytest

from tests.unit.docs._app_menu_bar import real_menu_bar
from tests.unit.docs.menu_claims import ROOT, check_documents

DOCS = [ROOT / "standalone" / "player" / "docs" / "userguide.md"]

#: Findings allowed on purpose, each with its reason. Empty: fix the document.
ALLOW: dict[str, str] = {}


def test_player_guide_promises_only_what_its_menus_show(
    quill_data_dir, monkeypatch, request
) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("wx")
    with real_menu_bar(monkeypatch, request, "quill.apps.player", "QuillMediaPlayerFrame") as items:
        tops = [item.path[0] for item in items if len(item.path) == 1]
        assert tops == [
            "&File",
            "&Navigation",
            "&Playback",
            "&View",
            "A&I",
            "&QuillVille",
            "&Help",
            "&Window",
        ]
        findings, used = check_documents(DOCS, items, ALLOW)
    assert findings == []
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
