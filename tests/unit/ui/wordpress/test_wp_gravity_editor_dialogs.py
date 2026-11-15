"""QUILL's Gravity Forms editor and its Field and Condition dialogs, as real wx dialogs (WP-C).

Each test builds the dialog on the session App and calls the handler a button
or key reaches; the nested dialogs are answered by patching the helpers the
editor calls. Nothing is shown modally and no site is called.
"""

from __future__ import annotations

import copy
from typing import Any

import pytest

wx = pytest.importorskip("wx")

from quill.core.wordpress import gravity_build as gb  # noqa: E402
from quill.ui import wordpress_gravity_field_dialogs as fdlg  # noqa: E402
from quill.ui.wordpress_gravity_editor import GravityFormEditor  # noqa: E402

FORM = {
    "id": "1",
    "title": "Signup",
    "button": {"type": "text", "text": "Join", "imageUrl": ""},
    "confirmations": {"c1": {"id": "c1", "isDefault": True, "type": "message", "message": "Ta"}},
    "notifications": {
        "n1": {"id": "n1", "name": "Admin Notification", "toType": "email",
               "to": "{admin_email}", "subject": "New"},
    },
    "fields": [
        {"id": 1, "type": "radio", "label": "Show",
         "choices": [{"text": "Morning", "value": "am"}, {"text": "Night", "value": "pm"}]},
        {"id": 2, "type": "text", "label": "Name"},
        {"id": 3, "type": "list", "label": "Songs"},
    ],
}  # fmt: skip


@pytest.fixture
def editor(wx_session_app):
    said: list[str] = []
    dialog = GravityFormEditor(
        None, lambda _d, _t: wx.ID_OK, title="Edit", form=copy.deepcopy(FORM), announce=said.append
    )
    dialog.said = said  # type: ignore[attr-defined]
    yield dialog
    dialog.Destroy()


def test_the_list_speaks_each_field_and_the_settings_are_filled(editor) -> None:
    assert editor.fields.GetStrings() == [
        "1. Show, Radio Buttons",
        "2. Name, Single Line Text",
        "3. Songs, list, kept as it is",
    ]
    assert editor.title_box.GetValue() == "Signup" and editor.button.GetValue() == "Join"
    assert editor.notify_to.IsEnabled() and editor.confirmation.GetValue() == "Ta"


def test_add_edit_move_remove_and_condition(editor, monkeypatch) -> None:
    replies: list[Any] = [fdlg.FieldAnswer("email", {"label": "Email", "isRequired": True})]
    monkeypatch.setattr(fdlg, "ask_field", lambda *_a, **_k: replies.pop(0))
    editor.fields.SetSelection(0)
    editor.add_after_selected()
    assert editor.fields.GetString(1) == "2. Email, Email, required"
    assert editor.fields.GetSelection() == 1

    replies.append(fdlg.FieldAnswer("email", {"label": "Your email", "isRequired": True}))
    editor.edit_selected()
    assert editor.fields.GetString(1).startswith("2. Your email")

    editor.move_selected(1)
    assert editor.fields.GetSelection() == 2 and editor.said[-1] == "Your email moved to 3 of 4."

    monkeypatch.setattr(
        fdlg, "ask_condition", lambda *_a, **kw: (True, gb.Condition("show", "1", "is", "pm"))
    )
    editor.condition_selected()
    assert editor.fields.GetString(2).endswith("shown when field 1 is pm")

    editor.fields.SetSelection(0)
    editor.remove_selected()
    assert "Removed Show" in editor.said[-1]
    assert gb.condition_of(gb.fields_of(editor.form)[1]) is None  # its logic went with it


def test_a_field_quill_does_not_build_is_only_moved(editor, monkeypatch) -> None:
    monkeypatch.setattr(fdlg, "ask_field", lambda *_a, **_k: pytest.fail("no editing"))
    editor.fields.SetSelection(2)
    editor.edit_selected()
    assert "keeps it as it is" in editor.said[-1]


def test_result_writes_the_settings_and_keeps_the_rest(editor) -> None:
    editor.title_box.SetValue("Sign up")
    editor.button.SetValue("Send")
    editor.placement.SetSelection(1)
    editor.subject.SetValue("New signup")
    form = editor.result()
    assert form["title"] == "Sign up" and form["button"]["text"] == "Send"
    assert form["labelPlacement"] == "left_label"
    assert form["notifications"]["n1"]["subject"] == "New signup"
    assert form["fields"][2] == FORM["fields"][2]


def test_the_field_dialog_shows_only_what_the_type_uses(wx_session_app) -> None:
    dialog = fdlg.FieldDialog(None, title="Edit", field=FORM["fields"][0])
    try:
        assert not dialog.kind.IsEnabled()
        assert dialog.choices.IsShown() and not dialog.content.IsShown()
        assert dialog.choices.GetValue() == "Morning = am\nNight = pm"
        dialog.label.SetValue("Programme")
        answer = dialog.answer()
        assert answer.kind == "radio" and answer.values["label"] == "Programme"
        assert answer.values["choices"] == "Morning = am\nNight = pm"
    finally:
        dialog.Destroy()
    dialog = fdlg.FieldDialog(None, title="Add", field=None)
    try:
        assert dialog.kind.IsEnabled()
        dialog.kind.SetSelection(list(gb.FIELD_TYPES).index("html"))
        dialog._show_for_kind()
        assert dialog.content.IsShown() and not dialog.required.IsShown()
        assert "isRequired" not in dialog.answer().values
    finally:
        dialog.Destroy()


def test_the_condition_dialog(wx_session_app) -> None:
    others = [FORM["fields"][0]]
    dialog = fdlg.ConditionDialog(
        None, title="Condition", others=others, current=gb.Condition("hide", "1", "isnot", "pm")
    )
    try:
        assert dialog.when.GetSelection() == 2 and dialog.value.GetValue() == "pm"
        assert dialog.value.GetStrings() == ["am", "pm"]
        assert dialog.answer() == gb.Condition("hide", "1", "isnot", "pm")
        dialog.when.SetSelection(0)
        assert dialog.answer() is None
    finally:
        dialog.Destroy()
