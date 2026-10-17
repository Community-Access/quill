"""AutoCorrect for misspellings: the built-in list, the word rules, your entries.

The rules both editors run (quill/core/autocorrect.py). The typing paths are
tested in tests/unit/ui/test_main_frame_typing_assist.py (QUILL) and
tests/unit/apps/test_lite_typing_assist.py (QUILL Lite).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from quill.core.abbreviations import (
    AUTOCORRECT_CATEGORY,
    AbbreviationLibrary,
    quick_insert_order,
    try_expand,
)
from quill.core.abbreviations_store import load_abbreviation_library, save_abbreviation_library
from quill.core.autocorrect import (
    ORIGIN_BUILT_IN,
    ORIGIN_CHANGED,
    ORIGIN_YOURS,
    autocorrect_allows,
    correction_rows,
    default_corrections,
    default_source,
    delete_correction,
    find_correction,
    lookup,
    match_case,
    note_declined,
    resume_correction,
    set_correction,
    stop_correction,
    validate_entry,
)
from quill.core.spellcheck_live import live_alert_suppressed

DATA = Path(__file__).resolve().parents[3] / "quill" / "core" / "data" / "autocorrect_en.json"


def _empty() -> AbbreviationLibrary:
    return AbbreviationLibrary(version=2, abbreviations=[])


def _fix(before: str, library: AbbreviationLibrary | None = None, **kwargs: object):
    return find_correction(before, 0, library, **kwargs)  # type: ignore[arg-type]


# -- the built-in list --------------------------------------------------------- #


def test_the_built_in_list_is_committed_data_with_its_source_written_down() -> None:
    raw = json.loads(DATA.read_text(encoding="utf-8"))
    assert raw["schema"] == 1
    assert "Hunspell" in raw["source"]
    assert default_source() == raw["source"]
    assert len(default_corrections()) >= 300
    assert default_corrections()["teh"] == "the"
    assert default_corrections()["recieve"] == "receive"


def test_every_built_in_key_is_a_lower_case_word_that_corrects_to_something_else() -> None:
    for typed, fixed in default_corrections().items():
        assert typed == typed.lower(), typed
        assert validate_entry(typed, fixed) is None, typed
        assert fixed.lower() != typed


def test_no_built_in_misspelling_is_a_correctly_spelled_word() -> None:
    """The one rule the list can never break: it must not "correct" real words.

    Checked against both Hunspell dictionaries the list was built with, when
    they are installed; every word of each correction must itself be English.
    """
    enchant = pytest.importorskip("enchant")
    try:
        us, gb = enchant.Dict("en_US"), enchant.Dict("en_GB")
    except Exception:  # noqa: BLE001 - no dictionaries on this machine
        pytest.skip("en_US and en_GB Hunspell dictionaries are not installed")
    real = [word for word in default_corrections() if us.check(word) or gb.check(word)]
    assert real == []
    for fixed in default_corrections().values():
        for part in fixed.split():
            assert us.check(part), fixed


def test_words_that_look_wrong_but_are_real_are_left_out_on_purpose() -> None:
    for word in ("calender", "wich", "sargent", "everytime", "noone", "copywrite", "the"):
        assert word not in default_corrections()


# -- the word rules ------------------------------------------------------------ #


def test_a_misspelling_before_the_space_is_found() -> None:
    match = _fix("I saw teh")
    assert match is not None
    assert (match.start, match.end, match.original, match.replacement) == (6, 9, "teh", "the")


def test_a_capital_is_kept_and_a_word_in_capitals_is_left_alone() -> None:
    assert _fix("Teh").replacement == "The"
    assert _fix("TEH") is None
    assert match_case("Febuary", "February") == "February"
    assert _fix("febuary").replacement == "February"


def test_punctuation_around_the_word_is_kept_out_of_it() -> None:
    match = _fix("(teh,")
    assert match is not None
    assert (match.start, match.end, match.replacement) == (1, 4, "the")
    assert _fix('"recieve."').replacement == "receive"


@pytest.mark.parametrize(
    "before",
    [
        "teh.example.com",
        "https://teh.org/recieve",
        "www.recieve",
        "adress@example.com",
        "C:\\teh",
        "teh_name",
        "teh2",
        "e.g",
    ],
)
def test_addresses_paths_and_identifiers_are_never_touched(before: str) -> None:
    assert _fix(before) is None


def test_a_word_inside_code_or_an_address_is_left_alone() -> None:
    text = "use `teh"
    assert (
        find_correction(
            text, 0, None, suppressed=lambda s, e: live_alert_suppressed(text + "`", s, e)
        )
        is None
    )
    fenced = "```\nteh"
    assert (
        find_correction(
            fenced, 0, None, suppressed=lambda s, e: live_alert_suppressed(fenced, s, e)
        )
        is None
    )
    prose = "plain teh"
    assert (
        find_correction(prose, 0, None, suppressed=lambda s, e: live_alert_suppressed(prose, s, e))
        is not None
    )


def test_a_run_with_no_space_in_the_window_is_not_a_word() -> None:
    assert find_correction("x" * 10 + "teh", 500, None) is None
    assert find_correction(" teh", 500, None).start == 501


def test_a_declined_word_is_not_corrected_again() -> None:
    assert _fix("teh", declined={"teh"}) is None


# -- your own entries, through the abbreviation library ------------------------- #


def test_your_entry_corrects_and_wins_over_the_built_in_one() -> None:
    library = _empty()
    set_correction(library, "qill", "QUILL")
    set_correction(library, "teh", "tea")
    assert _fix("qill", library).replacement == "QUILL"
    assert _fix("teh", library).replacement == "tea"
    assert lookup(library, "qill").origin == ORIGIN_YOURS
    assert lookup(library, "teh").origin == ORIGIN_CHANGED
    assert all(entry.category == AUTOCORRECT_CATEGORY for entry in library.abbreviations)


def test_a_match_case_entry_fires_only_on_exactly_what_was_typed() -> None:
    library = _empty()
    set_correction(library, "Qt", "Quill Tools", case_sensitive=True)
    assert _fix("Qt", library).replacement == "Quill Tools"
    assert _fix("qt", library) is None


def test_stopping_and_resuming_a_built_in_correction() -> None:
    library = _empty()
    assert stop_correction(library, "teh") is True
    assert _fix("teh", library) is None
    row = lookup(library, "teh")
    assert (row.origin, row.active) == (ORIGIN_BUILT_IN, False)
    assert "stopped" in row.describe()
    assert resume_correction(library, "teh") is True
    assert library.abbreviations == []  # the stop was all there was
    assert _fix("teh", library).replacement == "the"


def test_removing_your_entries() -> None:
    library = _empty()
    set_correction(library, "qill", "QUILL")
    set_correction(library, "teh", "tea")
    assert delete_correction(library, "qill") == "removed"
    assert _fix("qill", library) is None
    assert delete_correction(library, "teh") == "restored"
    assert _fix("teh", library).replacement == "the"
    assert delete_correction(library, "teh") == "built-in"
    assert delete_correction(library, "zzzq") == "missing"


def test_saving_the_built_in_pair_removes_your_copy_of_it() -> None:
    library = _empty()
    set_correction(library, "teh", "tea")
    assert set_correction(library, "teh", "the") is None
    assert library.abbreviations == []


@pytest.mark.parametrize(
    ("typed", "fixed"),
    [("", "the"), ("two words", "x"), ("teh", ""), ("teh", "teh"), ("a.b", "x"), ("t3h", "the")],
)
def test_entries_that_cannot_be_saved_say_why(typed: str, fixed: str) -> None:
    assert validate_entry(typed, fixed)


def test_your_corrections_persist_in_the_abbreviation_file(tmp_path: Path) -> None:
    library = _empty()
    set_correction(library, "qill", "QUILL")
    stop_correction(library, "recieve")
    save_abbreviation_library(library, tmp_path)
    assert not (tmp_path / "autocorrect.json").exists()  # one store, not two
    again = load_abbreviation_library(tmp_path)
    assert _fix("qill", again).replacement == "QUILL"
    assert _fix("recieve", again) is None
    rows = {row.typed: row for row in correction_rows(again)}
    assert rows["qill"].origin == ORIGIN_YOURS
    assert rows["recieve"].active is False


def test_corrections_are_not_abbreviations() -> None:
    """Turning abbreviations on must not turn corrections on, anywhere."""
    library = _empty()
    set_correction(library, "qill", "QUILL")
    library.add("btw", "by the way")
    assert try_expand("qill ", 5, library) is None
    assert try_expand("btw ", 4, library) is not None
    assert [entry.abbreviation for entry in library.enabled_only()] == ["btw"]
    assert library.find_by_trigger("qill") is None
    assert [entry.abbreviation for entry in quick_insert_order(library)] == ["btw"]


# -- taking one back ----------------------------------------------------------- #


def test_the_undone_word_back_in_place_is_noted_as_declined() -> None:
    last = _fix("I saw teh")
    declined: set[str] = set()
    assert note_declined(last, "I saw teh", 0, declined) is True
    assert declined == {"teh"}
    assert note_declined(last, "I saw the", 0, set()) is False
    assert note_declined(None, "I saw teh", 0, set()) is False


# -- where --------------------------------------------------------------------- #


@pytest.mark.parametrize(
    ("kind", "name", "allowed"),
    [
        ("plain", None, True),
        ("plain", "notes.txt", True),
        ("markdown", "notes.md", True),
        ("plain", "letter.rtf", True),
        ("plain", "script.py", False),
        ("plain", "settings.json", False),
        ("yaml", "config.yml", False),
        ("plain", "page.html", False),
        ("json", None, False),
    ],
)
def test_prose_only(kind: str, name: str | None, allowed: bool) -> None:
    assert autocorrect_allows(kind, name) is allowed
