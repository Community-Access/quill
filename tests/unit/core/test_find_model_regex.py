"""Regex mode in the shared find model.

The model had two modes -- literal and extended-escape -- and QUILL's regular
expression search went through a second, older core (``quill.core.search``).
Adding the third mode here rather than teaching QUILL Lite about that other core
is what lets both products search by pattern from one implementation, which is
the rule the two are held to: a capability the small product needs goes in the
shared package, not into a copy.

Two behaviours are worth pinning by name. Whole-word wraps the *whole* pattern,
so ``cat|dog`` means "the word cat or the word dog" rather than "the word cat,
or dog anywhere". And a malformed pattern raises with a sentence a person can
act on rather than matching nothing quietly -- a search that found nothing and
a search that could not run are different facts, and only one of them is fixed
by retyping.
"""

from __future__ import annotations

import pytest

from quill.core.find_model import (
    FindPatternError,
    FindQuery,
    all_matches,
    compile_query,
    count_matches,
    find_next,
)


def _compiled(text: str, **kwargs: object) -> object:
    return compile_query(FindQuery(text=text, mode="regex", **kwargs))  # type: ignore[arg-type]


def test_a_character_class_matches_what_it_should() -> None:
    compiled = _compiled("c[au]t")
    assert count_matches(compiled, "cat cot cut")[0] == 2


def test_the_pattern_is_not_escaped_which_is_the_whole_point() -> None:
    """In normal mode ``.`` is a full stop; here it is any character."""
    literal = compile_query(FindQuery(text="c.t", mode="normal"))
    assert count_matches(literal, "cat c.t")[0] == 1
    assert count_matches(_compiled("c.t"), "cat c.t")[0] == 2


def test_whole_word_wraps_the_whole_alternation_not_just_its_first_branch() -> None:
    """``cat|dog`` must not become "the word cat, or dog anywhere"."""
    compiled = _compiled("cat|dog", whole_word=True)
    assert compiled.pattern.pattern == r"\b(?:cat|dog)\b"
    assert count_matches(compiled, "cat catalog dog dogma")[0] == 2


def test_case_insensitive_by_default_and_sensitive_when_asked() -> None:
    assert count_matches(_compiled("cat"), "Cat cat")[0] == 2
    assert count_matches(_compiled("cat", case_sensitive=True), "Cat cat")[0] == 1


def test_an_unclosed_group_is_refused_with_a_sentence_not_a_stack_trace() -> None:
    with pytest.raises(FindPatternError) as caught:
        _compiled("(unclosed")
    message = str(caught.value)
    assert "closing parenthesis" in message
    assert "character 1" in message


def test_an_unclosed_character_class_names_the_bracket() -> None:
    with pytest.raises(FindPatternError) as caught:
        _compiled("[abc")
    assert "closing bracket" in str(caught.value)


def test_a_repeat_with_nothing_to_repeat_says_so() -> None:
    with pytest.raises(FindPatternError) as caught:
        _compiled("*abc")
    assert "nothing to repeat" in str(caught.value)


def test_a_pattern_error_is_still_a_find_model_error() -> None:
    """A caller that only wants "the search text was unusable" catches one."""
    from quill.core.find_model import FindModelError

    with pytest.raises(FindModelError):
        _compiled("(unclosed")


def test_an_empty_pattern_matches_nothing_rather_than_everything() -> None:
    compiled = _compiled("")
    assert compiled.pattern is None
    assert count_matches(compiled, "anything")[0] == 0


def test_find_next_walks_regex_matches_and_reports_the_wrap() -> None:
    compiled = _compiled(r"\d+")
    text = "a 1 b 22 c"
    first, wrapped = find_next(compiled, text, from_pos=0)
    assert (first.text, wrapped) == ("1", False)
    second, wrapped = find_next(compiled, text, from_pos=first.end)
    assert (second.text, wrapped) == ("22", False)
    third, wrapped = find_next(compiled, text, from_pos=second.end)
    assert (third.text, wrapped) == ("1", True)


def test_all_matches_carries_line_and_column_for_speech() -> None:
    compiled = _compiled(r"\bdog\b")
    matches, truncated = all_matches(compiled, "cat\ndog\ndog")
    assert [(m.line, m.column) for m in matches] == [(2, 1), (3, 1)]
    assert truncated is False


def test_the_other_two_modes_are_untouched() -> None:
    """Regex is a third mode, not a change to the two that already worked."""
    assert count_matches(compile_query(FindQuery(text="c.t")), "cat c.t")[0] == 1
    extended = compile_query(FindQuery(text=r"\t", mode="extended"))
    assert count_matches(extended, "a\tb")[0] == 1
