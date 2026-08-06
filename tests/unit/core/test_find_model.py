"""Tests for the unified Find dialog core model (issue #1327, phase F1)."""

from __future__ import annotations

import re

import pytest

from quill.core.error_codes import CodedError
from quill.core.find_model import (
    NAMED_CHARACTERS,
    CompiledQuery,
    FindMatch,
    FindModelError,
    FindQuery,
    all_matches,
    compile_query,
    context_sentence,
    count_matches,
    find_next,
    preview_replacements,
    replace_all,
    replace_next,
    translate_extended,
)

# -- NAMED_CHARACTERS ---------------------------------------------------------


def test_named_characters_entries_are_nonempty() -> None:
    for name, char in NAMED_CHARACTERS.items():
        assert len(name) >= 1
        assert len(char) >= 1, f"empty character for {name!r}"


def test_named_characters_names_unique_and_plentiful() -> None:
    names = list(NAMED_CHARACTERS)
    assert len(names) == len(set(names))
    assert len(names) == 40


def test_named_characters_values_unique() -> None:
    values = list(NAMED_CHARACTERS.values())
    assert len(values) == len(set(values))


def test_named_characters_spot_checks() -> None:
    assert NAMED_CHARACTERS["Tab"] == "\t"
    assert NAMED_CHARACTERS["Line break"] == "\n"
    assert NAMED_CHARACTERS["Page break (form feed)"] == "\f"
    assert NAMED_CHARACTERS["Non-breaking space"] == " "
    assert NAMED_CHARACTERS["Em dash"] == "—"
    assert NAMED_CHARACTERS["Soft hyphen"] == "­"
    assert NAMED_CHARACTERS["Left double curly quote"] == "“"
    assert NAMED_CHARACTERS["Zero-width space"] == "​"
    assert NAMED_CHARACTERS["Byte order mark"] == "﻿"
    assert NAMED_CHARACTERS["Object replacement character"] == "￼"
    assert NAMED_CHARACTERS["Ellipsis"] == "…"
    assert NAMED_CHARACTERS["Pilcrow (paragraph mark)"] == "¶"


# -- translate_extended -------------------------------------------------------


def test_translate_simple_escapes() -> None:
    assert translate_extended(r"\t") == "\t"
    assert translate_extended(r"\n") == "\n"
    assert translate_extended(r"\r") == "\r"
    assert translate_extended(r"\f") == "\f"
    assert translate_extended(r"\0") == "\x00"
    assert translate_extended(r"\\") == "\\"


def test_translate_hex_and_unicode_escapes() -> None:
    assert translate_extended(r"\x41") == "A"
    assert translate_extended("\\u2014") == "—"
    assert translate_extended(r"\x0a") == "\n"


def test_translate_named_character() -> None:
    assert translate_extended(r"\N{EM DASH}") == "—"
    assert translate_extended(r"\N{BULLET}") == "•"
    assert translate_extended(r"a\tb\N{EM DASH}c") == "a\tb—c"


def test_translate_unknown_name_raises_with_name_and_position() -> None:
    with pytest.raises(FindModelError) as excinfo:
        translate_extended(r"abcd\N{NOT A REAL NAME}")
    message = str(excinfo.value)
    assert "NOT A REAL NAME" in message
    assert "position 5" in message


def test_translate_unfinished_name_raises() -> None:
    with pytest.raises(FindModelError) as excinfo:
        translate_extended(r"\N{EM DASH")
    assert "position 1" in str(excinfo.value)


def test_translate_forgiving_unknown_escape() -> None:
    assert translate_extended(r"\q") == "\\q"
    assert translate_extended(r"a\qb") == "a\\qb"
    # \N without a brace is just an unknown escape.
    assert translate_extended(r"\N") == "\\N"


def test_translate_forgiving_trailing_backslash() -> None:
    assert translate_extended("abc\\") == "abc\\"


def test_translate_forgiving_short_hex() -> None:
    assert translate_extended(r"\x4") == "\\x4"
    assert translate_extended(r"\xZZ") == "\\xZZ"
    assert translate_extended(r"\u12") == "\\u12"
    # Signs are not hex digits even though int() would take them.
    assert translate_extended(r"\x+1") == "\\x+1"


def test_translate_plain_text_passes_through() -> None:
    assert translate_extended("no escapes here") == "no escapes here"
    assert translate_extended("") == ""


def test_find_model_error_is_coded() -> None:
    error = FindModelError("boom")
    assert isinstance(error, CodedError)
    assert error.code.startswith("QUILL-CORE-FIND-")
    assert error.code in str(error)


# -- compile_query and whole word ---------------------------------------------


def test_whole_word_does_not_match_inside_words() -> None:
    compiled = compile_query(FindQuery(text="cat", whole_word=True))
    match, _ = find_next(compiled, "concatenate", from_pos=0)
    assert match is None
    match, _ = find_next(compiled, "the cat sat", from_pos=0)
    assert match is not None
    assert match.text == "cat"


def test_whole_word_with_non_word_ends() -> None:
    compiled = compile_query(FindQuery(text="C++", whole_word=True))
    match, _ = find_next(compiled, "I like C++ a lot", from_pos=0)
    assert match is not None
    assert match.text == "C++"
    match, _ = find_next(compiled, "ABC++ is not it", from_pos=0)
    assert match is None


def test_whole_word_at_document_edges() -> None:
    compiled = compile_query(FindQuery(text="cat", whole_word=True))
    match, _ = find_next(compiled, "cat nap", from_pos=0)
    assert match is not None
    assert match.start == 0
    match, _ = find_next(compiled, "nap cat", from_pos=0)
    assert match is not None
    assert match.end == 7


def test_case_folding_default_insensitive() -> None:
    compiled = compile_query(FindQuery(text="quill"))
    match, _ = find_next(compiled, "The QUILL editor", from_pos=0)
    assert match is not None
    assert match.text == "QUILL"


def test_case_sensitive_option() -> None:
    compiled = compile_query(FindQuery(text="quill", case_sensitive=True))
    match, _ = find_next(compiled, "The QUILL editor", from_pos=0)
    assert match is None


def test_normal_mode_treats_metacharacters_literally() -> None:
    compiled = compile_query(FindQuery(text="a.b"))
    match, _ = find_next(compiled, "axb a.b", from_pos=0)
    assert match is not None
    assert match.start == 4


def test_extended_mode_end_to_end() -> None:
    compiled = compile_query(FindQuery(text=r"\t", mode="extended"))
    match, _ = find_next(compiled, "a\tb", from_pos=0)
    assert match is not None
    assert match.start == 1
    assert match.text == "\t"


# -- find_next ----------------------------------------------------------------


def test_find_next_advances() -> None:
    compiled = compile_query(FindQuery(text="fox"))
    text = "fox one fox two fox"
    first, wrapped = find_next(compiled, text, from_pos=0)
    assert first is not None and not wrapped
    assert first.start == 0
    second, wrapped = find_next(compiled, text, from_pos=first.end)
    assert second is not None and not wrapped
    assert second.start == 8


def test_find_next_wraps_forward_with_flag() -> None:
    compiled = compile_query(FindQuery(text="fox"))
    text = "fox and hound"
    match, wrapped = find_next(compiled, text, from_pos=5)
    assert match is not None
    assert match.start == 0
    assert wrapped is True


def test_find_next_no_wrap_forward() -> None:
    compiled = compile_query(FindQuery(text="fox", wrap=False))
    match, wrapped = find_next(compiled, "fox and hound", from_pos=5)
    assert match is None
    assert wrapped is False


def test_find_next_backwards() -> None:
    compiled = compile_query(FindQuery(text="fox"))
    text = "fox one fox two"
    match, wrapped = find_next(compiled, text, from_pos=len(text), backwards=True)
    assert match is not None and not wrapped
    assert match.start == 8
    previous, wrapped = find_next(compiled, text, from_pos=match.start, backwards=True)
    assert previous is not None and not wrapped
    assert previous.start == 0


def test_find_next_backwards_wraps_to_end_with_flag() -> None:
    compiled = compile_query(FindQuery(text="fox"))
    text = "hound and fox"
    match, wrapped = find_next(compiled, text, from_pos=0, backwards=True)
    assert match is not None
    assert match.start == 10
    assert wrapped is True


def test_find_next_backwards_no_wrap() -> None:
    compiled = compile_query(FindQuery(text="fox", wrap=False))
    match, wrapped = find_next(compiled, "hound and fox", from_pos=0, backwards=True)
    assert match is None
    assert wrapped is False


def test_find_next_out_of_range_from_pos_is_clamped() -> None:
    compiled = compile_query(FindQuery(text="fox"))
    match, wrapped = find_next(compiled, "the fox", from_pos=999)
    assert match is not None
    assert wrapped is True
    match, _ = find_next(compiled, "the fox", from_pos=-5)
    assert match is not None


# -- zero-width safety --------------------------------------------------------


def _zero_width_compiled(wrap: bool = True) -> CompiledQuery:
    # compile_query never produces a zero-width pattern; build one directly to
    # prove the matching layer stays safe if that ever changes.
    return CompiledQuery(query=FindQuery(text="x", wrap=wrap), pattern=re.compile(""))


def test_zero_width_count_terminates() -> None:
    count, truncated = count_matches(_zero_width_compiled(), "abc")
    assert count == 4  # positions 0..3
    assert truncated is False


def test_zero_width_find_next_advances() -> None:
    compiled = _zero_width_compiled()
    text = "abc"
    match, wrapped = find_next(compiled, text, from_pos=0)
    assert match is not None and not wrapped
    assert match.start == match.end == 1
    following, wrapped = find_next(compiled, text, from_pos=match.end)
    assert following is not None and not wrapped
    assert following.start == 2


def test_zero_width_backwards_advances() -> None:
    compiled = _zero_width_compiled()
    text = "abc"
    match, wrapped = find_next(compiled, text, from_pos=2, backwards=True)
    assert match is not None and not wrapped
    assert match.start == match.end == 1


def test_zero_width_replace_all_terminates() -> None:
    new_text, count = replace_all(_zero_width_compiled(), "ab", "-")
    assert new_text == "-a-b-"
    assert count == 3


# -- counting and truncation --------------------------------------------------


def test_count_matches_basic_and_truncated() -> None:
    compiled = compile_query(FindQuery(text="a"))
    count, truncated = count_matches(compiled, "a" * 7)
    assert (count, truncated) == (7, False)
    count, truncated = count_matches(compiled, "a" * 7, max_count=5)
    assert (count, truncated) == (5, True)
    count, truncated = count_matches(compiled, "a" * 5, max_count=5)
    assert (count, truncated) == (5, False)


def test_all_matches_basic_and_truncated() -> None:
    compiled = compile_query(FindQuery(text="a"))
    matches, truncated = all_matches(compiled, "banana")
    assert [m.start for m in matches] == [1, 3, 5]
    assert truncated is False
    matches, truncated = all_matches(compiled, "banana", max_matches=2)
    assert len(matches) == 2
    assert truncated is True


# -- line and column ----------------------------------------------------------


def test_line_and_column_lf() -> None:
    compiled = compile_query(FindQuery(text="bar"))
    matches, _ = all_matches(compiled, "foo\nxbar\nbar")
    assert matches[0].line == 2
    assert matches[0].column == 2
    assert matches[1].line == 3
    assert matches[1].column == 1


def test_line_and_column_crlf() -> None:
    compiled = compile_query(FindQuery(text="bar"))
    matches, _ = all_matches(compiled, "foo\r\nbar\r\nxxbar")
    assert matches[0].line == 2
    assert matches[0].column == 1
    assert matches[1].line == 3
    assert matches[1].column == 3


def test_line_and_column_first_line() -> None:
    compiled = compile_query(FindQuery(text="foo"))
    match, _ = find_next(compiled, "a foo", from_pos=0)
    assert match is not None
    assert match.line == 1
    assert match.column == 3


# -- context_sentence ---------------------------------------------------------


def _match_for(text: str, needle: str) -> FindMatch:
    compiled = compile_query(FindQuery(text=needle, case_sensitive=True))
    match, _ = find_next(compiled, text, from_pos=0)
    assert match is not None
    return match


def test_context_sentence_mid_sentence() -> None:
    text = "First one. The quick brown fox jumps. Last one."
    sentence = context_sentence(text, _match_for(text, "fox"))
    assert sentence == "The quick brown fox jumps."


def test_context_sentence_at_document_start() -> None:
    text = "Hello world. Next sentence."
    sentence = context_sentence(text, _match_for(text, "Hello"))
    assert sentence == "Hello world."


def test_context_sentence_newline_boundary_and_collapse() -> None:
    text = "line one\nthe   spaced    match here\nline three"
    sentence = context_sentence(text, _match_for(text, "match"))
    assert sentence == "the spaced match here"


def test_context_sentence_long_line_clamps_with_ellipsis() -> None:
    text = "x" * 200 + " needle " + "y" * 200
    sentence = context_sentence(text, _match_for(text, "needle"), max_chars=60)
    assert "needle" in sentence
    assert sentence.startswith("...")
    assert sentence.endswith("...")
    assert len(sentence) <= 60 + 6


# -- replace ------------------------------------------------------------------


def test_replace_next_basic() -> None:
    compiled = compile_query(FindQuery(text="colour"))
    new_text, match, wrapped = replace_next(compiled, "the colour red", "color", from_pos=0)
    assert new_text == "the color red"
    assert match is not None
    assert match.text == "colour"
    assert wrapped is False


def test_replace_next_wraps() -> None:
    compiled = compile_query(FindQuery(text="colour"))
    new_text, match, wrapped = replace_next(compiled, "colour first", "color", from_pos=8)
    assert new_text == "color first"
    assert wrapped is True
    assert match is not None


def test_replace_next_no_match_leaves_text() -> None:
    compiled = compile_query(FindQuery(text="missing"))
    new_text, match, wrapped = replace_next(compiled, "nothing here", "x", from_pos=0)
    assert new_text == "nothing here"
    assert match is None
    assert wrapped is False


def test_replace_next_replacement_is_literal() -> None:
    compiled = compile_query(FindQuery(text="a"))
    new_text, _, _ = replace_next(compiled, "a", r"\g<0>$1", from_pos=0)
    assert new_text == r"\g<0>$1"


def test_replace_all_counts_and_single_pass() -> None:
    compiled = compile_query(FindQuery(text="aa", case_sensitive=True))
    new_text, count = replace_all(compiled, "aaa", "b")
    assert new_text == "ba"
    assert count == 1
    new_text, count = replace_all(compiled, "aa aa", "b")
    assert new_text == "b b"
    assert count == 2


def test_replace_all_no_matches() -> None:
    compiled = compile_query(FindQuery(text="zzz"))
    new_text, count = replace_all(compiled, "abc", "x")
    assert new_text == "abc"
    assert count == 0


def test_replace_all_does_not_rescan_replacements() -> None:
    compiled = compile_query(FindQuery(text="ab", case_sensitive=True))
    new_text, count = replace_all(compiled, "abb", "ab")
    assert new_text == "abb"
    assert count == 1


def test_preview_replacements_goldens() -> None:
    compiled = compile_query(FindQuery(text="colour"))
    text = "one\ntwo colour\nthree\ncolour four"
    previews = preview_replacements(compiled, text, "color")
    assert previews == (
        "'colour' to 'color' at line 2",
        "'colour' to 'color' at line 4",
    )


def test_preview_replacements_respects_count() -> None:
    compiled = compile_query(FindQuery(text="a"))
    previews = preview_replacements(compiled, "aaaa", "b", count=2)
    assert len(previews) == 2


# -- empty query --------------------------------------------------------------


def test_empty_query_yields_nothing_everywhere() -> None:
    compiled = compile_query(FindQuery(text=""))
    assert compiled.pattern is None
    assert count_matches(compiled, "anything") == (0, False)
    assert find_next(compiled, "anything", from_pos=0) == (None, False)
    assert find_next(compiled, "anything", from_pos=5, backwards=True) == (None, False)
    assert all_matches(compiled, "anything") == ((), False)
    assert replace_next(compiled, "anything", "x", from_pos=0) == ("anything", None, False)
    assert replace_all(compiled, "anything", "x") == ("anything", 0)
    assert preview_replacements(compiled, "anything", "x") == ()


def test_empty_extended_query_yields_nothing() -> None:
    compiled = compile_query(FindQuery(text="", mode="extended"))
    assert compiled.pattern is None
