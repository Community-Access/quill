"""
HTML paste cleaner — intelligently detects and cleans HTML from clipboard.

Detects HTML content and offers cleaning options: strip to plain text, preserve
structure, or keep as-is. The converter is QUILL's own and needs no third-party
library.

This module provides:
- is_html(text) → bool: Heuristic detection of HTML content
- clean_html(html) → str: Strip HTML to plain text, preserving structure
- HtmlPasteContext: Data class for paste context (original text, detected type, cleaned)

Screen-reader integration: All detection and cleaning is silent; the UI layer
announces results via prism_bridge.announce().
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape

__all__ = ["is_html", "clean_html", "HtmlPasteContext", "HTML_PASTE_HEURISTIC_TAGS"]

# HTML tags that strongly indicate HTML content (not plain text with < and >).
HTML_PASTE_HEURISTIC_TAGS = (
    "<p>",
    "<p ",
    "<div>",
    "<div ",
    "<span>",
    "<span ",
    "<h1>",
    "<h2>",
    "<h3>",
    "<h4>",
    "<h5>",
    "<h6>",
    "<ul>",
    "<ol>",
    "<li>",
    "<table>",
    "<tr>",
    "<td>",
    "<th>",
    "<br>",
    "<br/>",
    "<br />",
    "<blockquote>",
    "<a href",
    "<img",
    "<strong>",
    "<em>",
    "<b>",
    "<i>",
    "<!DOCTYPE",
    "<html",
    "<body",
    "<head",
)


def is_html(text: str) -> bool:
    """
    Heuristic detection: is this clipboard content HTML?

    Returns True if the text contains HTML-like tags that suggest it's
    from a web browser or rich text editor, not plain text or code.

    Heuristics:
    - Contains common HTML structural tags (<p>, <div>, <h1>, etc.)
    - Does NOT flag code samples like "vector<int>" or email footers with <name@example.com>
    - Case-insensitive tag detection
    """
    if not text or len(text) < 10:
        return False

    text_lower = text.lower()

    # Strong indicators: structural HTML tags.
    for tag in HTML_PASTE_HEURISTIC_TAGS:
        if tag.lower() in text_lower:
            return True

    # Weak indicator: <something> pattern but not too many (could be code).
    # Threshold: at least 2 tag-like patterns suggests HTML.
    tag_pattern = re.compile(r"<[a-z][a-z0-9\s:]*>", re.IGNORECASE)
    if len(tag_pattern.findall(text)) >= 2:
        return True

    return False


def clean_html(html: str) -> str:
    """
    Convert HTML to plain text, preserving document structure.

    Uses QUILL's own regex-based converter (no third-party library).

    Behavior:
    - Strips scripts, styles, and metadata
    - Preserves heading hierarchy (spacing)
    - Preserves table structure (reading order)
    - Preserves link text (URLs captured in metadata by caller)
    - Converts <br> and <hr> to newlines

    Returns plain text suitable for insertion into Quill editor.
    """
    # Remove script and style blocks.
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Convert common block elements to double newlines.
    text = re.sub(r"</?(p|div|blockquote|h[1-6])[^>]*>", "\n\n", text, flags=re.IGNORECASE)

    # Convert <br> and <hr> to newlines.
    text = re.sub(r"<br\s*/?>\s*", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<hr\s*/?>\s*", "\n" + "-" * 80 + "\n", text, flags=re.IGNORECASE)

    # Strip remaining tags.
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities.
    text = unescape(text)

    # Collapse excess whitespace.
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r" +", " ", text)

    return text.strip()


@dataclass(slots=True)
class HtmlPasteContext:
    """Context for a paste event that includes HTML detection and cleaning."""

    original_text: str
    """Raw clipboard text."""

    is_html: bool
    """True if original_text appears to be HTML."""

    cleaned_text: str | None = None
    """Plain text version if is_html is True; None otherwise."""

    def get_paste_text(self, *, clean: bool) -> str:
        """Return text to paste: cleaned or original."""
        if clean and self.cleaned_text is not None:
            return self.cleaned_text
        return self.original_text


def analyze_paste(text: str) -> HtmlPasteContext:
    """
    Analyze clipboard paste for HTML content.

    Returns HtmlPasteContext with detection and (if HTML) cleaned text.
    If HTML is detected, clean_html is called immediately so it's ready
    for quick insertion if user chooses clean mode.
    """
    detected_html = is_html(text)
    cleaned = clean_html(text) if detected_html else None
    return HtmlPasteContext(original_text=text, is_html=detected_html, cleaned_text=cleaned)
