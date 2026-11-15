"""An HTML document, or plain text, as WordPress block markup (wordpress.md 9.16).

Send This Document to WordPress takes any document. A Markdown one goes
through :mod:`~quill.core.wordpress.fences`; this module does the other two:

* **HTML** (:func:`html_to_blocks`): the page's ``<body>`` (its ``<head>`` is
  never sent) becomes the blocks the block editor would have made of it --
  headings, paragraphs, lists (nested ones too), quotes, code, preformatted
  text, tables, images and separators -- with inline markup (links, emphasis,
  code, line breaks) kept inside them. Wrappers with no meaning of their own
  (``div``, ``section``, ``article``, ``main``...) are unwrapped. Anything a
  block would lose the meaning of -- a script, a form, a video, a definition
  list, a table with merged cells -- is kept exactly, in a **Custom HTML**
  block, rather than being flattened into text.
* **Plain text** (:func:`text_to_blocks`): a paragraph per blank-line-separated
  run, its line breaks kept as ``<br>``, and ``<``, ``>`` and ``&`` escaped, so
  nothing in the text is ever read as markup or as Markdown.

Every block is built by the same builders the Markdown conversion uses, which
write what WordPress's own save code writes, so the block editor does not mark
them invalid. Wx-free.
"""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from html.parser import HTMLParser

from quill.core.wordpress.blocks import Block
from quill.core.wordpress.fences_markup import (
    _code,
    _emit,
    _esc_attr,
    _heading,
    _image,
    _list,
    _list_item,
    _new,
    _paragraph,
    _preformatted,
    _quote_block,
    _separator,
)

__all__ = ["html_title_and_blocks", "html_to_blocks", "text_to_blocks"]

_VOID = frozenset("area base br col embed hr img input link meta param source track wbr".split())
_RAW = frozenset({"script", "style"})
_INLINE = frozenset(
    "a abbr b bdi bdo br cite code data del dfn em font i ins kbd mark q s samp small span "
    "strong sub sup time u var wbr".split()
)
#: Wrappers that carry no meaning a block would keep: their children are used.
_UNWRAP = frozenset(
    "html body div section article main header footer aside nav center hgroup search".split()
)
_DROP = frozenset({"head", "title", "meta", "link", "base"})
_BLOCK_START = frozenset(
    "address article aside blockquote details div dl fieldset figure footer form h1 h2 h3 h4 "
    "h5 h6 header hr main nav ol p pre section table ul".split()
)


class _Node:
    __slots__ = ("attrs", "children", "tag")

    def __init__(self, tag: str, attrs: Sequence[tuple[str, str | None]] = ()) -> None:
        self.tag = tag
        self.attrs = list(attrs)
        self.children: list[_Node | str] = []

    def attr(self, name: str) -> str:
        for key, value in self.attrs:
            if key == name:
                return value or ""
        return ""

    def elements(self) -> list[_Node]:
        return [c for c in self.children if isinstance(c, _Node)]


class _Tree(HTMLParser):
    """A forgiving tree: the implicit closes HTML allows, and stray end tags ignored."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("#root")
        self.stack = [self.root]

    def _close_to(self, index: int) -> None:
        del self.stack[index:]

    def _last(self, *tags: str) -> int:
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag in tags:
                return index
        return -1

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in _BLOCK_START and self.stack[-1].tag == "p":
            self.stack.pop()
        if tag == "li" and self._last("li") > self._last("ul", "ol"):
            self._close_to(self._last("li"))
        if tag in {"td", "th"} and self._last("td", "th") > self._last("tr"):
            self._close_to(self._last("td", "th"))
        if tag == "tr" and self._last("tr") > self._last("table"):
            self._close_to(self._last("tr"))
        if tag in {"dt", "dd"} and self._last("dt", "dd") > self._last("dl"):
            self._close_to(self._last("dt", "dd"))
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in _VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        if tag not in _VOID and self.stack[-1].tag == tag:
            self.stack.pop()

    def handle_endtag(self, tag: str) -> None:
        index = self._last(tag)
        if index > 0:
            self._close_to(index)

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)


def _parse(text: str) -> _Node:
    tree = _Tree()
    tree.feed(text)
    tree.close()
    return tree.root


# --------------------------------------------------------------------------- #
# Serializing nodes back to HTML


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _open_tag(node: _Node) -> str:
    attrs = "".join(
        f" {key}" if value is None else f' {key}="{html.escape(value, quote=True)}"'
        for key, value in node.attrs
    )
    return f"<{node.tag}{attrs}>"


def _outer(node: _Node | str, raw: bool = False) -> str:
    if isinstance(node, str):
        return node if raw else _escape(node)
    if node.tag in _VOID:
        return _open_tag(node)
    inner = "".join(_outer(c, raw or node.tag in _RAW) for c in node.children)
    return f"{_open_tag(node)}{inner}</{node.tag}>"


def _inline(children: Sequence[_Node | str]) -> str:
    """Inline content as one line: HTML whitespace collapsed, line breaks as ``<br>``."""
    out: list[str] = []
    for child in children:
        if isinstance(child, _Node) and child.tag == "p":
            out.append(" " + _inline(child.children) + " ")  # a paragraph inside a list item
        else:
            out.append(_outer(child))
    joined = re.sub(r"\s+", " ", "".join(out))
    return re.sub(r"\s*<br>\s*", "<br>", joined).strip()


def _text(node: _Node | str) -> str:
    if isinstance(node, str):
        return node
    return "".join(_text(c) for c in node.children)


def _blank(child: _Node | str) -> bool:
    return isinstance(child, str) and not child.strip()


# --------------------------------------------------------------------------- #
# Nodes to blocks


def _custom_html(node: _Node) -> Block:
    return _new("core/html", None, f"\n{_outer(node)}\n")


def _children_blocks(children: Sequence[_Node | str]) -> list[Block]:
    blocks: list[Block] = []
    pending: list[_Node | str] = []

    def flush() -> None:
        inner = _inline(pending)
        if inner:
            blocks.append(_paragraph(inner))
        pending.clear()

    for child in children:
        if isinstance(child, str) or child.tag in _INLINE:
            pending.append(child)
            continue
        flush()
        blocks.extend(_node_blocks(child))
    flush()
    return blocks


def _image_of(node: _Node) -> tuple[_Node, str] | None:
    """``(img, link)`` when *node* is only a picture, perhaps inside a link."""
    kids = [c for c in node.children if not _blank(c)]
    if node.tag == "img":
        return node, ""
    if len(kids) == 1 and isinstance(kids[0], _Node):
        inner = kids[0]
        if inner.tag == "img":
            return inner, node.attr("href") if node.tag == "a" else ""
        if inner.tag == "a" and node.tag != "a":
            found = _image_of(inner)
            if found is not None:
                return found[0], inner.attr("href")
    return None


def _image_block(img: _Node, link: str, caption: str = "") -> Block:
    if not link:
        return _image(img.attr("src"), img.attr("alt"), caption or None, None, None, None)
    picture = f'<img src="{_esc_attr(img.attr("src"))}" alt="{_esc_attr(img.attr("alt"))}"/>'
    cap = f'<figcaption class="wp-element-caption">{caption}</figcaption>' if caption else ""
    markup = (
        f'\n<figure class="wp-block-image"><a href="{_esc_attr(link)}">{picture}</a>{cap}'
        "</figure>\n"
    )
    return _new("core/image", {"linkDestination": "custom"}, markup)


def _list_block(node: _Node) -> Block:
    items: list[Block] = []
    for li in node.elements():
        if li.tag != "li":
            continue
        nested = [_list_block(c) for c in li.elements() if c.tag in {"ul", "ol"}]
        rest = [c for c in li.children if not (isinstance(c, _Node) and c.tag in {"ul", "ol"})]
        items.append(_list_item(_inline(rest), nested))
    return _list(node.tag == "ol", items)


def _rows(node: _Node) -> list[tuple[str, _Node]]:
    found: list[tuple[str, _Node]] = []
    for child in node.elements():
        if child.tag == "tr":
            found.append((node.tag, child))
        elif child.tag in {"thead", "tbody", "tfoot"}:
            found.extend(_rows(child))
    return found


def _table_block(node: _Node, caption: str = "") -> Block:
    rows = _rows(node)
    cells = [[c for c in tr.elements() if c.tag in {"td", "th"}] for _part, tr in rows]
    if (
        any(
            c.attr("colspan") not in {"", "1"} or c.attr("rowspan") not in {"", "1"}
            for row in cells
            for c in row
        )
        or not rows
    ):
        return _custom_html(node)
    head_count = sum(1 for part, _tr in rows if part == "thead")
    if not head_count and cells[0] and all(c.tag == "th" for c in cells[0]):
        head_count = 1

    def row_html(row: list[_Node], tag: str) -> str:
        return "<tr>" + "".join(f"<{tag}>{_inline(c.children)}</{tag}>" for c in row) + "</tr>"

    markup = '\n<figure class="wp-block-table"><table class="has-fixed-layout">'
    if head_count:
        markup += "<thead>" + "".join(row_html(r, "th") for r in cells[:head_count]) + "</thead>"
    if cells[head_count:]:
        markup += "<tbody>" + "".join(row_html(r, "td") for r in cells[head_count:]) + "</tbody>"
    markup += "</table>"
    if caption:
        markup += f'<figcaption class="wp-element-caption">{caption}</figcaption>'
    return _new("core/table", None, markup + "</figure>\n")


def _figure_blocks(node: _Node) -> list[Block]:
    caption_node = next((c for c in node.elements() if c.tag == "figcaption"), None)
    caption = _inline(caption_node.children) if caption_node is not None else ""
    body = _Node("div", [])
    body.children = [c for c in node.children if c is not caption_node]
    table = next((c for c in body.elements() if c.tag == "table"), None)
    if table is not None and len(body.elements()) == 1:
        return [_table_block(table, caption)]
    found = _image_of(body)
    if found is not None:
        return [_image_block(found[0], found[1], caption)]
    return [_custom_html(node)]


def _node_blocks(node: _Node) -> list[Block]:
    tag = node.tag
    if tag in _DROP:
        return []
    if tag in _UNWRAP:
        return _children_blocks(node.children)
    if re.fullmatch(r"h[1-6]", tag):
        inner = _inline(node.children)
        return [_heading(int(tag[1]), inner)] if inner else []
    if tag == "p":
        found = _image_of(node)
        if found is not None:
            return [_image_block(*found)]
        inner = _inline(node.children)
        return [_paragraph(inner)] if inner else []
    if tag in {"ul", "ol"}:
        return [_list_block(node)]
    if tag == "blockquote":
        cite_node = next((c for c in node.elements() if c.tag in {"cite", "footer"}), None)
        rest = [c for c in node.children if c is not cite_node]
        cite = _inline(cite_node.children) if cite_node is not None else None
        return [_quote_block(_children_blocks(rest), cite)]
    if tag == "pre":
        kids = [c for c in node.children if not _blank(c)]
        if len(kids) == 1 and isinstance(kids[0], _Node) and kids[0].tag == "code":
            return [_code(_text(kids[0]).strip("\n"))]
        return [_preformatted("".join(_outer(c) for c in node.children).strip("\n"))]
    if tag == "hr":
        return [_separator()]
    if tag == "img":
        return [_image_block(node, "")]
    if tag == "table":
        return [_table_block(node)]
    if tag == "figure":
        return _figure_blocks(node)
    return [_custom_html(node)]


# --------------------------------------------------------------------------- #
# Public


def _body_and_title(text: str) -> tuple[list[_Node | str], str]:
    root = _parse(text)
    title_node: _Node | None = None
    body: list[_Node | str] = root.children

    def find(node: _Node, tag: str) -> _Node | None:
        for child in node.elements():
            if child.tag == tag:
                return child
            deeper = find(child, tag)
            if deeper is not None:
                return deeper
        return None

    title_node = find(root, "title")
    body_node = find(root, "body")
    if body_node is not None:
        body = body_node.children
    title = re.sub(r"\s+", " ", _text(title_node)).strip() if title_node is not None else ""
    return body, title


def html_to_blocks(text: str) -> str:
    """An HTML document or fragment as block markup (see the module's note)."""
    body, _title = _body_and_title(text)
    return _emit(_children_blocks(body))


def html_title_and_blocks(text: str, fallback: str) -> tuple[str, str]:
    """``(title, block markup)`` for an HTML document.

    A heading that opens the page is its title and leaves the body, as the
    first heading of a Markdown document does. Without one, the page's
    ``<title>`` is used, then *fallback*.
    """
    body, page_title = _body_and_title(text)
    blocks = _children_blocks(body)
    if blocks and blocks[0].name == "core/heading":
        heading = re.sub(r"<[^>]+>", "", blocks[0].inner_html)
        title = html.unescape(re.sub(r"\s+", " ", heading)).strip()
        if title:
            return title, _emit(blocks[1:])
    return page_title or fallback, _emit(blocks)


def text_to_blocks(text: str) -> str:
    """Plain text as paragraph blocks: blank lines part them, line breaks are kept."""
    paragraphs = re.split(r"\n[ \t]*\n", text.replace("\r\n", "\n").replace("\r", "\n"))
    blocks = [
        _paragraph("<br>".join(_escape(line.rstrip()) for line in chunk.strip("\n").split("\n")))
        for chunk in paragraphs
        if chunk.strip()
    ]
    return _emit(blocks)
