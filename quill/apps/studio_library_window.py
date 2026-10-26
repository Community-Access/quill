from __future__ import annotations

from collections.abc import Callable

import wx

from quill.core.a11y import set_accessible_name


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

    panel.SetSizer(root)
    frame.SetSize((720, 520))

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
