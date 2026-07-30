"""Sanitize untrusted feed HTML into safe, readable article text (xxx.md 3.7).

Feed content is attacker-controlled, and the reader renders it into a native
read-only text control (never a WebView -- plan xxx.md 3.10.6), so the job here
is to produce **accessible plain text**, not to emit HTML:

- the *content* of dangerous elements (``script``, ``style``, ``head``,
  ``noscript``, ``svg``, ``template``, ``iframe``) is dropped entirely -- unlike a
  naive tag-stripper, which would leak inline script/style source into the body;
- block elements become line breaks so paragraphs and list items read cleanly;
- links render as ``text (url)`` so the URL is spoken and openable, and images
  render as ``[Image: alt]`` (or ``[Image]``) so they land in the caret stream.

Pure standard library; never raises on malformed markup.
"""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin

# Elements whose *text content* must be discarded, not just their tags.
_DROP_CONTENT = frozenset(
    {"script", "style", "head", "noscript", "template", "svg", "iframe"}
)
_HEADINGS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6"})
_BLOCK = frozenset(
    {
        "p", "div", "br", "li", "tr", "blockquote", "section", "article",
        "figure", "figcaption", "pre", "ul", "ol", "table", "hr", *_HEADINGS,
    }
)


class _Sanitizer(HTMLParser):
    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []
        self._skip_depth = 0
        self._base = base_url
        self._href: str | None = None
        self._link_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _DROP_CONTENT:
            self._skip_depth += 1
            return
        if self._skip_depth:
            return
        a = {k.lower(): (v or "") for k, v in attrs}
        if tag == "a":
            self._href = a.get("href", "")
            self._link_text = []
        elif tag == "img":
            alt = a.get("alt", "").strip()
            self._parts.append(f"[Image: {alt}]" if alt else "[Image]")
        elif tag == "li":
            self._parts.append("\n- ")
        elif tag in _BLOCK:
            self._parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        # e.g. <img .../> or <br/>
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in _DROP_CONTENT:
            if self._skip_depth:
                self._skip_depth -= 1
            return
        if self._skip_depth:
            return
        if tag == "a":
            text = "".join(self._link_text).strip()
            href = self._href or ""
            if href and self._base:
                href = urljoin(self._base, href)
            if href and text and href != text:
                self._parts.append(f"{text} ({href})")
            elif text:
                self._parts.append(text)
            elif href:
                self._parts.append(href)
            self._href = None
            self._link_text = []
        elif tag in _BLOCK:
            self._parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self._skip_depth:
            return
        if self._href is not None:
            self._link_text.append(data)
        else:
            self._parts.append(data)

    def text(self) -> str:
        raw = "".join(self._parts)
        lines = [ln.strip() for ln in raw.splitlines()]
        out: list[str] = []
        blank = False
        for ln in lines:
            if ln:
                out.append(ln)
                blank = False
            elif not blank:
                out.append("")
                blank = True
        return "\n".join(out).strip()


def sanitize_to_text(html: str, *, base_url: str = "") -> str:
    """Return safe, readable plain text for an HTML fragment. Never raises."""
    if not html:
        return ""
    if "<" not in html and "&" not in html:
        return html.strip()
    parser = _Sanitizer(base_url)
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # noqa: BLE001 - malformed markup must not break rendering
        return html.strip()
    return parser.text()
