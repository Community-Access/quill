"""A wx-free rich-text model for QUILL's native RTF editing surface.

Part One of ``docs/QUILL-PRD.md`` introduces an optional rich editing surface backed by
``wx.RichTextCtrl``. The control itself lives in ``quill/ui`` (wx is forbidden in
``quill/core`` and ``quill/io``); this module is the pure, testable model the
control reads and writes through.

The design keeps QUILL's Markdown-style markup as the *canonical* document text so
every existing ``core`` feature (search, metrics, outline, autosave) keeps working
unchanged. The rich model is an **overlay** over that markup:

* :class:`RichDocument` is the structured view used to drive native formatting.
* :func:`markdown_to_rich` / :func:`rich_to_markdown` convert between the canonical
  markup and the model.
* :func:`rtf_to_rich` / :func:`rich_to_rtf` reuse the existing EDS-21 RTF
  round-trip in :mod:`quill.io.rtf`, so there is a single RTF serializer.
* :func:`analyze_markdown` exposes the character-level mapping between the markup
  string (what the plain lens edits) and the visible text (what the rich lens
  shows). The UI uses it to keep the caret on the same word when a writer switches
  lenses, and to answer "what formatting is under the caret" for spoken cues.

The supported inline subset matches the canonical markup grammar: ``**bold**``,
``*italic*`` and ``[label](url)`` links, plus heading and bullet paragraph styles.
The "hidden codes" design note
(``the QUILL PRD hidden-codes appendix``) extends that grammar with a
small, explicit-value vocabulary that is invisible in the editor and materialized
only at export:

* Inline runs gain ``font-family``, ``font-size`` (points), ``color``,
  ``highlight``, ``underline``, ``strike``, ``superscript`` and ``subscript``,
  carried as Pandoc attribute spans ``[text]{font-family="Arial" font-size="14"}``.
* Paragraphs gain block attributes carried as Pandoc fenced divs
  ``::: {align="center" line-spacing="1.5"}`` ... ``:::`` — ``align``
  (``left``/``right``/``center``/``justify``), ``pstyle`` (a named Word style:
  ``quote``/``title``/``subtitle``/``caption``), ``line-spacing``
  (``1``/``1.5``/``2``), ``space-before``/``space-after`` (points),
  ``indent`` (left indent, points) and ``first-line-indent`` (points).
* A page break is the standalone marker line ``::: pagebreak``.

Span, div and page-break markup is consumed without contributing visible
characters, exactly like ``**`` is, so caret-offset tracking stays correct.
Anything an RTF file carries beyond the readable subset is flattened by the
existing round-trip; :func:`scan_rtf_features` reports such cases so the UI can
warn before a lossy conversion.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field, replace

from quill.core.heading_styles import _ALLOWED_TEXT_ALIGN
from quill.io.rtf import markdown_to_rtf, rtf_to_markdown

__all__ = [
    "InlineSpan",
    "RichParagraph",
    "RichDocument",
    "InlineFormat",
    "MarkdownSegment",
    "MarkdownAnalysis",
    "markdown_to_rich",
    "rich_to_markdown",
    "rtf_to_rich",
    "rich_to_rtf",
    "analyze_markdown",
    "format_at_markdown_offset",
    "markdown_offset_to_plain_offset",
    "plain_offset_to_markdown_offset",
    "scan_rtf_features",
    "parse_span_attributes",
    "ALLOWED_LINE_SPACING",
    "NAMED_PARAGRAPH_STYLES",
]

_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
_LIST_RE = re.compile(r"^[-*]\s+(.*)$")
_LINK_MD_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
_SPAN_MD_RE = re.compile(r"\[([^\]]+)\]\{([^}]*)\}")

# Pandoc fenced div: ``::: {align="center"}`` opens, a bare ``:::`` closes; the
# standalone ``::: pagebreak`` marker is its own line.
_FENCE_OPEN_RE = re.compile(r"^:::+\s*\{([^}]*)\}\s*$")
_FENCE_CLOSE_RE = re.compile(r"^:::+\s*$")
_PAGEBREAK_RE = re.compile(r"^:::+\s*pagebreak\s*$", re.IGNORECASE)

# Whitespace-separated ``key="value"`` pairs (and bare flag tokens such as
# ``underline``) inside a span ``{...}`` or fenced-div header.
_ATTR_PAIR_RE = re.compile(r'([A-Za-z][\w-]*)\s*=\s*"([^"]*)"|([A-Za-z][\w-]*)')

#: Line-spacing values the model recognizes (a single, double, or 1.5 lines).
ALLOWED_LINE_SPACING = {"1", "1.5", "2"}
#: Named Word paragraph styles the ``pstyle`` block attribute accepts.
NAMED_PARAGRAPH_STYLES = {"quote", "title", "subtitle", "caption"}

#: Block-attribute field names, in materialization order, shared by the parser,
#: the emitter and the per-character analysis.
_BLOCK_FIELDS = (
    "align",
    "named_style",
    "line_spacing",
    "space_before",
    "space_after",
    "indent",
    "first_line_indent",
)
_EMPTY_BLOCK: dict[str, object] = dict.fromkeys(_BLOCK_FIELDS, None)


def parse_span_attributes(raw: str) -> dict[str, str]:
    """Parse a Pandoc attribute string into a ``{key: value}`` map.

    Handles whitespace-separated ``font-family="Arial" font-size="14"`` pairs and
    bare flag tokens (``underline``), which map to an empty-string value. Unlike
    :func:`quill.core.tagging.parse_attribute_pairs` (comma/semicolon separated),
    this matches the space-separated grammar Pandoc spans and divs actually use.
    """
    attrs: dict[str, str] = {}
    for match in _ATTR_PAIR_RE.finditer(raw):
        if match.group(1) is not None:
            attrs[match.group(1).lower()] = match.group(2)
        elif match.group(3) is not None:
            attrs.setdefault(match.group(3).lower(), "")
    return attrs


def _coerce_size(value: str) -> int | None:
    try:
        size = int(round(float(value)))
    except (TypeError, ValueError):
        return None
    return size if size > 0 else None


# --------------------------------------------------------------------------- #
# Model
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class InlineSpan:
    """A run of text sharing the same inline formatting."""

    text: str
    bold: bool = False
    italic: bool = False
    href: str | None = None
    underline: bool = False
    strike: bool = False
    superscript: bool = False
    subscript: bool = False
    font_family: str | None = None
    font_size_pt: int | None = None
    color: str | None = None
    highlight: str | None = None


@dataclass(slots=True)
class RichParagraph:
    """A paragraph: spans plus paragraph-level style and block formatting.

    ``style`` is one of ``"paragraph"``, ``"heading"``, ``"bullet"`` or
    ``"pagebreak"``. ``level`` carries the heading level (1-6) when
    ``style == "heading"``; it is ``0`` otherwise. The block attributes
    (``align``, ``named_style``, ``line_spacing``, ``space_before``,
    ``space_after``, ``indent``, ``first_line_indent``) come from an enclosing
    alignment/style fenced div and are ``None`` when unset.
    """

    spans: list[InlineSpan] = field(default_factory=list)
    style: str = "paragraph"
    level: int = 0
    align: str | None = None
    named_style: str | None = None
    line_spacing: str | None = None
    space_before: int | None = None
    space_after: int | None = None
    indent: int | None = None
    first_line_indent: int | None = None

    def text(self) -> str:
        """Return the visible text of this paragraph (no markup, no prefix)."""
        return "".join(span.text for span in self.spans)

    def block_key(self) -> tuple[object, ...]:
        return tuple(getattr(self, name) for name in _BLOCK_FIELDS)

    def has_block(self) -> bool:
        return any(self.block_key())


@dataclass(slots=True)
class RichDocument:
    """An ordered list of paragraphs forming a rich document."""

    paragraphs: list[RichParagraph] = field(default_factory=list)

    def plain_text(self) -> str:
        """Return the visible text of the whole document, one line per paragraph.

        Heading hashes and bullet dashes are *structure*, not content, so they are
        excluded. This is the text used for word counts, search and read-aloud when
        the rich lens is active.
        """
        return "\n".join(paragraph.text() for paragraph in self.paragraphs)


@dataclass(slots=True)
class InlineFormat:
    """The formatting in effect at a point in the document."""

    bold: bool = False
    italic: bool = False
    href: str | None = None
    heading_level: int = 0
    bullet: bool = False
    underline: bool = False
    strike: bool = False
    superscript: bool = False
    subscript: bool = False
    font_family: str | None = None
    font_size_pt: int | None = None
    color: str | None = None
    highlight: str | None = None
    align: str | None = None
    named_style: str | None = None
    line_spacing: str | None = None
    space_before: int | None = None
    space_after: int | None = None
    indent: int | None = None
    first_line_indent: int | None = None


# --------------------------------------------------------------------------- #
# Inline attribute state carried while walking markup
# --------------------------------------------------------------------------- #
@dataclass(frozen=True, slots=True)
class _Attrs:
    """Immutable inline formatting state; hashable so runs group by equality."""

    bold: bool = False
    italic: bool = False
    href: str | None = None
    underline: bool = False
    strike: bool = False
    superscript: bool = False
    subscript: bool = False
    font_family: str | None = None
    font_size_pt: int | None = None
    color: str | None = None
    highlight: str | None = None


def _merge_span_attrs(base: _Attrs, raw: str) -> _Attrs:
    """Fold a span attribute string onto the active inline state."""
    parsed = parse_span_attributes(raw)
    return replace(
        base,
        underline=base.underline or "underline" in parsed,
        strike=base.strike or "strike" in parsed,
        superscript=base.superscript or "superscript" in parsed,
        subscript=base.subscript or "subscript" in parsed,
        font_family=parsed.get("font-family") or base.font_family,
        font_size_pt=_coerce_size(parsed.get("font-size", "")) or base.font_size_pt,
        color=parsed.get("color") or base.color,
        highlight=parsed.get("highlight") or base.highlight,
    )


# --------------------------------------------------------------------------- #
# Inline parsing with offset tracking
# --------------------------------------------------------------------------- #
def _walk_inline(
    text: str,
    base: int,
    current: _Attrs,
    plain_chars: list[str],
    md_index: list[int],
    attrs: list[_Attrs],
) -> None:
    """Walk an inline fragment, recording each visible character.

    ``base`` is the absolute offset of ``text`` within the full markup string so the
    recorded ``md_index`` values are absolute. Markup characters (``**``, ``*``,
    link and span syntax) are consumed but never contribute a visible character.
    """
    index = 0
    length = len(text)
    while index < length:
        link = _LINK_MD_RE.match(text, index)
        if link:
            _walk_inline(
                link.group(1),
                base + link.start(1),
                replace(current, href=link.group(2)),
                plain_chars,
                md_index,
                attrs,
            )
            index = link.end()
            continue
        span = _SPAN_MD_RE.match(text, index)
        if span:
            _walk_inline(
                span.group(1),
                base + span.start(1),
                _merge_span_attrs(current, span.group(2)),
                plain_chars,
                md_index,
                attrs,
            )
            index = span.end()
            continue
        if text.startswith("**", index):
            close = text.find("**", index + 2)
            if close != -1:
                _walk_inline(
                    text[index + 2 : close],
                    base + index + 2,
                    replace(current, bold=True),
                    plain_chars,
                    md_index,
                    attrs,
                )
                index = close + 2
                continue
        if text[index] == "*":
            close = text.find("*", index + 1)
            if close != -1:
                _walk_inline(
                    text[index + 1 : close],
                    base + index + 1,
                    replace(current, italic=True),
                    plain_chars,
                    md_index,
                    attrs,
                )
                index = close + 1
                continue
        plain_chars.append(text[index])
        md_index.append(base + index)
        attrs.append(current)
        index += 1


def _span_from_attrs(char: str, attr: _Attrs) -> InlineSpan:
    return InlineSpan(
        char,
        bold=attr.bold,
        italic=attr.italic,
        href=attr.href,
        underline=attr.underline,
        strike=attr.strike,
        superscript=attr.superscript,
        subscript=attr.subscript,
        font_family=attr.font_family,
        font_size_pt=attr.font_size_pt,
        color=attr.color,
        highlight=attr.highlight,
    )


def _spans_from_attr_runs(chars: list[str], attrs: list[_Attrs]) -> list[InlineSpan]:
    spans: list[InlineSpan] = []
    last: _Attrs | None = None
    for char, attr in zip(chars, attrs, strict=True):
        if spans and attr == last:
            spans[-1].text += char
        else:
            spans.append(_span_from_attrs(char, attr))
            last = attr
    return spans


# --------------------------------------------------------------------------- #
# Block (paragraph) scanning: alignment, named style, spacing, indent, page break
# --------------------------------------------------------------------------- #
def _parse_block(raw: str) -> dict[str, object]:
    """Parse a fenced-div header into the normalized block-attribute map."""
    parsed = parse_span_attributes(raw)
    align = parsed.get("align")
    named = parsed.get("pstyle", "").lower()
    spacing = parsed.get("line-spacing")
    return {
        "align": align if align in _ALLOWED_TEXT_ALIGN else None,
        "named_style": named if named in NAMED_PARAGRAPH_STYLES else None,
        "line_spacing": spacing if spacing in ALLOWED_LINE_SPACING else None,
        "space_before": _coerce_size(parsed.get("space-before", "")),
        "space_after": _coerce_size(parsed.get("space-after", "")),
        "indent": _coerce_size(parsed.get("indent", "")),
        "first_line_indent": _coerce_size(parsed.get("first-line-indent", "")),
    }


def _classify_lines(lines: list[str]) -> list[tuple[str, dict[str, object]]]:
    """Classify each source line as ``(kind, block)``.

    ``kind`` is ``"open"``/``"close"`` (fence markers, no visible text),
    ``"pagebreak"`` (the standalone marker), or ``"content"``. ``block`` is the
    block-attribute map in effect for a content line (inherited from the enclosing
    open fence), else :data:`_EMPTY_BLOCK`.
    """
    result: list[tuple[str, dict[str, object]]] = []
    current = _EMPTY_BLOCK
    for line in lines:
        if _PAGEBREAK_RE.match(line):
            result.append(("pagebreak", _EMPTY_BLOCK))
            continue
        opener = _FENCE_OPEN_RE.match(line)
        if opener:
            current = _parse_block(opener.group(1))
            result.append(("open", _EMPTY_BLOCK))
            continue
        if _FENCE_CLOSE_RE.match(line):
            current = _EMPTY_BLOCK
            result.append(("close", _EMPTY_BLOCK))
            continue
        result.append(("content", current))
    return result


# --------------------------------------------------------------------------- #
# Markdown <-> rich model
# --------------------------------------------------------------------------- #
def markdown_to_rich(markdown: str) -> RichDocument:
    """Convert canonical QUILL markup into a :class:`RichDocument`."""
    paragraphs: list[RichParagraph] = []
    lines = markdown.split("\n")
    for line, (kind, block) in zip(lines, _classify_lines(lines), strict=True):
        if kind in ("open", "close"):
            continue
        if kind == "pagebreak":
            paragraphs.append(RichParagraph(style="pagebreak"))
            continue
        style = "paragraph"
        level = 0
        content = line
        heading = _HEADING_RE.match(line)
        if heading:
            style = "heading"
            level = len(heading.group(1))
            content = heading.group(2)
        else:
            item = _LIST_RE.match(line)
            if item:
                style = "bullet"
                content = item.group(1)
        chars: list[str] = []
        md_index: list[int] = []
        attrs: list[_Attrs] = []
        _walk_inline(content, 0, _Attrs(), chars, md_index, attrs)
        spans = _spans_from_attr_runs(chars, attrs)
        paragraphs.append(RichParagraph(spans=spans, style=style, level=level, **block))  # type: ignore[arg-type]
    return RichDocument(paragraphs=paragraphs)


def _span_attr_markup(span: InlineSpan) -> str:
    """Render the run-level extras of ``span`` as a Pandoc attribute string."""
    parts: list[str] = []
    if span.font_family:
        parts.append(f'font-family="{span.font_family}"')
    if span.font_size_pt is not None and span.font_size_pt > 0:
        parts.append(f'font-size="{span.font_size_pt}"')
    if span.color:
        parts.append(f'color="{span.color}"')
    if span.highlight:
        parts.append(f'highlight="{span.highlight}"')
    if span.underline:
        parts.append("underline")
    if span.strike:
        parts.append("strike")
    if span.superscript:
        parts.append("superscript")
    if span.subscript:
        parts.append("subscript")
    return " ".join(parts)


def _span_to_markdown(span: InlineSpan) -> str:
    body = span.text
    if span.italic:
        body = f"*{body}*"
    if span.bold:
        body = f"**{body}**"
    if span.href:
        return f"[{body}]({span.href})"
    attr = _span_attr_markup(span)
    if attr:
        return f"[{body}]{{{attr}}}"
    return body


def _span_key(span: InlineSpan) -> tuple[object, ...]:
    return (
        span.bold,
        span.italic,
        span.href,
        span.underline,
        span.strike,
        span.superscript,
        span.subscript,
        span.font_family,
        span.font_size_pt,
        span.color,
        span.highlight,
    )


def _merge_spans(spans: list[InlineSpan]) -> list[InlineSpan]:
    merged: list[InlineSpan] = []
    for span in spans:
        if merged and _span_key(merged[-1]) == _span_key(span):
            merged[-1].text += span.text
        else:
            merged.append(replace(span))
    return merged


def _paragraph_to_markdown(paragraph: RichParagraph) -> str:
    inline = "".join(_span_to_markdown(span) for span in _merge_spans(paragraph.spans))
    if paragraph.style == "heading":
        level = min(max(paragraph.level, 1), 6)
        return f"{'#' * level} {inline}"
    if paragraph.style == "bullet":
        return f"- {inline}"
    return inline


def _block_markup(paragraph: RichParagraph) -> str:
    parts: list[str] = []
    if paragraph.align:
        parts.append(f'align="{paragraph.align}"')
    if paragraph.named_style:
        parts.append(f'pstyle="{paragraph.named_style}"')
    if paragraph.line_spacing:
        parts.append(f'line-spacing="{paragraph.line_spacing}"')
    if paragraph.space_before:
        parts.append(f'space-before="{paragraph.space_before}"')
    if paragraph.space_after:
        parts.append(f'space-after="{paragraph.space_after}"')
    if paragraph.indent:
        parts.append(f'indent="{paragraph.indent}"')
    if paragraph.first_line_indent:
        parts.append(f'first-line-indent="{paragraph.first_line_indent}"')
    return " ".join(parts)


def rich_to_markdown(document: RichDocument) -> str:
    """Render a :class:`RichDocument` back to canonical QUILL markup.

    Consecutive paragraphs sharing the same block attributes are wrapped in a
    single fenced div so the round trip with :func:`markdown_to_rich` is an
    identity. Page breaks emit the standalone ``::: pagebreak`` marker.
    """
    lines: list[str] = []
    open_key: tuple[object, ...] | None = None
    for paragraph in document.paragraphs:
        if paragraph.style == "pagebreak":
            if open_key is not None:
                lines.append(":::")
                open_key = None
            lines.append("::: pagebreak")
            continue
        key = paragraph.block_key() if paragraph.has_block() else None
        if key != open_key:
            if open_key is not None:
                lines.append(":::")
            if key is not None:
                lines.append(f"::: {{{_block_markup(paragraph)}}}")
            open_key = key
        lines.append(_paragraph_to_markdown(paragraph))
    if open_key is not None:
        lines.append(":::")
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# RTF <-> rich model (single serializer via quill.io.rtf)
# --------------------------------------------------------------------------- #
def rtf_to_rich(rtf: str) -> RichDocument:
    """Parse an RTF document string into a :class:`RichDocument`.

    Reuses the EDS-21 RTF reader, so the supported subset is the canonical markup
    subset (headings, bold, italic, bullets, links) plus the run attributes the
    reader now recovers (underline, strike, super/subscript, color, highlight).
    """
    return markdown_to_rich(rtf_to_markdown(rtf))


def rich_to_rtf(document: RichDocument) -> str:
    """Serialize a :class:`RichDocument` to a valid RTF document string."""
    return markdown_to_rtf(rich_to_markdown(document))


# --------------------------------------------------------------------------- #
# Offset mapping between markup and visible text
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class MarkdownSegment:
    """A visible character's place in both coordinate spaces."""

    md_offset: int
    plain_offset: int
    bold: bool
    italic: bool
    href: str | None
    heading_level: int
    bullet: bool
    underline: bool = False
    strike: bool = False
    superscript: bool = False
    subscript: bool = False
    font_family: str | None = None
    font_size_pt: int | None = None
    color: str | None = None
    highlight: str | None = None
    align: str | None = None
    named_style: str | None = None
    line_spacing: str | None = None
    space_before: int | None = None
    space_after: int | None = None
    indent: int | None = None
    first_line_indent: int | None = None


@dataclass(slots=True)
class MarkdownAnalysis:
    """The character-level relationship between markup and visible text."""

    plain_text: str
    segments: list[MarkdownSegment]
    md_to_plain: list[int]

    def heading_level_at_plain(self, plain_offset: int) -> int:
        seg = self._segment_at_plain(plain_offset)
        return seg.heading_level if seg is not None else 0

    def _segment_at_plain(self, plain_offset: int) -> MarkdownSegment | None:
        if not self.segments:
            return None
        index = min(max(plain_offset, 0), len(self.segments) - 1)
        return self.segments[index]


def analyze_markdown(markdown: str) -> MarkdownAnalysis:
    """Build the full mapping between a markup string and its visible text.

    ``md_to_plain`` has one entry per markup character (plus a trailing entry for
    the end-of-string caret position) giving the visible offset that character maps
    to. Markup-only characters (heading hashes, bullet dashes, emphasis markers,
    link/span syntax, and whole ``:::`` fence / page-break lines) map to the visible
    offset of the next visible character, so a caret sitting on markup lands
    sensibly in the rich lens.
    """
    plain_parts: list[str] = []
    segments: list[MarkdownSegment] = []
    length = len(markdown)
    # -1 marks "not a visible character yet"; a backward pass fills markup gaps.
    md_to_plain = [-1] * (length + 1)
    plain_cursor = 0
    md_line_start = 0
    visible_emitted = 0
    lines = markdown.split("\n")
    for line, (kind, block) in zip(lines, _classify_lines(lines), strict=True):
        if kind != "content":
            # Whole fence / page-break lines are structure: no visible text, no
            # visible newline. Their characters inherit the next visible offset via
            # the backward pass below.
            md_line_start += len(line) + 1
            continue

        if visible_emitted > 0:
            # The newline that ended the previous source line is visible in both
            # spaces. md_line_start - 1 is that newline regardless of skipped fences.
            md_to_plain[md_line_start - 1] = plain_cursor
            plain_parts.append("\n")
            plain_cursor += 1

        style = "paragraph"
        level = 0
        bullet = False
        content_offset = 0
        content = line
        heading = _HEADING_RE.match(line)
        if heading:
            style = "heading"
            level = len(heading.group(1))
            content_offset = heading.start(2)
            content = heading.group(2)
        else:
            item = _LIST_RE.match(line)
            if item:
                style = "bullet"
                bullet = True
                content_offset = item.start(1)
                content = item.group(1)

        chars: list[str] = []
        rel_md: list[int] = []
        attrs: list[_Attrs] = []
        _walk_inline(content, 0, _Attrs(), chars, rel_md, attrs)

        for visible_index, (char, rel, attr) in enumerate(zip(chars, rel_md, attrs, strict=True)):
            abs_md = md_line_start + content_offset + rel
            plain_offset = plain_cursor + visible_index
            md_to_plain[abs_md] = plain_offset
            plain_parts.append(char)
            segments.append(
                MarkdownSegment(
                    md_offset=abs_md,
                    plain_offset=plain_offset,
                    bold=attr.bold,
                    italic=attr.italic,
                    href=attr.href,
                    heading_level=level if style == "heading" else 0,
                    bullet=bullet,
                    underline=attr.underline,
                    strike=attr.strike,
                    superscript=attr.superscript,
                    subscript=attr.subscript,
                    font_family=attr.font_family,
                    font_size_pt=attr.font_size_pt,
                    color=attr.color,
                    highlight=attr.highlight,
                    align=block["align"],  # type: ignore[arg-type]
                    named_style=block["named_style"],  # type: ignore[arg-type]
                    line_spacing=block["line_spacing"],  # type: ignore[arg-type]
                    space_before=block["space_before"],  # type: ignore[arg-type]
                    space_after=block["space_after"],  # type: ignore[arg-type]
                    indent=block["indent"],  # type: ignore[arg-type]
                    first_line_indent=block["first_line_indent"],  # type: ignore[arg-type]
                )
            )
        plain_cursor += len(chars)
        md_line_start += len(line) + 1
        visible_emitted += 1

    # Markup-only characters inherit the visible offset of the next visible
    # character. Walking backward propagates the next mapped value.
    running = plain_cursor
    for index in range(length, -1, -1):
        if md_to_plain[index] == -1:
            md_to_plain[index] = running
        else:
            running = md_to_plain[index]
    return MarkdownAnalysis(
        plain_text="".join(plain_parts), segments=segments, md_to_plain=md_to_plain
    )


def markdown_offset_to_plain_offset(markdown: str, offset: int) -> int:
    """Map a caret offset in the markup string to the visible-text offset."""
    analysis = analyze_markdown(markdown)
    clamped = min(max(offset, 0), len(markdown))
    return analysis.md_to_plain[clamped]


def plain_offset_to_markdown_offset(markdown: str, plain_offset: int) -> int:
    """Map a visible-text caret offset back to the markup string."""
    analysis = analyze_markdown(markdown)
    target = min(max(plain_offset, 0), len(analysis.plain_text))
    for segment in analysis.segments:
        if segment.plain_offset == target:
            return segment.md_offset
    return len(markdown)


def format_at_markdown_offset(markdown: str, offset: int) -> InlineFormat:
    """Return the :class:`InlineFormat` in effect at a markup caret offset.

    The caret reports the formatting of the character to its left (the run it is
    extending), matching how screen readers describe the caret context.
    """
    analysis = analyze_markdown(markdown)
    if not analysis.segments:
        return InlineFormat()
    plain_offset = analysis.md_to_plain[min(max(offset, 0), len(markdown))]
    index = plain_offset - 1
    if index < 0:
        index = 0
    index = min(index, len(analysis.segments) - 1)
    segment = analysis.segments[index]
    return InlineFormat(
        bold=segment.bold,
        italic=segment.italic,
        href=segment.href,
        heading_level=segment.heading_level,
        bullet=segment.bullet,
        underline=segment.underline,
        strike=segment.strike,
        superscript=segment.superscript,
        subscript=segment.subscript,
        font_family=segment.font_family,
        font_size_pt=segment.font_size_pt,
        color=segment.color,
        highlight=segment.highlight,
        align=segment.align,
        named_style=segment.named_style,
        line_spacing=segment.line_spacing,
        space_before=segment.space_before,
        space_after=segment.space_after,
        indent=segment.indent,
        first_line_indent=segment.first_line_indent,
    )


# --------------------------------------------------------------------------- #
# Fidelity reporting
# --------------------------------------------------------------------------- #
# RTF control words that carry content the canonical markup subset cannot express.
# Their presence means a round trip through QUILL markup would flatten something.
# Underline, color, highlight, strikethrough and super/subscript are now recovered
# by the RTF reader, so they are no longer listed; tables, images, footnotes etc.
# remain unsupported and are still reported.
_UNSUPPORTED_FEATURES: dict[str, str] = {
    r"\\trowd": "tables",
    r"\\cell": "tables",
    r"\\pict": "images",
    r"\\footnote": "footnotes",
}


def scan_rtf_features(rtf: str) -> list[str]:
    """Return human-readable names of RTF features the markup subset would flatten.

    The UI uses this to warn, before a lossy conversion, exactly what will be lost
    (``docs/QUILL-PRD.md`` "Honest fidelity"). An empty list means a clean round trip.
    """
    found: list[str] = []
    for pattern, label in _UNSUPPORTED_FEATURES.items():
        if re.search(pattern, rtf) and label not in found:
            found.append(label)
    return found
