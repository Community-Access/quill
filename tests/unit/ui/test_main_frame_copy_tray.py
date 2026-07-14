"""Source-contract test for the Copy Tray slot-search dialog (#330).

The live ``wx.Dialog`` is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts (see ``test_session_browser.py``).
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (
    Path(__file__).resolve().parents[3] / "quill" / "ui" / "main_frame_copy_tray.py"
).read_text(encoding="utf-8")


def test_search_dialog_accepts_announce_fn() -> None:
    assert "announce_fn: Callable[[str], None] | None = None" in SOURCE
    assert "self._announce_fn = announce_fn" in SOURCE


def test_search_dialog_announces_selection_change() -> None:
    assert "self._results.SetSelection(0)" in SOURCE
    assert "self._announce_fn(labels[0])" in SOURCE


def test_search_tray_slots_passes_announce_fn() -> None:
    assert "_TraySearchDialog(self.frame, tray, announce_fn=self._announce)" in SOURCE


def test_open_copy_tray_passes_announce_cb() -> None:
    assert "announce_cb=self._announce" in SOURCE
