"""Sections: select one, move one a step, or move one to a heading you choose.

Split out of :mod:`quill.apps.lite_window_format` (GATE-11). The Format menu is
about *runs of text* -- bold, a size, an alignment; this is about **the outline**,
which is a different idea with different rules. Formatting needs rich text and
says so when it cannot run; these need Markdown or HTML, because a rich-text
heading is a font size rather than markup and there is nothing for a section move
to parse.

Three keys, and the third is the one that actually scales:

* ``Alt+Shift+Up`` / ``Alt+Shift+Down`` -- one step. Right for tidying two
  adjacent sections; useless across a long document, where forty presses is forty
  announcements you have to count because there is no page to glance at.
* ``Alt+Shift+F5`` -- **Select Section**, the clipboard route. Ordinary Ctrl+X and
  Ctrl+V then put a section anywhere, including another document or another
  program, with no new idea to learn.
* ``Ctrl+Alt+Shift+F5`` -- **Move Section To**, a destination instead of a
  direction. Two questions from filtered lists, one edit, one undo step.

Every rule, refusal, renumbering and spoken sentence lives in
:mod:`quill.core.markdown_sections`, :mod:`quill.core.section_speech` and
:mod:`quill.core.section_move_to`, shared with QUILL. This module supplies
QuillLite's text control and its chooser and nothing else, which is what stops one
capability becoming two that drift.
"""

from __future__ import annotations

from quill.core.lite.keymap import spoken_key_for
from quill.core.markdown_sections import (
    MoveResult,
    describe_section_selection,
    move_section,
    section_selection_at,
)
from quill.core.section_move_to import MoveToStatus, run_move_section_to
from quill.ui.atomic_edit import replace_as_one_undo
from quill.ui.richedit_editing import RICH

__all__ = ["DocumentSectionCommandsMixin"]


class DocumentSectionCommandsMixin:
    """Select Section, Move Section Up/Down, and Move Section To.

    Mixed into :class:`~quill.apps.lite_window.DocumentFrame` beside the Format
    commands, which supply ``control``, ``editor``, ``markup_surface()``,
    ``_announce``, ``_set_modified``, ``_touch_status()``,
    ``sync_structure_announcer()`` and ``_no_formatting_here()``.
    """

    def cmd_select_section(self) -> None:
        """Alt+Shift+F5: select this section, subsections and all.

        The move keys reorder a section against its neighbours; this hands it
        to the clipboard, which is how it reaches anywhere else -- another part
        of the document, another document, another program. No new idea to
        learn: Control X and Control V do the rest.

        It exists because doing it by hand is the operation this whole family
        was written for. Selecting from a heading to exactly the start of the
        next one means finding an invisible boundary by trial, and overshooting
        it takes the next heading with you without saying so.
        """
        if self.editor.mode == RICH:
            # Not _no_formatting_here(): that sentence sends people TO rich text,
            # which is where this command does not work. A section here is a
            # Markdown or HTML heading plus its body; a rich-text heading is a
            # point size, and there is nothing for the parser to find.
            self._announce(
                "Selecting a section needs a Markdown or HTML document: a rich-text "
                "heading is a font size rather than markup."
            )
            return
        surface = self.markup_surface()
        if not surface:
            self._announce(self._no_formatting_here())
            return
        selection = section_selection_at(
            self.control.GetValue(), self.control.GetInsertionPoint(), markup_kind=surface
        )
        if selection is None:
            self._announce("Put the cursor in a section to select it")
            return
        self.control.SetSelection(selection.start, selection.end)
        self.control.ShowPosition(selection.start)
        # The reader says a selection changed, not how much is in it -- and
        # "did that take the sub-headings too?" is the whole question here.
        self._announce(describe_section_selection(selection))

    def _move_section(self, direction: str) -> None:
        """Move the whole section the cursor is in, heading and body together.

        QUILL's own :func:`~quill.core.markdown_sections.move_section`, over
        Markdown, and therefore plain text only: rich-text headings are a font
        size rather than markup, and moving formatted runs through the Text
        Object Model is a different piece of work that QUILL has not done
        either. Saying so is better than a key that quietly does nothing in
        half the documents somebody opens.

        This is the operation cut-and-paste is worst at. Reorganising by hand
        means selecting from a heading to the start of the next one -- a
        boundary you cannot see and have to find by ear -- and the usual result
        of getting it wrong is losing your place in the document you were
        halfway through reorganising.
        """
        if self.editor.mode == RICH:
            self._announce(
                "Moving a section needs a Markdown or HTML document: a rich-text "
                "heading is a font size rather than markup."
            )
            return
        text = self.control.GetValue()
        caret = self.control.GetInsertionPoint()
        # The document's own markup, not an assumed "markdown". An HTML document
        # has headings too, and move_section was looking for hashes it would
        # never find in one -- so Alt+Shift+Up in a .html said "not in a
        # section" about a section (bad.md R13).
        # No Markdown fallback here either: "No section to move" in a plain
        # text document is a sentence about sections that document cannot have.
        surface = self.markup_surface()
        if not surface:
            self._announce(self._no_formatting_here())
            return
        new_text, new_caret, result, announce = move_section(
            text,
            caret,
            direction,
            markup_kind=surface,
            # Read out of the keymap, not typed into the sentence: the chord is
            # rebindable, and a refusal that names a key which does something
            # else is the same defect as no refusal at all.
            promote_key=spoken_key_for(getattr(self.app, "keymap", None), "cmd_promote_heading"),
        )
        if result is not MoveResult.OK:
            self._announce(announce)
            return
        replace_as_one_undo(self.control, 0, self.control.GetLastPosition(), new_text)
        self.control.SetInsertionPoint(min(new_caret, self.control.GetLastPosition()))
        self.control.ShowPosition(self.control.GetInsertionPoint())
        self._set_modified(True)
        self._touch_status()
        # One sentence, composed in core: what it did, what it passed, and
        # where it now sits among its siblings. Composed there rather than here
        # so QUILL and QuillLite cannot describe the same move two ways.
        self._announce(announce)

    def cmd_move_section_up(self) -> None:
        self._move_section("up")

    def cmd_move_section_down(self) -> None:
        self._move_section("down")

    def cmd_move_section_to(self) -> None:
        """Ctrl+Alt+Shift+F5: move this section to a heading you choose.

        The move keys are one step each, which is right for swapping two
        adjacent sections and useless across a long document -- forty presses is
        forty announcements and you have to count them, because there is no page
        to glance at to see how far you have got. This asks where instead, in two
        questions: which heading, then before, after or inside it. One edit, one
        undo step.

        The rules, the refusals, the renumbering and the sentence all live in
        :func:`quill.core.section_move_to.run_move_section_to`. This supplies
        QuillLite's searchable chooser -- the same one Headings and Bookmarks
        use, so there is no new dialog to learn or to keep accessible -- and
        writes the answer back through the ordinary undo stack.
        """
        if self.editor.mode == RICH:
            self._announce(
                "Moving a section needs a Markdown or HTML document: a rich-text "
                "heading is a font size rather than markup."
            )
            return
        surface = self.markup_surface()
        if not surface:
            self._announce(self._no_formatting_here())
            return
        outcome = run_move_section_to(
            self.control.GetValue(),
            self.control.GetInsertionPoint(),
            markup_kind=surface,
            choose_heading=self._choose_move_destination,
            choose_placement=self._choose_move_placement,
        )
        if outcome.status is MoveToStatus.CANCELLED:
            # Nothing changed, so nothing is said: the reader announces the
            # caret arriving back in the document (GATE-13).
            return
        if not outcome.moved:
            self._announce(outcome.announce)
            return
        replace_as_one_undo(self.control, 0, self.control.GetLastPosition(), outcome.text)
        self.control.SetInsertionPoint(min(outcome.caret, self.control.GetLastPosition()))
        self.control.ShowPosition(self.control.GetInsertionPoint())
        self._set_modified(True)
        self._touch_status()
        self._announce(outcome.announce)
        self.sync_structure_announcer()

    def _choose_move_destination(self, targets: list) -> object | None:
        """Question one: which heading. The document's outline, filtered by typing.

        Rows are never re-ranked as you type. The list *is* the outline, in
        document order, and an outline that reshuffles itself is one you cannot
        navigate by position -- which is the whole reason each row leads with
        "3 of 7" rather than with the title.
        """
        from quill.apps.lite_dialogs import choose_searchable

        rows = [target.label for target in targets]
        chosen = choose_searchable(
            self,
            title="Move Section To",
            label="&Destination heading:",
            help_text=(
                "Every heading in this document, in the order they appear. Choose "
                "the one you want to move this section next to. The next question "
                "asks whether to put it before, after or inside it."
            ),
            choices=rows,
            search=lambda query: _matching_rows(rows, query),
            examples="for example: bread, or 3",
        )
        if chosen is None or chosen not in rows:
            return None
        return targets[rows.index(chosen)]

    def _choose_move_placement(self, choices: list[tuple[str, str]]) -> str | None:
        """Question two: before, after or inside. Three rows, asked out loud.

        Asked rather than guessed because "next to that heading" is genuinely
        ambiguous, and because one of the three answers changes the moved
        section's level. A command that renumbered your headings on a guess
        would have edited more than it said.
        """
        from quill.apps.lite_dialogs import choose_searchable

        rows = [label for _value, label in choices]
        chosen = choose_searchable(
            self,
            title="Where, Relative to That Heading?",
            label="&Placement:",
            help_text=(
                "Before puts this section just above that heading. After puts it "
                "below that heading and everything under it. Inside makes it the "
                "last section under that heading, which changes its level."
            ),
            choices=rows,
            search=lambda query: _matching_rows(rows, query),
        )
        if chosen is None or chosen not in rows:
            return None
        return choices[rows.index(chosen)][0]


def _matching_rows(rows: list[str], query: str) -> list[str]:
    """The rows containing every word of *query*, in their original order.

    Word-wise rather than substring: the rows lead with a position ("3 of 7,
    level 2 - Bread"), and somebody who types "bread 2" means both halves of
    what they typed. The order is the document's own, never re-ranked.
    """
    words = query.lower().split()
    if not words:
        return list(rows)
    return [row for row in rows if all(word in row.lower() for word in words)]
