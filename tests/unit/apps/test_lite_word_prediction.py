"""QUILL Lite's Edit > Word Prediction (quill/apps/lite_window_word_prediction.py),
called the way the menu and the key handler call it, over QUILL's shared list."""

from __future__ import annotations

from types import SimpleNamespace

import wx

from quill.core.lite.parity import COMMAND_EQUIVALENTS


class _FakePopup:
    """The shared popup's surface, without a floating wx window."""

    def __init__(self) -> None:
        self.visible = False
        self.suggestions: list = []
        self.index = 0
        self.status = ""

    def update(self, suggestions, status) -> None:
        self.suggestions, self.status, self.index = list(suggestions), status, 0

    def show(self, _position) -> None:
        self.visible = True

    def hide(self) -> None:
        self.visible = False

    def is_visible(self) -> bool:
        return self.visible

    def selection_index(self) -> int:
        return self.index

    def set_selection(self, index: int) -> None:
        self.index = max(0, min(index, len(self.suggestions) - 1))

    def selected_suggestion(self):
        return self.suggestions[self.index] if self.suggestions else None


def _key(code: int) -> SimpleNamespace:
    return SimpleNamespace(GetKeyCode=lambda: code)


def _window(lite_window, text: str, cursor: int):
    win = lite_window(text, cursor=cursor)
    win._intellisense_popup = _FakePopup()
    win._spell_dictionary = lambda: {"elephant", "elegant", "element"}
    return win


def test_ctrl_period_opens_the_list_and_says_the_count(lite_window) -> None:
    win = _window(lite_window, "An ele", 6)
    win.cmd_word_prediction()
    popup = win._intellisense_popup
    assert popup.visible
    first = popup.suggestions[0].label
    assert win.announcements[-1] == f"{len(popup.suggestions)} prediction(s). {first}"


def test_down_says_the_next_and_enter_inserts_only_the_fragment(lite_window) -> None:
    win = _window(lite_window, "An ele here", 6)
    win.cmd_word_prediction()
    first = win._intellisense_popup.suggestions[0].label
    assert win._word_prediction_key_down(_key(wx.WXK_DOWN))
    second = win._intellisense_popup.suggestions[1].label
    assert win.announcements[-1] == second != first
    assert win._word_prediction_key_down(_key(wx.WXK_RETURN))
    assert win.control.GetValue() == f"An {second} here"
    assert win.control.GetInsertionPoint() == len(f"An {second}")
    assert win.announcements[-1] == f'Inserted prediction "{second}".'
    assert not win._intellisense_popup.visible


def test_escape_closes_the_list_and_never_changes_the_text(lite_window) -> None:
    win = _window(lite_window, "An ele", 6)
    win.cmd_word_prediction()
    assert win._word_prediction_key_down(_key(wx.WXK_ESCAPE))
    assert win.control.GetValue() == "An ele"
    assert win.control.GetInsertionPoint() == 6
    assert not win._intellisense_popup.visible


def test_nothing_to_predict_says_so(lite_window) -> None:
    win = _window(lite_window, "An ", 3)
    win.cmd_word_prediction()
    assert win.announcements[-1] == "No predictions available"
    assert not win._intellisense_popup.visible


def test_keys_pass_through_when_the_list_is_closed(lite_window) -> None:
    win = _window(lite_window, "text", 4)
    assert not win._word_prediction_key_down(_key(wx.WXK_DOWN))
    assert not win._word_prediction_key_down(_key(wx.WXK_RETURN))


def test_typing_with_the_list_open_refreshes_after_the_key(lite_window, monkeypatch) -> None:
    calls: list = []
    monkeypatch.setattr(wx, "CallAfter", lambda fn, *a: calls.append(fn))
    win = _window(lite_window, "An ele", 6)
    win.cmd_word_prediction()
    assert not win._word_prediction_key_down(_key(ord("g")))
    assert calls == [win._refresh_intellisense_popup]


def test_word_prediction_is_quills_command_on_quills_chord() -> None:
    from quill.core.keymap import DEFAULT_KEYMAP
    from quill.core.lite.commands import COMMANDS

    row = next(r for r in COMMANDS if r[3] == "cmd_word_prediction")
    assert row[0] == "&Edit" and row[1] == "&Word Prediction..."
    assert COMMAND_EQUIVALENTS["cmd_word_prediction"] == "edit.word_prediction"
    assert row[2] == DEFAULT_KEYMAP["edit.word_prediction"] == "Ctrl+."
