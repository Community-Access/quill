"""Splicing real Word (OMML) equations into the native docx writer.

The native writer (:mod:`quill.io.docx_writer`) has no math model of its own;
this module finds \\(...\\) / $$...$$ spans in plain paragraph text and turns
each into a real <m:oMath> fragment by round-tripping the single equation
through QUILL's existing Pandoc bridge (Pandoc already produces correct OMML
from LaTeX math). When Pandoc is unavailable or a specific equation fails to
convert, the caller keeps the literal delimited text instead of hard-failing
the whole docx write.
"""

from __future__ import annotations

import functools
import re
import tempfile
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path

from defusedxml import ElementTree as DET

from quill.io.pandoc import PandocConversionError, PandocUnavailableError, convert_file_with_pandoc

_MATH_OMML_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"
_MATH_SPAN_RE = re.compile(r"\$\$(.+?)\$\$|\\\((.+?)\\\)", re.DOTALL)


@dataclass(frozen=True, slots=True)
class MathSegment:
    """One piece of a run's text: plain, or a single LaTeX equation."""

    is_math: bool
    content: str
    display: bool = False


def split_math_segments(text: str) -> list[MathSegment]:
    """Split *text* into plain-text and math segments.

    Recognizes ``$$...$$`` (display) and ``\\(...\\)`` (inline) only — matching
    the delimiters ``quill/quillins_bundled/math-equations`` emits. A bare
    ``$`` (e.g. an ordinary dollar amount) is never treated as math.
    """
    segments: list[MathSegment] = []
    pos = 0
    for match in _MATH_SPAN_RE.finditer(text):
        if match.start() > pos:
            segments.append(MathSegment(is_math=False, content=text[pos : match.start()]))
        display_latex, inline_latex = match.group(1), match.group(2)
        if display_latex is not None:
            segments.append(MathSegment(is_math=True, content=display_latex, display=True))
        else:
            segments.append(MathSegment(is_math=True, content=inline_latex, display=False))
        pos = match.end()
    if pos < len(text):
        segments.append(MathSegment(is_math=False, content=text[pos:]))
    if not segments:
        segments.append(MathSegment(is_math=False, content=text))
    return segments


@functools.lru_cache(maxsize=256)
def omml_fragment_for_latex(latex: str, *, display: bool) -> str | None:
    """Return an ``<m:oMath>``/``<m:oMathPara>`` XML fragment for *latex*, or None.

    Returns None (never raises) when Pandoc is unavailable, fails, or the
    conversion produces no math element — callers fall back to plain text.
    Memoized: a document repeating the same formula (or Pandoc being simply
    unavailable) should not spawn a Pandoc subprocess per occurrence.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tmp = Path(tmpdir)
            source = tmp / "eq.md"
            target = tmp / "eq.docx"
            wrapped = f"$${latex}$$" if display else f"${latex}$"
            source.write_text(wrapped, encoding="utf-8")
            convert_file_with_pandoc(source, target, from_format="gfm", to_format="docx")
            with zipfile.ZipFile(target) as archive:
                xml = archive.read("word/document.xml").decode("utf-8")
    except (PandocUnavailableError, PandocConversionError, OSError, KeyError):
        return None

    try:
        root = DET.fromstring(xml)
    except Exception:  # noqa: BLE001 - malformed pandoc output degrades to plain text
        return None
    tag = f"{_MATH_OMML_NS}oMathPara" if display else f"{_MATH_OMML_NS}oMath"
    for element in root.iter(tag):
        return ET.tostring(element, encoding="unicode")
    return None
