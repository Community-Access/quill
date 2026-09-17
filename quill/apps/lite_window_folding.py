"""Folding over Markdown sections: how a listener skims a long document.

Collapsing to headings is the thing a sighted reader gets for free by scrolling
and glancing, and the only way anybody without that glance can answer "what is
in this file" without reading all of it. QuillLite already parses heading blocks
for its outline, so the structure was there and nothing was using it for this
(bad.md 4.2 Tier 3, P3.6).

**The fold is a navigation aid, not a change to the document.** Nothing is
hidden from the caret, nothing is removed from the buffer, and arrowing through
a folded region reads it exactly as it reads unfolded -- which is deliberate and
is the same decision QUILL made. A fold that actually hid text would be a
document whose contents depend on a view state, and the first thing it would
break is Find.

What the fold state *is*, then, is a remembered answer to "have I dealt with
this section", surfaced when you jump between regions: ``Ctrl+Shift+Left`` and
``Ctrl+Shift+Right`` walk the boundaries and say the heading, its state and how
many lines are under it. That is the skim.

The engine is :mod:`quill.core.code_folding`, wx-free and already shared with
QUILL, so neither editor can drift on what counts as a region.
"""

from __future__ import annotations

from quill.core.code_folding import (
    FoldableRegion,
    extract_foldable_regions,
    next_region_boundary,
    previous_region_boundary,
    region_line_count,
    smallest_region_containing,
)

__all__ = ["DocumentFoldingMixin"]


class DocumentFoldingMixin:
    """Fold, unfold, and walk the foldable regions of a Markdown document."""

    def _init_folding(self) -> None:
        #: ``(start, end)`` of every region folded in this window. Per window
        #: and gone when it closes: it is a reading aid for this afternoon, not
        #: a property of the file, and one written to disk would be a view state
        #: somebody else opening the document would inherit without asking.
        self._folded_regions: set[tuple[int, int]] = set()

    def _foldable_regions(self) -> list[FoldableRegion]:
        surface = self.markup_surface()
        if surface is None:
            return []
        return extract_foldable_regions(self.doc_text.text, surface)

    def cmd_toggle_fold(self) -> None:
        """Ctrl+Shift+Minus: fold or unfold the section the caret is in.

        The *smallest* region containing the caret, so inside a sub-section it
        folds that rather than the whole chapter -- which is what somebody means
        when they are standing in one.
        """
        regions = self._foldable_regions()
        if not regions:
            self._announce("Nothing to fold in this document")
            return
        region = smallest_region_containing(regions, int(self.control.GetInsertionPoint()))
        if region is None:
            self._announce("No foldable section at the cursor")
            return
        key = (region.start, region.end)
        lines = region_line_count(self.doc_text.text, region)
        if key in self._folded_regions:
            self._folded_regions.discard(key)
            self._announce(f'Unfolded: "{region.label}"')
            return
        self._folded_regions.add(key)
        self._announce(f'Folded: {lines} lines under "{region.label}"')

    def cmd_next_fold(self) -> None:
        """Ctrl+Shift+Right: jump to the next section, and say what it is."""
        self._walk_folds(forward=True)

    def cmd_previous_fold(self) -> None:
        """Ctrl+Shift+Left: jump to the previous section, and say what it is."""
        self._walk_folds(forward=False)

    def _walk_folds(self, *, forward: bool) -> None:
        regions = self._foldable_regions()
        if not regions:
            self._announce("No foldable sections in this document")
            return
        caret = int(self.control.GetInsertionPoint())
        finder = next_region_boundary if forward else previous_region_boundary
        region = finder(regions, caret)
        if region is None:
            self._announce("No more sections ahead" if forward else "No more sections behind")
            return
        # Through ``_go_to`` so Alt+Left undoes it, like every other jump in the
        # app (bad.md L8).
        self._go_to(region.start)
        state = "folded" if (region.start, region.end) in self._folded_regions else "expanded"
        lines = region_line_count(self.doc_text.text, region)
        self._announce(f'"{region.label}", {state}, {lines} lines')

    def cmd_unfold_all(self) -> None:
        """Ctrl+Shift+Equals: expand everything, and say how much that was."""
        count = len(self._folded_regions)
        if not count:
            self._announce("Nothing is folded")
            return
        self._folded_regions.clear()
        self._announce(f"Unfolded {count} section{'s' if count != 1 else ''}")
