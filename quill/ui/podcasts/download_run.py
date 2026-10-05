"""Download All Episodes, from "Downloading 12" to one sentence at the end (qc.md F-10).

The download queue reports each episode as it lands, with a sound. A batch of
twelve used to end in silence: the twelfth sound was the only way to know it
was over, and a failure in the middle was a sound that did not come. This
tallies one batch the listener started:

* progress milestones through the shared :class:`~quill.core.activity.ProgressAnnouncer`
  -- "Downloading The Daily, 3 of 12, 25 percent" -- every quarter, not every file;
* one result at the end through :func:`~quill.ui.activity_window.report_result`,
  so F9 repeats it and Activity lists it, with Open Folder.

Quiet Hours hold back the milestones, never the final sentence about a batch
somebody started and is waiting for.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from quill.core import activity

__all__ = ["DownloadRun", "start", "step"]


@dataclass(slots=True)
class DownloadRun:
    title: str
    total: int
    pending: set[str] = field(default_factory=set)
    done: int = 0
    failed: list[str] = field(default_factory=list)
    folder: str = ""
    token: object = field(default_factory=object)
    operation_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    announcer: activity.ProgressAnnouncer | None = None


def _progress(run: DownloadRun) -> activity.Progress:
    return activity.Progress(
        operation_id=run.operation_id,
        phase="downloading",
        message=f"Downloading {run.title}, {run.done} of {run.total}",
        current=run.done,
        total=run.total,
        owner_token=run.token,
    )


def start(host: Any, title: str, guids: list[str], folder: Path | str | None = None) -> None:
    """Begin tallying a batch of *guids* the listener started for *title*."""
    if host is None or len(guids) < 2:
        return  # one download already says everything it needs to
    run = DownloadRun(title=title, total=len(guids), pending=set(guids), folder=str(folder or ""))
    run.announcer = activity.ProgressAnnouncer(step=25, owner_token=run.token)
    run.announcer.next_sentence(_progress(run))
    activity.LOG.begin(_progress(run))  # listed in Activity while it runs (X-04)
    host._download_run = run


def step(host: Any, guid: str, *, failed_title: str = "") -> None:
    """One episode of the batch finished (or failed)."""
    run: DownloadRun | None = getattr(host, "_download_run", None)
    if run is None or guid not in run.pending:
        return
    run.pending.discard(guid)
    run.done += 1
    if failed_title:
        run.failed.append(failed_title)
    activity.LOG.update(_progress(run))
    if run.done < run.total:
        said = run.announcer.next_sentence(_progress(run)) if run.announcer else None
        if said:
            from quill.ui.quiet_hours_ui import speak_background

            speak_background(host, said)
        return
    host._download_run = None
    activity.LOG.end(run.operation_id)
    got = run.total - len(run.failed)
    sentence = f"Downloaded {got} of {run.total} episodes of {run.title}."
    if run.failed:
        sentence += f" {len(run.failed)} failed; Recent Problems says why."
    from quill.ui.outcome_report import report_outcome

    report_outcome(
        host,
        "Download All Episodes",
        sentence,
        object_name=run.title,
        path=run.folder or None,
        failed=got == 0,
    )
