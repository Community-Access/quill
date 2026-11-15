"""Form editing on structure: repeaters, columns, sections, rules and undo (complete.md WP-C).

The edits Form Outline makes (quill/ui/forms_doc.py) on the shapes beyond a flat
page, and what a person hears and where Check This Form takes them afterwards.
"""

from __future__ import annotations

import copy

import pytest

from quill.core.forms import model as M
from quill.ui import forms_check
from quill.ui import forms_doc as fd


def _model() -> dict:
    return {
        "version": 1,
        "title": "Family",
        "pages": [
            {
                "id": "p1",
                "items": [
                    {
                        "id": "kids",
                        "type": "repeater",
                        "label": "Children",
                        "items": [
                            {"id": "kname", "type": "text", "label": "Name"},
                            {
                                "id": "kage",
                                "type": "number",
                                "label": "Age",
                                "when": "#kname is filled",
                            },
                        ],
                    },
                    {
                        "id": "cols",
                        "type": "columns",
                        "columns": [
                            {"items": [{"id": "first", "type": "text", "label": "First"}]},
                            {"items": [{"id": "last", "type": "text", "label": "Last"}]},
                        ],
                    },
                    {
                        "id": "about",
                        "type": "section",
                        "label": "About you",
                        "items": [{"id": "email", "type": "email", "label": "Email"}],
                    },
                    {"id": "notes", "type": "textarea", "label": "Notes"},
                ],
            }
        ],
        "rules": [
            {"action": "show", "when": '#first is "a"', "targets": ["last"]},
            {"action": "show", "when": "#kname is filled", "targets": ["notes"]},
        ],
    }


def _ids(model: dict) -> list[str]:
    return [str(i["id"]) for i in M.iter_items(model)]


def test_items_inside_columns_and_repeaters_are_found_with_their_holder() -> None:
    model = _model()
    assert fd.place_of(model, "last").parent["id"] == "cols"
    assert fd.place_of(model, "kage").parent["id"] == "kids"
    assert fd.place_of(model, "notes").parent is None


def test_duplicating_a_repeater_copies_its_questions_and_their_conditions_follow() -> None:
    model = _model()
    assert fd.duplicate(model, "kids") == "Duplicated. The copy is straight after it."
    copy_of = model["pages"][0]["items"][1]
    assert copy_of["id"] == "kids_copy"
    assert [c["id"] for c in copy_of["items"]] == ["kname_copy", "kage_copy"]
    assert copy_of["items"][1]["when"] == "#kname_copy is filled"
    assert M.find(model, "kage")["when"] == "#kname is filled"  # the original is untouched
    assert len(_ids(model)) == len(set(_ids(model)))


def test_duplicating_columns_renames_every_question_in_every_column() -> None:
    model = _model()
    fd.duplicate(model, "cols")
    copy_of = model["pages"][0]["items"][2]
    assert [col["items"][0]["id"] for col in copy_of["columns"]] == ["first_copy", "last_copy"]
    assert len(_ids(model)) == len(set(_ids(model)))


def test_removing_columns_drops_rules_that_only_targeted_them() -> None:
    model = _model()
    assert fd.remove(model, "cols") == "cols removed."
    assert [r["targets"] for r in model["rules"]] == [["notes"]]
    assert "first" not in _ids(model) and "last" not in _ids(model)


def test_removing_a_question_a_condition_still_asks_about_says_so_and_check_finds_it() -> None:
    model = _model()
    said = fd.remove(model, "kname")
    assert said == "Name removed. 2 conditions still name it; Check This Form goes to each."
    findings = forms_check._model_problems(model)
    # Go to It lands on the question whose condition names it; the form-level rule has no item.
    assert {f.item_id for f in findings if "#kname" in f.text} == {"kage", None}


def test_sections_take_questions_in_and_out_but_not_other_sections() -> None:
    model = _model()
    model["pages"][0]["items"].insert(3, {"id": "more", "type": "section", "items": []})
    with pytest.raises(fd.Refused, match="no section just above"):
        fd.move_in(model, "cols")
    assert fd.move_in(model, "notes") == "Moved into more."
    with pytest.raises(fd.Refused, match="not inside a section"):
        fd.move_out(model, "cols")
    assert fd.move_out(model, "email") == "Moved out of About you."
    assert [i["id"] for i in model["pages"][0]["items"]] == [
        "kids",
        "cols",
        "about",
        "email",
        "more",
    ]


def test_moves_stay_inside_their_repeater() -> None:
    model = _model()
    assert fd.move(model, "kage", -1) == "Moved up."
    assert [c["id"] for c in M.find(model, "kids")["items"]] == ["kage", "kname"]
    with pytest.raises(fd.Refused, match="already first"):
        fd.move(model, "kage", -1)


def test_a_refused_edit_leaves_the_form_as_it_was() -> None:
    model = _model()
    before = copy.deepcopy(model)
    for edit in (
        lambda: fd.move_in(model, "kids"),
        lambda: fd.change_type(model, "notes", "likert"),
        lambda: fd.change_id(model, "notes", "email"),
        lambda: fd.remove(model, "missing"),
    ):
        with pytest.raises(fd.Refused):
            edit()
    assert model == before


def test_change_type_keeps_the_fields_own_condition() -> None:
    model = _model()
    assert fd.change_type(model, "kage", "text").startswith("Changed to")
    assert M.find(model, "kage")["when"] == "#kname is filled"


# -- through Form Outline: one undo step each, and cancel changes nothing ------------- #


def test_duplicate_and_remove_are_one_undo_step_each(forms, forms_host, forms_dialogs) -> None:
    forms.cmd_outline()
    forms_dialogs.press("Duplicate", 1)
    assert forms_host.replaced == 1
    forms_dialogs.answer("confirm", True)
    forms_dialogs.press("Remove...", 2)
    assert forms_host.replaced == 2
    assert [f["id"] for f in fd.fields(fd.read(forms_host.text).model)][:2] == ["name", "email"]


def test_removing_a_question_a_condition_asks_about_says_so(
    forms, forms_host, forms_dialogs
) -> None:
    forms_dialogs.answer("confirm", True)
    forms.cmd_outline()
    forms_dialogs.press("Remove...", 3)  # How did you hear about us?
    assert forms_host.announced[-1] == (
        "How did you hear about us? removed. 1 condition still names it; "
        "Check This Form goes to each."
    )
