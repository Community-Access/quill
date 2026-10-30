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

import logging
from collections.abc import Callable
from typing import Protocol

from quill.core.media.list_columns import ColumnDef
from quill.core.podcasts import retention
from quill.core.podcasts.list_columns import DOWNLOADS
from quill.core.podcasts.storage_maintenance import StoragePlan, StorageUsage, UsageRow
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids, bind_close_button
from quill.ui.dpi import dip_size
from quill.ui.media.list_columns_view import build_columns
from quill.ui.podcasts.storage_reconcile import StorageOutcome
from quill.ui.podcasts.storage_report import UsageReport
from quill.ui.podcasts.storage_snapshot import TurnJob
from quill.ui.podcasts.storage_tasks import Prepared, ReadJob, StorageJobs
from quill.ui.surface_lifetime import destroy_event_matches, lifetime_for, window_is_going
from quill.ui.virtual_list import virtual_report_list

_FILTER_LABELS = ("All downloads", "Unheard only")
logger = logging.getLogger(__name__)


class FreeSpaceAction(Protocol):
    def __call__(self, *, completed: Callable[[int], None]) -> None: ...


class DownloadsDialog:
    """Storage usage, per show, with the rules and a way to reclaim space."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
        on_free_space: FreeSpaceAction | None = None,
        storage_jobs: StorageJobs,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_free_space = on_free_space
        self._storage_jobs = storage_jobs
        self._reader: ReadJob | None = None
        self._render: TurnJob | None = None
        self._usage: StorageUsage | None = None
        self._closed = False
        self._busy = False
        self._refresh_generation = 0
        self._rows: tuple[UsageRow, ...] = ()
        self._display_unheard = False

        self.dialog = wx.Dialog(
            parent, title="Downloads", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self._lifetime = lifetime_for(self.dialog)
        self._window_id = self.dialog.GetId()
        self.dialog.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)
        self.dialog.SetMinSize(dip_size(self.dialog, 620, 520))
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

        # A real heading, created immediately before the list. The association
        # is by creation order, so a label placed after the list -- or a SetName,
        # which is what this carried -- names nothing and the list announces as a
        # bare "list". The Show combo above has one, which is why it announces.
        root.Add(
            wx.StaticText(self.dialog, label="Downloaded &episodes:"), 0, wx.LEFT | wx.RIGHT, 10
        )
        self._list = virtual_report_list(wx, self.dialog, self._row_text, style=wx.BORDER_SIMPLE)
        self._list.SetHelpText(
            "Every downloaded episode, grouped by podcast. Arrow through for "
            "sizes; Remove This Podcast's Downloads deletes the files for the "
            "podcast you are on. Queued, part-played, pinned, and active downloads are kept."
        )
        # Subscriptions > Choose Columns... owns which columns exist and in
        # what order -- a report row is read out column by column.
        self._columns: list[ColumnDef] = [
            column for column in DOWNLOADS.columns if column.default_visible
        ]
        build_columns(self._list, self._columns)
        root.Add(self._list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        self._rules = wx.StaticText(self.dialog, label="")
        self._rules.SetName("Storage rules in force")
        root.Add(self._rules, 0, wx.EXPAND | wx.ALL, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        free_btn = wx.Button(self.dialog, label="&Free Up Space")
        free_btn.SetName(
            "Apply the age limit and the storage cap now. Queued, part-played, "
            "pinned, and active downloads are never removed."
        )
        free_btn.Enable(on_free_space is not None)
        remove_show_btn = wx.Button(self.dialog, label="&Remove This Podcast's Downloads...")
        remove_show_btn.SetName("Delete unprotected downloaded files for the selected podcast")
        close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        bind_close_button(self.dialog, close_btn, modeless=False)
        close_btn.SetDefault()
        self._free_btn = free_btn
        self._remove_show_btn = remove_show_btn
        btn_row.Add(free_btn, 0, wx.RIGHT, 6)
        btn_row.Add(remove_show_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._filter.Bind(wx.EVT_CHOICE, lambda _e: self._refresh(announce=True))
        free_btn.Bind(wx.EVT_BUTTON, self._on_free_space_click)
        remove_show_btn.Bind(wx.EVT_BUTTON, self._on_remove_show_downloads)
        self._refresh(announce=True)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_CANCEL,
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        # Focus on the thing this window is for, not on whatever control happens
        # to come first in it (qc.md 6b: eight windows landed on a filter or a
        # chooser). Set before ShowModal, which keeps a focus already placed.
        self._list.SetFocus()
        try:
            show_modal_dialog(self.dialog, "Downloads", announce=self._announce)
        finally:
            self._cancel_ui()
            self.dialog.Destroy()

    # -- content ---------------------------------------------------------

    def _unheard_only(self) -> bool:
        return self._filter.GetSelection() == 1

    def _row_text(self, row: int, column: int) -> str:
        if not 0 <= row < len(self._rows) or not 0 <= column < len(self._columns):
            return ""
        value = self._rows[row]
        values = {
            "podcast": value.title,
            "files": str(value.unheard_files if self._display_unheard else value.files),
            "size": retention.format_bytes(
                value.unheard_size if self._display_unheard else value.size
            ),
        }
        return values[self._columns[column].id]

    def _refresh(self, *, announce: bool = False) -> None:
        if not self._alive():
            return
        if self._reader is not None:
            self._reader.cancel()
        if self._render is not None:
            self._render.cancel()
        self._refresh_generation += 1
        revision = self._refresh_generation
        selected = self._selected_show()
        selected_id = selected.show_id if selected is not None else ""
        unheard = self._unheard_only()
        self._remove_show_btn.Enable(False)
        self._summary.SetLabel("Reading download storage...")

        def ready(prepared: Prepared) -> None:
            if not self._alive() or revision != self._refresh_generation:
                return
            report = prepared.value
            if not isinstance(report, UsageReport):
                self._failed(TypeError("The storage report had an invalid shape"))
                return
            usage = report.usage
            self._usage = usage
            rows = usage.unheard_rows if unheard else usage.rows

            def render():
                shown = 0
                selected_index = 0
                for index, row in enumerate(rows):
                    files = row.unheard_files if unheard else row.files
                    shown += files
                    if row.show_id == selected_id:
                        selected_index = index
                    yield
                return shown, selected_index

            def rendered(result: tuple[int, int]) -> None:
                if not self._alive() or revision != self._refresh_generation:
                    return
                shown, selected_index = result
                self._list.set_rows(0)
                self._rows = rows
                self._display_unheard = unheard
                if tuple(self._columns) != report.columns:
                    self._columns = list(report.columns)
                    build_columns(self._list, self._columns)
                self._list.set_rows(len(self._rows))
                summary = (
                    f"{usage.files} downloaded episode(s) using "
                    f"{retention.format_bytes(usage.size)} across {len(usage.rows)} podcast(s)."
                )
                hidden = usage.files - shown
                if hidden:
                    summary += f" The filter is hiding {hidden} already-played download(s)."
                if usage.missing:
                    summary += f" {usage.missing} recorded file(s) are already unavailable."
                if usage.unreadable:
                    summary += f" Sizes for {usage.unreadable} file(s) could not be read."
                self._summary.SetLabel(summary)
                self._rules.SetLabel(self._rules_text())
                self._set_busy(self._busy)
                if announce or usage.unreadable:
                    self._announce(summary)
                if self._rows and self._list.GetFirstSelected() < 0:
                    self._list.Select(selected_index)
                    self._list.Focus(selected_index)

            self._render = TurnJob(
                self._wx,
                render(),
                completed=rendered,
                failed=self._failed,
                alive=self._alive,
                valid=lambda: revision == self._refresh_generation,
            )
            self._render.start()

        self._reader = self._storage_jobs.usage(ready, self._failed)

    def _rules_text(self) -> str:
        settings = self._storage_jobs.host._podcast_library.settings
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
                "In force: " + "; ".join(parts) + ". Queued, part-played, pinned, and "
                "active downloads are never removed automatically."
            )
        return text + self._streamed_text()

    def _streamed_text(self) -> str:
        """What streamed episodes are using, said separately from downloads.

        Deliberately its own sentence rather than a row in the table above: a
        streamed episode's audio is not a download, it is removed on its own,
        and counting the two together would make the list of things the
        listener *keeps* wrong.
        """
        used = self._usage.streamed_size if self._usage is not None else 0
        if used <= 0:
            return ""
        cap = self._storage_jobs.host._podcast_library.settings.playback_cache_cap_mb
        limit = f" of at most {cap} MB" if cap > 0 else ""
        return (
            f" Streamed episodes are separately using "
            f"{retention.format_bytes(used)}{limit}; that audio is removed "
            "automatically and is not part of the figures above."
        )

    # -- actions ---------------------------------------------------------

    def _on_free_space_click(self, _event: object) -> None:
        if self._on_free_space is None or self._busy:
            return
        self._set_busy(True)

        def completed(_reclaimed: int) -> None:
            if self._alive():
                self._set_busy(False)
                self._refresh(announce=True)

        self._on_free_space(completed=completed)

    def _selected_show(self) -> UsageRow | None:
        index = self._list.GetFirstSelected()
        if 0 <= index < len(self._rows):
            return self._rows[index]
        return None

    def _on_remove_show_downloads(self, _event: object) -> None:
        from quill.ui.dialog_contract import show_message_box

        if self._busy:
            return
        wx = self._wx
        show = self._selected_show()
        if show is None:
            self._announce("Select a podcast first.")
            return
        self._set_busy(True)
        self._announce("Checking which downloads can be removed...")

        def prepared(proposal: Prepared) -> None:
            if not self._alive():
                return
            plan = proposal.value
            if not isinstance(plan, StoragePlan):
                self._failed(TypeError("The removal proposal had an invalid shape"))
                return
            if not plan.downloads:
                self._set_busy(False)
                message = (
                    f"Nothing to remove for {show.title}: changed or protected downloads are kept."
                )
                if plan.unreadable:
                    message += f" {plan.unreadable} file(s) could not be inspected."
                self._announce(message)
                return
            note = f" {plan.protected} protected episode(s) are kept." if plan.protected else ""
            if plan.unreadable:
                note += f" {plan.unreadable} unreadable file(s) are kept."
            answer = show_message_box(
                f"Delete {len(plan.downloads)} downloaded file(s) for {show.title}, freeing "
                f"up to {retention.format_bytes(plan.size)}? The episodes stay in your library "
                f"and can be downloaded again.{note}",
                "Remove Downloads",
                wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION,
                self.dialog,
                announce=self._announce,
            )
            if answer != wx.YES:
                self._set_busy(False)
                return

            def completed(outcome: StorageOutcome) -> None:
                if not self._alive():
                    return
                self._set_busy(False)
                self._announce(
                    f"Removed {outcome.removed} download(s) for {show.title}, "
                    f"freeing {retention.format_bytes(outcome.reclaimed)}"
                    + (". " + "; ".join(outcome.details()) if outcome.details() else "")
                    + "."
                )
                self._refresh(announce=True)

            self._storage_jobs.run("show", completed, show_id=show.show_id, allowed=plan.downloads)

        self._reader = self._storage_jobs.prepare_removal(show.show_id, prepared, self._failed)

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        self._free_btn.Enable(not busy and self._on_free_space is not None)
        self._remove_show_btn.Enable(not busy and bool(self._rows))

    def _alive(self) -> bool:
        return not self._closed and self._lifetime.is_alive and not window_is_going(self.dialog)

    def _failed(self, error: BaseException) -> None:
        logger.error("Could not prepare the Downloads report or action", exc_info=error)
        if self._alive():
            self._set_busy(False)
            self._summary.SetLabel("Could not read podcast storage. Please try again.")
            self._announce("Could not read podcast storage. No removal was started.")

    def _cancel_ui(self) -> None:
        self._closed = True
        self._lifetime.invalidate()
        if self._reader is not None:
            self._reader.cancel()
        if self._render is not None:
            self._render.cancel()

    def _on_destroy(self, event: object) -> None:
        if destroy_event_matches(event, self.dialog, self._window_id):
            self._cancel_ui()
        event.Skip()
