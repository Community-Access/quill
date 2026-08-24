"""When a subscribed feed is checked, and which feeds are checked at all.

The rules that used to be spread across three places -- QUILL Cast's monitor,
Quill Radio's absence of one, and a ``paused`` flag two code paths disagreed
about -- now live in one pure module, so they can be pinned here rather than
inferred from the behaviour of two apps.

Three of these are regressions, not coverage:

* ``force`` reaching :func:`shows_to_refresh` at all. Radio's worker took the
  argument, documented it, and never passed it on, so Refresh on a paused show
  quietly checked nothing.
* the shared stamp being claimed *before* the fetch rather than after.
* ``is_due`` answering False for a manual cadence, which is what stops an
  interval of zero from meaning "always".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from quill.core.podcasts import refresh_policy as policy


@dataclass
class _Show:
    feed_url: str = "https://example.com/feed.xml"
    paused: bool = False
    title: str = "A Show"
    episodes: list = field(default_factory=list)


# -- the interval ---------------------------------------------------------------


def test_zero_means_manually_and_is_the_shipped_answer() -> None:
    assert policy.DEFAULT_INTERVAL_MINUTES == 0
    assert policy.normalize_interval(0) == 0
    assert policy.INTERVAL_CHOICES[0][0] == 0


def test_an_unreadable_interval_reads_as_manual() -> None:
    """A typo in a settings file must never start traffic nobody asked for."""
    for junk in ("15", None, [], {}, True, False, object()):
        assert policy.normalize_interval(junk) == 0


def test_an_interval_is_clamped_rather_than_obeyed() -> None:
    assert policy.normalize_interval(1) == policy.MIN_INTERVAL_MINUTES
    assert policy.normalize_interval(10**9) == policy.MAX_INTERVAL_MINUTES
    assert policy.normalize_interval(-5) == 0


def test_a_hand_edited_interval_shows_the_nearest_row_at_or_below_it() -> None:
    """Showing something true beats silently rewriting somebody's number."""
    assert policy.INTERVAL_CHOICES[policy.interval_index(45)][0] == 30
    assert policy.interval_index(15) == 1
    assert policy.interval_index(0) == 0


def test_the_index_round_trips_through_a_wx_selection() -> None:
    for position, (minutes, _label) in enumerate(policy.INTERVAL_CHOICES):
        assert policy.interval_from_index(position) == minutes
        assert policy.interval_index(minutes) == position


def test_an_out_of_range_selection_is_the_default_rather_than_a_crash() -> None:
    for junk in (-1, len(policy.INTERVAL_CHOICES), "1", None):
        assert policy.interval_from_index(junk) == 0


# -- which shows ----------------------------------------------------------------


def test_a_show_with_no_feed_cannot_be_refreshed_even_forced() -> None:
    """Audio dropped into a watched folder has no publisher to ask."""
    local = _Show(feed_url="")
    assert policy.can_refresh(local) is False
    assert policy.shows_to_refresh([local]) == []
    assert policy.shows_to_refresh([local], force=True) == []


def test_the_automatic_check_leaves_a_paused_show_alone() -> None:
    live, paused = _Show(), _Show(paused=True)
    assert policy.shows_to_refresh([live, paused]) == [live]


def test_refresh_on_a_paused_show_checks_it_anyway() -> None:
    """The pause must never mean unreachable -- that would make it a trap."""
    live, paused = _Show(), _Show(paused=True)
    assert policy.shows_to_refresh([live, paused], force=True) == [live, paused]


# -- the shared stamp -----------------------------------------------------------


def test_a_manual_cadence_is_never_due() -> None:
    """Zero minutes must not read as "no interval has elapsed, so go"."""
    assert policy.is_due("", 0, 1_000_000.0) is False
    assert policy.is_due(policy.stamp_now(0.0), 0, 1_000_000.0) is False


def test_never_checked_is_due() -> None:
    """The safe direction: the worst case is one extra fetch."""
    assert policy.is_due("", 60, 1_000_000.0) is True
    assert policy.is_due(None, 60, 1_000_000.0) is True
    assert policy.is_due("not a timestamp", 60, 1_000_000.0) is True


def test_a_check_the_other_app_just_ran_is_not_due() -> None:
    now = 1_000_000.0
    stamp = policy.stamp_now(now - 60)
    assert policy.is_due(stamp, 60, now) is False


def test_a_check_an_interval_ago_is_due() -> None:
    now = 1_000_000.0
    assert policy.is_due(policy.stamp_now(now - 3600), 60, now) is True


def test_two_timers_seconds_apart_count_as_the_same_tick() -> None:
    """The tolerance is what stops both apps deciding they are the one."""
    now = 1_000_000.0
    a_hair_early = policy.stamp_now(now - (3600 * 0.95))
    assert policy.is_due(a_hair_early, 60, now) is True
    clearly_inside = policy.stamp_now(now - (3600 * 0.5))
    assert policy.is_due(clearly_inside, 60, now) is False


def test_the_stamp_round_trips() -> None:
    now = 1_700_000_000.0
    elapsed = policy.seconds_since(policy.stamp_now(now), now)
    assert elapsed is not None and elapsed < 1.0


def test_a_stamp_from_the_future_is_not_negative_time() -> None:
    assert policy.seconds_since(policy.stamp_now(2_000.0), 1_000.0) == 0.0


# -- what it says ---------------------------------------------------------------


def test_the_sentence_says_what_it_does_not_do() -> None:
    said = policy.describe_schedule(60)
    assert "download" in said.lower()
    assert "paused" in said.lower()


def test_manually_only_reads_as_a_choice_rather_than_an_absence() -> None:
    said = policy.describe_schedule(0)
    assert "Refresh" in said
    assert policy.describe_schedule(0, on_launch=True) != said
