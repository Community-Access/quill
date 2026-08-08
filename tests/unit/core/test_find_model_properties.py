"""Property-based tests for the find model (Hypothesis).

The example-based suite in ``test_find_model.py`` pins the behaviors we
designed for. These properties assert the invariants that must hold for
*every* input, which is how the generator earns its keep: the caller-side
anchor bug fixed on 2026-08-07 (a repeated backwards search that re-found
the same match forever) is exactly the shape of defect a hand-written
example set can miss and a shrinking counterexample names precisely. The
first run of this file found a real one -- ``context_sentence`` returned an
empty string for a match on a whitespace-only line, which would have
announced a found match as silence.

Properties only, no timing assertions -- see ``_configure_hypothesis`` in
``tests/conftest.py`` for why the Hypothesis deadline is disabled.
"""

from __future__ import annotations

import pytest

hypothesis = pytest.importorskip("hypothesis")

from hypothesis import assume, given  # noqa: E402
from hypothesis import strategies as st  # noqa: E402

from quill.core.find_model import (  # noqa: E402
    FindQuery,
    all_matches,
    compile_query,
    context_sentence,
    count_matches,
    find_next,
)

# Deliberately nasty alphabet: regex metacharacters (the literal path must
# escape them), newlines (line/column arithmetic and sentence boundaries),
# and non-ASCII (word boundaries and case folding).
_ALPHABET = "ab.*+?[]()\\|^$ \nÉé "
_TEXT = st.text(alphabet=_ALPHABET, max_size=200)
_NEEDLE = st.text(alphabet=_ALPHABET, min_size=1, max_size=8)


@st.composite
def _document_and_needle(draw: st.DrawFn) -> tuple[str, str]:
    """A document that is GUARANTEED to contain its needle.

    Random text almost never contains a random needle, so the naive
    ``assume(match is not None)`` filters out nearly every example and
    Hypothesis (rightly) fails the health check. Joining chunks *with* the
    needle puts real matches in every document, which is what the
    search-advances properties need to exercise anything.
    """
    needle = draw(_NEEDLE)
    chunks = draw(st.lists(st.text(alphabet=_ALPHABET, max_size=20), min_size=2, max_size=5))
    return needle.join(chunks), needle


def _compiled(needle: str, **kwargs: object) -> object:
    return compile_query(FindQuery(text=needle, **kwargs))  # type: ignore[arg-type]


@given(text=_TEXT, needle=_NEEDLE, case_sensitive=st.booleans())
def test_reported_offsets_always_describe_the_real_text(
    text: str, needle: str, case_sensitive: bool
) -> None:
    """Every match's offsets slice exactly the text the match reports."""
    matches, _truncated = all_matches(_compiled(needle, case_sensitive=case_sensitive), text)
    for match in matches:
        assert 0 <= match.start <= match.end <= len(text)
        assert text[match.start : match.end] == match.text


@given(text=_TEXT, needle=_NEEDLE)
def test_matches_are_ordered_and_non_overlapping(text: str, needle: str) -> None:
    """all_matches walks left to right without revisiting consumed text."""
    matches, _truncated = all_matches(_compiled(needle), text)
    for earlier, later in zip(matches, matches[1:], strict=False):
        assert earlier.end <= later.start


@given(text=_TEXT, needle=_NEEDLE)
def test_count_agrees_with_the_match_list(text: str, needle: str) -> None:
    """count_matches is a cheaper path to the same answer as all_matches."""
    compiled = _compiled(needle)
    count, count_truncated = count_matches(compiled, text)
    matches, list_truncated = all_matches(compiled, text)
    if not count_truncated and not list_truncated:
        assert count == len(matches)


@given(doc=_document_and_needle(), start=st.integers(min_value=-50, max_value=250))
def test_forward_search_always_advances(doc: tuple[str, str], start: int) -> None:
    """A forward find from a match's end never returns that same match.

    The invariant that keeps repeated Find Next from looping forever, and the
    forward twin of the backwards anchor bug fixed in the Find dialog.
    """
    text, needle = doc
    compiled = _compiled(needle, wrap=False)
    first, _wrapped = find_next(compiled, text, from_pos=start, backwards=False)
    assume(first is not None)
    assert first is not None
    second, _wrapped2 = find_next(compiled, text, from_pos=first.end, backwards=False)
    if second is not None:
        assert (second.start, second.end) != (first.start, first.end)
        assert second.start >= first.start


@given(doc=_document_and_needle(), start=st.integers(min_value=-50, max_value=250))
def test_backward_search_always_retreats(doc: tuple[str, str], start: int) -> None:
    """A backwards find anchored at a match's start never re-finds it.

    This is the exact invariant the Find dialog violated by anchoring its
    backwards repeat at ``match.end`` instead of ``match.start``.
    """
    text, needle = doc
    compiled = _compiled(needle, wrap=False)
    first, _wrapped = find_next(compiled, text, from_pos=start, backwards=True)
    assume(first is not None)
    assert first is not None
    second, _wrapped2 = find_next(compiled, text, from_pos=first.start, backwards=True)
    if second is not None:
        assert (second.start, second.end) != (first.start, first.end)
        assert second.end <= first.end


@given(text=_TEXT, needle=_NEEDLE)
def test_line_and_column_match_the_offset(text: str, needle: str) -> None:
    """The spoken position (line N, column M) agrees with the raw offset."""
    matches, _truncated = all_matches(_compiled(needle), text)
    for match in matches:
        expected_line = text.count("\n", 0, match.start) + 1
        line_start = text.rfind("\n", 0, match.start) + 1
        assert match.line == expected_line
        assert match.column == match.start - line_start + 1


@given(text=_TEXT, needle=_NEEDLE)
def test_case_insensitive_finds_at_least_as_much(text: str, needle: str) -> None:
    """Relaxing case can only ever find more matches, never fewer."""
    sensitive, s_trunc = count_matches(_compiled(needle, case_sensitive=True), text)
    insensitive, i_trunc = count_matches(_compiled(needle, case_sensitive=False), text)
    if not s_trunc and not i_trunc:
        assert insensitive >= sensitive


@given(text=_TEXT, needle=_NEEDLE)
def test_context_sentence_is_never_silent(text: str, needle: str) -> None:
    """Every match yields a non-empty, newline-free announcement.

    A screen reader reads this aloud verbatim: an empty string announces a
    found match as silence (indistinguishable from "not found"), and an
    embedded newline splits one announcement into two. Hypothesis found the
    empty case on a whitespace-only line; context_sentence now falls back to
    the match position.
    """
    matches, _truncated = all_matches(_compiled(needle), text)
    for match in matches[:5]:
        sentence = context_sentence(text, match)
        assert sentence.strip(), f"silent announcement for {match!r} in {text!r}"
        assert "\n" not in sentence


@given(needle=_NEEDLE)
def test_empty_document_never_matches(needle: str) -> None:
    matches, truncated = all_matches(_compiled(needle), "")
    assert len(matches) == 0
    assert not truncated


@given(text=_TEXT)
def test_empty_query_never_matches(text: str) -> None:
    """An empty needle finds nothing rather than matching everywhere."""
    compiled = compile_query(FindQuery(text=""))
    matches, truncated = all_matches(compiled, text)
    assert len(matches) == 0
    assert not truncated
    assert count_matches(compiled, text) == (0, False)
    assert find_next(compiled, text, from_pos=0) == (None, False)
