"""Blocks to Markdown for :mod:`quill.core.wordpress.fences`.

Each block's Markdown is read straight back (through the ``reread`` callable
the public module supplies, which keeps the reader and writer free of an
import cycle) and compared with the original; any difference makes the block
an island instead.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable, Mapping, Sequence
from typing import Any

from quill.core.wordpress.blocks import Block, serialize_block
from quill.core.wordpress.fences_markup import (
    _GROUP_LAYOUT,
    _code_unescape,
    _emit,
    _escape_line,
    _inline_to_md,
    _quote,
)

#: Markdown lines, islands, inside-buttons -> rebuilt blocks, or None on a problem.
Reread = Callable[[Sequence[str], Mapping[str, str], bool], list[Block] | None]


def _join_chunks(chunks: Sequence[list[str]]) -> list[str]:
    out: list[str] = []
    for index, chunk in enumerate(chunks):
        if index:
            out.append("")
        out.extend(chunk)
    return out


def _single(markup: str) -> str | None:
    """Inline Markdown that must fit on one non-empty line."""
    md = _inline_to_md(markup)
    if md is None or not md.strip() or "\n" in md:
        return None
    return md


class _Writer:
    """Blocks to Markdown lines, checking each block converts back exactly."""

    def __init__(self, reread: Reread) -> None:
        self.islands: dict[str, str] = {}
        self._count = 0
        self._reread = reread

    def island(self, block: Block, text: str | None = None) -> list[str]:
        self._count += 1
        token = f"island-{self._count}"
        self.islands[token] = serialize_block(block) if text is None else text
        return [f"::: block {block.name or 'core/freeform'} {token}"]

    def block(self, block: Block, in_buttons: bool = False) -> list[str]:
        before = set(self.islands)
        lines = self._try(block)
        if lines is not None and self._verify(lines, block, in_buttons):
            return lines
        for token in set(self.islands) - before:
            del self.islands[token]
        return self.island(block)

    def _verify(self, lines: Sequence[str], block: Block, in_buttons: bool) -> bool:
        rebuilt = self._reread(lines, self.islands, in_buttons)
        return rebuilt is not None and _emit(rebuilt) == serialize_block(block)

    def children(self, block: Block) -> list[str]:
        return _join_chunks([self.block(child) for child in block.inner_blocks])

    def _try(self, block: Block) -> list[str] | None:
        handler = _HANDLERS.get(block.name or "")
        return handler(self, block) if handler is not None else None

    # -- text blocks -----------------------------------------------------------
    def paragraph(self, block: Block) -> list[str] | None:
        m = re.fullmatch(r"\n<p>(.*)</p>\n", block.inner_html, re.S)
        if m is None or block.attrs or block.inner_blocks:
            return None
        md = _inline_to_md(m.group(1))
        if md is None:
            return None
        lines = md.split("\n")
        if any(not line.strip() for line in lines):
            return None
        return [_escape_line(line) for line in lines]

    def heading(self, block: Block) -> list[str] | None:
        m = re.fullmatch(
            r'\n<h([1-6]) class="wp-block-heading">(.*)</h\1>\n', block.inner_html, re.S
        )
        if m is None:
            return None
        md = _single(m.group(2))
        return None if md is None else ["#" * int(m.group(1)) + " " + md]

    def list_block(self, block: Block) -> list[str] | None:
        ordered = block.attrs.get("ordered") is True
        lines: list[str] = []
        for number, item in enumerate(block.inner_blocks, start=1):
            if item.name != "core/list-item" or item.attrs:
                return None
            m = re.match(r"\n<li>(.*?)(?:</li>\n)?$", item.inner_content[0] or "", re.S)
            if m is None:
                return None
            md = _single(m.group(1))
            if md is None:
                return None
            marker = f"{number}. " if ordered else "- "
            lines.append(marker + md)
            for nested in item.inner_blocks:
                sub = self.list_block(nested) if nested.name == "core/list" else None
                if sub is None:
                    return None
                lines.extend(" " * len(marker) + line for line in sub)
        return lines or None

    def quote(self, block: Block) -> list[str] | None:
        if block.attrs or not block.inner_blocks:
            return None
        tail = block.inner_content[-1] or ""
        m = re.search(r"(?:<cite>(.*)</cite>)?</blockquote>\n$", tail, re.S)
        if m is None:
            return None
        body = self.children(block)
        if m.group(1) is not None:
            cite = _single(m.group(1))
            if cite is None:
                return None
            body += ["", "-- " + cite]
        return ["> " + line if line else ">" for line in body]

    def image(self, block: Block) -> list[str] | None:
        m = re.fullmatch(
            r'\n<figure class="wp-block-image(?: size-([\w-]+))?"><img src="([^"]*)" alt="([^"]*)"'
            r'(?: class="wp-image-(\d+)")?/>'
            r'(?:<figcaption class="wp-element-caption">(.*)</figcaption>)?'
            r"</figure>\n",
            block.inner_html,
            re.S,
        )
        if m is None:
            return None
        src = html.unescape(m.group(2))
        if not src or re.search(r"[\s()]", src):
            return None
        alt = re.sub(r"[\\\[\]]", lambda x: "\\" + x.group(0), html.unescape(m.group(3)))
        line = f"![{alt}]({src}"
        if m.group(5) is not None:
            caption = _single(m.group(5))
            if caption is None:
                return None
            line += " " + _quote(caption)
        line += ")"
        options = []
        if "id" in block.attrs:
            options.append(f"id={block.attrs['id']}")
        if "sizeSlug" in block.attrs:
            options.append(f"size={block.attrs['sizeSlug']}")
        if "linkDestination" in block.attrs:
            options.append(f"link={block.attrs['linkDestination']}")
        if options:
            line += " {" + " ".join(options) + "}"
        return [line]

    def separator(self, block: Block) -> list[str] | None:
        return ["---"]

    def code(self, block: Block) -> list[str] | None:
        m = re.fullmatch(
            r'\n<pre class="wp-block-code"><code>(.*)</code></pre>\n', block.inner_html, re.S
        )
        if m is None:
            return None
        body = _code_unescape(m.group(1)).split("\n")
        if any(line.rstrip() == "```" for line in body):
            return None
        return ["```", *body, "```"]

    def preformatted(self, block: Block) -> list[str] | None:
        m = re.fullmatch(
            r'\n<pre class="wp-block-preformatted">(.*)</pre>\n', block.inner_html, re.S
        )
        if m is None:
            return None
        body = m.group(1).split("\n")
        if any(line.startswith(":::") for line in body):
            return None
        return ["::: preformatted", *body, "::: end preformatted"]

    def table(self, block: Block) -> list[str] | None:
        m = re.fullmatch(
            r'\n<figure class="wp-block-table"><table class="has-fixed-layout">'
            r"<thead><tr>(.*?)</tr></thead>(?:<tbody>(.*)</tbody>)?</table></figure>\n",
            block.inner_html,
            re.S,
        )
        if m is None:
            return None

        def cells(row: str, tag: str) -> list[str] | None:
            found = re.findall(rf"<{tag}>(.*?)</{tag}>", row, re.S)
            out = []
            for cell in found:
                md = _inline_to_md(cell)
                if md is None or "\n" in md:
                    return None
                out.append(md.replace("|", "\\|"))
            return out

        header = cells(m.group(1), "th")
        if not header:
            return None
        lines = ["| " + " | ".join(header) + " |", "|" + "|".join(" --- " for _ in header) + "|"]
        for row in re.findall(r"<tr>(.*?)</tr>", m.group(2) or "", re.S):
            data = cells(row, "td")
            if data is None:
                return None
            lines.append("| " + " | ".join(data) + " |")
        return lines

    # -- fenced blocks ---------------------------------------------------------
    def _button_md(self, block: Block) -> str | None:
        if block.name != "core/button" or block.attrs:
            return None
        m = re.fullmatch(
            r'\n<div class="wp-block-button"><a class="wp-block-button__link wp-element-button"'
            r'(?: href="([^"]*)")?>(.*)</a></div>\n',
            block.inner_html,
            re.S,
        )
        if m is None:
            return None
        label = _single(m.group(2))
        if label is None:
            return None
        line = "::: button " + _quote(label)
        if m.group(1) is not None:
            url = html.unescape(m.group(1))
            if not url or re.search(r"\s", url):
                return None
            line += " " + url
        return line

    def buttons(self, block: Block) -> list[str] | None:
        if block.attrs or not block.inner_blocks:
            return None
        simple = [self._button_md(child) for child in block.inner_blocks]
        if all(line is not None for line in simple):
            return [line for line in simple if line is not None]
        inner: list[str] = []
        for child, line in zip(block.inner_blocks, simple, strict=True):
            inner.extend([line] if line is not None else self.island(child))
        return ["::: buttons", *inner, "::: end buttons"]

    def columns(self, block: Block) -> list[str] | None:
        if block.attrs or not block.inner_blocks:
            return None
        lines = ["::: columns"]
        for column in block.inner_blocks:
            if column.name != "core/column" or set(column.attrs) - {"width"}:
                return None
            width = column.attrs.get("width")
            if width is not None and (
                not isinstance(width, str) or not re.fullmatch(r"\S+", width)
            ):
                return None
            lines.append("::: column" + (f" {width}" if width else ""))
            lines.extend(self.children(column))
        lines.append("::: end columns")
        return lines

    def group(self, block: Block) -> list[str] | None:
        if block.attrs != _GROUP_LAYOUT:
            return None
        return ["::: group", *self.children(block), "::: end group"]

    def details(self, block: Block) -> list[str] | None:
        if block.attrs or not block.inner_content:
            return None
        m = re.match(
            r'\n<details class="wp-block-details"><summary>(.*?)</summary>',
            block.inner_content[0] or "",
            re.S,
        )
        if m is None:
            return None
        summary = _single(m.group(1))
        if summary is None:
            return None
        return [f"::: details {_quote(summary)}", *self.children(block), "::: end details"]

    def embed(self, block: Block) -> list[str] | None:
        url = block.attrs.get("url")
        if not isinstance(url, str) or not url or re.search(r"\s", url):
            return None
        words = [url]
        if "type" in block.attrs:
            words.append(f"type={block.attrs['type']}")
        if "providerNameSlug" in block.attrs:
            words.append(f"provider={block.attrs['providerNameSlug']}")
        aspect = re.fullmatch(
            r"wp-embed-aspect-(\S+) wp-has-aspect-ratio", str(block.attrs.get("className", ""))
        )
        if aspect:
            words.append(f"aspect={aspect.group(1)}")
        return ["::: embed " + " ".join(words)]

    def spacer(self, block: Block) -> list[str] | None:
        height = block.attrs.get("height")
        if height is None:
            return ["::: spacer"]
        if not isinstance(height, str) or re.search(r"\s", height):
            return None
        return [f"::: spacer {height}"]


_HANDLERS: dict[str, Any] = {
    "core/paragraph": _Writer.paragraph,
    "core/heading": _Writer.heading,
    "core/list": _Writer.list_block,
    "core/quote": _Writer.quote,
    "core/image": _Writer.image,
    "core/separator": _Writer.separator,
    "core/code": _Writer.code,
    "core/preformatted": _Writer.preformatted,
    "core/table": _Writer.table,
    "core/buttons": _Writer.buttons,
    "core/columns": _Writer.columns,
    "core/group": _Writer.group,
    "core/details": _Writer.details,
    "core/embed": _Writer.embed,
    "core/spacer": _Writer.spacer,
}
