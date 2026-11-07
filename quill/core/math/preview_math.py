"""TeX math in Markdown rendered as MathML, for preview and HTML export.

The preview and the exported page used to load MathJax from a CDN, which made
a network request and left the math unreadable offline. MathML needs no
script: browsers draw it, and screen readers with a math engine (NVDA's
MathCAT, JAWS) read and navigate it themselves.

The renderer that turns Markdown into HTML knows nothing about math, and would
read the underscores in ``a_1`` as emphasis, so math is lifted out first.
:func:`protect_math` swaps every math span for a plain token, the Markdown is
rendered, and :func:`restore_math` puts MathML where the tokens landed. Code
spans and fenced code are left alone. Line count is preserved so the preview's
source map still points at the right lines.

When the optional ``latex2mathml`` package is missing, or one formula will not
convert, that formula is left as its TeX source text: still readable, and still
nothing fetched.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field

_TOKEN = "QUILLMATHSPAN{index}Z"
_TOKEN_RE = re.compile(r"QUILLMATHSPAN(\d+)Z")
_CODE_FENCE_RE = re.compile(r"^\s{0,3}(`{3,}|~{3,})\s*([^\s`]*)")
_DISPLAY_OPEN = {"$$": "$$", "\\[": "\\]"}
_INLINE_RE = re.compile(r"\$\$(.+?)\$\$|\\\[(.+?)\\\]|\\\((.+?)\\\)")
_CODE_SPAN_RE = re.compile(r"(`+)(?:.+?)\1")


@dataclass(slots=True)
class ProtectedMath:
    """Markdown with its math swapped for tokens, and the math that was taken."""

    text: str
    spans: list[tuple[str, str]] = field(default_factory=list)  # (latex, display)


def protect_math(text: str) -> ProtectedMath:
    """Replace every math span in Markdown *text* with a token."""

    result = ProtectedMath(text="")
    out: list[str] = []
    lines = text.splitlines(keepends=True)
    index = 0
    while index < len(lines):
        raw = lines[index]
        line = raw.rstrip("\r\n")
        ending = raw[len(line) :]
        fence = _CODE_FENCE_RE.match(line)
        if fence is not None:
            marker = fence.group(1)
            close = re.compile(rf"^\s{{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$")
            end = index + 1
            while end < len(lines) and close.match(lines[end].rstrip("\r\n")) is None:
                end += 1
            if fence.group(2).lower() == "math":
                latex = "".join(lines[index + 1 : end]).strip()
                closing = lines[end] if end < len(lines) else ending
                out.append(_token(result, latex, "block") + _ending_of(closing))
                out.extend(_blank_like(lines[index + 1 : end + 1]))
            else:
                out.extend(lines[index : end + 1])
            index = end + 1
            continue
        stripped = line.strip()
        if stripped in _DISPLAY_OPEN:
            closer = _DISPLAY_OPEN[stripped]
            end = index + 1
            while end < len(lines) and lines[end].strip() != closer:
                end += 1
            if end < len(lines):
                latex = "".join(lines[index + 1 : end]).strip()
                out.append(_token(result, latex, "block") + _ending_of(lines[end]))
                out.extend(_blank_like(lines[index + 1 : end + 1]))
                index = end + 1
                continue
        out.append(_protect_inline(result, line) + ending)
        index += 1
    result.text = "".join(out)
    return result


def restore_math(rendered: str, protected: ProtectedMath) -> str:
    """Put MathML (or the escaped TeX) where :func:`protect_math` left tokens."""

    if not protected.spans:
        return rendered

    def swap(match: re.Match[str]) -> str:
        number = int(match.group(1))
        if number >= len(protected.spans):
            return match.group(0)
        latex, display = protected.spans[number]
        return latex_to_html(latex, display)

    return _TOKEN_RE.sub(swap, rendered)


def dollar_math(text: str) -> str:
    """Rewrite every math span with dollar delimiters, for Pandoc's GFM reader.

    That reader knows ``$...$``, ``$$...$$`` and fenced ``math`` blocks but
    reads ``\\(x\\)`` as an escaped bracket, and QUILL's Insert Equation writes
    that spelling. Code is left alone, and line numbers do not move.
    """

    protected = protect_math(text)
    if not protected.spans:
        return text

    def swap(match: re.Match[str]) -> str:
        number = int(match.group(1))
        if number >= len(protected.spans):
            return match.group(0)
        latex, display = protected.spans[number]
        return f"$${latex}$$" if display == "block" else f"${latex}$"

    return _TOKEN_RE.sub(swap, protected.text)


def latex_to_html(latex: str, display: str = "inline") -> str:
    """MathML for *latex*, or its escaped source when it cannot be converted."""

    try:
        from quill.core.math.latex_bridge import latex_to_mathml

        return latex_to_mathml(latex, display=display)
    except Exception:  # noqa: BLE001 - missing extra or a formula it cannot parse
        return f'<span class="math-source">{html.escape(latex)}</span>'


def _protect_inline(result: ProtectedMath, line: str) -> str:
    pieces: list[str] = []
    position = 0
    for code in _CODE_SPAN_RE.finditer(line):
        pieces.append(_swap_inline(result, line[position : code.start()]))
        pieces.append(code.group(0))
        position = code.end()
    pieces.append(_swap_inline(result, line[position:]))
    return "".join(pieces)


def _swap_inline(result: ProtectedMath, segment: str) -> str:
    def swap(match: re.Match[str]) -> str:
        if match.group(3) is not None:
            return _token(result, match.group(3).strip(), "inline")
        latex = match.group(1) if match.group(1) is not None else match.group(2)
        return _token(result, latex.strip(), "block")

    return _INLINE_RE.sub(swap, segment)


def _token(result: ProtectedMath, latex: str, display: str) -> str:
    result.spans.append((latex, display))
    return _TOKEN.format(index=len(result.spans) - 1)


def _ending_of(raw: str) -> str:
    stripped = raw.rstrip("\r\n")
    return raw[len(stripped) :] or "\n"


def _blank_like(lines: list[str]) -> list[str]:
    """One empty line for each consumed line, so line numbers do not shift."""

    return [_ending_of(line) for line in lines]
