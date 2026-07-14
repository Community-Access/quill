"""LaTeX -> MathML conversion and the LaTeX-source round-trip via annotation."""

from __future__ import annotations

import pytest

pytest.importorskip("latex2mathml")

from quill.core.math.latex_bridge import (  # noqa: E402
    LatexConversionError,
    latex_to_mathml,
    mathml_to_latex,
)
from quill.core.math.mathml import is_valid_mathml  # noqa: E402


def test_latex_to_mathml_produces_valid_mathml() -> None:
    mathml = latex_to_mathml(r"x^2 + 1")
    assert is_valid_mathml(mathml)
    assert "<msup>" in mathml
    assert "<mn>2</mn>" in mathml


def test_latex_to_mathml_round_trips_source() -> None:
    source = r"\frac{1}{y}"
    mathml = latex_to_mathml(source)
    assert mathml_to_latex(mathml) == source


def test_latex_to_mathml_greek_letter() -> None:
    mathml = latex_to_mathml(r"\alpha")
    assert "α" in mathml  # alpha


def test_latex_to_mathml_display_mode() -> None:
    mathml = latex_to_mathml(r"x", display="block")
    assert 'display="block"' in mathml


def test_latex_to_mathml_raises_on_malformed_input() -> None:
    with pytest.raises(LatexConversionError):
        latex_to_mathml("")


def test_mathml_to_latex_none_for_mathml_without_annotation() -> None:
    mathml = '<math xmlns="http://www.w3.org/1998/Math/MathML" display="inline"><mi>x</mi></math>'
    assert mathml_to_latex(mathml) is None
