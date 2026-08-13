"""Unit tests for fill-in fields."""

from __future__ import annotations

from quill.core.expansion.fields import (
    FieldSpec,
    default_values,
    fill_fields,
    has_fields,
    parse_fields,
)


def test_a_plain_expansion_asks_nothing() -> None:
    assert has_fields("by the way") is False
    assert parse_fields("by the way") == []


def test_a_single_field_is_found() -> None:
    specs = parse_fields("Dear ${field:Name},")
    assert [s.label for s in specs] == ["Name"]
    assert specs[0].default == ""
    assert has_fields("Dear ${field:Name},") is True


def test_a_default_is_carried() -> None:
    specs = parse_fields("Ref ${field:Reference=none}")
    assert specs[0].default == "none"


def test_fields_are_ordered_as_they_are_first_asked() -> None:
    specs = parse_fields("${field:Second} then ${field:First}")
    assert [s.label for s in specs] == ["Second", "First"]


def test_a_repeated_field_is_asked_once() -> None:
    specs = parse_fields("Dear ${field:Name}, ... regards to ${field:Name}.")
    assert len(specs) == 1


def test_a_repeat_matches_regardless_of_case_and_spacing() -> None:
    specs = parse_fields("${field:First Name} and ${field:first  name}")
    assert len(specs) == 1


def test_the_first_non_empty_default_wins() -> None:
    specs = parse_fields("${field:Name} ... ${field:Name=Jeff}")
    assert specs[0].default == "Jeff"


def test_an_empty_label_is_ignored() -> None:
    assert parse_fields("${field: }") == []


def test_an_unclosed_token_is_left_alone() -> None:
    # Better literal text than swallowing the rest of the expansion.
    assert parse_fields("${field:Name") == []
    assert has_fields("${field:Name") is False


def test_filling_substitutes_every_occurrence() -> None:
    text = "Dear ${field:Name}, thank you ${field:Name}."
    assert fill_fields(text, {"name": "Ada"}) == "Dear Ada, thank you Ada."


def test_filling_uses_the_default_when_no_answer_is_given() -> None:
    assert fill_fields("Ref ${field:Reference=none}", {}) == "Ref none"


def test_an_empty_answer_falls_back_to_the_default() -> None:
    assert fill_fields("Ref ${field:Reference=none}", {"reference": ""}) == "Ref none"


def test_an_unanswered_field_with_no_default_leaves_a_gap() -> None:
    # Never the literal token: it would be ugly on screen and baffling read aloud.
    assert fill_fields("Dear ${field:Name},", {}) == "Dear ,"


def test_filling_leaves_other_variables_alone() -> None:
    text = "${field:Name} on ${date} at ${cursor}"
    assert fill_fields(text, {"name": "Ada"}) == "Ada on ${date} at ${cursor}"


def test_default_values_seeds_the_form() -> None:
    specs = [FieldSpec("Name", "Ada"), FieldSpec("Reference")]
    assert default_values(specs) == {"name": "Ada", "reference": ""}


def test_a_multi_word_label_survives_round_trip() -> None:
    specs = parse_fields("${field:Customer order number}")
    assert specs[0].label == "Customer order number"
    assert fill_fields("${field:Customer order number}", {specs[0].key: "12"}) == "12"
