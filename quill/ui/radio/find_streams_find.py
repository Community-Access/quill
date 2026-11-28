"""Find in Streams Found: the Find prompt, Find Next and Find Previous.

Extracted from ``link_finder_dialog.py`` under GATE-11 (extract, never rebaseline)
as a mixin: it reads and writes the dialog's own state (``_candidates``,
``_rows``, ``_list``, ``_find_term``) and nothing else, so it moves whole.
"""

from __future__ import annotations

from quill.core.radio import find_streams_view as view
from quill.ui.radio import find_streams_actions as actions


class FindMixin:
    """The Find commands of the Find Streams window."""

    def _find(self) -> None:
        def land(term: str) -> str:
            if not term:
                return ""
            self._find_term = term
            # Select and focus the match before the prompt goes, so the row is
            # read once, when focus comes back to the list.
            return self._land(backwards=False)

        message = "Find a stream by its name, link, format or how it was found:"
        sentence = actions.prompt_text(
            self._wx,
            self.dialog,
            "Find in Streams Found",
            message,
            self._find_term,
            self._announce,
            land,
        )
        if sentence is None:
            return  # Cancel does nothing
        self._results.SetFocus()
        self._say_after(sentence)

    def _land(self, *, backwards: bool) -> str:
        result = view.find(
            self._candidates,
            self._rows,
            self._list.shown,
            self._find_term,
            self._list.focused_position(),
            backwards=backwards,
        )
        if result.position is not None:
            self._list.go_to(result.position)
            self._enable_row_buttons()
        return result.sentence

    def _find_again(self, *, backwards: bool) -> None:
        if not self._find_term:
            self._find()
            return
        sentence = self._land(backwards=backwards)
        if sentence:
            self._announce(sentence)
