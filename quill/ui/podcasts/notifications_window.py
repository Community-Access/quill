"""Cast's Notifications window: a peer, with actions per notice (qc.md 5b).

The family's Notifications dialog (``quill/ui/notification_center``) is
modal, which Quill Radio needs; Cast wants the same list as a **peer window**
-- the menu bar's Window menu, Ctrl+number, Escape back to where you were --
and with the four verbs a new-episode notice earns (ear.md R9): Play Now,
Add to Queue, Go to the Podcast, Mark Read. Enter keeps meaning "go to it";
the other three are one key deeper, in the row's context menu.

Made once and hidden on close, like Now Playing, so its number in the
Window menu does not move.
"""

from __future__ import annotations

from typing import Any

import wx

from quill.core.notifications import (
    clear_notifications,
    load_notifications,
    mark_all_read,
    mark_read,
    newest_first,
)
from quill.ui.notification_center import row_label

__all__ = ["NotificationsWindow", "open_notifications_window"]

TITLE = "Notifications"
_EMPTY = "Nothing to tell you yet."


class NotificationsWindow:
    """The frame, its list, and the verbs."""

    TITLE = TITLE
    MENU_TITLE = "&Notifications"

    def __init__(self, host: Any) -> None:
        self._host = host
        self._notices: list[Any] = []
        self.frame = wx.Frame(host.frame, title=TITLE, size=(680, 440))
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)
        root.Add(
            wx.StaticText(panel, label="&Notifications, newest first:"), 0, wx.LEFT | wx.TOP, 8
        )
        self._list = wx.ListBox(panel, choices=[], style=wx.LB_SINGLE)
        self._list.SetHelpText(
            "What QUILL Cast told you, newest first. A row beginning New has not "
            "been read. Enter goes to what it was about; the Applications key "
            "offers Play Now, Add to Queue, Go to the Podcast and Mark Read on a "
            "new-episode notice. Escape closes the window."
        )
        root.Add(self._list, 1, wx.EXPAND | wx.ALL, 8)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        for label, help_text, handler in (
            ("&Open", "Goes to what this notification was about.", self._open),
            (
                "Mark All as &Read",
                "Clears the New marker on every row. Nothing is removed.",
                self._mark_all,
            ),
            (
                "Cl&ear List",
                "Empties the list. Never the episodes it was telling you about.",
                self._clear,
            ),
        ):
            button = wx.Button(panel, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer(1)
        close = wx.Button(panel, label="Close")
        close.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close, modeless=True)
        buttons.Add(close, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)
        panel.SetSizer(root)
        from quill.ui.dialog_contract import apply_listbox_activation

        apply_listbox_activation(self._list, lambda _e: self._open())
        for context_event in (wx.EVT_CONTEXT_MENU, wx.EVT_RIGHT_UP):
            self._list.Bind(context_event, self._on_context)
        self._list.Bind(wx.EVT_KEY_DOWN, self._on_key)
        self.refresh()

    # -- showing -------------------------------------------------------------------- #

    def focus_target(self) -> Any:
        return self._list

    def refresh(self, *, keep: int = -1) -> None:
        try:
            self._notices = newest_first(load_notifications())
        except Exception:  # noqa: BLE001
            self._notices = []
        self._list.Set([row_label(n) for n in self._notices] or [_EMPTY])
        if self._list.GetCount():
            wanted = keep if 0 <= keep < self._list.GetCount() else 0
            self._list.SetSelection(wanted)
        refresh_counts = getattr(self._host, "_refresh_place_counts", None)
        if callable(refresh_counts):
            refresh_counts()

    # -- the verbs ----------------------------------------------------------------------- #

    def _current(self) -> Any:
        index = self._list.GetSelection()
        if not self._notices or not (0 <= index < len(self._notices)):
            return None
        return self._notices[index]

    def _resolved(self, notice: Any) -> tuple[Any, Any] | None:
        """(show, newest unplayed episode) for a new-episode notice, or None."""
        from quill.ui.podcasts.notice_actions import episode_for

        return episode_for(notice)

    def _read_it(self, notice: Any) -> None:
        if not notice.read:
            mark_read(notice.id)
            self.refresh(keep=self._list.GetSelection())

    def _open(self) -> None:
        notice = self._current()
        if notice is None:
            return
        self._read_it(notice)
        target = str(getattr(notice, "target", "") or "")
        if not target:
            self._host._announce("There is nothing to open for this one.")
            return
        self.frame.Hide()
        wx.CallAfter(self._host.open_notification_target, target)

    def _play_now(self) -> None:
        from quill.ui.podcasts.notice_actions import play_now

        notice = self._current()
        if notice is not None and play_now(self._host, notice):
            self.refresh(keep=self._list.GetSelection())

    def _add_to_queue(self) -> None:
        from quill.ui.podcasts.notice_actions import add_to_queue

        notice = self._current()
        if notice is not None and add_to_queue(self._host, notice):
            self.refresh(keep=self._list.GetSelection())

    def _mark_read(self) -> None:
        notice = self._current()
        if notice is None:
            return
        if notice.read:
            self._host._announce("Already read.")
            return
        self._read_it(notice)
        self._host._announce("Marked as read.")

    def _mark_all(self) -> None:
        unread = sum(1 for n in self._notices if not n.read)
        mark_all_read()
        self.refresh(keep=self._list.GetSelection())
        self._host._announce("Nothing was unread." if not unread else f"Marked {unread} as read.")

    def _clear(self) -> None:
        if not self._notices:
            self._host._announce("The list is already empty.")
            return
        removed = len(self._notices)
        clear_notifications()
        self.refresh()
        self._host._announce(f"Cleared {removed} notification{'s' if removed != 1 else ''}.")

    def _on_key(self, event: Any) -> None:
        code = event.GetKeyCode()
        if code in (wx.WXK_DELETE, wx.WXK_NUMPAD_DELETE):
            self._mark_read()
            return
        if code in (wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER) and event.ControlDown():
            self._play_now()  # ear.md R9: a toast is not reliably reachable
            return
        if code == wx.WXK_SPACE and not event.HasAnyModifiers():
            self._add_to_queue()
            return
        event.Skip()

    def _on_context(self, event: Any) -> None:
        notice = self._current()
        if notice is None:
            return
        menu = wx.Menu()
        rows: list[tuple[str, Any]] = [("&Open\tEnter", self._open)]
        if self._resolved(notice) is not None:
            rows += [
                ("&Play Now\tCtrl+Enter", self._play_now),
                ("Add to &Queue\tSpace", self._add_to_queue),
            ]
            rows.append(("&Go to the Podcast", self._open))
        rows.append(("Mark &Read\tDelete", self._mark_read))
        for label, handler in rows:
            item = menu.Append(wx.ID_ANY, label)
            menu.Bind(wx.EVT_MENU, lambda _e, h=handler: h(), item)
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()
        if hasattr(event, "Skip"):
            event.Skip(False)


def open_notifications_window(
    host: Any, *, focus: bool = True, opener: Any = None
) -> NotificationsWindow:
    """Open, or raise, the host's Notifications window.

    Through the shared peer contract (``peer_window``): made once, hidden on
    close, raised and refreshed when asked again, and Escape returns focus to
    whatever opened it.
    """
    from quill.ui.podcasts.peer_window import open_peer

    window: NotificationsWindow = open_peer(
        host, "_notifications_window", NotificationsWindow, focus=focus, opener=opener
    )
    return window
