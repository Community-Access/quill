"""Heading levels in QUILL's markup surfaces: set one, or move one a step.

Two operations with two keys and one rule underneath. ``Ctrl+Alt+2`` means
"this is a Heading 2" whatever it was before; ``Alt+Shift+Right`` means "one
level deeper than it is". Both are :mod:`quill.core.heading_levels`, which is
shared with QUILL Lite so the two editors cannot answer the same question two
ways.

Extracted from ``main_frame.py`` on 2026-09-16 while fixing bad.md R3. Setting a
heading here **prepended** rather than rewrote, so applying Heading 2 to a line
that already read ``### Notes`` produced ``## ### Notes`` -- a Heading 2 whose
text begins with three hashes -- and a caret sitting mid-line produced
``foo ## bar``. A selection of five lines got one heading and four untouched
lines, with nothing said about the four.

Every one of those is invisible by ear, which is why it survived: the screen
reader says "Heading 2" in all four cases, and the damage is only discoverable
in the published document. QUILL Lite fixed exactly this by calling
``set_heading_level``, whose docstring names the bug; QUILL never adopted it.
"""

from __future__ import annotations

from quill.core.heading_levels import (
    LevelResult,
    adjust_heading_level,
    set_heading_level,
    set_heading_level_over_lines,
)

__all__ = ["HeadingLevelsMixin"]


class HeadingLevelsMixin:
    """Heading N, Body Text, and the two level-step commands."""

    def format_heading(self, level: int) -> None:
        """Make the caret's line -- or every selected line -- a heading.

        ``level=0`` is the way back to body text: the marker comes off and the
        words stay. A rich document takes the rich path instead, where the
        heading is a real paragraph style rather than characters.
        """
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        if self._rich_format_command("set_heading", f"Heading {level}", level):
            self.sync_structure_announcer()  # already announced; do not echo it
            return
        surface = self._active_markup_surface()
        if surface is None:
            choice = self._offer_plain_text_formatting_choice(f"Heading {level}")
            if choice == "rich":
                # Converted just now, so apply the heading in the document you
                # are now in rather than returning and leaving the command you
                # pressed undone (bad.md R11).
                if self._rich_format_command("set_heading", f"Heading {level}", level):
                    self.sync_structure_announcer()
                return
            if choice != "markdown":
                return
            surface = "markdown"
        text = self.editor.GetValue()
        start, end = self.editor.GetSelection()
        # One Replace over the whole block rather than one per line, so a
        # five-line heading is one press of Ctrl+Z to walk back, not five.
        if end > start:
            change = set_heading_level_over_lines(text, start, end, level, markup_kind=surface)
        else:
            change = set_heading_level(
                text, self.editor.GetInsertionPoint(), level, markup_kind=surface
            )
        if change.result is not LevelResult.OK:
            self._set_status("Already body text" if not level else "Heading tools need a line")
            return
        self.editor.Replace(change.start, change.end, change.replacement)
        # Replace leaves the caret at the end of what it wrote, which in HTML is
        # after ``</h1>`` -- outside the element you just asked for. change.caret
        # is where the words go instead.
        self.editor.SetInsertionPoint(change.caret)
        self.document.set_text(self.editor.GetValue())
        self._set_status(f"Heading {level}" if level else "Body text")
        # Already reported. Latch it so the caret hook does not say it again.
        self.sync_structure_announcer()

    def decrease_heading_level(self) -> None:
        self._adjust_heading_level(-1)

    def increase_heading_level(self) -> None:
        self._adjust_heading_level(1)

    def _adjust_heading_level(self, delta: int) -> None:
        if not self._feature_enabled("core.format"):
            self._set_status("Heading tools are unavailable in this profile")
            return
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Headings are only available in Markdown or HTML documents")
            return
        text = self.editor.GetValue()
        cursor = self.editor.GetInsertionPoint()
        # The rule itself is quill.core.heading_levels, shared with QUILL Lite,
        # which binds the same Alt+Shift+Left / Right pair. It used to be two
        # regexes and four branches inline here, which is the shape that gets
        # copied rather than called the second time somebody needs it.
        change = adjust_heading_level(text, cursor, delta, markup_kind=surface)
        if change.result is LevelResult.NOT_A_HEADING:
            self._set_status("Place cursor on a heading line to adjust its level")
            return
        if change.result in {LevelResult.AT_TOP, LevelResult.AT_BOTTOM}:
            direction = "minimum" if change.result is LevelResult.AT_TOP else "maximum"
            self._set_status(f"Heading already at {direction} level")
            return
        if not change.changed:
            self._set_status("Headings are only available in Markdown or HTML documents")
            return
        self.editor.SetSelection(change.start, change.end)
        self.editor.Replace(change.start, change.end, change.replacement)
        self.document.set_text(self.editor.GetValue())
        # The new level, not "adjusted": which way it went is the whole outcome,
        # and a listener cannot see the hashes change.
        self._set_status(f"Heading {change.new_level}")
        self.sync_structure_announcer()
