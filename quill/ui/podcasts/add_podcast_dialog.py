"""Tools > Media > Podcasts > Add Podcast... -- search, feed URL, OPML.

Three entry points in one dialog: iTunes search (network, explicit Search
action), Add by Feed URL (any RSS URL, including shows iTunes doesn't
index), and Import OPML... (a whole subscription list at once). Stays open
after a successful add so several podcasts can be added in one session;
Close ends it.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.core.podcasts import feed_reader, itunes_search
from quill.core.podcasts import opml as opml_module
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id
from quill.ui.dialog_contract import apply_modal_ids


class AddPodcastDialog:
    """Search iTunes, add a feed URL directly, or import an OPML file."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._search_results: list[itunes_search.PodcastSearchResult] = []

        self.dialog = wx.Dialog(
            parent, title="Add Podcast", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, "Search iTunes")
        self._query_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._query_ctrl.SetName("Podcast name to search for")
        search_box.Add(self._query_ctrl, 1, wx.ALL | wx.EXPAND, 6)
        self._search_btn = wx.Button(self.dialog, label="&Search")
        self._search_btn.SetName("Search iTunes for podcasts matching this name")
        search_box.Add(self._search_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        root.Add(search_box, 0, wx.EXPAND | wx.ALL, 10)

        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Search results")
        self._results.InsertColumn(0, "Title", width=320)
        self._results.InsertColumn(1, "Artist/Network", width=220)
        root.Add(self._results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._subscribe_btn = wx.Button(self.dialog, label="Su&bscribe to Selected")
        self._subscribe_btn.Enable(False)
        root.Add(self._subscribe_btn, 0, wx.ALL, 10)

        url_box = wx.StaticBoxSizer(wx.HORIZONTAL, self.dialog, "Add by Feed URL")
        self._url_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._url_ctrl.SetName("The podcast's RSS feed URL")
        url_box.Add(self._url_ctrl, 1, wx.ALL | wx.EXPAND, 6)
        self._add_url_btn = wx.Button(self.dialog, label="&Add")
        self._add_url_btn.SetName("Subscribe using this feed URL")
        url_box.Add(self._add_url_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        root.Add(url_box, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(self.dialog, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        import_btn = wx.Button(self.dialog, label="&Import OPML...")
        import_btn.SetName("Import a whole subscription list from an OPML file")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(import_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._query_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_result_deselected)
        self._subscribe_btn.Bind(wx.EVT_BUTTON, self._on_subscribe_selected)
        self._url_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_add_url)
        self._add_url_btn.Bind(wx.EVT_BUTTON, self._on_add_url)
        import_btn.Bind(wx.EVT_BUTTON, self._on_import_opml)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Add Podcast", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # ------------------------------------------------------------------
    # Search

    def _on_search(self, _event: object) -> None:
        if self._safe_mode:
            self._status.SetLabel("Podcast search is disabled in Safe Mode.")
            return
        query = self._query_ctrl.GetValue().strip()
        if not query:
            self._status.SetLabel("Type a podcast name to search for.")
            return
        self._status.SetLabel("Searching iTunes...")
        self._search_btn.Enable(False)

        def _do_search(**_kwargs: Any) -> list[itunes_search.PodcastSearchResult]:
            return itunes_search.search_podcasts(query, safe_mode=self._safe_mode)

        self._task_manager.submit(
            "podcast-search",
            _do_search,
            on_success=lambda _op, results: self._on_search_done(results, None),
            on_failure=lambda _op, exc: self._on_search_done([], exc),
        )

    def _on_search_done(
        self, results: list[itunes_search.PodcastSearchResult], error: BaseException | None
    ) -> None:
        self._search_btn.Enable(True)
        if error is not None:
            self._status.SetLabel(f"Search failed: {error}")
            return
        self._search_results = results
        self._results.DeleteAllItems()
        for row, result in enumerate(results):
            self._results.InsertItem(row, result.title)
            self._results.SetItem(row, 1, result.artist)
        self._status.SetLabel(f"{len(results)} result(s).")
        self._announce(f"{len(results)} search results")
        if results:
            self._results.Select(0)
            self._results.Focus(0)

    def _on_result_selected(self, _event: object) -> None:
        self._subscribe_btn.Enable(True)

    def _on_result_deselected(self, _event: object) -> None:
        self._subscribe_btn.Enable(False)

    def _on_subscribe_selected(self, _event: object) -> None:
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._search_results)):
            return
        result = self._search_results[index]
        self._subscribe_to_feed(result.feed_url, title_hint=result.title)

    # ------------------------------------------------------------------
    # Add by URL

    def _on_add_url(self, _event: object) -> None:
        url = self._url_ctrl.GetValue().strip()
        if not url:
            self._status.SetLabel("Type a feed URL first.")
            return
        self._subscribe_to_feed(url)

    def _subscribe_to_feed(self, feed_url: str, *, title_hint: str = "") -> None:
        if self._safe_mode:
            self._status.SetLabel("Adding podcasts is disabled in Safe Mode.")
            return
        if self._library.find_show_by_feed_url(feed_url) is not None:
            self._status.SetLabel("You're already subscribed to that feed.")
            return
        self._status.SetLabel(f"Fetching {title_hint or feed_url}...")

        def _do_fetch(**_kwargs: Any) -> feed_reader.FeedInfo:
            return feed_reader.fetch_and_parse_feed(feed_url, safe_mode=self._safe_mode)

        self._task_manager.submit(
            "podcast-subscribe",
            _do_fetch,
            on_success=lambda _op, info: self._on_fetch_done(feed_url, info, None),
            on_failure=lambda _op, exc: self._on_fetch_done(feed_url, None, exc),
        )

    def _on_fetch_done(
        self, feed_url: str, info: feed_reader.FeedInfo | None, error: BaseException | None
    ) -> None:
        if error is not None or info is None:
            self._status.SetLabel(f"Could not subscribe: {error}")
            return
        show = PodcastShow(
            id=new_id(),
            title=info.title or feed_url,
            feed_url=feed_url,
            homepage=info.homepage,
            artwork_url=info.artwork_url,
            episodes=info.episodes,
        )
        added = self._library.add_show(show)
        if not added:
            self._status.SetLabel("You're already subscribed to that feed.")
            return
        self._on_library_changed()
        self._status.SetLabel(f"Subscribed to {show.title} ({len(show.episodes)} episodes).")
        self._announce(f"Subscribed to {show.title}")
        self._url_ctrl.SetValue("")

    # ------------------------------------------------------------------
    # OPML import

    def _on_import_opml(self, _event: object) -> None:
        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Import OPML",
            wildcard="OPML files (*.opml;*.xml)|*.opml;*.xml|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = dialog.GetPath()
        try:
            with open(path, encoding="utf-8", errors="replace") as handle:
                text = handle.read()
        except OSError as error:
            self._status.SetLabel(f"Could not read that file: {error}")
            return
        try:
            added, skipped = opml_module.import_opml(self._library, text)
        except opml_module.OpmlError as error:
            self._status.SetLabel(str(error))
            return
        self._on_library_changed()
        self._status.SetLabel(f"Imported {len(added)} podcast(s); {skipped} already subscribed.")
        self._announce(self._status.GetLabel())
