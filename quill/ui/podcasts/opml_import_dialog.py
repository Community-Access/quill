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
from threading import Event
from time import perf_counter
from types import SimpleNamespace
from typing import Any

from quill.core.podcasts import opml_import
from quill.core.podcasts.opml import OpmlError, OpmlValidationResult
from quill.core.podcasts.subscriptions import PodcastLibrary
from quill.ui.dialog_contract import bind_close_button
from quill.ui.dpi import dip_size
from quill.ui.podcasts.say_status import say_status
from quill.ui.surface_lifetime import surface_tasks

#: Announce progress this often during the sweep (every N per cent).
_ANNOUNCE_EVERY_PERCENT = 10


class OpmlImportDialog:
    """Runs one OPML import end to end and reports what happened."""

    TITLE = "Import OPML"
    MENU_TITLE = "&Import"

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
        on_import_finished: Callable[[list[str]], None] | None = None,
        host: Any = None,
    ) -> None:
        import wx

        self._wx = wx
        self._library = library
        self._path = Path(path)
        # Every task this window starts is tied to its lifetime (qc.md F-02).
        self._task_manager = surface_tasks(task_manager, lambda: getattr(self, "dialog", None))
        self._safe_mode = safe_mode
        self._announce = announce_cb or (lambda _m: None)
        self._on_library_changed = on_library_changed or (lambda: None)
        self._on_import_finished = on_import_finished or (lambda _ids: None)

        self._source_text = ""
        self._plan: opml_import.ImportPlan | None = None
        self._results: list[OpmlValidationResult] = []
        self._cancelled = False
        self._running = False
        self._last_announced_percent = 0
        self._imported_show_ids: list[str] = []
        self._cancel_event = Event()
        self._generation = 0
        self._apply_later: Any = None
        self._active_feeds: dict[str, str] = {}
        self._host = host or SimpleNamespace(frame=parent, _wx=wx, _announce=self._announce)

        self.frame = wx.Frame(parent, title="Import OPML")
        self._frame_id = self.frame.GetId()
        self.dialog = self.frame
        self.dialog.SetMinSize(dip_size(self.dialog, 560, 340))
        panel = wx.Panel(self.frame)
        root = wx.BoxSizer(wx.VERTICAL)

        self._heading = wx.StaticText(panel, label=f"Importing {self._path.name}")
        root.Add(self._heading, 0, wx.EXPAND | wx.ALL, 10)

        self._check_feeds = wx.CheckBox(
            panel, label="&Check that each feed is still reachable after importing"
        )
        self._check_feeds.SetName(
            "Makes one request per feed to find dead feeds. Slower on a "
            "large file, can be cancelled, and produces a report you can use to "
            "prune the OPML file."
        )
        self._check_feeds.SetValue(not safe_mode)
        self._check_feeds.SetHelpText(
            "After importing, check feed reachability on two background workers. "
            "Stop Checking ends the check without removing the shows you brought in."
        )
        self._check_feeds.Enable(not safe_mode)
        root.Add(self._check_feeds, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._stream_only = wx.CheckBox(
            panel, label="Add every show as &streaming (no bulk downloading)"
        )
        self._stream_only.SetName(
            "Recommended for a large list: imported shows stream instead of "
            "queueing a download for every episode of every show"
        )
        self._stream_only.SetValue(True)
        self._stream_only.SetHelpText(
            "Keep imported podcasts streaming so their back catalogues do not start downloading."
        )
        root.Add(self._stream_only, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._status = wx.StaticText(panel, label="Ready to import.")
        self._status.SetName("Import status")
        self._status.SetHelpText("Import and feed-check progress, including active podcasts.")
        root.Add(self._status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self._gauge = wx.Gauge(panel, range=100)
        self._gauge.SetName("Import progress")
        self._gauge.SetHelpText("How many imported feeds have been checked.")
        root.Add(self._gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        btn_row = wx.BoxSizer(wx.HORIZONTAL)
        self._start_btn = wx.Button(panel, wx.ID_OK, "&Import")
        self._start_btn.SetDefault()
        self._start_btn.SetHelpText("Import this feed list in the background.")
        self._cancel_check_btn = wx.Button(panel, label="S&top Checking")
        self._cancel_check_btn.SetName(
            "Stop checking feeds and report what has been checked so far"
        )
        self._cancel_check_btn.Enable(False)
        self._cancel_check_btn.SetHelpText(
            "Stop checking immediately, keep every show already added, and "
            "prepare a partial report."
        )
        self._close_btn = wx.Button(panel, wx.ID_CANCEL, "Close")
        self._close_btn.SetHelpText(
            "Hide this window without stopping the import. Return through the Window menu."
        )
        btn_row.Add(self._start_btn, 0, wx.RIGHT, 6)
        btn_row.Add(self._cancel_check_btn, 0, wx.RIGHT, 6)
        btn_row.AddStretchSpacer()
        btn_row.Add(self._close_btn)
        root.Add(btn_row, 0, wx.EXPAND | wx.ALL, 10)

        panel.SetSizer(root)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.frame.SetSizer(outer)
        bind_close_button(self.frame, self._close_btn, modeless=True)
        self._start_btn.Bind(wx.EVT_BUTTON, self._on_start)
        self._cancel_check_btn.Bind(wx.EVT_BUTTON, self._on_cancel_check)
        self.frame.Bind(wx.EVT_WINDOW_DESTROY, self._on_destroy)

    def show(self) -> None:
        from quill.ui.podcasts.peer_window import open_peer

        self.dialog.CentreOnParent()
        open_peer(self._host, "_opml_import_window", lambda _host: self)

    def focus_target(self) -> Any:
        return self._check_feeds

    def menu_rows(self) -> list[tuple[str, Any]]:
        return [
            ("Import file\tCtrl+I", lambda: self._on_start(None)),
            ("Stop checking\tAlt+T", lambda: self._on_cancel_check(None)),
        ]

    def _on_destroy(self, event: Any) -> None:
        if event.GetId() == self._frame_id:
            self._generation += 1
            self._cancel_event.set()
            if self._apply_later is not None:
                self._apply_later.Stop()
        event.Skip()

    # -- phase 1: read, plan, add ---------------------------------------

    def _on_start(self, _event: object) -> None:
        if self._running:
            return
        self._running = True
        self._generation += 1
        self._start_btn.Enable(False)
        self._check_feeds.Enable(False)
        self._stream_only.Enable(False)
        self._set_status("Reading the file...")
        path = self._path
        generation = self._generation
        from quill.core.podcasts.models import PodcastShow

        library = PodcastLibrary(
            shows=[
                PodcastShow(id=show.id, title=show.title, feed_url=show.feed_url)
                for show in self._library.shows
            ]
        )

        def _do_import(**_kwargs: object) -> tuple[str, opml_import.ImportPlan]:
            # File read, XML parse, and planning happen off the UI thread: a
            # 2,000-entry file is several megabytes of XML and planning walks
            # it twice. The live library is only mutated on the UI thread.
            text = path.read_text(encoding="utf-8", errors="replace")
            plan = opml_import.parse_and_plan(library, text)
            return text, plan

        self._task_manager.submit(
            "podcast-opml-import",
            _do_import,
            on_success=lambda _op, outcome: (
                self._on_imported(outcome, None) if generation == self._generation else None
            ),
            on_failure=lambda _op, error: (
                self._on_imported(None, error) if generation == self._generation else None
            ),
        )

    def _on_imported(self, outcome: object, error: BaseException | None) -> None:
        if error is not None:
            message = (
                str(error)
                if isinstance(error, OpmlError)
                else f"That file could not be imported: {error}"
            )
            self._set_status(message)
            self._running = False
            self._enable_import_choices()
            return
        text, plan = outcome  # type: ignore[misc]
        self._source_text = text
        self._plan = plan
        self._imported_show_ids = []
        steps = opml_import.apply_plan_steps(
            self._library,
            plan,
            stream_only=self._stream_only.GetValue(),
            revision=lambda: self._host.__dict__.get("_podcast_library_revision", 0),
        )

        def advance() -> None:
            self._apply_later = None
            if not self.dialog or self.dialog.IsBeingDeleted():
                steps.close()
                return
            deadline = perf_counter() + 0.008
            changed = False
            try:
                for _ in range(32):
                    before = (
                        len(self._library.shows),
                        len(self._library.folders),
                        plan.copied_placements,
                    )
                    show = next(steps)
                    changed |= before != (
                        len(self._library.shows),
                        len(self._library.folders),
                        plan.copied_placements,
                    )
                    if show is not None:
                        self._imported_show_ids.append(show.id)
                    if perf_counter() >= deadline:
                        break
            except StopIteration:
                self._on_library_changed()
                self._import_applied()
                return
            except Exception as error:
                if changed:
                    self._on_library_changed()
                self._set_status(
                    f"Import stopped after a problem: {error}. Added podcasts are kept."
                )
                self._running = False
                self._enable_import_choices()
                return
            if changed:
                self._on_library_changed()
            self._apply_later = self._wx.CallLater(1, advance)

        advance()

    def _enable_import_choices(self) -> None:
        self._start_btn.Enable(True)
        self._check_feeds.Enable(not self._safe_mode)
        self._stream_only.Enable(True)

    def set_path(self, path: Path) -> None:
        self._cancel_event.set()
        self._generation += 1
        self._path = path
        self._plan = None
        self._results = []
        self._heading.SetLabel(f"Importing {path.name}")
        self._gauge.SetRange(100)
        self._gauge.SetValue(0)
        self._enable_import_choices()
        self._set_status("Ready to import.", speak=False)

    def _import_applied(self) -> None:
        plan = self._plan
        if plan is None:
            raise RuntimeError("The import finished without a plan")
        added = len(self._imported_show_ids)
        self._on_library_changed()
        from quill.core.counted import plural

        summary = (
            f"Imported {plural(added, 'podcast')}. {len(plan.duplicates_in_library)} already "
            f"followed, {len(plan.duplicates_in_file)} listed twice in the file, "
            f"{len(plan.unusable)} unusable."
        )
        self._set_status(summary)
        self._on_import_finished(list(self._imported_show_ids))
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
        imported = set(self._imported_show_ids)
        feeds = [(show.title, show.feed_url) for show in self._library.shows if show.id in imported]
        self._cancelled = False
        self._cancel_event = Event()
        cancelled = self._cancel_event
        generation = self._generation
        self._active_feeds.clear()
        self._results = []
        self._last_announced_percent = 0
        self._cancel_check_btn.Enable(True)
        self._gauge.SetRange(len(feeds))
        from quill.core.counted import plural

        self._set_status(f"Checking {plural(len(feeds), 'feed')}...")
        self._announce(
            f"Checking {plural(len(feeds), 'feed')}. This runs in the background; "
            "Stop Checking reports what has been checked so far."
        )
        safe_mode = self._safe_mode

        def _do_validate(**_kwargs: object) -> list[OpmlValidationResult]:
            return opml_import.validate_feeds(
                feeds,
                on_progress=lambda done, total: self._post(
                    generation, self._on_progress, done, total
                ),
                on_started=lambda title, url: self._post(
                    generation, self._feed_started, title, url
                ),
                on_result=lambda result: self._post(generation, self._feed_checked, result),
                should_cancel=cancelled.is_set,
                safe_mode=safe_mode,
            )

        self._task_manager.submit(
            "podcast-opml-validate",
            _do_validate,
            on_success=lambda _op, results: (
                self._on_validated(results) if not cancelled.is_set() else None
            ),
            on_failure=lambda _op, _error: (
                self._on_validation_failed() if not cancelled.is_set() else None
            ),
        )

    def _post(self, generation: int, callback: Any, *args: Any) -> None:
        def deliver() -> None:
            if generation == self._generation and not self._cancel_event.is_set() and self.dialog:
                callback(*args)

        self._wx.CallAfter(deliver)

    def _feed_started(self, title: str, url: str) -> None:
        self._active_feeds[url] = title
        self._on_progress(len(self._results), self._gauge.GetRange())

    def _feed_checked(self, result: OpmlValidationResult) -> None:
        self._active_feeds.pop(result.feed_url, None)
        self._results.append(result)

    def _on_progress(self, done: int, total: int) -> None:
        if not self.dialog:  # destroyed while the sweep was running
            return
        try:
            self._gauge.SetValue(done)
            # Paced: the percentage below is spoken every few per cent.
            active = "; ".join(self._active_feeds.values())
            say_status(
                self._status,
                f"Checking feeds: {done} of {total}."
                + (f" Currently checking: {active}." if active else ""),
                speak=False,
            )
        except RuntimeError:
            return
        percent = int(done * 100 / total) if total else 100
        if percent - self._last_announced_percent >= _ANNOUNCE_EVERY_PERCENT:
            self._last_announced_percent = percent
            self._announce(f"Checking feeds: {percent} per cent")

    def _on_cancel_check(self, _event: object) -> None:
        if not self._running or not self._cancel_check_btn.IsEnabled():
            return
        self._cancelled = True
        self._cancel_event.set()
        self._running = False
        self._cancel_check_btn.Enable(False)
        self._set_status("Feed checking stopped. Everything already imported is kept.")
        self._finish()

    def _on_validated(self, results: list[OpmlValidationResult]) -> None:
        # A feed the server says has moved for good is pointed at its new
        # address -- where that podcast's "Follow permanent feed redirects"
        # allows it, the same rule a refresh follows -- and the report says
        # which were updated and which were left alone (check.md bug 5).
        self._results = opml_import.apply_permanent_moves(self._library, list(results))
        if any(result.applied for result in self._results):
            self._on_library_changed()
        self._running = False
        try:
            self._cancel_check_btn.Enable(False)
        except RuntimeError:
            return
        from quill.core.counted import plural

        unreachable = sum(1 for result in self._results if not result.ok)
        self._set_status(
            f"Checked {plural(len(self._results), 'feed')}: {unreachable} unreachable."
            + (" (Stopped early.)" if self._cancelled else "")
        )
        self._finish()

    def _on_validation_failed(self) -> None:
        """The feed check itself broke: say so, rather than "checked 0 feeds".

        It used to land in ``_on_validated`` with an empty list, which reported
        zero feeds checked and zero unreachable -- a success-shaped sentence for
        a check that never ran (qc.md 6b item 20). The import itself is already
        committed by this point, so the sentence says that too, and names where
        the same question can be asked later. No exception text: it can carry a
        feed address, and the listener cannot act on a traceback.
        """
        self._results = []
        self._running = False
        try:
            self._cancel_check_btn.Enable(False)
        except RuntimeError:
            return
        message = (
            "The feed check could not run. Everything you imported is kept; "
            "Podcasts, Feed Check shows which feeds are healthy."
        )
        self._set_status(message)  # set and spoken
        self._finish()

    # -- report ---------------------------------------------------------

    def _finish(self) -> None:
        plan = self._plan
        if plan is None:
            return
        from quill.ui.podcasts.opml_import_report_dialog import OpmlImportReportDialog

        findings = {
            "results": self._results,
            "skipped_duplicates": [*plan.duplicates_in_library, *plan.duplicates_in_file],
            "possible_duplicates": plan.same_title_different_feed,
            "unusable": [f"{entry}: {reason}" for entry, reason in plan.unusable],
            "source_opml": self._source_text,
        }
        report = self._host.__dict__.get("_opml_import_report_window")
        if report is not None and report.frame:
            report.set_findings(**findings)
        else:
            report = OpmlImportReportDialog(
                self._host.frame,
                **findings,
                announce_cb=self._announce,
                host=self._host,
            )
        report.show(focus=False)
        self._announce("The OPML import report is ready in the Window menu.")

    def _set_status(self, text: str, *, speak: bool = True) -> None:
        say_status(self._status, text, self._announce, speak=speak)


def open_import_window(host: Any, path: Path) -> OpmlImportDialog:
    """Keep one live import window; a second request never discards its operation."""
    from quill.ui.podcasts.peer_window import open_peer

    window = host.__dict__.get("_opml_import_window")
    if window is not None and window.frame:
        if window._running:
            host._announce(
                "An import is already running. Stop its feed check before importing another file."
            )
        else:
            window.set_path(path)

    def imported(show_ids: list[str]) -> None:
        host._podcast_library_added_to()
        host._start_new_podcast_feed_check(
            show_ids,
            action="Refresh Imported Feeds",
            only_if_automatic_checks_enabled=True,
        )

    return open_peer(
        host,
        "_opml_import_window",
        lambda owner: OpmlImportDialog(
            owner.frame,
            library=owner._podcast_library,
            path=path,
            task_manager=owner._task_manager,
            safe_mode=owner._safe_mode,
            announce_cb=owner._announce,
            on_library_changed=owner._save_podcast_library,
            on_import_finished=imported,
            host=owner,
        ),
    )
