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
        self.frame.Bind(wx.EVT_CLOSE, self._on_close)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)

    # -- showing -------------------------------------------------------------------- #

    def show(self, *, focus: bool = True) -> None:
        self.refresh()
        from quill.ui.dialog_contract import show_modeless_surface

        show_modeless_surface(self.frame, TITLE, announce=self._host._announce)
        self.frame.Raise()
        if focus:
            self._list.SetFocus()

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

    def _on_close(self, event: Any) -> None:
        if event.CanVeto():
            event.Veto()
            self.frame.Hide()
            from quill.ui.dialog_contract import announce_surface_exit

            announce_surface_exit(TITLE, self._host._announce)
            focus = getattr(self._host, "_focus_cast_initial_control", None)
            if callable(focus):
                focus()
            return
        event.Skip()

    def _on_char_hook(self, event: Any) -> None:
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            self.frame.Close()
            return
        event.Skip()

    # -- the verbs ----------------------------------------------------------------------- #

    def _current(self) -> Any:
        index = self._list.GetSelection()
        if not self._notices or not (0 <= index < len(self._notices)):
            return None
        return self._notices[index]

    def _resolved(self, notice: Any) -> tuple[Any, Any] | None:
        """(show, newest unplayed episode) for a new-episode notice, or None."""
        from quill.core.podcasts import notices as cast_notices
        from quill.ui.notification_open import resolve_show

        if cast_notices.kind_of(notice) != cast_notices.NEW_EPISODE:
            return None
        show, _refusal = resolve_show(str(getattr(notice, "target", "") or ""))
        if show is None:
            return None
        from quill.core.podcasts.sorting import sort_episodes

        for episode in sort_episodes(list(show.episodes), "newest_first"):
            if not episode.played:
                return show, episode
        return None

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
        notice = self._current()
        pair = self._resolved(notice) if notice is not None else None
        if pair is None:
            self._host._announce("Nothing to play for this one.")
            return
        self._read_it(notice)
        self._host._play_episode_object(*pair)

    def _add_to_queue(self) -> None:
        from quill.core.podcasts import queue as queue_ops

        notice = self._current()
        pair = self._resolved(notice) if notice is not None else None
        if pair is None:
            self._host._announce("Nothing to queue for this one.")
            return
        show, episode = pair
        self._read_it(notice)
        if queue_ops.add_to_queue(self._host._podcast_library, show.id, episode.guid):
            self._host._save_podcast_library()
            self._host._announce(f"Added {episode.title} to the Play Queue.")
        else:
            self._host._announce(f"{episode.title} is already in the Play Queue.")

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
        event.Skip()

    def _on_context(self, event: Any) -> None:
        notice = self._current()
        if notice is None:
            return
        menu = wx.Menu()
        rows: list[tuple[str, Any]] = [("&Open\tEnter", self._open)]
        if self._resolved(notice) is not None:
            rows += [("&Play Now", self._play_now), ("Add to &Queue", self._add_to_queue)]
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


def open_notifications_window(host: Any, *, focus: bool = True) -> NotificationsWindow:
    """Open, or raise, the host's Notifications window (made once, hidden on close)."""
    window = getattr(host, "_notifications_window", None)
    if window is None:
        window = NotificationsWindow(host)
        host._notifications_window = window
        _install_peer(host, window)
    window.show(focus=focus)
    return window


def _install_peer(host: Any, window: NotificationsWindow) -> None:
    windows = getattr(host, "_windows", None)
    frame = window.frame
    menu_bar = wx.MenuBar()
    own = wx.Menu()
    close_id = wx.NewIdRef()
    own.Append(close_id, "&Close\tCtrl+W")
    frame.Bind(wx.EVT_MENU, lambda _e: frame.Close(), id=close_id)
    menu_bar.Append(own, "&Notifications")
    if windows is not None:
        windows.install(frame, menu_bar)
    frame.SetMenuBar(menu_bar)
    keep = getattr(host, "_keep_menu_ids", None)
    if callable(keep):
        keep(close_id)
    if windows is not None:
        windows.register(frame, TITLE, focus=lambda: window._list.SetFocus())
