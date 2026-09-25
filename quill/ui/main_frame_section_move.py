"""Section-level editor commands for ``MainFrame``.

Extracted from ``main_frame.py`` to keep that module within the size budget
(GATE-11) and to keep the section-move code path cohesive.

A "section" is a Markdown heading (or HTML heading) plus the body lines
between it and the next heading of equal or higher level.  The chord
``Alt+Shift+Up`` / ``Alt+Shift+Down`` moves the current section past its
sibling -- subsections and all -- and announces the result, or, where it has
no sibling that way, says which parent it is already first or last inside.
Plain-text documents are explicitly rejected at the surface gate so a user who
pastes a Markdown heading into a plain-text file does not get a silent no-op.

Three commands live here. ``Alt+Shift+Up``/``Down`` move one step;
``Alt+Shift+F5`` selects the section so the clipboard can take it anywhere; and
``Ctrl+Alt+Shift+F5`` (**Move Section To**) asks for a destination instead of a
direction, which is the only one of the three that is any use across a long
document.

Pure logic lives in :mod:`quill.core.markdown_sections` and
:mod:`quill.core.section_move_to`; this mixin is a thin shell that wires the
editor text and caret into the pure helpers, supplies QUILL's own picker where
one is needed, and forwards the result to the existing announcement pipeline.
"""

from __future__ import annotations

from quill.core.markdown_sections import (
    MoveResult,
    describe_section_selection,
    move_section,
    section_selection_at,
)
from quill.core.section_move_to import MoveToStatus, run_move_section_to


class SectionMoveMixin:
    def move_section_up(self) -> None:
        self._move_section("up")

    def move_section_down(self) -> None:
        self._move_section("down")

    def select_section(self) -> None:
        """Select this section, subsections and all, and say how much that is.

        The move keys reorder a section against its neighbours; this hands it
        to the clipboard, which is how it reaches anywhere else. Same command,
        same wording and the same core helper as QUILL Lite's, because one
        capability described two ways is two capabilities to keep in step.
        """
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Select Section is only available in Markdown or HTML documents")
            return
        try:
            text = self.editor.GetValue()
            caret = self.editor.GetInsertionPoint()
        except RuntimeError:  # dead C++ widget, as in _move_section below
            return
        selection = section_selection_at(text, caret, markup_kind=surface)
        if selection is None:
            self._announce("Put the cursor in a section to select it")
            return
        try:
            self.editor.SetSelection(selection.start, selection.end)
            self.editor.SetFocus()
        except RuntimeError:
            return
        self._announce(describe_section_selection(selection))

    def move_section_to(self) -> None:
        """Move this section to a chosen heading, rather than one step at a time.

        Alt+Shift+Up forty times is not a way to cross a long document: forty
        presses is forty announcements and you have to count them, because there
        is no page to glance at. This asks where instead -- which heading, then
        before, after or inside it -- and does the whole thing as one undoable
        edit.

        The rules, the refusals and the sentence all live in
        :func:`quill.core.section_move_to.run_move_section_to`; this supplies
        QUILL's searchable picker for the two questions and writes the result
        back. QUILL Lite supplies its own picker to the same function, which is
        what keeps one capability from becoming two.
        """
        surface = self._active_markup_surface()
        if surface is None:
            self._set_status("Move Section To is only available in Markdown or HTML documents")
            return
        try:
            text = self.editor.GetValue()
            caret = self.editor.GetInsertionPoint()
        except RuntimeError:  # dead C++ widget, as in _move_section below
            return

        def choose_heading(targets):  # noqa: ANN001,ANN202 - list[MoveTarget]
            rows = [target.label for target in targets]
            chosen = self._choose_searchable_option(
                title="Move Section To",
                prompt="Type part of a heading",
                dialog_label="Destination heading",
                initial_choices=rows,
                search_callback=lambda query: _matching(rows, query),
            )
            if chosen is None or chosen not in rows:
                return None
            return targets[rows.index(chosen)]

        def choose_placement(choices):  # noqa: ANN001,ANN202 - list[tuple[str, str]]
            rows = [label for _value, label in choices]
            chosen = self._choose_searchable_option(
                title="Where, Relative to That Heading?",
                prompt="Type before, after or inside",
                dialog_label="Placement",
                initial_choices=rows,
                search_callback=lambda query: _matching(rows, query),
            )
            if chosen is None or chosen not in rows:
                return None
            return choices[rows.index(chosen)][0]

        outcome = run_move_section_to(
            text,
            caret,
            markup_kind=surface,
            choose_heading=choose_heading,
            choose_placement=choose_placement,
        )
        if outcome.status is MoveToStatus.CANCELLED:
            # Nothing changed, so nothing is said: the reader announces the
            # caret arriving back in the document (GATE-13).
            return
        if not outcome.moved:
            self._announce(outcome.announce)
            return
        try:
            self.editor.SetValue(outcome.text)
            self.editor.SetInsertionPoint(outcome.caret)
            self.editor.SetFocus()
        except RuntimeError:
            return
        self._announce(outcome.announce)

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
            text,
            caret,
            direction,
            markup_kind=surface,
            # The refusal that names a key reads it out of the keymap, because
            # the chord is rebindable and advice naming a key that does
            # something else is worse than no advice.
            promote_key=self._binding_for("format.decrease_heading_level") or "",
        )
        if result is MoveResult.OK:
            try:
                self.editor.SetValue(new_text)
                self.editor.SetInsertionPoint(new_caret)
                self.editor.SetFocus()
            except RuntimeError:
                return
            self._announce(announce)
            return
        # Edge / no-section cases speak the string the pure helper already
        # composed, rather than a second copy of the same sentences here.
        # The wording is outcome-specific -- "Bottom of Heading 1" names the
        # parent the section is already last inside -- and a re-derivation
        # from the enum alone cannot say that, which is how QUILL ended up
        # announcing less than QUILL Lite did for the same key.
        if announce:
            self._announce(announce)
        else:  # pragma: no cover - defensive: unannounced enum member
            self._announce("Section move could not be performed")


def _matching(rows: list[str], query: str) -> list[str]:
    """The rows that contain every word of *query*, in document order.

    Word-wise rather than substring, because the rows lead with a position
    ("3 of 7, level 2 - Bread") and somebody who types "bread 2" means both
    halves of what they typed. Order is never re-ranked: the list is the
    document's outline, and an outline that reorders itself as you type is one
    you cannot navigate by position.
    """
    words = query.lower().split()
    if not words:
        return list(rows)
    return [row for row in rows if all(word in row.lower() for word in words)]
