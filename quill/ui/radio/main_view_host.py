"""Showing any of Quill Radio's surfaces *inside* the main window.

The policy -- which views exist and which one is stored -- is pure and lives in
:mod:`quill.core.radio.main_view`. This is the wx half: it owns the swappable
region between the now-playing line and the volume row, builds a surface into
it the first time that view is asked for, and puts focus where that surface
expects it.

**Built once, kept.** Switching back to a view you have already visited shows
the page you left, with its tree still expanded and its search still typed.
Rebuilding would be simpler and would throw away the state somebody spent time
on, which is the same reason the browse tree remembers its position.

**A hosted surface is not a second window.** It has no frame, no menu bar of
its own, no Close button and no entry in the window list -- the main window
already has all four, and that is the whole point of showing Browse *there*
rather than on top of it. Opening the same surface from its menu item while it
is the main view therefore focuses this one instead of building a duplicate;
see ``RadioAppFrame.open_browse_stations`` and its siblings.

The surfaces themselves grew one keyword argument each (``embed_in``) and a
``focus_default_control``; everything else about them is unchanged, which is
why Browse behaves identically whether it is a window or the main view.
"""

from __future__ import annotations

from typing import Any

from quill.core.radio import main_view


class MainViewHost:
    """The main window's swappable middle, and the surfaces living in it."""

    def __init__(self, app: Any, wx: Any) -> None:
        self._app = app
        self._wx = wx
        #: view id -> the page panel built for it.
        self._pages: dict[str, Any] = {}
        #: view id -> the surface object, so a second Ctrl+B can focus it.
        self._surfaces: dict[str, Any] = {}
        self._current = main_view.FAVORITES
        self.book: Any = None

    # -- building ---------------------------------------------------------------

    def build(self, parent: Any, favorites_page: Any) -> Any:
        """Create the book with the favorites page already in it.

        The favorites page is passed in rather than built here because it is
        not a surface object at all -- it is the label and tree the main frame
        has always owned, with thirty-odd references to it across the app.
        Moving it would have been the biggest and least useful part of this
        change.
        """
        wx = self._wx
        self.book = wx.Simplebook(parent)
        self.book.AddPage(favorites_page, main_view.label(main_view.FAVORITES))
        self._pages[main_view.FAVORITES] = favorites_page
        return self.book

    # -- switching --------------------------------------------------------------

    @property
    def current(self) -> str:
        """Which view the main window is showing."""
        return self._current

    def surface(self, view_id: str) -> Any:
        """The built surface for *view_id*, or ``None`` if it is not built."""
        return self._surfaces.get(main_view.normalize(view_id))

    def show(self, view_id: str, *, announce: bool = True, focus: bool = True) -> str:
        """Show *view_id*, building it if this is its first visit.

        Returns the view actually shown. A surface that cannot be built leaves
        the main window on whatever it was showing and says so -- an empty main
        window is the one state a listener cannot get out of by keyboard.
        """
        wanted = main_view.normalize(view_id)
        if self.book is None:
            return self._current
        if wanted not in self._pages:
            try:
                self._build_page(wanted)
            except Exception as error:  # noqa: BLE001 - never leave the window empty
                self._app._announce(
                    f"{main_view.label(wanted)} could not be shown in the main "
                    f"window. {error}. Showing {main_view.label(self._current)}."
                )
                return self._current
        page = self._pages[wanted]
        self.book.ChangeSelection(self.book.FindPage(page))
        self._current = wanted
        if announce:
            self._app._announce(main_view.announcement(wanted))
        if focus:
            self._wx.CallAfter(self.focus_current)
        return wanted

    def focus_current(self) -> None:
        """Land keyboard focus on the current view's own default control."""
        surface = self._surfaces.get(self._current)
        focus = getattr(surface, "focus_default_control", None)
        if callable(focus):
            focus()
            return
        # Favorites: the frame has owned that tree since the first version.
        tree = getattr(self._app, "_favorites_tree", None)
        if tree is not None:
            try:
                tree.SetFocus()
            except Exception:  # noqa: BLE001 - focus is best-effort
                pass

    # -- the surfaces -----------------------------------------------------------
    #
    # Built by the app's *own* openers with ``embed_in`` set, not by a second
    # copy of their argument lists here. Those lists are fifteen keywords long
    # and carry real decisions -- which download queue, which catalog, which
    # visible sources -- so a copy would be wrong within a release, and wrong
    # in the way that is hardest to see: Browse-as-a-window and
    # Browse-as-the-main-view would quietly differ.

    #: view id -> the app method that builds that surface, and the keyword it
    #: takes. Every one is the same command its menu item runs.
    BUILDERS: dict[str, str] = {
        "browse": "open_browse_stations",
        "search": "open_internet_radio",
        "recordings": "open_radio_recordings",
        "player": "_radio_go_to_player",
    }

    def _build_page(self, view_id: str) -> None:
        wx = self._wx
        page = wx.Panel(self.book, style=wx.TAB_TRAVERSAL)
        opener = getattr(self._app, self.BUILDERS[view_id], None)
        if not callable(opener):
            page.Destroy()
            raise RuntimeError(f"this build has no {main_view.label(view_id)}")
        surface = opener(embed_in=page)
        if surface is None:
            page.Destroy()
            raise RuntimeError(f"{main_view.label(view_id)} is not available here")
        self.book.AddPage(page, main_view.label(view_id))
        self._pages[view_id] = page
        self._surfaces[view_id] = surface


__all__ = ["MainViewHost"]
