"""View > Form Outline and Format > Form Rules, pressed button by button."""

from __future__ import annotations

from quill.core.forms import model as M
from quill.ui import forms_doc as fd
from quill.ui import forms_field_types as ft


def _model(host):
    return fd.read(host.text).model


def _ids(host):
    return [f["id"] for f in fd.fields(_model(host))]


# -- the outline ------------------------------------------------------------- #


def test_the_outline_reads_each_question_as_a_sentence(forms, forms_dialogs) -> None:
    forms.cmd_outline()
    rows = forms_dialogs.window["rows"]
    assert rows[0] == "Page 1, 4 questions"
    assert "Email address, email field, required, with an autofill hint, page 1" in rows[2]
    assert "shown when How did you hear about us? is Somewhere else" in rows[4]


def test_enter_goes_to_the_question(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    forms_dialogs.enter(3)
    assert forms_host.line_at_caret().startswith("radio #heard")


def test_enter_on_a_page_goes_to_its_start(forms, forms_host, forms_dialogs) -> None:
    forms_host.caret = 50
    forms.cmd_outline()
    forms_dialogs.enter(0)
    assert forms_host.caret == 0


def test_move_up_and_down_are_one_undo_step_each(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    rows = forms_dialogs.press("Move Up", 2)
    assert _ids(forms_host) == ["email", "name", "heard", "heard_other"]
    assert forms_host.replaced == 1 and forms_host.announced == ["Moved up."]
    assert rows[1].strip().startswith("Email address")
    forms_dialogs.press("Move Down", 1)
    assert _ids(forms_host) == ["name", "email", "heard", "heard_other"]


def test_the_first_cannot_move_up_and_says_so(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    assert forms_dialogs.press("Move Up", 1) is None
    assert forms_host.announced == ["It is already first."]


def test_a_page_row_is_not_moved(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    forms_dialogs.press("Move Down", 0)
    assert forms_host.announced == ["That is a page. Move or change its questions instead."]


def test_move_in_and_out_of_a_section(forms, forms_host, forms_dialogs) -> None:
    doc = fd.read(forms_host.text)
    doc.model["pages"][0]["items"].insert(
        0, {"id": "about", "type": "section", "label": "About you", "items": []}
    )
    forms_host.text = fd.write(doc)
    forms.cmd_outline()
    forms_dialogs.press("Move In", 2)  # Your name, just under the empty section
    section = M.find(_model(forms_host), "about")
    assert [i["id"] for i in section["items"]] == ["name"]
    assert forms_host.announced[-1] == "Moved into About you."
    forms_dialogs.press("Move Out", 2)
    assert M.find(_model(forms_host), "about")["items"] == []
    assert forms_host.announced[-1] == "Moved out of About you."


def test_rename_and_change_id_keep_the_rules_pointing_at_it(
    forms, forms_host, forms_dialogs
) -> None:
    forms_dialogs.answer("ask_text", "How did you find us?", "found")
    forms.cmd_outline()
    forms_dialogs.press("Rename...", 3)
    forms_dialogs.press("Change Id...", 3)
    model = _model(forms_host)
    assert M.find(model, "found")["label"] == "How did you find us?"
    assert M.find(model, "heard_other")["when"] == '#found is "somewhere-else"'
    assert forms_host.announced[-1] == "The id is now found."


def test_change_id_refuses_an_id_in_use(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer("ask_text", "email")
    forms.cmd_outline()
    forms_dialogs.press("Change Id...", 1)
    assert forms_host.announced == ["The id email is already used in this form."]


def test_change_type_duplicate_and_remove(forms, forms_host, forms_dialogs) -> None:
    kinds = [k for k in ft.kinds() if k not in (ft.SECTION, ft.PAGE_BREAK)]
    forms_dialogs.answer("ask_choice", kinds.index("select"))
    forms_dialogs.answer("confirm", True)
    forms.cmd_outline()
    forms_dialogs.press("Change Type...", 3)
    assert M.find(_model(forms_host), "heard")["type"] == "select"
    forms_dialogs.press("Duplicate", 1)
    assert _ids(forms_host)[:2] == ["name", "name_copy"]
    forms_dialogs.press("Remove...", 2)
    assert "name_copy" not in _ids(forms_host)
    assert forms_host.announced[-1] == "Your name removed."


def test_remove_cancelled_keeps_it(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    forms_dialogs.press("Remove...", 1)
    assert _ids(forms_host)[0] == "name" and forms_host.announced == ["Nothing changed."]


# -- the rules ---------------------------------------------------------------- #


def test_rules_are_listed_as_sentences(forms, forms_dialogs) -> None:
    forms.cmd_rules()
    assert forms_dialogs.window["rows"] == [
        "Show Where? when How did you hear about us? is Somewhere else."
    ]


def test_add_rule_from_three_choices(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer(
        "ask_fields",
        {
            "when": "heard",
            "test": 0,
            "value": "a-friend",
            "own": "",
            "action": "require",
            "target": "email",
        },
    )
    forms.cmd_rules()
    rows = forms_dialogs.press("Add Rule...", None)
    assert _model(forms_host)["rules"] == [
        {"action": "require", "targets": ["email"], "when": '#heard is "a-friend"'}
    ]
    assert forms_host.announced == [
        "Require Email address when How did you hear about us? is A friend."
    ]
    assert len(rows) == 2


def test_a_show_rule_is_written_on_the_question_itself(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer(
        "ask_fields",
        {"when": "name", "test": 2, "value": "", "own": "", "action": "show", "target": "email"},
    )
    forms.cmd_rules()
    forms_dialogs.press("Add Rule...", None)
    assert M.find(_model(forms_host), "email")["when"] == "#name is not empty"


def test_a_rule_written_by_hand_is_checked_first(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer(
        "ask_fields",
        {
            "when": "name",
            "test": 0,
            "value": "",
            "own": "#name is is",
            "action": "show",
            "target": "email",
        },
    )
    before = forms_host.text
    forms.cmd_rules()
    forms_dialogs.press("Add Rule...", None)
    assert forms_host.text == before
    assert forms_host.said.startswith("That rule cannot be read:")


def test_edit_and_remove_a_rule(forms, forms_host, forms_dialogs) -> None:
    forms_dialogs.answer("ask_text", '#heard is "a-friend"')
    forms_dialogs.answer("confirm", True)
    forms.cmd_rules()
    assert forms_dialogs.press("Edit...", 0) == [
        "Show Where? when How did you hear about us? is A friend."
    ]
    assert forms_dialogs.press("Remove...", 0) == []
    assert "when" not in M.find(_model(forms_host), "heard_other")


def test_go_to_a_rule_goes_to_its_question(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_rules()
    forms_dialogs.enter(0)
    assert forms_host.line_at_caret().startswith("text #heard_other")


def test_add_rule_in_a_form_with_no_questions_says_so(forms, forms_host, forms_dialogs) -> None:
    forms_host.text = 'bfl 1\nform "Empty"\n'
    forms.cmd_rules()
    forms_dialogs.press("Add Rule...", None)
    assert forms_host.announced == ["This form has no questions for a rule to use yet."]


def test_a_rule_answer_typed_as_its_label_matches_the_stored_choice() -> None:
    from quill.ui.forms_outline_commands import choice_value

    question = {
        "id": "contact",
        "type": "radio",
        "choices": [{"value": "phone", "label": "Phone"}, {"value": "email", "label": "Email"}],
    }
    assert choice_value(question, {}, "Phone") == "phone"
    assert choice_value(question, {}, "EMAIL") == "email"
    assert choice_value(question, {}, "17") == "17"
    assert choice_value(None, {}, "Phone") == "Phone"
