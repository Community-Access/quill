"""Preview Blocks: what the site makes of the blocks, read as plain text (8.5).

Nothing is saved to do this. A static block's saved HTML *is* what the site
shows (the site only adds its theme around it), so it is read as it is. A
server-rendered (dynamic) block -- latest posts, a query loop, a synced
pattern, a plugin's form -- has no saved HTML, so each one is sent to the
site's block renderer (``wp/v2/block-renderer/<name>``), which renders it
with the attributes in the document and saves nothing.

The readout is plain text in reading order: a heading says its level, a list
item starts with a dash, a picture says its alt text (or that it has none),
and a table reads row by row.
"""

from __future__ import annotations

import copy as _copy
from collections.abc import Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any

from quill.core.wordpress.api import WordPressApi, WordPressApiError
from quill.core.wordpress.blocks import Block, describe, parse, serialize

__all__ = ["PreviewResult", "dynamic_blocks", "html_readout", "render_preview"]


def _is_dynamic(block: Block) -> bool:
    return not block.freeform and not any(part for part in block.inner_content if part)


def dynamic_blocks(blocks: list[Block]) -> list[Block]:
    """Every block with no saved HTML, nested ones included, in reading order."""
    out: list[Block] = []
    for block in blocks:
        if _is_dynamic(block):
            out.append(block)
        else:
            out.extend(dynamic_blocks(block.inner_blocks))
    return out


@dataclass
class PreviewResult:
    readout: str
    rendered: int
    failed: list[str]


Render = Callable[[Block], str]


def _api_render(api: WordPressApi, post_id: int) -> Render:
    def render(block: Block) -> str:
        body: dict[str, Any] = {"attributes": block.attrs}
        if post_id:
            body["post_id"] = post_id
        answer = api.post(f"wp/v2/block-renderer/{block.name}", body, context="edit")
        rendered = answer.get("rendered") if isinstance(answer, dict) else None
        return rendered if isinstance(rendered, str) else ""

    return render


def render_preview(html: str, render: Render | WordPressApi, post_id: int = 0) -> PreviewResult:
    """Render every dynamic block, then read the whole document as text."""
    renderer = _api_render(render, post_id) if isinstance(render, WordPressApi) else render
    blocks = _copy.deepcopy(parse(html))
    failed: list[str] = []
    rendered = 0
    for block in dynamic_blocks(blocks):
        try:
            markup = renderer(block)
        except WordPressApiError as exc:
            failed.append(f"{describe(block)}: {exc.plain}")
            markup = f"<p>[{describe(block)}: the site could not show this.]</p>"
        else:
            rendered += 1
        block.name = None
        block.attrs = {}
        block.inner_blocks = []
        block.inner_content = [markup]
        block.inner_html = markup
    return PreviewResult(html_readout(serialize(blocks)), rendered, failed)


# --------------------------------------------------------------------------- #
# HTML to a plain readout

_BREAKS = {
    "p",
    "div",
    "figure",
    "section",
    "article",
    "header",
    "footer",
    "main",
    "aside",
    "nav",
    "ul",
    "ol",
    "table",
    "thead",
    "tbody",
    "details",
    "pre",
    "hr",
    "br",
    "form",
}
_SKIP = {"script", "style", "template", "noscript"}


class _Reader(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.lines: list[str] = []
        self.current: list[str] = []
        self.skip = 0
        self.cells: list[str] | None = None

    def _flush(self) -> None:
        text = " ".join("".join(self.current).split())
        if text:
            self.lines.append(text)
        self.current = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _SKIP:
            self.skip += 1
            return
        found = dict(attrs)
        if tag in _BREAKS:
            self._flush()
        if tag in ("h1", "h2", "h3", "h4", "h5", "h6"):
            self._flush()
            self.current.append(f"Heading level {tag[1]}: ")
        elif tag == "li":
            self._flush()
            self.current.append("- ")
        elif tag == "blockquote":
            self._flush()
            self.current.append("Quote: ")
        elif tag == "figcaption":
            self._flush()
            self.current.append("Caption: ")
        elif tag == "summary":
            self._flush()
            self.current.append("Details: ")
        elif tag == "hr":
            self.lines.append("Separator")
        elif tag == "img":
            alt = (found.get("alt") or "").strip()
            self._flush()
            self.lines.append(f"Picture: {alt}" if alt else "Picture with no alt text")
        elif tag in ("iframe", "video", "audio"):
            title = (found.get("title") or found.get("src") or "").strip()
            self._flush()
            self.lines.append(f"Embedded {tag}: {title}" if title else f"Embedded {tag}")
        elif tag == "tr":
            self._flush()
            self.cells = []
        elif tag in ("td", "th") and self.cells is not None:
            self._flush()

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP:
            self.skip = max(0, self.skip - 1)
            return
        if tag in ("td", "th") and self.cells is not None:
            self.cells.append(" ".join("".join(self.current).split()))
            self.current = []
        elif tag == "tr" and self.cells is not None:
            self.lines.append(" | ".join(self.cells))
            self.cells = None
        elif tag in _BREAKS or tag in (
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "li",
            "blockquote",
            "figcaption",
            "summary",
        ):
            self._flush()

    def handle_data(self, data: str) -> None:
        if not self.skip:
            self.current.append(data)


def html_readout(html: str) -> str:
    """Rendered HTML as plain lines in reading order. Comments are dropped."""
    reader = _Reader()
    reader.feed(html)
    reader.close()
    reader._flush()
    return "\n".join(reader.lines)
