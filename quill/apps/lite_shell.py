"""The MDI shell: one QuillLite window holding numbered documents.

QuillLite opens documents as **numbered children inside one parent window**
rather than as separate top-level windows. The parent is
:class:`QuillLiteShell`; the documents are ``wx.MDIChildFrame``s built by
:mod:`quill.apps.lite_window`.

### Why this shape, and what it costs

Numbering is the point. "Document 3" is a name a person can hold, say out loud,
and go back to; "the other Untitled" is not. With one parent window the number
is stable, the Window menu is a real list, and Alt+1 to Alt+9 always mean the
same nine things.

The cost is honest and worth writing down: **MDI children do not appear in
Alt+Tab.** On Windows, Alt+Tab lists top-level windows, and an MDI child is not
one. So the whole burden of moving between documents falls on the app, and the
app has to carry it properly:

* **Ctrl+F6** (the Windows MDI convention) and **Ctrl+Tab** (what people
  actually press) both move to the next document, with Shift for the previous.
  A key somebody expects and does not get is indistinguishable from a broken
  app, so both are bound rather than one.
* **Alt+1 to Alt+9** jump straight to a numbered document from anywhere.
* The **Window menu** lists every document by number, with a check mark on the
  one you are in.
* Every document's **title carries its number** ("3: notes.txt"), so the number
  is in the one string the screen reader announces on arrival.

### Multiple instances

One process holds one shell; a second launch hands its files to the running one
and exits (:mod:`quill.core.lite.inbox`). That is what makes a number mean
something -- two processes would both start counting at 1.

``--new-instance`` opts out for the case that genuinely needs it: two shells
side by side, on two monitors, with two sets of documents. The second one gets
its own numbering and its own window, and both write the same settings file, so
the last one closed wins on window size. That is the documented cost of asking
for it.

### Where the menu bar lives

On Windows an MDI child's menu bar replaces the parent's while that child is
active, which is exactly what is wanted: each document owns the bar, so a menu
item can act on *this* document without asking which one is in front. The parent
carries its own smaller bar for the state where nothing is open at all -- which
QuillLite avoids by always keeping one document, but a menu bar that vanishes is
worse than one that is briefly short.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.lite import APP_NAME

__all__ = ["QuillLiteShell"]

#: Documents beyond this many stop getting an Alt+digit; the Window menu still
#: lists them all, and Ctrl+F6 still walks them.
MAX_NUMBERED = 9


class QuillLiteShell(wx.MDIParentFrame):
    """The one top-level window. Documents live inside it, numbered."""

    def __init__(self, app: Any, size: tuple[int, int]) -> None:
        super().__init__(None, title=APP_NAME, size=size)
        self.app = app
        self._build_placeholder_menu()
        # F1 on the shell itself: no show path wraps a main window, so the
        # context-help engine has to be bound here directly. A child that is
        # active binds its own, and the child wins because it has focus.
        from quill.ui import app_context_help

        app_context_help.install(self, wx=wx)
        self.Bind(wx.EVT_CLOSE, self._on_close)

    def _build_placeholder_menu(self) -> None:
        """The bar shown when no document is open.

        Two items, because there are only two things that can be done with no
        document. An MDI parent with no menu bar at all reads to a screen reader
        as a window with nothing in it, which is worse than a short menu.
        """
        menu_bar = wx.MenuBar()
        file_menu = wx.Menu()
        new_item = file_menu.Append(wx.ID_ANY, "&New\tCtrl+N")
        open_item = file_menu.Append(wx.ID_ANY, "&Open...\tCtrl+O")
        file_menu.AppendSeparator()
        exit_item = file_menu.Append(wx.ID_ANY, "E&xit QuillLite\tCtrl+Q")
        menu_bar.Append(file_menu, "&File")
        self.SetMenuBar(menu_bar)
        self.Bind(
            wx.EVT_MENU,
            lambda _e: self.app.new_window(self.app.settings.default_mode),
            new_item,
        )
        self.Bind(wx.EVT_MENU, lambda _e: self.app.open_from_dialog(self), open_item)
        self.Bind(wx.EVT_MENU, lambda _e: self.app.exit_all(), exit_item)

    def _on_close(self, event: wx.CloseEvent) -> None:
        """Closing the shell closes everything, and asks about each document.

        Vetoed if any document refuses, because Alt+F4 on the shell is
        indistinguishable from Exit and must not be able to lose work either.
        """
        if event.CanVeto():
            for frame in list(self.app.frames):
                if not frame.confirm_discard():
                    event.Veto()
                    return
            for frame in list(self.app.frames):
                frame.modified = False
        # While the windows still exist: after Destroy there is nothing left to
        # ask which files were open, and Alt+F4 on the shell has to remember the
        # session exactly as Exit does.
        self.app.remember_session()
        self.app.shutting_down = True
        # Stop the children's timers before the parent takes them down. A
        # wx.Timer outlives the window that owns it just long enough to fire
        # into a destroyed control, and the resulting error surfaces as a
        # crash dialog on the way out of a session that went fine.
        for frame in list(self.app.frames):
            frame.stop_timers()
        self.Destroy()
