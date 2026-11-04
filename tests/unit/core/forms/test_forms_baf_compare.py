"""Check This Form can say where BAF's older parser (still in Structure Mode) differs."""

from __future__ import annotations

from quill.core.forms.baf_compare import divergences


def test_agreement_gives_no_sentences() -> None:
    assert divergences('form "T"\ntext #name "Name" { @required @placeholder "Jane" }\n') == []


def test_first_indented_choice_dropped_by_the_older_parser() -> None:
    assert divergences('radio #c "Contact"\n  + Email\n  + Phone\n') == [
        "The older reader drops Email from Contact."
    ]


def test_indented_if_swallows_its_first_field() -> None:
    assert "The older reader skips B (text)." in divergences(
        'text #a "A"\n\nif #a filled\n  text #b "B"\n'
    )


def test_bfl_1_spellings_the_older_parser_does_not_know() -> None:
    found = divergences(
        'text #a "A"\ntext #b "B"\n  @when #a is not empty\ntoggle #t "Newsletter"\n'
    )
    assert "The older reader shows B every time: it does not read the condition." in found
    assert "The older reader skips Newsletter (toggle)." in found
