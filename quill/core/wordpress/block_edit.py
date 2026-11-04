"""Changing blocks without breaking them (wordpress.md 8.3, 8.5).

Every operation here takes the document text and the spans from
:mod:`block_spans` and returns the new text and where the caret goes. Each one
rewrites only the block it is about: the bytes before and after it are copied,
never re-serialized, so a block QUILL did not touch goes back to the site
exactly as it came (8.5). The commands put the result in the editor with one
``replace_text``, which is one undo step.

The same operations work on both document formats. HTML documents move real
block markup; Markdown documents move Markdown and ``:::`` fences, and when an
operation copies a protected island it gets a fresh island token, so changing
one copy later never changes the other.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field

from quill.core.wordpress.block_spans import Span, block_at, siblings
from quill.core.wordpress.blocks import Block, parse, serialize, serialize_block
from quill.core.wordpress.fences import blocks_to_markdown
from quill.core.wordpress.fences_markup import (
    _HEADING,
    _LIST_ITEM,
    _escape_line,
    _heading,
    _list,
    _list_item,
    _paragraph,
    _quote_block,
)

__all__ = [
    "Edit",
    "change_targets",
    "change_to",
    "duplicate",
    "group",
    "insert_markup",
    "markup_to_text",
    "move",
    "remove",
    "replace_block",
    "ungroup",
]


@dataclass
class Edit:
    """The whole new text, where the caret goes, and any new island originals."""

    text: str
    caret: int
    islands: dict[str, str] = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# Islands


_ISLAND_LINE = re.compile(r"^(:::[ \t]+block[ \t]+\S+[ \t]+)(\S+)([ \t]*)$", re.M)


def _next_number(islands: Mapping[str, str]) -> int:
    numbers = [int(k[7:]) for k in islands if k.startswith("island-") and k[7:].isdigit()]
    return max(numbers, default=0) + 1


def _retoken(
    markdown: str, originals: Mapping[str, str], existing: Mapping[str, str]
) -> tuple[str, dict[str, str]]:
    """Give every island line in *markdown* a token not already in *existing*."""
    number = _next_number(existing)
    added: dict[str, str] = {}

    def fresh(m: re.Match[str]) -> str:
        nonlocal number
        original = originals.get(m.group(2))
        if original is None:
            return m.group(0)
        token = f"island-{number}"
        number += 1
        added[token] = original
        return m.group(1) + token + m.group(3)

    return _ISLAND_LINE.sub(fresh, markdown), added


def markup_to_text(
    markup: str, text_format: str, islands: Mapping[str, str]
) -> tuple[str, dict[str, str]]:
    """Block markup as the document's own format, plus any new islands."""
    if text_format == "html":
        return markup, {}
    markdown, produced = blocks_to_markdown(parse(markup))
    return _retoken(markdown.rstrip("\n"), produced, islands)


# --------------------------------------------------------------------------- #
# Inserting


def _pad(text: str, at: int, new: str) -> tuple[str, int]:
    before, after = text[:at], text[at:]
    if not before or before.endswith("\n\n"):
        lead = ""
    else:
        lead = "\n" if before.endswith("\n") else "\n\n"
    if not after:
        trail = "\n"
    elif after.startswith("\n\n"):
        trail = ""
    elif after.startswith("\n"):
        trail = "\n"
    else:
        trail = "\n\n"
    return lead + new + trail, len(lead)


def insert_markup(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    caret: int,
    markup: str,
    islands: Mapping[str, str] | None = None,
) -> tuple[int, str, int, dict[str, str]]:
    """Where to insert a new block and what to type there.

    Returns ``(offset, inserted, caret_after, new_islands)``: the new block
    goes right after the innermost block the caret is inside (never into the
    middle of one's markup), or at the start of the caret's line when the
    caret is between blocks. ``caret_after`` is the new block's start.
    """
    new, added = markup_to_text(markup, text_format, islands or {})
    inside = [s for s in spans if s.start < caret < s.end or (s.end == caret and caret)]
    if inside:
        at = max(inside, key=lambda s: (s.depth, s.start)).end
    else:
        at = text.rfind("\n", 0, caret) + 1
    inserted, lead = _pad(text, at, new)
    return at, inserted, at + lead, added


# --------------------------------------------------------------------------- #
# Structure: move, duplicate, remove, group, ungroup


def move(text: str, spans: Sequence[Span], index: int, step: int) -> Edit | str:
    """Swap a block with its previous (*step* -1) or next (+1) sibling."""
    family = siblings(spans, index)
    where = family.index(index)
    other_at = where + step
    if other_at < 0:
        return "This is already the first block here."
    if other_at >= len(family):
        return "This is already the last block here."
    a, b = sorted((spans[index], spans[family[other_at]]), key=lambda s: s.start)
    first, middle, second = text[a.start : a.end], text[a.end : b.start], text[b.start : b.end]
    new = text[: a.start] + second + middle + first + text[b.end :]
    caret = a.start if step < 0 else a.start + len(second) + len(middle)
    return Edit(new, caret)


def duplicate(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    index: int,
    islands: Mapping[str, str] | None = None,
) -> Edit:
    """A copy of the block straight after it, with the same gap between them."""
    span = spans[index]
    family = siblings(spans, index)
    where = family.index(index)
    if where + 1 < len(family):
        gap = text[span.end : spans[family[where + 1]].start]
    elif where > 0:
        gap = text[spans[family[where - 1]].end : span.start]
    else:
        gap = "\n\n"
    copy = text[span.start : span.end]
    added: dict[str, str] = {}
    if text_format != "html" and islands:
        copy, added = _retoken(copy, islands, islands)
    insert_at = span.end
    new = text[:insert_at] + gap + copy + text[insert_at:]
    return Edit(new, insert_at + len(gap), added)


def remove(text: str, spans: Sequence[Span], index: int) -> Edit:
    """Take the block out, with the gap that separated it from a neighbour."""
    span = spans[index]
    family = siblings(spans, index)
    where = family.index(index)
    if where + 1 < len(family):
        start, end = span.start, spans[family[where + 1]].start
        caret = start
    elif where > 0:
        start, end = spans[family[where - 1]].end, span.end
        caret = spans[family[where - 1]].start
    else:
        start, end = span.start, span.end
        caret = start
    return Edit(text[:start] + text[end:], caret)


#: Blocks that only make sense inside their parent, so cannot be grouped alone.
_NOT_GROUPABLE = frozenset({"core/column", "core/list-item", "core/button"})


def group(text: str, text_format: str, spans: Sequence[Span], index: int) -> Edit | str:
    """Wrap the block in a Group block, the way the block editor writes one."""
    span = spans[index]
    if span.name in _NOT_GROUPABLE:
        return "This block lives inside its parent, so group the parent instead."
    inner = text[span.start : span.end]
    if text_format == "html":
        wrapped = (
            '<!-- wp:group {"layout":{"type":"constrained"}} -->\n'
            f'<div class="wp-block-group">{inner}</div>\n<!-- /wp:group -->'
        )
    else:
        wrapped = f"::: group\n{inner}\n::: end group"
    return Edit(text[: span.start] + wrapped + text[span.end :], span.start)


def ungroup(text: str, spans: Sequence[Span], index: int) -> Edit | str:
    """Replace a Group block by the blocks inside it."""
    span = spans[index]
    if span.name != "core/group":
        return "Only a Group block can be ungrouped."
    inner = "\n\n".join(text[spans[c].start : spans[c].end] for c in span.children)
    return Edit(text[: span.start] + inner + text[span.end :], span.start)


# --------------------------------------------------------------------------- #
# Change To

_P = re.compile(r"\s*<p(?:\s[^>]*)?>(.*)</p>\s*", re.S)
_H = re.compile(r"\s*<h([1-6])(?:\s[^>]*)?>(.*)</h\1>\s*", re.S)
_LI = re.compile(r"\s*<li(?:\s[^>]*)?>(.*?)(?:</li>)?\s*", re.S)
_CITE = re.compile(r"<cite>(.*?)</cite>", re.S)
_BR = re.compile(r"<br\s*/?>")


def change_targets(name: str) -> list[tuple[str, str]]:
    """``(key, spoken label)`` for every block this one can change to."""
    headings = [(f"heading-{n}", f"Heading level {n}") for n in range(2, 7)]
    if name == "core/paragraph":
        return [*headings[:3], ("list", "List"), ("quote", "Quote")]
    if name == "core/heading":
        return [("paragraph", "Paragraph"), *headings]
    if name in ("core/list", "core/quote"):
        return [("paragraphs", "Paragraphs")]
    return []


def _items(block: Block) -> list[str]:
    out: list[str] = []
    for item in block.inner_blocks:
        head = next((part for part in item.inner_content if part is not None), "")
        m = _LI.fullmatch(head)
        if m and m.group(1).strip():
            out.append(m.group(1).strip())
        for nested in item.inner_blocks:
            out.extend(_items(nested))
    return out


def _html_change(text: str, spans: Sequence[Span], index: int, target: str) -> str | None:
    span = spans[index]
    block = block_at(text, "html", spans, index)
    if block is None:
        return None
    built: list[Block] = []
    if block.name == "core/paragraph" and (m := _P.fullmatch(block.inner_html)):
        inner = m.group(1)
        if target.startswith("heading-"):
            built = [_heading(int(target[8:]), inner)]
        elif target == "list":
            lines = [part.strip() for part in _BR.split(inner) if part.strip()]
            built = [_list(False, [_list_item(line, []) for line in lines])]
        elif target == "quote":
            built = [_quote_block([_paragraph(inner)], None)]
    elif block.name == "core/heading" and (m := _H.fullmatch(block.inner_html)):
        if target == "paragraph":
            built = [_paragraph(m.group(2))]
        elif target.startswith("heading-"):
            built = [_heading(int(target[8:]), m.group(2))]
    elif block.name == "core/list" and target == "paragraphs":
        built = [_paragraph(item) for item in _items(block)]
    elif block.name == "core/quote" and target == "paragraphs":
        parts = [text[spans[c].start : spans[c].end] for c in span.children]
        cite = _CITE.search(block.inner_html)
        if cite:
            parts.append(serialize_block(_paragraph(cite.group(1))))
        return "\n\n".join(parts)
    if not built:
        return None
    return "\n\n".join(serialize_block(b) for b in built)


def _md_change(segment: str, name: str, target: str) -> str | None:
    lines = segment.split("\n")
    if name == "core/paragraph":
        if target.startswith("heading-"):
            return "#" * int(target[8:]) + " " + " ".join(line.strip() for line in lines)
        if target == "list":
            return "\n".join(f"- {line.strip()}" for line in lines if line.strip())
        if target == "quote":
            return "\n".join(f"> {line}" if line else ">" for line in lines)
    if name == "core/heading":
        m = _HEADING.match(lines[0])
        if m is None:
            return None
        if target == "paragraph":
            return _escape_line(m.group(2))
        if target.startswith("heading-"):
            return "#" * int(target[8:]) + " " + m.group(2)
    if name == "core/list" and target == "paragraphs":
        out: list[str] = []
        for line in lines:
            item = _LIST_ITEM.match(line.strip())
            words = item.group(4) if item else line.strip()
            if words:
                out.append(_escape_line(words))
        return "\n\n".join(out)
    if name == "core/quote" and target == "paragraphs":
        body = [line[2:] if line.startswith("> ") else line[1:] for line in lines]
        return "\n".join(body).strip("\n")
    return None


def change_to(
    text: str, text_format: str, spans: Sequence[Span], index: int, target: str
) -> Edit | str:
    """Turn a paragraph into a heading, a list into paragraphs, and so on."""
    span = spans[index]
    if target not in {key for key, _label in change_targets(span.name)}:
        return "This block cannot change to that."
    segment = text[span.start : span.end]
    if text_format == "html":
        new = _html_change(text, spans, index, target)
    else:
        new = _md_change(segment.replace("\r\n", "\n"), span.name, target)
    if new is None:
        return "This block has settings QUILL would lose by changing it, so it was left alone."
    return Edit(text[: span.start] + new + text[span.end :], span.start)


# --------------------------------------------------------------------------- #
# Rewriting one block (Block Settings)


def replace_block(
    text: str,
    text_format: str,
    spans: Sequence[Span],
    index: int,
    change: Callable[[Block], None],
    islands: Mapping[str, str] | None = None,
) -> Edit | str:
    """Apply *change* to the block a span stands for and write it back.

    HTML rewrites only that block's markup. Markdown rewrites the top-level
    block that holds it, through the same checked converter Open uses, so
    anything Markdown cannot say becomes a protected island line rather than
    being lost; the edit's ``islands`` then holds the new originals.
    """
    if text_format == "html":
        span = spans[index]
        blocks = parse(text[span.start : span.end])
        target = next((b for b in blocks if not b.freeform), None)
        if target is None:
            return "QUILL could not read this block."
        change(target)
        new = serialize(blocks)
        return Edit(text[: span.start] + new + text[span.end :], span.start)
    top = index
    while spans[top].parent is not None:
        top = spans[top].parent  # type: ignore[assignment]
    root = block_at(text, text_format, spans, top, islands)
    walker: Block | None = root
    for step in spans[index].path[1:]:
        if walker is None or step >= len(walker.inner_blocks):
            walker = None
            break
        walker = walker.inner_blocks[step]
    if root is None or walker is None:
        return "QUILL could not read this block."
    change(walker)
    new_text, added = markup_to_text(serialize_block(root), text_format, islands or {})
    span = spans[top]
    return Edit(text[: span.start] + new_text + text[span.end :], span.start, added)
