"""The portable content spine for Look Up (#897), the Clip Library (#895), and
Email hand-off (#900): one small object plus a renderer, so "keep it" and
"send it" work identically everywhere a piece of content can come from.

QUILL's canonical text is already Markdown-style markup, and :mod:`quill.io.export`
/ :mod:`quill.core.browser_preview` already know how to turn that markup into
plain text or HTML. A :class:`Fragment` carries that markup plus provenance
(title, source, an optional citation URL); :func:`render_fragment` is the single
place the text/Markdown/HTML choice is honored, so changing how a format
renders changes Look Up, the Clip Library, and Email together.

Pure, wx-free, no network, no filesystem -- everything here is a function of
its inputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

__all__ = ["Fragment", "FragmentFormat", "render_fragment"]


class FragmentFormat(StrEnum):
    TEXT = "text"
    MARKDOWN = "markdown"
    HTML = "html"


@dataclass(frozen=True, slots=True)
class Fragment:
    """A portable piece of content with one canonical form and known origin."""

    markup: str  # canonical QUILL Markdown-style markup
    title: str = ""  # human/screen-reader label, e.g. "Wikipedia: Ada Lovelace"
    source: str = ""  # provenance: "Wikipedia", "Look Up", "Clipboard", "Document"
    source_url: str = ""  # citation link when one exists (Wikipedia, dictionary)
    kind: str = "text"  # text | encyclopedia | definition
    created_at: str = ""  # ISO-8601, UTC


def _citation_line(frag: Fragment, fmt: FragmentFormat) -> str:
    if not frag.source_url:
        return ""
    label = frag.source or frag.title or frag.source_url
    if fmt is FragmentFormat.HTML:
        return f'<p><a href="{frag.source_url}">Source: {label}</a></p>'
    if fmt is FragmentFormat.MARKDOWN:
        return f"\n\n[Source: {label}]({frag.source_url})"
    return f"\n\nSource: {label} ({frag.source_url})"


def render_fragment(frag: Fragment, fmt: FragmentFormat, *, link_style: str = "text_url") -> str:
    """Render *frag* in the requested format (pure).

    ``TEXT`` -> plain readable text (via :func:`quill.io.export.markdown_to_plain_text`);
    ``MARKDOWN`` -> the canonical markup verbatim; ``HTML`` -> a standalone
    snippet (via :func:`quill.core.browser_preview.render_preview_body`, not a
    full document -- this is meant to be embedded in a clip or an email body,
    not opened as its own page). A ``source_url``, when present, is appended as
    a citation appropriate to the format, so a kept or sent fact never loses
    where it came from.
    """
    citation = _citation_line(frag, fmt)
    if fmt is FragmentFormat.MARKDOWN:
        return frag.markup + citation
    if fmt is FragmentFormat.HTML:
        from quill.core.browser_preview import render_preview_body

        return render_preview_body(frag.markup, "markdown") + citation
    from quill.io.export import markdown_to_plain_text

    return markdown_to_plain_text(frag.markup, link_style) + citation
