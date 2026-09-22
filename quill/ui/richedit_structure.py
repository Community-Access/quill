r"""Moving and re-levelling whole ranges of a rich document, through the TOM.

Split out of :mod:`quill.ui.richedit_editing` under GATE-11, and the line is a
real one: that module is the *surface* -- what a character run looks like, what
the caret is in, what the control will say about itself -- and these three are
edits to the document's **structure**, which arrived together when the Heading
Organizer learned to work in rich text.

They exist because reordering sections in a Markdown document is a string
operation and in a rich one it is not. A heading there *is* a point size and a
bold on a run, so moving lines as text would arrive unformatted and flatten the
document on the way. ``ITextRange.FormattedText`` is what makes the move keep
its formatting, and everything here is built on it.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.heading_ladder import BODY_POINT_SIZE, HEADING_POINT_SIZES
from quill.ui.richedit_rtf_surface import (
    _TOM_FALSE,
    _TOM_TRUE,
    _TOM_UNIT_PARAGRAPH,
    RichEditRtfError,
    _get_text_document,
    _one_undo_step,
)

#: ``tomStory`` from tom.h: the whole of the document, for finding its end.
_TOM_UNIT_STORY = 6

__all__ = ["RichEditStructureMixin"]


class RichEditStructureMixin:
    """Formatted-range moves, in-place text replacement, and heading levels."""

    def reorder_ranges(self, spans: Sequence[tuple[int, int]]) -> None:
        """Rewrite the document as *spans*, in that order, keeping all formatting.

        The Heading Organizer's rich-text half. Reordering sections in a markup
        document is a string operation -- cut the lines, paste them elsewhere --
        and in a rich document it is not: a heading there *is* a point size and a
        bold on a run, so moving lines as text would arrive unformatted and take
        every heading with it. That is why the organizer refused in rich text,
        and "it should work there" is the correct objection: those documents have
        headings, :meth:`all_headings` already lists them, and the only thing
        missing was a way to move a *formatted* range.

        ``ITextRange.FormattedText`` is that way. Assigning one range's formatted
        text to another is the control copying its own rich content, so every
        size, weight, colour and paragraph property travels with it -- verified
        on the live control rather than assumed
        (``tests/unit/ui/test_rich_heading_organizer.py``).

        The order of operations is what makes it safe. Every span is appended to
        the **end** of the story first, and the original text is deleted only
        once they are all there, so no offset moves under a span that has not
        been copied yet. Doing it in place would mean each insertion shifting the
        spans after it, which is the shape of bug that silently drops a
        paragraph.

        One undo step, because the user did one thing.
        """
        wanted = [(int(start), int(end)) for start, end in spans if int(end) > int(start)]
        if not wanted:
            return
        try:
            document = _get_text_document(self.hwnd())
            original_end = self._story_end(document)
            cursor = original_end
            with _one_undo_step(self.hwnd()):
                for start, end in wanted:
                    tail = document.Range(cursor, cursor)
                    tail.FormattedText = document.Range(start, end).FormattedText
                    cursor = self._story_end(document)
                document.Range(0, original_end).Text = ""
        except RichEditRtfError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not reorder the document: {exc}") from exc

    def _story_end(self, document: Any) -> int:
        """The offset just past the last character of the story."""
        probe = document.Range(0, 0)
        probe.EndOf(_TOM_UNIT_STORY, 0)
        return int(probe.End)

    def set_range_text(self, start: int, end: int, text: str) -> None:
        """Replace ``[start, end)`` with *text*, keeping the range's formatting.

        Used for a heading renamed in the organizer. The characters change and
        the run's size and weight do not, which is what makes a rename a rename
        rather than a heading quietly becoming body text.
        """
        try:
            document = _get_text_document(self.hwnd())
            with _one_undo_step(self.hwnd()):
                document.Range(int(start), int(end)).Text = str(text)
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not replace the text: {exc}") from exc

    def set_heading_at(self, position: int, level: int) -> None:
        """Set the heading level of the paragraph containing *position*.

        :meth:`set_heading` works on the selection, which the organizer has no
        business moving: the caret belongs to the person, and putting it back
        afterwards is one more thing to get wrong.
        """
        try:
            document = _get_text_document(self.hwnd())
            span = document.Range(int(position), int(position))
            span.Expand(_TOM_UNIT_PARAGRAPH)
            with _one_undo_step(self.hwnd()):
                font = span.Font
                if int(level) <= 0:
                    font.Size = BODY_POINT_SIZE
                    font.Bold = _TOM_FALSE
                else:
                    font.Size = HEADING_POINT_SIZES[int(level)]
                    font.Bold = _TOM_TRUE
        except Exception as exc:  # noqa: BLE001
            raise RichEditRtfError(f"Could not set heading {level}: {exc}") from exc
