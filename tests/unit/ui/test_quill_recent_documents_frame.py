"""QUILL's half of Recent Documents: the window on Alt+Shift+0 and Clear Recent Files.

The shipped mixin on a duck-typed frame, with the shared window patched where
the mixin imports it, and QUILL's stores in a temporary data folder.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from quill.core.recent import load_pinned_recent_files, load_recent_files
from quill.core.settings import Settings
from quill.ui import recent_documents_dialog
from quill.ui.main_frame_recent_documents import RecentDocumentsMixin
from quill.ui.recent_documents_dialog import RecentDocumentsAnswer


class _Frame(RecentDocumentsMixin):
    def __init__(self, recent: list[Path]) -> None:
        self.frame = None
        self.settings = Settings()
        self.recent_files = list(recent)
        self._safe_mode = False
        self.opened: list[Path] = []
        self.status: list[str] = []
        self.said: list[str] = []

    def open_file(self, path: Path) -> None:
        self.opened.append(path)

    def _set_status(self, text: str) -> None:
        self.status.append(text)

    def _announce(self, text: str) -> None:
        self.said.append(text)


@pytest.fixture
def frame(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> _Frame:
    monkeypatch.setenv("QUILL_DATA_DIR", str(tmp_path / "data"))
    files = []
    for name in ("a.txt", "b.txt", "c.txt"):
        target = tmp_path / name
        target.write_text("x", encoding="utf-8")
        files.append(target)
    return _Frame(files)


def test_recent_documents_opens_the_chosen_file(frame: _Frame, monkeypatch) -> None:
    chosen = str(frame.recent_files[2])
    answer = RecentDocumentsAnswer(open_path=chosen, limit=10)
    monkeypatch.setattr(recent_documents_dialog, "show_recent_documents", lambda *a, **k: answer)
    frame.open_recent_documents()
    assert frame.opened == [Path(chosen)]


def test_pins_and_removals_reach_quills_stores(frame: _Frame, monkeypatch) -> None:
    keep = str(frame.recent_files[0])
    answer = RecentDocumentsAnswer(
        recent=(keep,), pinned=(keep,), limit=7, auto_clear_missing=True, changed=True
    )
    monkeypatch.setattr(recent_documents_dialog, "show_recent_documents", lambda *a, **k: answer)
    frame.open_recent_documents()
    assert [str(p) for p in load_recent_files()] == [keep]
    assert load_pinned_recent_files() == [keep]
    assert frame.settings.recent_files_limit == 7
    assert frame.settings.recent_files_auto_clear_missing is True
    assert frame.opened == []


def test_clear_recent_files_asks_and_no_keeps_the_list(frame: _Frame, monkeypatch) -> None:
    asked: list[tuple[int, int]] = []

    def _no(_parent, removed, kept):
        asked.append((removed, kept))
        return False

    monkeypatch.setattr(recent_documents_dialog, "confirm_clear_recent", _no)
    before = list(frame.recent_files)
    frame.clear_recent_files()
    assert asked == [(3, 0)]
    assert frame.recent_files == before


def test_clear_recent_files_keeps_pins(frame: _Frame, monkeypatch) -> None:
    pinned = str(frame.recent_files[1])
    frame._pinned_recent_cache = [pinned]
    monkeypatch.setattr(recent_documents_dialog, "confirm_clear_recent", lambda *_a: True)
    frame.clear_recent_files()
    assert [str(p) for p in frame.recent_files] == [pinned]
    assert frame.status[-1] == "Cleared 2 recent documents. 1 pinned document stays."


def test_open_recent_numbers_rows_pins_first_and_offers_the_window(frame: _Frame) -> None:
    import wx

    app = wx.GetApp() or wx.App()
    assert app is not None
    pinned = str(frame.recent_files[2])
    frame._pinned_recent_cache = [pinned]
    frame._wx = wx
    frame._recent_menu = wx.Menu()
    frame._recent_menu_ids = {}
    frame._id_clear_recent = wx.NewIdRef()
    frame._id_recent_documents = wx.NewIdRef()
    frame._menu_updates_allowed = lambda: True
    frame._reapply_menu_routes = lambda: None
    frame._menu_label = lambda title, _command: f"{title}\tAlt+Shift+0"
    try:
        frame._refresh_recent_menu()
        labels = [item.GetItemLabel() for item in frame._recent_menu.GetMenuItems()]
        assert labels[0].startswith("&1 c.txt") and labels[0].endswith("pinned\tAlt+Shift+1")
        assert labels[1].startswith("&2 a.txt") and labels[1].endswith("\tAlt+Shift+2")
        assert "Recent &Documents...\tAlt+Shift+0" in labels
        assert labels[-1] == "C&lear Recent Files..."
    finally:
        frame._recent_menu.Destroy()
