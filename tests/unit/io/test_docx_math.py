"""Segment-splitting and OMML-fragment generation for docx math splicing."""

from __future__ import annotations

import pytest

pytest.importorskip("docx")

from quill.io.docx_math import MathSegment, omml_fragment_for_latex, split_math_segments
from quill.io.pandoc import PandocUnavailableError


def _pandoc_available() -> bool:
    from quill.core.external_tools import get_external_tool_status

    return get_external_tool_status("pandoc").installed


def test_split_plain_text_is_single_text_segment() -> None:
    segments = split_math_segments("just some prose, no math")
    assert segments == [MathSegment(is_math=False, content="just some prose, no math")]


def test_split_inline_math_segment() -> None:
    segments = split_math_segments("The formula \\(x^2 + 1\\) here.")
    assert segments == [
        MathSegment(is_math=False, content="The formula "),
        MathSegment(is_math=True, content="x^2 + 1", display=False),
        MathSegment(is_math=False, content=" here."),
    ]


def test_split_display_math_segment() -> None:
    segments = split_math_segments("$$a^2+b^2=c^2$$")
    assert segments == [MathSegment(is_math=True, content="a^2+b^2=c^2", display=True)]


def test_split_multiple_math_segments() -> None:
    segments = split_math_segments("\\(x\\) and \\(y\\)")
    assert [s.is_math for s in segments] == [True, False, True]
    assert segments[0].content == "x"
    assert segments[2].content == "y"


def test_split_no_dollar_ambiguity_from_plain_prose() -> None:
    # Regression guard: ordinary prose with a lone $ never becomes a math segment.
    segments = split_math_segments("It costs $5 today.")
    assert segments == [MathSegment(is_math=False, content="It costs $5 today.")]


@pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")
def test_omml_fragment_for_valid_latex() -> None:
    fragment = omml_fragment_for_latex("a^2+b^2=c^2", display=False)
    assert fragment is not None
    assert "oMath" in fragment


@pytest.mark.skipif(not _pandoc_available(), reason="Pandoc not installed")
def test_omml_fragment_display_mode() -> None:
    fragment = omml_fragment_for_latex("a^2+b^2=c^2", display=True)
    assert fragment is not None
    assert "oMath" in fragment


def test_omml_fragment_returns_none_without_pandoc(monkeypatch: pytest.MonkeyPatch) -> None:
    """omml_fragment_for_latex degrades to None rather than raising when Pandoc is absent."""

    def _raise_unavailable(*args: object, **kwargs: object) -> None:
        raise PandocUnavailableError("not installed")

    # omml_fragment_for_latex is memoized; clear so this test's monkeypatch actually
    # runs rather than returning a result cached by a different test's real call.
    omml_fragment_for_latex.cache_clear()
    monkeypatch.setattr("quill.io.docx_math.convert_file_with_pandoc", _raise_unavailable)
    assert omml_fragment_for_latex("a^2+b^2=c^2", display=False) is None
    omml_fragment_for_latex.cache_clear()
