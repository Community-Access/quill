"""QAF field-type conversion (quill/core/forms/type_conversion.py), complete.md WP-C.

Change Type in Form Outline asks this planner first: it must keep what the two
controls share (label, help, required, the field's own rule, validation),
carry choices and defaults between compatible choice controls, say what it
cannot carry, and refuse a target that needs setup the field does not have.
"""

from __future__ import annotations

import pytest

from quill.core.forms.type_conversion import plan_type_change

RULE = '#age is "adult"'


def _field(**extra):
    base = {
        "id": "colour",
        "type": "radio",
        "label": "Favourite colour",
        "help": "Pick one",
        "required": True,
        "when": RULE,
        "validation": {"message": "Choose a colour"},
        "attributes": {"class": "wide"},
        "choices": [{"value": "red", "label": "Red"}, {"value": "blue", "label": "Blue"}],
        "default": "blue",
    }
    base.update(extra)
    return base


def test_radio_to_select_keeps_everything_and_reports_nothing_lost() -> None:
    field = _field()
    plan = plan_type_change(field, "select")
    assert plan.field == {**field, "type": "select"}
    assert plan.removed == () and plan.converted == () and plan.can_apply
    assert {"label", "help", "required", "when", "validation", "choices"} <= set(plan.kept)
    assert field["type"] == "radio"  # the planner never changes what it was given


def test_single_to_multi_choice_makes_the_default_a_one_item_selection() -> None:
    plan = plan_type_change(_field(), "checkbox")
    assert plan.field["default"] == ["blue"]
    assert plan.field["choices"] == _field()["choices"]
    assert plan.converted == ("kept the selected default as a one-item selection",)


def test_multi_to_single_choice_keeps_the_first_default() -> None:
    plan = plan_type_change(_field(type="checkbox", default=["red", "blue"]), "radio")
    assert plan.field["default"] == "red"
    assert "first selected default" in plan.converted[0]


def test_choice_to_text_previews_the_loss_and_keeps_the_rule() -> None:
    field = _field(type="checkbox", default=["red", "blue"], choice_library="colours")
    plan = plan_type_change(field, "text")
    assert "choices" not in plan.field and "choice_library" not in plan.field
    assert plan.removed == ("choices", "choice library")
    assert plan.field["default"] == "red, blue"
    assert plan.field["when"] == RULE and plan.field["required"] is True
    lines = plan.review_lines()
    assert lines[0].startswith("Kept: label, help")
    assert "Cannot carry over: choices, choice library." in lines
    assert "Adjusted: kept selected values as comma-separated text." in lines


def test_text_to_choice_turns_the_default_into_a_matching_choice() -> None:
    plan = plan_type_change(
        {"id": "city", "type": "text", "label": "City", "default": "Leeds"}, "select"
    )
    assert plan.field["choices"] == [{"value": "leeds", "label": "Leeds"}]
    assert plan.field["default"] == "leeds"
    assert plan.converted == ("made the existing default a matching choice",)


def test_text_to_choice_without_a_default_gets_a_starter_choice() -> None:
    plan = plan_type_change({"id": "city", "type": "text", "label": "City"}, "radio")
    assert plan.field["choices"] == [{"value": "choice-1", "label": "Choice 1"}]
    assert "default" not in plan.field


@pytest.mark.parametrize(
    ("target", "needs"),
    [
        ("calculation", ("calculation",)),
        ("matrix", ("props.rows", "props.columns")),
        ("likert", ("props.rows",)),
        ("repeater", ("items",)),
    ],
)
def test_a_target_that_needs_setup_is_refused(target: str, needs: tuple[str, ...]) -> None:
    plan = plan_type_change({"id": "q", "type": "text", "label": "Q"}, target)
    assert plan.blocked == needs and not plan.can_apply
    assert plan.review_lines()[-1] == "Set up first: " + "; ".join(needs) + "."


def test_setup_already_present_is_not_asked_for_again() -> None:
    field = {"id": "q", "type": "matrix", "label": "Q", "props": {"rows": ["a"], "columns": ["b"]}}
    assert plan_type_change(field, "matrix").can_apply  # same type: nothing to do
    likert = plan_type_change({**field, "type": "text"}, "likert")
    assert likert.blocked == () and likert.field["props"] == field["props"]


def test_an_unknown_type_raises_and_the_same_type_is_a_no_op() -> None:
    with pytest.raises(ValueError):
        plan_type_change(_field(), "hologram")
    field = _field()
    same = plan_type_change(field, "radio")
    assert same.field == field and same.field is not field
    assert (same.kept, same.converted, same.removed, same.blocked) == ((), (), (), ())
