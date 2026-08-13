"""Unit tests for matching typed keys against the shared abbreviation library."""

from __future__ import annotations

from quill.core.abbreviations import Abbreviation, AbbreviationLibrary
from quill.core.expansion.matcher import apply_typed_case, match_buffer
from quill.core.expansion.ring_buffer import RingBuffer


def _library(*entries: Abbreviation) -> AbbreviationLibrary:
    return AbbreviationLibrary(version=2, abbreviations=list(entries))


def _entry(trigger: str, expansion: str, **fields: object) -> Abbreviation:
    return Abbreviation(id=trigger, abbreviation=trigger, expansion=expansion, **fields)  # type: ignore[arg-type]


def _typed(text: str) -> RingBuffer:
    buffer = RingBuffer()
    for char in text:
        buffer.push(char)
    return buffer


def test_expands_on_a_space() -> None:
    match = match_buffer(_typed("btw "), _library(_entry("btw", "by the way")))
    assert match is not None
    assert match.text == "by the way"
    # The trigger character stays put, so only the abbreviation is erased.
    assert match.backspace_count == 3


def test_expands_on_punctuation() -> None:
    match = match_buffer(_typed("btw."), _library(_entry("btw", "by the way")))
    assert match is not None
    assert match.backspace_count == 3


def test_no_match_without_a_trigger_character() -> None:
    assert match_buffer(_typed("btw"), _library(_entry("btw", "by the way"))) is None


def test_no_match_for_an_unknown_word() -> None:
    assert match_buffer(_typed("xyz "), _library(_entry("btw", "by the way"))) is None


def test_disabled_entries_never_match() -> None:
    library = _library(_entry("btw", "by the way", enabled=False))
    assert match_buffer(_typed("btw "), library) is None


def test_longest_abbreviation_wins() -> None:
    library = _library(_entry("ad", "advertisement"), _entry("addr", "12 High Street"))
    match = match_buffer(_typed("addr "), library)
    assert match is not None
    assert match.text == "12 High Street"


def test_only_the_last_word_is_considered() -> None:
    match = match_buffer(_typed("hello btw "), _library(_entry("btw", "by the way")))
    assert match is not None
    assert match.backspace_count == 3


def test_case_sensitive_entry_requires_the_exact_spelling() -> None:
    library = _library(_entry("SQL", "Structured Query Language", case_sensitive=True))
    assert match_buffer(_typed("SQL "), library) is not None
    assert match_buffer(_typed("sql "), library) is None


def test_case_insensitive_entry_follows_the_typed_case() -> None:
    library = _library(_entry("btw", "by the way"))
    shouted = match_buffer(_typed("BTW "), library)
    titled = match_buffer(_typed("Btw "), library)
    assert shouted is not None and shouted.text == "BY THE WAY"
    assert titled is not None and titled.text == "By The Way"


def test_trigger_mode_space_ignores_punctuation() -> None:
    library = _library(_entry("btw", "by the way", triggers="space"))
    assert match_buffer(_typed("btw "), library) is not None
    assert match_buffer(_typed("btw."), library) is None


def test_trigger_mode_punctuation_ignores_spaces() -> None:
    library = _library(_entry("btw", "by the way", triggers="punctuation"))
    assert match_buffer(_typed("btw."), library) is not None
    assert match_buffer(_typed("btw "), library) is None


def test_manual_entries_never_expand_by_typing() -> None:
    library = _library(_entry("nda", "a very long clause", triggers="manual"))
    assert match_buffer(_typed("nda "), library) is None
    assert match_buffer(_typed("nda."), library) is None


def test_trailing_space_only_applies_after_punctuation() -> None:
    library = _library(_entry("co", "Company", trailing_space=True))
    after_punctuation = match_buffer(_typed("co,"), library)
    after_space = match_buffer(_typed("co "), library)
    assert after_punctuation is not None and after_punctuation.trailing_space is True
    # A space trigger already leaves a space; adding another would read badly.
    assert after_space is not None and after_space.trailing_space is False


def test_cursor_marker_is_reported_and_removed() -> None:
    library = _library(_entry("sig", "Regards,\n${cursor}\nJeff"))
    match = match_buffer(_typed("sig "), library)
    assert match is not None
    assert "${cursor}" not in match.text
    assert match.has_cursor is True
    assert match.cursor_offset == len("Regards,\n")


def test_clipboard_variable_is_resolved_from_the_supplied_text() -> None:
    library = _library(_entry("paste", "Quoting: ${clipboard}"))
    match = match_buffer(_typed("paste "), library, "hello there")
    assert match is not None
    assert match.text == "Quoting: hello there"


def test_the_matched_entry_is_returned_for_its_per_entry_settings() -> None:
    entry = _entry("btw", "by the way", speak_mode="name", sound="on")
    match = match_buffer(_typed("btw "), _library(entry))
    assert match is not None
    assert match.abbreviation is entry


def test_apply_typed_case_leaves_ordinary_typing_alone() -> None:
    assert apply_typed_case("btw", "by the way") == "by the way"
