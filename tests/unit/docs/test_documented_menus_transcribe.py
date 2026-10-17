"""GATE-DOCMENU for QUILL Transcribe: what its documents promise, its menus keep.

Built from the real :class:`~quill.apps.transcribe.QuillTranscribeFrame` over an
empty data folder with the release gate closed, so the menu bar is the one a new
install shows (``_app_menu_bar``). Every menu path the changelog, the guide and
the 1.0 release notes write must exist, and every command they name beside a
key must be on that key in the menus.

The 2026-10-16 pass found the start and stop key taught as "Dictation > Start
and Stop Key" in the changelog and the release notes, and spoken that way by the
app itself when the key was taken; the row has always been in the File menu.

Nothing here registers a hotkey, opens a tray icon or reaches the screen reader:
``_app_menu_bar`` replaces those before the frame is built.
"""

from __future__ import annotations

import pytest

from tests.unit.docs._app_menu_bar import real_menu_bar
from tests.unit.docs.menu_claims import ROOT, check_documents

DOCS = [
    ROOT / "standalone" / "transcribe" / "docs" / "CHANGELOG.md",
    ROOT / "standalone" / "transcribe" / "docs" / "userguide.md",
    ROOT / "standalone" / "transcribe" / "docs" / "release-notes-1.0.md",
]

#: Findings allowed on purpose, each with its reason. Empty: fix the document.
ALLOW: dict[str, str] = {}

#: Keys bound outside the menu bar on purpose, named as the documents name them.
EXTRA_KEYS = {
    # The Review Dictation window's own accelerator table
    # (quill/ui/dictation_review_frame.py); the main window has no such rows.
    "Ctrl+Enter": "Insert",
    "Ctrl+P": "Polish",
}


def test_transcribe_documents_promise_only_what_its_menus_show(
    quill_data_dir, monkeypatch, request
) -> None:  # type: ignore[no-untyped-def]
    pytest.importorskip("wx")
    with real_menu_bar(
        monkeypatch, request, "quill.apps.transcribe", "QuillTranscribeFrame"
    ) as items:
        assert any(item.path[-1] == "&File" for item in items), "no File menu was built"
        findings, used = check_documents(DOCS, items, ALLOW, extra_keys=EXTRA_KEYS)
        # The gate is looking: the path the documents used to teach is caught.
        stale = quill_data_dir / "stale.md"
        stale.write_text("Change it in Dictation > Start and Stop Key.\n", encoding="utf-8")
        caught, _ = check_documents([stale], items, {})
    assert findings == []
    assert caught == ["stale.md:1: no menu path 'dictation > start and stop key'"]
    assert used == set(ALLOW), f"stale allowlist entries: {sorted(set(ALLOW) - used)}"
