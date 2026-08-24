"""The ACB Media Schedule window: a week you can act on (list.md section 6).

A week of radio, Sunday to Saturday, in one list with a day heading before each
day's programmes -- the same shape the Play Queue uses for its groups, because
a screen-reader user arrowing down a week needs the day announced once rather
than repeated on every row.

Everything a listener can do here they can do three ways, which is 6.6 and is
not negotiable: the context menu (Applications key or Shift+F10), the buttons
below the list (tabbable, in the same order), and Enter on the row for the
obvious verb. A window whose verbs live only in a right-click menu is a window
half its audience cannot use.

**The week never blocks.** Loading goes through the task manager, and the
schedule comes from ``acb_calendar``, which answers from the cache when the
network is not there and says how old its answer is. A failure is recorded in
Recent Problems rather than raised, so a week that will not load is an empty
week with a sentence, never a window that dies.

**Search filters the week in place** (6.3) rather than opening a second
surface: the day headings stay, the counts follow, and clearing the box puts
the week back -- the search-reset rule the family already follows.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.radio import acb_calendar, calendar_actions
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "ACB Media Schedule"


def show_calendar(host: Any) -> None:
    """Open the schedule. Modal, house pattern."""
    import wx

    _CalendarWindow(host, wx).show()


class _CalendarWindow:
    """The window's state: which week, which stream, which query."""

    def __init__(self, host: Any, wx: Any) -> None:
        self._host = host
        self._wx = wx
        self._events: list[Any] = []
        self._age: float | None = None
        self._rows: list[tuple[int | None, Any]] = []
        self._anchor = datetime.now(UTC)
        self._stream = ""
        self._query = ""

    # -- building ---------------------------------------------------------------

    def show(self) -> None:
        """Build, load, and show through the hardened modal path.

        One method because the dialog-hardening gate reads the scope that
        *constructs* a ``wx.Dialog`` for its accessible show path -- and it is
        right to: a window built in one place and shown in another is a window
        that can grow a second, unhardened way in.
        """
        wx = self._wx
        self.dialog = wx.Dialog(
            self._host.frame, title=TITLE, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetSize(wx.Size(820, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        self._summary = wx.StaticText(self.dialog, label="Loading the schedule...")
        root.Add(self._summary, 0, wx.ALL, 8)

        filters = wx.BoxSizer(wx.HORIZONTAL)
        filters.Add(
            wx.StaticText(self.dialog, label="&Search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._search = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "Filters this week by programme name, description or channel. Every "
            "word has to appear somewhere, in any order. It narrows what is "
            "listed and changes nothing about what is playing; clearing the box "
            "puts the whole week back."
        )
        self._search.SetName(_help)
        self._search.SetHelpText(_help)
        filters.Add(self._search, 1, wx.EXPAND | wx.RIGHT, 12)
        filters.Add(
            wx.StaticText(self.dialog, label="C&hannel:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        self._streams = wx.Choice(self.dialog, choices=["Every channel"])
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "Narrows the week to one ACB Media channel. It filters what is "
            "listed and changes nothing about what is playing."
        )
        self._streams.SetName(_help)
        self._streams.SetHelpText(_help)
        self._streams.SetSelection(0)
        filters.Add(self._streams, 0)
        root.Add(filters, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 8)

        self._list = wx.ListBox(self.dialog, style=wx.LB_SINGLE)
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "This week's programmes, Sunday to Saturday, with a heading before "
            "each day. Enter tunes in to the highlighted programme's channel; "
            "Shift+F10 offers the rest. A day heading is not a programme and no "
            "verb acts on one."
        )
        self._list.SetName(_help)
        self._list.SetHelpText(_help)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 8)

        root.Add(self._buttons(), 0, wx.ALL, 8)
        apply_modal_ids(
            self.dialog, affirmative_id=self._close_btn.GetId(), escape_id=self._close_btn.GetId()
        )
        self.dialog.SetSizer(root)

        self._search.Bind(wx.EVT_TEXT, lambda _e: self._on_query())
        self._streams.Bind(wx.EVT_CHOICE, lambda _e: self._on_stream())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync())
        self._list.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._popup())
        apply_listbox_activation(self._list, lambda _e=None: self._run(calendar_actions.PLAY))

        self._load()
        self._wx.CallAfter(self._list.SetFocus)
        try:
            self._host._show_modal_dialog(self.dialog, TITLE)
        finally:
            self.dialog.Destroy()

    def _buttons(self) -> Any:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        # Every verb on the context menu is also a button, in the same order
        # (6.6). A verb reachable only by right-click is a verb half the
        # audience does not have.
        self._verb_buttons: list[tuple[str, Any]] = []
        for action_id, label, help_text in (
            (calendar_actions.PLAY, "&Play", "Tunes in to the highlighted programme's channel."),
            (
                calendar_actions.RECORD,
                "&Record...",
                "Opens Schedule Recording pre-filled with this programme's channel and times.",
            ),
            (
                calendar_actions.REMIND,
                "Re&mind Me...",
                "Sets a reminder before this programme starts. Quiet hours can hold it back.",
            ),
            (
                calendar_actions.QUEUE,
                "Add to &Queue",
                "Puts this channel in the Play Queue. A live channel plays whatever "
                "is on when it is reached, which is why the label says channel.",
            ),
            (calendar_actions.COPY, "&Copy Details", "Copies what, when and where, as text."),
            (calendar_actions.DETAILS, "&Show Notes...", "Reads this programme's description."),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, a=action_id: self._run(a))
            row.Add(button, 0, wx.RIGHT, 4)
            self._verb_buttons.append((action_id, button))

        for label, handler, help_text in (
            ("&Previous Week", lambda: self._step(-7), "The seven days before this one."),
            ("&Next Week", lambda: self._step(7), "The seven days after this one."),
            ("&Today", lambda: self._step(None), "Back to the week containing today."),
            ("Re&fresh", self._refresh, "Reads the schedule from ACB again, now."),
            ("E&xport...", self._export, "Writes this week to a Markdown file."),
        ):
            button = wx.Button(self.dialog, label=label)
            button.SetHelpText(help_text)
            button.Bind(wx.EVT_BUTTON, lambda _e, h=handler: h())
            row.Add(button, 0, wx.RIGHT, 4)

        self._close_btn = self._wx.Button(self.dialog, self._wx.ID_CLOSE, label="Cl&ose")
        self._close_btn.SetHelpText("Closes the schedule. Reminders you set stay set.")
        self._close_btn.Bind(self._wx.EVT_BUTTON, lambda _e: self.dialog.EndModal(wx.ID_CLOSE))
        row.Add(self._close_btn, 0)
        return row

    # -- loading ----------------------------------------------------------------

    def _load(self, *, refresh: bool = False) -> None:
        """Fetch off the UI thread; fall back to fetching inline without one."""
        tasks = getattr(self._host, "_task_manager", None)
        safe = bool(getattr(self._host, "_safe_mode", False))

        # The anchor decides which month is fetched: My Calendar serves a
        # window, so stepping into September has to ask for September rather
        # than re-reading August from the cache.
        when = self._anchor

        def _work(**_kwargs: Any) -> Any:
            return acb_calendar.fetch_schedule(when=when, refresh=refresh, safe_mode=safe)

        def _done(_op: str, result: Any) -> None:
            events, age = result if isinstance(result, tuple) else ([], None)
            self._events, self._age = list(events), age
            self._fill_streams()
            self._reload(announce=True)

        if tasks is None:
            _done("", _work())
            return
        tasks.submit(
            "radio-acb-calendar",
            _work,
            on_success=lambda op, result: self._wx.CallAfter(_done, op, result),
            on_failure=lambda _op, error: self._wx.CallAfter(self._failed, error),
        )

    def _failed(self, error: BaseException) -> None:
        # Never raised into the window: an empty week with a sentence beats a
        # window that dies. The reason is already in Recent Problems.
        self._summary.SetLabel("The schedule could not be read.")
        self._host._announce(f"The ACB Media schedule could not be read. {error}.")

    def _refresh(self) -> None:
        self._host._announce("Reading the schedule again...")
        self._load(refresh=True)

    # -- the list ---------------------------------------------------------------

    def _visible(self) -> list[tuple[datetime, list[Any]]]:
        events = acb_calendar.by_stream(self._events, self._stream)
        events = acb_calendar.search(events, self._query)
        return acb_calendar.days_of(events, self._anchor)

    def _reload(self, *, announce: bool = False, select: int = 0) -> None:
        days = self._visible()
        labels: list[str] = []
        self._rows = []
        now = datetime.now(UTC)
        for midnight, events in days:
            labels.append(calendar_actions.day_label(midnight, len(events)))
            self._rows.append((None, midnight))
            for event in events:
                labels.append("    " + calendar_actions.row_label(event, now))
                self._rows.append((len(self._rows), event))
        self._list.Set(labels)
        said = calendar_actions.summarise_week(days, self._age)
        self._summary.SetLabel(said)
        if labels:
            self._list.SetSelection(max(0, min(select, len(labels) - 1)))
        self._sync()
        if announce:
            self._host._announce(said)

    def _selected(self) -> Any:
        row = self._list.GetSelection()
        if row == self._wx.NOT_FOUND or row >= len(self._rows):
            return None
        index, payload = self._rows[row]
        # A day heading is not a programme. Acting on one because it happened
        # to be selected is how somebody records a Wednesday.
        return payload if index is not None else None

    def _sync(self) -> None:
        event = self._selected()
        now = datetime.now(UTC)
        by_id = {}
        if event is not None:
            by_id = {
                action.action_id: action
                for action in calendar_actions.actions_for(
                    event, now, has_reminder=self._has_reminder(event)
                )
            }
        for action_id, button in self._verb_buttons:
            action = by_id.get(action_id)
            if action_id == calendar_actions.REMIND and calendar_actions.UNREMIND in by_id:
                action = by_id[calendar_actions.UNREMIND]
                button.SetLabel("Re&move Reminder")
            elif action_id == calendar_actions.REMIND:
                button.SetLabel("Re&mind Me...")
            button.Enable(action is not None and action.enabled)
            if action is not None and not action.enabled:
                button.SetHelpText(f"Not available: {action.reason}.")

    # -- verbs ------------------------------------------------------------------

    def _popup(self) -> None:
        event = self._selected()
        if event is None:
            self._host._announce("That is a day heading, not a programme.")
            return
        wx = self._wx
        menu = wx.Menu()
        now = datetime.now(UTC)
        for action in calendar_actions.actions_for(
            event, now, has_reminder=self._has_reminder(event)
        ):
            item = menu.Append(wx.ID_ANY, action.label)
            item.Enable(action.enabled)
            if not action.enabled:
                item.SetHelp(f"Not available: {action.reason}.")
            menu.Bind(wx.EVT_MENU, lambda _e, a=action: self._invoke(a), item)
        self._list.PopupMenu(menu)
        menu.Destroy()

    def _run(self, action_id: str) -> None:
        event = self._selected()
        if event is None:
            self._host._announce("No programme is selected.")
            return
        wanted = action_id
        if action_id == calendar_actions.REMIND and self._has_reminder(event):
            wanted = calendar_actions.UNREMIND
        for action in calendar_actions.actions_for(
            event, datetime.now(UTC), has_reminder=self._has_reminder(event)
        ):
            if action.action_id == wanted:
                self._invoke(action)
                return

    def _invoke(self, action: Any) -> None:
        event = self._selected()
        if event is None:
            return
        if not action.enabled:
            # 11.2: a dimmed verb says which state dimmed it, out loud, when
            # somebody reaches it anyway.
            self._host._announce(f"{action.label.replace('&', '')}: {action.reason}.")
            return
        from quill.ui.radio import calendar_verbs

        calendar_verbs.run(self._host, self, action.action_id, event)

    # -- filters and weeks ------------------------------------------------------

    def _on_query(self) -> None:
        self._query = self._search.GetValue().strip()
        self._reload()

    def _on_stream(self) -> None:
        index = self._streams.GetSelection()
        self._stream = "" if index <= 0 else self._streams.GetString(index)
        self._reload(announce=True)

    def _fill_streams(self) -> None:
        names = acb_calendar.stream_names(self._events)
        self._streams.Set(["Every channel", *names])
        self._streams.SetSelection(0)
        self._stream = ""

    def _step(self, days: int | None) -> None:
        before = self._anchor
        self._anchor = datetime.now(UTC) if days is None else self._anchor + timedelta(days=days)
        if (self._anchor.year, self._anchor.month) != (before.year, before.month):
            # A different month is a different fetch. Reloading first would
            # show an empty week for a second and then fill it, which reads as
            # "nothing on" to anybody listening.
            self._load()
            return
        self._reload(announce=True)

    def _has_reminder(self, event: Any) -> bool:
        from quill.core.paths import app_data_dir
        from quill.core.radio import reminders

        return (
            reminders.find_for_target(app_data_dir(), reminders.KIND_EVENT, event.uid) is not None
        )

    def _export(self) -> None:
        from quill.ui.radio import calendar_verbs

        calendar_verbs.export_week(self._host, self.dialog, self._visible(), self._anchor)


__all__ = ["TITLE", "show_calendar"]
