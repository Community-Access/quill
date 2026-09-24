"""Headings as a tree: parsing, boundaries, and the arithmetic of a move.

Extracted from :mod:`quill.core.markdown_sections` (GATE-11), which had grown
into a grab-bag of three unrelated jobs -- working out the shape of a document,
composing the sentence a screen reader hears about it, and filling in list
markers. This module is the first of those, and it answers only questions about
shape: where a section starts, what is inside it, which heading is next to it,
and where the caret lands once two spans have traded places.

Nothing here edits a document except :func:`swap_sections`, which is pure text.
The verbs people press keys for -- Move Section, Select Section, Move Section
To -- live in :mod:`quill.core.markdown_sections` and
:mod:`quill.core.section_move_to`, and are built out of these pieces.

Helpers that were private to the old module keep their behaviour exactly and
lose the leading underscore, because a name three modules share is not private.
``markdown_sections`` re-exports everything it always exported, so no caller
outside this package had to change.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Literal

__all__ = [
    "HTML_HEADING_PATTERN",
    "HTML_TAG_PATTERN",
    "MD_HEADING_PATTERN",
    "HeadingBlock",
    "HeadingContext",
    "MoveResult",
    "Section",
    "SectionSelection",
    "caret_after_move",
    "contains_the_rest",
    "find_sibling",
    "outer_neighbour",
    "parent_title",
    "parse_heading_blocks",
    "section_for_caret",
    "sibling_position",
    "split_trailing_newlines",
    "subtree_end",
    "swap_sections",
]


MD_HEADING_PATTERN = re.compile(r"^(?P<marker>#{1,6})[ \t]*(?P<title>.*)$", re.MULTILINE)
HTML_HEADING_PATTERN = re.compile(
    r"<h(?P<level>[1-6])(?P<attrs>[^>]*)>(?P<body>.*?)</h(?P=level)>",
    re.IGNORECASE | re.DOTALL,
)
HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
# Recognise the opening line of a fenced code block.  The closing fence is any
# line that contains only the same fence character (``` or ~~~), optionally
# preceded by up to three spaces of indentation and followed by optional
# trailing whitespace.  We deliberately use a permissive regex here because
# indented closing fences (CommonMark §4.5) are common in real-world docs.
_FENCE_PATTERN = re.compile(r"^(?P<indent>[ ]{0,3})(?P<fence>`{3,}|~{3,})[ \t]*(?P<info>.*)$")


@dataclass(frozen=True, slots=True)
class HeadingBlock:
    source_index: int
    level: int
    title: str
    start: int
    end: int
    section_start: int
    section_end: int
    attributes: str = ""


@dataclass(frozen=True, slots=True)
class HeadingContext:
    level: int
    ordinal: int
    total: int
    title: str


@dataclass(frozen=True, slots=True)
class Section:
    level: int
    title: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


@dataclass(frozen=True, slots=True)
class SectionSelection:
    """A section's whole extent, and enough about it to say so out loud."""

    #: Offsets into the document: the heading line through the last line under
    #: it, subsections included.
    start: int
    end: int
    #: The heading's own text, for the announcement.
    title: str
    level: int
    #: This section plus every section nested inside it. ``1`` means a leaf.
    sections: int
    #: Lines the selection covers, counted the way a person counts them.
    lines: int


class MoveResult(StrEnum):
    OK = "ok"
    NO_SECTION = "no_section"
    # TOP / BOTTOM cover "there is no sibling that way", which is the same
    # thing said about the document instead of about the search: a section
    # with no sibling above it is already first among its siblings.
    TOP = "top"
    BOTTOM = "bottom"


def parse_heading_blocks(text: str, markup_kind: str) -> list[HeadingBlock]:
    if markup_kind == "markdown":
        return _parse_markdown_heading_blocks(text)
    if markup_kind == "html":
        return _parse_html_heading_blocks(text)
    return []


def _is_fence_close(line: str, open_fence: str) -> bool:
    """Return True if ``line`` closes the fence opened with ``open_fence``.

    CommonMark §4.5: a closing fence must use the same character (``` or ~~~)
    as the opening fence and be at least as long.  Indentation up to three
    spaces is allowed.  Anything after the fence is treated as info-string
    content and ignored.
    """
    stripped = line.lstrip(" ")
    indent = len(line) - len(stripped)
    if indent > 3:
        return False
    if not stripped.startswith(open_fence[0]):
        return False
    char = open_fence[0]
    count = 0
    for ch in stripped:
        if ch == char:
            count += 1
        else:
            break
    return count >= len(open_fence) and stripped[count:].strip() == ""


def _parse_markdown_heading_blocks(text: str) -> list[HeadingBlock]:
    # Walk the document line by line so we can recognise fenced code blocks
    # (``` or ~~~) and skip any `# ...` lines that appear inside them.
    # CommonMark §4.5: an opening fence is 3+ backticks or tildes; a closing
    # fence must use the same character and be at least as long.
    blocks: list[HeadingBlock] = []
    open_fence: str | None = None
    block_index = 0
    line_start = 0
    for line in text.splitlines(keepends=True):
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if open_fence is not None:
            if _is_fence_close(line, open_fence):
                open_fence = None
        else:
            fence_match = _FENCE_PATTERN.match(line) if indent <= 3 else None
            if fence_match is not None:
                open_fence = fence_match.group("fence")
            else:
                heading_match = MD_HEADING_PATTERN.match(line)
                if heading_match is not None:
                    start = line_start
                    end = line_start + len(line)
                    blocks.append(
                        HeadingBlock(
                            source_index=block_index,
                            level=len(heading_match.group("marker")),
                            title=(heading_match.group("title") or "").strip(),
                            start=start,
                            end=end,
                            section_start=start,
                            section_end=0,  # filled in once the next block is found
                        )
                    )
                    block_index += 1
        line_start += len(line)
    # Fill in section_end for every block: the last block's section runs to
    # end-of-text; earlier blocks end where the next block begins.
    for index, block in enumerate(blocks):
        if index + 1 < len(blocks):
            blocks[index] = replace(block, section_end=blocks[index + 1].start)
        else:
            blocks[index] = replace(block, section_end=len(text))
    return blocks


def _parse_html_heading_blocks(text: str) -> list[HeadingBlock]:
    matches = list(HTML_HEADING_PATTERN.finditer(text))
    blocks: list[HeadingBlock] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_title = HTML_TAG_PATTERN.sub("", match.group("body"))
        blocks.append(
            HeadingBlock(
                source_index=index,
                level=int(match.group("level")),
                title=" ".join(raw_title.split()),
                start=start,
                end=end,
                section_start=start,
                section_end=section_end,
                attributes=match.group("attrs") or "",
            )
        )
    return blocks


def section_for_caret(blocks: list[HeadingBlock], caret: int) -> tuple[int, int, int, int] | None:
    """Return ``(index, level, section_start, section_end)`` for the section
    whose start is at or before ``caret`` and whose end is after ``caret``.

    If the caret is past the last section's end, return that last section.
    Returns ``None`` if there are no sections at all.
    """
    if not blocks:
        return None
    chosen_index = 0
    for index, block in enumerate(blocks):
        if block.start <= caret:
            chosen_index = index
        else:
            break
    block = blocks[chosen_index]
    return chosen_index, block.level, block.section_start, block.section_end


def find_sibling(
    blocks: list[HeadingBlock], section_index: int, direction: Literal["up", "down"]
) -> int | None:
    """Return the index of the closest sibling (same ``level``) of
    ``blocks[section_index]`` in the requested direction, or ``None``.

    A sibling shares the same level and has the same parent (the nearest
    preceding heading whose level is strictly less).  Top-level headings
    (``level == 1``) all share an implicit parent of 0, so any other
    ``level == 1`` heading is a sibling.
    """
    if not blocks or section_index < 0 or section_index >= len(blocks):
        return None
    current = blocks[section_index]
    if direction == "up":
        for index in range(section_index - 1, -1, -1):
            other = blocks[index]
            if other.level < current.level:
                return None
            if other.level == current.level:
                return index
        return None
    # direction == "down"
    for index in range(section_index + 1, len(blocks)):
        other = blocks[index]
        if other.level < current.level:
            return None
        if other.level == current.level:
            return index
    return None


def subtree_end(blocks: list[HeadingBlock], section_index: int, text_length: int) -> int:
    """Where ``blocks[section_index]``'s section ends, **subsections included**.

    ``HeadingBlock.section_end`` stops at the next heading of *any* level, which
    is the right answer for "which section is the caret in" and the wrong one
    for moving: a section is a heading plus everything under it, down to the
    next heading of equal or higher level. Moving by ``section_end`` left the
    children behind -- ``## A1`` with a ``### A1a`` under it swapped past
    ``## A2`` and the ``### A1a`` stayed where it was, under a heading it had
    nothing to do with. That is a document silently rearranged into something
    nobody wrote, which is the worst thing this command could do.
    """
    level = blocks[section_index].level
    for other in blocks[section_index + 1 :]:
        if other.level <= level:
            return other.section_start
    return text_length


def outer_neighbour(
    blocks: list[HeadingBlock],
    section_index: int,
    direction: Literal["up", "down"],
    text_length: int,
) -> tuple[int, int, str] | None:
    """What to trade places with when there is no sibling that way.

    Returns ``(start, end, title)`` for the block immediately above or below
    this section, or ``None`` when there is nothing there at all.

    This is the "move past whatever is next to me" half of Word's Move Up /
    Move Down, and the two directions are not mirror images, because a document
    is a tree rather than a list:

    * **Up** takes the block immediately before this section -- which, when this
      section is the first child of its parent, is the parent's own heading and
      body, *not* the parent's subtree. That subtree contains this section, and
      nothing can trade places with something it is inside. The effect is that a
      first child rises above its parent's heading, which is what Word's outline
      Move Up does.
    * **Down** takes the next block after this whole subtree, and that block's
      subtree with it. Anything deeper is already inside this section and
      travels with it, so the first block past the subtree is always at this
      level or shallower.

    Both spans meet this section exactly -- the "up" span ends where this
    section starts, the "down" span starts where it ends -- so the swap is
    always of two adjacent, non-overlapping ranges.
    """
    if direction == "up":
        if section_index <= 0:
            return None
        previous = blocks[section_index - 1]
        return previous.section_start, blocks[section_index].section_start, previous.title
    after = subtree_end(blocks, section_index, text_length)
    for index in range(section_index + 1, len(blocks)):
        if blocks[index].section_start == after:
            return after, subtree_end(blocks, index, text_length), blocks[index].title
    return None


def swap_sections(text: str, first: tuple[int, int], second: tuple[int, int]) -> str:
    """Swap two ``(start, end)`` ranges in ``text``.

    Ranges must be non-overlapping and ordered such that ``first`` precedes
    ``second``.  Any gap between them rides in the middle, where it already is.

    **The blank lines stay with the slot, not with the section.**  Each range is
    split into its content and the run of newlines that ends it, and the two
    runs stay in document order while the contents change places.  Sections
    rarely end the same way -- the last one in a file typically ends with a
    single newline and every earlier one with a blank line -- so carrying the
    terminator along with the text jams two headings together on consecutive
    lines at one end of the swap and leaves a stray blank line at the other.
    Splitting them means a document keeps exactly the shape it had, which is
    what makes this safe to press twice.
    """
    a_start, a_end = first
    b_start, b_end = second
    if a_end > b_start:
        raise ValueError("ranges must be ordered and non-overlapping")
    a_body, a_tail = split_trailing_newlines(text[a_start:a_end])
    b_body, b_tail = split_trailing_newlines(text[b_start:b_end])
    gap = text[a_end:b_start]
    return text[:a_start] + b_body + a_tail + gap + a_body + b_tail + text[b_end:]


def split_trailing_newlines(span: str) -> tuple[str, str]:
    """``("## A\\n\\nbody", "\\n\\n")`` -- the section, and how it ended."""
    body = span.rstrip("\n")
    return body, span[len(body) :]


def caret_after_move(
    caret: int,
    section_start: int,
    new_text: str,
    moved_heading_line: str,
) -> int:
    """Compute the caret position after a section has been moved.

    The caret is preserved as an offset from the heading line start (column
    within the heading) so it lands on the same column of the moved heading.
    We look the moved heading up in ``new_text`` rather than relying on a
    precomputed destination, because the swap helper can shift the section
    by an arbitrary offset (the gap between the swapped sections rides
    with the moved section).
    """
    column = max(0, caret - section_start)
    heading_pos = new_text.find(moved_heading_line)
    if heading_pos == -1:
        return caret
    heading_line_end = moved_heading_line.find("\n")
    if heading_line_end == -1:
        heading_line_end = len(moved_heading_line)
    column = min(column, heading_line_end)
    return heading_pos + column


def parent_title(blocks: list[HeadingBlock], section_index: int) -> str:
    """Return the title of the nearest enclosing heading, or ``""``.

    The parent is the closest preceding heading whose level is strictly less
    than this one's.  Top-level headings have no parent.
    """
    if not blocks or section_index <= 0 or section_index >= len(blocks):
        return ""
    level = blocks[section_index].level
    for index in range(section_index - 1, -1, -1):
        if blocks[index].level < level:
            return str(blocks[index].title).strip()
    return ""


def sibling_position(blocks: list[HeadingBlock], section_index: int) -> tuple[int, int]:
    """``(ordinal, total)`` for this section among its siblings, 1-based.

    What a sighted reader gets from glancing at the page after a move, and the
    one thing the screen reader will not say: it reports that the text changed,
    never where in the outline the thing now sits.
    """
    if not blocks or not 0 <= section_index < len(blocks):
        return (1, 1)
    level = blocks[section_index].level
    before = 0
    for index in range(section_index - 1, -1, -1):
        if blocks[index].level < level:
            break
        if blocks[index].level == level:
            before += 1
    after = 0
    for index in range(section_index + 1, len(blocks)):
        if blocks[index].level < level:
            break
        if blocks[index].level == level:
            after += 1
    return (before + 1, before + 1 + after)


def contains_the_rest(blocks: list[HeadingBlock], section_index: int, text_length: int) -> str:
    """The title of the first section *inside* this one, when this section runs
    to the end of the document; otherwise ``""``.

    The one case where "you cannot move down" needs more than a refusal. In a
    strictly nested outline everything below the caret is *inside* the section
    the caret is in, so there is nothing left for it to move below -- and no
    rule about moving can change that. What can change it is promoting the
    child, so the answer says so instead of closing the door.
    """
    if subtree_end(blocks, section_index, text_length) != text_length:
        return ""
    if section_index + 1 >= len(blocks):
        return ""
    return blocks[section_index + 1].title
