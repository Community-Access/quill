"""The shared Recent Documents window, on a real wx dialog.

Its verbs are methods so they can be pressed here without a modal loop. What is
asserted is what each one does to the two lists and what it says, because those
are what both editors save and what a listener hears.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import wx

from quill.ui import recent_documents_dialog as dialog_mod
from quill.ui.recent_documents_dialog import RecentDocumentsWindow


@pytest.fixture
def app():
    existing = wx.GetApp()
    return existing if existing is not None else wx.App()


@pytest.fixture
def files(tmp_path: Path) -> list[str]:
    paths = []
    for name in ("one.txt", "two.md", "three.rtf"):
        target = tmp_path / name
        target.write_text("x", encoding="utf-8")
        paths.append(str(target))
    return paths


def _window(recent, pinned=(), *, confirm=True, reveal=None, said=None):
    asked: list[tuple[int, int]] = []

    def _confirm(_parent, removed, kept):
        asked.append((removed, kept))
        return confirm

    window = RecentDocumentsWindow(
        None,
        recent,
        pinned,
        limit=10,
        auto_clear_missing=False,
        announce=(said.append if said is not None else None),
        confirm_clear=_confirm,
        reveal=(reveal.append if reveal is not None else (lambda _p: None)),
    )
    window.asked = asked  # type: ignore[attr-defined]
    return window


def _close(window: RecentDocumentsWindow) -> None:
    window.dialog.Destroy()


def test_open_returns_the_row_you_are_on(app, files) -> None:
    window = _window(files)
    try:
        window.listbox.SetSelection(1)
        assert window.open_selected() is True
        assert window.answer().open_path == files[1]
    finally:
        _close(window)


def test_a_missing_file_cannot_be_opened_and_says_why(app, files, tmp_path) -> None:
    said: list[str] = []
    gone = str(tmp_path / "gone.txt")
    window = _window([gone, *files], said=said)
    try:
        assert window.listbox.GetString(0).endswith("not found")
        assert window.open_selected() is False
        assert window.answer().open_path == ""
        assert "no longer in" in said[-1]
    finally:
        _close(window)


def test_pin_moves_a_document_to_the_top_and_unpin_puts_it_back(app, files) -> None:
    said: list[str] = []
    window = _window(files, said=said)
    try:
        window.listbox.SetSelection(2)
        window.toggle_pin_selected()
        assert window.pinned == [files[2]]
        assert window.listbox.GetSelection() == 0
        assert window.listbox.GetString(0).endswith("pinned")
        assert window.pin_button.GetLabel() == "Un&pin"
        assert said[-1] == "Pinned three.rtf."
        window.toggle_pin_selected()
        assert window.pinned == []
        assert said[-1] == "Unpinned three.rtf."
        assert window.answer().changed is True
    finally:
        _close(window)


def test_remove_takes_the_row_off_and_leaves_the_file(app, files) -> None:
    window = _window(files, pinned=[files[0]])
    try:
        window.listbox.SetSelection(0)
        window.remove_selected()
        answer = window.answer()
        assert files[0] not in answer.recent
        assert answer.pinned == ()
        assert Path(files[0]).is_file()
    finally:
        _close(window)


def test_clear_asks_first_and_no_keeps_the_list(app, files) -> None:
    window = _window(files, confirm=False)
    try:
        window.clear()
        assert window.asked == [(3, 0)]
        assert window.answer().recent == tuple(files)
        assert window.answer().changed is False
    finally:
        _close(window)


def test_clear_keeps_pinned_documents(app, files) -> None:
    said: list[str] = []
    window = _window(files, pinned=[files[1]], said=said)
    try:
        window.clear()
        assert window.asked == [(2, 1)]
        answer = window.answer()
        assert answer.recent == (files[1],)
        assert answer.pinned == (files[1],)
        assert said[-1] == "Cleared 2 recent documents. 1 pinned document stays."
    finally:
        _close(window)


def test_open_containing_folder_reveals_the_file(app, files) -> None:
    shown: list[str] = []
    window = _window(files, reveal=shown)
    try:
        window.listbox.SetSelection(0)
        window.open_folder_selected()
        assert shown == [files[0]]
    finally:
        _close(window)


def test_the_limit_trims_the_list_on_the_way_out(app, files) -> None:
    window = _window(files)
    try:
        window.limit_spin.SetValue(2)
        window.auto_clear.SetValue(True)
        answer = window.answer()
        assert answer.limit == 2
        assert answer.recent == tuple(files[:2])
        assert answer.auto_clear_missing is True
        assert answer.changed is True
    finally:
        _close(window)


def test_an_empty_list_says_so_and_offers_nothing(app) -> None:
    window = _window([])
    try:
        assert window.listbox.GetString(0) == "No recent documents"
        assert not window.open_button.IsEnabled()
        assert not window.clear_button.IsEnabled()
        assert window.open_selected() is False
    finally:
        _close(window)


def test_the_confirmation_defaults_to_no(app, monkeypatch) -> None:
    seen: dict[str, int] = {}

    class _Message:
        def __init__(self, _parent, message, caption, style) -> None:
            seen["style"] = style
            seen["message"] = message

        def Destroy(self) -> None:  # noqa: N802 - wx API shape
            seen["destroyed"] = 1

    monkeypatch.setattr(dialog_mod.wx, "MessageDialog", _Message)
    monkeypatch.setattr(dialog_mod, "show_modal_dialog", lambda _d, _l: wx.ID_NO)
    assert dialog_mod.confirm_clear_recent(None, 3, 1) is False
    assert seen["style"] & wx.NO_DEFAULT
    assert "Pinned documents stay" in seen["message"]
    assert seen["destroyed"] == 1
