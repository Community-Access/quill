"""Source-contract test for CopyTrayDialog (#323, #329).

The live ``wx.Dialog`` is not runtime-instantiated in tests; the repo validates
dialog wiring through source contracts (see ``test_session_browser.py``).
"""

from __future__ import annotations

from pathlib import Path

SOURCE = (Path(__file__).resolve().parents[3] / "quill" / "ui" / "copy_tray_dialog.py").read_text(
    encoding="utf-8"
)


def test_listbox_name_is_set_once_and_stays_stable() -> None:
    assert SOURCE.count('self._listbox.SetName("Copy tray slots")') == 1
    assert "self._listbox.SetName(f" not in SOURCE


def test_ephemeral_status_uses_dedicated_static_text() -> None:
    assert 'self._status_label = wx.StaticText(self.dialog, label="")' in SOURCE
    assert "self._status_label.SetLabel(msg)" in SOURCE
    assert "self._announce(msg)" in SOURCE
    for fragment in (
        'self._set_status(f"Slot {n}{label_part}{pin_part} loaded")',
        'self._set_status(f"Pasted from system clipboard to slot {n}{label_part}")',
        'self._set_status(f"Slot {n} saved{label_part}")',
        'self._set_status(f"Slot {n} cleared")',
        'self._set_status(f"Slot {n} {state}")',
    ):
        assert fragment in SOURCE


def test_accepts_optional_announce_cb() -> None:
    assert "announce_cb: Callable[[str], None] | None = None" in SOURCE
    assert "self._announce = announce_cb or (lambda _msg: None)" in SOURCE


def test_show_delegates_to_show_modal_dialog() -> None:
    assert "from quill.ui.dialog_contract import show_modal_dialog" in SOURCE
    assert 'return show_modal_dialog(self.dialog, "Copy Tray")' in SOURCE
