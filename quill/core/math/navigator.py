"""A lightweight, structural equation navigator (no MathCAT required).

This is deliberately not a math-speech engine: it does not implement Nemeth
or UEB Technical braille rules, and its plain-English readings are simple
templates, not linguistically tuned output. What it does provide, using only
the MathML already produced by :mod:`quill.core.math.latex_bridge`: a way to
step into a formula's structure (numerator/denominator, base/exponent, a
square root's radicand, ...) one piece at a time, and a plain-English linear
reading of any piece. Real Nemeth-quality math speech is MathCAT's job
(docs/planning/math.md, step 3, deferred pending a native-build decision);
this module is the "basic algebra, useful today" alternative.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

from quill.core.error_codes import CodedError
from quill.core.math.latex_bridge import (
    LatexBridgeUnavailable,
    LatexConversionError,
    latex_to_mathml,
)
from quill.core.math.mathml import MATHML_NS, MathMLError, parse_mathml

_TAG = f"{{{MATHML_NS}}}"

#: Per-parent-tag labels for each child, in order. Parents not listed here
#: (mrow, math, semantics, ...) have no special per-child role.
_ROLE_LABELS: dict[str, tuple[str, ...]] = {
    "mfrac": ("Numerator", "Denominator"),
    "mroot": ("Radicand", "Root index"),
    "msup": ("Base", "Exponent"),
    "msub": ("Base", "Subscript"),
    "msubsup": ("Base", "Subscript", "Exponent"),
}

#: Plain-English words for symbols LaTeX math commonly produces, keyed by the
#: literal character(s) MathML ends up with — regardless of whether the
#: converter tagged them <mo> or (as latex2mathml does for a few, e.g. \pm)
#: <mi>. Anything not listed here is read as its literal character(s).
_SYMBOL_WORDS: dict[str, str] = {
    "=": "equals",
    "+": "plus",
    "−": "minus",
    "-": "minus",
    "±": "plus or minus",
    "∓": "minus or plus",
    "×": "times",
    "⋅": "times",
    "÷": "divided by",
    "<": "is less than",
    ">": "is greater than",
    "≤": "is less than or equal to",
    "≥": "is greater than or equal to",
    "≠": "is not equal to",
    "∞": "infinity",
    "(": "open paren",
    ")": "close paren",
}

#: Special-cased small exponents read more naturally than "to the power N".
_EXPONENT_WORDS: dict[str, str] = {"2": "squared", "3": "cubed"}


class MathNavigatorError(CodedError):
    """Raised when *text* cannot be parsed as LaTeX or MathML."""

    code = "QUILL-MATH-NAVIGATOR-PARSE"


def _local_tag(element: ET.Element) -> str:
    tag = element.tag
    return tag[len(_TAG) :] if tag.startswith(_TAG) else tag


def _children(element: ET.Element) -> list[ET.Element]:
    return list(element)


def _text_of(element: ET.Element) -> str:
    return (element.text or "").strip()


def _symbol_reading(text: str) -> str:
    return _SYMBOL_WORDS.get(text, text)


def parse_equation(text: str) -> ET.Element:
    """Parse *text* — bare LaTeX or a raw MathML string — into a MathML root.

    Raises :class:`MathNavigatorError` if it is neither valid LaTeX nor
    well-formed MathML.
    """
    stripped = text.strip()
    if stripped.startswith("<math"):
        try:
            return parse_mathml(stripped)
        except MathMLError as exc:
            raise MathNavigatorError(str(exc)) from exc
    try:
        mathml = latex_to_mathml(stripped)
    except (LatexConversionError, LatexBridgeUnavailable) as exc:
        raise MathNavigatorError(str(exc)) from exc
    return parse_mathml(mathml)


def node_kind_label(element: ET.Element) -> str:
    """A short label describing what *element* itself is."""
    tag = _local_tag(element)
    if tag == "mfrac":
        return "Fraction"
    if tag == "msqrt":
        return "Square root"
    if tag == "mroot":
        return "Root"
    if tag in ("msup", "msub", "msubsup"):
        # Short compounds (e.g. "a squared", "x sub 1") read fine as a single
        # child-list entry, unlike mfrac/msqrt/mroot which can get long.
        return read_aloud(element)
    if tag == "mrow":
        return "Group"
    if tag in ("mi", "mn", "mtext"):
        return _symbol_reading(_text_of(element)) or tag
    if tag == "mo":
        return _symbol_reading(_text_of(element))
    if tag in ("math", "semantics"):
        return "Equation"
    return tag


def read_aloud(element: ET.Element) -> str:
    """A plain-English linear reading of *element* and everything inside it."""
    tag = _local_tag(element)
    if tag in ("math", "semantics"):
        children = [c for c in _children(element) if _local_tag(c) != "annotation"]
        return " ".join(read_aloud(c) for c in children)
    if tag == "mrow":
        return " ".join(read_aloud(c) for c in _children(element))
    if tag in ("mi", "mn", "mtext"):
        return _symbol_reading(_text_of(element))
    if tag == "mo":
        return _symbol_reading(_text_of(element))
    if tag == "mfrac":
        num, den = _children(element)
        return f"the fraction {read_aloud(num)} over {read_aloud(den)}"
    if tag == "msqrt":
        inner = " ".join(read_aloud(c) for c in _children(element))
        return f"the square root of {inner}"
    if tag == "mroot":
        radicand, index = _children(element)
        return f"the {read_aloud(index)}-root of {read_aloud(radicand)}"
    if tag == "msup":
        base, exponent = _children(element)
        exp_text = _text_of(exponent) if _local_tag(exponent) == "mn" else None
        if exp_text in _EXPONENT_WORDS:
            return f"{read_aloud(base)} {_EXPONENT_WORDS[exp_text]}"
        return f"{read_aloud(base)} to the power {read_aloud(exponent)}"
    if tag == "msub":
        base, sub = _children(element)
        return f"{read_aloud(base)} sub {read_aloud(sub)}"
    if tag == "msubsup":
        base, sub, exp = _children(element)
        return f"{read_aloud(base)} sub {read_aloud(sub)} to the power {read_aloud(exp)}"
    # Unrecognized structure: read children in order rather than fail outright.
    return " ".join(read_aloud(c) for c in _children(element))


def _normalize(node: ET.Element) -> ET.Element:
    """Collapse transparent wrapper elements down to the real content.

    ``<math>``/``<semantics>`` only ever appear once, at the very top, each
    wrapping exactly one real content element (plus, for ``semantics``, a
    sibling ``<annotation>``). A single-child ``<mrow>`` is likewise a
    redundant grouping — LaTeX converters wrap even a lone variable in one —
    and collapsing it means navigating never lands on a pointless "Group"
    hop that contains only one thing.
    """
    while True:
        tag = _local_tag(node)
        if tag in ("math", "semantics"):
            children = [c for c in _children(node) if _local_tag(c) != "annotation"]
        elif tag == "mrow":
            children = _children(node)
        else:
            return node
        if len(children) != 1:
            return node
        node = children[0]


@dataclass(frozen=True, slots=True)
class ChildOption:
    """One navigable child of the current node: its index and a label."""

    index: int
    role: str
    label: str


class EquationNavigator:
    """Steps through a parsed equation's structure, one node at a time."""

    def __init__(self, root: ET.Element) -> None:
        self._path: list[ET.Element] = [_normalize(root)]

    @property
    def current(self) -> ET.Element:
        return self._path[-1]

    def at_root(self) -> bool:
        return len(self._path) == 1

    def is_leaf(self) -> bool:
        return len(_children(self.current)) == 0

    def label(self) -> str:
        """A short label for the current node."""
        return node_kind_label(self.current)

    def reading(self) -> str:
        """The full plain-English reading of the current node's subtree."""
        return read_aloud(self.current)

    def child_options(self) -> list[ChildOption]:
        """The navigable children of the current node, with role labels."""
        current = self.current
        tag = _local_tag(current)
        children = _children(current)
        if tag in ("math", "semantics"):
            children = [c for c in children if _local_tag(c) != "annotation"]
        roles = _ROLE_LABELS.get(tag)
        options: list[ChildOption] = []
        for index, child in enumerate(children):
            role = roles[index] if roles and index < len(roles) else ""
            child_label = node_kind_label(child)
            label = f"{role}: {child_label}" if role else child_label
            options.append(ChildOption(index=index, role=role, label=label))
        return options

    def descend(self, index: int) -> None:
        """Move into the child at *index* (as returned by :meth:`child_options`)."""
        current = self.current
        tag = _local_tag(current)
        children = _children(current)
        if tag in ("math", "semantics"):
            children = [c for c in children if _local_tag(c) != "annotation"]
        self._path.append(_normalize(children[index]))

    def ascend(self) -> None:
        """Move back to the parent of the current node. No-op at the root."""
        if len(self._path) > 1:
            self._path.pop()

    def reset(self) -> None:
        """Jump back to the root."""
        del self._path[1:]
