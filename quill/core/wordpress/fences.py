"""Blocks to readable Markdown and back (wordpress.md 8.1).

Ordinary writing stays ordinary: a paragraph, heading, list, quote, image,
table, separator or code block is plain Markdown. The other blocks QUILL
knows are ``:::`` fences::

    ::: button "Book a session" https://example.org/book

    ::: columns
    ::: column
    Morning sessions run from nine.
    ::: column
    Evening sessions run from six.
    ::: end columns

Anything else is an *island*: one line, ``::: block jetpack/contact-form
island-3``, whose original text waits in a side table and goes back byte for
byte.

**Nothing is converted on trust.** Each block's Markdown is turned straight
back into block markup and compared with the original; if the two differ by
one byte (an extra class, a colour, an attribute QUILL has no Markdown for),
the block becomes an island instead. So opening a post and sending it back
never changes a block the user did not edit, and the Markdown that *is* shown
is always Markdown QUILL can write back exactly.

New blocks written in Markdown serialize the way WordPress's own save code
writes them (WordPress 6.4 and later), so the block editor does not mark them
invalid (section 8.5). A fence that cannot be understood never raises: it is
kept as a paragraph of text and reported as a :class:`FenceProblem` with its
line, for Check Before Publishing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

from quill.core.wordpress.blocks import Block, parse
from quill.core.wordpress.fences_markup import (
    _HEADING,
    _IMAGE,
    _LIST_ITEM,
    _TABLE_RULE,
    _button,
    _buttons,
    _code,
    _column,
    _columns,
    _details,
    _embed,
    _emit,
    _fence_key,
    _fence_parts,
    _group,
    _heading,
    _image,
    _inline_to_html,
    _line_kind,
    _list,
    _list_item,
    _md_unescape,
    _paragraph,
    _preformatted,
    _quote_block,
    _separator,
    _spacer,
    _table,
    _unquote,
)
from quill.core.wordpress.fences_write import _join_chunks, _Writer

__all__ = [
    "FenceProblem",
    "FenceResult",
    "blocks_to_markdown",
    "check_markdown",
    "convert_markdown",
    "markdown_to_blocks",
    "post_to_markdown",
]


@dataclass(frozen=True)
class FenceProblem:
    """A line of the Markdown QUILL could not turn into a block."""

    line: int
    message: str


@dataclass(frozen=True)
class FenceResult:
    """Block markup ready to send, plus anything that needs a human look."""

    html: str
    problems: list[FenceProblem] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Markdown -> blocks
# ---------------------------------------------------------------------------

_Line = tuple[int, str]
_Stops = tuple[frozenset[str], ...]


class _Reader:
    def __init__(
        self, lines: Sequence[_Line], islands: Mapping[str, str], problems: list[FenceProblem]
    ) -> None:
        self.lines = list(lines)
        self.i = 0
        self.islands = islands
        self.problems = problems

    # -- helpers -----------------------------------------------------------
    def _line(self) -> _Line | None:
        return self.lines[self.i] if self.i < len(self.lines) else None

    def _problem(self, line: int, message: str) -> None:
        self.problems.append(FenceProblem(line, message))

    def _at(self, keys: frozenset[str]) -> bool:
        current = self._line()
        return current is not None and _fence_key(current[1]) in keys

    def _literal(self, text: str) -> Block:
        return _paragraph(_inline_to_html(text))

    # -- sequences -----------------------------------------------------------
    def read(self, stops: _Stops = (), in_buttons: bool = False) -> list[Block]:
        out: list[Block] = []
        while (current := self._line()) is not None:
            number, text = current
            kind = _line_kind(text)
            if kind == "blank":
                self.i += 1
                continue
            if kind == "fence":
                key = _fence_key(text)
                if key == "end " and stops:
                    return out
                if any(key in stop for stop in stops):
                    return out
                out.extend(self._fence(number, text, stops, in_buttons))
            elif kind == "code":
                out.append(self._code(number, text))
            elif kind == "heading":
                m = _HEADING.match(text)
                assert m is not None
                out.append(_heading(len(m.group(1)), _inline_to_html(m.group(2))))
                self.i += 1
            elif kind == "separator":
                out.append(_separator())
                self.i += 1
            elif kind == "quote":
                out.append(self._quote())
            elif kind == "list":
                out.append(self._list())
            elif kind == "table" and self._table_ahead():
                out.append(self._table())
            elif kind == "image":
                out.append(self._image(number, text))
            else:
                out.append(self._paragraph())
        return out

    def _paragraph(self) -> Block:
        collected = [self.lines[self.i][1]]
        self.i += 1
        while (current := self._line()) is not None and _line_kind(current[1]) in ("text", "cite"):
            collected.append(current[1])
            self.i += 1
        return _paragraph(_inline_to_html("\n".join(collected)))

    def _code(self, number: int, opener: str) -> Block:
        self.i += 1
        body: list[str] = []
        while (current := self._line()) is not None:
            self.i += 1
            if current[1].rstrip() == "```":
                return _code("\n".join(body))
            body.append(current[1])
        self._problem(number, "This code block has no closing ``` line, so it runs to the end.")
        return _code("\n".join(body))

    def _quote(self) -> Block:
        sub: list[_Line] = []
        while (current := self._line()) is not None and current[1].startswith(">"):
            text = current[1]
            sub.append((current[0], text[2:] if text.startswith("> ") else text[1:]))
            self.i += 1
        cite: str | None = None
        while sub and not sub[-1][1].strip():
            sub.pop()
        if sub and sub[-1][1].startswith("-- "):
            cite = _inline_to_html(sub.pop()[1][3:])
        children = _Reader(sub, self.islands, self.problems).read()
        return _quote_block(children, cite)

    def _list(self) -> Block:
        first = _LIST_ITEM.match(self.lines[self.i][1])
        assert first is not None
        ordered = first.group(2) is not None
        items: list[Block] = []
        while (current := self._line()) is not None:
            m = _LIST_ITEM.match(current[1])
            if m is None or (m.group(2) is not None) != ordered:
                break
            self.i += 1
            offset = len(current[1]) - len(m.group(4))
            sub: list[_Line] = []
            while (more := self._line()) is not None and more[1][:1] == " " and more[1].strip():
                lead = len(more[1]) - len(more[1].lstrip(" "))
                sub.append((more[0], more[1][min(lead, offset) :]))
                self.i += 1
            nested = _Reader(sub, self.islands, self.problems).read() if sub else []
            if any(block.name != "core/list" for block in nested) or len(nested) > 1:
                self._problem(sub[0][0], "Only one nested list can be indented under a list item.")
            items.append(_list_item(_inline_to_html(m.group(4)), nested))
        return _list(ordered, items)

    def _table_ahead(self) -> bool:
        nxt = self.lines[self.i + 1][1] if self.i + 1 < len(self.lines) else ""
        return bool(_TABLE_RULE.match(nxt)) and "-" in nxt

    @staticmethod
    def _cells(line: str) -> list[str]:
        text = line.strip()
        if text.startswith("|"):
            text = text[1:]
        if text.endswith("|") and not text.endswith("\\|"):
            text = text[:-1]
        cells = re.split(r"(?<!\\)\|", text)
        return [_inline_to_html(cell.strip()) for cell in cells]

    def _table(self) -> Block:
        header = self._cells(self.lines[self.i][1])
        self.i += 2
        rows: list[list[str]] = []
        while (current := self._line()) is not None and current[1].startswith("|"):
            row = self._cells(current[1])
            row = (row + [""] * len(header))[: max(len(header), 1)]
            rows.append(row)
            self.i += 1
        return _table(header, rows)

    def _image(self, number: int, text: str) -> Block:
        m = _IMAGE.match(text)
        assert m is not None
        self.i += 1
        alt = _md_unescape(m.group(1))
        caption = _inline_to_html(_unquote(m.group(3))) if m.group(3) else None
        image_id: int | None = None
        size: str | None = None
        link: str | None = None
        for word in (m.group(4) or "").split():
            key, _, value = word.partition("=")
            if key == "id" and value.isdigit():
                image_id = int(value)
            elif key == "size" and value:
                size = value
            elif key == "link" and value:
                link = value
            else:
                self._problem(number, f"The image setting {word!r} is not one QUILL knows.")
        return _image(m.group(2), alt, caption, image_id, size, link)

    # -- fences --------------------------------------------------------------
    def _fence(self, number: int, text: str, stops: _Stops, in_buttons: bool) -> list[Block]:
        parts = _fence_parts(text)
        assert parts is not None
        head, args = parts
        words = [value for value, _quoted in args]
        if head == "end":
            self._problem(number, "This end line has no block open to end.")
            self.i += 1
            return []
        if head == "block":
            return self._island(number, text, words)
        if head == "button":
            if in_buttons:
                return [self._button_line(number, text, args)]
            group: list[Block] = []
            while (current := self._line()) is not None and _fence_key(current[1]) == "button":
                inner = _fence_parts(current[1])
                assert inner is not None
                group.append(self._button_line(current[0], current[1], inner[1]))
            return [_buttons(group)]
        if head == "buttons":
            return [_buttons(self._container(number, "buttons", stops, in_buttons=True))]
        if head == "columns":
            return [self._columns(number, stops)]
        if head == "group":
            return [_group(self._container(number, "group", stops))]
        if head == "details":
            summary = _inline_to_html(" ".join(words)) if words else ""
            if not words:
                self._problem(number, "A details block needs a summary line in quotes.")
            return [_details(summary, self._container(number, "details", stops))]
        if head == "preformatted":
            return [self._preformatted(number)]
        if head == "embed":
            self.i += 1
            if not words:
                self._problem(number, "An embed needs the address to embed.")
                return [self._literal(text)]
            options: dict[str, str] = {}
            for word in words[1:]:
                key, _, value = word.partition("=")
                options[key] = value
            unknown = set(options) - {"type", "provider", "aspect"}
            if unknown:
                self._problem(
                    number, f"The embed setting {sorted(unknown)[0]!r} is not one QUILL knows."
                )
            return [
                _embed(
                    words[0], options.get("type"), options.get("provider"), options.get("aspect")
                )
            ]
        if head == "spacer":
            self.i += 1
            return [_spacer(words[0] if words else None)]
        self.i += 1
        if head == "column":
            self._problem(number, "A column line belongs inside ::: columns.")
        elif head:
            self._problem(
                number, f"QUILL does not know a {head!r} block, so this line is kept as text."
            )
        else:
            self._problem(number, "This ::: line names no block, so it is kept as text.")
        return [self._literal(text)]

    def _island(self, number: int, text: str, words: Sequence[str]) -> list[Block]:
        self.i += 1
        token = words[-1] if len(words) >= 2 else ""
        original = self.islands.get(token)
        if original is None:
            self._problem(
                number, "This protected block's original text is missing, so it cannot be sent."
            )
            return [self._literal(text)]
        return [b for b in parse(original) if not (b.freeform and not b.inner_html.strip())]

    def _button_line(self, number: int, text: str, args: Sequence[tuple[str, bool]]) -> Block:
        self.i += 1
        if not args:
            self._problem(number, "A button needs its text, in quotes, and then its link.")
            return _button("", None)
        if args[0][1]:
            label, rest = args[0][0], [value for value, _q in args[1:]]
        elif len(args) > 1 and re.match(r"^(?:[a-z][a-z0-9+.-]*:|/|#)", args[-1][0], re.I):
            label, rest = " ".join(v for v, _q in args[:-1]), [args[-1][0]]
        else:
            label, rest = " ".join(v for v, _q in args), []
        if len(rest) > 1:
            self._problem(number, "A button takes its text in quotes and then one link.")
        return _button(_inline_to_html(label), rest[0] if rest else None)

    def _container(
        self, number: int, name: str, stops: _Stops, in_buttons: bool = False
    ) -> list[Block]:
        self.i += 1
        stop = frozenset({f"end {name}"})
        children = self.read((*stops, stop), in_buttons=in_buttons)
        current = self._line()
        if current is not None and _fence_key(current[1]) in (f"end {name}", "end "):
            self.i += 1
        else:
            self._problem(number, f"This {name} block has no '::: end {name}' line.")
        return children

    def _columns(self, number: int, stops: _Stops) -> Block:
        self.i += 1
        stop = frozenset({"end columns", "column"})
        inner = (*stops, stop)
        columns: list[Block] = []
        before = self.read(inner)
        if before:
            self._problem(number, "Text after ::: columns needs a ::: column line first.")
            columns.append(_column(None, before))
        while self._at(frozenset({"column"})):
            current = self._line()
            assert current is not None
            parts = _fence_parts(current[1])
            assert parts is not None
            width = parts[1][0][0] if parts[1] else None
            self.i += 1
            columns.append(_column(width, self.read(inner)))
        if self._at(frozenset({"end columns", "end "})):
            self.i += 1
        else:
            self._problem(number, "These columns have no '::: end columns' line.")
        return _columns(columns)

    def _preformatted(self, number: int) -> Block:
        self.i += 1
        body: list[str] = []
        while (current := self._line()) is not None:
            if _fence_key(current[1]) in ("end preformatted", "end "):
                self.i += 1
                return _preformatted("\n".join(body))
            body.append(current[1])
            self.i += 1
        self._problem(number, "This preformatted block has no '::: end preformatted' line.")
        return _preformatted("\n".join(body))


def _read_markdown(
    markdown: str, islands: Mapping[str, str]
) -> tuple[list[Block], list[FenceProblem]]:
    text = markdown.replace("\r\n", "\n").replace("\r", "\n")
    lines = list(enumerate(text.split("\n"), start=1))
    problems: list[FenceProblem] = []
    blocks = _Reader(lines, islands, problems).read()
    return blocks, problems


def convert_markdown(markdown: str, islands: Mapping[str, str] | None = None) -> FenceResult:
    """Markdown (with fences and islands) to block markup, plus any problems."""
    blocks, problems = _read_markdown(markdown, islands or {})
    return FenceResult(_emit(blocks), problems)


def markdown_to_blocks(markdown: str, islands: Mapping[str, str] | None = None) -> str:
    """Markdown to block markup ready to send. Never raises."""
    return convert_markdown(markdown, islands).html


def check_markdown(markdown: str, islands: Mapping[str, str] | None = None) -> list[FenceProblem]:
    """The fences Check Before Publishing should name, with their lines."""
    return convert_markdown(markdown, islands).problems


def _reread(
    lines: Sequence[str], islands: Mapping[str, str], in_buttons: bool
) -> list[Block] | None:
    problems: list[FenceProblem] = []
    reader = _Reader(list(enumerate(lines, start=1)), islands, problems)
    rebuilt = reader.read(in_buttons=in_buttons)
    return None if problems else rebuilt


def blocks_to_markdown(blocks: Sequence[Block]) -> tuple[str, dict[str, str]]:
    """Blocks to readable Markdown, and the island table that restores the rest.

    Whitespace between top-level blocks becomes one blank line; everything
    else either converts exactly or is kept, byte for byte, as an island.
    """
    writer = _Writer(_reread)
    chunks: list[list[str]] = []
    for block in blocks:
        if block.freeform:
            text = block.inner_html.strip()
            if text:
                chunks.append(writer.island(Block.from_text(text), text))
            continue
        chunks.append(writer.block(block))
    lines = _join_chunks(chunks)
    return ("\n".join(lines) + "\n" if lines else ""), writer.islands


def post_to_markdown(content: str) -> tuple[str, dict[str, str]]:
    """Post content (block markup) straight to Markdown and its islands."""
    return blocks_to_markdown(parse(content))
