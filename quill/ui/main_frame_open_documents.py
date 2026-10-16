"""QUILL's side of Find in Open Documents (ui/open_documents_find).

The shared window does the searching; this says what QUILL's open documents
are -- one per tab, with the tab's live text, unsaved or untitled -- and how to
reach one. It also makes F3 and Shift+F3 carry on across documents after a
search there, and hands them back to ordinary Find the moment Ctrl+F or Ctrl+H
starts one. Mixed in ahead of the search commands so those overrides win.
"""

from __future__ import annotations

from typing import Any

from quill.core.open_documents_search import OpenDoc
from quill.ui.open_documents_find import (
    OpenDocumentsState,
    find_again,
    open_find_in_open_documents,
    replace_text_in,
)

__all__ = ["OpenDocumentsFindMixin", "QuillOpenDocuments"]

_RICH_MODES = ("rich", "rich_converted")


class QuillOpenDocuments:
    """The adapter: QUILL's tabs, as the shared window asks for them."""

    def __init__(self, frame: Any) -> None:
        self._frame = frame

    @property
    def parent(self) -> Any:
        return self._frame.frame

    @property
    def state(self) -> OpenDocumentsState:
        return _state(self._frame)

    def _tabs(self) -> list[Any]:
        return list(getattr(self._frame, "_document_tabs", []) or [])

    def documents(self) -> list[OpenDoc]:
        docs: list[OpenDoc] = []
        for tab in self._tabs():
            editor = tab.editor
            editable = bool(getattr(editor, "IsEditable", lambda: True)())
            editable = editable and not getattr(tab, "read_only_remote", False)
            name = getattr(tab.document, "name", "") or "Untitled"
            docs.append(OpenDoc(name, editor.GetValue(), editable))
        return docs

    def current(self) -> int:
        return int(getattr(self._frame, "_active_tab_index", 0) or 0)

    def selection(self) -> tuple[int, int]:
        start, end = self._frame.editor.GetSelection()
        return int(start), int(end)

    def go_to(self, index: int, start: int, end: int) -> None:
        if index != self.current():
            self._frame._select_tab(index)
        editor = self._frame.editor
        editor.SetSelection(start, end)
        editor.ShowPosition(start)

    def write(self, index: int, new_text: str, spans: list[tuple[int, int, str]]) -> None:
        tab = self._tabs()[index]
        rich = getattr(tab, "editor_mode", "") in _RICH_MODES
        replace_text_in(tab.editor, new_text, spans, rich=rich)
        # A tab in the background gets no text event QUILL listens to
        # (main_frame_typing), so its document is told it changed here.
        tab.document.set_text(tab.editor.GetValue())
        refresh = getattr(self._frame, "_refresh_title", None)
        if callable(refresh):
            refresh()

    def announce(self, text: str) -> None:
        self._frame._announce(text)

    def show_modal(self, dialog: Any, label: str) -> int:
        return int(self._frame._show_modal_dialog(dialog, label))


def _state(frame: Any) -> OpenDocumentsState:
    state = getattr(frame, "_open_documents_state", None)
    if state is None:
        state = OpenDocumentsState()
        frame._open_documents_state = state
    return state


COMMAND_ID = "edit.find_in_open_documents"


class OpenDocumentsFindMixin:
    """Edit > Find in Open Documents..., and F3 that remembers it."""

    def _register_open_documents_command(self) -> None:
        """Called from the command table, beside Find All Matches."""
        self.commands.register(  # type: ignore[attr-defined]
            COMMAND_ID,
            "Find in Open Documents",
            self.find_in_open_documents,
            self._binding_for(COMMAND_ID),  # type: ignore[attr-defined]
        )

    def _append_open_documents_item(self, menu: Any) -> None:
        """Called from the Edit menu, after Find All Matches. I, because the
        Edit menu has spent every other letter in the name."""
        import wx

        from quill.core.i18n import _

        self._id_find_in_open_documents = wx.NewIdRef()
        menu.Append(
            self._id_find_in_open_documents,
            self._menu_label(_("F&ind in Open Documents..."), COMMAND_ID),  # type: ignore[attr-defined]
        )
        self.frame.Bind(  # type: ignore[attr-defined]
            wx.EVT_MENU,
            lambda _event: self.find_in_open_documents(),
            id=self._id_find_in_open_documents,
        )

    def find_in_open_documents(self) -> None:
        """Ctrl+Shift+F10: find and replace across every open tab."""
        open_find_in_open_documents(QuillOpenDocuments(self))

    def find_next(self) -> None:
        if not find_again(QuillOpenDocuments(self)):
            super().find_next()  # type: ignore[misc]

    def find_previous(self) -> None:
        if not find_again(QuillOpenDocuments(self), backwards=True):
            super().find_previous()  # type: ignore[misc]

    def find_text(self) -> None:
        _state(self).end()  # an ordinary Find: F3 is that Find's again
        super().find_text()  # type: ignore[misc]

    def replace_text(self) -> None:
        _state(self).end()
        super().replace_text()  # type: ignore[misc]
