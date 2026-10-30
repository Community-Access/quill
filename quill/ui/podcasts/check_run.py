"""One Refresh All Now, from "Checking 12 feeds" to one sentence at the end (qc.md F-10).

A check of every feed finishes show by show over the next few seconds, and
until now it never finished out loud: each podcast with something new said
so, and silence meant either "nothing new" or "still going". This keeps a
small tally for a run the listener started (F5, Refresh All Now):

* progress milestones through the shared :class:`~quill.core.activity.ProgressAnnouncer`
  -- "Checking feeds, 50 percent" -- never a sentence per feed;
* one result when the last feed answers, through the shared
  :func:`~quill.ui.activity_window.report_result`, so F9 repeats it and
  Activity (Shift+F9) lists it: "Checked 12 feeds: 3 new episodes from 2
  podcasts. 1 could not be read." with Retry when anything failed.

A background check on a timer keeps its own quieter behaviour; only a run a
person asked for is tallied.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from quill.core import activity
from quill.ui.dpi import dip_size

__all__ = ["CheckRun", "finish_sentence", "start", "step"]


@dataclass(slots=True)
class CheckRun:
    total: int
    action: str = "Refresh All Now"
    requested_total: int = 0
    pending: set[str] = field(default_factory=set)
    done: int = 0
    new_episodes: int = 0
    podcasts_with_new: int = 0
    failed: list[str] = field(default_factory=list)
    token: object = field(default_factory=object)
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    announcer: activity.ProgressAnnouncer | None = None
    cancelled: bool = False
    progress_window: Any = None
    active_feeds: dict[str, str] = field(default_factory=dict)


def start(host: Any, show_ids: list[str], *, action: str = "Refresh All Now") -> CheckRun | None:
    """Begin tallying a run over *show_ids*, the checks the listener asked for."""
    if not show_ids:
        host._check_run = None
        return None
    run = CheckRun(
        total=len(show_ids),
        requested_total=len(show_ids),
        action=action,
        pending=set(show_ids),
    )
    run.announcer = activity.ProgressAnnouncer(step=25, owner_token=run.token)
    # The phase sentence was already said by the caller ("Checking 12
    # feeds..."), so the announcer starts in that phase.
    run.announcer.next_sentence(_progress(run))
    activity.LOG.begin(_progress(run))  # listed in Activity while it runs (X-04)
    host._check_run = run
    _show_progress_window(host, run)
    return run


def _progress(run: CheckRun) -> activity.Progress:
    return activity.Progress(
        operation_id=run.operation_id,
        phase="checking",
        message="Checking feeds",
        current=run.done,
        total=run.total,
        owner_token=run.token,
    )


def finish_sentence(run: CheckRun) -> str:
    total = run.requested_total or run.total
    feeds = f"{total} feed{'s' if total != 1 else ''}"
    if run.cancelled:
        feeds = f"{run.done} of {feeds}"
    if run.new_episodes:
        eps = f"{run.new_episodes} new episode{'s' if run.new_episodes != 1 else ''}"
        pods = f"{run.podcasts_with_new} podcast{'s' if run.podcasts_with_new != 1 else ''}"
        sentence = f"Checked {feeds}: {eps} from {pods}."
    else:
        sentence = f"Checked {feeds}: nothing new."
    if run.cancelled:
        sentence = f"Stopped. {sentence}"
    if run.failed:
        count = len(run.failed)
        sentence += f" {count} could not be read" + (
            f": {run.failed[0]}." if count == 1 else "; Recent Problems has them."
        )
    return sentence


class _FeedProgressWindow:
    TITLE = "Feed Refresh Progress"
    MENU_TITLE = "&Feed Refresh"

    def __init__(self, host: Any, run: CheckRun) -> None:
        wx = host._wx
        self._host = host
        self.frame = wx.Frame(
            host.frame, title="Feed Refresh Progress", style=wx.DEFAULT_FRAME_STYLE
        )
        panel = wx.Panel(self.frame)
        layout = wx.BoxSizer(wx.VERTICAL)
        status_label = wx.StaticText(panel, label="Feed refresh status and active podcasts:")
        layout.Add(status_label, 0, wx.LEFT | wx.RIGHT | wx.TOP, 12)
        self.status = wx.TextCtrl(panel, style=wx.TE_MULTILINE | wx.TE_READONLY)
        self.status.SetName("Feed refresh status and active podcasts")
        self.status.SetHelpText(
            "Shows completed feed counts and the podcasts currently being checked. "
            "Window menu, Control Tab, and Alt Tab return to the library without stopping."
        )
        layout.Add(self.status, 1, wx.EXPAND | wx.ALL, 12)
        progress_label = wx.StaticText(panel, label="Feed refresh progress:")
        layout.Add(progress_label, 0, wx.LEFT | wx.RIGHT, 12)
        self.gauge = wx.Gauge(panel, range=max(run.requested_total, 1))
        self.gauge.SetName("Feed refresh progress")
        self.gauge.SetHelpText("The number of feeds checked so far.")
        layout.Add(self.gauge, 0, wx.EXPAND | wx.LEFT | wx.RIGHT | wx.BOTTOM, 12)
        self.stop = wx.Button(panel, label="&Stop")
        self.stop.SetName("Stop feed checks")
        self.stop.SetHelpText(
            "Stop this refresh immediately. Queued requests are cancelled and late results "
            "from requests already running are ignored. Completed checks are kept."
        )
        self.stop.SetDefault()
        layout.Add(self.stop, 0, wx.EXPAND | wx.ALL, 12)
        panel.SetSizer(layout)
        outer = wx.BoxSizer(wx.VERTICAL)
        outer.Add(panel, 1, wx.EXPAND)
        self.frame.SetSizer(outer)
        self.frame.SetMinSize(dip_size(self.frame, 440, 240))
        self.stop.Bind(wx.EVT_BUTTON, lambda _event: cancel_remaining(host))

    def focus_target(self) -> Any:
        return self.status

    def menu_rows(self) -> list[tuple[str, Any]]:
        return [("Stop checks\tAlt+S", lambda: cancel_remaining(self._host))]


def _show_progress_window(host: Any, run: CheckRun) -> None:
    wx = getattr(host, "_wx", None)
    parent = getattr(host, "frame", None)
    if wx is None or parent is None or not callable(getattr(wx, "Frame", None)):
        return

    from quill.ui.podcasts.peer_window import open_peer

    peer = open_peer(
        host,
        "_podcast_feed_progress_window",
        lambda owner: _FeedProgressWindow(owner, run),
        focus=False,
    )
    peer.gauge.SetRange(max(run.requested_total, 1))
    peer.stop.Enable(True)
    run.progress_window = (peer.frame, peer.status, peer.gauge, peer.stop)
    _update_progress_window(run)


def _update_progress_window(run: CheckRun) -> None:
    controls = run.progress_window
    if not controls:
        return
    _window, label, gauge, _cancel = controls
    gauge.SetValue(min(run.done, run.requested_total))
    message = (
        f"Checked {run.done} of {run.requested_total} feeds."
        if not run.cancelled
        else f"Stopped: checked {run.done} of {run.requested_total} feeds."
    )
    if run.active_feeds:
        message += "\nCurrently checking:\n" + "\n".join(run.active_feeds.values())
    label.ChangeValue(message)


def started(host: Any, show_id: str, title: str) -> None:
    """Expose active feed names without a spoken sentence per request."""
    run = getattr(host, "_check_run", None)
    if run is not None and show_id in run.pending:
        run.active_feeds[show_id] = title
        _update_progress_window(run)


def cancel_remaining(host: Any) -> None:
    """Stop delivery immediately, preserving only checks already committed."""
    run: CheckRun | None = getattr(host, "_check_run", None)
    monitor = getattr(host, "_podcast_check_monitor", None)
    if run is None:
        return
    from quill.ui.podcasts.feed_refresh import shutdown_feed_checks

    shutdown_feed_checks(host)
    cancel_all = getattr(monitor, "cancel_all", None)
    if callable(cancel_all):
        cancel_all()
    run.pending.clear()
    run.active_feeds.clear()
    run.total = run.done
    run.cancelled = True
    activity.LOG.update(_progress(run))
    _update_progress_window(run)
    if not run.pending:
        _finish(host, run)


def step(host: Any, show_id: str, *, new_episodes: int = 0, failed_title: str = "") -> None:
    """One feed of the run answered. Says a milestone, or the result at the end."""
    run: CheckRun | None = getattr(host, "_check_run", None)
    if run is None or show_id not in run.pending:
        monitor = getattr(host, "_podcast_check_monitor", None)
        completed = getattr(monitor, "refresh_completed", None)
        if callable(completed):
            completed(show_id)
        return
    run.pending.discard(show_id)
    run.active_feeds.pop(show_id, None)
    monitor = getattr(host, "_podcast_check_monitor", None)
    completed = getattr(monitor, "refresh_completed", None)
    if callable(completed):
        completed(show_id)
    run.done += 1
    _update_progress_window(run)
    if failed_title:
        run.failed.append(failed_title)
    elif new_episodes:
        run.new_episodes += new_episodes
        run.podcasts_with_new += 1
    activity.LOG.update(_progress(run))
    if run.done < run.total:
        said = run.announcer.next_sentence(_progress(run)) if run.announcer else None
        if said:
            from quill.ui.quiet_hours_ui import speak_background

            speak_background(host, said)
        return
    _finish(host, run)


def _finish(host: Any, run: CheckRun) -> None:
    # The sweep has finished. Let Cast publish its deferred tree update once,
    # even if an earlier periodic save already cleared the dirty flag.
    host._check_run = None
    maintenance = getattr(host, "podcast_run_maintenance", None)
    if not run.cancelled and callable(maintenance):
        maintenance()
    flush = getattr(host, "_flush_podcast_library", None)
    if (
        getattr(host, "_podcast_library_dirty", False)
        or getattr(host, "_tree_reload_pending", False)
    ) and callable(flush):
        flush()
    manager = getattr(host, "_podcast_manager_dialog", None)
    refresh_tree = getattr(manager, "refresh_tree", None)
    if callable(refresh_tree):
        refresh_tree()
    activity.LOG.end(run.operation_id)
    controls = run.progress_window
    if controls:
        controls[1].ChangeValue(finish_sentence(run))
        controls[3].Enable(False)
    from quill.ui.activity_window import report_result

    outcome = (
        activity.CANCELLED
        if run.cancelled
        else activity.PARTIAL
        if run.failed
        else activity.COMPLETED
    )
    actions = {}
    next_actions: tuple[activity.NextAction, ...] = ()
    retry = getattr(host, "_on_check_all_feeds", None)
    if run.failed and run.action == "Refresh All Now" and callable(retry):
        next_actions = (activity.RETRY,)
        actions = {activity.RETRY.id: lambda: retry() or "Checking again."}
    report_result(
        host,
        activity.ActionResult(
            action=run.action,
            object_name=f"{run.requested_total or run.total} feeds",
            outcome=outcome,
            summary=finish_sentence(run),
            next_actions=next_actions,
            operation_id=run.operation_id,
        ),
        actions,
    )
