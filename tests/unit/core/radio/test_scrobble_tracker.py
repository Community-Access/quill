"""The one-minute rule, against a fake clock: heard, not broadcast.

The rule and its time-shift behaviour come from BlindRadio by serrebidev (MIT).
"""

from __future__ import annotations

from quill.core.radio.scrobble_tracker import (
    MIN_HEARD_SECONDS,
    HeardTracker,
    Listen,
    song_from_title,
)

STATION = "station-1"
T0 = 1_800_000_000.0


def _run(
    tracker: HeardTracker, start: float, end: float, *, behind: float = 0.0, step: float = 5.0
):
    heard: list[Listen] = []
    started: list[Listen] = []
    moment = start
    while moment <= end:
        tick = tracker.tick(STATION, now=moment, behind=behind)
        heard.extend(tick.heard)
        if tick.started is not None:
            started.append(tick.started)
        moment += step
    return heard, started


def test_a_song_heard_for_a_minute_is_sent_once_stamped_when_hearing_began() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    heard, started = _run(tracker, T0, T0 + 180)
    assert heard == [Listen("Artist", "Song", int(T0))]
    assert started == [Listen("Artist", "Song", int(T0))]


def test_fifty_five_seconds_is_not_a_listen() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    heard, _ = _run(tracker, T0, T0 + 55)
    assert heard == []
    tracker.note_title(STATION, "Artist - Next", now=T0 + 56)
    heard, _ = _run(tracker, T0 + 60, T0 + 61)
    assert heard == [], "a song cut short is never sent, even when the next one starts"


def test_exactly_a_minute_counts() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    heard, _ = _run(tracker, T0, T0 + MIN_HEARD_SECONDS)
    assert len(heard) == 1


def test_noise_titles_and_titles_without_an_artist_are_never_sent() -> None:
    assert song_from_title("Live") is None
    assert song_from_title("My Station", "My Station") is None
    assert song_from_title("Just a title") is None
    assert song_from_title("") is None
    tracker = HeardTracker()
    tracker.note_title(STATION, "Advertisement", now=T0)
    heard, started = _run(tracker, T0, T0 + 300)
    assert heard == [] and started == []


def test_a_noise_title_ends_the_song_before_it() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    _run(tracker, T0, T0 + 30)
    tracker.note_title(STATION, "Live", now=T0 + 31)
    heard, _ = _run(tracker, T0 + 35, T0 + 200)
    assert heard == []


def test_the_broadcast_key_value_form_is_read() -> None:
    song = song_from_title('title="YOUR SONG",artist="Elton John",album="Elton John"')
    assert song == Listen("Elton John", "YOUR SONG", 0, "Elton John")


def test_time_shifted_listening_counts_when_heard_not_when_broadcast() -> None:
    """Song A is broadcast at T0 and B at T0+120, but we listen ten minutes behind."""
    tracker = HeardTracker()
    tracker.note_title(STATION, "A1 - Song A", now=T0)
    tracker.note_title(STATION, "B1 - Song B", now=T0 + 120)
    behind = 600.0
    # Live is now T0+600; the playhead is at T0, in song A.
    heard, started = _run(tracker, T0 + 600, T0 + 700, behind=behind)
    assert heard == [Listen("A1", "Song A", int(T0 + 600))], "stamped when heard"
    assert started[0].title == "Song A"
    # The playhead reaches B's broadcast start at wall time T0+720.
    heard, started = _run(tracker, T0 + 705, T0 + 800, behind=behind)
    assert [listen.title for listen in heard] == ["Song B"]
    assert heard[0].listened_at >= int(T0 + 720)


def test_a_pause_adds_nothing() -> None:
    """Paused: behind grows as fast as the clock, so the playhead stands still."""
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    _run(tracker, T0, T0 + 30)  # 30 s heard
    moment = T0 + 35
    while moment <= T0 + 600:  # paused for nine and a half minutes
        assert tracker.tick(STATION, now=moment, behind=moment - (T0 + 30)).heard == []
        moment += 5
    # Resumed: still in the same song, 30 s more is the minute.
    behind = (T0 + 600) - (T0 + 30)
    heard, _ = _run(tracker, T0 + 605, T0 + 640, behind=behind)
    assert [listen.title for listen in heard] == ["Song"]
    assert heard[0].listened_at == int(T0), "the listen began before the pause"


def test_rewinding_adds_nothing_and_jumping_ahead_adds_only_real_time() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0 - 1000)
    tracker.tick(STATION, now=T0, behind=500.0)
    # Jump 400 s forward in five seconds of real time: only 5 s counted.
    assert tracker.tick(STATION, now=T0 + 5, behind=100.0).heard == []
    # Rewind: nothing counted, never negative.
    assert tracker.tick(STATION, now=T0 + 10, behind=300.0).heard == []
    heard, _ = _run(tracker, T0 + 15, T0 + 60, behind=300.0)
    assert heard == []
    heard, _ = _run(tracker, T0 + 65, T0 + 80, behind=300.0)
    assert len(heard) == 1


def test_a_new_station_starts_clean() -> None:
    tracker = HeardTracker()
    tracker.note_title(STATION, "Artist - Song", now=T0)
    _run(tracker, T0, T0 + 50)
    tick = tracker.tick("station-2", now=T0 + 55, behind=0)
    assert tick.heard == [] and tracker.station == "station-2"
    heard, _ = _run(tracker, T0 + 60, T0 + 200)
    assert heard == [], "the old station's song does not follow you"


def test_a_repeated_title_is_one_song() -> None:
    tracker = HeardTracker()
    for offset in (0, 30, 60, 90):
        tracker.note_title(STATION, "Artist - Song", now=T0 + offset)
    heard, started = _run(tracker, T0, T0 + 180)
    assert len(heard) == 1 and len(started) == 1


def test_listens_survive_the_round_trip_through_the_queue_file() -> None:
    listen = Listen("A", "T", 1_800_000_000, "Al")
    assert Listen.from_dict(listen.to_dict()) == listen
    assert Listen.from_dict({"artist": "A", "title": "", "listened_at": 5}) is None
    assert Listen.from_dict("nonsense") is None
