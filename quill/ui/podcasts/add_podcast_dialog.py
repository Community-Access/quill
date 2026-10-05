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
from quill.ui.media.list_columns_view import build_columns, columns_for, fill_row
from quill.ui.podcasts.say_status import say_status
from quill.ui.surface_lifetime import surface_tasks


def _apply_backfill(library: Any, show: Any) -> int:
    """Collect this podcast's back catalogue once, if it was asked for (7.2).

    Separate from the automatic download count, which only ever looks forward:
    "fetch the newest 3 from now on" and "when I subscribe, also get the last
    ten" are different questions, and until now only Always Sync -- meaning
    *everything* -- answered the second.

    A one-off, at the one moment it can be: subscribing. It marks episodes for
    download and never plays, queues or deletes anything, and a podcast whose
    setting says "nothing" (the default, and every existing subscription) does
    exactly what it did before.
    """
    try:
        from quill.core.podcasts.show_policy import backfill_episodes

        wanted = backfill_episodes(library, show, show.episodes)
    except Exception:  # noqa: BLE001 - a backfill must never break subscribing
        return 0
    for episode in wanted:
        if not episode.downloaded_path and episode.mode_override != "stream":
            episode.mode_override = "download"
    return len(wanted)


class AddPodcastWindow:
    """Search a directory, add a feed URL, or import OPML -- a peer window.

    Made once (qc.md Phase 4): Follow keeps it open for the next podcast, and
    asking for it again raises it with its results as you left them.
    """

    TITLE = "Add Podcast"
    MENU_TITLE = "Add Pod&cast"

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
        # Every task this window starts is tied to its lifetime (qc.md F-02).
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "frame", None))
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        #: Land the cursor on a show already in the library (11.6). Returns
        #: whether it could; None where there is no list to move in.
        self._on_reveal_show = on_reveal_show
        self._search_results: list[itunes_search.PodcastSearchResult] = []

        self.frame = wx.Frame(parent, title="Add Podcast", size=(760, 620))
        self.frame.SetMinSize((640, 520))
        panel = wx.Panel(self.frame, style=wx.TAB_TRAVERSAL)
        root = wx.BoxSizer(wx.VERTICAL)

        search_box = wx.StaticBoxSizer(wx.VERTICAL, panel, "Find a Podcast in a Directory")
        source_row = wx.BoxSizer(wx.HORIZONTAL)
        source_row.Add(
            wx.StaticText(panel, label="&Directory:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            6,
        )
        self._source_choice = wx.Choice(
            panel, choices=[label for _sid, label in directory_search.SOURCE_LABELS]
        )
        self._source_choice.SetHelpText(
            "Which directory to look in. iTunes needs nothing. Podcast Index "
            "carries the extra Podcasting 2.0 information -- chapters, "
            "transcripts -- and needs a key you add with Podcast Index Credentials."
        )
        self._source_choice.SetSelection(self._source_index())
        source_row.Add(self._source_choice, 1, wx.ALL | wx.EXPAND, 6)
        search_box.Add(source_row, 0, wx.EXPAND)
        query_row = wx.BoxSizer(wx.HORIZONTAL)
        # A real StaticText, not only SetName. On wxMSW the accessible name of
        # a plain text field comes from the static text preceding it in
        # z-order; SetName sets wxWindow's own name and the reader never sees
        # it. This field announced as bare "edit" for that reason (reported
        # 2026-09-30), while the Directory combo box above -- which has a
        # label -- announced correctly. Created before the field, because the
        # association is by creation order and not by sizer position.
        query_row.Add(
            wx.StaticText(panel, label="Podcast &name:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            6,
        )
        self._query_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._query_ctrl.SetName("Podcast name to find")
        self._query_ctrl.SetHelpText(
            "Type part of a podcast's name and press Enter, or choose Find Podcasts. "
            "The chosen directory is searched, and nothing is followed to "
            "until you say so."
        )
        query_row.Add(self._query_ctrl, 1, wx.ALL | wx.EXPAND, 6)
        self._search_btn = wx.Button(panel, label="Find Podcast&s")
        self._search_btn.SetHelpText("Finds podcasts matching this name in the chosen directory")
        query_row.Add(self._search_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        search_box.Add(query_row, 0, wx.EXPAND)
        root.Add(search_box, 0, wx.EXPAND | wx.ALL, 10)

        # The list needs the same treatment as the two fields above: a real
        # heading created immediately before it, because the association is by
        # creation order and not by sizer position. "Search results" was only a
        # SetName, which wxMSW never hands to the reader.
        root.Add(wx.StaticText(panel, label="&Results:"), 0, wx.LEFT | wx.RIGHT, 10)
        self._results = wx.ListCtrl(panel, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._results.SetHelpText(
            "Podcasts the chosen directory matched. Enter previews the one you "
            "are on; Follow adds it to your library."
        )
        # Subscriptions > Choose Columns... owns which columns exist and in
        # what order -- a report row is read out column by column.
        self._columns: list[ColumnDef] = columns_for("cast", DIRECTORY_RESULTS.id)
        build_columns(self._results, self._columns)
        root.Add(self._results, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        result_row = wx.BoxSizer(wx.HORIZONTAL)
        # Preview first, and it is what Enter does: subscribing from a title
        # alone is the thing that produces regret, and a title is all a search
        # result shows.
        self._preview_btn = wx.Button(panel, label="&Preview...")
        self._preview_btn.SetHelpText("Look at this podcast before following it")
        self._preview_btn.Enable(False)
        # Follow, not Subscribe. Every podcast app a listener has used in
        # the last five years says Follow, and "subscribe" now reads as
        # something with a price attached -- the wrong thing to suggest
        # about a free app adding a free feed. The label alternates with
        # the selected row (see _refresh_follow_button).
        from quill.ui.podcasts.add_podcast_actions import FOLLOW_LABEL

        self._subscribe_btn = wx.Button(panel, label=FOLLOW_LABEL)
        self._subscribe_btn.SetName(
            "Follow the selected podcast, or stop following it if you already do"
        )
        self._subscribe_btn.SetHelpText(
            "Adds the selected podcast to your library. If you already follow "
            "it, this button says Unfollow instead and asks before removing "
            "anything."
        )
        self._subscribe_btn.Enable(False)
        result_row.Add(self._preview_btn, 0, wx.RIGHT, 6)
        result_row.Add(self._subscribe_btn, 0)
        root.Add(result_row, 0, wx.ALL, 10)

        url_box = wx.StaticBoxSizer(wx.HORIZONTAL, panel, "Add by Feed URL")
        # Labelled for the same reason as the search field above it.
        url_box.Add(
            wx.StaticText(panel, label="&Feed address:"),
            0,
            wx.ALIGN_CENTER_VERTICAL | wx.ALL,
            6,
        )
        self._url_ctrl = wx.TextCtrl(panel, style=wx.TE_PROCESS_ENTER)
        self._url_ctrl.SetName("The podcast's RSS feed URL")
        self._url_ctrl.SetHelpText(
            "Paste a podcast's feed address here when you already have it, then "
            "press Enter or choose Add. Both http and https addresses work."
        )
        url_box.Add(self._url_ctrl, 1, wx.ALL | wx.EXPAND, 6)
        self._add_url_btn = wx.Button(panel, label="&Add")
        self._add_url_btn.SetHelpText("Follow the podcast at this feed address")
        url_box.Add(self._add_url_btn, 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6)
        root.Add(url_box, 0, wx.EXPAND | wx.ALL, 10)

        self._status = wx.StaticText(panel, label="")
        self._status.SetName("Status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        import_btn = wx.Button(panel, label="&Import OPML...")
        import_btn.SetHelpText("Import a whole subscription list from an OPML file")
        close_btn = wx.Button(panel, label="Close")
        close_btn.SetHelpText("Closes this window and returns to where you were.")
        from quill.ui.dialog_contract import bind_close_button

        bind_close_button(self.frame, close_btn, modeless=True)
        btn_row.Add(import_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        self.frame.CentreOnParent()

        self._query_ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_search)
        self._search_btn.Bind(wx.EVT_BUTTON, self._on_search)
        self._results.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_result_selected)
        self._results.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_result_deselected)
        self._subscribe_btn.Bind(wx.EVT_BUTTON, self._on_subscribe_selected)
        self._preview_btn.Bind(wx.EVT_BUTTON, self._on_preview_selected)
        # Enter on a result previews rather than subscribing.
        self._results.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_preview_selected)
        # Both routes to the row menu. EVT_CONTEXT_MENU is the keyboard one
        # (Applications key, Shift+F10) and is the one that matters here.
        self._results.Bind(wx.EVT_CONTEXT_MENU, self._on_results_context_menu)
        self._results.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_results_context_menu)
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
        self._refresh_follow_button()
        say_status(self._status, "", speak=False)
        self._announce("Find cleared.")

    def prefill_address(self, address: str) -> None:
        """Ctrl+N with a web address on the clipboard: it is filled in, with the
        cursor on it, so following is one Enter (qc.md section 18 item 8)."""
        self._url_ctrl.SetValue(address)
        # Spoken when the window has opened (show), not now, behind it.
        say_status(
            self._status,
            "The address on your clipboard is filled in. Press Enter to follow it.",
            speak=False,
        )
        self._prefilled = True

    def focus_target(self) -> Any:
        return self._url_ctrl if getattr(self, "_prefilled", False) else self._query_ctrl

    def land_on_prefill(self) -> None:
        """After a prefill: the cursor on the address, and the status said."""
        if getattr(self, "_prefilled", False):
            self._url_ctrl.SetFocus()
            self._url_ctrl.SelectAll()
            self._announce(self._status.GetLabel())
            self._prefilled = False

    # ------------------------------------------------------------------
    # Search

    def _on_search(self, _event: object) -> None:
        if self._safe_mode:
            say_status(self._status, "Finding podcasts is disabled in Safe Mode.", self._announce)
            return
        query = self._query_ctrl.GetValue().strip()
        if not query:
            say_status(self._status, "Type a podcast name to find.", self._announce)
            return
        source = directory_search.SOURCES[self._source_choice.GetSelection()]
        say_status(self._status, "Searching...", self._announce)
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
            say_status(self._status, f"Find failed: {error}", self._announce)
            return
        from quill.ui.podcasts.add_podcast_actions import following_cell

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
                    "following": following_cell(self._library, result.feed_url),
                },
            )
        # One sentence that names the directories and any that did not answer:
        # "12 results" from an unknown source is what makes somebody wonder
        # whether the other one was asked at all.
        said = found.summary()
        say_status(self._status, said, self._announce)
        if results:
            self._results.Select(0)
            self._results.Focus(0)

    def _on_result_selected(self, _event: object) -> None:
        self._subscribe_btn.Enable(True)
        self._preview_btn.Enable(True)
        self._refresh_follow_button()

    def _on_result_deselected(self, _event: object) -> None:
        self._subscribe_btn.Enable(False)
        self._preview_btn.Enable(False)

    def _selected_result(self) -> object | None:
        """The result row the cursor is on, or None."""
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._search_results)):
            return None
        return self._search_results[index]

    def _refresh_follow_button(self) -> None:
        from quill.ui.podcasts.add_podcast_actions import refresh_follow_button

        refresh_follow_button(self)

    def _on_results_context_menu(self, event: object) -> None:
        """The row's own menu. Bound to EVT_CONTEXT_MENU as well as the
        right-click, so the Applications key and Shift+F10 reach it -- which
        is how it will usually be opened here."""
        from quill.ui.podcasts.add_podcast_actions import open_context_menu

        open_context_menu(self, self._results.GetFirstSelected())
        if hasattr(event, "Skip"):
            event.Skip(False)

    def _on_preview_selected(self, _event: object = None) -> None:
        """Look at the selected show before committing to it (C2)."""
        index = self._results.GetFirstSelected()
        if not (0 <= index < len(self._search_results)):
            return
        from quill.ui.podcasts.preview_command import preview_search_result

        preview_search_result(self, self._search_results[index], index)

    def _on_subscribe_selected(self, _event: object = None) -> None:
        """Kept as the button's bound name; the verb is decided below."""
        self._on_follow_action()

    def _on_follow_action(self) -> None:
        from quill.ui.podcasts.add_podcast_actions import follow_action

        follow_action(self)

    def _refresh_row_following(self, index: int, feed_url: str) -> None:
        from quill.ui.podcasts.add_podcast_actions import refresh_row_following

        refresh_row_following(self, index, feed_url)

    # ------------------------------------------------------------------
    # Add by URL

    def _on_add_url(self, _event: object) -> None:
        url = self._url_ctrl.GetValue().strip()
        if not url:
            say_status(self._status, "Type a feed URL first.", self._announce)
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
            say_status(self._status, "Adding podcasts is disabled in Safe Mode.", self._announce)
            return
        existing = self._library.find_show_by_feed_url(feed_url)
        if existing is not None:
            self._say_already_have(existing)
            return
        say_status(self._status, f"Fetching {title_hint or feed_url}...", self._announce)

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
            say_status(self._status, f"Could not follow it: {error}", self._announce)
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
        backfilled = _apply_backfill(self._library, show)
        # The fuller sentence (with the back-catalogue) is spoken below.
        say_status(
            self._status,
            f"Now following {show.title} ({len(show.episodes)} episodes).",
            speak=False,
        )
        from quill.core.podcasts.follow_words import followed

        message = followed(show.title)
        if backfilled:
            message += (
                f"; {backfilled} back-catalogue episode"
                f"{'' if backfilled == 1 else 's'} queued for download"
            )
        from quill.ui.outcome_report import report_outcome

        report_outcome(self, "Follow", message, object_name=show.title)
        self._url_ctrl.SetValue("")
        self._return_focus_to_results(result_index)

    def _say_already_have(self, show: Any) -> None:
        """Name the show you already follow, and go to it if we can (11.6).

        The status label alone was not enough: a StaticText that changes is
        silent to a screen reader, so "You're already followed to that feed"
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
        say_status(self._status, sentence, self._announce)

    def _return_focus_to_results(self, result_index: int | None) -> None:
        """After subscribing from a search result, put focus back on the list.

        Only applies to the iTunes-search path (``result_index`` set); the
        Add-by-Feed-URL path leaves focus alone so the URL box stays put. The
        just-followed row is re-selected and focused so a screen-reader user
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
            self.frame,
            username=last_username,
            message=message,
            announce_cb=self._announce,
        ).show()
        if result is None or result.action != "save":
            say_status(
                self._status,
                "That feed requires a sign-in. Add it again when you have the credentials.",
                self._announce,
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
            self.frame,
            "Import OPML",
            wildcard="OPML files (*.opml;*.xml)|*.opml;*.xml|All files (*.*)|*.*",
            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST,
        ) as dialog:  # dialog_button_contract: exempt
            if dialog.ShowModal() != wx.ID_OK:
                return
            path = Path(dialog.GetPath())
        importer = OpmlImportDialog(
            self.frame,
            library=self._library,
            path=path,
            task_manager=self._task_manager,
            safe_mode=self._safe_mode,
            announce_cb=self._announce,
            on_library_changed=self._on_library_changed,
        )
        importer.show()
        # The import window has already said what it imported.
        say_status(self._status, f"Finished importing {path.name}.", speak=False)
