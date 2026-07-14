"""QUILL Illumination — formatting preserved beside a clean plain-text file.

In a manuscript, the *illumination* is the decorative layer a scribe adds over
plain text. QUILL's Illumination is the same idea for the hidden-codes formatting
model: when you save a formatted document as plain text, the ``.txt`` stays clean
for every other tool, and an **Illumination sidecar** (``<file>.illumination``)
stores the run and paragraph formatting so QUILL can re-apply every font, colour,
and alignment when you reopen the ``.txt``.

The sidecar is a small JSON record:

* ``version`` — schema version.
* ``text_sha256`` — a hash of the clean text the Illumination was built from, so
  an edit made to the ``.txt`` outside QUILL is detected and the (now-stale)
  overlay is not applied to the wrong text.
* ``document`` — the serialized :class:`~quill.io.rtf_model.RichDocument` (clean
  text plus the full run/paragraph attribute structure).

This module is the pure, testable model and the sidecar read/write helpers; the
UI decides *when* to write one (the ``plain_text_with_formatting`` setting).
"""

from __future__ import annotations

import dataclasses
import hashlib
from pathlib import Path

from quill.core.storage import read_json, write_json_atomic
from quill.io.rtf_model import (
    InlineSpan,
    RichDocument,
    RichParagraph,
    markdown_to_rich,
    rich_to_markdown,
)

__all__ = [
    "ILLUMINATION_SUFFIX",
    "ILLUMINATION_VERSION",
    "build_illumination",
    "illumination_path_for",
    "markup_has_formatting",
    "read_illumination",
    "restore_markup",
    "write_illumination",
]

ILLUMINATION_VERSION = 1
#: Sidecar suffix, appended to the full document filename: ``report.txt`` ->
#: ``report.txt.illumination``. Keeping the original name visible makes the
#: association obvious and survives a rename of either half being noticed.
ILLUMINATION_SUFFIX = ".illumination"

_SPAN_FIELDS = {f.name for f in dataclasses.fields(InlineSpan)}
_PARAGRAPH_FIELDS = {f.name for f in dataclasses.fields(RichParagraph)} - {"spans"}
_PARAGRAPH_ATTRS = (
    "align",
    "named_style",
    "line_spacing",
    "space_before",
    "space_after",
    "indent",
    "first_line_indent",
)


def _span_is_formatted(span: InlineSpan) -> bool:
    return bool(
        span.bold
        or span.italic
        or span.href
        or span.underline
        or span.strike
        or span.superscript
        or span.subscript
        or span.font_family
        or span.font_size_pt is not None
        or span.color
        or span.highlight
    )


def markup_has_formatting(markdown: str) -> bool:
    """True when the QUILL markup carries formatting an Illumination would keep.

    Headings, bullets, links, and every inline/paragraph attribute count; a
    document of only plain body paragraphs has nothing to preserve, so the UI can
    save it as plain text without offering an Illumination.
    """
    doc = markdown_to_rich(markdown)
    for paragraph in doc.paragraphs:
        if paragraph.style != "paragraph":
            return True
        if any(getattr(paragraph, name) is not None for name in _PARAGRAPH_ATTRS):
            return True
        if any(_span_is_formatted(span) for span in paragraph.spans):
            return True
    return False


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_illumination(markdown: str) -> dict:
    """Capture a document's hidden formatting as a clean-text + overlay record."""
    doc = markdown_to_rich(markdown)
    clean_text = doc.plain_text()
    return {
        "version": ILLUMINATION_VERSION,
        "text_sha256": _sha(clean_text),
        "document": dataclasses.asdict(doc),
    }


def restore_markup(illumination: object, clean_text: str) -> str | None:
    """Reconstruct QUILL markup from an Illumination and the current clean text.

    Returns the formatted markup when the Illumination is valid and the clean
    text still matches what it was built from; returns ``None`` when the version
    is unknown or the text drifted (edited outside QUILL), so the caller opens the
    file as plain text instead of applying a stale overlay.
    """
    if not isinstance(illumination, dict):
        return None
    if illumination.get("version") != ILLUMINATION_VERSION:
        return None
    if illumination.get("text_sha256") != _sha(clean_text):
        return None
    document = _document_from_dict(illumination.get("document"))
    if document is None:
        return None
    return rich_to_markdown(document)


def _document_from_dict(data: object) -> RichDocument | None:
    if not isinstance(data, dict):
        return None
    raw_paragraphs = data.get("paragraphs")
    if not isinstance(raw_paragraphs, list):
        return None
    paragraphs: list[RichParagraph] = []
    for raw_p in raw_paragraphs:
        if not isinstance(raw_p, dict):
            return None
        spans: list[InlineSpan] = []
        for raw_s in raw_p.get("spans") or []:
            if not isinstance(raw_s, dict) or "text" not in raw_s:
                return None
            spans.append(InlineSpan(**{k: v for k, v in raw_s.items() if k in _SPAN_FIELDS}))
        p_kwargs = {k: v for k, v in raw_p.items() if k in _PARAGRAPH_FIELDS}
        paragraphs.append(RichParagraph(spans=spans, **p_kwargs))
    return RichDocument(paragraphs=paragraphs)


def illumination_path_for(document_path: Path) -> Path:
    """The Illumination sidecar path for *document_path* (``<name>.illumination``)."""
    return document_path.parent / (document_path.name + ILLUMINATION_SUFFIX)


def write_illumination(document_path: Path, illumination: dict) -> Path:
    """Write the Illumination sidecar next to *document_path* (atomic JSON)."""
    target = illumination_path_for(document_path)
    write_json_atomic(target, illumination)
    return target


def read_illumination(document_path: Path) -> dict | None:
    """Read the Illumination sidecar for *document_path*, or ``None`` if absent."""
    source = illumination_path_for(document_path)
    if not source.is_file():
        return None
    data = read_json(source, default=None)
    return data if isinstance(data, dict) else None
