"""Convert an episode's HTML show notes/description into an accessible,
lightweight plain-text form -- real line breaks at paragraph boundaries (so a
screen reader's line-by-line navigation moves by line, not by wrapping a
single giant line word by word), and links rendered as ``text (url)`` rather
than being silently dropped. Also a minimal HTML sanitizer for the "rich"
view, which strips ``<img>`` tags so viewing show notes can never trigger a
silent, unaudited image fetch (QUILL's house rule: every network egress site
is reviewed; an HTML renderer quietly loading remote images would not be).

wx-free, strict-typed, pure (no I/O, no network).
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

#: Tags whose *end* implies a paragraph break in the plain-text conversion.
_BLOCK_END_TAGS = frozenset({"p", "div", "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote"})
#: Tags that are themselves a line break (no matching end-tag content).
_BREAK_TAGS = frozenset({"br", "hr"})


class _PlainTextParser(HTMLParser):
    """Collects visible text, converting links to ``text (url)`` and block
    boundaries to real newlines."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._link_stack: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BREAK_TAGS:
            self._parts.append("\n")
        elif tag == "a":
            href = dict(attrs).get("href") or ""
            self._link_stack.append(href.strip())

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link_stack:
            href = self._link_stack.pop()
            if href:
                self._parts.append(f" ({href})")
        elif tag in _BLOCK_END_TAGS:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        self._parts.append(data)

    def text(self) -> str:
        return "".join(self._parts)


def html_to_plain_text(html: str) -> str:
    """Convert *html* to plain text with real paragraph line breaks and
    ``link text (url)`` in place of ``<a>`` tags. Tolerant of malformed HTML
    (:class:`html.parser.HTMLParser` never raises on bad markup); returns the
    input unchanged if it contains no tags at all (already-plain text)."""
    if "<" not in html:
        return html.strip()
    parser = _PlainTextParser()
    parser.feed(html)
    parser.close()
    text = parser.text()
    # Each paragraph/list-item/break already contributes its own newline;
    # drop lines that are empty after stripping (an empty <p></p>, or a run of
    # several) rather than rendering them as blank filler lines.
    lines = [line.strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


_IMG_TAG_RE = re.compile(r"<img\b[^>]*>", re.IGNORECASE)


def strip_html_images(html: str) -> str:
    """Remove every ``<img>`` tag from *html* (pure string operation).

    Used before handing show-notes HTML to a rich HTML view: an HTML
    renderer that itself fetches ``<img src="...">`` would be a silent,
    unreviewed network egress site invisible to a static audit of QUILL's
    own ``urlopen``/``urlretrieve`` call sites.
    """
    return _IMG_TAG_RE.sub("", html)
