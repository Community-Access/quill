"""The WordPress block grammar: parse and serialize post content (wordpress.md 8).

This is the grammar of Gutenberg's ``@wordpress/block-serialization-default-parser``:
a block is an HTML comment pair, ``<!-- wp:name {"json":"attrs"} -->`` ...
``<!-- /wp:name -->``, or one void comment ending ``/-->``. Everything outside
any block is *freeform* (the "classic" content the parser hands back with a
``null`` block name).

The one promise this module makes above all others is the round trip:
``serialize(parse(text)) == text``, byte for byte, for *any* input. A post
opened in QUILL and sent back untouched must not change by a single character,
because the block editor marks a block "invalid" the moment its markup differs
from what it expects (section 8.5). So each parsed block keeps its original
opening and closing comment text and reuses it until its name or attributes
are changed on purpose.

Two deliberate differences from the JavaScript parser, both on malformed input
only, and both so that nothing is ever lost or duplicated:

- a closing comment must name the block it closes; a stray or mismatched one
  is left in place as plain text rather than closing whatever happens to be
  open;
- an opening comment that is never closed is left in place as plain text, and
  what followed it is parsed as if it were not there. (The JavaScript parser
  copies the rest of the document into every unclosed block.)
"""

from __future__ import annotations

import copy
import html
import json
import math
import re
from collections.abc import Iterable, Iterator, Sequence
from dataclasses import dataclass, field
from typing import Any

__all__ = [
    "CORE_TEXT_BLOCKS",
    "Block",
    "describe",
    "first_words",
    "parse",
    "serialize",
    "serialize_attributes",
    "serialize_block",
    "walk",
]

#: The core blocks that map onto plain Markdown or HTML (section 8.1): these
#: are written as ordinary writing, never as fences.
CORE_TEXT_BLOCKS: frozenset[str] = frozenset({
    "core/paragraph",
    "core/heading",
    "core/list",
    "core/list-item",
    "core/quote",
    "core/image",
    "core/table",
    "core/separator",
    "core/code",
    "core/preformatted",
})


@dataclass
class Block:
    """One parsed block, in the shape the Gutenberg parser returns.

    ``inner_content`` is the source of truth for serialization: its strings
    are the block's own HTML, and each ``None`` marks where the next of
    ``inner_blocks`` sits. ``inner_html`` is the strings joined, for reading.
    A freeform block (HTML outside any block) has ``name`` None and its text
    as the single entry of ``inner_content``.
    """

    name: str | None
    attrs: dict[str, Any] = field(default_factory=dict)
    inner_blocks: list[Block] = field(default_factory=list)
    inner_html: str = ""
    inner_content: list[str | None] = field(default_factory=list)
    #: The original ``<!-- wp:... -->`` text, reused while nothing changed.
    raw_opener: str = field(default="", repr=False, compare=False)
    #: The original ``<!-- /wp:... -->`` text ("" for a void block).
    raw_closer: str = field(default="", repr=False, compare=False)
    _orig_name: str | None = field(default=None, repr=False, compare=False)
    _orig_attrs: dict[str, Any] | None = field(default=None, repr=False, compare=False)
    _orig_void: bool = field(default=False, repr=False, compare=False)

    @property
    def freeform(self) -> bool:
        """True for HTML outside any block (the parser's classic content)."""
        return self.name is None

    @property
    def namespace(self) -> str:
        """``core`` for ``core/paragraph``; "" for freeform content."""
        if self.name is None:
            return ""
        return self.name.split("/", 1)[0]

    @classmethod
    def from_text(cls, text: str) -> Block:
        """A freeform block holding ``text`` exactly."""
        return cls(name=None, inner_html=text, inner_content=[text] if text else [])


# ---------------------------------------------------------------------------
# Tokenizer
# ---------------------------------------------------------------------------

_HEAD = re.compile(r"<!--\s+(/)?wp:([a-z][a-z0-9_-]*/)?([a-z][a-z0-9_-]*)\s+")
_TAIL_PLAIN = re.compile(r"(/)?-->")
_TAIL_ATTRS = re.compile(r"\}\s+(/)?-->")


@dataclass(frozen=True)
class _Token:
    kind: str  # "opener" | "closer" | "void"
    start: int
    end: int
    name: str
    attrs: dict[str, Any]


def _parse_attrs(text: str | None) -> dict[str, Any]:
    if text is None:
        return {}
    try:
        value = json.loads(text)
    except (ValueError, RecursionError):
        return {}
    return value if isinstance(value, dict) else {}


def _tokens(text: str) -> list[_Token]:
    out: list[_Token] = []
    pos = 0
    while True:
        m = _HEAD.search(text, pos)
        if m is None:
            return out
        after = m.end()
        attrs_text: str | None = None
        tail = _TAIL_PLAIN.match(text, after)
        if tail is None and text.startswith("{", after):
            tail = _TAIL_ATTRS.search(text, after)
            if tail is not None:
                attrs_text = text[after : tail.start() + 1]
        if tail is None:
            pos = m.start() + 1
            continue
        closer, namespace, short = m.group(1), m.group(2), m.group(3)
        name = (namespace or "core/") + short
        if tail.group(1):
            kind = "void"
        elif closer:
            kind = "closer"
        else:
            kind = "opener"
        out.append(_Token(kind, m.start(), tail.end(), name, _parse_attrs(attrs_text)))
        pos = tail.end()


def _pair(tokens: Sequence[_Token]) -> list[bool]:
    """Which tokens are real delimiters; the rest stay in the text."""
    valid = [False] * len(tokens)
    stack: list[int] = []
    for i, tok in enumerate(tokens):
        if tok.kind == "void":
            valid[i] = True
        elif tok.kind == "opener":
            stack.append(i)
        else:
            for depth in range(len(stack) - 1, -1, -1):
                if tokens[stack[depth]].name == tok.name:
                    valid[stack[depth]] = True
                    valid[i] = True
                    del stack[depth:]
                    break
    return valid


# ---------------------------------------------------------------------------
# Parse
# ---------------------------------------------------------------------------


def _start_block(tok: _Token, text: str) -> Block:
    block = Block(name=tok.name, attrs=tok.attrs)
    block.raw_opener = text[tok.start : tok.end]
    block._orig_name = tok.name
    block._orig_attrs = copy.deepcopy(tok.attrs)
    block._orig_void = tok.kind == "void"
    return block


def parse(text: str) -> list[Block]:
    """Parse post content into blocks. Never raises; never loses a byte."""
    tokens = _tokens(text)
    valid = _pair(tokens)
    output: list[Block] = []
    stack: list[Block] = []
    pos = 0

    def add_text(chunk: str) -> None:
        if not chunk:
            return
        if stack:
            stack[-1].inner_content.append(chunk)
            stack[-1].inner_html += chunk
        else:
            output.append(Block.from_text(chunk))

    def add_block(block: Block) -> None:
        if stack:
            stack[-1].inner_blocks.append(block)
            stack[-1].inner_content.append(None)
        else:
            output.append(block)

    for tok, ok in zip(tokens, valid, strict=True):
        if not ok:
            continue
        add_text(text[pos : tok.start])
        if tok.kind == "void":
            add_block(_start_block(tok, text))
        elif tok.kind == "opener":
            stack.append(_start_block(tok, text))
        else:
            block = stack.pop()
            block.raw_closer = text[tok.start : tok.end]
            add_block(block)
        pos = tok.end
    add_text(text[pos:])
    return output


# ---------------------------------------------------------------------------
# Serialize
# ---------------------------------------------------------------------------


def _js_numbers(value: Any) -> Any:
    """Integral floats print as JavaScript prints them (``1``, not ``1.0``)."""
    if isinstance(value, float) and math.isfinite(value) and value.is_integer():
        if abs(value) < 1e21:
            return int(value)
    if isinstance(value, dict):
        return {k: _js_numbers(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_js_numbers(v) for v in value]
    return value


def serialize_attributes(attrs: dict[str, Any]) -> str:
    """Gutenberg's ``serializeAttributes``: JSON safe inside an HTML comment."""
    text = json.dumps(_js_numbers(attrs), ensure_ascii=False, separators=(",", ":"))
    return (
        text
        .replace("--", "\\u002d\\u002d")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
        .replace('\\"', "\\u0022")
    )


def _comment_name(name: str) -> str:
    return name[5:] if name.startswith("core/") else name


def serialize_block(block: Block) -> str:
    """One block back to text, reusing its original comments when unchanged."""
    if block.name is None:
        return "".join(part for part in block.inner_content if part is not None)
    children = iter(block.inner_blocks)
    parts: list[str] = []
    for item in block.inner_content:
        if item is None:
            child = next(children, None)
            if child is not None:
                parts.append(serialize_block(child))
        else:
            parts.append(item)
    parts.extend(serialize_block(child) for child in children)
    content = "".join(parts)
    short = _comment_name(block.name)
    same_name = bool(block.raw_opener) and block.name == block._orig_name
    if same_name and block.attrs == block._orig_attrs:
        if not block._orig_void:
            return block.raw_opener + content + (block.raw_closer or f"<!-- /wp:{short} -->")
        if not content:
            return block.raw_opener
    attrs = serialize_attributes(block.attrs) + " " if block.attrs else ""
    if not content:
        return f"<!-- wp:{short} {attrs}/-->"
    if same_name and block.raw_closer:
        closer = block.raw_closer
    else:
        closer = f"<!-- /wp:{short} -->"
    return f"<!-- wp:{short} {attrs}-->" + content + closer


def serialize(blocks: Iterable[Block]) -> str:
    """Blocks back to post content: exactly the text :func:`parse` was given."""
    return "".join(serialize_block(block) for block in blocks)


# ---------------------------------------------------------------------------
# Reading helpers
# ---------------------------------------------------------------------------


def walk(
    blocks: Sequence[Block], *, include_freeform: bool = False
) -> Iterator[tuple[int, tuple[int, ...], Block]]:
    """Every block in document order as ``(depth, path, block)``.

    ``path`` indexes the real lists (freeform entries included), so
    ``blocks[path[0]].inner_blocks[path[1]]`` is the block it names. Freeform
    content is skipped unless ``include_freeform`` is set, and whitespace-only
    freeform is always skipped.
    """

    def visit(
        items: Sequence[Block], depth: int, prefix: tuple[int, ...]
    ) -> Iterator[tuple[int, tuple[int, ...], Block]]:
        for index, block in enumerate(items):
            path = (*prefix, index)
            if block.freeform:
                if include_freeform and block.inner_html.strip():
                    yield depth, path, block
                continue
            yield depth, path, block
            yield from visit(block.inner_blocks, depth + 1, path)

    yield from visit(blocks, 0, ())


_SKIP_ELEMENTS = re.compile(r"<(script|style)\b.*?</\1\s*>", re.S | re.I)
_TAG = re.compile(r"<!--.*?-->|<[^<>]*>", re.S)


def _rendered(block: Block) -> str:
    children = iter(block.inner_blocks)
    parts: list[str] = []
    for item in block.inner_content:
        if item is None:
            child = next(children, None)
            if child is not None:
                parts.append(" " + _rendered(child) + " ")
        else:
            parts.append(item)
    return "".join(parts)


def _plain(markup: str) -> str:
    text = _TAG.sub(" ", _SKIP_ELEMENTS.sub(" ", markup))
    return " ".join(html.unescape(text).split())


def first_words(block: Block, n: int = 8) -> str:
    """The first ``n`` words of the block's text, tags and entities removed."""
    return " ".join(_plain(_rendered(block)).split()[:n])


_FRIENDLY: dict[str, str] = {
    "core/paragraph": "Paragraph",
    "core/heading": "Heading",
    "core/list": "List",
    "core/list-item": "List item",
    "core/quote": "Quote",
    "core/pullquote": "Pull quote",
    "core/image": "Image",
    "core/gallery": "Gallery",
    "core/table": "Table",
    "core/separator": "Separator",
    "core/code": "Code",
    "core/preformatted": "Preformatted",
    "core/verse": "Verse",
    "core/button": "Button",
    "core/buttons": "Buttons",
    "core/columns": "Columns",
    "core/column": "Column",
    "core/group": "Group",
    "core/cover": "Cover",
    "core/media-text": "Media and text",
    "core/details": "Details",
    "core/embed": "Embed",
    "core/spacer": "Spacer",
    "core/html": "Custom HTML",
    "core/shortcode": "Shortcode",
    "core/video": "Video",
    "core/audio": "Audio",
    "core/file": "File",
    "core/latest-posts": "Latest posts",
    "core/query": "Query loop",
    "core/navigation": "Navigation",
    "core/more": "More",
    "core/nextpage": "Page break",
    "core/social-links": "Social icons",
    "core/social-link": "Social icon",
    "core/search": "Search",
    "core/block": "Synced pattern",
    "core/freeform": "Classic",
    "core/footnotes": "Footnotes",
}


def _derived_name(name: str) -> str:
    short = name.split("/", 1)[-1].replace("-", " ").replace("_", " ").strip()
    return short[:1].upper() + short[1:] if short else name


def _detail(block: Block) -> str:
    name = block.name
    if name == "core/image":
        alt = re.search(r'<img\b[^>]*\balt="([^"]*)"', block.inner_html)
        if alt and alt.group(1).strip():
            return html.unescape(alt.group(1)).strip()
        caption = first_words(block)
        return caption or "no alt text"
    if name == "core/embed":
        url = block.attrs.get("url")
        return url if isinstance(url, str) else first_words(block)
    if name == "core/spacer":
        height = block.attrs.get("height", "100px")
        return str(height)
    if name == "core/columns":
        count = sum(1 for child in block.inner_blocks if child.name == "core/column")
        return f"{count} column" + ("" if count == 1 else "s")
    if name in {"core/separator", "core/more", "core/nextpage"}:
        return ""
    return first_words(block)


def describe(block: Block) -> str:
    """A spoken one-line name: "Button block: Book a session"."""
    if block.name is None:
        words = first_words(block)
        return f"Classic content: {words}" if words else "Classic content"
    label = _FRIENDLY.get(block.name) or _derived_name(block.name)
    if block.name == "core/heading":
        level = block.attrs.get("level", 2)
        label = f"Heading level {level}"
    head = f"{label} block"
    if block.namespace != "core":
        head += " (from a plugin)"
    detail = _detail(block)
    return f"{head}: {detail}" if detail else head
