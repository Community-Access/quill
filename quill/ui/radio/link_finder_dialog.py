"""Internet Radio > Find Streams from a Website... -- scan one page for links.

Scan fetches the one page typed and lists the stream links it finds
(``core/radio/link_finder.py``), each checked first (the live check, an idea
from Andre Louis's StreamSift, https://github.com/OnjLouis/StreamSift), so the
list is filled once and one sentence says the result (FUX-04). Scan stays
enabled, as disabling the focused button would drop focus out of the window.

**A list you can work with** (ideas from StreamSift too, in QUILL's own code):
sort, filter by format or to live streams only, find, select several, add them
to Favorites in a folder, save them as a playlist, copy their links, and scan
a stream's own server. The list changes only when the listener asks (FUX-06):
a sort or a filter keeps focus on the same stream when it is still shown, a
filter never empties the list, and a new scan clears the filter, so nothing
hides its results, while keeping the order, which its sentence names.

Every refill runs in one order: frozen while focus is on the button, refilled
with focus and selection kept by address, thawed, focus moved to the list,
and only then the sentence, with ``wx.CallAfter``, so the row is read first
and the sentence is not cut off. Keys go through the dialog's key hook (an
accelerator table would replace the transport keys) and act only in the list.
See find_streams_list, find_streams_actions and core find_streams_view.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio import find_fallback as fb
from quill.core.radio import find_streams_view as view
from quill.core.radio.find_fallback_io import FoundResult
from quill.core.radio.find_streams_text import (
    failure_sentence,
    scan_counts,
    status_label,
    summary_sentence,
)
from quill.core.radio.link_finder import PageStreamCandidate
from quill.core.radio.page_url import normalize_page_url
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip_size
from quill.ui.radio import find_streams_actions as actions
from quill.ui.radio import find_streams_menus as menus
from quill.ui.radio import play_random_ui
from quill.ui.radio.find_streams_address import AddressBox
from quill.ui.radio.find_streams_cues import CuesMixin
from quill.ui.radio.find_streams_find import FindMixin
from quill.ui.radio.find_streams_last import LastResultsMixin
from quill.ui.radio.find_streams_list import FindStreamsList
from quill.ui.radio.find_streams_tracks import TracksMixin
from quill.ui.radio.find_streams_ways import LOOKING_UP, WaysMixin
from quill.ui.spoken_name import set_spoken_name
from quill.ui.surface_lifetime import stop_timer_on_destroy, surface_tasks

#: Silence after Scan before "still scanning" is said, once.
STILL_SCANNING_SECONDS = 8
STILL_SCANNING = "Still scanning the page and checking its links."

NO_LISTENER_COUNTS = "In scan order: this page gave no listener counts."
FILTER_CLEARED = "The filter was cleared."


def _button(wx: Any, parent: Any, label: str, help_text: str, **kwargs: Any) -> Any:
    button = wx.Button(parent, label=label, **kwargs)
    set_spoken_name(button, label)
    button.SetHelpText(help_text)
    return button


class LinkFinderDialog(FindMixin, LastResultsMixin, CuesMixin, WaysMixin, TracksMixin):
    """Scan a website for candidate stream links, and work with what it found.

    *host* is the app frame (QUILL's main frame or Quill Radio's): its
    ``frame``, ``_radio_controller``, ``_task_manager``, ``_safe_mode``,
    ``_announce``, ``_radio_open_add_custom``, ``_radio_favorites`` and
    ``_save_radio_favorites``.
    """

    def __init__(self, host: Any) -> None:
        import wx

        self._wx = wx
        self._host = host
        self._controller = host._radio_controller
        # Every task this window starts is tied to its lifetime (qc.md F-02).
        self._task_manager = surface_tasks(
            host._task_manager, lambda: getattr(self, "dialog", None)
        )
        self._safe_mode = bool(host._safe_mode)
        self._announce: Callable[..., None] = host._announce
        self._candidates: list[PageStreamCandidate] = []
        self._rows: list[str] = []
        self._state = view.ViewState()
        self._page_url = ""
        self._page_title = ""
        self._favicon_url = ""
        self._find_term = ""
        self._testing = False
        self._testing_url = ""
        self._scanning = False
        self._ids = {name: wx.NewIdRef() for name in menus.MENU_NAMES}

        self.dialog = wx.Dialog(
            host.frame,
            title="Find Streams from a Website",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 760, 560))
        root = wx.BoxSizer(wx.VERTICAL)

        intro = wx.StaticText(
            self.dialog,
            label=(
                "Type a station's website address. QUILL will fetch that one page "
                "and look for stream links on it -- nothing else is contacted."
            ),
        )
        intro.Wrap(600)
        root.Add(intro, 0, wx.EXPAND | wx.ALL, 10)

        url_row = wx.BoxSizer(wx.HORIZONTAL)
        url_row.Add(
            wx.StaticText(self.dialog, label="&Website address:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.RIGHT,
            6,
        )
        # A combo box of the last ten sites that found a live stream.
        self._address = AddressBox(self.dialog, wx, host)
        self._url_ctrl = self._address.ctrl
        url_row.Add(self._url_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        self._scan_btn = wx.Button(self.dialog, label="&Scan")
        self._scan_btn.SetName("Fetch the typed page and scan it for stream links")
        url_row.Add(self._scan_btn, 0)
        root.Add(url_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._list = FindStreamsList(self.dialog, wx, root, on_context_menu=self._open_context_menu)
        self._results = self._list.ctrl

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._sort_btn = _button(
            wx,
            self.dialog,
            "S&ort and Filter",
            "Opens a menu to sort the streams found, or show only one format or only "
            "live streams. A filter never empties the list.",
        )
        self._test_btn = wx.Button(self.dialog, label="&Test")
        self._test_btn.SetName("Play the focused stream link now")
        self._use_btn = wx.Button(self.dialog, label="&Use This Link...")
        self._use_btn.SetName("Use the focused link to add a custom station")
        self._add_btn = _button(
            wx,
            self.dialog,
            menus.add_label(1),
            "Adds the selected streams to Favorites, or the focused one when none is "
            "selected. Two or more go into a folder you name.",
        )
        self._save_btn = _button(
            wx,
            self.dialog,
            menus.save_label(1),
            "Saves the selected streams, or the focused one, as an M3U, PLS, XSPF or ASX playlist.",
        )
        self._reopen_btn = _button(
            wx,
            self.dialog,
            "Reo&pen Last Results",
            "Shows the streams from your last scan again, sorted and filtered as you left "
            "them. Nothing is scanned or played. It is dimmed when there are none saved.",
        )
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close")
        for button in (self._sort_btn, self._test_btn, self._use_btn):
            btn_row.Add(button, 0, wx.RIGHT, 6)
        btn_row.Add(self._add_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._save_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._reopen_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)
        self.dialog.SetSizer(root)
        self._enable_row_buttons()
        self._load_last()

        self._url_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_scan)
        self._scan_btn.Bind(wx.EVT_BUTTON, self._on_scan)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selection_changed)
        self._results.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_selection_changed)
        self._results.Bind(wx.EVT_LIST_ITEM_FOCUSED, self._on_selection_changed)
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_test)
        self._sort_btn.Bind(wx.EVT_BUTTON, self._on_sort_button)
        self._test_btn.Bind(wx.EVT_BUTTON, lambda e: self._on_test(e, from_button=True))
        self._use_btn.Bind(wx.EVT_BUTTON, self._on_use)
        self._add_btn.Bind(wx.EVT_BUTTON, lambda _e: self._add())
        self._save_btn.Bind(wx.EVT_BUTTON, lambda _e: self._save())
        self._reopen_btn.Bind(wx.EVT_BUTTON, self._on_reopen_last)
        self.dialog.Bind(wx.EVT_MENU, self._on_menu)
        self.dialog.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        # Owned by the dialog, one-shot, and stopped whenever a scan ends.
        self._still_timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, self._on_still_scanning, self._still_timer)
        stop_timer_on_destroy(self.dialog, self._still_timer)
        self._init_cues()

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        # The transport keyboard (transport_keys): testing a found stream is
        # exactly when somebody wants to stop or turn down what is already on.
        from quill.ui.radio import transport_keys

        transport_keys.install(self.dialog, self, wx=self._wx)
        play_random_ui.register_source(self)
        self._offer_last()
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Find Streams from a Website", announce=self._announce)
        finally:
            self._remember_last()
            self._stop_cues()
            self._scanning = False
            self._still_timer.Stop()
            self.dialog.Destroy()

    def random_pool(self) -> tuple[str, list[Any]]:
        """The streams shown, for Play Random (ui/radio/play_random_ui)."""
        return play_random_ui.streams_pool(
            self._candidates, self._list.shown, self._page_title, self._favicon_url
        )

    # -- saying things ----------------------------------------------------------

    def _say(self, text: str) -> None:
        """Show *text* in the status line and say it, once."""
        self._status.SetLabel(text)
        self._announce(text)

    def _say_after(self, text: str, sound: str = "", *, show: bool = True) -> None:
        """Say *text* once the focus change before it has been read; with
        *show*, put it in the status line too (a scan sets its own, fuller one)."""
        if not text:
            return
        if show:
            self._status.SetLabel(text)
        if sound:
            self._wx.CallAfter(self._announce, text, sound=sound)
        else:
            self._wx.CallAfter(self._announce, text)

    # -- scanning ---------------------------------------------------------------

    def _on_scan(self, _event: object) -> None:
        if self._scanning:
            # Not disabled while it works (that would drop focus out of the
            # window), so a press is answered rather than ignored -- and the
            # timed notice is spent: the listener asked and has been told.
            self._still_timer.Stop()
            self._announce(STILL_SCANNING)
            return
        if self._safe_mode:
            self._say("Finding stream links is disabled in Safe Mode.")
            return
        url = self._url_ctrl.GetValue().strip()
        if not url:
            self._say("Type a website address or a station name first.")
            return
        url = self._what_to_look_up(url)
        is_name = fb.typed_kind(url) == "name"
        # Shown, not said: the listener has just pressed Scan.
        self._status.SetLabel(
            LOOKING_UP.format(name=url)
            if is_name
            else f"Scanning {url} and checking the links it finds..."
        )
        self._scanning = True
        self._page_url = "" if is_name else normalize_page_url(url)
        self._still_timer.StartOnce(STILL_SCANNING_SECONDS * 1000)
        self._start_cues()

        def _do_scan(**_kwargs: Any) -> Any:
            return self._run_ways(url, self._on_checked)

        self._task_manager.submit(
            "radio-link-finder",
            _do_scan,
            on_success=lambda _op, result: self._on_scan_done(result, None),
            on_failure=lambda _op, exc: self._on_scan_done(None, exc),
        )

    def _on_still_scanning(self, _event: object) -> None:
        # The result and this tick can both be queued: say it only if still true.
        if self._scanning:
            self._announce(STILL_SCANNING)

    def _keep_focus_through_refill(self) -> None:
        """Emptying the list disables the row buttons; move focus off them first."""
        focused = self._wx.Window.FindFocus()
        row_buttons = (self._use_btn, self._add_btn, self._save_btn, self._sort_btn)
        if focused in row_buttons or (focused is self._test_btn and not self._testing):
            self._results.SetFocus()

    def _on_scan_done(self, result: Any, error: BaseException | None) -> None:
        self._scanning = False
        self._still_timer.Stop()
        self._stop_cues()
        if error is not None or result is None:
            self._keep_focus_through_refill()
            self._candidates, self._rows = [], []
            self._list.clear()
            self._enable_row_buttons()
            failed = failure_sentence(error)
            self._status.SetLabel(failed)
            # Said once focus has settled where emptying the list left it.
            self._say_after(failed, self._outcome_sound(failed=True, found=0), show=False)
            return
        how = ""
        if isinstance(result, FoundResult):  # the way that found it, when it is worth saying
            how, result = result.how, result.scan
        self._page_title = result.page_title or self._url_ctrl.GetValue().strip()
        self._favicon_url = result.favicon_url
        candidates: list[PageStreamCandidate] = list(result.candidates)
        counts = scan_counts(result)
        # A new scan clears the filter, so nothing hides its results, and keeps
        # the order, which the sentence then names.
        was_filtered = self._state.filtered
        self._state = view.ViewState(order=self._state.order)
        extra = []
        if (
            candidates
            and self._state.order == view.LISTENERS
            and not view.has_listeners(candidates)
        ):
            extra.append(NO_LISTENER_COUNTS)
            self._state = view.ViewState()  # the order shown is scan order
        elif candidates and self._state.order != view.SCAN:
            extra.append(view.order_sentence(self._state.order))
        if was_filtered:
            extra.append(FILTER_CLEARED)
        if how:
            extra.append(how)
        sentence = " ".join([summary_sentence(candidates, **counts), *extra])
        self._status.SetLabel(" ".join([status_label(candidates, **counts), *extra]))
        if not candidates:
            self._keep_focus_through_refill()
            self._candidates, self._rows = [], []
            self._list.clear()
            self._enable_row_buttons()
            self._forget_last()
            self._say_after(sentence, self._outcome_sound(failed=False, found=0), show=False)
            return
        self._candidates = candidates
        self._rows = view.distinct_rows(candidates)
        self._refill(sentence, keep="", keep_selected=False, show=False)
        # Remembered after the refill, so the list is read first (FUX-04).
        self._address.remember(self._page_url, candidates)
        self._remember_last()
        self._reopen_btn.Enable(True)

    def _refill(
        self, sentence: str, *, keep: str, keep_selected: bool = True, show: bool = True
    ) -> None:
        """Freeze, refill keeping *keep*, thaw, focus the list, then say *sentence*."""
        if self._wx.Window.FindFocus() is self._results and self._sort_btn.IsEnabled():
            # From the context menu: step off the list, so coming back to it
            # reads the row once, after the refill.
            self._sort_btn.SetFocus()
        self.dialog.Freeze()
        try:
            self._list.fill(
                self._candidates,
                self._rows,
                view.visible(self._candidates, self._state),
                keep=keep,
                keep_selected=keep_selected,
            )
            self._enable_row_buttons()
        finally:
            self.dialog.Thaw()
        self._results.SetFocus()
        self._say_after(sentence, show=show)

    # -- buttons that follow the rows --------------------------------------------

    def _enable_row_buttons(self) -> None:
        has_rows = len(self._list) > 0
        count = len(self._list.selected_candidates()) if has_rows else 0
        for button, label in (
            (self._add_btn, menus.add_label(count)),
            (self._save_btn, menus.save_label(count)),
        ):
            if button.GetLabel() != label:
                button.SetLabel(label)
                set_spoken_name(button, label)
            button.Enable(has_rows)
        self._sort_btn.Enable(has_rows)
        focused = self._list.focused() is not None
        # Never strand a playing test behind a disabled button: while testing,
        # the button is the Stop control and must stay reachable.
        self._test_btn.Enable(focused or self._testing)
        self._use_btn.Enable(focused)

    def _on_selection_changed(self, event: Any) -> None:
        if not self._list.quiet:  # Select All and Find run it once, after
            self._enable_row_buttons()
        event.Skip()

    # -- Sort and Filter -----------------------------------------------------------

    def _sort_menu(self) -> Any:
        return menus.sort_menu(self._wx, self._ids, self._candidates, self._state)

    def _on_sort_button(self, _event: object) -> None:
        if not self._candidates:
            return
        menu = self._sort_menu()
        try:
            self.dialog.PopupMenu(menu, self._sort_btn.GetPosition())
        finally:
            menu.Destroy()

    def _apply(self, state: view.ViewState, sentence: str) -> None:
        """Show the list as *state*; a no-op choice repeats its sentence."""
        if state == self._state:
            self._say_after(sentence)
            return
        if not view.visible(self._candidates, state):
            self._say_after(view.empty_filter_sentence(state))
            return
        self._state = state
        focused = self._list.focused()
        self._refill(sentence, keep=focused.url if focused else "")

    def _choose_order(self, order: str) -> None:
        state = view.ViewState(order, self._state.format, self._state.live_only)
        self._apply(state, view.order_sentence(order))

    def _choose_filter(self, fmt: str | None = None, live_only: bool | None = None) -> None:
        state = view.ViewState(
            self._state.order,
            self._state.format if fmt is None else fmt,
            self._state.live_only if live_only is None else live_only,
        )
        shown = len(view.visible(self._candidates, state))
        self._apply(state, view.shown_sentence(shown, len(self._candidates), state))

    # -- the context menu ----------------------------------------------------------

    def _context_menu(self) -> Any:
        return menus.context_menu(
            self._wx,
            self._ids,
            count=len(self._list.targets()),
            testing=self._testing,
            server=bool(self._server_to_scan()),
            submenu=self._sort_menu(),
        )

    def _open_context_menu(self) -> None:
        if not len(self._list):
            return
        menu = self._context_menu()
        try:
            self._results.PopupMenu(menu, self._list.focused_rect())
        finally:
            menu.Destroy()

    def _on_menu(self, event: Any) -> None:
        names = {int(ref): name for name, ref in self._ids.items()}
        name = names.get(event.GetId())
        if name is None:
            event.Skip()
            return
        if name.startswith("order:"):
            self._choose_order(name.split(":", 1)[1])
        elif name.startswith("format:"):
            self._choose_filter(fmt=name.split(":", 1)[1])
        elif name == "live_only":
            self._choose_filter(live_only=not self._state.live_only)
        else:
            self._run(name)

    def _run(self, name: str) -> None:
        commands: dict[str, Callable[[], None]] = {
            "test": lambda: self._on_test(None, from_button=self._testing),
            "use": lambda: self._on_use(None),
            "add": self._add,
            "save": self._save,
            "copy": self._copy,
            "server": lambda: self._wx.CallAfter(self._scan_server),
            "find": self._find,
            "find_next": lambda: self._find_again(backwards=False),
            "find_previous": lambda: self._find_again(backwards=True),
            "select_all": self._select_all,
            "random": lambda: play_random_ui.play_random_stream(self),
        }
        commands[name]()

    # -- keys: in the list only, modifiers matched exactly -----------------------

    def _on_char_hook(self, event: Any) -> None:
        wx = self._wx
        if wx.Window.FindFocus() is not self._results or not len(self._list):
            event.Skip()
            return
        key = menus.key_command(wx, event.GetKeyCode(), event.GetModifiers())
        if key is None:
            event.Skip()
            return
        self._run(key)

    # -- the actions -----------------------------------------------------------------

    def _select_all(self) -> None:
        already = self._list.select_all()  # quietly: the buttons follow once
        self._enable_row_buttons()
        sentence = view.select_all_sentence(already, len(self._list), len(self._candidates))
        self._say_after(sentence)

    def _add(self) -> None:
        outcome = actions.add_to_favorites(
            self._host,
            self._wx,
            self.dialog,
            self._list.targets(),
            page_title=self._page_title,
            favicon=self._favicon_url,
        )
        self._say_after(outcome.sentence, outcome.sound)

    def _save(self) -> None:
        outcome = actions.save_as_playlist(
            self._host, self._wx, self.dialog, self._list.targets(), page_title=self._page_title
        )
        self._say_after(outcome.sentence)

    def _copy(self) -> None:
        from quill.ui.say_commands import set_clipboard_text

        self._say_after(actions.copy_links(self._list.targets(), set_clipboard_text).sentence)

    def _server_to_scan(self) -> str:
        focused = self._list.focused()
        return view.server_to_scan(focused, self._page_url) if focused is not None else ""

    def _scan_server(self) -> None:
        """Put the stream's server in the address field, focus it so the new
        address is read, then scan it like any address."""
        address = self._server_to_scan()
        if not address:
            return
        self._url_ctrl.ChangeValue(address)
        self._url_ctrl.SetFocus()
        self._url_ctrl.SetInsertionPointEnd()
        self._on_scan(None)

    def _on_test(self, _event: object, *, from_button: bool = False) -> None:
        """Test the focused row. While a test plays, the button (or Enter on
        the same row) stops it; Enter on another row tests that row instead."""
        if self._play_selected_tracks():
            return
        candidate = self._list.focused()
        if self._testing and (
            from_button or candidate is None or candidate.url == self._testing_url
        ):
            self._controller.stop()
            self._set_testing(False)
            self._announce("Test stopped.")
            return
        if candidate is None:
            return
        station = actions.station_for(candidate, self._page_title)
        self._controller.play_station(station)
        self._testing_url = candidate.url
        self._set_testing(True)
        self._announce(f"Testing {station.name}.")

    def _set_testing(self, testing: bool) -> None:
        self._testing = testing
        self._test_btn.SetLabel("S&top Test" if testing else "&Test")
        self._test_btn.SetName(
            "Stop the test playback" if testing else "Play the focused stream link now"
        )

    def _on_use(self, _event: object) -> None:
        candidate = self._list.focused()
        if candidate is None:
            return
        station = actions.station_for(
            candidate, self._page_title or "Custom Station", self._favicon_url
        )
        self._host._radio_open_add_custom(station)
