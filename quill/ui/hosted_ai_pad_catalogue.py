"""The AI pad's list of actions: the built-in rows, then the service's extras.

The built-in rows are :data:`quill.core.ai.writing_tools.ACTIONS`. After them
come any tools the hosted service's catalogue describes that this build does not
have built in (:mod:`quill.core.ai.gateway_catalogue`), so a new text tool on
the server reaches QUILL and QUILL Lite as one more row in the same list --
reached by the same key, read by the same F1 (each row's own help sentence) and
sent by the same Send, with no release of either editor.

**Only on the free service.** A catalogue tool's instructions live on QUILL's
server; with the person's own key or ChatGPT plan nothing goes there, so there
is nothing to run it with and the rows are not offered.

**Rows arrive late, and quietly.** The catalogue comes with the limits, which
are fetched in the background the first time the pad opens. Rows it brings are
appended to the end of the list -- never inserted, so the row somebody is on
does not move under them -- and nothing is announced: they are there the next
time somebody arrows to the end, and a sentence about housekeeping while
somebody is reading the preview is exactly what GATE-13 forbids.

Split from :mod:`quill.ui.hosted_ai_pad` under GATE-11: that module is at its
cap, and which rows exist is a different question from what Send does.
"""

from __future__ import annotations

from typing import Any

from quill.core.ai.gateway_catalogue import (
    INPUT_DOCUMENT,
    INPUT_PROMPT,
    INPUT_SELECTION,
    CatalogueFeature,
    extra_features,
)
from quill.core.ai.writing_tools import ACTIONS, CONVERSATION

__all__ = ["PadRowsMixin"]

#: What each built-in row works on, in the catalogue's words. Everything not
#: named here is a passage (``selection``).
_BUILT_IN_INPUTS: dict[str, str] = {
    "document_qna": INPUT_DOCUMENT,
    "ask": INPUT_PROMPT,
    CONVERSATION: "conversation",
}

#: The kinds that take typing rather than a passage.
_TYPED_INPUTS = frozenset({INPUT_PROMPT, INPUT_DOCUMENT, "conversation"})


class PadRowsMixin:
    """The rows of :class:`~quill.ui.hosted_ai_pad.AiPadFrame`'s action list."""

    #: Both set by the pad, which also defines ``_direct()``.
    _actions: Any
    _service: Any

    def _init_rows(self) -> list[str]:
        """Build the rows from the built-in table and whatever is cached.

        Returns the labels, for the list box. A catalogue already fetched this
        session is in the first list; one still on its way is added by
        :meth:`add_catalogue_rows` when it lands.
        """
        self._rows: list[tuple[str, str, str]] = list(ACTIONS)
        self._extras: dict[str, CatalogueFeature] = {}
        self._merge_catalogue(getattr(self._service, "limits", None))
        return [label for _id, label, _help in self._rows]

    def _merge_catalogue(self, limits: Any) -> list[str]:
        """Add the catalogue entries not yet in the list; return their labels."""
        if limits is None or self._direct():
            return []
        added: list[str] = []
        for entry in extra_features(
            tuple(getattr(limits, "features", ()) or ()),
            {row[0] for row in self._rows},
            {row[1] for row in self._rows},
        ):
            self._extras[entry.id] = entry
            self._rows.append((entry.id, entry.label, entry.help))
            added.append(entry.label)
        return added

    def add_catalogue_rows(self, limits: Any) -> None:
        """The limits arrived: append any new tools they describe.

        Called on the UI thread by the service once the background fetch is
        done, when the pad may already have been closed -- a destroyed window
        is falsy, and is left alone.
        """
        try:
            if not self:
                return
            for label in self._merge_catalogue(limits):
                self._actions.Append(label)
        except RuntimeError:  # the list went with its window
            return

    # -- the row somebody is on ------------------------------------------- #

    def _row(self) -> tuple[str, str, str]:
        index = self._actions.GetSelection()
        return self._rows[index if 0 <= index < len(self._rows) else 0]

    @property
    def _action_id(self) -> str:
        return self._row()[0]

    def _input_kind(self) -> str:
        """What the current row works on: a passage, typing, or both."""
        extra = self._extras.get(self._action_id)
        if extra is not None:
            return extra.input
        return _BUILT_IN_INPUTS.get(self._action_id, INPUT_SELECTION)

    def _asking(self) -> bool:
        return self._input_kind() in _TYPED_INPUTS

    def _row_index(self, action: str) -> int:
        return next((i for i, row in enumerate(self._rows) if row[0] == action), 0)

    def _input_limit(self) -> int:
        """The input ceiling for the current row, in tokens.

        The service's global one, or a catalogue entry's own when it is
        smaller. Never larger: the server re-checks whatever the client
        believes, and promising more than the global ceiling would only move
        the refusal from the summary to the Send button.
        """
        limit = int(self._service.limits.max_input_tokens)
        extra = self._extras.get(self._action_id)
        if extra is not None and extra.max_input_tokens:
            return min(limit, extra.max_input_tokens)
        return limit
