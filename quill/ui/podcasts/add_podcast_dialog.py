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

from quill.core.media.list_columns import ColumnDef
from quill.core.podcasts import directory_search, feed_reader, itunes_search
from quill.core.podcasts.list_columns import DIRECTORY_RESULTS
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.subscriptions import PodcastLibrary, new_id
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.media.list_columns_view import build_columns, columns_for, fill_row


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
        on_reveal_show: Callable[[str], bool] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        #: Land the cursor on a show already in the library (11.6). Returns
        #: whether it could; None where there is no list to move in.
        self._on_reveal_show = on_reveal_show
        self._search_results: list[itunes_search.PodcastSearchResult] = []

        self.dialog = wx.Dialog(
            parent, title="Add Podcast", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((640, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.VERTICAL, self.dialog, "Search a Podcast Directory")
        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(
            wx.StaticText(self.dialog, label="&Directory:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            6,
        )
        self._source_choice = wx.Choice(
            self.dialog, choices=[label for _sid, label in directory_search.SOURCE_LABELS]
        )
        self._source_choice.SetName(
            "Which directory to search. iTunes needs nothing. Podcast Index "
            "carries the extra Podcasting 2.0 information -- chapters, "
            "transcripts -- and needs a key you add in Podcast Settings."
        )
        self._source_choice.SetSelection(self._source_index())
        source_row.Add(self._source_choice, 1, wx.ALL | wx.EXPAND, 6)
        search_box.Add(source_row, 0, wx.EXPAND)
        query_row = wx.BoxSizer(wx.HORIZONTAL)
        self._query_ctrl = wx.TextCtrl(self.dialog, style=wx.TE_PROCESS_ENTER)
        self._query_ctrl.SetName("Podcast name to search for")
        query_row.Add(self._query_ctrl, 1, wx.ALL | wx.EXPAND, 6)
        self._search_btn = wx.Button(self.dialog, label="&Search")
        self._search_btn.SetName("Search the chosen directory for podcasts matching this name")
        query_row.Add(self._search_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        search_box.Add(query_row, 0, wx.EXPAND)
        root.Add(search_box, 0, wx.EXPAND | wx.ALL, 10)

        self._results = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetName("Search results")
        # Subscriptions > Choose Columns... owns which columns exist and in
        # what order -- a report row is read out column by column.
        self._columns: list[ColumnDef] = columns_for("cast", DIRECTORY_RESULTS.id)
        build_columns(self._results, self._columns)
        root.Add(self._results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        result_row = wx.BoxSizer(wx.HORIZONTAL)
        # Preview first, and it is what Enter does: subscribing from a title
        # alone is the thing that produces regret, and a title is all a search
        # result shows.
        self._preview_btn = wx.Button(self.dialog, label="&Preview...")
        self._preview_btn.SetName("Look at this podcast before subscribing to it")
        self._preview_btn.Enable(False)
        self._subscribe_btn = wx.Button(self.dialog, label="Su&bscribe to Selected")
        self._subscribe_btn.Enable(False)
        result_row.Add(self._preview_btn, 0, wx.RIGHT, 6)
        result_row.Add(self._subscribe_btn, 0)
        root.Add(result_row, 0, wx.ALL, 10)

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
        self._preview_btn.Bind(wx.EVT_BUTTON, self._on_preview_selected)
        # Enter on a result previews rather than subscribing.
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_preview_selected)
        self._url_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_add_url)
        self._add_url_btn.Bind(wx.EVT_BUTTON, self._on_add_url)
        import_btn.Bind(wx.EVT_BUTTON, self._on_import_opml)
        from quill.ui.search_reset import bind_empty_query_reset

        bind_empty_query_reset(self._query_ctrl, self._reset_search_results)

    def _reset_search_results(self) -> None:
        """Emptying the search field empties the results list."""
        if not self._search_results:
            return
        self._search_results = []
        self._results.DeleteAllItems()
        self._subscribe_btn.Enable(False)
        self._status.SetLabel("")
        self._announce("Search cleared.")

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
        source = directory_search.SOURCES[self._source_choice.GetSelection()]
        self._status.SetLabel("Searching...")
        self._search_btn.Enable(False)
        from quill.ui.podcasts.preview_command import podcast_index_credentials

        key, secret = podcast_index_credentials()

        def _do_search(**_kwargs: Any) -> directory_search.DirectorySearch:
            return directory_search.search(
                query, source=source, key=key, secret=secret, safe_mode=self._safe_mode
            )

        self._task_manager.submit(
            "podcast-search",
            _do_search,
            on_success=lambda _op, found: self._on_search_done(found, None),
            on_failure=lambda _op, exc: self._on_search_done(None, exc),
        )

    def _source_index(self) -> int:
        """Which directory the library last chose (both, when it has not)."""
        settings = getattr(self._library, "settings", None)
        wanted = str(getattr(settings, "directory_source", "both") or "both")
        return directory_search.SOURCES.index(wanted) if wanted in directory_search.SOURCES else 0

    def _on_search_done(
        self, found: directory_search.DirectorySearch | None, error: BaseException | None
    ) -> None:
        self._search_btn.Enable(True)
        if error is not None or found is None:
            self._status.SetLabel(f"Search failed: {error}")
            return
        results = found.results
        self._search_results = results
        self._results.DeleteAllItems()
        for row, result in enumerate(results):
            fill_row(
                self._results,
                row,
                self._columns,
                {
                    "title": result.title,
                    "artist": result.artist,
                    "feed": result.feed_url,
                },
            )
        # One sentence that names the directories and any that did not answer:
        # "12 results" from an unknown source is what makes somebody wonder
        # whether the other one was asked at all.
        said = found.summary()
        self._status.SetLabel(said)
        self._announce(said)
        if results:
            self._results.Select(0)
            self._results.Focus(0)

    def _on_result_selected(self, _event: object) -> None:
        self._subscribe_btn.Enable(True)
        self._preview_btn.Enable(True)

    def _on_result_deselected(self, _event: object) -> None:
        self._subscribe_btn.Enable(False)
        self._preview_btn.Enable(False)

    def _on_preview_selected(self, _event: object = None) -> None:
        """Look at the selected show before committing to it (C2)."""
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._search_results)):
            return
        from quill.ui.podcasts.preview_command import preview_search_result

        preview_search_result(self, self._search_results[index], index)

    def _on_subscribe_selected(self, _event: object) -> None:
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._search_results)):
            return
        result = self._search_results[index]
        self._subscribe_to_feed(result.feed_url, title_hint=result.title, result_index=index)

    # ------------------------------------------------------------------
    # Add by URL

    def _on_add_url(self, _event: object) -> None:
        url = self._url_ctrl.GetValue().strip()
        if not url:
            self._status.SetLabel("Type a feed URL first.")
            return
        self._subscribe_to_feed(url)

    def _subscribe_to_feed(
        self,
        feed_url: str,
        *,
        title_hint: str = "",
        result_index: int | None = None,
        username: str = "",
        password: str = "",
    ) -> None:
        if self._safe_mode:
            self._status.SetLabel("Adding podcasts is disabled in Safe Mode.")
            return
        existing = self._library.find_show_by_feed_url(feed_url)
        if existing is not None:
            self._say_already_have(existing)
            return
        self._status.SetLabel(f"Fetching {title_hint or feed_url}...")

        def _do_fetch(**_kwargs: Any) -> feed_reader.FeedInfo:
            return feed_reader.fetch_and_parse_feed(
                feed_url, username=username, password=password, safe_mode=self._safe_mode
            )

        self._task_manager.submit(
            "podcast-subscribe",
            _do_fetch,
            on_success=lambda _op, info: self._on_fetch_done(
                feed_url, info, None, result_index, username=username, password=password
            ),
            on_failure=lambda _op, exc: self._on_fetch_done(
                feed_url, None, exc, result_index, username=username, password=password
            ),
        )

    def _on_fetch_done(
        self,
        feed_url: str,
        info: feed_reader.FeedInfo | None,
        error: BaseException | None,
        result_index: int | None = None,
        *,
        username: str = "",
        password: str = "",
    ) -> None:
        if isinstance(error, feed_reader.FeedAuthError):
            self._prompt_for_credentials(feed_url, last_username=username)
            return
        if error is not None or info is None:
            self._status.SetLabel(f"Could not subscribe: {error}")
            self._return_focus_to_results(result_index)
            return
        show = PodcastShow(
            id=new_id(),
            title=info.title or feed_url,
            feed_url=feed_url,
            homepage=info.homepage,
            artwork_url=info.artwork_url,
            feed_username=username,
            tags=info.tags,
            episodes=info.episodes,
        )
        added = self._library.add_show(show)
        if not added:
            existing = self._library.find_show_by_feed_url(feed_url)
            self._say_already_have(existing or show)
            self._return_focus_to_results(result_index)
            return
        if username and password:
            from quill.core.podcasts import feed_auth

            feed_auth.save_feed_password(show.id, password)
        self._on_library_changed()
        self._status.SetLabel(f"Subscribed to {show.title} ({len(show.episodes)} episodes).")
        self._announce(f"Subscribed to {show.title}")
        self._url_ctrl.SetValue("")
        self._return_focus_to_results(result_index)

    def _say_already_have(self, show: Any) -> None:
        """Name the show you already follow, and go to it if we can (11.6).

        The status label alone was not enough: a StaticText that changes is
        silent to a screen reader, so "You're already subscribed to that feed"
        was, in practice, nothing happening. It is announced now, it names the
        show rather than "that feed", and where the Podcast Manager is open
        behind this dialog the cursor lands on the row you already have.
        """
        from quill.core import duplicate_add

        title = str(getattr(show, "title", "") or "that podcast")
        moved = False
        reveal = self._on_reveal_show
        if reveal is not None:
            try:
                moved = bool(reveal(str(getattr(show, "id", "") or "")))
            except Exception:  # noqa: BLE001 - a reveal that fails is not fatal
                moved = False
        sentence = duplicate_add.already_have("podcast", title, moved=moved)
        self._status.SetLabel(sentence)
        self._announce(sentence)

    def _return_focus_to_results(self, result_index: int | None) -> None:
        """After subscribing from a search result, put focus back on the list.

        Only applies to the iTunes-search path (``result_index`` set); the
        Add-by-Feed-URL path leaves focus alone so the URL box stays put. The
        just-subscribed row is re-selected and focused so a screen-reader user
        can keep arrowing through results without hunting for the list again.
        """
        if result_index is None:
            return
        count = self._results.GetItemCount()
        if count == 0:
            return
        target = max(0, min(result_index, count - 1))
        self._results.Select(target)
        self._results.Focus(target)
        self._results.SetFocus()

    def _prompt_for_credentials(self, feed_url: str, *, last_username: str) -> None:
        """A 401/403 lands here: ask for credentials and retry the subscribe.
        Wrong credentials come straight back (the retry 401s again), with the
        username kept so only the password needs re-typing."""
        from quill.ui.podcasts.feed_credentials_dialog import FeedCredentialsDialog

        message = "The username or password was not accepted. Try again." if last_username else ""
        result = FeedCredentialsDialog(
            self.dialog,
            username=last_username,
            message=message,
            announce_cb=self._announce,
        ).show()
        if result is None or result.action != "save":
            self._status.SetLabel(
                "That feed requires a sign-in. Add it again when you have the credentials."
            )
            return
        self._subscribe_to_feed(feed_url, username=result.username, password=result.password)

    # ------------------------------------------------------------------
    # OPML import

    def _on_import_opml(self, _event: object) -> None:
        """Hand a chosen OPML file to the bulk-import flow.

        The whole import runs there, off the UI thread: a real subscription
        list is thousands of entries, and reading, planning, adding, and
        optionally checking every feed is not work to do inside a button
        handler. See ``opml_import_dialog.py``.
        """
        from pathlib import Path

        from quill.ui.podcasts.opml_import_dialog import OpmlImportDialog

        wx = self._wx
        with wx.FileDialog(
            self.dialog,
            "Import OPML",
            wildcard="OPML files (*.opml;*.xml)|*.opml;*.xml|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        importer = OpmlImportDialog(
            self.dialog,
            library=self._library,
            path=path,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_library_changed=self._on_library_changed,
        )
        importer.show()
        self._status.SetLabel(f"Finished importing {path.name}.")
