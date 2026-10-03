"""The content pane: one control whose kind depends on the place (qc.md 4.4).

A ``wx.Simplebook`` with two pages -- the report list (episodes, podcasts,
playlists or notices, columns per kind) and the folder tree (the Podcasts
place). Each page is a panel holding a heading that names the place and its
count, created *before* the page's control: on wxMSW a control's accessible
name is the static text constructed immediately before it among its
siblings, so the heading is what a listener arriving by Tab hears the list or
the tree called ("Inbox (6)"). Showing a place is a page change, never a
second copy of the library and never a dialog.

Tab across a Simplebook needs help: a page at the end of its own controls
hands Tab upward naming *itself* as the focus, the book has no navigation
handling of its own, and the main panel then starts again from the book --
so Tab stayed on the page (Radio found this on 2026-09-27; its
``main_view_host`` has the same fix, copied here rather than imported
because Radio's host is built around Radio's views).
"""

from __future__ import annotations

from typing import Any

__all__ = ["ContentPane"]


class ContentPane:
    """The book, its two pages and their headings, and which page is up."""

    LIST = "list"
    TREE = "tree"

    def __init__(self, parent: Any, *, wx: Any) -> None:
        self._wx = wx
        self.book = wx.Simplebook(parent)
        self.list_page = wx.Panel(self.book, style=wx.TAB_TRAVERSAL)
        #: Made by the list's builder, immediately before the list (attach).
        self._list_heading: Any = None
        self.tree_page = wx.Panel(self.book, style=wx.TAB_TRAVERSAL)
        self._tree_heading = wx.StaticText(self.tree_page, label="Podcasts")
        self._list: Any = None
        self._tree: Any = None
        self._showing = self.LIST
        self.book.Bind(wx.EVT_NAVIGATION_KEY, self._on_navigation_key)

    def attach(self, list_ctrl: Any, tree: Any, *, list_heading: Any) -> None:
        """Lay out the two controls, each under its own heading."""
        wx = self._wx
        self._list_heading = list_heading
        for page, heading, control in (
            (self.list_page, self._list_heading, list_ctrl),
            (self.tree_page, self._tree_heading, tree),
        ):
            sizer = wx.BoxSizer(wx.VERTICAL)
            sizer.Add(heading, 0, wx.LEFT | wx.RIGHT | wx.TOP, 4)
            sizer.Add(control, 1, wx.EXPAND | wx.ALL, 4)
            page.SetSizer(sizer)
        self._list = list_ctrl
        self._tree = tree
        self.book.AddPage(self.list_page, "List")
        self.book.AddPage(self.tree_page, "Tree")

    # -- which page ------------------------------------------------------------ #

    @property
    def heading(self) -> Any:
        """The heading of the page that is up."""
        return self._tree_heading if self._showing == self.TREE else self._list_heading

    @property
    def showing(self) -> str:
        return self._showing

    @property
    def control(self) -> Any:
        return self._tree if self._showing == self.TREE else self._list

    def show(self, page: str) -> None:
        if page == self._showing:
            return
        self._showing = page
        self.book.ChangeSelection(1 if page == self.TREE else 0)

    def set_heading(self, text: str) -> None:
        heading = self.heading
        if heading.GetLabel() != text:
            heading.SetLabel(text)

    def focus(self) -> None:
        try:
            self.control.SetFocus()
        except Exception:  # noqa: BLE001 - mid-teardown
            pass

    # -- Tab across the book ------------------------------------------------------ #

    def _on_navigation_key(self, event: Any) -> None:
        book = self.book
        parent = book.GetParent()
        page = book.GetCurrentPage()
        if parent is not None and self._is_within(event.GetCurrentFocus(), page):
            event.SetCurrentFocus(book)
            event.SetEventObject(book)
            parent.HandleWindowEvent(event)
            return
        if page is None:
            return
        control = self.control
        (control if control is not None else page).SetFocus()

    @staticmethod
    def _is_within(window: Any, ancestor: Any) -> bool:
        while window is not None and ancestor is not None:
            if window is ancestor:
                return True
            window = window.GetParent()
        return False
