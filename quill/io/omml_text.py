"""Word equations (OMML) as readable LaTeX text, for QUILL's own Word readers.

**Why this exists (2026-10-16).** QUILL's own Word readers became the first
choice for opening a ``.docx`` so that a cold open stops paying MarkItDown's
11-17 second import. Comparing the two on real files found one thing
MarkItDown kept and QUILL's readers silently dropped: equations. A Word
equation is stored as Office Math Markup (``<m:oMath>``), which python-docx's
``paragraph.text`` skips entirely, so "Pythagorean theorem: a² + b² = c²"
opened as "Pythagorean theorem:" and nothing else. Losing the one part of a
maths handout that matters, without a word, is worse than being slow.

This module turns OMML back into LaTeX, written with the delimiters QUILL's
own Insert Equation writes (:mod:`quill.core.math.equation_text`): ``\\(...\\)``
for an equation inside a line and ``$$...$$`` for one on its own line. That is
also what the Word writer (:mod:`quill.io.docx_math`) turns back into a real
equation, so a document QUILL saved with an equation opens with the same
equation text it was written with.

Covered: runs, superscripts and subscripts, fractions (stacked and linear),
roots, delimiters, n-ary operators (sums, products, integrals), functions,
accents, bars, group characters, limits, matrices, equation arrays and boxes.
Anything else falls back to its plain characters, so nothing is ever dropped.
Symbols stay as the Unicode characters Word stored (π, ≤, →), which a screen
reader already speaks.

wx-free; standard library only; works on ElementTree and lxml elements alike.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["MATH_NS", "is_math_element", "omml_to_latex", "omml_to_text"]

MATH_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
_W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

_FUNCTION_NAMES = frozenset({
    "sin", "cos", "tan", "cot", "sec", "csc", "arcsin", "arccos", "arctan",
    "sinh", "cosh", "tanh", "log", "ln", "lg", "exp", "lim", "max", "min",
    "sup", "inf", "det", "gcd", "deg", "dim", "ker", "arg",
})  # fmt: skip

_NARY: dict[str, str] = {
    "∑": "\\sum",
    "∏": "\\prod",
    "∐": "\\coprod",
    "∫": "\\int",
    "∬": "\\iint",
    "∭": "\\iiint",
    "∮": "\\oint",
    "⋃": "\\bigcup",
    "⋂": "\\bigcap",
    "⋁": "\\bigvee",
    "⋀": "\\bigwedge",
}

_ACCENTS: dict[str, str] = {
    "̂": "\\hat",
    "̃": "\\tilde",
    "̇": "\\dot",
    "̈": "\\ddot",
    "⃗": "\\vec",
    "̄": "\\bar",
    "̅": "\\bar",
    "́": "\\acute",
    "̀": "\\grave",
    "̌": "\\check",
    "̆": "\\breve",
}

#: Delimiter characters that are syntax in LaTeX and must be escaped.
_ESCAPED_DELIMITERS = {"{": "\\{", "}": "\\}"}


def _m(name: str) -> str:
    return f"{{{MATH_NS}}}{name}"


def _local(element: Any) -> str:
    tag = element.tag
    if not isinstance(tag, str) or not tag.startswith(f"{{{MATH_NS}}}"):
        return ""
    return tag[len(MATH_NS) + 2 :]


def is_math_element(element: Any) -> bool:
    """True for ``<m:oMath>`` and ``<m:oMathPara>``."""
    return _local(element) in {"oMath", "oMathPara"}


def omml_to_text(element: Any) -> str:
    """An ``<m:oMath>`` or ``<m:oMathPara>`` as delimited LaTeX, ready for the page.

    ``\\(...\\)`` inside a line, ``$$...$$`` for a display equation. Empty when
    the equation has no characters at all.
    """
    if _local(element) == "oMathPara":
        parts = [omml_to_latex(child) for child in element if _local(child) == "oMath"]
        return " ".join(f"$${part}$$" for part in parts if part.strip())
    latex = omml_to_latex(element)
    return f"\\({latex}\\)" if latex.strip() else ""


def omml_to_latex(element: Any) -> str:
    """The LaTeX for one OMML element (no delimiters)."""
    name = _local(element)
    handler = _HANDLERS.get(name)
    if handler is not None:
        return handler(element)
    if name.endswith("Pr") or name == "ctrlPr":
        return ""
    return _children(element)


def _children(element: Any) -> str:
    parts: list[str] = []
    for child in element:
        if _local(child):
            parts.append(omml_to_latex(child))
        elif child.tag == f"{{{_W_NS}}}r" or child.tag == f"{{{_W_NS}}}t":
            parts.append("".join(child.itertext()))
    return "".join(parts)


def _part(element: Any, name: str) -> str:
    found = element.find(_m(name))
    return omml_to_latex(found) if found is not None else ""


def _prop(element: Any, prop: str, name: str, default: str) -> str:
    """A property value: ``<m:dPr><m:begChr m:val="["/></m:dPr>`` -> ``"["``."""
    properties = element.find(_m(prop))
    if properties is None:
        return default
    node = properties.find(_m(name))
    if node is None:
        return default
    value = node.get(_m("val"))
    return default if value is None else value


def _run(element: Any) -> str:
    return "".join(
        "".join(child.itertext()) for child in element if child.tag in (_m("t"), f"{{{_W_NS}}}t")
    )


def _named(text: str) -> str:
    stripped = text.strip()
    return f"\\{stripped}" if stripped in _FUNCTION_NAMES else text


def _sup(element: Any) -> str:
    return f"{_group(element)}^{{{_part(element, 'sup')}}}"


def _sub(element: Any) -> str:
    return f"{_group(element)}_{{{_part(element, 'sub')}}}"


def _subsup(element: Any) -> str:
    return f"{_group(element)}_{{{_part(element, 'sub')}}}^{{{_part(element, 'sup')}}}"


def _pre(element: Any) -> str:
    return f"{{}}_{{{_part(element, 'sub')}}}^{{{_part(element, 'sup')}}}{_group(element)}"


def _group(element: Any) -> str:
    base = _part(element, "e")
    return base if len(base) <= 1 else f"{{{base}}}"


def _fraction(element: Any) -> str:
    num, den = _part(element, "num"), _part(element, "den")
    if _prop(element, "fPr", "type", "bar") == "lin":
        return f"{num}/{den}"
    return f"\\frac{{{num}}}{{{den}}}"


def _radical(element: Any) -> str:
    degree = _part(element, "deg")
    body = _part(element, "e")
    return f"\\sqrt[{degree}]{{{body}}}" if degree.strip() else f"\\sqrt{{{body}}}"


def _delimiter(element: Any) -> str:
    begin = _prop(element, "dPr", "begChr", "(")
    end = _prop(element, "dPr", "endChr", ")")
    separator = _prop(element, "dPr", "sepChr", "|")
    inner = separator.join(omml_to_latex(child) for child in element if _local(child) == "e")
    return f"{_ESCAPED_DELIMITERS.get(begin, begin)}{inner}{_ESCAPED_DELIMITERS.get(end, end)}"


def _nary(element: Any) -> str:
    symbol = _prop(element, "naryPr", "chr", "∫")
    operator = _NARY.get(symbol, symbol)
    sub, sup = _part(element, "sub"), _part(element, "sup")
    limits = (f"_{{{sub}}}" if sub.strip() else "") + (f"^{{{sup}}}" if sup.strip() else "")
    return f"{operator}{limits} {_part(element, 'e')}".rstrip()


def _function(element: Any) -> str:
    return f"{_named(_part(element, 'fName'))} {_part(element, 'e')}".rstrip()


def _accent(element: Any) -> str:
    command = _ACCENTS.get(_prop(element, "accPr", "chr", "̂"), "\\hat")
    return f"{command}{{{_part(element, 'e')}}}"


def _bar(element: Any) -> str:
    position = _prop(element, "barPr", "pos", "bot")
    command = "\\overline" if position == "top" else "\\underline"
    return f"{command}{{{_part(element, 'e')}}}"


def _group_char(element: Any) -> str:
    position = _prop(element, "groupChrPr", "pos", "bot")
    command = "\\overbrace" if position == "top" else "\\underbrace"
    return f"{command}{{{_part(element, 'e')}}}"


def _lim_low(element: Any) -> str:
    return f"{_named(_part(element, 'e'))}_{{{_part(element, 'lim')}}}"


def _lim_upp(element: Any) -> str:
    return f"{_named(_part(element, 'e'))}^{{{_part(element, 'lim')}}}"


def _matrix(element: Any) -> str:
    rows = [
        " & ".join(omml_to_latex(cell) for cell in row if _local(cell) == "e")
        for row in element
        if _local(row) == "mr"
    ]
    return "\\begin{matrix}" + " \\\\ ".join(rows) + "\\end{matrix}"


def _equation_array(element: Any) -> str:
    rows = [omml_to_latex(row) for row in element if _local(row) == "e"]
    return "\\begin{aligned}" + " \\\\ ".join(rows) + "\\end{aligned}"


_HANDLERS: dict[str, Callable[[Any], str]] = {
    "r": _run,
    "sSup": _sup,
    "sSub": _sub,
    "sSubSup": _subsup,
    "sPre": _pre,
    "f": _fraction,
    "rad": _radical,
    "d": _delimiter,
    "nary": _nary,
    "func": _function,
    "acc": _accent,
    "bar": _bar,
    "groupChr": _group_char,
    "limLow": _lim_low,
    "limUpp": _lim_upp,
    "m": _matrix,
    "eqArr": _equation_array,
}
