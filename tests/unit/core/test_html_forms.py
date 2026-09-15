"""A form control inserted whole, with the wiring that makes it usable.

The wiring is the point and the wiring is invisible: a missing ``for`` looks
exactly like a present one, a radio group without a shared ``name`` looks
exactly like one with, and the only symptom of two fields sharing an ``id`` is
that clicking one label focuses the wrong box. None of that is reviewable by eye
by the people this editor is for, so it is asserted here instead.
"""

from __future__ import annotations

import re

import pytest

from quill.core.html_forms import (
    FORM_SNIPPETS,
    build_form_snippet,
    form_snippet_names,
    is_form_snippet,
    next_free_id,
)
from quill.core.tagging import build_html_insertion, html_insert_choices, search_html_tag_choices

_LABEL_FOR = re.compile(r'<label[^>]*\bfor="([^"]+)"')
_ID = re.compile(r'\bid="([^"]+)"')
_NAME = re.compile(r'\bname="([^"]+)"')
_FIELD = re.compile(r"<(input|select|textarea)\b[^>]*>")


def _built(name: str, selected: str = "", document: str = "") -> str:
    return build_form_snippet(name, selected, document).inserted_text


# -- the contract every snippet keeps ------------------------------------------


@pytest.mark.parametrize("name", form_snippet_names())
def test_every_label_points_at_a_field_that_exists(name: str) -> None:
    """A ``for`` with no matching ``id`` is a label that labels nothing.

    It is also completely silent: the page renders identically, and a reader
    announces the field as unlabelled while the text sits right beside it.
    """
    written = _built(name)
    ids = set(_ID.findall(written))
    for target in _LABEL_FOR.findall(written):
        assert target in ids, f"{name}: <label for={target!r}> points at nothing"


@pytest.mark.parametrize("name", form_snippet_names())
def test_every_field_that_can_be_labelled_is(name: str) -> None:
    written = _built(name)
    labelled = set(_LABEL_FOR.findall(written))
    for match in _FIELD.finditer(written):
        element = match.group(0)
        if 'type="hidden"' in element:
            continue
        found = _ID.search(element)
        assert found, f"{name}: {match.group(1)} has no id to be labelled by"
        assert found.group(1) in labelled, f"{name}: {found.group(1)} has no label"


@pytest.mark.parametrize("name", form_snippet_names())
def test_every_field_submits_something(name: str) -> None:
    written = _built(name)
    for match in _FIELD.finditer(written):
        assert _NAME.search(match.group(0)), f"{name}: {match.group(1)} has no name"


@pytest.mark.parametrize("name", form_snippet_names())
def test_no_snippet_emits_a_duplicate_id(name: str) -> None:
    ids = _ID.findall(_built(name))
    assert len(ids) == len(set(ids)), f"{name}: repeated id {ids}"


# -- the two controls that are silent when they are wrong ----------------------


def test_a_radio_group_shares_one_name_and_has_a_legend() -> None:
    """Radios are wrong in two silent ways at once.

    Without a shared ``name`` they are not a group and every one of them can be
    on at once. Without a fieldset and legend they are a group with no name, so
    a reader announces three options and never the question they answer.
    """
    written = _built("Form field: radio group")
    names = set(_NAME.findall(written))
    assert len(names) == 1, f"radios must share one name, got {names}"
    assert "<fieldset>" in written and "<legend>" in written
    assert written.count('type="radio"') == 3
    assert written.count("checked") == 1  # exactly one default, never none or two


def test_a_checkbox_group_shares_a_name_and_is_fieldset_wrapped() -> None:
    written = _built("Form field: checkbox group")
    assert len(set(_NAME.findall(written))) == 1
    assert "<legend>" in written


def test_a_dropdown_does_not_default_to_a_real_answer() -> None:
    # A select whose first option is a real choice collects answers nobody gave,
    # because not touching it submits one.
    written = _built("Form field: dropdown (select)")
    first = written.index("<option")
    assert 'value=""' in written[first : first + 60]


def test_the_error_pattern_wires_hint_and_error_and_starts_out_valid() -> None:
    written = _built("Form field: required, with hint and error")
    described = re.search(r'aria-describedby="([^"]+)"', written)
    assert described, "the hint and the error must be announced with the field"
    ids = set(_ID.findall(written))
    for target in described.group(1).split():
        assert target in ids, f"aria-describedby points at missing {target}"
    assert 'aria-invalid="false"' in written
    assert 'role="alert"' in written


def test_an_autocomplete_input_points_at_its_datalist() -> None:
    written = _built("Form field: autocomplete (input + datalist)")
    listed = re.search(r'\blist="([^"]+)"', written)
    assert listed and listed.group(1) in set(_ID.findall(written))


# -- the selection becomes the label, and the id follows it --------------------


def test_a_selection_becomes_the_label_and_the_id_agrees_with_it() -> None:
    written = _built("Form field: text", "Postcode")
    assert ">Postcode</label>" in written
    assert 'id="postcode"' in written
    assert 'for="postcode"' in written


def test_a_multi_line_selection_uses_only_its_first_line() -> None:
    written = _built("Form field: text", "Postcode\nand more besides")
    assert ">Postcode</label>" in written


def test_a_selection_of_punctuation_falls_back_rather_than_emitting_an_empty_id() -> None:
    # An empty id is worse than a generic one: for="" matches nothing at all.
    written = _built("Form field: text", "!!!")
    found = _ID.search(written)
    assert found and found.group(1)


# -- ids do not collide with what is already in the document -------------------


def test_an_id_already_in_the_document_is_stepped_over() -> None:
    """The commonest way a form stops being accessible when it is copied.

    Two fields sharing one id renders identically, and the only symptom is that
    the second label focuses the first field.
    """
    document = '<label for="email">Email</label><input id="email">'
    written = _built("Form field: email", "Email", document)
    assert 'id="email"' not in written
    found = _ID.search(written)
    assert found and found.group(1).startswith("email")


def test_the_suffixed_ids_a_group_derives_are_checked_too() -> None:
    # A radio group inserted twice must not collide on its children while its
    # parent looks free.
    first = _built("Form field: radio group", "Delivery")
    second = _built("Form field: radio group", "Delivery", first)
    assert not set(_ID.findall(first)) & set(_ID.findall(second))


def test_next_free_id_walks_until_it_finds_one() -> None:
    document = '<b id="name"></b><b id="name-2"></b><b id="name-3"></b>'
    assert next_free_id("name", document) == "name-4"


def test_next_free_id_on_an_empty_document_is_the_stem() -> None:
    assert next_free_id("email", "") == "email"


# -- how the picker sees them ---------------------------------------------------


def test_whole_controls_are_offered_before_the_bare_tags() -> None:
    # Somebody reaching for "checkbox" nearly always wants one with a label
    # bound to it, and the wiring is invisible, so forgetting it looks exactly
    # like doing it. The bare tags are still there, one row further down.
    choices = html_insert_choices()
    assert choices[: len(FORM_SNIPPETS)] == form_snippet_names()
    assert "select" in choices and "input" in choices


@pytest.mark.parametrize(
    ("query", "expected"),
    [
        ("dropdown", "Form field: dropdown (select)"),
        ("radio", "Form field: radio group"),
        ("checkbox", "Form field: checkbox"),
        ("autocomplete", "Form field: autocomplete (input + datalist)"),
        ("error message", "Form field: required, with hint and error"),
        ("contact form", "Form field: whole form"),
        ("multiline", "Form field: long answer (textarea)"),
    ],
)
def test_the_search_finds_a_control_by_what_it_is_called_in_conversation(
    query: str, expected: str
) -> None:
    assert search_html_tag_choices(query)[0] == expected


def test_the_bare_tag_is_still_reachable_alongside_the_whole_control() -> None:
    assert "select" in search_html_tag_choices("dropdown")


def test_the_shared_builder_routes_a_snippet_to_the_snippet_builder() -> None:
    assert is_form_snippet("Form field: checkbox")
    assert not is_form_snippet("select")
    written = build_html_insertion("Form field: checkbox", "", {}, "").inserted_text
    assert "<label" in written


def test_an_unknown_snippet_name_inserts_nothing_rather_than_guessing() -> None:
    assert build_form_snippet("Form field: nonsense").inserted_text == ""
