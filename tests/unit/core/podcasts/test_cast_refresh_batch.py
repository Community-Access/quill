"""Checking many feeds as a bounded batch, and one feed against a deadline (F-09).

``FeedRefreshBatch`` is wx-free and drives nothing itself: each test hands it a
``start`` that records what it was asked to fetch, and answers by calling
``report`` -- exactly what ``ui/podcasts/feed_refresh.py`` does from the UI
thread when a fetch comes back.
"""

from __future__ import annotations

import time

import pytest

from quill.core.podcasts import feed_reader
from quill.core.podcasts.refresh_batch import (
    FeedRefreshBatch,
    finished_sentence,
    milestone_sentence,
)
from quill.stability.task_manager import CancelledError


class _Recorder:
    def __init__(self) -> None:
        self.started: list[str] = []
        self.said: list[str] = []
        self.finished: list[FeedRefreshBatch] = []

    def batch(self, **kwargs: object) -> FeedRefreshBatch:
        return FeedRefreshBatch(
            start=lambda show_id, _batch: self.started.append(show_id),
            on_milestone=self.said.append,
            on_finished=self.finished.append,
            **kwargs,  # type: ignore[arg-type]
        )


def test_no_more_than_the_limit_is_ever_in_flight() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=3)
    assert batch.extend([f"s{i}" for i in range(10)]) == 10
    assert rec.started == ["s0", "s1", "s2"]
    assert (batch.in_flight, batch.waiting) == (3, 7)
    batch.report("s1", ok=True)
    assert rec.started[-1] == "s3"
    for show_id in list(rec.started):
        batch.report(show_id, ok=True)
    while batch.in_flight:
        for show_id in rec.started[-batch.in_flight :]:
            batch.report(show_id, ok=True)
    assert batch.peak_in_flight == 3
    assert batch.done == 10 and batch.finished
    assert rec.finished == [batch]


def test_extend_skips_what_is_already_waiting_or_in_flight() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=1)
    batch.extend(["a", "b"])
    assert batch.extend(["a", "b", "c"]) == 1
    assert batch.total == 3


def test_extend_skips_a_feed_that_already_completed() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=1)
    batch.extend(["a", "b"])
    batch.report("a", ok=True)
    assert batch.extend(["a", "c"]) == 1
    assert rec.started == ["a", "b"]
    assert batch.total == 3


def test_cancel_starts_nothing_more_and_finishes_when_the_last_fetch_stops() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=2)
    batch.extend(["a", "b", "c", "d"])
    assert batch.cancel() is True
    assert batch.is_cancelled() and batch.waiting == 0
    assert rec.finished == []  # two fetches still in flight
    batch.report("a", ok=False, stopped=True)
    batch.report("b", ok=True)
    assert rec.started == ["a", "b"]
    assert rec.finished == [batch]
    assert (batch.done, batch.failed) == (1, 0)  # a stopped fetch is not a failure
    assert batch.cancel() is False
    assert batch.extend(["e"]) == 0


def test_milestones_are_spoken_once_per_quarter_and_never_per_feed() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=40)
    ids = [f"s{i}" for i in range(40)]
    batch.extend(ids)
    for index, show_id in enumerate(ids):
        batch.report(show_id, ok=index % 10 != 0)
    assert rec.said == [
        "Checked 10 of 40 feeds. 1 failed.",
        "Checked 20 of 40 feeds. 2 failed.",
        "Checked 30 of 40 feeds. 3 failed.",
    ]


def test_a_small_check_has_no_milestones() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=5)
    batch.extend(["a", "b", "c", "d"])
    for show_id in ["a", "b", "c", "d"]:
        batch.report(show_id, ok=True)
    assert rec.said == []
    assert batch.finished


def test_a_feed_that_cannot_start_is_counted_failed_and_the_rest_go_on() -> None:
    started: list[str] = []

    def start(show_id: str, batch: FeedRefreshBatch) -> None:
        if show_id == "bad":
            raise RuntimeError("no")
        started.append(show_id)

    batch = FeedRefreshBatch(start=start, limit=1)
    batch.extend(["bad", "good"])
    assert started == ["good"]
    assert batch.failed == 1


def test_an_answer_reported_twice_or_for_a_stranger_changes_nothing() -> None:
    rec = _Recorder()
    batch = rec.batch(limit=2)
    batch.extend(["a"])
    batch.report("a", ok=True)
    batch.report("a", ok=False)
    batch.report("zzz", ok=False)
    assert (batch.done, batch.failed) == (1, 0)


def test_the_sentences() -> None:
    assert milestone_sentence(1, 1, 0) == "Checked 1 of 1 feed."
    assert finished_sentence(10, 10, 0, cancelled=False) == "Finished checking 10 feeds."
    assert finished_sentence(10, 10, 2, cancelled=False) == (
        "Finished checking 10 feeds. 2 failed; Feed Check lists them."
    )
    assert finished_sentence(4, 1500, 0, cancelled=True) == (
        "Stopped checking feeds. 4 of 1,500 feeds were checked."
    )


@pytest.mark.perf
def test_fifteen_hundred_feeds_that_answer_at_once_neither_recurse_nor_go_quadratic() -> None:
    """A start that answers synchronously (a fake, or a start that fails at once)
    must not nest one frame per feed, and the bookkeeping must stay linear."""
    batch: FeedRefreshBatch | None = None

    def start(show_id: str, owner: FeedRefreshBatch) -> None:
        owner.report(show_id, ok=True, new_episodes=1)

    batch = FeedRefreshBatch(start=start, limit=3)
    began = time.perf_counter()
    batch.extend([f"s{i}" for i in range(1500)])
    elapsed = time.perf_counter() - began
    assert batch.finished and batch.done == 1500 and batch.new_episodes == 1500
    assert batch.peak_in_flight <= 3
    assert elapsed < 2.0, f"1,500 synchronous feeds took {elapsed:.2f}s"


# -- one feed, bounded -------------------------------------------------------------- #


class _Dribble:
    """A response that hands back one byte per read, for ever."""

    def __init__(self) -> None:
        self.reads = 0

    def read(self, _n: int = -1) -> bytes:
        self.reads += 1
        return b"x"


def test_a_feed_that_dribbles_past_its_deadline_is_stopped() -> None:
    response = _Dribble()
    with pytest.raises(feed_reader.FeedTimeoutError) as caught:
        feed_reader._read_bounded(response, time.monotonic() + 0.05, None)
    assert caught.value.code == "QUILL-PODCASTS-FEED-TIMEOUT"
    assert response.reads > 1


def test_a_stopped_check_stops_a_fetch_between_reads() -> None:
    response = _Dribble()
    answers = iter([False, False, True])
    with pytest.raises(CancelledError):
        feed_reader._read_bounded(response, None, lambda: next(answers))
    assert response.reads == 2


def test_without_bounds_the_body_is_read_in_one_call_as_before() -> None:
    class _Whole:
        def __init__(self) -> None:
            self.sizes: list[int] = []

        def read(self, n: int = -1) -> bytes:
            self.sizes.append(n)
            return b"<rss/>"

    response = _Whole()
    assert feed_reader._read_bounded(response, None, None) == b"<rss/>"
    assert response.sizes == [feed_reader._MAX_BYTES]


def test_a_cancelled_check_does_not_parse_what_it_fetched(monkeypatch) -> None:
    monkeypatch.setattr(feed_reader, "_fetch_feed_bytes", lambda *a, **k: b"<rss/>")
    parsed: list[bytes] = []
    monkeypatch.setattr(feed_reader, "parse_feed", parsed.append)
    with pytest.raises(CancelledError):
        feed_reader.fetch_and_parse_feed("https://example.invalid/f", is_cancelled=lambda: True)
    assert parsed == []
