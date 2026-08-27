"""Tests for per-source health -- the record of how a directory has been doing.

The contract this file pins down is as much about what does *not* happen: no
source is ever switched off automatically, an empty answer is never a fault, and
the record lives in this process only.
"""

from __future__ import annotations

import pytest

from quill.core.radio import browse_sources as bs
from quill.core.radio import shoutcast, source_health


@pytest.fixture(autouse=True)
def _clean_slate() -> None:
    source_health.reset()
    yield
    source_health.reset()


def test_a_source_never_tried_is_unknown_not_broken() -> None:
    record = source_health.health("shoutcast")
    assert record.status == "unknown"
    assert source_health.status_text("shoutcast") == "Not tried yet"
    assert not record.in_trouble


def test_an_empty_answer_is_not_a_failure() -> None:
    """A genre with nothing in it is a true answer, not an outage."""
    source_health.record_ok("xiph", empty=True)
    assert source_health.consecutive_failures("xiph") == 0
    assert source_health.status_text("xiph") == "Nothing found"


def test_failures_accumulate_and_a_success_clears_them() -> None:
    for _ in range(2):
        source_health.record_error("tunein", TimeoutError("timed out"))
    assert source_health.consecutive_failures("tunein") == 2
    assert source_health.status_text("tunein") == "Failed 2 times in a row"
    source_health.record_ok("tunein")
    assert source_health.consecutive_failures("tunein") == 0
    assert source_health.status_text("tunein") == "OK"
    # The lifetime totals survive the recovery, for a diagnostic bundle.
    assert source_health.health("tunein").error_count == 2


def test_three_in_a_row_is_trouble_and_says_where_the_switch_is() -> None:
    for _ in range(source_health.TROUBLE_THRESHOLD):
        source_health.record_error("live365", OSError("no route to host"))
    assert source_health.in_trouble("live365")
    note = source_health.failure_note("live365")
    assert "3 times in a row" in note
    assert "Browse Sources" in note


def test_the_first_failure_says_nothing_extra() -> None:
    """One failure is already explained by "could not be reached"."""
    source_health.record_error("live365", OSError("blip"))
    assert source_health.failure_note("live365") == ""


def test_a_long_error_message_is_trimmed_because_it_is_read_aloud() -> None:
    source_health.record_error("archive", "x" * 400)
    assert len(source_health.health("archive").message) <= 120


def test_nothing_is_ever_disabled_automatically() -> None:
    """StreamTuner-ng trips a plugin off after three; we report and leave it on."""
    for _ in range(10):
        source_health.record_error("tunein", OSError("down"))
    from quill.core.radio import browse_visibility

    assert browse_visibility.is_enabled(browse_visibility.default_enabled(), "tunein")


def test_browsing_records_the_outcome(monkeypatch) -> None:
    monkeypatch.setattr(shoutcast, "fetch_genres", lambda **_kw: ["Jazz"])
    assert bs.browse("shoutcast")
    assert source_health.status_text("shoutcast") == "OK"

    def _fail(**_kw):
        raise shoutcast.ShoutcastError("down")

    monkeypatch.setattr(shoutcast, "fetch_genres", _fail)
    assert bs.browse("shoutcast") == []
    assert bs.browse("shoutcast") == []
    assert source_health.consecutive_failures("shoutcast") == 2
    # ...and that is what an empty branch will add to its one explanatory row.
    assert "2 times in a row" in bs.repeat_failure_note("shoutcast")
    assert bs.repeat_failure_note("live365") == ""


def test_the_note_follows_the_source_not_the_sub_branch(monkeypatch) -> None:
    def _fail(_genre, **_kw):
        raise shoutcast.ShoutcastError("down")

    monkeypatch.setattr(shoutcast, "fetch_genre_stations", _fail)
    bs.browse("shoutcast:Jazz")
    bs.browse("shoutcast:Blues")
    # Both are the same source, so the count is the source's.
    assert source_health.consecutive_failures("shoutcast") == 2


def test_a_snapshot_reads_every_source() -> None:
    source_health.record_ok("soma")
    source_health.record_error("tunein", "down")
    snapshot = source_health.snapshot()
    assert set(snapshot) == {"soma", "tunein"}
    assert snapshot["soma"].status == "ok"
