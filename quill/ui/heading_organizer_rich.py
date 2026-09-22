"""The Heading Organizer over a rich text document.

"It should work there." It should: a rich document has headings, the editor has
listed them since heading navigation shipped, and the organizer refused anyway
-- because reordering sections in Markdown is a string operation and in rich
text it is not. A heading there *is* a point size and a bold on a run, so moving
lines as text would arrive unformatted and flatten the document on the way.

What was missing was never the list, it was the move. ``ITextRange.FormattedText``
lets the control copy its own rich content from one range to another, so a
section arrives with its sizes, weights, colours and paragraph properties intact
(:meth:`~quill.ui.richedit_editing.RichEditDocument.reorder_ranges`).

The **same dialog** runs over both kinds of document, which is the point of
doing it this way rather than writing a rich-text organizer: the window, the
arrow keys, the promote and demote, the rename, the duplicate-Heading-1 warning
and everything a person has already learned are one implementation. All this
module does is answer the two questions the dialog asks of a document -- what
are the headings, and please apply these edits -- in the vocabulary of a control
rather than of a string.

Order matters in the applying, and the reason is the same one that makes the
reorder safe: **sections move first, then levels and titles**. Every edit after
the reorder is addressed by the heading's *new* position, read back from the
control, so nothing is applied to an offset that a previous edit has moved.
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from quill.core.markdown_sections import HeadingBlock

__all__ = ["apply_rich_organizer_edits", "rich_heading_blocks", "unchanged"]


def rich_heading_blocks(text: str, headings: list[tuple[int, int, str]]) -> list[HeadingBlock]:
    """The organizer's blocks for a rich document, from its own heading list.

    *headings* is what
    :meth:`~quill.ui.richedit_editing.RichEditDocument.all_headings` returns --
    ``(offset, level, title)`` per heading, in document order.

    The spans follow the Markdown parser's convention exactly, because the
    dialog and the apply step are shared and a second convention would be a
    second set of off-by-ones: a section runs from its heading to the *start of
    the next heading*, so the blank line between two sections belongs to the one
    above it and travels with it.
    """
    blocks: list[HeadingBlock] = []
    for index, (start, level, title) in enumerate(headings):
        line_end = text.find("\n", start)
        heading_end = len(text) if line_end == -1 else line_end
        section_end = headings[index + 1][0] if index + 1 < len(headings) else len(text)
        blocks.append(
            HeadingBlock(
                source_index=index,
                level=int(level),
                title=str(title),
                start=int(start),
                end=heading_end,
                section_start=int(start),
                section_end=int(section_end),
            )
        )
    return blocks


def apply_rich_organizer_edits(
    wrapper: Any,
    original: list[HeadingBlock],
    updated: list[HeadingBlock],
) -> bool:
    """Apply the organizer's edits to the live control. ``True`` if anything moved.

    Three kinds of edit, applied in the one order that cannot trip over itself.

    **The order first.** Every section is rewritten in the new order in a single
    formatted move, so a document whose sections were 1, 2, 3 becomes 3, 1, 2
    with every run's formatting still on it.

    **Then the levels and the titles**, addressed by reading the headings back
    out of the control rather than by arithmetic. After a reorder every offset in
    *original* is stale, and computing the new ones by adding up section lengths
    would be a second implementation of what the control already knows.

    Anything before the first heading -- a title paragraph, a note, a stray blank
    line -- is kept where it is, ahead of the reordered sections. It is not part
    of any section, and dropping it would be the organizer eating text nobody
    asked it to touch.
    """
    by_index = {block.source_index: block for block in original}
    ordered = [by_index[block.source_index] for block in updated if block.source_index in by_index]
    if not ordered:
        return False
    preamble = min(block.section_start for block in original)
    spans: list[tuple[int, int]] = []
    if preamble > 0:
        spans.append((0, preamble))
    spans.extend((block.section_start, block.section_end) for block in ordered)
    wrapper.reorder_ranges(spans)

    # Read the new positions back; the control is the only thing that knows them.
    fresh = wrapper.all_headings()
    for position, block in enumerate(updated):
        if position >= len(fresh):
            break
        start, level, title = fresh[position]
        if block.title != title:
            wrapper.set_range_text(start, start + len(title), block.title)
            fresh = wrapper.all_headings()
            start = fresh[position][0] if position < len(fresh) else start
        if block.level != level:
            wrapper.set_heading_at(start, block.level)
            fresh = wrapper.all_headings()
    return True


def unchanged(original: list[HeadingBlock], updated: list[HeadingBlock]) -> bool:
    """Whether the dialog came back with nothing to do.

    Compared on what the organizer can actually change -- order, level, title --
    rather than on the blocks themselves, whose offsets differ for reasons the
    user did not ask for.
    """
    shape = [(replace(block, start=0, end=0, section_start=0, section_end=0)) for block in updated]
    was = [(replace(block, start=0, end=0, section_start=0, section_end=0)) for block in original]
    return shape == was
