"""What the Workbench window does to the selection: copy, open, Properties, menus.

Split out of :mod:`quill.ui.workbench_frame` (GATE-11) so the frame keeps to
arranging panes and routing keys. Every method here runs on the UI thread and
reads the frame's own state (``self.rows``, ``self.current``, ``self.provider``).
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from quill.core.workbench.actions import ActionRow
from quill.ui.dialog_contract import show_modal_dialog

__all__ = ["WorkbenchActionsMixin"]


class WorkbenchActionsMixin:
    """Copying, the browser, Properties, the context menus and the address box."""

    _wx: Any
    provider: Any
    frame: Any
    tree: Any
    list: Any
    rows: list[object]
    current: Any
    _editor: Any

    def say_selection(self) -> None:
        self._say(f"{len(self.selected_indices())} of {len(self.rows)} selected")

    def copy_text(self, text: str) -> None:
        wx = self._wx
        if not text or not wx.TheClipboard.Open():
            self._say("Could not copy.")
            return
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
        self._say("Copied.")

    def copy_link(self) -> None:
        if self.current is not None:
            self.copy_text(self.provider.url(self.current, self.selected_row()))

    def open_in_browser(self) -> None:
        import webbrowser

        url = self.provider.url(self.current, self.selected_row()) if self.current else ""
        if not url or not webbrowser.open(url, new=2):
            self._say("Could not open this in your browser.")

    def show_properties(self) -> None:
        """Alt+Enter: the selected row's sheet (several rows, and nodes, come later)."""
        chosen = self.selected_indices()
        on_list = self._wx.Window.FindFocus() is self.list or bool(chosen)
        if not on_list or self.current is None:
            self._say("Properties of a tree node come in a later preview.")
            return
        if len(chosen) > 1:
            self._say("Properties of several rows at once come in a later preview.")
            return
        built = self.provider.properties(self.current, self.rows[chosen[0]]) if chosen else None
        if built is None:
            self._say("This row has no Properties sheet yet.")
            return
        from quill.ui.workbench_properties_dialog import WorkbenchPropertiesDialog

        sheet, values, title = built
        WorkbenchPropertiesDialog(
            self.frame, sheet, values, title=title, copy_text=self.copy_text
        ).show()

    def _popup(self, window: Any, top: Sequence[ActionRow], more: Sequence[ActionRow]) -> None:
        wx = self._wx
        menu = wx.Menu()

        def fill(target: Any, rows: Sequence[ActionRow]) -> None:
            for row in rows:
                item = target.Append(wx.ID_ANY, row.label, row.help)
                item.Enable(self.can_run(row.command_id))
                target.Bind(wx.EVT_MENU, lambda _e, c=row.command_id: self.run(c), item)

        fill(menu, top[:-1])
        if more:
            sub = wx.Menu()
            fill(sub, more)
            menu.AppendSubMenu(sub, "More")
        fill(menu, top[-1:])
        try:
            window.PopupMenu(menu)
        finally:
            menu.Destroy()

    def show_row_menu(self) -> None:
        row = self.selected_row()
        if row is None:
            self.show_node_menu()
            return
        self._popup(self.list, *self.row_actions(row))

    def show_node_menu(self) -> None:
        self._popup(self.tree, *self.provider.actions.menu_for("node"))

    def switch_to_editor(self) -> None:
        editor = self._editor
        if editor is None:
            return
        try:
            editor.Raise()
            editor.SetFocus()
        except RuntimeError:
            self._say("The editor that opened this window is closed.")

    def show_help(self) -> None:
        from quill.ui import app_context_help

        app_context_help.show_help(self.frame)

    def open_address(self) -> None:
        wx = self._wx
        with wx.TextEntryDialog(
            self.frame, "Repository (owner/name) or GitHub link:", "Open GitHub Address"
        ) as dialog:
            if show_modal_dialog(dialog, "Open GitHub Address") != wx.ID_OK:
                return
            text = dialog.GetValue()
        ref = self.provider.add_instance("repository", text)
        if ref is None:
            self._say("That is not a repository name or GitHub link.")
            return
        self.rebuild_tree()
        self.frame.SetTitle(self.provider.window_title(ref.instance))
        self.select(ref)
        self.tree.SetFocus()
