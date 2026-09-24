"""The section verbs: select one, move one, and rewrite a document around it.

This module used to be everything -- the heading parser, the section
arithmetic, the sentences both editors speak, and the list-marker helpers --
and at 1085 lines it had become a grab-bag whose name described only a third of
it. It is now the *verbs* only, and the three jobs it was carrying live beside
it:

* :mod:`quill.core.section_tree` -- the shapes (``HeadingBlock``, ``Section``,
  ``SectionSelection``, ``MoveResult``) and the arithmetic: parse, boundaries,
  siblings, subtree ends, swapping two spans.
* :mod:`quill.core.section_speech` -- the one sentence each outcome gets, so
  that QUILL and QuillLite cannot word the same action two ways.
* :mod:`quill.core.list_markers` -- numbered- and bulleted-list markers, which
  were never about sections at all.
* :mod:`quill.core.section_move_to` -- Move Section To, the destination picker.

Every name this module exported before it was split is still exported from it,
so no caller outside the package changed.

Public API:

* :func:`current_section_at` -- find the section containing the caret.
* :func:`section_selection_at` -- the same section *including* its
  subsections, for Select Section and the clipboard.
* :func:`move_section` -- apply a one-step move and return the new text, new
  caret, the result code, and a screen-reader-friendly announce string.
* :func:`apply_heading_organizer_edits` -- rewrite a document after the
  Heading Organizer dialog has reordered or renamed its sections.
* :func:`heading_context_at` -- describe the heading containing a caret.
* :func:`validate_heading_sequence` -- check a list of parsed headings for
  common structural problems.

The Markdown path is fence-aware so ``# not a heading`` lines inside a
````` or ``~~~`` block are never matched.  For plain text (no Markdown),
the section-move code falls back to form-feed (``\f``) delimited blocks,
which the main editor produces when text is pasted from certain sources.
"""

from __future__ import annotations

from typing import Literal

from quill.core.section_speech import (
    announce_edge,
    describe_move,
    describe_section_selection,
)
from quill.core.section_tree import (
    HTML_HEADING_PATTERN,
    MD_HEADING_PATTERN,
    HeadingBlock,
    HeadingContext,
    MoveResult,
    Section,
    SectionSelection,
    caret_after_move,
    contains_the_rest,
    find_sibling,
    outer_neighbour,
    parent_title,
    parse_heading_blocks,
    section_for_caret,
    subtree_end,
    swap_sections,
)

__all__ = [
    "HeadingBlock",
    "HeadingContext",
    "MoveResult",
    "Section",
    "SectionSelection",
    "apply_heading_organizer_edits",
    "current_section_at",
    "describe_section_selection",
    "heading_context_at",
    "move_section",
    "parse_heading_blocks",
    "section_selection_at",
    "validate_heading_sequence",
]


def validate_heading_sequence(
    blocks: list[HeadingBlock],
    *,
    require_single_h1: bool = False,
) -> list[str]:
    """Return a list of issue strings for common heading-structure mistakes."""
    issues: list[str] = []
    if not blocks:
        return issues
    first = blocks[0]
    if first.level != 1:
        issues.append(
            f"Heading order should start at H1 (found H{first.level}: {first.title or '(empty)'})"
        )
    h1_count = 0
    previous_level = 0
    for block in blocks:
        title = block.title.strip()
        if not title:
            issues.append(f"Heading H{block.level} is empty")
        if block.level == 1:
            h1_count += 1
        if previous_level and block.level > previous_level + 1:
            issues.append(
                f"Heading level skipped: H{previous_level} -> H{block.level} at "
                f"'{title or '(empty heading)'}'"
            )
        previous_level = block.level
    if require_single_h1 and h1_count > 1:
        issues.append(f"Expected a single H1 but found {h1_count}")
    return issues


def heading_context_at(text: str, target: int, markup_kind: str) -> HeadingContext | None:
    """Describe the heading whose start line contains ``target``.

    Returns the heading level (1-6), its 1-based ordinal among all headings,
    the total heading count, and the heading title. Matching is by line so
    it is robust to leading whitespace differences. Returns ``None`` when
    the target is not on a heading line.
    """
    blocks = parse_heading_blocks(text, markup_kind)
    if not blocks:
        return None
    # #314: walk the text once and record the line index for each block
    # plus the target, instead of calling ``text.count("\\n", 0, ...)``
    # once per block.  The previous implementation was O(N*H) for a
    # document with N newlines and H headings; this is O(N).
    next_block = 0
    block_line_at: list[int | None] = [None] * len(blocks)
    target_line = -1
    line_index = 0
    pending_target_line = -1
    for index, ch in enumerate(text):
        if next_block < len(blocks) and blocks[next_block].start == index:
            block_line_at[next_block] = line_index
            next_block += 1
        if index == target:
            pending_target_line = line_index
        if ch == "\n":
            line_index += 1
    if pending_target_line != -1:
        target_line = pending_target_line
    else:
        # ``target`` was at or past end-of-text: it lives on the line
        # after the last newline (which is ``line_index`` if there was
        # one, or 0 if there were no newlines at all).
        target_line = line_index
    for block_index, block_line in enumerate(block_line_at):
        if block_line == target_line:
            block = blocks[block_index]
            return HeadingContext(
                level=block.level,
                ordinal=block_index + 1,
                total=len(blocks),
                title=block.title.strip(),
            )
    return None


def apply_heading_organizer_edits(
    text: str,
    markup_kind: str,
    updated_blocks: list[HeadingBlock],
) -> str:
    """Rewrite ``text`` after the Heading Organizer dialog has reordered or
    renamed its sections (#359).

    Preserves the inter-section whitespace pattern of the original
    document.  Sections that were separated by a blank line
    (``# A\\nA body\\n\\n# B``) are still separated by a blank line in
    the new order; tight sections (``# First\\nA\\n## Second``) remain
    tight.  The pre-consolidation code spliced raw section strings
    back-to-back, which lost blank-line gaps on reorder.

    The parser stores each section's ``section_end`` as the *start* of
    the next section's heading, so the trailing blank line (``\\n\\n``)
    is recorded inside the previous section's content rather than in a
    gap.  We strip the trailing whitespace from each section's content,
    then re-emit sections in the new order separated by either ``\\n\\n``
    (if any original consecutive pair had a blank line) or ``\\n``.
    """
    original_blocks = parse_heading_blocks(text, markup_kind)
    if not original_blocks or not updated_blocks:
        return text
    by_index = {block.source_index: block for block in original_blocks}
    sorted_originals = sorted(original_blocks, key=lambda block: block.section_start)
    first_start = sorted_originals[0].section_start
    # The parser stores ``section_end`` as the *start* of the next
    # section's heading, so the trailing blank-line whitespace
    # (``\\n\\n``) lives inside the previous section's content rather
    # than in a gap between sections. Detect whether the document uses
    # blank-line separators between sections: a section whose content
    # ends in two-or-more ``\\n``s is followed by a blank line. If any
    # pair uses a blank line, treat the whole document as
    # blank-separated so reordering cannot drop a gap; the extra ``\\n``
    # is added between every consecutive pair in the new output.
    uses_blank_line = False
    for block in sorted_originals[:-1]:
        content = text[block.section_start : block.section_end]
        if content.endswith("\n\n"):
            uses_blank_line = True
            break
    # The blank-line separator is one extra ``\\n`` (each section's body
    # already ends in its own line terminator, so tight = nothing extra,
    # blank-separated = one extra ``\\n``).
    inter_separator = "\n" if uses_blank_line else ""
    last_block = sorted_originals[-1]
    last_trailing = text[last_block.section_end :]
    rebuilt: list[str] = [text[:first_start]]
    valid_updated = [block for block in updated_blocks if block.source_index in by_index]
    for index, block in enumerate(valid_updated):
        original = by_index[block.source_index]
        section_text = text[original.section_start : original.section_end]
        # Normalize so the section ends in exactly one ``\\n``: strip any
        # trailing newlines then add a single newline terminator.
        section_text = section_text.rstrip("\n") + "\n"
        rewritten = _rewrite_first_heading(
            section_text,
            markup_kind,
            block.level,
            block.title,
            original,
        )
        rebuilt.append(rewritten)
        if index + 1 < len(valid_updated):
            rebuilt.append(inter_separator)
        else:
            rebuilt.append(last_trailing)
    return "".join(rebuilt)


def _rewrite_first_heading(
    section: str,
    markup_kind: str,
    level: int,
    title: str,
    original: HeadingBlock,
) -> str:
    normalized_level = min(6, max(1, int(level)))
    normalized_title = title.strip()
    if markup_kind == "markdown":
        return MD_HEADING_PATTERN.sub(
            f"{'#' * normalized_level} {normalized_title}",
            section,
            count=1,
        )
    if markup_kind == "html":
        replacement = (
            f"<h{normalized_level}{original.attributes}>{normalized_title}</h{normalized_level}>"
        )
        return HTML_HEADING_PATTERN.sub(replacement, section, count=1)
    return section


def section_selection_at(
    text: str, caret: int, *, markup_kind: str = "markdown"
) -> SectionSelection | None:
    """The section the caret is in, **including its subsections**, or ``None``.

    The span :func:`move_section` moves, offered to the clipboard: select it and
    ordinary Control X and Control V put a section anywhere, in this document or
    another one or another program. That is the answer to "move it somewhere
    there is no heading to move past", and it needs no new mental model --
    which is why it is a selection rather than a fifth kind of move.

    Selecting from a heading to exactly the start of the next one is the
    operation this exists to replace: by ear that boundary is invisible, it has
    to be found by trial, and getting it wrong loses your place in the document
    you were halfway through reorganising.
    """
    if markup_kind not in {"markdown", "html"}:
        return None
    blocks = parse_heading_blocks(text, markup_kind)
    if not blocks:
        return None
    found = section_for_caret(blocks, caret)
    if found is None:
        return None
    index, level, start, _own_end = found
    end = subtree_end(blocks, index, len(text))
    nested = sum(1 for block in blocks[index + 1 :] if block.section_start < end)
    span = text[start:end]
    # Trailing blank lines belong to the gap between sections rather than to
    # this one, so they are neither selected nor counted. Selecting them would
    # make a cut-and-paste swallow the separation between two sections and run
    # the next heading onto the end of this one.
    span = span.rstrip("\n")
    end = start + len(span)
    return SectionSelection(
        start=start,
        end=end,
        title=blocks[index].title,
        level=level,
        sections=nested + 1,
        lines=span.count("\n") + 1 if span else 0,
    )


def current_section_at(text: str, caret: int, *, markup_kind: str = "markdown") -> Section | None:
    """Return the section containing ``caret``, or ``None`` if no section.

    Markdown and HTML documents share the same fence-aware parser path
    (HTML uses ``<hN>`` tags; markdown uses ``#``/``##``/etc.).  Plain
    text falls back to form-feed (``\\f``) delimited blocks.
    """
    if markup_kind in {"markdown", "html"}:
        blocks = parse_heading_blocks(text, markup_kind)
        if not blocks:
            return None
        found = section_for_caret(blocks, caret)
        if found is None:
            return None
        _, level, start, end = found
        return Section(level=level, title="", start=start, end=end)
    # Plain text: split on form-feed (no nesting concept).
    if "\f" not in text:
        return None
    boundaries: list[int] = [0]
    for index, ch in enumerate(text):
        if ch == "\f":
            boundaries.append(index + 1)
    if boundaries[-1] != len(text):
        boundaries.append(len(text))
    for index in range(len(boundaries) - 1):
        section_start = boundaries[index]
        section_end = boundaries[index + 1]
        if section_start <= caret < section_end:
            return Section(level=0, title="", start=section_start, end=section_end)
    if boundaries and caret >= boundaries[-1]:
        last_start = boundaries[-1]
        return Section(level=0, title="", start=last_start, end=len(text))
    return None


def move_section(
    text: str,
    caret: int,
    direction: Literal["up", "down"],
    *,
    markup_kind: str = "markdown",
    promote_key: str = "",
) -> tuple[str, int, MoveResult, str]:
    """Move the section containing ``caret`` one step in ``direction``.

    Returns ``(new_text, new_caret, result, announce_text)``.

    * ``new_text`` is the rewritten document.  When the move is rejected
      (no section, already at top/bottom, no sibling), ``new_text`` equals
      the input.
    * ``new_caret`` is the new caret position.  When the move is rejected
      it equals the input caret.
    * ``result`` is one of the :class:`MoveResult` codes.
    * ``announce_text`` is a screen-reader-friendly short string (already
      used by the QUILL-key wrapper).
    """
    if markup_kind in {"markdown", "html"}:
        blocks = parse_heading_blocks(text, markup_kind)
        if not blocks:
            return text, caret, MoveResult.NO_SECTION, announce_edge(MoveResult.NO_SECTION)
        found = section_for_caret(blocks, caret)
        if found is None:
            return text, caret, MoveResult.NO_SECTION, announce_edge(MoveResult.NO_SECTION)
        section_index, _level, section_start, _section_end = found
        # Subsections included, on both sides of the swap: moving "## A1" moves
        # the "### A1a" under it, and jumping over "## A2" jumps over all of
        # A2's children too.  See :func:`subtree_end`.
        section_end = subtree_end(blocks, section_index, len(text))
        sibling_index = find_sibling(blocks, section_index, direction)
        if sibling_index is not None:
            # A sibling: trade places with it, subtrees and all.  This is the
            # hierarchy-preserving move and the common case, and it is what
            # this command has always done.
            sibling = blocks[sibling_index]
            sibling_start = sibling.section_start
            sibling_end = subtree_end(blocks, sibling_index, len(text))
            jumped = sibling.title
        else:
            # No sibling that way, so move past whatever *is* there -- which is
            # what Word's Move Up / Move Down does on this same chord, and what
            # "move this section somewhere else" means to the person pressing
            # it.  Refusing here is what made a strictly nested outline
            # (# / ## / ###, where no heading has a sibling anywhere) answer
            # every press with a sentence and no movement.
            #
            # The moved section keeps its level: it does not renumber itself to
            # fit its new surroundings.  That keeps every move exactly
            # reversible, and keeps a key that says "move" from also editing.
            # Changing level is what Alt+Shift+Left/Right is for, and the two
            # compose.
            neighbour = outer_neighbour(blocks, section_index, direction, len(text))
            if neighbour is None:
                # Genuinely nothing that way.  The first section in a document
                # cannot rise; a section whose subtree runs to the end of the
                # file cannot sink, because everything below it is *inside* it.
                # Name the parent it is already first or last inside: "Bottom!"
                # is not true of a document that plainly continues above.
                edge = MoveResult.TOP if direction == "up" else MoveResult.BOTTOM
                parent = parent_title(blocks, section_index)
                contained = (
                    contains_the_rest(blocks, section_index, len(text))
                    if edge is MoveResult.BOTTOM
                    else ""
                )
                return (
                    text,
                    caret,
                    edge,
                    announce_edge(
                        edge,
                        parent_title=parent,
                        contained=contained,
                        promote_key=promote_key,
                    ),
                )
            sibling_start, sibling_end, jumped = neighbour
        # ``heading_line`` is the unique span we use to locate the moved
        # heading in the new text.  For Markdown it is the full heading line
        # up to the next newline; for HTML (no newlines) it is the
        # whole `<h...>...</h...>` span.
        newline_at = text.find("\n", section_start)
        if newline_at == -1:
            heading_line = text[blocks[section_index].start : blocks[section_index].end]
        else:
            heading_line = text[section_start:newline_at]
        if direction == "up":
            new_text = swap_sections(
                text,
                (sibling_start, sibling_end),
                (section_start, section_end),
            )
            new_caret = caret_after_move(
                caret,
                section_start,
                new_text,
                heading_line,
            )
            return (
                new_text,
                new_caret,
                MoveResult.OK,
                describe_move(new_text, new_caret, markup_kind, "above", jumped),
            )
        # direction == "down"
        new_text = swap_sections(
            text,
            (section_start, section_end),
            (sibling_start, sibling_end),
        )
        new_caret = caret_after_move(
            caret,
            section_start,
            new_text,
            heading_line,
        )
        return (
            new_text,
            new_caret,
            MoveResult.OK,
            describe_move(new_text, new_caret, markup_kind, "below", jumped),
        )

    # Plain-text form-feed fallback.
    if "\f" not in text:
        return text, caret, MoveResult.NO_SECTION, announce_edge(MoveResult.NO_SECTION)
    section = current_section_at(text, caret, markup_kind="plain")
    if section is None:
        return text, caret, MoveResult.NO_SECTION, announce_edge(MoveResult.NO_SECTION)
    boundaries: list[int] = [0]
    for index, ch in enumerate(text):
        if ch == "\f":
            boundaries.append(index + 1)
    if boundaries[-1] != len(text):
        boundaries.append(len(text))
    section_index = -1
    for index in range(len(boundaries) - 1):
        if boundaries[index] == section.start:
            section_index = index
            break
    if section_index < 0:
        return text, caret, MoveResult.NO_SECTION, announce_edge(MoveResult.NO_SECTION)
    if direction == "up" and section_index == 0:
        return text, caret, MoveResult.TOP, announce_edge(MoveResult.TOP)
    if direction == "down" and section_index == len(boundaries) - 2:
        return text, caret, MoveResult.BOTTOM, announce_edge(MoveResult.BOTTOM)
    if direction == "up":
        target = section_index - 1
    else:
        target = section_index + 1
    target_start = boundaries[target]
    target_end = boundaries[target + 1]
    if direction == "up":
        new_text = swap_sections(text, (target_start, target_end), (section.start, section.end))
    else:
        new_text = swap_sections(text, (section.start, section.end), (target_start, target_end))
    # For plain text, "heading line" doesn't apply; preserve the caret
    # offset within the moved section by looking for the first character
    # of the moved section in the new text.
    moved_prefix = text[section.start : min(section.start + 1, section.end)]
    if moved_prefix:
        moved_pos = new_text.find(moved_prefix)
        if moved_pos != -1:
            column = caret - section.start
            new_caret = moved_pos + column
        else:
            new_caret = caret
    else:
        new_caret = caret
    return new_text, new_caret, MoveResult.OK, ""
