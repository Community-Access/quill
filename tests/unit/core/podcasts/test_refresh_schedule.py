"""Refresh schedules: five kinds, one next_due, one sentence (qc.md 5e)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from quill.core.podcasts import refresh_schedule as rs
from quill.core.podcasts import schedule_policy
from quill.core.podcasts.models import PodcastShow
from quill.core.podcasts.models_episode import PodcastEpisode
from quill.core.podcasts.subscriptions import PodcastLibrary

NOW = datetime(2026, 10, 6, 9, 0, tzinfo=UTC)  # a Tuesday


def test_encode_and_decode_round_trip_every_kind() -> None:
    for schedule in (
        rs.Schedule(rs.MANUAL),
        rs.Schedule(rs.INTERVAL, 45),
        rs.Schedule(rs.TIMES, times=("06:00", "18:00"), days=(0, 1, 2, 3, 4)),
        rs.Schedule(rs.LEARNED),
        rs.Schedule(rs.LEARNED, pinned=(1, 6)),
        rs.Schedule(rs.PUBLISHER),
    ):
        assert rs.decode(rs.encode(schedule)) == schedule, schedule
    assert (
        rs.decode("") is None and rs.decode("junk") is None and rs.decode('{"kind": "x"}') is None
    )
    assert rs.decode(
        '{"kind": "times", "times": ["6:00", "25:00", "x"], "days": [1, 9]}'
    ) == rs.Schedule(rs.TIMES, times=("06:00",), days=(1,))
    assert rs.decode('{"kind": "interval", "minutes": 1}').minutes == 5, "clamped to five minutes"


def test_the_legacy_interval_still_answers_so_nothing_changes_on_upgrade() -> None:
    assert rs.from_legacy(0) == rs.Schedule(rs.MANUAL)
    assert rs.from_legacy("60") == rs.Schedule(rs.INTERVAL, 60)
    assert rs.from_legacy("junk") == rs.Schedule(rs.MANUAL)


def test_describe_is_one_sentence_per_kind() -> None:
    assert rs.describe(rs.Schedule(rs.MANUAL)) == "Never checks on its own."
    assert rs.describe(rs.Schedule(rs.INTERVAL, 45)) == "Every 45 minutes."
    assert rs.describe(rs.Schedule(rs.INTERVAL, 180)) == "Every 3 hours."
    assert rs.describe(rs.Schedule(rs.INTERVAL, 1440)) == "Every day."
    assert rs.describe(rs.Schedule(rs.TIMES, times=("06:00", "18:00"), days=(0, 1, 2, 3, 4))) == (
        "At 06:00 and 18:00, weekdays."
    )
    assert rs.describe(rs.Schedule(rs.TIMES)) == "At set times, none chosen yet."
    assert rs.describe(rs.Schedule(rs.LEARNED)).startswith("Learning when")
    assert rs.describe(rs.Schedule(rs.LEARNED), pattern=rs.Pattern(1, 6)) == (
        "Usually Tuesdays about 6 a.m.; checking closely then."
    )
    assert rs.describe(rs.Schedule(rs.LEARNED, pinned=(1, 6))).startswith("Pinned to Tuesdays")
    assert rs.describe(rs.Schedule(rs.PUBLISHER), hint=rs.Hint(10080, "weekly")) == (
        "The publisher says weekly."
    )
    assert rs.describe(rs.Schedule(rs.PUBLISHER)).startswith("The publisher gives no hint")


def test_next_due_per_kind_against_a_fixed_clock() -> None:
    checked = NOW - timedelta(minutes=50)
    assert rs.next_due(rs.Schedule(rs.MANUAL), NOW, checked) is None
    assert rs.next_due(rs.Schedule(rs.INTERVAL, 60), NOW, None) == NOW, "never checked is due now"
    assert rs.next_due(rs.Schedule(rs.INTERVAL, 60), NOW, checked) == checked + timedelta(
        minutes=60
    )
    at_times = rs.Schedule(rs.TIMES, times=("06:00", "18:00"), days=(0, 1, 2, 3, 4))
    assert rs.next_due(at_times, NOW, checked) == datetime(2026, 10, 6, 18, 0, tzinfo=UTC)
    friday_evening = datetime(2026, 10, 9, 19, 0, tzinfo=UTC)
    assert rs.next_due(at_times, friday_evening, friday_evening) == datetime(
        2026, 10, 12, 6, 0, tzinfo=UTC
    ), "weekends are skipped"
    assert rs.next_due(rs.Schedule(rs.PUBLISHER), NOW, checked, hint=rs.Hint(120, "")) == (
        checked + timedelta(minutes=120)
    )
    assert rs.next_due(rs.Schedule(rs.PUBLISHER), NOW, checked) == checked + timedelta(days=1)


def test_learning_finds_the_usual_day_and_hour_and_checks_closely_then() -> None:
    published = [
        datetime(2026, 9, 1 + 7 * n, 6, 10, tzinfo=UTC) for n in range(5)
    ]  # Tuesdays, 6 a.m.
    pattern = rs.learn(published)
    assert pattern is not None and (pattern.weekday, pattern.hour) == (1, 6)
    assert rs.learn(published[:2]) is None, "fewer than three episodes is nothing learned"
    scattered = [datetime(2026, 9, 1 + n, 3 * n, 0, tzinfo=UTC) for n in range(6)]
    assert rs.learn(scattered) is None
    learned = rs.Schedule(rs.LEARNED)
    checked = NOW - timedelta(minutes=1)
    # Tuesday 9 a.m. is three hours after the usual time: hourly for the rest of the day.
    assert rs.next_due(learned, NOW, checked, published=published) == checked + timedelta(
        minutes=60
    )
    close = datetime(2026, 10, 6, 5, 30, tzinfo=UTC)
    assert rs.next_due(learned, close, close, published=published) == close + timedelta(minutes=15)
    other_day = datetime(2026, 10, 8, 9, 0, tzinfo=UTC)
    assert rs.next_due(learned, other_day, other_day, published=published) == other_day + timedelta(
        days=1
    )


def test_the_publishers_hint_is_read_from_the_feed() -> None:
    sy = (
        "<channel><sy:updatePeriod>weekly</sy:updatePeriod>"
        "<sy:updateFrequency>2</sy:updateFrequency>"
    )
    assert rs.parse_hint(sy) == rs.Hint(5040, "2 times weekly")
    assert rs.parse_hint("<sy:updatePeriod>daily</sy:updatePeriod>") == rs.Hint(1440, "daily")
    p20 = (
        '<podcast:updateFrequency rrule="FREQ=WEEKLY;BYDAY=MO">'
        "Every Monday</podcast:updateFrequency>"
    )
    assert rs.parse_hint(p20) == rs.Hint(10080, "Every Monday")
    assert (
        rs.parse_hint(
            '<podcast:updateFrequency rrule="FREQ=WEEKLY;BYDAY=MO,WE,FR">x'
            "</podcast:updateFrequency>"
        ).minutes
        == 3360
    )
    assert not rs.parse_hint("<channel>nothing</channel>").is_known
    assert rs.parse_published("Tue, 01 Sep 2026 06:10:00 +0000") == datetime(
        2026, 9, 1, 6, 10, tzinfo=UTC
    )
    assert rs.parse_published("2026-09-01T06:10:00Z") == datetime(2026, 9, 1, 6, 10, tzinfo=UTC)
    assert rs.parse_published("") is None and rs.parse_published("yesterday") is None


# -- resolved against a library ------------------------------------------------- #


def _library() -> tuple[PodcastLibrary, PodcastShow]:
    library = PodcastLibrary()
    show = PodcastShow(id="s1", title="The Daily", feed_url="http://x.invalid/1")
    for n in range(4):
        show.episodes.append(
            PodcastEpisode(
                guid=f"e{n}",
                title=f"Ep {n}",
                audio_url="http://x/a.mp3",
                published=(datetime(2026, 9, 1 + 7 * n, 6, 0, tzinfo=UTC)).isoformat(),
            )
        )
    library.add_show(show)
    return library, show


def test_the_policy_resolves_the_legacy_interval_until_a_schedule_is_set() -> None:
    library, show = _library()
    assert schedule_policy.schedule_for(library, show) == rs.Schedule(rs.MANUAL)
    library.settings.refresh_minutes = 60
    assert schedule_policy.schedule_for(library, show) == rs.Schedule(rs.INTERVAL, 60)
    schedule_policy.set_schedule(library, show, rs.Schedule(rs.LEARNED))
    assert schedule_policy.schedule_for(library, show).kind == rs.LEARNED
    assert schedule_policy.schedule_for(library, None) == rs.Schedule(rs.INTERVAL, 60), (
        "the default is untouched"
    )
    assert "Tuesdays about 6 a.m." in schedule_policy.describe_for(library, show)
    assert schedule_policy.next_check(library, show, now=NOW) == NOW, "never checked: due now"
    assert schedule_policy.is_due(library, show, now=NOW)
    summary = schedule_policy.summary(library)
    assert summary.startswith("1 podcast: 0 on the shared schedule, 1 learned.")
    assert "every hour" in summary


def test_next_check_words_say_when() -> None:
    assert schedule_policy.next_check_words(None) == "never"
    assert schedule_policy.next_check_words(NOW, now=NOW) == "now"
    assert schedule_policy.next_check_words(NOW + timedelta(minutes=40), now=NOW) == "in 40 minutes"
    assert schedule_policy.next_check_words(NOW + timedelta(minutes=1), now=NOW) == "in 1 minute"
    assert schedule_policy.next_check_words(NOW + timedelta(days=5), now=NOW).startswith(
        "Sunday at "
    )


def test_a_paused_or_local_podcast_is_never_due() -> None:
    library, show = _library()
    library.settings.refresh_minutes = 60
    show.paused = True
    assert schedule_policy.next_check(library, show, now=NOW) is None
    show.paused = False
    show.feed_url = ""
    assert schedule_policy.next_check(library, show, now=NOW) is None
