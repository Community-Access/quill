"""Gravity Forms field-type conversion, wx-free (complete.md WP-C).

The planner works on the complete form Gravity Forms returned, because ``PUT
gf/v2/forms/{id}`` replaces the whole form: every other field, the form's
settings and the converted field's shared properties must go back as they came.
"""

from __future__ import annotations

import copy

import pytest

from quill.core.wordpress.workbench_forms import (
    gravity_replacement_problems,
    plan_gravity_field_type_change,
)

LOGIC = {
    "actionType": "show",
    "logicType": "all",
    "rules": [{"fieldId": "2", "operator": "is", "value": "yes"}],
}

FORM = {
    "id": 4,
    "title": "Volunteers",
    "button": {"type": "text", "text": "Send"},
    "confirmations": {"c1": {"message": "Thanks"}},
    "notifications": {"n1": {"to": "{admin_email}"}},
    "fields": [
        {
            "id": 1,
            "type": "text",
            "label": "Shift",
            "description": "When you can help",
            "adminLabel": "shift",
            "isRequired": True,
            "cssClass": "wide",
            "placeholder": "Morning",
            "defaultValue": "Morning",
            "conditionalLogic": LOGIC,
            "visibility": "visible",
            "inputName": "shift",
            "allowsPrepopulate": True,
        },
        {
            "id": 2,
            "type": "radio",
            "label": "Over 18?",
            "choices": [
                {"text": "Yes", "value": "yes", "isSelected": True},
                {"text": "No", "value": "no", "isSelected": False},
            ],
            "enableOtherChoice": True,
        },
        {
            "id": 3,
            "type": "checkbox",
            "label": "Days",
            "choices": [
                {"text": "Monday", "value": "mon", "isSelected": True},
                {"text": "Tuesday", "value": "tue", "isSelected": True},
            ],
            "inputs": [
                {"id": "3.1", "label": "Monday", "name": "monday"},
                {"id": "3.2", "label": "Tuesday"},
            ],
            "defaultValue": "mon, tue",
        },
        {"id": 5, "type": "address", "label": "Address", "inputs": [{"id": "5.1"}]},
        {"id": 6, "type": "list", "label": "Children", "enableColumns": True},
    ],
}


def _field(form: dict, field_id: int) -> dict:
    return next(f for f in form["fields"] if f["id"] == field_id)


def test_text_to_select_keeps_shared_properties_and_seeds_a_choice_from_the_default() -> None:
    plan = plan_gravity_field_type_change(FORM, "1", "select")
    field = _field(plan.form, 1)
    assert field["type"] == "select"
    for key in ("label", "description", "adminLabel", "isRequired", "cssClass", "placeholder"):
        assert field[key] == _field(FORM, 1)[key]
    assert field["conditionalLogic"] == LOGIC  # the rule on the field survives
    assert field["choices"] == [{"text": "Morning", "value": "Morning", "isSelected": False}]
    assert "conditionalLogic" in plan.kept and "1 choices" in plan.kept
    assert plan.adjusted == ("added a starter choice so the new control can be filled in",)


def test_the_planner_never_changes_the_form_it_was_given() -> None:
    before = copy.deepcopy(FORM)
    plan_gravity_field_type_change(FORM, "3", "radio")
    plan_gravity_field_type_change(FORM, "2", "text")
    assert FORM == before


def test_the_rest_of_the_form_goes_back_whole() -> None:
    plan = plan_gravity_field_type_change(FORM, "2", "select")
    for key in ("title", "button", "confirmations", "notifications"):
        assert plan.form[key] == FORM[key]
    for field_id in (1, 3, 5, 6):
        assert _field(plan.form, field_id) == _field(FORM, field_id)
    assert "complete form" in plan.review_lines()[-1]


def test_radio_to_checkbox_keeps_choices_and_builds_their_inputs() -> None:
    plan = plan_gravity_field_type_change(FORM, "2", "checkbox")
    field = _field(plan.form, 2)
    assert [c["value"] for c in field["choices"]] == ["yes", "no"]
    assert field["inputs"] == [{"id": "2.1", "label": "Yes"}, {"id": "2.2", "label": "No"}]
    assert field["enableOtherChoice"] is True  # a choice setting the new control still has


def test_checkbox_to_radio_keeps_one_default_and_says_so() -> None:
    plan = plan_gravity_field_type_change(FORM, "3", "radio")
    field = _field(plan.form, 3)
    assert [c["isSelected"] for c in field["choices"]] == [True, False]
    assert field["defaultValue"] == "mon"
    assert "inputs" not in field and "checkbox input records" in plan.removed
    assert any("first selected default" in line for line in plan.adjusted)


def test_choice_to_text_previews_what_cannot_carry_over() -> None:
    plan = plan_gravity_field_type_change(FORM, "2", "text")
    field = _field(plan.form, 2)
    assert "choices" not in field and "enableOtherChoice" not in field
    assert set(plan.removed) == {"choices", "enableOtherChoice"}
    lines = plan.review_lines()
    assert lines[1].startswith("Cannot carry over: choices")
    assert plan.summary == "Change Over 18? (field 2) from Radio buttons to Single line text."


@pytest.mark.parametrize("field_id", ["5", "6"])
def test_complex_families_are_left_alone(field_id: str) -> None:
    with pytest.raises(ValueError, match="does not convert"):
        plan_gravity_field_type_change(FORM, field_id, "text")


def test_unknown_targets_missing_fields_and_formless_answers_are_refused() -> None:
    with pytest.raises(ValueError, match="not a supported"):
        plan_gravity_field_type_change(FORM, "1", "address")
    with pytest.raises(ValueError, match="no longer in this form"):
        plan_gravity_field_type_change(FORM, "99", "text")
    with pytest.raises(ValueError, match="fields list"):
        plan_gravity_field_type_change({"id": 4}, "1", "text")


def test_the_read_back_must_show_the_new_type_and_every_other_field() -> None:
    plan = plan_gravity_field_type_change(FORM, "1", "textarea")
    assert gravity_replacement_problems(plan, plan.form) == []

    unchanged = copy.deepcopy(FORM)
    assert gravity_replacement_problems(plan, unchanged) == [
        "Field 1 reads back as text, not textarea."
    ]

    lost = copy.deepcopy(plan.form)
    lost["fields"] = [f for f in lost["fields"] if f["id"] != 6]
    assert gravity_replacement_problems(plan, lost) == ["Fields missing after the change: 6."]

    drifted = copy.deepcopy(plan.form)
    _field(drifted, 2)["type"] = "select"
    assert gravity_replacement_problems(plan, drifted) == [
        "Field 2 changed type, which QUILL did not ask for."
    ]
    assert gravity_replacement_problems(plan, None) == [
        "Gravity Forms did not return the form's fields after the change."
    ]
