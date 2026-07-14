"""LaTeX <-> MathML conversion bridge.

Only LaTeX -> MathML is a real conversion (the underlying ``latex2mathml``
library has no converse direction). MathML -> LaTeX recovers the original
source when it was embedded by :func:`latex_to_mathml`; MathML that never came
from LaTeX (e.g. an imported docx equation) has no LaTeX form to recover, so
:func:`mathml_to_latex` returns None for it rather than guessing.

``latex2mathml`` is the optional ``math`` extra (docs/planning/math.md, Tier
1-B); when it is not installed, :func:`latex_to_mathml` raises
:class:`LatexBridgeUnavailable` rather than importing at module load time.
"""

from __future__ import annotations

from quill.core.error_codes import CodedError

from .mathml import extract_tex_annotation, wrap_with_tex_annotation

try:
    import latex2mathml.converter as _converter
except ImportError:  # pragma: no cover - exercised only when the math extra is absent
    _converter = None  # type: ignore[assignment]


class LatexConversionError(CodedError):
    """Raised when *latex* cannot be converted to MathML."""

    code = "QUILL-MATH-LATEX-CONVERT"


class LatexBridgeUnavailable(CodedError):
    """Raised when the optional ``latex2mathml`` dependency is not installed."""

    code = "QUILL-MATH-LATEX-UNAVAILABLE"


def latex_to_mathml(latex: str, *, display: str = "inline") -> str:
    """Convert *latex* to canonical MathML with the source embedded for round-trip."""
    if _converter is None:
        raise LatexBridgeUnavailable("latex2mathml is not installed; install the 'math' extra")
    try:
        raw = _converter.convert(latex, display=display)
    except Exception as exc:  # noqa: BLE001 - latex2mathml raises many distinct error types
        raise LatexConversionError(str(exc) or type(exc).__name__) from exc
    return wrap_with_tex_annotation(raw, latex)


def mathml_to_latex(mathml: str) -> str | None:
    """Return the LaTeX source embedded in *mathml*, or None if it has none."""
    return extract_tex_annotation(mathml)
