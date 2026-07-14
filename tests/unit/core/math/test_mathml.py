"""Canonical MathML model: parsing, validation, and the LaTeX annotation round-trip."""

from __future__ import annotations

import pytest

from quill.core.math.mathml import (
    MathMLError,
    extract_tex_annotation,
    is_valid_mathml,
    parse_mathml,
    wrap_with_tex_annotation,
)

_SIMPLE = '<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>x</mi></math>'
_MULTI = (
    '<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline">'
    "<mi>x</mi><mo>+</mo><mn>1</mn></math>"
)


def test_parse_mathml_returns_math_root() -> None:
    root = parse_mathml(_SIMPLE)
    assert root.tag.endswith("math")


def test_parse_mathml_rejects_non_math_root() -> None:
    with pytest.raises(MathMLError):
        parse_mathml("<mrow><mi>x</mi></mrow>")


def test_parse_mathml_rejects_malformed_xml() -> None:
    with pytest.raises(MathMLError):
        parse_mathml("<math><mi>x</mi>")


def test_is_valid_mathml_true_and_false() -> None:
    assert is_valid_mathml(_SIMPLE) is True
    assert is_valid_mathml("not xml at all") is False


def test_wrap_and_extract_round_trip_single_child() -> None:
    wrapped = wrap_with_tex_annotation(_SIMPLE, "x")
    assert extract_tex_annotation(wrapped) == "x"
    assert is_valid_mathml(wrapped)


def test_wrap_and_extract_round_trip_multiple_children() -> None:
    wrapped = wrap_with_tex_annotation(_MULTI, "x+1")
    assert extract_tex_annotation(wrapped) == "x+1"
    assert is_valid_mathml(wrapped)


def test_extract_tex_annotation_none_when_absent() -> None:
    assert extract_tex_annotation(_SIMPLE) is None


def test_wrap_preserves_display_attribute() -> None:
    wrapped = wrap_with_tex_annotation(_SIMPLE, "x")
    root = parse_mathml(wrapped)
    assert root.get("display") == "inline"
