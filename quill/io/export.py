"""Format-aware document export for Save As.

QUILL's editor keeps its canonical text as Markdown-style markup (the same markup
RTF files are converted into on open). This module turns that canonical markup
into the file format the user picks in the Save As dialog, so choosing a type
actually converts the content rather than renaming it.

Everything here is wx-free so it can live in ``quill/io`` and be unit tested
without a display. The dispatcher :func:`write_document_as` is the single entry
point the UI calls; it routes by the target file extension.
"""

from __future__ import annotations

import html
import re
from pathlib import Path

from quill.core.browser_preview import render_preview_body
from quill.core.document import Document
from quill.io.rtf import write_rtf_document
from quill.io.text import _normalize_line_endings, write_text_document

__all__ = [
    "EXPORT_ONLY_SUFFIXES",
    "HTML_SUFFIXES",
    "LINK_STYLES",
    "UnsupportedSaveFormatError",
    "markdown_to_plain_text",
    "markdown_to_html",
    "write_plain_text_document",
    "write_html_document",
    "write_docx_document",
    "write_document_as",
    "format_label_for_path",
]

HTML_SUFFIXES = frozenset({".html", ".htm", ".xhtml"})
_HTML_SUFFIXES = HTML_SUFFIXES
_PLAIN_SUFFIXES = {".txt", ".text"}
_RTF_SUFFIXES = {".rtf"}
_DOCX_SUFFIXES = {".docx"}

#: Formats QUILL can open (as extracted text) but cannot write back. Writing the
#: editor's markup to one of these would destroy a binary original (an opened
#: PDF, EPUB, spreadsheet...) or produce a file other apps cannot open (Markdown
#: text named .pdf). Save must refuse and steer the user to Save As / Export.
EXPORT_ONLY_SUFFIXES: frozenset[str] = frozenset({
    ".pdf",
    ".doc",
    ".odt",
    ".epub",
    ".pages",
    ".ppt",
    ".pptx",
    ".xls",
    ".xlsx",
    ".sqlite",
    ".db",
})


class UnsupportedSaveFormatError(ValueError):
    """Save targeted an extension QUILL cannot convert the editor text into."""

    def __init__(self, suffix: str) -> None:
        super().__init__(
            f"QUILL cannot save directly to {suffix}. Use File > Export for this format."
        )
        self.suffix = suffix


_FENCE_RE = re.compile(r"^\s*(```|~~~)")
_HEADING_RE = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BLOCKQUOTE_RE = re.compile(r"^\s*>\s?(.*)$")
_BULLET_RE = re.compile(r"^(\s*)([-*+])\s+(.*)$")
_NUMBERED_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
_HRULE_RE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")

_IMAGE_RE = re.compile(r"!\[([^\]]*)\]\(([^)]*)\)")
_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")
# Hidden-codes run span ``[text]{attrs}`` and alignment fence lines. Plain text
# keeps only the visible words (the codes are lost — honest fidelity reporting
# warns about this on plain-text save).
_SPAN_CODE_RE = re.compile(r"\[([^\]]+)\]\{[^}]*\}")
_FENCE_LINE_RE = re.compile(r"^:::+(\s*\{[^}]*\}|\s+pagebreak)?\s*$", re.IGNORECASE)
_CODE_SPAN_RE = re.compile(r"`([^`]+)`")
_BOLD_STAR_RE = re.compile(r"\*\*([^*]+)\*\*")
_BOLD_UNDER_RE = re.compile(r"(?<!\w)__([^_]+)__(?!\w)")
_ITALIC_STAR_RE = re.compile(r"(?<!\*)\*([^*\s][^*]*?)\*(?!\*)")
_ITALIC_UNDER_RE = re.compile(r"(?<!\w)_([^_]+)_(?!\w)")

#: Valid values for the plain-text link rendering style.
LINK_STYLES = ("text", "text_url", "url", "markdown")


def _strip_emphasis(text: str) -> str:
    """Remove bold/italic Markdown markers, keeping the emphasized words."""
    text = _BOLD_STAR_RE.sub(r"\1", text)
    text = _BOLD_UNDER_RE.sub(r"\1", text)
    text = _ITALIC_STAR_RE.sub(r"\1", text)
    text = _ITALIC_UNDER_RE.sub(r"\1", text)
    return text


def _format_link(label: str, target: str, link_style: str) -> str:
    """Render one Markdown link/image as plain text per ``link_style``.

    The visible label is emphasis-stripped (so ``[**Docs**](url)`` reads as
    ``Docs``), while the URL is preserved verbatim. ``url`` is the first
    whitespace-delimited token of the destination, with any wrapping angle
    brackets removed, so titles such as ``(url "Title")`` keep just the URL.
    """
    label = _strip_emphasis(label.strip())
    destination = target.strip()
    url = destination.split(" ", 1)[0] if destination else ""
    if url.startswith("<") and url.endswith(">") and len(url) >= 2:
        url = url[1:-1]
    if link_style == "url":
        return url or label
    if link_style == "text_url":
        if not label:
            return url
        if not url or url == label:
            return label
        return f"{label} ({url})"
    return label


def _strip_inline(text: str, link_style: str = "text") -> str:
    """Remove inline Markdown markers, preserving code spans and links.

    Inline code spans are protected first so that markup *inside* a code span
    survives untouched. Links and images are rendered per ``link_style`` and the
    result is also stashed behind a placeholder, so the URL it may contain is
    never altered by the emphasis stripping that follows. ``markdown`` keeps the
    original link/image markup verbatim. Images are handled before links because
    an image is a link with a leading ``!``.
    """
    placeholders: list[str] = []

    def _stash(value: str) -> str:
        placeholders.append(value)
        return f"\x00{len(placeholders) - 1}\x00"

    # Unwrap hidden-codes run spans to their visible text before any other inline
    # handling, so ``[text]{font-family="Arial"}`` reads as ``text``.
    text = _SPAN_CODE_RE.sub(lambda m: m.group(1), text)
    text = _CODE_SPAN_RE.sub(lambda m: _stash(m.group(1)), text)
    if link_style == "markdown":
        text = _IMAGE_RE.sub(lambda m: _stash(m.group(0)), text)
        text = _LINK_RE.sub(lambda m: _stash(m.group(0)), text)
    else:
        text = _IMAGE_RE.sub(
            lambda m: _stash(_format_link(m.group(1), m.group(2), link_style)), text
        )
        text = _LINK_RE.sub(
            lambda m: _stash(_format_link(m.group(1), m.group(2), link_style)), text
        )

    text = _strip_emphasis(text)

    def _restore(match: re.Match[str]) -> str:
        return placeholders[int(match.group(1))]

    return re.sub(r"\x00(\d+)\x00", _restore, text)


def markdown_to_plain_text(markdown: str, link_style: str = "text") -> str:
    """Convert QUILL Markdown-style markup to readable plain text.

    Block markers (headings, blockquotes, list bullets, horizontal rules, code
    fences) and inline markers (emphasis, code, links, images) are stripped while
    keeping the visible words. Fenced code content is preserved verbatim.
    ``link_style`` controls how links render (see :func:`_format_link`).
    """
    out: list[str] = []
    in_fence = False
    for raw in markdown.splitlines():
        if _FENCE_RE.match(raw):
            in_fence = not in_fence
            continue
        if in_fence:
            out.append(raw)
            continue
        if _FENCE_LINE_RE.match(raw):
            # Alignment fenced-div markers carry no visible text.
            continue
        if _HRULE_RE.match(raw):
            out.append("")
            continue
        heading = _HEADING_RE.match(raw)
        if heading:
            out.append(_strip_inline(heading.group(2), link_style))
            continue
        quote = _BLOCKQUOTE_RE.match(raw)
        if quote and raw.lstrip().startswith(">"):
            out.append(_strip_inline(quote.group(1), link_style))
            continue
        bullet = _BULLET_RE.match(raw)
        if bullet:
            out.append(f"{bullet.group(1)}- {_strip_inline(bullet.group(3), link_style)}")
            continue
        numbered = _NUMBERED_RE.match(raw)
        if numbered:
            out.append(
                f"{numbered.group(1)}{numbered.group(2)}. "
                f"{_strip_inline(numbered.group(3), link_style)}"
            )
            continue
        out.append(_strip_inline(raw, link_style))
    text = "\n".join(out)
    return re.sub(r"\n{3,}", "\n\n", text)


def markdown_to_html(markdown: str, title: str) -> str:
    """Render QUILL Markdown-style markup as a standalone HTML document."""
    body = render_preview_body(markdown, "markdown")
    return (
        "<!doctype html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{html.escape(title)}</title>\n"
        '<script src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-mml-chtml.js"'
        " async></script>\n"
        "</head>\n"
        f"<body>\n{body}\n</body>\n"
        "</html>\n"
    )


def _write_utf8(document: Document, target: Path, text: str) -> Path:
    """Write ``text`` as UTF-8 with the document's line ending and mark it saved."""
    normalized = _normalize_line_endings(text, document.line_ending)
    with target.open("w", encoding="utf-8", newline="") as handle:
        handle.write(normalized)
    document.encoding = "utf-8"
    document.mark_saved(target)
    return target


def write_plain_text_document(
    document: Document, path: Path | None = None, *, link_style: str = "text"
) -> Path:
    """Write a document's markup out as stripped plain text."""
    target = path or document.path
    if target is None:
        raise ValueError("A path is required to save this document.")
    return _write_utf8(document, target, markdown_to_plain_text(document.text, link_style))


def write_html_document(document: Document, path: Path | None = None) -> Path:
    """Write a document's markup out as a standalone HTML file."""
    target = path or document.path
    if target is None:
        raise ValueError("A path is required to save this document.")
    title = target.stem or "Document"
    return _write_utf8(document, target, markdown_to_html(document.text, title))


def write_docx_document(
    document: Document, path: Path | None = None, *, engine: str = "auto"
) -> Path:
    """Write a document's Markdown markup out as a Word (.docx) file.

    ``engine`` selects the converter: ``auto`` (default) prefers the native
    python-docx writer and falls back to Pandoc; ``native`` requires python-docx
    and fails clearly when it is missing; ``pandoc`` forces the Pandoc path for
    users who want structure-first Word styles instead of QUILL's run-level
    formatting codes.

    Prefers the native python-docx writer (:mod:`quill.io.docx_writer`), which
    carries QUILL's hidden-codes attributes — per-run font family, point size,
    color, highlight, underline and per-paragraph alignment — onto real Word runs
    and paragraphs. When python-docx is not installed, falls back to the Pandoc
    path, which maps headings, lists, emphasis, links, and simple tables to Word
    styles (but drops the font/size/color/alignment attributes). Either way the
    result is a properly structured, screen-reader-navigable document, and the
    document is marked saved at the target like every other writer here — so the
    window title, the modified flag, and the next plain Save stay truthful.
    """
    if engine not in {"auto", "native", "pandoc"}:
        raise ValueError(f"Unknown docx engine {engine!r}; use auto, native, or pandoc.")
    target = path or document.path
    if target is None:
        raise ValueError("A path is required to save this document.")
    target = Path(target)

    from quill.io.docx_writer import python_docx_available, write_docx

    if engine != "pandoc" and python_docx_available():
        write_docx(document, target)
        document.mark_saved(target)
        return target
    if engine == "native":
        raise ValueError("The native Word writer needs python-docx, which is not installed.")

    import tempfile

    from quill.io.pandoc import convert_file_with_pandoc

    with tempfile.TemporaryDirectory() as tmp:
        source = Path(tmp) / "source.md"
        source.write_text(document.text, encoding="utf-8", newline="\n")
        # hard_line_breaks: the editor is line-oriented (one editor line is one
        # paragraph, exactly what markdown_to_rich produces on the native path),
        # so a bare "gfm" read — where a single newline is a soft wrap — would
        # join the user's lines into one long Word paragraph.
        convert_file_with_pandoc(
            source, target, from_format="gfm+hard_line_breaks", to_format="docx"
        )
    document.mark_saved(target)
    return target


def write_document_as(
    document: Document,
    path: Path | None = None,
    *,
    plain_text_link_style: str = "text",
    docx_engine: str = "auto",
) -> Path:
    """Write ``document`` to ``path``, converting to the format of its extension.

    ``.rtf`` re-serializes to RTF, ``.docx`` renders to Word via Pandoc, and
    ``.html``/``.htm``/``.xhtml`` render to HTML. Everything else —
    ``.txt``/``.text``, ``.md``, and any unknown extension — is written
    **verbatim** (#649): the canonical text already is Markdown, and a plain-text
    file must round-trip without Markdown stripping or blank-line collapsing. The
    explicit "Save as plain text" command (``write_plain_text_document``) still
    flattens markup. ``plain_text_link_style`` is accepted for call-site symmetry
    and applies only on that explicit plain-text path (see :data:`LINK_STYLES`).
    ``docx_engine`` is forwarded to :func:`write_docx_document` (the
    ``docx_write_engine`` setting).
    """
    target = path or document.path
    if target is None:
        raise ValueError("A path is required to save this document.")
    suffix = Path(target).suffix.lower()
    if suffix in EXPORT_ONLY_SUFFIXES:
        # Never fall through to the verbatim text writer for these: it would
        # overwrite an opened binary original (PDF, EPUB, spreadsheet...) with
        # plain text, or mint a Markdown file wearing a .pdf name that other
        # apps cannot open.
        raise UnsupportedSaveFormatError(suffix)
    if suffix in _RTF_SUFFIXES:
        return write_rtf_document(document, target)
    if suffix in _DOCX_SUFFIXES:
        return write_docx_document(document, target, engine=docx_engine)
    if suffix in _HTML_SUFFIXES:
        return write_html_document(document, target)
    # A plain-text file the user opened (or saves to by extension) must round-trip
    # verbatim: no Markdown stripping and, critically, no collapsing of blank-line
    # runs (#649). The explicit "Save as plain text" command (save_as_plain_text)
    # still routes through write_plain_text_document for users who want their
    # Markdown markup flattened.
    return write_text_document(document, target)


def format_label_for_path(path: Path) -> str:
    """A short, speakable name for the format implied by ``path``'s extension."""
    suffix = Path(path).suffix.lower()
    if suffix in _RTF_SUFFIXES:
        return "rich text"
    if suffix in _DOCX_SUFFIXES:
        return "Word"
    if suffix in _HTML_SUFFIXES:
        return "HTML"
    if suffix in _PLAIN_SUFFIXES:
        return "plain text"
    if suffix in {".md", ".markdown"}:
        return "Markdown"
    return "Markdown"
