"""Section-move primitives for Markdown and plain-text documents.

This module is the single source of truth for heading parsing, section
boundaries, and the heading regex (#359 / consolidation of the former
``quill.core.heading_organizer`` and ``quill.core.heading_styles``).

Public API:

* :class:`Section` — frozen dataclass describing a heading section.
* :class:`HeadingBlock` — frozen dataclass describing a parsed heading
  (used by the Heading Organizer dialog and the section-move UI).
* :class:`HeadingContext` — frozen dataclass with the level, ordinal, and
  total count for the heading at a caret offset.
* :class:`MoveResult` — ``OK | NO_SECTION | TOP | BOTTOM | NO_SIBLING``.
* :func:`current_section_at` — find the section containing the caret.
* :func:`move_section` — apply a one-step move and return the new text, new
  caret, the result code, and a screen-reader-friendly announce string.
* :func:`parse_heading_blocks` — fence-aware markdown / html heading parser.
* :func:`apply_heading_organizer_edits` — rewrite a document after the
  Heading Organizer dialog has reordered or renamed its sections.
* :func:`heading_context_at` — describe the heading containing a caret.
* :func:`validate_heading_sequence` — check a list of parsed headings for
  common structural problems.

The Markdown path is fence-aware so ``# not a heading`` lines inside a
````` or ``~~~`` block are never matched.  For plain text (no Markdown),
the section-move code falls back to form-feed (``\\f``) delimited blocks,
which the main editor produces when text is pasted from certain sources.
"""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Literal

# ---------------------------------------------------------------------------
# Heading patterns and parser (consolidated from heading_organizer.py).
# ---------------------------------------------------------------------------

_MD_HEADING_PATTERN = re.compile(r"^(?P<marker>#{1,6})[ \t]*(?P<title>.*)$", re.MULTILINE)
_HTML_HEADING_PATTERN = re.compile(
    r"<h(?P<level>[1-6])(?P<attrs>[^>]*)>(?P<body>.*?)</h(?P=level)>",
    re.IGNORECASE | re.DOTALL,
)
_HTML_TAG_PATTERN = re.compile(r"<[^>]+>")
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
                heading_match = _MD_HEADING_PATTERN.match(line)
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
    matches = list(_HTML_HEADING_PATTERN.finditer(text))
    blocks: list[HeadingBlock] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = match.end()
        section_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        raw_title = _HTML_TAG_PATTERN.sub("", match.group("body"))
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
        return _MD_HEADING_PATTERN.sub(
            f"{'#' * normalized_level} {normalized_title}",
            section,
            count=1,
        )
    if markup_kind == "html":
        replacement = (
            f"<h{normalized_level}{original.attributes}>{normalized_title}</h{normalized_level}>"
        )
        return _HTML_HEADING_PATTERN.sub(replacement, section, count=1)
    return section


# ---------------------------------------------------------------------------
# Section-move primitives (the original content of this module).
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Section:
    level: int
    title: str
    start: int
    end: int

    @property
    def length(self) -> int:
        return self.end - self.start


class MoveResult(StrEnum):
    OK = "ok"
    NO_SECTION = "no_section"
    TOP = "top"
    BOTTOM = "bottom"
    NO_SIBLING = "no_sibling"


def _section_for_caret(blocks: list, caret: int) -> tuple[int, int, int, int] | None:
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
        found = _section_for_caret(blocks, caret)
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


def _find_sibling(blocks: list, section_index: int, direction: Literal["up", "down"]) -> int | None:
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


def _swap_sections(text: str, first: tuple[int, int], second: tuple[int, int]) -> str:
    """Swap two ``(start, end)`` ranges in ``text``.

    Ranges must be non-overlapping and ordered such that ``first`` precedes
    ``second``.  The whitespace gap between the two ranges is attached to
    whichever section ends up on top so the moved heading keeps its
    surrounding blank lines.
    """
    a_start, a_end = first
    b_start, b_end = second
    if a_end > b_start:
        raise ValueError("ranges must be ordered and non-overlapping")
    a_text = text[a_start:a_end]
    b_text = text[b_start:b_end]
    gap = text[a_end:b_start]
    # The gap (whitespace between the sections) rides with whichever
    # section now comes first.  For "up" we want the moved-up heading to
    # keep the gap above it; for "down" we want it below.
    if a_text.endswith("\n") and not b_text.endswith("\n"):
        b_text = b_text.rstrip("\n") + "\n"
    if not b_text.endswith("\n") and gap.endswith("\n"):
        # CommonMark headings should end with a newline.
        b_text = b_text + "\n"
    return text[:a_start] + b_text + gap + a_text + text[b_end:]


def _caret_after_move(
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


def _announce(result: MoveResult, sibling_title: str = "") -> str:
    if result == MoveResult.TOP:
        return "Top!"
    if result == MoveResult.BOTTOM:
        return "Bottom!"
    if result == MoveResult.NO_SECTION:
        return "No section to move"
    if result == MoveResult.NO_SIBLING:
        return "No sibling to swap with"
    if sibling_title:
        return sibling_title
    return ""


def move_section(
    text: str,
    caret: int,
    direction: Literal["up", "down"],
    *,
    markup_kind: str = "markdown",
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
            return text, caret, MoveResult.NO_SECTION, _announce(MoveResult.NO_SECTION)
        found = _section_for_caret(blocks, caret)
        if found is None:
            return text, caret, MoveResult.NO_SECTION, _announce(MoveResult.NO_SECTION)
        section_index, _level, section_start, section_end = found
        sibling_index = _find_sibling(blocks, section_index, direction)
        if direction == "up" and section_index == 0:
            return text, caret, MoveResult.TOP, _announce(MoveResult.TOP)
        if direction == "down" and section_index == len(blocks) - 1:
            return text, caret, MoveResult.BOTTOM, _announce(MoveResult.BOTTOM)
        if sibling_index is None:
            return text, caret, MoveResult.NO_SIBLING, _announce(MoveResult.NO_SIBLING)
        sibling = blocks[sibling_index]
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
            new_text = _swap_sections(
                text,
                (sibling.section_start, sibling.section_end),
                (section_start, section_end),
            )
            new_caret = _caret_after_move(
                caret,
                section_start,
                new_text,
                heading_line,
            )
            return new_text, new_caret, MoveResult.OK, sibling.title.strip()
        # direction == "down"
        new_text = _swap_sections(
            text,
            (section_start, section_end),
            (sibling.section_start, sibling.section_end),
        )
        new_caret = _caret_after_move(
            caret,
            section_start,
            new_text,
            heading_line,
        )
        return new_text, new_caret, MoveResult.OK, sibling.title.strip()

    # Plain-text form-feed fallback.
    if "\f" not in text:
        return text, caret, MoveResult.NO_SECTION, _announce(MoveResult.NO_SECTION)
    section = current_section_at(text, caret, markup_kind="plain")
    if section is None:
        return text, caret, MoveResult.NO_SECTION, _announce(MoveResult.NO_SECTION)
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
        return text, caret, MoveResult.NO_SECTION, _announce(MoveResult.NO_SECTION)
    if direction == "up" and section_index == 0:
        return text, caret, MoveResult.TOP, _announce(MoveResult.TOP)
    if direction == "down" and section_index == len(boundaries) - 2:
        return text, caret, MoveResult.BOTTOM, _announce(MoveResult.BOTTOM)
    if direction == "up":
        target = section_index - 1
    else:
        target = section_index + 1
    target_start = boundaries[target]
    target_end = boundaries[target + 1]
    if direction == "up":
        new_text = _swap_sections(text, (target_start, target_end), (section.start, section.end))
    else:
        new_text = _swap_sections(text, (section.start, section.end), (target_start, target_end))
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


# --- Numbered-list auto-fill gate ------------------------------------------
#
# The EdSharp port toggle for numbered lists (Ctrl+Alt+8) inserts a list
# with leading "1. ", "2. ", "3. " markers when (and only when) one of
# the three OR'd conditions below holds:
#
#   1. the active document surface is markdown (the default-experience
#      rule -- a user who explicitly authored a Markdown file wants
#      markers, and we honour that without an extra click),
#   2. settings.list_auto_fill_numbers is on (explicit opt-in),
#   3. the user just ran toggle_numbered_list on the active document
#      (per-document arming flag with a 5-minute lifetime; cleared on
#      document close).
#
# In every other case the inserted list uses today's no-fill behaviour:
# only the first item gets a marker and the rest are bare lines.
#
# We model this as a single helper that takes a frame-like object so it
# can be exercised from pure unit tests without spinning up a real
# MainFrame.

_LIST_AUTO_FILL_ARM_SECONDS = 300.0


def should_auto_fill_numbers(
    settings: object | None,
    surface: str,
    *,
    armed_until: float = 0.0,
    now: float | None = None,
) -> bool:
    """Return True if a numbered-list insertion should auto-fill markers.

    Parameters mirror the live conditions:

    * ``settings`` — a Settings-like object exposing
      ``list_auto_fill_numbers``; ``None`` disables the explicit opt-in.
    * ``surface`` — the active document surface (``"markdown"``,
      ``"html"``, ``"plain"``).
    * ``armed_until`` — the value of the per-document arming flag (a
      monotonic-clock timestamp); ``0.0`` means no arming.
    * ``now`` — the current monotonic-clock value (defaults to the real
      clock in production; pass a fixed value from tests).
    """
    if surface == "markdown":
        return True
    explicit = bool(getattr(settings, "list_auto_fill_numbers", False))
    if explicit:
        return True
    if armed_until > 0.0:
        current = time.monotonic() if now is None else now
        if current <= armed_until:
            return True
    return False


# --- Numbered-list marker helpers -----------------------------------------
#
# The toggle commands and the auto-fill gate produce Markdown like:
#
#     1. item one
#     2. item two
#     3. item three
#
# so we keep the rewrite pure: fill_numbered_markers scans the inserted
# list and rewrites the leading "1. " markers to "1. ", "2. ", "3. ", ...
# without touching body text.  strip_list_markers removes both bullet
# ("- ") and numbered ("1. ") markers so the toggle can collapse a list
# back to plain text.

_NUMBERED_MARKER_RE = re.compile(r"^(?P<indent>\s*)\d+\.\s")


def fill_numbered_markers(text: str) -> str:
    """Rewrite consecutive '1. ' markers to 1., 2., 3., ... .

    Only the first item of each consecutive numbered run is renumbered.
    Existing non-numbered lines (blank lines, indented sub-items) are
    preserved as-is.
    """
    out_lines: list[str] = []
    counter = 0
    for line in text.splitlines():
        match = _NUMBERED_MARKER_RE.match(line)
        if match is None:
            counter = 0
            out_lines.append(line)
            continue
        counter += 1
        out_lines.append(f"{match.group('indent')}{counter}. {line[match.end() :]}")
    return "\n".join(out_lines)


_BULLET_MARKER_RE = re.compile(r"^(?P<indent>\s*)[-*+]\s")


def strip_list_markers(text: str) -> str:
    """Remove leading '-' / '*' / '+' / 'N. ' markers from each line.

    Blank lines and lines without a recognised marker pass through
    unchanged so the caller's surrounding whitespace is preserved.
    """
    out_lines: list[str] = []
    for line in text.splitlines():
        bullet = _BULLET_MARKER_RE.match(line)
        if bullet is not None:
            out_lines.append(f"{bullet.group('indent')}{line[bullet.end() :]}")
            continue
        numbered = _NUMBERED_MARKER_RE.match(line)
        if numbered is not None:
            out_lines.append(f"{numbered.group('indent')}{line[numbered.end() :]}")
            continue
        out_lines.append(line)
    return "\n".join(out_lines)


def is_caret_inside_list(text: str, caret: int, *, markup_kind: str = "markdown") -> bool:
    """Return True if ``caret`` is on or inside a recognised list item.

    Used by the toggle commands to decide whether to insert or strip.
    """
    if markup_kind != "markdown":
        return False
    line_start = text.rfind("\n", 0, caret) + 1
    line_end = text.find("\n", caret)
    if line_end == -1:
        line_end = len(text)
    line = text[line_start:line_end]
    return _BULLET_MARKER_RE.match(line) is not None or _NUMBERED_MARKER_RE.match(line) is not None
