"""Check This Form can say, in a sentence, where BAF's current reader differs."""

from __future__ import annotations

from quill.core.forms.baf_compare import divergences


def test_agreement_gives_no_sentences() -> None:
    assert divergences('form "T"\ntext #name "Name" { @required @placeholder "Jane" }\n') == []


def test_first_indented_choice_dropped_by_baf() -> None:
    found = divergences('radio #c "Contact"\n  + Email\n  + Phone\n')
    assert found == ["BAF's reader drops Email from Contact."]


def test_indented_if_swallows_its_first_field() -> None:
    found = divergences('text #a "A"\n\nif #a filled\n  text #b "B"\n')
    assert "BAF's reader skips B (text)." in found


def test_conditions_baf_cannot_spell() -> None:
    # BAF reads "#a is x", then skips the rest of the line, block opener included.
    found = divergences('text #a "A"\n\nif #a is "x" or #a is "y" {\n  text #b "B"\n}\n')
    assert found == ["BAF shows B every time: it does not read the condition."]
    found = divergences('text #a "A"\n\nif #a is "x" or #a is "y"\n  text #b "B"\n  text #c "C"\n')
    assert "BAF shows C every time: it does not read the condition." in found
    assert divergences('number #n "N"\n\nif #n is 5.0 {\n  text #b "B"\n}\n') == []
    found = divergences('text #a "A"\ntext #b "B"\n  @when #a is filled\n')
    assert found == ["BAF shows B every time: it does not read the condition."]


def test_model_only_types_and_settings() -> None:
    found = divergences(
        'toggle #t "Newsletter"\nselect #d "D" { @required @placeholder "Pick" + A }\n'
    )
    assert "BAF's reader skips Newsletter (toggle)." in found
