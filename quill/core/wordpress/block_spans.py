"""Where each block sits in a WordPress document's text (wordpress.md 8.3).

A WordPress document is kept in one of two formats (``WorkingCopy.text_format``):

- **html**: real block markup, ``<!-- wp:name {...} -->`` ... ``<!-- /wp:name -->``.
  Its blocks are found with the byte-exact parser in :mod:`blocks`, so each
  block's span is exactly the text that block serializes to.
- **markdown**: ordinary Markdown with ``:::`` fences and island lines
  (:mod:`fences`). Its blocks are found by a line scanner that mirrors the
  fence reader rule for rule, so the scanner and the converter always agree on
  where one block ends and the next begins.

Either way the result is the same flat list of :class:`Span` in document
order, each knowing its parent and children, which is all Next Block, Where Am
I and the Blocks window need. Nothing here edits text; :mod:`block_edit` does.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from quill.core.wordpress.blocks import Block, describe, parse, serialize_block
from quill.core.wordpress.fences import convert_markdown
from quill.core.wordpress.fences_markup import (
    _LIST_ITEM,
    _TABLE_RULE,
    _fence_key,
    _fence_parts,
    _line_kind,
)

__all__ = [
    "NOT_A_STOP",
    "Span",
    "ancestors",
    "block_at",
    "describe_span",
    "html_spans",
    "innermost_at",
    "label",
    "markdown_spans",
    "next_stop",
    "previous_stop",
    "siblings",
    "spans_for",
    "spoken_move",
    "stops",
    "where_am_i",
]

#: Blocks that are part of their parent rather than a place to stop: a list is
#: read as a whole, so its items are not separate stops.
NOT_A_STOP: frozenset[str] = frozenset({"core/list-item"})


@dataclass
class Span:
    """One block's place in the text: ``text[start:end]`` is the whole block."""

    start: int
    end: int
    #: ``core/paragraph``, ``jetpack/contact-form``...
    name: str
    depth: int
    #: Index of the parent span in the same list, or None at the top level.
    parent: int | None
    #: HTML: indexes into ``parse()`` (top level) then ``inner_blocks``.
    #: Markdown: index among top-level blocks, then ``inner_blocks``.
    path: tuple[int, ...]
    children: list[int] = field(default_factory=list)
    #: Markdown only: the island token of a protected block line.
    island: str = ""


# --------------------------------------------------------------------------- #
# HTML


def html_spans(text: str) -> list[Span]:
    """Every block in block markup, outermost first, with exact offsets."""
    spans: list[Span] = []

    def visit(block: Block, pos: int, depth: int, parent: int | None, path: tuple[int, ...]) -> int:
        length = len(serialize_block(block))
        if block.freeform:
            return length
        me = len(spans)
        spans.append(Span(pos, pos + length, block.name or "", depth, parent, path))
        if parent is not None:
            spans[parent].children.append(me)
        if block.inner_blocks:
            cursor = pos + len(block.raw_opener)
            kids = iter(enumerate(block.inner_blocks))
            for item in block.inner_content:
                if item is None:
                    found = next(kids, None)
                    if found is not None:
                        index, child = found
                        cursor += visit(child, cursor, depth + 1, me, (*path, index))
                else:
                    cursor += len(item)
        return length

    pos = 0
    for index, block in enumerate(parse(text)):
        pos += visit(block, pos, 0, None, (index,))
    return spans


# --------------------------------------------------------------------------- #
# Markdown: a scanner that mirrors fences._Reader line for line

_Stops = tuple[frozenset[str], ...]


@dataclass
class _Node:
    name: str
    first: int
    last: int
    children: list[_Node] = field(default_factory=list)
    island: str = ""


_ONE_LINE = {
    "heading": "core/heading",
    "separator": "core/separator",
    "image": "core/image",
}


class _Scanner:
    def __init__(self, text: str) -> None:
        self.raw = text.splitlines(keepends=True)
        self.lines = [line.rstrip("\r\n") for line in self.raw]
        self.i = 0

    def _key(self) -> str | None:
        return _fence_key(self.lines[self.i]) if self.i < len(self.lines) else None

    def read(self, stops: _Stops = (), in_buttons: bool = False) -> list[_Node]:
        out: list[_Node] = []
        while self.i < len(self.lines):
            text = self.lines[self.i]
            kind = _line_kind(text)
            first = self.i
            if kind == "blank":
                self.i += 1
                continue
            if kind == "fence":
                key = _fence_key(text)
                if key == "end " and stops:
                    return out
                if any(key in stop for stop in stops):
                    return out
                out.extend(self._fence(text, stops, in_buttons))
                continue
            if kind == "code":
                self.i += 1
                while self.i < len(self.lines):
                    self.i += 1
                    if self.lines[self.i - 1].rstrip() == "```":
                        break
                out.append(_Node("core/code", first, self.i))
            elif kind in _ONE_LINE:
                self.i += 1
                out.append(_Node(_ONE_LINE[kind], first, self.i))
            elif kind == "quote":
                while self.i < len(self.lines) and self.lines[self.i].startswith(">"):
                    self.i += 1
                out.append(_Node("core/quote", first, self.i))
            elif kind == "list":
                self._list()
                out.append(_Node("core/list", first, self.i))
            elif kind == "table" and self._table_ahead():
                self.i += 2
                while self.i < len(self.lines) and self.lines[self.i].startswith("|"):
                    self.i += 1
                out.append(_Node("core/table", first, self.i))
            else:
                self.i += 1
                while self.i < len(self.lines) and _line_kind(self.lines[self.i]) in (
                    "text",
                    "cite",
                ):
                    self.i += 1
                out.append(_Node("core/paragraph", first, self.i))
        return out

    def _table_ahead(self) -> bool:
        nxt = self.lines[self.i + 1] if self.i + 1 < len(self.lines) else ""
        return bool(_TABLE_RULE.match(nxt)) and "-" in nxt

    def _list(self) -> None:
        head = _LIST_ITEM.match(self.lines[self.i])
        assert head is not None
        ordered = head.group(2) is not None
        while self.i < len(self.lines):
            m = _LIST_ITEM.match(self.lines[self.i])
            if m is None or (m.group(2) is not None) != ordered:
                return
            self.i += 1
            while (
                self.i < len(self.lines)
                and self.lines[self.i][:1] == " "
                and self.lines[self.i].strip()
            ):
                self.i += 1

    def _one(self, name: str, island: str = "") -> list[_Node]:
        self.i += 1
        return [_Node(name, self.i - 1, self.i, island=island)]

    def _fence(self, text: str, stops: _Stops, in_buttons: bool) -> list[_Node]:
        parts = _fence_parts(text)
        assert parts is not None
        head, args = parts
        words = [value for value, _quoted in args]
        first = self.i
        if head == "end":
            self.i += 1
            return []
        if head == "block":
            token = words[-1] if len(words) >= 2 else ""
            return self._one(words[0] if words else "", token)
        if head == "button":
            if in_buttons:
                return self._one("core/button")
            buttons: list[_Node] = []
            while self._key() == "button":
                buttons.extend(self._one("core/button"))
            return [_Node("core/buttons", first, self.i, buttons)]
        if head in ("buttons", "group", "details"):
            children = self._container(head, stops, in_buttons=head == "buttons")
            return [_Node(f"core/{head}", first, self.i, children)]
        if head == "columns":
            return [self._columns(stops)]
        if head == "preformatted":
            self.i += 1
            while self.i < len(self.lines):
                self.i += 1
                if _fence_key(self.lines[self.i - 1]) in ("end preformatted", "end "):
                    break
            return [_Node("core/preformatted", first, self.i)]
        if head == "embed" and words:
            return self._one("core/embed")
        if head == "spacer":
            return self._one("core/spacer")
        return self._one("core/paragraph")

    def _container(self, name: str, stops: _Stops, in_buttons: bool = False) -> list[_Node]:
        self.i += 1
        children = self.read((*stops, frozenset({f"end {name}"})), in_buttons=in_buttons)
        if self._key() in (f"end {name}", "end "):
            self.i += 1
        return children

    def _columns(self, stops: _Stops) -> _Node:
        first = self.i
        self.i += 1
        inner = (*stops, frozenset({"end columns", "column"}))
        before = self.read(inner)
        columns: list[_Node] = []
        while self._key() == "column":
            start = self.i
            self.i += 1
            columns.append(_Node("core/column", start, self.i, self.read(inner)))
            columns[-1].last = self.i
        if self._key() in ("end columns", "end "):
            self.i += 1
        # Text before the first column becomes a column of its own when sent;
        # rather than guess its place, such malformed columns have no stops.
        return _Node("core/columns", first, self.i, [] if before else columns)


def markdown_spans(text: str) -> list[Span]:
    """Every block in Markdown-with-fences, outermost first, with exact offsets."""
    scanner = _Scanner(text)
    nodes = scanner.read()
    starts = [0]
    for line in scanner.raw:
        starts.append(starts[-1] + len(line))
    spans: list[Span] = []

    def end_of(node: _Node) -> int:
        last = node.last - 1
        while last > node.first and not scanner.lines[last].strip():
            last -= 1
        return starts[last] + len(scanner.lines[last])

    def visit(node: _Node, depth: int, parent: int | None, path: tuple[int, ...]) -> None:
        me = len(spans)
        start = starts[node.first]
        spans.append(Span(start, end_of(node), node.name, depth, parent, path, island=node.island))
        if parent is not None:
            spans[parent].children.append(me)
        for index, child in enumerate(node.children):
            visit(child, depth + 1, me, (*path, index))

    for index, node in enumerate(nodes):
        visit(node, 0, None, (index,))
    return spans


def spans_for(text: str, text_format: str) -> list[Span]:
    return html_spans(text) if text_format == "html" else markdown_spans(text)


# --------------------------------------------------------------------------- #
# Reading a span back as a block


def _first_block(markup: str) -> Block | None:
    return next((b for b in parse(markup) if not b.freeform), None)


def block_at(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    index: int,
    islands: Mapping[str, str] | None = None,
) -> Block | None:
    """The parsed block a span stands for (Markdown is converted to read it)."""
    span = spans[index]
    if text_format == "html":
        return _first_block(text[span.start : span.end])
    top = index
    while spans[top].parent is not None:
        top = spans[top].parent  # type: ignore[assignment]
    root = spans[top]
    block = _first_block(convert_markdown(text[root.start : root.end], islands).html)
    for step in span.path[1:]:
        if block is None or step >= len(block.inner_blocks):
            return None
        block = block.inner_blocks[step]
    return block


def describe_span(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    index: int,
    islands: Mapping[str, str] | None = None,
) -> str:
    """ "Image block: Volunteers at the spring fair"."""
    block = block_at(text, text_format, spans, index, islands)
    if block is None:
        return label(spans[index].name) + " block"
    return describe(block)


def label(name: str) -> str:
    """ "Columns" for ``core/columns``: the block's name without "block"."""
    return describe(Block(name=name)).split(" block", 1)[0]


# --------------------------------------------------------------------------- #
# Positions


def stops(spans: Sequence[Span]) -> list[int]:
    """The indexes Next Block and the Blocks window stop at."""
    return [i for i, s in enumerate(spans) if s.name not in NOT_A_STOP]


def innermost_at(spans: Sequence[Span], offset: int) -> int | None:
    """The deepest block containing *offset* (its start, inside, or its end)."""
    found: int | None = None
    for i, span in enumerate(spans):
        if span.start <= offset <= span.end:
            if found is None or span.depth >= spans[found].depth:
                found = i
    return found


def ancestors(spans: Sequence[Span], index: int) -> list[int]:
    """Parents of a span, nearest first."""
    out: list[int] = []
    parent = spans[index].parent
    while parent is not None:
        out.append(parent)
        parent = spans[parent].parent
    return out


def siblings(spans: Sequence[Span], index: int) -> list[int]:
    parent = spans[index].parent
    if parent is not None:
        return list(spans[parent].children)
    return [i for i, s in enumerate(spans) if s.parent is None]


def next_stop(spans: Sequence[Span], caret: int) -> int | None:
    return next((i for i in stops(spans) if spans[i].start > caret), None)


def previous_stop(spans: Sequence[Span], caret: int) -> int | None:
    found = [i for i in stops(spans) if spans[i].start < caret]
    return found[-1] if found else None


def spoken_move(description: str, position: int, total: int) -> str:
    """ "Image block, 4 of 12: Volunteers at the spring fair"."""
    head, sep, detail = description.partition(": ")
    return f"{head}, {position} of {total}" + (f": {detail}" if sep else "")


def _where(spans: Sequence[Span], index: int) -> str:
    span = spans[index]
    if span.name == "core/column" and span.parent is not None:
        number = spans[span.parent].children.index(index) + 1
        return f"column {number} of {label(spans[span.parent].name)}"
    return label(span.name)


def where_am_i(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    caret: int,
    islands: Mapping[str, str] | None = None,
) -> str:
    """ "Paragraph block: Morning sessions, inside column 1 of Columns"."""
    index = innermost_at(spans, caret)
    if index is None:
        after = next_stop(spans, caret)
        if after is None:
            return "Not in a block, and there are no blocks after this point."
        nxt = describe_span(text, text_format, spans, after, islands)
        return f"Not in a block. The next one is {nxt}."
    parent_of = spans[index].parent
    if spans[index].name in NOT_A_STOP and parent_of is not None:
        index = parent_of
    sentence = describe_span(text, text_format, spans, index, islands)
    chain: list[str] = []
    skip: int | None = None
    for parent in ancestors(spans, index):
        if parent == skip:
            continue
        chain.append(_where(spans, parent))
        if spans[parent].name == "core/column":
            skip = spans[parent].parent
    if chain:
        sentence += ", inside " + ", inside ".join(chain)
    return sentence + "."
