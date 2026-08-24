"""Download All as a bounded, counted batch.

Two problems with an unbounded "queue everything": a show with a decade of
back catalogue starts eight hundred downloads from one keypress, and the
only thing said out loud is a single number that hides what happened to the
rest. This module answers both -- a cap per invocation, and exact counts for
every episode the action touched: how many were eligible, how many started,
how many were skipped because the file is already here or already coming,
and how many were deferred to the next run.

Pure and wx-free so both Quill Cast and Quill Radio can say the same
sentence, and so the counting can be tested without a queue.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

# The batch is generic in its row type (PEP 695): Quill Cast passes
# ``PodcastEpisode``, Quill Radio the ``RadioStation`` rows its download queue
# takes. The counting is about *rows*, not about what a row happens to be
# (11.4 / 2.1).

#: How many episodes one Download All may start. Fifty is a batch a slow
#: connection can finish in an evening; the rest are deferred rather than
#: dropped, and a second Download All picks up where this one stopped.
BATCH_CAP = 50


@dataclass(frozen=True)
class DownloadBatch[RowT]:
    """What one Download All did, in numbers that can be read aloud."""

    #: The episodes to enqueue now, in feed order.
    started: tuple[RowT, ...]
    #: Already downloaded, or already in the download queue.
    skipped: int
    #: Eligible, but over the cap -- the next Download All will take them.
    deferred: int

    @property
    def eligible(self) -> int:
        """Episodes that could be downloaded: started plus deferred."""
        return len(self.started) + self.deferred

    def sentence(self, show_title: str) -> str:
        """The spoken summary. Every clause carries a number, always."""
        title = show_title or "this show"
        if not self.started:
            if self.skipped:
                return (
                    f"Nothing to download for {title}: all {self.skipped} episode(s) "
                    "are already downloaded or in progress."
                )
            return f"Nothing to download for {title}: it has no episodes yet."
        parts = [f"{self.eligible} eligible", f"{len(self.started)} started"]
        if self.skipped:
            parts.append(f"{self.skipped} skipped as already downloaded or in progress")
        if self.deferred:
            parts.append(f"{self.deferred} deferred -- run Download All again for the next batch")
        return f"Download All for {title}: " + ", ".join(parts) + "."


def plan_download_all[RowT](
    episodes: Iterable[RowT],
    *,
    already_have: Callable[[RowT], bool],
    cap: int = BATCH_CAP,
) -> DownloadBatch[RowT]:
    """Split *episodes* into started / skipped / deferred.

    *already_have* answers "is this one downloaded or queued already?" --
    each caller knows that differently (Cast asks its download queue, Radio
    its download manager), and neither should have to know the counting.
    """
    started: list[RowT] = []
    skipped = 0
    deferred = 0
    for episode in episodes:
        if already_have(episode):
            skipped += 1
        elif len(started) < cap:
            started.append(episode)
        else:
            deferred += 1
    return DownloadBatch(started=tuple(started), skipped=skipped, deferred=deferred)
