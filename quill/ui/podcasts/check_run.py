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

__all__ = ["CheckRun", "finish_sentence", "start", "step"]


@dataclass(slots=True)
class CheckRun:
    total: int
    pending: set[str] = field(default_factory=set)
    done: int = 0
    new_episodes: int = 0
    podcasts_with_new: int = 0
    failed: list[str] = field(default_factory=list)
    token: object = field(default_factory=object)
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    announcer: activity.ProgressAnnouncer | None = None


def start(host: Any, show_ids: list[str]) -> CheckRun | None:
    """Begin tallying a run over *show_ids*, the checks the listener asked for."""
    if not show_ids:
        host._check_run = None
        return None
    run = CheckRun(total=len(show_ids), pending=set(show_ids))
    run.announcer = activity.ProgressAnnouncer(step=25, owner_token=run.token)
    # The phase sentence was already said by the caller ("Checking 12
    # feeds..."), so the announcer starts in that phase.
    run.announcer.next_sentence(_progress(run))
    activity.LOG.begin(_progress(run))  # listed in Activity while it runs (X-04)
    host._check_run = run
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
    feeds = f"{run.total} feed{'s' if run.total != 1 else ''}"
    if run.new_episodes:
        eps = f"{run.new_episodes} new episode{'s' if run.new_episodes != 1 else ''}"
        pods = f"{run.podcasts_with_new} podcast{'s' if run.podcasts_with_new != 1 else ''}"
        sentence = f"Checked {feeds}: {eps} from {pods}."
    else:
        sentence = f"Checked {feeds}: nothing new."
    if run.failed:
        count = len(run.failed)
        sentence += f" {count} could not be read" + (
            f": {run.failed[0]}." if count == 1 else "; Recent Problems has them."
        )
    return sentence


def step(host: Any, show_id: str, *, new_episodes: int = 0, failed_title: str = "") -> None:
    """One feed of the run answered. Says a milestone, or the result at the end."""
    run: CheckRun | None = getattr(host, "_check_run", None)
    if run is None or show_id not in run.pending:
        return
    run.pending.discard(show_id)
    run.done += 1
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
    host._check_run = None
    activity.LOG.end(run.operation_id)
    from quill.ui.activity_window import report_result

    outcome = activity.PARTIAL if run.failed else activity.COMPLETED
    actions = {}
    next_actions: tuple[activity.NextAction, ...] = ()
    retry = getattr(host, "_on_check_all_feeds", None)
    if run.failed and callable(retry):
        next_actions = (activity.RETRY,)
        actions = {activity.RETRY.id: lambda: retry() or "Checking again."}
    report_result(
        host,
        activity.ActionResult(
            action="Refresh All Now",
            object_name=f"{run.total} feeds",
            outcome=outcome,
            summary=finish_sentence(run),
            next_actions=next_actions,
            operation_id=run.operation_id,
        ),
        actions,
    )
