"""Downloads > Downloads... -- what is on disk, and how to get it back.

Through 1.0.x the Downloads menu had two items, both about transfers in
flight (Pause All, Resume All), and there was nowhere in the app that could
answer "how much disk are my podcasts using". For an app whose whole job is
to accumulate audio files, that is a strange thing not to know.

The report is text first: a total, a per-show breakdown, and a plain
statement of the rules in force. The Unheard/All filter announces how many
rows it hid, because a filtered list that does not say it is filtered is a
list that has silently lied about how much you have.

Freeing space is deliberate and reported: the button applies the age limit
and the storage cap, then says how many bytes came back. Nothing here evicts
a queued or part-played episode -- that rule lives in ``retention.py`` and is
the reason an automatic cap is safe to offer at all.
"""

from __future__ import annotations

from collections.abc import Callable

from quill.core.media.list_columns import ColumnDef
from quill.core.podcasts import retention
from quill.core.podcasts.list_columns import DOWNLOADS
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids
from quill.ui.media.list_columns_view import build_columns, columns_for, fill_row

_FILTER_LABELS = ("All downloads", "Unheard only")


class DownloadsDialog:
    """Storage usage, per show, with the rules and a way to reclaim space."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
        on_free_space: Callable[[], int] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_free_space = on_free_space

        self.dialog = wx.Dialog(
            parent, title="Downloads", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((620, 520))
        root = wx.BoxSizer(wx.VERTICAL)

        self._summary = wx.StaticText(self.dialog, label="")
        self._summary.SetName("Total podcast download storage")
        root.Add(self._summary, 0, wx.EXPAND | wx.ALL, 10)

        filter_row = wx.BoxSizer(wx.HORIZONTAL)
        filter_row.Add(
            wx.StaticText(self.dialog, label="&Show:"), 0, wx.ALIGN_CENTER_VERTICAL | wx.RIGHT, 6
        )
        self._filter = wx.Choice(self.dialog, choices=list(_FILTER_LABELS))
        self._filter.SetName("Which downloaded episodes to list")
        self._filter.SetSelection(0)
        filter_row.Add(self._filter, 1, wx.EXPAND)
        root.Add(filter_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._list = wx.ListCtrl(self.dialog, style=wx.LC_REPORT | wx.BORDER_SIMPLE)
        self._list.SetName("Downloaded episodes by podcast; arrow through for sizes")
        # Subscriptions > Choose Columns... owns which columns exist and in
        # what order -- a report row is read out column by column.
        self._columns: list[ColumnDef] = columns_for("cast", DOWNLOADS.id)
        build_columns(self._list, self._columns)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._rules = wx.StaticText(self.dialog, label="")
        self._rules.SetName("Storage rules in force")
        root.Add(self._rules, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        free_btn = wx.Button(self.dialog, label="&Free Up Space")
        free_btn.SetName(
            "Apply the age limit and the storage cap now. Queued and part-played "
            "episodes are never removed."
        )
        free_btn.Enable(on_free_space is not None)
        remove_show_btn = wx.Button(self.dialog, label="&Remove This Podcast's Downloads...")
        remove_show_btn.SetName("Delete every downloaded file for the selected podcast")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(free_btn, 0, wx.RIGHT, 6)
        btn_row.Add(remove_show_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._filter.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(announce=True))
        free_btn.Bind(wx.EVT_BUTTON, self._on_free_space_click)
        remove_show_btn.Bind(wx.EVT_BUTTON, self._on_remove_show_downloads)
        self._rows: list = []
        self._refresh()

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(self.dialog, cancel_id=self._wx.ID_CANCEL, escape_id=self._wx.ID_CANCEL)
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Downloads", announce=self._announce)
        finally:
            self.dialog.Destroy()

    # -- content ---------------------------------------------------------

    def _unheard_only(self) -> bool:
        return self._filter.GetSelection() == 1

    def _refresh(self, *, announce: bool = False) -> None:
        entries = retention.downloaded_episodes(self._library)
        total_files = len(entries)
        total_bytes = sum(size for _s, _e, size in entries)
        if self._unheard_only():
            entries = [row for row in entries if not row[1].played]
        totals: dict[str, list] = {}
        for show, _episode, size in entries:
            row = totals.setdefault(show.id, [show, 0, 0])
            row[1] += 1
            row[2] += size
        self._rows = sorted(totals.values(), key=lambda row: row[2], reverse=True)

        self._list.DeleteAllItems()
        self._list.Freeze()
        try:
            for index, (show, files, size) in enumerate(self._rows):
                fill_row(
                    self._list,
                    index,
                    self._columns,
                    {
                        "podcast": show.title,
                        "files": str(files),
                        "size": retention.format_bytes(size),
                    },
                )
        finally:
            self._list.Thaw()

        shown_files = sum(row[1] for row in self._rows)
        hidden = total_files - shown_files
        summary = (
            f"{total_files} downloaded episode(s) using "
            f"{retention.format_bytes(total_bytes)} across "
            f"{len(retention.per_show_usage(self._library))} podcast(s)."
        )
        if hidden:
            summary += f" The filter is hiding {hidden} already-played download(s)."
        self._summary.SetLabel(summary)
        self._rules.SetLabel(self._rules_text())
        if announce:
            self._announce(summary)
        if self._rows:
            self._list.Select(0)
            self._list.Focus(0)

    def _rules_text(self) -> str:
        settings = self._library.settings
        parts: list[str] = []
        if settings.download_retention_days > 0:
            parts.append(f"downloads older than {settings.download_retention_days} day(s) go")
        if settings.storage_cap_mb > 0:
            parts.append(f"total storage is capped at {settings.storage_cap_mb} MB")
        if not parts:
            text = (
                "No automatic storage rules are set. Podcast Settings can add an age "
                "limit or a total cap."
            )
        else:
            text = (
                "In force: " + "; ".join(parts) + ". A queued or part-played episode is "
                "never removed automatically."
            )
        return text + self._streamed_text()

    def _streamed_text(self) -> str:
        """What streamed episodes are using, said separately from downloads.

        Deliberately its own sentence rather than a row in the table above: a
        streamed episode's audio is not a download, it is removed on its own,
        and counting the two together would make the list of things the
        listener *keeps* wrong.
        """
        from quill.core.podcasts import playback_cache

        used = playback_cache.total_bytes()
        if used <= 0:
            return ""
        cap = self._library.settings.playback_cache_cap_mb
        limit = f" of at most {cap} MB" if cap > 0 else ""
        return (
            f" Streamed episodes are separately using "
            f"{retention.format_bytes(used)}{limit}; that audio is removed "
            "automatically and is not part of the figures above."
        )

    # -- actions ---------------------------------------------------------

    def _on_free_space_click(self, _event: object) -> None:
        if self._on_free_space is None:
            return
        self._on_free_space()
        self._refresh()

    def _selected_show(self) -> object | None:
        index = self._list.GetFirstSelected()
        if 0 <= index < len(self._rows):
            return self._rows[index][0]
        return None

    def _on_remove_show_downloads(self, _event: object) -> None:
        from pathlib import Path

        from quill.ui.dialog_contract import show_message_box

        wx = self._wx
        show = self._selected_show()
        if show is None:
            self._announce("Select a podcast first.")
            return
        downloaded = [e for e in show.episodes if e.downloaded_path]
        protected = [e for e in downloaded if retention.is_protected(self._library, show, e)]
        removable = [e for e in downloaded if e not in protected]
        if not removable:
            self._announce(
                f"Nothing to remove for {show.title}: every download is queued or part-played."
            )
            return
        size = sum(retention.file_size(e.downloaded_path) for e in removable)
        note = f" {len(protected)} queued or part-played episode(s) are kept." if protected else ""
        answer = show_message_box(
            f"Delete {len(removable)} downloaded file(s) for {show.title}, freeing "
            f"{retention.format_bytes(size)}? The episodes stay in your library and can "
            f"be downloaded again.{note}",
            "Remove Downloads",
            wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
            self.dialog,
            announce=self._announce,
        )
        if answer != wx.YES:
            return
        for episode in removable:
            try:
                Path(episode.downloaded_path).unlink(missing_ok=True)
            except OSError:
                continue
            episode.downloaded_path = ""
        self._on_library_changed()
        self._refresh()
        self._announce(
            f"Removed {len(removable)} download(s) for {show.title}, "
            f"freeing {retention.format_bytes(size)}"
        )
