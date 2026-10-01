"""Feed Check: which of your podcasts are healthy, and which need something (R2).

Cast has always known this. ``core/podcasts/check_state.py`` records, per podcast,
when it was last read, how many checks have failed in a row and when it last carried
something new -- and it uses those facts to decide when to check and when to speak.
What it never did was let anybody **ask**.

That asymmetry is the whole reason this window exists. The notices are latched: a
failing feed says so once per run of failures, a quiet one once per silence. That is
right for an app that must not nag, and useless to somebody who heard something a
week ago and now wants to know what is going on. "Which of my sixty podcasts is
broken" had no answer at all except re-subscribing to each one and watching.

The report itself is ``core/podcasts/feed_health.py``, wx-free and tested, so what is
here is a window and nothing more. **Opening it checks nothing** -- no new network
code, and Retry is the refresh Cast already has.

Four decisions in the window worth naming:

* **Worst first**, which the report decides, not this. A list sorted by title is one
  you read all of; a list sorted by trouble is one you read the top of, and a
  screen-reader user pays for every row.
* **Every label is constructed before the control it names.** On wxMSW that ordering
  *is* the accessible name -- see ``quill/tools/check_control_labels.py`` for the
  class of bug this avoids.
* **A context menu, on the Applications key and Shift+F10 as well as the right
  click**, because on a list that is where a keyboard user looks for what a row can
  do.
* **Retry says what it found**, per feed, rather than only refreshing. A button that
  silently does the thing the app does in the background anyway is a button nobody
  can tell worked.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from quill.ui.dialog_contract import apply_modal_ids

__all__ = ["FeedCheckDialog", "open_feed_check"]

_COLUMNS: tuple[tuple[str, int], ...] = (
    # Status second, not last. The row is read out column by column, and a
    # listener scanning for trouble should meet the verdict before three dates.
    ("Podcast", 240),
    ("Status", 260),
    ("Last checked", 130),
    ("Last new episode", 140),
)


class FeedCheckDialog:
    """The report, as a list with four actions."""

    def __init__(
        self,
        parent: Any,
        *,
        library: Any,
        announce: Callable[[str], None],
        retry: Callable[[str], None],
        safe_mode: bool = False,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._announce = announce
        self._retry = retry
        self._safe_mode = safe_mode
        self._rows: list[Any] = []

        self.dialog = wx.Dialog(
            parent,
            title="Feed Check",
            style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER,
        )
        self.dialog.SetMinSize((720, 420))
        root = wx.BoxSizer(wx.VERTICAL)

        # The summary is a StaticText that changes, which is exactly what a screen
        # reader does not announce -- so it is also spoken on open and after every
        # retry (GATE-12's cure, not GATE-13's violation).
        self._summary = wx.StaticText(self.dialog, label="")
        root.Add(self._summary, 0, wx.EXPAND | wx.ALL, 10)

        # Label first, then the list. The ordering is the accessible name.
        list_label = wx.StaticText(self.dialog, label="Your feeds, &worst first:")
        root.Add(list_label, 0, wx.LEFT | wx.RIGHT, 10)
        self._list = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list.SetHelpText(
            "Every podcast you follow, worst first: the ones failing to check, then "
            "any never checked, then any that have gone quiet, then the healthy "
            "ones. Nothing here has been unfollowed and nothing has stopped being "
            "checked -- Cast keeps trying a failing feed. Shift+F10 opens what you "
            "can do to a row."
        )
        for index, (heading, width) in enumerate(_COLUMNS):
            self._list.InsertColumn(index, heading, width=width)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self._retry_btn = wx.Button(self.dialog, label="&Retry")
        self._retry_btn.SetHelpText("Check the selected feed again, now.")
        self._retry_btn.Enable(False)
        self._retry_all_btn = wx.Button(self.dialog, label="Retry All &Failed")
        self._retry_all_btn.SetHelpText(
            "Check every failing feed again. Feeds that have gone quiet are left "
            "alone -- a quiet feed is working perfectly, and retrying it would "
            "report nothing new."
        )
        self._copy_btn = wx.Button(self.dialog, label="&Copy Feed Address")
        self._copy_btn.SetHelpText(
            "Put the selected podcast's feed address on the clipboard, so you can "
            "open it in a browser and see what the publisher is actually sending."
        )
        self._copy_btn.Enable(False)
        # No access key on Close: Escape already serves it, and the letter it gives
        # up resolves a collision elsewhere (GATE-14's first rule).
        close_btn = wx.Button(self.dialog, self._wx.ID_CANCEL, "Close")
        close_btn.SetHelpText("Closes Feed Check without changing which podcasts you follow.")
        for button in (self._retry_btn, self._retry_all_btn, self._copy_btn):
            buttons.Add(button, 0, wx.RIGHT, 6)
        buttons.AddStretchSpacer()
        buttons.Add(close_btn, 0)
        root.Add(buttons, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)

        self._list.Bind(wx.EVT_LIST_ITEM_SELECTED, self._on_selected)
        self._list.Bind(wx.EVT_LIST_ITEM_DESELECTED, self._on_deselected)
        self._list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, lambda _e: self._on_retry())
        # Both routes to the row menu. EVT_CONTEXT_MENU is the keyboard one.
        self._list.Bind(wx.EVT_CONTEXT_MENU, self._on_context_menu)
        self._list.Bind(wx.EVT_LIST_ITEM_RIGHT_CLICK, self._on_context_menu)
        self._retry_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_retry())
        self._retry_all_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_retry_all())
        self._copy_btn.Bind(wx.EVT_BUTTON, lambda _e: self._on_copy())

        self._reload()

    # -- the report -------------------------------------------------------- #

    def _reload(self, *, keep_index: int = -1) -> None:
        """Rebuild the list from the live bookkeeping.

        *keep_index* restores the cursor after a retry, because a report that
        reshuffles under a screen-reader cursor is unusable -- and a retry changes
        a row's rank, so the list genuinely does reorder.
        """
        from quill.core.podcasts import feed_health

        self._rows = feed_health.rows(self._library)
        self._list.DeleteAllItems()
        for index, row in enumerate(self._rows):
            self._list.InsertItem(index, row.title)
            self._list.SetItem(index, 1, row.status)
            self._list.SetItem(index, 2, row.checked_ago)
            self._list.SetItem(index, 3, row.published_ago)
        said = feed_health.summary(self._rows)
        self._summary.SetLabel(said)
        self._retry_all_btn.Enable(bool(feed_health.failing_rows(self._rows)))
        if self._rows:
            wanted = keep_index if 0 <= keep_index < len(self._rows) else 0
            self._list.Select(wanted)
            self._list.Focus(wanted)
        return None

    def _selected_row(self) -> Any:
        index = self._list.GetFirstSelected()
        return self._rows[index] if 0 <= index < len(self._rows) else None

    def _on_selected(self, _event: object) -> None:
        row = self._selected_row()
        # A local show has no feed, so neither Retry nor Copy means anything on it.
        # Disabled rather than silently doing nothing, so the row's own status line
        # ("Local files, no feed to check") and the buttons agree.
        usable = row is not None and not row.is_local
        self._retry_btn.Enable(usable)
        self._copy_btn.Enable(usable)

    def _on_deselected(self, _event: object) -> None:
        self._retry_btn.Enable(False)
        self._copy_btn.Enable(False)

    # -- the actions ------------------------------------------------------- #

    def _on_retry(self) -> None:
        row = self._selected_row()
        if row is None or row.is_local:
            return
        if self._safe_mode:
            self._announce("Checking a feed is disabled in Safe Mode.")
            return
        index = self._list.GetFirstSelected()
        # Said before, not after: the refresh is asynchronous, so an announcement
        # afterwards would arrive before anything had happened and read as a result.
        self._announce(f"Checking {row.title}")
        self._retry(row.show_id)
        self._reload(keep_index=index)

    def _on_retry_all(self) -> None:
        """Retry every failing feed. Quiet feeds are deliberately left alone."""
        from quill.core.podcasts import feed_health

        if self._safe_mode:
            self._announce("Checking feeds is disabled in Safe Mode.")
            return
        failing = feed_health.failing_rows(self._rows)
        if not failing:
            self._announce("Nothing is failing, so there is nothing to retry.")
            return
        for row in failing:
            self._retry(row.show_id)
        self._announce(
            f"Checking {len(failing)} failing feed{'' if len(failing) == 1 else 's'}. "
            "The list updates as each one answers."
        )
        self._reload()

    def _on_copy(self) -> None:
        """Copy the feed address, and say so.

        Announced because a clipboard write is the textbook thing a screen reader
        cannot report: nothing on screen changed, and the only way to find out
        whether it worked would be to paste it somewhere.
        """
        row = self._selected_row()
        if row is None or not row.feed_url:
            self._announce("That row has no feed address.")
            return
        clipboard = self._wx.TheClipboard
        if not clipboard.Open():
            self._announce("The clipboard could not be opened, so nothing was copied.")
            return
        try:
            clipboard.SetData(self._wx.TextDataObject(row.feed_url))
        finally:
            clipboard.Close()
        self._announce(f"Feed address for {row.title} copied")

    def _on_context_menu(self, event: object) -> None:
        """The row's own menu, positioned on the list rather than at the pointer.

        On the list, because it has to appear in the same place whether it was
        opened with the Applications key, with Shift+F10 or with a right click --
        and here the first two are how it will usually be opened.
        """
        wx = self._wx
        row = self._selected_row()
        if row is None:
            return
        menu = wx.Menu()
        retry_id, copy_id = wx.NewIdRef(), wx.NewIdRef()
        menu.Append(retry_id, "&Retry This Feed")
        menu.Append(copy_id, "&Copy Feed Address")
        menu.Enable(retry_id, not row.is_local and not self._safe_mode)
        menu.Enable(copy_id, bool(row.feed_url))
        self.dialog.Bind(wx.EVT_MENU, lambda _e: self._on_retry(), id=retry_id)
        self.dialog.Bind(wx.EVT_MENU, lambda _e: self._on_copy(), id=copy_id)
        try:
            self._list.PopupMenu(menu)
        finally:
            menu.Destroy()
        if hasattr(event, "Skip"):
            event.Skip(False)

    # -- showing it -------------------------------------------------------- #

    def show(self) -> None:
        from quill.ui.dialog_contract import show_modal_dialog

        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL)
        # The summary is spoken on arrival: it is the answer to the question
        # somebody opened this window to ask, and a StaticText is silent.
        self._announce(self._summary.GetLabel())
        try:
            show_modal_dialog(self.dialog, "Feed Check", announce=self._announce)
        finally:
            self.dialog.Destroy()


def open_feed_check(host: Any) -> None:
    """Podcasts > Feed Check...: the report, with Retry wired to the real refresh."""
    from quill.ui.podcasts.feed_refresh import refresh_feed

    dialog = FeedCheckDialog(
        host.frame,
        library=host._podcast_library,
        announce=host._announce,
        retry=lambda show_id: refresh_feed(host, show_id),
        safe_mode=bool(getattr(host, "_safe_mode", False)),
    )
    dialog.show()
