"""Import OPML... -- the bulk-import flow, sized for a real subscription list.

A two-thousand-entry OPML file is not an edge case; it is what a decade of
podcast listening looks like when it is exported. This dialog is built for
that file:

- **Nothing blocks the window.** Reading, parsing, planning, and adding all
  happen on the task manager, and the reachability sweep runs on its own
  bounded pool afterwards. The only thing that ever runs on the UI thread is
  updating this dialog's own status line.
- **The import finishes first, the checking comes after.** Adding two
  thousand subscriptions takes a moment; checking whether two thousand feeds
  still answer takes minutes. Doing them in that order means the listener has
  their library immediately and can walk away from the slow part -- or cancel
  it, and keep everything already imported.
- **Progress is spoken, not just drawn.** The gauge is there for people who
  want it; the status line is a real label that updates, and every tenth of
  the sweep is announced, so progress is available without watching a bar.
- **The report is actionable.** Knowing that 312 feeds are dead is only
  useful if you can do something about it, so the report exports both a
  plain-text list and a **pruned copy of the original OPML** with the dead
  feeds removed.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from quill.core.podcasts import opml_import
from quill.core.podcasts.opml import OpmlError, OpmlValidationResult
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import apply_modal_ids

#: Announce progress this often during the sweep (every N per cent).
_ANNOUNCE_EVERY_PERCENT = 10


class OpmlImportDialog:
    """Runs one OPML import end to end and reports what happened."""

    def __init__(
        self,
        parent: object,
        *,
        library: PodcastLibrary,
        path: Path,
        task_manager: object,
        safe_mode: bool,
        announce_cb: Callable[[str], None] | None = None,
        on_library_changed: Callable[[], None] | None = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._path = Path(path)
        self._task_manager = task_manager
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)

        self._source_text = ""
        self._plan: opml_import.ImportPlan | None = None
        self._results: list[OpmlValidationResult] = []
        self._cancelled = False
        self._running = False
        self._last_announced_percent = 0

        self.dialog = wx.Dialog(
            parent, title="Import OPML", style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER
        )
        self.dialog.SetMinSize((560, 340))
        root = wx.BoxSizer(wx.VERTICAL)

        heading = wx.StaticText(self.dialog, label=f"Importing {self._path.name}")
        root.Add(heading, 0, wx.EXPAND | wx.ALL, 10)

        self._check_feeds = wx.CheckBox(
            self.dialog, label="&Check that each feed is still reachable after importing"
        )
        self._check_feeds.SetName(
            "Makes one request per feed to find dead subscriptions. Slower on a "
            "large file, can be cancelled, and produces a report you can use to "
            "prune the OPML file."
        )
        self._check_feeds.SetValue(not safe_mode)
        self._check_feeds.Enable(not safe_mode)
        root.Add(self._check_feeds, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._stream_only = wx.CheckBox(
            self.dialog, label="Add every show as &streaming (no bulk downloading)"
        )
        self._stream_only.SetName(
            "Recommended for a large list: imported shows stream instead of "
            "queueing a download for every episode of every show"
        )
        self._stream_only.SetValue(True)
        root.Add(self._stream_only, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(self.dialog, label="Ready to import.")
        self._status.SetName("Import status")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._gauge = wx.Gauge(self.dialog, range=100)
        self._gauge.SetName("Import progress")
        root.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._start_btn = wx.Button(self.dialog, wx.ID_OK, "&Import")
        self._cancel_check_btn = wx.Button(self.dialog, label="S&top Checking")
        self._cancel_check_btn.SetName(
            "Stop checking feeds and report what has been checked so far"
        )
        self._cancel_check_btn.Enable(False)
        self._close_btn = wx.Button(self.dialog, wx.ID_CANCEL, "Close")
        btn_row.Add(self._start_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._cancel_check_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        self.dialog.SetSizer(root)
        self._start_btn.Bind(wx.EVT_BUTTON, self._on_start)
        self._cancel_check_btn.Bind(wx.EVT_BUTTON, self._on_cancel_check)

    def show(self) -> None:
        self.dialog.CentreOnParent()
        apply_modal_ids(
            self.dialog,
            affirmative_id=self._wx.ID_OK,
            affirmative_label="Import",
            cancel_id=self._wx.ID_CANCEL,
            escape_id=self._wx.ID_CANCEL,
        )
        from quill.ui.dialog_contract import show_modal_dialog

        try:
            show_modal_dialog(self.dialog, "Import OPML", announce=self._announce)
        finally:
            # Cancel any sweep still running: the dialog is going away and its
            # progress callbacks must not fire into a destroyed window.
            self._cancelled = True
            self.dialog.Destroy()

    # -- phase 1: read, plan, add ---------------------------------------

    def _on_start(self, _event: object) -> None:
        if self._running:
            return
        self._running = True
        self._start_btn.Enable(False)
        self._set_status("Reading the file...")
        stream_only = self._stream_only.GetValue()
        path = self._path
        library = self._library

        def _do_import(**_kwargs: object) -> tuple[str, opml_import.ImportPlan, int]:
            # File read, XML parse, planning, and the adds all happen here,
            # off the UI thread: a 2,000-entry file is several megabytes of
            # XML and the planning walks it twice.
            text = path.read_text(encoding="utf-8", errors="replace")
            plan = opml_import.parse_and_plan(library, text)
            added = opml_import.apply_plan(library, plan, stream_only=stream_only)
            return text, plan, len(added)

        self._task_manager.submit(
            "podcast-opml-import",
            _do_import,
            on_success=lambda _op, outcome: self._wx.CallAfter(self._on_imported, outcome, None),
            on_failure=lambda _op, error: self._wx.CallAfter(self._on_imported, None, error),
        )

    def _on_imported(self, outcome: object, error: BaseException | None) -> None:
        if error is not None:
            message = (
                str(error)
                if isinstance(error, OpmlError)
                else f"That file could not be imported: {error}"
            )
            self._set_status(message)
            self._announce(message)
            self._running = False
            self._start_btn.Enable(True)
            return
        text, plan, added = outcome  # type: ignore[misc]
        self._source_text = text
        self._plan = plan
        self._on_library_changed()
        summary = (
            f"Imported {added} podcast(s). {len(plan.duplicates_in_library)} already "
            f"subscribed, {len(plan.duplicates_in_file)} listed twice in the file, "
            f"{len(plan.unusable)} unusable."
        )
        self._set_status(summary)
        self._announce(summary)
        if not self._check_feeds.GetValue() or not plan.new:
            self._running = False
            self._finish()
            return
        self._start_sweep()

    # -- phase 2: reachability sweep ------------------------------------

    def _start_sweep(self) -> None:
        plan = self._plan
        if plan is None:
            return
        feeds = [(candidate.title, candidate.feed_url) for candidate in plan.new]
        self._cancelled = False
        self._last_announced_percent = 0
        self._cancel_check_btn.Enable(True)
        self._gauge.SetRange(len(feeds))
        self._set_status(f"Checking {len(feeds)} feed(s)...")
        self._announce(
            f"Checking {len(feeds)} feed(s). This runs in the background; "
            "Stop Checking reports what has been checked so far."
        )
        safe_mode = self._safe_mode

        def _do_validate(**_kwargs: object) -> list[OpmlValidationResult]:
            return opml_import.validate_feeds(
                feeds,
                on_progress=lambda done, total: self._wx.CallAfter(self._on_progress, done, total),
                should_cancel=lambda: self._cancelled,
                safe_mode=safe_mode,
            )

        self._task_manager.submit(
            "podcast-opml-validate",
            _do_validate,
            on_success=lambda _op, results: self._wx.CallAfter(self._on_validated, results),
            on_failure=lambda _op, _error: self._wx.CallAfter(self._on_validated, []),
        )

    def _on_progress(self, done: int, total: int) -> None:
        if not self.dialog:  # destroyed while the sweep was running
            return
        try:
            self._gauge.SetValue(done)
            self._status.SetLabel(f"Checking feeds: {done} of {total}...")
        except RuntimeError:
            return
        percent = int(done * 100 / total) if total else 100
        if percent - self._last_announced_percent >= _ANNOUNCE_EVERY_PERCENT:
            self._last_announced_percent = percent
            self._announce(f"Checking feeds: {percent} per cent")

    def _on_cancel_check(self, _event: object) -> None:
        self._cancelled = True
        self._cancel_check_btn.Enable(False)
        self._announce("Stopping the feed check; everything already imported is kept.")

    def _on_validated(self, results: list[OpmlValidationResult]) -> None:
        self._results = list(results)
        self._running = False
        try:
            self._cancel_check_btn.Enable(False)
        except RuntimeError:
            return
        unreachable = sum(1 for result in self._results if not result.ok)
        self._set_status(
            f"Checked {len(self._results)} feed(s): {unreachable} unreachable."
            + (" (Stopped early.)" if self._cancelled else "")
        )
        self._finish()

    # -- report ---------------------------------------------------------

    def _finish(self) -> None:
        plan = self._plan
        if plan is None:
            return
        from quill.ui.podcasts.opml_import_report_dialog import OpmlImportReportDialog

        report = OpmlImportReportDialog(
            self.dialog,
            results=self._results,
            skipped_duplicates=[*plan.duplicates_in_library, *plan.duplicates_in_file],
            possible_duplicates=plan.same_title_different_feed,
            unusable=[f"{entry}: {reason}" for entry, reason in plan.unusable],
            source_opml=self._source_text,
            announce_cb=self._announce,
        )
        report.show()

    def _set_status(self, text: str) -> None:
        try:
            self._status.SetLabel(text)
        except RuntimeError:
            pass
