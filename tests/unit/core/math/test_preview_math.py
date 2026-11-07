"""TeX math rendered as MathML in the preview and the exported page."""

from __future__ import annotations

import pytest

from quill.core.browser_preview import render_preview_body, render_preview_html
from quill.core.math.preview_math import dollar_math, protect_math
from quill.io.export import markdown_to_html
from quill.io.html_page import standalone_html

pytest.importorskip("latex2mathml")

DOC = (
    "Inline \\(a_1 < b_1\\) here.\n"
    "\n"
    "$$\n"
    "x = \\frac{1}{2}\n"
    "$$\n"
    "\n"
    "```math\n"
    "E=mc^2\n"
    "```\n"
    "\n"
    "Code `\\(z\\)` stays.\n"
)


def test_math_becomes_mathml_and_underscores_are_not_emphasis() -> None:
    body = render_preview_body(DOC, "markdown")
    assert body.count("<math ") == 3
    assert 'display="block"' in body
    assert "<msub>" in body
    assert "<code>\\(z\\)</code>" in body


def test_line_numbers_survive_for_the_source_map() -> None:
    body = render_preview_body(DOC + "\nLast.\n", "markdown", source_map=True)
    # DOC is lines 0-10, then a blank line, then "Last." on line 12.
    assert '<p data-src="10">Code <code>\\(z\\)</code> stays.</p>' in body
    assert '<p data-src="12">Last.</p>' in body
    assert len(protect_math(DOC).text.splitlines()) == len(DOC.splitlines())


def test_no_page_loads_a_script_for_math() -> None:
    for page in (
        render_preview_html("t", DOC, "markdown"),
        markdown_to_html(DOC, "t"),
        standalone_html(DOC, "markdown", "t"),
    ):
        assert "<script src" not in page
        assert "mathjax" not in page.lower()
        assert "<math " in page


def test_a_formula_that_will_not_convert_stays_readable(monkeypatch) -> None:
    from quill.core.math import latex_bridge

    def fail(*_a, **_k):
        raise latex_bridge.LatexConversionError("bad")

    monkeypatch.setattr(latex_bridge, "latex_to_mathml", fail)
    body = render_preview_body("See \\(x < 1\\).\n", "markdown")
    assert '<span class="math-source">x &lt; 1</span>' in body


def test_dollar_math_is_what_pandocs_reader_understands() -> None:
    out = dollar_math(DOC)
    assert "$a_1 < b_1$" in out
    assert "$$x = \\frac{1}{2}$$" in out
    assert "$$E=mc^2$$" in out
    assert "`\\(z\\)`" in out
    assert len(out.splitlines()) == len(DOC.splitlines())
    assert dollar_math("no math") == "no math"
