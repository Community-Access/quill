"""Section-level editor commands for ``MainFrame``.

Extracted from ``main_frame.py`` to keep that module within the size budget
(GATE-11) and to keep the section-move code path cohesive.

A "section" is a Markdown heading (or HTML heading) plus the body lines
between it and the next heading of equal or higher level.  The chord
``Alt+Shift+Up`` / ``Alt+Shift+Down`` moves the current section past its
sibling and announces the result.  Plain-text documents are explicitly
rejected at the surface gate so a user who pastes a Markdown heading into a
plain-text file does not get a silent no-op.

Pure logic lives in :mod:`quill.core.markdown_sections`; this mixin is a
thin shell that wires the editor text and caret into the pure helper and
forwards the result to the existing announcement pipeline.
"""

from __future__ import annotations

from quill.core.markdown_sections import (
    MoveResult,
    move_section,
)


class SectionMoveMixin:
    def move_section_up(self) -> None:
        self._move_section("up")

    def move_section_down(self) -> None:
        self._move_section("down")

    def _move_section(self, direction: str) -> None:
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Section move is only available in Markdown or HTML documents")
            return
        try:
            text = self.editor.GetValue()
            caret = self.editor.GetInsertionPoint()
        except RuntimeError:
            # Dead C++ widget (e.g. closed tab). Mirrors the #269 statusbar fix.
            return
        new_text, new_caret, result, announce = move_section(
            text, caret, direction, markup_kind=surface
        )
        if result is MoveResult.OK:
            try:
                self.editor.SetValue(new_text)
                self.editor.SetInsertionPoint(new_caret)
                self.editor.SetFocus()
            except RuntimeError:
                return
            label = f"moved above {announce}" if direction == "up" else f"moved below {announce}"
            self._announce(f"Section {label}")
            return
        # Edge / no-section cases are announced as-is. Each branch is
        # enumerated against the MoveResult enum so a future addition
        # would surface as an unannounced outcome (we'd see the
        # "section move did nothing" report in support and know to add
        # a new branch) rather than silently falling into the
        # NO_SIBLING arm by accident.
        if result is MoveResult.NO_SECTION:
            self._announce("No section to move")
        elif result is MoveResult.TOP:
            self._announce("Top!")
        elif result is MoveResult.BOTTOM:
            self._announce("Bottom!")
        elif result is MoveResult.NO_SIBLING:
            self._announce("No sibling to swap with")
        else:  # pragma: no cover - defensive: unannounced enum member
            self._announce("Section move could not be performed")
