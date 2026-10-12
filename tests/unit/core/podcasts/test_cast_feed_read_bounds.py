"""One feed against a deadline, and a stopped check (F-09).

Kept from the retired refresh-batch tests when QUILL Cast's feed checks moved to
``check_monitor`` and ``check_run``: the batch went, but the bounds on a single
fetch live in ``feed_reader`` and still need saying.
"""

from __future__ import annotations

import time

import pytest

from quill.core.podcasts import feed_reader
from quill.stability.task_manager import CancelledError


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
