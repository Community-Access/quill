"""Internet Radio > Find Streams from a Website... -- scan one page for links.

Type a website's address; Scan fetches that one page and lists every
candidate stream link it finds (see ``core/radio/link_finder.py`` for what
"finds" means and why this is a fetch-and-parse rather than an embedded
browser). Test plays a candidate through the shared player; "Use This
Link..." hands the chosen URL plus guessed name/homepage to
:class:`~quill.ui.radio.add_station_dialog.AddStationDialog`.

Each candidate is checked before it is listed (the live check, an idea from
Andre Louis's StreamSift, https://github.com/OnjLouis/StreamSift). The checks
finish inside the scan, so the list is filled once, when everything is known,
and never changes under the listener (FUX-06). Its first column, which a
screen reader reads first, says what each row is ("Live: WXYZ FM, MP3, 128
kbps" or "Not checked: Capital UK, it took too long to answer"), and one sentence says the
result (FUX-04). A scan can now take a while, so Scan stays enabled --
disabling the focused button would drop focus out of the window -- and a press
during a scan, or eight seconds of silence, says once that it is still going.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.find_streams_text import (
    failure_sentence,
    row_status,
    status_label,
    summary_sentence,
)
from quill.core.radio.link_finder import PageStreamCandidate, scan_page_for_streams
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.dpi import dip, dip_size
from quill.ui.surface_lifetime import stop_timer_on_destroy, surface_tasks

#: Silence after Scan before "still scanning" is said, once.
STILL_SCANNING_SECONDS = 8
STILL_SCANNING = "Still scanning the page and checking its links."


class LinkFinderDialog:
    """Scan a website for candidate stream links."""

    def __init__(
        self,
        parent: object,
        *,
        controller: object,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
        on_use_link: Callable[[RadioStation], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._controller = controller
        # Every task this window starts is tied to its lifetime (qc.md F-02).
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "dialog", None))
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_use_link = on_use_link
        self._candidates: list[PageStreamCandidate] = []
        self._page_title = ""
        self._favicon_url = ""
        self._testing = False
        self._scanning = False

        self.dialog = wx.Dialog(
            parent,
            title="Find Streams from a Website",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize(dip_size(self.dialog, 760, 460))
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
        self._url_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._url_ctrl.SetName("The website address to scan for stream links")
        url_row.Add(self._url_ctrl, 1, wx.EXPAND | wx.RIGHT, 6)
        self._scan_btn = wx.Button(self.dialog, label="&Scan")
        self._scan_btn.SetName("Fetch the typed page and scan it for stream links")
        url_row.Add(self._scan_btn, 0)
        root.Add(url_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        root.Add(wx.StaticText(self.dialog, label="St&reams found"), 0, wx.LEFT | wx.TOP, 10)
        self._results = wx.ListCtrl(
            self.dialog, style=wx.LC_REPORT | wx.LC_SINGLE_SEL | wx.BORDER_SIMPLE
        )
        self._results.SetName("Stream links found on the page")
        # The verdict first: it is what a screen reader reads first, and in
        # JAWS's first-column mode the only thing it reads.
        self._results.InsertColumn(0, "Stream", width=dip(self._results, 280))
        self._results.InsertColumn(1, "Link", width=dip(self._results, 300))
        self._results.InsertColumn(2, "Found by", width=dip(self._results, 140))
        root.Add(self._results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.TOP, 8)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._test_btn = wx.Button(self.dialog, label="&Test")
        self._test_btn.SetName("Play the selected candidate link now")
        self._test_btn.Enable(False)
        self._use_btn = wx.Button(self.dialog, label="&Use This Link...")
        self._use_btn.SetName("Use the selected link to add a custom station")
        self._use_btn.Enable(False)
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        close_btn.SetName("Close")
        btn_row.Add(self._test_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._use_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._url_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_scan)
        self._scan_btn.Bind(wx.EVT_BUTTON, self._on_scan)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_result_deselected)
        self._test_btn.Bind(wx.EVT_BUTTON, self._on_test)
        self._use_btn.Bind(wx.EVT_BUTTON, self._on_use)
        # Owned by the dialog, one-shot, and stopped whenever a scan ends.
        self._still_timer = wx.Timer(self.dialog)
        self.dialog.Bind(wx.EVT_TIMER, self._on_still_scanning, self._still_timer)
        stop_timer_on_destroy(self.dialog, self._still_timer)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        # The transport keyboard (transport_keys): testing a found stream is
        # exactly when somebody wants to stop or turn down what is already on.
        from quill.ui.radio import transport_keys

        transport_keys.install(self.dialog, self, wx=self._wx)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Find Streams from a Website", announce=self._announce)
        finally:
            self._scanning = False
            self._still_timer.Stop()
            self.dialog.Destroy()

    # ------------------------------------------------------------------

    def _say(self, text: str) -> None:
        """Show *text* in the status line and say it, once."""
        self._status.SetLabel(text)
        self._announce(text)

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
            self._say("Type a website address first.")
            return
        # Shown, not said: the listener has just pressed Scan.
        self._status.SetLabel(f"Scanning {url} and checking the links it finds...")
        self._scanning = True
        self._still_timer.StartOnce(STILL_SCANNING_SECONDS * 1000)

        def _do_scan(**_kwargs: Any) -> Any:
            return scan_page_for_streams(url, safe_mode=self._safe_mode, check_live=True)

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
        """Emptying the list disables Test and Use. If one of them has focus,
        that would drop focus out of the window, so move it to the list first
        (the spoken result explains what is, or is not, in it)."""
        focused = self._wx.Window.FindFocus()
        if focused is self._use_btn or (focused is self._test_btn and not self._testing):
            self._results.SetFocus()

    def _on_scan_done(self, result: Any, error: BaseException | None) -> None:
        self._scanning = False
        self._still_timer.Stop()
        self._keep_focus_through_refill()
        if error is not None or result is None:
            self._candidates = []
            self._results.DeleteAllItems()
            self._on_result_deselected(None)
            self._say(failure_sentence(error))
            return
        self._page_title = result.page_title
        self._favicon_url = result.favicon_url
        candidates: list[PageStreamCandidate] = list(result.candidates)
        checked = bool(getattr(result, "checked", False))
        left_out = int(getattr(result, "left_out", 0) or 0)
        limit = int(getattr(result, "check_limit", 0) or 0)
        # One list, in one order, for the rows and for what Test and Use act
        # on: the scan already sorted it (live first) and left out non-audio.
        self._candidates = candidates
        self._results.DeleteAllItems()
        for row, candidate in enumerate(candidates):
            self._results.InsertItem(row, row_status(candidate))
            self._results.SetItem(row, 1, candidate.url)
            self._results.SetItem(row, 2, candidate.reason)
        counts = {"checked": checked, "left_out": left_out, "check_limit": limit}
        self._status.SetLabel(status_label(candidates, **counts))
        # The sentence once (FUX-04); the "left out" count stays in the label.
        self._announce(summary_sentence(candidates, **counts))
        if candidates:
            self._select_first_quietly()
        else:
            self._on_result_deselected(None)

    def _select_first_quietly(self) -> None:
        """Select row 0 so Test and Use have a target -- unless the listener is
        already in the list, where a new selection would be read over the
        result sentence; then they arrow to a row themselves."""
        if self._wx.Window.FindFocus() is self._results:
            return
        self._results.Select(0)
        self._results.Focus(0)

    def _selected_candidate(self) -> PageStreamCandidate | None:
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._candidates):
            return self._candidates[index]
        return None

    def _on_result_selected(self, _event: object) -> None:
        has_selection = self._selected_candidate() is not None
        self._test_btn.Enable(has_selection or self._testing)
        self._use_btn.Enable(has_selection)

    def _on_result_deselected(self, _event: object) -> None:
        # Never strand a playing test behind a disabled button: while testing,
        # the button is the Stop control and must stay reachable.
        self._test_btn.Enable(self._testing)
        self._use_btn.Enable(False)

    def _on_test(self, _event: object) -> None:
        # Toggle: while a test plays, the same button reads Stop and stops it.
        if self._testing:
            self._controller.stop()
            self._set_testing(False)
            self._announce("Test stopped.")
            return
        candidate = self._selected_candidate()
        if candidate is None:
            return
        name = candidate.stream_name or candidate.label or self._page_title or candidate.url
        station = RadioStation(name=name, stream_url=candidate.url)
        self._controller.play_station(station)
        self._set_testing(True)
        self._announce(f"Testing {station.name}.")

    def _set_testing(self, testing: bool) -> None:
        self._testing = testing
        self._test_btn.SetLabel("S&top Test" if testing else "&Test")
        self._test_btn.SetName(
            "Stop the test playback" if testing else "Play the selected candidate link now"
        )

    def _on_use(self, _event: object) -> None:
        candidate = self._selected_candidate()
        if candidate is None or self._on_use_link is None:
            return
        # The stream's own name, when the live check heard one, beats a guess.
        name = candidate.stream_name or candidate.label or self._page_title or "Custom Station"
        station = RadioStation(
            name=name,
            stream_url=candidate.url,
            favicon=self._favicon_url,
            codec=candidate.codec if candidate.codec != "HLS" else "",
            bitrate_kbps=candidate.bitrate_kbps,
        )
        self._on_use_link(station)
