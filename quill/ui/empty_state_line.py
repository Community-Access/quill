"""A focusable line that says what fills an empty list (FUX-09).

An empty tree or list says nothing useful to a screen reader: "Favorite
stations, tree view, empty" tells somebody new that there is nothing here, not
what to do about it. :class:`EmptyStateLine` is one read-only text line placed
just before the list in the tab order. It is shown only while the list is
empty, and it carries the sentence from :func:`quill.core.first_task.first_task_line`
("No favorite stations yet. Browse Stations (Ctrl+B) finds one to play.").

Why a read-only line and not speech: the line is on screen for magnification,
in the tab order for keyboard users, read by the screen reader when it gets
focus and readable again at any time -- so the app never has to *say* it
(GATE-13), and it is never a tour or a modal. Why single-line: a screen reader
reads the whole value of a single-line edit on focus, where a multi-line one
reads only the line under the caret.

When the list fills, the line hides itself; if it had focus, focus moves to
the list, so a keyboard user is never left on a control that vanished. That
holds when the list fills from a dialog over the window (Add Custom Station):
the line was the window's last focus, so focus goes to the list when the
window is active again, not to a hidden control.

It has a normal border, so it looks like a field and shows a focus ring, and
the whole sentence is also its tooltip, for a magnifier user whose view of
the field is cut short.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

__all__ = ["EmptyStateLine", "key_for_host"]

_HELP = (
    "What to do first: this line is shown only while the list after it is "
    "empty, and it names the command, and its key, that fills it."
)


def key_for_host(host: Any) -> Callable[[str], str]:
    """The live key of a command in an app built on ``app_shell`` ("" if none)."""

    def key_for(command_id: str) -> str:
        binding = getattr(host, "_binding_for", None)
        return str(binding(command_id) or "") if callable(binding) else ""

    return key_for


def _focus_quietly(window: Any) -> None:
    try:
        window.SetFocus()
    except RuntimeError:  # destroyed meanwhile
        pass


class EmptyStateLine:
    """The line, built hidden; :meth:`update` shows or hides it."""

    def __init__(self, parent: Any, *, name: str) -> None:
        import wx

        from quill.ui.accessible_names import set_accessible_name
        from quill.ui.spoken_name import set_spoken_name

        self._wx = wx
        self.ctrl = wx.TextCtrl(parent, style=wx.TE_READONLY)
        set_accessible_name(self.ctrl, name)
        set_spoken_name(self.ctrl, name)  # what Windows screen readers read (#1693)
        self.ctrl.SetHelpText(_HELP)
        self.ctrl.Hide()
        #: The line was the window's last focus: focus left it for a dialog.
        self._last_focus = False
        #: Where focus goes when the window is active again (the line hid meanwhile).
        self._pending: Any = None
        self.ctrl.Bind(wx.EVT_SET_FOCUS, self._on_set_focus)
        self.ctrl.Bind(wx.EVT_KILL_FOCUS, self._on_kill_focus)
        top = self.ctrl.GetTopLevelParent()
        if top is not None:
            top.Bind(wx.EVT_ACTIVATE, self._on_activate)

    def _on_set_focus(self, event: Any) -> None:
        self._last_focus = True
        event.Skip()

    def _on_kill_focus(self, event: Any) -> None:
        # Focus moving within this window forgets the line; focus leaving
        # for a dialog or another app keeps it as the window's last focus.
        to = event.GetWindow()
        if to is not None and to.GetTopLevelParent() is self.ctrl.GetTopLevelParent():
            self._last_focus = False
        event.Skip()

    def _on_activate(self, event: Any) -> None:
        pending, self._pending = self._pending, None
        if event.GetActive() and pending is not None:
            self._wx.CallAfter(_focus_quietly, pending)
        event.Skip()

    @property
    def shown(self) -> bool:
        try:
            return bool(self.ctrl.IsShown())
        except RuntimeError:  # destroyed with its window
            return False

    @property
    def text(self) -> str:
        return str(self.ctrl.GetValue()) if self.shown else ""

    def update(self, text: str, *, then_focus: Any = None) -> None:
        """Show *text*, or hide the line when *text* is "".

        *then_focus* is the list: when the line hides while it has focus,
        focus goes there instead of to nowhere.
        """
        try:
            if text:
                if self.ctrl.GetValue() != text:
                    self.ctrl.ChangeValue(text)
                    self.ctrl.SetToolTip(text)
                if not self.ctrl.IsShown():
                    self.ctrl.Show()
                    self._relayout()
                return
            if not self.ctrl.IsShown():
                return
            had_focus = self._wx.Window.FindFocus() is self.ctrl
            remembered = self._last_focus
            self.ctrl.Hide()
            self._last_focus = False
            self._relayout()
            if then_focus is None:
                return
            if had_focus:
                then_focus.SetFocus()
            elif remembered:
                self._pending = then_focus  # set when the window is active again
        except RuntimeError:  # destroyed with its window
            return

    def focus(self) -> bool:
        """Put focus on the line when it is shown. True when it took focus."""
        if not self.shown:
            return False
        try:
            self.ctrl.SetFocus()
            self.ctrl.SetInsertionPoint(0)
        except RuntimeError:
            return False
        return True

    def _relayout(self) -> None:
        parent = self.ctrl.GetParent()
        if parent is not None:
            parent.Layout()
