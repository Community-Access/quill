"""Foldable-region detection (wx-free domain logic).

Code folding here is deliberately spoken-state, not visual line-hiding: the
document text is never mutated by folding, and fold state only changes what
structural *jump* commands (Quick Nav, Next/Previous Fold, the Fold List
dialog) announce and traverse. Raw character/line/word navigation is never
affected, so a screen reader user arrowing through a folded region reads it
exactly as if it weren't folded -- nothing reachable is ever made silently
unreachable. See x.md's "PRD: Code Folding" for the full accessibility
rationale.

Two kinds of foldable region are detected:

* Markdown/HTML headings -- reusing :func:`quill.core.outline.extract_outline_entries`,
  each heading's region runs to the next heading at the same-or-higher level
  (or end of document).
* Fenced code blocks (``` ``` ```) -- each complete fence is one atomic
  region, ``level=0``. Right-sized for a writing app with embedded code
  blocks, not an IDE needing per-function AST folding.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from quill.core.outline import extract_outline_entries

_FENCE_PATTERN = re.compile(r"^(```|~~~)([^\n]*)\n(.*?)^\1[ \t]*$", re.MULTILINE | re.DOTALL)


@dataclass(frozen=True, slots=True)
class FoldableRegion:
    """A structural span that can be folded: heading section or code fence."""

    start: int
    end: int
    label: str
    level: int  # heading level (1-6), or 0 for a fenced code block


def extract_foldable_regions(text: str, markup_kind: str) -> list[FoldableRegion]:
    """Return every foldable region in *text*, ordered by start position.

    Heading regions and fenced-code-block regions are both detected and
    merged into a single position-ordered list; overlapping regions are
    possible (a fence inside a heading's section) and both remain valid,
    independently foldable, entries -- the smallest region containing the
    cursor is picked at fold-toggle time, not here.
    """
    regions: list[FoldableRegion] = []
    regions.extend(_heading_regions(text, markup_kind))
    regions.extend(_fence_regions(text))
    regions.sort(key=lambda region: (region.start, -region.end))
    return regions


def _heading_regions(text: str, markup_kind: str) -> list[FoldableRegion]:
    entries = extract_outline_entries(text, markup_kind)
    if not entries:
        return []
    regions: list[FoldableRegion] = []
    for index, entry in enumerate(entries):
        end = len(text)
        for later in entries[index + 1 :]:
            if later.level <= entry.level:
                end = later.position
                break
        if end <= entry.position:
            continue
        regions.append(
            FoldableRegion(start=entry.position, end=end, label=entry.title, level=entry.level)
        )
    return regions


def _fence_regions(text: str) -> list[FoldableRegion]:
    regions: list[FoldableRegion] = []
    for match in _FENCE_PATTERN.finditer(text):
        info_string = match.group(2).strip()
        label = f"code block ({info_string})" if info_string else "code block"
        regions.append(FoldableRegion(start=match.start(), end=match.end(), label=label, level=0))
    return regions


def region_line_count(text: str, region: FoldableRegion) -> int:
    """Number of lines spanned by *region* within *text* (for announcements).

    A trailing newline ends the last line rather than starting an empty one,
    matching how a person would count lines when reading the block.
    """
    span = text[region.start : region.end]
    if not span:
        return 0
    return span.count("\n") + (0 if span.endswith("\n") else 1)


def smallest_region_containing(
    regions: list[FoldableRegion], position: int
) -> FoldableRegion | None:
    """The tightest-bound region containing *position*, or None.

    "Tightest" ties resolve to the one with the smallest span, so toggling
    fold on a code fence nested inside a heading section folds the fence
    alone, not the whole section.
    """
    containing = [r for r in regions if r.start <= position < r.end]
    if not containing:
        return None
    return min(containing, key=lambda r: r.end - r.start)


def next_region_boundary(regions: list[FoldableRegion], position: int) -> FoldableRegion | None:
    """The next region whose start is strictly after *position*, or None."""
    candidates = [r for r in regions if r.start > position]
    if not candidates:
        return None
    return min(candidates, key=lambda r: r.start)


def previous_region_boundary(regions: list[FoldableRegion], position: int) -> FoldableRegion | None:
    """The previous region whose start is strictly before *position*, or None."""
    candidates = [r for r in regions if r.start < position]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.start)
