"""Internet Radio > Find Streams from a Website... -- scan one page for links.

Type a website's address; Scan fetches that one page and lists every
candidate stream link it finds (see ``core/radio/link_finder.py`` for what
"finds" means and why this is a fetch-and-parse rather than an embedded
browser). Test plays a candidate through the shared player; "Use This
Link..." hands the chosen URL plus guessed name/homepage to
:class:`~quill.ui.radio.add_station_dialog.AddStationDialog`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.radio.link_finder import PageStreamCandidate, scan_page_for_streams
from quill.core.radio.models import RadioStation
from quill.ui.dialog_contract import apply_modal_ids


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
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_use_link = on_use_link
        self._candidates: list[PageStreamCandidate] = []
        self._page_title = ""
        self._favicon_url = ""

        self.dialog = wx.Dialog(
            parent,
            title="Find Streams from a Website",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((640, 460))
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

        root.Add(wx.StaticText(self.dialog, label="&Candidates found"), 0, wx.LEFT | wx.TOP, 10)
        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Candidate stream links found on the page")
        self._results.InsertColumn(0, "Link", width=340)
        self._results.InsertColumn(1, "Why it was flagged", width=180)
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

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Find Streams from a Website", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------

    def _on_scan(self, _event: object) -> None:
        if self._safe_mode:
            self._status.SetLabel("Finding stream links is disabled in Safe Mode.")
            return
        url = self._url_ctrl.GetValue().strip()
        if not url:
            self._status.SetLabel("Type a website address first.")
            return
        self._status.SetLabel(f"Fetching {url}...")
        self._scan_btn.Enable(False)

        def _do_scan(**_kwargs: Any) -> Any:
            return scan_page_for_streams(url, safe_mode=self._safe_mode)

        self._task_manager.submit(
            "radio-link-finder",
            _do_scan,
            on_success=lambda _op, result: self._on_scan_done(result, None),
            on_failure=lambda _op, exc: self._on_scan_done(None, exc),
        )

    def _on_scan_done(self, result: Any, error: BaseException | None) -> None:
        self._scan_btn.Enable(True)
        if error is not None or result is None:
            self._status.SetLabel(f"Could not scan that page: {error}")
            self._candidates = []
            self._results.DeleteAllItems()
            return
        self._page_title = result.page_title
        self._favicon_url = result.favicon_url
        self._candidates = result.candidates
        self._results.DeleteAllItems()
        for row, candidate in enumerate(self._candidates):
            self._results.InsertItem(row, candidate.url)
            self._results.SetItem(row, 1, candidate.reason)
        if self._candidates:
            self._status.SetLabel(f"{len(self._candidates)} candidate link(s) found.")
            self._results.Select(0)
            self._results.Focus(0)
        else:
            self._status.SetLabel("No stream-shaped links were found on that page.")
        self._announce(self._status.GetLabel())

    def _selected_candidate(self) -> PageStreamCandidate | None:
        index = self._results.GetFirstSelected()
        if 0 <= index < len(self._candidates):
            return self._candidates[index]
        return None

    def _on_result_selected(self, _event: object) -> None:
        has_selection = self._selected_candidate() is not None
        self._test_btn.Enable(has_selection)
        self._use_btn.Enable(has_selection)

    def _on_result_deselected(self, _event: object) -> None:
        self._test_btn.Enable(False)
        self._use_btn.Enable(False)

    def _on_test(self, _event: object) -> None:
        candidate = self._selected_candidate()
        if candidate is None:
            return
        name = candidate.label or self._page_title or candidate.url
        station = RadioStation(name=name, stream_url=candidate.url)
        self._controller.play_station(station)
        self._announce(f"Testing {station.name}")

    def _on_use(self, _event: object) -> None:
        candidate = self._selected_candidate()
        if candidate is None or self._on_use_link is None:
            return
        name = candidate.label or self._page_title or "Custom Station"
        station = RadioStation(
            name=name,
            stream_url=candidate.url,
            favicon=self._favicon_url,
        )
        self._on_use_link(station)
