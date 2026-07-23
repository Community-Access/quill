"""Inline accessible image descriptions (#899): what's under the caret.

GLOW (``quill/core/link_inventory.py``) already audits every image's alt
status after the fact -- a reactive repair pass. This module answers the
same question live, for whatever image reference the caret is inside or
touching right now: "Image: sunset.png, alt text: a sunset over the lake"
or, just as loudly, "Image: sunset.png, alt text MISSING" -- absent alt
text should be impossible to *miss*, not just impossible to *see*.

Non-image embeds (page breaks, equations, removed objects) are a
deliberately separate follow-up -- add.md's own note said to investigate a
shared placeholder model before designing one, and this module doesn't
invent one; it covers the object model that already exists (Markdown and
HTML images, the same two ``link_inventory.py`` already parses).
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

__all__ = [
    "ImageAtCursor",
    "build_image_html",
    "build_image_markdown",
    "describe_image",
    "image_at_position",
]

_MD_IMAGE_PATTERN = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")
_HTML_IMG_PATTERN = re.compile(r"<img[^>]*>", re.IGNORECASE)
_HTML_ATTR_PATTERN = re.compile(r"([a-zA-Z_:][-a-zA-Z0-9_:.]*)=['\"]([^'\"]*)['\"]")


@dataclass(frozen=True, slots=True)
class ImageAtCursor:
    source: str
    alt_text: str
    start: int
    end: int


def image_at_position(text: str, pos: int) -> ImageAtCursor | None:
    """Return the image reference the caret at *pos* is inside or touching."""
    for match in _MD_IMAGE_PATTERN.finditer(text):
        if match.start() <= pos <= match.end():
            return ImageAtCursor(
                source=match.group(2), alt_text=match.group(1), start=match.start(), end=match.end()
            )
    for match in _HTML_IMG_PATTERN.finditer(text):
        if match.start() <= pos <= match.end():
            found = _HTML_ATTR_PATTERN.findall(match.group(0))
            attrs = {name.lower(): value for name, value in found}
            source = attrs.get("src", "")
            if not source:
                continue
            return ImageAtCursor(
                source=source, alt_text=attrs.get("alt", ""), start=match.start(), end=match.end()
            )
    return None


def describe_image(record: ImageAtCursor) -> str:
    """The spoken description: present alt text, or an impossible-to-miss gap."""
    name = os.path.basename(record.source) or record.source
    if record.alt_text.strip():
        return f"Image: {name}, alt text: {record.alt_text}"
    return f"Image: {name}, alt text MISSING"


def build_image_markdown(path: str, alt_text: str, *, decorative: bool = False) -> str:
    """Build the ``![alt](path)`` Markdown for a newly inserted image.

    *decorative* images carry deliberately empty alt text (the correct,
    accepted accessible pattern for an image with no informational content)
    -- distinct from an image nobody ever gave alt text to, which is the
    actual problem this issue is about.
    """
    alt = "" if decorative else alt_text.strip()
    return f"![{alt}]({path})"


def _escape_attr(value: str) -> str:
    """Escape a string for use inside a double-quoted HTML attribute."""
    return value.replace("&", "&amp;").replace('"', "&quot;")


def _escape_text(value: str) -> str:
    """Escape a string for use as HTML text content (a figcaption)."""
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def build_image_html(
    path: str,
    alt_text: str,
    *,
    decorative: bool = False,
    width: int | None = None,
    height: int | None = None,
    responsive: bool = False,
    lazy: bool = True,
    caption: str = "",
) -> str:
    """Build accessible, page-ready ``<img>`` HTML for a newly inserted image.

    Markdown can only carry alt text; HTML can carry what a browser needs to
    lay the image out *correctly*, so in an HTML document we offer more:

    * ``width``/``height`` set the intrinsic box so the browser reserves space
      before the file loads -- the image no longer shoves the page around as it
      arrives (no cumulative layout shift).
    * ``responsive`` caps the image at its container width
      (``max-width:100%;height:auto``) so it never overflows a narrow column.
    * ``lazy`` defers off-screen images with ``loading="lazy"``.
    * ``decorative`` emits empty alt *and* ``role="presentation"`` so assistive
      technology skips it -- the correct pattern for a purely ornamental image,
      distinct from an image nobody ever described.
    * ``caption`` wraps the image in ``<figure>`` with a ``<figcaption>`` so the
      caption is programmatically tied to the image, not just text beside it.
    """
    alt = "" if decorative else alt_text.strip()
    attrs = [f'src="{_escape_attr(path)}"', f'alt="{_escape_attr(alt)}"']
    if decorative:
        attrs.append('role="presentation"')
    if width is not None and width > 0:
        attrs.append(f'width="{int(width)}"')
    if height is not None and height > 0:
        attrs.append(f'height="{int(height)}"')
    if lazy:
        attrs.append('loading="lazy"')
    if responsive:
        attrs.append('style="max-width:100%;height:auto;"')
    img = f"<img {' '.join(attrs)} />"
    caption_text = caption.strip()
    if caption_text:
        return (
            f"<figure>\n  {img}\n  <figcaption>{_escape_text(caption_text)}</figcaption>\n</figure>"
        )
    return img
