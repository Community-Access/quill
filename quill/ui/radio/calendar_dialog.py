"""The ACB Media Schedule window: one flat list of what is published.

**It was a week, and a week was wrong** (rewritten 2026-08-24). The window
used to page Sunday to Saturday with a day heading before each day. That shape
assumes a calendar which is always populated, and ACB's is not: they post a
fortnight of listings at a time and then stop, so the week containing *today*
is routinely empty. Arrowing to today and finding nothing is then
indistinguishable from a broken feed -- and it was reported as one. Confirmed
against the live feed on 2026-08-23 and again on 2026-08-24: the published
schedule ran out on 15 August both times.

So: every published programme, in one list, sorted by date. Three filters
above it -- a search box, a date picker holding only the dates that *have*
programmes, and a channel picker -- and a summary line that always says how
far the published listings actually run, and says plainly when that is already
in the past. A window that cannot tell "nothing posted yet" from "broken"
makes its reader do it.

Everything a listener can do here they can do three ways, which is 6.6 and is
not negotiable: the context menu (Applications key or Shift+F10), the buttons
below the list (tabbable, in the same order), and Enter on the row for the
obvious verb.

**The list never blocks.** Loading goes through the task manager, and the
schedule comes from ``acb_calendar``, which answers from the cache when the
network is not there and says how old its answer is. A failure is recorded in
Recent Problems rather than raised, so a schedule that will not load is an
empty list with a sentence, never a window that dies.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

from quill.core.radio import acb_calendar, calendar_actions
from quill.ui.dialog_contract import apply_listbox_activation, apply_modal_ids

TITLE = "ACB Media Schedule"


#: The schedule window currently on screen, if any. One per process.
#:
#: Playback is asynchronous: pressing Play leaves the stream CONNECTING and the
#: PLAYING transition arrives a second or two later, from a background thread.
#: A window that only re-faces its buttons when somebody presses something
#: therefore cannot follow a stream that starts, stalls, reconnects or dies on
#: its own -- so the app's state handler calls :func:`refresh_open`, exactly as
#: it already does for the player window.
_OPEN: Any = None


def show_calendar(host: Any) -> None:
    """Open the schedule. Modal, house pattern."""
    import wx

    _CalendarWindow(host, wx).show()


def refresh_open(_host: Any = None) -> None:
    """Re-face the open schedule's buttons. A no-op when none is open."""
    window = _OPEN
    if window is None:
        return
    try:
        window._sync()
    except Exception:  # noqa: BLE001 - a closing window must not break playback
        return


def reload_open() -> bool:
    """Re-pull the open schedule from ACB. ``False`` when none is open.

    What the Community menu's Refresh calls first: refreshing the feed while
    the window is up and leaving the window showing the old rows would be the
    same bug in a new place.
    """
    window = _OPEN
    if window is None:
        return False
    try:
        window._refresh()
    except Exception:  # noqa: BLE001 - a closing window must not break the menu
        return False
    return True


class _CalendarWindow:
    """The window's state: which date, which channel, which query."""

    def __init__(self, host: Any, wx: Any) -> None:
        self._host = host
        self._wx = wx
        self._events: list[Any] = []
        self._age: float | None = None
        # When this copy came off the feed. Captured once, at the moment the
        # load lands, rather than recomputed from *age* on every redraw -- the
        # age was measured then, and subtracting it from a later "now" walks
        # the timestamp forward every time somebody types in the search box.
        self._pulled_at: datetime | None = None
        self._rows: list[Any] = []
        self._dates: list[tuple[str, str]] = []
        self._date = ""
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
        self.dialog.SetSize(wx.Size(860, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        # A read-only edit field, not a StaticText. The summary is the sentence
        # that explains an empty list -- how far ACB's published schedule runs,
        # and that nothing is posted for today -- and static text cannot be
        # tabbed to, arrowed through, or re-read a word at a time. Somebody who
        # missed it as it was spoken had no way back to it (reported
        # 2026-08-24). Read-only rather than disabled, so it takes focus and the
        # review cursor while refusing edits.
        self._summary = wx.TextCtrl(
            self.dialog,
            value="Loading the schedule...",
            style=wx.TE_READONLY | wx.TE_MULTILINE | wx.TE_NO_VSCROLL,
            size=wx.Size(-1, 48),
        )
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "What this schedule contains, in a sentence: how many programmes "
            "are listed, how far ACB's published listings run, and when this "
            "copy was last pulled from ACB -- the time is here so you can tell "
            "a Refresh that fetched something new from one that did not. When "
            "the list is empty this is where the reason is. It is read-only -- "
            "you can tab to it and arrow through it, but not change it."
        )
        self._summary.SetName(_help)
        self._summary.SetHelpText(_help)
        root.Add(self._summary, 0, wx.EXPAND | wx.ALL, 8)

        filters = wx.BoxSizer(wx.HORIZONTAL)
        filters.Add(
            wx.StaticText(self.dialog, label="&Search:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._search = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "Filters the schedule by programme name, description or channel. "
            "Every word has to appear somewhere, in any order. It narrows what "
            "is listed and changes nothing about what is playing; clearing the "
            "box puts the whole schedule back."
        )
        self._search.SetName(_help)
        self._search.SetHelpText(_help)
        filters.Add(self._search, 1, wx.EXPAND | wx.RIGHT, 12)

        filters.Add(
            wx.StaticText(self.dialog, label="&Date:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._date_choice = wx.Choice(self.dialog, choices=["All dates"])
        # SetName is what focus announces; SetHelpText is what F1
        # answers. Different mechanisms, so both, spelled out -- the
        # radio-help audit reads the source for the second.
        _help = (
            "Jumps to one date. Only dates that actually have programmes are "
            "offered, and each says how many -- a picker that mostly answers "
            "'nothing' is the calendar this window replaced. Choose All dates "
            "to see the whole published schedule again."
        )
        self._date_choice.SetName(_help)
        self._date_choice.SetHelpText(_help)
        self._date_choice.SetSelection(0)
        filters.Add(self._date_choice, 0, wx.RIGHT, 12)

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
            "Narrows the schedule to one ACB Media channel. It filters what is "
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
            "Every published programme, oldest first, each row carrying its own "
            "date, time, name and channel. It opens on the next programme still "
            "to come. Enter tunes in to the highlighted programme's channel; "
            "Shift+F10 offers the rest. When the list is empty the line above "
            "says why -- most often that ACB has not posted listings this far "
            "ahead yet."
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
        self._date_choice.Bind(wx.EVT_CHOICE, lambda _e: self._on_date())
        self._streams.Bind(wx.EVT_CHOICE, lambda _e: self._on_stream())
        self._list.Bind(wx.EVT_LISTBOX, lambda _e: self._sync())
        self._list.Bind(wx.EVT_CONTEXT_MENU, lambda _e: self._popup())
        apply_listbox_activation(self._list, lambda _e=None: self._run(calendar_actions.PLAY))

        # refresh=True on open, deliberately. The cache stays fresh for an
        # hour, and the window used to honour that -- so a listener who saw ACB
        # move a programme, closed Quill Radio and opened it again got the same
        # stale listings back, with nothing on screen admitting it (reported
        # 2026-08-25). Opening this window *is* somebody asking for the
        # schedule; that is the one moment a fetch is not "reaching out on a
        # schedule nobody chose". It costs one small request, it does not
        # block (the load is on the task manager), and when the network is not
        # there ``resolve`` still falls back to the cache and says how old it
        # is. The hour-long cache still serves What Is On Now, which has to
        # answer instantly and does not open anything.
        self._load(refresh=True)
        self._wx.CallAfter(self._list.SetFocus)
        global _OPEN
        _OPEN = self
        try:
            self._host._show_modal_dialog(self.dialog, TITLE)
        finally:
            _OPEN = None
            self.dialog.Destroy()

    def _buttons(self) -> Any:
        wx = self._wx
        row = wx.BoxSizer(wx.HORIZONTAL)
        # Every verb on the context menu is also a button, in the same order
        # (6.6). A verb reachable only by right-click is a verb half the
        # audience does not have.
        self._verb_buttons: list[tuple[str, Any]] = []
        for action_id, label, help_text in (
            (
                calendar_actions.PLAY,
                "&Play",
                "Tunes in to the highlighted programme's channel, and stops it if "
                "that channel is already playing. The button says which.",
            ),
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
            (
                "&Next Programme",
                self._go_next,
                "Moves to the next programme that has not finished yet.",
            ),
            (
                "Re&fresh",
                self._refresh,
                "Reads the schedule from ACB again, now, ignoring every cached "
                "copy. The line at the top then says what time it was pulled.",
            ),
            ("E&xport...", self._export, "Writes what is listed to a Markdown file."),
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

        def _work(**_kwargs: Any) -> Any:
            return acb_calendar.fetch_schedule(refresh=refresh, safe_mode=safe)

        def _done(_op: str, result: Any) -> None:
            events, age = result if isinstance(result, tuple) else ([], None)
            self._events = sorted(events, key=lambda event: event.start)
            self._age = age
            self._pulled_at = datetime.now(UTC) - timedelta(seconds=age or 0.0)
            self._fill_streams()
            self._fill_dates()
            self._reload(announce=True, select=None)

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
        # Never raised into the window: an empty list with a sentence beats a
        # window that dies. The reason is already in Recent Problems.
        #
        # The pull note goes on the end even here, because a failed refresh is
        # exactly when "what am I looking at, then?" matters: the rows below
        # are still the copy from earlier, and a window that says only "could
        # not be read" leaves somebody unable to tell whether they are reading
        # today's schedule or Tuesday's.
        said = "The schedule could not be read."
        note = calendar_actions.pull_note(self._age, self._pulled_at, datetime.now(UTC))
        if note:
            said = f"{said} What is listed was {note[0].lower()}{note[1:]}"
        self._summary.SetValue(said)
        self._host._announce(f"The ACB Media schedule could not be read. {error}.")

    def _refresh(self) -> None:
        self._host._announce("Reading the schedule again...")
        self._load(refresh=True)

    # -- the list ---------------------------------------------------------------

    def _visible(self) -> list[Any]:
        events = acb_calendar.by_stream(self._events, self._stream)
        events = calendar_actions.on_date(events, self._date)
        return acb_calendar.search(events, self._query)

    def _reload(self, *, announce: bool = False, select: int | None = 0) -> None:
        """Rebuild the list. ``select=None`` means "the next programme"."""
        events = self._visible()
        now = datetime.now(UTC)
        self._rows = events
        self._list.Set([calendar_actions.full_row_label(event, now) for event in events])
        filtered = bool(self._query or self._stream or self._date)
        said = calendar_actions.summarise_schedule(
            events, self._events, now, self._age, filtered=filtered, pulled_at=self._pulled_at
        )
        self._summary.SetValue(said)
        if events:
            index = calendar_actions.first_upcoming_index(events, now) if select is None else select
            self._list.SetSelection(max(0, min(index, len(events) - 1)))
        self._sync()
        if announce:
            self._host._announce(said)

    def _go_next(self) -> None:
        """Put the cursor on the next programme still to come."""
        if not self._rows:
            self._host._announce("There is nothing listed to move to.")
            return
        now = datetime.now(UTC)
        index = calendar_actions.first_upcoming_index(self._rows, now)
        self._list.SetSelection(index)
        self._sync()
        self._host._announce(calendar_actions.full_row_label(self._rows[index], now))

    def _selected(self) -> Any:
        row = self._list.GetSelection()
        if row == self._wx.NOT_FOUND or row >= len(self._rows):
            return None
        return self._rows[row]

    def _actions_for(self, event: Any, now: datetime) -> list[Any]:
        """This programme's verbs, told what the player is currently on.

        The Play verb turns into Stop for the channel you are already
        listening to, so every route to it -- button, context menu, Enter --
        has to be built from the same answer.
        """
        from quill.ui.radio import calendar_verbs

        return calendar_actions.actions_for(
            event,
            now,
            has_reminder=self._has_reminder(event),
            playing_stream=calendar_verbs.playing_stream_name(self._host),
        )

    def _sync(self) -> None:
        event = self._selected()
        now = datetime.now(UTC)
        by_id = {}
        if event is not None:
            by_id = {action.action_id: action for action in self._actions_for(event, now)}
        for action_id, button in self._verb_buttons:
            action = by_id.get(action_id)
            if action_id == calendar_actions.REMIND and calendar_actions.UNREMIND in by_id:
                action = by_id[calendar_actions.UNREMIND]
                button.SetLabel("Re&move Reminder")
            elif action_id == calendar_actions.REMIND:
                button.SetLabel("Re&mind Me...")
            elif action_id == calendar_actions.PLAY and action is not None:
                # "Play" and "Stop" are different promises. A button that says
                # Play while the channel is on is the bug this fixes.
                button.SetLabel(action.label)
            button.Enable(action is not None and action.enabled)
            if action is not None and not action.enabled:
                button.SetHelpText(f"Not available: {action.reason}.")

    # -- verbs ------------------------------------------------------------------

    def _popup(self) -> None:
        """The row's verbs, and -- always -- Refresh.

        **Refresh is on the menu even when nothing is selected**, which is the
        whole reason this stopped being an early return. The moment a listener
        most wants to re-read the feed is the moment the list is empty or looks
        wrong, and that is precisely the moment there is no row to hang a menu
        off: the old menu answered "No programme is selected" and shut, so the
        only route left was a button eleventh in the tab order (reported
        2026-08-25). A verb about *the schedule* does not need a programme.
        """
        wx = self._wx
        menu = wx.Menu()
        event = self._selected()
        if event is not None:
            now = datetime.now(UTC)
            for action in self._actions_for(event, now):
                item = menu.Append(wx.ID_ANY, action.label)
                item.Enable(action.enabled)
                if not action.enabled:
                    item.SetHelp(f"Not available: {action.reason}.")
                menu.Bind(wx.EVT_MENU, lambda _e, a=action: self._invoke(a), item)
            menu.AppendSeparator()
        refresh_item = menu.Append(wx.ID_ANY, "Re&fresh the Schedule")
        refresh_item.SetHelp("Reads the schedule from ACB again, now, ignoring every cached copy.")
        menu.Bind(wx.EVT_MENU, lambda _e: self._refresh(), refresh_item)
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
        for action in self._actions_for(event, datetime.now(UTC)):
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
        # Every verb, not just the ones that used to remember to. Play changes
        # what this row offers as surely as Set a Reminder does, and it was the
        # one that did not say so: the button went on reading Play through the
        # whole broadcast.
        self._sync()

    # -- filters ----------------------------------------------------------------

    def _on_query(self) -> None:
        self._query = self._search.GetValue().strip()
        self._reload()

    def _on_stream(self) -> None:
        index = self._streams.GetSelection()
        self._stream = "" if index <= 0 else self._streams.GetString(index)
        self._reload(announce=True)

    def _on_date(self) -> None:
        index = self._date_choice.GetSelection()
        self._date = "" if index <= 0 else self._dates[index - 1][0]
        self._reload(announce=True)

    def _fill_streams(self) -> None:
        names = acb_calendar.stream_names(self._events)
        self._streams.Set(["Every channel", *names])
        self._streams.SetSelection(0)
        self._stream = ""

    def _fill_dates(self) -> None:
        self._dates = calendar_actions.date_choices(self._events)
        self._date_choice.Set(["All dates", *(label for _key, label in self._dates)])
        self._date_choice.SetSelection(0)
        self._date = ""

    def _has_reminder(self, event: Any) -> bool:
        from quill.core.paths import app_data_dir
        from quill.core.radio import reminders

        return (
            reminders.find_for_target(app_data_dir(), reminders.KIND_EVENT, event.uid) is not None
        )

    def _export(self) -> None:
        from quill.ui.radio import calendar_verbs

        calendar_verbs.export_schedule(self._host, self.dialog, self._visible())


__all__ = ["TITLE", "refresh_open", "reload_open", "show_calendar"]
