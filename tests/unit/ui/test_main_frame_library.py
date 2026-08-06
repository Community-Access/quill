"""Tests for LibraryMixin: the Book Library command wired onto MainFrame.

Regression for #1318: the dialog must be parented on the wx frame
(``self.frame``), not on the MainFrame controller object — passing the
controller raises ``TypeError: Dialog(): arguments did not match any
overloaded call`` the moment the dialog is constructed.
"""

from __future__ import annotations

from pathlib import Path

import pytest  # type: ignore[import-not-found]

from quill.ui.main_frame_library import LibraryMixin


class _Frame:
    """Stands in for the wx.Frame the dialog must be parented on."""


class _Host(LibraryMixin):
    def __init__(self) -> None:
        self.frame = _Frame()
        self.shown: list[object] = []
        self.opened: list[Path] = []
        self.announced: list[str] = []

    def _announce(self, message: str) -> None:
        self.announced.append(message)

    def open_file(self, path: Path) -> None:
        self.opened.append(path)

    def _show_modal_dialog(
        self, dialog: object, label: str, *, restore_editor_focus: bool = True
    ) -> int:
        # Mirror MainFrame._show_modal_dialog's real signature exactly — the
        # first regression (#1325) hid behind a stub that accepted fewer args.
        self.shown.append((dialog, label))
        return 0


class _DialogProbe:
    """Records the constructor call in place of the real wx dialog."""

    calls: list[tuple[object, dict[str, object]]] = []

    def __init__(self, parent, **kwargs) -> None:
        _DialogProbe.calls.append((parent, kwargs))

    def Destroy(self) -> None:
        pass


def test_library_dialog_is_parented_on_the_frame(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)
    monkeypatch.setattr("quill.ui.main_frame_library.LibraryDialog", _DialogProbe)
    _DialogProbe.calls.clear()

    host = _Host()
    host.open_library_dialog()

    assert len(_DialogProbe.calls) == 1
    parent, kwargs = _DialogProbe.calls[0]
    assert parent is host.frame, "dialog parent must be the wx frame, not the controller (#1318)"
    assert kwargs["dest_dir"] == tmp_path / "library"
    assert len(host.shown) == 1
    assert host.shown[0][1] == "Book Library", "_show_modal_dialog gets the label (#1325)"


def test_open_library_dialog_end_to_end_with_real_widgets(tmp_path: Path, monkeypatch) -> None:
    """Run the whole command with the real wx dialog — no dialog stub.

    Both field crashes in this path (#1318 wrong parent type, #1325 missing
    _show_modal_dialog label) only reproduce with the genuine constructor and
    call signature, so this test deliberately builds the real LibraryDialog.
    """
    wx = pytest.importorskip("wx")
    monkeypatch.setattr("quill.core.paths.app_data_dir", lambda: tmp_path)

    app = wx.App()
    try:
        host = _Host()
        host.frame = wx.Frame(None)
        try:
            host.open_library_dialog()
            assert len(host.shown) == 1
            dialog, label = host.shown[0]
            assert label == "Book Library"
            assert dialog.GetParent() is host.frame
        finally:
            host.frame.Destroy()
    finally:
        app.Destroy()
