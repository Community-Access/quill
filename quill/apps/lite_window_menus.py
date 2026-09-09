"""QuillLite's menu bar, generated from the command table.

Not fifty ``Append`` calls. The bar is built by walking
:data:`quill.core.lite.commands.COMMANDS`, so the keys the menus advertise, the
keys that are bound, and the keys the Keyboard Shortcuts window lists are one
list read three times -- and the uniqueness rules can be asserted against the
table (``tests/unit/core/lite/test_lite_commands.py``) rather than against a
running window.

Two menus are rebuilt as the app changes rather than built once:

* **Open Recent**, which skips entries whose file has gone. Skipped rather than
  greyed out: choosing a missing entry could only ever produce a "does not
  exist" prompt, so offering it costs a keystroke and an announcement for
  nothing.
* **Window**, which lists every open document *by its own number*, with Alt+1
  to Alt+9 on the first nine and a check mark on the one you are in. With MDI
  this is not a convenience -- an MDI child does not appear in Alt+Tab at all,
  so this list and Ctrl+F6 are the only ways between documents, and they have to
  be complete.

Both are rebuilt in *every* window whenever the set changes
(:meth:`~quill.apps.lite.QuillLiteApp.refresh_all_menus`), because a window
listing a stale set of siblings is worse than one listing none.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import wx

from quill.apps.lite_shell import MAX_NUMBERED
from quill.core.lite.commands import split_menu, visible_commands

__all__ = ["DocumentMenuMixin"]


class DocumentMenuMixin:
    """The menu bar of a :class:`~quill.apps.lite_window.DocumentFrame`."""

    def _build_menus(self) -> None:
        """Build the bar from the command table, in table order.

        Only the areas that are switched on: an item removed from
        :func:`~quill.core.lite.commands.visible_commands` loses its menu row
        *and* its accelerator, because a key that still fires for a feature
        somebody has turned off is the feature not being off.
        """
        menu_bar = wx.MenuBar()
        menus: dict[str, wx.Menu] = {}
        #: Submenus, built alongside their parent and attached at the end. A
        #: wx.Menu must be fully populated before AppendSubMenu on wxMSW --
        #: attach it early and the items added afterwards do not appear.
        submenus: list[tuple[str, str, wx.Menu]] = []
        self._recent_menu = wx.Menu()
        self._check_items = {}
        self._window_menu_items = []
        for menu_label, label, key, handler, kind in visible_commands(self.app.feature_enabled):
            parent_label, child_label = split_menu(menu_label)
            menu = menus.get(menu_label)
            if menu is None:
                menu = wx.Menu()
                menus[menu_label] = menu
                if child_label:
                    # The parent may not exist yet if the submenu's rows come
                    # first; build it now so the bar order still follows the
                    # table rather than the order menus happened to be needed.
                    if parent_label not in menus:
                        menus[parent_label] = wx.Menu()
                        menu_bar.Append(menus[parent_label], parent_label)
                    submenus.append((parent_label, child_label, menu))
                else:
                    menu_bar.Append(menu, menu_label)
            if kind == "sep":
                menu.AppendSeparator()
                continue
            item_kind = wx.ITEM_CHECK if kind == "check" else wx.ITEM_NORMAL
            item = menu.Append(wx.ID_ANY, f"{label}	{key}", kind=item_kind)
            self.Bind(wx.EVT_MENU, self._dispatch(handler), item)
            if kind == "check":
                self._check_items[handler] = item
            if handler == "cmd_open":
                menu.AppendSubMenu(self._recent_menu, "Open Recen&t")
        # Now that every submenu is full, hang it off its parent.
        for parent_label, child_label, child_menu in submenus:
            menus[parent_label].AppendSubMenu(child_menu, child_label)
        self._window_menu = menus["&Window"]
        self._window_menu.AppendSeparator()
        self.SetMenuBar(menu_bar)
        self.refresh_recent_menu()
        self.refresh_window_menu()
        self._sync_check_items()

    def rebuild_menus(self) -> None:
        """Build the bar again, after the feature set changed.

        A whole new ``wx.MenuBar`` rather than an edit of the old one: working
        out which rows to add and remove is the same walk as building it, with
        an extra chance to leave a stale accelerator behind.
        """
        self._build_menus()

    def _dispatch(self, handler: str) -> Any:
        def run(_event: wx.CommandEvent) -> None:
            getattr(self, handler)()

        return run

    def _sync_check_items(self) -> None:
        """Make the checkable items agree with the state they mirror.

        Looked up rather than indexed: an item whose area is switched off is not
        on the bar at all, so Check While Typing is simply absent when spelling
        is off. A ``KeyError`` here would take the menu build down with it.
        """
        marks = {
            "cmd_toggle_dark": self.app.settings.theme == "dark",
            "cmd_toggle_wrap": self.app.settings.word_wrap,
            # Per document, not per app: the file-type rule means two windows
            # can honestly disagree about this, and the mark has to read the
            # answer for the document in front of you.
            "cmd_toggle_live_spelling": getattr(self, "_live_spelling", False),
            # F8 extend mode: on while there is an anchor to extend from.
            "cmd_toggle_extend_mode": getattr(self, "_selection_anchor", None) is not None,
        }
        for handler, checked in marks.items():
            item = self._check_items.get(handler)
            if item is not None:
                item.Check(bool(checked))

    def refresh_recent_menu(self) -> None:
        """Rebuild Open Recent, skipping files that are no longer there.

        Skipped rather than greyed: choosing a missing entry could only ever
        produce a "does not exist" prompt, so offering it wastes a keystroke and
        an announcement.
        """
        for item in list(self._recent_menu.GetMenuItems()):
            self._recent_menu.Delete(item)
        recent = [entry for entry in self.app.settings.recent_files if Path(entry).exists()]
        if not recent:
            placeholder = self._recent_menu.Append(wx.ID_ANY, "No recent files")
            placeholder.Enable(False)
            return
        for index, entry in enumerate(recent[:9], start=1):
            path = Path(entry)
            item = self._recent_menu.Append(
                wx.ID_ANY, f"&{index} {path.name}  ({path.parent})\tAlt+Shift+{index}"
            )
            self.Bind(wx.EVT_MENU, lambda _e, p=entry: self.app.open_path(Path(p)), item)

    def refresh_window_menu(self) -> None:
        """Rebuild the list of open documents, by number.

        The number is the document's own, not its position in the list, so
        "document 3" keeps meaning the same document after document 1 is closed.
        Alt+1 to Alt+9 land on the first nine numbers; past that the list still
        names every document and Ctrl+F6 still walks them all.
        """
        for item_id in self._window_menu_items:
            self._window_menu.Delete(item_id)
        self._window_menu_items = []
        for frame in self.app.frames:
            label = f"{frame.number}: {frame.document_name()}"
            if frame.number <= MAX_NUMBERED:
                label = f"&{frame.number} {frame.document_name()}	Alt+{frame.number}"
            item = self._window_menu.Append(wx.ID_ANY, label, kind=wx.ITEM_CHECK)
            item.Check(frame is self)
            self._window_menu_items.append(item.GetId())
            self.Bind(wx.EVT_MENU, lambda _e, f=frame: self.app.focus_frame(f), item)

    def _on_menu_open(self, event: wx.MenuEvent) -> None:
        self._sync_check_items()
        event.Skip()
