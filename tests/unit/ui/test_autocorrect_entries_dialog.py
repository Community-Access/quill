"""The AutoCorrect Entries window, in memory: rows, filter, and the four actions.

Built for real (wx, no window shown, no input sent); the edit prompt is the
injectable seam, answered here, so every action is reached without a modal.
"""

from __future__ import annotations

import pytest

from quill.core.abbreviations import AbbreviationLibrary
from quill.core.autocorrect import lookup
from tests.wx_session import shared_wx_app

wx = pytest.importorskip("wx")


@pytest.fixture(scope="module")
def wx_app():
    app = shared_wx_app()
    # SetHelpText stores nothing without a help provider (CLAUDE.md, F1).
    wx.HelpProvider.Set(wx.SimpleHelpProvider())
    yield app


class _Prompt:
    """Answers the edit window with whatever the test queued."""

    def __init__(self, *answers: object) -> None:
        self.answers = list(answers)
        self.asked: list[tuple[str, str, bool]] = []

    def __call__(self, _parent: object, word: str, fixed: str, case: bool) -> object:
        self.asked.append((word, fixed, case))
        return self.answers.pop(0) if self.answers else None


def _dialog(prompt: _Prompt | None = None):
    from quill.ui.autocorrect_entries_dialog import AutocorrectEntriesDialog

    said: list[str] = []
    library = AbbreviationLibrary(version=2, abbreviations=[])
    dialog = AutocorrectEntriesDialog(None, library, announce=said.append, prompt=prompt)
    return dialog, library, said


def _select(dialog, word: str) -> None:
    dialog.filter.SetValue(word)
    dialog.refresh(keep=word)


def test_every_control_answers_f1_and_the_list_lists_the_built_in_corrections(wx_app) -> None:
    dialog, _library, _said = _dialog()
    try:
        assert dialog.dialog.GetTitle() == "AutoCorrect Entries"
        for control in (
            dialog.filter,
            dialog.list,
            dialog.add_button,
            dialog.edit_button,
            dialog.toggle_button,
            dialog.remove_button,
        ):
            assert control.GetHelpText()
        rows = [dialog.list.GetString(i) for i in range(dialog.list.GetCount())]
        assert "teh becomes the, built in" in rows
        assert dialog.changed is False
    finally:
        dialog.close()


def test_the_filter_narrows_by_either_side(wx_app) -> None:
    dialog, _library, _said = _dialog()
    try:
        dialog.filter.SetValue("receive")
        rows = [dialog.list.GetString(i) for i in range(dialog.list.GetCount())]
        assert rows and all("receiv" in row for row in rows)
    finally:
        dialog.close()


def test_add_edit_turn_off_turn_on_and_remove(wx_app) -> None:
    prompt = _Prompt(("qill", "QUILL", False), ("qill", "Quill", False))
    dialog, library, said = _dialog(prompt)
    try:
        dialog.add()
        assert said[-1] == "Added: qill becomes QUILL"
        assert dialog.selected().typed == "qill"
        dialog.edit_selected()
        assert prompt.asked[-1] == ("qill", "QUILL", False)
        assert lookup(library, "qill").replacement == "Quill"

        dialog.toggle_selected()
        assert said[-1] == "Turned off: qill will no longer be corrected"
        assert dialog.toggle_button.GetLabel() == "Turn O&n"
        dialog.toggle_selected()
        assert lookup(library, "qill").active is True
        assert dialog.toggle_button.GetLabel() == "Turn &Off"

        dialog.remove_selected()
        assert said[-1] == "Removed qill"
        assert lookup(library, "qill") is None
        assert dialog.changed is True
    finally:
        dialog.close()


def test_a_built_in_correction_is_turned_off_rather_than_removed(wx_app) -> None:
    dialog, library, said = _dialog()
    try:
        _select(dialog, "teh")
        assert dialog.selected().typed == "teh"
        dialog.remove_selected()
        assert "cannot be removed" in said[-1]
        assert lookup(library, "teh").active is False
        dialog.remove_selected()
        assert said[-1] == "Restored the built-in correction: teh becomes the"
        assert lookup(library, "teh").active is True
        assert library.abbreviations == []
    finally:
        dialog.close()


def test_changing_a_built_in_one_and_putting_it_back(wx_app) -> None:
    prompt = _Prompt(("teh", "tea", False))
    dialog, library, said = _dialog(prompt)
    try:
        _select(dialog, "teh")
        dialog.edit_selected()
        assert lookup(library, "teh").replacement == "tea"
        assert "changed by you" in dialog.list.GetString(dialog.list.GetSelection())
        dialog.remove_selected()
        assert said[-1] == "Restored the built-in correction: teh becomes the"
    finally:
        dialog.close()


def test_cancelling_the_edit_window_changes_nothing(wx_app) -> None:
    dialog, library, _said = _dialog(_Prompt())
    try:
        dialog.add()
        assert library.abbreviations == []
        assert dialog.changed is False
    finally:
        dialog.close()


def test_the_edit_window_refuses_a_word_it_cannot_correct(wx_app, monkeypatch) -> None:
    import quill.ui.autocorrect_entries_dialog as module

    told: list[str] = []
    monkeypatch.setattr(module, "show_message_box", lambda message, *_a, **_k: told.append(message))
    edit = module.CorrectionEditDialog(None, "two words", "x")
    try:
        assert edit.word.GetHelpText() and edit.fixed.GetHelpText() and edit.case.GetHelpText()
        edit._on_ok(None)
        assert told and "letters only" in told[0]
        assert edit.answer() == ("two words", "x", False)
    finally:
        edit.dialog.Destroy()
