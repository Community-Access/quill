"""The next three Inkwell capabilities: choices, app scope, Quillin reach.

Each is small on its own; each removes a reason people turn an expander off.
A signature firing into a code editor, a template that makes you type "Second
reminder" exactly right, and a Quillin's abbreviations stopping at the edge of
the editor are all the same complaint -- the expander does not know where it is.
"""

from __future__ import annotations

import pytest

from quill.core.abbreviations import (
    Abbreviation,
    AbbreviationLibrary,
    load_abbreviation_library,
    save_abbreviation_library,
)
from quill.core.expansion.contributed import describe, merge_libraries
from quill.core.expansion.fields import (
    default_values,
    fill_fields,
    has_fields,
    parse_fields,
)
from quill.core.expansion.matcher import match_buffer
from quill.core.expansion.ring_buffer import RingBuffer

_TEMPLATE = (
    "Dear ${field:Name}, this is a "
    "${choice:Kind|first reminder|second reminder|final notice} "
    "about ${field:Reference}. Regards, ${field:Name}"
)


# -- rich expansions: choices --------------------------------------------


def test_a_choice_offers_its_options_rather_than_asking_for_typing() -> None:
    # Picking is one arrow key; typing "Second reminder" exactly right is a
    # spelling test nobody asked to sit.
    specs = parse_fields(_TEMPLATE)
    kind = next(spec for spec in specs if spec.label == "Kind")
    assert kind.is_choice is True
    assert kind.choices == ("first reminder", "second reminder", "final notice")


def test_the_first_option_is_the_default() -> None:
    kind = next(spec for spec in parse_fields(_TEMPLATE) if spec.label == "Kind")
    assert kind.default == "first reminder"
    assert default_values(parse_fields(_TEMPLATE))[kind.key] == "first reminder"


def test_the_form_asks_in_the_order_the_template_reads() -> None:
    # Being asked for the closing before the greeting is disorienting when the
    # form is being heard rather than seen.
    assert [spec.label for spec in parse_fields(_TEMPLATE)] == ["Name", "Kind", "Reference"]


def test_a_repeated_field_is_asked_once_and_filled_everywhere() -> None:
    filled = fill_fields(_TEMPLATE, {"name": "Jane", "kind": "final notice", "reference": "A-12"})
    assert filled.startswith("Dear Jane,")
    assert filled.endswith("Regards, Jane")
    assert "final notice" in filled


def test_an_answer_that_is_not_one_of_the_options_falls_back() -> None:
    # A choice whose result can be anything is not a choice, and a stale saved
    # answer must not survive an edit that removed the option it named.
    filled = fill_fields(_TEMPLATE, {"name": "Jane", "kind": "something else"})
    assert "first reminder" in filled


def test_a_plain_expansion_still_asks_nothing() -> None:
    assert has_fields("Kind regards,\nJane") is False
    assert has_fields(_TEMPLATE) is True


def test_an_unclosed_token_is_left_as_text_rather_than_swallowing_the_rest() -> None:
    assert parse_fields("Hello ${choice:Broken") == []


# -- per-app abbreviations -----------------------------------------------


def _library(*entries: Abbreviation) -> AbbreviationLibrary:
    return AbbreviationLibrary(version=2, abbreviations=list(entries))


def _buffer(text: str) -> RingBuffer:
    buffer = RingBuffer()
    for character in text:
        buffer.push(character)
    return buffer


def test_an_unscoped_abbreviation_fires_anywhere() -> None:
    # Which is every abbreviation that exists today, and stays so.
    entry = Abbreviation(id="1", abbreviation="sig", expansion="Jane")
    assert entry.matches_app("outlook") is True
    assert entry.matches_app("") is True


def test_a_scoped_abbreviation_fires_only_where_it_belongs() -> None:
    entry = Abbreviation(id="1", abbreviation="sig", expansion="Jane", apps=("outlook",))
    assert entry.matches_app("OUTLOOK.EXE") is True
    assert entry.matches_app("code") is False


def test_a_scoped_abbreviation_does_not_fire_when_we_cannot_tell_where_we_are() -> None:
    # The safe direction for "I do not know where this would land" is not to
    # type into it.
    entry = Abbreviation(id="1", abbreviation="sig", expansion="Jane", apps=("outlook",))
    assert entry.matches_app("") is False


def test_the_matcher_honours_the_scope() -> None:
    library = _library(
        Abbreviation(id="1", abbreviation="sig", expansion="Regards, Jane", apps=("outlook",))
    )
    assert match_buffer(_buffer("sig "), library, process_name="outlook.exe") is not None
    assert match_buffer(_buffer("sig "), library, process_name="code.exe") is None


def test_a_scoped_entry_does_not_shadow_an_unscoped_one_elsewhere() -> None:
    library = _library(
        Abbreviation(id="1", abbreviation="sig", expansion="Work", apps=("outlook",)),
        Abbreviation(id="2", abbreviation="sig", expansion="Personal"),
    )
    match = match_buffer(_buffer("sig "), library, process_name="code.exe")
    assert match is not None
    assert match.text == "Personal"


@pytest.mark.parametrize("stored", [["Outlook.exe"], ["OUTLOOK"], [" outlook "]])
def test_a_hand_edited_scope_is_normalised_on_the_way_in(tmp_path, stored: list[str]) -> None:
    import json

    save_abbreviation_library(
        _library(Abbreviation(id="1", abbreviation="x", expansion="y")), tmp_path
    )
    path = tmp_path / "abbreviations.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["abbreviations"][0]["apps"] = stored
    path.write_text(json.dumps(data), encoding="utf-8")
    assert load_abbreviation_library(tmp_path).abbreviations[0].apps == ("outlook",)


def test_a_library_nobody_scoped_is_written_exactly_as_before(tmp_path) -> None:
    import json

    save_abbreviation_library(
        _library(Abbreviation(id="1", abbreviation="x", expansion="y")), tmp_path
    )
    written = json.loads((tmp_path / "abbreviations.json").read_text(encoding="utf-8"))
    assert "apps" not in written["abbreviations"][0]


# -- Quillin abbreviations, system-wide ----------------------------------


def test_a_quillin_abbreviation_becomes_available_outside_the_editor() -> None:
    user = _library(Abbreviation(id="u", abbreviation="addr", expansion="mine"))
    contributed = _library(Abbreviation(id="q:dx", abbreviation="dx", expansion="diagnosis"))
    merged = merge_libraries(user, contributed)
    assert [entry.abbreviation for entry in merged.abbreviations] == ["addr", "dx"]


def test_your_own_abbreviation_always_wins() -> None:
    # Anything else means an installed extension silently changing what a key
    # sequence does.
    user = _library(Abbreviation(id="u", abbreviation="addr", expansion="mine"))
    contributed = _library(Abbreviation(id="q", abbreviation="ADDR", expansion="theirs"))
    merged = merge_libraries(user, contributed)
    assert len(merged.abbreviations) == 1
    assert merged.abbreviations[0].expansion == "mine"


def test_nothing_contributed_changes_nothing() -> None:
    user = _library(Abbreviation(id="u", abbreviation="addr", expansion="mine"))
    assert merge_libraries(user, _library()) is user


def test_the_status_line_says_how_many_came_from_quillins() -> None:
    assert describe(_library()) == ""
    assert describe(_library(Abbreviation(id="q", abbreviation="dx", expansion="d"))) == (
        "1 abbreviation from your Quillins."
    )


def test_no_quillins_is_a_valid_state_not_a_failure() -> None:
    from quill.core.expansion.contributed import contributed_library

    assert contributed_library(None).abbreviations == []
    assert contributed_library(None, safe_mode=True).abbreviations == []
