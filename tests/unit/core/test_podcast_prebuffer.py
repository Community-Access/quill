"""Prebuffering the next queue item: when to, and the four times not to.

The gap between two queued episodes is not the few milliseconds people mean by
"gapless" -- it is however long it takes to open a stream and fill a buffer, which
on a poor connection is several seconds of silence in the middle of a listening
session. Having the next episode's first seconds already on disk removes that.

The refusals are the design. Speculative bytes are somebody's data allowance, so
this never runs unasked, never runs for a file already here, and never runs while
there is no cue to run on.
"""

from __future__ import annotations

import pytest

from quill.core.podcasts.models import PodcastSettings
from quill.core.podcasts.prebuffer import LEAD_MS, PREBUFFER_BYTES, describe, plan

_TEN_MINUTES = 10 * 60 * 1000


def _plan(**overrides):
    base = {
        "enabled": True,
        "position_ms": _TEN_MINUTES - 5_000,
        "duration_ms": _TEN_MINUTES,
        "next_show_id": "show",
        "next_episode_guid": "episode",
        "next_url": "https://example/next.mp3",
    }
    base.update(overrides)
    return plan(**base)


def test_it_starts_only_near_the_end() -> None:
    assert _plan().should_fetch is True
    # Early on there is nothing to gain and a whole episode's worth of chances
    # for the listener to skip somewhere else.
    early = _plan(position_ms=0)
    assert early.should_fetch is False
    assert "Not near the end" in describe(early)
    # The boundary itself is the lead window.
    assert _plan(position_ms=_TEN_MINUTES - LEAD_MS + 1).should_fetch is True
    assert _plan(position_ms=_TEN_MINUTES - LEAD_MS - 1).should_fetch is False


def test_it_is_off_unless_asked_for() -> None:
    # Speculative bytes are paid for by the megabyte on a metered connection.
    assert PodcastSettings().prebuffer_next is False
    off = _plan(enabled=False)
    assert off.should_fetch is False
    assert "switched off" in describe(off)


def test_an_episode_already_on_disk_needs_nothing() -> None:
    local = _plan(next_is_local=True)
    assert local.should_fetch is False
    assert "already on this computer" in describe(local)


def test_nothing_queued_after_this_is_not_a_failure() -> None:
    assert _plan(next_show_id="", next_episode_guid="").should_fetch is False
    assert "Nothing is queued" in describe(_plan(next_show_id=""))


def test_a_source_with_no_known_length_has_no_cue_to_fire_on() -> None:
    # A live item never becomes "nearly over", so there is no moment to start.
    unknown = _plan(duration_ms=0)
    assert unknown.should_fetch is False
    assert "no known length" in describe(unknown)


def test_it_never_repeats_work_already_done() -> None:
    assert _plan(already_prebuffered=True).should_fetch is False


def test_the_plan_says_what_to_fetch_and_how_much() -> None:
    result = _plan()
    assert result.url == "https://example/next.mp3"
    assert (result.show_id, result.episode_guid) == ("show", "episode")
    # A courtesy, not a download: capped, and it lands in the playback cache.
    assert result.byte_limit == PREBUFFER_BYTES
    assert "seconds left" in result.reason


@pytest.mark.parametrize("position", [_TEN_MINUTES, _TEN_MINUTES + 5_000])
def test_an_episode_already_over_starts_nothing(position: int) -> None:
    assert _plan(position_ms=position).should_fetch is False
