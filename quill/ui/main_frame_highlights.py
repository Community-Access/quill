"""QUILL's half of Highlighted Passages: registration and the Navigate submenu.

The commands are shared with QUILL Lite (:mod:`quill.ui.highlight_commands`);
this registers them under QUILL's ids and puts them on **Navigate >
Highlighted Passages**, beside Bookmarks, because going to a passage is a move
through the document like going to a bookmark. Default keys, the same in both
editors and all remappable in the Keymap Editor:

- ``navigate.next_highlight`` (Alt+Page Down) and
  ``navigate.previous_highlight`` (Alt+Page Up): move to the next or previous
  passage and say its colour, its place in the count and its words. Both wrap.
- ``navigate.list_highlights`` (Ctrl+F2): every passage in one list.

The submenu title has no access letter: Navigate's letters are spoken for, and
a duplicate would advertise a key that may not work (GATE-14). Its three rows
each show their chord.
"""

from __future__ import annotations

from typing import Any

from quill.ui.highlight_commands import HighlightCommandsMixin
from quill.ui.main_frame_editor_host import QuillEditorHostMixin

__all__ = ["HighlightPassagesMixin"]

#: Command id, menu label, command-palette name, handler name -- in menu order.
_HIGHLIGHT_ROWS: tuple[tuple[str, str, str, str], ...] = (
    (
        "navigate.next_highlight",
        "&Next Highlighted Passage",
        "Next Highlighted Passage",
        "cmd_next_highlight",
    ),
    (
        "navigate.previous_highlight",
        "&Previous Highlighted Passage",
        "Previous Highlighted Passage",
        "cmd_previous_highlight",
    ),
    (
        "navigate.list_highlights",
        "&List Highlighted Passages...",
        "List Highlighted Passages",
        "cmd_list_highlights",
    ),
)


class HighlightPassagesMixin(QuillEditorHostMixin, HighlightCommandsMixin):
    """Registration and menu rows. No commands of its own."""

    def register_highlight_commands(self) -> None:
        for command_id, _label, name, handler_name in _HIGHLIGHT_ROWS:
            self.commands.try_register(  # type: ignore[attr-defined]
                command_id,
                name,
                getattr(self, handler_name),
                self._binding_for(command_id),  # type: ignore[attr-defined]
            )

    def _highlight_passage_menu_ids(self) -> dict[str, Any]:
        ids = getattr(self, "_highlight_passage_ids", None)
        if ids is None:
            import wx

            ids = {command_id: wx.NewIdRef() for command_id, _l, _n, _h in _HIGHLIGHT_ROWS}
            self._highlight_passage_ids = ids
        return ids

    def _append_highlight_submenu(self, navigate_menu: Any) -> None:
        """Navigate > Highlighted Passages, its three rows bound once."""
        import wx

        from quill.core.i18n import _

        ids = self._highlight_passage_menu_ids()
        submenu = wx.Menu()
        for command_id, label, _name, _handler in _HIGHLIGHT_ROWS:
            submenu.Append(ids[command_id], self._menu_label(_(label), command_id))  # type: ignore[attr-defined]
        navigate_menu.AppendSubMenu(submenu, _("Highlighted Passages"))
        if not getattr(self, "_highlight_passage_rows_wired", False):
            self._highlight_passage_rows_wired = True
            for command_id, _label, _name, handler_name in _HIGHLIGHT_ROWS:
                handler = getattr(self, handler_name)
                self.frame.Bind(  # type: ignore[attr-defined]
                    wx.EVT_MENU, lambda _e, run=handler: run(), id=ids[command_id]
                )

    def _command_to_menu_id_map(self) -> dict[str, int]:
        mapping: dict[str, int] = super()._command_to_menu_id_map()  # type: ignore[misc]
        mapping.update(self._highlight_passage_menu_ids())
        return mapping
