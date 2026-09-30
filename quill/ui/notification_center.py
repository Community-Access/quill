"""Everything the apps have told you, in a list you can arrow through.

The window that makes a desktop notification survivable. A toast appears over
whatever you were reading, leaves on a schedule you did not choose, and if a
screen reader was mid-sentence when it arrived it may never have been read at
all -- so it cannot be the record. :mod:`quill.core.notifications` is the
record, and this is how you read it.

### Why a list, and why these columns

One listbox, newest first, each row a single line a screen reader reads in one
breath: whether it is new, which app said it, what it said, and how long ago.
Not a tree, not a grid, not a preview pane -- a notification centre somebody has
to navigate is one they stop opening, and the whole value here is that it is
faster to check than the thing it is about.

The unread marker is the **word** "New", not a colour, a bullet or an icon
font: it has to survive being read aloud, and "New" does while a bullet becomes
either silence or "black circle" depending on whose punctuation settings are in
force.

### What it does not do

It does not announce anything the reader already says. Arriving in the window,
moving through the list and the button names are all the reader's job
(GATE-13); this speaks only for outcomes it alone knows -- how many were marked
read, that the list was cleared, that there is nothing to open.

Opening a row hands the notice's *target* back to the app that raised it, which
is the only part of a notification worth keeping after you have read it: a way
back to the thing itself.
"""

from __future__ import annotations

from typing import Any

__all__ = ["TITLE", "NotificationCenterMixin", "open_notification_center", "row_label"]

TITLE = "Notifications"

#: Shown when the list is empty. A sentence rather than a blank box: an empty
#: listbox reads as nothing at all, which is indistinguishable from a window
#: that failed to load.
_EMPTY = "Nothing yet. New episodes and reminders you have been told about appear here."


def _ago(created_at: str) -> str:
    """How long ago, in the words somebody would use out loud.

    Relative rather than a timestamp, because "2 hours ago" is the question
    being asked. Falls back to the raw stored value rather than inventing a
    time when the string cannot be parsed -- a wrong clock is worse than an
    ugly one.
    """
    from datetime import UTC, datetime

    try:
        when = datetime.fromisoformat(created_at)
    except (TypeError, ValueError):
        return str(created_at or "")
    if when.tzinfo is None:
        when = when.replace(tzinfo=UTC)
    seconds = (datetime.now(UTC) - when).total_seconds()
    if seconds < 90:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes} minutes ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    days = int(hours // 24)
    return f"{days} day{'s' if days != 1 else ''} ago"


def row_label(notice: Any) -> str:
    """One notice as the single line the list reads.

    Order is deliberate: unread first (it is the reason to care), then the app,
    then what it said, then when. A listener arrowing the list hears the
    important half before deciding whether to wait for the rest.
    """
    parts = []
    if not getattr(notice, "read", False):
        parts.append("New")
    app = str(getattr(notice, "app", "") or "").strip()
    if app:
        parts.append(app)
    title = str(getattr(notice, "title", "") or "").strip()
    if not title:
        # An entry written by the older, message-only route.
        title = str(getattr(notice, "message", "") or "").strip()
    if title:
        parts.append(title)
    body = str(getattr(notice, "body", "") or "").strip()
    if body:
        parts.append(body)
    when = _ago(str(getattr(notice, "timestamp", "") or ""))
    if when:
        parts.append(when)
    return " -- ".join(parts)


def open_notification_center(host: Any, *, on_open: Any = None) -> None:
    """Show the list. *on_open* is called with a notice's target, if it has one.

    *host* supplies ``_announce`` and, where it has one, ``_show_modal_dialog``
    -- the hardened path every modal in this product goes through.
    """
    import wx

    from quill.core.notifications import (
        clear_notifications,
        load_notifications,
        mark_all_read,
        mark_read,
        newest_first,
    )
    from quill.ui.accessible_names import set_accessible_name
    from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

    say = getattr(host, "_announce", None) or (lambda _m: None)
    # Stored oldest-first, read newest-first: the order it is asked about.
    notices = newest_first(load_notifications())

    parent = getattr(host, "frame", None) or host
    dialog = wx.Dialog(parent, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
    root = wx.BoxSizer(wx.VERTICAL)

    listbox = wx.ListBox(dialog, choices=[], style=wx.LB_SINGLE)
    _list_help = (
        "Everything the QuillVille apps have told you, newest first. A row "
        'beginning "New" has not been read yet. Enter opens what a '
        "notification was about, where there is something to open."
    )
    set_accessible_name(listbox, "Notifications")
    listbox.SetHelpText(_list_help)
    root.Add(listbox, 1, wx.EXPAND | wx.ALL, 8)

    def _refresh(selection: int = 0) -> None:
        """Re-read the list into the box, keeping a sensible row selected."""
        listbox.Set([row_label(n) for n in notices] or [_EMPTY])
        if listbox.GetCount():
            listbox.SetSelection(max(0, min(selection, listbox.GetCount() - 1)))

    def _current() -> Any:
        index = listbox.GetSelection()
        if not notices or index < 0 or index >= len(notices):
            return None
        return notices[index]

    def _open(_event: Any = None) -> None:
        notice = _current()
        if notice is None:
            return
        # Reading it IS opening it: a row you have just acted on is not still
        # new, and making somebody mark it separately is busywork.
        if not notice.read:
            notices[:] = newest_first(mark_read(notice.id))
        index = listbox.GetSelection()
        target = str(getattr(notice, "target", "") or "")
        _refresh(index)
        if not target or on_open is None:
            say("There is nothing to open for this one.")
            return
        dialog.EndModal(wx.ID_OK)
        # After the modal loop has actually ended, not during it. ``EndModal``
        # only asks the loop to stop once this handler returns, so calling the
        # app straight away builds its window underneath a dialog that is still
        # closing -- and where focus lands then is whatever wx decides, which
        # for a screen-reader user is the difference between arriving in the
        # tree and arriving nowhere.
        wx.CallAfter(on_open, target)

    apply_listbox_activation(listbox, _open)

    # A stretch spacer rather than wx.ALIGN_RIGHT: the dialog contract bans the
    # alignment flag because a right-aligned button sizer does not grow with the
    # window, and a button that slides out of a resized dialog is one nobody can
    # reach (A11Y-4).
    buttons = wx.BoxSizer(wx.HORIZONTAL)
    buttons.AddStretchSpacer(1)
    # Open carries wx.ID_OK so Enter reaches it from anywhere in the window,
    # not only from the list: apply_modal_ids names ID_OK as the affirmative,
    # and an affirmative with no button behind it is an Enter key that is
    # silently ignored -- which the dialog-button gate exists to catch.
    open_btn = wx.Button(dialog, wx.ID_OK, label="&Open")
    open_btn.SetHelpText(
        "Opens what this notification was about -- the podcast it names, or "
        "the station a reminder was set on."
    )
    read_btn = wx.Button(dialog, label="Mark All as &Read")
    read_btn.SetHelpText(
        'Clears the "New" marker on every row. Nothing is removed; the list '
        "reads the same afterwards, minus the marker."
    )
    clear_btn = wx.Button(dialog, label="Cl&ear List")
    clear_btn.SetHelpText(
        "Empties this list. It removes the record of being told, never the "
        "episodes or stations it was telling you about."
    )
    close_btn = wx.Button(dialog, wx.ID_CANCEL, label="Close")
    for btn in (open_btn, read_btn, clear_btn, close_btn):
        buttons.Add(btn, 0, wx.LEFT, 6)
    root.Add(buttons, 0, wx.EXPAND | wx.ALL, 8)

    def _mark_all(_event: Any) -> None:
        unread = sum(1 for n in notices if not n.read)
        notices[:] = newest_first(mark_all_read())
        _refresh(listbox.GetSelection())
        # A count, which no tone carries and the reader cannot infer.
        say("Nothing was unread." if not unread else f"Marked {unread} as read.")

    def _clear(_event: Any) -> None:
        if not notices:
            say("The list is already empty.")
            return
        removed = len(notices)
        clear_notifications()
        notices.clear()
        _refresh()
        say(f"Cleared {removed} notification{'s' if removed != 1 else ''}.")

    open_btn.Bind(wx.EVT_BUTTON, _open)
    read_btn.Bind(wx.EVT_BUTTON, _mark_all)
    clear_btn.Bind(wx.EVT_BUTTON, _clear)

    _refresh()
    apply_modal_ids(dialog, affirmative_id=wx.ID_OK, escape_id=wx.ID_CANCEL)
    dialog.SetSizerAndFit(root)
    dialog.SetSize((640, 420))
    listbox.SetFocus()

    shower = getattr(host, "_show_modal_dialog", None)
    if callable(shower):
        shower(dialog, TITLE)
    else:
        try:
            dialog.ShowModal()
        finally:
            dialog.Destroy()


class NotificationCenterMixin:
    """The frame's side: one command, one window.

    A peer of Recent Problems and Quiet Hours, and shared the same way -- the
    list is one file both apps write, so a notification Quill Radio raised is
    one QUILL Cast can show you.
    """

    def _register_notification_commands(self) -> None:
        commands: Any = self.commands  # type: ignore[attr-defined]
        commands.try_register(
            "app.notifications",
            "Notifications...",
            self.open_notifications,
            feature_id="core.app",
        )

    def open_notifications(self) -> None:
        """Show everything the apps have told you."""
        open_notification_center(self, on_open=getattr(self, "open_notification_target", None))
