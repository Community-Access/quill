"""Canonical MathML equation model — the in-memory form every math feature shares.

MathML (not LaTeX, not a custom AST) is the canonical representation: it is
the format MathCAT, screen readers, and MathML-aware exporters already expect.
The original LaTeX source, when known, is preserved by embedding it as a
``semantics``/``annotation`` pair — the same interop convention MathJax's own
``tex2mathml`` output uses — so a round-trip to editable LaTeX text never
requires a general MathML-to-LaTeX parser.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import cast

from defusedxml import ElementTree as DET

from quill.core.error_codes import CodedError

MATHML_NS = "http://www.w3.org/1998/Math/MathML"
TEX_ANNOTATION_ENCODING = "application/x-tex"

ET.register_namespace("", MATHML_NS)


class MathMLError(CodedError):
    """Raised when a string is not well-formed MathML."""

    code = "QUILL-MATH-MATHML-FAILED"


@dataclass(frozen=True, slots=True)
class Equation:
    """A canonical math equation: MathML plus its LaTeX source, when known."""

    mathml: str
    latex: str | None = None


def parse_mathml(text: str) -> ET.Element:
    """Parse *text* as MathML, raising :class:`MathMLError` on malformed input.

    Uses defusedxml because the input may originate from an imported document
    or a Quillin, not only from QUILL's own LaTeX bridge.
    """
    try:
        root = cast(ET.Element, DET.fromstring(text))
    except Exception as exc:  # noqa: BLE001 - defusedxml raises varied XML error types
        raise MathMLError(str(exc) or type(exc).__name__) from exc
    if root.tag not in (f"{{{MATHML_NS}}}math", "math"):
        raise MathMLError(f"root element is not <math>: {root.tag}")
    return root


def is_valid_mathml(text: str) -> bool:
    """Return True when *text* parses as well-formed MathML with a <math> root."""
    try:
        parse_mathml(text)
    except MathMLError:
        return False
    return True


def wrap_with_tex_annotation(mathml: str, latex: str) -> str:
    """Return *mathml* rewritten with *latex* embedded as a semantics/annotation."""
    root = parse_mathml(mathml)
    children = list(root)
    content = children[0] if len(children) == 1 else _wrap_in_mrow(children)

    semantics = ET.Element(f"{{{MATHML_NS}}}semantics")
    semantics.append(content)
    annotation = ET.SubElement(
        semantics, f"{{{MATHML_NS}}}annotation", {"encoding": TEX_ANNOTATION_ENCODING}
    )
    annotation.text = latex

    new_root = ET.Element(f"{{{MATHML_NS}}}math", dict(root.attrib))
    new_root.append(semantics)
    return ET.tostring(new_root, encoding="unicode")


def extract_tex_annotation(mathml: str) -> str | None:
    """Return the LaTeX source embedded in *mathml*'s annotation, or None."""
    root = parse_mathml(mathml)
    for annotation in root.iter(f"{{{MATHML_NS}}}annotation"):
        if annotation.get("encoding") == TEX_ANNOTATION_ENCODING:
            return annotation.text or ""
    return None


def _wrap_in_mrow(children: list[ET.Element]) -> ET.Element:
    mrow = ET.Element(f"{{{MATHML_NS}}}mrow")
    mrow.extend(children)
    return mrow
