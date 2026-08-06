"""Tests for LibraryMixin: the Book Library command wired onto MainFrame.

Regression for #1318: the dialog must be parented on the wx frame
(``self.frame``), not on the MainFrame controller object — passing the
controller raises ``TypeError: Dialog(): arguments did not match any
overloaded call`` the moment the dialog is constructed.
"""

from __future__ import annotations

from pathlib import Path

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

    def _show_modal_dialog(self, dialog: object) -> int:
        self.shown.append(dialog)
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
    assert host.shown, "the dialog goes through _show_modal_dialog"
