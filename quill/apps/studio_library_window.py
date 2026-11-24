from __future__ import annotations

from collections.abc import Callable

import wx

from quill.ui.accessible_names import set_accessible_name
from quill.ui.dpi import dip_size


def enter_without_book(tree: wx.TreeCtrl | None) -> str:
    """What Enter says on a row that is not a book (a group row is not "no book")."""
    from quill.core.audio_studio.library_row_help import enter_on
    from quill.ui.audio_studio.library_tree import selected_key

    key = selected_key(tree) if tree is not None else None
    return enter_on(str(key[0]) if key else "")


def describe_selected_row(tree: wx.TreeCtrl) -> str:
    """F1's paragraph about the selected row (FUX-10): a group row, or a book that moved."""
    from pathlib import Path

    from quill.core.audio_studio.library_row_help import row_situation
    from quill.ui.audio_studio.library_tree import selected_key

    key = selected_key(tree)
    if key is None:
        return ""
    kind, value = key
    if kind != "book":
        return row_situation(str(kind))
    title = tree.GetItemText(tree.GetSelection())
    return row_situation("book", title=title, exists=Path(str(value)).exists())


def ensure_library_window(
    *,
    parent: wx.Window,
    title: str,
    existing: wx.Frame | None,
    reload_tree: Callable[[wx.TreeCtrl], None],
    on_activate,
    on_context_menu,
    on_key,
    on_destroy: Callable[[], None],
) -> tuple[wx.Frame, wx.TreeCtrl]:
    """Ensure the Studio's Library Window exists and is focused.

    Returns the (frame, tree) pair.
    """

    if existing is not None and existing.IsShown():
        try:
            existing.Raise()
            existing.SetFocus()
        except Exception:  # noqa: BLE001 - best-effort focus
            pass
        tree = existing.FindWindowByName("Your books")
        if isinstance(tree, wx.TreeCtrl):
            return existing, tree

    frame = wx.Frame(parent, title=title)
    panel = wx.Panel(frame, style=wx.TAB_TRAVERSAL)
    root = wx.BoxSizer(wx.VERTICAL)

    library_label = wx.StaticText(panel, label="&Your books:")
    root.Add(library_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 8)

    tree = wx.TreeCtrl(panel, style=wx.TR_DEFAULT_STYLE | wx.TR_HIDE_ROOT, name="Your books")
    set_accessible_name(
        tree,
        "Your books, grouped by Favorites, In Progress, Recently Played, and Inbox; "
        "Enter opens the selected book in the Chapter Workbench, Delete removes it, "
        "Application key opens the folder menu",
    )
    root.Add(tree, 1, wx.EXPAND | wx.ALL, 8)
    from quill.ui import app_context_help

    app_context_help.set_selection_help(tree, lambda: describe_selected_row(tree))

    panel.SetSizer(root)
    frame.SetSize(dip_size(frame, 720, 520))

    reload_tree(tree)

    tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, on_activate)
    tree.Bind(wx.EVT_TREE_ITEM_MENU, on_context_menu)
    tree.Bind(wx.EVT_KEY_DOWN, on_key)

    def destroyed(event: wx.WindowDestroyEvent) -> None:
        if event.GetEventObject() is frame:
            on_destroy()
        event.Skip()

    frame.Bind(wx.EVT_WINDOW_DESTROY, destroyed)
    frame.Show()
    try:
        tree.SetFocus()
    except Exception:  # noqa: BLE001 - best-effort focus
        pass

    return frame, tree
