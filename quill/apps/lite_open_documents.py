"""QUILL Lite's side of Find in Open Documents (ui/open_documents_find).

The same window QUILL opens; this says what QUILL Lite's open documents are --
one per window, in the order they were opened, with each window's live text --
and how to bring one to the front. The search state lives on the app rather
than on a window, so F3 in any window carries on the same search across all
of them.
"""

from __future__ import annotations

from typing import Any

from quill.core.open_documents_search import OpenDoc
from quill.ui.open_documents_find import OpenDocumentsState, replace_text_in

__all__ = ["LiteOpenDocuments", "state_for"]


def state_for(app: Any) -> OpenDocumentsState:
    """The app's one search state, made on first use."""
    state = getattr(app, "_open_documents_state", None)
    if state is None:
        state = OpenDocumentsState()
        app._open_documents_state = state
    return state


class LiteOpenDocuments:
    """The adapter: QUILL Lite's windows, as the shared window asks for them."""

    def __init__(self, window: Any) -> None:
        self._window = window
        self._app = window.app

    @property
    def parent(self) -> Any:
        return self._window

    @property
    def state(self) -> OpenDocumentsState:
        return state_for(self._app)

    def _frames(self) -> list[Any]:
        frames = list(getattr(self._app, "frames", []) or [])
        return frames or [self._window]

    def _front(self) -> Any:
        active = getattr(self._app, "active_frame", None)
        return active if active in self._frames() else self._window

    def documents(self) -> list[OpenDoc]:
        docs: list[OpenDoc] = []
        for frame in self._frames():
            control = frame.control
            editable = bool(getattr(control, "IsEditable", lambda: True)())
            docs.append(OpenDoc(frame.document_name(), control.GetValue(), editable))
        return docs

    def current(self) -> int:
        return self._frames().index(self._front())

    def selection(self) -> tuple[int, int]:
        start, end = self._front().control.GetSelection()
        return int(start), int(end)

    def go_to(self, index: int, start: int, end: int) -> None:
        frame = self._frames()[index]
        if frame is not self._front():
            self._app.focus_frame(frame)
        frame.control.SetSelection(start, end)
        frame.control.ShowPosition(start)

    def write(self, index: int, new_text: str, spans: list[tuple[int, int, str]]) -> None:
        from quill.ui.richedit_editing import RICH

        frame = self._frames()[index]
        replace_text_in(frame.control, new_text, spans, rich=frame.editor.mode == RICH)
        frame._set_modified(True)

    def announce(self, text: str) -> None:
        self._window._announce(text)

    def show_modal(self, dialog: Any, label: str) -> int:
        from quill.ui.dialog_contract import show_modal_dialog

        return int(show_modal_dialog(dialog, label))
